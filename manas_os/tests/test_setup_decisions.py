import json

from fastapi.testclient import TestClient

from manas_os import db
from manas_os.api import app as api_app
from manas_os.scanner import candidates
from manas_os.tests.conftest import AS_OF, insert_price_ramp, seed_confluent_symbol


def test_setup_decision_taken_skipped_and_unknown(tmp_path, monkeypatch):
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    try:
        insert_price_ramp(conn, symbol="ACME", n=210)
        seed_confluent_symbol(conn, symbol="ACME", scan_date=AS_OF)
        result = candidates.run(conn, AS_OF)
        assert result["status"] == "ok"
    finally:
        conn.close()

    orig_connect = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: orig_connect(db_path))
    client = TestClient(api_app.app)

    taken = client.post(
        "/api/setups/decision",
        json={"scan_date": AS_OF, "symbol": "ACME", "decision": "taken", "entry_price": 123.45, "qty": 10},
    )
    assert taken.status_code == 200
    assert taken.json()["decision"] == "taken"
    assert taken.json()["trade_id"]

    conn = db.connect(db_path)
    try:
        decision_row = conn.execute(
            "SELECT decision, snapshot_json FROM setup_decisions WHERE scan_date = ? AND symbol = ?",
            (AS_OF, "ACME"),
        ).fetchone()
        assert decision_row["decision"] == "taken"
        assert '"rank"' in decision_row["snapshot_json"]
        assert json.loads(decision_row["snapshot_json"])["symbol"] == "ACME"
        assert conn.execute("SELECT COUNT(*) FROM journal_trades").fetchone()[0] == 1
    finally:
        conn.close()

    skipped = client.post(
        "/api/setups/decision",
        json={"scan_date": AS_OF, "symbol": "ACME", "decision": "skipped", "skip_reason": "fear"},
    )
    assert skipped.status_code == 200
    assert skipped.json()["decision"] == "skipped"

    conn = db.connect(db_path)
    try:
        decision_row = conn.execute(
            "SELECT decision, skip_reason FROM setup_decisions WHERE scan_date = ? AND symbol = ?",
            (AS_OF, "ACME"),
        ).fetchone()
        assert decision_row["decision"] == "skipped"
        assert decision_row["skip_reason"] == "fear"
        assert conn.execute("SELECT COUNT(*) FROM journal_trades").fetchone()[0] == 1
    finally:
        conn.close()

    unknown = client.post(
        "/api/setups/decision",
        json={"scan_date": AS_OF, "symbol": "NOPE", "decision": "taken"},
    )
    assert unknown.status_code == 404
