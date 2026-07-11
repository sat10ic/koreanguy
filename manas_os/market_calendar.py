"""NSE trading-calendar helpers — display-only staleness math.

Calendar-day math (e.g. "snapshot is 2 days old") falsely flags a Friday
snapshot as stale on a Saturday or Sunday. These helpers count only actual
NSE trading sessions (Mon-Fri, minus known holidays) so staleness reflects
"how many trading days behind" rather than "how many calendar days have
passed" — a weekend or holiday alone should never trip the stale banner.

Nothing here touches ingestion or the DB; it exists purely so /api/regime/*
can compute an honest days_behind for display.
"""
from __future__ import annotations

from datetime import date, datetime, time as _time, timedelta

# NSE regular session, IST wall-clock. Pre-open auction (09:00-09:08) is
# deliberately excluded from "market hours" for the live loop's purposes
# (LIVE_LOOP_FABLE §2.7): no ticks should feed the FSM during the auction.
MARKET_OPEN = _time(9, 8)
MARKET_CLOSE = _time(15, 30)

# ─────────────────────────────────────────────────────────────────────────────
# NSE HOLIDAYS — maintainable, approximate set for 2025-2026. NSE publishes an
# official trading-holiday list each year; this is a hand-maintained
# best-effort covering the well-known fixed/major holidays so weekday-only
# math doesn't over-count trading days on actual market closures. Update this
# set annually (or when NSE publishes the next year's calendar) — it is NOT
# pulled from any live source.
# ─────────────────────────────────────────────────────────────────────────────
HOLIDAYS: set[date] = {
    # 2025
    date(2025, 1, 26),   # Republic Day
    date(2025, 2, 26),   # Maha Shivratri
    date(2025, 3, 14),   # Holi
    date(2025, 3, 31),   # Id-Ul-Fitr (Ramzan Id)
    date(2025, 4, 10),   # Mahavir Jayanti
    date(2025, 4, 14),   # Dr. Baba Saheb Ambedkar Jayanti
    date(2025, 4, 18),   # Good Friday
    date(2025, 5, 1),    # Maharashtra Day
    date(2025, 8, 15),   # Independence Day
    date(2025, 8, 27),   # Ganesh Chaturthi
    date(2025, 10, 2),   # Gandhi Jayanti / Dussehra
    date(2025, 10, 21),  # Diwali Laxmi Pujan
    date(2025, 10, 22),  # Diwali Balipratipada
    date(2025, 11, 5),   # Guru Nanak Jayanti
    date(2025, 12, 25),  # Christmas
    # 2026 (approximate — confirm against NSE's published circular each year)
    date(2026, 1, 26),   # Republic Day
    date(2026, 3, 4),    # Holi
    date(2026, 3, 21),   # Id-Ul-Fitr (Ramzan Id, approx.)
    date(2026, 4, 3),    # Good Friday
    date(2026, 4, 14),   # Dr. Baba Saheb Ambedkar Jayanti
    date(2026, 5, 1),    # Maharashtra Day
    date(2026, 8, 15),   # Independence Day
    date(2026, 10, 2),   # Gandhi Jayanti
    date(2026, 11, 8),   # Diwali Laxmi Pujan (approx.)
    date(2026, 11, 9),   # Diwali Balipratipada (approx.)
    date(2026, 12, 25),  # Christmas
}


def is_trading_day(d: date) -> bool:
    """Mon-Fri and not in HOLIDAYS."""
    return d.weekday() < 5 and d not in HOLIDAYS


def last_trading_day(on_or_before: date) -> date:
    """Most recent trading day on or before `on_or_before` (inclusive)."""
    cur = on_or_before
    while not is_trading_day(cur):
        cur -= timedelta(days=1)
    return cur


def trading_days_between(a: date, b: date) -> int:
    """Count of trading days strictly between `a` and `b` (exclusive of both
    endpoints), assuming a <= b. Mirrors the previous calendar-day helper's
    contract (a Friday `a` vs a Sunday `b` returns 0 trading days between),
    but skips holidays too. If a > b, returns 0 (never negative)."""
    if a >= b:
        return 0
    count = 0
    cur = b - timedelta(days=1)
    while cur > a:
        if is_trading_day(cur):
            count += 1
        cur -= timedelta(days=1)
    return count


def is_market_hours(when: datetime | None = None) -> bool:
    """True only on a trading day, between the post-auction open (09:08 IST)
    and close (15:30 IST). `when` is assumed already IST wall-clock (this repo
    has no timezone-aware datetime handling elsewhere; callers pass IST
    directly, matching the rest of the codebase's convention). Used by the
    live loop to refuse to open a WS connection or emit anything outside
    NSE hours (LIVE_LOOP_FABLE §2.7, §4.3)."""
    now = when or datetime.now()
    if not is_trading_day(now.date()):
        return False
    t = now.time()
    return MARKET_OPEN <= t <= MARKET_CLOSE
