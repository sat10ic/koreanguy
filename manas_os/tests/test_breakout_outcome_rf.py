from __future__ import annotations

import math
import random

import pandas as pd
import pytest

from manas_os import db
from manas_os.ml import breakout_outcome_rf as borf


def _seed_prices(conn, symbol: str, n_days: int = 140, start_price: float = 100.0, seed: int = 7):
    rng = random.Random(seed)
    price = start_price
    rows = []
    day0 = pd.Timestamp("2025-01-01")
    d = day0
    count = 0
    while count < n_days:
        if d.weekday() < 5:
            price *= 1 + rng.uniform(-0.02, 0.021)
            volume = rng.uniform(1e5, 2e5)
            delivery_pct = rng.uniform(20, 70)
            rows.append((symbol, d.strftime("%Y-%m-%d"), "EQ", price, price + 2.0, price - 2.0, price, volume, delivery_pct))
            count += 1
        d += pd.Timedelta(days=1)
    conn.executemany(
        "INSERT INTO daily_prices (symbol, trade_date, series, open, high, low, close, volume, delivery_pct) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        rows,
    )
    conn.commit()


@pytest.fixture()
def seeded_conn(tmp_path):
    conn = db.init_db(tmp_path / "borf_test.db")
    _seed_prices(conn, "TESTSYM", n_days=140, seed=11)
    _seed_prices(conn, "OTHERSYM", n_days=140, seed=23)
    yield conn
    conn.close()


def test_feature_builder_leakage_safety(seeded_conn):
    # We want to check that truncated features match full features
    prices = borf.load_price_frame(seeded_conn, symbols=["TESTSYM"])
    assert len(prices) >= 80
    
    cutoff_date = prices.loc[70, "trade_date"]
    
    # Compute full symbol features
    full_feats = borf.compute_symbol_features(prices)
    
    # Compute truncated symbol features
    truncated_prices = prices[prices["trade_date"] <= cutoff_date].reset_index(drop=True)
    truncated_feats = borf.compute_symbol_features(truncated_prices)
    
    for col in borf.FEATURE_COLS:
        if col == "rs":
            continue
        a = full_feats.loc[70, col]
        b = truncated_feats.iloc[-1][col]
        if pd.isna(a) and pd.isna(b):
            continue
        assert math.isclose(float(a), float(b), rel_tol=1e-9, abs_tol=1e-9)


def test_label_uses_future_rows(seeded_conn):
    prices = borf.load_price_frame(seeded_conn, symbols=["TESTSYM"])
    labels = borf.compute_asymmetric_label(prices)
    n = len(prices)
    assert labels.iloc[: n - borf.HORIZON_DAYS].notna().sum() > 0
    assert labels.iloc[-borf.HORIZON_DAYS:].isna().all()


def test_run_skips_gracefully_when_sklearn_missing(seeded_conn, monkeypatch):
    monkeypatch.setattr(borf, "HAS_SKLEARN", False)
    result = borf.run(seeded_conn, "2025-06-01", shortlist_symbols=["TESTSYM"])
    assert result == 0
    row = seeded_conn.execute(
        "SELECT status FROM pipeline_runs WHERE stage=? ORDER BY run_id DESC LIMIT 1",
        (borf.STAGE,),
    ).fetchone()
    assert row is not None
    assert row["status"] == "skip"
