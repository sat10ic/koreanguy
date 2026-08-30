"""Delivery availability vs decision time (Phase 0 spec §14.2 / D14.3).

Until a 20-session first-seen availability ledger exists, delivery from
session T is safe only for a *next-session* decision. Same-session 15:30
use is forbidden even if the bhavcopy row already carries DELIV_PER —
the file's public timestamp is not yet measured.
"""
from __future__ import annotations

from datetime import date

from unidesk.contracts.base import ensure_date
from unidesk.momentum.data.calendar import TradingCalendar

# Frozen until the availability study in Phase 0 spec §14.2 is run.
SAME_SESSION_DELIVERY_SAFE = False


def delivery_usable_for_decision(
    trade_date: date,
    decision_date: date,
    calendar: TradingCalendar,
) -> bool:
    """True iff delivery printed for ``trade_date`` may enter a money
    decision dated ``decision_date``."""
    trade_date = ensure_date(trade_date, "trade_date")
    decision_date = ensure_date(decision_date, "decision_date")
    if SAME_SESSION_DELIVERY_SAFE:
        distance = calendar.session_distance(trade_date, decision_date)
        return distance is not None and distance >= 0
    distance = calendar.session_distance(trade_date, decision_date)
    return distance is not None and distance >= 1
