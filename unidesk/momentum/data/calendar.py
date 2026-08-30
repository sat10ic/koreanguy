"""Exchange trading calendar (Phase 0 spec §9).

Built from *actual observed sessions*, never from weekdays. Rolling windows
must count trading sessions, not calendar days. Timezone is Asia/Kolkata.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time
from typing import Optional, Sequence

from unidesk.contracts.base import ContractError, ensure_date

TZ_NAME = "Asia/Kolkata"
SESSION_OPEN = time(9, 15)
SESSION_CLOSE = time(15, 30)


@dataclass(frozen=True)
class TradingDay:
    trade_date: date
    previous_trade_date: Optional[date]
    next_trade_date: Optional[date]
    is_trading_day: bool = True
    is_special_session: bool = False
    is_muhurat_session: bool = False
    is_half_day: bool = False
    timezone: str = TZ_NAME


@dataclass(frozen=True)
class TradingCalendar:
    """Immutable session list, chronological, unique."""

    days: tuple[TradingDay, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "days", tuple(self.days))
        seen = set()
        prev = None
        for d in self.days:
            if d.trade_date in seen:
                raise ContractError(f"duplicate trade_date {d.trade_date}")
            seen.add(d.trade_date)
            if prev is not None and d.trade_date <= prev:
                raise ContractError("calendar must be strictly chronological")
            prev = d.trade_date
        object.__setattr__(self, "_index", {d.trade_date: i for i, d in enumerate(self.days)})

    def __len__(self) -> int:
        return len(self.days)

    def get(self, session: date) -> Optional[TradingDay]:
        session = ensure_date(session, "session")
        i = self._index.get(session)
        return None if i is None else self.days[i]

    def session_distance(self, a: date, b: date) -> Optional[int]:
        """Signed trading-session distance ``b - a``. None if either date
        is not an observed session (we do not invent sessions)."""
        a = ensure_date(a, "a")
        b = ensure_date(b, "b")
        ia = self._index.get(a)
        ib = self._index.get(b)
        if ia is None or ib is None:
            return None
        return ib - ia


def from_sessions(sessions: Sequence[date]) -> TradingCalendar:
    """Build a calendar from observed exchange sessions (unique, sorted)."""
    unique = sorted({ensure_date(s, "session") for s in sessions})
    if not unique:
        raise ContractError("calendar requires at least one session")
    days = []
    n = len(unique)
    for i, d in enumerate(unique):
        days.append(TradingDay(
            trade_date=d,
            previous_trade_date=unique[i - 1] if i else None,
            next_trade_date=unique[i + 1] if i + 1 < n else None,
        ))
    return TradingCalendar(tuple(days))
