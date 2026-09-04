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
from unidesk.contracts.research import ResearchEvent
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


def _event_session(event: ResearchEvent) -> date:
    # Same convention as research/candidates.py:_event_session, duplicated
    # rather than imported -- this module is the lower-level constitution
    # layer; candidates.py depends on leakage.py, not the reverse.
    if ":" in event.event_id:
        return date.fromisoformat(event.event_id.rsplit(":", 1)[-1])
    return event.timestamp.date()


def embargo_overlapping_events(
    events: Sequence[ResearchEvent],
    calendar: TradingCalendar,
    *,
    window: int = DEFAULT_SAME_SYMBOL_EMBARGO_SESSIONS,
) -> tuple[list[ResearchEvent], list[tuple[ResearchEvent, date]]]:
    """Constitution §6: same-symbol analogues inside the embargo window are
    forbidden as independent samples (their outcomes overlap and share
    autocorrelated market state, so counting both inflates apparent edge).

    Per symbol, keeps the EARLIEST-decided event in each cluster and
    embargoes every later same-symbol event whose decision session falls
    inside ``window`` sessions of the kept one — deterministic, and it
    never looks at any event's outcome to decide what to keep, only its
    decision date. A newly-kept event resets the window: two events 65
    sessions apart with nothing between them are both independent even if
    a third event 200 sessions later would collide with neither alone.

    Returns ``(kept, embargoed)`` — ``embargoed`` pairs each dropped event
    with the decision session of the kept event that embargoed it, so a
    caller can report why, not just silently shrink the sample count.
    Asserts (defense-in-depth, mirroring ``attach_outcomes``'s
    ``assert_future_only`` pattern) that ``kept`` itself never collides on
    ``same_event_collision`` — a bug in this function's own dedup, not a
    real embargo case, would otherwise pass through silently.
    """
    by_symbol: dict[str, list[ResearchEvent]] = {}
    for ev in events:
        by_symbol.setdefault(ev.symbol, []).append(ev)
    kept: list[ResearchEvent] = []
    embargoed: list[tuple[ResearchEvent, date]] = []
    for symbol_events in by_symbol.values():
        ordered = sorted(symbol_events, key=_event_session)
        last_kept_session: date | None = None
        for ev in ordered:
            session = _event_session(ev)
            if last_kept_session is not None and same_symbol_embargo(
                session, last_kept_session, calendar, window=window,
            ):
                embargoed.append((ev, last_kept_session))
                continue
            kept.append(ev)
            last_kept_session = session
    if same_event_collision([e.event_id for e in kept]):
        raise ContractError("embargo_overlapping_events produced a duplicate event_id in kept")
    return kept, embargoed
