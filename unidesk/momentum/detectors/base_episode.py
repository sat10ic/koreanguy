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


@dataclass(frozen=True)
class ScreenMatch:
    preset: BasePreset
    episode_id: str
    included: bool
    failed_rules: tuple[str, ...]


def _episode_from_pattern(
    *, symbol: str, pattern: BasePattern, as_of: object,
    adjustment_basis_hash: str, method_version: str,
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
    )


def base_episode_from_bars(
    *, symbol: str, bars: Sequence[DailyBar], rules: BaseRules = BaseRules(),
    rs_rank: Optional[int] = None, adjustment_basis_hash: str,
    method_version: str = BASE_EPISODE_METHOD_VERSION,
) -> Optional[BaseEpisode]:
    """Derive an episode at the final supplied EOD bar, or return ``None``."""
    symbol = require_str(symbol, "symbol")
    adjustment_basis_hash = require_str(adjustment_basis_hash, "adjustment_basis_hash")
    method_version = require_str(method_version, "method_version")
    if not bars:
        return None
    pattern = detect_base_pattern(bars, rules=rules, rs_rank=rs_rank)
    return _episode_from_pattern(
        symbol=symbol, pattern=pattern, as_of=bars[-1].day,
        adjustment_basis_hash=adjustment_basis_hash, method_version=method_version,
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
