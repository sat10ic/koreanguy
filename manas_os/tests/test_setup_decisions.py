import json

from fastapi.testclient import TestClient

from manas_os import db
from manas_os.api import app as api_app
from manas_os.scanner import candidates
from manas_os.tests.conftest import AS_OF, insert_price_ramp, seed_confluent_symbol, seed_sizer_verdict


def test_setup_decision_taken_skipped_and_unknown(tmp_path, monkeypatch):
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    try:
        insert_price_ramp(conn, symbol="ACME", n=210)
        seed_confluent_symbol(conn, symbol="ACME", scan_date=AS_OF)
        result = candidates.run(conn, AS_OF)
        assert result["status"] == "ok"
        # Actionable gate (P0 fix): TAKEN is only accepted once a sizer
        # verdict with a positive final_qty exists for this scan_date/symbol
        # -- see app._plan_actionability. This test exercises the normal
        # decision-recording mechanics, not the gate itself (that is covered
        # by test_setup_decision_taken_without_sizer_is_refused_409 and
        # test_setup_decision_taken_with_zero_qty_sizer_is_refused_409 below).
        seed_sizer_verdict(conn, symbol="ACME", scan_date=AS_OF, final_qty=10)
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


def test_setup_decision_taken_without_sizer_is_refused_409(tmp_path, monkeypatch):
    """P0 fix (mechanical gate, server side): a scan_candidates plan with no
    recorded sizer verdict at all is 'sizing-unavailable' -- final qty is
    unknown, not zero -- and TAKEN must be refused with a structured 409,
    not silently accepted and written to the journal as a real trade."""
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    try:
        insert_price_ramp(conn, symbol="ACME", n=210)
        seed_confluent_symbol(conn, symbol="ACME", scan_date=AS_OF)
        result = candidates.run(conn, AS_OF)
        assert result["status"] == "ok"
        # Deliberately no seed_sizer_verdict() call -- no agent_verdicts row.
    finally:
        conn.close()

    orig_connect = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: orig_connect(db_path))
    client = TestClient(api_app.app)

    taken = client.post(
        "/api/setups/decision",
        json={"scan_date": AS_OF, "symbol": "ACME", "decision": "taken"},
    )
    assert taken.status_code == 409
    detail = taken.json()["detail"]
    assert detail["code"] == "NOT_ACTIONABLE"
    assert "sizer" in detail["cause"].lower()
    assert detail["action"]

    # The refused TAKEN must not have been persisted anywhere.
    conn = db.connect(db_path)
    try:
        assert conn.execute(
            "SELECT COUNT(*) FROM setup_decisions WHERE scan_date = ? AND symbol = ?",
            (AS_OF, "ACME"),
        ).fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM journal_trades").fetchone()[0] == 0
    finally:
        conn.close()

    # SKIPPED must still work for a non-actionable candidate (only TAKEN is gated).
    skipped = client.post(
        "/api/setups/decision",
        json={"scan_date": AS_OF, "symbol": "ACME", "decision": "skipped", "skip_reason": "no sizer yet"},
    )
    assert skipped.status_code == 200
    assert skipped.json()["decision"] == "skipped"


def test_setup_decision_taken_with_zero_qty_sizer_is_refused_409(tmp_path, monkeypatch):
    """A sizer verdict that explicitly refused (final_qty 0) must also 409,
    not just a missing sizer row."""
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    try:
        insert_price_ramp(conn, symbol="ACME", n=210)
        seed_confluent_symbol(conn, symbol="ACME", scan_date=AS_OF)
        result = candidates.run(conn, AS_OF)
        assert result["status"] == "ok"
        seed_sizer_verdict(conn, symbol="ACME", scan_date=AS_OF, final_qty=0, multiplier=0,
                           reasoning="Sizer refused: stop 6.2% exceeds 5.0% cap")
    finally:
        conn.close()

    orig_connect = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: orig_connect(db_path))
    client = TestClient(api_app.app)

    taken = client.post(
        "/api/setups/decision",
        json={"scan_date": AS_OF, "symbol": "ACME", "decision": "taken"},
    )
    assert taken.status_code == 409
    detail = taken.json()["detail"]
    assert detail["code"] == "NOT_ACTIONABLE"
    assert "refused" in detail["cause"].lower() or "0" in detail["cause"]
