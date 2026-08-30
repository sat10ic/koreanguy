"""ADR/ATR tests (manual P1.5): hand-computed expectations, Wilder seed
verified by a second route, warm-up honesty, exclusive prior windows."""
import pytest

from unidesk.contracts.base import ContractError
from unidesk.momentum.features.adr_atr import adr, atr, atr_pct, today_move_adr, true_ranges


def test_adr_exclusive_prior_window_hand_computed():
    # ranges: days 0..3 are 2,2,2,2; days 4..5 are 8,8
    highs = [11, 11, 11, 11, 15, 15]
    lows = [9, 9, 9, 9, 7, 7]
    out = adr(highs, lows, span=4)
    assert out[:4] == [None] * 4              # 4-prior window not full before index 4
    assert out[4] == pytest.approx(2.0)       # window days 0..3
    assert out[5] == pytest.approx(3.5)       # window days 1..4 = (2+2+2+8)/4 — day 5 excluded from its own ADR


def test_true_range_picks_widest_gap():
    h = [12, 13]
    l = [10, 11]
    c = [11, 12.5]
    tr = true_ranges(h, l, c)
    assert tr[0] is None                       # no prior close, never invented
    assert tr[1] == pytest.approx(2.0)         # max(2, |13-11|, |11-11|) = 2


def test_atr_wilder_seed_second_route():
    # constant ranges 2 with closes equal to lows: every TR = 2
    n = 20
    highs = [12.0] * n
    lows = [10.0] * n
    closes = [10.0] * n
    out = atr(highs, lows, closes, span=14)
    assert out[:13] == [None] * 12 + [None]    # seed lands at index 14
    assert out[14] == pytest.approx(2.0)       # SMA of 14 TRs, each 2
    assert all(v == pytest.approx(2.0) for v in out[14:])


def test_atr_seed_index_is_span():
    highs = [12.0, 13, 12, 13, 12, 13, 12, 13, 12, 13, 12, 13, 12, 13, 12, 13, 12]
    lows = [10.0] * len(highs)
    closes = [11.0] * len(highs)
    out = atr(highs, lows, closes, span=14)
    for i in range(14):
        assert out[i] is None
    assert out[14] is not None


def test_atr_pct_and_today_move_adr():
    highs = [12.0] * 16
    lows = [10.0] * 16
    closes = [10.0] * 15 + [12.0]
    a = atr(highs, lows, closes, span=14)
    p = atr_pct(a, closes)
    assert p[14] == pytest.approx(20.0)        # 2/10 * 100
    mv = today_move_adr(closes, a)
    assert mv[:14] == [None] * 14              # needs prior close + adr (warm-up)
    assert mv[14] == 0.0                       # real zero: flat day with valid ADR
    assert mv[15] == pytest.approx(1.0)        # (12-10)/2


def test_adr_rejects_negative_range():
    with pytest.raises(ContractError):
        adr([10.0, 10.0], [11.0, 9.0], span=1)
