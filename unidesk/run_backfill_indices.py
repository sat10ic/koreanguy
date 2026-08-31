"""Backfill NSE index daily closes from nse-archives (NikhilSuthar/indian-market-data).

Fetches ind_close_all for each session from START_DATE to the last known session
in the existing indices.parquet, then appends to the parquet store.

The existing store has 1,299 sessions from 2021-06-01 → 2026-08-28.
This backfill targets the gap: 2016-01-01 → 2021-05-31.

    .venv-orderflow/Scripts/python.exe unidesk/run_backfill_indices.py --dry-run

    .venv-orderflow/Scripts/python.exe unidesk/run_backfill_indices.py

Uses the existing indices.py adapter (fetch_ind_close_all, parse_ind_close_all_rows).
No credentials. Public NSE data via nse-archives. Rate-limited to ~1 request/s.
"""
from __future__ import annotations

import sys
import time
import argparse
from datetime import date, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from unidesk.momentum.data.indices import (
    fetch_ind_close_all, harvest_sessions, load_index_rows, persist_index_rows,
    parse_ind_close_all_rows,
)
from unidesk.contracts.base import ContractError

START_DATE = date(2016, 1, 1)
INDEX_PATH = REPO / "data" / "market" / "reference" / "indices.parquet"
SLEEP_SEC = 1.0  # be polite to the public API


def existing_sessions() -> set[date]:
    if not INDEX_PATH.exists():
        return set()
    rows = load_index_rows(INDEX_PATH)
    return {date.fromisoformat(r["session"]) for r in rows}


def main():
    p = argparse.ArgumentParser(description="Backfill NSE index daily closes from nse-archives")
    p.add_argument("--dry-run", action="store_true", help="Print what would be fetched without downloading")
    args = p.parse_args()

    existing = existing_sessions()
    # Existing store has 2021-06-01 → 2026-08-28. Gap is 2016-01-01 → 2021-05-31.
    min_existing = min(existing) if existing else None

    # Build session list: every weekday from target_start to max(old_data, today)
    today = date.today()
    end = date(2021, 5, 31) if min_existing and min_existing > START_DATE else today
    sessions: list[date] = []
    d = end
    while d >= START_DATE:
        if d.weekday() < 5 and (min_existing is None or d < min_existing):
            sessions.append(d)
        d -= timedelta(days=1)
    sessions.sort()

    if not sessions:
        print(f"[idx-backfill] no new sessions needed (last existing: {last_existing})", flush=True)
        return 0

    print(f"[idx-backfill] {len(sessions)} new sessions from {sessions[0]} to {sessions[-1]}", flush=True)

    if args.dry_run:
        print(f"[idx-backfill] DRY-RUN: would fetch {len(sessions)} sessions", flush=True)
        return 0

    # Merge with existing rows
    all_rows = load_index_rows(INDEX_PATH) if INDEX_PATH.exists() else []
    failed: list[str] = []
    for i, session in enumerate(sessions):
        try:
            raw = fetch_ind_close_all(session)
            rows = parse_ind_close_all_rows(raw, source_file=f"ind_close_all_{session.isoformat()}")
            if rows:
                all_rows.extend(rows)
            else:
                failed.append(session.isoformat())
        except Exception as exc:
            failed.append(f"{session.isoformat()}: {exc}")
        if (i + 1) % 20 == 0:
            print(f"[idx-backfill] {i+1}/{len(sessions)} sessions processed", flush=True)
        time.sleep(SLEEP_SEC)

    # Deduplicate on (session, index_id) — last write wins
    uniq: dict = {}
    for row in all_rows:
        k = (row["session"], row["index_id"])
        uniq[k] = row
    out = [uniq[k] for k in sorted(uniq)]
    persist_index_rows(out, INDEX_PATH)
    print(f"[idx-backfill] wrote {len(out)} rows ({len(sessions)} sessions, {len(failed)} failed)", flush=True)
    if failed:
        print(f"[idx-backfill] failed sessions (first 10): {failed[:10]}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())