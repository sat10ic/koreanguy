"""RELIABILITY_AUDIT_2026-07-19 defect #2: honest completion contract.

Exit-code propagation, durable run_manifest rows, and manifest-based catch-up
(reboot mid-night even when scan_candidates already exist).
"""
from __future__ import annotations

from datetime import date

from manas_os import db, jobs
from manas_os.cli import (
    OPTIONAL_STAGES,
    fetch_eod_sources_with_code,
    required_stage_names,
    run_eod,
)
from manas_os.scheduled_update import pending_sessions, run as scheduled_run


# ---------------------------------------------------------------------------
# Exit codes
# ---------------------------------------------------------------------------


def test_status_exit_code_mapping():
    assert jobs.status_exit_code("succeeded") == 0
    assert jobs.status_exit_code("partial") == 1
    assert jobs.status_exit_code("cancelled") == 1
    assert jobs.status_exit_code("failed") == 2
    assert jobs.status_exit_code("interrupted") == 2
    assert jobs.status_exit_code("unknown") == 2


def test_run_stages_exit_code_partial_and_succeeded(tmp_path):
    conn = db.init_db(tmp_path / "m.db")

    def fail(_c, _d):
        raise RuntimeError("boom")

    partial = jobs.run_stages(
        conn, "2026-07-11", [("bad", fail)], requested_by="test"
    )
    assert partial["status"] == "partial"
    assert partial["exit_code"] == 1

    ok = jobs.run_stages(
        conn, "2026-07-12", [("good", lambda c, d: None)], requested_by="test"
    )
    assert ok["status"] == "succeeded"
    assert ok["exit_code"] == 0
    conn.close()


def _patch_init_db(monkeypatch, path):
    real_init = db.init_db

    def _init(db_path=None):
        return real_init(path)

    monkeypatch.setattr("manas_os.db.init_db", _init)
    monkeypatch.setattr("manas_os.cli.db.init_db", _init)
    monkeypatch.setattr("manas_os.scheduled_update.db.init_db", _init)


def test_run_eod_propagates_partial_exit_code(tmp_path, monkeypatch):
    path = tmp_path / "eod.db"
    _patch_init_db(monkeypatch, path)

    def fake_run_stages(conn, run_date, stages, **kwargs):
        return {
            "job_id": 1,
            "status": "partial",
            "stages": [jobs.StageResult("x", "fail", "nope")],
            "exit_code": 1,
        }

    monkeypatch.setattr("manas_os.jobs.run_stages", fake_run_stages)
    monkeypatch.setattr(
        "manas_os.cli._load_stages",
        lambda: [("stub", lambda c, d: None)],
    )
    monkeypatch.setattr(
        "manas_os.live.refresh.stage",
        lambda c, d: None,
    )

    rc = run_eod("2026-07-11", fetch_sources_first=False, requested_by="test")
    assert rc == 1


def test_run_eod_propagates_failed_exit_code_on_crash(tmp_path, monkeypatch):
    path = tmp_path / "eod.db"
    _patch_init_db(monkeypatch, path)

    def boom(*_a, **_k):
        raise RuntimeError("runner dead")

    monkeypatch.setattr("manas_os.jobs.run_stages", boom)
    monkeypatch.setattr("manas_os.cli._load_stages", lambda: [("stub", lambda c, d: None)])
    monkeypatch.setattr("manas_os.live.refresh.stage", lambda c, d: None)

    rc = run_eod("2026-07-11", fetch_sources_first=False, requested_by="test")
    assert rc == 2


def test_fetch_failure_contributes_exit_code(monkeypatch):
    import subprocess

    def fake_run(*_a, **_k):
        raise subprocess.TimeoutExpired(cmd="x", timeout=1)

    monkeypatch.setattr(subprocess, "run", fake_run)
    lines, code = fetch_eod_sources_with_code()
    assert code == 1
    assert any("TIMED OUT" in line for line in lines)


def test_scheduler_aggregates_worst_exit_code(tmp_path, monkeypatch):
    path = tmp_path / "sched.db"
    _patch_init_db(monkeypatch, path)
    monkeypatch.setattr(
        "manas_os.scheduled_update.LOG", tmp_path / "last_auto_update.log"
    )

    # No pending sessions — worst should still reflect fetch failure.
    monkeypatch.setattr(
        "manas_os.scheduled_update.fetch_eod_sources_with_code",
        lambda: (["fetch_bhavcopy: TIMED OUT (1s)"], 1),
    )
    monkeypatch.setattr(
        "manas_os.scheduled_update.pending_sessions",
        lambda conn, today, cap=10: [],
    )

    assert scheduled_run() == 1

    # With a failed eod day, worst is 2.
    monkeypatch.setattr(
        "manas_os.scheduled_update.fetch_eod_sources_with_code",
        lambda: (["fetch_bhavcopy: exit 0"], 0),
    )
    monkeypatch.setattr(
        "manas_os.scheduled_update.pending_sessions",
        lambda conn, today, cap=10: ["2026-07-10"],
    )
    monkeypatch.setattr(
        "manas_os.scheduled_update.run_eod",
        lambda d, **k: 2,
    )
    assert scheduled_run() == 2


# ---------------------------------------------------------------------------
# Manifest rows
# ---------------------------------------------------------------------------


def test_run_stages_writes_manifest_per_stage(tmp_path):
    conn = db.init_db(tmp_path / "m.db")

    def fail(_c, _d):
        raise RuntimeError("x")

    def skip_stage(c, run_date):
        c.execute(
            "INSERT INTO pipeline_runs(run_date,stage,status,detail) VALUES (?,?,?,?)",
            (run_date, "skipper", "partial", "half done"),
        )
        c.commit()

    jobs.run_stages(
        conn,
        "2026-07-11",
        [("ok_stage", lambda c, d: None), ("bad", fail), ("skipper", skip_stage)],
        requested_by="test",
    )

    rows = {
        r[0]: r[1]
        for r in conn.execute(
            "SELECT stage, status FROM run_manifest WHERE run_date='2026-07-11' "
            "ORDER BY stage"
        )
    }
    assert rows == {"ok_stage": "ok", "bad": "fail", "skipper": "partial"}
    conn.close()


def test_manifest_upsert_on_rerun(tmp_path):
    conn = db.init_db(tmp_path / "m.db")

    def fail(_c, _d):
        raise RuntimeError("first")

    jobs.run_stages(conn, "2026-07-11", [("a", fail)], requested_by="test")
    assert conn.execute(
        "SELECT status FROM run_manifest WHERE run_date=? AND stage=?",
        ("2026-07-11", "a"),
    ).fetchone()[0] == "fail"

    jobs.run_stages(conn, "2026-07-11", [("a", lambda c, d: None)], requested_by="test")
    assert conn.execute(
        "SELECT status FROM run_manifest WHERE run_date=? AND stage=?",
        ("2026-07-11", "a"),
    ).fetchone()[0] == "ok"
    # Still a single row for the stage.
    assert conn.execute(
        "SELECT COUNT(*) FROM run_manifest WHERE run_date=? AND stage=?",
        ("2026-07-11", "a"),
    ).fetchone()[0] == 1
    conn.close()


def test_is_run_date_complete_accepts_ok_partial_skip(tmp_path):
    conn = db.init_db(tmp_path / "m.db")
    required = ["ingest_bhavcopy", "scan_candidates", "telegram_digest"]

    assert not jobs.is_run_date_complete(conn, "2026-07-11", required)

    for stage in required:
        jobs.record_run_manifest(conn, "2026-07-11", stage, "ok")
    assert jobs.is_run_date_complete(conn, "2026-07-11", required)

    jobs.record_run_manifest(conn, "2026-07-11", "scan_candidates", "fail")
    assert not jobs.is_run_date_complete(conn, "2026-07-11", required)

    jobs.record_run_manifest(conn, "2026-07-11", "scan_candidates", "partial")
    assert jobs.is_run_date_complete(conn, "2026-07-11", required)

    # Intentional no-op (coach empty shortlist, etc.) still completes the date.
    jobs.record_run_manifest(conn, "2026-07-11", "scan_candidates", "skip")
    assert jobs.is_run_date_complete(conn, "2026-07-11", required)
    conn.close()


def test_production_shaped_skips_still_complete_date(tmp_path, monkeypatch):
    """Normal EOD: coach/debate/mars often skip — must not re-queue forever."""
    conn = db.init_db(tmp_path / "m.db")
    required = [
        "ingest_bhavcopy",
        "scan_candidates",
        "agents_debate",
        "agents_coach",
        "ingest_mars",
        "telegram_digest",
    ]
    monkeypatch.setattr(
        "manas_os.scheduled_update.required_stage_names", lambda: required
    )
    d = "2026-07-10"
    for stage, status in (
        ("ingest_bhavcopy", "ok"),
        ("scan_candidates", "ok"),
        ("agents_debate", "skip"),
        ("agents_coach", "skip"),
        ("ingest_mars", "skip"),
        ("telegram_digest", "ok"),
    ):
        jobs.record_run_manifest(conn, d, stage, status)
    conn.commit()
    assert jobs.is_run_date_complete(conn, d, required)
    assert d not in pending_sessions(conn, date(2026, 7, 10), cap=10)
    conn.close()


def test_required_stage_names_exclude_optional():
    names = required_stage_names()
    assert "scan_candidates" in names
    assert "telegram_digest" in names
    assert "refresh_live_quotes" in names
    for opt in OPTIONAL_STAGES:
        assert opt not in names
    assert "ml_direction" not in names
    assert "discovery_bucket" not in names


# ---------------------------------------------------------------------------
# Catch-up: incomplete manifest despite scan_candidates
# ---------------------------------------------------------------------------


def test_catchup_reruns_incomplete_date_despite_scan_candidates(tmp_path, monkeypatch):
    """Reboot-mid-night: candidates exist but later stages never wrote manifest."""
    conn = db.init_db(tmp_path / "m.db")
    required = ["ingest_bhavcopy", "scan_candidates", "telegram_digest"]
    monkeypatch.setattr(
        "manas_os.scheduled_update.required_stage_names", lambda: required
    )

    # Friday 2026-07-10 and Monday 2026-07-13 are trading days; use a fixed today.
    incomplete = "2026-07-10"
    conn.execute(
        "INSERT INTO scan_candidates(scan_date, symbol, setup, readiness) "
        "VALUES (?, 'ACME', 'VCP', 0.9)",
        (incomplete,),
    )
    # Only partial manifest — missing telegram_digest (the audit scenario).
    jobs.record_run_manifest(conn, incomplete, "ingest_bhavcopy", "ok")
    jobs.record_run_manifest(conn, incomplete, "scan_candidates", "ok")
    conn.commit()

    # last_trading_day for 2026-07-10 (Friday) is itself.
    days = pending_sessions(conn, date(2026, 7, 10), cap=10)
    assert incomplete in days

    # Completing the manifest removes it from pending.
    jobs.record_run_manifest(conn, incomplete, "telegram_digest", "ok")
    days_after = pending_sessions(conn, date(2026, 7, 10), cap=10)
    assert incomplete not in days_after
    conn.close()


def test_complete_date_not_rerun(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    required = ["a", "b"]
    monkeypatch.setattr(
        "manas_os.scheduled_update.required_stage_names", lambda: required
    )
    d = "2026-07-10"
    for stage in required:
        jobs.record_run_manifest(conn, d, stage, "ok")
    conn.commit()

    days = pending_sessions(conn, date(2026, 7, 10), cap=10)
    assert d not in days
    conn.close()


def test_schema_creates_run_manifest(tmp_path):
    conn = db.init_db(tmp_path / "m.db")
    tables = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    assert "run_manifest" in tables
    cols = {r[1] for r in conn.execute("PRAGMA table_info(run_manifest)")}
    assert cols >= {"run_date", "stage", "status", "finished_at"}
    conn.close()
