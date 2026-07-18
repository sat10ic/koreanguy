"""Tests for the ChartsMaze reader + freshness run + history migration."""
from pathlib import Path

import pytest

from manas_os import db
from manas_os.sources import chartsmaze, chartsmaze_migrate

_REAL_DATE = "2026-07-04"
# The real ChartsMaze history still lives in the legacy tree (migration is a
# separate manual step). Point the readers there so we exercise real files.
_LEGACY_CM = (Path(__file__).resolve().parents[2] / "legacy" / "SwingEdge"
              / "data" / "chartsmaze").resolve()
_REAL_FOLDER = _LEGACY_CM / _REAL_DATE


@pytest.fixture
def legacy_cm(monkeypatch):
    """Repoint chartsmaze_dir() at the real legacy history for this test."""
    monkeypatch.setattr(chartsmaze, "chartsmaze_dir", lambda: _LEGACY_CM)


@pytest.mark.skipif(not _REAL_FOLDER.is_dir(), reason="real chartsmaze folder absent")
def test_read_market_breadth(legacy_cm):
    df = chartsmaze.read_market_breadth(_REAL_DATE)
    assert not df.empty
    # First column is the metric label (transposed layout); BOM stripped.
    assert df.columns[0] == "Type of Info"


@pytest.mark.skipif(not _REAL_FOLDER.is_dir(), reason="real chartsmaze folder absent")
def test_read_sector_analytics(legacy_cm):
    df = chartsmaze.read_sector_analytics(_REAL_DATE, "Relative Strength", "sectors")
    assert list(df.columns) == ["name", "pct"]
    assert not df.empty


@pytest.mark.skipif(not _REAL_FOLDER.is_dir(), reason="real chartsmaze folder absent")
def test_run_records_freshness(legacy_cm, tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        count = chartsmaze.run(conn, _REAL_DATE)
        assert count > 0
        row = conn.execute(
            "SELECT status, rows_affected FROM pipeline_runs "
            "WHERE stage='ingest_chartsmaze'"
        ).fetchone()
        assert row[0] == "ok"
        assert row[1] == count
    finally:
        conn.close()


# ── parse_industry_analytics — pure parser ──────────────────────────────────
# Synthetic CSV echoing the real industry-analytics shape (BOM, % suffixes,
# messy spacing). Verifies BOM strip, substring header match, typing.
_INDUSTRY_CSV = (
    "\ufeffBasic Industry,Industry 1D Performance(%),Industry 1W Performance(%),"
    "Industry 1M Performance(%),Industry 3M Performance(%),"
    "Industry 1M Performance Rank,Industry 3M Performance Rank,"
    "Number of Stocks,Group Market Cap,Industry % from 52W High\n"
    "Investment Banking & Broking,0.40,2.37,6.31,15.84,44,51,42,454000,9.8\n"
    "Electrical - Power Equipment,-3.92,-4.66,-3.96,19.55,101,39,70,1227695,9.7\n"
    ",x,y,z\n"  # blank name → skipped
)


def test_parse_industry_analytics_pure():
    rows = chartsmaze.parse_industry_analytics(_INDUSTRY_CSV)
    assert len(rows) == 2  # blank-name row skipped
    first = rows[0]
    assert first["name"] == "Investment Banking & Broking"
    assert first["perf_1d"] == 0.4
    assert first["perf_1m"] == 6.31
    assert first["rank_3m"] == 51
    assert first["num_stocks"] == 42
    assert first["market_cap_cr"] == 454000.0
    assert first["pct_from_52w_high"] == 9.8
    # negative perf parses with sign intact
    assert rows[1]["perf_1d"] == -3.92


@pytest.mark.skipif(not _REAL_FOLDER.is_dir(), reason="real chartsmaze folder absent")
def test_read_industry_analytics_real(legacy_cm):
    df = chartsmaze.read_industry_analytics(_REAL_DATE)
    assert not df.empty
    assert {"name", "perf_1m", "perf_3m", "num_stocks"} <= set(df.columns)
    # Sorted by ChartsMaze rank in the file; just sanity-check values exist.
    assert df["perf_1m"].notna().any()


@pytest.mark.skipif(not _REAL_FOLDER.is_dir(), reason="real chartsmaze folder absent")
def test_run_populates_sector_and_industry_metrics(legacy_cm, tmp_path):
    """run() writes sector, industry, and per-stock RS rows plus freshness."""
    conn = db.init_db(tmp_path / "manas.db")
    try:
        chartsmaze.run(conn, _REAL_DATE)

        sec = conn.execute("SELECT COUNT(*) AS n FROM sector_metrics").fetchone()["n"]
        ind = conn.execute("SELECT COUNT(*) AS n FROM industry_metrics").fetchone()["n"]
        stocks = conn.execute("SELECT COUNT(*) AS n FROM stock_industry_rs").fetchone()["n"]
        assert sec > 0, "sector_metrics not populated"
        assert ind > 0, "industry_metrics not populated"
        assert stocks > 0, "stock_industry_rs not populated"

        top_stock = conn.execute(
            "SELECT ticker, industry, rs FROM stock_industry_rs "
            "WHERE snapshot_date = ? ORDER BY rs DESC, ticker LIMIT 1",
            (_REAL_DATE,),
        ).fetchone()
        assert top_stock is not None
        assert top_stock["ticker"]
        assert top_stock["industry"]
        assert top_stock["rs"] is not None

        # sector_metrics carry the RS% from sector-analytics-Relative Strength.
        cap = conn.execute(
            "SELECT sector_key, rs_score FROM sector_metrics "
            "WHERE rs_score IS NOT NULL ORDER BY rs_score DESC LIMIT 1"
        ).fetchone()
        assert cap is not None
        assert cap["sector_key"]
        assert cap["rs_score"] >= 0

        # industries sorted by perf_1m desc on read; just confirm a value present.
        top = conn.execute(
            "SELECT name, perf_1m FROM industry_metrics "
            "WHERE perf_1m IS NOT NULL ORDER BY perf_1m DESC LIMIT 1"
        ).fetchone()
        assert top is not None and top["name"]

        # pipeline_runs still records the ingest honestly.
        run = conn.execute(
            "SELECT status FROM pipeline_runs WHERE stage='ingest_chartsmaze'"
        ).fetchone()
        assert run["status"] == "ok"
    finally:
        conn.close()


def test_run_missing_folder_skips(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        n = chartsmaze.run(conn, "1999-01-01")
        assert n == 0
        row = conn.execute(
            "SELECT status FROM pipeline_runs WHERE stage='ingest_chartsmaze'"
        ).fetchone()
        assert row[0] == "skip"
    finally:
        conn.close()


def test_migrate_history_copies_fixture(tmp_path):
    # Build a tiny fixture tree mimicking the real layout.
    src = tmp_path / "src"
    (src / "2026-01-01" / "analytics").mkdir(parents=True)
    (src / "2026-01-01" / "analytics" / "market-breadth.csv").write_text("a,b\n1,2\n")
    (src / "2026-01-02" / "scanners").mkdir(parents=True)
    (src / "2026-01-02" / "scanners" / "gap-up.csv").write_text("x\n1\n")
    (src / "order-wins-master.csv").write_text("m\n1\n")

    dst = tmp_path / "dst"
    copied = chartsmaze_migrate.migrate_history(src, dst)

    assert set(copied) == {"2026-01-01", "2026-01-02", "order-wins-master.csv"}
    assert (dst / "2026-01-01" / "analytics" / "market-breadth.csv").read_text() == "a,b\n1,2\n"
    assert (dst / "2026-01-02" / "scanners" / "gap-up.csv").exists()
    assert (dst / "order-wins-master.csv").exists()
    # Source preserved.
    assert (src / "2026-01-01" / "analytics" / "market-breadth.csv").exists()

    # Idempotent: existing date folders are skipped on a second run.
    copied2 = chartsmaze_migrate.migrate_history(src, dst)
    assert "2026-01-01" not in copied2
    assert "2026-01-02" not in copied2
