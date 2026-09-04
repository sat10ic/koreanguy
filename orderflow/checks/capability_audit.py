"""Feed capability audit (build-manual Task P0.1).

Measures what the feed actually does and writes ``capability.json`` — the
file the future feature engine reads at runtime to enable or disable windows
(manual R1: measure first, never assume).

What it measures
----------------
* depth inter-arrival histogram, fixed buckets
  (0–100 / 100–250 / 250–500 / 500–1000 / >1000 ms), globally and per symbol
* median + p95 update interval **per liquidity bucket** — one global number
  hides the difference between liquid midcaps and thin smallcaps
* quote/depth synchronisation (nearest-event offsets, share within window)
* burstiness (coefficient of variation, max messages per 1 s window)
* stale periods per symbol (inter-arrival beyond threshold), excluding
  intervals that overlap a disconnect
* disconnect gaps: data-silent intervals, correlated with lifecycle events —
  gaps are recorded, never interpolated
* subscription outcomes (acks/rejections actually observed), against the
  documented batch limit; if no rejection is observed the limit is reported
  as NOT established, not guessed
* which optional fields are populated (``order_count``, ``total_buy_qty``,
  ``total_sell_qty``, ``last_trade_qty``)
* whether more than 5 depth levels are observed (50-level TBT). The standard
  data socket carries 5 levels by protocol; TBT requires the owner's separate
  live session, so the default answer here is honest ``not_observed``.

Offline operation: ``run_synthetic_audit`` replays a recorded-style fixture
(a stand-in for captured live messages) through :class:`ReplayTransport` →
:class:`~orderflow.market_data.websocket_manager.WebSocketManager` →
:class:`~orderflow.market_data.fyers_adapter.FyersAdapter` → this auditor —
the exact pipeline a live session uses with the transport swapped.

CLI::

    python -m orderflow.checks.capability_audit --synthetic \
        [--fixtures orderflow/tests/fixtures/synthetic_session.json] \
        [--out orderflow/capability.json]

A live run is the same harness with an owner-supplied transport (credentials
never enter this package, R7).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence

from orderflow.market_data.fyers_adapter import FyersAdapter
from orderflow.market_data.schemas import DepthSnapshot, QuoteUpdate
from orderflow.market_data.websocket_manager import (
    LifecycleEvent,
    MessageTransport,
    TransportClosed,
    WebSocketManager,
)

UTC = timezone.utc

#: Fixed histogram buckets for inter-arrival times, in milliseconds.
HISTOGRAM_EDGES_MS = (100, 250, 500, 1000)
HISTOGRAM_LABELS = ("0-100ms", "100-250ms", "250-500ms", "500-1000ms", ">1000ms")

DEFAULT_DEPTH_STALE_MS = 5_000
DEFAULT_QUOTE_STALE_MS = 10_000
DEFAULT_SYNC_WINDOW_MS = 1_000
DEFAULT_SILENT_GAP_MS = 2_000
DEFAULT_BURST_WINDOW_MS = 1_000


# --------------------------------------------------------------------- statistics


def histogram(values_ms: Iterable[float]) -> dict:
    counts = {label: 0 for label in HISTOGRAM_LABELS}
    for value in values_ms:
        for i, edge in enumerate(HISTOGRAM_EDGES_MS):
            if value < edge:
                counts[HISTOGRAM_LABELS[i]] += 1
                break
        else:
            counts[HISTOGRAM_LABELS[-1]] += 1
    return counts


def median(values: Sequence[float]) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2:
        return float(ordered[mid])
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def percentile_nearest_rank(values: Sequence[float], pct: float) -> Optional[float]:
    """Nearest-rank percentile: sorted[ceil(pct*n) - 1]."""
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(pct * len(ordered)))
    return float(ordered[rank - 1])


def interval_summary(values_ms: Sequence[float]) -> dict:
    if not values_ms:
        return {
            "count": 0,
            "min_ms": None,
            "median_ms": None,
            "p95_ms": None,
            "max_ms": None,
            "histogram": {label: 0 for label in HISTOGRAM_LABELS},
        }
    return {
        "count": len(values_ms),
        "min_ms": _round(min(values_ms)),
        "median_ms": _round(median(values_ms)),
        "p95_ms": _round(percentile_nearest_rank(values_ms, 0.95)),
        "max_ms": _round(max(values_ms)),
        "histogram": histogram(values_ms),
    }


def coefficient_of_variation(values_ms: Sequence[float]) -> Optional[float]:
    if len(values_ms) < 2:
        return None
    mean = sum(values_ms) / len(values_ms)
    if mean == 0:
        return None
    variance = sum((v - mean) ** 2 for v in values_ms) / len(values_ms)
    return _round(math.sqrt(variance) / mean)


def max_in_window(timestamps: Sequence[datetime], window_ms: float) -> Optional[int]:
    """Max count of events in any sliding ``window_ms`` window."""
    if not timestamps:
        return None
    ordered = sorted(timestamps)
    best = 0
    left = 0
    window_s = window_ms / 1000.0
    for right in range(len(ordered)):
        while (ordered[right] - ordered[left]).total_seconds() > window_s:
            left += 1
        best = max(best, right - left + 1)
    return best


def _round(value: Optional[float], places: int = 3) -> Optional[float]:
    if value is None:
        return None
    return round(float(value), places)


def _iso(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat()


def _nearest_distances(a: Sequence[datetime], b: Sequence[datetime]) -> list:
    """For each ts in ``a``, the distance (seconds) to the nearest ts in ``b``."""
    if not a or not b:
        return []
    distances = []
    j = 0
    for ts in a:
        while j + 1 < len(b) and abs(b[j + 1] - ts) <= abs(b[j] - ts):
            j += 1
        distances.append(abs(b[j] - ts).total_seconds())
    return distances


# --------------------------------------------------------------------- auditor


@dataclass
class FieldPresence:
    present: int = 0
    absent: int = 0

    def observe(self, present: bool) -> None:
        if present:
            self.present += 1
        else:
            self.absent += 1

    def status(self) -> Optional[str]:
        total = self.present + self.absent
        if total == 0:
            return "not_observed"
        return "populated" if self.present else "absent"

    def as_dict(self) -> dict:
        return {
            "populated_count": self.present,
            "null_count": self.absent,
            "status": self.status(),
        }


@dataclass
class SymbolStats:
    symbol: str
    bucket: str
    quote_ts: list = field(default_factory=list)
    depth_ts: list = field(default_factory=list)
    quote_intervals_ms: list = field(default_factory=list)
    depth_intervals_ms: list = field(default_factory=list)
    max_bid_levels: int = 0
    max_ask_levels: int = 0
    latency_ms: list = field(default_factory=list)
    last_trade_qty: FieldPresence = field(default_factory=FieldPresence)
    order_count: FieldPresence = field(default_factory=FieldPresence)
    total_buy_qty: FieldPresence = field(default_factory=FieldPresence)
    total_sell_qty: FieldPresence = field(default_factory=FieldPresence)

    @property
    def first_seen(self) -> Optional[datetime]:
        candidates = []
        if self.quote_ts:
            candidates.append(self.quote_ts[0])
        if self.depth_ts:
            candidates.append(self.depth_ts[0])
        return min(candidates) if candidates else None

    @property
    def last_seen(self) -> Optional[datetime]:
        candidates = []
        if self.quote_ts:
            candidates.append(self.quote_ts[-1])
        if self.depth_ts:
            candidates.append(self.depth_ts[-1])
        return max(candidates) if candidates else None


class CapabilityAuditor:
    """Consumes canonical events + lifecycle events; produces the report."""

    def __init__(
        self,
        *,
        liquidity_buckets: Optional[Mapping[str, str]] = None,
        depth_stale_ms: float = DEFAULT_DEPTH_STALE_MS,
        quote_stale_ms: float = DEFAULT_QUOTE_STALE_MS,
        sync_window_ms: float = DEFAULT_SYNC_WINDOW_MS,
        silent_gap_ms: float = DEFAULT_SILENT_GAP_MS,
        burst_window_ms: float = DEFAULT_BURST_WINDOW_MS,
    ) -> None:
        self._buckets = dict(liquidity_buckets or {})
        self._depth_stale_ms = depth_stale_ms
        self._quote_stale_ms = quote_stale_ms
        self._sync_window_ms = sync_window_ms
        self._silent_gap_ms = silent_gap_ms
        self._burst_window_ms = burst_window_ms
        self._symbols: dict[str, SymbolStats] = {}
        self._timeline: list[datetime] = []
        self._lifecycle: list[LifecycleEvent] = []
        self._subscribe_attempts: list[Any] = []

    # ------------------------------------------------------------------ intake

    def record_event(self, event: Any) -> None:
        ts: datetime = event.ts_received
        stats = self._symbol_stats(event.symbol)
        self._timeline.append(ts)
        if isinstance(event, QuoteUpdate):
            if stats.quote_ts and ts > stats.quote_ts[-1]:
                stats.quote_intervals_ms.append((ts - stats.quote_ts[-1]).total_seconds() * 1000.0)
            stats.quote_ts.append(ts)
            stats.last_trade_qty.observe(event.last_trade_qty is not None)
            if event.feed_latency_ms is not None:
                stats.latency_ms.append(event.feed_latency_ms)
        elif isinstance(event, DepthSnapshot):
            if stats.depth_ts and ts > stats.depth_ts[-1]:
                stats.depth_intervals_ms.append((ts - stats.depth_ts[-1]).total_seconds() * 1000.0)
            stats.depth_ts.append(ts)
            stats.max_bid_levels = max(stats.max_bid_levels, len(event.bids))
            stats.max_ask_levels = max(stats.max_ask_levels, len(event.asks))
            stats.total_buy_qty.observe(event.total_buy_qty is not None)
            stats.total_sell_qty.observe(event.total_sell_qty is not None)
            if event.bids or event.asks:
                stats.order_count.observe(any(l.order_count is not None for l in event.bids + event.asks))
            if event.feed_latency_ms is not None:
                stats.latency_ms.append(event.feed_latency_ms)

    def record_lifecycle(self, event: LifecycleEvent) -> None:
        self._lifecycle.append(event)

    def record_subscription_attempts(self, attempts: Iterable[Any]) -> None:
        self._subscribe_attempts = list(attempts)

    def _symbol_stats(self, symbol: str) -> SymbolStats:
        if symbol not in self._symbols:
            self._symbols[symbol] = SymbolStats(symbol=symbol, bucket=self._buckets.get(symbol, "unclassified"))
        return self._symbols[symbol]

    # ------------------------------------------------------------------ derived

    def _disconnect_windows(self) -> list:
        """Paired disconnected→connected lifecycle windows."""
        windows = []
        open_start = None
        for event in self._lifecycle:
            if event.kind == "disconnected":
                open_start = event.at
            elif event.kind == "connected" and open_start is not None:
                windows.append((open_start, event.at))
                open_start = None
        if open_start is not None:
            windows.append((open_start, None))  # unterminated: stream ended while down
        return windows

    def _silent_gaps(self) -> list:
        """Data-silent intervals over the global event timeline."""
        gaps = []
        ordered = sorted(self._timeline)
        windows = self._disconnect_windows()
        for prev, nxt in zip(ordered, ordered[1:]):
            duration_ms = (nxt - prev).total_seconds() * 1000.0
            if duration_ms <= self._silent_gap_ms:
                continue
            cause = "quiet"
            for start, end in windows:
                # strict interior overlap: a silence that begins exactly at
                # reconnection is post-reconnect quiet, not the outage itself
                if end is None or (prev < end and nxt > start):
                    cause = "disconnect"
                    break
            gaps.append(
                {
                    "start_utc": _iso(prev),
                    "end_utc": _iso(nxt),
                    "duration_ms": _round(duration_ms),
                    "cause": cause,
                }
            )
        return gaps

    def _stale_periods(self, stats: SymbolStats, kind: str) -> list:
        times = stats.depth_ts if kind == "depth" else stats.quote_ts
        threshold = self._depth_stale_ms if kind == "depth" else self._quote_stale_ms
        windows = [w for w in self._disconnect_windows() if w[1] is not None]
        periods = []
        for prev, nxt in zip(times, times[1:]):
            duration_ms = (nxt - prev).total_seconds() * 1000.0
            if duration_ms <= threshold:
                continue
            overlaps_disconnect = any(prev <= end and nxt >= start for start, end in windows)
            if overlaps_disconnect:
                continue
            periods.append(
                {
                    "from_utc": _iso(prev),
                    "until_utc": _iso(nxt),
                    "duration_ms": _round(duration_ms),
                    "stale_from_utc": _iso(prev + timedelta(milliseconds=threshold)),
                }
            )
        return periods

    # ------------------------------------------------------------------ report

    def report(
        self,
        *,
        data_source: str,
        generated_at: Optional[datetime] = None,
        adapter: Optional[FyersAdapter] = None,
        extra_notes: Optional[Iterable[str]] = None,
    ) -> dict:
        symbols_report = {sym: self._symbol_report(stats) for sym, stats in sorted(self._symbols.items())}
        bucket_report = self._bucket_report()
        all_depth_intervals = [iv for stats in self._symbols.values() for iv in stats.depth_intervals_ms]
        gaps = self._silent_gaps()
        max_levels = max(
            (max(s.max_bid_levels, s.max_ask_levels) for s in self._symbols.values()),
            default=0,
        )
        tbt_verified = max_levels > FyersAdapter.DEPTH_LEVELS_PER_SIDE
        presence = self._pooled_presence()

        return {
            "schema_version": 1,
            "generated_at_utc": _iso(generated_at or datetime.now(UTC)),
            "data_source": data_source,
            "config": {
                "depth_stale_ms": self._depth_stale_ms,
                "quote_stale_ms": self._quote_stale_ms,
                "sync_window_ms": self._sync_window_ms,
                "silent_gap_ms": self._silent_gap_ms,
                "burst_window_ms": self._burst_window_ms,
                "histogram_edges_ms": list(HISTOGRAM_EDGES_MS),
            },
            "coverage": {
                "symbols_observed": len(self._symbols),
                "quote_updates": sum(len(s.quote_ts) for s in self._symbols.values()),
                "depth_snapshots": sum(len(s.depth_ts) for s in self._symbols.values()),
                "unknown_or_ignored_messages_skipped": dict(adapter.skipped) if adapter else {},
                "liquidity_buckets_assigned": self._buckets or None,
            },
            "depth_inter_arrival_histogram": interval_summary(all_depth_intervals)["histogram"],
            "liquidity_buckets": bucket_report,
            "quote_depth_sync": self._sync_report(),
            "gaps": gaps,
            "lifecycle_events": [
                {"kind": e.kind, "at_utc": _iso(e.at), "detail": dict(e.detail)} for e in self._lifecycle
            ],
            "subscription_limits": self._subscription_report(data_source),
            "optional_field_presence": presence,
            "tbt_50_level": {
                "max_bid_levels_observed": max((s.max_bid_levels for s in self._symbols.values()), default=0),
                "max_ask_levels_observed": max((s.max_ask_levels for s in self._symbols.values()), default=0),
                "status": "verified_by_observation" if tbt_verified else "not_observed",
                "note": (
                    "More than 5 levels observed on the stream."
                    if tbt_verified
                    else "Only ≤5-level depth observed. The standard data socket carries 5 levels by protocol; "
                    "50-level TBT requires the separate TBT socket, which can only be verified in an owner-run "
                    "live session. Unverified: an external review claims FYERS provides it for NSE cash."
                ),
            },
            "stale_periods": {
                sym: {"depth": self._stale_periods(stats, "depth"), "quote": self._stale_periods(stats, "quote")}
                for sym, stats in sorted(self._symbols.items())
            },
            "symbols": symbols_report,
            "measurement_notes": list(extra_notes or []),
        }

    def _symbol_report(self, stats: SymbolStats) -> dict:
        sync = self._symbol_sync(stats)
        return {
            "liquidity_bucket": stats.bucket,
            "first_seen_utc": _iso(stats.first_seen),
            "last_seen_utc": _iso(stats.last_seen),
            "quote_updates": len(stats.quote_ts),
            "depth_snapshots": len(stats.depth_ts),
            "depth_interval_ms": interval_summary(stats.depth_intervals_ms),
            "quote_interval_ms": interval_summary(stats.quote_intervals_ms),
            "burstiness": {
                "depth_interval_cv": coefficient_of_variation(stats.depth_intervals_ms),
                "max_depth_per_1s": max_in_window(stats.depth_ts, self._burst_window_ms),
                "max_quotes_per_1s": max_in_window(stats.quote_ts, self._burst_window_ms),
            },
            "sync": sync,
            "max_bid_levels_observed": stats.max_bid_levels,
            "max_ask_levels_observed": stats.max_ask_levels,
            "feed_latency_ms": {
                "count": len(stats.latency_ms),
                "median_ms": _round(median(stats.latency_ms)),
                "p95_ms": _round(percentile_nearest_rank(stats.latency_ms, 0.95)),
            },
            "optional_fields": {
                "last_trade_qty": stats.last_trade_qty.as_dict(),
                "order_count": stats.order_count.as_dict(),
                "total_buy_qty": stats.total_buy_qty.as_dict(),
                "total_sell_qty": stats.total_sell_qty.as_dict(),
            },
        }

    def _symbol_sync(self, stats: SymbolStats) -> dict:
        quotes = sorted(stats.quote_ts)
        depth = sorted(stats.depth_ts)
        depth_to_quote = _nearest_distances(depth, quotes)
        quote_to_depth = _nearest_distances(quotes, depth)
        window_s = self._sync_window_ms / 1000.0
        return {
            "sync_window_ms": self._sync_window_ms,
            "depth_with_quote_within_window": {
                "share": _round(sum(1 for d in depth_to_quote if d <= window_s) / len(depth_to_quote), 3)
                if depth_to_quote
                else None,
                "median_offset_ms": _round(median([d * 1000.0 for d in depth_to_quote])),
            },
            "quote_with_depth_within_window": {
                "share": _round(sum(1 for d in quote_to_depth if d <= window_s) / len(quote_to_depth), 3)
                if quote_to_depth
                else None,
                "median_offset_ms": _round(median([d * 1000.0 for d in quote_to_depth])),
            },
        }

    def _sync_report(self) -> dict:
        depth_all = []
        quote_all = []
        for stats in self._symbols.values():
            depth_all.extend(_nearest_distances(sorted(stats.depth_ts), sorted(stats.quote_ts)))
            quote_all.extend(_nearest_distances(sorted(stats.quote_ts), sorted(stats.depth_ts)))
        window_s = self._sync_window_ms / 1000.0
        return {
            "sync_window_ms": self._sync_window_ms,
            "depth_with_quote_within_window_share": _round(
                sum(1 for d in depth_all if d <= window_s) / len(depth_all), 3
            )
            if depth_all
            else None,
            "quote_with_depth_within_window_share": _round(
                sum(1 for d in quote_all if d <= window_s) / len(quote_all), 3
            )
            if quote_all
            else None,
            "median_depth_to_quote_offset_ms": _round(median([d * 1000.0 for d in depth_all])),
            "median_quote_to_depth_offset_ms": _round(median([d * 1000.0 for d in quote_all])),
        }

    def _bucket_report(self) -> dict:
        report = {}
        by_bucket: dict[str, list[SymbolStats]] = {}
        for stats in self._symbols.values():
            by_bucket.setdefault(stats.bucket, []).append(stats)
        for bucket, stats_list in sorted(by_bucket.items()):
            depth_iv = [iv for s in stats_list for iv in s.depth_intervals_ms]
            quote_iv = [iv for s in stats_list for iv in s.quote_intervals_ms]
            report[bucket] = {
                "symbols": sorted(s.symbol for s in stats_list),
                "depth_interval_ms": interval_summary(depth_iv),
                "quote_interval_ms": interval_summary(quote_iv),
            }
        return report

    def _pooled_presence(self) -> dict:
        pooled = {
            "last_trade_qty": FieldPresence(),
            "order_count": FieldPresence(),
            "total_buy_qty": FieldPresence(),
            "total_sell_qty": FieldPresence(),
        }
        for stats in self._symbols.values():
            for key in pooled:
                pooled[key].present += getattr(stats, key).present
                pooled[key].absent += getattr(stats, key).absent
        return {key: fp.as_dict() for key, fp in pooled.items()}

    def _subscription_report(self, data_source: str) -> dict:
        attempts = self._subscribe_attempts
        accepted = [a for a in attempts if a.accepted is True]
        rejected = [a for a in attempts if a.accepted is False]
        unresolved = [a for a in attempts if a.accepted is None]
        documented = FyersAdapter.DOCUMENTED_LIMITS
        return {
            "requests_sent": len(attempts),
            "requests_acked_ok": len(accepted),
            "requests_acked_fail": len(rejected),
            "requests_unresolved": len(unresolved),
            "rejections": [
                {
                    "data_kind": a.canonical_kind,
                    "symbols_requested": len(a.symbols),
                    "ack_code": a.ack_code,
                    "ack_message": a.ack_message,
                    "at_utc": _iso(a.ack_at),
                }
                for a in rejected
            ],
            "max_symbols_in_accepted_request": max((len(a.symbols) for a in accepted), default=0),
            "documented_batch_limit": documented,
            "limit_enforced_observed": bool(rejected),
            "evidence": (
                "Rejection observed on the stream (see rejections)."
                if rejected
                else "No rejection observed; only that the limit is at least the accepted count. "
                "The enforced ceiling was NOT established by this run."
            ),
            "evidence_scope": data_source,
        }


# --------------------------------------------------------------------- replay harness


class ReplayState:
    """Virtual clock + replay transport state over a fixture record list.

    Fixture record shapes (the ``_t_ms`` key is replay scheduling, not wire
    data; everything under ``msg``/``control`` IS wire data):

        {"_t_ms": 305,  "msg": {...raw decoded feed message...}}
        {"_t_ms": 10,   "control": {...raw control message...}}
        {"_t_ms": 20000, "disconnect": true, "cause": "fixture_forced_disconnect"}
        {"_t_ms": 28000, "connect": true}
    """

    def __init__(self, records: Sequence[Mapping[str, Any]], session_start: datetime) -> None:
        self.records = [dict(r) for r in records]
        self.session_start = session_start
        self.cursor = 0
        self._last_t_ms = 0.0
        self._slept_ms = 0.0
        self.sent_payloads: list[Mapping[str, Any]] = []
        self.connected = False

    # virtual clock -------------------------------------------------------
    def now(self) -> datetime:
        return self.session_start + timedelta(milliseconds=self._last_t_ms + self._slept_ms)

    def sleep(self, seconds: float) -> None:
        self._slept_ms += seconds * 1000.0

    # transport -----------------------------------------------------------
    def transport(self) -> "ReplayTransport":
        return ReplayTransport(self)

    def receive(self, timeout_s: float) -> Mapping[str, Any]:
        while self.cursor < len(self.records):
            record = self.records[self.cursor]
            self.cursor += 1
            # lifecycle records advance the virtual clock too, so disconnect
            # and resumption timestamps line up with the scripted schedule
            if "_t_ms" in record:
                self._last_t_ms = float(record["_t_ms"])
            if record.get("disconnect"):
                self.connected = False
                raise TransportClosed(record.get("cause", "forced_disconnect"))
            if record.get("connect"):
                self.connected = True
                continue
            if "control" in record:
                return dict(record["control"])
            return dict(record["msg"])
        raise TransportClosed("exhausted")


class ReplayTransport:
    """MessageTransport over shared ReplayState (survives reconnects)."""

    def __init__(self, state: ReplayState) -> None:
        self._state = state

    def connect(self) -> None:
        self._state.connected = True

    def send(self, payload: Mapping[str, Any]) -> None:
        self._state.sent_payloads.append(dict(payload))

    def receive(self, timeout_s: float) -> Mapping[str, Any]:
        return self._state.receive(timeout_s)

    def close(self) -> None:
        self._state.connected = False


def load_fixture(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def run_synthetic_audit(
    fixture_path: Path,
    out_path: Path,
    *,
    data_source: str = "synthetic",
    quiet: bool = False,
) -> dict:
    """End-to-end offline run: fixture → transport → manager → adapter →
    auditor → capability.json. Returns the report dict."""
    fixture = load_fixture(fixture_path)
    records = fixture["records"]
    session_start = datetime.fromisoformat(fixture["session_start_utc"])
    buckets = fixture.get("liquidity_buckets", {})

    state = ReplayState(records, session_start)
    adapter = FyersAdapter()
    auditor = CapabilityAuditor(
        liquidity_buckets=buckets,
        depth_stale_ms=fixture.get("depth_stale_ms", DEFAULT_DEPTH_STALE_MS),
        quote_stale_ms=fixture.get("quote_stale_ms", DEFAULT_QUOTE_STALE_MS),
    )
    manager = WebSocketManager(
        state.transport,
        adapter,
        on_event=auditor.record_event,
        on_lifecycle=auditor.record_lifecycle,
        clock=state.now,
        sleeper=state.sleep,
        reconnect_base_delay_s=0.5,
        reconnect_max_delay_s=4.0,
        max_reconnects=5,
    )

    manager.connect()
    manager.subscribe(fixture["subscribe_symbols"])
    extra_probe = fixture.get("extra_probe_symbols")
    if extra_probe:
        manager.subscribe(extra_probe)
    manager.run()

    auditor.record_subscription_attempts(manager.subscribe_attempts)
    report = auditor.report(
        data_source=data_source,
        adapter=adapter,
        extra_notes=fixture.get("measurement_notes", []),
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
        fh.write("\n")
    if not quiet:
        print(f"capability report written to {out_path}")
        print(
            f"  symbols={report['coverage']['symbols_observed']} "
            f"quotes={report['coverage']['quote_updates']} "
            f"depth={report['coverage']['depth_snapshots']} "
            f"gaps={len(report['gaps'])}"
        )
    return report


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Feed capability audit (offline synthetic mode)")
    parser.add_argument("--synthetic", action="store_true", help="run against the synthetic fixture stream")
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "synthetic_session.json",
        help="fixture file to replay (default: the committed synthetic session)",
    )
    parser.add_argument(
        "--out", type=Path, default=Path(__file__).resolve().parents[1] / "capability.json",
        help="where to write the capability report",
    )
    parser.add_argument("--source", default="synthetic", help="data_source label recorded in the report")
    args = parser.parse_args(argv)
    if not args.synthetic:
        parser.error("only --synthetic is supported; live runs are wired by the owner (credentials never touch this package)")
    run_synthetic_audit(args.fixtures, args.out, data_source=args.source)
    return 0


if __name__ == "__main__":
    sys.exit(main())
