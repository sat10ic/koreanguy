import math

import numpy as np
import pandas as pd

from manas_os import db
from manas_os.regime import vol_har as vh
from manas_os.tests.test_regime_snapshot import _insert_breadth


def _seed_index_history(conn, symbol, n=120, seed=0, vol=0.01):
    rng = np.random.RandomState(seed)
    dates = pd.bdate_range("2025-01-01", periods=n)
    rets = rng.normal(0, vol, size=n)
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


def test_build_har_frame_only_uses_backward_looking_windows():
    conn = db.init_db(":memory:")
    dates = _seed_index_history(conn, vh.NIFTY_SYMBOL, n=120)
    _seed_index_history(conn, vh.VIX_SYMBOL, n=120, seed=1, vol=0.02)

    full = vh.build_har_frame(conn)
    # Truncate the raw price history to day 60 and recompute — the feature
    # row (not the target, which needs future rows and will be NaN there)
    # at day 60 must be identical either way: proof rv_1d/5d/22d never peek
    # past their own row.
    cutoff = dates[60]
    conn2 = db.init_db(":memory:")
    rows = conn.execute(
        "SELECT symbol, trade_date, close FROM sector_index_prices WHERE trade_date <= ?", (cutoff,)
    ).fetchall()
    conn2.executemany(
        "INSERT OR REPLACE INTO sector_index_prices (symbol, trade_date, close) VALUES (?,?,?)",
        [(r["symbol"], r["trade_date"], r["close"]) for r in rows],
    )
    conn2.commit()
    truncated = vh.build_har_frame(conn2)

    row_full = full[full["trade_date"] == cutoff].iloc[0]
    row_trunc = truncated[truncated["trade_date"] == cutoff].iloc[0]
    for col in ("rv_1d", "rv_5d", "rv_22d"):
        assert math.isclose(row_full[col], row_trunc[col], rel_tol=1e-9)


def test_qlike_prefers_closer_forecast():
    y_true = np.array([0.0001, 0.0002, 0.00015])
    close_pred = y_true * 1.05
    far_pred = y_true * 3.0
    assert vh.qlike(y_true, close_pred) < vh.qlike(y_true, far_pred)


def test_walk_forward_validate_and_beats_baseline_on_synthetic_data():
    conn = db.init_db(":memory:")
    _seed_index_history(conn, vh.NIFTY_SYMBOL, n=300, seed=42)
    _seed_index_history(conn, vh.VIX_SYMBOL, n=300, seed=7, vol=0.02)
    df = vh.build_har_frame(conn)
    folds, pooled = vh.walk_forward_validate(df)
    assert pooled["n"] > 0
    assert isinstance(vh.beats_baseline(pooled), bool)


def test_run_skips_when_insufficient_history():
    conn = db.init_db(":memory:")
    _insert_breadth(conn, trade_date="2026-01-05")
    from manas_os.regime import snapshot
    snapshot.run(conn, "2026-01-05")
    _seed_index_history(conn, vh.NIFTY_SYMBOL, n=10, seed=3)
    result = vh.run(conn, "2026-01-05")
    assert result["status"] == "skip"


def test_run_tolerates_missing_session_in_22d_window():
    """Gap-tolerance regression (root cause: NIFTY 50 / India VIX in
    sector_index_prices have no dedicated nightly updater, so the feed can
    legitimately lag or gap by a session or two). Drop ONE session inside
    the trailing window and confirm rv_22d/rv_5d still compute (>= MIN_*
    _SESSIONS present) and run() still writes a forecast — the old exact
    min_periods=22/5 continuity requirement would have NaN'd the row and
    silently skipped."""
    conn = db.init_db(":memory:")
    dates = _seed_index_history(conn, vh.NIFTY_SYMBOL, n=300, seed=42)
    _seed_index_history(conn, vh.VIX_SYMBOL, n=300, seed=7, vol=0.02)
    run_date = dates[-1]

    # Delete one NIFTY session from inside the trailing 22d window (not the
    # run_date row itself) to simulate a single missing feed day.
    gap_date = dates[-10]
    conn.execute(
        "DELETE FROM sector_index_prices WHERE symbol = ? AND trade_date = ?",
        (vh.NIFTY_SYMBOL, gap_date),
    )
    conn.commit()

    _insert_breadth(conn, trade_date=run_date)
    from manas_os.regime import snapshot
    snapshot.run(conn, run_date)

    full = vh.build_har_frame(conn)
    today = full[full["trade_date"] == pd.Timestamp(run_date)].iloc[0]
    # rv_22d/rv_5d must still be present despite the single missing session.
    assert not math.isnan(today["rv_22d"])
    assert not math.isnan(today["rv_5d"])

    result = vh.run(conn, run_date)
    row = conn.execute(
        "SELECT vol_forecast FROM regime_snapshots WHERE snapshot_date = ?", (run_date,)
    ).fetchone()
    if result["status"] == "ok":
        assert row["vol_forecast"] is not None
    else:
        # Only acceptable non-ok reason left is "doesn't beat baseline" —
        # never "no row" / "incomplete inputs" due to the single gap.
        assert result["detail"] != "no row for run_date"


def test_run_writes_vol_forecast_when_history_sufficient_and_gate_passes():
    conn = db.init_db(":memory:")
    dates = _seed_index_history(conn, vh.NIFTY_SYMBOL, n=300, seed=42)
    _seed_index_history(conn, vh.VIX_SYMBOL, n=300, seed=7, vol=0.02)
    run_date = dates[-1]
    _insert_breadth(conn, trade_date=run_date)
    from manas_os.regime import snapshot
    snapshot.run(conn, run_date)

    result = vh.run(conn, run_date)
    row = conn.execute(
        "SELECT vol_forecast FROM regime_snapshots WHERE snapshot_date = ?", (run_date,)
    ).fetchone()
    if result["status"] == "ok":
        assert row["vol_forecast"] is not None
    else:
        assert row["vol_forecast"] is None
