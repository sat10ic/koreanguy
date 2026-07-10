"""Tests for WAVE_J7 task 2/3: counterfactual_candidates/counterfactual_outcomes
plumbing (backtest/replay.py persist_counterfactual, scanner/outcomes.py
backfill_counterfactual_outcomes). Purity guard: persist_counterfactual must
NEVER write scan_candidates/candidates/outcomes/refusals -- it is a strictly
additive, separate cohort table (WAVE_J_SPEC.md task 2)."""
from __future__ import annotations

from datetime import date, timedelta

from manas_os import db
from manas_os.backtest import replay as replay_mod
from manas_os.scanner import outcomes as scanner_outcomes


def _dates(n, start="2026-03-02"):
    d0 = date.fromisoformat(start)
    out, d = [], d0
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def _seed_prices(conn, symbol, closes_by_date):
    rows = [(symbol, d, "EQ", c, c + 0.5, c - 0.5, c, c - 0.1, 500000, 100, 60.0, "test")
            for d, c in closes_by_date.items()]
    conn.executemany(
        "INSERT OR REPLACE INTO daily_prices (symbol, trade_date, series, open, high, low, "
        "close, prev_close, volume, delivery_qty, delivery_pct, source) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()


def _table_count(conn, table):
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_persist_counterfactual_never_writes_real_tables(monkeypatch, tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        days = _dates(15)
        closes = {d: 100.0 for d in days}
        closes[days[10]] = 110.0
        _seed_prices(conn, "AAA", closes)

        before_scan = _table_count(conn, "scan_candidates")
        before_cand = _table_count(conn, "candidates")
        before_out = _table_count(conn, "outcomes")
        before_refusals = _table_count(conn, "refusals") if _has_table(conn, "refusals") else 0

        fake_rows = [{
            "scan_date": days[0], "symbol": "AAA", "setup_family": "pattern",
            "entry": 100.0, "stop": 95.0, "failed_gate": None,
        }]
        monkeypatch.setattr(
            replay_mod, "_counterfactual_session_candidates",
            lambda conn, session_date: fake_rows if session_date == days[0] else [],
        )

        result = replay_mod.persist_counterfactual(conn, days[0], days[0])
        assert result["status"] == "ok"
        assert result["candidates_persisted"] == 1

        assert _table_count(conn, "scan_candidates") == before_scan
        assert _table_count(conn, "candidates") == before_cand
        assert _table_count(conn, "outcomes") == before_out
        if _has_table(conn, "refusals"):
            assert _table_count(conn, "refusals") == before_refusals

        row = conn.execute(
            "SELECT scan_date, symbol, setup_family, entry, stop, failed_gate "
            "FROM counterfactual_candidates"
        ).fetchone()
        assert tuple(row) == (days[0], "AAA", "pattern", 100.0, 95.0, None)
    finally:
        conn.close()


def _has_table(conn, name):
    return conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def test_persist_counterfactual_idempotent(monkeypatch, tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        days = _dates(15)
        closes = {d: 100.0 for d in days}
        closes[days[10]] = 110.0
        _seed_prices(conn, "AAA", closes)

        fake_rows = [{
            "scan_date": days[0], "symbol": "AAA", "setup_family": "pattern",
            "entry": 100.0, "stop": 95.0, "failed_gate": "fresh-leg",
        }]
        monkeypatch.setattr(
            replay_mod, "_counterfactual_session_candidates",
            lambda conn, session_date: fake_rows if session_date == days[0] else [],
        )

        r1 = replay_mod.persist_counterfactual(conn, days[0], days[0])
        n1 = _table_count(conn, "counterfactual_candidates")
        o1 = _table_count(conn, "counterfactual_outcomes")

        r2 = replay_mod.persist_counterfactual(conn, days[0], days[0])
        n2 = _table_count(conn, "counterfactual_candidates")
        o2 = _table_count(conn, "counterfactual_outcomes")

        assert n1 == n2 == 1
        assert o1 == o2 == 1  # one horizon (10) row, not duplicated
        assert r1["candidates_persisted"] == r2["candidates_persisted"] == 1
    finally:
        conn.close()


def test_backfill_counterfactual_outcomes_managed_exit(tmp_path):
    """Direct fixture on counterfactual_candidates (bypassing the scan
    machinery) -- verifies the managed-exit walk (stop-out) computes matching
    the SAME model backfill_forward_returns uses for the real cohort."""
    conn = db.init_db(tmp_path / "manas.db")
    try:
        days = _dates(15)
        closes = {d: 100.0 for d in days}
        # entry fill = next open after scan_date (days[0] -> days[1] open=100)
        # then stop-out: low touches 90 on days[3]
        closes[days[3]] = 100.0
        _seed_prices(conn, "AAA", closes)
        conn.execute(
            "UPDATE daily_prices SET low=90.0 WHERE symbol='AAA' AND trade_date=?",
            (days[3],),
        )
        conn.commit()

        scanner_outcomes.ensure_counterfactual_schema(conn)
        conn.execute(
            "INSERT INTO counterfactual_candidates (scan_date, symbol, setup_family, "
            "entry, stop, regime, failed_gate) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (days[0], "AAA", "pattern", 100.0, 95.0, "RISK_ON", None),
        )
        conn.commit()

        written = scanner_outcomes.backfill_counterfactual_outcomes(conn, horizon=10)
        assert written == 1
        row = conn.execute(
            "SELECT status, exit_reason, managed_r FROM counterfactual_outcomes "
            "WHERE scan_date=? AND symbol='AAA' AND setup_family='pattern' AND horizon=10",
            (days[0],),
        ).fetchone()
        assert row[0] == "complete"
        assert row[1] in ("stop", "gap_through_stop")
        assert row[2] is not None and row[2] <= -0.9  # stop-out, ~ -1R (slippage haircut)

        # idempotent re-run: same row, no duplicate
        written2 = scanner_outcomes.backfill_counterfactual_outcomes(conn, horizon=10)
        assert written2 == 1
        n = conn.execute("SELECT COUNT(*) FROM counterfactual_outcomes").fetchone()[0]
        assert n == 1
    finally:
        conn.close()
