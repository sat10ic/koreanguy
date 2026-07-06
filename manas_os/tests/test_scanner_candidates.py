from fastapi.testclient import TestClient

from manas_os import db
from manas_os.api import app as api_app
from manas_os.scanner import candidates

from manas_os.tests.conftest import insert_price_ramp, seed_confluent_symbol


def _insert_prices(conn, symbol="ACME", n=210):
    # 210 real-dated bars: enough for the 200SMA trend-template gate.
    insert_price_ramp(conn, symbol=symbol, n=n)


def _insert_wide_stop_prices(conn, symbol="WIDE", n=210):
    # Deep daily lows (low = 80% of close): every candidate stop lands far
    # outside the 8% cap, so the risk gate must refuse with a named reason.
    insert_price_ramp(conn, symbol=symbol, n=n, low_frac=0.80)


def test_scanner_run_persists_candidates_and_logs_pipeline(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        _insert_prices(conn)
        seed_confluent_symbol(conn, scan_date="2026-06-30")
        result = candidates.run(conn, "2026-06-30")

        assert result["status"] == "ok"
        assert result["rows"] == 1
        row = conn.execute(
            "SELECT symbol, setup, readiness, grade, evidence_json "
            "FROM scan_candidates WHERE scan_date = '2026-06-30'"
        ).fetchone()
        assert row["symbol"] == "ACME"
        assert row["readiness"] > 0
        assert row["grade"] in {"A+", "A", "B", "C"}
        assert "delivery>=60" in row["evidence_json"]

        run = conn.execute(
            "SELECT status, rows_affected FROM pipeline_runs WHERE stage = 'scan_candidates'"
        ).fetchone()
        assert run["status"] == "ok"
        assert run["rows_affected"] == 1
    finally:
        conn.close()


def test_setups_endpoint_reads_persisted_scanner_rows(tmp_path, monkeypatch):
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    try:
        _insert_prices(conn)
        seed_confluent_symbol(conn, scan_date="2026-06-30")
        candidates.run(conn, "2026-06-30")
    finally:
        conn.close()

    orig_connect = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: orig_connect(db_path))
    client = TestClient(api_app.app)

    res = client.get("/api/setups", params={"date": "2026-06-30"})
    assert res.status_code == 200
    payload = res.json()
    assert payload["available"] is True
    assert payload["source"] == "scan_candidates"
    assert payload["as_of"] == "2026-06-30"
    assert payload["candidates"][0]["symbol"] == "ACME"


def test_growth_clamp_marks_untrusted_and_negative_sign_format(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        _insert_prices(conn)
        seed_confluent_symbol(conn, scan_date="2026-06-30")
        conn.execute(
            "UPDATE symbol_quality SET eps_yoy = 55250, eps_qoq = -5 WHERE symbol = 'ACME'"
        )
        result = candidates.scan_candidates(conn, "2026-06-30")
        card = result["candidates"][0]
        growth = card["score_breakdown"]["growth"]

        assert growth["eps_yoy"] == {"value": 55250.0, "untrusted": True}
        assert "EPS YoY" not in {e["filter"] for e in card["evidence"]}
        assert candidates.format_growth_value(-5) == "-5%"
        assert candidates.format_growth_value(55250) == "N/A (data error)"
    finally:
        conn.close()


def test_wide_stop_candidate_is_dropped_with_named_reason(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        _insert_wide_stop_prices(conn)
        seed_confluent_symbol(conn, symbol="WIDE", scan_date="2026-06-30")
        result = candidates.scan_candidates(conn, "2026-06-30")
        assert result["candidates"] == []
        refusal = result["dropped"][0]
        assert refusal["symbol"] == "WIDE"
        assert refusal["failed_gate"] == "risk"
        assert "stop" in refusal["reason"] and "cap" in refusal["reason"]
        # and it landed in the refusal ledger (T1.5)
        row = conn.execute("SELECT failed_gate, reason FROM refusals WHERE symbol='WIDE'").fetchone()
        assert row["failed_gate"] == "risk" and "cap" in row["reason"]
    finally:
        conn.close()


def test_persisted_candidates_have_rr_and_suggested_qty(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        _insert_prices(conn)
        seed_confluent_symbol(conn, scan_date="2026-06-30")
        result = candidates.run(conn, "2026-06-30")
        assert result["rows"] == 1
        row = conn.execute(
            "SELECT rr, suggested_qty FROM scan_candidates WHERE scan_date = '2026-06-30'"
        ).fetchone()
        durable = conn.execute(
            "SELECT rr, suggested_qty, source_payload_json FROM candidates WHERE candidate_date = '2026-06-30'"
        ).fetchone()
        assert row["rr"] is not None
        assert row["suggested_qty"] > 0
        assert durable["rr"] == row["rr"]
        assert durable["suggested_qty"] == row["suggested_qty"]
        assert '"suggested_qty"' in durable["source_payload_json"]
    finally:
        conn.close()
