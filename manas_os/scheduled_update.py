"""Nightly auto-update: catch up every incomplete session, honestly logged.

Run by the Windows scheduled task "ManasOS-NightlyUpdate" (19:15 IST daily).
Also safe to run by hand after ``pip install -e .``: python -m manas_os.scheduled_update
Writes a plain-text result to manas_os/data/last_auto_update.log so the
data-health panel (and the user) can see what the last automatic run did.

Completion is defined by the durable run_manifest of required stages (audit
defect #2), NOT by the existence of scan_candidates rows. External ops step
(not done here): enable "run as soon as possible after a missed start" on the
Windows scheduled task and set an execution time limit slightly above the
real stage budget.
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from manas_os import db, jobs, market_calendar
from manas_os.cli import fetch_eod_sources_with_code, required_stage_names, run_eod
from manas_os.ops_logging import configure_ops_logger

REPO = Path(__file__).resolve().parents[1]
LOG = REPO / "manas_os" / "data" / "last_auto_update.log"


def pending_sessions(conn, today: date, cap: int = 10) -> list[str]:
    """Trading days that still need a full required-stage run, oldest first.

    A date is incomplete when any required stage is missing from run_manifest
    or has status fail — even if scan_candidates already has rows
    (reboot-mid-night scenario). ok/partial/skip all count as finished.
    """
    required = required_stage_names()
    end = market_calendar.last_trading_day(today)

    last_complete: date | None = None
    cur = end
    for _ in range(90):
        if market_calendar.is_trading_day(cur):
            if jobs.is_run_date_complete(conn, cur.isoformat(), required):
                last_complete = cur
                break
        cur -= timedelta(days=1)
        if cur.year < 2020:
            break

    if last_complete is None:
        # Nothing ever completed: re-run the most recent incomplete sessions
        # up to cap (avoid replaying unbounded history on a fresh DB).
        days: list[str] = []
        cur = end
        while len(days) < cap:
            if market_calendar.is_trading_day(cur):
                d = cur.isoformat()
                if not jobs.is_run_date_complete(conn, d, required):
                    days.append(d)
            cur -= timedelta(days=1)
            if cur.year < 2020:
                break
        return list(reversed(days))

    days = []
    cur = last_complete + timedelta(days=1)
    while cur <= end and len(days) < cap:
        if market_calendar.is_trading_day(cur):
            d = cur.isoformat()
            if not jobs.is_run_date_complete(conn, d, required):
                days.append(d)
        cur += timedelta(days=1)
    return days


def run() -> int:
    logger = configure_ops_logger("scheduled_update")
    lines: list[str] = [f"auto-update started {date.today().isoformat()}"]
    fetch_lines, worst = fetch_eod_sources_with_code()
    lines.extend(fetch_lines)
    conn = db.init_db()
    try:
        days = pending_sessions(conn, date.today())
    finally:
        conn.close()
    if not days:
        lines.append("nothing pending — analysis already at the latest trading day")
    for d in days:
        rc = run_eod(d, fetch_sources_first=False, requested_by="scheduled")
        lines.append(f"run-eod {d}: exit {rc}")
        worst = max(worst, int(rc))
    conn = db.init_db()
    try:
        scan_max = conn.execute("SELECT MAX(scan_date) FROM scan_candidates").fetchone()[0]
        price_max = conn.execute(
            "SELECT MAX(trade_date) FROM daily_prices WHERE series='EQ'").fetchone()[0]
        lines.append(f"final: prices at {price_max}, analysis at {scan_max}, exit {worst}")
    finally:
        conn.close()
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text("\n".join(lines), encoding="utf-8")
    for line in lines:
        logger.info(line)
    return worst


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except Exception:  # noqa: BLE001
        configure_ops_logger("scheduled_update").exception("scheduled update crashed")
        raise
