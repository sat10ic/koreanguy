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

from datetime import date, timedelta

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
