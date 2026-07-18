"""Nightly auto-update: catch up every un-scanned session, honestly logged.

Run by the Windows scheduled task "ManasOS-NightlyUpdate" (19:15 IST daily).
Also safe to run by hand: python manas_os/scheduled_update.py
Writes a plain-text result to manas_os/data/last_auto_update.log so the
data-health panel (and the user) can see what the last automatic run did.
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from manas_os import db, market_calendar  # noqa: E402
from manas_os.cli import main as cli_main  # noqa: E402

LOG = REPO / "manas_os" / "data" / "last_auto_update.log"


def pending_sessions(conn, today: date, cap: int = 10) -> list[str]:
    row = conn.execute("SELECT MAX(scan_date) FROM scan_candidates").fetchone()
    last_scan = row[0] if row and row[0] else None
    end = market_calendar.last_trading_day(today)
    if last_scan is None:
        return [end.isoformat()]
    days: list[str] = []
    cur = date.fromisoformat(last_scan) + timedelta(days=1)
    while cur <= end and len(days) < cap:
        if market_calendar.is_trading_day(cur):
            days.append(cur.isoformat())
        cur += timedelta(days=1)
    return days


def run() -> int:
    lines: list[str] = [f"auto-update started {date.today().isoformat()}"]
    conn = db.init_db()
    try:
        days = pending_sessions(conn, date.today())
    finally:
        conn.close()
    if not days:
        lines.append("nothing pending — analysis already at the latest trading day")
    for d in days:
        rc = cli_main(["run-eod", "--date", d])
        lines.append(f"run-eod {d}: exit {rc}")
    conn = db.init_db()
    try:
        scan_max = conn.execute("SELECT MAX(scan_date) FROM scan_candidates").fetchone()[0]
        price_max = conn.execute(
            "SELECT MAX(trade_date) FROM daily_prices WHERE series='EQ'").fetchone()[0]
        lines.append(f"final: prices at {price_max}, analysis at {scan_max}")
    finally:
        conn.close()
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
