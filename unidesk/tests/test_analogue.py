"""Tests for the L1.5 exploration prototype (research/analogue.py).

These verify the CONSTRAINTS (cosine-only, k legality, embargo, PIT
scaling, week concentration cap, null safety) on synthetic events with
known geometry — NOT any edge claim. No real outcome distribution is
asserted anywhere: the Phase 0 gate is open and results are not evidence.
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone

import pytest

from unidesk.contracts.base import ContractError
from unidesk.contracts.research import ResearchEvent
from unidesk.momentum.data.calendar import from_sessions
from unidesk.research.analogue import (
    ALLOWED_K, cosine_distance, flatten_vector, pit_rank, pit_scale,
)
from unidesk.research.leakage import embargo_overlapping_events


# ---- pure geometry -------------------------------------------------------

def test_cosine_distance_known_values():
    # 4 dims: MIN_SHARED_DIMS requires >= 4 shared dimensions
    a = {"a": 1.0, "b": 0.0, "c": 1.0, "d": 0.0}
    same = dict(a)
    perp = {"a": 0.0, "b": 1.0, "c": 0.0, "d": 1.0}
    assert cosine_distance(a, same) == pytest.approx(0.0)
    assert cosine_distance(a, perp) == pytest.approx(1.0)


def test_cosine_distance_needs_shared_dims():
    a = {"x": 1.0, "y": 2.0, "z": 3.0, "w": 4.0}
    b = {"x": 1.0}
    assert cosine_distance(a, b) is None  # 1 shared dim < MIN_SHARED_DIMS


def test_cosine_none_values_excluded_not_zeroed():
    # A None dim must be EXCLUDED from the computation, never treated as 0
    # (zero-filling would silently change the direction of the vector).
    a = {"x": 1.0, "y": 0.0, "z": None, "w": 1.0, "q": 2.0, "r": 0.5}
    b = {"x": 1.0, "y": 0.0, "z": 5.0, "w": 1.0, "q": 2.0, "r": 0.5}
    assert cosine_distance(a, b) == pytest.approx(0.0)


def test_flatten_vector_maps_n5_inputs():
    snap = {
        "rs_rank": 91.0,
        "adr_pct": 5.2,
        "n5_inputs": {
            "ep": {"gap_pct": 2.0, "close_loc": 0.8, "rvol": 3.1},
            "tight": {
                "base_episode": {"atrp_percentile": 42.0, "depth_pct": 12.5},
                "tightness": {"score": 66.0},
            },
        },
    }
    v = flatten_vector(snap, market_regime="BULL")
    assert v["gap_pct"] == 2.0
    assert v["close_loc"] == 0.8
    assert v["rvol"] == 3.1
    assert v["prior_atr_pct"] == 42.0
    assert v["S_ep"] == 66.0
    assert v["base_depth"] == 12.5
    assert v["rs"] == 91.0
    assert v["adr_pct"] == 5.2
    assert v["market_regime"] == 1.0


def test_flatten_vector_missing_stays_none():
    v = flatten_vector({}, market_regime=None)
    assert v["gap_pct"] is None
    assert v["market_regime"] is None  # regime absent -> None, never 0-as-fact


# ---- PIT scaling ----------------------------------------------------------

def test_pit_rank_basic():
    ref = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert pit_rank(3.0, ref) == pytest.approx(3 / 5)
    assert pit_rank(0.0, ref) == 0.0          # below every observation
    assert pit_rank(10.0, ref) == 1.0         # above every observation
    assert pit_rank(1.0, ref) == pytest.approx(1 / 5)


def test_pit_scale_ignores_none():
    out = pit_scale([{"x": 1.0, "y": None}, {"x": 2.0}])
    assert out["x"] == [1.0, 2.0]
    assert "y" not in out


# ---- embargo wiring (constitution §6, previously unwired) -----------------

def _cal(*sessions: date):
    return from_sessions(sorted(sessions))


def _ev(symbol, session, event_id=None):
    return ResearchEvent(
        event_id=event_id or f"{symbol}:{session.isoformat()}",
        candidate_id=event_id or f"{symbol}:{session.isoformat()}",
        symbol=symbol,
        timestamp=datetime(session.year, session.month, session.day, 18, 0, tzinfo=timezone.utc),
        snapshot={"close": 100.0}, config_hash="cfg",
        research_schema_version="research-event-v1",
    )


def test_embargo_excludes_same_symbol_neighbours():
    sessions = [date(2026, 1, 1) + timedelta(days=i) for i in range(120)]
    cal = _cal(*sessions)
    events = [
        _ev("AAA", sessions[0]),
        _ev("AAA", sessions[7]),    # 7 sessions later — inside the 60 embargo
        _ev("AAA", sessions[100]),  # far later — independent
        _ev("BBB", sessions[10]),   # different symbol — untouched
    ]
    kept, embargoed = embargo_overlapping_events(events, cal, window=60)
    kept_ids = {e.event_id for e in kept}
    assert "AAA:2026-01-01" in kept_ids
    assert "AAA:2026-01-08" not in kept_ids
    assert "BBB:2026-01-11" in kept_ids
    assert any(e.symbol == "AAA" for e, _s in embargoed)


# ---- k legality (constitution §10) ----------------------------------------

def test_k_is_25_or_50_only():
    from unidesk.research.analogue import ALLOWED_K
    assert ALLOWED_K == (25, 50)


def test_retrieve_rejects_illegal_k(tmp_path):
    from unidesk.research.analogue import retrieve
    cal = _cal(date(2026, 1, 5))
    q = _ev("AAA", date(2026, 1, 5))
    with pytest.raises(ContractError):
        retrieve(q, tmp_path, k=10, calendar=cal)


def test_allowed_k_values():
    assert ALLOWED_K == (25, 50)
