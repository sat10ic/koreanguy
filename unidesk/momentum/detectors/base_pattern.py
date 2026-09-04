"""Clean-room, point-in-time base-pattern measurements.

This module deliberately reconstructs only behavior observable from public
BananaPatterns guides and rendered/API fields.  It is *not* a copy of that
product's undisclosed base-window selection or relative-strength weighting.
Every heuristic below is explicit and configurable so it can be calibrated
against a licensed historical data set without silently changing signals.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from statistics import median
from typing import Mapping, Optional, Sequence

from unidesk.contracts.base import ContractError, require_float
from unidesk.momentum.primitives.pivots import PivotKind, fractal_pivots, pivots_known_at


class BaseVerdict(Enum):
    """Lifecycle state; thresholds are held in :class:`BaseRules`."""

    WATCH = "watch"
    BREAKOUT = "breakout"
    RUNNING = "running"
    EXITED = "exited"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass(frozen=True)
class DailyBar:
    """One split-adjusted daily OHLCV observation."""

    day: date
    open: float
    high: float
    low: float
    close: float
    volume: float

    def __post_init__(self) -> None:
        if not isinstance(self.day, date):
            raise ContractError("day must be a datetime.date")
        for name in ("open", "high", "low", "close", "volume"):
            object.__setattr__(self, name, require_float(getattr(self, name), name))
        if self.volume < 0:
            raise ContractError("volume must be non-negative")
        if self.low > min(self.open, self.close) or self.high < max(self.open, self.close):
            raise ContractError("OHLC bounds are inconsistent")
        if self.low > self.high:
            raise ContractError("low must not exceed high")


@dataclass(frozen=True)
class BaseRules:
    """Transparent approximation choices, all adjustable during calibration."""

    swing_left_right: int = 7
    min_base_sessions: int = 15
    min_rebase_sessions: int = 20
    max_base_sessions: int = 1_500
    max_depth_pct: float = 35.0
    fresh_breakout_sessions: int = 5
    running_extension_pct: float = 5.0
    ma_period: int = 50

    def __post_init__(self) -> None:
        for name in ("swing_left_right", "min_base_sessions", "min_rebase_sessions", "max_base_sessions", "fresh_breakout_sessions", "ma_period"):
            if not isinstance(getattr(self, name), int) or getattr(self, name) < 1:
                raise ContractError(f"{name} must be a positive integer")
        if self.max_base_sessions < self.min_base_sessions:
            raise ContractError("max_base_sessions must be >= min_base_sessions")
        for name in ("max_depth_pct", "running_extension_pct"):
            value = require_float(getattr(self, name), name)
            if value < 0:
                raise ContractError(f"{name} must be non-negative")
            object.__setattr__(self, name, value)


@dataclass(frozen=True)
class BasePattern:
    """The public-facing annotations a clean-room screen can expose."""

    base_start: Optional[date]
    base_end: Optional[date]
    base_sessions: Optional[int]
    base_weeks: Optional[float]
    pivot: Optional[float]
    depth_pct: Optional[float]
    coil_ratio: Optional[float]
    dry_ratio: Optional[float]
    dry_depth_ratio: Optional[float]
    up_down_volume_ratio: Optional[float]
    net_volume_balance: Optional[float]
    rs_rank: Optional[int]
    squat_dates: tuple[date, ...]
    failed_poke_dates: tuple[date, ...]
    breakout_date: Optional[date]
    verdict: BaseVerdict
    notes: tuple[str, ...] = ()


def _true_range_pct(bars: Sequence[DailyBar], index: int) -> float:
    bar = bars[index]
    prior_close = bars[index - 1].close if index else bar.close
    true_range = max(bar.high - bar.low, abs(bar.high - prior_close), abs(bar.low - prior_close))
    if bar.close <= 0:
        raise ContractError("close must be positive for true-range percentage")
    return true_range / bar.close


def _mean(values: Sequence[float]) -> Optional[float]:
    return sum(values) / len(values) if values else None


def _ratio(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def _failed_pokes(bars: Sequence[DailyBar], start: int, end: int) -> tuple[date, ...]:
    """Confirmed failed-poke annotation; confirmation needs up to ten later bars.

    The public description gives this sequence but not its exact windowing.  It
    is therefore intentionally an annotation-only heuristic, not an entry rule.
    """
    out: list[date] = []
    for index in range(start + 1, end):
        prior_close_high = max(bar.close for bar in bars[start:index])
        prior_high = max(bar.high for bar in bars[start:index])
        bar = bars[index]
        if bar.close <= prior_close_high or bar.high > prior_high:
            continue
        confirmation_end = min(end, index + 10)
        if any(bars[later].close <= prior_close_high for later in range(index + 1, confirmation_end + 1)):
            out.append(bar.day)
    return tuple(out)


def classify_base_verdict(
    *, closes: Sequence[float], pivot: float, breakout_index: Optional[int], rules: BaseRules
) -> BaseVerdict:
    """Classify a known base without looking beyond the supplied session."""
    values = [require_float(value, f"closes[{index}]") for index, value in enumerate(closes)]
    pivot = require_float(pivot, "pivot")
    if pivot <= 0:
        raise ContractError("pivot must be positive")
    if not values or breakout_index is None:
        return BaseVerdict.WATCH
    if breakout_index < 0 or breakout_index >= len(values):
        raise ContractError("breakout_index is outside closes")

    current_index = len(values) - 1
    # The clearing bar is always a fresh breakout, even if it travels far.
    # Its extension is a next-session lifecycle assessment, not a reason to
    # rewrite the entry-day label.
    if current_index == breakout_index:
        return BaseVerdict.BREAKOUT
    if len(values) >= rules.ma_period:
        moving_average = sum(values[-rules.ma_period:]) / rules.ma_period
        if values[-1] < moving_average:
            return BaseVerdict.EXITED
    if values[-1] >= pivot * (1 + rules.running_extension_pct / 100):
        return BaseVerdict.RUNNING
    if current_index - breakout_index < rules.fresh_breakout_sessions:
        return BaseVerdict.BREAKOUT
    return BaseVerdict.WATCH


def _empty(rs_rank: Optional[int], note: str) -> BasePattern:
    return BasePattern(
        base_start=None, base_end=None, base_sessions=None, base_weeks=None,
        pivot=None, depth_pct=None, coil_ratio=None, dry_ratio=None,
        dry_depth_ratio=None, up_down_volume_ratio=None, net_volume_balance=None,
        rs_rank=rs_rank, squat_dates=(), failed_poke_dates=(), breakout_date=None,
        verdict=BaseVerdict.INSUFFICIENT_DATA, notes=(note,),
    )


def detect_base_pattern(
    bars: Sequence[DailyBar], *, rules: BaseRules = BaseRules(), rs_rank: Optional[int] = None
) -> BasePattern:
    """Return the latest confirmed-fractal base and public-style measurements.

    A base begins on the session after the latest *confirmed* structural swing
    high that leaves a valid-sized window.  The pivot is the highest close in
    the window (not the high).  A close above that pre-existing pivot on the
    final supplied session is a breakout; the breakout bar is excluded from the
    base measurements.  This last-session restriction prevents look-ahead and
    makes historical lifecycle persistence an explicit future extension.
    """
    values = tuple(bars)
    if rs_rank is not None and (not isinstance(rs_rank, int) or not 1 <= rs_rank <= 99):
        raise ContractError("rs_rank must be an integer in 1..99")
    if len(values) < rules.min_base_sessions + rules.swing_left_right + 1:
        return _empty(rs_rank, "no_confirmed_base")
    if any(values[index].day >= values[index + 1].day for index in range(len(values) - 1)):
        raise ContractError("bars must be strictly ordered by day")

    highs = [bar.high for bar in values]
    lows = [bar.low for bar in values]
    as_of = len(values) - 1
    high_pivots = [
        pivot for pivot in pivots_known_at(fractal_pivots(highs, lows, rules.swing_left_right), as_of)
        if pivot.kind is PivotKind.HIGH
    ]
    # An incumbent forming episode takes priority over a later, one-day
    # prospective breakout candidate.  This avoids treating a nested test of a
    # still-active ceiling as an automatic rebase.  When no valid forming
    # candidate exists, the usual latest-first ordering recognizes a breakout.
    forming_anchors = []
    for anchor in high_pivots:
        start = anchor.index + 1
        if start >= as_of:
            continue
        base = values[start:as_of + 1]
        if not rules.min_base_sessions <= len(base) <= rules.max_base_sessions:
            continue
        pivot = max(bar.close for bar in base)
        depth_pct = (pivot - min(bar.low for bar in base)) / pivot * 100 if pivot > 0 else None
        if depth_pct is None or depth_pct > rules.max_depth_pct:
            continue
        if values[as_of].close <= max(bar.close for bar in values[start:as_of]):
            forming_anchors.append(anchor)
    # A short nested base cannot silently replace the incumbent.  The public
    # data does not reveal its rebase rule, so this maturation threshold is an
    # explicit calibration parameter.  In the absence of an incumbent, search
    # newest first for the live breakout candidate.
    mature_forming = [
        anchor for anchor in forming_anchors
        if as_of - anchor.index >= rules.min_rebase_sessions
    ]
    candidate_anchors = list(reversed(mature_forming or forming_anchors or high_pivots))

    for anchor in candidate_anchors:
        start = anchor.index + 1
        if start >= as_of:
            continue

        breakout_index: Optional[int] = None
        end = as_of
        if as_of - start >= rules.min_base_sessions:
            prior_pivot = max(bar.close for bar in values[start:as_of])
            if values[as_of].close > prior_pivot:
                breakout_index = as_of
                end = as_of - 1
        base = values[start:end + 1]
        if not rules.min_base_sessions <= len(base) <= rules.max_base_sessions:
            continue

        pivot = max(bar.close for bar in base)
        depth_pct = (pivot - min(bar.low for bar in base)) / pivot * 100 if pivot > 0 else None
        if depth_pct is None or depth_pct > rules.max_depth_pct:
            continue
        midpoint = len(base) // 2
        first, second = base[:midpoint], base[midpoint:]
        first_range = _mean([_true_range_pct(values, start + index) for index in range(len(first))])
        second_range = _mean([_true_range_pct(values, start + midpoint + index) for index in range(len(second))])
        coil_ratio = _ratio(second_range, first_range)
        dry_ratio = _ratio(_mean([bar.volume for bar in second]), _mean([bar.volume for bar in first]))
        dry_depth_ratio = _ratio(min(bar.volume for bar in base), median(bar.volume for bar in base))

        up_volume = down_volume = 0.0
        for index in range(start, end + 1):
            prior_close = values[index - 1].close if index else values[index].close
            if values[index].close > prior_close:
                up_volume += values[index].volume
            elif values[index].close < prior_close:
                down_volume += values[index].volume
        total_directional_volume = up_volume + down_volume
        squats = tuple(
            bar.day for bar in base if bar.high > pivot and bar.close <= pivot
        )
        notes = ("cleanroom_heuristic_base_selection",)
        verdict = classify_base_verdict(
            closes=[bar.close for bar in values], pivot=pivot,
            breakout_index=breakout_index, rules=rules,
        )
        return BasePattern(
            base_start=base[0].day, base_end=base[-1].day,
            base_sessions=len(base), base_weeks=len(base) / 5,
            pivot=pivot, depth_pct=depth_pct, coil_ratio=coil_ratio,
            dry_ratio=dry_ratio, dry_depth_ratio=dry_depth_ratio,
            up_down_volume_ratio=_ratio(up_volume, down_volume),
            net_volume_balance=((up_volume - down_volume) / total_directional_volume
                                if total_directional_volume else None),
            rs_rank=rs_rank, squat_dates=squats,
            failed_poke_dates=_failed_pokes(values, start, end),
            breakout_date=values[breakout_index].day if breakout_index is not None else None,
            verdict=verdict, notes=notes,
        )
    return _empty(rs_rank, "no_confirmed_base")


def relative_strength_ranks(
    closes_by_symbol: Mapping[str, Sequence[float]], *,
    lookbacks: Sequence[int] = (63, 126, 189, 252),
    weights: Sequence[float] = (0.4, 0.2, 0.2, 0.2),
) -> dict[str, int]:
    """Return 1--99 cross-sectional trailing-return percentiles.

    The exact BananaPatterns return horizons and weights are undisclosed; these
    defaults are a configurable clean-room composite, not a parity assertion.
    """
    if not closes_by_symbol:
        return {}
    if not lookbacks or len(lookbacks) != len(weights):
        raise ContractError("lookbacks and weights must be non-empty and equal length")
    if any(not isinstance(period, int) or period < 1 for period in lookbacks):
        raise ContractError("lookbacks must be positive integers")
    float_weights = [require_float(weight, f"weights[{index}]") for index, weight in enumerate(weights)]
    if sum(float_weights) <= 0:
        raise ContractError("weights must have a positive total")

    scores: dict[str, float] = {}
    for symbol, series in closes_by_symbol.items():
        closes = [require_float(value, f"{symbol}[{index}]") for index, value in enumerate(series)]
        if len(closes) <= max(lookbacks):
            raise ContractError(f"{symbol} has insufficient history for requested lookbacks")
        if any(value <= 0 for value in closes):
            raise ContractError(f"{symbol} closes must be positive")
        scores[symbol] = sum(
            weight * (closes[-1] / closes[-1 - period] - 1)
            for period, weight in zip(lookbacks, float_weights)
        ) / sum(float_weights)

    ordered = sorted(scores.items(), key=lambda item: (item[1], item[0]))
    if len(ordered) == 1:
        return {ordered[0][0]: 99}
    ranks: dict[str, int] = {}
    index = 0
    while index < len(ordered):
        stop = index + 1
        while stop < len(ordered) and ordered[stop][1] == ordered[index][1]:
            stop += 1
        average_position = (index + stop - 1) / 2
        rating = round(1 + 98 * average_position / (len(ordered) - 1))
        for symbol, _ in ordered[index:stop]:
            ranks[symbol] = rating
        index = stop
    return ranks
