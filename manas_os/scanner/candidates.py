"""Manas 2.0 candidate engine — the deterministic refusal cascade (plan T1.4/T1.5).

Pool = (ChartsMaze screener confluence when a dump exists) UNION (an OHLCV
detector shortlist: tradeable names within 15% of their 252d high) — so the
feed and the replay harness work on EVERY session, not only dump dates
(LEARNINGS 2026-07-06). Every pooled name then runs scanner.gates.run_cascade
(regime → tradability → trend-template → fresh-leg → participation → risk).
Refusals are LEDGERED with the failed gate + reason. Survivors get an ORDINAL
rank (1..M) ordered by (delivery_z, sector-adjusted momentum, confluence
families) — there is no additive 0-100 score any more; `readiness` persists
the rank-percentile for backward compatibility only. exit_state is joined at
build time: Weakening caps the grade at B, Broken refuses (one symbol = one
opinion). risk/plan.py is the single writer of stop/size/R:R.
"""
from __future__ import annotations

from typing import Any
import json
import time

from manas_os.engine import eod_detectors, price_action
from manas_os.engine.universe_filter import GateConfig, evaluate_symbol
from manas_os.regime.sectors import INDUSTRY_TO_SECTOR, canonical_sector_key, display_label
from manas_os.risk import plan as risk_plan
from manas_os.scanner import gates, outcomes
from manas_os.sources import chartsmaze
from manas_os.sources.chartsmaze_scanners import confluence_for_date

STAGE = "scan_candidates"
SOURCE = "daily_prices+chartsmaze"

MIN_CONFLUENCE = 2  # symbols need >=2 distinct non-bearish screener hits to enter the pool
GROWTH_FIELDS = ("eps_yoy", "eps_qoq", "sales_yoy", "opm_yoy")
GROWTH_MIN = -200.0
GROWTH_MAX = 500.0
STOP_MIN_PCT = 1.0
STOP_MAX_PCT = 8.0
INTERIM_CAPITAL = 1_000_000.0
INTERIM_RISK_PCT = 0.005

# setup_type -> gate FAMILY (plan T1.4 mapping; pullback is a pattern for
# regime-eligibility purposes — SELECTIVE allows it, per the LOCKED table).
SETUP_FAMILY = {
    "ep": "catalyst", "ipo_base": "catalyst",
    "vcp": "base/pattern", "launch_pad": "base/pattern", "tight": "base/pattern",
    "pullback": "base/pattern", "shakeout": "base/pattern",
    "pocket_pivot": "momentum", "near_pivot": "momentum", "watchlist_timing": "momentum",
    "ants": "accumulation",
}
# screener name -> family, for confluence-family counting
SCREENER_FAMILY = {
    "vcp": "base/pattern", "vcp-loose": "base/pattern", "tight-setup-daily": "base/pattern",
    "tight-setup-weekly": "base/pattern", "flag-pennants": "base/pattern",
    "inside-bar-daily": "base/pattern", "inside-bar-weekly": "base/pattern",
    "horizontal-resistance-daily": "base/pattern", "ipo-setups": "catalyst",
    "earnings-gap-up": "catalyst", "positive-earnings-reaction": "catalyst",
    "episodic-pivot": "catalyst", "momentum-scanner": "momentum", "gap-up": "momentum",
    "top-gainers": "momentum", "rs-high-before-price-high": "momentum",
    "past-winners": "momentum", "highest-volume": "accumulation",
    "volume-spike": "accumulation", "volume-footprint": "accumulation",
    "shakeout-10EMA": "base/pattern", "shakeout-21EMA": "base/pattern",
    "shakeout-50EMA": "base/pattern", "shakeout-200EMA": "base/pattern",
}


def setup_family(setup_type: str | None) -> str:
    return SETUP_FAMILY.get((setup_type or "").lower(), "momentum")


def confluence_families(screeners: list[str], setup_type: str | None) -> int:
    fams = {SCREENER_FAMILY.get(str(s).lower(), None) for s in (screeners or [])}
    fams.discard(None)
    fams.add(setup_family(setup_type))
    return len(fams)


def ensure_schema(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS scan_candidates ("
        "scan_date TEXT NOT NULL, symbol TEXT NOT NULL, setup TEXT NOT NULL, "
        "readiness REAL, grade TEXT, rs REAL, rs_as_of TEXT, delivery_pct REAL, "
        "delivery_as_of TEXT, pivot REAL, entry REAL, stop REAL, target REAL, "
        "sector TEXT, industry TEXT, evidence_json TEXT, read TEXT, timing_json TEXT, "
        "source TEXT DEFAULT 'scanner', ingested_at TEXT DEFAULT (datetime('now')), "
        "PRIMARY KEY (scan_date, symbol, setup))"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_scan_candidates_date_readiness "
        "ON scan_candidates(scan_date, readiness DESC)"
    )
    # score_breakdown_json / measured_move / measured_move_note are additive
    # columns on top of the P2 schema — added via ALTER so existing DBs
    # upgrade transparently (mirrors the pattern in manas_os.db.init_db).
    have = {r[1] for r in conn.execute("PRAGMA table_info(scan_candidates)")}
    for name, ddl in {
        "score_breakdown_json": "TEXT",
        "measured_move": "REAL",
        "measured_move_note": "TEXT",
        "confluence_count": "INTEGER",
        "setup_type": "TEXT",
        "pattern_label": "TEXT",
        "base_age": "INTEGER",
        "days_since_listing": "INTEGER",
        "trade_plan_json": "TEXT",
        "rr": "REAL",
        "suggested_qty": "INTEGER",
        "rank": "INTEGER",
        "rank_of": "INTEGER",
        "setup_family": "TEXT",
        "exit_state": "TEXT",
        "gates_json": "TEXT",
    }.items():
        if name not in have:
            conn.execute(f"ALTER TABLE scan_candidates ADD COLUMN {name} {ddl}")


def latest_price_date(conn, on_or_before: str) -> str | None:
    row = conn.execute(
        "SELECT MAX(trade_date) AS d FROM daily_prices "
        "WHERE series='EQ' AND trade_date <= ?",
        (on_or_before,),
    ).fetchone()
    return row["d"] if row and row["d"] else None


def load_symbol_bars(conn, symbol: str, on_or_before: str, limit: int = 260) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT trade_date AS date, open, high, low, close, prev_close, volume, "
        "delivery_qty, delivery_pct "
        "FROM daily_prices WHERE symbol = ? AND series = 'EQ' AND trade_date <= ? "
        "ORDER BY trade_date DESC LIMIT ?",
        (symbol.upper(), on_or_before, limit),
    ).fetchall()
    return [dict(r) for r in reversed(rows)]


def _avg(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _round(value: Any, ndigits: int = 2) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value), ndigits)
    except (TypeError, ValueError):
        return None


def _growth_payload(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    try:
        raw = float(value)
    except (TypeError, ValueError):
        return None
    payload: dict[str, Any] = {"value": raw}
    if raw < GROWTH_MIN or raw > GROWTH_MAX:
        payload["untrusted"] = True
    return payload


def growth_payloads(quality: dict[str, Any] | None) -> dict[str, dict[str, Any] | None]:
    """UI/scoring boundary for all growth fields.

    Raw values stay in symbol_quality. Candidate payloads carry a trust marker
    so displays can render bad data as unavailable and scorers can ignore it.
    """
    quality = quality or {}
    return {field: _growth_payload(quality.get(field)) for field in GROWTH_FIELDS}


def trusted_growth_value(quality: dict[str, Any] | None, field: str) -> float | None:
    payload = growth_payloads(quality).get(field)
    if not payload or payload.get("untrusted"):
        return None
    return float(payload["value"])


def format_growth_value(value: Any) -> str:
    payload = _growth_payload(value)
    if not payload:
        return "N/A"
    if payload.get("untrusted"):
        return "N/A (data error)"
    return f"{float(payload['value']):+.0f}%"


def validate_interim_risk(entry: Any, stop: Any, measured_move: Any) -> dict[str, Any]:
    try:
        entry_f = float(entry)
        stop_f = float(stop)
        mm_f = float(measured_move)
    except (TypeError, ValueError):
        return {"valid": False, "reason": "missing valid entry/stop/measured move"}
    risk = entry_f - stop_f
    if entry_f <= 0 or risk <= 0:
        return {"valid": False, "reason": "missing valid entry/stop/measured move"}
    stop_pct = risk / entry_f * 100.0
    if stop_pct < STOP_MIN_PCT or stop_pct > STOP_MAX_PCT:
        return {
            "valid": False,
            "stop_pct": round(stop_pct, 1),
            "reason": f"stop {stop_pct:.1f}% -- no valid invalidation within cap",
        }
    rr = (mm_f - entry_f) / risk
    if rr <= 0:
        return {"valid": False, "stop_pct": round(stop_pct, 1), "reason": "missing valid R:R"}
    suggested_qty = int((INTERIM_CAPITAL * INTERIM_RISK_PCT) // risk)
    if suggested_qty <= 0:
        return {"valid": False, "stop_pct": round(stop_pct, 1), "reason": "position size is zero"}
    return {
        "valid": True,
        "stop_pct": round(stop_pct, 2),
        "rr": round(rr, 2),
        "suggested_qty": suggested_qty,
    }


def symbol_timing(conn, symbol: str, on_or_before: str) -> dict[str, Any]:
    sym = symbol.upper()
    bars = load_symbol_bars(conn, sym, on_or_before, 80)
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
        "read": "; ".join(read_parts) + "." if read_parts else "Not enough timing data yet.",
    }


def _most_recent_table_date(conn, table: str, date_col: str, on_or_before: str) -> str | None:
    """Latest `date_col` <= on_or_before that has rows in `table`.

    ChartsMaze-derived tables (screener_hits, symbol_quality, sector_metrics)
    can be stamped ahead of the latest bhavcopy/regime date (dated dump
    folders don't line up 1:1 with trade dates), so every read here resolves
    MOST-RECENT <= as_of rather than requiring an exact match — otherwise the
    feed goes empty on any date the dump folders don't exactly cover.
    """
    row = conn.execute(
        f"SELECT MAX({date_col}) AS d FROM {table} WHERE {date_col} <= ?",
        (on_or_before,),
    ).fetchone()
    return row["d"] if row and row["d"] else None


def confluence_pool(conn, on_or_before: str) -> tuple[str | None, dict[str, dict[str, Any]]]:
    """The candidate pool: symbols with confluence_count >= MIN_CONFLUENCE,
    resolved from the most-recent screener_hits trade_date <= on_or_before.

    Returns (screener_date, {symbol: confluence_entry}) filtered to the
    confluence threshold. screener_date is None if no screener_hits rows
    exist on/before on_or_before (empty pool).
    """
    screener_date = _most_recent_table_date(conn, "screener_hits", "trade_date", on_or_before)
    if screener_date is None:
        return None, {}
    confluence = confluence_for_date(conn, screener_date)
    pool = {sym: entry for sym, entry in confluence.items() if entry["count"] >= MIN_CONFLUENCE}
    return screener_date, pool


def symbol_quality_map(conn, on_or_before: str) -> tuple[str | None, dict[str, dict[str, Any]]]:
    """{symbol: symbol_quality row} as of the most-recent trade_date <= on_or_before."""
    quality_date = _most_recent_table_date(conn, "symbol_quality", "trade_date", on_or_before)
    if quality_date is None:
        return None, {}
    rows = conn.execute(
        "SELECT symbol, market_cap_cr, asm_stage, eps_qoq, eps_yoy, sales_yoy, opm_yoy, "
        "is_fno, exchange FROM symbol_quality WHERE trade_date = ?",
        (quality_date,),
    ).fetchall()
    return quality_date, {r["symbol"]: dict(r) for r in rows}


def sector_rs_quartile(conn, on_or_before: str) -> tuple[str | None, set[str]]:
    """Sector keys in the TOP quartile of sector_metrics.rs_score, resolved
    most-recent snapshot_date <= on_or_before. Returns (snapshot_date, set of
    top-quartile sector_key). Empty set if <4 sectors have an rs_score.
    """
    sec_date = _most_recent_table_date(conn, "sector_metrics", "snapshot_date", on_or_before)
    if sec_date is None:
        return None, set()
    rows = conn.execute(
        "SELECT sector_key, rs_score FROM sector_metrics "
        "WHERE snapshot_date = ? AND rs_score IS NOT NULL ORDER BY rs_score DESC",
        (sec_date,),
    ).fetchall()
    if len(rows) < 4:
        return sec_date, set()
    cutoff = max(1, len(rows) // 4)
    top = {r["sector_key"] for r in rows[:cutoff]}
    return sec_date, top


def market_mode_for(conn, on_or_before: str) -> tuple[str, bool]:
    """(market_mode, defaulted). No snapshot at all -> SELECTIVE with a
    defaulted flag (fresh DB / tests); the cascade's regime gate then only
    admits catalyst + base/pattern families — never permissive, never empty
    by accident. A real NO_TRADE snapshot still yields NO_TRADE."""
    row = conn.execute(
        "SELECT market_mode FROM regime_snapshots WHERE snapshot_date <= ? "
        "ORDER BY snapshot_date DESC LIMIT 1",
        (on_or_before,),
    ).fetchone()
    if row and row["market_mode"]:
        return str(row["market_mode"]).upper(), False
    return "SELECTIVE", True


def _index_return_63d(conn, index_symbol: str, on_or_before: str) -> float | None:
    rows = conn.execute(
        "SELECT close FROM sector_index_prices WHERE symbol = ? AND trade_date <= ? "
        "AND close IS NOT NULL ORDER BY trade_date DESC LIMIT 64",
        (index_symbol, on_or_before),
    ).fetchall()
    if len(rows) < 64 or not rows[-1]["close"]:
        return None
    return (float(rows[0]["close"]) - float(rows[-1]["close"])) / float(rows[-1]["close"]) * 100.0


def sector_adjusted_momentum(conn, bars: list[dict[str, Any]], sector_key: str | None,
                             on_or_before: str) -> float | None:
    """stock 63d return − sector-index 63d return (LOCKED rank tiebreak).

    Falls back to the NIFTYMIDSML400 benchmark, then to the raw stock return
    when no index history exists (thin sector_index_prices coverage)."""
    closes = [b.get("close") for b in bars if b.get("close")]
    if len(closes) < 64 or not closes[-64]:
        return None
    stock_ret = (float(closes[-1]) - float(closes[-64])) / float(closes[-64]) * 100.0
    bench = None
    if sector_key:
        idx_row = conn.execute(
            "SELECT DISTINCT symbol FROM sector_index_prices",
        ).fetchall()
        for r in idx_row:
            if canonical_sector_key(r["symbol"], "index") == sector_key:
                bench = _index_return_63d(conn, r["symbol"], on_or_before)
                break
    if bench is None:
        bench = _index_return_63d(conn, "NIFTYMIDSML400", on_or_before)
    return round(stock_ret - (bench or 0.0), 2)


def detector_shortlist(conn, price_date: str, limit: int = 600) -> list[str]:
    """OHLCV pool: EQ names within 15% of their 252d high on price_date.

    This is what makes the feed + replay work on sessions with no ChartsMaze
    dump (LEARNINGS 2026-07-06): nearness>=0.85 is already a cascade gate, so
    pre-filtering on it is lossless for non-catalyst setups."""
    rows = conn.execute(
        "SELECT p.symbol FROM daily_prices p JOIN ("
        "  SELECT symbol, MAX(high) AS hi FROM daily_prices "
        "  WHERE series='EQ' AND trade_date <= ? AND trade_date >= date(?, '-372 days') "
        "  GROUP BY symbol) mx ON mx.symbol = p.symbol "
        "WHERE p.series='EQ' AND p.trade_date = ? AND p.close IS NOT NULL "
        "AND mx.hi > 0 AND p.close >= 0.85 * mx.hi ORDER BY p.symbol LIMIT ?",
        (price_date, price_date, price_date, limit),
    ).fetchall()
    return [r["symbol"] for r in rows]


def ensure_refusals_schema(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS refusals ("
        "scan_date TEXT NOT NULL, symbol TEXT NOT NULL, setup_family TEXT, "
        "failed_gate TEXT NOT NULL, reason TEXT, evidence_json TEXT, "
        "ingested_at TEXT DEFAULT (datetime('now')), "
        "PRIMARY KEY (scan_date, symbol))"
    )


def _refuse(conn, refusals: list, scan_date: str, symbol: str, family: str | None,
            gate_name: str, reason: str | None, evidence: Any = None) -> None:
    refusals.append({"symbol": symbol, "setup_family": family, "failed_gate": gate_name,
                     "reason": reason})
    conn.execute(
        "INSERT OR REPLACE INTO refusals (scan_date, symbol, setup_family, failed_gate, "
        "reason, evidence_json) VALUES (?, ?, ?, ?, ?, ?)",
        (scan_date, symbol.upper(), family, gate_name, reason,
         json.dumps(evidence) if evidence is not None else None),
    )


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


def stock_rs_map(on_or_before: str) -> dict[str, dict[str, Any]]:
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


def grade(readiness: float) -> str:
    if readiness >= 90:
        return "A+"
    if readiness >= 75:
        return "A"
    if readiness >= 60:
        return "B"
    return "C"


def _confluence_component(count: int) -> float:
    """More screeners = stronger. Capped at 30 (count 4+ saturates)."""
    return min(30.0, count * 7.5)


def _theme_component(sector_key: str | None, top_quartile: set[str]) -> float:
    """15pt boost when the symbol's sector is in the sector_metrics top quartile."""
    if sector_key and sector_key in top_quartile:
        return 15.0
    return 0.0


def _earnings_component(quality: dict[str, Any] | None) -> float:
    """Up to 15: 8 for eps_yoy>0, 7 for eps_qoq>0."""
    if not quality:
        return 0.0
    score = 0.0
    eps_yoy = trusted_growth_value(quality, "eps_yoy")
    eps_qoq = trusted_growth_value(quality, "eps_qoq")
    if eps_yoy is not None and eps_yoy > 0:
        score += 8.0
    if eps_qoq is not None and eps_qoq > 0:
        score += 7.0
    return score


def _delivery_component(delivery_pct: float | None) -> float:
    """Up to 10, scaled from delivery_pct."""
    if delivery_pct is None:
        return 0.0
    if delivery_pct >= 60:
        return 10.0
    if delivery_pct >= 40:
        return 5.0
    return 0.0


def _rs_component(rs_rating: float | None) -> float:
    """Up to 15, linear 0-100 -> 0-15."""
    if rs_rating is None:
        return 0.0
    return max(0.0, min(15.0, rs_rating / 100.0 * 15.0))


def _percentile(value: float | None, values: list[float]) -> float | None:
    if value is None or not values:
        return None
    below = sum(1 for v in values if v <= value)
    return round(below / len(values) * 100.0, 1)


def absolute_strength_percentiles(conn, on_or_before: str) -> dict[str, float]:
    """Own-price 63-session momentum percentile across the EQ universe.

    Single window-function query (was one query PER symbol — ~2,400/session —
    which made historical replay time out; see LEARNINGS 2026-07-06)."""
    date_row = conn.execute(
        "SELECT MAX(trade_date) AS d FROM daily_prices WHERE series='EQ' AND trade_date <= ?",
        (on_or_before,),
    ).fetchone()
    if not date_row or not date_row["d"]:
        return {}
    latest_date = date_row["d"]
    rows = conn.execute(
        "WITH ranked AS ("
        "  SELECT symbol, close, ROW_NUMBER() OVER "
        "    (PARTITION BY symbol ORDER BY trade_date DESC) AS rn "
        "  FROM daily_prices WHERE series='EQ' AND trade_date <= ? AND close IS NOT NULL"
        ") "
        "SELECT a.symbol, a.close AS c0, b.close AS c63 FROM ranked a "
        "JOIN ranked b ON b.symbol = a.symbol AND b.rn = 64 WHERE a.rn = 1 AND b.close > 0",
        (latest_date,),
    ).fetchall()
    raw = {r["symbol"]: (float(r["c0"]) - float(r["c63"])) / float(r["c63"]) * 100.0 for r in rows}
    vals = list(raw.values())
    return {sym: pct for sym, value in raw.items() if (pct := _percentile(value, vals)) is not None}


def eps_growth_percentiles(quality_map: dict[str, dict[str, Any]]) -> dict[str, float]:
    values = [v for q in quality_map.values() if (v := trusted_growth_value(q, "eps_yoy")) is not None]
    return {
        sym: pct
        for sym, q in quality_map.items()
        if (pct := _percentile(trusted_growth_value(q, "eps_yoy"), values)) is not None
    }


_TRIGGER_KINDS = {"POCKET_PIVOT", "SHAKEOUT"}


def _signal_component(latest_signals: list[dict[str, Any]]) -> tuple[float, str | None]:
    """10pts if a price-action trigger fired on the as-of date. Returns
    (points, signal_label) — signal_label feeds score_breakdown."""
    for sig in latest_signals:
        kind = sig.get("kind")
        if kind in _TRIGGER_KINDS or "TOUCH" in (kind or "") or "RECLAIM" in (kind or ""):
            return 10.0, kind
    return 0.0, None


def candidate_for_symbol(
    conn,
    symbol: str,
    on_or_before: str,
    confluence_entry: dict[str, Any],
    quality: dict[str, Any] | None,
    top_quartile_sectors: set[str],
    rs_info: dict[str, Any] | None = None,
    absolute_strength_pctile: float | None = None,
    eps_growth_pctile: float | None = None,
    market_mode: str = "SELECTIVE",
    universe_verdict: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Build one candidate through the FULL cascade. Returns a survivor dict
    (rank assigned later by scan_candidates), a refusal dict ({refused: True,
    failed_gate, drop_reason, gates}), or None when no timing data exists.
    """
    timing = symbol_timing(conn, symbol, on_or_before)
    if not timing.get("available"):
        return None
    bars = load_symbol_bars(conn, symbol, timing["as_of"], 260)
    state = price_action.signals_for_symbol(conn, symbol, timing["as_of"], max_bars=180)
    latest_signals = [s for s in state["recent_signals"] if s.get("date") == timing["as_of"]]

    evidence: list[dict[str, Any]] = []
    setup = "Watchlist timing"
    setup_type = "watchlist_timing"
    pattern_label = None
    base_age = None
    days_since_listing = None

    # Confluence + theme + ASM-clear + earnings evidence chips.
    # Only surface screener names with a recognized FAMILY (pattern/catalyst/
    # momentum/accumulation) as individual evidence — ChartsMaze also includes
    # ad-hoc personal screens (arbitrary user-named screens with no family) in
    # this list, which read as meaningless codenames to a trader and add no
    # decision value beyond the confluence count already shown separately.
    screeners = confluence_entry.get("screeners") or []
    screeners = ["vcp-loose" if str(name).lower() in {"tight-setup", "tight_setup", "chartsmaze-tight"} else name for name in screeners]
    named_screeners = [s for s in screeners if SCREENER_FAMILY.get(str(s).lower())]
    for name in named_screeners[:6]:
        evidence.append({"filter": name, "value": "hit"})

    industry = confluence_entry.get("basic_industry") or (rs_info or {}).get("industry")
    sector_key = canonical_sector_key(industry, "chartsmaze") if industry else None
    theme_tag = None
    if sector_key:
        top = sector_key in top_quartile_sectors
        theme_tag = f"{display_label(sector_key)}" + (" (top-quartile)" if top else "")
        evidence.append({"filter": "theme", "value": theme_tag})

    if quality is not None and quality.get("asm_stage") is None:
        evidence.append({"filter": "ASM-clear", "value": "yes"})

    growth = growth_payloads(quality)
    eps_yoy = trusted_growth_value(quality, "eps_yoy")
    if eps_yoy is not None and eps_yoy > 0:
        evidence.append({"filter": "EPS YoY", "value": format_growth_value(eps_yoy)})

    if timing.get("delivery_pct") is not None and timing["delivery_pct"] >= 60:
        evidence.append({"filter": "delivery>=60", "value": f"{timing['delivery_pct']:.0f}%"})
    if timing.get("rvol") is not None and timing["rvol"] >= 1.5:
        evidence.append({"filter": "rvol>=1.5", "value": f"{timing['rvol']:.2f}x"})
    if timing.get("dist_pivot") is not None and abs(timing["dist_pivot"]) <= 3:
        evidence.append({"filter": "near-pivot", "value": f"{timing['dist_pivot']:+.1f}%"})
        setup = "Near pivot"
        setup_type = "near_pivot"

    for sig in latest_signals[:3]:
        evidence.append({"filter": sig["kind"], "value": sig["detail"]})
        if sig["kind"] == "POCKET_PIVOT":
            setup = "Pocket pivot"
            setup_type = "pocket_pivot"
        elif sig["kind"] == "SHAKEOUT":
            setup = "Shakeout"
            setup_type = "shakeout"
        elif "TOUCH" in sig["kind"]:
            setup = "Pullback-to-EMA"
            setup_type = "pullback"

    rs_rating = confluence_entry.get("rs_rating")
    rs = rs_rating if rs_rating is not None else (None if not rs_info else rs_info.get("rs"))
    if rs is not None and rs >= 70:
        evidence.append({"filter": "rs>=70", "value": f"{rs:.0f}"})

    launch = eod_detectors.launch_pad(bars)
    if launch:
        setup = launch["label"]
        setup_type = launch["setup"]
        evidence.append({"filter": "launch-pad", "value": "MA cluster"})

    ants = eod_detectors.ants_accumulation(bars)
    if ants:
        evidence.append({"filter": ants["filter"], "value": ants["value"]})

    detector_quality = dict(quality or {})
    for field in GROWTH_FIELDS:
        payload = growth.get(field)
        if payload and payload.get("untrusted"):
            detector_quality[field] = None
    ep = eod_detectors.earnings_power(bars, detector_quality)
    if ep:
        setup = ep["label"]
        setup_type = ep["setup"]
        pattern_label = "Earnings Power gap"
        evidence.append({"filter": "EP", "value": "30% growth + gap"})

    listing = eod_detectors.listing_status(conn, symbol, timing["as_of"])
    ipo = eod_detectors.ipo_base(bars, listing)
    if ipo:
        setup = "IPO Base"
        setup_type = "ipo_base"
        pattern_label = ipo["label"]
        days_since_listing = listing.get("days_since_listing")
        timing["stop"] = ipo["stop"]
        evidence.append({"filter": "IPO base", "value": ipo["label"]})

    if absolute_strength_pctile is not None:
        evidence.append({"filter": "abs-strength", "value": f"{absolute_strength_pctile:.0f} pctile"})
    if eps_growth_pctile is not None:
        evidence.append({"filter": "eps-growth", "value": f"{eps_growth_pctile:.0f} pctile"})

    # --- rank inputs (NOT a score): delivery_z, sector-adjusted momentum,
    # confluence FAMILIES — the LOCKED ordinal-rank tiebreak ---
    confluence_count = confluence_entry.get("count", 0)
    _, signal_label = _signal_component(latest_signals)
    family = setup_family(setup_type)
    dz = gates.delivery_z(bars)
    sam = sector_adjusted_momentum(conn, bars, sector_key, timing["as_of"])
    families = confluence_families(screeners, setup_type)
    components = {
        "confluence": confluence_count,
        "confluence_families": families,
        "delivery_z": None if dz is None else round(dz, 2),
        "sector_adj_momentum": sam,
        "theme": theme_tag,
        "eps_yoy": eps_yoy,
        "growth": growth,
        "rs": rs,
        "delivery": timing.get("delivery_pct"),
        "signal": signal_label,
        "ants": bool(ants),
        "setup_type": setup_type,
        "setup_family": family,
        "abs_strength_pctile": absolute_strength_pctile,
        "eps_growth_pctile": eps_growth_pctile,
    }

    # --- risk plan: risk/plan.py is the single writer of stop/size/R:R ---
    entry = timing.get("entry")
    chosen = risk_plan.choose_stop(bars, family, float(entry)) if entry else None
    stop = chosen["stop"] if chosen else timing.get("stop")
    if ipo:  # IPO hard <=4% day-low stop stays authoritative
        stop = timing.get("stop")
    timing["stop"] = stop

    # --- structural measured move (single writer: risk_plan.structural_target).
    # Replaces the old `entry + 2*risk` synthetic projection that made every
    # R:R uniformly 2.0 and so the R:R>=1.5 floor never bit (LEARNINGS T1.6).
    # Computed BEFORE validate() so the floor actually gates on the real level.
    measured_move = None
    measured_move_note = None
    if entry and stop and entry > stop:
        st = risk_plan.structural_target(bars, float(entry), float(stop), family)
        if st is not None:
            measured_move = st["target"]
            measured_move_note = (
                f"Measured move = {st['method']}"
                + (" (synthetic — no overhead resistance visible; ATR projection)"
                   if st.get("synthetic") else
                   " — prior resistance the trade races toward, not a promise.")
            )
        else:
            measured_move_note = "No structural target visible — R:R unknowable; refused by the risk gate."

    plan_result = risk_plan.validate(
        entry=float(entry) if entry else 0.0,
        stop=float(stop) if stop else 0.0,
        measured_move=measured_move,
        regime=market_mode,
        setup_family=setup_type or "",
        sector=sector_key,
    )
    if (
        plan_result.get("pass")
        and timing.get("adr")
        and plan_result.get("stop_pct") is not None
        and plan_result["stop_pct"] > 0.75 * timing["adr"] * 1.0
    ):
        evidence.append({
            "filter": "wide-stop-vs-ADR",
            "value": f"stop {plan_result['stop_pct']:.1f}% vs ADR {timing['adr']:.1f}%",
        })

    # --- one symbol = one opinion: exit_state reconciliation ---
    exit_info = eod_detectors.exit_state(bars)

    # --- the cascade ---
    cascade = gates.run_cascade({
        "bars": bars, "symbol": symbol, "setup_family": family,
        "market_mode": market_mode, "quality": quality,
        "universe_verdict": universe_verdict, "rs_rating": rs,
        "pivot": timing.get("pivot"), "breakout_age": None,
        "breakout_day_entry": setup_type in ("pocket_pivot", "ep"),
        "plan_result": plan_result,
    })
    if exit_info["state"] == "Broken" and cascade["passed"]:
        cascade = {"passed": False, "failed_at": "one-opinion",
                   "reasons": ["exit state is Broken — a name flashing structural exits "
                               "cannot also be a fresh entry"], "gates": cascade["gates"]}
    if not cascade["passed"]:
        return {
            "symbol": symbol.upper(), "refused": True,
            "setup_family": family, "setup_type": setup_type,
            "failed_gate": cascade["failed_at"],
            "drop_reason": (cascade["reasons"] or [None])[0],
            "gates": cascade["gates"],
            "entry": entry, "stop": stop, "measured_move": measured_move,
        }

    # One-opinion grade cap: only REAL weakness caps the grade. Mere
    # below-21EMA is the entry condition of a pullback, not a conflict —
    # capping on it made every pullback grade B (QC 2026-07-06).
    _real_weakness = {"distribution-days", "distribution-cluster", "lower-low",
                      "downside-reversal-bar", "crossed-below-21EMA"}
    weak_rules = {r["rule"] for r in exit_info["fired_rules"]} & _real_weakness
    grade_cap = "B" if (exit_info["state"] == "Weakening" and weak_rules) else None
    if grade_cap:
        evidence.append({"filter": "exit-conflict",
                         "value": f"entry conflicts with weakness ({', '.join(sorted(weak_rules))}) — grade capped at B"})

    plan = eod_detectors.trade_plan(setup_type or setup, entry, stop, measured_move)
    if plan is not None:
        plan["suggested_qty"] = plan_result["qty"]
        plan["position_size_source"] = (
            f"{plan_result['risk_pct_used']}% risk ({risk_plan.active_profile()} profile)")

    return {
        "symbol": symbol.upper(),
        "setup": setup,
        "setup_type": setup_type,
        "setup_family": family,
        "pattern_label": pattern_label,
        # rank + readiness(=rank percentile) are assigned by scan_candidates
        "readiness": None,
        "grade": None,
        "grade_cap": grade_cap,
        "rank_inputs": (dz if dz is not None else -99.0,
                        sam if sam is not None else -999.0,
                        families),
        "gates": cascade["gates"],
        "exit_state": exit_info["state"],
        "rs": rs,
        "rs_as_of": None if not rs_info else rs_info.get("rs_as_of"),
        "delivery_pct": timing.get("delivery_pct"),
        "delivery_as_of": timing.get("as_of"),
        "pivot": timing.get("pivot"),
        "entry": entry,
        "stop": stop,
        "measured_move": measured_move,
        "rr": plan_result["rr"],
        "suggested_qty": plan_result["qty"],
        "risk_pct_used": plan_result["risk_pct_used"],
        "measured_move_note": (
            "Measured move if it works out — not a promise; NSE swings often fall short or overshoot."
            if measured_move is not None
            else None
        ),
        "confluence_count": confluence_count,
        "score_breakdown": components,
        "evidence": evidence,
        "read": f"{setup}: " + "; ".join(f"{e['filter']} {e['value']}" for e in evidence[:3]) + ".",
        "timing": timing,
        "base_age": base_age,
        "days_since_listing": days_since_listing,
        "trade_plan": plan,
        "sector": sector_key,
        "industry": industry,
    }


def _assign_ranks(candidates: list[dict[str, Any]]) -> None:
    """Ordinal rank 1..M by (delivery_z, sector_adj_momentum, families) desc.
    readiness = rank percentile (backward-compat only). Grades (LOCKED):
    A+ = top-3 AND >=2 boosts · A = any boost · B = passed. exit-state
    Weakening caps at B (grade_cap)."""
    candidates.sort(key=lambda c: c["rank_inputs"], reverse=True)
    m = len(candidates)
    for i, c in enumerate(candidates, start=1):
        c["rank"] = i
        c["rank_of"] = m
        c["readiness"] = round((m - i + 1) / m * 100.0, 1)
        comp = c.get("score_breakdown") or {}
        boosts = sum([
            1 if (comp.get("delivery_z") or 0) >= 1.5 else 0,
            1 if comp.get("theme") and "top-quartile" in str(comp.get("theme")) else 0,
            1 if c.get("setup_family") == "catalyst" or comp.get("signal") else 0,
        ])
        if i <= 3 and boosts >= 2:
            g = "A+"
        elif boosts >= 1:
            g = "A"
        else:
            g = "B"
        if c.get("grade_cap") == "B" and g in ("A+", "A"):
            g = "B"
        c["grade"] = g
        c.pop("rank_inputs", None)


def scan_candidates(conn, on_or_before: str, scan_limit: int | None = None) -> dict[str, Any]:
    """Manas 2.0 scan: pooled candidates through the deterministic cascade.

    Pool = ChartsMaze confluence (when a dump exists) UNION the OHLCV
    detector shortlist (names within 15% of 252d high) — sessions without a
    dump still scan. Every pooled name runs the full cascade; refusals are
    ledgered with the failed gate; survivors get an ordinal rank.
    """
    price_date = latest_price_date(conn, on_or_before)
    if price_date is None:
        return {"available": False, "as_of": None, "candidates": []}
    ensure_refusals_schema(conn)
    conn.execute("DELETE FROM refusals WHERE scan_date = ?", (price_date,))

    screener_date, pool = confluence_pool(conn, on_or_before)
    market_mode, mode_defaulted = market_mode_for(conn, price_date)
    _, quality_map = symbol_quality_map(conn, on_or_before)
    _, top_quartile = sector_rs_quartile(conn, on_or_before)
    rs_map = stock_rs_map(on_or_before)
    abs_strength = absolute_strength_percentiles(conn, price_date)
    eps_pctiles = eps_growth_percentiles(quality_map)

    shortlist = detector_shortlist(conn, price_date)
    pool_symbols = list(dict.fromkeys(list(pool.keys()) + shortlist))
    if scan_limit is not None:
        pool_symbols = pool_symbols[:scan_limit]

    cfg = GateConfig()
    candidates: list[dict[str, Any]] = []
    refused: list[dict[str, Any]] = []
    for sym in pool_symbols:
        quality = quality_map.get(sym)
        bars25 = load_symbol_bars(conn, sym, price_date, limit=25)
        verdict = evaluate_symbol(
            bars25, sym, cfg,
            market_cap_cr=(quality or {}).get("market_cap_cr"))
        if not verdict["tradeable"]:
            _refuse(conn, refused, price_date, sym, None, "tradability",
                    "; ".join(verdict.get("reasons_failed", [])))
            continue

        candidate = candidate_for_symbol(
            conn, sym, price_date,
            pool.get(sym, {"count": 0, "screeners": [], "rs_rating": None, "basic_industry": None}),
            quality, top_quartile, rs_map.get(sym),
            abs_strength.get(sym), eps_pctiles.get(sym),
            market_mode=market_mode, universe_verdict=verdict,
        )
        if candidate is None:
            continue
        if candidate.get("refused"):
            _refuse(conn, refused, price_date, sym, candidate.get("setup_family"),
                    candidate.get("failed_gate"), candidate.get("drop_reason"),
                    candidate.get("gates"))
            continue
        candidates.append(candidate)

    _assign_ranks(candidates)
    conn.commit()
    return {
        "available": True,
        "as_of": price_date,
        "screener_as_of": screener_date,
        "market_mode": market_mode,
        "market_mode_defaulted": mode_defaulted,
        "candidates": candidates,
        "refused_count": len(refused),
        "dropped": refused,  # backward-compat key
    }


def persist_candidates(conn, scan_date: str, candidates: list[dict[str, Any]]) -> int:
    ensure_schema(conn)
    outcomes.ensure_schema(conn)
    conn.execute("DELETE FROM scan_candidates WHERE scan_date = ?", (scan_date,))
    for c in candidates:
        conn.execute(
            "INSERT INTO scan_candidates (scan_date, symbol, setup, readiness, grade, rs, rs_as_of, "
            "delivery_pct, delivery_as_of, pivot, entry, stop, target, sector, industry, "
            "evidence_json, read, timing_json, score_breakdown_json, measured_move, "
            "measured_move_note, confluence_count, setup_type, pattern_label, base_age, "
            "days_since_listing, trade_plan_json, rr, suggested_qty, rank, rank_of, "
            "setup_family, exit_state, gates_json, source, ingested_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'scanner', datetime('now'))",
            (
                scan_date,
                c["symbol"],
                c["setup"],
                c["readiness"],
                c["grade"],
                c.get("rs"),
                c.get("rs_as_of"),
                c.get("delivery_pct"),
                c.get("delivery_as_of"),
                c.get("pivot"),
                c.get("entry"),
                c.get("stop"),
                c.get("measured_move"),
                c.get("sector"),
                c.get("industry"),
                json.dumps(c.get("evidence") or []),
                c.get("read"),
                json.dumps(c.get("timing") or {}),
                json.dumps(c.get("score_breakdown") or {}),
                c.get("measured_move"),
                c.get("measured_move_note"),
                c.get("confluence_count"),
                c.get("setup_type"),
                c.get("pattern_label"),
                c.get("base_age"),
                c.get("days_since_listing"),
                json.dumps(c.get("trade_plan") or {}),
                c.get("rr"),
                c.get("suggested_qty"),
                c.get("rank"),
                c.get("rank_of"),
                c.get("setup_family"),
                c.get("exit_state"),
                json.dumps(c.get("gates") or []),
            ),
        )
        outcomes.persist_candidate_snapshot(conn, scan_date, c)
    return len(candidates)


def filter_candidates(
    candidates: list[dict[str, Any]],
    min_rs: float | None = None,
    setup: str | None = None,
    sector: str | None = None,
    min_grade: str | None = None,
    limit: int = 80,
) -> list[dict[str, Any]]:
    setup_filter = (setup or "").strip().lower()
    sector_filter = (sector or "").strip().upper()
    min_grade_rank = {"C": 0, "B": 1, "A": 2, "A+": 3}.get((min_grade or "C").upper(), 0)
    grade_rank = {"C": 0, "B": 1, "A": 2, "A+": 3}
    out = []
    for item in candidates:
        if min_rs is not None and (item.get("rs") is None or item["rs"] < min_rs):
            continue
        if setup_filter and setup_filter not in str(item.get("setup") or "").lower():
            continue
        if sector_filter and item.get("sector") != sector_filter:
            continue
        if grade_rank.get(item.get("grade"), 0) < min_grade_rank:
            continue
        out.append(item)
    return out[:limit]


def load_persisted_candidates(
    conn,
    on_or_before: str,
    min_rs: float | None = None,
    setup: str | None = None,
    sector: str | None = None,
    min_grade: str | None = None,
    limit: int = 80,
) -> dict[str, Any]:
    ensure_schema(conn)
    row = conn.execute(
        "SELECT MAX(scan_date) AS d FROM scan_candidates WHERE scan_date <= ?",
        (on_or_before,),
    ).fetchone()
    if not row or not row["d"]:
        return {"available": False, "as_of": None, "candidates": []}
    scan_date = row["d"]
    rows = conn.execute(
        "SELECT * FROM scan_candidates WHERE scan_date = ? ORDER BY readiness DESC, symbol",
        (scan_date,),
    ).fetchall()
    candidates = []
    for row in rows:
        item = dict(row)
        item["evidence"] = json.loads(item.pop("evidence_json") or "[]")
        item["timing"] = json.loads(item.pop("timing_json") or "{}")
        item["score_breakdown"] = json.loads(item.pop("score_breakdown_json", None) or "{}")
        item["trade_plan"] = json.loads(item.pop("trade_plan_json", None) or "{}") or None
        item.setdefault("measured_move", item.get("target"))
        item.pop("target", None)
        item.pop("source", None)
        item.pop("ingested_at", None)
        candidates.append(item)
    # expectancy chip (T2.3b): system + personal cell for this family × today's regime
    from manas_os.scanner import expectancy as _exp
    mode, _ = market_mode_for(conn, scan_date)
    _chips: dict[str, Any] = {}
    for item in candidates:
        fam = item.get("setup_family") or "unknown"
        if fam not in _chips:
            _chips[fam] = _exp.chip_for(conn, fam, mode)
        item["expectancy"] = _chips[fam]
    return {
        "available": True,
        "as_of": scan_date,
        "candidates": filter_candidates(candidates, min_rs, setup, sector, min_grade, limit),
    }


def run(conn, run_date: str) -> dict[str, Any]:
    """Run the persisted P2 scanner. Never raises; always logs pipeline_runs."""
    started = time.monotonic()
    try:
        result = scan_candidates(conn, run_date)
        if not result["available"]:
            _log(conn, run_date, "skip", 0, started, "no EQ prices for scan")
            conn.commit()
            return {"status": "skip", "rows": 0, "as_of": None}
        rows = persist_candidates(conn, result["as_of"], result["candidates"])
        detail = f"scan_date={result['as_of']} candidates={rows}"
        _log(conn, run_date, "ok", rows, started, detail)
        conn.commit()
        return {"status": "ok", "rows": rows, "as_of": result["as_of"]}
    except Exception as exc:  # noqa: BLE001
        _log(conn, run_date, "fail", 0, started, str(exc))
        conn.commit()
        return {"status": "fail", "rows": 0, "detail": str(exc)}


def _log(conn, run_date: str, status: str, rows: int, started: float, detail: str) -> None:
    conn.execute(
        "INSERT INTO pipeline_runs (run_date, stage, source, status, rows_affected, "
        "duration_s, detail) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (run_date, STAGE, SOURCE, status, rows, round(time.monotonic() - started, 3), detail),
    )
