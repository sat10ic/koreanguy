"""Pivot/contraction/detector tests: known_at confirmation lag (the manual's
P2.1 acceptance), hand-computed windows, rule-composition paths."""
import pytest

from unidesk.contracts.base import ContractError
from unidesk.momentum.detectors.momentum_burst import BurstRules, Detection, momentum_burst
from unidesk.momentum.primitives.contraction import (
    base_depth_pct, range_contraction_ratio, volume_dryup_ratio,
)
from unidesk.momentum.primitives.pivots import PivotKind, fractal_pivots, pivots_known_at


def test_pivot_highs_and_lows_with_confirmation_lag():
    highs = [10, 11, 12, 11, 10]          # pivot HIGH at index 2 (k=1)
    lows = [9, 8.5, 9, 8.5, 9]
    pivots = fractal_pivots(highs, lows, k=1)
    kinds = {(p.index, p.kind) for p in pivots}
    assert (2, PivotKind.HIGH) in kinds
    assert (1, PivotKind.LOW) in kinds and (3, PivotKind.LOW) in kinds
    for p in pivots:
        assert p.known_at == p.index + 1   # confirmed one bar later, recorded


def test_pivot_not_visible_before_known_at():
    highs = [10, 11, 12, 11, 10, 9, 8]
    lows = [8] * 7
    pivots = fractal_pivots(highs, lows, k=2)
    high2 = next(p for p in pivots if p.kind is PivotKind.HIGH)
    assert high2.known_at == 4
    assert high2 not in pivots_known_at(pivots, 3)   # future-confirmed: invisible
    assert high2 in pivots_known_at(pivots, 4)       # visible from its known_at


def test_ties_reject_pivots_deterministically():
    highs = [10, 12, 12, 12, 10]          # equal highs: no strict max
    lows = [9, 8, 8, 8, 9]
    pivots = fractal_pivots(highs, lows, k=1)
    assert all(p.kind is PivotKind.LOW for p in pivots)


def test_k_must_be_positive():
    with pytest.raises(ContractError):
        fractal_pivots([1], [1], k=0)


def test_base_depth_pct_hand_computed():
    highs = [110, 112, 111]
    lows = [100, 99, 100]
    assert base_depth_pct(highs, lows, 0, 3) == pytest.approx((112 - 99) / 99 * 100)
    with pytest.raises(ContractError):
        base_depth_pct(highs, lows, 0, 1)   # window too short


def test_range_contraction_ratio_hand_computed():
    # prior 2 days range 4 each; recent 2 days range 2 each
    highs = [12, 12, 11, 11]
    lows = [8, 8, 9, 9]
    assert range_contraction_ratio(highs, lows, recent_n=2, prior_n=2) == pytest.approx(0.5)


def test_volume_dryup_ratio_and_short_series():
    vols = [1000] * 4 + [250] * 2
    assert volume_dryup_ratio(vols, recent_n=2, prior_n=4) == pytest.approx(0.25)
    # warm-up honesty: a window that cannot fill is None, never an error
    assert volume_dryup_ratio([100.0], recent_n=2, prior_n=2) is None


def test_momentum_burst_paths():
    rules = BurstRules()
    valid = momentum_burst(adr_pct=4.0, rs_rank=90.0, rvol=2.0,
                           contraction_ratio=0.6, avwap_extension_adr=1.0, rules=rules)
    assert valid.detection is Detection.VALID and valid.rule_failures == ()

    invalid = momentum_burst(adr_pct=2.0, rs_rank=50.0, rvol=1.0,
                             contraction_ratio=1.2, avwap_extension_adr=5.0, rules=rules)
    assert invalid.detection is Detection.INVALID
    assert len(invalid.rule_failures) == 5   # every rule failed, all named

    insufficient = momentum_burst(adr_pct=None, rs_rank=90.0, rvol=2.0,
                                  contraction_ratio=0.6, avwap_extension_adr=None, rules=rules)
    assert insufficient.detection is Detection.INSUFFICIENT_DATA
    assert insufficient.rule_failures == ("missing:adr_pct",)


def test_avwap_extension_absent_is_lenient():
    d = momentum_burst(adr_pct=4.0, rs_rank=90.0, rvol=2.0,
                       contraction_ratio=0.6, avwap_extension_adr=None)
    assert d.detection is Detection.VALID
