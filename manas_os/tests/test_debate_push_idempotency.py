"""R1 residual: push-to-debate idempotency + in-flight guard.

Covers manas_os/agents/debate.py::push_symbol_debate:
  - a pair with an existing user_pushed card returns already_debated=True
    and does NOT re-invoke the LLM cascade.
  - a pair currently marked in-flight returns already_running=True (which
    the API route in manas_os/api/app.py::desk_debate_push turns into a
    409) without touching the DB or the LLM client.
"""
import json

from manas_os import db
from manas_os.agents import debate
from manas_os.tests.conftest import insert_price_ramp
from manas_os.tests.test_agent_debate import FakeClient, _patch_config


AS_OF = "2026-06-30"


def test_push_returns_already_debated_for_existing_card_without_recalling_llm(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    try:
        insert_price_ramp(conn, symbol="TANLA", end=AS_OF)
        _patch_config(monkeypatch, shortlist_size=15)
        fake = FakeClient([
            {
                "symbol": "TANLA",
                "verdict": "TAKE",
                "conviction": 4,
                "rank": 1,
                "lens_scores": {"strong_start": 4},
                "bull_case": "Clean structure.",
                "bear_case": "Thin volume.",
                "reasoning": "First push.",
            }
        ])

        first = debate.push_symbol_debate(conn, "TANLA", AS_OF, client=fake)
        assert first["status"] == "ok"
        assert not first.get("already_debated")
        calls_after_first = len(fake.calls)
        assert calls_after_first > 0

        second = debate.push_symbol_debate(conn, "TANLA", AS_OF, client=fake)
        assert second.get("already_debated") is True
        assert second["status"] == "ok"
        # No new LLM call (debate-model or chair/sizer) for the
        # already-debated pair -- call count must not grow.
        assert len(fake.calls) == calls_after_first
    finally:
        conn.close()


def test_push_returns_already_running_for_in_flight_pair_without_llm_call(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    try:
        insert_price_ramp(conn, symbol="GROWW", end=AS_OF)
        _patch_config(monkeypatch, shortlist_size=15)
        fake = FakeClient([{"symbol": "GROWW", "verdict": "TAKE", "conviction": 3, "rank": 1}])

        # Simulate a push already in-flight for this (symbol, resolved
        # scan_date) pair -- push_symbol_debate resolves scan_date via
        # MAX(scan_date) <= date against scan_candidates, which is empty
        # here, so the resolved scan_date falls back to `date` itself.
        debate._PUSH_INFLIGHT.add(("GROWW", AS_OF))
        try:
            result = debate.push_symbol_debate(conn, "GROWW", AS_OF, client=fake)
        finally:
            debate._PUSH_INFLIGHT.discard(("GROWW", AS_OF))

        assert result.get("already_running") is True
        assert result["status"] == "fail"
        assert result["reason"] == "already running"
        assert fake.calls == []
        assert conn.execute("SELECT COUNT(*) FROM agent_verdicts").fetchone()[0] == 0
    finally:
        conn.close()


def test_desk_debate_push_route_returns_409_when_in_flight(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from manas_os.api import app as api_app

    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    conn.close()

    orig_connect = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: orig_connect(db_path))
    client = TestClient(api_app.app)

    debate._PUSH_INFLIGHT.add(("TCS", AS_OF))
    try:
        resp = client.post("/api/desk/debate/push", json={"symbol": "TCS", "date": AS_OF})
    finally:
        debate._PUSH_INFLIGHT.discard(("TCS", AS_OF))
    assert resp.status_code == 409
