"""G-2 — levels.py tests (HANDOFF_2026-09-04_STRUCTURAL_LEVELS_KDE §1-§2).

The no-lookahead test is the one that matters: a pivot at bar *i* must be
invisible at ``as_of_index = i + right - 1`` and visible at ``i + right``.
"""
from __future__ import annotations

import pytest

from unidesk.contracts.base import ContractError
from unidesk.momentum.features.levels import (
    Level, confirmed_pivots, level_density, nearest_above, nearest_below,
    structural_levels,
)

LEFT, RIGHT = 10, 5


def _zigzag(pivots_at: dict[int, float], n: int, base: float = 90.0):
    """Fixture: the listed indices carry a swing whose HIGH (for highs) and
    LOW (for lows) equal the given price; every other bar is flat at
    ``base`` (high) / ``base - 1`` (low). Flat plateaus produce NO pivots —
    the strict-both-sides rule is what the fixture also tests."""
    highs, lows = [], []
    for i in range(n):
        v = pivots_at.get(i, base)
        highs.append(v)
        lows.append(v - 1.0)
    return highs, lows


# ---------------------------------------------------------------- no-lookahead

def test_pivot_invisible_before_confirmation_visible_after():
    highs, lows = _zigzag({10: 100.0}, 20)
    before = confirmed_pivots(highs, lows, left=LEFT, right=RIGHT, as_of_index=14)
    at = confirmed_pivots(highs, lows, left=LEFT, right=RIGHT, as_of_index=15)
    assert all(p.index != 10 for p in before), "pivot leaked before i + right"
    assert any(p.index == 10 for p in at), "confirmed pivot missing at i + right"
    p10 = next(p for p in at if p.index == 10)
    assert p10.price == 100.0 and p10.kind == "HIGH"


def test_no_lookahead_under_truncation():
    """Truncated series (as-of = cut) must reproduce the full-series pivots
    with as_of_index = cut — identical, no future reads in either direction."""
    pivots_at = {10: 100.0, 21: 100.0, 32: 100.0, 43: 100.0}
    highs, lows = _zigzag(pivots_at, 55)
    for cut in (16, 27, 38, 49, 55):
        truncated = confirmed_pivots(highs[:cut], lows[:cut],
                                     left=LEFT, right=RIGHT, as_of_index=cut)
        from_full = confirmed_pivots(highs, lows, left=LEFT, right=RIGHT, as_of_index=cut)
        assert truncated == from_full, f"prefix/full mismatch at cut={cut}"


def test_flat_plateaus_produce_no_pivots():
    """Strict-both-sides means a flat series has no pivots at all — ties are
    not swings. This is what keeps the base of a fixture quiet."""
    highs, lows = _zigzag({}, 30, base=90.0)
    assert confirmed_pivots(highs, lows, left=LEFT, right=RIGHT, as_of_index=30) == []


# ---------------------------------------------------------------- warm-up

def test_warmup_refuses_below_min_pivots():
    # only 3 confirmed pivots — the frozen MIN_PIVOTS (8) refuses: None
    highs, lows = _zigzag({10: 100.0, 21: 100.0, 32: 100.0}, 45)
    assert structural_levels(highs, lows, list(highs), atr=2.0,
                             left=LEFT, right=RIGHT, as_of_index=45) is None
    # the hand-built §1 acceptance fixture unlocks with an explicit override
    levels = structural_levels(highs, lows, list(highs), atr=2.0,
                               left=LEFT, right=RIGHT, as_of_index=45, min_pivots=3)
    assert levels is not None
    hundred = next(lv for lv in levels if abs(lv.price - 100.0) <= 1.0)
    assert hundred.n_supporting_pivots == 3


# ---------------------------------------------------------------- §1 acceptance

def test_hand_built_cluster_acceptance():
    """Three pivots at 100.0 + outlier at 130.0 (+ five far pivots at 60 to
    clear MIN_PIVOTS): the 100-cluster carries n_supporting_pivots == 3 and
    outranks the lone 130 outlier."""
    pivots_at = {10: 100.0, 21: 100.0, 32: 100.0, 45: 130.0,
                 56: 60.0, 67: 60.0, 78: 60.0, 89: 60.0, 100: 60.0}
    n = 110
    highs, lows = _zigzag(pivots_at, n)
    levels = structural_levels(highs, lows, list(highs), atr=5.0,
                               left=LEFT, right=RIGHT, as_of_index=n, min_pivots=3)
    assert levels is not None
    hundred = next((lv for lv in levels if abs(lv.price - 100.0) <= 1.0), None)
    outlier = next((lv for lv in levels if abs(lv.price - 130.0) <= 1.0), None)
    sixty = next((lv for lv in levels if abs(lv.price - 59.0) <= 1.0), None)
    assert hundred is not None, "100.0 cluster missing"
    assert hundred.n_supporting_pivots == 3
    assert outlier is not None and outlier.n_supporting_pivots == 1
    assert levels.index(hundred) < levels.index(outlier), "cluster must outrank the lone outlier"


# ---------------------------------------------------------------- determinism / separation / errors

def test_deterministic():
    pivots_at = {10: 100.0, 21: 100.0, 32: 100.0, 45: 130.0,
                 56: 60.0, 67: 60.0, 78: 60.0, 89: 60.0, 100: 60.0}
    highs, lows = _zigzag(pivots_at, 125)
    kwargs = dict(atr=5.0, left=LEFT, right=RIGHT, as_of_index=125, min_pivots=3)
    a = structural_levels(highs, lows, list(highs), **kwargs)
    b = structural_levels(highs, lows, list(highs), **kwargs)
    assert a == b


def test_separation_honoured():
    pivots_at = {10: 100.0, 21: 100.0, 32: 100.0, 45: 130.0,
                 56: 60.0, 67: 60.0, 78: 60.0, 89: 60.0, 100: 60.0}
    highs, lows = _zigzag(pivots_at, 125)
    levels = structural_levels(highs, lows, list(highs), atr=5.0,
                               left=LEFT, right=RIGHT, as_of_index=125, min_pivots=3)
    assert levels is not None
    for i in range(len(levels) - 1):
        for j in range(i + 1, len(levels)):
            assert abs(levels[i].price - levels[j].price) >= 1.5 * 5.0


def test_bad_input_raises():
    with pytest.raises(ContractError):
        confirmed_pivots([100.0], [100.0, 101.0], left=10, right=5, as_of_index=1)
    with pytest.raises(ContractError):
        confirmed_pivots([100.0] * 20, [99.0] * 20, left=0, right=5, as_of_index=20)
    with pytest.raises(ContractError):
        structural_levels([100.0] * 40, [99.0] * 40, [100.0] * 40, atr=0.0,
                          as_of_index=40, min_pivots=3)


def test_nearest_below_and_above():
    below = Level(price=100.0, density=3.0, n_supporting_pivots=3, kind="HIGH")
    above = Level(price=130.0, density=1.0, n_supporting_pivots=1, kind="HIGH")
    levels = [below, above]
    assert nearest_below(levels, 110.0) is below
    assert nearest_above(levels, 110.0) is above
    assert nearest_below(levels, 100.0) is None   # strictly below
    assert nearest_above(levels, 130.0) is None   # strictly above


def test_level_density_triangular_kernel_skips_zero_range():
    from unidesk.momentum.features.levels import Pivot
    pivots = [Pivot(0, 100.0, 1.0, "HIGH"), Pivot(1, 100.0, 0.0, "HIGH")]
    grid = [99.0, 99.5, 100.0, 100.5, 101.0]
    d = level_density(pivots, grid)
    assert d[2] == pytest.approx(1.0)          # kernel peak of the range-1 pivot
    assert d[0] == 0.0 and d[4] == 0.0          # beyond the half-width
    assert d[1] == pytest.approx(0.5)           # zero-range pivot contributed nothing
