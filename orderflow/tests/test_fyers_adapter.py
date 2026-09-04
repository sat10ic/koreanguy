"""Adapter tests: raw FYERS message dicts → canonical models.

These tests construct raw wire-format dicts on purpose — they sit on the
boundary, speaking the dialect the adapter must translate. Production code
downstream never sees these names (see test_boundaries.py).
"""
from datetime import datetime, timedelta, timezone

import pytest

from orderflow.market_data.fyers_adapter import FyersAdapter
from orderflow.market_data.schemas import DepthSnapshot, QuoteUpdate

UTC = timezone.utc
T_RECV = datetime(2026, 8, 28, 4, 15, 1, tzinfo=UTC)
EPOCH = int((T_RECV - timedelta(seconds=2)).timestamp())  # exchange ~2 s behind local


@pytest.fixture()
def adapter():
    return FyersAdapter()


def make_quote(**overrides):
    msg = {
        "type": "sf",
        "symbol": "NSE:ABC-EQ",
        "ltp": 100.25,
        "open_price": 99.5,
        "high_price": 101.0,
        "low_price": 99.0,
        "prev_close_price": 99.2,
        "vol_traded_today": 150_000,
        "last_traded_qty": 50,
        "exch_feed_time": EPOCH,
    }
    msg.update(overrides)
    return msg


def make_depth(**overrides):
    msg = {"type": "dp", "symbol": "NSE:ABC-EQ", "exch_feed_time": EPOCH}
    for i in range(1, 6):
        msg[f"bid_price{i}"] = 100.0 - 0.05 * i
        msg[f"ask_price{i}"] = 100.1 + 0.05 * i
        msg[f"bid_size{i}"] = 100 * i
        msg[f"ask_size{i}"] = 90 * i
        msg[f"bid_order{i}"] = 2 + i
        msg[f"ask_order{i}"] = 3 + i
    msg.update({"tot_buy_qty": 45_000, "tot_sell_qty": 52_000})
    msg.update(overrides)
    return msg


# ---------------------------------------------------------------- classify / dispatch


def test_classify_buckets(adapter):
    assert adapter.classify(make_quote()) == "quote"
    assert adapter.classify(make_depth()) == "depth"
    assert adapter.classify({"type": "cn"}) == "control"
    assert adapter.classify({"type": "sub"}) == "control"
    assert adapter.classify({"type": "if", "symbol": "NSE:NIFTY50-INDEX"}) == "index"
    assert adapter.classify({"type": "mystery"}) == "unknown"
    assert adapter.classify("not a dict") == "unknown"


def test_parse_dispatches_and_counts_ignored(adapter):
    assert isinstance(adapter.parse(make_quote(), T_RECV), QuoteUpdate)
    assert isinstance(adapter.parse(make_depth(), T_RECV), DepthSnapshot)
    assert adapter.parse({"type": "cn", "code": 200}, T_RECV) is None
    assert adapter.parse({"type": "if"}, T_RECV) is None
    assert adapter.parse({"type": "mystery"}, T_RECV) is None
    assert adapter.skipped["ignored_control"] == 1
    assert adapter.skipped["ignored_index"] == 1
    assert adapter.skipped["unknown_message"] == 1


# ---------------------------------------------------------------- quotes


def test_quote_full_mapping(adapter):
    q = adapter.parse_quote(make_quote(), T_RECV)
    assert q.symbol == "NSE:ABC-EQ"
    assert q.ltp == 100.25
    assert q.open == 99.5 and q.high == 101.0 and q.low == 99.0
    assert q.prev_close == 99.2
    assert q.session_volume == 150_000
    assert q.last_trade_qty == 50
    assert q.ts_received == T_RECV
    assert q.ts_exchange == datetime.fromtimestamp(EPOCH, tz=UTC)
    assert q.feed_latency_ms is not None


def test_quote_missing_optionals_are_none_r5(adapter):
    msg = make_quote()
    for key in ("last_traded_qty", "open_price", "high_price", "low_price", "prev_close_price", "vol_traded_today"):
        del msg[key]
    q = adapter.parse_quote(msg, T_RECV)
    assert q.last_trade_qty is None
    assert q.open is None and q.high is None and q.low is None and q.prev_close is None
    assert q.session_volume is None
    assert q.ltp == 100.25  # present field survives


def test_quote_unparseable_field_is_null_not_invented(adapter):
    q = adapter.parse_quote(make_quote(ltp="not-a-number"), T_RECV)
    assert q.ltp is None


def test_quote_negative_ltp_is_structurally_invalid(adapter):
    assert adapter.parse_quote(make_quote(ltp=-5.0), T_RECV) is None
    assert adapter.skipped["quote_invalid"] == 1


def test_quote_without_symbol_skipped(adapter):
    assert adapter.parse_quote({"type": "sf", "ltp": 1.0}, T_RECV) is None
    assert adapter.skipped["quote_no_symbol"] == 1


def test_exchange_time_string_ist_form(adapter):
    parsed = FyersAdapter.parse_exchange_time("14 Feb 2023 15:19:59 IST")
    assert parsed is not None
    assert parsed.utcoffset().total_seconds() == 5.5 * 3600
    # canonical models normalise to UTC on construction
    q = adapter.parse_quote(make_quote(exch_feed_time="14 Feb 2023 15:19:59 IST"), T_RECV)
    assert q.ts_exchange == datetime(2023, 2, 14, 9, 49, 59, tzinfo=UTC)


def test_exchange_time_garbage_is_none(adapter):
    q = adapter.parse_quote(make_quote(exch_feed_time="whenever"), T_RECV)
    assert q.ts_exchange is None


def test_exchange_clock_ahead_of_local_is_kept_as_negative_latency(adapter):
    # exchange 3 s AHEAD of local: latency is negative — that is clock-skew
    # signal to be recorded, not invalid data to be dropped.
    ahead = int((T_RECV + timedelta(seconds=3)).timestamp())
    snap = adapter.parse_depth(make_depth(exch_feed_time=ahead), T_RECV)
    assert snap is not None
    assert snap.feed_latency_ms is not None and snap.feed_latency_ms < 0


# ---------------------------------------------------------------- depth


def test_depth_flat_fields_expand_to_levels(adapter):
    snap = adapter.parse_depth(make_depth(), T_RECV)
    assert len(snap.bids) == 5 and len(snap.asks) == 5
    assert snap.bids[0].price == pytest.approx(99.95)
    assert snap.bids[0].quantity == 100
    assert snap.bids[0].order_count == 3
    assert snap.asks[0].order_count == 4
    assert snap.total_buy_qty == 45_000 and snap.total_sell_qty == 52_000
    assert snap.feed_latency_ms is not None


def test_depth_missing_order_counts_stay_none_r5(adapter):
    msg = make_depth()
    for i in range(1, 6):
        del msg[f"bid_order{i}"]
        del msg[f"ask_order{i}"]
    snap = adapter.parse_depth(msg, T_RECV)
    assert len(snap.bids) == 5
    assert all(level.order_count is None for level in snap.bids + snap.asks)


def test_depth_absent_levels_are_dropped_not_zero_filled(adapter):
    msg = make_depth()
    for i in range(4, 6):  # levels 4 and 5 absent entirely
        for side in ("bid", "ask"):
            del msg[f"{side}_price{i}"]
            del msg[f"{side}_size{i}"]
            del msg[f"{side}_order{i}"]
    snap = adapter.parse_depth(msg, T_RECV)
    assert len(snap.bids) == 3 and len(snap.asks) == 3


def test_depth_invalid_level_dropped_and_counted(adapter):
    snap = adapter.parse_depth(make_depth(bid_price2=-1.0), T_RECV)
    assert len(snap.bids) == 4
    assert adapter.skipped["depth_level_invalid"] == 1


# ---------------------------------------------------------------- tbt


def test_tbt_50_levels_parse(adapter):
    msg = {
        "type": "tbt",
        "symbol": "NSE:ABC-EQ",
        "exch_feed_time": EPOCH,
        "bids": [{"price": 100 - 0.01 * i, "quantity": 10 * i, "order_count": i} for i in range(1, 51)],
        "asks": [{"price": 100 + 0.01 * i, "quantity": 10 * i, "order_count": i} for i in range(1, 51)],
        "total_buy_qty": 90_000,
        "total_sell_qty": 80_000,
    }
    snap = adapter.parse_tbt(msg, T_RECV)
    assert len(snap.bids) == 50 and len(snap.asks) == 50
    assert snap.total_buy_qty == 90_000


# ---------------------------------------------------------------- outbound encodings


def test_encode_subscribe_uses_wire_types(adapter):
    payload = adapter.encode_subscribe("depth", ["NSE:A-EQ", "NSE:B-EQ"])
    assert payload == {"symbols": ["NSE:A-EQ", "NSE:B-EQ"], "data_type": "DepthUpdate"}
    quote_payload = adapter.encode_subscribe("quote", ["NSE:A-EQ"])
    assert quote_payload["data_type"] == "SymbolUpdate"


def test_manager_stays_fyers_free_of_ack_literals():
    import inspect

    from orderflow.market_data import websocket_manager

    source = inspect.getsource(websocket_manager)
    for marker in ('"sub"', "'sub'", "SymbolUpdate", "DepthUpdate"):
        assert marker not in source
