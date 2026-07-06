"""Tests for ChartsMaze disclosure-feed ingestion."""
from manas_os import db
from manas_os.sources import chartsmaze, disclosures


def _build_fixture(tmp_path):
    root = tmp_path / "chartsmaze"
    old = root / "2026-01-02" / "tools"
    cur = root / "2026-01-05" / "tools"
    old.mkdir(parents=True)
    cur.mkdir(parents=True)

    (old / "order-wins-new.csv").write_text(
        "Stock Name,Date,Order Value\n"
        "OLDCO,2026-01-02,10\n",
        encoding="utf-8",
    )
    (cur / "order-wins-new.csv").write_text(
        "Stock Name,Date,Order Value,Client\n"
        " Acutaas ,2026-01-03,125,Metro Rail\n",
        encoding="utf-8",
    )
    (cur / "corporate-announcements-new.csv").write_text(
        "Symbol,Announcement Date,Subject\n"
        "ZOMATO,03/01/2026,Board approves expansion\n",
        encoding="utf-8",
    )
    (cur / "circuit-limit-revision-history-new.csv").write_text(
        "ticker,Date,From,To,Reason\n"
        "acutaas,2026-01-05,5,2,Surveillance\n",
        encoding="utf-8",
    )
    return root


def test_run_writes_disclosures_and_circuit_bands(tmp_path, monkeypatch):
    root = _build_fixture(tmp_path)
    monkeypatch.setattr(chartsmaze, "chartsmaze_dir", lambda: root)
    conn = db.init_db(tmp_path / "manas.db")
    try:
        written = disclosures.run(conn, "2026-01-06")

        assert written == 4
        rows = conn.execute(
            "SELECT trade_date, symbol, kind FROM disclosures ORDER BY symbol, kind"
        ).fetchall()
        got = {(r["trade_date"], r["symbol"], r["kind"]) for r in rows}
        assert ("2026-01-03", "ACUTAAS", "order_win") in got
        assert ("2026-01-03", "ZOMATO", "announcement") in got
        assert ("2026-01-05", "ACUTAAS", "circuit_revision") in got

        band = conn.execute(
            "SELECT band_pct FROM circuit_bands WHERE symbol='ACUTAAS' AND as_of='2026-01-05'"
        ).fetchone()
        assert band["band_pct"] == 2.0
    finally:
        conn.close()


def test_recent_disclosure_window_uses_last_distinct_trade_dates(tmp_path, monkeypatch):
    root = _build_fixture(tmp_path)
    monkeypatch.setattr(chartsmaze, "chartsmaze_dir", lambda: root)
    conn = db.init_db(tmp_path / "manas.db")
    try:
        disclosures.run(conn, "2026-01-06")
        for d in ("2026-01-06", "2026-01-07", "2026-01-08", "2026-01-09"):
            conn.execute(
                "INSERT INTO disclosures (trade_date, symbol, kind, detail_json) "
                "VALUES (?, 'FILLER', 'announcement', '{}')",
                (d,),
            )
        conn.commit()

        assert disclosures.has_recent_disclosure(conn, "acutaas", "2026-01-06", 5) is True
        assert disclosures.has_recent_disclosure(conn, "ACUTAAS", "2026-01-09", 3) is False
        assert disclosures.has_recent_disclosure(conn, "MISSING", "2026-01-09", 5) is False
    finally:
        conn.close()


def test_circuit_band_returns_latest_band_at_or_before_date(tmp_path, monkeypatch):
    root = _build_fixture(tmp_path)
    monkeypatch.setattr(chartsmaze, "chartsmaze_dir", lambda: root)
    conn = db.init_db(tmp_path / "manas.db")
    try:
        disclosures.run(conn, "2026-01-06")
        conn.execute(
            "INSERT INTO circuit_bands (symbol, as_of, band_pct) VALUES ('ACUTAAS', '2026-01-07', 10)"
        )
        conn.commit()

        assert disclosures.circuit_band(conn, "acutaas", "2026-01-04") is None
        assert disclosures.circuit_band(conn, "acutaas", "2026-01-06") == 2.0
        assert disclosures.circuit_band(conn, "acutaas", "2026-01-08") == 10.0
    finally:
        conn.close()


def test_run_missing_folder_logs_skip(tmp_path, monkeypatch):
    monkeypatch.setattr(chartsmaze, "chartsmaze_dir", lambda: tmp_path / "missing")
    conn = db.init_db(tmp_path / "manas.db")
    try:
        assert disclosures.run(conn, "2026-01-06") == 0
        row = conn.execute(
            "SELECT status FROM pipeline_runs WHERE stage='ingest_disclosures'"
        ).fetchone()
        assert row["status"] == "skip"
    finally:
        conn.close()
