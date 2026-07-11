"""Tests for manas_os.alpha.symbol_identity — point-in-time identity/universe
helpers built from daily_prices only (no external listing feed).
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

import pytest

from manas_os.alpha.symbol_identity import (
    DELIST_GAP_SESSIONS,
    build_symbol_identity,
    listing_age_sessions,
    run,
    universe_on,
)


def _conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute(
        "CREATE TABLE daily_prices(symbol TEXT, trade_date TEXT, series TEXT, close REAL)"
    )
    c.execute(
        "CREATE TABLE pipeline_runs(run_id INTEGER PRIMARY KEY AUTOINCREMENT, run_date TEXT, "
        "stage TEXT, source TEXT, status TEXT, rows_affected INTEGER, duration_s REAL, "
        "detail TEXT, ran_at TEXT DEFAULT (datetime('now')))"
    )
    return c


def _dates(start: str, n: int) -> list[str]:
    """n consecutive calendar days from start (fine for a synthetic trading calendar)."""
    d0 = date.fromisoformat(start)
    return [(d0 + timedelta(days=i)).isoformat() for i in range(n)]


def _insert(conn, symbol, dates):
    conn.executemany(
        "INSERT INTO daily_prices(symbol, trade_date, series, close) VALUES (?,?,?,100)",
        [(symbol, d, "EQ") for d in dates],
    )


def test_build_symbol_identity_first_last_seen_and_session_count():
    conn = _conn()
    all_dates = _dates("2026-01-01", 60)
    # AAA trades the whole panel; a 2024-style IPO (ZZZ) only appears late.
    _insert(conn, "AAA", all_dates)
    _insert(conn, "ZZZ_IPO", all_dates[-5:])
    conn.commit()

    n = build_symbol_identity(conn)
    assert n == 2

    row = conn.execute("SELECT * FROM symbol_identity WHERE symbol='ZZZ_IPO'").fetchone()
    assert row["first_seen"] == all_dates[-5]
    assert row["last_seen"] == all_dates[-1]
    assert row["session_count"] == 5
    assert row["delisted"] == 0  # still trading at panel end

    row_aaa = conn.execute("SELECT * FROM symbol_identity WHERE symbol='AAA'").fetchone()
    assert row_aaa["session_count"] == 60


def test_build_symbol_identity_delisted_flag_from_trailing_gap():
    conn = _conn()
    all_dates = _dates("2026-01-01", 60)
    _insert(conn, "AAA", all_dates)  # trades through panel end
    _insert(conn, "DELISTED_CO", all_dates[:20])  # stops trading 40 sessions before panel end
    conn.commit()

    build_symbol_identity(conn)

    row = conn.execute("SELECT * FROM symbol_identity WHERE symbol='DELISTED_CO'").fetchone()
    assert row["trailing_gap_sessions"] == 40
    assert row["delisted"] == 1

    row_aaa = conn.execute("SELECT * FROM symbol_identity WHERE symbol='AAA'").fetchone()
    assert row_aaa["delisted"] == 0
    assert row_aaa["trailing_gap_sessions"] == 0


def test_build_symbol_identity_boundary_at_gap_threshold():
    conn = _conn()
    all_dates = _dates("2026-01-01", 60)
    _insert(conn, "AAA", all_dates)
    # Stops exactly DELIST_GAP_SESSIONS sessions before the panel end -> not yet delisted.
    boundary_dates = all_dates[: len(all_dates) - DELIST_GAP_SESSIONS]
    _insert(conn, "EXACT_BOUNDARY", boundary_dates)
    conn.commit()

    build_symbol_identity(conn)
    row = conn.execute("SELECT * FROM symbol_identity WHERE symbol='EXACT_BOUNDARY'").fetchone()
    assert row["trailing_gap_sessions"] == DELIST_GAP_SESSIONS
    assert row["delisted"] == 0  # > threshold required, not >=


def test_build_symbol_identity_is_idempotent_full_rebuild():
    conn = _conn()
    all_dates = _dates("2026-01-01", 30)
    _insert(conn, "AAA", all_dates)
    conn.commit()

    n1 = build_symbol_identity(conn)
    n2 = build_symbol_identity(conn)
    assert n1 == n2 == 1
    assert conn.execute("SELECT COUNT(*) FROM symbol_identity").fetchone()[0] == 1


def test_listing_age_sessions_is_point_in_time():
    conn = _conn()
    all_dates = _dates("2026-01-01", 30)
    _insert(conn, "AAA", all_dates)
    conn.commit()

    # Only 10 sessions have occurred as of the 10th date, even though 30 exist in total.
    as_of = all_dates[9]
    assert listing_age_sessions(conn, "AAA", as_of) == 10
    assert listing_age_sessions(conn, "AAA", all_dates[-1]) == 30
    assert listing_age_sessions(conn, "AAA", "2020-01-01") is None


def test_universe_on_excludes_symbol_not_yet_listed():
    conn = _conn()
    all_dates = _dates("2026-01-01", 40)
    _insert(conn, "OLDCO", all_dates)
    _insert(conn, "NEW_IPO_2026", all_dates[-3:])  # lists near the end of the panel
    conn.commit()

    # Before the IPO's first session, it must not appear in the point-in-time universe.
    early_universe = universe_on(conn, all_dates[10])
    assert "OLDCO" in early_universe
    assert "NEW_IPO_2026" not in early_universe

    # From its first session onward, it is included.
    late_universe = universe_on(conn, all_dates[-1])
    assert "NEW_IPO_2026" in late_universe


def test_universe_on_excludes_delisted_symbol_and_uses_only_data_up_to_as_of():
    conn = _conn()
    all_dates = _dates("2026-01-01", 80)
    _insert(conn, "SURVIVOR", all_dates)
    # Stops trading with 40 sessions still remaining in the (unseen future) panel.
    _insert(conn, "GONE", all_dates[:20])
    conn.commit()

    # Immediately after GONE's last session, it is still within the universe
    # (not yet 30 sessions since it last traded, as of that date).
    just_after = universe_on(conn, all_dates[25])
    assert "GONE" in just_after

    # Far enough past its last session (as of a date that only sees GONE's
    # first 20 sessions), it should be excluded once the point-in-time gap
    # exceeds the threshold.
    far_after = universe_on(conn, all_dates[55])
    assert "GONE" not in far_after
    assert "SURVIVOR" in far_after


def test_universe_on_never_reads_beyond_as_of_date():
    """Guardrail: universe_on(d) must be blind to any row with trade_date > d."""
    conn = _conn()
    all_dates = _dates("2026-01-01", 40)
    _insert(conn, "AAA", all_dates)
    conn.commit()

    as_of = all_dates[15]
    universe = universe_on(conn, as_of)
    assert "AAA" in universe

    # Prove it by deleting all future rows and re-running: same answer.
    conn.execute("DELETE FROM daily_prices WHERE trade_date > ?", (as_of,))
    conn.commit()
    universe_after_delete = universe_on(conn, as_of)
    assert universe_after_delete == universe


def test_universe_on_empty_panel_returns_empty_list():
    conn = _conn()
    assert universe_on(conn, "2026-01-01") == []


def test_run_stage_is_idempotent_and_logs_pipeline_run():
    conn = _conn()
    all_dates = _dates("2026-01-01", 10)
    _insert(conn, "AAA", all_dates)
    conn.commit()

    result1 = run(conn, all_dates[-1])
    assert result1["status"] == "ok"
    assert result1["rows"] == 1

    result2 = run(conn, all_dates[-1])
    assert result2["status"] == "ok"
    assert result2["rows"] == 1
    assert conn.execute("SELECT COUNT(*) FROM symbol_identity").fetchone()[0] == 1

    logged = conn.execute(
        "SELECT COUNT(*) FROM pipeline_runs WHERE stage='alpha_symbol_identity'"
    ).fetchone()[0]
    assert logged == 2


def test_run_stage_never_raises_on_missing_table():
    """Failure-safe like the other alpha stages: must not break run-eod."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE pipeline_runs(run_id INTEGER PRIMARY KEY AUTOINCREMENT, run_date TEXT, "
        "stage TEXT, source TEXT, status TEXT, rows_affected INTEGER, duration_s REAL, "
        "detail TEXT, ran_at TEXT DEFAULT (datetime('now')))"
    )
    # No daily_prices table at all -> build_symbol_identity must fail gracefully.
    result = run(conn, "2026-01-01")
    assert result["status"] == "skip"
