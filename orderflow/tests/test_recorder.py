"""U-P0.5 recorder tests: parquet round-trip, DuckDB views, feed-health
state transitions proven by ADVANCING A CLOCK (not by inspection)."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from orderflow.checks.feed_health import FeedHealthMonitor, State, Thresholds
from orderflow.market_data.websocket_manager import LifecycleEvent
from orderflow.market_data.schemas import DepthLevel, DepthSnapshot, QuoteUpdate
from orderflow.storage.parquet_writer import ParquetWriter
from orderflow.storage.recorder import ContinuousRecorder

UTC = timezone.utc
T0 = datetime(2026, 8, 28, 4, 15, 0, tzinfo=UTC)

pytest.importorskip("pyarrow")
duckdb = pytest.importorskip("duckdb")


def make_quote(ts=T0, **kw):
    base = dict(ts_exchange=None, ts_received=ts, symbol="NSE:ABC-EQ", ltp=100.0)
    base.update(kw)
    return QuoteUpdate(**base)


def make_depth(ts=T0, levels=5, **kw):
    bids = tuple(DepthLevel(price=99.9 - 0.05 * i, quantity=100 * (i + 1)) for i in range(levels))
    asks = tuple(DepthLevel(price=100.1 + 0.05 * i, quantity=90 * (i + 1)) for i in range(levels))
    base = dict(ts_exchange=None, ts_received=ts, symbol="NSE:ABC-EQ", bids=bids, asks=asks)
    base.update(kw)
    return DepthSnapshot(**base)


# ------------------------------------------------------------------ parquet


def test_parquet_round_trip_preserves_nulls(tmp_path):
    w = ParquetWriter(tmp_path)
    q = make_quote(ts=T0)  # every optional field None (R5: absent stays absent)
    d = make_depth(ts=T0 + timedelta(milliseconds=100))
    assert w.write_quotes([q]) == 1
    assert w.write_depth([d]) == 1

    files = sorted(tmp_path.rglob("*.parquet"))
    assert len(files) == 2
    assert "date=2026-08-28" in str(files[0])
    assert "symbol=NSE_ABC-EQ" in str(files[0])  # partition key sanitized; file column keeps canonical symbol
    assert ":" not in files[0].parent.name and ":" not in files[0].parent.parent.name

    import pyarrow.parquet as pq
    quotes_file = next(tmp_path.rglob("quotes-*.parquet"))
    q_table = pq.read_table(quotes_file)
    row = q_table.to_pylist()[0]
    assert row["ltp"] == 100.0
    assert row["last_trade_qty"] is None      # null stays null, never zero
    assert row["prev_close"] is None

    depth_file = next(tmp_path.rglob("depth-*.parquet"))
    d_table = pq.read_table(depth_file)
    drow = d_table.to_pylist()[0]
    assert len(drow["bids_price"]) == 5
    assert drow["bids_order_count"] is None   # levels had no order counts
    assert drow["total_buy_qty"] is None


def test_flushes_create_distinct_files_not_rewrites(tmp_path):
    w = ParquetWriter(tmp_path)
    w.write_quotes([make_quote(ts=T0)])
    w.write_quotes([make_quote(ts=T0 + timedelta(seconds=1))])
    assert len(list(tmp_path.rglob("quotes-*.parquet"))) == 2


def test_one_batch_groups_same_partition_into_one_file(tmp_path):
    w = ParquetWriter(tmp_path)
    w.write_quotes([
        make_quote(ts=T0, ltp=100.0),
        make_quote(ts=T0 + timedelta(seconds=1), ltp=101.0),
    ])
    assert len(list(tmp_path.rglob("quotes-*.parquet"))) == 1


def test_new_writer_process_cannot_overwrite_same_timestamp_file(tmp_path):
    ParquetWriter(tmp_path).write_quotes([make_quote(ts=T0, ltp=100.0)])
    ParquetWriter(tmp_path).write_quotes([make_quote(ts=T0, ltp=101.0)])
    files = list(tmp_path.rglob("quotes-*.parquet"))
    assert len(files) == 2


# ------------------------------------------------------------------ duckdb


def test_duckdb_views_and_coverage(tmp_path):
    from orderflow.storage.duckdb_repo import DuckRepository

    w = ParquetWriter(tmp_path)
    sym2 = "NSE:XYZ-EQ"
    w.write_quotes([
        make_quote(ts=T0),
        make_quote(ts=T0 + timedelta(seconds=1), symbol=sym2, ltp=50.0),
    ])
    w.write_depth([make_depth(ts=T0 + timedelta(milliseconds=200))])

    repo = DuckRepository(tmp_path)
    assert len(repo.quotes(symbol="NSE:ABC-EQ")) == 1
    assert len(repo.quotes()) == 2
    assert len(repo.depth(symbol=sym2)) == 0

    rows = repo.quotes(start=T0 + timedelta(milliseconds=500))
    assert [r[2] for r in rows] == [sym2]

    coverage = {(r[0], r[2]): r[3] for r in repo.coverage()}
    assert coverage[("NSE:ABC-EQ", "quote")] == 1
    assert coverage[("NSE:ABC-EQ", "depth")] == 1
    assert coverage[("NSE:XYZ-EQ", "quote")] == 1


def test_replay_reproduces_the_latest_canonical_book_without_filling_nulls(tmp_path):
    from orderflow.storage.duckdb_repo import DuckRepository

    first = make_depth(ts=T0, levels=2)
    latest = make_depth(
        ts=T0 + timedelta(seconds=2),
        levels=2,
        bids=(
            DepthLevel(price=100.0, quantity=250, order_count=3),
            DepthLevel(price=99.9, quantity=300, order_count=None),
        ),
        asks=(
            DepthLevel(price=100.2, quantity=200, order_count=2),
            DepthLevel(price=100.3, quantity=400, order_count=None),
        ),
        total_buy_qty=None,
        total_sell_qty=900,
    )
    writer = ParquetWriter(tmp_path)
    writer.write_depth([first, latest])

    repo = DuckRepository(tmp_path)
    replayed = repo.replay_depth("NSE:ABC-EQ", day="2026-08-28")
    assert replayed == [first, latest]
    assert repo.latest_book("NSE:ABC-EQ", day="2026-08-28") == latest
    assert replayed[-1].total_buy_qty is None


def test_recorder_persists_health_lifecycle_and_closed_gap_without_secrets(tmp_path):
    from orderflow.storage.duckdb_repo import DuckRepository

    monitor, clock = make_monitor(depth_stale_s=5.0, quote_stale_s=10.0)
    recorder = ContinuousRecorder(ParquetWriter(tmp_path), monitor, batch_size=1)
    recorder.record_lifecycle(LifecycleEvent("connected", clock.now, {}))
    recorder.record_event(make_depth(ts=clock.now))

    clock.advance(1)
    recorder.record_lifecycle(LifecycleEvent(
        "disconnected", clock.now,
        {"cause": "forced_disconnect", "FYERS_TOKEN": "must-not-persist"},
    ))
    clock.advance(3)
    recorder.record_lifecycle(LifecycleEvent(
        "connected", clock.now, {"after_reconnect": True, "cause": "forced_disconnect"}
    ))
    recorder.record_lifecycle(LifecycleEvent(
        "resubscribed", clock.now, {"symbols": ["NSE:ABC-EQ"], "access_token": "secret"}
    ))

    repo = DuckRepository(tmp_path)
    lifecycle = repo.lifecycle()
    gaps = repo.gaps()
    health = repo.health()
    assert [row[2] for row in lifecycle] == [
        "connected", "disconnected", "connected", "resubscribed"
    ]
    assert len(gaps) == 1
    assert gaps[0][3] == pytest.approx(3.0)
    assert gaps[0][4] == "forced_disconnect"
    assert any(row[2] == "DISCONNECTED" for row in health)

    written = "\n".join(
        str(value)
        for file in tmp_path.rglob("*.parquet")
        for row in __import__("pyarrow.parquet").parquet.read_table(file).to_pylist()
        for value in row.values()
    )
    assert "must-not-persist" not in written
    assert "secret" not in written


def test_recorder_buffers_hot_path_and_flushes_explicitly(tmp_path):
    monitor, clock = make_monitor()
    recorder = ContinuousRecorder(ParquetWriter(tmp_path), monitor, batch_size=100)
    recorder.record_event(make_quote(ts=clock.now, ltp=100.0))
    recorder.record_event(make_quote(ts=clock.now + timedelta(seconds=1), ltp=101.0))
    assert not list(tmp_path.rglob("*.parquet"))
    recorder.flush()
    assert len(list(tmp_path.rglob("quotes-*.parquet"))) == 1
    assert len(list(tmp_path.rglob("health-*.parquet"))) == 1


# ------------------------------------------------------------------ feed health


class Clock:
    def __init__(self):
        self.now = T0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now = self.now + timedelta(seconds=seconds)


def make_monitor(**thresholds):
    clock = Clock()
    monitor = FeedHealthMonitor(Thresholds(**thresholds), clock=clock)
    return monitor, clock


def test_healthy_then_depth_stale_disables_flow_state():
    monitor, clock = make_monitor(depth_stale_s=5.0, quote_stale_s=10.0)
    v1 = monitor.on_depth(make_depth(ts=clock.now))
    assert v1.state is State.HEALTHY and v1.order_flow_enabled is True

    clock.advance(6)  # no depth for 6 s, quotes still fresh
    v2 = monitor.on_quote(make_quote(ts=clock.now))
    assert v2.state is State.DEGRADED
    assert "depth_stale" in v2.reasons
    assert v2.order_flow_enabled is False
    assert v2.flow_state == "UNKNOWN"   # R3/R10: last reading never shown as live


def test_no_data_at_all_is_stale_not_healthy():
    monitor, clock = make_monitor(depth_stale_s=5.0, quote_stale_s=10.0)
    clock.advance(30)
    v = monitor._evaluate(())
    assert v.state is State.STALE
    assert v.flow_state == "UNKNOWN"


def test_disconnected_then_reconnected_counts_churn():
    monitor, clock = make_monitor(depth_stale_s=5.0, quote_stale_s=10.0, degraded_reconnects=1)
    monitor.on_depth(make_depth(ts=clock.now))
    v_disc = monitor.on_disconnected("forced_disconnect")
    assert v_disc.state is State.DISCONNECTED
    assert v_disc.order_flow_enabled is False and v_disc.flow_state == "UNKNOWN"

    v_rec = monitor.on_reconnected()
    assert v_rec.state is not State.DISCONNECTED
    assert monitor.reconnect_count == 1

    monitor.on_disconnected("x")
    v_rec2 = monitor.on_reconnected()
    assert monitor.reconnect_count == 2
    assert "reconnect_churn" in v_rec2.reasons        # churn beyond threshold
    assert v_rec2.state is State.DEGRADED


def test_reconnect_requires_fresh_depth_before_flow_can_be_live_again():
    monitor, clock = make_monitor(depth_stale_s=5.0, quote_stale_s=10.0)
    assert monitor.on_depth(make_depth(ts=clock.now)).order_flow_enabled is True
    clock.advance(1)
    monitor.on_disconnected("forced_disconnect")
    clock.advance(1)
    reconnected = monitor.on_reconnected()
    assert reconnected.state is State.DEGRADED
    assert reconnected.order_flow_enabled is False
    assert reconnected.flow_state == "UNKNOWN"
    quote_only = monitor.on_quote(make_quote(ts=clock.now))
    assert quote_only.order_flow_enabled is False
    fresh_depth = monitor.on_depth(make_depth(ts=clock.now))
    assert fresh_depth.order_flow_enabled is True
    assert fresh_depth.flow_state == "LIVE"


def test_duplicate_and_clock_skew_flags():
    monitor, clock = make_monitor(max_clock_skew_ms=1500.0)
    monitor.on_quote(make_quote(ts=clock.now, ltp=100.0))
    v_dup = monitor.on_quote(make_quote(ts=clock.now + timedelta(milliseconds=10), ltp=100.0))
    assert "duplicate_quote" in v_dup.reasons
    assert monitor.duplicate_count == 1

    v_skew = monitor.on_quote(make_quote(
        ts=clock.now + timedelta(milliseconds=20), ltp=101.0,
        ts_exchange=clock.now - timedelta(seconds=5)))  # 5000 ms latency >> threshold
    assert "clock_skew" in v_skew.reasons
    assert monitor.clock_skew_count == 1


def test_duplicate_window_expires_and_good_data_recovers_quality_state():
    monitor, clock = make_monitor(duplicate_window_s=0.05)
    monitor.on_quote(make_quote(ts=clock.now, ltp=100.0))
    clock.advance(0.01)
    assert monitor.on_quote(make_quote(ts=clock.now, ltp=100.0)).state is State.DEGRADED
    clock.advance(1.0)
    recovered = monitor.on_quote(make_quote(ts=clock.now, ltp=100.0))
    assert recovered.state is State.HEALTHY
    assert recovered.reasons == ()


def test_out_of_order_detected():
    monitor, clock = make_monitor()
    monitor.on_quote(make_quote(ts=clock.now + timedelta(seconds=2)))
    v = monitor.on_quote(make_quote(ts=clock.now + timedelta(seconds=1)))
    assert "out_of_order" in v.reasons
    assert monitor.out_of_order_count == 1
    assert monitor.last_quote_at == clock.now + timedelta(seconds=2)


def test_recorder_tick_persists_quiet_period_verdicts(tmp_path):
    """CP-2 finding 6: the public tick() path (quiet-period staleness checks)
    must persist verdicts, so a feed that goes silent is recorded as STALE —
    not invisible."""
    from orderflow.storage.duckdb_repo import DuckRepository
    from orderflow.storage.recorder import ContinuousRecorder

    monitor, clock = make_monitor(depth_stale_s=5.0, quote_stale_s=10.0)
    recorder = ContinuousRecorder(ParquetWriter(tmp_path), monitor, batch_size=1)
    recorder.record_lifecycle(LifecycleEvent("connected", clock.now, {}))
    recorder.record_event(make_depth(ts=clock.now))

    clock.advance(6)          # depth goes stale while nothing arrives
    recorder.tick()
    recorder.flush()

    import pyarrow.parquet as pq
    health_rows = []
    for f in tmp_path.rglob("health-*.parquet"):
        health_rows.extend(pq.read_table(f).to_pylist())
    feed_rows = [r for r in health_rows if r["symbol"] == "__FEED__"]
    assert feed_rows, "tick() verdicts must be persisted"
    assert feed_rows[-1]["state"] == "DEGRADED"
