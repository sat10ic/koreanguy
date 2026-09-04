"""WebSocket manager tests: connect, subscribe, ack resolution, forced
disconnect → reconnect + resubscribe, heartbeat staleness, stream end.

All offline: a scripted fake transport, an injectable virtual clock and a
recording sleeper. No network, no credentials (the manager takes none).
"""
from datetime import datetime, timedelta, timezone

import pytest

from orderflow.market_data.fyers_adapter import FyersAdapter
from orderflow.market_data.schemas import DepthSnapshot, QuoteUpdate
from orderflow.market_data.websocket_manager import LifecycleEvent, TransportClosed, WebSocketManager

UTC = timezone.utc
T0 = datetime(2026, 8, 28, 4, 15, 0, tzinfo=UTC)

QUOTE = {"type": "sf", "symbol": "NSE:A-EQ", "ltp": 10.0}
DEPTH = {"type": "dp", "symbol": "NSE:A-EQ", "bid_price1": 9.95, "bid_size1": 10, "ask_price1": 10.05, "ask_size1": 12}
ACK_OK = {"type": "sub", "code": 200, "message": "Subscribed", "s": "ok"}
ACK_FAIL = {"type": "sub", "code": 11011, "message": "subscription failed", "s": "error"}


class ScriptedTransport:
    """Transport whose receive() replays a script. Script items are message
    dicts or TransportClosed instances to raise. After exhaustion the stream
    ends (TransportClosed "exhausted")."""

    def __init__(self, script, sent_sink):
        self.script = script
        self.sent_sink = sent_sink
        self.connected = False

    def connect(self):
        self.connected = True

    def send(self, payload):
        self.sent_sink.append(dict(payload))

    def receive(self, timeout_s):
        if not self.connected:
            raise TransportClosed("forced_disconnect")
        while self.script:
            item = self.script.pop(0)
            if isinstance(item, TransportClosed):
                raise item
            return item
        raise TransportClosed("exhausted")

    def close(self):
        self.connected = False


class Harness:
    """Builds a manager over scripted transports with a virtual clock."""

    def __init__(self, script, **kwargs):
        self.script = list(script)
        self.sent: list[dict] = []
        self.events: list = []
        self.controls: list = []
        self.lifecycle: list[LifecycleEvent] = []
        self.delays: list[float] = []
        self.state = {"now": T0}
        self.manager = WebSocketManager(
            self._factory,
            FyersAdapter(),
            on_event=self.events.append,
            on_control=self.controls.append,
            on_lifecycle=self.lifecycle.append,
            clock=lambda: self.state["now"],
            sleeper=self._sleep,
            **kwargs,
        )

    def _factory(self):
        return ScriptedTransport(self.script, self.sent)

    def _sleep(self, seconds):
        self.delays.append(seconds)
        self.state["now"] += timedelta(seconds=seconds)

    def advance(self, seconds):
        self.state["now"] += timedelta(seconds=seconds)


def test_connect_and_subscribe_send_both_kinds():
    h = Harness([ACK_OK, ACK_OK])
    h.manager.connect()
    assert h.manager.connected
    h.manager.subscribe(["NSE:A-EQ", "NSE:B-EQ"])
    kinds = [payload["data_type"] for payload in h.sent]
    assert kinds == ["SymbolUpdate", "DepthUpdate"]
    assert all(payload["symbols"] == ["NSE:A-EQ", "NSE:B-EQ"] for payload in h.sent)
    assert h.manager.subscribed_symbols == frozenset({"NSE:A-EQ", "NSE:B-EQ"})
    assert h.lifecycle[0].kind == "connected"


def test_subscribe_acks_resolve_fifo_including_rejection():
    h = Harness([ACK_OK, ACK_FAIL])
    h.manager.connect()
    h.manager.subscribe(["NSE:A-EQ"])  # one request per kind → two attempts
    h.manager.poll_once()
    h.manager.poll_once()
    attempts = h.manager.subscribe_attempts
    assert [a.accepted for a in attempts] == [True, False]
    assert attempts[0].canonical_kind == "quote"
    assert attempts[1].canonical_kind == "depth"
    assert attempts[1].ack_code == 11011
    assert attempts[1].ack_at is not None


def test_two_batches_resolve_in_send_order():
    h = Harness([ACK_OK, ACK_OK, ACK_FAIL, ACK_FAIL])
    h.manager.connect()
    h.manager.subscribe(["NSE:A-EQ"])
    h.manager.subscribe(["NSE:X-EQ", "NSE:Y-EQ"])
    for _ in range(4):
        h.manager.poll_once()
    flags = [a.accepted for a in h.manager.subscribe_attempts]
    assert flags == [True, True, False, False]


def test_unresolved_acks_report_none():
    h = Harness([])
    h.manager.connect()
    h.manager.subscribe(["NSE:A-EQ"])
    assert h.manager.subscribe_attempts[0].accepted is None


def test_poll_dispatches_canonical_events():
    h = Harness([QUOTE, DEPTH])
    h.manager.connect()
    assert h.manager.poll_once() == "event"
    assert h.manager.poll_once() == "event"
    assert [type(e) for e in h.events] == [QuoteUpdate, DepthSnapshot]
    assert h.events[0].ltp == 10.0
    assert h.events[1].bids[0].price == 9.95


def test_forced_disconnect_reconnects_resubscribes_and_records_gap_parts():
    script = [
        ACK_OK,
        ACK_OK,
        QUOTE,
        TransportClosed("forced_disconnect"),
        ACK_OK,
        ACK_OK,
        DEPTH,
    ]
    h = Harness(script)
    h.manager.connect()
    h.manager.subscribe(["NSE:A-EQ"])
    processed = h.manager.run(heartbeat=False)

    kinds = [e.kind for e in h.lifecycle]
    assert kinds.count("connected") == 2  # initial + after reconnect
    assert "disconnected" in kinds and "resubscribed" in kinds
    disc = next(e for e in h.lifecycle if e.kind == "disconnected")
    reconn = next(e for e in h.lifecycle if e.kind == "connected" and e.detail.get("after_reconnect"))
    assert disc.detail["cause"] == "forced_disconnect"
    assert reconn.at > disc.at
    assert h.delays == [0.5]  # first backoff step, consumed on the virtual clock
    assert h.manager.reconnects == 1
    assert processed >= 1
    # resubscribe re-sent both wire kinds for the still-requested symbol set
    resub_payloads = h.sent[2:]
    assert [p["data_type"] for p in resub_payloads] == ["SymbolUpdate", "DepthUpdate"]
    assert all(p["symbols"] == ["NSE:A-EQ"] for p in resub_payloads)
    assert isinstance(h.events[-1], DepthSnapshot)


def test_exhausted_stream_ends_cleanly():
    h = Harness([QUOTE])
    h.manager.connect()
    processed = h.manager.run(heartbeat=False)
    assert processed == 1
    assert h.lifecycle[-1].kind == "stream_end"


def test_heartbeat_staleness_forces_reconnect():
    h = Harness([QUOTE], stale_after_s=30.0, heartbeat_interval_s=5.0)
    h.manager.connect()
    h.manager.poll_once()
    h.advance(31)  # silence past the stale window
    h.manager.maybe_heartbeat()
    kinds = [e.kind for e in h.lifecycle]
    assert "heartbeat_timeout" in kinds
    assert h.manager.reconnects == 1


def test_not_stale_within_window():
    h = Harness([QUOTE], stale_after_s=30.0)
    h.manager.connect()
    h.manager.poll_once()
    h.advance(10)
    assert h.manager.is_stale() is False


def test_max_reconnects_abandons():
    h = Harness(
        [QUOTE, TransportClosed("forced_disconnect"), TransportClosed("forced_disconnect")],
        max_reconnects=1,
    )
    h.manager.connect()
    h.manager.poll_once()          # QUOTE event
    h.manager.poll_once()          # first disconnect → reconnect #1 succeeds
    assert h.manager.reconnects == 1
    with pytest.raises(TransportClosed):  # second disconnect → limit hit
        h.manager.poll_once()
    kinds = [e.kind for e in h.lifecycle]
    assert "reconnect_abandoned" in kinds
    assert h.manager.connected is False


def test_unsubscribe_removes_from_requested_set():
    h = Harness([])
    h.manager.connect()
    h.manager.subscribe(["NSE:A-EQ", "NSE:B-EQ"])
    h.manager.unsubscribe(["NSE:B-EQ"])
    assert h.manager.subscribed_symbols == frozenset({"NSE:A-EQ"})


def test_poll_requires_connection():
    h = Harness([])
    with pytest.raises(RuntimeError):
        h.manager.poll_once()


def test_benign_poll_timeout_does_not_reconnect():
    class QuietTransport(ScriptedTransport):
        """Never yields messages, never drops: empty polls are timeouts."""

        def receive(self, timeout_s):
            if not self.connected:
                raise TransportClosed("forced_disconnect")
            raise TransportClosed("timeout")

    h = Harness.__new__(Harness)
    h.sent, h.events, h.controls, h.lifecycle, h.delays = [], [], [], [], []
    h.state = {"now": T0}
    h.manager = WebSocketManager(
        lambda: QuietTransport([], h.sent),
        FyersAdapter(),
        on_event=h.events.append,
        on_control=h.controls.append,
        on_lifecycle=h.lifecycle.append,
        clock=lambda: h.state["now"],
        sleeper=h._sleep,
    )
    h.manager.connect()
    assert h.manager.poll_once() == "timeout"
    assert h.manager.poll_once() == "timeout"
    assert h.manager.reconnects == 0
    assert h.manager.connected is True
    assert "disconnected" not in [e.kind for e in h.lifecycle]
