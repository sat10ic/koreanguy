from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from manas_os import db
from manas_os.api import app as api_app
from manas_os.live import quotes, refresh
from manas_os.providers.base import SnapshotRow


IST = timezone(timedelta(hours=5, minutes=30))


class _FakeProvider:
    name = "fyers"

    def is_available(self):
        return True

    def get_snapshot(self, symbols, lookback=20):
        assert lookback == 0
        return [
            SnapshotRow(
                symbol=symbol,
                last=123.4,
                today_open=120.0,
                today_low=119.5,
                today_high=124.0,
                today_volume=500_000,
                prev_close=118.0,
            )
            for symbol in symbols
        ]


class _RecordingProvider(_FakeProvider):
    def __init__(self):
        self.requested = None

    def get_snapshot(self, symbols, lookback=20):
        self.requested = list(symbols)
        return super().get_snapshot(symbols, lookback=lookback)


def test_rest_refresh_persists_normalized_fyers_snapshot_with_provenance(tmp_path):
    path = tmp_path / "market.db"
    conn = db.init_db(path)
    try:
        result = refresh.refresh_quotes(
            conn,
            provider=_FakeProvider(),
            symbols=["aaa"],
            observed_at=datetime(2026, 7, 14, 10, 0, tzinfo=IST),
        )
        cached = quotes.get_quotes(conn, ["AAA"])["AAA"]
    finally:
        conn.close()

    assert result == {
        "state": "ready",
        "provider": "fyers",
        "requested": 1,
        "written": 1,
        "failed": 0,
        "as_of": "2026-07-14T10:00:00+05:30",
    }
    assert cached["ltp"] == 123.4
    assert cached["open"] == 120.0
    assert cached["high"] == 124.0
    assert cached["low"] == 119.5
    assert cached["volume"] == 500_000
    assert cached["prev_close"] == 118.0
    assert cached["provider"] == "fyers"
    assert cached["bar_ts"] == "2026-07-14T10:00:00+05:30"


def test_explicit_empty_refresh_does_not_expand_to_full_universe(tmp_path):
    conn = db.init_db(tmp_path / "market.db")
    provider = _RecordingProvider()
    try:
        result = refresh.refresh_quotes(conn, provider=provider, symbols=[])
    finally:
        conn.close()

    assert provider.requested == []
    assert result["requested"] == 0


def test_live_quotes_endpoint_rejects_stale_cache_as_live(tmp_path, monkeypatch):
    path = tmp_path / "market.db"
    conn = db.init_db(path)
    quotes.update_snapshot(
        conn,
        SnapshotRow(symbol="AAA", last=123.4),
        provider="fyers",
        observed_at="2026-07-14T09:55:00+05:30",
    )
    conn.close()

    original = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: original(path))
    monkeypatch.setattr(api_app.market_calendar, "is_market_hours", lambda when=None: True)
    monkeypatch.setattr(
        api_app,
        "_now_ist",
        lambda: datetime(2026, 7, 14, 10, 0, tzinfo=IST),
    )

    body = TestClient(api_app.app).get("/api/live/quotes", params={"symbols": "AAA"}).json()

    assert body["available"] is False
    assert body["state"] == "STALE"
    assert body["provider"] == "fyers"
    assert body["quotes"]["AAA"]["fresh"] is False


def test_live_quotes_endpoint_marks_recent_cache_live(tmp_path, monkeypatch):
    path = tmp_path / "market.db"
    conn = db.init_db(path)
    quotes.update_snapshot(
        conn,
        SnapshotRow(symbol="AAA", last=123.4),
        provider="fyers",
        observed_at="2026-07-14T09:59:30+05:30",
    )
    conn.close()

    original = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: original(path))
    monkeypatch.setattr(api_app.market_calendar, "is_market_hours", lambda when=None: True)
    monkeypatch.setattr(
        api_app,
        "_now_ist",
        lambda: datetime(2026, 7, 14, 10, 0, tzinfo=IST),
    )

    body = TestClient(api_app.app).get("/api/live/quotes", params={"symbols": "AAA"}).json()

    assert body["available"] is True
    assert body["state"] == "LIVE"
    assert body["quotes"]["AAA"]["fresh"] is True


def test_canonical_price_prefers_fresh_live_then_falls_back_to_finalized_eod(tmp_path):
    path = tmp_path / "market.db"
    conn = db.init_db(path)
    try:
        conn.execute(
            "INSERT INTO daily_prices "
            "(symbol,trade_date,series,close,source) VALUES ('AAA','2026-07-13','EQ',118,'bhavcopy')"
        )
        quotes.update_snapshot(
            conn,
            SnapshotRow(symbol="AAA", last=123.4),
            provider="fyers",
            observed_at="2026-07-14T09:59:30+05:30",
        )
        live = quotes.resolve_price(
            conn,
            "AAA",
            on_or_before="2026-07-14",
            now=datetime(2026, 7, 14, 10, 0, tzinfo=IST),
            market_open=True,
            allow_live=True,
        )
        stale = quotes.resolve_price(
            conn,
            "AAA",
            on_or_before="2026-07-14",
            now=datetime(2026, 7, 14, 10, 5, tzinfo=IST),
            market_open=True,
            allow_live=True,
        )
    finally:
        conn.close()

    assert live == {
        "price": 123.4,
        "state": "LIVE",
        "provider": "fyers",
        "as_of": "2026-07-14T09:59:30+05:30",
        "fresh": True,
    }
    assert stale == {
        "price": 118.0,
        "state": "EOD_FINAL",
        "provider": "bhavcopy",
        "as_of": "2026-07-13",
        "fresh": False,
    }


def test_bulk_price_resolution_mixes_live_eod_and_empty_without_cross_talk(tmp_path):
    conn = db.init_db(tmp_path / "market.db")
    try:
        conn.executemany(
            "INSERT INTO daily_prices "
            "(symbol,trade_date,series,close,source) VALUES (?,?,?,?,?)",
            [
                ("AAA", "2026-07-13", "EQ", 118.0, "bhavcopy"),
                ("BBB", "2026-07-12", "EQ", 205.0, "bhavcopy"),
            ],
        )
        quotes.update_snapshot(
            conn,
            SnapshotRow(symbol="AAA", last=123.4),
            provider="fyers",
            observed_at="2026-07-14T09:59:30+05:30",
        )
        resolved = quotes.resolve_prices(
            conn,
            ["AAA", "BBB", "CCC"],
            on_or_before="2026-07-14",
            now=datetime(2026, 7, 14, 10, 0, tzinfo=IST),
            market_open=True,
            allow_live=True,
        )
    finally:
        conn.close()

    assert resolved["AAA"]["state"] == "LIVE"
    assert resolved["BBB"] == {
        "price": 205.0,
        "state": "EOD_FINAL",
        "provider": "bhavcopy",
        "as_of": "2026-07-12",
        "fresh": False,
    }
    assert resolved["CCC"]["state"] == "EMPTY"
