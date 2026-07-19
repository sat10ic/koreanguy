import sqlite3
from datetime import date

from manas_os import ops_freshness


def test_check_freshness_reports_current_session_as_fresh(monkeypatch):
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE daily_prices (trade_date TEXT, series TEXT)")
    conn.execute("INSERT INTO daily_prices VALUES ('2026-07-17', 'EQ')")
    monkeypatch.setattr(ops_freshness, "_today_ist", lambda: date(2026, 7, 17))

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
    monkeypatch.setattr(ops_freshness, "_today_ist", lambda: date(2026, 7, 17))

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
    monkeypatch.setattr(ops_freshness, "_today_ist", lambda: date(2026, 7, 19))

    result = ops_freshness.check_freshness(conn)

    assert result == {
        "latest_price_date": "2026-07-17",
        "expected_last_session": "2026-07-17",
        "stale": False,
    }
    conn.close()
