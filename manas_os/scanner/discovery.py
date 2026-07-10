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
# K4.1 EMSLIMITED fix: corpus states the liquidity floor as EITHER share-count
# OR turnover ("2 lakh shares/day OR >=3cr turnover"; WK groww3) -- a
# high-price name can clear real money turnover on a below-floor share count.
# Own 30d window (not evaluate_symbol's 20d one) for consistency with
# MIN_AVG_VOL_30D's window.
MIN_AVG_TURNOVER_CR_30D_ALT = 3.0

# --- buying force (§B row 2; WK groww2/CH3.1) ----------------------------
BUYING_FORCE_PCT_UP_65D_LOW = 30.0  # ">=30-35% up from 65d low"; low end used

# --- recent-listing force waiver (K4.1; WK groww2/GROWW autopsy) ---------
# GROWW knife-edged the current-force gate (28.7% vs 30%) partly from
# listing-window artifacts -- insufficient 65d history is not weakness.
# Force is waived (velocity required instead) across the same recent-listing
# window used by the archetype tag; K4.1 recall favors admitting recent IPO/
# demerger velocity names over re-killing them on archive/listing-window
# artifacts. RECENT_LISTING_MAX_DAYS (matches eod_detectors.listing_status's
# own is_ipo<=252 window, rounded) defines both the waiver and the broader
# "recent_listing" archetype tag. Listing age = first daily_prices
# row for the symbol as proxy (eod_detectors.listing_status), which also
# covers demerger listings (e.g. VEDPOWER) that have no true IPO date in our
# data -- documented proxy, not an authoritative listing-date source.
RECENT_LISTING_MAX_DAYS = 250

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

# --- archetype d: reversal, K7 re-anchor (WK6 structural finding: Arora's
# reversal buys sit at momentum BOTTOMS -- BSOFT +1.5% off 65d low/mom_pctile
# 5, NCC +7.4%, ZENTEC +8.3%. A current-force OR current-momentum test
# structurally excludes them; even the 60d leg_force_from_65d_low fails
# because these had MONTH-LONG corrections whose leg high predates the 40-60
# session lookback. Re-anchored to 180d/252d prior strength + a 15-40%
# correction band off the 180d high + an explicit reversal TRIGGER, per
# design/knowledge/INDIA_PLAYBOOK.md entry archetypes and 6 Manas Entry
# ("strong PRIOR uptrend visible on a longer frame + 3-5 down days on
# declining volume + first strength day"). ------------------------------
REVERSAL_PRIOR_STRENGTH_MULT = 1.5  # "max close of 180d >= 1.5x the 252d low"
REVERSAL_CORRECTION_MIN = 15.0  # "down 15-40% from that 180d high"
REVERSAL_CORRECTION_MAX = 40.0
REVERSAL_MA_BELOW_MIN_SESSIONS = 10  # "first close above 10SMA after >=10 sessions below"


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


def _avg_turnover_cr_30d(bars: list[dict[str, Any]]) -> float | None:
    """Avg rupee-crore turnover over the trailing 30 sessions -- the turnover
    ALTERNATIVE to the 2-lakh share-count floor (K4.1)."""
    window = bars[-30:]
    turnovers = []
    for b in window:
        close, vol = _num(b, "close"), _num(b, "volume")
        if close is None or vol is None:
            continue
        turnovers.append(close * vol / 1e7)
    if not turnovers:
        return None
    return sum(turnovers) / len(turnovers)


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


def _reversal_prior_strength(bars: list[dict[str, Any]], momentum_top40_value: float | None) -> bool:
    """(a) prior-strength: max close of last 180 sessions >= 1.5x the 252d
    low, OR 63d momentum was top-40pctile at ANY point in the last 120
    sessions (rolling-max value compared against TODAY's population-derived
    top-40pctile threshold -- cheap proxy, avoids a per-historical-day
    universe percentile). Cite: WK K7 fix / 6 Manas Entry."""
    high180 = dm.high_180d(bars)
    low252 = dm.low_252d(bars)
    if high180 is not None and low252 is not None and low252 > 0:
        if high180 >= REVERSAL_PRIOR_STRENGTH_MULT * low252:
            return True
    if momentum_top40_value is None:
        return False
    roll_max_mom = dm.rolling_max_momentum_120d(bars)
    return roll_max_mom is not None and roll_max_mom >= momentum_top40_value


def _reversal_correction_ok(bars: list[dict[str, Any]]) -> bool:
    """(b) correction: down 15-40% from the 180d high. Cite: WK K7 fix."""
    depth180 = dm.correction_depth_from_180d_high(bars)
    return depth180 is not None and REVERSAL_CORRECTION_MIN <= depth180 <= REVERSAL_CORRECTION_MAX


def _reversal_trigger(bars: list[dict[str, Any]]) -> bool:
    """(c) reversal trigger: 3-5 consecutive down days on declining volume
    followed by an up day, OR first close above the 10SMA after >=10 sessions
    below it. Cite: WK 6 Manas Entry (archetype d)."""
    if len(bars) < 15:
        return False
    closes = [_num(b, "close") for b in bars]
    vols = [_num(b, "volume") for b in bars]

    # trigger 1: today is an up day preceded by 3-5 consecutive down days on
    # declining volume. "Declining volume" is read the way the corpus reads
    # it -- the pullback happens on LIGHTER-than-normal volume ("up-volume >>
    # down-volume; no big red-dot (heavy-volume down) day in the pullback",
    # WK groww2/groww4) -- so the down-run's AVERAGE volume is compared
    # against the stock's trailing-20-session average, not first-vs-last bar
    # of the run (a 3-bar run's endpoints are too noisy to carry the test;
    # ZENTEC 23-Feb-2026 in the label set is the case that shows it).
    if closes[-1] is not None and closes[-2] is not None and closes[-1] > closes[-2]:
        down_run = 0
        i = len(closes) - 2
        while i > 0 and closes[i] is not None and closes[i - 1] is not None and closes[i] < closes[i - 1]:
            down_run += 1
            i -= 1
        if 3 <= down_run <= 5:
            run_vols = [v for v in vols[len(closes) - 1 - down_run: len(closes) - 1] if v is not None]
            base_vols = [v for v in vols[-21:-1] if v is not None]
            if run_vols and base_vols and sum(run_vols) / len(run_vols) <= sum(base_vols) / len(base_vols):
                return True

    # trigger 2: first close above the 10SMA after >=10 consecutive sessions
    # closing below it.
    from manas_os.engine.manas_indicators import _sma
    sma10 = _sma(closes, 10)
    if len(sma10) >= REVERSAL_MA_BELOW_MIN_SESSIONS + 2 and sma10[-1] is not None and closes[-1] is not None:
        if closes[-1] > sma10[-1]:
            below_run = 0
            i = len(sma10) - 2
            while i >= 0 and sma10[i] is not None and closes[i] is not None and closes[i] < sma10[i]:
                below_run += 1
                i -= 1
            if below_run >= REVERSAL_MA_BELOW_MIN_SESSIONS:
                return True
    return False


def _reversal_archetype(bars: list[dict[str, Any]], momentum_top40_value: float | None) -> bool:
    """Reversal archetype = prior-strength AND correction-band AND trigger.
    NO current-force requirement (WK6 finding: current force is structurally
    lowest exactly when these setups trigger). Cite: WK K7 fix / 6 Manas
    Entry / AR-Undercut (archetype d)."""
    if len(bars) < 70:
        return False
    return (
        _reversal_prior_strength(bars, momentum_top40_value)
        and _reversal_correction_ok(bars)
        and _reversal_trigger(bars)
    )


def _pullback_to_rising_ma(bars: list[dict[str, Any]], correction_depth: float | None,
                           max_depth: float = CORRECTION_DEPTH_MAX) -> bool:
    """Close near a RISING 10/20 SMA; depth <=30% from the 60d leg high (or
    <=40% when the caller admits the name via the 180d prior-strength frame,
    K7 -- `max_depth` carries the caller's band so a month-long-correction
    pullback measured off the 180d high is not re-killed by the 60d band);
    AND an ACTUAL recent pullback: >=3 down closes in the last 5 sessions
    (K7 -- without this, any name drifting up along a rising MA tags
    "pullback" and the archetype balloons to 280-400 members/day; Arora's
    pullback buys come after "3-5 down days on declining volume", 6 Manas
    Entry -- every label-set pullback pick shows >=3-of-5 down closes).
    Cite: WK, 6 Manas Entry; TTM-C10, TTM-H-III4 (archetype b)."""
    if correction_depth is None or correction_depth > max_depth:
        return False
    closes = [_num(b, "close") for b in bars]
    if len(closes) < 25:
        return False
    recent_downs = sum(
        1 for i in range(len(closes) - 5, len(closes))
        if closes[i] is not None and closes[i - 1] is not None and closes[i] < closes[i - 1]
    )
    if recent_downs < 3:
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
            # WAVE K8: three corpus-cited quality gates AND-ed on top of the
            # existing rising+near+3-of-5-down admission -- these SHRINK the
            # crowd (~200 names/day drifting-up-along-a-rising-MA), they do
            # not loosen any threshold.

            # D1 -- no heavy-volume red-dot day in the pullback + up-volume
            # dominance (supply drying up). Cite: groww2/groww4.
            vc = dm.pullback_volume_character(bars)
            if vc["has_heavy_red_day"]:
                continue
            if vc["up_down_vol_ratio"] is not None and vc["up_down_vol_ratio"] < 1.0:
                continue

            # D2 -- undercut-and-recover: must have recently traded BELOW
            # the 10/20 SMA and now be back at/above it (the "near" test
            # above already proves "back at/above"). Cite: ARORA_SHARDS
            # L43/L186-188 -- "recently gone below 10 and 20... then forms
            # base." Kills names that only ever drifted up along the MA.
            recent_len = min(10, len(closes), len(series))
            undercut = False
            for i in range(len(closes) - recent_len, len(closes)):
                c = closes[i]
                s = series[i] if i < len(series) else None
                if c is not None and s is not None and c < s:
                    undercut = True
                    break
            if not undercut:
                continue

            # D3 -- contraction into the MA: an orderly, non-expanding
            # pullback, not a sloppy wide/climactic decline. Cite: ARORA_
            # SHARDS L34-36/L55-57, TTM_NUANCES #14, STOCKGEEKS L60-63.
            tightness = dm.prev_day_tightness_pctile(bars)
            tight_ok = tightness is not None and tightness <= 50
            ranges = []
            for i in range(len(bars) - 3, len(bars)):
                if i < 0:
                    continue
                h, l = _num(bars[i], "high"), _num(bars[i], "low")
                if h is not None and l is not None:
                    ranges.append(h - l)
            non_increasing = len(ranges) == 3 and ranges[0] >= ranges[1] >= ranges[2]
            if not (tight_ok or non_increasing):
                continue

            return True
    return False


def _ma_distance_pct(bars: list[dict[str, Any]]) -> float | None:
    """% distance of the latest close from the NEAREST of the 10/20 SMAs --
    the proximity-to-trigger rank key for the pullback archetype (K7; the
    spec's own size-control language: "rank within archetype by proximity-
    to-trigger"). Smaller = closer to the buyable MA touch."""
    closes = [_num(b, "close") for b in bars]
    if len(closes) < 21 or closes[-1] is None:
        return None
    from manas_os.engine.manas_indicators import _sma
    best = None
    for n in (10, 20):
        series = _sma(closes, n)
        if series and series[-1]:
            d = abs(closes[-1] - series[-1]) / series[-1] * 100.0
            best = d if best is None else min(best, d)
    return best


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
        avg_turnover_cr = _avg_turnover_cr_30d(bars)
        vol_ok = (
            (avg_vol is not None and avg_vol >= MIN_AVG_VOL_30D)
            or (avg_turnover_cr is not None and avg_turnover_cr >= MIN_AVG_TURNOVER_CR_30D_ALT)
        )
        if not vol_ok:
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

    # raw momentum VALUE at the top-40pctile cutoff of today's eligible-
    # universe population -- K7 reversal fix's cheap proxy for "was
    # top-40pctile at ANY point in the last 120 sessions" (rolling_max_
    # momentum_120d is compared against this fixed value instead of
    # recomputing a universe percentile at every historical day).
    momentum_top40_value: float | None = None
    if momentum_pop:
        sorted_mom = sorted(momentum_pop)
        idx = min(len(sorted_mom) - 1, int(round((100.0 - TOP_PCTILE_CUTOFF) / 100.0 * (len(sorted_mom) - 1))))
        momentum_top40_value = sorted_mom[idx]

    bucket: list[dict[str, Any]] = []
    for sym in eligible:
        bars = per_symbol_bars[sym]

        pct_up_65d = dm.pct_up_from_65d_low(bars)
        momentum = _momentum_63d(bars)
        momentum_pctile = _pctile_rank(momentum, momentum_pop)
        current_force = (
            (pct_up_65d is not None and pct_up_65d >= BUYING_FORCE_PCT_UP_65D_LOW)
            or (momentum_pctile is not None and momentum_pctile >= (100.0 - TOP_PCTILE_CUTOFF))
        )

        purple_dots = dm.purple_dot_count_60d(bars)
        adr = dm.adr20(bars)
        adr_pctile = _pctile_rank(adr, adr_pop)
        velocity = (
            purple_dots >= PURPLE_DOT_MIN
            or (adr_pctile is not None and adr_pctile >= (100.0 - TOP_PCTILE_CUTOFF))
        )
        if not velocity:
            # corpus: "ZERO dots = skip regardless of setup" -- the one hard
            # floor that applies to every archetype family, unlike buying
            # force below (which is now per-archetype, K4.1).
            continue

        leg_force = dm.leg_force_from_65d_low(bars)
        correction_depth = dm.correction_depth_from_leg_high(bars)
        leg_force_ok = leg_force is not None and leg_force >= BUYING_FORCE_PCT_UP_65D_LOW
        correction_ok = correction_depth is not None and correction_depth <= CORRECTION_DEPTH_MAX

        listing = eod_detectors.listing_status(conn, sym, scan_date)
        days_listed = listing.get("days_since_listing")
        recent_listing = days_listed is not None and days_listed <= RECENT_LISTING_MAX_DAYS
        force_waived = recent_listing

        tightness_pctile = dm.prev_day_tightness_pctile(bars)
        range_contraction = dm.range_contraction_flag(bars)
        persistency = dm.persistency_counts(bars)
        persistent_momentum = dm.is_persistent_momentum(persistency)

        archetypes: list[str] = []

        # CURRENT-FORCE family: momentum/near-high/persistent-momentum/
        # strong-start/D2/EP archetypes -- buying force measured NOW,
        # unchanged from K4 -- OR waived for a fresh listing with
        # insufficient 65d history (GROWW-class knife-edge miss).
        if current_force or force_waived:
            # "uptrend" for strong-start-ready: current 63d momentum > 0, OR
            # a longer-frame uptrend already visible via the EMA200
            # persistency streak (K7 fix -- Strong_Start_Tightness_Study.md's
            # named examples (Chennai Petroleum, Coal India, EMS, Intellect)
            # sit in a tight CONTRACTION the day of/before entry, which pulls
            # current 63d momentum toward zero/negative even though "the
            # earlier momentum was upward" per the corpus's own framing;
            # ema200 persistency (already computed below) is the existing,
            # not-invented longer-frame-uptrend proxy).
            uptrend = (momentum is not None and momentum > 0) or (
                (persistency.get("ema200") or 0) > 0
            )
            # a. strong-start-ready
            if (tightness_pctile is not None and tightness_pctile <= TIGHTNESS_BOTTOM_PCTILE
                    and uptrend):
                archetypes.append("strong_start_ready")
            # c. VCP coil
            if range_contraction:
                archetypes.append("vcp_coil")
            # e. D2/episodic
            if _d2_episodic(bars):
                archetypes.append("d2_episodic")
            # f. EP/IPO base (existing detector, wired-in)
            if eod_detectors.ipo_base(bars, listing):
                archetypes.append("ep_ipo")
            # g. persistent-momentum
            if persistent_momentum:
                archetypes.append("persistent_momentum")
            # recent-listing (fresh IPO/demerger; velocity-only when waived)
            if recent_listing:
                archetypes.append("recent_listing")

        # PRIOR-STRENGTH family: pullback-to-rising-MA + reversal -- Arora
        # buys 3-5 red days INTO a correction, exactly when CURRENT-price
        # force is at its lowest (WAVE K6 structural finding). Buying force
        # is read off the PRIOR LEG (60d), or -- K7 fix -- off the LONGER
        # 180d/252d frame when the prior leg predates the 40-60 session
        # lookback entirely (month-long corrections: BSOFT, NCC, ZENTEC;
        # 6 Manas Entry's reversal buys show "strong PRIOR uptrend visible
        # on a longer frame").
        rev_prior = _reversal_prior_strength(bars, momentum_top40_value)
        depth180 = dm.correction_depth_from_180d_high(bars)
        band180_ok = depth180 is not None and depth180 <= REVERSAL_CORRECTION_MAX
        if (leg_force_ok and correction_ok) or (rev_prior and band180_ok):
            # b. pullback-to-rising-MA (depth measured off whichever anchor
            # admitted the name: 60d leg high, else 180d high)
            if leg_force_ok and correction_ok:
                pb_hit = _pullback_to_rising_ma(bars, correction_depth)
            else:
                pb_hit = _pullback_to_rising_ma(bars, depth180,
                                                max_depth=REVERSAL_CORRECTION_MAX)
            if pb_hit:
                archetypes.append("pullback_to_rising_ma")

        # d. reversal -- K7 fix: independent of the 60d leg-force gate above.
        # 180d/252d prior strength + 15-40% correction band off the 180d
        # high + an explicit trigger; NO current-force requirement.
        if _reversal_archetype(bars, momentum_top40_value):
            archetypes.append("reversal")

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
                "leg_force_from_65d_low": leg_force,
                "correction_depth_from_leg_high": correction_depth,
                "prev_day_tightness_pctile": tightness_pctile,
                "range_contraction_flag": range_contraction,
                "persistency_counts": persistency,
                "days_since_listing": days_listed,
                "correction_depth_from_180d_high": depth180,
                "ma_distance_pct": _ma_distance_pct(bars),
            },
        })

    return _apply_size_control(bucket)


# --- K4.1/K7 SIZE CONTROL (WAVE K6 finding: 181-428/day vs 30-80 target) --
# Rank members WITHIN each archetype and keep the top CAP_PER_ARCHETYPE per
# archetype; a symbol survives if it makes the cap in ANY archetype it was
# tagged with (multi-archetype names get one chance per tag -- that IS their
# consensus advantage; the old blanket "multi-archetype = immune from the
# cap" clause was unbounded and drove buckets to 315-470/day, K7 fix).
# 8 archetypes x 20 cap = <=160 raw slots before de-duplication; overlap
# keeps the union near/under the ~120/day ceiling in practice. When cap
# tightness and label recall conflict, the archetype-specific ranking (see
# _MOMENTUM_BOTTOM_ARCHETYPES) is the mechanism that protects recall, not
# an uncapped immunity class.
CAP_PER_ARCHETYPE = 20


def _velocity_score(entry: dict[str, Any]) -> float:
    """Higher = more "alive" -- ADR20 percentile + purple-dot count (each dot
    weighted like a meaningful percentile jump) + momentum percentile as the
    nearest RS proxy available in this metric set (no separate RS series is
    computed in Manas OS; momentum_63d_pctile is the corpus-adjacent stand-in
    per §B's own "top universe percentile" language)."""
    m = entry["metrics"]
    score = 0.0
    if m.get("adr20_pctile") is not None:
        score += m["adr20_pctile"]
    score += (m.get("purple_dot_count_60d") or 0) * 5.0
    if m.get("momentum_63d_pctile") is not None:
        score += m["momentum_63d_pctile"]
    if m.get("leg_force_from_65d_low") is not None:
        score += min(m["leg_force_from_65d_low"], 100.0)
    return score


# K7: archetypes whose members sit at momentum BOTTOMS by construction --
# ranking them by the momentum-weighted _velocity_score buries exactly the
# names the archetype exists to admit (BSOFT fired 'reversal' on 12-Jun-2026
# and was then evicted by the cap). Per the spec's own size-control language
# ("rank within archetype by proximity-to-trigger"), these rank by proximity:
# - pullback_to_rising_ma: K8 D4 -- DESCENDING prior-leg force
#   (leg_force_from_65d_low), tiebreak ascending ma_distance_pct then
#   liveness. K7's ma-proximity ranking barely separated the crowd (every
#   label pick sits <=2.1% from its MA); leg force is Arora's #1 momentum
#   signal and does separate strong bases from weak drift once the K8
#   D1-D3 quality gates (in `_pullback_to_rising_ma`) shrink the crowd.
# - reversal: ascending prev-day tightness percentile (the corpus's own
#   contraction-before-expansion read, Tightness Study / groww4; BSOFT
#   12-Jun-2026 shows tightness_pctile 15 at the trigger).
def _liveness(entry: dict[str, Any]) -> float:
    """ADR percentile + purple dots -- velocity/liveness tiebreak for the
    proximity rankers (corpus: dots/ADR are the universal "is it alive"
    read; groww2/CH3.1)."""
    m = entry["metrics"]
    score = 0.0
    if m.get("adr20_pctile") is not None:
        score += m["adr20_pctile"]
    score += (m.get("purple_dot_count_60d") or 0) * 5.0
    return score


def _pullback_leg_force_rank_key(entry: dict[str, Any]):
    """K8: rank pullback-to-rising-MA members by prior-leg force DESC
    (strongest prior advance first), tiebreak ma_distance_pct ascending,
    then liveness descending. Replaces proximity-to-trigger (K7): every
    label-set pullback pick sits <=2.1% from its MA, so proximity barely
    separates the ~200-name crowd; leg_force_from_65d_low is Arora's
    stated #1 momentum signal (groww2/CH3.1 "up >=30-35% from 3-month low")
    and does separate strong bases from weak drift once D1-D3 shrink the
    crowd (WAVE_K8_PULLBACK_SPEC D4). None sinks (coerced to -1e9 so it
    ranks last, ascending sort)."""
    m = entry["metrics"]
    leg_force = m.get("leg_force_from_65d_low")
    lf = leg_force if leg_force is not None else -1e9
    d = m.get("ma_distance_pct")
    d = d if d is not None else 1e9
    return (-lf, d, -_liveness(entry))


def _tightness_proximity_rank_key(entry: dict[str, Any]):
    # reversal + strong-start-ready: ascending prev-day tightness percentile
    # (Tightness Study: "the tighter the stock is, the more it can improve
    # the odds"), liveness as tiebreak.
    t = entry["metrics"].get("prev_day_tightness_pctile")
    return (t if t is not None else 1e9, -_liveness(entry))


_ARCHETYPE_RANKERS: dict[str, tuple[Any, bool]] = {
    # key_fn, reverse (True = higher-is-better)
    "pullback_to_rising_ma": (_pullback_leg_force_rank_key, False),
    "reversal": (_tightness_proximity_rank_key, False),
    "strong_start_ready": (_tightness_proximity_rank_key, False),
}


def _apply_size_control(bucket: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_archetype: dict[str, list[dict[str, Any]]] = {}
    for entry in bucket:
        for a in entry["archetypes"]:
            by_archetype.setdefault(a, []).append(entry)
    keep_symbols: set[str] = set()
    for archetype, entries in by_archetype.items():
        key, reverse = _ARCHETYPE_RANKERS.get(archetype, (_velocity_score, True))
        ranked = sorted(entries, key=key, reverse=reverse)
        # K7 fix: the original clauses making the top quartile AND every
        # multi-archetype name immune from the cap were both UNBOUNDED --
        # wide-firing archetypes + heavy tag overlap drove buckets to
        # 315-470/day (vs the ~120/day ceiling). A hard per-archetype top-N
        # keep, with archetype-appropriate ranking, is the whole size
        # control now; multi-archetype names still get one shot per tag.
        keep_symbols.update(e["symbol"] for e in ranked[:CAP_PER_ARCHETYPE])
    return [e for e in bucket if e["symbol"] in keep_symbols]


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
