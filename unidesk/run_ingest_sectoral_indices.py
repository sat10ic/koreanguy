"""ROTATION R-0.2 — harvest NSE sectoral indices (ind_close_all) for the
rotation screen: catches up every session from the day after the store's
last NSE_ARCHIVES session through today, then canonicalises.

    .venv-orderflow/Scripts/python.exe unidesk/run_ingest_sectoral_indices.py
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import date, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from unidesk.momentum.data.indices import (  # noqa: E402
    canonicalise_index_rows, fetch_ind_close_all, load_index_rows,
    parse_ind_close_all_rows, persist_index_rows,
)

INDEX_PATH = REPO / "data" / "market" / "reference" / "indices.parquet"
SLEEP_SEC = 1.0
MAX_BACKFILL = 90  # ~60-session JdK warm-up + margin


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--days", type=int, default=MAX_BACKFILL)
    ap.add_argument("--from", dest="from_date", default=None,
                    help="harvest every weekday from this date (sectoral depth backfill)")
    args = ap.parse_args()

    rows = load_index_rows(INDEX_PATH) if INDEX_PATH.exists() else []
    nse_sessions = {date.fromisoformat(r["session"]) for r in rows
                    if r.get("source_tier") == "NSE_ARCHIVES_IND_CLOSE_ALL"}
    last = max(nse_sessions) if nse_sessions else None
    if args.from_date:
        start = date.fromisoformat(args.from_date)
        sessions: list[date] = []
        d = start
        while d <= date.today():
            if d.weekday() < 5:
                sessions.append(d)
            d += timedelta(days=1)
        sessions = [s for s in sessions if s not in nse_sessions]
    else:
        sessions = []
        d = date.today()
        while d > last and len(sessions) < args.days:
            if d.weekday() < 5:
                sessions.append(d)
            d -= timedelta(days=1)
        sessions.sort()
    print(f"[sectoral] {len(sessions)} sessions to harvest "
          f"(after {last or 'start'})")
    if not sessions or args.dry_run:
        print("[sectoral] nothing to do")
        return 0

    kept: list = []
    failed: list[str] = []
    for i, session in enumerate(sessions):
        try:
            raw = fetch_ind_close_all(session)
            parsed = parse_ind_close_all_rows(
                raw, source_file=f"ind_close_all_{session.isoformat()}",
            )
            if parsed:
                kept.extend(parsed)
            else:
                failed.append(session.isoformat())
        except Exception as exc:  # noqa: BLE001 — a failed session is recorded, never fatal
            failed.append(f"{session.isoformat()}: {exc}")
        if (i + 1) % 10 == 0:
            print(f"[sectoral] {i + 1}/{len(sessions)} sessions", flush=True)
        time.sleep(1.0)

    merged = rows + kept
    out, stats = canonicalise_index_rows(merged)
    persist_index_rows(out, INDEX_PATH)
    sectoral_ids = {r["index_id"] for r in out if r["index_id"].startswith("NIFTY_")
                    and r["index_id"] not in ("NIFTY_50", "NIFTY_500", "NIFTY_MIDCAP_150",
                                              "NIFTY_SMALLCAP_250")}
    print(f"[sectoral] wrote {len(out)} rows; stats={stats}")
    print(f"[sectoral] sectoral indices now in store: {len(sectoral_ids)}")
    if failed:
        print(f"[sectoral] failed sessions (first 10): {failed[:10]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
