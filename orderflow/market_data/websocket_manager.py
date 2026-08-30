"""Connection lifecycle for the market-data feed: connect, subscribe,
reconnect, heartbeat.

This module is deliberately provider-agnostic — it contains no FYERS
vocabulary. Wire payloads are produced by the injected adapter
(``FyersAdapter.encode_subscribe``); transport I/O goes through the
:class:`MessageTransport` port. A live transport (owner-side glue over the
official ``fyers-apiv3`` client, holding credentials out-of-band per R7)
plugs in via a zero-argument ``transport_factory``; tests and the capability
audit plug in a replay transport instead. Nothing here reads env or config.

Design notes
------------
* Lifecycle is observable: every connect / disconnect / resubscribe emits a
  :class:`LifecycleEvent` to ``on_lifecycle``. The capability audit turns
  these into gap records — a disconnect is a visible gap, never interpolated.
* Heartbeat is a receive-side watchdog: if no message of any kind arrives
  within ``stale_after_s``, the connection is presumed dead and force-
  reconnected (cause ``heartbeat_timeout``). Transports may additionally
  expose ``send_ping()``; the manager calls it every ``heartbeat_interval_s``
  when present.
* Reconnects are exponential backoff (base ×2, capped), executed through the
  injected ``sleeper`` so tests can advance virtual time deterministically.
  After ``max_reconnects`` consecutive failures the manager gives up and
  emits ``reconnect_abandoned``.
* A :class:`TransportClosed` with reason ``"exhausted"`` is treated as a
  normal end-of-stream (replay/recorded source), not a failure: the manager
  emits ``stream_end`` and stops.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Optional, Protocol, Sequence

from .fyers_adapter import FyersAdapter
from .schemas import DepthSnapshot, QuoteUpdate

EventCallback = Callable[[Any], None]
ControlCallback = Callable[[Mapping[str, Any]], None]
LifecycleCallback = Callable[["LifecycleEvent"], None]
Clock = Callable[[], datetime]
Sleeper = Callable[[float], None]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _sleep_noop(_seconds: float) -> None:
    return None


class TransportClosed(Exception):
    """The transport produced no message because the stream ended.

    ``reason`` distinguishes failure (``"forced_disconnect"``,
    ``"heartbeat_timeout"`` …) from a normal end of a recorded/replayed
    stream (``"exhausted"``).
    """

    def __init__(self, reason: str = "closed") -> None:
        super().__init__(reason)
        self.reason = reason


class MessageTransport(Protocol):
    """Minimal I/O port the manager needs from any feed transport.

    Implementations own authentication (connect-time headers, tokens) — the
    manager never sees credentials (R7).
    """

    def connect(self) -> None: ...

    def send(self, payload: Mapping[str, Any]) -> None: ...

    def receive(self, timeout_s: float) -> Mapping[str, Any]: ...

    def close(self) -> None: ...


@dataclass(frozen=True)
class LifecycleEvent:
    """One observable connection-lifecycle step."""

    kind: str  # connected | disconnected | resubscribed | heartbeat_timeout | reconnect_abandoned | stream_end
    at: datetime
    detail: Mapping[str, Any] = field(default_factory=dict)


@dataclass
class SubscribeAttempt:
    """A subscribe request whose ack may arrive later on the message stream."""

    symbols: tuple
    canonical_kind: str
    sent_at: datetime
    ack_at: Optional[datetime] = None
    ack_code: Optional[int] = None
    ack_message: Optional[str] = None
    accepted: Optional[bool] = None  # None = no ack observed yet

    def as_dict(self) -> dict:
        return {
            "symbols": list(self.symbols),
            "data_kind": self.canonical_kind,
            "sent_at": self.sent_at.isoformat(),
            "ack_at": self.ack_at.isoformat() if self.ack_at else None,
            "ack_code": self.ack_code,
            "ack_message": self.ack_message,
            "accepted": self.accepted,
        }


class WebSocketManager:
    """Drives a :class:`MessageTransport` and emits canonical events.

    The manager never parses provider messages itself: data messages go
    through the adapter, control messages are passed to ``on_control``
    verbatim and used to resolve :class:`SubscribeAttempt` outcomes.
    """

    def __init__(
        self,
        transport_factory: Callable[[], MessageTransport],
        adapter: FyersAdapter,
        *,
        on_event: Optional[EventCallback] = None,
        on_control: Optional[ControlCallback] = None,
        on_lifecycle: Optional[LifecycleCallback] = None,
        clock: Clock = utc_now,
        sleeper: Sleeper = _sleep_noop,
        heartbeat_interval_s: float = 5.0,
        stale_after_s: float = 30.0,
        reconnect_base_delay_s: float = 0.5,
        reconnect_max_delay_s: float = 30.0,
        max_reconnects: Optional[int] = None,
    ) -> None:
        self._transport_factory = transport_factory
        self._adapter = adapter
        self._on_event = on_event
        self._on_control = on_control
        self._on_lifecycle = on_lifecycle
        self._clock = clock
        self._sleeper = sleeper
        self._heartbeat_interval_s = heartbeat_interval_s
        self._stale_after_s = stale_after_s
        self._base_delay_s = reconnect_base_delay_s
        self._max_delay_s = reconnect_max_delay_s
        self._max_reconnects = max_reconnects

        self._transport: Optional[MessageTransport] = None
        self._requested_symbols: frozenset[str] = frozenset()
        self._subscribes: list[SubscribeAttempt] = []
        self._last_message_at: Optional[datetime] = None
        self._last_ping_at: Optional[datetime] = None
        self._reconnects = 0
        self.closed = False

    # ------------------------------------------------------------------ properties

    @property
    def connected(self) -> bool:
        return self._transport is not None

    @property
    def transport(self) -> Optional[MessageTransport]:
        """The current transport, or None when disconnected. Callers that
        need shim-specific capabilities (error queues) use this instead of
        reaching into privates."""
        return self._transport

    @property
    def reconnects(self) -> int:
        return self._reconnects

    @property
    def subscribed_symbols(self) -> frozenset:
        return self._requested_symbols

    @property
    def subscribe_attempts(self) -> list:
        return list(self._subscribes)

    # ------------------------------------------------------------------ lifecycle plumbing

    def _emit(self, kind: str, **detail: Any) -> LifecycleEvent:
        event = LifecycleEvent(kind=kind, at=self._clock(), detail=detail)
        if self._on_lifecycle is not None:
            self._on_lifecycle(event)
        return event

    # ------------------------------------------------------------------ connection

    def connect(self) -> None:
        if self._transport is not None:
            return
        transport = self._transport_factory()
        transport.connect()
        self._transport = transport
        self._last_message_at = self._clock()
        self._emit("connected")

    def close(self) -> None:
        if self._transport is not None:
            self._transport.close()
            self._transport = None
        self.closed = True

    def subscribe(self, symbols: Sequence[str]) -> None:
        """Request subscriptions for ``symbols`` on every canonical kind.

        Acks arrive asynchronously as control messages; each request is
        tracked as a :class:`SubscribeAttempt` and resolved in
        :meth:`_resolve_subscribe_acks`.
        """
        self._require_transport()
        symbols = tuple(dict.fromkeys(symbols))  # dedupe, keep order
        self._requested_symbols |= frozenset(symbols)
        for canonical_kind in ("quote", "depth"):
            payload = self._adapter.encode_subscribe(canonical_kind, symbols)
            attempt = SubscribeAttempt(
                symbols=symbols, canonical_kind=canonical_kind, sent_at=self._clock()
            )
            self._subscribes.append(attempt)
            self._transport.send(payload)

    def unsubscribe(self, symbols: Sequence[str]) -> None:
        self._require_transport()
        symbols = tuple(symbols)
        for canonical_kind in ("quote", "depth"):
            self._transport.send(self._adapter.encode_unsubscribe(canonical_kind, symbols))
        self._requested_symbols -= frozenset(symbols)

    def _require_transport(self) -> None:
        if self._transport is None:
            raise RuntimeError("not connected; call connect() first")

    # ------------------------------------------------------------------ message loop

    def poll_once(self, timeout_s: float = 1.0) -> str:
        """Process at most one incoming message. Returns one of
        ``"event"`` / ``"control"`` / ``"skipped"`` / ``"timeout"`` /
        ``"reconnected"``.

        A ``TransportClosed`` with reason ``"timeout"`` is a benign empty poll
        on a live socket (quiet market second) — no reconnect; heartbeat
        staleness is what decides a dead connection, not one empty poll."""
        self._require_transport()
        try:
            message = self._transport.receive(timeout_s)
        except TransportClosed as exc:
            if exc.reason == "timeout":
                return "timeout"
            if exc.reason == "exhausted":
                self._emit("stream_end", reason=exc.reason)
                raise
            self._reconnect(exc.reason)
            return "reconnected"
        self._last_message_at = self._clock()
        return self._dispatch(message)

    def _dispatch(self, message: Mapping[str, Any]) -> str:
        kind = self._adapter.classify(message)
        if kind in ("quote", "depth", "tbt"):
            event = self._adapter.parse(message, self._clock())
            if event is not None and self._on_event is not None:
                self._on_event(event)
                return "event"
            return "skipped"
        if kind in ("control", "index", "unknown"):
            if kind == "control":
                self._resolve_subscribe_acks(message)
                if self._on_control is not None:
                    self._on_control(message)
                return "control"
            self._adapter.skipped[f"ignored_{kind}"] += 1
            return "skipped"
        return "skipped"

    def _resolve_subscribe_acks(self, message: Mapping[str, Any]) -> None:
        if not self._adapter.is_subscribe_ack(message):
            return
        ok = self._adapter.ack_indicates_success(message)
        # acks arrive in send order: resolve the OLDEST unresolved attempt
        for attempt in self._subscribes:
            if attempt.accepted is None:
                attempt.accepted = bool(ok)
                attempt.ack_at = self._clock()
                attempt.ack_code = message.get("code")
                attempt.ack_message = message.get("message")
                return

    # ------------------------------------------------------------------ heartbeat

    def is_stale(self) -> bool:
        if self._last_message_at is None:
            return False
        age_s = (self._clock() - self._last_message_at).total_seconds()
        return age_s > self._stale_after_s

    def maybe_heartbeat(self) -> None:
        """Send a transport-level ping on interval; force-reconnect on stale."""
        self._require_transport()
        now = self._clock()
        if self._last_message_at is not None and (now - self._last_message_at).total_seconds() > self._heartbeat_interval_s:
            ping = getattr(self._transport, "send_ping", None)
            if callable(ping):
                ping()
                self._last_ping_at = now
        if self.is_stale():
            self._emit("heartbeat_timeout", stale_after_s=self._stale_after_s)
            self._reconnect("heartbeat_timeout")

    # ------------------------------------------------------------------ reconnect

    def _reconnect(self, reason: str) -> None:
        if self._transport is not None:
            self._transport.close()
            self._transport = None
        self._emit("disconnected", cause=reason)
        if self._max_reconnects is not None and self._reconnects >= self._max_reconnects:
            self._emit("reconnect_abandoned", reconnects=self._reconnects)
            raise TransportClosed("abandoned")
        delay = min(self._base_delay_s * (2**self._reconnects), self._max_delay_s)
        self._reconnects += 1
        self._sleeper(delay)
        self._emit("reconnect_scheduled", delay_s=delay, attempt=self._reconnects)
        transport = self._transport_factory()
        transport.connect()
        self._transport = transport
        self._last_message_at = self._clock()
        self._emit("connected", after_reconnect=True, cause=reason)
        if self._requested_symbols:
            self.subscribe(sorted(self._requested_symbols))
            self._emit("resubscribed", symbols=sorted(self._requested_symbols))

    # ------------------------------------------------------------------ long-running

    def run(
        self,
        *,
        max_messages: Optional[int] = None,
        until: Optional[datetime] = None,
        poll_timeout_s: float = 1.0,
        heartbeat: bool = True,
    ) -> int:
        """Poll until the stream ends, a limit is hit, or the connection is
        abandoned. Returns the number of canonical events emitted."""
        processed = 0
        while True:
            if max_messages is not None and processed >= max_messages:
                return processed
            if until is not None and self._clock() >= until:
                return processed
            if heartbeat and self.connected:
                try:
                    self.maybe_heartbeat()
                except TransportClosed as exc:
                    if exc.reason in ("exhausted", "abandoned"):
                        return processed
                    raise
            try:
                outcome = self.poll_once(poll_timeout_s)
            except TransportClosed as exc:
                if exc.reason in ("exhausted", "abandoned"):
                    return processed
                raise
            if outcome == "event":
                processed += 1
