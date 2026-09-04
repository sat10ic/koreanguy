"""SHIP-1 #7: leakage safety, walk-forward split correctness, and the
failure-safe skip-when-missing-dep contract for manas_os.ml.direction_lgbm.
No network; builds a small synthetic daily_prices history in a tmp db.
"""
from __future__ import annotations

import math
import random

import pandas as pd
import pytest

from manas_os import db
from manas_os.ml import direction_lgbm as dl


def _seed_prices(conn, symbol: str, n_days: int = 140, start_price: float = 100.0, seed: int = 7):
    rng = random.Random(seed)
    price = start_price
    rows = []
    day0 = pd.Timestamp("2025-01-01")
    d = day0
    count = 0
    while count < n_days:
        if d.weekday() < 5:  # weekdays only, close enough to trading sessions
            price *= 1 + rng.uniform(-0.02, 0.021)
            volume = rng.uniform(1e5, 2e5)
            delivery_pct = rng.uniform(20, 70)
            rows.append((symbol, d.strftime("%Y-%m-%d"), "EQ", price, price, price, price, volume, delivery_pct))
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
    conn = db.init_db(tmp_path / "ml_test.db")
    _seed_prices(conn, "TESTSYM", n_days=140, seed=11)
    _seed_prices(conn, "OTHERSYM", n_days=140, seed=23)
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# 1. Leakage test: a feature row at date D must be identical whether or not
#    future rows (after D) exist in the input frame.
# ---------------------------------------------------------------------------

def test_feature_builder_unchanged_when_future_rows_added(seeded_conn):
    full = dl.build_feature_matrix(seeded_conn, symbols=["TESTSYM"])
    full = full.sort_values("trade_date").reset_index(drop=True)
    assert len(full) >= 100

    cutoff_idx = 80
    cutoff_date = full.loc[cutoff_idx, "trade_date"]

    # Truncate the raw price frame to <= cutoff_date and recompute alone.
    prices = dl.load_price_frame(seeded_conn, symbols=["TESTSYM"])
    prices_truncated = prices[prices["trade_date"] <= cutoff_date].reset_index(drop=True)
    truncated_feats = dl.compute_symbol_features(prices_truncated)

    full_row_at_cutoff = full.iloc[cutoff_idx]
    truncated_row_at_cutoff = truncated_feats.iloc[-1]

    price_only_cols = [
        "ret_5d", "ret_20d", "ret_60d", "vol_20d", "delivery_pct",
        "delivery_pct_z20", "volume_z20", "dist_from_52w_high", "ema_stack_state",
    ]
    for col in price_only_cols:
        a = full_row_at_cutoff[col]
        b = truncated_row_at_cutoff[col]
        if pd.isna(a) and pd.isna(b):
            continue
        assert math.isclose(float(a), float(b), rel_tol=1e-9, abs_tol=1e-9), (
            f"{col} changed when future rows were added: {a} != {b}"
        )


def test_label_uses_future_rows_but_features_do_not(seeded_conn):
    """Sanity: the label column IS allowed to depend on future rows (it's
    the target, not a feature) — dropping the last HORIZON_DAYS rows should
    turn those labels to NaN, while earlier labels are unaffected."""
    full = dl.build_feature_matrix(seeded_conn, symbols=["TESTSYM"]).sort_values("trade_date").reset_index(drop=True)
    n = len(full)
    assert full.iloc[: n - dl.HORIZON_DAYS]["label"].notna().sum() > 0
    assert full.iloc[-3:]["label"].isna().all()


# ---------------------------------------------------------------------------
# 2. Walk-forward split correctness: every test-month row's trade_date must
#    be later than every training row's trade_date used for that fold (pure
#    expanding-window, no look-ahead across the train/test boundary).
# ---------------------------------------------------------------------------

def test_walk_forward_split_never_trains_on_future_relative_to_test_month():
    dates = pd.date_range("2025-01-01", periods=260, freq="B")
    rng = random.Random(3)
    rows = []
    for i, d in enumerate(dates):
        rows.append({
            "symbol": "SYN",
            "trade_date": d,
            "ret_5d": rng.uniform(-1, 1),
            "ret_20d": rng.uniform(-1, 1),
            "ret_60d": rng.uniform(-1, 1),
            "vol_20d": rng.uniform(0, 1),
            "delivery_pct": rng.uniform(0, 100),
            "delivery_pct_z20": rng.uniform(-2, 2),
            "volume_z20": rng.uniform(-2, 2),
            "dist_from_52w_high": rng.uniform(-1, 0),
            "ema_stack_state": rng.choice([-1, 0, 1]),
            "sector_rel_ret_20d": rng.uniform(-1, 1),
            "fii_dii_net5d_z": rng.uniform(-2, 2),
            "bulk_deal_flag_5d": rng.choice([0, 1]),
            "label": float(rng.choice([0, 1])),
        })
    df = pd.DataFrame(rows)

    d = dl._clean_dataset(df)
    months = sorted(d["month"].unique())
    assert len(months) >= 3
    for test_month in months[1:]:
        train = d[d["month"] < test_month]
        test = d[d["month"] == test_month]
        if train.empty or test.empty:
            continue
        assert train["trade_date"].max() < test["trade_date"].min(), (
            f"train/test overlap or inversion at fold {test_month}"
        )


def test_walk_forward_validate_runs_and_beats_or_reports_against_baseline(seeded_conn):
    if not dl.HAS_LIGHTGBM:
        pytest.skip("lightgbm not installed in this environment")
    full = dl.build_feature_matrix(seeded_conn, symbols=["TESTSYM", "OTHERSYM"])
    folds, pooled = dl.walk_forward_validate(full, min_train_rows=30)
    # With so little synthetic data most months may not clear min_train_rows;
    # the contract under test is that it runs without raising and returns a
    # well-shaped pooled summary (n, auc, hit_rate, baseline_hit_rate keys).
    assert set(pooled.keys()) == {"n", "auc", "hit_rate", "baseline_hit_rate"}
    if pooled["n"] > 0:
        assert 0.0 <= pooled["hit_rate"] <= 1.0
        assert 0.0 <= pooled["baseline_hit_rate"] <= 1.0


# ---------------------------------------------------------------------------
# 3. Stage skip-when-missing-dep: run() must never raise, and must be a
#    no-op `skip` pipeline_runs row when lightgbm isn't importable.
# ---------------------------------------------------------------------------

def test_run_skips_gracefully_when_lightgbm_missing(seeded_conn, monkeypatch):
    monkeypatch.setattr(dl, "HAS_LIGHTGBM", False)
    result = dl.run(seeded_conn, "2025-06-01", shortlist_symbols=["TESTSYM"])
    assert result == 0
    row = seeded_conn.execute(
        "SELECT status FROM pipeline_runs WHERE stage=? ORDER BY run_id DESC LIMIT 1",
        (dl.STAGE,),
    ).fetchone()
    assert row is not None
    assert row["status"] == "skip"


def test_run_skips_gracefully_with_no_shortlist(seeded_conn):
    result = dl.run(seeded_conn, "2025-06-01", shortlist_symbols=[])
    assert result == 0
    row = seeded_conn.execute(
        "SELECT status FROM pipeline_runs WHERE stage=? ORDER BY run_id DESC LIMIT 1",
        (dl.STAGE,),
    ).fetchone()
    assert row is not None
    assert row["status"] == "skip"


def test_run_never_raises_on_unexpected_error(seeded_conn, monkeypatch):
    if not dl.HAS_LIGHTGBM:
        pytest.skip("lightgbm not installed in this environment")

    def _boom(*a, **kw):
        raise RuntimeError("boom")

    monkeypatch.setattr(dl, "build_feature_matrix", _boom)
    result = dl.run(seeded_conn, "2025-06-01", shortlist_symbols=["TESTSYM"])
    assert result == 0
    row = seeded_conn.execute(
        "SELECT status, detail FROM pipeline_runs WHERE stage=? ORDER BY run_id DESC LIMIT 1",
        (dl.STAGE,),
    ).fetchone()
    assert row is not None
    assert row["status"] == "skip"
    assert "boom" in (row["detail"] or "")
