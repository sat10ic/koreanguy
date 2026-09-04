"""Continuous canonical event recorder for the unified desk's offline core.

It is a pair of callbacks for ``WebSocketManager``: ``record_event`` persists
quotes/depth before updating health, and ``record_lifecycle`` persists every
connection transition plus explicit closed gaps. Credentials and provider wire
messages never enter this boundary.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from orderflow.checks.feed_health import FeedHealthMonitor
from orderflow.market_data.schemas import DepthSnapshot, QuoteUpdate

from .parquet_writer import ParquetWriter


class ContinuousRecorder:
    def __init__(
        self,
        writer: ParquetWriter,
        monitor: FeedHealthMonitor,
        *,
        batch_size: int = 1000,
    ) -> None:
        if isinstance(batch_size, bool) or not isinstance(batch_size, int) or batch_size < 1:
            raise ValueError("batch_size must be a positive integer")
        self.writer = writer
        self.monitor = monitor
        self.batch_size = batch_size
        self._quotes: list[QuoteUpdate] = []
        self._depth: list[DepthSnapshot] = []
        self._health: list[tuple] = []
        self._gap_started_at: Optional[datetime] = None
        self._gap_cause: Optional[str] = None

    def record_event(self, event) -> None:
        """Buffer a canonical event and its health verdict in the same batch."""
        if isinstance(event, QuoteUpdate):
            self._quotes.append(event)
            verdict = self.monitor.on_quote(event)
        elif isinstance(event, DepthSnapshot):
            self._depth.append(event)
            verdict = self.monitor.on_depth(event)
        else:
            raise TypeError(f"unsupported event type {type(event)!r}")
        self._health.append((event.ts_received, verdict, event.symbol))
        self._maybe_flush()

    def record_lifecycle(self, event) -> None:
        """Persist connection state and turn disconnect/resubscribe into a gap."""
        self.flush()
        self.writer.write_lifecycle(event)
        verdict = None
        if event.kind == "disconnected":
            cause = str(event.detail.get("cause") or "closed")
            if self._gap_started_at is None:
                self._gap_started_at = event.at
                self._gap_cause = cause
            verdict = self.monitor.on_disconnected(cause)
        elif event.kind == "connected" and event.detail.get("after_reconnect"):
            verdict = self.monitor.on_reconnected()
        elif event.kind == "reconnect_abandoned":
            verdict = self.monitor.on_disconnected("reconnect_abandoned")
        elif event.kind == "resubscribed" and self._gap_started_at is not None:
            self.writer.write_gap(
                self._gap_started_at,
                event.at,
                self._gap_cause or "closed",
            )
            self._gap_started_at = None
            self._gap_cause = None
        elif event.kind == "stream_end" and self._gap_started_at is not None:
            # stream ended mid-outage: close the gap so it cannot stay
            # unterminated in the recorded record (CP-2 finding 3)
            self.writer.write_gap(
                self._gap_started_at,
                event.at,
                self._gap_cause or "closed",
            )
            self._gap_started_at = None
            self._gap_cause = None
        if verdict is not None:
            self.writer.write_health(event.at, verdict)

    def tick(self) -> None:
        """Persist a clock-driven health check during quiet feed periods."""
        verdict = self.monitor.tick()
        self._health.append((self.monitor.clock(), verdict, "__FEED__"))
        self._maybe_flush()

    def _maybe_flush(self) -> None:
        if len(self._quotes) + len(self._depth) + len(self._health) >= self.batch_size:
            self.flush()

    def flush(self) -> None:
        """Write buffered canonical events in partition-sized Parquet batches."""
        if self._quotes:
            self.writer.write_quotes(self._quotes)
            self._quotes.clear()
        if self._depth:
            self.writer.write_depth(self._depth)
            self._depth.clear()
        if self._health:
            self.writer.write_health_batch(self._health)
            self._health.clear()

    def finalize(self, at: datetime) -> None:
        """Flush buffers and close an outage interval at session shutdown."""
        self.flush()
        if self._gap_started_at is not None:
            self.writer.write_gap(
                self._gap_started_at,
                at,
                self._gap_cause or "session_ended_while_disconnected",
            )
            self._gap_started_at = None
            self._gap_cause = None

    close = flush
