"""P7.2 outcome-label tests: hand-computed MFE/MAE/R-multiples, first-touch
stop honesty, breakout hold/fail including the unresolved state."""
import pytest

from unidesk.contracts.base import ContractError
from unidesk.research.labels import breakout_hold, long_outcome


def test_stop_touch_fails_closed_even_when_later_ohlc_shows_a_large_mfe():
    # entry 100, stop 95 (risk 5). The same OHLC bar reaches high 110
    # (+10%) and low 93 (-7%). Intrabar ordering is unknowable, so a research
    # label must not claim a captured +2R after observing a stop touch.
    o = long_outcome(entry=100.0, stop=95.0, highs=[110.0], lows=[93.0], horizon=3)
    assert o.mfe_pct == pytest.approx(10.0)
    assert o.mae_pct == pytest.approx(-7.0)
    assert o.stop_hit is True
    assert o.potential_r_multiple == pytest.approx(2.0)
    assert o.r_multiple == pytest.approx(-1.0)
    assert not o.attained_1r and not o.attained_2r and not o.attained_3r


def test_horizon_slices_future():
    highs = [101.0, 110.0, 999.0]
    lows = [99.0, 99.0, 1.0]
    o = long_outcome(entry=100.0, stop=95.0, highs=highs, lows=lows, horizon=2)
    assert o.mfe_pct == pytest.approx(10.0)       # third bar excluded by horizon
    assert o.stop_hit is False


def test_flat_day_real_zero_mfe():
    o = long_outcome(entry=100.0, stop=95.0, highs=[100.0], lows=[100.0], horizon=1)
    assert o.mfe_pct == 0.0 and o.mae_pct == 0.0  # real zeros, not warm-up Nones
    assert o.r_multiple == 0.0 and not o.attained_1r


def test_stop_and_invariants():
    with pytest.raises(ContractError):
        long_outcome(entry=100.0, stop=105.0, highs=[110.0], lows=[95.0], horizon=1)
    with pytest.raises(ContractError):
        long_outcome(entry=100.0, stop=95.0, highs=[], lows=[], horizon=0)


def test_breakout_hold_fail_and_unresolved():
    assert breakout_hold([102.0, 103.0, 104.0], trigger=101.0, min_sessions=3) == (True, ())
    assert breakout_hold([102.0, 100.0, 104.0], trigger=101.0, min_sessions=3) == (
        False, ("closed_back_below_trigger",))
    assert breakout_hold([100.0, 103.0], trigger=101.0, min_sessions=3)[0] is False  # never cleared
    state, reasons = breakout_hold([102.0, 103.0], trigger=101.0, min_sessions=3)
    assert state is None and reasons == ("insufficient_sessions",)   # honestly undecided
