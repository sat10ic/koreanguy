"""Tests for the adopted indicator engine (manas_os.engine.indicators)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from manas_os import db
from manas_os.engine import indicators


def _synthetic_ohlcv(symbol: str = "TESTCO", n: int = 250, seed: int = 7) -> pd.DataFrame:
    """~250 rows of deterministic daily OHLCV with a gentle uptrend + noise."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2024-01-01", periods=n).strftime("%Y-%m-%d").tolist()
    close = 100.0 + np.cumsum(rng.normal(0.15, 1.0, size=n))
    close = np.abs(close) + 10.0  # keep strictly positive
    high = close + rng.uniform(0.2, 2.0, size=n)
    low = close - rng.uniform(0.2, 2.0, size=n)
    open_ = close + rng.uniform(-1.0, 1.0, size=n)
    volume = rng.integers(500_000, 2_000_000, size=n).astype(float)
    return pd.DataFrame({
        "symbol": symbol,
        "date": dates,
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    })


def test_compute_indicators_values_are_sane():
    df = _synthetic_ohlcv()
    out = indicators.compute_indicators_for_symbol(df, mcap=float("nan"))
    assert not out.empty
    last = out.iloc[-1]

    # sma20 on the last row must equal the mean of the last 20 closes.
    expected_sma20 = df["close"].tail(20).mean()
    assert last["sma20"] == pytest.approx(expected_sma20, rel=1e-9)

    # RSI is bounded [0, 100].
    rsi_vals = out["rsi14"].dropna()
    assert not rsi_vals.empty
    assert (rsi_vals >= 0).all() and (rsi_vals <= 100).all()

    # ATR is non-negative where defined.
    atr_vals = out["atr14"].dropna()
    assert (atr_vals >= 0).all()

    # Stage is one of the expected Weinstein labels.
    assert last["stage"] in {"S1A", "S1B", "S2", "S3", "S4"}


def test_compute_indicators_short_history_returns_empty():
    df = _synthetic_ohlcv(n=15)
    out = indicators.compute_indicators_for_symbol(df, mcap=float("nan"))
    assert out.empty


def test_engine_run_empty(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        res = indicators.run(conn, run_date="2024-12-31")
        assert res["status"] == "ok"
        assert res["rows_affected"] == 0
        assert res["symbols"] == 0

        row = conn.execute(
            "SELECT stage, status, rows_affected FROM pipeline_runs "
            "WHERE run_date = ? AND stage = 'indicators'",
            ("2024-12-31",),
        ).fetchone()
        assert row is not None
        assert row["stage"] == "indicators"
        assert row["status"] == "ok"
        assert row["rows_affected"] == 0
    finally:
        conn.close()


def test_engine_run_populates_features(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        df = _synthetic_ohlcv(symbol="ACME", n=250)
        conn.executemany(
            "INSERT INTO daily_prices (symbol, trade_date, open, high, low, close, "
            "volume, source) VALUES (?, ?, ?, ?, ?, ?, ?, 'test')",
            [
                (r.symbol, r.date, r.open, r.high, r.low, r.close, r.volume)
                for r in df.itertuples(index=False)
            ],
        )
        conn.commit()

        run_date = df["date"].iloc[-1]
        res = indicators.run(conn, run_date=run_date)
        assert res["status"] == "ok"
        assert res["symbols"] == 1
        assert res["rows_affected"] == 1

        import json
        row = conn.execute(
            "SELECT feature_json FROM features_daily WHERE symbol = 'ACME' AND trade_date = ?",
            (run_date,),
        ).fetchone()
        assert row is not None
        bag = json.loads(row["feature_json"])
        assert "sma20" in bag and "rsi14" in bag and "stage" in bag
        assert bag["stage"] in {"S1A", "S1B", "S2", "S3", "S4"}
    finally:
        conn.close()
