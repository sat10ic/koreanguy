"""sys.path shim for derive/style.py. See run_w4.py for why this exists.

    python traderlog/run_style.py            # derive trader_style, idempotent
    python traderlog/run_style.py --dry-run  # SELECT-only report; no writes
    python traderlog/run_style.py --db path/to.db  # target a non-production DB

Runs over the production traderlog.db by default. Computes one trader_style
row per active real trader per computation date, from the reconciler's real
positions (see the module docstring for the exact computation rules -- they
are the QC surface). Upserts on (handle, as_of): a same-day re-run refreshes,
a later-date run appends history. --dry-run issues SELECTs only and commits
nothing, so it is the safe way to preview counts against production.
"""
from __future__ import annotations

import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from traderlog.db import DB_PATH, connect  # noqa: E402
from traderlog.derive.style import (  # noqa: E402
    RATE_MIN_CLOSED,
    _fmt,
    derive,
    run,
)


def _print_stats(stats: dict) -> None:
    t = stats["threshold"]
    print(
        f"active real traders: {stats['handles']}; rows to write: {stats['rows']}; "
        f"positions {stats['positions_total']}, closed {stats['closed_total']}"
    )
    print(
        f"threshold >= {RATE_MIN_CLOSED} crossings -- win_rate: {t['win_rate'] or '-'}, "
        f"avg_r: {t['avg_r'] or '-'}, stop_stated: {t['stop_stated'] or '-'}, "
        f"stop_honored: {t['stop_honored'] or '-'}"
    )
    print("per-handle (n / closed / stated / wins / win% / median_hold / "
          "stop_stated% / stop_honored% / avg_r):")
    for handle in sorted(stats["per_handle"]):
        d = stats["per_handle"][handle]
        v = d["values"]
        print(
            f"  {handle:<18} {d['n_positions']:>4} / {d['closed']:>4} / "
            f"{d['stated_results']:>4} / {d['wins']:>4} / "
            f"{_fmt(v['stated_win_rate']):>7} / {_fmt(v['median_hold_days']):>5} / "
            f"{_fmt(v['stop_stated_pct']):>7} / {_fmt(v['stop_honored_pct']):>7} / "
            f"{_fmt(v['avg_r']):>6}"
        )


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    dry_run = "--dry-run" in argv
    db_path = DB_PATH
    if "--db" in argv:
        db_path = Path(argv[argv.index("--db") + 1])

    conn = connect(db_path)
    try:
        t0 = time.monotonic()
        rows, stats = derive(conn)
        dur = time.monotonic() - t0
        print(f"derivation scan complete in {dur:.2f}s (read-only)")
        _print_stats(stats)
        if dry_run:
            print("dry-run: no writes performed")
            return 0

        t0 = time.monotonic()
        counts = run(conn, date.today().isoformat(), _stats_out={})
        print(
            f"trader_style rows written: {counts['rows']} for {counts['handles']} "
            f"active real traders ({time.monotonic() - t0:.2f}s)"
        )
        if rows:
            print(f"  as_of: {date.today().isoformat()}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())