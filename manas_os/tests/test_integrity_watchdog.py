"""Tests for manas_os.integrity.watchdog -- the alerting layer over
manas_os/integrity/report.py's checks. Mirrors manas_os/tests/test_integrity.py's
fixture style (a real on-disk SQLite file via db.init_db, never :memory:) but
keeps every test decoupled from the live repo's check_lookahead/overfit_capacity
state by monkeypatching report.run_all() with a controlled result -- exactly
the strategy test_integrity.py's own test_cli_integrity_exit_code_zero_on_pass
uses, for the same reason (check_lookahead scans the real manas_os/ tree and
may legitimately be FAIL against real code at any given time).

No test here touches the real manas.db and no test makes a network call --
delivery is always exercised either via dry_run=True (which short-circuits
before any sender is invoked) or via a fake sender substituted for
telegram_engine.get_sender().
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date
from pathlib import Path

from manas_os import cli, db
from manas_os.alerts import outbox
from manas_os.integrity import watchdog

DATE = date(2026, 7, 24)
DATE_S = "2026-07-24"
ALERT_KEY = f"integrity-{DATE_S}"


def _mk_conn(tmp_path: Path) -> tuple[sqlite3.Connection, Path]:
    path = tmp_path / "m.db"
    conn = db.init_db(path)
    return conn, path


def _mk_result(status: str, checks: list[dict] | None = None) -> dict:
    if checks is None:
        checks = [{"name": "freshness", "status": status, "detail": "stub", "evidence": {}}]
    n_fail = sum(1 for c in checks if c["status"] == "FAIL")
    n_warn = sum(1 for c in checks if c["status"] == "WARN")
    return {
        "today": DATE_S,
        "expected_session": DATE_S,
        "overall_status": status,
        "n_checks": len(checks),
        "n_fail": n_fail,
        "n_warn": n_warn,
        "checks": checks,
    }


def _patch_run_all(monkeypatch, result: dict) -> None:
    monkeypatch.setattr(watchdog.integrity_report, "run_all", lambda db_path, today: result)


def _patch_telegram_config(monkeypatch, *, dry_run: bool, bot_token: str = "x", chat_id: str = "y") -> None:
    def fake_get(key, default=None):
        values = {
            "telegram.dry_run": dry_run,
            "telegram.bot_token": bot_token,
            "telegram.chat_id": chat_id,
        }
        return values.get(key, default)

    monkeypatch.setattr(watchdog.telegram_engine.config, "get", fake_get)


# ---------------------------------------------------------------------------
# PASS -> no alert
# ---------------------------------------------------------------------------


def test_pass_status_does_not_enqueue_an_alert(tmp_path, monkeypatch):
    conn, _path = _mk_conn(tmp_path)
    try:
        _patch_run_all(monkeypatch, _mk_result("PASS"))

        result = watchdog.run(conn, DATE)

        assert result["status"] == "ok"
        assert result["alerted"] is False
        assert result["alert_key"] == ALERT_KEY
        assert outbox.get(conn, ALERT_KEY) is None
        n = conn.execute("SELECT COUNT(*) AS n FROM telegram_outbox").fetchone()["n"]
        assert n == 0
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# FAIL -> exactly one alert, body names the failing checks
# ---------------------------------------------------------------------------


def test_fail_status_enqueues_exactly_one_alert_naming_failing_checks(tmp_path, monkeypatch):
    checks = [
        {"name": "freshness", "status": "FAIL",
         "detail": "no pipeline_runs row for 2026-07-24", "evidence": {"sessions_behind": 2}},
        {"name": "silent_skips", "status": "FAIL",
         "detail": "ingest_mars wrote 0 rows", "evidence": {}},
        {"name": "verdict_grading", "status": "PASS", "detail": "all graded", "evidence": {}},
    ]
    conn, _path = _mk_conn(tmp_path)
    try:
        _patch_run_all(monkeypatch, _mk_result("FAIL", checks))

        result = watchdog.run(conn, DATE, dry_run=True)  # dry_run=True -> never touches a real sender

        assert result["status"] == "fail"
        assert result["alerted"] is True
        assert result["alert_key"] == ALERT_KEY

        n = conn.execute("SELECT COUNT(*) AS n FROM telegram_outbox").fetchone()["n"]
        assert n == 1

        row = outbox.get(conn, ALERT_KEY)
        assert row is not None
        assert row["state"] == "sent"  # dry_run still walks pending -> sent
        message = json.loads(row["payload_json"])["message"]
        assert "freshness" in message
        assert "silent_skips" in message
        assert "verdict_grading" not in message  # PASS checks are not actionable noise
        assert "MANAS INTEGRITY: FAIL" in message
    finally:
        conn.close()


def test_fail_message_body_is_short_and_capped(tmp_path, monkeypatch):
    """>6 failing checks must cap the bullet list and append a '+N more' tail
    -- the body has to stay readable on a phone lock screen."""
    checks = [
        {"name": f"check_{i}", "status": "FAIL", "detail": f"detail {i}", "evidence": {}}
        for i in range(9)
    ]
    conn, _path = _mk_conn(tmp_path)
    try:
        _patch_run_all(monkeypatch, _mk_result("FAIL", checks))
        result = watchdog.run(conn, DATE, dry_run=True)

        row = outbox.get(conn, ALERT_KEY)
        message = json.loads(row["payload_json"])["message"]
        lines = message.splitlines()
        bullet_lines = [ln for ln in lines if ln.startswith("- check_")]
        assert len(bullet_lines) == 6
        assert "+3 more" in message
        assert result["status"] == "fail"
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# WARN -> still alerts, status field reflects "warn"
# ---------------------------------------------------------------------------


def test_warn_status_alerts_with_warn_status_field(tmp_path, monkeypatch):
    checks = [{"name": "survivorship", "status": "WARN", "detail": "dead-rate ratio 4.0", "evidence": {}}]
    conn, _path = _mk_conn(tmp_path)
    try:
        _patch_run_all(monkeypatch, _mk_result("WARN", checks))
        result = watchdog.run(conn, DATE, dry_run=True)

        assert result["status"] == "warn"
        assert result["alerted"] is True
        row = outbox.get(conn, ALERT_KEY)
        assert row["state"] == "sent"
        assert "survivorship" in json.loads(row["payload_json"])["message"]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# idempotency: second same-day invocation does not spam; force=True resends
# ---------------------------------------------------------------------------


def test_second_invocation_same_day_does_not_alert_again_force_resends(tmp_path, monkeypatch):
    checks = [{"name": "freshness", "status": "FAIL", "detail": "no pipeline_runs row", "evidence": {}}]
    conn, _path = _mk_conn(tmp_path)
    try:
        _patch_run_all(monkeypatch, _mk_result("FAIL", checks))
        _patch_telegram_config(monkeypatch, dry_run=False, bot_token="FAKE-TOKEN-abc123", chat_id="999")

        sent: list[str] = []

        def fake_sender(message: str):
            sent.append(message)
            return {"message_id": "1"}

        monkeypatch.setattr(watchdog.telegram_engine, "get_sender", lambda: fake_sender)

        result1 = watchdog.run(conn, DATE)
        assert result1["alerted"] is True
        assert len(sent) == 1

        result2 = watchdog.run(conn, DATE)
        assert result2["alerted"] is False
        assert "already alerted" in result2["detail"]
        assert len(sent) == 1  # no second send

        n = conn.execute("SELECT COUNT(*) AS n FROM telegram_outbox").fetchone()["n"]
        assert n == 1  # still exactly one outbox row for this alert_key

        result3 = watchdog.run(conn, DATE, force=True)
        assert result3["alerted"] is True
        assert len(sent) == 2  # forced resend actually re-sent

        n2 = conn.execute("SELECT COUNT(*) AS n FROM telegram_outbox").fetchone()["n"]
        assert n2 == 1  # forced resend replaces the row, does not duplicate it
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# run_all raising -> status "fail", never propagates
# ---------------------------------------------------------------------------


def test_run_all_raising_returns_fail_status_without_propagating(tmp_path, monkeypatch):
    def boom(db_path, today):
        raise RuntimeError("integrity checks exploded")

    conn, _path = _mk_conn(tmp_path)
    try:
        monkeypatch.setattr(watchdog.integrity_report, "run_all", boom)

        result = watchdog.run(conn, DATE)  # must not raise

        assert result["status"] == "fail"
        assert result["alerted"] is False
        assert result["integrity"] is None
        assert "integrity checks exploded" in result["detail"]
        assert outbox.get(conn, ALERT_KEY) is None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# the bot token must never appear anywhere in the alert
# ---------------------------------------------------------------------------


def test_message_and_outbox_never_contain_the_bot_token(tmp_path, monkeypatch):
    checks = [{"name": "freshness", "status": "FAIL", "detail": "no pipeline_runs row", "evidence": {}}]
    conn, _path = _mk_conn(tmp_path)
    try:
        _patch_run_all(monkeypatch, _mk_result("FAIL", checks))
        secret_token = "SECRET-BOT-TOKEN-should-never-leak"
        _patch_telegram_config(monkeypatch, dry_run=False, bot_token=secret_token, chat_id="999")

        captured: list[str] = []

        def fake_sender(message: str):
            captured.append(message)

        monkeypatch.setattr(watchdog.telegram_engine, "get_sender", lambda: fake_sender)

        result = watchdog.run(conn, DATE)

        assert result["alerted"] is True
        assert captured, "sender was never invoked"
        for msg in captured:
            assert secret_token not in msg
        row = outbox.get(conn, ALERT_KEY)
        assert secret_token not in row["payload_json"]
        assert secret_token not in result["detail"]
        assert secret_token not in json.dumps(result["integrity"], default=str)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# CLI wiring: exit codes
# ---------------------------------------------------------------------------


def _patch_cli_init_db(monkeypatch, path: Path) -> None:
    real_init = db.init_db

    def _init(db_path=None):
        return real_init(path)

    monkeypatch.setattr("manas_os.cli.db.init_db", _init)


def test_cli_watchdog_exit_code_nonzero_on_fail(tmp_path, monkeypatch, capsys):
    conn, path = _mk_conn(tmp_path)
    conn.close()
    _patch_cli_init_db(monkeypatch, path)
    checks = [{"name": "freshness", "status": "FAIL", "detail": "no pipeline_runs row", "evidence": {}}]
    monkeypatch.setattr("manas_os.integrity.report.run_all", lambda db_path, today: _mk_result("FAIL", checks))

    parser = cli.build_parser()
    args = parser.parse_args(["watchdog", "--date", DATE_S, "--dry-run"])
    rc = args.func(args)

    assert rc == 1
    out = capsys.readouterr().out
    assert "status=fail" in out
    assert "alerted=True" in out


def test_cli_watchdog_exit_code_zero_on_warn(tmp_path, monkeypatch, capsys):
    conn, path = _mk_conn(tmp_path)
    conn.close()
    _patch_cli_init_db(monkeypatch, path)
    checks = [{"name": "survivorship", "status": "WARN", "detail": "dead-rate ratio 4.0", "evidence": {}}]
    monkeypatch.setattr("manas_os.integrity.report.run_all", lambda db_path, today: _mk_result("WARN", checks))

    parser = cli.build_parser()
    args = parser.parse_args(["watchdog", "--date", DATE_S, "--dry-run"])
    rc = args.func(args)

    assert rc == 0
    out = capsys.readouterr().out
    assert "status=warn" in out
    assert "alerted=True" in out


def test_cli_watchdog_exit_code_zero_on_pass(tmp_path, monkeypatch, capsys):
    conn, path = _mk_conn(tmp_path)
    conn.close()
    _patch_cli_init_db(monkeypatch, path)
    monkeypatch.setattr("manas_os.integrity.report.run_all", lambda db_path, today: _mk_result("PASS"))

    parser = cli.build_parser()
    args = parser.parse_args(["watchdog", "--date", DATE_S, "--dry-run"])
    rc = args.func(args)

    assert rc == 0
    out = capsys.readouterr().out
    assert "status=ok" in out
    assert "alerted=False" in out
