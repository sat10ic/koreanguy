"""Participation-engine tests (manual P1.4): exclusive prior windows,
warm-up honesty, delivery reconstruction rule — expectations hand-computed."""
import pytest

from unidesk.contracts.base import ContractError
from unidesk.momentum.features.participation import (
    delivery_volume, delivery_volume_ratio, rvol,
)


def test_rvol_uses_exclusive_prior_window():
    vols = [100.0] * 21 + [200.0]
    out = rvol(vols, span=20)
    assert out[:20] == [None] * 20          # window needs 20 PRIOR values
    assert out[20] == 1.0                   # priors 0..19 all 100, today 100
    assert out[21] == pytest.approx(2.0)    # today 200 vs prior mean 100


def test_rvol_baseline_unaffected_by_today_volume():
    """The exclusive-window property: today's volume changes the ratio, never
    the baseline of earlier indices."""
    a = rvol([100.0] * 21 + [150.0], span=20)
    b = rvol([100.0] * 21 + [999.0], span=20)
    assert a[:21] == b[:21]
    assert a[21] != b[21]


def test_rvol_warmup_never_partial_baseline():
    vols = [100.0] * 5
    assert rvol(vols, span=20) == [None] * 5


def test_rvol_zero_baseline_is_none_not_error():
    vols = [0.0] * 20 + [100.0]
    assert rvol(vols, span=20)[20] is None


def test_delivery_volume_requires_both_inputs():
    vols = [1000.0, 1000.0, 1000.0]
    pcts = [50.0, None, 100.0]
    out = delivery_volume(vols, pcts)
    assert out[0] == 500.0
    assert out[1] is None                   # missing pct -> None, never volume-as-default
    assert out[2] == 1000.0
    with pytest.raises(ContractError):
        delivery_volume(vols, [50.0, 101.0, 0.0])  # out of range rejected


def test_delivery_ratio_requires_full_prior_window():
    vols = [1000.0] * 22
    pcts = [50.0] * 21 + [None]             # today missing -> ratio None even with full window
    out = delivery_volume_ratio(vols, pcts, span=20)
    assert out[20] == 1.0                   # priors 0..19 all 500, today 500
    assert out[21] is None                  # today has no delivery data


def test_delivery_ratio_one_missing_prior_day_disables():
    vols = [1000.0] * 23
    pcts = [50.0] * 23
    pcts[1] = None                          # hole at day 1
    out = delivery_volume_ratio(vols, pcts, span=20)
    assert out[20] is None                  # prior window [0..20) contains day 1
    assert out[21] is None                  # prior window [1..21) contains day 1
    assert out[22] == 1.0                   # prior window [2..22) is finally clean


def test_delivery_ratio_computed_hand_checked():
    vols = [1000.0] * 21 + [2000.0]
    pcts = [40.0] * 21 + [50.0]
    out = delivery_volume_ratio(vols, pcts, span=20)
    assert out[21] == pytest.approx(1000.0 / 400.0)  # today dv 1000 vs prior mean 400
