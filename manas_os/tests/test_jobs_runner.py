import os
import time

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


def test_stage_reported_skip_makes_job_partial_and_keeps_reason(tmp_path):
    conn = db.init_db(tmp_path / "jobs.db")
    def skipped(c, run_date):
        c.execute(
            "INSERT INTO pipeline_runs(run_date,stage,status,detail) VALUES (?,?,?,?)",
            (run_date, "source", "skip", "folder missing"),
        )
        c.commit()

    result = jobs.run_stages(
        conn, "2026-07-16", [("source", skipped)], requested_by="test"
    )

    assert result["status"] == "partial"
    assert result["stages"][0].status == "skip"
    assert result["stages"][0].error == "folder missing"
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


def test_reap_if_stalled_fails_a_silent_running_job(tmp_path):
    # Same pid as this process (so finalize_orphaned_jobs would NOT catch it --
    # that's exactly the gap the watchdog closes: a job whose thread hung or
    # died silently inside a still-live server process).
    conn = db.init_db(tmp_path / "jobs.db")
    cur = conn.execute(
        "INSERT INTO jobs(kind,run_date,status,pid,params_json,started_at,heartbeat_at) "
        "VALUES('debate-on-demand','2026-07-17','running',?,?,datetime('now','-20 minutes'),NULL)",
        (os.getpid(), '{"symbol": "TANLA"}'),
    )
    job_id = cur.lastrowid
    step_id = conn.execute(
        "INSERT INTO job_steps(job_id,seq,name,status,started_at) VALUES(?,1,'context_pack','running',datetime('now','-20 minutes'))",
        (job_id,),
    ).lastrowid
    conn.commit()

    reaped = jobs.reap_if_stalled(conn, job_id, stale_after_s=600)

    assert reaped == {
        "job_id": job_id, "kind": "debate-on-demand", "run_date": "2026-07-17",
        "params_json": '{"symbol": "TANLA"}',
    }
    row = conn.execute("SELECT status,error FROM jobs WHERE job_id=?", (job_id,)).fetchone()
    assert row[0] == "failed"
    assert "stalled" in row[1]
    step = conn.execute("SELECT status,error FROM job_steps WHERE step_id=?", (step_id,)).fetchone()
    assert step[0] == "fail"
    assert "stalled" in step[1]
    # The reap itself is durable/replay-visible via job_events, same contract
    # as finalize_orphaned_jobs.
    last_event = conn.execute(
        "SELECT event_type FROM job_events WHERE job_id=? ORDER BY event_id DESC LIMIT 1", (job_id,)
    ).fetchone()
    assert last_event[0] == "job_finished"
    conn.close()


def test_reap_if_stalled_leaves_a_fresh_running_job_alone(tmp_path):
    conn = db.init_db(tmp_path / "jobs.db")
    cur = conn.execute(
        "INSERT INTO jobs(kind,run_date,status,pid,heartbeat_at) VALUES('debate-on-demand','2026-07-17','running',?,datetime('now'))",
        (os.getpid(),),
    )
    job_id = cur.lastrowid
    conn.commit()

    assert jobs.reap_if_stalled(conn, job_id, stale_after_s=600) is None
    assert conn.execute("SELECT status FROM jobs WHERE job_id=?", (job_id,)).fetchone()[0] == "running"
    conn.close()


def test_reap_if_stalled_uses_last_event_not_just_start_time(tmp_path):
    # A job that started 20 minutes ago but emitted an event 1 minute ago is
    # slow, not dead -- staleness must be measured from real activity, never
    # penalizing a genuinely long-running (many models, slow API) job.
    conn = db.init_db(tmp_path / "jobs.db")
    cur = conn.execute(
        "INSERT INTO jobs(kind,run_date,status,pid,started_at) "
        "VALUES('debate-on-demand','2026-07-17','running',?,datetime('now','-20 minutes'))",
        (os.getpid(),),
    )
    job_id = cur.lastrowid
    conn.execute(
        "INSERT INTO job_events(job_id,event_type,payload_json,created_at) "
        "VALUES(?,'seat_verdict','{}',datetime('now','-1 minutes'))",
        (job_id,),
    )
    conn.commit()

    assert jobs.reap_if_stalled(conn, job_id, stale_after_s=600) is None
    assert conn.execute("SELECT status FROM jobs WHERE job_id=?", (job_id,)).fetchone()[0] == "running"
    conn.close()


def test_reap_all_stalled_jobs_sweeps_every_running_job(tmp_path):
    conn = db.init_db(tmp_path / "jobs.db")
    stale = conn.execute(
        "INSERT INTO jobs(kind,run_date,status,pid,params_json,started_at) "
        "VALUES('debate-on-demand','2026-07-17','running',?,?,datetime('now','-20 minutes'))",
        (os.getpid(), '{"symbol": "TANLA"}'),
    ).lastrowid
    fresh = conn.execute(
        "INSERT INTO jobs(kind,run_date,status,pid,heartbeat_at) VALUES('run-eod','2026-07-17','running',?,datetime('now'))",
        (os.getpid(),),
    ).lastrowid
    conn.commit()

    reaped = jobs.reap_all_stalled_jobs(conn, stale_after_s=600)

    assert [r["job_id"] for r in reaped] == [stale]
    assert conn.execute("SELECT status FROM jobs WHERE job_id=?", (stale,)).fetchone()[0] == "failed"
    assert conn.execute("SELECT status FROM jobs WHERE job_id=?", (fresh,)).fetchone()[0] == "running"
    conn.close()


def test_sse_tail_self_heals_a_stalled_job(tmp_path):
    # End-to-end through the exact endpoint DebateLivePanel subscribes to:
    # a job stuck 'running' with no events must flip to failed within the
    # stream itself, so the UI stops showing "Waiting on response" forever.
    from manas_os.api import app as api

    path = tmp_path / "sse-watchdog.db"
    conn = db.init_db(path)
    job_id = conn.execute(
        "INSERT INTO jobs(kind,run_date,status,pid,started_at) "
        "VALUES('debate-on-demand','2026-07-17','running',?,datetime('now','-20 minutes'))",
        (os.getpid(),),
    ).lastrowid
    conn.commit()
    conn.close()

    opener = lambda: db.connect(path)
    chunks = list(api._stream_job_events(job_id, 0, open_connection=opener, poll_seconds=0))
    assert any("job_finished" in chunk for chunk in chunks)
    assert chunks[-1].startswith("event: done")

    final = db.connect(path)
    assert final.execute("SELECT status FROM jobs WHERE job_id=?", (job_id,)).fetchone()[0] == "failed"
    final.close()


def test_reap_if_stalled_records_untrusted_output_note(tmp_path):
    # RELIABILITY_AUDIT_2026-07-19 defect #3: a reap can only ever flip
    # durable status -- the stage's Python thread cannot be killed and may
    # still be silently running/writing after the row says "failed". The
    # reap must say so explicitly instead of letting "failed" imply the
    # work actually stopped.
    conn = db.init_db(tmp_path / "jobs.db")
    cur = conn.execute(
        "INSERT INTO jobs(kind,run_date,status,pid,started_at,heartbeat_at) "
        "VALUES('run-eod','2026-07-17','running',?,datetime('now','-20 minutes'),NULL)",
        (os.getpid(),),
    )
    job_id = cur.lastrowid
    conn.commit()

    reaped = jobs.reap_if_stalled(conn, job_id, stale_after_s=600)
    assert reaped is not None

    events = [r[0] for r in conn.execute(
        "SELECT event_type FROM job_events WHERE job_id=? ORDER BY event_id", (job_id,)
    )]
    assert "reap_note" in events
    # job_finished must still be last (existing SSE/UI contract), so the
    # note is inserted before it, not after.
    assert events[-1] == "job_finished"

    note_payload = conn.execute(
        "SELECT payload_json FROM job_events WHERE job_id=? AND event_type='reap_note'", (job_id,)
    ).fetchone()[0]
    assert "output of this run is untrusted" in note_payload
    conn.close()


def test_rollback_before_step_failed_leaves_no_partial_rows(tmp_path):
    # RELIABILITY_AUDIT_2026-07-19 defect #6: step_failed() was previously
    # called without rolling back the stage's own partial business
    # transaction first, so a failed stage's half-written rows could
    # survive on the shared connection right alongside the "fail" telemetry.
    conn = db.init_db(tmp_path / "jobs.db")
    conn.execute("CREATE TABLE scratch_partial (id INTEGER PRIMARY KEY, val TEXT)")
    conn.commit()

    def bad_stage(c, run_date):
        c.execute("INSERT INTO scratch_partial (val) VALUES (?)", ("uncommitted",))
        raise RuntimeError("stage blew up mid-transaction")

    result = jobs.run_stages(conn, "2026-07-11", [("bad", bad_stage)], requested_by="test")

    assert result["status"] == "partial"
    # The INSERT was never committed by the stage -- the runner's rollback
    # (which must happen BEFORE step_failed is recorded) must have
    # discarded it.
    assert conn.execute("SELECT COUNT(*) FROM scratch_partial").fetchone()[0] == 0
    # The failure telemetry itself is a separate, later, committed write and
    # must still be present -- the rollback must not also erase it.
    step = conn.execute("SELECT status, error FROM job_steps WHERE name='bad'").fetchone()
    assert step[0] == "fail"
    assert "stage blew up" in step[1]
    conn.close()


def _job_id(conn):
    return conn.execute("SELECT job_id FROM jobs ORDER BY job_id DESC LIMIT 1").fetchone()[0]


def test_in_stage_heartbeat_keeps_a_slow_stage_from_looking_stalled(tmp_path):
    # RELIABILITY_AUDIT_2026-07-19 defect #3: run_stages() previously only
    # heartbeated BETWEEN stages (jobs.py ~380-400), so a single stage that
    # legitimately runs past STALE_JOB_SECONDS (600s) with no further
    # job_events row would look dead to reap_if_stalled(). Simulate "700s of
    # silence" by backdating every timestamp source the reaper reads, then
    # give the in-stage ticker (tiny interval so the test stays fast) one
    # window to refresh heartbeat_at before checking staleness mid-stage.
    conn = db.init_db(tmp_path / "jobs.db")
    observed = {}

    def slow_stage(c, run_date):
        job_id = _job_id(c)
        c.execute(
            "UPDATE jobs SET heartbeat_at=datetime('now','-700 seconds'), "
            "started_at=datetime('now','-700 seconds') WHERE job_id=?",
            (job_id,),
        )
        c.execute(
            "UPDATE job_events SET created_at=datetime('now','-700 seconds') WHERE job_id=?",
            (job_id,),
        )
        c.commit()
        time.sleep(0.25)
        observed["stalled"] = jobs.stalled_job_age(c, job_id, stale_after_s=600)

    result = jobs.run_stages(
        conn, "2026-07-11", [("slow", slow_stage)], requested_by="test",
        heartbeat_interval_s=0.05,
    )

    assert result["status"] == "succeeded"
    assert observed["stalled"] is None, "in-stage heartbeat should have kept the job looking alive"
    conn.close()


def test_in_stage_heartbeat_must_actually_tick_to_help(tmp_path):
    # Counterfactual for the test above: with an interval longer than the
    # stage's runtime, the ticker never fires within the window, so the
    # same backdated job DOES read as stalled. This proves the previous
    # test's non-staleness is caused by the ticker firing, not by some
    # unrelated freshness signal.
    conn = db.init_db(tmp_path / "jobs.db")
    observed = {}

    def slow_stage(c, run_date):
        job_id = _job_id(c)
        c.execute(
            "UPDATE jobs SET heartbeat_at=datetime('now','-700 seconds'), "
            "started_at=datetime('now','-700 seconds') WHERE job_id=?",
            (job_id,),
        )
        c.execute(
            "UPDATE job_events SET created_at=datetime('now','-700 seconds') WHERE job_id=?",
            (job_id,),
        )
        c.commit()
        time.sleep(0.25)
        observed["stalled"] = jobs.stalled_job_age(c, job_id, stale_after_s=600)

    jobs.run_stages(
        conn, "2026-07-11", [("slow", slow_stage)], requested_by="test",
        heartbeat_interval_s=30.0,
    )

    assert observed["stalled"] is not None
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
