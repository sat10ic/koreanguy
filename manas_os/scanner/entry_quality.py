"""scanner/entry_quality.py — WAVE_J counterfactual entry-quality refusals.

One writer per metric (design/WAVE_J_SPEC.md J1). Each function wraps the
already-ported, already-tested indicators in engine/manas_indicators.py and
returns a gates.py-shaped verdict: ``{"pass": bool, "reason": str|None,
"evidence": {...}}``. These are NOT wired into the live cascade, risk/plan.py,
sizing, chair, debate, or rank (WAVE_J_SPEC.md §4.6) — they exist so
backtest/entry_variants.py can compose counterfactual refusals over the
already-persisted candidate cohort.

No DB access. No ml import. No risk/plan import. Pure functions over
oldest-first OHLCV bar lists (the same convention as manas_indicators.py).

Thresholds are module constants; every one cites the Arora source file +
concept it operationalizes, verified to exist via Glob before this module was
written:
  - design/agents/LENS_STRONG_START.md (Arora entry-process digest)
  - design/study/Manas Arora/Course Notes/6 Manas Entry.md (primary source
    chapter, "6 Manas Entry")
  - design/study/Manas Arora/Course Notes/cleaned/Manas/
    Strong_Start_Tightness_Study.md (empirical tightness-precondition study)
"""
from __future__ import annotations

from typing import Any

from manas_os.engine import manas_indicators as mi

Bar = dict[str, Any]

# --- LOCKED-for-this-wave constants (evaluation only; see WAVE_J_SPEC §4.1) -------

# H1 compression-first (WAVE_J_SPEC.md §2 H1). rmv rank<=2 is manas_indicators.rmv's
# own existing rank scale (rank 1 = A+ AND local trough, rank 2 = A+ tight/vdu
# setup); RMV_TIGHT_MAX=15 mirrors manas_indicators.rmv's own `aplus` threshold
# (rmv_val <= 15) used to define tightness_setup/vdu_setup eligibility — not a
# new fitted number, the module's existing gate reused here.
RMV_RANK_MAX = 2
RMV_TIGHT_MAX = 15.0
# Source for the compression precondition itself: Strong_Start_Tightness_Study.md
# ("Before many good Strong Start results, the previous day was really tight" —
# ">80% of the cases" empirical finding); LENS_STRONG_START.md §1 restates it.

# H2 leg-freshness (WAVE_J_SPEC.md §2 H2).
# STALE_COUNT=8: persistency(10EMA) trend-age guard. Chosen to sit just above
# gates.py's own PULLBACK_AGE_MAX=15 pullback window scaled to the ~half-ratio
# between a 10-bar EMA and the pivot/breakout-age tracked in gates.py; recorded
# here as a counterfactual a-priori pick, not tuned on the 55-trade cohort
# (WAVE_J_SPEC.md §4.1 binding).
STALE_COUNT = 8
# GREEN_STREAK_MAX=3 (i.e. refuse on the 4th consecutive green day, streak>=4):
# LENS_STRONG_START.md §3 "Buying on the 4th (or later) green day in a row and
# calling it a Strong Start — explicitly invalidated... hard disqualifier
# regardless of outcome"; Strong_Start_Tightness_Study.md "The invalid Strong
# Start: buying on the fourth green day" (DLF example, excluded from Arora's own
# win sample on principle).
GREEN_STREAK_MAX = 3

# H4 trigger-day quality (WAVE_J_SPEC.md §2 H4).
# GAP_MAX_PCT=5.0: "6 Manas Entry.md" summary — "avoid it if the gap is already
# some 5-6%. It will really disturb your risk-reward"; LENS_STRONG_START.md §3
# repeats "Gap already 5-6%+ at open". We take the conservative (lower) bound
# of the quoted 5-6% range as the refusal threshold.
GAP_MAX_PCT = 5.0
# CLOSE_UPPER_HALF_MIN=0.5: WAVE_J_SPEC.md §2 H4 itself specifies "close-in-
# upper-half" as the trigger-day-quality component; Arora's sources describe
# the *qualitative* requirement (price holding above the prior close/high, "the
# low of the next day should not really breach the previous day's close" —
# 6 Manas Entry.md) but give no exact fraction, so 0.5 (literal upper half of
# the day's own high-low range) is the direct, undistorted reading of "upper
# half" — not a fitted number.
CLOSE_UPPER_HALF_MIN = 0.5
STRONG_VOLUME_STATES = {"bull_pp", "high_up"}

# H5 mswing filter (WAVE_J_SPEC.md §2 H5).
MSWING_REFUSE_COLORS = {"down", "neutral_negative"}

# H6 burst exhaustion (WAVE_J_SPEC.md §2 H6).
# BURST_LOOKBACK=63: reuses the existing quarterly window already wired in
# agents/context_pack.py (`manas_indicators.burst_power(bars, 63)`) — not a new
# fitted number, the codebase's own established burst-power evaluation window.
BURST_LOOKBACK = 63
BURST_COUNT19_MIN = 1
BURST_ROUNDED_MIN = 8


def _verdict(ok: bool, reason: str | None, **evidence: Any) -> dict[str, Any]:
    return {"pass": ok, "reason": None if ok else reason, "evidence": evidence}


def rmv_eligible(bars: list[Bar]) -> dict[str, Any]:
    """H1 compression-first: eligible only if trigger-day rmv rank<=2 OR
    (rmv<=RMV_TIGHT_MAX AND (tightness_setup OR vdu_setup))."""
    series = mi.rmv(bars)
    if not series:
        return _verdict(False, "no bars to compute RMV", rmv=None, rank=None)
    row = series[-1]
    rank, rmv_val = row.get("rank"), row.get("rmv")
    tight_or_vdu = bool(row.get("tightness_setup") or row.get("vdu_setup"))
    ok = bool(
        (rank is not None and rank != 0 and rank <= RMV_RANK_MAX)
        or (rmv_val is not None and rmv_val <= RMV_TIGHT_MAX and tight_or_vdu)
    )
    evidence = {
        "rmv": None if rmv_val is None else round(rmv_val, 2),
        "rank": rank,
        "tightness_setup": row.get("tightness_setup"),
        "vdu_setup": row.get("vdu_setup"),
    }
    reason = None
    if not ok:
        reason = (
            f"no coil: rmv rank {rank} (need <={RMV_RANK_MAX}) and rmv "
            f"{'unknown' if rmv_val is None else round(rmv_val, 1)} with tightness/vdu "
            f"{tight_or_vdu} (need <={RMV_TIGHT_MAX} AND tight/vdu)"
        )
    return _verdict(ok, reason, **evidence)


def _green_streak(bars: list[Bar]) -> int:
    """Count consecutive close > prev_close days ending at the last bar."""
    closes = mi._closes(bars)
    streak = 0
    for i in range(len(closes) - 1, 0, -1):
        c, pc = closes[i], closes[i - 1]
        if c is None or pc is None or not (c > pc):
            break
        streak += 1
    return streak


def leg_fresh(bars: list[Bar]) -> dict[str, Any]:
    """H2 leg-freshness: HARD refuse 4th-or-later consecutive green day;
    refuse persistency(10EMA) count >= STALE_COUNT."""
    streak = _green_streak(bars)
    if streak >= GREEN_STREAK_MAX:
        return _verdict(
            False,
            f"{streak + 1}th (or later) consecutive green day — Arora hard "
            f"disqualifier regardless of outcome (Tightness Study DLF example)",
            green_streak=streak, persistency_count=None,
        )
    series = mi.persistency(bars, "EMA", 10)
    if not series:
        return _verdict(False, "no bars to compute persistency", green_streak=streak,
                        persistency_count=None)
    count = series[-1]["count"]
    ok = bool(count is not None and count < STALE_COUNT)
    reason = None
    if not ok:
        reason = f"persistency(10EMA) count {count} >= {STALE_COUNT} — leg is stale"
    return _verdict(ok, reason, green_streak=streak, persistency_count=count)


def strong_start_quality(bars: list[Bar]) -> dict[str, Any]:
    """H4 trigger-day quality: strong_start True AND gap<=GAP_MAX_PCT AND
    close-in-upper-half AND volume state in {bull_pp, high_up} or
    range-expansion."""
    ss_series = mi.ss_rvol(bars)
    vol_series = mi.simple_volume(bars)
    if not ss_series or not vol_series:
        return _verdict(False, "no bars to compute strong-start quality",
                        strong_start=None)
    last_bar = bars[-1]
    prev_close = mi._num(bars[-2], "close") if len(bars) > 1 else None
    open_ = mi._num(last_bar, "open")
    high = mi._num(last_bar, "high")
    low = mi._num(last_bar, "low")
    close = mi._num(last_bar, "close")

    strong_start = ss_series[-1]["strong_start"]
    gap_pct = (
        (open_ - prev_close) / prev_close * 100.0
        if open_ is not None and prev_close not in (None, 0) else None
    )
    close_pos = (
        (close - low) / (high - low) if None not in (close, high, low) and high != low
        else None
    )
    vol_state = vol_series[-1]["state"]
    expansion = _range_expansion(bars)

    evidence = {
        "strong_start": strong_start,
        "gap_pct": None if gap_pct is None else round(gap_pct, 2),
        "close_position": None if close_pos is None else round(close_pos, 2),
        "volume_state": vol_state,
        "range_expanded": expansion,
    }

    if not strong_start:
        return _verdict(False, "not a Strong Start trigger day (gap/hold-above-close check failed)",
                        **evidence)
    if gap_pct is None or gap_pct > GAP_MAX_PCT:
        return _verdict(False, f"gap {gap_pct} exceeds {GAP_MAX_PCT}% ceiling — risk-reward destroyed",
                        **evidence)
    if close_pos is None or close_pos < CLOSE_UPPER_HALF_MIN:
        return _verdict(False, f"close position {close_pos} below upper-half of day's range",
                        **evidence)
    if vol_state not in STRONG_VOLUME_STATES and not expansion:
        return _verdict(False, f"volume state '{vol_state}' not in {sorted(STRONG_VOLUME_STATES)} "
                        f"and no range-expansion confirm", **evidence)
    return _verdict(True, None, **evidence)


def _range_expansion(bars: list[Bar]) -> bool:
    """TR of the last bar >= 1.2x ATR14 (matches gates.range_expansion logic,
    reimplemented locally to keep this module free of a gates.py import)."""
    trs: list[float] = []
    for i, bar in enumerate(bars):
        high, low = mi._num(bar, "high"), mi._num(bar, "low")
        prev_close = mi._num(bars[i - 1], "close") if i > 0 else None
        if high is None or low is None or prev_close is None:
            continue
        trs.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))
    if not trs:
        return False
    tr = trs[-1]
    window = trs[-14:]
    atr14 = sum(window) / len(window) if len(window) == 14 else None
    return bool(atr14 is not None and tr >= 1.2 * atr14)


def mswing_ok(bars: list[Bar], index_bars: list[Bar]) -> dict[str, Any]:
    """H5 mswing filter: refuse color in {down, neutral_negative} vs index."""
    series = mi.mswing(bars, index_bars)
    if not series:
        return _verdict(False, "no bars to compute mswing", color=None)
    row = series[-1]
    color = row.get("color")
    ok = color not in MSWING_REFUSE_COLORS
    reason = None if ok else f"mswing color '{color}' vs index — stock lags/falls faster than the index"
    return _verdict(ok, reason, color=color, stock_mswing=row.get("mswing"),
                    index_mswing=row.get("index_mswing"))


def burst_exhausted(bars: list[Bar]) -> dict[str, Any]:
    """H6 burst exhaustion guard: refuse count_19>=1 OR rounded>=8 over the
    BURST_LOOKBACK window (climax exhaustion — evidence chip / guard only)."""
    result = mi.burst_power(bars, BURST_LOOKBACK)
    count_19 = result.get("count_19", 0)
    rounded = result.get("rounded", 0)
    exhausted = bool(count_19 >= BURST_COUNT19_MIN or rounded >= BURST_ROUNDED_MIN)
    ok = not exhausted
    reason = None
    if not ok:
        reason = (f"burst exhaustion: count_19={count_19} (>={BURST_COUNT19_MIN}) or "
                  f"rounded={rounded} (>={BURST_ROUNDED_MIN}) — climax move, refusing the chase")
    return _verdict(ok, reason, count_19=count_19, rounded=rounded,
                    power_value=result.get("power_value"))
