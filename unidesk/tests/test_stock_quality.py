"""P1.9 acceptance: decomposable score, nulls reduce coverage (never zeros),
per-feature disablement, hard gates, insufficient-data honesty."""
from datetime import datetime, timezone

import pytest

from unidesk.contracts.base import ContractError
from unidesk.momentum.features.circuit import CircuitRiskState
from unidesk.momentum.features.trend import TrendState
from unidesk.momentum.scoring.stock_quality import stock_quality_snapshot

UTC = timezone.utc
T0 = datetime(2026, 8, 28, 9, 45, tzinfo=UTC)

WEIGHTS = {"trend": 20, "rs_rank": 20, "rvol": 15, "delivery_ratio": 15,
           "room_to_52w_high": 15, "circuit_safety": 15}


def snap(**over):
    base = dict(
        symbol="TRENT", as_of=T0, weights=WEIGHTS,
        trend_state=TrendState.STRONG_UPTREND, rs_rank=95.0, rvol=2.0,
        delivery_ratio=2.0, distance_52w_high_pct=-4.0,
        circuit_state=CircuitRiskState.NONE,
        feature_version="fv1", config_hash="cfg1",
    )
    base.update(over)
    return stock_quality_snapshot(**base)


def test_score_is_the_weighted_mean_of_available_contributors():
    s = snap()
    # all available: trend 100, rs 95, rvol 100, delivery 100, room (1-4/25)*100=84, circuit 100
    expect = (20*100 + 20*95 + 15*100 + 15*100 + 15*84 + 15*100) / 100
    assert s.score == pytest.approx(expect, abs=0.01)
    assert s.coverage == 1.0
    assert s.unknowns == () and s.hard_gates == ()


def test_missing_inputs_reduce_coverage_never_zeroed():
    s = snap(rvol=None, delivery_ratio=None)   # 30 of 100 weight unavailable
    assert s.coverage == pytest.approx(0.70)
    assert "RVOL_UNAVAILABLE" in s.unknowns and "DELIVERY_RATIO_UNAVAILABLE" in s.unknowns
    # score over remaining contributors only — rvol contributor absent, not 0
    c = s.contributor("rvol")
    assert c.available is False and c.normalized is None
    expect = (20*100 + 20*95 + 15*84 + 15*100) / 70
    assert s.score == pytest.approx(expect, abs=0.01)


def test_insufficient_coverage_yields_none_with_reason():
    s = snap(rs_rank=None, rvol=None, delivery_ratio=None, distance_52w_high_pct=None)
    assert s.coverage == pytest.approx(0.35)
    assert s.score is None
    assert "INSUFFICIENT_DATA" in s.unknowns


def test_contributor_disableable_via_zero_weight():
    w = dict(WEIGHTS, delivery_ratio=0)                     # R15: flag = config change
    s = snap(weights=w, delivery_ratio=2.0)
    assert s.contributor("delivery_ratio") is None          # absent from the math entirely
    full = snap()
    w2 = dict(WEIGHTS)
    w2.pop("delivery_ratio")
    assert s.score == snap(weights=w2).score


def test_circuit_uc_risk_is_score_zero_and_hard_gate():
    s = snap(circuit_state=CircuitRiskState.UC_RISK)
    assert "CIRCUIT_UC_RISK" in s.hard_gates
    assert s.contributor("circuit_safety").normalized == 0.0


def test_circuit_unknown_is_unavailable_not_zero():
    s = snap(circuit_state=CircuitRiskState.UNKNOWN)
    assert "CIRCUIT_BANDS_NOT_PUBLISHED" in s.unknowns
    assert s.contributor("circuit_safety").available is False


def test_versions_and_hashes_mandatory():
    with pytest.raises(ContractError):
        snap(feature_version="")
    with pytest.raises(ContractError):
        snap(config_hash="")


def test_unknown_weight_names_rejected():
    with pytest.raises(ContractError):
        snap(weights=dict(WEIGHTS, vibes=50))


def test_trend_unknown_is_unavailable_never_crash():
    """Regression (found on real data): symbols with warm-up EMA history
    carry TrendState.UNKNOWN; the snapshot must treat it as an unavailable
    contributor — coverage-reducing, never a crash, never a zero."""
    s = snap(trend_state=TrendState.UNKNOWN)
    assert s.contributor("trend").available is False
    assert "TREND_STATE_UNAVAILABLE" in s.unknowns
