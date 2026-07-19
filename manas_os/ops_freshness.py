"""Read-only operational data-freshness checks."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from manas_os import market_calendar

_IST = timezone(timedelta(hours=5, minutes=30))


def _today_ist() -> date:
    return datetime.now(_IST).date()


def check_freshness(conn) -> dict[str, str | bool | None]:
    """Compare the latest EQ price with the expected NSE session."""
    row = conn.execute(
        "SELECT MAX(trade_date) FROM daily_prices WHERE series='EQ'"
    ).fetchone()
    latest_price_date = row[0] if row and row[0] else None
    expected_last_session = market_calendar.last_trading_day(_today_ist()).isoformat()
    return {
        "latest_price_date": latest_price_date,
        "expected_last_session": expected_last_session,
        "stale": bool(not latest_price_date or latest_price_date < expected_last_session),
    }
