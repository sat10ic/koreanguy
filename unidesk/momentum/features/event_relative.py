"""Point-in-time IPO and earnings-gap features in an event-relative frame.

These are descriptive research features, not setup detectors or ranking inputs.
They intentionally measure only bars from the documented event anchor through
``as_of``.  The caller supplies the exchange ``TradingCalendar`` and complete
point-in-time bar series; dates absent from that calendar are rejected rather
than approximated with weekday arithmetic.

Formulas are deliberately explicit:

* first-day range is ``(high[day0] - low[day0]) / low[day0] * 100``;
* IPO base depth is the drawdown from the listing-day high to the lowest low
  observed through ``as_of``, expressed in first-day ranges;
* EP gap is ``(open[day0] / close[day-1] - 1) * 100``;
* EP close location is ``(close - low) / (high - low)`` on day 0.

No missing input is silently converted to zero.  A missing optional issue
price, catalyst, RVOL, or circuit series produces its documented ``None``
field; malformed or misaligned data raises ``ContractError``.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional, Sequence

from unidesk.contracts.base import ContractError, ensure_date, require_float, require_str
from unidesk.momentum.data.calendar import TradingCalendar


@dataclass(frozen=True)
class IPOEventRelativeFeatures:
    sessions_since_event: int
    pct_from_listing_high: Optional[float]
    pct_from_listing_low: Optional[float]
    first_day_range_pct: Optional[float]
    base_vs_listing_range: Optional[float]
    pct_from_issue_price: Optional[float]


@dataclass(frozen=True)
class EPEventRelativeFeatures:
    sessions_since_event: int
    gap_pct: Optional[float]
    gap_day_close_location: Optional[float]
    held_above_gap_low: Optional[bool]
    volume_decay_since_gap: tuple[Optional[float], ...]
    days_locked_since_gap: Optional[int]
    catalyst_type: Optional[str]
    days_since_catalyst: Optional[int]


def _bar_series(values: Sequence[float], name: str, expected_length: int) -> list[float]:
    if len(values) != expected_length:
        raise ContractError(f"{name} must have exactly one value per calendar session")
    return [require_float(value, f"{name}[{index}]") for index, value in enumerate(values)]


def _optional_series(
    values: Optional[Sequence[Optional[float]]], name: str, expected_length: int
) -> Optional[list[Optional[float]]]:
    if values is None:
        return None
    if len(values) != expected_length:
        raise ContractError(f"{name} must have exactly one value per calendar session")
    return [None if value is None else require_float(value, f"{name}[{index}]")
            for index, value in enumerate(values)]


def _optional_bool_series(
    values: Optional[Sequence[Optional[bool]]], name: str, expected_length: int
) -> Optional[list[Optional[bool]]]:
    if values is None:
        return None
    if len(values) != expected_length:
        raise ContractError(f"{name} must have exactly one value per calendar session")
    result: list[Optional[bool]] = []
    for index, value in enumerate(values):
        if value is not None and not isinstance(value, bool):
            raise ContractError(f"{name}[{index}] must be bool or None")
        result.append(value)
    return result


def _event_indexes(
    calendar: TradingCalendar, anchor_session: date, as_of: date
) -> tuple[int, int]:
    if not isinstance(calendar, TradingCalendar):
        raise ContractError("calendar must be a TradingCalendar")
    anchor_session = ensure_date(anchor_session, "anchor_session")
    as_of = ensure_date(as_of, "as_of")
    anchor_index = calendar._index.get(anchor_session)
    as_of_index = calendar._index.get(as_of)
    if anchor_index is None:
        raise ContractError("anchor_session is absent from the trading calendar")
    if as_of_index is None:
        raise ContractError("as_of is absent from the trading calendar")
    if as_of_index < anchor_index:
        raise ContractError("as_of precedes event anchor")
    return anchor_index, as_of_index


def sessions_since_event(calendar: TradingCalendar, anchor_session: date, as_of: date) -> int:
    """Trading-session age from an event anchor to ``as_of`` (day 0 = 0)."""
    anchor_index, as_of_index = _event_indexes(calendar, anchor_session, as_of)
    return as_of_index - anchor_index


def ipo_event_features(
    calendar: TradingCalendar,
    *,
    anchor_session: date,
    as_of: date,
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    issue_price: Optional[float] = None,
) -> IPOEventRelativeFeatures:
    """IPO features anchored at the documented listing session.

    A listing session alone is enough to calculate its range.  ``issue_price``
    is optional because it is not yet in the reference contract.
    """
    anchor_index, as_of_index = _event_indexes(calendar, anchor_session, as_of)
    n = len(calendar)
    high = _bar_series(highs, "highs", n)
    low = _bar_series(lows, "lows", n)
    close = _bar_series(closes, "closes", n)
    first_high, first_low = high[anchor_index], low[anchor_index]
    if first_low <= 0 or first_high < first_low:
        raise ContractError("listing-day high/low must be non-negative and ordered")
    first_range_pct = (first_high - first_low) / first_low * 100.0
    current_close = close[as_of_index]
    pct_from_high = (current_close / first_high - 1.0) * 100.0 if first_high > 0 else None
    pct_from_low = (current_close / first_low - 1.0) * 100.0
    lowest_low = min(low[anchor_index:as_of_index + 1])
    base_vs_range = None if first_range_pct == 0 else (first_high - lowest_low) / (first_high - first_low)
    if issue_price is None:
        pct_from_issue = None
    else:
        issue = require_float(issue_price, "issue_price")
        if issue <= 0:
            raise ContractError("issue_price must be positive")
        pct_from_issue = (current_close / issue - 1.0) * 100.0
    return IPOEventRelativeFeatures(
        sessions_since_event=as_of_index - anchor_index,
        pct_from_listing_high=pct_from_high,
        pct_from_listing_low=pct_from_low,
        first_day_range_pct=first_range_pct,
        base_vs_listing_range=base_vs_range,
        pct_from_issue_price=pct_from_issue,
    )


def ep_event_features(
    calendar: TradingCalendar,
    *,
    anchor_session: date,
    as_of: date,
    opens: Sequence[float],
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    rvols: Optional[Sequence[Optional[float]]] = None,
    locked_sessions: Optional[Sequence[Optional[bool]]] = None,
    catalyst_type: Optional[str] = None,
    catalyst_session: Optional[date] = None,
) -> EPEventRelativeFeatures:
    """Earnings-gap features from day 0 through ``as_of`` only.

    ``rvols`` must be point-in-time RVOL values generated upstream.  The
    returned decay path is normalised to the event-day RVOL (1.0 on day 0), so
    it preserves a trajectory rather than pretending the latest value alone is
    a trend.  A missing event-day RVOL makes the entire path unknown.
    """
    anchor_index, as_of_index = _event_indexes(calendar, anchor_session, as_of)
    n = len(calendar)
    open_ = _bar_series(opens, "opens", n)
    high = _bar_series(highs, "highs", n)
    low = _bar_series(lows, "lows", n)
    close = _bar_series(closes, "closes", n)
    rvol = _optional_series(rvols, "rvols", n)
    locked = _optional_bool_series(locked_sessions, "locked_sessions", n)
    if high[anchor_index] < low[anchor_index]:
        raise ContractError("gap-day high must be >= low")
    if anchor_index == 0:
        gap_pct = None
    else:
        prior_close = close[anchor_index - 1]
        gap_pct = None if prior_close <= 0 else (open_[anchor_index] / prior_close - 1.0) * 100.0
    gap_range = high[anchor_index] - low[anchor_index]
    close_location = None if gap_range == 0 else (close[anchor_index] - low[anchor_index]) / gap_range
    held_above_gap_low = all(value >= low[anchor_index] for value in close[anchor_index:as_of_index + 1])
    path_length = as_of_index - anchor_index + 1
    if rvol is None or rvol[anchor_index] is None or rvol[anchor_index] <= 0:
        volume_path = (None,) * path_length
    else:
        event_rvol = rvol[anchor_index]
        volume_path = tuple(
            None if value is None else value / event_rvol
            for value in rvol[anchor_index:as_of_index + 1]
        )
    locked_count = None if locked is None or any(
        value is None for value in locked[anchor_index:as_of_index + 1]
    ) else sum(bool(value) for value in locked[anchor_index:as_of_index + 1])
    if catalyst_type is None:
        if catalyst_session is not None:
            raise ContractError("catalyst_session requires catalyst_type")
        days_since_catalyst = None
    else:
        catalyst_type = require_str(catalyst_type, "catalyst_type")
        if catalyst_session is None:
            raise ContractError("catalyst_type requires catalyst_session")
        catalyst_session = ensure_date(catalyst_session, "catalyst_session")
        days_since_catalyst = sessions_since_event(calendar, catalyst_session, as_of)
    return EPEventRelativeFeatures(
        sessions_since_event=as_of_index - anchor_index,
        gap_pct=gap_pct,
        gap_day_close_location=close_location,
        held_above_gap_low=held_above_gap_low,
        volume_decay_since_gap=volume_path,
        days_locked_since_gap=locked_count,
        catalyst_type=catalyst_type,
        days_since_catalyst=days_since_catalyst,
    )
