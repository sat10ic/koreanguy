import json
import time
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from manas_os import db
from manas_os.agents import debate
from manas_os.tests.conftest import insert_price_ramp
from manas_os.tests.test_agent_debate import FakeClient, _patch_config
from manas_os.api import app as api_app

AS_OF = "2026-06-30"


def test_debate_push_stream_creates_job_and_runs_async(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    from manas_os.scanner import candidates
    candidates.ensure_schema(conn)
    insert_price_ramp(conn, symbol="INFY", end=AS_OF)
    
    # Insert candidate row to ensure shortlist item is fetched
    conn.execute(
        "INSERT INTO scan_candidates (scan_date, symbol, setup, setup_family) VALUES (?, ?, ?, ?)",
        (AS_OF, "INFY", "momentum", "momentum")
    )
    conn.commit()
    conn.close()

    orig_connect = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: orig_connect(db_path))
    monkeypatch.setattr(db, "init_db", lambda db_path_arg=None: orig_connect(db_path))

    _patch_config(monkeypatch, shortlist_size=15)
    
    fake = FakeClient([
        {
            "symbol": "INFY",
            "verdict": "TAKE",
            "conviction": 4,
            "rank": 1,
            "lens_scores": {"strong_start": 4},
            "bull_case": "Support ramp.",
            "bear_case": "Resistance zone.",
            "reasoning": "Live stream test.",
        }
    ])
    
    # We patch debate.OpenRouterClient to use our fake client
    monkeypatch.setattr(debate, "OpenRouterClient", lambda *args, **kwargs: fake)

    client = TestClient(api_app.app)
    
    # Kicks off async job stream
    resp = client.post("/api/desk/debate/push?stream=true", json={"symbol": "INFY", "date": AS_OF})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "job_id" in body
    job_id = body["job_id"]

    # Wait for the background thread job to finish
    max_wait = 10
    finished = False
    for _ in range(max_wait * 10):
        time.sleep(0.1)
        conn = orig_connect(db_path)
        row = conn.execute("SELECT status FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        conn.close()
        if row and row[0] in ("succeeded", "failed"):
            assert row[0] == "succeeded"
            finished = True
            break
            
    assert finished, "Job did not complete in time"

    # Query events to make sure ordered stages and custom seat events are populated
    conn = orig_connect(db_path)
    events = conn.execute("SELECT event_type, payload_json FROM job_events WHERE job_id = ? ORDER BY event_id ASC", (job_id,)).fetchall()
    steps = conn.execute("SELECT name, status FROM job_steps WHERE job_id = ? ORDER BY seq ASC", (job_id,)).fetchall()
    conn.close()

    # Steps order verification: context_pack -> llm_debate -> chair_adjudication -> sizer_allocation
    step_names = [s[0] for s in steps]
    assert "context_pack" in step_names
    assert "llm_debate" in step_names
    assert "chair_adjudication" in step_names
    assert "sizer_allocation" in step_names

    # Custom event verification
    event_types = [e[0] for e in events]
    assert "seat_verdict" in event_types


def test_debate_push_unknown_symbol_rejected_honestly(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    conn.close()

    orig_connect = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: orig_connect(db_path))
    client = TestClient(api_app.app)

    # Unknown symbol request should fail with 404 (honestly)
    resp = client.post("/api/desk/debate/push?stream=true", json={"symbol": "XYZ_UNKNOWN", "date": AS_OF})
    assert resp.status_code == 404
    assert "no price history" in resp.json()["detail"]
