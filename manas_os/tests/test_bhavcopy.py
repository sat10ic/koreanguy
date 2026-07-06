"""Tests for the bhavcopy ingestion adapter against a REAL NSE file."""
from pathlib import Path

import pytest

from manas_os import db
from manas_os.sources import bhavcopy

_REAL_DATE = "2025-07-01"
_REAL_FILE = bhavcopy.bhavcopy_dir() / bhavcopy.filename_for(_REAL_DATE)


def test_filename_mapping():
    assert bhavcopy.filename_for("2025-07-01") == "cm01JUL2025bhav.csv"
    assert bhavcopy.filename_for("2026-01-02") == "cm02JAN2026bhav.csv"


def test_filename_candidates_covers_both_source_names():
    # NSE ships the same payload under two names (girish 'cm…' vs NSE-Data-bank
    # 'sec_bhavdata_full_…'); ingest must try both or recent data is invisible.
    cands = bhavcopy.filename_candidates("2026-04-01")
    assert "cm01APR2026bhav.csv" in cands
    assert "sec_bhavdata_full_01042026.csv" in cands


def test_run_finds_sec_bhavdata_full_name(tmp_path, monkeypatch):
    # A file present ONLY under the sec_bhavdata_full name must still ingest.
    directory = tmp_path
    monkeypatch.setattr(bhavcopy, "bhavcopy_dir", lambda: directory)
    header = ("SYMBOL, SERIES, DATE1, PREV_CLOSE, OPEN_PRICE, HIGH_PRICE, LOW_PRICE, "
              "LAST_PRICE, CLOSE_PRICE, AVG_PRICE, TTL_TRD_QNTY, TURNOVER_LACS, "
              "NO_OF_TRADES, DELIV_QTY, DELIV_PER")
    body = "ABC, EQ, 01-Apr-2026, 100, 101, 105, 99, 104, 104, 102, 1000, 10.4, 50, 800, 80.00"
    (directory / "sec_bhavdata_full_01042026.csv").write_text(header + "\n" + body, encoding="utf-8")
    conn = db.init_db(":memory:")
    n = bhavcopy.run(conn, "2026-04-01")
    assert n == 1
    row = conn.execute(
        "SELECT symbol, close, delivery_pct FROM daily_prices WHERE trade_date='2026-04-01'"
    ).fetchone()
    assert row["symbol"] == "ABC"
    assert row["delivery_pct"] == 80.0


@pytest.mark.skipif(not _REAL_FILE.exists(), reason="real bhavcopy file absent")
def test_parse_real_file():
    records = bhavcopy.parse_bhavcopy(_REAL_FILE.read_text(encoding="utf-8"))
    # >1000 rows
    assert len(records) > 1000

    # An EQ row has a numeric delivery_pct.
    eq = [r for r in records if r["series"] == "EQ"]
    assert eq, "no EQ rows parsed"
    assert any(isinstance(r["delivery_pct"], float) for r in eq)
    sample = next(r for r in eq if r["delivery_pct"] is not None)
    assert sample["delivery_pct"] is not None
    assert sample["trade_date"] == _REAL_DATE
    assert sample["source"] == "bhavcopy"

    # A non-EQ '-' delivery becomes NULL (None). GS/BE series carry '-'.
    non_eq_null = [
        r for r in records
        if r["series"] in ("GS", "BE") and r["delivery_qty"] is None
    ]
    assert non_eq_null, "expected at least one non-EQ row with NULL delivery"
    assert non_eq_null[0]["delivery_pct"] is None


@pytest.mark.skipif(not _REAL_FILE.exists(), reason="real bhavcopy file absent")
def test_run_idempotent(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        n1 = bhavcopy.run(conn, _REAL_DATE)
        assert n1 > 1000
        count1 = conn.execute("SELECT COUNT(*) FROM daily_prices").fetchone()[0]

        # Second run: INSERT OR REPLACE on PK → 0 NET new rows.
        n2 = bhavcopy.run(conn, _REAL_DATE)
        count2 = conn.execute("SELECT COUNT(*) FROM daily_prices").fetchone()[0]
        assert count2 == count1, "second run changed net row count"
        assert n2 == n1

        # Two pipeline_runs rows recorded.
        runs = conn.execute(
            "SELECT status FROM pipeline_runs WHERE stage='ingest_bhavcopy'"
        ).fetchall()
        assert len(runs) == 2
        assert all(r[0] == "ok" for r in runs)
    finally:
        conn.close()


def test_run_missing_file_skips(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        n = bhavcopy.run(conn, "1999-01-01")  # no such file
        assert n == 0
        row = conn.execute(
            "SELECT status FROM pipeline_runs WHERE stage='ingest_bhavcopy'"
        ).fetchone()
        assert row[0] == "skip"
    finally:
        conn.close()
