"""unidesk desk server (PART E-2) — localhost operator console.

FastAPI bound to 127.0.0.1 only, port 8181. No auth: it is a local operator
console, not a deployed service. It NEVER touches broker credentials (that
is the owner-gated orderflow workstream, out of scope here by charter).

Two file roots (verified against the exporter sources):
  * reports, authoritative:  <REPO>/data/market/reports/   (repo root)
  * derived UI exports:      <REPO>/unidesk_terminal/src/data/

/api/health reports BOTH newest sessions on purpose — a mismatch between
"newest on disk" and "newest derived" is the freshness signal the UI
renders. "Newest" always means sorted by session date descending, never
glob/file order (the C-2 bug class).

The refresh chain itself lives in unidesk/server/jobs.py (shared with the
CLI); this module only wraps it in a job registry, a worker thread and an
SSE stream. One job at a time — a second concurrent start is a 409.

Run:  .venv-orderflow/Scripts/python.exe -m uvicorn unidesk.server.app:app
      --host 127.0.0.1 --port 8181
"""
from __future__ import annotations

import asyncio
import json
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from unidesk.server.jobs import (
    REPORTS, SRC_DATA, iter_job, newest_derived_session, newest_report_sessions,
)

app = FastAPI(title="unidesk desk server", docs_url=None, redoc_url=None)

_SESSION_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")  # a session IS a date; traversal dies here
_SSE_POLL_S = 0.4
_SSE_HEARTBEAT_S = 15.0


def _dated_newest(pattern: str, data_dir: Path = SRC_DATA) -> Optional[Path]:
    """Newest file matching e.g. 'outcomes_*.json' by its embedded YYYY-MM-DD."""
    best_date, best_path = "", None
    for p in Path(data_dir).glob(pattern):
        m = re.search(r"(\d{4}-\d{2}-\d{2})", p.stem)
        if m and m.group(1) > best_date:
            best_date, best_path = m.group(1), p
    return best_path


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"not found: {path.name}")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"unreadable: {path.name}: {exc}")


def _session_json_response(session: str, pattern: str) -> JSONResponse:
    if not _SESSION_RE.match(session):
        raise HTTPException(status_code=400, detail="session must be YYYY-MM-DD")
    path = SRC_DATA / pattern.replace("{session}", session)
    # defense in depth: even with a regex-failing input, never escape the root
    if not str(path.resolve()).startswith(str(SRC_DATA.resolve())):
        raise HTTPException(status_code=400, detail="invalid path")
    return JSONResponse(_read_json(path))


# ---------------------------------------------------------------- job registry

class _Job:
    def __init__(self, job_id: str, options: dict):
        self.id = job_id
        self.options = options
        self.status = "running"
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.finished_at: Optional[str] = None
        self.events: list[dict] = []
        self.steps: list[dict] = []
        self.error: Optional[str] = None
        self.session: Optional[str] = None
        self._done = threading.Event()

    def snapshot(self) -> dict:
        return {
            "job_id": self.id,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "session": self.session,
            "error": self.error,
            "steps": [dict(s) for s in self.steps],
        }


_jobs: dict[str, _Job] = {}
_job_lock = threading.Lock()


def _run_job_thread(job: _Job) -> None:
    try:
        for ev in iter_job(job.options, capture_output=True):
            ev = dict(ev)
            ev.setdefault("job_id", job.id)
            job.events.append(ev)
            kind = ev.get("event")
            if kind == "stage_started":
                job.steps.append({"name": ev["name"], "label": ev["label"],
                                  "status": "running", "exit_code": None, "duration_s": None})
            elif kind == "stage_skipped":
                job.steps.append({"name": ev["name"], "label": ev["label"],
                                  "status": "skipped", "exit_code": None, "duration_s": None})
            elif kind == "stage_finished":
                for s in job.steps:
                    if s["name"] == ev["name"] and s["status"] == "running":
                        s.update(status="finished", exit_code=ev.get("exit_code"),
                                 duration_s=ev.get("duration_s"))
            elif kind == "stage_failed":
                for s in job.steps:
                    if s["name"] == ev["name"] and s["status"] == "running":
                        s.update(status="failed", exit_code=ev.get("exit_code"),
                                 duration_s=ev.get("duration_s"),
                                 error=ev.get("error"),
                                 output_tail=ev.get("output_tail", ""))
                job.error = ev.get("error")
            elif kind == "job_finished":
                job.status, job.session = "succeeded", ev.get("session")
            elif kind == "job_failed":
                job.status = "failed"
    except Exception as exc:  # noqa: BLE001 — the worker never dies silently
        job.status, job.error = "failed", f"worker error: {type(exc).__name__}: {exc}"
        job.events.append({"event": "job_failed", "job_id": job.id,
                           "error": job.error,
                           "finished_at": datetime.now(timezone.utc).isoformat()})
    finally:
        job.finished_at = datetime.now(timezone.utc).isoformat()
        job._done.set()


def _start_job(options: dict) -> _Job:
    with _job_lock:
        running = next((j for j in _jobs.values() if j.status == "running"), None)
        if running is not None:
            raise HTTPException(status_code=409, detail={
                "error": "job_already_running", "job_id": running.id})
        job = _Job(uuid.uuid4().hex, options)
        _jobs[job.id] = job
    threading.Thread(target=_run_job_thread, args=(job,), daemon=True).start()
    return job


# ---------------------------------------------------------------- GETs

def _last_scheduled_run() -> Optional[dict]:
    """B2-7: the last scheduled nightly's outcome (run_scheduled_refresh.py
    writes it). A scheduled job that fails silently is worse than none — the
    UI renders a banner from this."""
    p = Path(__file__).resolve().parents[1] / "last_run.json"
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


@app.get("/api/health")
def health():
    running = any(j.status == "running" for j in _jobs.values())
    return {
        "ok": True,
        "newest_session_on_disk": (newest_report_sessions(1) or [None])[0],
        "newest_derived_session": newest_derived_session(),
        "reports_dir": str(REPORTS),
        "job_running": running,
        "last_scheduled_run": _last_scheduled_run(),
    }


@app.get("/api/reports")
def reports():
    return {"sessions": newest_report_sessions(1000)}


@app.get("/api/report/{session}")
def report(session: str):
    if not _SESSION_RE.match(session):
        raise HTTPException(status_code=400, detail="session must be YYYY-MM-DD")
    path = REPORTS / f"tonight_{session}.json"
    if not str(path.resolve()).startswith(str(REPORTS.resolve())):
        raise HTTPException(status_code=400, detail="invalid path")
    return JSONResponse(_read_json(path))


@app.get("/api/outcomes")
def outcomes():
    p = _dated_newest("outcomes_*.json")
    if p is None:
        raise HTTPException(status_code=404, detail="no outcomes export found")
    return {"session": re.search(r"(\d{4}-\d{2}-\d{2})", p.stem).group(1), "data": _read_json(p)}


@app.get("/api/settings")
def settings():
    p = _dated_newest("settings_*.json")
    if p is None:
        raise HTTPException(status_code=404, detail="no settings export found")
    return {"session": re.search(r"(\d{4}-\d{2}-\d{2})", p.stem).group(1), "data": _read_json(p)}


@app.get("/api/coverage")
def coverage():
    p = _dated_newest("research_coverage_*.json")
    if p is None:
        raise HTTPException(status_code=404, detail="no research coverage export found")
    return {"session": re.search(r"(\d{4}-\d{2}-\d{2})", p.stem).group(1), "data": _read_json(p)}


@app.get("/api/desk-checks")
def desk_checks():
    return JSONResponse(_read_json(SRC_DATA / "desk_checks.json"))


@app.get("/api/stock-history/{session}")
def stock_history(session: str):
    return _session_json_response(session, "stock_history_{session}.json")


@app.get("/api/regime-history")
def regime_history():
    return JSONResponse(_read_json(SRC_DATA / "regime_history.json"))


@app.get("/api/metric-history")
def metric_history():
    return JSONResponse(_read_json(SRC_DATA / "metric_history.json"))


@app.get("/api/sector-mapping")
def sector_mapping():
    return JSONResponse(_read_json(SRC_DATA / "sector_mapping.json"))


# ---------------------------------------------------------------- F-4.3: positions register
# The Desk register lived ONLY in localStorage, which a cache clear erases.
# The server copy under data/market/ is the durable record; localStorage is a
# cache (F-4.3). Extends the E-2 contract deliberately (POST-E follow-up named
# in the handoff) — no broker data ever passes through here.

REGISTER_PATH = REPORTS.parent / "desk_register.json"


class RegisterBody(BaseModel):
    positions: list = []
    accountSize: Optional[float] = None
    updatedAt: Optional[str] = None


@app.get("/api/register")
def register_get():
    if not REGISTER_PATH.exists():
        return {"positions": [], "accountSize": None, "updatedAt": None}
    return JSONResponse(_read_json(REGISTER_PATH))


@app.put("/api/register")
def register_put(body: RegisterBody):
    REGISTER_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = REGISTER_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(body.model_dump(), indent=1), encoding="utf-8")
    tmp.replace(REGISTER_PATH)  # atomic — a crash mid-write cannot corrupt the record
    return {"ok": True, "positions": len(body.positions)}


# ---------------------------------------------------------------- POST + jobs

class RefreshBody(BaseModel):
    no_download: bool = False
    exports_only: bool = False
    skip_build: bool = False
    allow_no_new_session: bool = False


def _refresh_impl(body: RefreshBody) -> JSONResponse:
    job = _start_job({
        "no_download": body.no_download,
        "exports_only": body.exports_only,
        "skip_build": body.skip_build,
        "allow_no_new_session": body.allow_no_new_session,
    })
    return JSONResponse({"job_id": job.id}, status_code=202)


@app.post("/api/refresh")
def refresh(body: Optional[RefreshBody] = None):
    return _refresh_impl(body or RefreshBody())


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str):
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="unknown job")
    return job.snapshot()


@app.get("/api/jobs/{job_id}/events")
async def job_events(job_id: str, request: Request):
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="unknown job")

    async def stream():
        idx = 0
        last_beat = asyncio.get_event_loop().time()
        # A client connecting to an already-finished job replays the full
        # history then gets the terminal event — never a hang.
        while True:
            while idx < len(job.events):
                ev = job.events[idx]
                idx += 1
                yield f"data: {json.dumps(ev)}\n\n"
            if job._done.is_set() and idx >= len(job.events):
                break
            now = asyncio.get_event_loop().time()
            if now - last_beat > _SSE_HEARTBEAT_S:
                last_beat = now
                yield ": heartbeat\n\n"
            if await request.is_disconnected():
                return
            await asyncio.sleep(_SSE_POLL_S)

    return StreamingResponse(stream(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache", "X-Accel-Buffering": "no",
    })


if __name__ == "__main__":  # convenience: python -m unidesk.server.app
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8181)
