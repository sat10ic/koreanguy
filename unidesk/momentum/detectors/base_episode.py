"""Versioned clean-room base episodes and explainable screen presets.

This is a domain adapter over ``base_pattern``. It records the observation
time of annotations and deliberately fails closed when a public-style preset
needs context (listing age or high history) that daily base geometry alone
does not provide.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Sequence

from unidesk.contracts.base import ContractError, require_str
from unidesk.momentum.detectors.base_pattern import (
    BasePattern,
    BaseRules,
    BaseVerdict,
    DailyBar,
    detect_base_pattern,
)
from unidesk.momentum.features.adr_atr import atr
from unidesk.momentum.primitives.pivots import PivotKind, fractal_pivots


BASE_EPISODE_METHOD_VERSION = "cleanroom-base-v1"


class BaseAnnotationKind(Enum):
    SQUAT = "squat"
    FAILED_POKE = "failed_poke"
    BREAKOUT = "breakout"


class BasePreset(Enum):
    VCP = "vcp"
    BLUE_SKY = "blue_sky"
    MULTI_YEAR = "multi_year"
    IPO_BASE = "ipo_base"


@dataclass(frozen=True)
class BaseAnnotation:
    kind: BaseAnnotationKind
    occurred_at: object
    known_at: object


@dataclass(frozen=True)
class BaseEpisode:
    episode_id: str
    symbol: str
    as_of: object
    known_at: object
    method_version: str
    adjustment_basis_hash: str
    base_start: object
    base_end: object
    base_sessions: int
    base_weeks: float
    pivot: float
    floor: float
    depth_pct: float
    coil_ratio: Optional[float]
    dry_ratio: Optional[float]
    dry_depth_ratio: Optional[float]
    rs_rank: Optional[int]
    verdict: BaseVerdict
    annotations: tuple[BaseAnnotation, ...]
    notes: tuple[str, ...]
    # N5 S_tight inputs (Wave C-2): derived from the bar series at
    # episode-creation time. All optional with defaults so existing
    # callers (test fixtures, report_json's _episode_dict) do not break.
    # When absent the tightness_score() caller sees None / empty and
    # coverage drops honestly — never a fabricated value (R12).
    pullback_depths: tuple[float, ...] = ()
    atrp_percentile: Optional[float] = None
    delivery_bottom_quintile: Optional[bool] = None
    rs_made_20d_low: Optional[bool] = None


@dataclass(frozen=True)
class ScreenMatch:
    preset: BasePreset
    episode_id: str
    included: bool
    failed_rules: tuple[str, ...]


def _pullback_depths_from_bars(
    bars: Sequence[DailyBar], *, pivot: float, base_start, base_end,
    swing_left_right: int,
) -> tuple[float, ...]:
    """Coarse clean-room proxy for the base's pullback structure (Wave C-2).

    Fractal LOW pivots inside the base window, depth measured from the base
    pivot: ``(pivot - low) / pivot * 100`` in the order encountered
    (chronological). This is a deterministic approximation of the spec's
    "pullback depth sequence" — it does not reconstruct any undisclosed
    swing-identification rule; it uses the same fractal pivots as the rest
    of the clean-room detector, documented honestly as a proxy. Fewer than
    two pullbacks yields an empty/1-element tuple and tightness_score()'s
    contraction monotonicity component then scores 0 (a single-leg move is
    not a coil). Point-in-time: only pivots observed at the final bar are
    used.
    """
    if not bars:
        return ()
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    pivots = fractal_pivots(highs, lows, swing_left_right)
    start_i = next((i for i, b in enumerate(bars) if b.day >= base_start), 0)
    end_i = next((i for i, b in enumerate(bars) if b.day > base_end), len(bars))
    depths: list[float] = []
    for p in pivots:
        if p.kind is not PivotKind.LOW:
            continue
        if not (start_i <= p.index <= end_i):
            continue
        if p.known_at > len(bars) - 1:
            continue  # not observable at the final bar yet (point-in-time)
        if p.price <= 0 or pivot <= 0:
            continue
        depths.append(round((pivot - p.price) / pivot * 100.0, 3))
    return tuple(depths)


def _atrp_percentile_from_bars(bars: Sequence[DailyBar], *, window: int = 20) -> Optional[float]:
    """ATR% percentile (Wave C-2): current ATR% rank within its own trailing
    ``window`` values (0=lowest .. 100=highest). A coarse, self-consistent,
    point-in-time proxy for the spec's ATR-percentile contributor — computed
    only from the supplied bar series, never a cross-sectional claim.
    Unresolved (None) below ``window+1`` bars or when ATR is unavailable
    (R12) — the caller's tightness_score() coverage then drops honestly.
    """
    if len(bars) < window + 1:
        return None
    closes = [b.close for b in bars]
    if any(c <= 0 for c in closes[-window - 1:]):
        return None
    atrp_series = atr(
        highs=[b.high for b in bars],
        lows=[b.low for b in bars],
        closes=closes,
        span=10,
    )
    if not atrp_series or len(atrp_series) < window:
        return None
    current = atrp_series[-1]
    past = [v for v in atrp_series[-window - 1:-1] if v is not None]
    if not past or current is None:
        return None
    below = sum(1 for v in past if v < current)
    return round(below / len(past) * 100.0, 3)


def _episode_from_pattern(
    *, symbol: str, pattern: BasePattern, as_of: object,
    adjustment_basis_hash: str, method_version: str,
    bars: Optional[Sequence[DailyBar]] = None,
    delivery_bottom_quintile: Optional[bool] = None,
    rs_made_20d_low: Optional[bool] = None,
) -> Optional[BaseEpisode]:
    if pattern.verdict is BaseVerdict.INSUFFICIENT_DATA:
        return None
    required = (
        pattern.base_start, pattern.base_end, pattern.base_sessions,
        pattern.base_weeks, pattern.pivot, pattern.depth_pct,
    )
    if any(value is None for value in required):
        return None
    annotations: list[BaseAnnotation] = [
        BaseAnnotation(BaseAnnotationKind.SQUAT, day, day)
        for day in pattern.squat_dates
    ]
    # Failed poke confirmation uses later bars. The underlying detector only
    # yields it after that confirmation, so it is known no earlier than as_of.
    annotations.extend(
        BaseAnnotation(BaseAnnotationKind.FAILED_POKE, day, as_of)
        for day in pattern.failed_poke_dates
    )
    if pattern.breakout_date is not None:
        annotations.append(
            BaseAnnotation(BaseAnnotationKind.BREAKOUT, pattern.breakout_date, pattern.breakout_date)
        )
    pivot = float(pattern.pivot)
    floor = pivot * (1 - float(pattern.depth_pct) / 100)
    # Wave C-2 S_tight inputs (all point-in-time, coarse-proxy documented):
    pullback_depths = (
        _pullback_depths_from_bars(
            bars, pivot=pivot, base_start=pattern.base_start,
            base_end=pattern.base_end, swing_left_right=7,
        )
        if bars else ()
    )
    atrp_percentile = _atrp_percentile_from_bars(bars) if bars else None
    return BaseEpisode(
        episode_id=f"{symbol}:{pattern.base_start.isoformat()}:{method_version}:{adjustment_basis_hash}",
        symbol=symbol, as_of=as_of, known_at=as_of,
        method_version=method_version, adjustment_basis_hash=adjustment_basis_hash,
        base_start=pattern.base_start, base_end=pattern.base_end,
        base_sessions=int(pattern.base_sessions), base_weeks=float(pattern.base_weeks),
        pivot=pivot, floor=floor, depth_pct=float(pattern.depth_pct),
        coil_ratio=pattern.coil_ratio, dry_ratio=pattern.dry_ratio,
        dry_depth_ratio=pattern.dry_depth_ratio, rs_rank=pattern.rs_rank,
        verdict=pattern.verdict, annotations=tuple(annotations), notes=pattern.notes,
        pullback_depths=tuple(pullback_depths),
        atrp_percentile=atrp_percentile,
        delivery_bottom_quintile=delivery_bottom_quintile,
        rs_made_20d_low=rs_made_20d_low,
    )


def base_episode_from_bars(
    *, symbol: str, bars: Sequence[DailyBar], rules: BaseRules = BaseRules(),
    rs_rank: Optional[int] = None, adjustment_basis_hash: str,
    method_version: str = BASE_EPISODE_METHOD_VERSION,
    delivery_bottom_quintile: Optional[bool] = None,
    rs_made_20d_low: Optional[bool] = None,
) -> Optional[BaseEpisode]:
    """Derive an episode at the final supplied EOD bar, or return ``None``.

    Wave C-2: the bar series is threaded through so the S_tight inputs
    (``pullback_depths``, ``atrp_percentile``) are derived point-in-time at
    episode creation; the caller may additionally supply the cross-sectional
    ``delivery_bottom_quintile`` / ``rs_made_20d_low`` flags (None here
    means the tightness_score() coverage drops honestly for those
    contributors, never a fabricated value)."""
    symbol = require_str(symbol, "symbol")
    adjustment_basis_hash = require_str(adjustment_basis_hash, "adjustment_basis_hash")
    method_version = require_str(method_version, "method_version")
    if not bars:
        return None
    pattern = detect_base_pattern(bars, rules=rules, rs_rank=rs_rank)
    return _episode_from_pattern(
        symbol=symbol, pattern=pattern, as_of=bars[-1].day,
        adjustment_basis_hash=adjustment_basis_hash, method_version=method_version,
        bars=bars,
        delivery_bottom_quintile=delivery_bottom_quintile,
        rs_made_20d_low=rs_made_20d_low,
    )


def match_base_preset(episode: BaseEpisode, preset: BasePreset) -> ScreenMatch:
    """Apply transparent screen rules without redetecting the base."""
    if not isinstance(preset, BasePreset):
        raise ContractError("preset must be a BasePreset")
    if preset is BasePreset.BLUE_SKY:
        failures = ("requires_52_week_high_context",)
    elif preset is BasePreset.MULTI_YEAR:
        failures = ("requires_multi_year_high_context",)
    elif preset is BasePreset.IPO_BASE:
        failures = ("requires_listing_age_sessions",)
    else:
        failures_list: list[str] = []
        if episode.base_weeks < 3:
            failures_list.append("base_weeks_below_3")
        if episode.depth_pct > 35:
            failures_list.append("base_depth_above_35")
        if episode.coil_ratio is None or episode.coil_ratio > 0.9:
            failures_list.append("coil_not_tight")
        if episode.dry_ratio is None or episode.dry_ratio > 0.9:
            failures_list.append("dry_not_quiet")
        if episode.rs_rank is None or episode.rs_rank < 70:
            failures_list.append("rs_below_70")
        if episode.verdict is BaseVerdict.INSUFFICIENT_DATA:
            failures_list.append("insufficient_base_data")
        failures = tuple(failures_list)
    return ScreenMatch(
        preset=preset, episode_id=episode.episode_id,
        included=not failures, failed_rules=failures,
    )
