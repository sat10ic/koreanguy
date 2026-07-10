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
    assert "order_ticket" in steps
    assert steps["order_ticket"]["status"] == "blocked"
    assert payload["current_step"] == "setups"


def test_flow_today_taken_setup_unlocks_copyable_order_ticket(tmp_path, monkeypatch):
    """After the user logs TAKEN, setup review is done and the copyable
    order ticket becomes the current action."""
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
    decision = client.post(
        "/api/setups/decision",
        json={"scan_date": AS_OF, "symbol": "ACME", "decision": "taken"},
    )
    assert decision.status_code == 200

    res = client.get("/api/flow/today")
    assert res.status_code == 200
    payload = res.json()
    steps = {s["id"]: s for s in payload["steps"]}

    assert [s["id"] for s in payload["steps"]] == [
        "data",
        "regime",
        "positions",
        "setups",
        "order_ticket",
        "done",
    ]
    assert steps["setups"]["status"] == "done"
    assert steps["order_ticket"]["status"] == "action"
    assert payload["current_step"] == "order_ticket"
    ticket = steps["order_ticket"]["ticket"]
    assert ticket["symbol"] == "ACME"
    assert "BUY ACME" in ticket["copy_text"]
    assert "STOP" in ticket["copy_text"]
    assert "QTY" in ticket["copy_text"]


def test_flow_today_done_when_all_steps_clear(tmp_path, monkeypatch):
    """Scan ran but the gate refused everything (no candidates) → setups is
    'done', the terminal step is 'done', and current_step is 'done'.

    WAVE_M M3 (user order 2026-07-11): a regime family-kill is now a scored
    OBJECTION, not a hard drop, so DEFENSIVE no longer guarantees 0
    candidates. NO_TRADE is the one mode that stays a hard, fail-fast
    refusal (0 cards stays 0 — LOCKED invariant), so it is the scenario that
    still exercises this "nothing cleared the gate" path.
    """
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    try:
        # Prices + regime but NO confluence seed → scan produces 0 candidates
        insert_price_ramp(conn, symbol="ACME", n=210, end=AS_OF)
        seed_regime(conn, scan_date=AS_OF, mode="NO_TRADE")
        candidates.run(conn, AS_OF)
    finally:
        conn.close()

    client = _client(db_path, monkeypatch, today=AS_OF)
    res = client.get("/api/flow/today")
    payload = res.json()
    steps = {s["id"]: s for s in payload["steps"]}
    # 0 candidates in NO_TRADE → setups detail says "nothing cleared the gate"
    assert steps["setups"]["status"] == "done"
    assert steps["order_ticket"]["status"] == "skipped"
    assert steps["done"]["status"] == "done"
    assert payload["current_step"] == "done"


def test_flow_today_no_trade_variant_says_sit_out(tmp_path, monkeypatch):
    """T3.8 NO_TRADE variant: when the posture is NO_TRADE, the setups step is
    done because the governor blocks all entries — NOT because the gate refused
    everything. The detail must say 'sit out' so the beginner reads it right."""
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    try:
        insert_price_ramp(conn, symbol="ACME", n=210, end=AS_OF)
        seed_confluent_symbol(conn, symbol="ACME", scan_date=AS_OF)
        seed_regime(conn, scan_date=AS_OF, mode="NO_TRADE")
        candidates.run(conn, AS_OF)  # scan runs even under NO_TRADE
    finally:
        conn.close()

    client = _client(db_path, monkeypatch, today=AS_OF)
    res = client.get("/api/flow/today")
    payload = res.json()
    steps = {s["id"]: s for s in payload["steps"]}
    assert steps["setups"]["status"] == "done"
    assert steps["order_ticket"]["status"] == "skipped"
    # The NO_TRADE message must be explicit — not the generic "gate refused" line.
    assert "NO_TRADE" in steps["setups"]["detail"]
    assert "sit out" in steps["setups"]["detail"].lower()
    assert payload["current_step"] == "done"


def test_flow_today_friday_adds_weekly_review(tmp_path, monkeypatch):
    """T3.8 Friday weekly step: on a Friday, the done step carries the weekly-
    review prompt. 2026-07-03 is a Friday."""
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    try:
        insert_price_ramp(conn, symbol="ACME", n=210, end="2026-07-03")
        seed_regime(conn, scan_date="2026-07-03", mode="SELECTIVE")
    finally:
        conn.close()

    # 2026-07-03 is a Friday (verified: weekday()==4).
    client = _client(db_path, monkeypatch, today="2026-07-03")
    res = client.get("/api/flow/today")
    payload = res.json()
    steps = {s["id"]: s for s in payload["steps"]}
    # Even if not fully terminal, the friday flag is set and the detail mentions weekly review.
    assert steps["done"]["weekly_review"] is True
    assert "weekly review" in steps["done"]["detail"].lower()


def test_flow_today_non_friday_has_no_weekly_review(tmp_path, monkeypatch):
    """A non-Friday must NOT set weekly_review (the Friday note is conditional)."""
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    try:
        insert_price_ramp(conn, symbol="ACME", n=210, end=AS_OF)
        seed_regime(conn, scan_date=AS_OF, mode="SELECTIVE")
    finally:
        conn.close()

    client = _client(db_path, monkeypatch, today=AS_OF)
    res = client.get("/api/flow/today")
    payload = res.json()
    steps = {s["id"]: s for s in payload["steps"]}
    assert steps["done"]["weekly_review"] is False
