"""M9: choppy brake — 3+ stops/5 trading days, or weekly DD >= 4%."""
from manas_os.regime.choppy_brake import brake


def _trade(date, r_result):
    return {"trade_date": date, "r_result": r_result}


def test_three_stops_in_five_days_arms_brake():
    trades = [
        _trade("2026-07-01", -1.0),
        _trade("2026-07-02", -1.0),
        _trade("2026-07-03", 0.5),
        _trade("2026-07-06", -1.0),
        _trade("2026-07-07", 0.2),
    ]
    result = brake(trades, "2026-07-07")
    assert result["active"] is True
    assert "stops" in result["reason"]


def test_two_stops_does_not_arm_brake():
    trades = [
        _trade("2026-07-01", -1.0),
        _trade("2026-07-02", 0.5),
        _trade("2026-07-03", -1.0),
        _trade("2026-07-06", 0.3),
        _trade("2026-07-07", 0.2),
    ]
    result = brake(trades, "2026-07-07")
    assert result["active"] is False
    assert result["reason"] is None


def test_weekly_drawdown_trigger():
    result = brake([], "2026-07-07", weekly_dd_pct=-4.5)
    assert result["active"] is True
    assert "drawdown" in result["reason"]


def test_weekly_drawdown_under_threshold_does_not_trigger():
    result = brake([], "2026-07-07", weekly_dd_pct=-2.0)
    assert result["active"] is False


def test_only_trades_within_lookback_window_count():
    # 3 stops, but 2 of them are outside the 5-trading-day window (older dates
    # not in the most-recent 5 distinct trade_dates) -> should not arm.
    trades = [
        _trade("2026-06-01", -1.0),
        _trade("2026-06-02", -1.0),
        _trade("2026-07-03", 0.1),
        _trade("2026-07-06", 0.1),
        _trade("2026-07-07", -1.0),
        _trade("2026-07-08", 0.1),
        _trade("2026-07-09", 0.1),
    ]
    result = brake(trades, "2026-07-09")
    assert result["active"] is False


def test_point_in_time_ignores_future_trades():
    trades = [
        _trade("2026-07-01", -1.0),
        _trade("2026-07-02", -1.0),
        _trade("2026-07-03", -1.0),
        _trade("2026-12-31", -1.0),  # future, must not count
    ]
    result = brake(trades, "2026-07-03")
    assert result["active"] is True
    result_future_excluded = brake(trades, "2026-07-03")
    assert result_future_excluded["evidence"]["stop_count"] == 3
