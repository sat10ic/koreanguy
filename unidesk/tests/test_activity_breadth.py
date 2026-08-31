"""Tests for Reactor Scale activity score and breadth analytics."""
import pytest
from unidesk.momentum.features.activity import activity_score
from unidesk.momentum.features.breadth import (
    bo_bd_ratio, net_nh_nl, up_down_close_pct, volatility_ratio, volume_ratio,
)


class TestActivityScore:
    def test_normal_case(self):
        r = activity_score(
            volume=2e6, num_trades=8000, delivery_pct=60.0,
            prior_volumes=[1e6] * 25, prior_num_trades=[5000] * 25,
            prior_delivery_pcts=[50.0] * 25,
        )
        assert r is not None
        assert r["activity_score"] > 0
        assert r["q_ratio"] > 0
        assert r["d_ratio"] > 0

    def test_too_few_priors(self):
        r = activity_score(
            volume=1e6, num_trades=5000, delivery_pct=50.0,
            prior_volumes=[1e6] * 5, prior_num_trades=[5000] * 5,
            prior_delivery_pcts=[50.0] * 5,
        )
        assert r is None

    def test_zero_volume_returns_none(self):
        r = activity_score(
            volume=0, num_trades=0, delivery_pct=50.0,
            prior_volumes=[1e6] * 25, prior_num_trades=[5000] * 25,
            prior_delivery_pcts=[50.0] * 25,
        )
        assert r is None


class TestBreadthAnalytics:
    def test_net_nh_nl(self):
        counts = {"total_universe": 1000, "new_52wk_high": 50, "new_52wk_low": 20}
        assert net_nh_nl(counts) == pytest.approx(3.0)

    def test_volatility_ratio(self):
        counts = {"range_contraction": 200, "range_expansion": 50}
        assert volatility_ratio(counts) == pytest.approx(0.25)

    def test_volume_ratio(self):
        counts = {"high_vol": 100, "low_vol": 50}
        assert volume_ratio(counts) == pytest.approx(2.0)

    def test_bo_bd_ratio(self):
        counts = {"breakouts": 30, "breakdowns": 10}
        assert bo_bd_ratio(counts) == pytest.approx(3.0)

    def test_up_down_close_pct(self):
        counts = {"close_upper_half": 600, "close_lower_half": 400}
        assert up_down_close_pct(counts) == pytest.approx(150.0)

    def test_division_by_zero(self):
        assert net_nh_nl({"total_universe": 0}) is None
        assert volatility_ratio({"range_contraction": 0}) is None
        assert volume_ratio({"low_vol": 0}) is None
        assert bo_bd_ratio({"breakdowns": 0}) is None