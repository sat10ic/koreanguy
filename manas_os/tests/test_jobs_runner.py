import os

from manas_os import db, jobs


def test_happy_path_records_ordered_events(tmp_path):
    conn = db.init_db(tmp_path / "jobs.db")
    seen = []
    result = jobs.run_stages(conn, "2026-07-11", [("one", lambda c, d: seen.append(("one", d))),
                                                   ("two", lambda c, d: seen.append(("two", d)))],
                             requested_by="test")
    assert result["status"] == "succeeded"
    assert seen == [("one", "2026-07-11"), ("two", "2026-07-11")]
    steps = conn.execute("SELECT name,status FROM job_steps ORDER BY seq").fetchall()
    assert [(r[0], r[1]) for r in steps] == [("one", "ok"), ("two", "ok")]
    ids = [r[0] for r in conn.execute("SELECT event_id FROM job_events ORDER BY event_id")]
    assert ids == sorted(set(ids))
    conn.close()


def test_reserved_job_identity_is_reused(tmp_path):
    conn = db.init_db(tmp_path / "jobs.db")
    job_id = jobs.reserve_job(
        conn, "run-eod", "2026-07-11", requested_by="api", params={"fetch_sources": True}
    )
    assert conn.execute("SELECT status FROM jobs WHERE job_id=?", (job_id,)).fetchone()[0] == "queued"
    result = jobs.run_stages(
        conn, "2026-07-11", [("one", lambda c, d: None)], requested_by="api",
        fetch_sources=True, job_id=job_id,
    )
    assert result["job_id"] == job_id
    assert conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 1
    assert conn.execute("SELECT status FROM jobs WHERE job_id=?", (job_id,)).fetchone()[0] == "succeeded"
    conn.close()


def test_stage_failure_is_partial_and_later_stage_runs(tmp_path):
    conn = db.init_db(tmp_path / "jobs.db")
    seen = []
    def fail(_conn, _date):
        raise RuntimeError("expected failure")
    result = jobs.run_stages(conn, "2026-07-11", [("bad", fail), ("later", lambda c, d: seen.append("later"))],
                             requested_by="test")
    assert result["status"] == "partial"
    assert seen == ["later"]
    assert conn.execute("SELECT status FROM jobs").fetchone()[0] == "partial"
    conn.close()


def test_telemetry_exception_does_not_change_stage_execution(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "jobs.db")
    monkeypatch.setattr(jobs.JobEmitter, "job_started", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("rail down")))
    seen = []
    result = jobs.run_stages(conn, "2026-07-11", [("real", lambda c, d: seen.append(d))], requested_by="test")
    assert seen == ["2026-07-11"]
    assert result["status"] == "succeeded"
    conn.close()


def test_orphan_finalization_and_cursor_paging(tmp_path):
    conn = db.init_db(tmp_path / "jobs.db")
    cur = conn.execute("INSERT INTO jobs(kind,status,pid) VALUES('run-eod','running',?)", (os.getpid() + 100000,))
    job_id = cur.lastrowid
    for n in range(5):
        conn.execute("INSERT INTO job_events(job_id,event_type,payload_json) VALUES(?,?,?)", (job_id, "tick", str(n)))
    conn.commit()
    assert jobs.finalize_orphaned_jobs(conn) == 1
    assert conn.execute("SELECT status FROM jobs WHERE job_id=?", (job_id,)).fetchone()[0] == "interrupted"
    first = [r[0] for r in conn.execute("SELECT event_id FROM job_events WHERE job_id=? AND event_id>? ORDER BY event_id LIMIT 2", (job_id, 0))]
    second = [r[0] for r in conn.execute("SELECT event_id FROM job_events WHERE job_id=? AND event_id>? ORDER BY event_id LIMIT 2", (job_id, first[-1]))]
    assert set(first).isdisjoint(second)
    assert first + second == sorted(first + second)
    conn.close()


def test_poll_endpoints_read_fixture_database(tmp_path, monkeypatch):
    from manas_os.api import app as api

    path = tmp_path / "api-jobs.db"
    conn = db.init_db(path)
    result = jobs.run_stages(conn, "2026-07-11", [("scan", lambda c, d: None)], requested_by="test")
    conn.close()
    init_db = db.init_db
    monkeypatch.setattr(api.db, "init_db", lambda: init_db(path))

    listed = api.jobs_list(limit=10)
    assert listed["jobs"][0]["job_id"] == result["job_id"]
    detail = api.jobs_get(result["job_id"])
    assert detail["steps"][0]["name"] == "scan"
    page = api.jobs_events(result["job_id"], after=0, limit=2)
    next_page = api.jobs_events(result["job_id"], after=page["next_after"], limit=20)
    assert {event["event_id"] for event in page["events"]}.isdisjoint(
        event["event_id"] for event in next_page["events"]
    )
