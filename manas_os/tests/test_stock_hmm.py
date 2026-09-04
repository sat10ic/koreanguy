import numpy as np
import pandas as pd
import pytest

from manas_os import db
from manas_os.ml import stock_hmm as sh


def _seed_prices(conn, symbol="TESTCO", n=200, seed=0, drift=0.0015, vol=0.01, start="2025-01-01"):
    rng = np.random.RandomState(seed)
    dates = pd.bdate_range(start, periods=n)
    price = 100.0
    rows = []
    for d in dates:
        r = rng.normal(drift, vol)
        price *= (1 + r)
        volume = int(max(1000 + rng.normal(0, 200), 1))
        rows.append((symbol, d.strftime("%Y-%m-%d"), "EQ", price, volume, "test"))
    conn.executemany(
        "INSERT OR REPLACE INTO daily_prices (symbol, trade_date, series, close, volume, source) "
        "VALUES (?,?,?,?,?,?)",
        rows,
    )
    conn.commit()
    return [d.strftime("%Y-%m-%d") for d in dates]


@pytest.mark.skipif(not sh.HAS_HMMLEARN, reason="hmmlearn not installed")
def test_insufficient_history_is_honest_not_a_guess():
    conn = db.init_db(":memory:")
    dates = _seed_prices(conn, n=50)  # well below MIN_HISTORY_BARS
    out = sh.compute(conn, "TESTCO", dates[-1])
    assert out["available"] is False
    assert "insufficient history" in out["reason"]


@pytest.mark.skipif(not sh.HAS_HMMLEARN, reason="hmmlearn not installed")
def test_sufficient_history_returns_series_and_current():
    conn = db.init_db(":memory:")
    dates = _seed_prices(conn, n=200, seed=7)
    out = sh.compute(conn, "TESTCO", dates[-1])
    assert out["available"] is True
    assert out["symbol"] == "TESTCO"
    assert len(out["series"]) > 0
    for row in out["series"]:
        total = row["p_bull"] + row["p_bear"] + row["p_chop"]
        assert abs(total - 1.0) < 1e-3
    current = out["current"]
    assert current["state"] in ("BULLISH", "BEARISH", "CHOP")
    assert current["confidence"] in ("LOW", "MED", "HIGH")


@pytest.mark.skipif(not sh.HAS_HMMLEARN, reason="hmmlearn not installed")
def test_state_label_mapping_is_deterministic():
    conn = db.init_db(":memory:")
    dates = _seed_prices(conn, n=200, seed=11)
    out1 = sh.compute(conn, "TESTCO", dates[-1])
    out2 = sh.compute(conn, "TESTCO", dates[-1])
    assert out1["current"] == out2["current"]
    assert out1["series"] == out2["series"]


@pytest.mark.skipif(not sh.HAS_HMMLEARN, reason="hmmlearn not installed")
def test_cache_roundtrip_returns_identical_payload():
    conn = db.init_db(":memory:")
    dates = _seed_prices(conn, n=200, seed=3)
    first = sh.get_or_compute(conn, "TESTCO", dates[-1])
    # second call should hit the cache row, not refit
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM stock_hmm_cache WHERE symbol=? AND as_of=?",
        ("TESTCO", dates[-1]),
    ).fetchone()
    assert row["n"] == 1
    second = sh.get_or_compute(conn, "TESTCO", dates[-1])
    assert first == second


def test_summary_line_unavailable_returns_none():
    assert sh.summary_line({"available": False, "reason": "insufficient history"}) is None


def test_summary_line_format():
    payload = {
        "available": True,
        "current": {"state": "BULLISH", "confidence": "LOW", "p_bull": 0.48, "p_bear": 0.30, "p_chop": 0.22},
    }
    line = sh.summary_line(payload)
    assert line == "stock HMM: BULLISH 48% (low conf)"
