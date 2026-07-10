"""WAVE K K3 — unit tests for scanner/discovery_metrics.py (hand fixtures)."""
from manas_os.scanner import discovery_metrics as dm


def _bar(date, o, h, l, c, v, prev_close=None):
    return {"date": date, "open": o, "high": h, "low": l, "close": c,
            "prev_close": prev_close, "volume": v}


def _flat_bars(n, price=100.0, rng=2.0, vol=100_000):
    bars = []
    prev = None
    for i in range(n):
        h = price + rng / 2
        l = price - rng / 2
        bars.append(_bar(f"2026-01-{i+1:03d}", price, h, l, price, vol, prev))
        prev = price
    return bars


def test_adr20_averages_trailing_20_ranges_pct_of_close():
    bars = _flat_bars(25, price=100.0, rng=4.0)  # (h-l)/c = 4/100 = 4%
    assert round(dm.adr20(bars), 2) == 4.0


def test_adr20_empty_when_no_bars():
    assert dm.adr20([]) is None


def test_purple_dot_count_60d_counts_big_move_high_volume_days():
    bars = _flat_bars(60, price=100.0, rng=1.0, vol=100_000)
    # inject 3 purple-dot days: >5% move AND >5 lakh volume
    bars[10] = _bar("d10", 100, 106, 99, 106, 600_000, prev_close=100)   # +6%, 6L vol -> dot
    bars[30] = _bar("d30", 100, 106, 95, 95, 600_000, prev_close=100)    # -5% exactly at floor? use -6%
    bars[30] = _bar("d30", 100, 100, 94, 94, 600_000, prev_close=100)    # -6%, 6L vol -> dot
    bars[45] = _bar("d45", 100, 101, 99, 101, 400_000, prev_close=100)   # +1% -> not a dot (small move)
    bars[46] = _bar("d46", 100, 108, 98, 108, 100_000, prev_close=100)   # +8% but low vol -> not a dot
    assert dm.purple_dot_count_60d(bars) == 2


def test_purple_dot_count_60d_zero_dots_when_flat():
    bars = _flat_bars(60, price=100.0, rng=0.5, vol=1_000)
    assert dm.purple_dot_count_60d(bars) == 0


def test_pct_up_from_65d_low_measures_off_the_low_not_high():
    bars = _flat_bars(65, price=100.0, rng=1.0)
    # trailing-65 low is ~99.5 (100 - rng/2); push a deliberate low then rally
    bars[5]["low"] = 80.0
    bars[-1]["close"] = 104.0
    pct = dm.pct_up_from_65d_low(bars)
    assert pct == (104.0 - 80.0) / 80.0 * 100.0


def test_pct_up_from_65d_low_none_without_bars():
    assert dm.pct_up_from_65d_low([]) is None


def test_correction_depth_from_leg_high_measures_pullback_pct():
    bars = _flat_bars(60, price=100.0, rng=1.0)
    bars[40]["high"] = 150.0  # leg high
    bars[-1]["close"] = 120.0  # 20% pullback from 150
    depth = dm.correction_depth_from_leg_high(bars)
    assert round(depth, 2) == round((150.0 - 120.0) / 150.0 * 100.0, 2)


def test_leg_force_from_65d_low_reads_off_prior_leg_not_current_close():
    bars = _flat_bars(65, price=100.0, rng=1.0)
    bars[5]["low"] = 80.0        # trailing-65 low
    bars[40]["high"] = 150.0     # leg high (well above the low)
    bars[-1]["close"] = 82.0     # deep into a pullback -- current price is weak
    leg_force = dm.leg_force_from_65d_low(bars)
    assert leg_force == (150.0 - 80.0) / 80.0 * 100.0
    # a reversal picked 3-5 red days into a correction still shows leg force
    # even though pct_up_from_65d_low (current-price anchored) is near zero
    assert dm.pct_up_from_65d_low(bars) < 5.0
    assert leg_force >= 30.0


def test_leg_force_from_65d_low_none_without_bars():
    assert dm.leg_force_from_65d_low([]) is None


def test_leg_force_shares_leg_high_with_correction_depth():
    bars = _flat_bars(60, price=100.0, rng=1.0)
    bars[40]["high"] = 150.0
    bars[-1]["close"] = 120.0
    depth = dm.correction_depth_from_leg_high(bars)
    leg_force = dm.leg_force_from_65d_low(bars)
    implied_leg_high_from_depth = bars[-1]["close"] / (1 - depth / 100.0)
    assert round(implied_leg_high_from_depth, 2) == 150.0
    assert leg_force is not None


def test_prev_day_tightness_pctile_flags_tight_prior_day_as_low_percentile():
    bars = _flat_bars(21, price=100.0, rng=10.0)
    # yesterday (index -2) gets an unusually TIGHT range
    bars[-2]["high"] = 100.5
    bars[-2]["low"] = 99.5
    pctile = dm.prev_day_tightness_pctile(bars)
    assert pctile is not None and pctile <= 20.0  # tight day ranks near the bottom


def test_prev_day_tightness_pctile_none_when_too_few_bars():
    assert dm.prev_day_tightness_pctile([_flat_bars(1)[0]]) is None


def test_range_contraction_flag_true_on_shrinking_atr_low_percentile():
    bars = []
    prev = None
    price = 100.0
    for i in range(65):
        # first 50 bars: wide ranges (rng=10); last 15: contracting (10 -> 2)
        if i < 50:
            rng = 10.0
        else:
            rng = max(2.0, 10.0 - (i - 50) * 0.6)
        h, l = price + rng / 2, price - rng / 2
        bars.append(_bar(f"d{i}", price, h, l, price, 100_000, prev))
        prev = price
    assert dm.range_contraction_flag(bars) is True


def test_range_contraction_flag_false_on_flat_wide_ranges():
    bars = _flat_bars(65, price=100.0, rng=10.0)
    assert dm.range_contraction_flag(bars) is False


def test_range_contraction_flag_false_when_too_few_bars():
    assert dm.range_contraction_flag(_flat_bars(10)) is False


def test_persistency_counts_returns_all_four_ema_legs():
    bars = _flat_bars(260, price=100.0, rng=1.0)
    counts = dm.persistency_counts(bars)
    assert set(counts.keys()) == {"ema10", "ema21", "ema50", "ema200"}


def test_is_persistent_momentum_true_when_uptrend_sustained():
    # strictly rising closes for 260 bars -> price stays above every EMA leg
    bars = []
    prev = None
    for i in range(260):
        price = 100.0 + i * 0.5
        bars.append(_bar(f"d{i}", price, price + 1, price - 1, price, 100_000, prev))
        prev = price
    counts = dm.persistency_counts(bars)
    assert dm.is_persistent_momentum(counts) is True


def test_is_persistent_momentum_false_on_flat_series():
    bars = _flat_bars(260, price=100.0, rng=0.1)
    counts = dm.persistency_counts(bars)
    # flat/no-cross series never accrues a long persistency run
    assert dm.is_persistent_momentum(counts) is False
