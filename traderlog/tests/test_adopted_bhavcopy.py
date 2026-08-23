"""W4 — traderlog/adopted/bhavcopy.py.

Covers the defensive CSV parsing (leading spaces, '-' delivery), the two
on-disk filename conventions, date discovery, and idempotent ingest into
daily_prices with TraderLog's own (narrower) column set.
"""
from __future__ import annotations

from traderlog.adopted import bhavcopy
from traderlog.db import init_db


_HEADER = (
    "SYMBOL, SERIES, DATE1, PREV_CLOSE, OPEN_PRICE, HIGH_PRICE, LOW_PRICE, "
    "LAST_PRICE, CLOSE_PRICE, AVG_PRICE, TTL_TRD_QNTY, TURNOVER_LACS, "
    "NO_OF_TRADES, DELIV_QTY, DELIV_PER"
)


def _row(symbol="FOO", series="EQ", date1="01-Apr-2025", deliv_qty="100", deliv_per="50.0"):
    return (
        f"{symbol}, {series}, {date1}, 100.0, 101.0, 105.0, 99.0, 102.0, 102.0, "
        f"101.5, 10000, 50.0, 200, {deliv_qty}, {deliv_per}"
    )


def test_parse_bhavcopy_handles_leading_spaces_and_dash_delivery():
    text = _HEADER + "\n" + _row() + "\n" + _row(symbol="BOND", series="GS", deliv_qty="-", deliv_per="-")
    rows = bhavcopy.parse_bhavcopy(text)
    assert len(rows) == 2
    assert rows[0]["symbol"] == "FOO"
    assert rows[0]["trade_date"] == "2025-04-01"
    assert rows[0]["delivery_pct"] == 50.0
    assert rows[1]["symbol"] == "BOND"
    assert rows[1]["delivery_qty"] is None
    assert rows[1]["delivery_pct"] is None


def test_parse_bhavcopy_skips_blank_symbol_rows():
    text = _HEADER + "\n" + _row() + "\n,,,,,,,,,,,,,,\n"
    rows = bhavcopy.parse_bhavcopy(text)
    assert len(rows) == 1


def test_parse_bhavcopy_missing_column_raises():
    bad_header = "SYMBOL, SERIES, DATE1\n"
    try:
        bhavcopy.parse_bhavcopy(bad_header + "FOO, EQ, 01-Apr-2025\n")
    except ValueError as exc:
        assert "missing columns" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_filename_candidates_returns_both_naming_conventions():
    cands = bhavcopy.filename_candidates("2025-04-01")
    assert "cm01APR2025bhav.csv" in cands
    assert "sec_bhavdata_full_01042025.csv" in cands


def test_discover_dates_dedupes_across_both_conventions(tmp_path):
    (tmp_path / "cm01APR2025bhav.csv").write_text("x", encoding="utf-8")
    (tmp_path / "sec_bhavdata_full_01042025.csv").write_text("x", encoding="utf-8")  # same date, other name
    (tmp_path / "sec_bhavdata_full_02042025.csv").write_text("x", encoding="utf-8")  # different date
    (tmp_path / "not_a_bhavcopy.txt").write_text("x", encoding="utf-8")
    dates = bhavcopy.discover_dates(tmp_path)
    assert dates == ["2025-04-01", "2025-04-02"]


def test_run_upserts_daily_prices_and_is_idempotent(tmp_path, monkeypatch):
    conn = init_db(tmp_path / "traderlog.db")
    bh_dir = tmp_path / "bhavcopy"
    bh_dir.mkdir()
    (bh_dir / "cm01APR2025bhav.csv").write_text(
        _HEADER + "\n" + _row() + "\n" + _row(symbol="BAR") + "\n", encoding="utf-8"
    )
    monkeypatch.setattr(bhavcopy, "bhavcopy_dir", lambda: bh_dir)

    n1 = bhavcopy.run(conn, "2025-04-01")
    assert n1 == 2
    total = conn.execute("SELECT COUNT(*) FROM daily_prices").fetchone()[0]
    assert total == 2

    # Re-run: idempotent, no duplicate rows (PK is symbol, trade_date).
    n2 = bhavcopy.run(conn, "2025-04-01")
    assert n2 == 2
    total2 = conn.execute("SELECT COUNT(*) FROM daily_prices").fetchone()[0]
    assert total2 == 2

    row = conn.execute(
        "SELECT symbol, series, close, delivery_pct, source FROM daily_prices WHERE symbol='FOO'"
    ).fetchone()
    assert dict(row) == {
        "symbol": "FOO", "series": "EQ", "close": 102.0, "delivery_pct": 50.0, "source": "bhavcopy",
    }

    runs = conn.execute(
        "SELECT status, rows FROM pipeline_runs WHERE stage='adopted.bhavcopy'"
    ).fetchall()
    assert len(runs) == 2
    assert all(r["status"] == "ok" and r["rows"] == 2 for r in runs)


def test_run_missing_file_skips_and_logs(tmp_path, monkeypatch):
    conn = init_db(tmp_path / "traderlog.db")
    bh_dir = tmp_path / "bhavcopy_empty"
    bh_dir.mkdir()
    monkeypatch.setattr(bhavcopy, "bhavcopy_dir", lambda: bh_dir)

    n = bhavcopy.run(conn, "2025-04-01")
    assert n == 0
    row = conn.execute(
        "SELECT status, detail FROM pipeline_runs WHERE stage='adopted.bhavcopy'"
    ).fetchone()
    assert row["status"] == "skip"
    assert "file not found" in row["detail"]


def test_run_rejects_csv_whose_internal_date_differs_from_requested_date(tmp_path, monkeypatch):
    conn = init_db(tmp_path / "traderlog.db")
    bh_dir = tmp_path / "bhavcopy"
    bh_dir.mkdir()
    # The filename says 01 Apr, but DATE1 says 02 Apr.  Persisting it would
    # silently put a different session into the requested pipeline run.
    (bh_dir / "cm01APR2025bhav.csv").write_text(
        _HEADER + "\n" + _row(date1="02-Apr-2025") + "\n", encoding="utf-8"
    )
    monkeypatch.setattr(bhavcopy, "bhavcopy_dir", lambda: bh_dir)

    try:
        bhavcopy.run(conn, "2025-04-01")
    except ValueError as exc:
        assert "DATE1 mismatch" in str(exc)
    else:
        raise AssertionError("expected DATE1 mismatch to fail")

    assert conn.execute("SELECT COUNT(*) FROM daily_prices").fetchone()[0] == 0
    run = conn.execute(
        "SELECT status, detail FROM pipeline_runs WHERE stage='adopted.bhavcopy'"
    ).fetchone()
    assert run["status"] == "fail"
    assert "DATE1 mismatch" in run["detail"]


def test_backfill_iterates_discovered_dates(tmp_path, monkeypatch):
    conn = init_db(tmp_path / "traderlog.db")
    bh_dir = tmp_path / "bhavcopy"
    bh_dir.mkdir()
    (bh_dir / "cm01APR2025bhav.csv").write_text(
        _HEADER + "\n" + _row(date1="01-Apr-2025") + "\n", encoding="utf-8"
    )
    (bh_dir / "cm02APR2025bhav.csv").write_text(
        _HEADER + "\n" + _row(date1="02-Apr-2025") + "\n", encoding="utf-8"
    )
    monkeypatch.setattr(bhavcopy, "bhavcopy_dir", lambda: bh_dir)

    result = bhavcopy.backfill(conn)
    assert result == {"dates": 2, "rows": 2, "failed": []}
    total = conn.execute("SELECT COUNT(*) FROM daily_prices").fetchone()[0]
    assert total == 2
