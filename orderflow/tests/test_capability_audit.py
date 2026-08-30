"""Capability-audit tests: histogram, per-bucket medians, sync, staleness,
gaps (never interpolated), field presence, TBT levels, subscription limits —
plus the end-to-end synthetic run writing capability.json.

Metric checks recompute expectations by an independent route (statistics
module / direct counting) rather than re-using the auditor's helpers.
"""
import json
import math
import statistics
from datetime import datetime, timedelta, timezone

import pytest

from orderflow.checks import capability_audit as ca
from orderflow.checks.capability_audit import (
    CapabilityAuditor,
    ReplayState,
    histogram,
    max_in_window,
    median,
    percentile_nearest_rank,
)
from orderflow.market_data.fyers_adapter import FyersAdapter
from orderflow.market_data.schemas import DepthLevel, DepthSnapshot, QuoteUpdate
from orderflow.market_data.websocket_manager import LifecycleEvent, TransportClosed, WebSocketManager
from orderflow.tests.fixtures.generate_synthetic_session import SESSION_START as FIXTURE_SESSION_START

UTC = timezone.utc
T0 = FIXTURE_SESSION_START

FIXTURE_PATH = ca.Path(__file__).resolve().parent / "fixtures" / "synthetic_session.json"


# --------------------------------------------------------------------- statistics helpers


def test_histogram_bucket_edges():
    counts = histogram([0, 99.9, 100, 249.9, 250, 499.9, 500, 999.9, 1000, 5000])
    assert counts == {
        "0-100ms": 2,        # 0, 99.9
        "100-250ms": 2,      # 100, 249.9
        "250-500ms": 2,      # 250, 499.9
        "500-1000ms": 2,     # 500, 999.9
        ">1000ms": 2,        # 1000, 5000
    }
    assert sum(histogram([]).values()) == 0


def test_median_matches_statistics_module():
    values = [3.0, 1.0, 4.0, 1.5, 5.0, 9.0, 2.0, 6.0]
    assert median(values) == pytest.approx(statistics.median(values))
    assert median([]) is None


def test_p95_nearest_rank_independent_route():
    values = list(range(1, 101))  # p95 rank = ceil(0.95*100) = 95
    assert percentile_nearest_rank(values, 0.95) == 95
    small = [10.0, 20.0]  # ceil(0.95*2)=2 → max
    assert percentile_nearest_rank(small, 0.95) == 20.0
    assert percentile_nearest_rank([], 0.95) is None


def test_max_in_window_independent_route():
    base = datetime(2026, 8, 28, 4, 15, 0, tzinfo=UTC)
    ts = [base + timedelta(milliseconds=m) for m in (0, 100, 200, 950, 1200, 1500)]
    # windows of 1000ms: [0..950]=4, [100..1200]=4, [200..1500]=4
    assert max_in_window(ts, 1000) == 4
    assert max_in_window([], 1000) is None


# --------------------------------------------------------------------- auditor units


def make_quote(symbol, ts, **kw):
    return QuoteUpdate(ts_exchange=None, ts_received=ts, symbol=symbol, ltp=kw.pop("ltp", 1.0), **kw)


def make_depth(symbol, ts, levels=5, totals=None, order_counts=True):
    side = [
        DepthLevel(price=100 - 0.05 * (i + 1), quantity=10 * (i + 1), order_count=(i + 1 if order_counts else None))
        for i in range(levels)
    ]
    other = [
        DepthLevel(price=100 + 0.05 * (i + 1), quantity=10 * (i + 1), order_count=(i + 1 if order_counts else None))
        for i in range(levels)
    ]
    return DepthSnapshot(
        ts_exchange=None,
        ts_received=ts,
        symbol=symbol,
        bids=tuple(side),
        asks=tuple(other),
        total_buy_qty=totals[0] if totals else None,
        total_sell_qty=totals[1] if totals else None,
    )


def test_per_bucket_median_and_p95():
    auditor = CapabilityAuditor(liquidity_buckets={"NSE:LIQ-EQ": "liquid", "NSE:THIN-EQ": "thin"})
    # liquid: 10 depth updates 200 ms apart → median 200
    t = T0
    for _ in range(10):
        t += timedelta(milliseconds=200)
        auditor.record_event(make_depth("NSE:LIQ-EQ", t))
    # thin: 5 updates 3000 ms apart → median 3000
    for _ in range(5):
        t += timedelta(milliseconds=3000)
        auditor.record_event(make_depth("NSE:THIN-EQ", t))
    report = auditor.report(data_source="test")
    liquid = report["liquidity_buckets"]["liquid"]["depth_interval_ms"]
    thin = report["liquidity_buckets"]["thin"]["depth_interval_ms"]
    assert liquid["median_ms"] == pytest.approx(200.0)
    assert thin["median_ms"] == pytest.approx(3000.0)
    # p95 by independent route: 9 intervals of 200 → sorted, rank ceil(.95*9)=9 → 200
    assert liquid["p95_ms"] == pytest.approx(200.0)
    assert thin["p95_ms"] == pytest.approx(3000.0)
    # global histogram counts every interval exactly once
    assert sum(report["depth_inter_arrival_histogram"].values()) == 9 + 4


def test_unclassified_symbols_land_in_unclassified_bucket():
    auditor = CapabilityAuditor()
    auditor.record_event(make_depth("NSE:WHO-EQ", T0 + timedelta(seconds=1)))
    report = auditor.report(data_source="test")
    assert "unclassified" in report["liquidity_buckets"]


def test_sync_shares_recomputed_by_direct_counting():
    auditor = CapabilityAuditor(sync_window_ms=1000)
    sym = "NSE:A-EQ"
    # quotes at 0..9 s; depth at 0.1..9.1 s → every depth has a quote within 1 s
    for i in range(10):
        auditor.record_event(make_quote(sym, T0 + timedelta(seconds=i)))
        auditor.record_event(make_depth(sym, T0 + timedelta(seconds=i, milliseconds=100)))
    report = auditor.report(data_source="test")
    sync = report["symbols"][sym]["sync"]
    assert sync["depth_with_quote_within_window"]["share"] == 1.0
    assert sync["depth_with_quote_within_window"]["median_offset_ms"] == pytest.approx(100.0)


def test_stale_periods_detected_and_disconnect_overlaps_excluded():
    auditor = CapabilityAuditor(depth_stale_ms=5000)
    sym = "NSE:A-EQ"
    t = T0
    # 1) a 7 s depth gap OUTSIDE any disconnect → stale recorded
    for ts in (T0, T0 + timedelta(seconds=7), T0 + timedelta(seconds=8)):
        auditor.record_event(make_depth(sym, ts))
    # 2) an 8 s gap covered by a disconnect window → NOT stale
    auditor.record_lifecycle(LifecycleEvent("disconnected", T0 + timedelta(seconds=10)))
    auditor.record_lifecycle(LifecycleEvent("connected", T0 + timedelta(seconds=18)))
    auditor.record_event(make_depth(sym, T0 + timedelta(seconds=10)))
    auditor.record_event(make_depth(sym, T0 + timedelta(seconds=18)))
    report = auditor.report(data_source="test")
    stale = report["stale_periods"][sym]["depth"]
    assert len(stale) == 1
    assert stale[0]["duration_ms"] == pytest.approx(7000.0)
    assert stale[0]["stale_from_utc"] == (T0 + timedelta(seconds=5)).isoformat()


def test_silent_gap_correlated_with_disconnect_and_not_interpolated():
    auditor = CapabilityAuditor(silent_gap_ms=2000)
    sym = "NSE:A-EQ"
    auditor.record_event(make_depth(sym, T0))
    auditor.record_event(make_depth(sym, T0 + timedelta(seconds=2)))
    auditor.record_lifecycle(LifecycleEvent("disconnected", T0 + timedelta(seconds=2)))
    auditor.record_lifecycle(LifecycleEvent("connected", T0 + timedelta(seconds=10)))
    auditor.record_event(make_depth(sym, T0 + timedelta(seconds=10)))
    report = auditor.report(data_source="test")
    assert len(report["gaps"]) == 1
    gap = report["gaps"][0]
    assert gap["cause"] == "disconnect"
    assert gap["duration_ms"] == pytest.approx(8000.0)
    # a quiet (non-disconnect) silence is still reported, labelled quiet
    auditor.record_event(make_depth(sym, T0 + timedelta(seconds=25)))
    report2 = auditor.report(data_source="test")
    quiet = [g for g in report2["gaps"] if g["cause"] == "quiet"]
    assert quiet and quiet[0]["duration_ms"] == pytest.approx(15000.0)


def test_optional_field_presence_statuses():
    auditor = CapabilityAuditor(liquidity_buckets={})
    # populated: order_count present
    auditor.record_event(make_depth("NSE:P-EQ", T0, order_counts=True, totals=(10, 20)))
    # absent: messages seen, field never present
    auditor.record_event(make_depth("NSE:A-EQ", T0, order_counts=False, totals=None))
    # not_observed: no depth messages at all for this symbol
    auditor.record_event(make_quote("NSE:N-EQ", T0, last_trade_qty=None))
    report = auditor.report(data_source="test")
    fields = report["symbols"]
    assert fields["NSE:P-EQ"]["optional_fields"]["order_count"]["status"] == "populated"
    assert fields["NSE:A-EQ"]["optional_fields"]["order_count"]["status"] == "absent"
    assert fields["NSE:A-EQ"]["optional_fields"]["total_buy_qty"]["status"] == "absent"
    assert fields["NSE:N-EQ"]["optional_fields"]["order_count"]["status"] == "not_observed"
    # pooled presence mirrors per-symbol statuses
    pooled = report["optional_field_presence"]
    assert pooled["order_count"]["populated_count"] == 1
    assert pooled["order_count"]["null_count"] == 1


def test_tbt_status_flips_only_above_five_levels():
    auditor = CapabilityAuditor()
    auditor.record_event(make_depth("NSE:A-EQ", T0, levels=5))
    assert auditor.report(data_source="test")["tbt_50_level"]["status"] == "not_observed"
    auditor.record_event(make_depth("NSE:A-EQ", T0 + timedelta(seconds=1), levels=6))
    tbt = auditor.report(data_source="test")["tbt_50_level"]
    assert tbt["status"] == "verified_by_observation"
    assert tbt["max_bid_levels_observed"] == 6


def test_subscription_report_from_attempts():
    auditor = CapabilityAuditor()
    attempts = _fake_attempts(accepted=2, rejected=1)
    auditor.record_subscription_attempts(attempts)
    report = auditor.report(data_source="synthetic")
    subs = report["subscription_limits"]
    assert subs["requests_sent"] == 3
    assert subs["requests_acked_ok"] == 2
    assert subs["requests_acked_fail"] == 1
    assert subs["limit_enforced_observed"] is True
    assert subs["rejections"][0]["ack_code"] == 11011
    assert subs["max_symbols_in_accepted_request"] == 4


def _fake_attempts(accepted, rejected):
    from orderflow.market_data.websocket_manager import SubscribeAttempt

    out = []
    for i in range(accepted):
        a = SubscribeAttempt(symbols=("NSE:A-EQ", "NSE:B-EQ", "NSE:C-EQ", "NSE:D-EQ"), canonical_kind="quote", sent_at=T0)
        a.accepted = True
        a.ack_code = 200
        a.ack_at = T0
        out.append(a)
    for i in range(rejected):
        a = SubscribeAttempt(symbols=("NSE:P1-EQ", "NSE:P2-EQ"), canonical_kind="depth", sent_at=T0)
        a.accepted = False
        a.ack_code = 11011
        a.ack_message = "subscription failed"
        a.ack_at = T0
        out.append(a)
    return out


# --------------------------------------------------------------------- end-to-end replay


def drive_fixture(tmp_path, out_name="capability.json"):
    """Run the full offline pipeline exactly as the CLI does, returning the
    report dict, the replay state and the auditor (for white-box assertions)."""
    fixture = ca.load_fixture(FIXTURE_PATH)
    state = ReplayState(fixture["records"], datetime.fromisoformat(fixture["session_start_utc"]))
    adapter = FyersAdapter()
    auditor = CapabilityAuditor(liquidity_buckets=fixture["liquidity_buckets"])
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
    manager.subscribe(fixture["extra_probe_symbols"])
    manager.run()
    auditor.record_subscription_attempts(manager.subscribe_attempts)
    report = auditor.report(data_source="synthetic", adapter=adapter, extra_notes=fixture["measurement_notes"])
    out = tmp_path / out_name
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report, state, auditor, manager


def test_end_to_end_synthetic_run_writes_valid_capability_json(tmp_path):
    report, *_ = drive_fixture(tmp_path)
    loaded = json.loads((tmp_path / "capability.json").read_text(encoding="utf-8"))
    assert loaded["data_source"] == "synthetic"

    coverage = loaded["coverage"]
    assert coverage["symbols_observed"] == 4
    assert coverage["quote_updates"] > 0 and coverage["depth_snapshots"] > 0

    # histogram is real: every depth interval falls in exactly one bucket,
    # and the total matches an independent recount from the fixture timeline
    hist = loaded["depth_inter_arrival_histogram"]
    assert sum(hist.values()) == coverage["depth_snapshots"] - coverage["symbols_observed"]
    assert hist["0-100ms"] == 0  # scripted cadences are all ≥250 ms
    assert hist["250-500ms"] > 0 and hist[">1000ms"] > 0

    # per-bucket medians for all four scripted buckets
    buckets = loaded["liquidity_buckets"]
    for name in ("liquid_midcap", "moderate_midcap", "liquid_smallcap", "thin_smallcap"):
        assert name in buckets
        assert buckets[name]["depth_interval_ms"]["median_ms"] is not None
    assert buckets["thin_smallcap"]["depth_interval_ms"]["median_ms"] > buckets["liquid_midcap"]["depth_interval_ms"]["median_ms"]


def test_end_to_end_forced_disconnect_visible_as_gap_never_interpolated(tmp_path):
    report, state, auditor, manager = drive_fixture(tmp_path)
    disconnect_gaps = [g for g in report["gaps"] if g["cause"] == "disconnect"]
    assert disconnect_gaps, "the scripted forced disconnect must appear as a gap"
    gap = disconnect_gaps[0]
    assert gap["duration_ms"] >= 7500.0  # ~8 s scripted outage

    # no events were fabricated inside the gap: recount events on the auditor's
    # own symbol timelines and check the gap window is empty
    start = datetime.fromisoformat(gap["start_utc"])
    end = datetime.fromisoformat(gap["end_utc"])
    inside = 0
    for stats in auditor._symbols.values():
        for ts in stats.depth_ts + stats.quote_ts:
            if start < ts < end:
                inside += 1
    assert inside == 0

    kinds = [e["kind"] for e in report["lifecycle_events"]]
    assert "disconnected" in kinds and "resubscribed" in kinds
    assert manager.reconnects == 1


def test_end_to_end_rejection_probe_and_tbt_and_stale(tmp_path):
    report, *_ = drive_fixture(tmp_path)
    # the fixture's simulated subscribe limit is observed and labelled synthetic
    subs = report["subscription_limits"]
    assert subs["limit_enforced_observed"] is True
    assert subs["requests_acked_fail"] == 2
    assert subs["evidence_scope"] == "synthetic"
    # only ≤5-level depth was fed → TBT stays honestly unverified
    assert report["tbt_50_level"]["status"] == "not_observed"
    # the engineered thin-smallcap stale period (5.5 s → 15.9 s) is recorded;
    # the outage-shaped interval around the disconnect is NOT counted as stale
    thin = report["stale_periods"]["NSE:THINSML-EQ"]["depth"]
    assert len(thin) == 1 and thin[0]["duration_ms"] == pytest.approx(10400.0)
    # optional-field policy from the fixture is visible per symbol
    symbols = report["symbols"]
    assert symbols["NSE:ABCAP-EQ"]["optional_fields"]["order_count"]["status"] == "populated"
    assert symbols["NSE:THINSML-EQ"]["optional_fields"]["order_count"]["status"] == "absent"
    # THINSML depth snapshots exist but never carry totals → "absent";
    # a symbol with NO depth at all would be "not_observed" (unit-tested above)
    assert symbols["NSE:THINSML-EQ"]["optional_fields"]["total_buy_qty"]["status"] == "absent"


def test_cli_synthetic_run(tmp_path):
    out = tmp_path / "cap_cli.json"
    rc = ca.main(["--synthetic", "--fixtures", str(FIXTURE_PATH), "--out", str(out)])
    assert rc == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["coverage"]["depth_snapshots"] > 0


def test_replay_state_rejects_after_exhaustion():
    fixture = ca.load_fixture(FIXTURE_PATH)
    state = ReplayState([], T0)
    with pytest.raises(TransportClosed):
        state.receive(0.1)


# ------------------------------------------------- R1 gate table (N1 launcher)


def test_window_gate_table_from_measured_medians():
    from orderflow.checks.run_live_session import window_gate_table

    table = window_gate_table({
        "liquid_midcap": 300.0,     # materially faster than 1 Hz
        "thin_smallcap": 2600.0,    # slower than 1 Hz
        "empty_bucket": None,       # nothing observed
    })
    assert table["liquid_midcap"] == {w: "valid" for w in ("5s", "15s", "1m", "5m")}
    assert table["thin_smallcap"] == {
        "5s": "research_only", "15s": "low_confidence", "1m": "valid", "5m": "valid",
    }
    assert table["empty_bucket"] == {w: "not_observed" for w in ("5s", "15s", "1m", "5m")}


def test_boundary_at_threshold_is_slow():
    from orderflow.checks.run_live_session import window_gate_table, GATE_FAST_THRESHOLD_MS

    table = window_gate_table({"b": GATE_FAST_THRESHOLD_MS})
    assert table["b"]["5s"] == "research_only"  # exactly 1 Hz counts as slow


def test_live_session_callbacks_record_before_capability_analysis():
    from orderflow.checks.run_live_session import recording_callbacks

    calls = []

    class Recorder:
        def record_event(self, event): calls.append(("record_event", event))
        def record_lifecycle(self, event): calls.append(("record_lifecycle", event))

    class Auditor:
        def record_event(self, event): calls.append(("audit_event", event))
        def record_lifecycle(self, event): calls.append(("audit_lifecycle", event))

    on_event, on_lifecycle = recording_callbacks(Auditor(), Recorder())
    on_event("tick")
    on_lifecycle("connected")
    assert calls == [
        ("record_event", "tick"),
        ("audit_event", "tick"),
        ("record_lifecycle", "connected"),
        ("audit_lifecycle", "connected"),
    ]


def test_raw_logging_transport_redacts_secret_shaped_fields():
    import io
    from orderflow.checks.run_live_session import RawLoggingTransport

    class Inner:
        def receive(self, _timeout):
            return {
                "type": "sf",
                "ltp": 100.0,
                "access_token": "do-not-write",
                "nested": {"api_key": "also-secret"},
            }

    output = io.StringIO()
    message = RawLoggingTransport(Inner(), output).receive(1.0)
    assert message["access_token"] == "do-not-write"  # adapter receives exact source
    written = output.getvalue()
    assert "do-not-write" not in written
    assert "also-secret" not in written
    assert '"ltp": 100.0' in written


def test_owner_transport_error_redaction_is_recursive():
    from scripts.fyers_live_transport import _redact_sensitive

    redacted = _redact_sensitive({
        "message": "failed",
        "access_token": "do-not-log",
        "nested": [{"client_id": "also-private"}],
    })
    rendered = json.dumps(redacted)
    assert "do-not-log" not in rendered
    assert "also-private" not in rendered
    assert redacted["message"] == "failed"


def test_launcher_module_is_env_free():
    """The launcher must never touch the environment — the owner-side shim
    (outside orderflow/) is the only credential-aware code (R7/D7)."""
    import inspect
    from orderflow.checks import run_live_session

    source = inspect.getsource(run_live_session)
    for marker in ("os.environ", "getenv", "FYERS_TOKEN", "FYERS_CLIENT_ID"):
        assert marker not in source, f"launcher carries credential marker: {marker}"
