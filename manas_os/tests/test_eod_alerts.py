from fastapi.testclient import TestClient

from manas_os import db
from manas_os.alerts import eod
from manas_os.api import app as api_app
from manas_os.scanner import candidates

from manas_os.tests.conftest import seed_confluent_symbol


from manas_os.tests.conftest import insert_price_ramp


def _insert_prices(conn, symbol="ACME", n=210):
    # 210 real-dated bars: enough for the 200SMA trend-template gate.
    insert_price_ramp(conn, symbol=symbol, n=n)


def test_eod_alert_stage_persists_candidate_alerts(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        _insert_prices(conn)
        seed_confluent_symbol(conn, scan_date="2026-06-30")
        candidates.run(conn, "2026-06-30")
        result = eod.run(conn, "2026-06-30")

        assert result["status"] == "ok"
        assert result["rows"] == 1
        row = conn.execute(
            "SELECT symbol, alert_type, severity, detail FROM alert_log WHERE alert_date = '2026-06-30'"
        ).fetchone()
        assert row["symbol"] == "ACME"
        assert row["alert_type"] == "SETUP_READY"
        assert "readiness" in row["detail"]

        run = conn.execute(
            "SELECT status, rows_affected FROM pipeline_runs WHERE stage = 'eod_alerts'"
        ).fetchone()
        assert run["status"] == "ok"
        assert run["rows_affected"] == 1
    finally:
        conn.close()


def test_eod_alerts_endpoint_returns_persisted_alerts(tmp_path, monkeypatch):
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    try:
        _insert_prices(conn)
        seed_confluent_symbol(conn, scan_date="2026-06-30")
        candidates.run(conn, "2026-06-30")
        eod.run(conn, "2026-06-30")
    finally:
        conn.close()

    orig_connect = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: orig_connect(db_path))
    client = TestClient(api_app.app)

    res = client.get("/api/alerts/eod", params={"date": "2026-06-30"})
    assert res.status_code == 200
    payload = res.json()
    assert payload["available"] is True
    assert payload["as_of"] == "2026-06-30"
    assert payload["alerts"][0]["symbol"] == "ACME"
    assert payload["alerts"][0]["evidence"]
