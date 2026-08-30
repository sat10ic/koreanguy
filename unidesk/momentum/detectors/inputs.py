"""Point-in-time setup-detector inputs computed from a completed bar series.

Every value is derived from chronological OHLCV (plus optional delivery and
an already-computed RS rank). Warm-up and missing data become None — never
zero-filled, never guessed (R12). Thresholds do not live here; this module
owns measurement, the detectors own rules.
"""
from __future__ import annotations

from typing import Optional, Sequence

from unidesk.contracts.base import ContractError, require_float
from unidesk.momentum.features.adr_atr import adr
from unidesk.momentum.features.participation import rvol
from unidesk.momentum.features.rs import window_return
from unidesk.momentum.features.trend import ema
from unidesk.momentum.primitives.contraction import base_depth_pct, range_contraction_ratio


def _f(values: Sequence[float], name: str) -> list:
    return [require_float(v, f"{name}[{i}]") for i, v in enumerate(values)]


def _round(value: Optional[float], ndigits: int) -> Optional[float]:
    return None if value is None else round(value, ndigits)


# ``blue_sky`` claims to mean "genuinely at/above the symbol's known price
# history." Below this many loaded bars, ``max(h[:-1])`` is nothing more
# than the edge of whatever window happened to be passed in, and (for
# n <= base_window + 1) is *identical* to the base-breakout pivot slice,
# which mechanically forces blue_sky True alongside close_cleared_pivot and
# bypasses the room-vs-ADR check base_breakout() relies on for short-history
# symbols. 61 matches the nightly scan's own documented floor for "enough
# bars to trust a high" (scan.py: 20 prior + 20 window + 20 EMA + 1) so the
# meaning of blue_sky does not depend on which caller happens to invoke this
# function. Below the floor the value is unresolved (R12) — None, never a
# guess — and base_breakout()'s room rule (setups.py) already treats a None
# blue_sky as INSUFFICIENT_DATA rather than a silent pass.
BLUE_SKY_MIN_SESSIONS = 61


def compute_setup_inputs(
    *,
    opens: Sequence[float],
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    volumes: Sequence[float],
    delivery_pcts: Sequence[Optional[float]] | None = None,
    rs_rank: Optional[float] = None,
    adr_span: int = 20,
    rvol_span: int = 20,
    contraction_recent_n: int = 5,
    contraction_prior_n: int = 20,
    base_window: int = 20,
) -> dict:
    """Return a flat dict of named detector inputs for the LAST bar.

    ``listing_age_sessions`` is the length of the supplied series — a proxy
    for true listing age equal to the store's first bar, recorded honestly
    so IPO-base fixtures never pretend we have a listing calendar.
    """
    o = _f(opens, "opens")
    h = _f(highs, "highs")
    l = _f(lows, "lows")
    c = _f(closes, "closes")
    v = _f(volumes, "volumes")
    n = len(c)
    if not (len(o) == len(h) == len(l) == len(v) == n):
        raise ContractError("opens/highs/lows/closes/volumes must have equal length")
    if n < 2:
        raise ContractError("need at least 2 sessions to form setup inputs")
    if delivery_pcts is not None and len(delivery_pcts) != n:
        raise ContractError("delivery_pcts length must match the bar series")

    last_o, last_h, last_l, last_c, last_v = o[-1], h[-1], l[-1], c[-1], v[-1]
    prev_o, prev_h, prev_l, prev_c, prev_v = o[-2], h[-2], l[-2], c[-2], v[-2]

    gap_pct = (last_o / prev_c - 1.0) * 100.0 if prev_c > 0 else None
    day_range = last_h - last_l
    close_location = (last_c - last_l) / day_range if day_range > 0 else None

    is_inside_bar = last_h <= prev_h and last_l >= prev_l
    mother_range_pct = (prev_h - prev_l) / prev_c * 100.0 if prev_c > 0 else None
    volume_ratio_bar_to_mother = (last_v / prev_v) if prev_v > 0 else None

    adr_series = adr(h, l, adr_span)
    adr_value = adr_series[-1]
    adr_pct = (adr_value / last_c * 100.0) if adr_value and last_c > 0 else None

    rvol_series = rvol(v, rvol_span)
    rvol_value = rvol_series[-1]

    contraction = range_contraction_ratio(h, l, contraction_recent_n, contraction_prior_n)

    listing_age_sessions = n
    listing_high = max(h)
    distance_from_listing_high_pct = (
        (listing_high - last_c) / listing_high * 100.0 if listing_high > 0 else None
    )

    base_depth = None
    if n >= base_window + 2:
        try:
            base_depth = base_depth_pct(h, l, n - base_window, n)
        except ContractError:
            base_depth = None

    pre_breakout_pivot = None
    close_cleared_pivot = None
    base_breakout_depth = None
    base_breakout_contraction = None
    if n >= base_window + 1:
        prior_highs = h[-base_window - 1:-1]
        prior_lows = l[-base_window - 1:-1]
        pre_breakout_pivot = max(prior_highs)
        close_cleared_pivot = bool(last_c > pre_breakout_pivot)
        if pre_breakout_pivot > 0:
            base_breakout_depth = (pre_breakout_pivot - min(prior_lows)) / pre_breakout_pivot * 100.0
    if n >= contraction_recent_n + contraction_prior_n + 1:
        base_breakout_contraction = range_contraction_ratio(
            h[:-1], l[:-1], contraction_recent_n, contraction_prior_n,
        )

    prior_listing_high = max(h[:-1]) if n >= BLUE_SKY_MIN_SESSIONS else None
    # Strict ">" to match close_cleared_pivot's semantics: a close sitting
    # exactly at the prior high has not yet made a new one, and (via
    # overhead_room_adr below) correctly yields zero room rather than a
    # bypass.
    blue_sky = bool(last_c > prior_listing_high) if prior_listing_high is not None else None
    overhead_room_adr = None
    if blue_sky is False and prior_listing_high and adr_pct and adr_pct > 0:
        overhead_room_adr = ((prior_listing_high - last_c) / last_c * 100.0) / adr_pct

    e21 = ema(c, 21)
    ema21 = e21[-1]
    proximity_to_anchor_pct = None
    if ema21 and ema21 > 0:
        proximity_to_anchor_pct = abs(last_c - ema21) / ema21 * 100.0

    pullback_volume_ratio = None
    if n >= 6:
        prior_mean = sum(v[-6:-1]) / 5.0
        if prior_mean > 0:
            pullback_volume_ratio = last_v / prior_mean

    reclaimed = None
    if ema21 is not None and n >= 6:
        recently_below = any(c[i] < ema21 for i in range(n - 6, n - 1))
        reclaimed = bool(last_c > ema21 and recently_below)

    returns = window_return(c, 20)
    rs_improving = None
    if n >= 26 and returns[-1] is not None and returns[-6] is not None:
        rs_improving = bool(returns[-1] > returns[-6])

    failed_breakdown = None
    if n >= 7:
        prior_floor = min(l[-7:-1])
        failed_breakdown = bool(last_l < prior_floor and last_c > prior_floor)

    delivery_ratio = None
    if delivery_pcts is not None:
        from unidesk.contracts.base import ContractError as _CE
        from unidesk.momentum.features.participation import delivery_volume_ratio
        try:
            series = delivery_volume_ratio(list(v), list(delivery_pcts), rvol_span)
            delivery_ratio = series[-1] if series else None
        except _CE:
            delivery_ratio = None

    breakout_rvol = rvol_value  # same measurement; named for the breakout detector

    return {
        "gap_pct": _round(gap_pct, 3),
        "rvol": _round(rvol_value, 3),
        "close_location": _round(close_location, 3),
        "delivery_ratio": _round(delivery_ratio, 3),
        "listing_age_sessions": listing_age_sessions,
        "base_depth_pct": _round(base_depth, 3),
        "contraction_ratio": _round(contraction, 3),
        "rs_rank": _round(rs_rank, 1) if rs_rank is not None else None,
        "distance_from_listing_high_pct": _round(distance_from_listing_high_pct, 3),
        "is_inside_bar": is_inside_bar,
        "mother_range_pct": _round(mother_range_pct, 3),
        "volume_ratio_bar_to_mother": _round(volume_ratio_bar_to_mother, 3),
        "breakout_rvol": _round(breakout_rvol, 3),
        "pre_breakout_pivot": _round(pre_breakout_pivot, 3),
        "close_cleared_pivot": close_cleared_pivot,
        "base_breakout_depth_pct": _round(base_breakout_depth, 3),
        "base_breakout_contraction_ratio": _round(base_breakout_contraction, 3),
        "blue_sky": blue_sky,
        "overhead_room_adr": _round(overhead_room_adr, 3),
        "proximity_to_anchor_pct": _round(proximity_to_anchor_pct, 3),
        "pullback_volume_ratio": _round(pullback_volume_ratio, 3),
        "adr_pct": _round(adr_pct, 3),
        "reclaimed": reclaimed,
        "volume_expansion": _round(rvol_value, 3),
        "rs_improving": rs_improving,
        "failed_breakdown": failed_breakdown,
        "avwap_extension_adr": None,  # no AVWAP anchor in the EOD series yet
    }
