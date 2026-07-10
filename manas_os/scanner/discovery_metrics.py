"""WAVE K K3 — additive discovery metrics for the Stage-1 SENSITIVE BUCKET.

Pure functions over oldest-first OHLCV bar dicts (same shape as
`candidates.load_symbol_bars`: date/open/high/low/close/prev_close/volume/
delivery_qty/delivery_pct). One writer per metric, shadow-only this wave —
nothing here gates scan_candidates. Every threshold is corpus-cited per
`design/knowledge/PLAYBOOK_TO_TOOL_MAP.md` §B; do not invent or retune values
here (retuning is a separate, explicitly-scoped wave).

Reuses `engine/manas_indicators` where it already computes the thing
(purple_dot, persistency) rather than re-deriving.
"""
from __future__ import annotations

from typing import Any

from manas_os.engine import manas_indicators as mi

Bar = dict[str, Any]


def _num(bar: Bar, key: str) -> float | None:
    v = bar.get(key)
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def adr20(bars: list[Bar]) -> float | None:
    """Average Daily Range over the trailing 20 sessions, % of close.

    Cite: TTM-H-III3 / WK groww2 — "ADR20 in top universe percentile; sort
    scan by ADR desc." Same (high-low)/close*100 formula candidates.py's
    symbol_timing already uses for its 14d display ADR (candidates.py L280-
    284); widened to the spec's 20d window and promoted from display-only to
    a scoreable metric (PLAYBOOK_TO_TOOL_MAP §B row 3).
    """
    window = bars[-20:]
    ranges = []
    for b in window:
        h, l, c = _num(b, "high"), _num(b, "low"), _num(b, "close")
        if h is not None and l is not None and c:
            ranges.append((h - l) / c * 100.0)
    if not ranges:
        return None
    return sum(ranges) / len(ranges)


def purple_dot_count_60d(bars: list[Bar]) -> int:
    """Count of >5% move on >5 lakh volume days over the trailing 60 sessions.

    Cite: WK groww2 / CH3.1 — "dot prints on >5% move (either direction) on
    >5 lakh volume; ZERO dots = skip regardless of setup." Reuses
    engine.manas_indicators.purple_dot (already ported); vol_floor is set to
    the corpus's ">5 lakh" (500,000 shares), not that function's own
    1,000,000-share default.
    """
    window = bars[-60:]
    flags = mi.purple_dot(window, vol_floor=500_000, pct=5)
    return sum(1 for f in flags if f)


def pct_up_from_65d_low(bars: list[Bar]) -> float | None:
    """% up from the trailing 65-session (3-month) low — Arora's buying-force
    "green number", measured off the LOW not off the 52w high.

    Cite: WK groww2 / CH3.1 — "stock up >=30-35% from its 3-month (65-day)
    low. His #1 momentum signal." PLAYBOOK_TO_TOOL_MAP §B row 2 (replaces the
    52w-high anchor as the buying-force test).
    """
    window = bars[-65:]
    lows = [_num(b, "low") for b in window if _num(b, "low") is not None]
    close = _num(bars[-1], "close") if bars else None
    if not lows or close is None:
        return None
    low65 = min(lows)
    if low65 <= 0:
        return None
    return (close - low65) / low65 * 100.0


def _leg_high(bars: list[Bar], leg_lookback: int = 60) -> float | None:
    """Highest high of the trailing `leg_lookback` sessions (the current "leg
    high") — ONE shared leg-high identification used by both
    `correction_depth_from_leg_high` and `leg_force_from_65d_low` (K4.1: do
    not re-derive the same concept twice)."""
    window = bars[-leg_lookback:]
    highs = [_num(b, "high") for b in window if _num(b, "high") is not None]
    if not highs:
        return None
    return max(highs)


def correction_depth_from_leg_high(bars: list[Bar], leg_lookback: int = 60) -> float | None:
    """% pullback of the latest close from the highest high of the trailing
    `leg_lookback` sessions (the current "leg high").

    Cite: WK groww2 — "pullback <=25-30% from leg high; >30% = avoid. Good
    examples 17/19/26%; bad 45%." Also SG-50%-Fall (reject >40-50% down-base
    reads as a distinct failure, not this metric's job to gate — K3 is
    shadow-only). leg_lookback=60 sessions (~3 months) matches the same
    "recent swing" window used by pct_up_from_65d_low above.
    """
    leg_high = _leg_high(bars, leg_lookback)
    close = _num(bars[-1], "close") if bars else None
    if leg_high is None or leg_high <= 0 or close is None:
        return None
    return (leg_high - close) / leg_high * 100.0


def leg_force_from_65d_low(bars: list[Bar], leg_lookback: int = 60) -> float | None:
    """% the PRIOR LEG's high sits above the trailing 65-session low —
    "did the leg that produced the current pullback itself show 30%+ buying
    force", re-anchored off the leg high instead of TODAY's close.

    Cite: WK groww2/CH3.1 — the same ">=30-35% up from 3-month low" test as
    `pct_up_from_65d_low`, but WAVE K6 found that anchoring it to the CURRENT
    close re-kills every reversal/pullback pick: Arora buys 3-5 red days INTO
    a correction, exactly when current-price force is at its lowest, but the
    LEG that preceded the pullback still shows the buying force groww2
    actually means. leg_high reuses `_leg_high` (correction_depth_from_
    leg_high's own leg-high identification, same leg_lookback default) —
    one definition, shared, not re-derived. low65 reuses the same trailing-65
    -session low window as `pct_up_from_65d_low`.
    """
    leg_high = _leg_high(bars, leg_lookback)
    lows = [_num(b, "low") for b in bars[-65:] if _num(b, "low") is not None]
    if leg_high is None or leg_high <= 0 or not lows:
        return None
    low65 = min(lows)
    if low65 <= 0:
        return None
    return (leg_high - low65) / low65 * 100.0


def prev_day_tightness_pctile(bars: list[Bar]) -> float | None:
    """Percentile rank of YESTERDAY's daily range among the stock's own
    trailing 20-day ranges (0 = tightest range in the window, 100 = widest).

    Cite: WK Strong_Start_Tightness_Study.md — "prev-day range in bottom
    pctile of own 20d ranges + uptrend" (archetype a, Strong-Start-ready).
    Percentile is NATURE-RELATIVE by construction (own 20d history, not a
    universe-wide cutoff) per WK CH3.1's nature-relative principle.
    """
    if len(bars) < 2:
        return None
    prior = bars[:-1]
    window = prior[-20:]
    ranges = []
    for b in window:
        h, l = _num(b, "high"), _num(b, "low")
        if h is not None and l is not None:
            ranges.append(h - l)
    if len(ranges) < 5:
        return None
    yday = bars[-2]
    yh, yl = _num(yday, "high"), _num(yday, "low")
    if yh is None or yl is None:
        return None
    yday_range = yh - yl
    below_or_equal = sum(1 for r in ranges if r <= yday_range)
    return below_or_equal / len(ranges) * 100.0


def range_contraction_flag(bars: list[Bar]) -> bool:
    """VCP-coil flag: today's ATR20 sits in the bottom quartile of ATR20
    observed over the trailing 60 sessions AND the last 3 ATR20 readings are
    non-increasing (successive contraction), i.e. "100->70->80->90/95 then
    break" — a genuinely CONTRACTING coil, not just a currently-low ATR.

    Cite: WK groww4/groww2 — "contracting ranges... For me VCP is a
    principle, not a pattern." TTM-S14 — VCP tightness measured via ATR, not
    volume rules.
    """
    if len(bars) < 65:
        return False
    trs = mi._true_ranges(bars)
    atr20 = mi._rma(trs, 20)
    window = atr20[-60:]
    clean = [v for v in window if v is not None]
    if len(clean) < 20:
        return False
    latest = clean[-1]
    sorted_clean = sorted(clean)
    cutoff_idx = max(0, len(sorted_clean) // 4 - 1)
    bottom_quartile_ceiling = sorted_clean[cutoff_idx]
    in_bottom_quartile = latest <= bottom_quartile_ceiling
    last3 = [v for v in atr20[-3:] if v is not None]
    # strictly contracting (not merely flat) -- a flat-but-low ATR is a quiet
    # stock, not a coiling one; the corpus's "100->70->80->90/95" progression
    # requires genuine shrinkage.
    contracting = len(last3) == 3 and last3[0] > last3[1] >= last3[2] and last3[0] > last3[2]
    return bool(in_bottom_quartile and contracting)


def persistency_counts(bars: list[Bar]) -> dict[str, int | None]:
    """Latest persistency `count` for the 10/21/50/200 EMA persistency-state
    machines (ported manas_indicators.persistency), keyed to the P0 archetype
    "persistent-momentum": close >10EMA >=20d, >20EMA >=30d, >50EMA >=50d,
    >200EMA >=150d (TTM-H-III1/III2). manas_indicators ports 10/21/50/200 EMA
    lengths (persistency_ema_bundle); 21 stands in for the corpus's "20EMA"
    (already the ported indicator's convention — not re-derived here).
    """
    bundle = mi.persistency_ema_bundle(bars)
    out: dict[str, int | None] = {}
    for key, rows in bundle.items():
        out[key] = rows[-1]["count"] if rows else None
    return out


PERSISTENCY_THRESHOLDS = {
    # Cite: TTM-H-III1/III2 — close >10EMA>=20d, >20EMA>=30d, >50EMA>=50d,
    # >200EMA>=150d. manas_indicators' 21EMA persistency stands in for "20EMA".
    "ema10": 20,
    "ema21": 30,
    "ema50": 50,
    "ema200": 150,
}


def is_persistent_momentum(counts: dict[str, int | None]) -> bool:
    """True if ANY EMA leg's persistency count has reached its TTM-H-III1/2
    threshold (positive count = still above the MA in an unbroken run)."""
    for key, threshold in PERSISTENCY_THRESHOLDS.items():
        c = counts.get(key)
        if c is not None and c >= threshold:
            return True
    return False
