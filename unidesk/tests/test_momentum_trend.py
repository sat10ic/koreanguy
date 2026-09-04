"""Trend-engine tests: frozen definitions, warm-up honesty, and the
no-look-ahead property (output[i] depends only on values[:i+1])."""
import math
from datetime import datetime, timezone

import pytest

from unidesk.contracts.base import ContractError
from unidesk.momentum.features.trend import (
    TrendState, ema, ema_rising, ema_slope_pct, price_vs_ema_pct, trend_state,
)


def closes():
    return [10, 10.5, 10.2, 10.8, 11.0, 10.9, 11.4, 11.8, 11.6, 12.0, 12.2, 11.9, 12.4, 12.8]


def test_ema_warmup_is_none_then_sma_seeded():
    out = ema(closes(), span=4)
    assert out[:3] == [None, None, None]
    assert out[3] == pytest.approx(sum(closes()[:4]) / 4)


def test_ema_no_lookahead_truncation_property():
    full = ema(closes(), span=4)
    for cut in (5, 8, 11):
        prefix = ema(closes()[:cut], span=4)
        assert prefix == full[:cut], f"look-ahead leak at cut={cut}"


def test_ema_converges_to_constant():
    out = ema([7.5] * 30, span=5)
    assert all(v is not None for v in out[4:])
    assert all(math.isclose(v, 7.5, rel_tol=1e-12) for v in out[4:])


def test_ema_span_one_is_identity_and_rejects_zero():
    series = closes()
    assert ema(series, span=1) == [float(v) for v in series]
    with pytest.raises(ContractError):
        ema(series, span=0)


def test_ema_rejects_none_inputs():
    with pytest.raises(ContractError):
        ema([1.0, None, 3.0], span=2)


def test_slope_and_price_vs_ema_hand_computed():
    series = [100.0] * 6 + [101.0, 102.0]
    e = ema(series, span=4)
    s = ema_slope_pct(e, lookback=2)
    assert s[:5] == [None] * 5
    # at i=6: e[6] vs e[4]=100 -> (e[6]/100-1)*100
    assert s[6] == pytest.approx((e[6] / 100.0 - 1) * 100)
    assert price_vs_ema_pct(110.0, 100.0) == pytest.approx(10.0)
    assert price_vs_ema_pct(110.0, None) is None
    assert price_vs_ema_pct(110.0, 0.0) is None


def test_trend_state_classification_table():
    assert trend_state(12.0, 11.5, 11.0, ema21_rising=True) is TrendState.STRONG_UPTREND
    assert trend_state(12.0, 11.5, 11.0, ema21_rising=False) is TrendState.UPTREND
    assert trend_state(10.8, 11.5, 11.0, ema21_rising=True) is TrendState.TRANSITION  # close under ema50, ema21 above
    assert trend_state(10.5, 11.0, 11.5, ema21_rising=False) is TrendState.WEAK
    assert trend_state(10.5, None, None, ema21_rising=False) is TrendState.UNKNOWN


def test_ema_rising_never_invents_warmup_direction():
    e = ema(closes(), span=4)
    assert ema_rising(e, 3) is False        # j = -2 → no direction invented
    assert ema_rising(e, 8) is True         # series trends up
    assert ema_rising([None] * 6 + [1.0, 1.1], 6) is False
