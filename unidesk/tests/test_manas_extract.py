"""Read-only manas.db extract: index history + dated universe snapshots."""
import sqlite3
from pathlib import Path

import pytest

from unidesk.momentum.data.manas_extract import (
    extract_index_rows, extract_universe_rows, merge_index_rows, write_index_extract,
)


def _mini_db(tmp_path: Path) -> Path:
    db = tmp_path / "mini.db"
    con = sqlite3.connect(db)
    con.execute(
        "CREATE TABLE sector_index_prices "
        "(symbol TEXT, trade_date TEXT, open REAL, high REAL, low REAL, close REAL)"
    )
    con.executemany(
        "INSERT INTO sector_index_prices VALUES (?,?,?,?,?,?)",
        [
            ("NIFTY 50", "2021-06-01", 15000, 15100, 14900, 15050),
            ("India VIX", "2021-06-01", 15, 16, 14, 15.5),
            ("NIFTY MIDCAP 150", "2024-07-08", 18000, 18100, 17900, 18050),
            ("IGNORE ME", "2024-07-08", 1, 1, 1, 1),
        ],
    )
    con.execute(
        "CREATE TABLE universe "
        "(symbol TEXT, as_of_date TEXT, series TEXT, sector TEXT, "
        "industry TEXT, is_tradeable INTEGER)"
    )
    con.executemany(
        "INSERT INTO universe VALUES (?,?,?,?,?,?)",
        [
            ("TRENT", "2026-08-20", "EQ", "RETAIL", "Retail", 1),
            ("TRENT", "2026-07-10", "EQ", "RETAIL", "Retail", 1),
            ("Z", "2026-08-20", "EQ", None, None, 0),
        ],
    )
    con.commit()
    con.close()
    return db


def test_extract_index_maps_symbols_and_skips_unknown(tmp_path):
    rows = extract_index_rows(_mini_db(tmp_path))
    ids = {r["index_id"] for r in rows}
    assert ids == {"NIFTY_50", "INDIA_VIX", "NIFTY_MIDCAP_150"}
    by = {r["index_id"]: r for r in rows}
    assert by["NIFTY_50"]["session"] == "2021-06-01"
    assert by["NIFTY_50"]["close"] == 15050
    assert by["NIFTY_50"]["source_tier"] == "MANAS_SECTOR_INDEX_PRICES"


def test_extract_universe_keeps_as_of_dates(tmp_path):
    rows = extract_universe_rows(_mini_db(tmp_path))
    assert len(rows) == 3
    dates = {r["as_of_date"] for r in rows}
    assert dates == {"2026-08-20", "2026-07-10"}
    # same symbol on two dates is two PIT rows, not a back-fill
    trent = [r for r in rows if r["symbol"] == "TRENT"]
    assert {r["as_of_date"] for r in trent} == {"2026-08-20", "2026-07-10"}


def test_overlay_wins_on_newer_session():
    primary = [{"session": "2026-08-20", "index_id": "NIFTY_50", "close": 1}]
    overlay = [{"session": "2026-08-28", "index_id": "NIFTY_50", "close": 2},
               {"session": "2026-08-20", "index_id": "NIFTY_50", "close": 9}]
    merged = merge_index_rows(primary, overlay)
    by = {(r["session"], r["index_id"]): r["close"] for r in merged}
    assert by[("2026-08-20", "NIFTY_50")] == 9
    assert by[("2026-08-28", "NIFTY_50")] == 2


def test_write_extract_roundtrip(tmp_path):
    db = _mini_db(tmp_path)
    dest = tmp_path / "idx.parquet"
    stats = write_index_extract(dest, db=db)
    assert stats["rows"] == 3
    assert "NIFTY_50" in stats["index_ids"]
    assert dest.exists()


def test_live_manas_index_extract_smoke():
    db = Path(__file__).resolve().parents[2] / "manas_os" / "data" / "manas.db"
    if not db.exists() or db.stat().st_size < 1000:
        pytest.skip("manas.db not present")
    rows = extract_index_rows(db)
    ids = {r["index_id"] for r in rows}
    assert "NIFTY_50" in ids and "INDIA_VIX" in ids
    nifty = [r for r in rows if r["index_id"] == "NIFTY_50"]
    assert len(nifty) >= 200  # enough for SMA200
    sessions = sorted(r["session"] for r in nifty)
    assert sessions[0] <= "2021-07-01"
