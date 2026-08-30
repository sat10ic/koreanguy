"""Phase 0 primitives (D14): calendar, costs, leakage, invariants, delivery lag."""
from datetime import date, datetime, timezone

import pytest

from unidesk.contracts.base import ContractError
from unidesk.momentum.data.calendar import from_sessions
from unidesk.momentum.data.invariants import (
    delivery_pct_calc, delivery_violations, ohlc_violations,
)
from unidesk.research.costs import (
    CostAssumptions, impact_bps_one_side, net_return_bps, round_trip_cost,
)
from unidesk.research.delivery_lag import delivery_usable_for_decision
from unidesk.contracts.research import ResearchEvent
from unidesk.research.leakage import (
    assert_feature_not_after_decision, embargo_overlapping_events,
    same_event_collision, same_symbol_embargo,
)
from unidesk.research.provenance import Provenance

UTC = timezone.utc


def test_calendar_from_observed_sessions_not_weekdays():
    # A Saturday is only a session if it was observed (muhurat etc.)
    sessions = [date(2026, 6, 29), date(2026, 6, 30), date(2026, 7, 1), date(2026, 7, 3)]
    cal = from_sessions(sessions)
    assert len(cal) == 4
    assert cal.get(date(2026, 7, 2)) is None          # weekday we did not observe
    assert cal.session_distance(date(2026, 6, 30), date(2026, 7, 3)) == 2
    assert cal.get(date(2026, 6, 30)).next_trade_date == date(2026, 7, 1)
    assert cal.get(date(2026, 6, 30)).previous_trade_date == date(2026, 6, 29)


def test_calendar_rejects_empty_and_duplicates_via_sort():
    with pytest.raises(ContractError):
        from_sessions([])
    cal = from_sessions([date(2026, 6, 30), date(2026, 6, 30), date(2026, 7, 1)])
    assert len(cal) == 2


def test_cost_model_hand_computed():
    # order 1% of ADV → 8 bps * 0.01 = 0.08 bps/side, well under 15 cap
    c = round_trip_cost(order_value=1e5, adv_value=1e7, gap_entry=False)
    assert c.impact_rt_bps == pytest.approx(2 * 8.0 * (1e5 / 1e7))
    assert c.gap_slippage_bps == 0.0
    assert c.total_rt_bps == pytest.approx(15 + 20 + 5 + c.impact_rt_bps)
    # impact cap: huge order / tiny ADV
    assert impact_bps_one_side(1e9, 1e6) == 15.0
    gap = round_trip_cost(order_value=1e5, adv_value=1e7, gap_entry=True)
    assert gap.gap_slippage_bps == 25.0
    assert net_return_bps(100.0, c) == pytest.approx(100.0 - c.total_rt_bps)


def test_cost_model_missing_adv_fails_closed():
    with pytest.raises(ContractError, match="adv_value"):
        round_trip_cost(order_value=1e5, adv_value=0.0)


def test_decision_time_contract():
    t0 = datetime(2026, 6, 30, 10, 0, tzinfo=UTC)
    t1 = datetime(2026, 6, 30, 12, 0, tzinfo=UTC)
    assert_feature_not_after_decision(t0, t1)
    with pytest.raises(ContractError, match="after"):
        assert_feature_not_after_decision(t1, t0)


def test_same_symbol_embargo_60_sessions():
    sessions = [date(2026, 1, 1) + __import__("datetime").timedelta(days=i)
                for i in range(80)]  # 80 consecutive calendar days as sessions
    cal = from_sessions(sessions)
    query = sessions[70]
    inside = sessions[70 - 60]
    outside = sessions[70 - 61]
    assert same_symbol_embargo(query, inside, cal) is True
    assert same_symbol_embargo(query, query, cal) is True
    assert same_symbol_embargo(query, outside, cal) is False
    assert same_symbol_embargo(query, date(2010, 1, 1), cal) is True  # unknown date = unsafe
    assert same_event_collision(["ep-A", "ep-B"]) is False
    assert same_event_collision(["ep-A", "ep-A"]) is True


def _event(symbol: str, session: date) -> ResearchEvent:
    return ResearchEvent(
        event_id=f"{symbol}:{session.isoformat()}", candidate_id=f"{symbol}:{session.isoformat()}",
        symbol=symbol, timestamp=datetime(session.year, session.month, session.day, 18, 0, tzinfo=UTC),
        snapshot={"close": 100.0}, config_hash="cfg", research_schema_version="research-event-v1",
    )


def test_embargo_overlapping_events_keeps_the_earliest_of_a_same_symbol_cluster():
    sessions = [date(2026, 1, 1) + __import__("datetime").timedelta(days=i) for i in range(80)]
    cal = from_sessions(sessions)
    # X: three decisions, all mutually within 60 sessions of the first one --
    # the constitution treats this whole run as ONE independent sample.
    events = [
        _event("X", sessions[0]), _event("X", sessions[30]), _event("X", sessions[59]),
        # Y: two decisions 61 sessions apart -- genuinely independent.
        _event("Y", sessions[0]), _event("Y", sessions[61]),
    ]
    kept, embargoed = embargo_overlapping_events(events, cal)
    kept_ids = {e.event_id for e in kept}
    assert kept_ids == {"X:2026-01-01", "Y:2026-01-01", "Y:2026-03-03"}
    assert {e.event_id for e, _reason_session in embargoed} == {"X:2026-01-31", "X:2026-03-01"}
    assert same_event_collision([e.event_id for e in kept]) is False


def test_embargo_overlapping_events_a_fresh_kept_event_resets_the_window():
    # A > 60 B > 60 C, with A-C also > 60: all three independent even though
    # they form one visually "dense" run -- greedy-earliest must not merge
    # non-overlapping pairs into a single false cluster.
    sessions = [date(2026, 1, 1) + __import__("datetime").timedelta(days=i) for i in range(200)]
    cal = from_sessions(sessions)
    events = [_event("Z", sessions[0]), _event("Z", sessions[61]), _event("Z", sessions[122])]
    kept, embargoed = embargo_overlapping_events(events, cal)
    assert {e.event_id for e in kept} == {e.event_id for e in events}
    assert embargoed == []


def test_ohlc_and_delivery_invariants():
    assert ohlc_violations(open=10, high=12, low=9, close=11, volume=100) == ()
    bad = ohlc_violations(open=10, high=10, low=11, close=10, volume=-1)
    assert "high < low" in bad
    assert "volume < 0" in bad
    assert delivery_pct_calc(1000, 400) == pytest.approx(40.0)
    assert delivery_violations(traded_qty=100, deliverable_qty=120) == ("deliverable_qty > traded_qty",)
    assert delivery_violations(
        traded_qty=100, deliverable_qty=40,
        delivery_pct_source=40.0, delivery_pct_calc=40.0,
    ) == ()
    assert delivery_violations(
        traded_qty=100, deliverable_qty=40,
        delivery_pct_source=41.0, delivery_pct_calc=40.0,
    ) == ("delivery_pct source/calc diverge > tolerance",)


def test_delivery_lag_blocks_same_session_decision():
    cal = from_sessions([date(2026, 6, 29), date(2026, 6, 30), date(2026, 7, 1)])
    assert delivery_usable_for_decision(date(2026, 6, 30), date(2026, 6, 30), cal) is False
    assert delivery_usable_for_decision(date(2026, 6, 30), date(2026, 7, 1), cal) is True
    assert delivery_usable_for_decision(date(2026, 6, 30), date(2026, 6, 29), cal) is False


def test_provenance_rejects_available_before_session():
    ok = Provenance(
        effective_date=date(2026, 6, 30),
        available_at=datetime(2026, 6, 30, 12, 30, tzinfo=UTC),
        built_at=datetime(2026, 6, 30, 13, 0, tzinfo=UTC),
        source_version="bhavcopy-v1",
    )
    assert ok.source_version == "bhavcopy-v1"
    with pytest.raises(ContractError):
        Provenance(
            effective_date=date(2026, 6, 30),
            available_at=datetime(2026, 6, 29, 12, 0, tzinfo=UTC),
            built_at=datetime(2026, 6, 30, 13, 0, tzinfo=UTC),
            source_version="bhavcopy-v1",
        )
