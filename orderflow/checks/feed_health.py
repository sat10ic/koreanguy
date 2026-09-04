"""Feed-health state machine (U-P0.5; rules R3/R10).

States: HEALTHY / DEGRADED / STALE / DISCONNECTED.

Fed canonical events + lifecycle marks; every transition returns the state
and the named reasons. The R3/R10 rule is mechanical here: depth older than
the stale threshold forces ``order_flow_enabled=False`` and
``flow_state=UNKNOWN`` — the last bullish/bearish reading is never presented
as live. Deterministic: all thresholds injected, clock injectable, so tests
advance time instead of sleeping.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class State(Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    STALE = "STALE"
    DISCONNECTED = "DISCONNECTED"


@dataclass
class Thresholds:
    quote_stale_s: float = 10.0
    depth_stale_s: float = 5.0
    max_clock_skew_ms: float = 1500.0     # |exchange - receive| beyond this flags skew
    duplicate_window_s: float = 0.05      # identical (symbol,ltp,bid) within window = dup
    degraded_reconnects: int = 3          # reconnects within monitor lifetime


@dataclass
class Verdict:
    state: State
    reasons: tuple
    order_flow_enabled: bool
    flow_state: str  # live flow reading or UNKNOWN per R3/R10


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class FeedHealthMonitor:
    def __init__(self, thresholds: Optional[Thresholds] = None, clock=_utcnow) -> None:
        self.t = thresholds or Thresholds()
        self.clock = clock
        self.state = State.HEALTHY
        self.reasons: tuple = ()
        self.last_quote_at: Optional[datetime] = None
        self.last_depth_at: Optional[datetime] = None
        self.reconnect_count = 0
        self.duplicate_count = 0
        self.out_of_order_count = 0
        self.clock_skew_count = 0
        self._start_at = clock()  # staleness baseline for never-seen streams
        self._last_quote_fingerprint: Optional[tuple] = None
        self._last_quote_ts: Optional[datetime] = None
        self._last_depth_fingerprint: Optional[tuple] = None
        self._last_depth_ts: Optional[datetime] = None
        self._disconnected = False
        self._awaiting_fresh_depth = False
        self._reconnected_at: Optional[datetime] = None

    # ---------------------------------------------------------------- intake

    def on_quote(self, event) -> Verdict:
        reasons = []
        fingerprint = (event.symbol, event.ltp)
        duplicate_age = (
            (event.ts_received - self._last_quote_ts).total_seconds()
            if self._last_quote_ts is not None else None
        )
        if (
            fingerprint == self._last_quote_fingerprint
            and duplicate_age is not None
            and 0 <= duplicate_age <= self.t.duplicate_window_s
        ):
            self.duplicate_count += 1
            reasons.append("duplicate_quote")
        self._last_quote_fingerprint = fingerprint
        self._last_quote_ts = event.ts_received
        if self.last_quote_at is not None and event.ts_received < self.last_quote_at:
            self.out_of_order_count += 1
            reasons.append("out_of_order")
        latency = event.feed_latency_ms
        if latency is not None and abs(latency) > self.t.max_clock_skew_ms:
            self.clock_skew_count += 1
            reasons.append("clock_skew")
        if self.last_quote_at is None or event.ts_received > self.last_quote_at:
            self.last_quote_at = event.ts_received
        return self._evaluate(tuple(reasons))

    def on_depth(self, event) -> Verdict:
        reasons = []
        fingerprint = (
            event.symbol,
            tuple((lv.price, lv.quantity, lv.order_count) for lv in event.bids),
            tuple((lv.price, lv.quantity, lv.order_count) for lv in event.asks),
        )
        duplicate_age = (
            (event.ts_received - self._last_depth_ts).total_seconds()
            if self._last_depth_ts is not None else None
        )
        if (
            fingerprint == self._last_depth_fingerprint
            and duplicate_age is not None
            and 0 <= duplicate_age <= self.t.duplicate_window_s
        ):
            self.duplicate_count += 1
            reasons.append("duplicate_depth")
        self._last_depth_fingerprint = fingerprint
        self._last_depth_ts = event.ts_received
        if self.last_depth_at is not None and event.ts_received < self.last_depth_at:
            self.out_of_order_count += 1
            reasons.append("out_of_order")
        if event.feed_latency_ms is not None and abs(event.feed_latency_ms) > self.t.max_clock_skew_ms:
            self.clock_skew_count += 1
            reasons.append("clock_skew")
        if self.last_depth_at is None or event.ts_received > self.last_depth_at:
            self.last_depth_at = event.ts_received
        if self._reconnected_at is None or event.ts_received >= self._reconnected_at:
            self._awaiting_fresh_depth = False
            self._reconnected_at = None
        return self._evaluate(tuple(reasons))

    def on_disconnected(self, reason: str = "closed") -> Verdict:
        self._disconnected = True
        self._awaiting_fresh_depth = True
        return self._evaluate((f"disconnected:{reason}",))

    def on_reconnected(self) -> Verdict:
        self._disconnected = False
        self._awaiting_fresh_depth = True
        self._reconnected_at = self.clock()
        self.reconnect_count += 1
        reasons = ("reconnected",)
        if self.reconnect_count > self.t.degraded_reconnects:
            reasons = reasons + ("reconnect_churn",)
        return self._evaluate(reasons)

    def tick(self) -> Verdict:
        """Re-evaluate time-based staleness without inventing a feed event."""
        return self._evaluate(())

    # ---------------------------------------------------------------- evaluation

    def _evaluate(self, extra_reasons: tuple) -> Verdict:
        now = self.clock()
        reasons = list(extra_reasons)

        if self._disconnected:
            self.state = State.DISCONNECTED
        else:
            # A never-seen stream ages from monitor start; a seen stream ages
            # from its last event. Neither is judged before its threshold.
            depth_age = max(0.0, (now - (self.last_depth_at or self._start_at)).total_seconds())
            quote_age = max(0.0, (now - (self.last_quote_at or self._start_at)).total_seconds())
            depth_stale = depth_age > self.t.depth_stale_s
            quote_stale = quote_age > self.t.quote_stale_s
            if depth_stale and quote_stale:
                self.state = State.STALE
                reasons.append("no_data" if self.last_depth_at is None and self.last_quote_at is None else "all_stale")
            elif depth_stale:
                self.state = State.DEGRADED
                reasons.append("depth_stale")
            elif quote_stale:
                self.state = State.DEGRADED
                reasons.append("quote_stale")
            elif self._awaiting_fresh_depth:
                self.state = State.DEGRADED
                reasons.append("awaiting_fresh_depth")
            elif self.reconnect_count > self.t.degraded_reconnects:
                self.state = State.DEGRADED
                reasons.append("reconnect_churn")
            elif any(
                reason in {"duplicate_quote", "duplicate_depth", "out_of_order", "clock_skew"}
                for reason in extra_reasons
            ):
                self.state = State.DEGRADED
                reasons.append("data_quality")
            else:
                self.state = State.HEALTHY

        self.reasons = tuple(dict.fromkeys(reasons))
        order_flow_enabled = (
            self._disconnected is False
            and self._awaiting_fresh_depth is False
            and self.last_depth_at is not None
            and (now - self.last_depth_at).total_seconds() <= self.t.depth_stale_s
        )
        flow_state = "LIVE" if order_flow_enabled else "UNKNOWN"
        return Verdict(self.state, self.reasons, order_flow_enabled, flow_state)
