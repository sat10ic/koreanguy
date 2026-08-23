"""sys.path shim for W4 breadth + XP/MBI. See run_checks.py for why this exists.

    python traderlog/run_w4.py                 # backfill everything, idempotent
    python traderlog/run_w4.py --dry-run        # just report discovered dates
    python traderlog/run_w4.py --db path/to.db  # target a non-production DB

Runs, in order, over the production traderlog.db by default:
  1. adopted/bhavcopy.py    -- every discoverable data/bhavcopy CSV -> daily_prices
  2. adopted/breadth_counts.py    -- own-universe ~38 counts, one date at a time
  3. adopted/universe_breadth.py  -- NIFTYMIDSML400 breadth -> breadth_daily
  4. adopted/regime_daily.py      -- XP + MBI -> regime_daily, STRICT ascending order

Every stage is upsert-based and re-runnable; interrupting and re-running this
script is safe and will not duplicate rows or double-count anything.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from traderlog.adopted import bhavcopy, breadth_counts, regime_daily, universe_breadth  # noqa: E402
from traderlog.db import DB_PATH, init_db  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    dry_run = "--dry-run" in argv
    db_path = DB_PATH
    if "--db" in argv:
        db_path = Path(argv[argv.index("--db") + 1])

    dates = bhavcopy.discover_dates()
    print(f"discovered {len(dates)} bhavcopy dates: {dates[0] if dates else '-'} .. {dates[-1] if dates else '-'}")
    if dry_run:
        return 0

    conn = init_db(db_path)
    try:
        t0 = time.monotonic()
        result = bhavcopy.backfill(conn, dates)
        print(f"[1/4] daily_prices: {result['rows']} rows over {result['dates']} dates, "
              f"{len(result['failed'])} failed ({time.monotonic() - t0:.1f}s)")
        if result["failed"]:
            print(f"      failed dates: {result['failed'][:10]}")
            print("      stopping: bhavcopy failures block dependent breadth/regime stages")
            return 1

        eq_dates = [
            r[0] for r in conn.execute(
                "SELECT DISTINCT trade_date FROM daily_prices WHERE series='EQ' ORDER BY trade_date ASC"
            ).fetchall()
        ]
        print(f"      {len(eq_dates)} distinct EQ trade dates in daily_prices")

        t0 = time.monotonic()
        bc_ok = bc_skip = bc_fail = 0
        for i, d in enumerate(eq_dates):
            r = breadth_counts.run(conn, d)
            if r["status"] == "ok":
                bc_ok += 1
            elif r["status"] == "skip":
                bc_skip += 1
            else:
                bc_fail += 1
            if (i + 1) % 50 == 0:
                print(f"      breadth_counts progress: {i + 1}/{len(eq_dates)} "
                      f"({time.monotonic() - t0:.1f}s elapsed)")
        print(f"[2/4] breadth_counts: {bc_ok} ok, {bc_skip} skip, {bc_fail} fail "
              f"({time.monotonic() - t0:.1f}s)")
        if bc_fail:
            print("      stopping: breadth_counts failures block dependent breadth/regime stages")
            return 1

        t0 = time.monotonic()
        ub_ok = ub_skip = ub_fail = 0
        for d in eq_dates:
            r = universe_breadth.run(conn, d)
            if r["status"] == "ok":
                ub_ok += 1
            elif r["status"] == "skip":
                ub_skip += 1
            else:
                ub_fail += 1
        print(f"[3/4] breadth_daily (NIFTYMIDSML400): {ub_ok} ok, {ub_skip} skip, {ub_fail} fail "
              f"({time.monotonic() - t0:.1f}s)")
        if ub_fail:
            print("      stopping: NIFTYMIDSML400 breadth failures block regime derivation")
            return 1

        t0 = time.monotonic()
        rd = regime_daily.backfill(conn)
        print(f"[4/4] regime_daily: {rd['ok']} ok, {rd['skipped']} skip, "
              f"{len(rd['failed'])} failed, {len(rd['reseed_points'])} reseed points "
              f"({time.monotonic() - t0:.1f}s)")
        print(f"      reseed points (chain breaks): {rd['reseed_points']}")
        if rd["failed"]:
            print(f"      failed dates: {rd['failed'][:10]}")

        return 0 if not (result["failed"] or bc_fail or ub_fail or rd["failed"]) else 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
