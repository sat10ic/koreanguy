"""Directive 1(e): the unconfirmed corporate-action guard -- the single most
important guard in this task.

`unidesk/config/confirmed_actions.csv` has 4 confirmed names. Everything
else the conservative gap detector (`momentum/data/corp_actions.py`'s
`detect_split_candidates_bars`, driven by `momentum/data/splits.py`'s
`scan_store_for_splits`) flags is an UNCONFIRMED open-gap candidate --
HANDOFF.md's "194 unconfirmed detector candidates" backlog. This test uses
a REAL unconfirmed candidate produced by the actual detector (not an
invented date) to prove that any research event whose outcome window spans
that candidate's gap session is refused a real outcome.
"""
from datetime import date, datetime, timedelta, timezone

import pytest

from unidesk.contracts.market import DailyBar
from unidesk.contracts.research import ResearchEvent
from unidesk.momentum.data.corp_actions import ConfirmedAction
from unidesk.momentum.data.market_store import InMemoryMarketStore, VersionedDailyBar
from unidesk.momentum.data.splits import scan_store_for_splits, unconfirmed_candidate_sessions
from unidesk.research.candidates import attach_outcomes

UTC = timezone.utc
DAY0 = datetime(2026, 6, 1, 18, 0, tzinfo=UTC)


def _add_session(store, symbol, i, close, vol=1000.0):
    session = (DAY0 + timedelta(days=i)).date()
    bar = DailyBar(
        symbol=symbol, session=session,
        open=close, high=close + 0.5, low=close - 0.5,
        close=close, volume=int(vol), data_version="test",
    )
    store.add_daily_bar(VersionedDailyBar(bar=bar, available_at=DAY0 + timedelta(days=i + 1)))
    return session


def _build_store_with_a_real_unconfirmed_gap(symbol="GAPCO", gap_index=35):
    """A clean ~2:1-implied overnight gap the detector WILL flag as a split
    candidate: open ~= prev_close*0.5, sustained volume, implied factor
    within the detector's clean-fraction tolerance of 0.5.

    Pre-gap closes RAMP (never repeat) rather than sitting flat, because
    ``detect_split_candidates_bars`` re-locates the gap bar via
    ``closes.index(cand.prev_close)`` -- with a flat pre-gap price that
    lookup returns the FIRST matching bar, not the true gap bar. That
    relocation quirk is pre-existing code outside this task's scope; the
    ramp sidesteps it so this fixture's SplitCandidate.session is the real
    gap day the detector meant to flag.
    """
    store = InMemoryMarketStore()
    sessions = []
    for i in range(60):
        close = (200.0 - i * 0.1) if i < gap_index else 100.0
        sessions.append(_add_session(store, symbol, i, close))
    return store, sessions


def test_the_real_detector_flags_this_fixture_as_an_unconfirmed_candidate():
    """Sanity: prove the candidate used below is a REAL detector output, not
    an invented date."""
    store, sessions = _build_store_with_a_real_unconfirmed_gap()
    candidates = scan_store_for_splits(store)
    gapco = [c for c in candidates if c.symbol == "GAPCO"]
    assert len(gapco) == 1
    assert gapco[0].session == sessions[35]
    assert gapco[0].nearest_clean == pytest.approx(0.5)

    backlog = unconfirmed_candidate_sessions(candidates, confirmed=[])
    assert sessions[35] in backlog["GAPCO"]


def test_confirming_the_action_removes_it_from_the_unconfirmed_backlog():
    store, sessions = _build_store_with_a_real_unconfirmed_gap()
    candidates = scan_store_for_splits(store)
    confirmed = [ConfirmedAction("GAPCO", sessions[35], 0.5, "test-confirmed")]
    backlog = unconfirmed_candidate_sessions(candidates, confirmed=confirmed)
    assert "GAPCO" not in backlog  # no longer unconfirmed


def _event(symbol: str, decision: date) -> ResearchEvent:
    ts = datetime(decision.year, decision.month, decision.day, 18, 0, tzinfo=UTC)
    return ResearchEvent(
        event_id=f"{symbol}:{decision.isoformat()}",
        candidate_id=f"{symbol}:{decision.isoformat()}",
        symbol=symbol,
        timestamp=ts,
        snapshot={
            "close": 200.0, "atr_pct": 2.0,
            "detectors": {"momentum_burst": {"detection": "VALID", "failures": []}},
        },
        config_hash="abcd",
        research_schema_version="research-event-v1",
        outcome_labels={},
    )


def test_attach_outcomes_refuses_a_real_outcome_when_the_window_spans_an_unconfirmed_candidate():
    """The decisive test: a decision fired a few sessions BEFORE the real
    unconfirmed gap, with a horizon long enough that the outcome window
    would otherwise span the gap. Without the guard, MAE would be a
    fabricated ~-50% (200 -> 100, i.e. exactly the catastrophic-loss shape
    the task warns about) that is indistinguishable from a genuine loss.
    With the guard wired in, the event must land UNRESOLVED instead."""
    store, sessions = _build_store_with_a_real_unconfirmed_gap(gap_index=35)
    candidates = scan_store_for_splits(store)
    backlog = unconfirmed_candidate_sessions(candidates, confirmed=[])
    assert "GAPCO" in backlog

    decision = sessions[30]  # 5 sessions before the gap
    event = _event("GAPCO", decision)
    future_sessions = sessions[31:40]
    closes = [200.0] * 4 + [100.0] * 5  # bars 31-34 pre-gap, 35-39 post-gap (raw, unadjusted)
    future = {
        "GAPCO": {
            "sessions": future_sessions,
            "opens": closes,
            "highs": [c + 0.5 for c in closes],
            "lows": [c - 0.5 for c in closes],
            "closes": closes,
        }
    }
    out = attach_outcomes(
        [event], future, horizon=9, unconfirmed_ca_sessions=backlog,
    )[0].outcome_labels
    assert out["status"] == "UNRESOLVED"
    assert out["reason"] == "unconfirmed_corporate_action"
    assert "mae_pct" not in out
    assert "r_multiple" not in out


def test_attach_outcomes_without_the_guard_would_have_produced_the_catastrophic_value():
    """Negative control: WITHOUT unconfirmed_ca_sessions, the same fixture
    resolves and DOES produce the ~-50% catastrophic MAE this guard exists
    to prevent -- proving the guard in the prior test is doing real work,
    not vacuously passing because the fixture never leaks."""
    store, sessions = _build_store_with_a_real_unconfirmed_gap(gap_index=35)
    decision = sessions[30]
    event = _event("GAPCO", decision)
    future_sessions = sessions[31:40]
    closes = [200.0] * 4 + [100.0] * 5
    future = {
        "GAPCO": {
            "sessions": future_sessions,
            "opens": closes,
            "highs": [c + 0.5 for c in closes],
            "lows": [c - 0.5 for c in closes],
            "closes": closes,
        }
    }
    out = attach_outcomes([event], future, horizon=9)[0].outcome_labels
    assert out["status"] == "RESOLVED"
    assert out["mae_pct"] < -45.0  # the fabricated catastrophic value


def test_a_candidate_outside_the_outcome_window_does_not_block_resolution():
    """The guard must not be overzealous: a decision whose entire outcome
    window sits safely before the gap (or a different symbol's gap) must
    still resolve normally."""
    store, sessions = _build_store_with_a_real_unconfirmed_gap(gap_index=35)
    candidates = scan_store_for_splits(store)
    backlog = unconfirmed_candidate_sessions(candidates, confirmed=[])

    decision = sessions[10]
    event = _event("GAPCO", decision)
    future_sessions = sessions[11:16]
    closes = [200.0, 201.0, 202.0, 201.5, 203.0]
    future = {
        "GAPCO": {
            "sessions": future_sessions,
            "opens": closes,
            "highs": [c + 0.5 for c in closes],
            "lows": [c - 0.5 for c in closes],
            "closes": closes,
        }
    }
    out = attach_outcomes(
        [event], future, horizon=4, unconfirmed_ca_sessions=backlog,
    )[0].outcome_labels
    assert out["status"] == "RESOLVED"


def test_no_backlog_supplied_is_a_noop():
    """Omitting unconfirmed_ca_sessions entirely must not change existing
    behaviour -- it does not invent a backlog on its own."""
    store, sessions = _build_store_with_a_real_unconfirmed_gap(gap_index=35)
    decision = sessions[30]
    event = _event("GAPCO", decision)
    future_sessions = sessions[31:40]
    closes = [200.0] * 4 + [100.0] * 5
    future = {
        "GAPCO": {
            "sessions": future_sessions,
            "opens": closes,
            "highs": [c + 0.5 for c in closes],
            "lows": [c - 0.5 for c in closes],
            "closes": closes,
        }
    }
    out = attach_outcomes([event], future, horizon=9)[0].outcome_labels
    assert out["status"] == "RESOLVED"
