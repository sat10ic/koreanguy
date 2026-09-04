"""Tests for deterministic price-action detectors."""
from __future__ import annotations

from collections import Counter

import pytest

from manas_os import db
from manas_os.engine import price_action as pa


def _bar(day: int, open_: float, high: float, low: float, close: float, volume: int = 1000):
    return {
        "date": f"2024-01-{day:02d}",
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    }


def test_detect_ema_events_loss_and_reclaim_only_when_close_crosses():
    bars = [
        _bar(1, 100, 100, 100, 100),
        _bar(2, 100, 100, 100, 100),
        _bar(3, 100, 100, 100, 100),
        _bar(4, 100, 100, 100, 100),
        _bar(5, 100, 100, 100, 100),
        _bar(6, 95, 96, 89, 90),
        _bar(7, 104, 106, 104, 105),
    ]

    signals = pa.detect_ema_events(bars, spans=(21,))
    counts = Counter(s["kind"] for s in signals)

    assert counts == {"EMA21_LOSS": 1, "EMA21_RECLAIM": 1}
    assert "closed below the 21EMA" in signals[0]["detail"]
    assert "reclaimed the 21EMA" in signals[1]["detail"]


def test_detect_ema_events_touch_requires_intraday_test_and_hold():
    bars = [
        _bar(1, 100, 100, 100, 100),
        _bar(2, 100, 100, 100, 100),
        _bar(3, 100, 100, 100, 100),
        _bar(4, 100, 100, 100, 100),
        _bar(5, 100, 100, 100, 100),
        _bar(6, 101, 102, 99, 101),
        _bar(7, 103, 104, 102, 103),
    ]

    signals = pa.detect_ema_events(bars, spans=(21,))
    counts = Counter(s["kind"] for s in signals)

    assert counts["EMA21_TOUCH"] == 1
    assert "tested the 21EMA and held" in signals[0]["detail"]


def test_trailing_stop_state_prioritizes_slow_trail_hit():
    base = [_bar(i, 100 + i, 101 + i, 99 + i, 100 + i) for i in range(1, 21)]
    hold = base + [_bar(21, 122, 124, 121, 123)]
    fast_hit = base + [_bar(21, 112, 113, 111, 112)]
    slow_hit = base + [_bar(21, 100, 101, 99, 100)]

    assert pa.trailing_stop_state(hold)["status"] == "HOLD"
    assert pa.trailing_stop_state(fast_hit)["status"] == "TRAIL_HIT_FAST"
    assert pa.trailing_stop_state(slow_hit)["status"] == "TRAIL_HIT_SLOW"
    assert pa.trailing_stop_state(slow_hit)["stop_level"] == pytest.approx(110.5773453712)


def test_detect_shakeout_triggers_only_on_undercut_and_reclaim():
    prior = [_bar(i, 101, 103, 100, 102) for i in range(1, 11)]
    trigger = _bar(11, 100, 102, 98, 101)
    no_reclaim = _bar(12, 100, 101, 97, 97.5)

    signals = pa.detect_shakeout(prior + [trigger, no_reclaim], lookback=10)

    assert [s["kind"] for s in signals] == ["SHAKEOUT"]
    assert signals[0]["date"] == "2024-01-11"
    assert "Undercut 10-day low 100" in signals[0]["detail"]


def test_detect_pocket_pivots_requires_volume_upper_half_and_ema10():
    prior = []
    for i in range(1, 11):
        if i % 2 == 0:
            prior.append(_bar(i, 101, 102, 99, 100, volume=1000 + i))
        else:
            prior.append(_bar(i, 100, 102, 99, 101, volume=900 + i))
    trigger = _bar(11, 101, 113, 100, 112, volume=2000)
    weak_close = _bar(12, 112, 113, 100, 104, volume=3000)

    signals = pa.detect_pocket_pivots(prior + [trigger, weak_close], lookback=10)

    assert [s["kind"] for s in signals] == ["POCKET_PIVOT"]
    assert signals[0]["date"] == "2024-01-11"
    assert "max down-day volume" in signals[0]["detail"]


def test_weinstein_stage_handles_insufficient_history_and_stage_two():
    short = [_bar(i, 100, 101, 99, 100) for i in range(1, 100)]
    assert pa.weinstein_stage(short)["stage"] is None

    bars = []
    for i in range(1, 181):
        close = float(i)
        bars.append({
            "date": f"2024-{((i - 1) // 28) + 1:02d}-{((i - 1) % 28) + 1:02d}",
            "open": close - 0.5,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": 1000,
        })

    stage = pa.weinstein_stage(bars)

    assert stage["stage"] == 2
    assert "close 180" in stage["detail"]
    assert "150-day SMA" in stage["detail"]


def test_signals_for_symbol_loads_eq_prices_and_returns_recent_signals(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        bars = []
        for i in range(1, 181):
            close = float(i)
            bars.append({
                "date": f"2024-{((i - 1) // 28) + 1:02d}-{((i - 1) % 28) + 1:02d}",
                "open": close - 0.5,
                "high": close + 1.0,
                "low": close - 1.0,
                "close": close,
                "volume": 1000 + i,
            })
        conn.executemany(
            "INSERT INTO daily_prices (symbol, trade_date, series, open, high, low, close, "
            "prev_close, volume, delivery_qty, delivery_pct, source) "
            "VALUES (?, ?, 'EQ', ?, ?, ?, ?, ?, ?, ?, ?, 'test')",
            [
                (
                    "ACME",
                    b["date"],
                    b["open"],
                    b["high"],
                    b["low"],
                    b["close"],
                    b["close"] - 1,
                    b["volume"],
                    100,
                    50.0,
                )
                for b in bars
            ],
        )
        conn.execute(
            "INSERT INTO daily_prices (symbol, trade_date, series, open, high, low, close, "
            "volume, source) VALUES ('ACME', '2024-07-01', 'BE', 1, 1, 1, 1, 1, 'test')"
        )
        conn.commit()

        out = pa.signals_for_symbol(conn, "ACME", bars[-1]["date"])

        assert out["symbol"] == "ACME"
        assert out["as_of"] == bars[-1]["date"]
        assert out["stage"]["stage"] == 2
        assert out["trail"]["status"] == "HOLD"
        assert len(out["recent_signals"]) <= 15
        assert out["recent_signals"] == sorted(
            out["recent_signals"], key=lambda s: s["date"], reverse=True
        )
    finally:
        conn.close()
