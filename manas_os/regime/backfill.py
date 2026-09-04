"""Regime-snapshot backfill — I1 (plan §P1.5).

breadth_daily already holds ~487 real trading days; XP/MBI/market_mode are
fully derivable from it. Rather than accumulating regime_snapshots one row
per day for a year, replay every historical breadth_daily date through the
SAME live path (``snapshot.run``) in ascending order so:

- XP's day-over-day recursion sees a real, unbroken prior-day chain (the
  reason order matters at all).
- there is exactly ONE writer for a regime_snapshots row (no separate
  backfill-specific compute path to drift from the live one — this IS the
  live one, just called once per historical date instead of once tonight).

For a historical date, ``run(conn, date)`` naturally computes source_date ==
run_date (the breadth row for that exact date exists), so every backfilled
row is data_stale=0 — correct: on that day, that breadth WAS "today's" data.
"""
from __future__ import annotations

import time

from manas_os.regime import snapshot

STAGE = "regime_backfill"
SOURCE = "breadth_daily_replay"


def _pending_dates(conn, start_date: str | None, end_date: str | None, force: bool) -> list[str]:
    where = []
    params: list[str] = []
    if start_date:
        where.append("trade_date >= ?")
        params.append(start_date)
    if end_date:
        where.append("trade_date <= ?")
        params.append(end_date)
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    dates = [r["trade_date"] for r in conn.execute(
        f"SELECT DISTINCT trade_date FROM breadth_daily {clause} ORDER BY trade_date ASC", params
    )]
    if force:
        return dates
    done = {
        r["snapshot_date"]
        for r in conn.execute("SELECT snapshot_date FROM regime_snapshots WHERE xp_value IS NOT NULL")
    }
    return [d for d in dates if d not in done]


def backfill_snapshots(
    conn, start_date: str | None = None, end_date: str | None = None, force: bool = False
) -> dict:
    """Replay breadth_daily ascending through ``snapshot.run``. Never raises.

    Returns {status, dates_processed, first_failure} — a per-date failure
    logs a pipeline_runs row for that date and stops the replay (later dates'
    XP recursion would be built on a gap otherwise); already-processed dates
    are kept.
    """
    started = time.monotonic()
    dates = _pending_dates(conn, start_date, end_date, force)
    processed = 0
    for d in dates:
        result = snapshot.run(conn, d)
        if result.get("status") == "fail":
            duration = time.monotonic() - started
            conn.execute(
                "INSERT INTO pipeline_runs (run_date, stage, source, status, rows_affected, "
                "duration_s, detail) VALUES (?,?,?,?,?,?,?)",
                (d, STAGE, SOURCE, "fail", processed, duration,
                 f"stopped at {d}: {result.get('detail')}"),
            )
            conn.commit()
            return {"status": "fail", "dates_processed": processed, "first_failure": d}
        processed += 1

    duration = time.monotonic() - started
    conn.execute(
        "INSERT INTO pipeline_runs (run_date, stage, source, status, rows_affected, "
        "duration_s, detail) VALUES (?,?,?,?,?,?,?)",
        (dates[-1] if dates else (end_date or start_date or "n/a"), STAGE, SOURCE, "ok", processed, duration,
         f"backfilled {processed} date(s)" if processed else "nothing pending"),
    )
    conn.commit()
    return {"status": "ok", "dates_processed": processed, "first_failure": None}
