"""Canonical schema tests: R5 null discipline, validation, latency."""
from datetime import datetime, timezone

import pytest

from orderflow.market_data.schemas import DepthLevel, DepthSnapshot, QuoteUpdate, SchemaError

UTC = timezone.utc
T_RECV = datetime(2026, 8, 28, 4, 15, 0, tzinfo=UTC)
T_EXCH = datetime(2026, 8, 28, 4, 14, 59, 850000, tzinfo=UTC)


def test_quote_defaults_are_none_not_zero():
    q = QuoteUpdate(ts_exchange=None, ts_received=T_RECV, symbol="NSE:X-EQ")
    assert q.ltp is None and q.open is None and q.high is None
    assert q.low is None and q.prev_close is None
    assert q.session_volume is None and q.last_trade_qty is None


def test_quote_zero_is_valid_and_distinct_from_none():
    q = QuoteUpdate(ts_exchange=None, ts_received=T_RECV, symbol="NSE:X-EQ", ltp=0.0, session_volume=0)
    assert q.ltp == 0.0 and q.session_volume == 0


def test_quote_rejects_naive_timestamp():
    with pytest.raises(SchemaError):
        QuoteUpdate(ts_exchange=None, ts_received=datetime(2026, 8, 28, 4, 15), symbol="NSE:X-EQ")


def test_quote_rejects_negative_price_and_empty_symbol():
    with pytest.raises(SchemaError):
        QuoteUpdate(ts_exchange=None, ts_received=T_RECV, symbol="NSE:X-EQ", ltp=-1.0)
    with pytest.raises(SchemaError):
        QuoteUpdate(ts_exchange=None, ts_received=T_RECV, symbol="")


def test_quote_normalises_timestamps_to_utc_and_computes_latency():
    q = QuoteUpdate(ts_exchange=T_EXCH, ts_received=T_RECV, symbol="NSE:X-EQ", ltp=10.0)
    assert q.ts_received.tzinfo is not None and q.ts_exchange.tzinfo is not None
    assert q.feed_latency_ms == pytest.approx(150.0)
    assert q.feed_latency_ms is None or QuoteUpdate(
        ts_exchange=None, ts_received=T_RECV, symbol="NSE:X-EQ"
    ).feed_latency_ms is None


def test_depth_level_rejects_negative_and_requires_numbers():
    assert DepthLevel(price=100.5, quantity=10, order_count=None).order_count is None
    with pytest.raises(SchemaError):
        DepthLevel(price=-1, quantity=10)
    with pytest.raises(SchemaError):
        DepthLevel(price=1.0, quantity=-5)
    with pytest.raises(SchemaError):
        DepthLevel(price="abc", quantity=10)


def test_snapshot_feed_latency_computed_when_exchange_time_present():
    snap = DepthSnapshot(
        ts_exchange=T_EXCH,
        ts_received=T_RECV,
        symbol="NSE:X-EQ",
        bids=(DepthLevel(price=99.95, quantity=100),),
    )
    assert snap.feed_latency_ms == pytest.approx(150.0)


def test_snapshot_no_latency_without_exchange_time():
    snap = DepthSnapshot(ts_exchange=None, ts_received=T_RECV, symbol="NSE:X-EQ")
    assert snap.feed_latency_ms is None
    assert snap.bids == () and snap.asks == ()


def test_snapshot_rejects_non_level_entries():
    with pytest.raises(SchemaError):
        DepthSnapshot(ts_exchange=None, ts_received=T_RECV, symbol="NSE:X-EQ", bids=(("x", 1),))


def test_models_are_frozen():
    q = QuoteUpdate(ts_exchange=None, ts_received=T_RECV, symbol="NSE:X-EQ")
    with pytest.raises(Exception):
        q.ltp = 1.0
    level = DepthLevel(price=1.0, quantity=1)
    with pytest.raises(Exception):
        level.quantity = 2
