"""FastAPI app for Manas OS.

Reads from manas.db (SQLite) — no CSVs, no legacy file coupling. Endpoints
register here as phases land. P1 surface: the Sectors & Themes leaderboard
behind the regime page.

Run with:  python -m manas_os.api     (see __main__.py → uvicorn on :8000)
"""
from __future__ import annotations

from typing import Any
import json
import re
import threading
import time
from datetime import date as _date
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from manas_os import config, db, market_calendar
from manas_os.agents import coach as agents_coach
from manas_os.alerts import eod as eod_alerts
from manas_os.regime import regime_hmm
from manas_os.regime import snapshot as regime_snapshot
from manas_os.regime.governor import governor
from manas_os.engine import eod_detectors, manas_indicators, pine_ports, price_action
from manas_os.regime.sectors import INDUSTRY_TO_SECTOR, canonical_sector_key, display_label, industries_for_sector
from manas_os.scanner import candidates as scanner_candidates
from manas_os.scanner import expectancy as scanner_expectancy
from manas_os.scanner import mentor_checklists
from manas_os.scanner import outcomes as scanner_outcomes
from manas_os.sources import chartsmaze
from manas_os.ml import screener_calibration
from manas_os.ml import stock_hmm

app = FastAPI(title="Manas AI Trading OS", version="0.0.1")

# Single-user, local-first: dev runs Vite on :5173 and this API on :8000, so
# allow the Vite origin. GET for reads; POST is needed for the Fyers login
# flow (credentials + auth-code exchange). Single-user localhost only.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


def _most_recent_snapshot(conn, table: str, on_or_before: str) -> str | None:
    """Latest snapshot_date <= on_or_before that actually has rows in `table`."""
    row = conn.execute(
        f"SELECT MAX(snapshot_date) AS d FROM {table} WHERE snapshot_date <= ?",
        (on_or_before,),
    ).fetchone()
    return row["d"] if row and row["d"] else None


def _sector_downside_by_key(conn, on_or_before: str) -> dict[str, dict[str, Any]]:
    """SHIP-1 #15 (I14): sector_key -> {p_drawdown_5d, n_train} from the most
    recent sector_downside as_of <= on_or_before. Empty dict when the table
    doesn't exist yet or the walk-forward gate hasn't ever passed (no rows
    written) — EXPERIMENTAL, display-only, never touches gates/sizing."""
    try:
        row = conn.execute(
            "SELECT MAX(as_of) AS d FROM sector_downside WHERE as_of <= ?", (on_or_before,)
        ).fetchone()
    except Exception:
        return {}
    as_of = row["d"] if row and row["d"] else None
    if as_of is None:
        return {}
    rows = conn.execute(
        "SELECT sector, p_drawdown_5d, n_train FROM sector_downside WHERE as_of = ?", (as_of,)
    ).fetchall()
    return {r["sector"]: {"p_drawdown_5d": r["p_drawdown_5d"], "n_train": r["n_train"]} for r in rows}


def _sector_rs_1w_ago(conn, sec_date: str) -> dict[str, float | None]:
    """sector_key -> rs_score from the sector_metrics snapshot ~1 trading week (5
    sessions) before `sec_date`. Used to compute a B1 "1-week RS delta" chip.

    sector_metrics only has one row per (snapshot_date, sector_key), so "1 week
    ago" is resolved by walking back 5 distinct snapshot_dates rather than by
    calendar days (skips weekends/holidays without a trading calendar table).
    Returns {} if there aren't at least 6 distinct snapshot dates on or before
    sec_date (not enough history yet for a delta).
    """
    dates = [
        r["snapshot_date"]
        for r in conn.execute(
            "SELECT DISTINCT snapshot_date FROM sector_metrics WHERE snapshot_date <= ? "
            "ORDER BY snapshot_date DESC LIMIT 6",
            (sec_date,),
        ).fetchall()
    ]
    if len(dates) < 6:
        return {}
    prior_date = dates[5]
    rows = conn.execute(
        "SELECT sector_key, rs_score FROM sector_metrics WHERE snapshot_date = ?",
        (prior_date,),
    ).fetchall()
    return {r["sector_key"]: r["rs_score"] for r in rows}


def _index_returns(conn, on_or_before: str) -> tuple[str | None, list[dict[str, Any]]]:
    """Return 1D/1W/1M/3M/6M performance for cached sector indices.

    Returns use trading-row offsets, not calendar days: 1W=5 sessions,
    1M=21, 3M=63, 6M=126. Missing history returns null per timeframe.
    """
    latest = conn.execute(
        "SELECT MAX(trade_date) AS d FROM sector_index_prices WHERE trade_date <= ?",
        (on_or_before,),
    ).fetchone()
    if not latest or not latest["d"]:
        return None, []
    latest_date = latest["d"]
    symbols = [
        r["symbol"]
        for r in conn.execute(
            "SELECT DISTINCT symbol FROM sector_index_prices WHERE trade_date = ? ORDER BY symbol",
            (latest_date,),
        ).fetchall()
    ]
    offsets = {"1d": 1, "1w": 5, "1m": 21, "3m": 63, "6m": 126}
    out = []
    for symbol in symbols:
        rows = conn.execute(
            "SELECT trade_date, close FROM sector_index_prices "
            "WHERE symbol = ? AND trade_date <= ? AND close IS NOT NULL "
            "ORDER BY trade_date DESC LIMIT ?",
            (symbol, latest_date, max(offsets.values()) + 1),
        ).fetchall()
        if not rows:
            continue
        latest_close = rows[0]["close"]
        returns: dict[str, float | None] = {}
        for key, offset in offsets.items():
            if latest_close is None or len(rows) <= offset or rows[offset]["close"] in (None, 0):
                returns[key] = None
            else:
                pct = (float(latest_close) - float(rows[offset]["close"])) / float(rows[offset]["close"]) * 100.0
                # Sanity guard: an index never moves >300% over these windows;
                # such a value means a bad/placeholder row in sector_index_prices
                # (e.g. the ~6mo data edge). Surface null, not garbage.
                returns[key] = None if abs(pct) > 300.0 else _round(pct)
        out.append({
            "symbol": symbol,
            "name": display_label(canonical_sector_key(symbol, "index")) if symbol.startswith("NIFTY ") else symbol,
            "as_of": latest_date,
            "close": _round(latest_close),
            "returns": returns,
        })
    return latest_date, out


def _most_recent_stock_rs_date(on_or_before: str) -> str | None:
    root = chartsmaze.chartsmaze_dir()
    if not root.is_dir():
        return None
    candidates = []
    for child in root.iterdir():
        if not child.is_dir() or child.name > on_or_before:
            continue
        path = child / "analytics" / "sector-analytics-Relative Strength-stocks.csv"
        if path.is_file():
            candidates.append(child.name)
    return max(candidates) if candidates else None


def _stock_rows_for_industries(run_date: str, industries: set[str]) -> list[dict[str, Any]]:
    try:
        df = chartsmaze.read_stock_relative_strength(run_date)
    except Exception:
        return []
    required = {"ticker", "industry", "rs"}
    if df.empty or not required <= set(df.columns):
        return []
    rows = []
    for _, r in df.iterrows():
        industry = str(r["industry"]).strip()
        if industry not in industries:
            continue
        rs = r.get("rs")
        rows.append({
            "ticker": str(r["ticker"]).strip().upper(),
            "rs": None if rs is None else float(rs),
        })
    return sorted(rows, key=lambda item: (item["rs"] is None, -(item["rs"] or 0), item["ticker"]))


def _unavailable_stock_payload(**identity: Any) -> dict[str, Any]:
    return {"available": False, **identity, "stocks": [], "count": 0}


def _json_col(value: str | None, fallback: Any) -> Any:
    if value is None:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def _known_pillars_from_technical_detail(technical_detail: str | None) -> int | None:
    """Recover known_pillars from the persisted technical_detail audit string
    (``... known_pillars=N ...``, always written by snapshot.py's
    _technical_detail). regime_snapshots has no known_pillars column of its
    own; this lets the read-time stale-explanation rebuild (JOB 1 bug fix,
    see stale_read_explanation) know the same "N of M checks" figure the
    original write-time explanation used, without a schema change."""
    if not technical_detail:
        return None
    match = re.search(r"known_pillars=(\d+)", technical_detail)
    return int(match.group(1)) if match else None


def _latest_price_date(conn, on_or_before: str) -> str | None:
    row = conn.execute(
        "SELECT MAX(trade_date) AS d FROM daily_prices "
        "WHERE series='EQ' AND trade_date <= ?",
        (on_or_before,),
    ).fetchone()
    return row["d"] if row and row["d"] else None


def _load_symbol_bars(conn, symbol: str, on_or_before: str, limit: int = 260) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT trade_date AS date, open, high, low, close, prev_close, volume, "
        "delivery_qty, delivery_pct "
        "FROM daily_prices WHERE symbol = ? AND series = 'EQ' AND trade_date <= ? "
        "ORDER BY trade_date DESC LIMIT ?",
        (symbol.upper(), on_or_before, limit),
    ).fetchall()
    return [dict(r) for r in reversed(rows)]


def _position_lifecycle(conn, symbol: str, entry_date: str, on_or_before: str,
                        entry: float, stop: float) -> list[dict[str, Any]]:
    """W2.3 trade lifecycle river: per-session open-R from entry to as-of,
    with the trail_plan phase band at each point. One writer — reads
    daily_prices only, phase derived from R via the same thresholds
    trail_plan uses (r<1 INITIATION, <2 TREND, else EXTENSION). Returns
    [{date, r, phase}] over the holding window; empty when entry/stop are
    invalid or no bars exist after entry."""
    try:
        entry_f = float(entry)
        stop_f = float(stop)
    except (TypeError, ValueError):
        return []
    risk = entry_f - stop_f
    if risk <= 0 or not entry_date:
        return []
    rows = conn.execute(
        "SELECT trade_date AS date, close FROM daily_prices "
        "WHERE symbol = ? AND series = 'EQ' AND trade_date >= ? AND trade_date <= ? "
        "AND close IS NOT NULL ORDER BY trade_date",
        (str(symbol).upper(), entry_date, on_or_before),
    ).fetchall()
    series = []
    for row in rows:
        close = float(row["close"])
        r = round((close - entry_f) / risk, 2)
        phase = "INITIATION" if r < 1.0 else ("TREND" if r < 2.0 else "EXTENSION")
        series.append({"date": row["date"], "r": r, "phase": phase})
    return series


def _ema(values: list[float | None], span: int) -> list[float | None]:
    alpha = 2.0 / (span + 1.0)
    prev: float | None = None
    out: list[float | None] = []
    for value in values:
        if value is None:
            out.append(prev)
            continue
        prev = value if prev is None else (value * alpha) + (prev * (1.0 - alpha))
        out.append(prev)
    return out


def _avg(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _round(value: Any, ndigits: int = 2) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value), ndigits)
    except (TypeError, ValueError):
        return None


def _symbol_timing(conn, symbol: str, on_or_before: str) -> dict[str, Any]:
    sym = symbol.upper()
    bars = _load_symbol_bars(conn, sym, on_or_before, 80)
    if not bars:
        return {"available": False, "symbol": sym, "as_of": None}

    latest = bars[-1]
    prior = bars[:-1]
    prior20 = prior[-20:]
    close = latest.get("close")
    open_ = latest.get("open")
    prev_close = latest.get("prev_close")
    if prev_close is None and prior:
        prev_close = prior[-1].get("close")

    prior_volumes = [float(b["volume"]) for b in prior20 if b.get("volume") not in (None, 0)]
    avg_vol = _avg(prior_volumes)
    rvol = (float(latest["volume"]) / avg_vol) if latest.get("volume") and avg_vol else None

    gap_pct = None
    if open_ is not None and prev_close:
        gap_pct = (float(open_) - float(prev_close)) / float(prev_close) * 100.0

    ranges = []
    for b in bars[-14:]:
        if b.get("high") is not None and b.get("low") is not None and b.get("close"):
            ranges.append((float(b["high"]) - float(b["low"])) / float(b["close"]) * 100.0)
    adr = _avg(ranges)

    prior_highs = [float(b["high"]) for b in prior20 if b.get("high") is not None]
    prior_lows = [float(b["low"]) for b in prior20 if b.get("low") is not None]
    pivot = max(prior_highs) if prior_highs else None
    stop = min(prior_lows) if prior_lows else None
    dist_pivot = None
    if close is not None and pivot:
        dist_pivot = (float(close) - pivot) / pivot * 100.0

    read_parts = []
    if rvol is not None:
        read_parts.append("RVOL building" if rvol >= 1.5 else "volume is not yet expanded")
    if dist_pivot is not None:
        if abs(dist_pivot) <= 1.0:
            read_parts.append("price is sitting near pivot")
        elif dist_pivot > 1.0:
            read_parts.append("price is extended above pivot")
        else:
            read_parts.append("price is still below pivot")
    if latest.get("delivery_pct") is not None:
        read_parts.append(
            "delivery is strong" if float(latest["delivery_pct"]) >= 60 else "delivery is ordinary"
        )
    read = "; ".join(read_parts) + "." if read_parts else "Not enough timing data yet."

    return {
        "available": True,
        "symbol": sym,
        "as_of": latest["date"],
        "close": _round(close),
        "entry": _round(pivot),
        "pivot": _round(pivot),
        "stop": _round(stop),
        "rvol": _round(rvol),
        "gap_pct": _round(gap_pct),
        "dist_pivot": _round(dist_pivot),
        "adr": _round(adr),
        "delivery_pct": _round(latest.get("delivery_pct")),
        "read": read,
    }


def _latest_symbols(conn, on_or_before: str, limit: int = 200) -> tuple[str | None, list[str]]:
    price_date = _latest_price_date(conn, on_or_before)
    if price_date is None:
        return None, []
    rows = conn.execute(
        "SELECT symbol FROM daily_prices WHERE series='EQ' AND trade_date = ? "
        "ORDER BY COALESCE(delivery_pct, 0) DESC, COALESCE(volume, 0) DESC, symbol LIMIT ?",
        (price_date, limit),
    ).fetchall()
    return price_date, [r["symbol"] for r in rows]


def _stock_rs_map(on_or_before: str) -> dict[str, dict[str, Any]]:
    run_date = _most_recent_stock_rs_date(on_or_before)
    if run_date is None:
        return {}
    try:
        df = chartsmaze.read_stock_relative_strength(run_date)
    except Exception:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for _, row in df.iterrows():
        ticker = str(row.get("ticker") or "").strip().upper()
        if not ticker:
            continue
        industry = str(row.get("industry") or "").strip()
        rs = row.get("rs")
        out[ticker] = {
            "rs": None if rs is None else float(rs),
            "rs_as_of": run_date,
            "industry": industry or None,
            "sector": INDUSTRY_TO_SECTOR.get(industry),
        }
    return out


def _grade(readiness: float) -> str:
    if readiness >= 90:
        return "A+"
    if readiness >= 75:
        return "A"
    if readiness >= 60:
        return "B"
    return "C"


def _candidate_for_symbol(
    conn,
    symbol: str,
    on_or_before: str,
    rs_info: dict[str, Any] | None,
) -> dict[str, Any] | None:
    timing = _symbol_timing(conn, symbol, on_or_before)
    if not timing.get("available"):
        return None
    state = price_action.signals_for_symbol(conn, symbol, timing["as_of"], max_bars=180)
    latest_signals = [s for s in state["recent_signals"] if s.get("date") == timing["as_of"]]

    evidence: list[dict[str, Any]] = []
    setup = "Watchlist timing"
    if timing.get("delivery_pct") is not None and timing["delivery_pct"] >= 60:
        evidence.append({"filter": "delivery>=60", "value": f"{timing['delivery_pct']:.0f}%"})
    if timing.get("rvol") is not None and timing["rvol"] >= 1.5:
        evidence.append({"filter": "rvol>=1.5", "value": f"{timing['rvol']:.2f}x"})
    if timing.get("dist_pivot") is not None and abs(timing["dist_pivot"]) <= 3:
        evidence.append({"filter": "near-pivot", "value": f"{timing['dist_pivot']:+.1f}%"})
        setup = "Near pivot"

    for sig in latest_signals[:3]:
        evidence.append({"filter": sig["kind"], "value": sig["detail"]})
        if sig["kind"] == "POCKET_PIVOT":
            setup = "Pocket pivot"
        elif sig["kind"] == "SHAKEOUT":
            setup = "Shakeout"
        elif "TOUCH" in sig["kind"]:
            setup = "Pullback-to-EMA"

    rs = None if not rs_info else rs_info.get("rs")
    if rs is not None and rs >= 70:
        evidence.append({"filter": "rs>=70", "value": f"{rs:.0f}"})
    if not evidence:
        return None

    readiness = 35 + min(45, len(evidence) * 12)
    if rs is not None:
        readiness += min(15, max(0, rs - 50) / 50 * 15)
    if timing.get("dist_pivot") is not None and abs(timing["dist_pivot"]) <= 1:
        readiness += 5
    readiness = round(min(100, readiness), 1)
    grade = _grade(readiness)
    read = (
        f"{setup}: " + "; ".join(f"{e['filter']} {e['value']}" for e in evidence[:3]) + "."
    )

    return {
        "symbol": symbol,
        "setup": setup,
        "readiness": readiness,
        "grade": grade,
        "rs": rs,
        "rs_as_of": None if not rs_info else rs_info.get("rs_as_of"),
        "delivery_pct": timing.get("delivery_pct"),
        "delivery_as_of": timing.get("as_of"),
        "pivot": timing.get("pivot"),
        "entry": timing.get("entry"),
        "stop": timing.get("stop"),
        "target": _round(timing["entry"] + ((timing["entry"] - timing["stop"]) * 2), 2)
        if timing.get("entry") is not None and timing.get("stop") is not None
        else None,
        "evidence": evidence,
        "read": read,
        "timing": timing,
        "sector": None if not rs_info else rs_info.get("sector"),
        "industry": None if not rs_info else rs_info.get("industry"),
    }


def _ensure_journal_table(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS journal_trades ("
        "trade_id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "trade_date TEXT NOT NULL, symbol TEXT NOT NULL, setup TEXT, "
        "entry REAL, exit REAL, stop REAL, r_result REAL, mistake_tags_json TEXT, "
        "notes TEXT, created_at TEXT DEFAULT (datetime('now')))"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_journal_trades_date ON journal_trades(trade_date)")
    have = {r[1] for r in conn.execute("PRAGMA table_info(journal_trades)")}
    if "exit_state_json" not in have:
        conn.execute("ALTER TABLE journal_trades ADD COLUMN exit_state_json TEXT")
    if "first_exit_flag_date" not in have:
        conn.execute("ALTER TABLE journal_trades ADD COLUMN first_exit_flag_date TEXT")
    # W1.5: exit_date so per-trade MFE/MAE can be computed over the actual
    # holding window [trade_date, exit_date]. Null while the trade is open.
    if "exit_date" not in have:
        conn.execute("ALTER TABLE journal_trades ADD COLUMN exit_date TEXT")
    if "qty" not in have:
        conn.execute("ALTER TABLE journal_trades ADD COLUMN qty REAL")


def _ensure_watchlist_exit_columns(conn) -> None:
    have = {r[1] for r in conn.execute("PRAGMA table_info(watchlist)")}
    if "exit_state_json" not in have:
        conn.execute("ALTER TABLE watchlist ADD COLUMN exit_state_json TEXT")


def _ensure_journal_flag_column(conn) -> None:
    have = {r[1] for r in conn.execute("PRAGMA table_info(journal_trades)")}
    if "first_exit_flag_date" not in have:
        conn.execute("ALTER TABLE journal_trades ADD COLUMN first_exit_flag_date TEXT")


def _ensure_avwap_anchors(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS avwap_anchors ("
        "symbol TEXT, as_of TEXT, anchor_date TEXT, anchor_type TEXT, reason TEXT, "
        "PRIMARY KEY(symbol, as_of))"
    )


def _ensure_organic_watchlist_schema(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS watchlist_candidates ("
        "candidate_date TEXT NOT NULL, symbol TEXT NOT NULL, source TEXT NOT NULL, "
        "status TEXT NOT NULL DEFAULT 'tracking', reason TEXT, failed_gate TEXT, "
        "snapshot_json TEXT, created_at TEXT DEFAULT (datetime('now')), "
        "updated_at TEXT DEFAULT (datetime('now')), "
        "PRIMARY KEY(candidate_date, symbol, source))"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_watchlist_candidates_symbol "
        "ON watchlist_candidates(symbol, candidate_date DESC)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS gate_overrides ("
        "override_date TEXT NOT NULL, symbol TEXT NOT NULL, reason TEXT, "
        "half_size INTEGER NOT NULL DEFAULT 1, failed_gate TEXT, snapshot_json TEXT, "
        "created_at TEXT DEFAULT (datetime('now')), "
        "PRIMARY KEY(override_date, symbol))"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS watchlist_candidate_outcomes ("
        "candidate_date TEXT NOT NULL, symbol TEXT NOT NULL, source TEXT NOT NULL, "
        "close_0 REAL, close_5 REAL, close_10 REAL, close_20 REAL, "
        "ret_5 REAL, ret_10 REAL, ret_20 REAL, updated_at TEXT DEFAULT (datetime('now')), "
        "PRIMARY KEY(candidate_date, symbol, source))"
    )


def _mini_chart_payload(conn, symbol: str, on_or_before: str, limit: int = 70) -> dict[str, Any]:
    bars = _load_symbol_bars(conn, symbol, on_or_before, limit)
    closes = [_round(b.get("close")) for b in bars]
    ema21 = _ema(closes, 21)
    candles = [
        {
            "date": b.get("date"),
            "open": _round(b.get("open")),
            "high": _round(b.get("high")),
            "low": _round(b.get("low")),
            "close": _round(b.get("close")),
            "volume": b.get("volume"),
        }
        for b in bars
    ]
    return {
        "available": bool(candles),
        "symbol": symbol.upper(),
        "as_of": candles[-1]["date"] if candles else None,
        "candles": candles,
        "ema21": [{"date": b.get("date"), "value": _round(v)} for b, v in zip(bars, ema21) if v is not None],
    }


def _distance_to_pass(failed_gate: str | None, evidence: Any, reason: str | None) -> dict[str, Any]:
    gate = (failed_gate or "gate").lower()
    text = reason or "Needs one more confirming condition."
    evidence = evidence if isinstance(evidence, dict) else {}
    numbers = [float(x) for x in re.findall(r"[-+]?\d+(?:\.\d+)?", text)]
    value = None
    unit = ""
    what = "Recheck on the next scan; needs the failed gate to flip."
    severity = "caution"
    if "fresh" in gate and len(numbers) >= 2:
        value = abs(numbers[0] - numbers[1])
        unit = "pp"
        what = f"Needs extension back inside the fresh-leg cap near {numbers[1]:g}%."
    elif "risk" in gate:
        rr = evidence.get("rr") or evidence.get("risk_reward")
        stop_pct = evidence.get("stop_pct")
        if rr is not None:
            value = max(0.0, 1.5 - float(rr))
            unit = "R"
            what = "Needs a tighter stop or higher target to restore acceptable R:R."
        elif stop_pct is not None:
            value = max(0.0, float(stop_pct) - 8.0)
            unit = "pp"
            what = "Needs invalidation inside the stop-width cap."
        else:
            what = "Needs valid entry, stop, target, and position size geometry."
    elif "particip" in gate:
        dz = evidence.get("delivery_z")
        rvol = evidence.get("rvol")
        if dz is not None:
            value = max(0.0, 1.0 - float(dz))
            unit = "z"
            what = "Needs delivery participation to expand."
        elif rvol is not None:
            value = max(0.0, 1.5 - float(rvol))
            unit = "x"
            what = "Needs volume expansion before it graduates."
    elif "trend" in gate:
        value = None
        what = "Needs price back above the trend template and leadership line."
    elif "trad" in gate:
        value = None
        what = "Needs liquidity, quality, or exchange filters to clear."
        severity = "hard"
    elif "regime" in gate:
        value = None
        what = "Track only until the market mode allows this setup family."
    label = "watch" if severity != "hard" else "hard no"
    return {
        "label": label,
        "value": _round(value),
        "unit": unit,
        "what_would_it_take": what,
        "read": text,
        "severity": severity,
    }


def _upsert_candidate_outcome(conn, candidate_date: str, symbol: str, source: str) -> dict[str, Any]:
    rows = conn.execute(
        "SELECT trade_date, close FROM daily_prices WHERE symbol = ? AND series = 'EQ' "
        "AND trade_date >= ? AND close IS NOT NULL ORDER BY trade_date ASC LIMIT 21",
        (symbol.upper(), candidate_date),
    ).fetchall()
    closes = [float(r["close"]) for r in rows]
    close_0 = closes[0] if closes else None
    def at(offset: int) -> float | None:
        return closes[offset] if len(closes) > offset else None
    def ret(close_n: float | None) -> float | None:
        return None if close_0 in (None, 0) or close_n is None else (close_n - close_0) / close_0 * 100.0
    close_5, close_10, close_20 = at(5), at(10), at(20)
    payload = {
        "close_0": _round(close_0),
        "close_5": _round(close_5),
        "close_10": _round(close_10),
        "close_20": _round(close_20),
        "ret_5": _round(ret(close_5)),
        "ret_10": _round(ret(close_10)),
        "ret_20": _round(ret(close_20)),
    }
    conn.execute(
        "INSERT INTO watchlist_candidate_outcomes "
        "(candidate_date, symbol, source, close_0, close_5, close_10, close_20, ret_5, ret_10, ret_20, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now')) "
        "ON CONFLICT(candidate_date, symbol, source) DO UPDATE SET "
        "close_0=excluded.close_0, close_5=excluded.close_5, close_10=excluded.close_10, "
        "close_20=excluded.close_20, ret_5=excluded.ret_5, ret_10=excluded.ret_10, "
        "ret_20=excluded.ret_20, updated_at=datetime('now')",
        (candidate_date, symbol.upper(), source, payload["close_0"], payload["close_5"], payload["close_10"],
         payload["close_20"], payload["ret_5"], payload["ret_10"], payload["ret_20"]),
    )
    return payload


def _near_miss_items(conn, on_or_before: str, limit: int) -> tuple[str | None, list[dict[str, Any]]]:
    scanner_candidates.ensure_refusals_schema(conn)
    _ensure_organic_watchlist_schema(conn)
    row = conn.execute("SELECT MAX(scan_date) AS d FROM refusals WHERE scan_date <= ?", (on_or_before,)).fetchone()
    if not row or not row["d"]:
        return None, []
    scan_date = row["d"]
    rows = conn.execute(
        "SELECT scan_date, symbol, setup_family, failed_gate, reason, evidence_json FROM refusals "
        "WHERE scan_date = ? ORDER BY failed_gate, symbol LIMIT ?",
        (scan_date, limit),
    ).fetchall()
    items = []
    for row in rows:
        evidence = _json_col(row["evidence_json"], {})
        tracked = conn.execute(
            "SELECT status, source, created_at FROM watchlist_candidates "
            "WHERE candidate_date = ? AND symbol = ? ORDER BY updated_at DESC LIMIT 1",
            (row["scan_date"], row["symbol"]),
        ).fetchone()
        override = conn.execute(
            "SELECT reason, half_size, created_at FROM gate_overrides WHERE override_date = ? AND symbol = ?",
            (row["scan_date"], row["symbol"]),
        ).fetchone()
        outcome = _upsert_candidate_outcome(conn, row["scan_date"], row["symbol"], "near_miss")
        items.append({
            "candidate_date": row["scan_date"],
            "symbol": row["symbol"],
            "setup_family": row["setup_family"],
            "failed_gate": row["failed_gate"],
            "reason": row["reason"],
            "evidence": evidence,
            "distance": _distance_to_pass(row["failed_gate"], evidence, row["reason"]),
            "chart": _mini_chart_payload(conn, row["symbol"], scan_date, 70),
            "tracked": dict(tracked) if tracked else None,
            "override": dict(override) if override else None,
            "outcome": outcome,
        })
    return scan_date, items


def _symbol_exit_state(conn, symbol: str, on_or_before: str) -> dict[str, Any]:
    price_date = _latest_price_date(conn, on_or_before)
    if price_date is None:
        return {"state": "Intact", "fired_rules": [], "read": "No price rows available for exit state."}
    return eod_detectors.exit_state(_load_symbol_bars(conn, symbol, price_date, 260))


def _setup_family_for_trade(trade_row) -> str:
    setup_name = str(trade_row["setup"] or "").lower()
    return "catalyst" if setup_name in {"ep", "ipo_base"} or "ep" in setup_name else "base/pattern"


def _latest_regime(conn, as_of: str) -> str:
    row = conn.execute(
        "SELECT market_mode FROM regime_snapshots WHERE snapshot_date <= ? "
        "ORDER BY snapshot_date DESC LIMIT 1",
        (as_of,),
    ).fetchone()
    return str(row["market_mode"]).upper() if row and row["market_mode"] else "UNKNOWN"


def _plain_coach_instruction(trade_row, trail: dict[str, Any], strikes: dict[str, Any]) -> str:
    phase = trail.get("phase")
    trail_stop = trail.get("trail_stop")
    fired = strikes.get("fired") or []
    if strikes.get("exit_now"):
        return (
            f"EXIT TODAY - {len(fired)} exit rules fired ({', '.join(fired)}). "
            "Sell the full position near the close."
        )
    if phase == "TREND":
        ema_name = "EMA10" if "EMA10" in str(trail.get("action", "")) else "EMA21"
        return f"HOLD - trailing {ema_name} (now {trail_stop}). You're +{trail.get('r')}R."
    if phase == "EXTENSION":
        return f"TRIM 25-33% into strength; tighten stop to the 2-bar low ({trail_stop})."
    return (
        f"HOLD - do nothing. Stop stays at {trade_row['stop']}. "
        "Wobble in the first few days is normal; the trade isn't wrong until the stop breaks."
    )


def _trading_sessions_since(flag_date: str | None, as_of: str) -> int:
    if not flag_date:
        return 0
    try:
        start = _date.fromisoformat(flag_date)
        end = _date.fromisoformat(as_of)
    except ValueError:
        return 0
    if end <= start:
        return 0
    return market_calendar.trading_days_between(start, end) + (1 if market_calendar.is_trading_day(end) else 0)


def _coach_for_open_trade(conn, trade_row, as_of: str) -> dict[str, Any] | None:
    _ensure_journal_flag_column(conn)
    if trade_row["entry"] is None or trade_row["stop"] is None:
        return None
    bars = _load_symbol_bars(conn, trade_row["symbol"], as_of, 80)
    if not bars:
        return None
    setup_family = _setup_family_for_trade(trade_row)
    trail = eod_detectors.trail_plan(
        bars,
        float(trade_row["entry"]),
        float(trade_row["stop"]),
        setup_family,
    )
    strikes = eod_detectors.two_strike(bars)
    verdict = {"INITIATION": "HOLD", "TREND": "HOLD", "EXTENSION": "TRIM"}.get(
        trail.get("phase"), "HOLD"
    )
    if strikes.get("exit_now"):
        verdict = "EXIT"
    out = {
        "available": True,
        "trade_id": trade_row["trade_id"] if "trade_id" in trade_row.keys() else None,
        "symbol": trade_row["symbol"],
        "phase": trail.get("phase"),
        "verdict": verdict,
        "r": trail.get("r"),
        "trail_stop": trail.get("trail_stop"),
        "plain_instruction": _plain_coach_instruction(trade_row, trail, strikes),
        "why": trail.get("why", []),
        "fired": strikes.get("fired", []),
        "exit_now": bool(strikes.get("exit_now")),
        "action": trail.get("action"),
    }
    if out["trade_id"] is not None:
        first_flag = trade_row["first_exit_flag_date"] if "first_exit_flag_date" in trade_row.keys() else None
        if out["exit_now"] and not first_flag:
            first_flag = as_of
            conn.execute(
                "UPDATE journal_trades SET first_exit_flag_date = ? WHERE trade_id = ?",
                (as_of, out["trade_id"]),
            )
        elif not out["exit_now"] and first_flag:
            first_flag = None
            conn.execute(
                "UPDATE journal_trades SET first_exit_flag_date = NULL WHERE trade_id = ?",
                (out["trade_id"],),
            )
        if out["exit_now"] and first_flag:
            sessions = _trading_sessions_since(first_flag, as_of)
            if sessions >= 2:
                out["banner"] = f"OVERDUE EXIT - flagged {sessions} sessions ago, still open"
    chip = scanner_expectancy.chip_for(conn, setup_family, _latest_regime(conn, as_of))
    personal = chip.get("personal") if chip else None
    if personal and int(personal.get("n") or 0) >= 10:
        latest = conn.execute("SELECT MAX(as_of) AS d FROM setup_expectancy").fetchone()
        row = conn.execute(
            "SELECT mean_r FROM setup_expectancy WHERE as_of = ? AND loop = 'personal' "
            "AND setup_family = ? AND regime = ?",
            (latest["d"] if latest else None, setup_family, _latest_regime(conn, as_of)),
        ).fetchone()
        mean_r = row["mean_r"] if row else personal.get("posterior_r")
        out["fear_greed_note"] = (
            f"your last {int(personal['n'])} trades in this family averaged {mean_r}R"
        )
    return out


def _order_ticket_for_scan(conn, scan_date: str | None) -> dict[str, Any] | None:
    """Copyable order ticket for the latest TAKEN setup decision.

    The ticket is presentation-only over the persisted scan candidate and the
    setup_decisions row. It does not recompute entry/stop/qty in the UI or here;
    it only chooses the user-entered override when present, otherwise the
    candidate's one-writer values.
    """
    if not scan_date:
        return None
    row = conn.execute(
        "SELECT d.symbol, d.entry_price, d.qty, c.setup, c.entry, c.stop, "
        "c.suggested_qty, c.rr, c.readiness "
        "FROM setup_decisions d "
        "JOIN scan_candidates c ON c.scan_date = d.scan_date AND c.symbol = d.symbol "
        "WHERE d.scan_date = ? AND d.decision = 'taken' "
        "ORDER BY d.created_at DESC, c.readiness DESC LIMIT 1",
        (scan_date,),
    ).fetchone()
    if not row:
        return None
    entry = row["entry_price"] if row["entry_price"] is not None else row["entry"]
    qty = row["qty"] if row["qty"] is not None else row["suggested_qty"]
    stop = row["stop"]
    risk_rupees = None
    if entry is not None and stop is not None and qty is not None:
        risk_rupees = round(max(0.0, float(entry) - float(stop)) * int(qty), 2)
    parts = [
        f"BUY {row['symbol']} only above {entry}",
        f"QTY {qty}",
        f"STOP {stop}",
    ]
    if risk_rupees is not None:
        parts.append(f"RISK Rs {risk_rupees}")
    if row["rr"] is not None:
        parts.append(f"R:R {row['rr']}")
    return {
        "symbol": row["symbol"],
        "setup": row["setup"],
        "entry": entry,
        "stop": stop,
        "qty": qty,
        "risk_rupees": risk_rupees,
        "rr": row["rr"],
        "copy_text": " | ".join(parts),
    }


def _normalize_tags(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [t.strip() for t in value.split(",") if t.strip()]
    if isinstance(value, list):
        return [str(t).strip() for t in value if str(t).strip()]
    return []


def _trade_r(entry: Any, exit_: Any, stop: Any) -> float | None:
    try:
        entry_f = float(entry)
        exit_f = float(exit_)
        stop_f = float(stop)
    except (TypeError, ValueError):
        return None
    risk = entry_f - stop_f
    if risk <= 0:
        return None
    return round((exit_f - entry_f) / risk, 2)


def _trade_excursion_r(conn, symbol: Any, entry_date: str | None, exit_date: str | None,
                       entry: Any, stop: Any) -> tuple[float | None, float | None]:
    """Per-trade MFE/MAE in R over the holding window (W1.5).

    Window = [entry_date+1, exit_date] for closed trades, or [entry_date+1,
    latest price date] for open trades. MFE = (max high - entry)/risk;
    MAE = (min low - entry)/risk. Returns (None, None) when entry/stop are
    invalid or no bars exist in the window. One writer: this endpoint, reading
    raw daily_prices — no second writer vs scanner/outcomes (that owns
    candidate-level excursion; this owns trade-level)."""
    try:
        entry_f = float(entry)
        stop_f = float(stop)
    except (TypeError, ValueError):
        return None, None
    risk = entry_f - stop_f
    if risk <= 0 or not entry_date:
        return None, None
    sym = str(symbol).upper()
    if exit_date:
        rows = conn.execute(
            "SELECT high, low FROM daily_prices WHERE symbol = ? AND series = 'EQ' "
            "AND trade_date > ? AND trade_date <= ? AND high IS NOT NULL AND low IS NOT NULL "
            "ORDER BY trade_date",
            (sym, entry_date, exit_date),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT high, low FROM daily_prices WHERE symbol = ? AND series = 'EQ' "
            "AND trade_date > ? AND high IS NOT NULL AND low IS NOT NULL "
            "ORDER BY trade_date",
            (sym, entry_date),
        ).fetchall()
    if not rows:
        return None, None
    highs = [float(r["high"]) for r in rows]
    lows = [float(r["low"]) for r in rows]
    mfe_r = round((max(highs) - entry_f) / risk, 2)
    mae_r = round((min(lows) - entry_f) / risk, 2)
    return mfe_r, mae_r


def _journal_item(row) -> dict[str, Any]:
    item = dict(row)
    item["mistake_tags"] = _json_col(item.pop("mistake_tags_json"), [])
    item["exit_state"] = _json_col(item.pop("exit_state_json", None), None)
    if item.get("r_result") is None:
        item["result"] = "open"
    else:
        item["result"] = "win" if item["r_result"] > 0 else "loss"
    return item


def _journal_stats(trades: list[dict[str, Any]]) -> dict[str, Any]:
    r_values = [t["r_result"] for t in trades if t.get("r_result") is not None]
    wins = [r for r in r_values if r > 0]
    tags: dict[str, int] = {}
    for trade in trades:
        for tag in trade.get("mistake_tags", []):
            tags[tag] = tags.get(tag, 0) + 1
    top_mistake = max(tags.items(), key=lambda item: item[1])[0] if tags else None
    avg_r = _avg([float(r) for r in r_values])
    return {
        "win_pct": round(len(wins) / len(r_values) * 100.0, 1) if r_values else None,
        "avg_r": _round(avg_r),
        "expectancy_r": _round(avg_r),
        "count": len(trades),
        "top_mistake": top_mistake,
    }


def _median(values: list[float]) -> float | None:
    vals = sorted(values)
    if not vals:
        return None
    mid = len(vals) // 2
    return vals[mid] if len(vals) % 2 else (vals[mid - 1] + vals[mid]) / 2


def _symbol_mars_series(
    conn,
    symbol: str,
    bars: list[dict[str, Any]],
    benchmark: str = "NIFTYMIDSML400",
    ma_length: int = 50,
) -> list[dict[str, Any]]:
    """Per-candle MARS values for charting; latest summary still comes from pine_ports."""
    if not bars:
        return []
    dates = [b["date"] for b in bars]
    benchmark_rows = conn.execute(
        "SELECT trade_date AS date, close FROM daily_prices "
        "WHERE symbol = ? AND series = 'EQ' AND trade_date <= ? "
        "ORDER BY trade_date ASC",
        (benchmark, dates[-1]),
    ).fetchall()
    benchmark_by_date = {row["date"]: row["close"] for row in benchmark_rows}
    benchmark_dates = [row["date"] for row in benchmark_rows]
    subject_closes: list[float] = []
    series: list[dict[str, Any]] = []

    for b in bars:
        close = b.get("close")
        if close is None:
            series.append({"date": b["date"], "value": None})
            continue
        subject_closes.append(float(close))
        eligible_benchmark = [d for d in benchmark_dates if d <= b["date"]]
        if len(subject_closes) < ma_length or len(eligible_benchmark) < ma_length:
            series.append({"date": b["date"], "value": None})
            continue
        subject_window = subject_closes[-ma_length:]
        benchmark_window = [float(benchmark_by_date[d]) for d in eligible_benchmark[-ma_length:] if benchmark_by_date[d] is not None]
        if len(benchmark_window) < ma_length:
            series.append({"date": b["date"], "value": None})
            continue
        subject_ma = sum(subject_window) / ma_length
        benchmark_ma = sum(benchmark_window) / ma_length
        if subject_ma == 0 or benchmark_ma == 0:
            series.append({"date": b["date"], "value": None})
            continue
        subject_pct = (float(close) - subject_ma) / subject_ma * 100.0
        benchmark_pct = (benchmark_window[-1] - benchmark_ma) / benchmark_ma * 100.0
        series.append({"date": b["date"], "value": _round(subject_pct - benchmark_pct)})
    return series


@app.get("/api/health")
def health() -> dict[str, Any]:
    """Liveness probe — DB reachability + Fyers auth state.

    Fyers token expires ~6am IST daily; the header needs to know this without
    a full provider round-trip, so this only checks token *availability*
    (cheap), not that it's still valid against the live API.
    """
    conn = db.connect()
    try:
        conn.execute("SELECT 1")
        fyers_connected = False
        try:
            from manas_os import config
            from manas_os.providers.fyers import FyersProvider
            fyers_connected = FyersProvider.from_config(config.load_config()).is_available()
        except Exception:
            fyers_connected = False
        return {"ok": True, "fyers_connected": fyers_connected}
    finally:
        conn.close()


def _sector_metrics_rows(conn, on_or_before: str) -> tuple[str | None, list[dict[str, Any]]]:
    """The ChartsMaze-derived sector_metrics leaderboard (RS% + MA-
    participation breadth + MARS), shared by /api/regime/sectors (the REGIME
    page) and desk_market's `chartsmaze_sectors` (MARKET tab taxonomy
    section) so both read the exact same rows/shape. Resolves to the most
    recent snapshot <= `on_or_before`; (None, []) when sector_metrics has no
    data at all."""
    sec_date = _most_recent_snapshot(conn, "sector_metrics", on_or_before)
    if sec_date is None:
        return None, []
    rows = conn.execute(
        "SELECT sector_key, rs_score, breadth_50_pct, "
        "mars_score, mars_state, action_label "
        "FROM sector_metrics WHERE snapshot_date = ? "
        "ORDER BY COALESCE(rs_score, -1) DESC",
        (sec_date,),
    ).fetchall()
    rs_1w_ago = _sector_rs_1w_ago(conn, sec_date)
    sectors = [
        {
            # named `sector_key`, not `key` — a bare "key" field collides
            # with React's reserved `key` prop when the frontend spreads
            # this object onto <SectorRow {...s} />.
            "sector_key": r["sector_key"],
            "name": display_label(r["sector_key"]),
            "rs_pct": r["rs_score"],
            "breadth": r["breadth_50_pct"],
            "mars_score": r["mars_score"],
            "mars_state": r["mars_state"],
            "action": r["action_label"],
            "rs_delta_1w": (
                r["rs_score"] - rs_1w_ago[r["sector_key"]]
                if r["rs_score"] is not None and rs_1w_ago.get(r["sector_key"]) is not None
                else None
            ),
        }
        for r in rows
    ]
    return sec_date, sectors


@app.get("/api/regime/sectors")
def regime_sectors(
    date: str | None = Query(default=None, description="YYYY-MM-DD; defaults to latest"),
) -> dict[str, Any]:
    """Sectors & Themes leaderboard for the regime page.

    Sectors come from sector_metrics (RS% + MA-participation breadth); Themes
    come from industry_metrics (1D/1W/1M/3M perf + ranks + stock count). Both
    resolve to the most recent snapshot <= `date` so a missing today-row never
    reads as empty.

    Returns {available: False} when the tables have no data at all (the §7
    empty state — never a blank 200).
    """
    on_or_before = date or _today()
    conn = db.connect()
    try:
        sec_date, sectors = _sector_metrics_rows(conn, on_or_before)
        ind_date = _most_recent_snapshot(conn, "industry_metrics", on_or_before)
        if sec_date is None and ind_date is None:
            return {"available": False, "as_of": None, "sectors": [], "industries": []}

        industries = []
        if ind_date is not None:
            rows = conn.execute(
                "SELECT name, perf_1d, perf_1w, perf_1m, perf_3m, rank_1m, "
                "rank_3m, num_stocks, market_cap_cr, pct_from_52w_high "
                "FROM industry_metrics WHERE snapshot_date = ? "
                "ORDER BY COALESCE(perf_1m, -1e9) DESC",
                (ind_date,),
            ).fetchall()
            industries = [
                {
                    "name": r["name"],
                    "perf_1d": r["perf_1d"],
                    "perf_1w": r["perf_1w"],
                    "perf_1m": r["perf_1m"],
                    "perf_3m": r["perf_3m"],
                    "perf_6m": None,
                    "performance": {
                        "1d": r["perf_1d"],
                        "1w": r["perf_1w"],
                        "1m": r["perf_1m"],
                        "3m": r["perf_3m"],
                        "6m": None,
                    },
                    "rank_1m": r["rank_1m"],
                    "rank_3m": r["rank_3m"],
                    "num_stocks": r["num_stocks"],
                    "market_cap_cr": r["market_cap_cr"],
                    "pct_from_52w_high": r["pct_from_52w_high"],
                }
                for r in rows
            ]

        # `as_of` = whichever snapshot fed the data; report the more recent one.
        as_of = max(d for d in (sec_date, ind_date) if d)
        return {
            "available": True,
            "as_of": as_of,
            "sectors": sectors,
            "industries": industries,
            "timeframes": ["1d", "1w", "1m", "3m"],
            "unavailable_timeframes": {"6m": "6M is not available in industry_metrics yet."},
        }
    finally:
        conn.close()


# The market-cap ladder shown in TOP INDICES — broad indices only, largest→smallest.
# Sectors live in the Sectors & Themes panel (ChartsMaze RS); keeping them out of here
# prevents the cross-panel contradiction of the same name reading differently in two
# places (one writer per view). display name is what the UI shows.
BROAD_INDEX_LADDER: list[tuple[str, str]] = [
    ("NIFTY 50", "Nifty 50"),
    ("NIFTY NEXT 50", "Nifty Next 50"),
    ("NIFTY MIDCAP 150", "Midcap 150"),
    ("NIFTY SMALLCAP 250", "Smallcap 250"),
    ("NIFTY MICROCAP 250", "Microcap 250"),
    ("NIFTY 500", "Nifty 500"),
]

# --- Index taxonomy (name-pattern based) --------------------------------
#
# scripts/import_nse_index_history.py backfills 180+ NSE index names verbatim
# from the source feed (title-cased, e.g. "Nifty Midcap150 Quality 50"), with
# no category column. The MARKET tab needs to separate market-cap ladders,
# single-industry sector indices, and strategy/factor/fixed-income indices so
# the grid/treemap don't drown in ~120 thematic names. classify_index() is a
# documented, best-effort regex classifier over the (normalized) index name —
# not a lookup against an authoritative NSE taxonomy table (none is ingested).
#
# Precedence: BROAD (exact cap-weighted ladder name, no extra qualifier
# words) -> THEMATIC_STRATEGY if a factor/strategy/fixed-income marker word
# is present (checked before SECTORAL so e.g. "Nifty MidSmall Healthcare" or
# "Nifty500 Healthcare" land in thematic, not sectoral) -> SECTORAL if a
# single-industry keyword is present -> THEMATIC_STRATEGY catch-all.
_BROAD_NAME_RE = re.compile(
    r"^NIFTY\s?(50|100|200|500|NEXT\s?50|MIDCAP\s?\d*|SMALLCAP\s?\d*|"
    r"MICROCAP\s?\d*|LARGEMIDCAP\s?\d*|MIDSMALLCAP\s?\d*)$"
)

# Multi-word phrases are matched as plain substrings (specific enough not to
# false-positive); single common words use \b so e.g. "IT" doesn't match
# inside an unrelated longer word.
_SECTORAL_WORD_KEYWORDS = (
    "BANK", "IT", "AUTO", "METAL", "FMCG", "ENERGY", "REALTY", "PSU", "MEDIA",
    "CPSE", "POWER", "CONSUMER", "INSURANCE", "NBFC",
)
_SECTORAL_PHRASE_KEYWORDS = (
    "FINANCIAL SERVICES", "HEALTHCARE", "INFRASTRUCTURE", "OIL & GAS",
    "OIL AND GAS", "PRIVATE BANK", "PSU BANK", "COMMODITIES", "DEFENCE",
    "CEMENT", "CHEMICALS", "CAPITAL GOODS", "CONSTRUCTION",
    "TELECOMMUNICATIONS", "SERVICES SECTOR", "HOUSING FINANCE", "MOBILITY",
)
# Strategy/factor/ESG/fixed-income marker words — presence of any of these
# overrides a sectoral keyword match (a "MidSmall Healthcare" index is a
# strategy blend, not a plain sector index).
_THEMATIC_MARKER_KEYWORDS = (
    "QUALITY", "MOMENTUM", "VALUE", "ALPHA", "LOW VOLATILITY", "EQUAL WEIGHT",
    "ESG", "SHARIAH", "DIVIDEND", "G-SEC", "GSEC", "BOND", "ARBITRAGE",
    "FUTURES", "INVERSE", "LEVERAGE", "USD", "MULTICAP", "MULTIFACTOR",
    "SELECT", "LIQUID", "MIDSMALL", "FLEXICAP", "GROWTH SECTORS",
    "HIGH BETA", "CORPORATE GROUP", "IPO", "SME", "RATE INDEX", "TR INDEX",
    "PR 1X", "PR 2X", "TOTAL MARKET", "MAATR", "EMERGE", "WAVES", "FPI",
    "TOP 10", "TOP 15", "TOP 20",
)

_VIX_SYMBOLS = {"INDIAVIX", "INDIA VIX"}


def _normalize_index_name(symbol: str) -> str:
    return re.sub(r"\s+", " ", symbol.strip().upper())


def classify_index(symbol: str) -> str:
    """BROAD / SECTORAL / THEMATIC_STRATEGY — see module-level comment above
    BROAD_INDEX_LADDER for the precedence rules."""
    name = _normalize_index_name(symbol)
    if _BROAD_NAME_RE.match(name):
        return "BROAD"
    if any(re.search(rf"\b{re.escape(m)}\b", name) for m in _THEMATIC_MARKER_KEYWORDS):
        return "THEMATIC_STRATEGY"
    if any(re.search(rf"\b{re.escape(k)}\b", name) for k in _SECTORAL_WORD_KEYWORDS):
        return "SECTORAL"
    if any(k in name for k in _SECTORAL_PHRASE_KEYWORDS):
        return "SECTORAL"
    return "THEMATIC_STRATEGY"


_VIX_BANDS = (
    (12.0, "low"),
    (20.0, "normal"),
    (25.0, "elevated"),
)


def _vix_band(value: float) -> str:
    """AD9 tiers: <12 low / 12-20 normal / 20-25 elevated / >25 danger."""
    for ceiling, band in _VIX_BANDS:
        if value < ceiling:
            return band
    return "danger"


def _extract_vix(index_rows: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Pop the India VIX row out of `index_rows` (it isn't an index for the
    grid/treemap) and return it as {value, band}, plus the remaining rows."""
    vix_row = None
    rest = []
    for row in index_rows:
        if _normalize_index_name(row["symbol"]) in _VIX_SYMBOLS:
            vix_row = row
        else:
            rest.append(row)
    if vix_row is None or vix_row["close"] is None:
        return None, rest
    value = float(vix_row["close"])
    return {"value": _round(value), "band": _vix_band(value)}, rest


@app.get("/api/regime/indices")
def regime_indices(
    date: str | None = Query(default=None, description="YYYY-MM-DD; defaults to latest"),
) -> dict[str, Any]:
    """Broad market-cap index performance with 1D/1W/1M/3M/6M returns."""
    on_or_before = date or _today()
    conn = db.connect()
    try:
        as_of, rows = _index_returns(conn, on_or_before)
        if as_of is None:
            return {"available": False, "as_of": None, "indices": []}
        by_symbol = {r["symbol"]: r for r in rows}
        ladder = []
        for symbol, label in BROAD_INDEX_LADDER:
            row = by_symbol.get(symbol)
            if row is None:
                continue
            row = {**row, "name": label}
            ladder.append(row)
        return {
            "available": True,
            "as_of": as_of,
            "timeframes": ["1d", "1w", "1m", "3m", "6m"],
            "indices": ladder,
        }
    finally:
        conn.close()


@app.get("/api/regime/summary")
def regime_summary(
    date: str | None = Query(default=None, description="YYYY-MM-DD; defaults to latest"),
) -> dict[str, Any]:
    """Top-strip regime snapshot for one date."""
    on_or_before = date or _today()
    conn = db.connect()
    try:
        row = conn.execute(
            "SELECT * FROM regime_snapshots WHERE snapshot_date <= ? "
            "ORDER BY snapshot_date DESC LIMIT 1",
            (on_or_before,),
        ).fetchone()
        if row is None:
            return {"available": False, "as_of": None}

        payload = dict(row)
        payload["available"] = True
        payload["as_of"] = payload["snapshot_date"]
        payload["preferred_setups"] = _json_col(payload.pop("preferred_setups_json"), [])
        payload["avoid_setups"] = _json_col(payload.pop("avoid_setups_json"), [])
        payload["quadrant"] = _json_col(payload.pop("quadrant_json"), {})
        # Beginner-safety: the latest snapshot can be days old (no recent
        # bhavcopy). A snapshot that was internally fresh on its own date
        # (data_stale=0) must still read as STALE when it's the "latest" shown
        # today — never present an old regime as a live one.
        #
        # JOB 3: this must be trading-calendar-aware, not raw calendar days —
        # a Saturday showing Friday's snapshot is current, not stale. `_lag`
        # counts actual NSE trading days between the snapshot and the most
        # recent trading day on/before today (weekends/holidays excluded), so
        # it only fires when a real session was actually missed. The prior
        # internal data_stale hard-degrade (set in snapshot.py at write time)
        # is preserved via `or` below, per the "keep existing logic OR'd in"
        # rule — either signal can force stale, neither alone is dropped.
        latest_trading_day = market_calendar.last_trading_day(_date.today())
        try:
            _lag = market_calendar.trading_days_between(
                _date.fromisoformat(payload["snapshot_date"]), latest_trading_day
            )
        except (ValueError, TypeError):
            _lag = 0
        payload["days_behind"] = _lag
        # One-writer: the Breadth/Swing chip and the posture line must both
        # read breadth from THIS payload, so expose the number the snapshot
        # itself was built from (breadth_daily row on/before snapshot_date).
        _b = conn.execute(
            "SELECT pct_above_20dma FROM breadth_daily WHERE trade_date <= ? "
            "ORDER BY trade_date DESC LIMIT 1",
            (payload["snapshot_date"],),
        ).fetchone()
        payload["breadth_20dma_pct"] = _b["pct_above_20dma"] if _b else None
        # BUG FIX (JOB 1): when read-time staleness (above) newly forces
        # data_stale=1 on a snapshot that was written as fresh (data_stale=0
        # at write time), the persisted explanation_text still says things
        # like "breadth is green, 2 of 2 checks favourable" as a live claim —
        # that directly contradicts the STALE posture badge this same
        # response drives. Regenerate the explanation from the honest
        # stale-branch wording (snapshot.stale_read_explanation) whenever
        # this read-time override is what makes it stale, so the banner and
        # the READ line can never disagree.
        if _lag > 0:
            was_stale_at_write = bool(payload.get("data_stale"))
            payload["data_stale"] = 1
            if not was_stale_at_write:
                known_pillars = _known_pillars_from_technical_detail(payload.get("technical_detail"))
                payload["explanation_text"] = regime_snapshot.stale_read_explanation(
                    payload.get("mbi_day_color"),
                    payload.get("pillars_passed"),
                    known_pillars,
                    _lag,
                )
        # Link open risk/cap for visual redesign governor tape (from portfolio heat)
        try:
            heat = portfolio_heat()
            payload["open_risk_pct"] = heat.get("open_risk_pct")
            payload["cap_pct"] = heat.get("cap_pct")
        except Exception:
            payload["open_risk_pct"] = None
            payload["cap_pct"] = None
        return payload
    finally:
        conn.close()


@app.get("/api/regime/history")
def regime_history(
    days: int = Query(default=90, ge=1, le=500, description="Number of snapshots to return"),
    date: str | None = Query(default=None, description="YYYY-MM-DD; defaults to latest"),
) -> dict[str, Any]:
    """Recent regime history for the XP line and posture ribbon."""
    on_or_before = date or _today()
    conn = db.connect()
    try:
        rows = conn.execute(
            "SELECT snapshot_date, xp_value, market_mode, mbi_day_color, warning_day, r4p5, "
            "r10, r20, r50 "
            "FROM ("
            "  SELECT snapshot_date, xp_value, market_mode, mbi_day_color, warning_day, r4p5, "
            "  r10, r20, r50 "
            "  FROM regime_snapshots WHERE snapshot_date <= ? "
            "  ORDER BY snapshot_date DESC LIMIT ?"
            ") ORDER BY snapshot_date ASC",
            (on_or_before, days),
        ).fetchall()
        if not rows:
            return {"available": False, "rows": []}
        result_rows = [dict(r) for r in rows]
        # Link backend data for visual overlays (regime ribbon with outcomes per plan/brainstorm #5)
        # Attach journal trades for these dates so frontend can plot entries/exits/R on the XP/posture ribbon.
        dates = [r["snapshot_date"] for r in result_rows]
        if dates:
            trades = conn.execute(
                "SELECT trade_date, symbol, r_result, entry, stop, exit FROM journal_trades "
                "WHERE trade_date IN (%s) ORDER BY trade_date" % ",".join("?" for _ in dates),
                dates,
            ).fetchall()
            by_date = {}
            for t in trades:
                d = t["trade_date"]
                if d not in by_date:
                    by_date[d] = []
                by_date[d].append({
                    "symbol": t["symbol"],
                    "r": t["r_result"],
                    "entry": t["entry"],
                    "stop": t["stop"],
                    "exit": t["exit"],
                })
            for r in result_rows:
                r["journal_outcomes"] = by_date.get(r["snapshot_date"], [])
        return {"available": True, "rows": result_rows}
    finally:
        conn.close()


@app.get("/api/regime/breadth-history")
def regime_breadth_history(
    days: int = Query(default=20, ge=1, le=500, description="Number of breadth rows to return"),
    date: str | None = Query(default=None, description="YYYY-MM-DD; defaults to latest"),
) -> dict[str, Any]:
    """Recent breadth trend for the Top Decision Strip sparkline."""
    on_or_before = date or _today()
    conn = db.connect()
    try:
        rows = conn.execute(
            "SELECT trade_date, pct_above_10dma, pct_above_20dma, pct_above_40dma, pct_above_50dma, advances, declines "
            "FROM ("
            "  SELECT trade_date, pct_above_10dma, pct_above_20dma, pct_above_40dma, pct_above_50dma, advances, declines "
            "  FROM breadth_daily WHERE trade_date <= ? "
            "  ORDER BY trade_date DESC LIMIT ?"
            ") ORDER BY trade_date ASC",
            (on_or_before, days),
        ).fetchall()
        if not rows:
            return {"available": False, "rows": []}
        return {"available": True, "rows": [dict(r) for r in rows]}
    finally:
        conn.close()


@app.get("/api/regime/sectors/{sector_key}/stocks")
def regime_sector_stocks(
    sector_key: str,
    date: str | None = Query(default=None, description="YYYY-MM-DD; defaults to latest"),
) -> dict[str, Any]:
    """Stock RS drill-down for a canonical sector key."""
    key = sector_key.strip().upper()
    on_or_before = date or _today()
    run_date = _most_recent_stock_rs_date(on_or_before)
    if run_date is None:
        return _unavailable_stock_payload(sector_key=key)

    industries = set(industries_for_sector(key))
    if not industries:
        return _unavailable_stock_payload(sector_key=key)

    stocks = _stock_rows_for_industries(run_date, industries)
    if not stocks:
        return _unavailable_stock_payload(sector_key=key)
    return {"available": True, "sector_key": key, "stocks": stocks, "count": len(stocks)}


@app.get("/api/regime/industries/{industry_name:path}/stocks")
def regime_industry_stocks(
    industry_name: str,
    date: str | None = Query(default=None, description="YYYY-MM-DD; defaults to latest"),
) -> dict[str, Any]:
    """Stock RS drill-down for one ChartsMaze Basic Industry label."""
    industry = industry_name.strip()
    on_or_before = date or _today()
    run_date = _most_recent_stock_rs_date(on_or_before)
    if run_date is None or industry not in INDUSTRY_TO_SECTOR:
        return _unavailable_stock_payload(industry=industry)

    stocks = _stock_rows_for_industries(run_date, {industry})
    if not stocks:
        return _unavailable_stock_payload(industry=industry)
    return {"available": True, "industry": industry, "stocks": stocks, "count": len(stocks)}


def _ema_stack_state(close: float | None, ema10: float | None, ema21: float | None, ema50: float | None) -> str | None:
    """ChartsMaze-style EMA-stack read: Lead when price is fully stacked above
    a rising-order EMA10>EMA21>EMA50, Lag when fully stacked below, else
    Mixed. None when any input is missing (features_daily has no row yet)."""
    vals = (close, ema10, ema21, ema50)
    if any(v is None for v in vals):
        return None
    if close > ema10 > ema21 > ema50:
        return "lead"
    if close < ema10 < ema21 < ema50:
        return "lag"
    return "mixed"


def _stock_market_rows_for_industries(
    conn, run_date: str, industries: set[str], on_or_before: str
) -> list[dict[str, Any]]:
    """Sector drill-down rows for the MARKET tab: ChartsMaze RS (via
    `_stock_rows_for_industries`, already sorted RS desc) enriched with
    close/1D%/EMA-stack/delivery-flag from daily_prices + features_daily on
    the latest priced date on/before `on_or_before`. Symbols with no priced
    row simply carry nulls for the extra columns — RS ordering is preserved."""
    base = _stock_rows_for_industries(run_date, industries)
    if not base:
        return []
    stock_date = _latest_price_date(conn, on_or_before)
    price_by_symbol: dict[str, Any] = {}
    feat_by_symbol: dict[str, Any] = {}
    if stock_date is not None:
        symbols = [r["ticker"] for r in base]
        placeholders = ",".join("?" for _ in symbols)
        price_rows = conn.execute(
            f"SELECT symbol, close, prev_close, delivery_pct FROM daily_prices "
            f"WHERE series = 'EQ' AND trade_date = ? AND symbol IN ({placeholders})",
            (stock_date, *symbols),
        ).fetchall()
        price_by_symbol = {r["symbol"]: dict(r) for r in price_rows}
        feat_rows = conn.execute(
            f"SELECT symbol, feature_json FROM features_daily "
            f"WHERE trade_date = ? AND symbol IN ({placeholders})",
            (stock_date, *symbols),
        ).fetchall()
        feat_by_symbol = {r["symbol"]: _json_col(r["feature_json"], {}) for r in feat_rows}

    out = []
    for item in base:
        sym = item["ticker"]
        price = price_by_symbol.get(sym)
        close = price["close"] if price else None
        prev_close = price["prev_close"] if price else None
        pct_1d = round((close - prev_close) / prev_close * 100.0, 2) if close is not None and prev_close else None
        delivery_pct = price["delivery_pct"] if price else None
        feat = feat_by_symbol.get(sym, {})
        out.append({
            "symbol": sym,
            "rs": item["rs"],
            "close": close,
            "pct_1d": pct_1d,
            "ema_state": _ema_stack_state(close, feat.get("ema10"), feat.get("ema21"), feat.get("ema50")),
            "delivery_pct": delivery_pct,
            "delivery_flag": delivery_pct is not None and delivery_pct >= 50,
        })
    return out


@app.get("/api/desk/market/sector-stocks")
def desk_market_sector_stocks(
    sector: str = Query(..., description="Raw NSE sector index name (e.g. 'NIFTY BANK') or canonical sector key"),
    date: str | None = Query(default=None, description="YYYY-MM-DD; defaults to latest"),
) -> dict[str, Any]:
    """MARKET tab sector/treemap-row drill-down: member stocks with ticker,
    RS, close, 1D%, EMA-stack state (lead/mixed/lag), and a delivery-heavy
    flag — reuses the same ChartsMaze-industry membership machinery as
    /api/regime/sectors/{sector_key}/stocks, joined against daily_prices +
    features_daily for the extra columns. Sorted RS desc. Honest empty state
    (available=False) when RS history, sector mapping, or priced stocks are
    missing for the date."""
    on_or_before = date or _today()
    key = canonical_sector_key(sector, "index")
    run_date = _most_recent_stock_rs_date(on_or_before)
    if run_date is None:
        return _unavailable_stock_payload(sector=sector, sector_key=key)
    industries = set(industries_for_sector(key))
    if not industries:
        return _unavailable_stock_payload(sector=sector, sector_key=key)
    conn = db.connect()
    try:
        stocks = _stock_market_rows_for_industries(conn, run_date, industries, on_or_before)
    finally:
        conn.close()
    if not stocks:
        return _unavailable_stock_payload(sector=sector, sector_key=key)
    return {"available": True, "sector": sector, "sector_key": key, "stocks": stocks, "count": len(stocks)}


@app.get("/api/symbol/{symbol}/timing")
def symbol_timing(
    symbol: str,
    date: str | None = Query(default=None, description="YYYY-MM-DD; defaults to latest"),
) -> dict[str, Any]:
    """Entry-timing metrics for one symbol from daily_prices only."""
    on_or_before = date or _today()
    conn = db.connect()
    try:
        return _symbol_timing(conn, symbol, on_or_before)
    finally:
        conn.close()


@app.get("/api/symbol/{symbol}/ohlc")
def symbol_ohlc(
    symbol: str,
    tf: str = Query(default="1D", description="Only 1D is supported today"),
    n: int = Query(default=250, ge=20, le=500, description="Number of candles"),
    date: str | None = Query(default=None, description="YYYY-MM-DD; defaults to latest"),
) -> dict[str, Any]:
    """Daily candles with EMA overlays and deterministic price-action signals."""
    if tf != "1D":
        raise HTTPException(400, "Only tf=1D is supported.")
    sym = symbol.upper()
    on_or_before = date or _today()
    conn = db.connect()
    try:
        bars = _load_symbol_bars(conn, sym, on_or_before, n)
        if not bars:
            return {"available": False, "symbol": sym, "as_of": None, "candles": []}

        closes = [None if b.get("close") is None else float(b["close"]) for b in bars]
        ema10 = _ema(closes, 10)
        ema15 = _ema(closes, 15)
        ema21 = _ema(closes, 21)
        ema50 = _ema(closes, 50)
        candles = []
        for idx, b in enumerate(bars):
            candles.append({
                "date": b["date"],
                "open": _round(b.get("open")),
                "high": _round(b.get("high")),
                "low": _round(b.get("low")),
                "close": _round(b.get("close")),
                "volume": b.get("volume"),
                "delivery_pct": _round(b.get("delivery_pct")),
                "ema10": _round(ema10[idx]),
                "ema15": _round(ema15[idx]),
                "ema21": _round(ema21[idx]),
                "ema50": _round(ema50[idx]),
            })
        state = price_action.signals_for_symbol(conn, sym, bars[-1]["date"], max_bars=n)
        exit_payload = eod_detectors.exit_state(bars)
        mars = pine_ports.symbol_mars(conn, sym, bars[-1]["date"])
        mars["series"] = _symbol_mars_series(
            conn,
            sym,
            bars,
            benchmark=mars.get("benchmark") or "NIFTYMIDSML400",
            ma_length=int(mars.get("ma_length") or 50),
        )
        pine = {"moving_average_rs": mars}
        _ensure_avwap_anchors(conn)
        prev = conn.execute(
            "SELECT anchor_date, anchor_type, reason FROM avwap_anchors "
            "WHERE symbol = ? AND as_of < ? ORDER BY as_of DESC LIMIT 1",
            (sym, bars[-1]["date"]),
        ).fetchone()
        prev_anchor = dict(prev) if prev else None
        avwap = eod_detectors.avwap_auto_anchor(bars, state["recent_signals"], prev_anchor)
        ttm = eod_detectors.ttm_squeeze_momentum(bars)
        return {
            "available": True,
            "symbol": sym,
            "as_of": bars[-1]["date"],
            "candles": candles,
            "stage": state["stage"],
            "trail": state["trail"],
            "exit_state": exit_payload,
            "signals": state["recent_signals"],
            "pine_ports": pine,
            "avwap": avwap,
            "rs_line": mars["series"],
            "rs_phase": mars.get("state"),
            "ttm_squeeze": ttm,
        }
    finally:
        conn.close()


@app.get("/api/watchlist")
def watchlist(date: str | None = Query(default=None, description="YYYY-MM-DD; defaults to latest")) -> dict[str, Any]:
    """Watchlist rows fused with current timing metrics."""
    on_or_before = date or _today()
    conn = db.connect()
    try:
        _ensure_watchlist_exit_columns(conn)
        rows = conn.execute(
            "SELECT symbol, note, alerts_enabled, added_at FROM watchlist ORDER BY added_at DESC, symbol"
        ).fetchall()
        rs_map = _stock_rs_map(on_or_before)
        items = []
        for row in rows:
            timing = _symbol_timing(conn, row["symbol"], on_or_before)
            exit_payload = _symbol_exit_state(conn, row["symbol"], on_or_before)
            rs_info = rs_map.get(row["symbol"], {})
            coach = None
            open_trade = conn.execute(
                "SELECT trade_id, symbol, setup, entry, stop, first_exit_flag_date FROM journal_trades "
                "WHERE symbol = ? AND exit IS NULL ORDER BY trade_date DESC, trade_id DESC LIMIT 1",
                (row["symbol"],),
            ).fetchone()
            if open_trade:
                coach = _coach_for_open_trade(conn, open_trade, on_or_before)
            conn.execute(
                "UPDATE watchlist SET exit_state_json = ? WHERE symbol = ?",
                (json.dumps(exit_payload), row["symbol"]),
            )
            items.append({
                "symbol": row["symbol"],
                "note": row["note"],
                "alerts_enabled": bool(row["alerts_enabled"]),
                "added_at": row["added_at"],
                "adr": timing.get("adr"),
                "rs": rs_info.get("rs"),
                "rs_as_of": rs_info.get("rs_as_of"),
                "timing": timing,
                "exit_state": exit_payload,
                "coach": coach,
            })
        price_date = _latest_price_date(conn, on_or_before)
        conn.commit()
        return {"available": True, "as_of": price_date, "items": items}
    finally:
        conn.close()


@app.get("/api/positions/{trade_id}/coach")
def position_coach(trade_id: int, date: str | None = Query(default=None)) -> dict[str, Any]:
    """Presentation-only coach for one open journal position."""
    as_of = date or _today()
    conn = db.connect()
    try:
        _ensure_journal_table(conn)
        trade = conn.execute(
            "SELECT trade_id, trade_date, symbol, setup, entry, stop, first_exit_flag_date "
            "FROM journal_trades WHERE trade_id = ? AND exit IS NULL",
            (trade_id,),
        ).fetchone()
        if not trade:
            return {"available": False, "reason": "no open position with that id"}
        coach = _coach_for_open_trade(conn, trade, as_of)
        if coach is None:
            return {"available": False, "reason": "coach unavailable for that position"}
        conn.commit()
        return coach
    finally:
        conn.close()


@app.post("/api/watchlist")
def watchlist_add(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """Add or update one watchlist symbol."""
    symbol = str(payload.get("symbol") or "").strip().upper()
    if not symbol:
        raise HTTPException(400, "symbol is required")
    note = payload.get("note")
    conn = db.connect()
    try:
        _ensure_watchlist_exit_columns(conn)
        conn.execute(
            "INSERT INTO watchlist (symbol, note, alerts_enabled) VALUES (?, ?, 1) "
            "ON CONFLICT(symbol) DO UPDATE SET note=excluded.note",
            (symbol, note),
        )
        conn.commit()
        return {"ok": True, "symbol": symbol}
    finally:
        conn.close()


@app.delete("/api/watchlist/{symbol}")
def watchlist_delete(symbol: str) -> dict[str, Any]:
    """Drop one symbol from the local watchlist."""
    sym = symbol.strip().upper()
    conn = db.connect()
    try:
        cur = conn.execute("DELETE FROM watchlist WHERE symbol = ?", (sym,))
        conn.commit()
        return {"ok": True, "symbol": sym, "deleted": cur.rowcount}
    finally:
        conn.close()


@app.get("/api/setups")
def setups(
    date: str | None = Query(default=None, description="YYYY-MM-DD; defaults to latest"),
    min_rs: float | None = Query(default=None, description="Minimum ChartsMaze RS"),
    setup: str | None = Query(default=None, description="Setup name substring"),
    sector: str | None = Query(default=None, description="Canonical sector key"),
    grade: str | None = Query(default=None, description="Minimum grade A+, A, B, or C"),
    limit: int = Query(default=80, ge=1, le=300, description="Maximum candidates"),
    scan_limit: int = Query(default=200, ge=50, le=2000, description="Symbols to inspect before ranking"),
) -> dict[str, Any]:
    """Deterministic setup candidates from the persisted P2 scanner."""
    on_or_before = date or _today()
    conn = db.connect()
    try:
        persisted = scanner_candidates.load_persisted_candidates(
            conn,
            on_or_before,
            min_rs=min_rs,
            setup=setup,
            sector=sector,
            min_grade=grade,
            limit=limit,
        )
        source = "scan_candidates"
        payload = persisted
        if not persisted["available"]:
            # Fresh DB/dev fallback only; the normal P2 path is run-eod ->
            # scan_candidates. The fallback is not persisted, so it cannot become
            # a second metric writer.
            live = scanner_candidates.scan_candidates(conn, on_or_before, scan_limit=scan_limit)
            source = "live_fallback"
            payload = {
                **live,
                "candidates": scanner_candidates.filter_candidates(
                    live.get("candidates", []),
                    min_rs=min_rs,
                    setup=setup,
                    sector=sector,
                    min_grade=grade,
                    limit=limit,
                ),
            }
        if not payload["available"]:
            return {"available": False, "as_of": None, "posture_mode": None, "source": source, "candidates": []}
        mode = None
        row = conn.execute(
            "SELECT market_mode FROM regime_snapshots WHERE snapshot_date <= ? "
            "ORDER BY snapshot_date DESC LIMIT 1",
            (on_or_before,),
        ).fetchone()
        if row:
            mode = row["market_mode"]
        # Regime governor is LAW (plan T1.3): the feed never shows more cards
        # than the posture allows, regardless of the caller's limit param.
        gv = governor(mode or "SELECTIVE")
        shown = payload["candidates"][: gv["max_cards"]]
        # Focus Center (T3.7a fix): the EP/IPO-base lens must see catalyst
        # names even when they rank below the governor's display cap — that's
        # the whole point of the focus view. The "All" list still respects the
        # cap; the focus list pulls EP/IPO-base from the FULL ranked list.
        # Without this the lens filtered an already-truncated list and showed
        # "0 setups" whenever the top-cap cards were pullbacks (STATE_OF_TOOL 3.3).
        focus = [c for c in payload["candidates"]
                 if c.get("setup_type") in {"ep", "ipo_base"}][:6]
        return {
            "available": True,
            "as_of": payload["as_of"],
            "posture_mode": mode,
            "source": source,
            "governor": gv,
            "total_passed": len(payload["candidates"]),
            "candidates": shown,
            "focus_candidates": focus,
        }
    finally:
        conn.close()


@app.post("/api/setups/decision")
def setup_decision(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    scan_date = str(payload.get("scan_date") or "").strip()
    symbol = str(payload.get("symbol") or "").strip().upper()
    decision = str(payload.get("decision") or "").strip().lower()
    if not scan_date or not symbol:
        raise HTTPException(400, "scan_date and symbol are required")
    if decision not in {"taken", "skipped"}:
        raise HTTPException(400, "decision must be taken or skipped")
    conn = db.connect()
    try:
        scanner_candidates.ensure_schema(conn)
        scanner_outcomes.ensure_setup_decisions_schema(conn)
        _ensure_journal_table(conn)
        row = conn.execute(
            "SELECT * FROM scan_candidates WHERE scan_date = ? AND symbol = ? "
            "ORDER BY rank IS NULL, rank, setup LIMIT 1",
            (scan_date, symbol),
        ).fetchone()
        if not row:
            raise HTTPException(404, "setup candidate not found")
        candidate = dict(row)
        snapshot_json = json.dumps(candidate, sort_keys=True)
        entry_price = payload.get("entry_price")
        qty = payload.get("qty")
        conn.execute(
            "INSERT INTO setup_decisions "
            "(scan_date, symbol, decision, skip_reason, entry_price, qty, snapshot_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(scan_date, symbol) DO UPDATE SET "
            "decision=excluded.decision, skip_reason=excluded.skip_reason, "
            "entry_price=excluded.entry_price, qty=excluded.qty, "
            "snapshot_json=excluded.snapshot_json, created_at=datetime('now')",
            (
                scan_date,
                symbol,
                decision,
                payload.get("skip_reason"),
                entry_price,
                qty,
                snapshot_json,
            ),
        )
        trade_id = None
        if decision == "taken":
            cur = conn.execute(
                "INSERT INTO journal_trades "
                "(trade_date, symbol, setup, entry, stop, exit, notes, mistake_tags_json) "
                "VALUES (?, ?, ?, ?, ?, NULL, 'auto-captured from setups', '[]')",
                (
                    scan_date,
                    symbol,
                    candidate.get("setup"),
                    entry_price if entry_price is not None else candidate.get("entry"),
                    candidate.get("stop"),
                ),
            )
            trade_id = cur.lastrowid
        conn.commit()
        out: dict[str, Any] = {"ok": True, "decision": decision}
        if trade_id is not None:
            out["trade_id"] = trade_id
        return out
    finally:
        conn.close()


@app.get("/api/setups/refusals")
def setups_refusals(
    date: str | None = Query(default=None, description="YYYY-MM-DD; defaults to latest"),
    limit: int = Query(default=25, ge=1, le=200),
) -> dict[str, Any]:
    """The refusal ledger (plan T1.5) — the feed that says NO, made visible.

    Feeds the Setups funnel visual and the journal loop's filtered-out cohort.
    """
    on_or_before = date or _today()
    conn = db.connect()
    try:
        scanner_candidates.ensure_refusals_schema(conn)
        row = conn.execute(
            "SELECT MAX(scan_date) AS d FROM refusals WHERE scan_date <= ?",
            (on_or_before,),
        ).fetchone()
        if not row or not row["d"]:
            return {"available": False, "as_of": None, "refusals": [], "by_gate": {}}
        scan_date = row["d"]
        rows = conn.execute(
            "SELECT symbol, setup_family, failed_gate, reason FROM refusals "
            "WHERE scan_date = ? ORDER BY failed_gate, symbol LIMIT ?",
            (scan_date, limit),
        ).fetchall()
        counts = conn.execute(
            "SELECT failed_gate, COUNT(*) AS n FROM refusals WHERE scan_date = ? "
            "GROUP BY failed_gate ORDER BY n DESC",
            (scan_date,),
        ).fetchall()
        return {
            "available": True,
            "as_of": scan_date,
            "refusals": [dict(r) for r in rows],
            "by_gate": {r["failed_gate"]: r["n"] for r in counts},
        }
    finally:
        conn.close()


@app.get("/api/setups/near-misses")
def setups_near_misses(
    date: str | None = Query(default=None, description="YYYY-MM-DD; defaults to latest"),
    limit: int = Query(default=12, ge=1, le=50),
) -> dict[str, Any]:
    """Visual-ready near-miss lane: refused symbols plus distance-to-pass and chart payload."""
    on_or_before = date or _today()
    conn = db.connect()
    try:
        scan_date, items = _near_miss_items(conn, on_or_before, limit)
        conn.commit()
        return {"available": bool(scan_date), "as_of": scan_date, "near_misses": items}
    finally:
        conn.close()


@app.post("/api/watchlist/candidates")
def watchlist_candidate(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    symbol = str(payload.get("symbol") or "").strip().upper()
    candidate_date = str(payload.get("candidate_date") or payload.get("date") or "").strip()
    if not symbol or not candidate_date:
        raise HTTPException(400, "candidate_date and symbol are required")
    source = str(payload.get("source") or "near_miss").strip() or "near_miss"
    status = str(payload.get("status") or "tracking").strip().lower()
    if status not in {"tracking", "ignored", "override"}:
        raise HTTPException(400, "status must be tracking, ignored, or override")
    snapshot = payload.get("snapshot") or payload.get("snapshot_json")
    conn = db.connect()
    try:
        _ensure_organic_watchlist_schema(conn)
        conn.execute(
            "INSERT INTO watchlist_candidates "
            "(candidate_date, symbol, source, status, reason, failed_gate, snapshot_json, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now')) "
            "ON CONFLICT(candidate_date, symbol, source) DO UPDATE SET "
            "status=excluded.status, reason=excluded.reason, failed_gate=excluded.failed_gate, "
            "snapshot_json=excluded.snapshot_json, updated_at=datetime('now')",
            (
                candidate_date,
                symbol,
                source,
                status,
                payload.get("reason"),
                payload.get("failed_gate"),
                json.dumps(snapshot, sort_keys=True) if not isinstance(snapshot, str) else snapshot,
            ),
        )
        outcome = _upsert_candidate_outcome(conn, candidate_date, symbol, source)
        conn.commit()
        return {"ok": True, "candidate_date": candidate_date, "symbol": symbol, "source": source, "status": status, "outcome": outcome}
    finally:
        conn.close()


@app.post("/api/setups/override")
def setup_override(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    symbol = str(payload.get("symbol") or "").strip().upper()
    override_date = str(payload.get("scan_date") or payload.get("candidate_date") or payload.get("date") or "").strip()
    reason = str(payload.get("reason") or "").strip()
    if not symbol or not override_date:
        raise HTTPException(400, "scan_date/candidate_date and symbol are required")
    if not reason:
        raise HTTPException(400, "override reason is required")
    snapshot = payload.get("snapshot") or {}
    snapshot_json = json.dumps(snapshot, sort_keys=True) if not isinstance(snapshot, str) else snapshot
    conn = db.connect()
    try:
        _ensure_organic_watchlist_schema(conn)
        conn.execute(
            "INSERT INTO gate_overrides "
            "(override_date, symbol, reason, half_size, failed_gate, snapshot_json) "
            "VALUES (?, ?, ?, 1, ?, ?) "
            "ON CONFLICT(override_date, symbol) DO UPDATE SET "
            "reason=excluded.reason, half_size=1, failed_gate=excluded.failed_gate, "
            "snapshot_json=excluded.snapshot_json, created_at=datetime('now')",
            (override_date, symbol, reason, payload.get("failed_gate"), snapshot_json),
        )
        conn.execute(
            "INSERT INTO watchlist_candidates "
            "(candidate_date, symbol, source, status, reason, failed_gate, snapshot_json, updated_at) "
            "VALUES (?, ?, 'override', 'override', ?, ?, ?, datetime('now')) "
            "ON CONFLICT(candidate_date, symbol, source) DO UPDATE SET "
            "status='override', reason=excluded.reason, failed_gate=excluded.failed_gate, "
            "snapshot_json=excluded.snapshot_json, updated_at=datetime('now')",
            (override_date, symbol, reason, payload.get("failed_gate"), snapshot_json),
        )
        outcome = _upsert_candidate_outcome(conn, override_date, symbol, "override")
        conn.commit()
        return {"ok": True, "symbol": symbol, "override_date": override_date, "half_size": True, "outcome": outcome}
    finally:
        conn.close()


@app.get("/api/watchlist/organic")
def watchlist_organic(date: str | None = Query(default=None)) -> dict[str, Any]:
    """Visual-ready watchlist lanes: active positions, tracked near-misses, overrides, manual watchlist."""
    on_or_before = date or _today()
    conn = db.connect()
    try:
        _ensure_organic_watchlist_schema(conn)
        _ensure_journal_table(conn)
        manual = watchlist(on_or_before).get("items", [])
        rs_map = _stock_rs_map(on_or_before)
        active_rows = conn.execute(
            "SELECT trade_id, trade_date, symbol, setup, entry, stop, r_result FROM journal_trades "
            "WHERE exit IS NULL ORDER BY trade_date DESC, trade_id DESC"
        ).fetchall()
        active = []
        for row in active_rows:
            item = dict(row)
            rs_info = rs_map.get(row["symbol"], {})
            timing = _symbol_timing(conn, row["symbol"], on_or_before)
            exit_payload = _symbol_exit_state(conn, row["symbol"], on_or_before)
            item["coach"] = _coach_for_open_trade(conn, row, on_or_before)
            item["open_r"] = (item.get("coach") or {}).get("r")
            item["rs"] = rs_info.get("rs")
            item["rs_as_of"] = rs_info.get("rs_as_of")
            item["adr"] = timing.get("adr")
            item["timing"] = timing
            item["exit_state"] = exit_payload
            item["trail"] = exit_payload.get("trail") if isinstance(exit_payload, dict) else None
            try:
                item["days_held"] = market_calendar.trading_days_between(
                    _date.fromisoformat(row["trade_date"]), _date.fromisoformat(on_or_before)
                )
            except (ValueError, TypeError):
                item["days_held"] = None
            item["chart"] = _mini_chart_payload(conn, row["symbol"], on_or_before, 60)
            # W2.3: per-session lifecycle river (sessions-since-entry vs open-R
            # with phase bands) for the coach card expand. One writer.
            item["lifecycle"] = _position_lifecycle(
                conn, row["symbol"], row["trade_date"], on_or_before,
                row["entry"], row["stop"],
            )
            active.append(item)
        candidate_rows = conn.execute(
            "SELECT candidate_date, symbol, source, status, reason, failed_gate, snapshot_json, created_at, updated_at "
            "FROM watchlist_candidates WHERE status IN ('tracking', 'override') "
            "ORDER BY candidate_date DESC, updated_at DESC, symbol LIMIT 80"
        ).fetchall()
        tracked = []
        overrides = []
        for row in candidate_rows:
            outcome = _upsert_candidate_outcome(conn, row["candidate_date"], row["symbol"], row["source"])
            current_refusal = conn.execute(
                "SELECT failed_gate, reason FROM refusals WHERE symbol = ? AND scan_date <= ? "
                "ORDER BY scan_date DESC LIMIT 1",
                (row["symbol"], on_or_before),
            ).fetchone()
            item = {
                **dict(row),
                "snapshot": _json_col(row["snapshot_json"], {}),
                "age_days": max(0, (_date.fromisoformat(on_or_before) - _date.fromisoformat(row["candidate_date"])).days)
                if row["candidate_date"] <= on_or_before else 0,
                "current_gate_status": dict(current_refusal) if current_refusal else {"failed_gate": None, "reason": "No current refusal found"},
                "outcome": outcome,
                "chart": _mini_chart_payload(conn, row["symbol"], on_or_before, 60),
            }
            if row["status"] == "override" or row["source"] == "override":
                overrides.append(item)
            else:
                tracked.append(item)
        conn.commit()
        return {
            "available": True,
            "as_of": _latest_price_date(conn, on_or_before),
            "active_positions": active,
            "tracked_near_misses": tracked,
            "overrides": overrides,
            "manual_watchlist": manual,
        }
    finally:
        conn.close()


@app.get("/api/visuals/gate-health")
def gate_health(date: str | None = Query(default=None), days: int = Query(default=60, ge=10, le=260)) -> dict[str, Any]:
    on_or_before = date or _today()
    conn = db.connect()
    try:
        _ensure_organic_watchlist_schema(conn)
        scanner_candidates.ensure_schema(conn)
        scanner_candidates.ensure_refusals_schema(conn)
        dates = [
            r["scan_date"]
            for r in conn.execute(
                "SELECT DISTINCT scan_date FROM refusals WHERE scan_date <= ? "
                "UNION SELECT DISTINCT scan_date FROM scan_candidates WHERE scan_date <= ? "
                "ORDER BY scan_date DESC LIMIT ?",
                (on_or_before, on_or_before, days),
            ).fetchall()
        ]
        dates = list(reversed(dates))
        refusal_counts = [
            {"date": r["scan_date"], "gate": r["failed_gate"], "count": r["n"]}
            for r in conn.execute(
                "SELECT scan_date, failed_gate, COUNT(*) AS n FROM refusals "
                "WHERE scan_date IN (%s) GROUP BY scan_date, failed_gate ORDER BY scan_date, failed_gate"
                % ",".join("?" for _ in dates),
                dates,
            ).fetchall()
        ] if dates else []
        passed_counts = [
            dict(r) for r in conn.execute(
                "SELECT scan_date AS date, COUNT(*) AS count FROM scan_candidates "
                "WHERE scan_date IN (%s) GROUP BY scan_date ORDER BY scan_date"
                % ",".join("?" for _ in dates),
                dates,
            ).fetchall()
        ] if dates else []
        outcome_rows = conn.execute(
            "SELECT source, candidate_date, ret_10 FROM watchlist_candidate_outcomes "
            "WHERE ret_10 IS NOT NULL ORDER BY candidate_date"
        ).fetchall()
        medians = []
        for source in sorted({r["source"] for r in outcome_rows}):
            vals = [float(r["ret_10"]) for r in outcome_rows if r["source"] == source]
            mid = len(vals) // 2
            median = None if not vals else (sorted(vals)[mid] if len(vals) % 2 else (sorted(vals)[mid - 1] + sorted(vals)[mid]) / 2)
            medians.append({"source": source, "median_ret_10": _round(median), "n": len(vals)})
        return {"available": True, "as_of": dates[-1] if dates else None, "refusal_counts": refusal_counts, "passed_counts": passed_counts, "rolling_t10_medians": medians}
    finally:
        conn.close()


@app.get("/api/journal/visuals")
def journal_visuals() -> dict[str, Any]:
    conn = db.connect()
    try:
        _ensure_journal_table(conn)
        _ensure_organic_watchlist_schema(conn)
        scanner_outcomes.ensure_schema(conn)
        scanner_outcomes.ensure_setup_decisions_schema(conn)
        rows = conn.execute(
            "SELECT trade_id, trade_date, symbol, setup, entry, exit, stop, r_result, "
            "mistake_tags_json, notes, exit_date "
            "FROM journal_trades ORDER BY trade_date, trade_id"
        ).fetchall()
        equity = []
        running = 0.0
        r_hist = []
        mistake_counts: dict[str, int] = {}
        slippage = []
        trades = []
        for row in rows:
            item = dict(row)
            trades.append(item)
            r_value = row["r_result"]
            if r_value is not None:
                running += float(r_value)
                r_hist.append(float(r_value))
            equity.append({"date": row["trade_date"], "symbol": row["symbol"], "cumulative_r": _round(running), "r": _round(r_value)})
            for tag in _json_col(row["mistake_tags_json"], []):
                mistake_counts[str(tag)] = mistake_counts.get(str(tag), 0) + 1
            decision = conn.execute(
                "SELECT entry_price FROM setup_decisions WHERE scan_date = ? AND symbol = ?",
                (row["trade_date"], row["symbol"]),
            ).fetchone()
            planned = decision["entry_price"] if decision and decision["entry_price"] is not None else row["entry"]
            if planned is not None and row["entry"] is not None:
                slippage.append({
                    "date": row["trade_date"],
                    "symbol": row["symbol"],
                    "planned": _round(planned),
                    "actual": _round(row["entry"]),
                    "slip_pct": _round((float(row["entry"]) - float(planned)) / float(planned) * 100.0) if float(planned) else None,
                })
        decisions = conn.execute("SELECT decision, COUNT(*) AS n FROM setup_decisions GROUP BY decision").fetchall()
        tracked = conn.execute("SELECT status, COUNT(*) AS n FROM watchlist_candidates GROUP BY status").fetchall()
        refused = conn.execute(
            "SELECT COUNT(*) AS n FROM refusals WHERE scan_date >= ("
            "  SELECT MIN(scan_date) FROM ("
            "    SELECT scan_date FROM ("
            "      SELECT DISTINCT scan_date FROM refusals "
            "      UNION SELECT DISTINCT scan_date FROM scan_candidates"
            "    ) ORDER BY scan_date DESC LIMIT 20"
            "  )"
            ")"
        ).fetchone()
        cohorts = {
            "taken": 0,
            "skipped": 0,
            "tracked_near_miss": 0,
            "refused": refused["n"] if refused else 0,
        }
        for row in decisions:
            cohorts[row["decision"]] = row["n"]
        for row in tracked:
            if row["status"] == "tracking":
                cohorts["tracked_near_miss"] = row["n"]
        decision_outcomes = conn.execute(
            "SELECT d.decision, d.skip_reason, o.forward_r "
            "FROM setup_decisions d "
            "JOIN outcomes o ON o.candidate_date = d.scan_date AND o.symbol = d.symbol "
            "WHERE o.horizon = 10 AND o.forward_r IS NOT NULL"
        ).fetchall()
        cohort_values: dict[str, list[float]] = {
            "taken": [float(t["r_result"]) for t in trades if t.get("r_result") is not None],
            "pushed-skipped": [],
            "armed-skipped": [],
            "refused": [],
        }
        for row in decision_outcomes:
            decision = str(row["decision"] or "").lower()
            reason = str(row["skip_reason"] or "").lower()
            if decision == "taken":
                continue
            key = "pushed-skipped" if "push" in reason else "armed-skipped"
            cohort_values[key].append(float(row["forward_r"]))
        cohort_medians = {
            key: {"median_r": _round(_median(values)), "n": len(values)}
            for key, values in cohort_values.items()
        }
        mistake_pareto = [{"tag": k, "count": v} for k, v in sorted(mistake_counts.items(), key=lambda item: (-item[1], item[0]))]
        open_positions = [t for t in trades if t.get("exit") is None]
        return {
            "available": True,
            "equity_curve": equity,
            "r_histogram": r_hist,
            "mistake_pareto": mistake_pareto,
            "cohort_counts": cohorts,
            "cohort_medians": cohort_medians,
            "slippage": slippage,
            "trade_lifecycle": open_positions,
            "regime_overlay": equity,
        }
    finally:
        conn.close()


@app.get("/api/alerts/eod")
def eod_alerts_latest(
    date: str | None = Query(default=None, description="YYYY-MM-DD; defaults to latest"),
    limit: int = Query(default=50, ge=1, le=200, description="Maximum alerts"),
) -> dict[str, Any]:
    """Latest persisted EOD alerts generated by the P3 alert stage."""
    on_or_before = date or _today()
    conn = db.connect()
    try:
        return eod_alerts.load_alerts(conn, on_or_before, limit=limit)
    finally:
        conn.close()


@app.get("/api/portfolio/heat")
def portfolio_heat() -> dict[str, Any]:
    conn = db.connect()
    try:
        _ensure_journal_table(conn)
        scanner_outcomes.ensure_setup_decisions_schema(conn)
        capital = float(config.get("risk.capital", 1_000_000) or 1_000_000)
        mode_row = conn.execute(
            "SELECT market_mode FROM regime_snapshots ORDER BY snapshot_date DESC LIMIT 1"
        ).fetchone()
        mode = mode_row["market_mode"] if mode_row else "NO_TRADE"
        cap_pct = governor(mode).get("open_risk_cap_pct")
        rows = conn.execute(
            "SELECT trade_id, trade_date, symbol, setup, entry, stop FROM journal_trades "
            "WHERE exit IS NULL ORDER BY trade_date DESC, trade_id DESC"
        ).fetchall()
        positions = []
        sector_counts: dict[str, int] = {}
        open_risk_pct = 0.0
        for row in rows:
            decision = conn.execute(
                "SELECT qty, snapshot_json FROM setup_decisions "
                "WHERE scan_date = ? AND symbol = ?",
                (row["trade_date"], row["symbol"]),
            ).fetchone()
            qty = int(decision["qty"]) if decision and decision["qty"] is not None else 0
            sector = None
            if decision and decision["snapshot_json"]:
                try:
                    sector = json.loads(decision["snapshot_json"]).get("sector")
                except json.JSONDecodeError:
                    sector = None
            entry = float(row["entry"]) if row["entry"] is not None else None
            stop = float(row["stop"]) if row["stop"] is not None else None
            risk_pct = 0.0
            if entry is not None and stop is not None and entry > 0 and qty > 0 and capital > 0:
                risk_pct = (entry - stop) / entry * qty * entry / capital * 100.0
            open_risk_pct += risk_pct
            if sector:
                sector_counts[sector] = sector_counts.get(sector, 0) + 1
            positions.append({
                "symbol": row["symbol"],
                "entry": entry,
                "stop": stop,
                "qty": qty,
                "risk_pct": round(risk_pct, 4),
                "sector": sector,
            })
        closed = conn.execute(
            "SELECT r_result FROM journal_trades WHERE exit IS NOT NULL AND r_result IS NOT NULL "
            "ORDER BY trade_date DESC, trade_id DESC LIMIT 10"
        ).fetchall()
        r_values = [float(r["r_result"]) for r in closed]
        rolling_avg = round(sum(r_values) / len(r_values), 2) if r_values else None
        return {
            "open_risk_pct": round(open_risk_pct, 4),
            "cap_pct": cap_pct,
            "positions": positions,
            "sector_counts": sector_counts,
            "rolling_10_avg_r": {"value": rolling_avg, "n": len(r_values)},
            "half_size_mode": bool(len(r_values) >= 10 and rolling_avg is not None and rolling_avg < 0),
        }
    finally:
        conn.close()


@app.get("/api/flow/today")
def flow_today() -> dict[str, Any]:
    """The Guided Daily Flow (plan T3.8). One state-driven stepper that walks
    a beginner through their day in five ordered steps, each with a status and
    a single primary action. This is the orchestration layer over the existing
    endpoints — it aggregates, never recomputes.

    Steps:
      1. data    — is today's pipeline run fresh? (checks latest prices vs today)
      2. regime  — posture known? (any regime snapshot <= today)
      3. positions — any open position needing action (two-strike exit_now)?
      4. setups  — how many cleared the gate tonight (governor-capped count)?
      5. done    — all steps cleared?

    Each step: {id, label, status in {done, action, blocked, skipped}, detail,
    count}. The frontend renders the FIRST non-done step expanded with its
    primary button; the rest collapse to a one-line strip.
    """
    conn = db.connect()
    try:
        _ensure_journal_table(conn)
        scanner_outcomes.ensure_setup_decisions_schema(conn)
        on_or_before = _today()

        # 1. DATA — latest bhavcopy price date vs today
        latest_price = _latest_price_date(conn, on_or_before)
        price_lag = None
        if latest_price:
            try:
                price_lag = market_calendar.trading_days_between(
                    _date.fromisoformat(latest_price), _date.fromisoformat(on_or_before)
                )
            except ValueError:
                price_lag = None
        data_status = "done" if (latest_price is not None and (price_lag == 0)) else (
            "action" if latest_price is not None else "blocked"
        )
        data_step = {
            "id": "data", "label": "Data",
            "status": data_status,
            "detail": (f"Latest session {latest_price} ({price_lag} trading day(s) behind)."
                       if latest_price else "No price data — run the pipeline."),
            "count": price_lag,
        }

        # 2. REGIME — latest posture
        mode_row = conn.execute(
            "SELECT market_mode, snapshot_date FROM regime_snapshots "
            "WHERE snapshot_date <= ? ORDER BY snapshot_date DESC LIMIT 1",
            (on_or_before,),
        ).fetchone()
        if mode_row and latest_price:
            regime_status = "done"
            regime_detail = f"Posture is {mode_row['market_mode']} (as of {mode_row['snapshot_date']})."
        elif mode_row and not latest_price:
            regime_status = "skipped"
            regime_detail = "Regime known but no fresh prices — review after the pipeline runs."
        else:
            regime_status = "blocked"
            regime_detail = "No regime snapshot — run the pipeline."
        regime_step = {
            "id": "regime", "label": "Regime",
            "status": regime_status, "detail": regime_detail,
            "count": None,
            "mode": mode_row["market_mode"] if mode_row else None,
        }

        # 3. POSITIONS — open journal trades with two-strike exit_now
        open_rows = conn.execute(
            "SELECT trade_id, symbol, trade_date, setup, entry, stop, first_exit_flag_date FROM journal_trades "
            "WHERE exit IS NULL ORDER BY trade_date DESC"
        ).fetchall()
        actions = []
        for row in open_rows:
            coach = _coach_for_open_trade(conn, row, latest_price or on_or_before)
            if not coach or not coach.get("exit_now"):
                continue
            actions.append({
                "symbol": row["symbol"],
                "reason": ", ".join(coach.get("fired", [])) or "two-strike rule",
                "banner": coach.get("banner"),
            })
        if not open_rows:
            pos_status = "skipped"
            pos_detail = "No open positions — nothing to manage today."
        elif actions:
            pos_status = "action"
            pos_detail = f"{len(actions)} position(s) flagged EXIT TODAY: " + ", ".join(
                a["symbol"] for a in actions)
        else:
            pos_status = "done"
            pos_detail = f"{len(open_rows)} open position(s), none flagged for exit today."
        pos_step = {
            "id": "positions", "label": "Positions",
            "status": pos_status, "detail": pos_detail,
            "count": len(open_rows),
            "actions": actions,
        }

        # 4. SETUPS — how many cleared the gate tonight
        scan_row = conn.execute(
            "SELECT MAX(scan_date) AS d FROM scan_candidates WHERE scan_date <= ?",
            (on_or_before,),
        ).fetchone()
        scan_date = scan_row["d"] if scan_row else None
        n_passed = 0
        n_displayed = 0
        n_reviewed = 0
        if scan_date:
            n_passed = conn.execute(
                "SELECT COUNT(*) FROM scan_candidates WHERE scan_date = ?",
                (scan_date,),
            ).fetchone()[0]
            mode_for_gov = (mode_row["market_mode"] if mode_row else "SELECTIVE") or "SELECTIVE"
            n_displayed = min(n_passed, governor(mode_for_gov)["max_cards"])
            n_reviewed = conn.execute(
                "SELECT COUNT(*) FROM setup_decisions WHERE scan_date = ?",
                (scan_date,),
            ).fetchone()[0]
        # A scan that RAN (per pipeline_runs) but found 0 candidates still counts
        # as "ran" — the gate worked, nothing cleared it. Without this fallback
        # the flow stays blocked on a day the gate correctly refused everything.
        scan_ran = bool(scan_date) or bool(conn.execute(
            "SELECT 1 FROM pipeline_runs WHERE stage = 'scan_candidates' "
            "AND run_date <= ? AND status = 'ok' LIMIT 1",
            (on_or_before,),
        ).fetchone())
        # NO_TRADE variant (T3.8): the governor suppresses all families by law,
        # so the setups step is done because you're sitting out — NOT because
        # the gate refused everything. The message must say so plainly so the
        # beginner reads "sit out" instead of "the gate found nothing."
        mode_now = (mode_row["market_mode"] if mode_row else None) or None
        if mode_now == "NO_TRADE":
            setups_status = "done"
            setups_detail = "NO_TRADE posture — the governor blocks all entries today. Sit out; no new trades."
        elif scan_date and n_passed > 0:
            setups_status = "done" if n_displayed <= 0 or n_reviewed >= n_displayed else "action"
            setups_detail = (
                f"All {n_displayed} displayed setup(s) reviewed (scan {scan_date})."
                if setups_status == "done"
                else f"{n_displayed - n_reviewed} of {n_displayed} setup(s) still need TAKEN / SKIPPED "
                     f"({n_passed} cleared the gate, scan {scan_date})."
            )
        elif scan_ran:
            setups_status = "done"
            setups_detail = "Scan ran but nothing cleared the gate tonight — the refusal IS the product."
        else:
            setups_status = "blocked"
            setups_detail = "No scan has run — run the pipeline."
        setups_step = {
            "id": "setups", "label": "Setups",
            "status": setups_status, "detail": setups_detail,
            "count": n_displayed,
        }

        ticket = _order_ticket_for_scan(conn, scan_date)
        if mode_now == "NO_TRADE":
            ticket_status = "skipped"
            ticket_detail = "NO_TRADE posture - no order ticket today."
        elif ticket:
            ticket_status = "action"
            ticket_detail = f"Order ticket ready for {ticket['symbol']} - copy it only if the trigger trades."
        elif setups_status in {"action", "blocked"}:
            ticket_status = "blocked"
            ticket_detail = "Review setups first and log TAKEN to unlock a copyable order ticket."
        else:
            ticket_status = "skipped"
            ticket_detail = "No order ticket needed - no setup was marked TAKEN."
        ticket_step = {
            "id": "order_ticket",
            "label": "Order Ticket",
            "status": ticket_status,
            "detail": ticket_detail,
            "count": 1 if ticket else 0,
            "ticket": ticket,
        }

        steps = [data_step, regime_step, pos_step, setups_step, ticket_step]
        # 5. DONE — all prior steps done/skipped (action/blocked = not done)
        terminal_ok = all(s["status"] in {"done", "skipped"} for s in steps)
        done_detail = ("All steps cleared — you're done for tonight."
                       if terminal_ok else "Finish the open steps above first.")
        # Friday weekly step (T3.8): on Fridays, prompt the weekly review —
        # journal mistakes, regime drift, expectancy cell trust progression.
        # Not a separate step (the wireframe is 5 chips); a note appended to
        # the done detail so the beginner sees it on a Friday regardless of
        # whether the day's steps are all terminal yet.
        try:
            is_friday = _date.fromisoformat(on_or_before).weekday() == 4
        except ValueError:
            is_friday = False
        if is_friday:
            done_detail += " It's Friday — weekly review: scan your mistake tags, check the regime ribbon, note any expectancy cells that crossed n=20."
        done_step = {
            "id": "done", "label": "Done",
            "status": "done" if terminal_ok else "blocked",
            "detail": done_detail,
            "count": None,
            "weekly_review": is_friday,
        }
        steps.append(done_step)

        # The FIRST non-done step is the "current" one the UI expands.
        current_idx = next((i for i, s in enumerate(steps)
                            if s["status"] not in {"done", "skipped"}), len(steps) - 1)

        conn.commit()
        return {
            "available": True,
            "as_of": on_or_before,
            "current_step": steps[current_idx]["id"],
            "steps": steps,
        }
    finally:
        conn.close()


@app.get("/api/expectancy")
def expectancy() -> dict[str, Any]:
    conn = db.connect()
    try:
        scanner_expectancy.ensure_schema(conn)
        latest = conn.execute("SELECT MAX(as_of) AS d FROM setup_expectancy").fetchone()
        if not latest or not latest["d"]:
            return {"available": False, "as_of": None, "system": [], "personal": []}
        as_of = latest["d"]
        rows = conn.execute(
            "SELECT as_of, loop, setup_family, regime, n, hit_rate, mean_r, median_r, posterior_r, trust "
            "FROM setup_expectancy WHERE as_of = ? ORDER BY loop, setup_family, regime",
            (as_of,),
        ).fetchall()
        out = {"system": [], "personal": []}
        for row in rows:
            item = dict(row)
            loop = item.pop("loop")
            out.setdefault(loop, []).append(item)
        return {"available": True, "as_of": as_of, "system": out["system"], "personal": out["personal"]}
    finally:
        conn.close()


@app.get("/api/journal")
def journal() -> dict[str, Any]:
    """Trade journal with expectancy stats."""
    conn = db.connect()
    try:
        _ensure_journal_table(conn)
        rows = conn.execute(
            "SELECT trade_id, trade_date, symbol, setup, entry, exit, stop, r_result, "
            "mistake_tags_json, notes, created_at, exit_date FROM journal_trades "
            "ORDER BY trade_date DESC, trade_id DESC"
        ).fetchall()
        trades = [_journal_item(row) for row in rows]
        for trade in trades:
            if trade.get("exit_state") is None:
                trade["exit_state"] = _symbol_exit_state(conn, trade["symbol"], trade["trade_date"])
            # W1.5: per-trade MFE/MAE in R over [trade_date, exit_date or latest].
            # Computed read-only from daily_prices; one writer (this endpoint).
            # The Journal scatter reads trade.mfe_r / trade.mae_r.
            trade["mfe_r"], trade["mae_r"] = _trade_excursion_r(
                conn, trade["symbol"], trade.get("trade_date") or trade.get("entry_date"),
                trade.get("exit_date"), trade.get("entry"), trade.get("stop"),
            )
        return {"available": True, "trades": trades, "stats": _journal_stats(trades)}
    finally:
        conn.close()


@app.post("/api/journal")
def journal_add(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """Add one journal trade. R is computed deterministically for long trades."""
    trade_date = str(payload.get("trade_date") or "").strip()
    symbol = str(payload.get("symbol") or "").strip().upper()
    if not trade_date or not symbol:
        raise HTTPException(400, "trade_date and symbol are required")
    tags = _normalize_tags(payload.get("mistake_tags"))
    r_result = _trade_r(payload.get("entry"), payload.get("exit"), payload.get("stop"))
    conn = db.connect()
    try:
        _ensure_journal_table(conn)
        exit_state = _symbol_exit_state(conn, symbol, trade_date)
        cur = conn.execute(
            "INSERT INTO journal_trades (trade_date, symbol, setup, entry, exit, stop, "
            "r_result, mistake_tags_json, notes, exit_state_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                trade_date,
                symbol,
                payload.get("setup"),
                payload.get("entry"),
                payload.get("exit"),
                payload.get("stop"),
                r_result,
                json.dumps(tags),
                payload.get("notes"),
                json.dumps(exit_state),
            ),
        )
        conn.commit()
        return {"ok": True, "trade_id": cur.lastrowid, "symbol": symbol, "r_result": r_result}
    finally:
        conn.close()


@app.put("/api/journal/{trade_id}")
def journal_update(trade_id: int, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """Update one journal trade and recompute R from entry/exit/stop."""
    trade_date = str(payload.get("trade_date") or "").strip()
    symbol = str(payload.get("symbol") or "").strip().upper()
    if not trade_date or not symbol:
        raise HTTPException(400, "trade_date and symbol are required")
    tags = _normalize_tags(payload.get("mistake_tags"))
    r_result = _trade_r(payload.get("entry"), payload.get("exit"), payload.get("stop"))
    conn = db.connect()
    try:
        _ensure_journal_table(conn)
        exit_state = _symbol_exit_state(conn, symbol, trade_date)
        cur = conn.execute(
            "UPDATE journal_trades SET trade_date = ?, symbol = ?, setup = ?, entry = ?, "
            "exit = ?, stop = ?, r_result = ?, mistake_tags_json = ?, notes = ?, exit_state_json = ?, "
            "first_exit_flag_date = CASE WHEN ? IS NOT NULL THEN NULL ELSE first_exit_flag_date END "
            "WHERE trade_id = ?",
            (
                trade_date,
                symbol,
                payload.get("setup"),
                payload.get("entry"),
                payload.get("exit"),
                payload.get("stop"),
                r_result,
                json.dumps(tags),
                payload.get("notes"),
                json.dumps(exit_state),
                payload.get("exit"),
                trade_id,
            ),
        )
        conn.commit()
        return {"ok": True, "trade_id": trade_id, "symbol": symbol, "r_result": r_result}
    finally:
        conn.close()


@app.post("/api/journal/trades/{trade_id}/close")
def journal_close_trade(trade_id: int, payload: dict[str, Any] = Body(...)):
    """Close one open journal trade, with the T3.9 early-exit guard."""
    if payload.get("exit_price") is None:
        raise HTTPException(400, "exit_price is required")
    conn = db.connect()
    try:
        _ensure_journal_table(conn)
        trade = conn.execute(
            "SELECT trade_id, trade_date, symbol, setup, entry, stop, exit, mistake_tags_json, first_exit_flag_date "
            "FROM journal_trades WHERE trade_id = ? AND exit IS NULL",
            (trade_id,),
        ).fetchone()
        if not trade:
            raise HTTPException(404, "open trade not found")
        as_of = str(payload.get("date") or _today())
        coach = _coach_for_open_trade(conn, trade, as_of)
        mistake_tag = str(payload.get("mistake_tag") or "").strip()
        if coach and coach.get("verdict") == "HOLD" and not mistake_tag:
            return JSONResponse(
                status_code=409,
                content={
                    "guard": True,
                    "message": (
                        "The system reads this as a HOLD - exiting now is the #1 beginner mistake "
                        "(fear of giving back). If you still want to exit, pick a reason."
                    ),
                    "reasons": ["fear", "need-cash", "thesis-change", "other"],
                },
            )
        tags = _json_col(trade["mistake_tags_json"], [])
        if mistake_tag:
            tags.append(mistake_tag)
        exit_price = float(payload["exit_price"])
        r_result = _trade_r(trade["entry"], exit_price, trade["stop"])
        exit_state = _symbol_exit_state(conn, trade["symbol"], as_of)
        conn.execute(
            "UPDATE journal_trades SET exit = ?, r_result = ?, mistake_tags_json = ?, "
            "exit_state_json = ?, exit_date = ?, first_exit_flag_date = NULL WHERE trade_id = ?",
            (exit_price, r_result, json.dumps(tags), json.dumps(exit_state), as_of, trade_id),
        )
        conn.commit()
        return {"ok": True, "trade_id": trade_id, "symbol": trade["symbol"], "r_result": r_result}
    finally:
        conn.close()


@app.delete("/api/journal/{trade_id}")
def journal_delete(trade_id: int) -> dict[str, Any]:
    """Delete one journal trade."""
    conn = db.connect()
    try:
        _ensure_journal_table(conn)
        cur = conn.execute("DELETE FROM journal_trades WHERE trade_id = ?", (trade_id,))
        conn.commit()
        return {"ok": True, "trade_id": trade_id, "deleted": cur.rowcount}
    finally:
        conn.close()


def _today() -> str:
    from datetime import date
    return date.today().isoformat()


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline run (the "Refresh data" button). Runs the same run-eod stages the
# CLI runs, in a background thread so the request returns immediately; the UI
# polls /api/pipeline/status until done, then refetches. Single-user, so one
# run at a time is enough.
# ─────────────────────────────────────────────────────────────────────────────

_PIPELINE_LOCK = threading.Lock()
_PIPELINE_STATUS: dict[str, Any] = {
    "running": False, "run_date": None, "current_stage": None,
    "stages": [], "started_at": None, "finished_at": None, "error": None,
}


def _run_pipeline_thread(run_date: str, prior: list[dict[str, str]] | None = None) -> None:
    from manas_os.cli import _load_stages
    conn = db.init_db()
    stages = _load_stages()
    done: list[dict[str, str]] = list(prior or [])
    try:
        for name, fn in stages:
            with _PIPELINE_LOCK:
                _PIPELINE_STATUS["current_stage"] = name
            try:
                fn(conn, run_date)
                done.append({"name": name, "status": "ok"})
            except Exception as exc:  # per-stage isolation, like the CLI loop
                done.append({"name": name, "status": f"fail: {exc}"})
            with _PIPELINE_LOCK:
                _PIPELINE_STATUS["stages"] = list(done)
    finally:
        conn.close()
        with _PIPELINE_LOCK:
            _PIPELINE_STATUS.update({
                "running": False, "current_stage": None,
                "finished_at": time.time(), "stages": done,
            })


def _fetch_source_files(done: list[dict[str, str]]) -> None:
    """Best-effort refresh of the on-disk source files, via the two extractors.

    Runs as subprocesses so a hung/failed scrape can't take down the API. Each
    is bounded by a timeout and reported honestly — breadth is NOT here because
    it's fetched live from the Google sheet during ingest_breadth every run.
    """
    import subprocess
    import sys
    from pathlib import Path

    repo = Path(__file__).resolve().parents[2]

    def _step(name: str, argv: list[str], cwd: Path, timeout: int) -> None:
        with _PIPELINE_LOCK:
            _PIPELINE_STATUS["current_stage"] = name
        try:
            r = subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)
            status = "ok" if r.returncode == 0 else f"fail: exit {r.returncode}"
        except subprocess.TimeoutExpired:
            status = f"fail: timed out ({timeout}s)"
        except Exception as exc:
            status = f"fail: {exc}"
        done.append({"name": name, "status": status})
        with _PIPELINE_LOCK:
            _PIPELINE_STATUS["stages"] = list(done)

    # NSE bhavcopy — 'both' tries girish then tilak; girish's mirror lags by
    # days (returned 0 files for a 5-day window on 2026-07-07), tilak had the
    # missing sessions. Writes to repo-root data/bhavcopy (see sources/bhavcopy).
    _step("fetch_bhavcopy",
          [sys.executable, "download_bhavcopy.py", "--source", "both", "--days", "5"],
          repo / "bhavcopy_extractor", 300)
    # ChartsMaze — Playwright scrape; needs a logged-in profile (run login.py once).
    # output_root is aligned to the ingest dir, so fresh files land where ingest reads.
    _step("fetch_chartsmaze",
          [sys.executable, "extractor.py", "--headless"],
          repo / "chartsmaze_extractor", 600)


def _run_pipeline_thread_full(run_date: str, fetch_sources: bool) -> None:
    done: list[dict[str, str]] = []
    if fetch_sources:
        _fetch_source_files(done)
    _run_pipeline_thread(run_date, prior=done)


@app.post("/api/pipeline/run")
def pipeline_run(
    date: str | None = Body(None, embed=True),
    fetch_sources: bool = Body(False, embed=True),
) -> dict[str, Any]:
    """Kick off a background run-eod. Returns immediately; poll /status.

    fetch_sources=True first refreshes the on-disk source files (bhavcopy +
    ChartsMaze extractors) before ingesting — the "update to latest" path.
    """
    run_date = date or market_calendar.last_trading_day(_date.today()).isoformat()
    with _PIPELINE_LOCK:
        if _PIPELINE_STATUS["running"]:
            return {"started": False, "reason": "already running", **_PIPELINE_STATUS}
        _PIPELINE_STATUS.update({
            "running": True, "run_date": run_date,
            "current_stage": "fetching sources" if fetch_sources else "starting",
            "stages": [], "started_at": time.time(), "finished_at": None, "error": None,
        })
    threading.Thread(
        target=_run_pipeline_thread_full, args=(run_date, fetch_sources), daemon=True
    ).start()
    return {"started": True, "run_date": run_date, "fetch_sources": fetch_sources}


@app.get("/api/pipeline/status")
def pipeline_status() -> dict[str, Any]:
    with _PIPELINE_LOCK:
        return dict(_PIPELINE_STATUS)


@app.get("/api/data/coverage")
def data_coverage() -> dict[str, Any]:
    """Per-source 'data updated until <date>' — the freshness identifier.

    Each source reports the latest date it holds, so the user can see at a
    glance what is current and what is lagging.
    """
    def _max(conn, table: str, col: str) -> str | None:
        try:
            r = conn.execute(f"SELECT MAX({col}) FROM {table}").fetchone()
            return r[0] if r and r[0] else None
        except Exception:
            return None

    def _latest_chartsmaze_folder() -> str | None:
        root = chartsmaze.chartsmaze_dir()
        if not root.is_dir():
            return None
        dates = [c.name for c in root.iterdir() if c.is_dir() and c.name[:4].isdigit()]
        return max(dates) if dates else None

    conn = db.connect()
    try:
        sources = [
            {"key": "breadth", "label": "Breadth (Google sheet)",
             "until": _max(conn, "breadth_daily", "trade_date"), "live_fetch": True},
            {"key": "prices", "label": "NSE bhavcopy (prices + delivery)",
             "until": _max(conn, "daily_prices", "trade_date"), "live_fetch": False},
            {"key": "chartsmaze", "label": "ChartsMaze (sectors/themes)",
             "until": _latest_chartsmaze_folder(), "live_fetch": False},
            {"key": "regime", "label": "Regime snapshot",
             "until": _max(conn, "regime_snapshots", "snapshot_date"), "live_fetch": False},
        ]
    finally:
        conn.close()
    return {"as_of_query": _today(), "sources": sources}


# ─────────────────────────────────────────────────────────────────────────────
# Fyers login (single-user, localhost only). Lets the user enter their app
# credentials and complete the daily auth-code exchange from the tool UI
# instead of the CLI. Secrets are written to config.yaml (gitignored) and NEVER
# returned in any response — status endpoints report booleans only.
# ─────────────────────────────────────────────────────────────────────────────

def _write_fyers_config(values: dict[str, str]) -> None:
    """Merge the given fyers.* keys into config.yaml, preserving other sections."""
    import yaml
    from pathlib import Path

    cfg_path = Path(__file__).resolve().parents[1] / "config.yaml"
    data: dict[str, Any] = {}
    if cfg_path.exists():
        data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    fyers = dict(data.get("fyers") or {})
    for k, v in values.items():
        if v is not None and str(v).strip():
            fyers[k] = str(v).strip()
    data["fyers"] = fyers
    cfg_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


@app.get("/api/fyers/status")
def fyers_status() -> dict[str, Any]:
    """Auth readiness — booleans only, no secrets returned."""
    from manas_os.providers import fyers_auth
    return {
        "app_id_set": bool(fyers_auth.app_id()),
        "secret_set": bool(fyers_auth.secret_key()),
        "token_ready": bool(fyers_auth.get_access_token()),
        "redirect_uri": fyers_auth.redirect_uri(),
        "status": fyers_auth.token_status(),  # ready | missing_app_id | missing_token
    }


@app.post("/api/fyers/credentials")
def fyers_credentials(
    client_id: str = Body(..., embed=True),
    secret_id: str = Body(..., embed=True),
    redirect_uri: str | None = Body(None, embed=True),
) -> dict[str, Any]:
    """Save the Fyers app id + secret (+ optional redirect) to config.yaml."""
    if not client_id.strip() or not secret_id.strip():
        raise HTTPException(400, "client_id and secret_id are required")
    _write_fyers_config({
        "client_id": client_id,
        "secret_id": secret_id,
        "redirect_uri": redirect_uri,
    })
    return fyers_status()


@app.get("/api/fyers/auth-url")
def fyers_auth_url() -> dict[str, Any]:
    """The Fyers login URL to open (needs app id + secret set first)."""
    from manas_os.providers import fyers_auth
    if not fyers_auth.app_id() or not fyers_auth.secret_key():
        raise HTTPException(400, "Set your Fyers app id and secret first.")
    try:
        return {"url": fyers_auth.generate_auth_url()}
    except Exception as exc:
        raise HTTPException(500, f"Could not build login URL: {exc}")


@app.post("/api/fyers/exchange")
def fyers_exchange(value: str = Body(..., embed=True)) -> dict[str, Any]:
    """Exchange the pasted auth_code (or full redirect URL) for a token + cache it."""
    from manas_os.providers import fyers_auth
    try:
        fyers_auth.exchange_auth_code(value)
    except Exception as exc:
        raise HTTPException(400, f"Token exchange failed: {exc}")
    return fyers_status()


@app.post("/api/fyers/token")
def fyers_token(token: str = Body(..., embed=True)) -> dict[str, Any]:
    """Fallback: cache a directly-pasted access token."""
    from manas_os.providers import fyers_auth
    try:
        fyers_auth.cache_access_token(token)
    except Exception as exc:
        raise HTTPException(400, f"Could not cache token: {exc}")
    return fyers_status()


# Mentor checklists (C15): isolated configurable yes/no discipline checks.
def _mentor_checklist_by_id(checklist_id: str) -> dict[str, Any]:
    for checklist in mentor_checklists.load_checklists():
        if checklist.get("id") == checklist_id:
            return checklist
    raise HTTPException(404, "checklist not found")


@app.get("/api/mentor/checklists")
def mentor_checklists_get() -> dict[str, Any]:
    return {"checklists": mentor_checklists.load_checklists()}


@app.get("/api/mentor/checklists/{checklist_id}/responses")
def mentor_checklist_responses_get(
    checklist_id: str,
    date: str | None = Query(None),
) -> dict[str, Any]:
    checklist = _mentor_checklist_by_id(checklist_id)
    response_date = date or _today()
    responses = {str(item.get("id")): False for item in checklist.get("items", [])}
    conn = db.connect()
    try:
        mentor_checklists.ensure_schema(conn)
        rows = conn.execute(
            "SELECT item_id, checked FROM checklist_responses "
            "WHERE response_date = ? AND checklist_id = ?",
            (response_date, checklist_id),
        ).fetchall()
        for row in rows:
            if row["item_id"] in responses:
                responses[row["item_id"]] = bool(row["checked"])
    finally:
        conn.close()
    return {"date": response_date, "responses": responses}


@app.post("/api/mentor/checklists/{checklist_id}/responses")
def mentor_checklist_responses_post(
    checklist_id: str,
    payload: dict[str, Any] = Body(...),
) -> dict[str, bool]:
    checklist = _mentor_checklist_by_id(checklist_id)
    response_date = str(payload.get("date") or "").strip()
    item_id = str(payload.get("item_id") or "").strip()
    if not response_date or not item_id:
        raise HTTPException(400, "date and item_id are required")
    valid_items = {str(item.get("id")) for item in checklist.get("items", [])}
    if item_id not in valid_items:
        raise HTTPException(404, "item not found")
    checked = bool(payload.get("checked"))
    conn = db.connect()
    try:
        mentor_checklists.ensure_schema(conn)
        conn.execute(
            "INSERT INTO checklist_responses (response_date, checklist_id, item_id, checked) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(response_date, checklist_id, item_id) DO UPDATE SET "
            "checked = excluded.checked",
            (response_date, checklist_id, item_id, 1 if checked else 0),
        )
        conn.commit()
    finally:
        conn.close()
    return {"ok": True}


@app.get("/api/advisor/today")
def advisor_today(date: str | None = Query(default=None)) -> dict[str, Any]:
    """Presentation-only ADVISOR notes for the current/latest note date."""
    from manas_os.advisor.advisor import ensure_schema

    on_or_before = date or _today()
    conn = db.connect()
    try:
        ensure_schema(conn)
        row = conn.execute(
            "SELECT MAX(note_date) AS d FROM advisor_notes WHERE note_date <= ?",
            (on_or_before,),
        ).fetchone()
        if not row or not row["d"]:
            return {"available": False, "as_of": None, "notes": []}
        note_date = row["d"]
        rows = conn.execute(
            "SELECT note_date, scope, symbol, stance, note, watch_for, model, user_action, outcome_r, created_at "
            "FROM advisor_notes WHERE note_date = ? "
            "ORDER BY CASE scope WHEN 'regime' THEN 0 WHEN 'entry' THEN 1 WHEN 'exit' THEN 2 "
            "WHEN 'risk' THEN 3 WHEN 'event' THEN 4 ELSE 5 END, symbol",
            (note_date,),
        ).fetchall()
        notes = []
        for r in rows:
            item = dict(r)
            item["symbol"] = item["symbol"] or None
            notes.append(item)
        return {"available": True, "as_of": note_date, "notes": notes}
    finally:
        conn.close()


@app.post("/api/advisor/note-action")
def advisor_note_action(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """Upsert a user's reaction to an ADVISOR note."""
    from manas_os.advisor.advisor import ensure_schema

    note_date = str(payload.get("note_date") or "").strip()
    scope = str(payload.get("scope") or "").strip().lower()
    symbol = str(payload.get("symbol") or "").strip().upper()
    action = str(payload.get("action") or "").strip().lower()
    if not note_date or not scope:
        raise HTTPException(400, "note_date and scope are required")
    if action not in {"agreed", "dismissed"}:
        raise HTTPException(400, "action must be agreed or dismissed")
    conn = db.connect()
    try:
        ensure_schema(conn)
        conn.execute(
            "INSERT INTO advisor_notes (note_date, scope, symbol, stance, note, user_action) "
            "VALUES (?, ?, ?, 'caution', '', ?) "
            "ON CONFLICT(note_date, scope, symbol) DO UPDATE SET user_action = excluded.user_action",
            (note_date, scope, symbol, action),
        )
        conn.commit()
        return {"ok": True, "note_date": note_date, "scope": scope, "symbol": symbol or None, "action": action}
    finally:
        conn.close()


def _models_say(conn, scan_date: str) -> dict[str, Any]:
    """SHIP-3 ML-visibility pass: surfaces facts the models already compute
    (ml_scores, features_daily delivery_flag, hmm_regime, sector_downside)
    for the DESK tab's "WHAT THE MODELS SAY" panel. No new computation here
    — every value already exists in a table another stage wrote; this only
    reads and formats. All fields are EXPERIMENTAL/fact-only (AD8): never
    gates or sizes anything."""
    # agent_watchlist is the broad nightly shortlist scan universe (often
    # 1000+ symbols incl. ETFs/indices) -- "debated" means the names that
    # actually went through agent_verdicts (chair/models/vision/sizer),
    # same set the DEBATE tab itself renders.
    debated_symbols = [
        r["symbol"]
        for r in conn.execute(
            "SELECT DISTINCT symbol FROM agent_verdicts WHERE scan_date = ?", (scan_date,)
        ).fetchall()
    ]

    ml_p_up_range: dict[str, Any] = {"available": False}
    delivery_names: list[str] = []
    if debated_symbols:
        placeholders = ",".join("?" for _ in debated_symbols)
        ml_rows = conn.execute(
            f"SELECT p_up_10d FROM ml_scores WHERE scan_date = ? AND symbol IN ({placeholders}) "
            "AND p_up_10d IS NOT NULL",
            (scan_date, *debated_symbols),
        ).fetchall()
        vals = [r["p_up_10d"] for r in ml_rows]
        if vals:
            ml_p_up_range = {
                "available": True, "n": len(vals),
                "min": round(min(vals), 2), "max": round(max(vals), 2),
            }

        feat_rows = conn.execute(
            f"SELECT symbol, feature_json FROM features_daily WHERE trade_date = ? "
            f"AND symbol IN ({placeholders})",
            (scan_date, *debated_symbols),
        ).fetchall()
        for r in feat_rows:
            bag = _json_col(r["feature_json"], {})
            if bag.get("delivery_flag") == "ACCUMULATION":
                delivery_names.append(r["symbol"])

    try:
        market_hmm = regime_hmm.get_display_caption(conn, scan_date).get("caption")
    except Exception:
        market_hmm = None

    sector_downside_by_key = _sector_downside_by_key(conn, scan_date)
    top3 = sorted(
        (
            (key, row)
            for key, row in sector_downside_by_key.items()
            if row.get("p_drawdown_5d") is not None
        ),
        key=lambda kv: kv[1]["p_drawdown_5d"],
        reverse=True,
    )[:3]
    sector_downside_top3 = [
        {
            "sector": display_label(key),
            "p_drawdown_5d": round(row["p_drawdown_5d"], 3),
            "n_train": row.get("n_train"),
        }
        for key, row in top3
    ]

    return {
        "ml_p_up_range": ml_p_up_range,
        "delivery_accumulation": {"names": sorted(set(delivery_names))},
        "market_hmm_status": market_hmm,
        "sector_downside_top3": sector_downside_top3,
    }


@app.get("/api/desk/run-card")
def desk_run_card(date: str | None = Query(default=None)) -> dict[str, Any]:
    """AD4: the canonical run_card.json for a night, written by agents_coach."""
    from manas_os.agents import run_card as run_card_module

    run_date = date or _today()
    path = run_card_module.RUN_CARD_ROOT / f"{run_date}.json"
    if not path.exists():
        return {"available": False, "run_date": run_date}
    try:
        card = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"available": False, "run_date": run_date}
    conn = db.connect()
    try:
        models_say = _models_say(conn, run_date)
    except Exception:
        models_say = None
    finally:
        conn.close()
    return {"available": True, **card, "models_say": models_say}


@app.get("/api/desk/chart")
def desk_chart(
    date: str = Query(...),
    symbol: str = Query(...),
    tf: str = Query("daily"),
) -> Any:
    """F0 G3: serve rendered agent chart PNGs from data/agent_charts."""
    if tf not in {"daily", "weekly"}:
        raise HTTPException(400, "tf must be daily or weekly")
    clean_symbol = str(symbol or "").strip().upper()
    if not re.fullmatch(r"[A-Z0-9._-]+", clean_symbol):
        raise HTTPException(400, "symbol is invalid")
    clean_date = str(date or "").strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", clean_date):
        raise HTTPException(400, "date must be YYYY-MM-DD")
    try:
        # AUDIT-2: regex only checks digit shape ("2026-13-99" would pass it);
        # fromisoformat rejects out-of-range month/day so a bad calendar date
        # 4xx's instead of silently building a bogus path.
        _date.fromisoformat(clean_date)
    except ValueError:
        raise HTTPException(400, "date must be a valid calendar date")

    root = Path("data") / "agent_charts" / clean_date
    path = root / f"{clean_symbol}_{tf}.png"
    if not path.exists() or not path.is_file():
        return JSONResponse(status_code=404, content={"available": False, "date": clean_date, "symbol": clean_symbol, "tf": tf})
    return FileResponse(path, media_type="image/png")


_DESK_CHART_SYMBOL_RE = re.compile(r"[A-Z0-9._-]+")
_MSWING_INDEX_SYMBOLS = ("NIFTYMIDSML400", "NIFTY MIDSML 400", "Nifty Midsml 400")


def _clean_chart_symbol(symbol: Any) -> str:
    clean_symbol = str(symbol or "").strip().upper()
    if not _DESK_CHART_SYMBOL_RE.fullmatch(clean_symbol):
        raise HTTPException(400, "symbol is invalid")
    return clean_symbol


def _clean_chart_date(value: Any) -> str:
    clean_date = str(value or "").strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", clean_date):
        raise HTTPException(400, "date must be YYYY-MM-DD")
    try:
        _date.fromisoformat(clean_date)
    except ValueError:
        raise HTTPException(400, "date must be a valid calendar date") from None
    return clean_date


def _chart_bar(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "time": row["date"],
        "open": _round(row.get("open")),
        "high": _round(row.get("high")),
        "low": _round(row.get("low")),
        "close": _round(row.get("close")),
        "volume": row.get("volume"),
    }


def _load_mswing_index_bars(conn, stock_bars: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not stock_bars:
        return []
    placeholders = ",".join("?" for _ in _MSWING_INDEX_SYMBOLS)
    rows = conn.execute(
        "SELECT trade_date, close FROM sector_index_prices "
        f"WHERE symbol IN ({placeholders}) AND trade_date >= ? AND trade_date <= ? "
        "AND close IS NOT NULL ORDER BY trade_date",
        (*_MSWING_INDEX_SYMBOLS, stock_bars[0]["date"], stock_bars[-1]["date"]),
    ).fetchall()
    by_date = {r["trade_date"]: r["close"] for r in rows}
    return [{"date": b["date"], "close": by_date.get(b["date"])} for b in stock_bars]


def _volume_state(raw_state: str | None) -> str:
    return {
        "high_up": "up",
        "high_down": "down",
        "bull_pp": "bull_pp",
        "bear_pp": "bear_pp",
        "dry": "dry",
    }.get(raw_state or "", "noise")


def _chart_data_payload(conn, symbol: str, on_or_before: str) -> dict[str, Any]:
    bars = _load_symbol_bars(conn, symbol, on_or_before, 250)
    if not bars:
        return {"available": False, "symbol": symbol, "as_of": None, "bars": []}

    closes = [None if b.get("close") is None else float(b["close"]) for b in bars]
    overlays = {
        f"ema{span}": [
            {"time": b["date"], "value": _round(v)}
            for b, v in zip(bars, _ema(closes, span))
        ]
        for span in (10, 21, 50, 200)
    }
    simple_volume = manas_indicators.simple_volume(bars)
    rmv_rows = manas_indicators.rmv(bars)
    mswing_rows = manas_indicators.mswing(bars, _load_mswing_index_bars(conn, bars))
    purple = manas_indicators.purple_dot(bars)
    persistency = manas_indicators.persistency_ema_bundle(bars)
    ss_rvol_rows = manas_indicators.ss_rvol(bars)

    persistency_entries = []
    persistency_exits = []
    for key, rows in persistency.items():
        for bar, row in zip(bars, rows):
            point = {"date": bar["date"], "ema": key, "count": row.get("count")}
            if row.get("entry_signal"):
                persistency_entries.append(point)
            if row.get("exit_signal"):
                persistency_exits.append(point)

    latest_rvol = ss_rvol_rows[-1] if ss_rvol_rows else {}
    hmm_payload = stock_hmm.get_or_compute(conn, symbol, bars[-1]["date"])
    return {
        "available": True,
        "symbol": symbol,
        "as_of": bars[-1]["date"],
        "bars": [_chart_bar(b) for b in bars],
        "hmm": hmm_payload,
        "overlays": overlays,
        "panes": {
            "volume_colors": [_volume_state(row.get("state")) for row in simple_volume],
            "rmv": [{"time": b["date"], "value": _round(row.get("rmv"))} for b, row in zip(bars, rmv_rows)],
            "mswing": [
                {
                    "time": b["date"],
                    "stock": _round(row.get("mswing")),
                    "index": _round(row.get("index_mswing")),
                    "color": row.get("color"),
                }
                for b, row in zip(bars, mswing_rows)
            ],
        },
        "markers": {
            "purple_dot": [b["date"] for b, flag in zip(bars, purple) if flag],
            "pocket_pivot": [
                b["date"]
                for b, row in zip(bars, simple_volume)
                if row.get("bull_pocket_pivot") or row.get("bear_pocket_pivot")
            ],
            "persistency": {"entry": persistency_entries, "exit": persistency_exits},
        },
        "meta": {
            "burst_power": manas_indicators.burst_power(bars, 250),
            "ss_rvol": {
                "rvol": _round(latest_rvol.get("rvol")),
                "avg_volume": _round(latest_rvol.get("avg_volume")),
                "strong_start": bool(latest_rvol.get("strong_start")),
                "star": bool(latest_rvol.get("strong_start") and (latest_rvol.get("rvol") or 0) >= 1.5),
            },
            "simple_volume": simple_volume[-1] if simple_volume else None,
            "rmv": rmv_rows[-1] if rmv_rows else None,
            "mswing": mswing_rows[-1] if mswing_rows else None,
        },
    }


@app.get("/api/desk/chart-data")
def desk_chart_data(date: str = Query(...), symbol: str = Query(...)) -> dict[str, Any]:
    """G5c: lightweight chart drawer payload with Wave G indicator overlays."""
    clean_symbol = _clean_chart_symbol(symbol)
    clean_date = _clean_chart_date(date)
    conn = db.connect()
    try:
        return _chart_data_payload(conn, clean_symbol, clean_date)
    finally:
        conn.close()


@app.get("/api/desk/track-record")
def desk_track_record() -> dict[str, Any]:
    """F0 G4: aggregate resolved agent outcomes by agent x setup family.

    E1/E2: also surfaces the SYSTEM expectancy ledger (setup_expectancy,
    passed vs refused cohort) so the LEDGER proves-or-kills each setup family
    over the full replayed history, not just the thin agent-verdict sample."""
    conn = db.connect()
    try:
        rows = conn.execute(
            "WITH families AS ("
            "  SELECT scan_date, symbol, MIN(setup_family) AS family "
            "  FROM scan_candidates GROUP BY scan_date, symbol"
            ") "
            "SELECT av.agent, COALESCE(f.family, 'unknown') AS family, "
            "COUNT(*) AS n, "
            "SUM(CASE WHEN av.outcome_r >= 1.0 THEN 1 ELSE 0 END) AS hits, "
            "AVG(av.outcome_r) AS avg_r "
            "FROM agent_verdicts av "
            "LEFT JOIN families f ON f.scan_date = av.scan_date AND f.symbol = av.symbol "
            "WHERE av.outcome_r IS NOT NULL "
            "GROUP BY av.agent, COALESCE(f.family, 'unknown') "
            "ORDER BY av.agent, family"
        ).fetchall()
        expectancy_rows = _system_expectancy_ledger(conn)
        screener_calibration_rows = screener_calibration.latest_ranked(conn, horizon=10)
    finally:
        conn.close()
    records = []
    for r in rows:
        n = int(r["n"] or 0)
        hits = int(r["hits"] or 0)
        records.append(
            {
                "agent": r["agent"],
                "family": r["family"],
                "n": n,
                "hit_rate": (hits / n) if n else None,
                "avg_r": r["avg_r"],
                "thin": n < 5,
            }
        )
    return {
        "records": records,
        "expectancy": expectancy_rows,
        "screener_calibration": screener_calibration_rows,
    }


def _system_expectancy_ledger(conn) -> list[dict[str, Any]]:
    """Per (family, regime) passed-vs-refused cohort rows from setup_expectancy,
    each cohort read at its own latest as_of (mirrors expectancy.chip_for).
    Never fabricates: n is whatever the replay/pipeline actually persisted;
    below TRUST_FLOOR_N the row is flagged `unproven` for the UI to render
    "UNPROVEN - building sample (n=X)" instead of a false-confidence stat."""
    scanner_expectancy.ensure_schema(conn)
    pairs = conn.execute(
        "SELECT DISTINCT setup_family, regime FROM setup_expectancy "
        "WHERE loop = 'system' ORDER BY setup_family, regime"
    ).fetchall()
    out = []
    for p in pairs:
        family, regime = p["setup_family"], p["regime"]
        passed = conn.execute(
            "SELECT n, hit_rate, mean_r, median_r, trust FROM setup_expectancy "
            "WHERE loop = 'system' AND cohort = 'passed' AND setup_family = ? AND regime = ? "
            "ORDER BY as_of DESC LIMIT 1",
            (family, regime),
        ).fetchone()
        refused = conn.execute(
            "SELECT n, hit_rate, mean_r, median_r, trust FROM setup_expectancy "
            "WHERE loop = 'system' AND cohort = 'refused' AND setup_family = ? AND regime = ? "
            "ORDER BY as_of DESC LIMIT 1",
            (family, regime),
        ).fetchone()
        if not passed and not refused:
            continue
        row: dict[str, Any] = {"family": family, "regime": regime}
        if passed:
            row["passed"] = {**dict(passed), "unproven": int(passed["n"] or 0) < scanner_expectancy.TRUST_FLOOR_N}
        if refused:
            row["refused"] = {**dict(refused), "unproven": int(refused["n"] or 0) < scanner_expectancy.TRUST_FLOOR_N}
        out.append(row)
    return out


@app.get("/api/desk/lessons")
def desk_lessons(limit: int = Query(20, ge=1, le=100)) -> dict[str, Any]:
    """F0 G5: list lesson markdown files and return the active digest text."""
    from manas_os.agents import lessons as lessons_module

    lesson_dir = lessons_module.LESSON_DIR
    digest_path = lesson_dir / "_digest.md"
    digest = ""
    if digest_path.exists():
        try:
            digest = digest_path.read_text(encoding="utf-8")
        except OSError:
            digest = ""

    items = []
    if lesson_dir.exists():
        for path in sorted(lesson_dir.glob("*.md"), key=lambda p: p.name, reverse=True):
            if path.name == "_digest.md":
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
            tag_match = re.search(r"\[(clean-hit|clean-miss|right-process-loss|wrong-process-win)\]", text)
            if not tag_match:
                tag_match = re.search(r"\b(clean-hit|clean-miss|right-process-loss|wrong-process-win)\b", text)
            items.append(
                {
                    "filename": path.name,
                    "tag": tag_match.group(1) if tag_match else None,
                    "first_line": first_line,
                }
            )
            if len(items) >= limit:
                break
    return {"lessons": items, "digest": digest}


def _feed_agent_line(row: dict[str, Any]) -> str:
    agent = row.get("agent") or "agent"
    model = row.get("model")
    parsed_ok = row.get("parsed_ok")
    validation = row.get("validation")
    error = row.get("error")
    if row.get("latency_ms") is None and not error:
        label = f" ({model})" if model and model != agent else ""
        return f"{agent}{label} · in flight"
    if error:
        return f"{agent} · failed · {error}"
    if parsed_ok:
        return f"{agent} · parsed ok" + (f" · {validation}" if validation and validation != "ok" else "")
    return f"{agent} · validation failed" + (f" · {validation}" if validation else "")


def _feed_agent_state(row: dict[str, Any]) -> str:
    if row.get("error"):
        return "failed"
    if row.get("latency_ms") is None:
        return "running"
    if row.get("parsed_ok"):
        return "done"
    return "failed"


def _feed_pipeline_line(row: dict[str, Any]) -> str:
    stage = row.get("stage") or "pipeline"
    detail = row.get("detail")
    status = row.get("status")
    if detail:
        return f"{stage}: {detail}"
    return f"{stage}: {status or 'unknown'}"


def _feed_pipeline_state(row: dict[str, Any]) -> str:
    status = row.get("status")
    if status is None:
        return "running"
    if status in ("fail", "error"):
        return "failed"
    return "done"


@app.get("/api/desk/feed")
def desk_feed(date: str | None = Query(default=None)) -> dict[str, Any]:
    """F1: server-composed activity-stream events for the DESK tab, built from
    scan_agent_logs (agent/model calls) + pipeline_runs (stage runs) for one
    run_date. Reverse-chronological. AD5 worker states: done|failed|running."""
    run_date = date or _today()
    conn = db.connect()
    try:
        log_rows = conn.execute(
            "SELECT log_id, run_date, agent, model, prompt_sha, latency_ms, tokens_in, "
            "tokens_out, parsed_ok, validation, error, created_at FROM scan_agent_logs "
            "WHERE run_date = ? ORDER BY log_id",
            (run_date,),
        ).fetchall()
        pipeline_rows = conn.execute(
            "SELECT run_id, run_date, stage, source, status, rows_affected, duration_s, "
            "detail, ran_at FROM pipeline_runs WHERE run_date = ? ORDER BY run_id",
            (run_date,),
        ).fetchall()
    finally:
        conn.close()

    events: list[dict[str, Any]] = []
    for r in log_rows:
        row = dict(r)
        events.append(
            {
                "ts": row.get("created_at"),
                "actor": row.get("agent"),
                "state": _feed_agent_state(row),
                "line": _feed_agent_line(row),
                "expand": row,
            }
        )
    for r in pipeline_rows:
        row = dict(r)
        events.append(
            {
                "ts": row.get("ran_at"),
                "actor": row.get("stage"),
                "state": _feed_pipeline_state(row),
                "line": _feed_pipeline_line(row),
                "expand": row,
            }
        )
    events.sort(key=lambda e: (e["ts"] or "", ), reverse=True)
    return {"run_date": run_date, "events": events}


def _parse_lens_scores(raw: Any) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except (TypeError, ValueError):
        return {}


def _desk_funnel(conn, scan_date: str, shortlist_count: int, debated_count: int) -> dict[str, Any]:
    """F5: {universe, screeners, gates, shortlist, by_gate} — reuses the
    /api/setups/refusals internals (refusals table, grouped by failed_gate)
    plus the shortlist/debated counts the debate endpoint already has.

    SHIP-1 #12: `refusals` already stores at most one row per (scan_date,
    symbol) — scan_candidates_deterministic() calls `_refuse()` exactly once
    per symbol then `continue`s, so `failed_gate` is already the single,
    exclusive, first-failed gate (cascade order: tradability [universe->
    screeners->gates boundary] before the named gates [regime/trend-template/
    fresh-leg/participation/risk], which fire only after tradability passes).
    The bug was in aggregation, not attribution: `by_gate` mixed the
    tradability count (a Screeners->Gates drop) in with the named-gate counts
    (Gates->Shortlist drops), so a caption summing `by_gate` summed to
    Screeners->Shortlist, not Gates->Shortlist. Fixed by splitting tradability
    into its own `screener_drop` field and keeping `by_gate` gate-stage-only,
    so sum(by_gate.values()) == gates - shortlist by construction."""
    scanner_candidates.ensure_refusals_schema(conn)
    universe_row = conn.execute(
        "SELECT COUNT(DISTINCT symbol) AS n FROM daily_prices WHERE series = 'EQ' AND trade_date = ("
        "  SELECT MAX(trade_date) FROM daily_prices WHERE series = 'EQ' AND trade_date <= ?)",
        (scan_date,),
    ).fetchone()
    universe = int(universe_row["n"]) if universe_row and universe_row["n"] is not None else 0
    counts = conn.execute(
        "SELECT failed_gate, COUNT(*) AS n FROM refusals WHERE scan_date = ? "
        "GROUP BY failed_gate ORDER BY n DESC",
        (scan_date,),
    ).fetchall()
    all_by_gate = {r["failed_gate"]: r["n"] for r in counts}
    screener_drop = all_by_gate.get("tradability", 0)
    by_gate = {k: v for k, v in all_by_gate.items() if k != "tradability"}
    total_refused = sum(all_by_gate.values())
    screeners = shortlist_count + total_refused
    gates = screeners - screener_drop
    # SHIP-3 #1: `screener_drop` (tradability) is a Screeners->Gates drop, not
    # a Universe->Screeners drop -- it fires on symbols already inside the
    # screener/detector pool (`pool_symbols` in scanner/candidates.py). The
    # Universe->Screeners arrow has its own, separate drop: symbols priced in
    # the EQ universe that day but never picked up by ANY screener hit or
    # technical detector, so they never even entered the scan cascade (no
    # refusals row is ever written for them -- they are not "filtered", they
    # were simply never selected for scanning). Surfacing this as its own
    # honest field keeps every arrow's drop = difference of adjacent stage
    # numbers, with no unexplained gap.
    no_hit_drop = max(universe - screeners, 0)
    return {
        "universe": universe,
        "screeners": screeners,
        "gates": gates,
        "shortlist": shortlist_count,
        "debated": debated_count,
        "no_hit_drop": no_hit_drop,
        "screener_drop": screener_drop,
        "by_gate": by_gate,
    }


@app.get("/api/desk/debate")
def desk_debate(date: str | None = Query(default=None)) -> dict[str, Any]:
    """F2: per-symbol debate theater payload — chair/model/vision/sizer rows,
    plan numbers, base rate, and track-record chips for one scan_date.
    F5: adds per-symbol gates (scan_candidates.gates_json) and a funnel block
    (universe -> screeners -> gates -> shortlist -> debated)."""
    scan_date = date or _today()
    conn = db.connect()
    try:
        verdict_rows = [
            dict(r)
            for r in conn.execute(
                "SELECT scan_date, symbol, agent, verdict, conviction, rank, "
                "lens_scores_json, bull_case, bear_case, reasoning, outcome_r "
                "FROM agent_verdicts WHERE scan_date = ? ORDER BY symbol",
                (scan_date,),
            ).fetchall()
        ]
        if not verdict_rows:
            return {"available": False, "scan_date": scan_date, "symbols": []}

        candidate_rows = {
            r["symbol"]: dict(r)
            for r in conn.execute(
                "SELECT symbol, setup_family, entry, stop, target, rr, suggested_qty, gates_json "
                "FROM scan_candidates WHERE scan_date = ?",
                (scan_date,),
            ).fetchall()
        }
        # SHIP-2 #4: near-miss debate rows (chair verdict exists, but the
        # symbol never cleared every gate so it has no scan_candidates row)
        # would otherwise render as an empty shell — null family/plan/gates
        # next to a populated gate-passed card. refusals already carries the
        # setup_family + failed_gate + reason a near-miss was tagged with;
        # surface it as a fact-only "why" chip. No plan/base-rate is invented
        # for these symbols — they were never priced as tradeable.
        scanner_candidates.ensure_refusals_schema(conn)
        refusal_rows = {
            r["symbol"]: dict(r)
            for r in conn.execute(
                "SELECT symbol, setup_family, failed_gate, reason FROM refusals "
                "WHERE scan_date = ?",
                (scan_date,),
            ).fetchall()
        }
        regime_row = conn.execute(
            "SELECT market_mode FROM regime_snapshots WHERE snapshot_date <= ? "
            "ORDER BY snapshot_date DESC LIMIT 1",
            (scan_date,),
        ).fetchone()
        regime_mode = regime_row["market_mode"] if regime_row else None

        track_rows = conn.execute(
            "WITH families AS ("
            "  SELECT scan_date, symbol, MIN(setup_family) AS family "
            "  FROM scan_candidates GROUP BY scan_date, symbol"
            ") "
            "SELECT av.agent, COALESCE(f.family, 'unknown') AS family, "
            "COUNT(*) AS n, "
            "SUM(CASE WHEN av.outcome_r >= 1.0 THEN 1 ELSE 0 END) AS hits, "
            "AVG(av.outcome_r) AS avg_r "
            "FROM agent_verdicts av "
            "LEFT JOIN families f ON f.scan_date = av.scan_date AND f.symbol = av.symbol "
            "WHERE av.outcome_r IS NOT NULL "
            "GROUP BY av.agent, COALESCE(f.family, 'unknown')"
        ).fetchall()
        track_by_agent_family: dict[tuple[str, str], dict[str, Any]] = {}
        for r in track_rows:
            n = int(r["n"] or 0)
            hits = int(r["hits"] or 0)
            track_by_agent_family[(r["agent"], r["family"])] = {
                "agent": r["agent"],
                "family": r["family"],
                "n": n,
                "hit_rate": (hits / n) if n else None,
                "avg_r": r["avg_r"],
                "thin": n < 5,
            }

        by_symbol: dict[str, list[dict[str, Any]]] = {}
        for row in verdict_rows:
            by_symbol.setdefault(row["symbol"], []).append(row)

        base_rate_cache: dict[str, Any] = {}
        symbols: list[dict[str, Any]] = []
        for symbol, rows in by_symbol.items():
            chair = next((r for r in rows if r["agent"] == "chair"), None)
            vision = next((r for r in rows if r["agent"] == "vision"), None)
            sizer = next((r for r in rows if r["agent"] == "sizer"), None)
            models = [r for r in rows if r["agent"] not in ("chair", "vision", "sizer")]

            candidate = candidate_rows.get(symbol)
            refusal = refusal_rows.get(symbol)
            family = (candidate or {}).get("setup_family") or (refusal or {}).get("setup_family")
            gates = _json_col(candidate.get("gates_json") if candidate else None, [])

            plan = None
            if candidate:
                plan = {
                    "entry": candidate.get("entry"),
                    "stop": candidate.get("stop"),
                    "target": candidate.get("target"),
                    "rr": candidate.get("rr"),
                    "suggested_qty": candidate.get("suggested_qty"),
                }

            near_miss = None
            if not candidate and refusal:
                near_miss = {
                    "failed_gate": refusal.get("failed_gate"),
                    "reason": refusal.get("reason"),
                }

            # SHIP-2 #4: base rate is a tradeable-candidate stat (expectancy
            # of names that actually cleared gates) — never invent it for a
            # near-miss that was never priced as tradeable.
            base_rate = None
            if candidate and family and regime_mode:
                cache_key = f"{family}|{regime_mode}"
                if cache_key not in base_rate_cache:
                    base_rate_cache[cache_key] = scanner_expectancy.chip_for(conn, family, regime_mode)
                base_rate = base_rate_cache[cache_key]

            # SHIP-1 #7: ML direction P(up 10d) — EXPERIMENTAL, read-only fact
            # chip. Never influences chair/sizer/base_rate above.
            ml_row = conn.execute(
                "SELECT p_up_10d, top_drivers_json FROM ml_scores WHERE scan_date=? AND symbol=?",
                (scan_date, symbol),
            ).fetchone()
            ml = None
            if ml_row is not None and ml_row["p_up_10d"] is not None:
                ml = {
                    "p_up_10d": ml_row["p_up_10d"],
                    "drivers": _json_col(ml_row["top_drivers_json"], []),
                    "experimental": True,
                }

            # SHIP-1 #9: delivery% accumulation/distribution tag — fact-only
            # chip, read from features_daily (engine/indicators.py is the
            # sole writer). Lift validation is pending; never claims edge.
            delivery = None
            feat_row = conn.execute(
                "SELECT feature_json FROM features_daily WHERE symbol=? AND trade_date<=? "
                "ORDER BY trade_date DESC LIMIT 1",
                (symbol, scan_date),
            ).fetchone()
            if feat_row is not None and feat_row["feature_json"]:
                bag = _json_col(feat_row["feature_json"], {})
                flag = bag.get("delivery_flag")
                if flag in ("ACCUMULATION", "DISTRIBUTION"):
                    delivery = {"flag": flag}

            # Per-stock 3-state HMM regime read (EXPERIMENTAL) — same fact
            # surfaced in the chart drawer pane; consolidated here so the
            # debate card's AI SIGNALS block doesn't require opening the
            # chart to see it. CACHE-ONLY read (never fits here) so this
            # list endpoint stays fast for many symbols; the fit itself
            # only ever runs from the chart drawer's own request or the
            # nightly context_pack build (both call get_or_compute).
            stock_hmm_chip = None
            try:
                hmm_payload = stock_hmm.get_cached(conn, symbol, scan_date)
            except Exception:
                hmm_payload = None
            if hmm_payload and hmm_payload.get("available"):
                current = hmm_payload.get("current") or {}
                stock_hmm_chip = {
                    "state": current.get("state"),
                    "confidence": current.get("confidence"),
                    "line": stock_hmm.summary_line(hmm_payload),
                }

            agents_present = {r["agent"] for r in rows}
            track_record = [
                v
                for (agent, fam), v in track_by_agent_family.items()
                if agent in agents_present and fam == (family or "unknown")
            ]

            chair_lens = _parse_lens_scores(chair.get("lens_scores_json")) if chair else {}
            sizer_lens = _parse_lens_scores(sizer.get("lens_scores_json")) if sizer else {}

            symbols.append(
                {
                    "symbol": symbol,
                    "family": family,
                    "chair": (
                        {
                            "verdict": chair.get("verdict"),
                            "conviction": chair.get("conviction"),
                            "rank": chair.get("rank"),
                            "reasoning": chair.get("reasoning"),
                            "struck": bool(chair.get("verdict") == "SKIP" and "struck" in (chair.get("reasoning") or "").lower()),
                            "disagreement": chair_lens.get("disagreement"),
                            "conviction_spread": chair_lens.get("conviction_spread"),
                        }
                        if chair
                        else None
                    ),
                    "models": [
                        {
                            "agent": m.get("agent"),
                            "verdict": m.get("verdict"),
                            "conviction": m.get("conviction"),
                            "bull_case": m.get("bull_case"),
                            "bear_case": m.get("bear_case"),
                            "reasoning": m.get("reasoning"),
                        }
                        for m in models
                    ],
                    "vision": (
                        {
                            "verdict": vision.get("verdict"),
                            "reasoning": vision.get("reasoning"),
                        }
                        if vision
                        else None
                    ),
                    "sizer": (
                        {
                            "verdict": sizer.get("verdict"),
                            "multiplier": sizer_lens.get("multiplier"),
                            "final_qty": sizer_lens.get("final_qty"),
                            "reasoning": sizer.get("reasoning"),
                        }
                        if sizer
                        else None
                    ),
                    "plan": plan,
                    "base_rate": base_rate,
                    "ml": ml,
                    "delivery": delivery,
                    "stock_hmm": stock_hmm_chip,
                    "track_record": track_record,
                    "gates": gates,
                    "near_miss": near_miss,
                    "_rank": (chair or {}).get("rank") if chair and chair.get("rank") is not None else 9999,
                }
            )

        symbols.sort(key=lambda s: (s.pop("_rank"), s["symbol"]))
        funnel = _desk_funnel(conn, scan_date, len(candidate_rows), len(by_symbol))
        return {
            "available": True,
            "scan_date": scan_date,
            "regime_mode": regime_mode,
            "symbols": symbols,
            "funnel": funnel,
        }
    finally:
        conn.close()


def _position_thesis(read: dict[str, Any]) -> dict[str, Any]:
    thesis = read.get("original_thesis") or {}
    rows = thesis.get("rows") if isinstance(thesis, dict) else None
    if not rows:
        return {"note": "no agent thesis"}
    # Prefer a model's own bull case for the quote (the wireframe attributes the
    # thesis to a named model, e.g. "ORIGINAL THESIS (Nemotron, Jul 3)"); fall
    # back to the chair row when only a chair verdict exists near the trade date.
    model_row = next((r for r in rows if r.get("agent") != "chair"), rows[0])
    return {
        "agent": model_row.get("agent"),
        "scan_date": thesis.get("scan_date"),
        "conviction": model_row.get("conviction"),
        "bull_case": model_row.get("bull_case") or model_row.get("reasoning"),
    }


POSITION_CLOSE_REASONS = {"target", "stop-hit", "fear", "need-cash", "thesis-change", "other"}


def _positive_float(value: Any, field: str, *, allow_zero: bool = False) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        raise HTTPException(400, f"{field} must be a number") from None
    if out < 0 or (out == 0 and not allow_zero):
        raise HTTPException(400, f"{field} must be positive")
    return out


def _parse_iso_date(value: Any, field: str) -> str:
    text = str(value or "").strip()
    try:
        _date.fromisoformat(text)
    except ValueError:
        raise HTTPException(400, f"{field} must be YYYY-MM-DD") from None
    return text


def _open_position_row(conn, trade_id: int):
    _ensure_journal_table(conn)
    row = conn.execute(
        "SELECT trade_id, trade_date, symbol, setup, entry, stop, qty, first_exit_flag_date, notes "
        "FROM journal_trades WHERE trade_id = ? AND exit IS NULL",
        (trade_id,),
    ).fetchone()
    if not row:
        raise HTTPException(404, "open position not found")
    return row


def _realized_r(entry: Any, stop: Any, exit_price: Any) -> float | None:
    if entry is None or stop is None or exit_price is None:
        return None
    risk = float(entry) - float(stop)
    if risk <= 0:
        return None
    return round((float(exit_price) - float(entry)) / risk, 4)


def _days_held(trade_date: Any, as_of: str) -> int | None:
    try:
        return market_calendar.trading_days_between(_date.fromisoformat(str(trade_date)), _date.fromisoformat(as_of))
    except (TypeError, ValueError):
        return None


@app.get("/api/desk/positions")
def desk_positions(date: str | None = Query(default=None)) -> dict[str, Any]:
    """F3: open journal positions — deterministic coach read (trail_plan phase/
    action/trail_stop, two_strike fired/exit_now), server-computed R-path series
    (per-session R from entry using daily closes, all <= date), the original
    agent thesis quoted from agent_verdicts, and the latest coach/telegram
    mirror signal. Reuses coach._deterministic_read/_open_trades so the
    lifecycle read here can never drift from the exit engine's own verdict."""
    from manas_os.advisor.advisor import ensure_schema as _ensure_advisor_schema

    run_date = date or _today()
    conn = db.connect()
    try:
        _ensure_journal_table(conn)
        agents_coach.signals.ensure_schema(conn)
        _ensure_advisor_schema(conn)
        trade_rows = agents_coach._open_trades(conn)
        positions: list[dict[str, Any]] = []
        for row in trade_rows:
            read = agents_coach._deterministic_read(conn, row, run_date)
            entry = row["entry"]
            stop = row["stop"]
            risk = (float(entry) - float(stop)) if entry is not None and stop is not None else None

            r_path: list[dict[str, Any]] = []
            if risk and risk > 0:
                bars = agents_coach._load_symbol_bars(conn, row["symbol"], run_date, 250)
                for bar in bars:
                    bar_date = bar.get("date")
                    close = bar.get("close")
                    if bar_date is None or close is None:
                        continue
                    if bar_date < row["trade_date"] or bar_date > run_date:
                        continue
                    r_path.append({"date": bar_date, "r": round((float(close) - float(entry)) / risk, 3)})

            coach_row = conn.execute(
                "SELECT message, sent, created_at FROM agent_signals "
                "WHERE symbol = ? AND channel = 'coach' AND scan_date <= ? "
                "ORDER BY scan_date DESC, created_at DESC LIMIT 1",
                (str(row["symbol"]).upper(), run_date),
            ).fetchone()
            advisor_note_row = conn.execute(
                "SELECT note, note_date FROM advisor_notes "
                "WHERE symbol = ? AND scope = 'exit' AND note_date <= ? "
                "ORDER BY note_date DESC LIMIT 1",
                (str(row["symbol"]).upper(), run_date),
            ).fetchone()

            if read is None:
                read = {
                    "symbol": str(row["symbol"]).upper(),
                    "setup_family": agents_coach._setup_family_for_trade(row),
                    "phase": None,
                    "action": None,
                    "action_line": None,
                    "trail_stop": None,
                    "r": None,
                    "verdict": None,
                    "fired": [],
                    "exit_now": False,
                    "banner": None,
                    "original_thesis": agents_coach._original_thesis(conn, str(row["symbol"]).upper(), row["trade_date"]),
                }

            positions.append(
                {
                    "trade_id": row["trade_id"],
                    "symbol": read["symbol"],
                    "trade_date": row["trade_date"],
                    "entry": entry,
                    "stop": stop,
                    "qty": row["qty"] if "qty" in row.keys() else None,
                    "setup": row["setup"],
                    "setup_family": read["setup_family"],
                    "phase": read["phase"],
                    "action": read["action"],
                    "action_line": read["action_line"],
                    "trail_stop": read["trail_stop"],
                    "r": read["r"],
                    "coach_verdict": read["verdict"],
                    "todays_stop": read["trail_stop"] if read["trail_stop"] is not None else stop,
                    "plain_why": read["action_line"],
                    # LLM narrative persisted by agents/coach.py into advisor_notes
                    # (scope=exit); null on nights the LLM didn't run/parse, in
                    # which case the UI falls back to plain_why (deterministic).
                    "advisor_note": advisor_note_row["note"] if advisor_note_row else None,
                    "days_held": _days_held(row["trade_date"], run_date),
                    "open_r": read["r"],
                    "r_path": r_path,
                    "fired": read["fired"],
                    "exit_now": read["exit_now"],
                    "urgent": bool(read["exit_now"]),
                    "banner": read["banner"],
                    "original_thesis": _position_thesis(read),
                    "coach": (
                        {
                            "message": coach_row["message"],
                            "sent": bool(coach_row["sent"]),
                            "created_at": coach_row["created_at"],
                        }
                        if coach_row
                        else None
                    ),
                }
            )
        return {"run_date": run_date, "positions": positions}
    finally:
        conn.close()


@app.post("/api/desk/positions")
def desk_position_add(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    symbol = str(payload.get("symbol") or "").strip().upper()
    if not re.fullmatch(r"[A-Z0-9&.-]{1,24}", symbol):
        raise HTTPException(400, "symbol is required")
    trade_date = _parse_iso_date(payload.get("date") or payload.get("trade_date"), "date")
    entry = _positive_float(payload.get("entry"), "entry")
    stop = _positive_float(payload.get("stop"), "stop")
    qty = _positive_float(payload.get("qty"), "qty")
    if stop >= entry:
        raise HTTPException(400, "stop must be below entry for long positions")
    setup = str(payload.get("setup") or "manual").strip() or "manual"
    conn = db.connect()
    try:
        _ensure_journal_table(conn)
        cur = conn.execute(
            "INSERT INTO journal_trades "
            "(trade_date, symbol, setup, entry, stop, qty, exit, mistake_tags_json, notes) "
            "VALUES (?, ?, ?, ?, ?, ?, NULL, '[]', 'manual position')",
            (trade_date, symbol, setup, entry, stop, qty),
        )
        conn.commit()
        return {"ok": True, "trade_id": cur.lastrowid}
    finally:
        conn.close()


@app.post("/api/desk/positions/{trade_id}/update")
def desk_position_update(trade_id: int, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    allowed = {"stop", "qty"}
    if not any(k in payload for k in allowed):
        raise HTTPException(400, "stop or qty is required")
    updates: list[str] = []
    params: list[Any] = []
    new_stop = None
    if "stop" in payload:
        new_stop = _positive_float(payload.get("stop"), "stop")
        updates.append("stop = ?")
        params.append(new_stop)
    if "qty" in payload:
        updates.append("qty = ?")
        params.append(_positive_float(payload.get("qty"), "qty", allow_zero=True))
    conn = db.connect()
    try:
        row = _open_position_row(conn, trade_id)
        if new_stop is not None and row["entry"] is not None and new_stop >= float(row["entry"]):
            raise HTTPException(400, "stop must be below entry for long positions")
        params.append(trade_id)
        conn.execute(f"UPDATE journal_trades SET {', '.join(updates)} WHERE trade_id = ? AND exit IS NULL", params)
        conn.commit()
        updated = _open_position_row(conn, trade_id)
        return {"ok": True, "trade_id": trade_id, "stop": updated["stop"], "qty": updated["qty"]}
    finally:
        conn.close()


@app.post("/api/desk/positions/{trade_id}/close")
def desk_position_close(trade_id: int, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    exit_price = _positive_float(payload.get("exit_price"), "exit_price")
    reason_tag = str(payload.get("reason_tag") or "").strip()
    if reason_tag not in POSITION_CLOSE_REASONS:
        raise HTTPException(400, "reason_tag must be one of target/stop-hit/fear/need-cash/thesis-change/other")
    exit_date = _parse_iso_date(payload.get("date") or _today(), "date")
    conn = db.connect()
    try:
        row = _open_position_row(conn, trade_id)
        r_result = _realized_r(row["entry"], row["stop"], exit_price)
        tags = json.dumps([reason_tag])
        # Append to notes — the row may carry entry-time notes worth keeping.
        prior_notes = (row["notes"] or "").strip() if "notes" in row.keys() else ""
        close_note = f"closed from positions: {reason_tag}"
        notes = f"{prior_notes} | {close_note}" if prior_notes else close_note
        conn.execute(
            "UPDATE journal_trades SET exit = ?, exit_date = ?, r_result = ?, "
            "mistake_tags_json = ?, notes = ? WHERE trade_id = ? AND exit IS NULL",
            (exit_price, exit_date, r_result, tags, notes, trade_id),
        )
        conn.commit()
        return {"ok": True, "trade_id": trade_id, "exit": exit_price, "exit_date": exit_date, "reason_tag": reason_tag, "r_result": r_result}
    finally:
        conn.close()


def _index_spark(conn, symbol: str, on_or_before: str, n: int = 30) -> list[float | None]:
    """Last `n` closes for `symbol` up to `on_or_before`, oldest first."""
    rows = conn.execute(
        "SELECT close FROM sector_index_prices "
        "WHERE symbol = ? AND trade_date <= ? AND close IS NOT NULL "
        "ORDER BY trade_date DESC LIMIT ?",
        (symbol, on_or_before, n),
    ).fetchall()
    return [_round(r["close"]) for r in reversed(rows)]


def _sector_num_stocks(conn, sec_date: str | None) -> dict[str, int]:
    """sector_key -> a stock-count proxy for treemap sizing (V2).

    sector_metrics has no literal per-sector universe stock count column (only
    breadth/RS/setup counts); the closest honest "how much is going on in this
    sector" figure it does carry is total ChartsMaze setup count
    (setup_count_a+b+c). Used only for relative treemap area, not displayed as
    a claimed universe count. Empty dict when no sector_metrics snapshot."""
    if sec_date is None:
        return {}
    rows = conn.execute(
        "SELECT sector_key, "
        "COALESCE(setup_count_a, 0) + COALESCE(setup_count_b, 0) + COALESCE(setup_count_c, 0) AS n "
        "FROM sector_metrics WHERE snapshot_date = ?",
        (sec_date,),
    ).fetchall()
    return {r["sector_key"]: max(int(r["n"]), 1) for r in rows}


def _stock_movers_and_delivery(conn, on_or_before: str, limit: int = 8) -> dict[str, Any]:
    """G3 bug fix: the MARKET tab's "movers"/"big delivery" panels were built
    from index/sector rows (see `_market_movers` below) — never actual
    stocks, which is what the user meant by "movers" and "big delivery".
    This pulls real STOCK rows from `daily_prices` (EQ series only, joined
    to `universe` for a display name + tradeable filter) for the latest
    priced date on/before `on_or_before`: 1D %chg gainers/losers, and a
    separate delivery% leaderboard. Empty lists (not an error) when
    daily_prices has nothing yet for this date."""
    stock_date = _latest_price_date(conn, on_or_before)
    if stock_date is None:
        return {"gainers": [], "losers": [], "big_delivery": []}

    rows = conn.execute(
        "SELECT dp.symbol AS symbol, u.name AS name, dp.close AS close, "
        "dp.prev_close AS prev_close, dp.volume AS volume, dp.delivery_pct AS delivery_pct "
        "FROM daily_prices dp "
        "LEFT JOIN universe u ON u.symbol = dp.symbol AND u.as_of_date = ("
        "  SELECT MAX(as_of_date) FROM universe WHERE as_of_date <= ?"
        ") "
        "WHERE dp.series = 'EQ' AND dp.trade_date = ? "
        "AND dp.prev_close IS NOT NULL AND dp.prev_close > 0 "
        "AND dp.close IS NOT NULL "
        "AND (u.is_tradeable IS NULL OR u.is_tradeable = 1)",
        (stock_date, stock_date),
    ).fetchall()

    # The universe table can be empty (it is on live DBs), so the join alone
    # can't exclude funds — ETFs/gilt funds trade as EQ series too (GSEC10ABSL,
    # LOWVOL, MAFANG all leaked into "big delivery"). Reuse the engine's
    # one-writer ETF heuristic instead of a second keyword list here.
    from manas_os.engine.universe_filter import is_probable_etf

    priced = []
    for r in rows:
        if is_probable_etf(r["symbol"]):
            continue
        # Turnover floor (₹1cr) — fund units the keyword heuristic misses trade
        # a few hundred shares a day; no genuine "mover" is this illiquid.
        if (r["close"] or 0) * (r["volume"] or 0) < 1e7:
            continue
        chg = (r["close"] - r["prev_close"]) / r["prev_close"] * 100.0
        priced.append({
            "symbol": r["symbol"],
            "name": r["name"] or r["symbol"],
            "close": r["close"],
            "chg_pct": round(chg, 2),
            "delivery_pct": r["delivery_pct"],
            "volume": r["volume"],
        })

    ranked = sorted(priced, key=lambda r: r["chg_pct"], reverse=True)
    gainers = ranked[:limit]
    losers = list(reversed(ranked))[:limit]

    # ~100% delivery is the ETF/fund-unit signature (creation-unit settlement),
    # not accumulation — MON100/PVTBANKADD style units slip past the keyword
    # heuristic but always print >=99.5%.
    deliverable = [
        r for r in priced if r["delivery_pct"] is not None and r["delivery_pct"] < 99.5
    ]
    big_delivery = sorted(deliverable, key=lambda r: r["delivery_pct"], reverse=True)[:limit]

    return {"as_of": stock_date, "gainers": gainers, "losers": losers, "big_delivery": big_delivery}


def _market_movers(
    conn, sector_rows: list[dict[str, Any]], ind_date: str | None, on_or_before: str
) -> dict[str, Any]:
    """d1/w1/m1 -> {sectors_up[5], sectors_down[5], themes_up[5]} using the
    already-computed sector_index_prices returns (SECTORAL-classified indices
    only — broad ladders and thematic/strategy/factor indices excluded) and
    the industry_metrics leaderboard for the same tf key."""
    sector_only = [r for r in sector_rows if classify_index(r["symbol"]) == "SECTORAL"]
    sec_date = _most_recent_snapshot(conn, "sector_metrics", on_or_before)
    num_stocks_by_key = _sector_num_stocks(conn, sec_date)
    for r in sector_only:
        sector_key = canonical_sector_key(r["symbol"], "index")
        r["sector_key"] = sector_key
        r["num_stocks"] = num_stocks_by_key.get(sector_key)

    industries: list[dict[str, Any]] = []
    if ind_date is not None:
        rows = conn.execute(
            "SELECT name, perf_1d, perf_1w, perf_1m, num_stocks "
            "FROM industry_metrics WHERE snapshot_date = ?",
            (ind_date,),
        ).fetchall()
        industries = [dict(r) for r in rows]

    tf_map = {"d1": ("1d", "perf_1d"), "w1": ("1w", "perf_1w"), "m1": ("1m", "perf_1m")}
    out: dict[str, Any] = {}
    for mover_key, (ret_key, ind_perf_key) in tf_map.items():
        ranked = sorted(
            (r for r in sector_only if r["returns"].get(ret_key) is not None),
            key=lambda r: r["returns"][ret_key],
            reverse=True,
        )
        sectors_up = [
            {
                "name": r["name"], "symbol": r["symbol"], "move_pct": r["returns"][ret_key],
                "num_stocks": r.get("num_stocks"),
            }
            for r in ranked[:5]
        ]
        sectors_down = [
            {
                "name": r["name"], "symbol": r["symbol"], "move_pct": r["returns"][ret_key],
                "num_stocks": r.get("num_stocks"),
            }
            for r in list(reversed(ranked))[:5]
        ]
        themes_ranked = sorted(
            (r for r in industries if r.get(ind_perf_key) is not None),
            key=lambda r: r[ind_perf_key],
            reverse=True,
        )
        themes_up = [
            {"name": r["name"], "move_pct": r[ind_perf_key], "num_stocks": r.get("num_stocks")}
            for r in themes_ranked[:5]
        ]
        out[mover_key] = {"sectors_up": sectors_up, "sectors_down": sectors_down, "themes_up": themes_up}
    return out


_DEAL_QTY_KEYS = ("Quantity Traded", "Quantity", "Qty", "qty")
_DEAL_PRICE_KEYS = ("Trade Price", "Price", "price")


def _deal_first_of(detail: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for k in keys:
        v = detail.get(k)
        if v is not None and v != "":
            return v
    return None


def _deal_to_float(raw: Any) -> float | None:
    if raw is None:
        return None
    s = str(raw).strip().replace(",", "")
    if s in ("", "-", "--", "NA", "N/A", "n.a."):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _market_deals(conn, on_or_before: str, limit: int = 15) -> dict[str, Any]:
    """Latest block/bulk deals and insider trades from `disclosures`.

    SHIP-1 #14: joins symbol_quality.market_cap_cr (as-of on_or_before) to
    compute pct_of_mcap = deal value (qty x price) / (market_cap_cr x 1e7)
    x 100, where qty/price can be parsed from the deal's detail_json. Rows
    are ranked by pct_of_mcap desc; deals with no computable pct (missing
    mcap or missing qty/price) sort last, ordered by trade_date desc among
    themselves so they're still recency-useful."""
    _, quality_map = scanner_candidates.symbol_quality_map(conn, on_or_before)

    def _rows(kinds: tuple[str, ...]) -> list[dict[str, Any]]:
        placeholders = ",".join("?" for _ in kinds)
        rows = conn.execute(
            f"SELECT trade_date, symbol, kind, detail_json FROM disclosures "
            f"WHERE kind IN ({placeholders}) AND trade_date <= ? "
            f"ORDER BY trade_date DESC, symbol ASC",
            (*kinds, on_or_before),
        ).fetchall()
        out = []
        for r in rows:
            detail = _json_col(r["detail_json"], {})
            qty = _deal_to_float(_deal_first_of(detail, _DEAL_QTY_KEYS))
            price = _deal_to_float(_deal_first_of(detail, _DEAL_PRICE_KEYS))
            mcap_cr = (quality_map.get(r["symbol"]) or {}).get("market_cap_cr")
            pct_of_mcap = None
            if qty is not None and price is not None and mcap_cr:
                try:
                    mcap_cr = float(mcap_cr)
                    if mcap_cr > 0:
                        pct_of_mcap = round((qty * price) / (mcap_cr * 1e7) * 100.0, 4)
                except (TypeError, ValueError):
                    pct_of_mcap = None
            out.append({
                "trade_date": r["trade_date"],
                "symbol": r["symbol"],
                "kind": r["kind"],
                "detail": detail,
                "pct_of_mcap": pct_of_mcap,
            })
        # Null-mcap (no computable pct) sorts last; within each bucket, rank
        # by pct_of_mcap desc (present) or trade_date desc (absent).
        with_pct = [d for d in out if d["pct_of_mcap"] is not None]
        without_pct = [d for d in out if d["pct_of_mcap"] is None]
        with_pct.sort(key=lambda d: d["pct_of_mcap"], reverse=True)
        without_pct.sort(key=lambda d: d["trade_date"], reverse=True)
        return (with_pct + without_pct)[:limit]

    return {
        "block_bulk": _rows(("bulk_deal",)),
        "insider": _rows(("insider",)),
    }


def _fii_dii_payload(conn, on_or_before: str, limit: int = 10) -> dict[str, Any] | None:
    """F7: last `limit` fii_dii_daily rows on/before the date, newest first.

    Returns None (honest gap) when the table has no rows yet — e.g. the
    ingest stage hasn't run or every attempt so far has been a `skip`.
    """
    rows = conn.execute(
        "SELECT trade_date, fii_buy, fii_sell, fii_net, dii_buy, dii_sell, dii_net, source "
        "FROM fii_dii_daily WHERE trade_date <= ? ORDER BY trade_date DESC LIMIT ?",
        (on_or_before, limit),
    ).fetchall()
    if not rows:
        return None
    last_10 = [dict(r) for r in rows]
    latest = last_10[0]
    fii_net_sum = sum(r["fii_net"] for r in last_10 if r["fii_net"] is not None)
    dii_net_sum = sum(r["dii_net"] for r in last_10 if r["dii_net"] is not None)
    return {
        "latest": latest,
        "last_10": last_10,
        "net_trend": {"fii_net_sum": fii_net_sum, "dii_net_sum": dii_net_sum},
    }


@app.get("/api/desk/market")
def desk_market(
    date: str | None = Query(default=None),
    include_thematic: bool = Query(default=False),
) -> dict[str, Any]:
    """F6: MARKET tab — indices (BROAD then SECTORAL; THEMATIC_STRATEGY
    indices only when include_thematic=true — see classify_index()) w/
    D/W/M/3M returns + 30d sparklines from sector_index_prices; sector/theme
    movers from sector_metrics/industry_metrics (SECTORAL class only);
    chartsmaze_sectors (F6 taxonomy cleanup) is the raw sector_metrics
    leaderboard (RS%/breadth/MARS) — the 21 ChartsMaze sector buckets, kept
    as its own field/table so the MARKET tab never mixes them into the NSE
    index rows; stock_movers (G3) is real STOCK gainers/losers/big-delivery
    from daily_prices — fixes the movers/big-delivery panels showing index
    rows; block/bulk + insider deals from disclosures; fii_dii (F7) is
    {latest, last_10, net_trend} from fii_dii_daily, or an honest null when
    the table has no rows on/before the date. India VIX is not an index in
    this payload — it's surfaced as the top-level `vix` field."""
    on_or_before = date or _today()
    conn = db.connect()
    try:
        as_of, raw_index_rows = _index_returns(conn, on_or_before)
        if as_of is None:
            return {
                "available": False,
                "as_of": None,
                "indices": [],
                "movers": {},
                "sectors": [],
                "chartsmaze_sectors": [],
                "stock_movers": {"gainers": [], "losers": [], "big_delivery": []},
                "deals": {"block_bulk": [], "insider": []},
                "fii_dii": _fii_dii_payload(conn, on_or_before),
                "vix": None,
            }

        vix, index_rows = _extract_vix(raw_index_rows)
        classified = [(r, classify_index(r["symbol"])) for r in index_rows]
        broad_rows = [r for r, c in classified if c == "BROAD"]
        sectoral_rows = [r for r, c in classified if c == "SECTORAL"]
        thematic_rows = [r for r, c in classified if c == "THEMATIC_STRATEGY"]

        # BROAD first (BROAD_INDEX_LADDER order — matched case-insensitively,
        # since the NSE index-history backfill mixes casing across sources),
        # then any other BROAD-classified rows, then SECTORAL alphabetical,
        # then THEMATIC_STRATEGY alphabetical (only when asked for).
        by_norm = {_normalize_index_name(r["symbol"]): r for r in broad_rows}
        indices: list[dict[str, Any]] = []
        seen: set[str] = set()
        for symbol, label in BROAD_INDEX_LADDER:
            row = by_norm.get(_normalize_index_name(symbol))
            if row is None:
                continue
            indices.append({**row, "name": label, "class": "BROAD", "spark": _index_spark(conn, row["symbol"], as_of)})
            seen.add(row["symbol"])
        for row in sorted(broad_rows, key=lambda r: r["name"]):
            if row["symbol"] in seen:
                continue
            indices.append({**row, "class": "BROAD", "spark": _index_spark(conn, row["symbol"], as_of)})
            seen.add(row["symbol"])
        sector_downside_by_key = _sector_downside_by_key(conn, on_or_before)
        for row in sorted(sectoral_rows, key=lambda r: r["name"]):
            downside = sector_downside_by_key.get(canonical_sector_key(row["symbol"], "index"))
            indices.append({
                **row, "class": "SECTORAL", "spark": _index_spark(conn, row["symbol"], as_of),
                "p_drawdown_5d": downside["p_drawdown_5d"] if downside else None,
            })
        if include_thematic:
            for row in sorted(thematic_rows, key=lambda r: r["name"]):
                indices.append({**row, "class": "THEMATIC_STRATEGY", "spark": _index_spark(conn, row["symbol"], as_of)})

        ind_date = _most_recent_snapshot(conn, "industry_metrics", on_or_before)
        movers = _market_movers(conn, index_rows, ind_date, on_or_before)
        stock_movers = _stock_movers_and_delivery(conn, on_or_before)
        deals = _market_deals(conn, on_or_before)

        # V2 treemap: SECTORAL-classified indices only, with the num_stocks
        # proxy attached by _market_movers's mutation of index_rows.
        sectors = [
            {
                "name": r["name"],
                "symbol": r["symbol"],
                "sector_key": r.get("sector_key"),
                "move_pct": r["returns"].get("1d"),
                "num_stocks": r.get("num_stocks"),
            }
            for r in sectoral_rows
        ]
        _, chartsmaze_sectors = _sector_metrics_rows(conn, on_or_before)

        return {
            "available": True,
            "as_of": as_of,
            "timeframes": ["1d", "1w", "1m", "3m"],
            "indices": indices,
            "movers": movers,
            "sectors": sectors,
            "chartsmaze_sectors": chartsmaze_sectors,
            "stock_movers": stock_movers,
            "deals": deals,
            "fii_dii": _fii_dii_payload(conn, on_or_before),
            "vix": vix,
        }
    finally:
        conn.close()


@app.get("/api/desk/latest")
def desk_latest() -> dict[str, Any]:
    """Most recent completed night — so the desk opens ON data, not on
    today's (usually empty) date. latest_run_card_date is the max date with
    a written run_card.json (data/run_cards/*.json); latest_scan_date is the
    max scan_date in scan_candidates (verdicts live under the scan date, so
    this is the fallback when no run_card has been written yet). Both are
    None when neither source has anything — caller falls back to today."""
    from manas_os.agents import run_card as run_card_module

    latest_run_card_date = None
    root = run_card_module.RUN_CARD_ROOT
    if root.is_dir():
        # Skip no_op cards (nights with no fresh scan) — the desk should open
        # on the last night that actually happened, not a phantom "today".
        dates = []
        for p in sorted(root.glob("*.json"), reverse=True):
            try:
                if json.loads(p.read_text(encoding="utf-8")).get("no_op"):
                    continue
            except (OSError, json.JSONDecodeError):
                continue
            dates.append(p.stem)
        latest_run_card_date = max(dates) if dates else None

    conn = db.connect()
    try:
        row = conn.execute("SELECT MAX(scan_date) AS d FROM scan_candidates").fetchone()
        latest_scan_date = row["d"] if row and row["d"] else None
    finally:
        conn.close()

    return {
        "latest_run_card_date": latest_run_card_date,
        "latest_scan_date": latest_scan_date,
    }


@app.get("/api/desk/watchlist")
def desk_watchlist(date: str | None = Query(default=None)) -> dict[str, Any]:
    """G1: the living agent watchlist — every debated symbol's PROMOTE/HOLD/
    DEMOTE/DROP status vs the previous debated night, joined with tonight's
    chair verdict/conviction. Honest empty-state when nothing has been
    computed yet for this date (no fabricated rows)."""
    scan_date = date or _today()
    conn = db.connect()
    try:
        # Live DBs predate the agent_watchlist table until the first agents
        # night runs — that's an honest empty state, not a 500.
        if conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='agent_watchlist'"
        ).fetchone() is None:
            return {"available": False, "scan_date": scan_date, "rows": []}
        rows = conn.execute(
            "SELECT wl.scan_date, wl.symbol, wl.tier, wl.status, wl.prev_status, wl.reason, "
            "ch.verdict AS chair_verdict, ch.conviction AS conviction "
            "FROM agent_watchlist wl "
            "LEFT JOIN agent_verdicts ch "
            "  ON ch.scan_date = wl.scan_date AND ch.symbol = wl.symbol AND ch.agent = 'chair' "
            "WHERE wl.scan_date = ? "
            "ORDER BY CASE wl.status WHEN 'PROMOTE' THEN 0 WHEN 'HOLD' THEN 1 "
            "WHEN 'DEMOTE' THEN 2 WHEN 'DROP' THEN 3 ELSE 4 END, wl.symbol",
            (scan_date,),
        ).fetchall()
        if not rows:
            return {"available": False, "scan_date": scan_date, "rows": []}
        return {
            "available": True,
            "scan_date": scan_date,
            "rows": [
                {
                    "symbol": r["symbol"],
                    "tier": r["tier"],
                    "status": r["status"],
                    "prev_status": r["prev_status"],
                    "reason": r["reason"],
                    "chair_verdict": r["chair_verdict"],
                    "conviction": r["conviction"],
                }
                for r in rows
            ],
        }
    finally:
        conn.close()
