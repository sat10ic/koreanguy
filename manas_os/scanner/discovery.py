"""WAVE K K4 — Stage-1 SENSITIVE BUCKET (design/WAVE_K_SPEC.md PART C,
design/knowledge/PLAYBOOK_TO_TOOL_MAP.md §B).

COUNTERFACTUAL ONLY this wave: persists to `discovery_bucket`
(scan_date, symbol, archetypes_json, metrics_json). Does NOT touch
scan_candidates / gates / refusals — build_bucket is additive and
recall-optimized (deliberately wide: 30-80 names/day target), not a refusal
cascade. Every threshold below carries its corpus cite; none are invented
(PLAYBOOK_TO_TOOL_MAP §B is the source of record).
"""
from __future__ import annotations

import json
import time
from typing import Any

from manas_os.engine import eod_detectors
from manas_os.engine.universe_filter import GateConfig, evaluate_symbol
from manas_os.scanner import discovery_metrics as dm

STAGE = "discovery_bucket"
SOURCE = "daily_prices"

# --- base eligibility (PLAYBOOK_TO_TOOL_MAP §B row 1; TTM-A2/S7, AR,
# WK groww3/CHARTSMAZE) --------------------------------------------------
BASE_GATE_CFG = GateConfig(min_price=30.0, min_avg_turnover_cr=3.0,
                            min_market_cap_cr=0.0, exclude_etf=True)
MIN_AVG_VOL_30D = 200_000  # 2 lakh shares/day, WK groww3

# --- buying force (§B row 2; WK groww2/CH3.1) ----------------------------
BUYING_FORCE_PCT_UP_65D_LOW = 30.0  # ">=30-35% up from 65d low"; low end used

# --- velocity (§B rows 3-4; WK groww2/CH3.1) -----------------------------
# "ZERO dots = skip regardless of setup" is the one hard corpus number here;
# >=1 dot is therefore the cited velocity floor. The corpus gives no separate
# numeric percentile for "ADR20 in top universe pctile" beyond "top" -- reused
# here as the SAME 40th-percentile cutoff already cited for buying-force
# momentum below, for internal consistency rather than inventing a second,
# unsourced number.
PURPLE_DOT_MIN = 1
TOP_PCTILE_CUTOFF = 40.0  # "top-40th-pctile" per WK groww2/CH3.1 momentum language

# --- correction depth (§B row 6; WK groww2) ------------------------------
CORRECTION_DEPTH_MAX = 30.0  # "<=25-30% from leg high; >30% = avoid"

# --- archetype b: pullback-to-rising-MA (WK, 6 Manas Entry; TTM-C10) -----
PULLBACK_MA_NEAR_PCT = 3.0  # "close near rising 10/20 SMA" -- no exact % in
# corpus; 3% mirrors gates.py's own EXT21_FRESH-scale "near" reading (gates.py
# L36) rather than an invented figure from a different family of number.

# --- archetype a: strong-start-ready tightness bottom-pctile (WK Tightness
# Study) -- corpus names "bottom pctile" without a number; bottom QUARTILE
# (25th) is used for internal consistency with range_contraction_flag's
# ATR bottom-quartile cutoff (discovery_metrics.py), both reading the same
# "own 20d/60d history, bottom quartile" contraction principle.
TIGHTNESS_BOTTOM_PCTILE = 25.0

# --- archetype e: D2/episodic (TTM-B5b) ----------------------------------
D2_EXPANSION_PCT = 10.0  # "Day-1 >=10% expansion (or 20% circuit)"
D2_CIRCUIT_PCT = 20.0


def _num(bar: dict[str, Any], key: str) -> float | None:
    v = bar.get(key)
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def ensure_schema(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS discovery_bucket ("
        "scan_date TEXT NOT NULL, symbol TEXT NOT NULL, "
        "archetypes_json TEXT NOT NULL, metrics_json TEXT NOT NULL, "
        "created_at TEXT DEFAULT (datetime('now')), "
        "PRIMARY KEY (scan_date, symbol))"
    )


def _universe_symbols(conn, scan_date: str) -> list[str]:
    rows = conn.execute(
        "SELECT DISTINCT symbol FROM daily_prices WHERE series='EQ' AND trade_date = ?",
        (scan_date,),
    ).fetchall()
    return [r["symbol"] for r in rows]


def _load_bars(conn, symbol: str, scan_date: str, limit: int = 280) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT trade_date AS date, open, high, low, close, prev_close, volume, "
        "delivery_qty, delivery_pct "
        "FROM daily_prices WHERE symbol = ? AND series = 'EQ' AND trade_date <= ? "
        "ORDER BY trade_date DESC LIMIT ?",
        (symbol.upper(), scan_date, limit),
    ).fetchall()
    return [dict(r) for r in reversed(rows)]


def _asm_symbols(conn, scan_date: str) -> set[str]:
    row_date = conn.execute(
        "SELECT MAX(trade_date) AS d FROM symbol_quality WHERE trade_date <= ?",
        (scan_date,),
    ).fetchone()
    if not row_date or not row_date["d"]:
        return set()
    rows = conn.execute(
        "SELECT symbol FROM symbol_quality WHERE trade_date = ? AND asm_stage IS NOT NULL",
        (row_date["d"],),
    ).fetchall()
    return {r["symbol"] for r in rows}


def _avg_vol_30d(bars: list[dict[str, Any]]) -> float | None:
    window = bars[-30:]
    vols = [_num(b, "volume") for b in window if _num(b, "volume") is not None]
    if not vols:
        return None
    return sum(vols) / len(vols)


def _momentum_63d(bars: list[dict[str, Any]]) -> float | None:
    if len(bars) < 64:
        return None
    closes = [_num(b, "close") for b in bars]
    now = closes[-1]
    then = closes[-64]
    if now is None or then in (None, 0):
        return None
    return (now - then) / then * 100.0


def _pctile_rank(value: float | None, population: list[float]) -> float | None:
    """% of `population` that is <= value (0 = lowest, 100 = highest)."""
    if value is None or not population:
        return None
    below_or_equal = sum(1 for v in population if v <= value)
    return below_or_equal / len(population) * 100.0


def _reversal_archetype(bars: list[dict[str, Any]]) -> bool:
    """Strong prior uptrend + down 3-5 days on declining volume.
    Cite: WK 6 Manas Entry / AR-Undercut (archetype d)."""
    if len(bars) < 70:
        return False
    prior_bars = bars[:-5]
    prior_momentum = _momentum_63d(prior_bars)
    if prior_momentum is None or prior_momentum <= 10.0:
        return False  # no meaningful prior uptrend to reverse from
    tail = bars[-5:]
    closes = [_num(b, "close") for b in tail]
    vols = [_num(b, "volume") for b in tail]
    if any(c is None for c in closes) or any(v is None for v in vols):
        return False
    down_days = sum(1 for i in range(1, len(closes)) if closes[i] < closes[i - 1])
    declining_vol = vols[-1] <= vols[0]
    return down_days >= 3 and declining_vol


def _pullback_to_rising_ma(bars: list[dict[str, Any]], correction_depth: float | None) -> bool:
    """Close near a RISING 10/20 SMA; depth <=30% from leg high.
    Cite: WK, 6 Manas Entry; TTM-C10, TTM-H-III4 (archetype b)."""
    if correction_depth is None or correction_depth > CORRECTION_DEPTH_MAX:
        return False
    closes = [_num(b, "close") for b in bars]
    if len(closes) < 25:
        return False
    from manas_os.engine.manas_indicators import _sma
    sma10 = _sma(closes, 10)
    sma20 = _sma(closes, 20)
    close = closes[-1]
    for series in (sma10, sma20):
        if len(series) < 6 or series[-1] is None or series[-6] is None or close is None:
            continue
        rising = series[-1] > series[-6]
        near = abs(close - series[-1]) / series[-1] * 100.0 <= PULLBACK_MA_NEAR_PCT if series[-1] else False
        if rising and near:
            return True
    return False


def _d2_episodic(bars: list[dict[str, Any]]) -> bool:
    """Day-1 >=10% expansion (or 20% circuit) out of a tight consolidation.
    Cite: TTM-B5b (archetype e)."""
    if len(bars) < 22:
        return False
    latest = bars[-1]
    close = _num(latest, "close")
    prev_close = _num(latest, "prev_close")
    if prev_close is None and len(bars) > 1:
        prev_close = _num(bars[-2], "close")
    if close is None or not prev_close:
        return False
    day_change = (close - prev_close) / prev_close * 100.0
    if day_change < D2_EXPANSION_PCT:
        return False
    # "out of consolidation": yesterday's range sat in the bottom quartile of
    # its own trailing-20d range history (same nature-relative tightness read
    # as prev_day_tightness_pctile, computed on bars EXCLUDING today's move).
    pre_move_bars = bars[:-1]
    tightness = dm.prev_day_tightness_pctile(pre_move_bars)
    return tightness is not None and tightness <= TIGHTNESS_BOTTOM_PCTILE


def build_bucket(conn, scan_date: str) -> list[dict[str, Any]]:
    """Stage-1 SENSITIVE BUCKET for `scan_date`. Pure read + one caller-owned
    write path via persist_bucket (this function does not write). Returns
    [{"symbol", "archetypes": [...], "metrics": {...}}, ...].
    """
    symbols = _universe_symbols(conn, scan_date)
    if not symbols:
        return []
    asm = _asm_symbols(conn, scan_date)

    per_symbol_bars: dict[str, list[dict[str, Any]]] = {}
    eligible: list[str] = []
    for sym in symbols:
        if sym in asm:
            continue
        bars = _load_bars(conn, sym, scan_date)
        if not bars or bars[-1].get("date") != scan_date:
            continue
        verdict = evaluate_symbol(bars, sym, BASE_GATE_CFG)
        if not verdict["tradeable"]:
            continue
        avg_vol = _avg_vol_30d(bars)
        if avg_vol is None or avg_vol < MIN_AVG_VOL_30D:
            continue
        per_symbol_bars[sym] = bars
        eligible.append(sym)

    if not eligible:
        return []

    # universe-relative percentile populations, computed over the ELIGIBLE
    # (base-eligibility-passed) set only -- "top universe pctile" per §B.
    momentum_pop = []
    adr_pop = []
    for sym in eligible:
        bars = per_symbol_bars[sym]
        mom = _momentum_63d(bars)
        if mom is not None:
            momentum_pop.append(mom)
        adr = dm.adr20(bars)
        if adr is not None:
            adr_pop.append(adr)

    bucket: list[dict[str, Any]] = []
    for sym in eligible:
        bars = per_symbol_bars[sym]

        pct_up_65d = dm.pct_up_from_65d_low(bars)
        momentum = _momentum_63d(bars)
        momentum_pctile = _pctile_rank(momentum, momentum_pop)

        buying_force = (
            (pct_up_65d is not None and pct_up_65d >= BUYING_FORCE_PCT_UP_65D_LOW)
            or (momentum_pctile is not None and momentum_pctile >= (100.0 - TOP_PCTILE_CUTOFF))
        )
        if not buying_force:
            continue

        purple_dots = dm.purple_dot_count_60d(bars)
        adr = dm.adr20(bars)
        adr_pctile = _pctile_rank(adr, adr_pop)
        velocity = (
            purple_dots >= PURPLE_DOT_MIN
            or (adr_pctile is not None and adr_pctile >= (100.0 - TOP_PCTILE_CUTOFF))
        )
        if not velocity:
            continue

        correction_depth = dm.correction_depth_from_leg_high(bars)
        tightness_pctile = dm.prev_day_tightness_pctile(bars)
        range_contraction = dm.range_contraction_flag(bars)
        persistency = dm.persistency_counts(bars)
        persistent_momentum = dm.is_persistent_momentum(persistency)

        archetypes: list[str] = []
        # a. strong-start-ready
        uptrend = momentum is not None and momentum > 0
        if (tightness_pctile is not None and tightness_pctile <= TIGHTNESS_BOTTOM_PCTILE
                and uptrend):
            archetypes.append("strong_start_ready")
        # b. pullback-to-rising-MA
        if _pullback_to_rising_ma(bars, correction_depth):
            archetypes.append("pullback_to_rising_ma")
        # c. VCP coil
        if range_contraction:
            archetypes.append("vcp_coil")
        # d. reversal
        if _reversal_archetype(bars):
            archetypes.append("reversal")
        # e. D2/episodic
        if _d2_episodic(bars):
            archetypes.append("d2_episodic")
        # f. EP/IPO base (existing detector, wired-in)
        listing = eod_detectors.listing_status(conn, sym, scan_date)
        if eod_detectors.ipo_base(bars, listing):
            archetypes.append("ep_ipo")
        # g. persistent-momentum
        if persistent_momentum:
            archetypes.append("persistent_momentum")

        if not archetypes:
            continue

        bucket.append({
            "symbol": sym,
            "archetypes": archetypes,
            "metrics": {
                "adr20": adr,
                "adr20_pctile": adr_pctile,
                "purple_dot_count_60d": purple_dots,
                "pct_up_from_65d_low": pct_up_65d,
                "momentum_63d": momentum,
                "momentum_63d_pctile": momentum_pctile,
                "correction_depth_from_leg_high": correction_depth,
                "prev_day_tightness_pctile": tightness_pctile,
                "range_contraction_flag": range_contraction,
                "persistency_counts": persistency,
            },
        })

    return bucket


def persist_bucket(conn, scan_date: str, bucket: list[dict[str, Any]]) -> int:
    ensure_schema(conn)
    conn.execute("DELETE FROM discovery_bucket WHERE scan_date = ?", (scan_date,))
    rows = 0
    for entry in bucket:
        conn.execute(
            "INSERT INTO discovery_bucket (scan_date, symbol, archetypes_json, metrics_json) "
            "VALUES (?, ?, ?, ?)",
            (scan_date, entry["symbol"], json.dumps(entry["archetypes"]),
             json.dumps(entry["metrics"])),
        )
        rows += 1
    return rows


def _log(conn, run_date: str, status: str, rows: int, started: float, detail: str) -> None:
    conn.execute(
        "INSERT INTO pipeline_runs (run_date, stage, source, status, rows_affected, "
        "duration_s, detail) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (run_date, STAGE, SOURCE, status, rows, round(time.monotonic() - started, 3), detail),
    )


def run(conn, run_date: str) -> dict[str, Any]:
    """Nightly stage entry point. Never raises; registered AFTER scan_candidates
    (run-eod, cli/__init__.py) and is failure-safe -- a build_bucket exception
    never blocks or rolls back the scan_candidates commit that already ran."""
    started = time.monotonic()
    try:
        ensure_schema(conn)
        price_date = conn.execute(
            "SELECT MAX(trade_date) AS d FROM daily_prices WHERE series='EQ' AND trade_date <= ?",
            (run_date,),
        ).fetchone()
        scan_date = price_date["d"] if price_date and price_date["d"] else None
        if scan_date is None:
            _log(conn, run_date, "skip", 0, started, "no EQ prices for discovery bucket")
            conn.commit()
            return {"status": "skip", "rows": 0, "as_of": None}
        bucket = build_bucket(conn, scan_date)
        rows = persist_bucket(conn, scan_date, bucket)
        _log(conn, run_date, "ok", rows, started, f"scan_date={scan_date} bucket={rows}")
        conn.commit()
        return {"status": "ok", "rows": rows, "as_of": scan_date}
    except Exception as exc:  # noqa: BLE001
        _log(conn, run_date, "fail", 0, started, str(exc))
        conn.commit()
        return {"status": "fail", "rows": 0, "detail": str(exc)}
