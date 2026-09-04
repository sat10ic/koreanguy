import sqlite3
from datetime import datetime

from manas_os import ops_freshness

IST = ops_freshness._IST


def test_check_freshness_reports_current_session_as_fresh(monkeypatch):
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE daily_prices (trade_date TEXT, series TEXT)")
    conn.execute("INSERT INTO daily_prices VALUES ('2026-07-17', 'EQ')")
    # Friday 2026-07-17, 20:00 IST -- after the 19:30 publish cutoff, so the
    # expected session is today itself, not the day before.
    monkeypatch.setattr(
        ops_freshness, "_now_ist", lambda: datetime(2026, 7, 17, 20, 0, tzinfo=IST)
    )

    result = ops_freshness.check_freshness(conn)

    assert result == {
        "latest_price_date": "2026-07-17",
        "expected_last_session": "2026-07-17",
        "stale": False,
    }
    conn.close()


def test_check_freshness_reports_older_session_as_stale(monkeypatch):
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE daily_prices (trade_date TEXT, series TEXT)")
    conn.execute("INSERT INTO daily_prices VALUES ('2026-07-16', 'EQ')")
    # Friday 2026-07-17, 20:00 IST -- expected session is today (17th); the
    # DB only has the prior day (16th) so it reads stale.
    monkeypatch.setattr(
        ops_freshness, "_now_ist", lambda: datetime(2026, 7, 17, 20, 0, tzinfo=IST)
    )

    result = ops_freshness.check_freshness(conn)

    assert result == {
        "latest_price_date": "2026-07-16",
        "expected_last_session": "2026-07-17",
        "stale": True,
    }
    conn.close()


def test_check_freshness_tolerates_weekend_without_new_prices(monkeypatch):
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE daily_prices (trade_date TEXT, series TEXT)")
    conn.execute("INSERT INTO daily_prices VALUES ('2026-07-17', 'EQ')")
    # Sunday 2026-07-19, 20:00 IST -- expected session is still Friday the
    # 17th (last trading day on/before the weekend), so Friday's data is fresh.
    monkeypatch.setattr(
        ops_freshness, "_now_ist", lambda: datetime(2026, 7, 19, 20, 0, tzinfo=IST)
    )

    result = ops_freshness.check_freshness(conn)

    assert result == {
        "latest_price_date": "2026-07-17",
        "expected_last_session": "2026-07-17",
        "stale": False,
    }
    conn.close()
