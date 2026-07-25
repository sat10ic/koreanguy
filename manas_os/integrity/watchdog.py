"""manas_os/integrity/watchdog.py -- the alerting layer on top of
manas_os/integrity/report.py.

The user's #1 complaint: the pipeline silently stops running and nothing
tells him. `integrity.report.run_all()` already computes the verdict (see
that module's docstring for the check list); this module's ONLY job is to
turn a non-PASS verdict into exactly one Telegram alert per day, via the
existing transactional outbox (manas_os.alerts.outbox) -- it does not
reimplement any check, does not compute freshness itself, and does not
write a new Telegram sender (reuses manas_os.alerts.telegram_engine's
config resolver + sender, exactly like live/heartbeat.py does).

THIS MUST RUN AS A SEPARATE PRE-MARKET JOB, NOT INSIDE `run-eod`. Integrity
checks whether the pipeline ran; running the watchdog from inside the
pipeline it is checking makes the freshness check vacuously pass every time
(the pipeline_runs row and fresh prices the check looks for would only ever
be missing if run-eod itself never started -- and in that case the watchdog
embedded inside it would never run either). `manas watchdog` is wired as
its own CLI subcommand for exactly this reason; schedule it (cron/Task
Scheduler) BEFORE the market session, independently of run-eod.

Design notes:
  * `run()` is handed an already-open, WRITABLE connection (conn) and uses
    it ONLY for the outbox tables (telegram_outbox via manas_os.alerts.
    outbox). It never uses `conn` for the integrity checks themselves --
    integrity.report.run_all() insists on opening its own strictly
    read-only `file:...?mode=ro` connection (see report.py's docstring for
    why: a watchdog that could itself lock/corrupt the DB it audits would
    defeat the point). The db file path is recovered from `conn` via
    `PRAGMA database_list` (same technique as manas_os/alpha/schema.py's
    `_database_identity`) so callers only ever hand this module one
    connection, not a connection AND a path.
  * Idempotency: alert_key = f"integrity-{today}" (one alert per calendar
    date, regardless of how many times the job is invoked that day -- a
    cron retry or a manual re-run must never spam the user). `force=True`
    clears any existing outbox row for that key first so a genuine resend
    is possible (outbox.enqueue is an idempotent INSERT OR IGNORE keyed on
    alert_key -- calling it again over an already-'sent' row is a silent
    no-op, so `force` has to clear the row, not just call enqueue again).
  * Never raises. Every branch is wrapped so a bug in this module can never
    make the watchdog process crash silently -- that failure mode (a
    watchdog that dies without telling anyone) is the exact bug class this
    module exists to kill. Exceptions are logged via ops_logging AND
    returned in `detail`.
"""
from __future__ import annotations

import sqlite3
from datetime import date
from typing import Any

from manas_os.alerts import outbox, telegram_engine
from manas_os.integrity import report as integrity_report
from manas_os.ops_logging import configure_ops_logger

_LOG = configure_ops_logger("integrity_watchdog")

_MAX_DETAIL_LINES = 6


def _db_path_from_conn(conn: sqlite3.Connection) -> str:
    """Recover the on-disk path of `conn`'s main database (same technique as
    manas_os/alpha/schema.py's _database_identity). Raises for an in-memory
    connection -- report.run_all() needs a real file path to open its own
    read-only connection against."""
    row = conn.execute("PRAGMA database_list").fetchone()
    path = str(row[2] or "") if row else ""
    if not path:
        raise RuntimeError(
            "watchdog: the connection passed to run() has no on-disk file "
            "(PRAGMA database_list returned no path) -- integrity.report.run_all() "
            "requires a real file to open its own read-only connection against; "
            "an in-memory sqlite3 connection cannot be used here."
        )
    return path


def _format_message(integrity_result: dict[str, Any]) -> str:
    """Short, plain-text message body -- phone-lock-screen readable, no
    markdown Telegram would mangle. Leads with the actionable line, then
    only the FAIL/WARN checks (PASS checks add nothing actionable), capped
    at _MAX_DETAIL_LINES with a '+N more' tail."""
    overall = integrity_result["overall_status"]
    checks = integrity_result.get("checks") or []
    bad = [c for c in checks if c["status"] in ("FAIL", "WARN")]

    # Count FAIL and WARN separately. Saying "FAIL (5 checks)" when one of the
    # five is only a WARN overstates the verdict, and an alert that inflates its
    # own severity is exactly the dishonesty this module exists to catch.
    n_fail = sum(1 for c in bad if c["status"] == "FAIL")
    n_warn = len(bad) - n_fail
    counts = f"{n_fail} failing" if n_fail else ""
    if n_warn:
        counts = f"{counts}, {n_warn} warning" if counts else f"{n_warn} warning"
    lines = [f"MANAS INTEGRITY: {overall} ({counts})" if counts
             else f"MANAS INTEGRITY: {overall}"]

    fresh = next((c for c in checks if c["name"] == "freshness"), None)
    if fresh is not None and fresh["status"] == "FAIL":
        ev = fresh.get("evidence") or {}
        sessions_behind = ev.get("sessions_behind")
        last_run = ev.get("last_pipeline_run_date")
        if sessions_behind:
            tail = f" ({last_run})" if last_run else ""
            lines.append(f"Pipeline last ran {sessions_behind} session(s) ago{tail}.")
        elif not ev.get("has_pipeline_run_for_expected_session"):
            lines.append("Pipeline did not run for the most recent session.")

    for c in bad[:_MAX_DETAIL_LINES]:
        detail = (c.get("detail") or "").replace("\n", " ").strip()
        lines.append(f"- {c['name']}: {c['status']} - {detail}")
    if len(bad) > _MAX_DETAIL_LINES:
        lines.append(f"+{len(bad) - _MAX_DETAIL_LINES} more")

    lines.append("Run: manas run-eod")
    return "\n".join(lines)


def run(
    conn: sqlite3.Connection,
    today: date | None = None,
    *,
    force: bool = False,
    dry_run: bool | None = None,
) -> dict[str, Any]:
    """Run every integrity check for `today` and, if the overall verdict is
    not PASS, enqueue + attempt delivery of exactly one Telegram alert
    (idempotent per calendar date; see module docstring).

    `dry_run` overrides config.telegram.dry_run when explicitly passed
    (True/False); left None it resolves from config exactly like every
    other alert path in this repo (telegram_engine._telegram_config()) --
    this mirrors telegram_engine.send_digest's own optional dry_run kwarg.

    Returns {"status": "ok"|"warn"|"fail", "alerted": bool, "alert_key": str,
    "detail": str, "integrity": <run_all() result or None>}. Never raises.
    """
    if today is None:
        today = date.today()
    today_s = today.isoformat()
    alert_key = f"integrity-{today_s}"

    try:
        db_path = _db_path_from_conn(conn)
        integrity_result = integrity_report.run_all(db_path, today)
    except Exception as exc:  # noqa: BLE001 - a watchdog that dies silently is the bug this exists to kill
        detail = f"watchdog: integrity.report.run_all() raised {type(exc).__name__}: {exc}"
        _LOG.error(detail)
        return {
            "status": "fail",
            "alerted": False,
            "alert_key": alert_key,
            "detail": detail,
            "integrity": None,
        }

    overall = integrity_result["overall_status"]

    if overall == "PASS":
        return {
            "status": "ok",
            "alerted": False,
            "alert_key": alert_key,
            "detail": "integrity status PASS; nothing to alert.",
            "integrity": integrity_result,
        }

    status = overall.lower()  # "warn" or "fail"

    try:
        outbox.ensure_schema(conn)
        existing = outbox.get(conn, alert_key)

        if existing is not None and not force:
            return {
                "status": status,
                "alerted": False,
                "alert_key": alert_key,
                "detail": (
                    f"already alerted for {today_s} (alert_key={alert_key}); "
                    "not re-enqueuing (pass force=True to resend)."
                ),
                "integrity": integrity_result,
            }

        if existing is not None and force:
            # enqueue() is an idempotent INSERT OR IGNORE keyed on alert_key --
            # re-enqueuing over an already-'sent' row would be a silent no-op,
            # so a genuine forced resend has to clear the prior row first. The
            # alert_key format itself never changes (stays f"integrity-{today}").
            conn.execute("DELETE FROM telegram_outbox WHERE alert_key = ?", (alert_key,))

        message = _format_message(integrity_result)
        outbox.enqueue(
            conn,
            alert_key,
            "integrity_watchdog",
            {"message": message, "today": today_s, "overall_status": overall},
        )
        # Enqueue commits here; delivery is only ever attempted after this
        # commit (same ordering guarantee as telegram_engine.send_digest /
        # live/heartbeat.py) -- a crash before this point means the alert
        # row never existed, nothing to duplicate on the next run.
        conn.commit()

        cfg = telegram_engine._telegram_config()  # noqa: SLF001 - reuse the one dry_run/token resolver
        is_dry_run = cfg["dry_run"] if dry_run is None else bool(dry_run)
        live_sender = telegram_engine.get_sender()
        send_fn = outbox.dry_run_or_live_sender(dry_run=is_dry_run, live_sender=live_sender)
        deliver = outbox.deliver_pending(conn, send_fn)
        sent = alert_key in deliver["delivered"]

        return {
            "status": status,
            "alerted": True,
            "alert_key": alert_key,
            "detail": (
                f"integrity {overall}; alert enqueued and delivery attempted "
                f"(sent={sent}, dry_run={is_dry_run})."
            ),
            "integrity": integrity_result,
        }
    except Exception as exc:  # noqa: BLE001 - same rule: never crash the caller
        detail = f"watchdog: alert enqueue/delivery raised {type(exc).__name__}: {exc}"
        _LOG.error(detail)
        try:
            conn.rollback()
        except Exception:  # noqa: BLE001 - best-effort only
            pass
        return {
            "status": "fail",
            "alerted": False,
            "alert_key": alert_key,
            "detail": detail,
            "integrity": integrity_result,
        }
