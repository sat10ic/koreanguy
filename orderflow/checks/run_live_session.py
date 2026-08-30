"""Live FYERS measurement session launcher (unified U-P0.4 live half).

OWNER-STARTED: credentials live in your environment; this module reads only
their presence, never their values, and never prints them. Prepare with
``scripts/fyers_login.py`` (it prints the exact export line to use), then:

    .venv-orderflow/Scripts/python.exe -m orderflow.checks.run_live_session \
        --duration-s 600                    # smoke run; omit for full session

What it does: subscribes the symbol set across the four liquidity buckets,
tees every RAW message (with ts_received) to a JSONL raw log under
data/orderflow/raw/, feeds the capability auditor through the WebSocketManager,
writes capability.json (data_source=live), and prints the R1
window-eligibility gate table computed from the measured per-bucket medians.

Run during NSE market hours (09:15-15:30 IST). Stop with Ctrl+C — the
auditor finalizes on interruption and still writes its report.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

from orderflow.checks.capability_audit import CapabilityAuditor
from orderflow.checks.feed_health import FeedHealthMonitor
from orderflow.market_data.fyers_adapter import FyersAdapter
from orderflow.market_data.websocket_manager import WebSocketManager
from orderflow.storage.parquet_writer import ParquetWriter
from orderflow.storage.recorder import ContinuousRecorder

IST = timezone(timedelta(hours=5, minutes=30))
_REPO_ROOT = Path(__file__).resolve().parents[2]

# R1 gate (build manual): materially faster than ~1 Hz enables all windows;
# ~1 Hz or slower demotes short windows (research_only / low_confidence).
GATE_FAST_THRESHOLD_MS = 1000.0
GATE_WINDOWS = ("5s", "15s", "1m", "5m")
_SECRET_KEY_PARTS = ("token", "secret", "password", "authorization", "api_key", "client_id")

# Owner-editable: 8 NSE cash symbols across the four liquidity buckets.
# These are PROVISIONAL tickers — confirm/replace with the owner before the
# session; the bucket labels are what the audit reports against.
DEFAULT_SYMBOLS = {
    "NSE:TRENT-EQ": "liquid_midcap",
    "NSE:HDFCAMC-EQ": "liquid_midcap",
    "NSE:DIXON-EQ": "moderate_midcap",
    "NSE:ABSLAMC-EQ": "moderate_midcap",
    "NSE:CAMS-EQ": "liquid_smallcap",
    "NSE:ROUTE-EQ": "liquid_smallcap",
    "NSE:SHIVALIK-EQ": "thin_smallcap",
    "NSE:DAMCAPITAL-EQ": "thin_smallcap",
}


def window_gate_table(bucket_medians_ms: dict) -> dict:
    """Eligibility of 5s/15s/1m/5m windows per liquidity bucket, from
    MEASURED medians — never from documentation."""
    table = {}
    for bucket, median_ms in bucket_medians_ms.items():
        if median_ms is None:
            table[bucket] = {w: "not_observed" for w in GATE_WINDOWS}
        elif median_ms < GATE_FAST_THRESHOLD_MS:
            table[bucket] = {w: "valid" for w in GATE_WINDOWS}
        else:
            table[bucket] = {
                "5s": "research_only",
                "15s": "low_confidence",
                "1m": "valid",
                "5m": "valid",
            }
    return table


class RawLoggingTransport:
    """Tees every raw message (with local receive time) to a JSONL file, then
    delegates to the real transport. Keeps the N1 'raw persisted' promise
    without touching orderflow production code."""

    def __init__(self, inner, raw_log) -> None:
        self._inner = inner
        self._raw_log = raw_log
        self.count = 0

    def connect(self) -> None:
        self._inner.connect()

    def send(self, payload: Mapping[str, Any]) -> None:
        self._inner.send(payload)

    def receive(self, timeout_s: float) -> Mapping[str, Any]:
        message = self._inner.receive(timeout_s)
        self.count += 1
        self._raw_log.write(
            json.dumps({
                "ts_received": datetime.now(timezone.utc).isoformat(),
                "raw": _redact_sensitive(dict(message)),
            }) + "\n"
        )
        return message

    def close(self) -> None:
        self._inner.close()

    def drain_errors(self) -> list:
        return self._inner.drain_errors() if hasattr(self._inner, "drain_errors") else []


def _redact_sensitive(value):
    if isinstance(value, Mapping):
        return {
            str(key): (
                "[REDACTED]"
                if any(part in str(key).casefold() for part in _SECRET_KEY_PARTS)
                else _redact_sensitive(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_redact_sensitive(item) for item in value]
    return value


def recording_callbacks(auditor, recorder):
    """Return record-before-analysis callbacks for the live manager."""
    def on_event(event):
        recorder.record_event(event)
        auditor.record_event(event)

    def on_lifecycle(event):
        recorder.record_lifecycle(event)
        auditor.record_lifecycle(event)

    return on_event, on_lifecycle


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Live FYERS capability measurement session")
    parser.add_argument("--symbols", default=",".join(DEFAULT_SYMBOLS),
                        help="comma-separated NSE symbols (default: the provisional 8-symbol mixed set)")
    parser.add_argument("--duration-s", type=float, default=None,
                        help="stop after this many seconds (smoke runs); omit = run until 15:30 IST")
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[1] / "capability.json")
    parser.add_argument("--raw-log-dir", type=Path, default=_REPO_ROOT / "data" / "orderflow" / "raw")
    parser.add_argument("--parquet-root", type=Path, default=_REPO_ROOT / "data" / "orderflow" / "parquet")
    parser.add_argument("--recorder-batch-size", type=int, default=1000)
    parser.add_argument("--flush-interval-s", type=float, default=60.0)
    parser.add_argument("--poll-timeout-s", type=float, default=1.0)
    args = parser.parse_args(argv)
    if args.duration_s is not None and args.duration_s <= 0:
        parser.error("--duration-s must be positive")
    if args.flush_interval_s <= 0:
        parser.error("--flush-interval-s must be positive")

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    if len(symbols) < 8:
        print(f"WARNING: {len(symbols)} symbols requested; the audit brief wants >=8 across 4 buckets.")
    liquidity_buckets = {s: DEFAULT_SYMBOLS.get(s, "unclassified") for s in symbols}

    sys.path.insert(0, str(_REPO_ROOT / "scripts"))
    from fyers_live_transport import FyersLiveTransportFactory  # owner-side shim, outside orderflow/

    adapter = FyersAdapter()
    auditor = CapabilityAuditor(liquidity_buckets=liquidity_buckets)
    recorder = ContinuousRecorder(
        ParquetWriter(args.parquet_root),
        FeedHealthMonitor(clock=lambda: datetime.now(timezone.utc)),
        batch_size=args.recorder_batch_size,
    )
    on_event, on_lifecycle = recording_callbacks(auditor, recorder)

    raw_log_path = args.raw_log_dir / f"live_{datetime.now(IST).strftime('%Y%m%d_%H%M%S')}.jsonl"
    raw_log_path.parent.mkdir(parents=True, exist_ok=True)
    raw_log = open(raw_log_path, "a", encoding="utf-8")

    factory = FyersLiveTransportFactory()
    transports: list[RawLoggingTransport] = []

    def factory_with_logging():
        transport = RawLoggingTransport(factory(), raw_log)
        transports.append(transport)
        return transport

    manager = WebSocketManager(
        factory_with_logging,
        adapter,
        on_event=on_event,
        on_control=lambda m: print(f"[control] {m}"),
        on_lifecycle=on_lifecycle,
        clock=lambda: datetime.now(timezone.utc),
        sleeper=time.sleep,
        reconnect_base_delay_s=1.0,
        reconnect_max_delay_s=30.0,
    )

    session_end = (
        datetime.now(timezone.utc) + timedelta(seconds=args.duration_s)
        if args.duration_s is not None
        else datetime.now(IST).replace(hour=15, minute=30, second=0, microsecond=0)
    )

    print(f"Session until {session_end.isoformat()}; symbols: {len(symbols)}; raw log: {raw_log_path}")
    last_report = datetime.now(timezone.utc)
    try:
        manager.connect()
        manager.subscribe(symbols)
        while datetime.now(timezone.utc) < session_end:
            manager.poll_once(args.poll_timeout_s)
            transport: Any = manager.transport
            for err in transport.drain_errors():
                print(f"[error] {err}")
            if (datetime.now(timezone.utc) - last_report).total_seconds() >= args.flush_interval_s:
                recorder.tick()
                recorder.flush()
                raw_log.flush()
                print(f"[progress] {auditor_events(auditor)} at {datetime.now(IST).strftime('%H:%M:%S')} IST")
                last_report = datetime.now(timezone.utc)
    except KeyboardInterrupt:
        print("\nInterrupted — finalizing report from what was measured.")
    finally:
        try:
            recorder.finalize(datetime.now(timezone.utc))
        finally:
            try:
                manager.close()
            finally:
                raw_log.flush()
                raw_log.close()

    auditor.record_subscription_attempts(manager.subscribe_attempts)
    report = auditor.report(data_source="live", adapter=adapter)

    bucket_medians = {
        bucket: stats["depth_interval_ms"]["median_ms"]
        for bucket, stats in report.get("liquidity_buckets", {}).items()
    }
    report["window_eligibility"] = window_gate_table(bucket_medians)
    report["raw_log"] = str(raw_log_path)

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
        fh.write("\n")

    print(f"\ncapability report written to {args.out} (data_source=live)")
    print(f"events observed: {report['coverage']['quote_updates']} quotes, "
          f"{report['coverage']['depth_snapshots']} depth snapshots; "
          f"raw lines: {sum(transport.count for transport in transports)}")
    print("\nR1 window-eligibility gate (computed from measured medians):")
    print(json.dumps(report["window_eligibility"], indent=2))
    print("\nPresent this gate to the owner before enabling any feature window.")
    return 0


def auditor_events(auditor: CapabilityAuditor) -> str:
    quotes = sum(len(s.quote_ts) for s in auditor._symbols.values())
    depth = sum(len(s.depth_ts) for s in auditor._symbols.values())
    return f"{quotes} quotes / {depth} depth"


if __name__ == "__main__":
    sys.exit(main())
