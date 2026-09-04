import sqlite3

from manas_os import db, jobs
from manas_os.api import app as api


def _ids(chunks):
    return [int(line[4:]) for chunk in chunks for line in chunk.splitlines() if line.startswith("id: ")]


def test_sse_orders_events_emits_done_and_resumes_without_duplicates(tmp_path):
    path = tmp_path / "stream.db"
    conn = db.init_db(path)
    result = jobs.run_stages(
        conn, "2026-07-11", [("one", lambda c, d: None), ("two", lambda c, d: None)],
        requested_by="test",
    )
    expected = [row[0] for row in conn.execute(
        "SELECT event_id FROM job_events WHERE job_id=? ORDER BY event_id", (result["job_id"],)
    )]
    conn.close()

    opener = lambda: db.connect(path)
    complete = list(api._stream_job_events(result["job_id"], 0, open_connection=opener, poll_seconds=0))
    assert _ids(complete) == expected
    assert complete[-1].startswith("event: done")

    split = expected[len(expected) // 2]
    resumed = list(api._stream_job_events(result["job_id"], split, open_connection=opener, poll_seconds=0))
    assert _ids(resumed) == [event_id for event_id in expected if event_id > split]
    assert set(_ids(resumed)).isdisjoint(event_id for event_id in expected if event_id <= split)

    # Three reconnecting clients can tail independently without shared state.
    cursors = (0, expected[1], expected[-2])
    received = [
        _ids(list(api._stream_job_events(result["job_id"], cursor, open_connection=opener, poll_seconds=0)))
        for cursor in cursors
    ]
    assert received == [[event_id for event_id in expected if event_id > cursor] for cursor in cursors]
    assert all(ids == sorted(set(ids)) for ids in received)


def test_sse_heartbeat_and_locked_tick_skip(tmp_path):
    path = tmp_path / "heartbeat.db"
    conn = db.init_db(path)
    job_id = conn.execute(
        "INSERT INTO jobs(kind,status,pid) VALUES('run-eod','running',?)", (999999,)
    ).lastrowid
    conn.commit()
    conn.close()

    now = [0.0]
    calls = [0]

    def clock():
        return now[0]

    def sleep(seconds):
        now[0] += max(seconds, 1.0)

    def opener():
        calls[0] += 1
        if calls[0] == 1:
            raise sqlite3.OperationalError("database is locked")
        return db.connect(path)

    stream = api._stream_job_events(
        job_id, 0, open_connection=opener, clock=clock, sleep=sleep,
        heartbeat_seconds=2, poll_seconds=1,
    )
    assert next(stream) == ": ping\n\n"
    assert calls[0] >= 2
    stream.close()


def test_cancel_is_cooperative_between_stages(tmp_path):
    conn = db.init_db(tmp_path / "cancel.db")
    seen = []

    def first(stage_conn, _run_date):
        seen.append("first-start")
        job_id = stage_conn.execute("SELECT MAX(job_id) FROM jobs").fetchone()[0]
        assert jobs.request_cancel(stage_conn, job_id)
        seen.append("first-finish")

    result = jobs.run_stages(
        conn, "2026-07-11", [("first", first), ("never", lambda c, d: seen.append("never"))],
        requested_by="test",
    )
    assert result["status"] == "cancelled"
    assert seen == ["first-start", "first-finish"]
    assert conn.execute("SELECT status FROM jobs WHERE job_id=?", (result["job_id"],)).fetchone()[0] == "cancelled"
    assert conn.execute(
        "SELECT COUNT(*) FROM job_events WHERE job_id=? AND event_type='cancel_requested'", (result["job_id"],)
    ).fetchone()[0] == 1
    conn.close()


def test_retry_appends_attempt_and_can_flip_partial_to_succeeded(tmp_path):
    conn = db.init_db(tmp_path / "retry.db")

    def fail(_conn, _date):
        raise RuntimeError("expected")

    result = jobs.run_stages(
        conn, "2026-07-11", [("repairable", fail), ("ok", lambda c, d: None)], requested_by="test"
    )
    failed = conn.execute(
        "SELECT step_id FROM job_steps WHERE job_id=? AND name='repairable'", (result["job_id"],)
    ).fetchone()[0]
    retried = jobs.retry_stage(conn, result["job_id"], failed, lambda c, d: None)
    attempts = conn.execute(
        "SELECT attempt,status FROM job_steps WHERE job_id=? AND name='repairable' ORDER BY attempt",
        (result["job_id"],),
    ).fetchall()
    assert [(row[0], row[1]) for row in attempts] == [(1, "fail"), (2, "ok")]
    assert retried["status"] == "succeeded"
    assert conn.execute("SELECT status FROM jobs WHERE job_id=?", (result["job_id"],)).fetchone()[0] == "succeeded"
    types = [row[0] for row in conn.execute(
        "SELECT event_type FROM job_events WHERE job_id=? ORDER BY event_id", (result["job_id"],)
    )]
    assert "retry_started" in types
    conn.close()


def test_orphan_finalization_is_replay_visible(tmp_path):
    conn = db.init_db(tmp_path / "orphan.db")
    job_id = conn.execute(
        "INSERT INTO jobs(kind,status,pid) VALUES('run-eod','running',?)", (999999,)
    ).lastrowid
    conn.commit()
    assert jobs.finalize_orphaned_jobs(conn) == 1
    row = conn.execute(
        "SELECT event_type,payload_json FROM job_events WHERE job_id=? ORDER BY event_id DESC LIMIT 1", (job_id,)
    ).fetchone()
    assert row[0] == "job_finished"
    assert '"status": "interrupted"' in row[1]
    conn.close()
