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

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from manas_os import config, db, market_calendar
from manas_os.alerts import eod as eod_alerts
from manas_os.regime import snapshot as regime_snapshot
from manas_os.regime.governor import governor
from manas_os.engine import eod_detectors, pine_ports, price_action
from manas_os.regime.sectors import INDUSTRY_TO_SECTOR, canonical_sector_key, display_label, industries_for_sector
from manas_os.scanner import candidates as scanner_candidates
from manas_os.scanner import expectancy as scanner_expectancy
from manas_os.scanner import mentor_checklists
from manas_os.scanner import outcomes as scanner_outcomes
from manas_os.sources import chartsmaze

app = FastAPI(title="Manas AI Trading OS", version="0.0.1")

# Single-user, local-first: dev runs Vite on :5173 and this API on :8000, so
# allow the Vite origin. GET for reads; POST is needed for the Fyers login
# flow (credentials + auth-code exchange). Single-user localhost only.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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
        sec_date = _most_recent_snapshot(conn, "sector_metrics", on_or_before)
        ind_date = _most_recent_snapshot(conn, "industry_metrics", on_or_before)
        if sec_date is None and ind_date is None:
            return {"available": False, "as_of": None, "sectors": [], "industries": []}

        sectors = []
        if sec_date is not None:
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
        conn.execute(
            "INSERT OR REPLACE INTO avwap_anchors (symbol, as_of, anchor_date, anchor_type, reason) "
            "VALUES (?, ?, ?, ?, ?)",
            (sym, bars[-1]["date"], avwap.get("anchor_date"), avwap.get("anchor_type"), avwap.get("reason")),
        )
        conn.commit()
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
        items = []
        for row in rows:
            timing = _symbol_timing(conn, row["symbol"], on_or_before)
            exit_payload = _symbol_exit_state(conn, row["symbol"], on_or_before)
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
        active_rows = conn.execute(
            "SELECT trade_id, trade_date, symbol, setup, entry, stop, r_result FROM journal_trades "
            "WHERE exit IS NULL ORDER BY trade_date DESC, trade_id DESC"
        ).fetchall()
        active = []
        for row in active_rows:
            item = dict(row)
            item["coach"] = _coach_for_open_trade(conn, row, on_or_before)
            item["open_r"] = (item.get("coach") or {}).get("r")
            try:
                item["days_held"] = market_calendar.trading_days_between(
                    _date.fromisoformat(row["trade_date"]), _date.fromisoformat(on_or_before)
                )
            except (ValueError, TypeError):
                item["days_held"] = None
            item["chart"] = _mini_chart_payload(conn, row["symbol"], on_or_before, 60)
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
        rows = conn.execute(
            "SELECT trade_id, trade_date, symbol, setup, entry, exit, stop, r_result, mistake_tags_json, notes "
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
            "SELECT COUNT(*) AS n FROM refusals WHERE scan_date IN "
            "(SELECT DISTINCT scan_date FROM refusals ORDER BY scan_date DESC LIMIT 20)"
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
        mistake_pareto = [{"tag": k, "count": v} for k, v in sorted(mistake_counts.items(), key=lambda item: (-item[1], item[0]))]
        open_positions = [t for t in trades if t.get("exit") is None]
        return {
            "available": True,
            "equity_curve": equity,
            "r_histogram": r_hist,
            "mistake_pareto": mistake_pareto,
            "cohort_counts": cohorts,
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
        if scan_date:
            n_passed = conn.execute(
                "SELECT COUNT(*) FROM scan_candidates WHERE scan_date = ?",
                (scan_date,),
            ).fetchone()[0]
            mode_for_gov = (mode_row["market_mode"] if mode_row else "SELECTIVE") or "SELECTIVE"
            n_displayed = min(n_passed, governor(mode_for_gov)["max_cards"])
        # A scan that RAN (per pipeline_runs) but found 0 candidates still counts
        # as "ran" — the gate worked, nothing cleared it. Without this fallback
        # the flow stays blocked on a day the gate correctly refused everything.
        scan_ran = bool(scan_date) or bool(conn.execute(
            "SELECT 1 FROM pipeline_runs WHERE stage = 'scan_candidates' "
            "AND run_date <= ? AND status = 'ok' LIMIT 1",
            (on_or_before,),
        ).fetchone())
        if scan_date and n_passed > 0:
            setups_status = "action" if n_displayed > 0 else "done"
            setups_detail = (f"{n_displayed} setup(s) to review tonight "
                             f"({n_passed} cleared the gate, scan {scan_date}).")
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

        steps = [data_step, regime_step, pos_step, setups_step]
        # 5. DONE — all prior steps done/skipped (action/blocked = not done)
        terminal_ok = all(s["status"] in {"done", "skipped"} for s in steps)
        done_step = {
            "id": "done", "label": "Done",
            "status": "done" if terminal_ok else "blocked",
            "detail": ("All steps cleared — you're done for tonight."
                       if terminal_ok else "Finish the open steps above first."),
            "count": None,
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
            "mistake_tags_json, notes, created_at FROM journal_trades "
            "ORDER BY trade_date DESC, trade_id DESC"
        ).fetchall()
        trades = [_journal_item(row) for row in rows]
        for trade in trades:
            if trade.get("exit_state") is None:
                trade["exit_state"] = _symbol_exit_state(conn, trade["symbol"], trade["trade_date"])
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
            "exit_state_json = ?, first_exit_flag_date = NULL WHERE trade_id = ?",
            (exit_price, r_result, json.dumps(tags), json.dumps(exit_state), trade_id),
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

    # NSE bhavcopy — 'girish' source produces the cmDDMMMYYYYbhav.csv the ingest reads.
    _step("fetch_bhavcopy",
          [sys.executable, "download_bhavcopy.py", "--source", "girish", "--days", "5"],
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
