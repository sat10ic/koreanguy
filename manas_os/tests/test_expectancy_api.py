from fastapi.testclient import TestClient

from manas_os import db
from manas_os.api import app as api_app
from manas_os.scanner import candidates, expectancy
from manas_os.tests.conftest import AS_OF, insert_price_ramp, seed_confluent_symbol


def test_expectancy_endpoint_latest_rows(tmp_path, monkeypatch):
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    try:
        insert_price_ramp(conn, symbol="ACME", n=210)
        seed_confluent_symbol(conn, symbol="ACME", scan_date=AS_OF)
        candidates.run(conn, AS_OF)
        expectancy.run(conn, AS_OF)
    finally:
        conn.close()

    orig_connect = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: orig_connect(db_path))
    client = TestClient(api_app.app)

    res = client.get("/api/expectancy")
    assert res.status_code == 200
    payload = res.json()
    assert {"available", "as_of", "system", "personal"} <= set(payload)
    assert isinstance(payload["system"], list)
    assert isinstance(payload["personal"], list)
