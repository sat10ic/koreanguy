"""Tests for unidesk/research/significance.py (R-01 DSR + block bootstrap,
R-02 arm comparison, R-03 metric suite, A-05 promotion rule).

Every input is a hand-checkable deterministic series; no randomness except
inside the bootstrap (seeded)."""
from __future__ import annotations

import math

import pytest

from unidesk.contracts.base import ContractError
from unidesk.research.significance import (
    block_bootstrap_ci, compare_arms, deflated_sharpe_ratio, metric_suite,
    promotion_rule, PromotionInput, sharpe,
)


def test_metric_suite_known_values():
    # 10 bps, -10 bps, 30 bps, -5 bps -> mean 6.25, hit rate 0.5
    s = metric_suite([10.0, -10.0, 30.0, -5.0])
    assert s.n == 4
    assert s.expectancy == pytest.approx(6.25, abs=1e-6)
    assert s.hit_rate == pytest.approx(0.5, abs=1e-9)
    assert s.max_drawdown < 0  # the -10 leg draws down from the +10 peak
    assert len(s.pnl_curve) == 4
    # compounding: 1.001 * 0.999 * 1.003 * 0.9995
    expected = 1.001 * 0.999 * 1.003 * 0.9995 - 1
    assert s.total_return == pytest.approx(expected, abs=1e-6)


def test_metric_suite_needs_observations():
    with pytest.raises(ContractError):
        metric_suite([1.0, 2.0])


def test_sharpes_null_and_positive_series():
    assert sharpe([5.0, -5.0, 5.0, -5.0, 5.0, -5.0]) == pytest.approx(0.0, abs=1e-12)
    assert sharpe([10.0] * 20) == 0.0  # zero std -> 0.0, never inf/NaN


def test_dsr_null_signal_fails_as_trials_grow():
    # A "winner" drawn from pure noise: zero-mean alternating series.
    noise = [5.0, -4.0, 6.0, -5.0, 4.5, -6.0, 5.5, -4.5, 5.0, -5.5,
             4.0, -5.0, 6.5, -4.0, 5.5, -6.5, 4.5, -5.0, 5.0, -4.5]
    assert _mean_of(noise) == pytest.approx(0.4, abs=0.6)  # ~zero, slightly lucky
    dsr_lucky = deflated_sharpe_ratio(noise, n_trials=1)
    dsr_bestof8 = deflated_sharpe_ratio(noise, n_trials=8)
    assert 0.0 <= dsr_lucky <= 1.0
    # The same lucky series is discounted once you admit it was the best of 8 tries.
    assert dsr_bestof8 < dsr_lucky


def test_dsr_strong_signal_passes():
    # Consistently positive series: high DSR even with many trials.
    strong = [10.0 + (i % 3) for i in range(60)]
    assert deflated_sharpe_ratio(strong, n_trials=10) > 0.99


def test_block_bootstrap_ci_null_contains_zero():
    zero_mean = [3.0, -3.0] * 40
    lo, hi = block_bootstrap_ci(zero_mean, n_boot=400, block=5, seed=11)
    assert lo <= 0.0 <= hi


def test_block_bootstrap_ci_positive_excludes_zero():
    positive = [8.0 + (i % 4) for i in range(120)]
    lo, hi = block_bootstrap_ci(positive, n_boot=400, block=10, seed=11)
    assert lo > 0.0


def test_compare_arms_reports_coverage_per_arm():
    arms = {
        "champion": [5.0] * 100,
        "champion+L1.5": [7.0] * 90,   # 10 observations missing -> coverage 0.9
        "champion+L2": [1.0] * 40,
    }
    out = compare_arms(arms)
    assert set(out) == set(arms)
    assert out["champion"].coverage == pytest.approx(1.0)
    assert out["champion+L1.5"].coverage == pytest.approx(0.9)
    assert out["champion+L2"].coverage == pytest.approx(0.4)
    assert out["champion+L1.5"].expectancy == pytest.approx(7.0)
    # every figure carries its n (R-03)
    for arm in out.values():
        assert arm.n > 0


def test_promotion_rule_null_signal_fails():
    verdict = promotion_rule(PromotionInput(
        fold_beats=(True, False, False, True, False),   # 2/5 < 3
        returns=[2.0, -2.0] * 50,                       # zero-mean noise
        n_trials=12,
        expectancy_uplift=0.02,                         # below the 15% band
    ))
    assert verdict.classification == "NO EDGE"
    assert verdict.folds_won == 2
    assert not verdict.uplift_ok


def test_promotion_rule_strong_result_promotes():
    verdict = promotion_rule(PromotionInput(
        fold_beats=(True, True, True, True, False),     # 4/5
        returns=[6.0 + (i % 3) for i in range(200)],    # consistently positive
        n_trials=5,
        expectancy_uplift=0.25,
    ))
    assert verdict.classification in ("RANKER", "SNIPER FILTER")
    assert verdict.ci_excludes_zero
    assert verdict.dsr >= 0.90
    assert verdict.uplift_ok


def test_promotion_rule_requires_five_folds():
    with pytest.raises(ContractError):
        promotion_rule(PromotionInput(
            fold_beats=(True, True, True), returns=[1.0] * 30, n_trials=1,
            expectancy_uplift=0.5,
        ))


def _mean_of(xs):
    return sum(xs) / len(xs)
