"""Round-4 evidence machinery: exit_variants pure-function bar-walk tests."""
from manas_os.backtest import exit_variants as ev


def _bar(date, o, h, low, c):
    return {"trade_date": date, "open": o, "high": h, "low": low, "close": c}


def test_baseline_x1_matches_next_open_stop_exit():
    # entry 100, stop 90 -> risk 10. Day1 stop touched (low 85).
    bars = [
        _bar("d1", 99, 101, 85, 90),
        _bar("d2", 90, 95, 88, 92),
    ]
    out = ev.walk_managed_exit(bars, plan_entry=100, plan_stop=90, horizon=2)
    assert out["skipped"] is False
    assert out["exit_reason"] == "stop"
    # exit at 90 * (1-0.002) = 89.82 -> r = (89.82-100)/10 = -1.018
    assert out["managed_r"] == -1.018


def test_wider_stop_x1_5_survives_same_dip_and_recovers():
    # Same bars as above but with stop widened 1.5x: effective_stop = 100-15=85.
    # Day1 low=85 touches exactly -> still stops (boundary); use low=86 instead.
    bars = [
        _bar("d1", 99, 101, 86, 90),
        _bar("d2", 92, 108, 90, 105),
    ]
    out_baseline = ev.walk_managed_exit(bars, plan_entry=100, plan_stop=90, horizon=2, stop_multiplier=1.0)
    out_wide = ev.walk_managed_exit(bars, plan_entry=100, plan_stop=90, horizon=2, stop_multiplier=1.5)
    assert out_baseline["exit_reason"] == "stop"  # low 86 <= effective_stop 90
    assert out_wide["exit_reason"] == "horizon_close"  # low 86 > effective_stop 85, survives to close
    assert out_wide["managed_r"] > out_baseline["managed_r"]


def test_stop_multiplier_scales_risk_denominator():
    bars = [
        _bar("d1", 100, 106, 99, 105),
        _bar("d2", 105, 110, 104, 108),
    ]
    out_x1 = ev.walk_managed_exit(bars, plan_entry=100, plan_stop=90, horizon=2, stop_multiplier=1.0)
    out_x2 = ev.walk_managed_exit(bars, plan_entry=100, plan_stop=90, horizon=2, stop_multiplier=2.0)
    # Same close-based R numerator direction but a bigger denominator -> smaller |R|.
    assert out_x1["exit_reason"] == out_x2["exit_reason"] == "horizon_close"
    assert abs(out_x2["managed_r"]) < abs(out_x1["managed_r"])


def test_buy_stop_skips_when_never_confirmed():
    # Entry pivot 100; price never trades a high >= 100 within the window.
    bars = [
        _bar("d1", 95, 98, 93, 96),
        _bar("d2", 96, 99, 94, 97),
    ]
    out = ev.walk_managed_exit(bars, plan_entry=100, plan_stop=90, horizon=2, entry_mode="buy_stop")
    assert out["skipped"] is True
    assert out["skip_reason"] == "buy_stop_never_confirmed"


def test_buy_stop_fills_on_confirmation_bar_not_next_open():
    # d1 doesn't confirm (high 99 < 100). d2 gaps above pivot at open 102.
    # d3/d4 provide the horizon window starting AT the confirmation bar (d2).
    bars = [
        _bar("d1", 95, 99, 93, 97),
        _bar("d2", 102, 104, 101, 103),
        _bar("d3", 103, 106, 102, 105),
    ]
    out = ev.walk_managed_exit(bars, plan_entry=100, plan_stop=90, horizon=2, entry_mode="buy_stop")
    assert out["skipped"] is False
    assert out["entry_fill"] == 102  # gapped above pivot -> fills at that bar's open
    assert out["exit_reason"] == "horizon_close"


def test_buy_stop_fills_at_pivot_when_intraday_cross_not_gap():
    # d1 trades up through 100 intraday (high 101) but opens below it (98) -> fill at pivot 100.
    bars = [
        _bar("d1", 98, 101, 97, 99),
        _bar("d2", 99, 103, 98, 102),
    ]
    out = ev.walk_managed_exit(bars, plan_entry=100, plan_stop=90, horizon=2, entry_mode="buy_stop")
    assert out["skipped"] is False
    assert out["entry_fill"] == 100


def test_invalid_plan_returns_none():
    bars = [_bar("d1", 100, 101, 99, 100)]
    assert ev.walk_managed_exit(bars, plan_entry=90, plan_stop=100, horizon=1) is None


def test_incomplete_window_returns_none():
    bars = [_bar("d1", 100, 101, 99, 100)]
    assert ev.walk_managed_exit(bars, plan_entry=100, plan_stop=90, horizon=5) is None


def test_gap_through_stop_recorded_honestly():
    # Entry 100, stop 90. Next session gaps open below stop.
    bars = [_bar("d1", 70, 71, 68, 70)]
    out = ev.walk_managed_exit(bars, plan_entry=100, plan_stop=90, horizon=1)
    assert out["exit_reason"] == "gap_through_stop"
    assert out["managed_r"] < -1.0
