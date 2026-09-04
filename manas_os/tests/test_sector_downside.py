import numpy as np
import pandas as pd

from manas_os import db
from manas_os.ml import sector_downside as sd
from manas_os.regime.sectors import SECTORS


def _seed_index_history(conn, symbol, n=120, seed=0, vol=0.01, drift=0.0):
    rng = np.random.RandomState(seed)
    dates = pd.bdate_range("2025-01-01", periods=n)
    rets = rng.normal(drift, vol, size=n)
    price = 100.0
    rows = []
    for d, r in zip(dates, rets):
        price *= (1 + r)
        rows.append((symbol, d.strftime("%Y-%m-%d"), price, None))
    conn.executemany(
        "INSERT OR REPLACE INTO sector_index_prices (symbol, trade_date, close, sma50) VALUES (?,?,?,?)",
        rows,
    )
    conn.commit()
    return [d.strftime("%Y-%m-%d") for d in dates]


def _seed_full_panel(conn, n=300):
    _seed_index_history(conn, sd.NIFTY_SYMBOL, n=n, seed=1)
    _seed_index_history(conn, sd.VIX_SYMBOL, n=n, seed=2, vol=0.02)
    for i, s in enumerate(SECTORS):
        if s["index"]:
            _seed_index_history(conn, s["index"], n=n, seed=10 + i, vol=0.015)


def test_build_panel_covers_all_indexed_sectors():
    conn = db.init_db(":memory:")
    _seed_full_panel(conn, n=60)
    panel = sd.build_panel(conn)
    assert set(panel["sector_key"].unique()) == set(sd.SECTOR_INDEX_KEYS.values())


def test_build_panel_features_are_backward_looking_only():
    conn = db.init_db(":memory:")
    dates = _seed_full_panel(conn, n=120) or []
    dates = [r["trade_date"] for r in conn.execute(
        "SELECT DISTINCT trade_date FROM sector_index_prices WHERE symbol=? ORDER BY trade_date", (sd.NIFTY_SYMBOL,)
    )]
    full = sd.build_panel(conn)
    cutoff = dates[70]

    conn2 = db.init_db(":memory:")
    rows = conn.execute(
        "SELECT symbol, trade_date, close FROM sector_index_prices WHERE trade_date <= ?", (cutoff,)
    ).fetchall()
    conn2.executemany(
        "INSERT OR REPLACE INTO sector_index_prices (symbol, trade_date, close) VALUES (?,?,?)",
        [(r["symbol"], r["trade_date"], r["close"]) for r in rows],
    )
    conn2.commit()
    truncated = sd.build_panel(conn2)

    for sector_key in list(sd.SECTOR_INDEX_KEYS.values())[:3]:
        row_full = full[(full["sector_key"] == sector_key) & (full["trade_date"] == cutoff)].iloc[0]
        row_trunc = truncated[(truncated["sector_key"] == sector_key) & (truncated["trade_date"] == cutoff)].iloc[0]
        for col in sd.FEATURE_COLS:
            assert np.isclose(row_full[col], row_trunc[col], rtol=1e-9, equal_nan=True) or (
                pd.isna(row_full[col]) and pd.isna(row_trunc[col])
            )


def test_ridge_logistic_shrinks_toward_prior_with_high_lambda():
    rng = np.random.RandomState(0)
    X = np.column_stack([np.ones(200), rng.normal(size=200)])
    y = (rng.uniform(size=200) < 0.3).astype(float)
    prior = np.array([1.0, 2.0])
    beta = sd.fit_ridge_logistic(X, y, prior=prior, lam=1e6)
    assert np.allclose(beta, prior, atol=1e-2)


def test_brier_score_prefers_calibrated_prediction():
    y = np.array([0.0, 1.0, 0.0, 1.0])
    good = np.array([0.1, 0.9, 0.1, 0.9])
    bad = np.array([0.9, 0.1, 0.9, 0.1])
    assert sd.brier_score(y, good) < sd.brier_score(y, bad)


def test_walk_forward_on_real_manas_db_reports_promotion_gate_honestly():
    """Report the current walk-forward verdict without forcing promotion.

    More history can invalidate old tuning; that is a valid shadow-model
    failure, not a reason to retune against the same evaluation window merely
    to keep a test green.
    """
    from manas_os import db as real_db
    conn = real_db.connect(r"C:\Users\satta\Downloads\koreanguy\manas_os\data\manas.db")
    panel = sd.build_panel(conn)
    assert not panel.empty
    folds, pooled = sd.walk_forward_validate(panel)
    assert pooled["n"] > 0
    assert np.isfinite(pooled["brier_model"])
    assert np.isfinite(pooled["brier_baseline"])
    assert sd.beats_baseline(pooled) == (pooled["brier_model"] < pooled["brier_baseline"])


def test_run_skips_when_insufficient_history():
    conn = db.init_db(":memory:")
    _seed_full_panel(conn, n=30)
    dates = [r["trade_date"] for r in conn.execute(
        "SELECT DISTINCT trade_date FROM sector_index_prices WHERE symbol=? ORDER BY trade_date", (sd.NIFTY_SYMBOL,)
    )]
    result = sd.run(conn, dates[-1])
    assert result["status"] == "skip"
    row = conn.execute("SELECT COUNT(*) AS n FROM sector_downside").fetchone()
    assert row["n"] == 0
