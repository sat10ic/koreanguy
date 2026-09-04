"""Tests for the breadth-sheet ingestion adapter (manas_os.sources.breadth_sheet).

No network: parse against the committed fixture; upsert against an in-memory DB.
"""
from pathlib import Path

from manas_os import db
from manas_os.sources import breadth_sheet as bs

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "breadth_sample.csv"


def _rows():
    return bs.parse_breadth_csv(_FIXTURE.read_text(encoding="utf-8"))


def test_parses_three_rows():
    rows = _rows()
    assert len(rows) == 3


def test_dates_normalized_to_iso():
    dates = [r["trade_date"] for r in _rows()]
    assert dates == ["2026-01-02", "2026-01-05", "2026-01-06"]


def test_typed_values_and_comma_percent_stripping():
    r0 = _rows()[0]
    assert r0["advances"] == 1320          # "1,320" -> comma stripped, int
    assert r0["declines"] == 680
    assert r0["up_4pct"] == 120
    assert r0["down_4pct"] == 30
    assert r0["pct_above_10dma"] == 62.5   # "62.5%" -> % stripped, float
    assert r0["pct_above_20dma"] == 58.1
    assert r0["nifty"] == 23450.75         # "23,450.75" -> float
    assert r0["nifty_chg_pct"] == 0.82
    assert r0["source"] == "breadth_sheet"
    # types
    assert isinstance(r0["advances"], int)
    assert isinstance(r0["pct_above_10dma"], float)


def test_negative_nifty_change_parsed():
    r1 = _rows()[1]
    assert r1["nifty_chg_pct"] == -0.60
    assert r1["nifty"] == 23310.20


def test_upsert_is_idempotent():
    conn = db.init_db(":memory:")
    rows = _rows()
    assert bs.upsert_rows(conn, rows) == 3
    conn.commit()
    # re-upsert same rows -> still 3 total (PK conflict updates in place)
    bs.upsert_rows(conn, rows)
    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM breadth_daily").fetchone()[0]
    assert total == 3
    got = conn.execute(
        "SELECT up_4pct, pct_above_10dma FROM breadth_daily WHERE trade_date='2026-01-02'"
    ).fetchone()
    assert got["up_4pct"] == 120
    assert got["pct_above_10dma"] == 62.5
    conn.close()
