"""Read-only operational data-freshness checks."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from manas_os import market_calendar

_IST = timezone(timedelta(hours=5, minutes=30))


def _now_ist() -> datetime:
    return datetime.now(_IST)


def _today_ist() -> date:
    return _now_ist().date()


def check_freshness(conn) -> dict[str, str | bool | None]:
    """Compare the latest EQ price with the expected NSE session.

    A trading day's own data only EXISTS after the evening bhavcopy publish
    (~19:00 IST) + our nightly run. Before that cutoff, the expected session
    is the PREVIOUS trading day — otherwise every trading day reads STALE
    from midnight until evening (the Sunday-00:30 false-STALE defect).
    """
    row = conn.execute(
        "SELECT MAX(trade_date) FROM daily_prices WHERE series='EQ'"
    ).fetchone()
    latest_price_date = row[0] if row and row[0] else None
    now_ist = _now_ist()
    anchor = now_ist.date()
    # Before 19:30 IST today's session data cannot be in the DB yet.
    if now_ist.hour < 19 or (now_ist.hour == 19 and now_ist.minute < 30):
        anchor = anchor - timedelta(days=1)
    expected_last_session = market_calendar.last_trading_day(anchor).isoformat()
    return {
        "latest_price_date": latest_price_date,
        "expected_last_session": expected_last_session,
        "stale": bool(not latest_price_date or latest_price_date < expected_last_session),
    }
