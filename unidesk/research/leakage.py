"""Decision-time contracts and analogue embargoes (constitution §§5–6).

Hard rules, not documentation:

* ``feature_timestamp <= decision_timestamp``
* same-symbol analogues inside ±60 trading sessions are forbidden
* same-event states cannot be treated as independent samples
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Sequence

from unidesk.contracts.base import ContractError, ensure_date, ensure_utc
from unidesk.momentum.data.calendar import TradingCalendar

DEFAULT_SAME_SYMBOL_EMBARGO_SESSIONS = 60


def assert_feature_not_after_decision(feature_timestamp: datetime,
                                      decision_timestamp: datetime) -> None:
    """Constitution §5 / Phase 0 spec §2.3. Fail closed."""
    feature_timestamp = ensure_utc(feature_timestamp, "feature_timestamp")
    decision_timestamp = ensure_utc(decision_timestamp, "decision_timestamp")
    if feature_timestamp > decision_timestamp:
        raise ContractError(
            f"feature_timestamp {feature_timestamp.isoformat()} is after "
            f"decision_timestamp {decision_timestamp.isoformat()}"
        )


def same_symbol_embargo(
    query_date: date,
    analogue_date: date,
    calendar: TradingCalendar,
    *,
    window: int = DEFAULT_SAME_SYMBOL_EMBARGO_SESSIONS,
) -> bool:
    """True if the analogue is FORBIDDEN for this query (inside the window)."""
    query_date = ensure_date(query_date, "query_date")
    analogue_date = ensure_date(analogue_date, "analogue_date")
    if window < 0:
        raise ContractError("embargo window must be >= 0")
    distance = calendar.session_distance(query_date, analogue_date)
    if distance is None:
        # One of the dates is not a trading session — cannot certify safety.
        return True
    return abs(distance) <= window


def same_event_collision(event_ids: Sequence[str]) -> bool:
    """True if the sample bag contains the same event more than once."""
    cleaned = [e for e in event_ids if e]
    return len(cleaned) != len(set(cleaned))
