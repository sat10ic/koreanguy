from manas_os import db


def test_jobs_schema_and_indexes(tmp_path):
    conn = db.init_db(tmp_path / "jobs.db")
    try:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"jobs", "job_steps", "job_events", "job_artifacts"} <= tables
        indexes = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")}
        assert {"idx_jobs_kind_date", "idx_job_steps_job", "idx_job_events_job", "idx_job_artifacts_job"} <= indexes
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    finally:
        conn.close()


def test_job_status_is_constrained(tmp_path):
    conn = db.init_db(tmp_path / "jobs.db")
    try:
        try:
            conn.execute("INSERT INTO jobs(kind,status) VALUES('x','invented')")
        except Exception:
            pass
        else:
            raise AssertionError("jobs.status accepted an unknown value")
    finally:
        conn.close()
