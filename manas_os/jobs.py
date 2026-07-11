"""Durable, best-effort telemetry for observable pipeline work."""
from __future__ import annotations

import contextvars
import json
import os
import sqlite3
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable

_active: contextvars.ContextVar["JobEmitter | None"] = contextvars.ContextVar("job_emitter", default=None)
TERMINAL_STATUSES = frozenset({"succeeded", "partial", "failed", "cancelled", "interrupted"})


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, default=str)


def _error(value: BaseException | str) -> str:
    return str(value).replace("\r", " ").replace("\n", " ")[:1000]


@dataclass
class StageResult:
    name: str
    status: str
    error: str | None = None


class JobEmitter:
    """Sole writer for the job rail; telemetry failures are always swallowed."""

    def __init__(self, conn: sqlite3.Connection, job_id: int | None = None) -> None:
        self.conn, self.job_id, self.step_id = conn, job_id, None
        self._started = 0.0

    def _write(self, sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Cursor | None:
        try:
            cur = self.conn.execute(sql, params)
            self.conn.commit()
            return cur
        except Exception:
            try:
                self.conn.rollback()
            except Exception:
                pass
            return None

    def event(self, event_type: str, payload: Any = None) -> None:
        if self.job_id is not None:
            self._write("INSERT INTO job_events(job_id,step_id,event_type,payload_json) VALUES(?,?,?,?)",
                        (self.job_id, self.step_id, event_type, _json(payload or {})))

    def heartbeat(self) -> None:
        if self.job_id is not None:
            self._write("UPDATE jobs SET heartbeat_at=datetime('now') WHERE job_id=?", (self.job_id,))

    def job_started(self, kind: str, run_date: str | None, *, requested_by: str, params: dict[str, Any]) -> int | None:
        if self.job_id is not None:
            self._write(
                "UPDATE jobs SET kind=?,run_date=?,status='running',requested_by=?,params_json=?,pid=?,"
                "started_at=datetime('now'),heartbeat_at=datetime('now'),finished_at=NULL,error=NULL WHERE job_id=?",
                (kind, run_date, requested_by, _json(params), os.getpid(), self.job_id),
            )
            self.event("job_started", {"kind": kind, "run_date": run_date})
            return self.job_id
        cur = self._write(
            "INSERT INTO jobs(kind,run_date,status,requested_by,params_json,pid,started_at,heartbeat_at) "
            "VALUES(?,?,?,?,?,?,datetime('now'),datetime('now'))",
            (kind, run_date, "running", requested_by, _json(params), os.getpid()))
        if cur:
            self.job_id = int(cur.lastrowid)
            self.event("job_started", {"kind": kind, "run_date": run_date})
        return self.job_id

    def step_started(self, seq: int, name: str, attempt: int = 1) -> int | None:
        if self.job_id is None:
            return None
        self._started = time.monotonic()
        cur = self._write("INSERT INTO job_steps(job_id,seq,name,attempt,status,started_at) "
                          "VALUES(?,?,?,?, 'running',datetime('now'))",
                          (self.job_id, seq, name, attempt))
        self.step_id = int(cur.lastrowid) if cur else None
        self.event("step_started", {"seq": seq, "name": name, "attempt": attempt})
        return self.step_id

    def step_finished(self, *, rows_affected: int | None = None, detail: str | None = None, status: str = "ok") -> None:
        if self.step_id is None:
            return
        duration, step_id = max(0.0, time.monotonic() - self._started), self.step_id
        self._write("UPDATE job_steps SET status=?,finished_at=datetime('now'),duration_s=?,rows_affected=?,detail=? WHERE step_id=?",
                    (status, duration, rows_affected, detail, step_id))
        self.event("step_finished", {"status": status, "duration_s": duration})
        self.step_id = None

    def step_failed(self, exc: BaseException | str) -> None:
        if self.step_id is None:
            return
        duration, step_id, error = max(0.0, time.monotonic() - self._started), self.step_id, _error(exc)
        self._write("UPDATE job_steps SET status='fail',finished_at=datetime('now'),duration_s=?,error=? WHERE step_id=?",
                    (duration, error, step_id))
        self.event("step_failed", {"error": error, "duration_s": duration})
        self.step_id = None

    def artifact(self, kind: str, ref: str, label: str | None = None, meta: Any = None) -> None:
        if self.job_id is not None:
            self._write("INSERT INTO job_artifacts(job_id,step_id,kind,ref,label,meta_json) VALUES(?,?,?,?,?,?)",
                        (self.job_id, self.step_id, kind, ref, label, _json(meta or {})))
            self.event("artifact", {"kind": kind, "ref": ref, "label": label})

    def job_finished(self, status: str, error: BaseException | str | None = None) -> None:
        if self.job_id is None:
            return
        safe = _error(error) if error else None
        self.event("job_finished", {"status": status, "error": safe})
        self._write("UPDATE jobs SET status=?,finished_at=datetime('now'),heartbeat_at=datetime('now'),error=? WHERE job_id=?",
                    (status, safe, self.job_id))


def emit(event_type: str, payload: Any = None) -> None:
    try:
        emitter = _active.get()
        if emitter:
            emitter.event(event_type, payload)
    except Exception:
        pass


def add_artifact(kind: str, ref: str, label: str | None = None, meta: Any = None) -> None:
    try:
        emitter = _active.get()
        if emitter:
            emitter.artifact(kind, ref, label, meta)
    except Exception:
        pass


def finalize_orphaned_jobs(conn: sqlite3.Connection) -> int:
    try:
        rows = conn.execute("SELECT job_id FROM jobs WHERE status='running' AND pid <> ?", (os.getpid(),)).fetchall()
        for row in rows:
            JobEmitter(conn, int(row[0])).job_finished("interrupted", "Process ended before completion")
        return len(rows)
    except Exception:
        conn.rollback()
        return 0


def reserve_job(conn: sqlite3.Connection, kind: str, run_date: str | None, *,
                requested_by: str, params: dict[str, Any]) -> int:
    """Create the queued identity returned to the UI before background work starts."""
    cur = conn.execute(
        "INSERT INTO jobs(kind,run_date,status,requested_by,params_json,pid) VALUES(?,?,?,?,?,?)",
        (kind, run_date, "queued", requested_by, _json(params), os.getpid()),
    )
    conn.commit()
    return int(cur.lastrowid)


def request_cancel(conn: sqlite3.Connection, job_id: int) -> bool:
    """Persist a cooperative cancellation request without rewriting history."""
    row = conn.execute("SELECT status FROM jobs WHERE job_id=?", (job_id,)).fetchone()
    if row is None or row[0] != "running":
        return False
    exists = conn.execute(
        "SELECT 1 FROM job_events WHERE job_id=? AND event_type='cancel_requested' LIMIT 1", (job_id,)
    ).fetchone()
    if exists is None:
        JobEmitter(conn, job_id).event("cancel_requested", {"between_stages": True})
    return True


def cancel_requested(conn: sqlite3.Connection, job_id: int | None) -> bool:
    if job_id is None:
        return False
    try:
        return conn.execute(
            "SELECT 1 FROM job_events WHERE job_id=? AND event_type='cancel_requested' LIMIT 1", (job_id,)
        ).fetchone() is not None
    except Exception:
        return False


def retry_stage(conn: sqlite3.Connection, job_id: int, step_id: int,
                stage: Callable[[sqlite3.Connection, str], Any]) -> dict[str, Any]:
    """Append one attempt for a failed terminal-job step and refresh aggregate status."""
    job = conn.execute("SELECT status,run_date FROM jobs WHERE job_id=?", (job_id,)).fetchone()
    step = conn.execute(
        "SELECT seq,name,attempt,status FROM job_steps WHERE job_id=? AND step_id=?", (job_id, step_id)
    ).fetchone()
    if job is None or step is None:
        raise ValueError("job or step not found")
    if job[0] not in TERMINAL_STATUSES or step[3] != "fail":
        raise ValueError("retry requires a failed step on a terminal job")
    latest = conn.execute(
        "SELECT MAX(attempt) FROM job_steps WHERE job_id=? AND seq=?", (job_id, step[0])
    ).fetchone()[0]
    if int(step[2]) != int(latest):
        raise ValueError("only the latest failed attempt may be retried")

    conn.execute(
        "UPDATE jobs SET status='running',pid=?,finished_at=NULL,error=NULL,heartbeat_at=datetime('now') WHERE job_id=?",
        (os.getpid(), job_id),
    )
    conn.commit()
    emitter = JobEmitter(conn, job_id)
    emitter.event("retry_started", {"step_id": step_id, "name": step[1], "attempt": int(latest) + 1})
    retry_step_id = emitter.step_started(int(step[0]), str(step[1]), int(latest) + 1)
    try:
        stage(conn, str(job[1]))
        emitter.step_finished()
        result = StageResult(str(step[1]), "ok")
    except Exception as exc:
        emitter.step_failed(exc)
        result = StageResult(str(step[1]), "fail", _error(exc))

    remaining_failures = conn.execute(
        "SELECT COUNT(*) FROM job_steps s WHERE s.job_id=? AND s.attempt=("
        "SELECT MAX(s2.attempt) FROM job_steps s2 WHERE s2.job_id=s.job_id AND s2.seq=s.seq"
        ") AND s.status='fail'", (job_id,)
    ).fetchone()[0]
    original_status = str(job[0])
    if original_status == "partial":
        status = "succeeded" if not remaining_failures else "partial"
    else:
        # A single-stage repair cannot prove that an interrupted/failed night
        # completed all work, so preserve that honest aggregate state.
        status = original_status
    emitter.job_finished(status)
    return {"job_id": job_id, "step_id": retry_step_id, "status": status, "stage": result}


def run_stages(conn: sqlite3.Connection, run_date: str,
               stages: Iterable[tuple[str, Callable[[sqlite3.Connection, str], Any]]], *,
               requested_by: str, fetch_sources: bool = False, kind: str = "run-eod",
               on_stage: Callable[[StageResult], None] | None = None,
               on_stage_start: Callable[[str], None] | None = None,
               job_id: int | None = None) -> dict[str, Any]:
    """Shared API/CLI runner preserving per-stage failure isolation."""
    emitter, results = JobEmitter(conn, job_id), []
    def telemetry(method: str, *args: Any, **kwargs: Any) -> Any:
        try:
            return getattr(emitter, method)(*args, **kwargs)
        except Exception:
            return None

    telemetry("job_started", kind, run_date, requested_by=requested_by,
              params={"fetch_sources": fetch_sources})
    token = _active.set(emitter)
    try:
        for seq, (name, fn) in enumerate(stages, 1):
            if cancel_requested(conn, emitter.job_id):
                telemetry("job_finished", "cancelled")
                return {"job_id": emitter.job_id, "status": "cancelled", "stages": results}
            telemetry("heartbeat")
            if on_stage_start:
                on_stage_start(name)
            telemetry("step_started", seq, name)
            try:
                fn(conn, run_date)
                telemetry("step_finished")
                result = StageResult(name, "ok")
            except Exception as exc:
                telemetry("step_failed", exc)
                result = StageResult(name, "fail", _error(exc))
            results.append(result)
            if on_stage:
                on_stage(result)
        status = "partial" if any(r.status == "fail" for r in results) else "succeeded"
        telemetry("job_finished", status)
        return {"job_id": emitter.job_id, "status": status, "stages": results}
    except BaseException as exc:
        telemetry("job_finished", "failed", exc)
        raise
    finally:
        _active.reset(token)
