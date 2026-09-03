"""PART E-6 — localhost desk server contract tests (FastAPI TestClient).

Every GET is validated against the REAL files on disk (no fixtures), plus
the security and job-machinery behaviours the UI depends on:
  * /api/report/{session} 404s on an unknown session and rejects path
    traversal;
  * a second POST /api/refresh while one runs is a 409;
  * newest-session selection picks by session DATE, not filename/glob order
    (a constructed case where the two differ);
  * run_job aborts on the first failing step and never executes later steps
    (fake step table — the real refresh chain is NEVER run in tests).
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from unidesk.server import app as app_mod
from unidesk.server.app import app
from unidesk.server.jobs import REPORTS, SRC_DATA, Step, StepFailure, newest_report_sessions

client = TestClient(app)


# ---------------------------------------------------------------- GETs against real disk

def test_health_shape():
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["job_running"] is False
    assert body["newest_session_on_disk"] == "2026-09-01"
    assert body["newest_derived_session"] == "2026-09-01"
    assert Path(body["reports_dir"]).is_dir()


def test_reports_list_newest_first():
    r = client.get("/api/reports")
    assert r.status_code == 200
    sessions = r.json()["sessions"]
    assert sessions == sorted(sessions, reverse=True)
    assert "2026-09-01" in sessions


def test_report_verbatim_matches_disk():
    disk = json.loads((REPORTS / "tonight_2026-09-01.json").read_text(encoding="utf-8"))
    r = client.get("/api/report/2026-09-01")
    assert r.status_code == 200
    assert r.json() == disk


def test_outcomes_settings_coverage_shapes():
    for endpoint, stem in (("outcomes", "outcomes_"), ("settings", "settings_"),
                           ("coverage", "research_coverage_")):
        r = client.get(f"/api/{endpoint}")
        assert r.status_code == 200, endpoint
        body = r.json()
        assert set(body) == {"session", "data"}, endpoint
        disk = json.loads((SRC_DATA / f"{stem}{body['session']}.json").read_text(encoding="utf-8"))
        assert body["data"] == disk, endpoint


def test_desk_checks_regime_metric_sector():
    assert client.get("/api/desk-checks").status_code == 200
    for endpoint in ("regime-history", "metric-history", "sector-mapping"):
        r = client.get(f"/api/{endpoint}")
        assert r.status_code == 200, endpoint
    sh = client.get("/api/stock-history/2026-09-01")
    assert sh.status_code == 200
    assert isinstance(sh.json(), dict) and len(sh.json()) > 0


# ---------------------------------------------------------------- traversal / unknown

def test_report_unknown_session_404():
    assert client.get("/api/report/1999-01-01").status_code == 404


def test_report_rejects_path_traversal():
    for evil in ("..%2F..%2Fetc%2Fpasswd", "../../../../etc/passwd", "....", "2026-09-01/../../secrets"):
        r = client.get(f"/api/report/{evil}")
        assert r.status_code in (400, 404), evil
        assert r.status_code != 200


def test_stock_history_rejects_path_traversal():
    r = client.get("/api/stock-history/../../../../etc/passwd")
    assert r.status_code in (400, 404)
    assert r.status_code != 200


# ---------------------------------------------------------------- 409 on concurrent refresh

def test_second_refresh_while_running_is_409():
    ghost = app_mod._Job("ghost-job", {})
    ghost.status = "running"  # pretend a job is mid-flight; no thread started
    app_mod._jobs[ghost.id] = ghost
    try:
        r = client.post("/api/refresh", json={"exports_only": True, "skip_build": True})
        assert r.status_code == 409
        assert r.json()["detail"]["error"] == "job_already_running"
        assert r.json()["detail"]["job_id"] == "ghost-job"
    finally:
        app_mod._jobs.pop("ghost-job", None)


def test_job_status_unknown_404():
    assert client.get("/api/jobs/no-such-job").status_code == 404


# ---------------------------------------------------------------- newest by DATE, not glob order

def test_newest_session_picks_by_date_not_filename_order(tmp_path):
    # filename says 2099 is newest; the embedded session_date says 2025 is.
    (tmp_path / "tonight_2099-01-01.json").write_text(
        json.dumps({"session_date": "2020-01-01"}), encoding="utf-8")
    (tmp_path / "tonight_2020-06-01.json").write_text(
        json.dumps({"session_date": "2025-01-01"}), encoding="utf-8")
    got = newest_report_sessions(2, reports_dir=tmp_path)
    assert got == ["2025-01-01", "2020-01-01"]


# ---------------------------------------------------------------- abort on first failed step

def test_run_job_aborts_on_first_failure(monkeypatch):
    executed: list[str] = []

    def ok_step(ctx):
        executed.append("ok1")

    def boom(ctx):
        raise StepFailure("planned failure")

    def never(ctx):
        executed.append("never")

    fake = [
        Step("ok1", "ok 1", fn=ok_step),
        Step("boom", "planned failure", fn=boom),
        Step("never", "must not run", fn=never),
    ]
    monkeypatch.setattr(app_mod, "REFRESH_STEPS_FOR_TEST", fake, raising=False)
    import unidesk.server.jobs as jobs
    monkeypatch.setattr(jobs, "refresh_steps", lambda: fake)

    events = list(jobs.iter_job({}, capture_output=True))
    kinds = [e["event"] for e in events]
    assert executed == ["ok1"], "later steps must never execute after a failure"
    assert kinds[-1] == "job_failed"
    assert kinds.count("stage_failed") == 1
    failed = next(e for e in events if e["event"] == "stage_failed")
    assert failed["name"] == "boom"
    assert "planned failure" in failed["error"]


# ---------------------------------------------------------------- SSE replay for a finished job

def test_job_events_replay_for_finished_job():
    done = app_mod._Job("done-job", {})
    done.status = "succeeded"
    done.finished_at = done.started_at
    done.events = [{"event": "job_started", "job_id": "done-job"},
                   {"event": "job_finished", "job_id": "done-job"}]
    done._done.set()
    app_mod._jobs["done-job"] = done
    try:
        with client.stream("GET", "/api/jobs/done-job/events") as resp:
            body = b"".join(resp.iter_bytes()).decode()
        assert "job_started" in body and "job_finished" in body
        assert body.count("data:") == 2
    finally:
        app_mod._jobs.pop("done-job", None)
