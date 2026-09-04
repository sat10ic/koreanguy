import pytest

from manas_os.engine.manas_indicators import (
    BENCHMARK_10MA,
    BENCHMARK_200MA,
    BENCHMARK_21MA,
    BENCHMARK_50MA,
    burst_power,
    mswing,
    persistency,
    persistency_ema_bundle,
    purple_dot,
    rmv,
    simple_volume,
    ss_rvol,
)


def bar(open_, high, low, close, volume=1000):
    return {"open": open_, "high": high, "low": low, "close": close, "volume": volume}


def test_burst_power_counts_and_score():
    # Keep moves comfortably inside their buckets — an exact-10% fixture
    # landed at 9.999…% in float math and drifted into the 5-10 bucket.
    bars = [
        bar(100, 101, 99, 100),
        bar(101, 107, 100, 106),        # +6%          -> 5-10 bucket
        bar(107, 119, 106, 118),        # +11.32%      -> 10-19 bucket
        bar(119, 143, 118, 141.6),      # +20%         -> >=19 bucket
        bar(142, 148, 141, 146),        # +3.1%        -> no bucket
    ]

    result = burst_power(bars, lookback_days=10)

    assert result["count_5"] == 1
    assert result["count_10"] == 1
    assert result["count_19"] == 1
    assert result["max_move"] == pytest.approx(20.0)
    assert result["power_value"] == pytest.approx(2.7)
    assert result["rounded"] == 3


def test_simple_volume_pocket_pivots_first_bar_edge_and_streak_break():
    bars = [
        bar(10, 10.5, 8.5, 9, 1000),
        bar(9.5, 10.5, 9, 10, 900),
        bar(10.5, 11.5, 10, 11, 1200),
        bar(10.5, 11, 9.5, 10, 1300),
        bar(10, 10.8, 9.8, 10.5, 1250),
    ]

    states = simple_volume(bars)

    # simple vol.txt lines 28-36: first bar uses open because prev close is unavailable.
    assert states[0]["is_down"] is True
    # simple vol.txt lines 38-44 and 60: bull PP scans only prior down-bar volumes.
    assert states[1]["bull_pocket_pivot"] is False
    assert states[2]["max_down_volume"] == 1000
    assert states[2]["bull_pocket_pivot"] is True
    # simple vol.txt lines 46-52 and 61: bear PP mirrors against prior up-bar volumes.
    assert states[3]["max_up_volume"] == 1200
    assert states[3]["bear_pocket_pivot"] is True
    # simple vol.txt lines 74-83: blue streak requires the last N bars all bull PP.
    assert simple_volume(bars[:3]).blue_streak(1) is True
    assert states.blue_streak(2) is False


def test_simple_volume_zero_down_window_blocks_pp_and_dry_priority():
    no_down = [
        bar(9, 10.5, 8.5, 10, 1000),
        bar(10.5, 11.5, 10, 11, 2000),
    ]
    states = simple_volume(no_down)

    # simple vol.txt lines 38-44 leave maxDown as na when no down bars exist.
    # simple vol.txt line 60 requires not na(maxDownVolume), so no PP fires.
    assert states[1]["max_down_volume"] is None
    assert states[1]["bull_pocket_pivot"] is False

    dry_fixture = [bar(10, 11, 9, 10, 1000) for _ in range(49)]
    dry_fixture.append(bar(10, 10.5, 9.5, 10.1, 100))
    dry_states = simple_volume(dry_fixture)

    # simple vol.txt lines 62 and 66-72: dry uses SMA50*0.20 and has top color priority.
    assert dry_states[-1]["dry"] is True
    assert dry_states[-1]["state"] == "dry"


def test_persistency_decisive_exit_hold_cancel_flip_and_immediate_repending():
    bars = [
        bar(10, 10.5, 9.5, 10),
        bar(12, 12.5, 11.5, 12),
        bar(13, 13.5, 12.5, 13),
        bar(11, 11.4, 10.8, 11),
        bar(12, 12.3, 11.2, 12),
        bar(10, 10.5, 9.8, 10),
        bar(10.5, 10.7, 9.7, 10.5),
    ]

    states = persistency(bars, "SMA", 2)

    assert states[1]["count"] == 2
    assert states[2]["count"] == 3
    assert states[3]["count"] == 4
    assert states[3]["pending_exit"] is True
    assert states[3]["exit_level"] == pytest.approx(10.8)
    assert states[4]["count"] == 5
    assert states[4]["pending_exit"] is False
    assert states[5]["pending_exit"] is True
    assert states[5]["exit_level"] == pytest.approx(9.8)
    assert states[6]["count"] == -1
    assert states[6]["exit_signal"] is True
    assert states[6]["pending_exit"] is True
    assert states[6]["exit_level"] == pytest.approx(10.7)


def test_persistency_ema_bundle_and_benchmark_constants():
    bars = [bar(10 + i, 11 + i, 9 + i, 10 + i) for i in range(5)]
    bundle = persistency_ema_bundle(bars)

    assert set(bundle) == {"ema10", "ema21", "ema50", "ema200"}
    assert (BENCHMARK_10MA, BENCHMARK_21MA, BENCHMARK_50MA, BENCHMARK_200MA) == (21, 42, 63, 252)


def test_mswing_ipo_available_length_fallback_and_color():
    stock = [bar(100, 101, 99, 100), bar(110, 111, 109, 110), bar(121, 122, 120, 121)]
    index = [bar(100, 101, 99, 100), bar(102, 103, 101, 102), bar(104, 105, 103, 104)]

    state = mswing(stock, index)[-1]

    assert state["momo20"] == pytest.approx(10.5)
    assert state["momo50"] == pytest.approx(10.5)
    assert state["mswing"] == pytest.approx(21.0)
    assert state["index_mswing"] == pytest.approx(4.0)
    assert state["color"] == "up"


def test_rmv_abs_tight_body_case_vs_expansion_range_case():
    prior = [bar(100, 105, 95, 100) for _ in range(5)]
    tight = prior + [bar(102, 105, 100, 103)]
    expansion = prior + [bar(100, 120, 90, 100)]

    tight_state = rmv(tight)[-1]
    expansion_state = rmv(expansion)[-1]

    assert tight_state["is_abs_tight"] is True
    assert tight_state["numerator"] == pytest.approx(1)
    assert tight_state["denominator"] == pytest.approx(10)
    assert tight_state["rmv"] == pytest.approx(5)
    assert expansion_state["is_abs_tight"] is False
    assert expansion_state["strong_oc"] is False
    assert expansion_state["numerator"] == pytest.approx(30)
    assert expansion_state["rmv"] == pytest.approx(100)
    assert isinstance(tight_state["tightness_setup"], bool)
    assert isinstance(tight_state["vdu_setup"], bool)
    assert tight_state["rank"] in {0, 1, 2, 3, 4}


def test_ss_rvol_prior_shifted_volume_and_strong_start():
    bars = [bar(100, 101, 99, 100, 100) for _ in range(20)]
    bars.append(bar(101, 103, 99.5, 102, 250))

    state = ss_rvol(bars, lookback=20)[-1]

    assert state["avg_volume"] == pytest.approx(100)
    assert state["rvol"] == pytest.approx(2.5)
    assert state["strong_start"] is True


def test_purple_dot_requires_abs_roc_and_volume_floor():
    bars = [
        bar(100, 101, 99, 100, 2_000_000),
        bar(105, 107, 104, 106, 1_000_000),
        bar(104, 105, 103, 104, 2_000_000),
        bar(98, 99, 97, 98, 999_999),
    ]

    assert purple_dot(bars) == [False, True, False, False]
