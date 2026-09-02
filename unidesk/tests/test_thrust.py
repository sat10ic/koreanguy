"""ADRMAX / ChopScore contracts (clean-room; see thrust.py for provenance)."""
import pytest

from unidesk.contracts.base import ContractError
from unidesk.momentum.features.thrust import (
    ADRMAX_MIN_BULLISH_BARS, adr_max, chop_band, chop_score, stop_in_thrust_days,
)


def _bars(n, *, bullish=True, rng=10.0, low=100.0):
    """n identical bars; bullish => close > open."""
    opens, highs, lows, closes = [], [], [], []
    for _ in range(n):
        lows.append(low)
        highs.append(low + rng)
        if bullish:
            opens.append(low + 1.0); closes.append(low + rng - 1.0)
        else:
            opens.append(low + rng - 1.0); closes.append(low + 1.0)
    return opens, highs, lows, closes


# --------------------------- ADRMAX ---------------------------

def test_adrmax_is_pct_of_low_on_uniform_bullish_bars():
    o, h, l, c = _bars(70, rng=10.0, low=100.0)
    # every bullish bar has range 10 on a low of 100 => 10%
    assert adr_max(h, l, o, c, lookback=60) == pytest.approx(10.0)


def test_adrmax_averages_only_the_top_slice():
    # 60 bars: 10 wide (20%), 50 narrow (5%). top 25% of 60 bullish = 15 bars,
    # so the mean is (10 wide + 5 narrow) / 15.
    o, h, l, c = [], [], [], []
    for i in range(61):
        low = 100.0
        wide = i < 10
        rng = 20.0 if wide else 5.0
        l.append(low); h.append(low + rng); o.append(low + 0.5); c.append(low + rng - 0.5)
    got = adr_max(h, l, o, c, lookback=60, top_pct=0.25)
    expected = (10 * 20.0 + 5 * 5.0) / 15
    assert got == pytest.approx(expected)


def test_adrmax_matches_the_authors_worked_example_count():
    """Author (@selfunmade): 250 lookback, 50% green => 125 green candles;
    15% of 125 = 18.75 -> rounded to 19 candles averaged.

    Pins two things that are easy to get wrong: the percentage applies to the
    GREEN count (not the lookback), and the count is ROUNDED (not truncated).
    Built so the top 19 are identifiable: 19 bars at 20%, the rest at 5%.
    """
    o, h, l, c = [], [], [], []
    green_made = 0
    for i in range(251):
        low = 100.0
        make_green = i % 2 == 0 and green_made < 125     # exactly 125 green
        if make_green:
            green_made += 1
            rng = 20.0 if green_made <= 19 else 5.0
            l.append(low); h.append(low + rng)
            o.append(low + 0.5); c.append(low + rng - 0.5)   # bullish
        else:
            l.append(low); h.append(low + 5.0)
            o.append(low + 4.5); c.append(low + 0.5)         # bearish
    got = adr_max(h, l, o, c, lookback=250, top_pct=0.15)
    # 19 candles all at 20% => mean 20%
    assert got == pytest.approx(20.0)


def test_adrmax_ignores_bearish_bars():
    """The whole point: it measures UPSIDE thrust."""
    o, h, l, c = _bars(70, bullish=False, rng=10.0)
    assert adr_max(h, l, o, c, lookback=60) is None   # no bullish bars at all


def test_adrmax_refuses_below_the_bullish_bar_floor():
    o, h, l, c = _bars(70, bullish=False)
    # make exactly one fewer than the floor bullish
    for i in range(ADRMAX_MIN_BULLISH_BARS - 1):
        o[i], c[i] = c[i], o[i]
    assert adr_max(h, l, o, c, lookback=60) is None


def test_adrmax_excludes_the_current_bar_no_lookahead():
    """A monster final bar must not change a value computed before it."""
    o, h, l, c = _bars(70, rng=10.0, low=100.0)
    base = adr_max(h, l, o, c, lookback=60)
    h[-1] = 900.0                      # today explodes
    c[-1] = 890.0
    assert adr_max(h, l, o, c, lookback=60) == pytest.approx(base)


def test_adrmax_none_before_the_window_fills():
    o, h, l, c = _bars(10)
    assert adr_max(h, l, o, c, lookback=60) is None


def test_adrmax_rejects_bad_parameters():
    o, h, l, c = _bars(70)
    with pytest.raises(ContractError):
        adr_max(h, l, o, c, lookback=0)
    with pytest.raises(ContractError):
        adr_max(h, l, o, c, top_pct=0.0)
    with pytest.raises(ContractError):
        adr_max(h, l, o, c, top_pct=1.5)


# --------------------------- ChopScore ---------------------------

def test_chop_score_zero_when_every_bar_closes_at_its_extreme():
    """Full-body bars = maximally decisive = least choppy."""
    o, h, l, c = [], [], [], []
    for _ in range(30):
        o.append(100.0); l.append(100.0); h.append(110.0); c.append(110.0)
    assert chop_score(o, h, l, c, lookback=20) == pytest.approx(0.0)


def test_chop_score_maximal_when_bars_close_where_they_opened():
    """Wide range, no net movement = pure churn."""
    o, h, l, c = [], [], [], []
    for _ in range(30):
        o.append(105.0); c.append(105.0); l.append(100.0); h.append(110.0)
    assert chop_score(o, h, l, c, lookback=20) == pytest.approx(100.0)


def test_chop_score_excludes_the_current_bar():
    o, h, l, c = [], [], [], []
    for _ in range(30):
        o.append(100.0); l.append(100.0); h.append(110.0); c.append(110.0)
    base = chop_score(o, h, l, c, lookback=20)
    o[-1], c[-1] = 105.0, 105.0        # today is pure churn
    assert chop_score(o, h, l, c, lookback=20) == pytest.approx(base)


def test_chop_score_none_before_warmup():
    o, h, l, c = _bars(5)
    assert chop_score(o, h, l, c, lookback=20) is None


def test_chop_band_never_guesses_on_none():
    assert chop_band(None) is None
    assert chop_band(40.0) == "CLEAN"
    assert chop_band(70.0) == "VERY_CHOPPY"


# --------------------------- reachability ---------------------------

def test_stop_in_thrust_days_matches_hand_computation():
    # stop 10% away, thrust 5% => 2 thrust-days of risk
    assert stop_in_thrust_days(100.0, 90.0, 5.0) == pytest.approx(2.0)


def test_stop_in_thrust_days_fails_closed_on_missing_inputs():
    assert stop_in_thrust_days(None, 90.0, 5.0) is None
    assert stop_in_thrust_days(100.0, None, 5.0) is None
    assert stop_in_thrust_days(100.0, 90.0, None) is None
    assert stop_in_thrust_days(100.0, 100.0, 5.0) is None   # non-positive risk
    assert stop_in_thrust_days(100.0, 90.0, 0.0) is None
