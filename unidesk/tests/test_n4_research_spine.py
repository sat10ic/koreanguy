"""N4 research spine: candidate freeze, walk-forward folds, leakage suite."""
from datetime import date, datetime, timedelta, timezone

import pytest

from unidesk.contracts.base import ContractError
from unidesk.contracts.market import DailyBar
from unidesk.contracts.research import ResearchEvent
from unidesk.momentum.data.calendar import from_sessions
from unidesk.momentum.data.market_store import InMemoryMarketStore, VersionedDailyBar
from unidesk.momentum.detectors.momentum_burst import Detection
from unidesk.momentum.detectors.registry import DetectorConfig
from unidesk.momentum.scan import scan_universe
from unidesk.research.candidates import (
    attach_outcomes, freeze_includes_negatives, freeze_scan, future_after,
)
from unidesk.research.event_store import load_events, persist_events
from unidesk.research.leakage_suite import (
    embargo_respected, gold_known_at, membership_as_of, planted_full_sample_mean,
    planted_future_bars_is_caught, planted_gold_includes_future,
    planted_include_future_bars, planted_today_membership, pit_prefix,
    train_only_mean, train_test_disjoint,
)
from unidesk.research.costs import COSTS_VERSION
from unidesk.research.labels import OUTCOME_LABELS_VERSION
from unidesk.research.walkforward import (
    assign_event, captured_return_bps, expanding_folds,
    next_session, simulate_long, years_4_1_folds,
)
from unidesk.research.archive_attach import sessions_needing_label_refresh

UTC = timezone.utc
DAY0 = datetime(2026, 1, 2, 18, 0, tzinfo=UTC)


def _calendar(n=120):
    sessions = [date(2025, 1, 2) + timedelta(days=i) for i in range(n)]
    return from_sessions(sessions)


def test_expanding_folds_embargo_and_disjoint():
    cal = _calendar(120)
    folds = expanding_folds(cal, min_train=63, test_sessions=21, embargo=5)
    assert len(folds) >= 1
    f0 = folds[0]
    assert f0.scheme == "expanding"
    assert embargo_respected(f0, cal)
    # embargo sessions are in neither train nor test
    mid = cal.days[63].trade_date  # first unused session after 63-session train
    assert assign_event(mid, f0) == "embargo"
    assert assign_event(f0.train_end, f0) == "train"
    assert assign_event(f0.test_start, f0) == "test"
    train = [d.trade_date for d in cal.days if assign_event(d.trade_date, f0) == "train"]
    test = [d.trade_date for d in cal.days if assign_event(d.trade_date, f0) == "test"]
    assert train_test_disjoint(train, test)
    assert len(test) == 21
    assert len(train) == 63


def test_years_4_1_refuses_short_calendar():
    with pytest.raises(ContractError, match="4y/1y"):
        years_4_1_folds(_calendar(120))


def test_next_bar_fill_is_not_same_session():
    cal = _calendar(10)
    s0 = cal.days[0].trade_date
    nxt = next_session(cal, s0)
    assert nxt == cal.days[1].trade_date
    assert nxt != s0


def test_simulate_long_reports_gross_and_net():
    # entry 100, close path 101 then 102 → 2% = 200 bps over horizon 2
    out = simulate_long(
        entry=100.0, stop=95.0,
        future_highs=[101.0, 110.0], future_lows=[99.0, 99.0],
        future_closes=[101.0, 102.0], future_opens=[100.0, 101.0], horizon=2,
        order_value=1e5, adv_value=1e7, gap_entry=False,
    )
    assert out["gross_bps"] == pytest.approx(200.0)
    assert out["net_bps"] < out["gross_bps"]
    assert out["stop_hit"] is False
    assert out["r_multiple"] == pytest.approx(2.0)  # MFE +10% / 5% risk


def test_simulate_long_uses_the_stop_loss_not_a_later_close_after_a_stop_touch():
    # A later closing rally cannot turn a stopped-out OHLC path into a gain.
    out = simulate_long(
        entry=100.0, stop=95.0,
        future_highs=[110.0, 112.0], future_lows=[93.0, 108.0],
        future_closes=[109.0, 111.0], future_opens=[100.0, 108.0], horizon=2,
        order_value=1e5, adv_value=1e7, gap_entry=False,
    )
    assert out["stop_hit"] is True
    assert out["potential_r_multiple"] == pytest.approx(2.4)
    assert out["r_multiple"] == pytest.approx(-1.0)
    assert out["gross_bps"] == pytest.approx(-500.0)
    assert out["net_bps"] < out["gross_bps"]


def test_simulate_long_fills_at_the_gap_open_not_the_stop_price():
    # First future bar OPENS below the stop (a real overnight gap-down),
    # not just touches it intraday. Regression for a NameError
    # (undefined first_stop_bar) that this exact path used to raise.
    out = simulate_long(
        entry=100.0, stop=95.0,
        future_highs=[91.0, 96.0], future_lows=[88.0, 90.0],
        future_closes=[90.0, 92.0], future_opens=[89.0, 90.0], horizon=2,
        order_value=1e5, adv_value=1e7, gap_entry=False,
    )
    assert out["stop_hit"] is True
    assert out["gap_through"] is True
    assert out["exit_price"] == pytest.approx(89.0)
    assert out["gross_bps"] == pytest.approx((89.0 / 100.0 - 1.0) * 10_000.0)


def test_leakage_suite_catches_planted_bugs():
    series = [10.0, 11.0, 12.0, 99.0]
    assert pit_prefix(series, 2) == [10.0, 11.0, 12.0]
    assert 99.0 in planted_include_future_bars(series, 2)
    assert planted_future_bars_is_caught() is True

    train, test_val, all_vals = [1.0, 2.0, 3.0], 10.0, [1.0, 2.0, 3.0, 10.0]
    honest = train_only_mean(train, test_val)
    leaky = planted_full_sample_mean(all_vals, test_val)
    assert honest != leaky  # full-sample mean is pulled toward the test point

    history = [
        {"symbol": "TRENT", "effective_from": date(2024, 1, 1), "effective_to": date(2025, 6, 30)},
    ]
    assert membership_as_of(history, "TRENT", date(2025, 6, 30)) is True
    assert membership_as_of(history, "TRENT", date(2025, 7, 1)) is False
    # planted today-list would still say TRENT is in on 2025-07-01
    assert planted_today_membership(["TRENT"], "TRENT", date(2025, 7, 1)) is True

    gold = [
        {"id": "past", "session": date(2026, 1, 2)},
        {"id": "future", "session": date(2026, 6, 1)},
    ]
    assert [c["id"] for c in gold_known_at(gold, date(2026, 3, 1))] == ["past"]
    assert len(planted_gold_includes_future(gold, date(2026, 3, 1))) == 2


def test_freeze_scan_keeps_invalid_symbols():
    store = InMemoryMarketStore()
    for i in range(70):
        close = 90 + i * 0.75
        bar = DailyBar(
            symbol="STRONG", session=(DAY0 + timedelta(days=i)).date(),
            open=close, high=close + 0.5, low=close - 0.5, close=close,
            volume=1000 + i * 10, delivery_percentage=50.0, data_version="test",
        )
        store.add_daily_bar(VersionedDailyBar(bar=bar, available_at=DAY0 + timedelta(days=i + 1)))
        flat = 50.0
        bar2 = DailyBar(
            symbol="FLAT", session=(DAY0 + timedelta(days=i)).date(),
            open=flat, high=flat + 0.1, low=flat - 0.1, close=flat,
            volume=800, delivery_percentage=40.0, data_version="test",
        )
        store.add_daily_bar(VersionedDailyBar(bar=bar2, available_at=DAY0 + timedelta(days=i + 1)))
    result = scan_universe(
        store, DAY0 + timedelta(days=70),
        detector_config=DetectorConfig.only(["momentum_burst", "power_play"]),
    )
    events = freeze_scan(result)
    assert len(events) == 2
    assert freeze_includes_negatives(events) is True
    by = {e.symbol: e for e in events}
    assert by["FLAT"].snapshot["detectors"]
    # FLAT should not be a burst VALID
    burst = by["FLAT"].snapshot["detectors"]["momentum_burst"]["detection"]
    assert burst in (Detection.INVALID.value, Detection.INSUFFICIENT_DATA.value)
    assert by["STRONG"].outcome_labels == {}  # outcomes not computed at freeze
    assert captured_return_bps(100.0, [101.0], 1) == pytest.approx(100.0)


def test_event_store_round_trip_keeps_negatives(tmp_path):
    store = InMemoryMarketStore()
    for i in range(70):
        close = 90 + i * 0.75
        store.add_daily_bar(VersionedDailyBar(
            bar=DailyBar(
                symbol="STRONG", session=(DAY0 + timedelta(days=i)).date(),
                open=close, high=close + 0.5, low=close - 0.5, close=close,
                volume=1000, data_version="test",
            ),
            available_at=DAY0 + timedelta(days=i + 1),
        ))
        store.add_daily_bar(VersionedDailyBar(
            bar=DailyBar(
                symbol="FLAT", session=(DAY0 + timedelta(days=i)).date(),
                open=50.0, high=50.1, low=49.9, close=50.0,
                volume=800, data_version="test",
            ),
            available_at=DAY0 + timedelta(days=i + 1),
        ))
    result = scan_universe(
        store, DAY0 + timedelta(days=70),
        detector_config=DetectorConfig.only(["momentum_burst"]),
    )
    events = freeze_scan(result)
    stats = persist_events(events, tmp_path)
    assert stats["rows"] == 2
    assert stats["partitions"] == 1
    loaded = load_events(tmp_path)
    assert {e.symbol for e in loaded} == {"STRONG", "FLAT"}
    assert freeze_includes_negatives(loaded) is True
    session = events[0].event_id.rsplit(":", 1)[-1]
    assert len(load_events(tmp_path, session=session)) == 2
    assert load_events(tmp_path, session="1999-01-01") == []


def test_future_after_excludes_decision_bar():
    sessions = [date(2026, 1, d) for d in (2, 3, 4)]
    closes = [100.0, 101.0, 102.0]
    assert future_after(sessions, closes, date(2026, 1, 3)) == [102.0]


def test_attach_outcomes_uses_next_bar_and_unresolved_on_empty_future():
    decision = date(2026, 1, 10)
    ts = datetime(2026, 1, 10, 18, 0, tzinfo=UTC)
    event = ResearchEvent(
        event_id=f"X:{decision.isoformat()}",
        candidate_id=f"X:{decision.isoformat()}",
        symbol="X",
        timestamp=ts,
        snapshot={"close": 100.0, "atr_pct": 2.0, "detectors": {"momentum_burst": {"detection": "VALID", "failures": []}}},
        config_hash="abcd",
        research_schema_version="research-event-v1",
        outcome_labels={},
    )
    empty = attach_outcomes([event], {})
    assert empty[0].outcome_labels["status"] == "UNRESOLVED"
    assert empty[0].outcome_labels["reason"] == "no_future_series"

    future = {
        "X": {
            "sessions": [date(2026, 1, 10), date(2026, 1, 11), date(2026, 1, 12)],
            "opens": [100.0, 101.0, 102.0],
            "highs": [101.0, 110.0, 112.0],
            "lows": [99.0, 100.0, 101.0],
            "closes": [100.5, 109.0, 111.0],
        }
    }
    labeled = attach_outcomes([event], future, horizon=2)
    out = labeled[0].outcome_labels
    assert out["status"] == "RESOLVED"
    assert out["label_version"] == OUTCOME_LABELS_VERSION
    assert out["entry"] == pytest.approx(101.0)  # next open, not 100
    assert out["mfe_pct"] > 0
    assert event.outcome_labels == {}  # freeze copy is immutable / original empty
    # decision-session print must not leak into the future slice
    assert future_after(future["X"]["sessions"], future["X"]["opens"], decision)[0] == 101.0

    # No adv_series in the future map (as above) -> cost fields fail closed
    # to None rather than fabricating a cost off a missing ADV (R12).
    assert out["net_bps"] is None
    assert out["cost_total_rt_bps"] is None
    assert out["costs_version"] is None


def test_attach_outcomes_computes_net_bps_when_adv_is_available():
    # Regression: OUTCOME_LABELS_VERSION was bumped to v4-net-cost claiming
    # net-of-cost wiring before candidates.attach_outcomes actually called
    # round_trip_cost/net_return_bps -- adv_value was fetched and discarded.
    # This locks in the real wiring: net_bps present and strictly below
    # gross_bps once a positive ADV is available.
    decision = date(2026, 1, 10)
    ts = datetime(2026, 1, 10, 18, 0, tzinfo=UTC)
    event = ResearchEvent(
        event_id="X:2026-01-10", candidate_id="X:2026-01-10", symbol="X",
        timestamp=ts,
        snapshot={"close": 100.0, "atr_pct": 2.0, "detectors": {}},
        config_hash="abcd", research_schema_version="research-event-v1",
        outcome_labels={},
    )
    future = {
        "X": {
            "sessions": [date(2026, 1, 10), date(2026, 1, 11), date(2026, 1, 12)],
            "opens": [100.0, 101.0, 102.0],
            "highs": [101.0, 110.0, 112.0],
            "lows": [99.0, 100.0, 101.0],
            "closes": [100.5, 109.0, 111.0],
            "adv_series": [5_000_000.0, 5_000_000.0, 5_000_000.0],
        }
    }
    out = attach_outcomes([event], future, horizon=2)[0].outcome_labels
    assert out["net_bps"] is not None
    assert out["cost_total_rt_bps"] is not None
    assert out["costs_version"] == COSTS_VERSION
    assert out["net_bps"] < out["gross_bps"]
    assert out["net_bps"] == pytest.approx(out["gross_bps"] - out["cost_total_rt_bps"])


def test_label_refresh_identifies_legacy_outcome_partitions(tmp_path):
    timestamp = datetime(2026, 1, 10, 18, 0, tzinfo=UTC)
    legacy = ResearchEvent(
        event_id="OLD:2026-01-10", candidate_id="OLD:2026-01-10", symbol="OLD",
        timestamp=timestamp, snapshot={"close": 100.0}, config_hash="old",
        research_schema_version="research-event-v1",
        outcome_labels={"status": "RESOLVED", "r_multiple": 2.0},
    )
    current = ResearchEvent(
        event_id="NEW:2026-01-11", candidate_id="NEW:2026-01-11", symbol="NEW",
        timestamp=timestamp + timedelta(days=1), snapshot={"close": 100.0}, config_hash="new",
        research_schema_version="research-event-v1",
        outcome_labels={"status": "RESOLVED", "label_version": OUTCOME_LABELS_VERSION},
    )
    persist_events([legacy, current], tmp_path)
    # B-05: these fixture snapshots carry no ca_table_hash, so the CA-basis
    # dimension is pinned to "" here to isolate the label-version dimension.
    assert sessions_needing_label_refresh(tmp_path, expected_ca_hash="") == ["2026-01-10"]


def test_label_refresh_flags_ca_table_change(tmp_path):
    """B-05 regression (2026-09-01 audit): changing ONLY the CA table must
    mark partitions stale even when every label_version matches. The old
    check compared label_version only and reported a false all-clear while
    the live archive sat on a rejected adjustment basis."""
    timestamp = datetime(2026, 1, 10, 18, 0, tzinfo=UTC)
    old_basis = ResearchEvent(
        event_id="X:2026-01-10", candidate_id="X:2026-01-10", symbol="X",
        timestamp=timestamp,
        snapshot={"close": 100.0, "ca_table_hash": "aaaa1111bbbb2222"},
        config_hash="abcd", research_schema_version="research-event-v1",
        outcome_labels={"status": "RESOLVED", "label_version": OUTCOME_LABELS_VERSION},
    )
    persist_events([old_basis], tmp_path)
    assert sessions_needing_label_refresh(tmp_path, expected_ca_hash="dddd4444eeee5555") == ["2026-01-10"]
    assert sessions_needing_label_refresh(tmp_path, expected_ca_hash="aaaa1111bbbb2222") == []


def test_simulate_long_frames_short_horizon_as_partial():
    out = simulate_long(
        entry=100.0, stop=95.0,
        future_highs=[110.0], future_lows=[99.0], future_closes=[109.0],
        future_opens=[100.0], horizon=5,
        order_value=1e5, adv_value=1e7,
    )
    assert out["framing"] == "PARTIAL"
    out2 = simulate_long(
        entry=100.0, stop=95.0,
        future_highs=[101.0, 110.0], future_lows=[99.0, 99.0],
        future_closes=[101.0, 102.0], future_opens=[100.0, 100.5], horizon=2,
        order_value=1e5, adv_value=1e7,
    )
    assert out2["framing"] == "RESOLVED"
