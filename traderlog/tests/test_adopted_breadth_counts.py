"""W4 — traderlog/adopted/breadth_counts.py.

Pure-helper math plus a small synthetic daily_prices universe exercised
through run(), checking the JSON-blob storage shape TraderLog's schema uses
(drift from manas_os's one-column-per-metric table, documented in the module).
"""
from __future__ import annotations

import json

from traderlog.adopted import breadth_counts as bc
from traderlog.db import init_db, now_iso


def test_ema_needs_full_period_and_matches_sma_seed():
    assert bc.ema([1, 2], 5) is None
    values = [10.0] * 10
    assert bc.ema(values, 10) == 10.0


def test_net_change_pct_guards_missing_or_nonpositive_prev_close():
    assert bc.net_change_pct(110, None) is None
    assert bc.net_change_pct(110, 0) is None
    assert bc.net_change_pct(110, 100) == 0.10


def test_daily_range_pct_guards_nonpositive_low():
    assert bc.daily_range_pct(110, 0) is None
    assert round(bc.daily_range_pct(105, 100), 4) == 0.05


def _insert_price(conn, symbol, trade_date, *, close, prev_close, high=None, low=None, volume=100000):
    conn.execute(
        "INSERT OR REPLACE INTO daily_prices "
        "(symbol, trade_date, series, open, high, low, close, prev_close, volume, "
        " turnover, num_trades, delivery_pct, source, ingested_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            symbol, trade_date, "EQ", close, high if high is not None else close * 1.01,
            low if low is not None else close * 0.99, close, prev_close, volume,
            10.0, 500, 50.0, "bhavcopy", now_iso(),
        ),
    )


def test_run_writes_counts_json_blob_and_universe_size(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    # Two symbols, one day: FOO breaks out +5% (>4% up_4pct AND >=4% BO band),
    # BAR is flat.
    _insert_price(conn, "FOO", "2025-04-01", close=105.0, prev_close=100.0, high=106.0, low=99.0)
    _insert_price(conn, "BAR", "2025-04-01", close=100.2, prev_close=100.0, high=100.5, low=99.8)
    conn.commit()

    result = bc.run(conn, "2025-04-01")
    assert result["status"] == "ok"

    row = conn.execute(
        "SELECT trade_date, counts_json, universe_size FROM breadth_counts WHERE trade_date='2025-04-01'"
    ).fetchone()
    assert row is not None
    assert row["universe_size"] == 2
    counts = json.loads(row["counts_json"])
    assert counts["total_universe"] == 2
    assert counts["up_4pct"] == 1  # FOO
    assert counts["down_4pct"] == 0
    assert set(counts) == set(bc._COUNT_COLS)


def test_run_is_idempotent_upsert(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    _insert_price(conn, "FOO", "2025-04-01", close=100.0, prev_close=100.0)
    conn.commit()

    bc.run(conn, "2025-04-01")
    bc.run(conn, "2025-04-01")
    total = conn.execute("SELECT COUNT(*) FROM breadth_counts").fetchone()[0]
    assert total == 1


def test_run_skips_date_with_no_eligible_universe(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    result = bc.run(conn, "2025-04-01")
    assert result["status"] == "skip"
    assert conn.execute("SELECT COUNT(*) FROM breadth_counts").fetchone()[0] == 0
    run_row = conn.execute(
        "SELECT status FROM pipeline_runs WHERE stage='adopted.breadth_counts'"
    ).fetchone()
    assert run_row["status"] == "skip"


def test_accumulate_symbol_flags_breakout_sustained_close(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    # high >= prev_close*1.04 and close near the high -> breakout_sustained.
    _insert_price(conn, "FOO", "2025-04-01", close=106.0, prev_close=100.0, high=106.5, low=99.5)
    conn.commit()
    counts = bc.compute_counts(conn, "2025-04-01")
    assert counts["breakouts"] == 1
    assert counts["breakout_sustained"] == 1
    assert counts["breakout_failed"] == 0
