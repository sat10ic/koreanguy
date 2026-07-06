"""T3.8 — /api/flow/today Guided Daily Flow endpoint."""
from fastapi.testclient import TestClient

from manas_os import db
from manas_os.api import app as api_app
from manas_os.scanner import candidates
from manas_os.tests.conftest import AS_OF, insert_price_ramp, seed_confluent_symbol, seed_regime


def _client(db_path, monkeypatch, today=None):
    """TestClient bound to the temp DB (mirror the expectancy_api pattern).

    `today`: when set, monkeypatches the endpoint's `_today()` so the data step
    resolves against the fixture's AS_OF instead of the real wall-clock today
    (we're testing flow *logic*, not the calendar)."""
    orig_connect = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: orig_connect(db_path))
    if today is not None:
        monkeypatch.setattr(api_app, "_today", lambda: today)
    return TestClient(api_app.app)


def test_flow_today_empty_db_blocks_on_data(tmp_path, monkeypatch):
    """No prices, no regime, no scan → step 1 (data) is the current blocked step."""
    db_path = tmp_path / "manas.db"
    db.init_db(db_path)  # empty schema, no rows
    client = _client(db_path, monkeypatch, today=AS_OF)

    res = client.get("/api/flow/today")
    assert res.status_code == 200
    payload = res.json()
    assert payload["available"] is True
    assert {"steps", "current_step"} <= set(payload)
    steps = {s["id"]: s for s in payload["steps"]}
    assert steps["data"]["status"] == "blocked"
    assert payload["current_step"] == "data"


def test_flow_today_full_setup_reaches_setups(tmp_path, monkeypatch):
    """Fresh prices + regime snapshot + scan run → reaches the Setups review step.

    This is the happy path: data done, regime done, no open positions (skipped),
    and a scan produced candidates → current step is 'setups' (action)."""
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    try:
        insert_price_ramp(conn, symbol="ACME", n=210, end=AS_OF)
        seed_confluent_symbol(conn, symbol="ACME", scan_date=AS_OF)
        seed_regime(conn, scan_date=AS_OF, mode="SELECTIVE")
        candidates.run(conn, AS_OF)
    finally:
        conn.close()

    client = _client(db_path, monkeypatch, today=AS_OF)
    res = client.get("/api/flow/today")
    assert res.status_code == 200
    payload = res.json()
    steps = {s["id"]: s for s in payload["steps"]}
    assert steps["data"]["status"] == "done"
    assert steps["regime"]["status"] == "done"
    assert steps["regime"]["mode"] == "SELECTIVE"
    assert steps["positions"]["status"] == "skipped"   # no open journal trades
    assert steps["setups"]["status"] == "action"
    assert steps["setups"]["count"] is not None and steps["setups"]["count"] >= 1
    assert payload["current_step"] == "setups"


def test_flow_today_done_when_all_steps_clear(tmp_path, monkeypatch):
    """Scan ran but the gate refused everything (no candidates) → setups is
    'done', the terminal step is 'done', and current_step is 'done'."""
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    try:
        # Prices + regime but NO confluence seed → scan produces 0 candidates
        insert_price_ramp(conn, symbol="ACME", n=210, end=AS_OF)
        seed_regime(conn, scan_date=AS_OF, mode="DEFENSIVE")
        candidates.run(conn, AS_OF)
    finally:
        conn.close()

    client = _client(db_path, monkeypatch, today=AS_OF)
    res = client.get("/api/flow/today")
    payload = res.json()
    steps = {s["id"]: s for s in payload["steps"]}
    # 0 candidates in DEFENSIVE → setups detail says "nothing cleared the gate"
    assert steps["setups"]["status"] == "done"
    assert steps["done"]["status"] == "done"
    assert payload["current_step"] == "done"
