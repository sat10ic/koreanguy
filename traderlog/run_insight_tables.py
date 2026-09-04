"""sys.path shim for derive/insight_tables.py. See run_w4.py for why this exists.

    python traderlog/run_insight_tables.py            # materialise, idempotent
    python traderlog/run_insight_tables.py --dry-run  # SELECT-only report; no writes
    python traderlog/run_insight_tables.py --db path/to.db  # target a non-production DB

Runs over the production traderlog.db by default. Materialises the three
classifier-shaped insight tables from the classified corpus:
  1. themes        -- distinct themes/sectors named literally in kind='theme'
                      posts (plus breadth posts naming the same phrases)
  2. breadth_notes -- one dated note per kind='breadth' post, stance only when
                      explicitly stated
  3. edu_items     -- one educational principle per kind='education' post

Every stage is upsert-based and re-runnable: interrupting and re-running is
safe and will not duplicate rows (see the module docstring for the exact
idempotency contract per table). --dry-run issues SELECTs only and commits
nothing, so it is the safe way to preview counts against production.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from traderlog.db import DB_PATH, connect  # noqa: E402
from traderlog.derive.insight_tables import derive, run  # noqa: E402


def _print_stats(stats: dict) -> None:
    t = stats["themes"]
    b = stats["breadth_notes"]
    e = stats["edu_items"]
    print(
        f"themes: {t['written']} themes from {t['considered']} posts "
        f"({t['theme_posts']} theme + {t['breadth_contrib_posts']} breadth contrib), "
        f"{t['mentions']} mentions, skipped: {t['skipped']}"
    )
    print(
        f"breadth_notes: {b['written']} rows from {b['considered']} posts, "
        f"stances {b['stances']}, ambiguous_stance {b['ambiguous_stance']}, "
        f"skipped: {b['skipped']}"
    )
    print(
        f"edu_items: {e['written']} rows from {e['considered']} posts, "
        f"tags {e['tags']}, skipped: {e['skipped']}"
    )
    print("themes detail (name: posts/traders, first..last):")
    for name, d in sorted(t["per_theme"].items(), key=lambda kv: -kv[1]["traders"]):
        print(
            f"  {name}: {d['posts']} posts / {d['traders']} traders, "
            f"{d['first_seen']}..{d['last_seen']}, unresolved {d['unresolved_total']}"
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
        n = run(conn, __import__("datetime").date.today().isoformat(),
                _stats_out={})
        print(f"rows written across the three tables: {n} "
              f"({time.monotonic() - t0:.2f}s)")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())