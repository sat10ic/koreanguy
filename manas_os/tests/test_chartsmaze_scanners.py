"""Tests for chartsmaze_scanners: screener_hits + symbol_quality ingestion."""
import pytest

from manas_os import db
from manas_os.sources import chartsmaze, chartsmaze_scanners

_RUN_DATE = "2026-01-01"


def _build_fixture(tmp_path):
    root = tmp_path / "cm"
    d = root / _RUN_DATE
    (d / "scanners").mkdir(parents=True)
    (d / "templates").mkdir(parents=True)
    (d / "tools").mkdir(parents=True)
    (d / "analytics").mkdir(parents=True)

    (d / "scanners" / "vcp.csv").write_text(
        "Stock Name,RS Rating,Basic Industry\n"
        "ACUTAAS,95,Chemicals Specialty\n"
        "ZOMATO,88,Internet Software\n",
        encoding="utf-8",
    )
    (d / "scanners" / "momentum-scanner.csv").write_text(
        "Stock Name,RS Rating,Basic Industry\n"
        "ACUTAAS,95,Chemicals Specialty\n"
        "TATAPOWER,70,Power Generation\n",
        encoding="utf-8",
    )
    (d / "scanners" / "shorting-scanner.csv").write_text(
        "Stock Name,Criterion,RS Rating,Basic Industry\n"
        "ADANIPOWER,EMA9 crossed below EMA21,93,Power Generation & Distribution\n",
        encoding="utf-8",
    )
    (d / "tools" / "asm.csv").write_text(
        "Stock Name,ASM Stage\nACUTAAS,LTASM - I\n",
        encoding="utf-8",
    )
    (d / "analytics" / "results-calendar.csv").write_text(
        "Stock Name,Quarterly Results Date,QoQ % EPS Latest,YoY % EPS Latest,"
        "QoQ % Sales Latest,YoY % Sales Latest,QoQ % OPM Latest,YoY % OPM Latest\n"
        "ACUTAAS,30/06/2026,44.8,143,7.4,45.4,22.9,78.6\n",
        encoding="utf-8",
    )
    return root


@pytest.fixture
def fake_cm(tmp_path, monkeypatch):
    root = _build_fixture(tmp_path)
    monkeypatch.setattr(chartsmaze, "chartsmaze_dir", lambda: root)
    return root


def test_run_writes_screener_hits(fake_cm, tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        chartsmaze_scanners.run(conn, _RUN_DATE)

        rows = conn.execute(
            "SELECT symbol, screener, bearish FROM screener_hits "
            "WHERE trade_date = ? ORDER BY symbol, screener",
            (_RUN_DATE,),
        ).fetchall()
        got = {(r["symbol"], r["screener"], r["bearish"]) for r in rows}
        assert ("ACUTAAS", "vcp", 0) in got
        assert ("ACUTAAS", "momentum-scanner", 0) in got
        assert ("ZOMATO", "vcp", 0) in got
        assert ("TATAPOWER", "momentum-scanner", 0) in got
        assert ("ADANIPOWER", "shorting-scanner", 1) in got
    finally:
        conn.close()


def test_confluence_excludes_bearish(fake_cm, tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        chartsmaze_scanners.run(conn, _RUN_DATE)
        conf = chartsmaze_scanners.confluence_for_date(conn, _RUN_DATE)

        assert conf["ACUTAAS"]["count"] == 2
        assert set(conf["ACUTAAS"]["screeners"]) == {"vcp", "momentum-scanner"}
        assert conf["ZOMATO"]["count"] == 1
        assert conf["TATAPOWER"]["count"] == 1
        # bearish-only symbol must not appear in confluence at all
        assert "ADANIPOWER" not in conf
    finally:
        conn.close()


def test_symbol_quality_populated(fake_cm, tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        chartsmaze_scanners.run(conn, _RUN_DATE)

        row = conn.execute(
            "SELECT asm_stage, eps_qoq, eps_yoy, sales_yoy, opm_yoy "
            "FROM symbol_quality WHERE trade_date=? AND symbol='ACUTAAS'",
            (_RUN_DATE,),
        ).fetchone()
        assert row is not None
        assert row["asm_stage"] == "LTASM - I"
        assert row["eps_qoq"] == 44.8
        assert row["eps_yoy"] == 143.0
        assert row["sales_yoy"] == 45.4
        assert row["opm_yoy"] == 78.6
    finally:
        conn.close()


def test_run_logs_pipeline_run(fake_cm, tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        chartsmaze_scanners.run(conn, _RUN_DATE)
        row = conn.execute(
            "SELECT status FROM pipeline_runs WHERE stage='ingest_chartsmaze_scanners'"
        ).fetchone()
        assert row["status"] == "ok"
    finally:
        conn.close()


def test_run_missing_folder_skips(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        n = chartsmaze_scanners.run(conn, "1999-01-01")
        assert n == 0
        row = conn.execute(
            "SELECT status FROM pipeline_runs WHERE stage='ingest_chartsmaze_scanners'"
        ).fetchone()
        assert row["status"] == "skip"
    finally:
        conn.close()


def test_run_idempotent(fake_cm, tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        chartsmaze_scanners.run(conn, _RUN_DATE)
        n1 = conn.execute("SELECT COUNT(*) AS n FROM screener_hits").fetchone()["n"]
        q1 = conn.execute("SELECT COUNT(*) AS n FROM symbol_quality").fetchone()["n"]

        chartsmaze_scanners.run(conn, _RUN_DATE)
        n2 = conn.execute("SELECT COUNT(*) AS n FROM screener_hits").fetchone()["n"]
        q2 = conn.execute("SELECT COUNT(*) AS n FROM symbol_quality").fetchone()["n"]

        assert n1 == n2
        assert q1 == q2
    finally:
        conn.close()
