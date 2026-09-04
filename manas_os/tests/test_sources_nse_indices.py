"""Tests for the nightly NSE index-close ingest (sources/nse_indices.py).

Covers: pure-parser fixture -> upsert, alias renaming (Nifty Bank ->
NIFTY BANK etc.), idempotent rerun, and the no-CSV skip path. Network is
never touched — ``run()`` takes an injected fetch via a fake session-like
object is avoided in favor of monkeypatching fetch_index_csv directly, which
keeps the test hermetic and fast.
"""
from manas_os import db
from manas_os.sources import nse_indices

FIXTURE_CSV = (
    "Index Name,Index Date,Open Index Value,High Index Value,Low Index Value,"
    "Closing Index Value,Points Change,Change(%),Volume,Turnover (Rs. Cr.),P/E,P/B,Div Yield\n"
    "Nifty 50,09-07-2026,23928.95,24134.7,23925.7,23962.8,80.75,.34,384795241,33799.64,20.66,3.13,1.23\n"
    "Nifty Bank,09-07-2026,56871,57464.2,56867.3,57252.45,509.85,.9,231570751,9445.81,14.38,1.84,.8\n"
    "Nifty MidSmallcap 400,09-07-2026,100,101,99,100.5,.5,.5,1,1,1,1,1\n"
    "India VIX,09-07-2026,14.68,14.68,13.0675,13.36,-1.32,-8.97,-,-,-,-,-\n"
    "Nifty Auto,09-07-2026,100,101,99,25000.1,.5,.5,1,1,1,1,1\n"
    "Some Unmapped Index,09-07-2026,1,2,0.5,42.5,.5,.5,1,1,1,1,1\n"
)


def test_parse_index_csv_aliases_known_symbols():
    rows = nse_indices.parse_index_csv(FIXTURE_CSV, "2026-07-09")
    by_symbol = {r["symbol"]: r for r in rows}
    assert by_symbol["NIFTY 50"]["close"] == 23962.8
    assert by_symbol["NIFTY BANK"]["close"] == 57252.45
    assert by_symbol["NIFTYMIDSML400"]["close"] == 100.5
    assert by_symbol["India VIX"]["close"] == 13.36
    assert by_symbol["NIFTY AUTO"]["close"] == 25000.1
    # Unmapped index passes through verbatim (raw NSE name), not dropped.
    assert by_symbol["Some Unmapped Index"]["close"] == 42.5
    assert all(r["trade_date"] == "2026-07-09" for r in rows)


def test_parse_index_csv_rejects_non_index_text():
    assert nse_indices.parse_index_csv("not,a,csv\n1,2,3\n", "2026-07-09") == []


def test_run_upserts_fixture_rows(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        monkeypatch.setattr(nse_indices, "fetch_index_csv", lambda sess, day, retries=2: FIXTURE_CSV)
        result = nse_indices.run(conn, "2026-07-09", sess=object())
        assert result["status"] == "ok"
        assert result["rows"] == 6

        nifty = conn.execute(
            "SELECT close FROM sector_index_prices WHERE symbol='NIFTY 50' AND trade_date='2026-07-09'"
        ).fetchone()
        assert nifty["close"] == 23962.8
        vix = conn.execute(
            "SELECT close FROM sector_index_prices WHERE symbol='India VIX' AND trade_date='2026-07-09'"
        ).fetchone()
        assert vix["close"] == 13.36

        run_row = conn.execute(
            "SELECT status, rows_affected FROM pipeline_runs WHERE stage='ingest_nse_indices'"
        ).fetchone()
        assert run_row["status"] == "ok"
        assert run_row["rows_affected"] == 6
    finally:
        conn.close()


def test_run_is_idempotent_on_rerun(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        monkeypatch.setattr(nse_indices, "fetch_index_csv", lambda sess, day, retries=2: FIXTURE_CSV)
        nse_indices.run(conn, "2026-07-09", sess=object())
        nse_indices.run(conn, "2026-07-09", sess=object())

        count = conn.execute(
            "SELECT COUNT(*) FROM sector_index_prices WHERE trade_date='2026-07-09'"
        ).fetchone()[0]
        assert count == 6  # no duplicate rows from the rerun

        nifty = conn.execute(
            "SELECT close FROM sector_index_prices WHERE symbol='NIFTY 50' AND trade_date='2026-07-09'"
        ).fetchone()
        assert nifty["close"] == 23962.8
    finally:
        conn.close()


def test_run_skips_when_no_csv_available(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        monkeypatch.setattr(nse_indices, "fetch_index_csv", lambda sess, day, retries=2: None)
        result = nse_indices.run(conn, "2026-07-09", sess=object())
        assert result["status"] == "skip"
        assert conn.execute("SELECT COUNT(*) FROM sector_index_prices").fetchone()[0] == 0
    finally:
        conn.close()
