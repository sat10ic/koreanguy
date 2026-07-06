"""`manas` CLI — the single orchestration entrypoint (anti-mashup rule #2).

    python -m manas_os.cli init-db
    python -m manas_os.cli run-eod [--date YYYY-MM-DD]

`run-eod` is the ONE command that drives the whole daily pipeline. Stages register here as
they are built (P0 ingest → P1 regime → P2 scan/readiness → ...); each stage writes a
pipeline_runs row so Pipeline Health and staleness detection stay honest.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date as _date

from manas_os import db


def _cmd_init_db(args: argparse.Namespace) -> int:
    conn = db.init_db()
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )]
    conn.close()
    print(f"init-db ok -> {db.DB_PATH}")
    print(f"tables ({len(tables)}): {', '.join(tables)}")
    return 0


def _load_stages() -> list[tuple[str, object]]:
    """Ordered daily pipeline, imported lazily so `init-db` needs no heavy deps.

    Stages register here as phases land. P0: ingest sources -> compute indicators.
    (P1 adds the regime/XP snapshot stage after ingest.)
    """
    from manas_os.alerts import eod, telegram_engine
    from manas_os.sources import bhavcopy, chartsmaze, chartsmaze_scanners, universe_breadth
    from manas_os.engine import indicators
    from manas_os.regime import mars_ingest, snapshot
    from manas_os.scanner import expectancy
    from manas_os.scanner import candidates, outcomes
    return [
        ("ingest_bhavcopy", bhavcopy.run),                  # prices + delivery% (local files)
        ("ingest_universe_breadth", universe_breadth.run),  # NIFTYMIDSML400 breadth from bhavcopy (feeds XP/MBI)
        ("ingest_chartsmaze", chartsmaze.run),              # sector/breadth freshness (local files)
        ("ingest_chartsmaze_scanners", chartsmaze_scanners.run),  # screener hits + quality signals (local files)
        ("ingest_disclosures", __import__("manas_os.sources.disclosures", fromlist=["run"]).run),  # disclosure feeds (local files)
        ("indicators", indicators.run),                     # per-symbol features (depends on prices)
        ("ingest_mars", mars_ingest.run),                   # sector RS vs benchmark (Fyers; graceful skip)
        ("regime_snapshot", snapshot.run),                  # XP + MBI + posture (depends on breadth)
        ("scan_candidates", candidates.run),                # P2 setup candidates + readiness
        ("expectancy", expectancy.run),                     # learnings loop (T2.3b)
        ("candidate_outcomes", outcomes.run),               # T+5/T+10/T+20 forward-return plumbing
        ("eod_alerts", eod.run),                            # P3 nightly manual-trading alerts
        ("telegram_digest", telegram_engine.run),            # T4.1 deterministic digest + armed list
    ]
    # breadth_sheet.py retained as a fallback provider (different universe), not
    # in the daily pipeline — the regime now runs on NIFTYMIDSML400 computed
    # breadth for scale-correctness vs the reference.


def _cmd_backfill_snapshots(args: argparse.Namespace) -> int:
    """Replay breadth_daily history through the live regime-snapshot path.

    One-time-ish operation (I1, plan §P1.5) — not a daily run-eod stage,
    since after the first run there's nothing pending most days. Safe to
    re-run: skips dates that already have a snapshot unless --force.
    """
    from manas_os.regime import backfill as backfill_mod

    conn = db.init_db()
    result = backfill_mod.backfill_snapshots(
        conn, start_date=args.start, end_date=args.end, force=args.force
    )
    conn.close()
    print(f"backfill-snapshots: {result['status']}, {result['dates_processed']} date(s) processed")
    if result["first_failure"]:
        print(f"  stopped at {result['first_failure']}")
    return 0 if result["status"] == "ok" else 1


def _cmd_replay(args: argparse.Namespace) -> int:
    from manas_os.backtest.replay import format_ab_table, format_replay_table, replay

    conn = db.init_db()
    try:
        if args.train_start or args.train_end or args.test_start or args.test_end:
            required = [args.train_start, args.train_end, args.test_start, args.test_end]
            if any(v is None for v in required):
                raise SystemExit("--train-start/--train-end/--test-start/--test-end must be supplied together")
            train = replay(conn, args.train_start, args.train_end, args.config)
            test = replay(conn, args.test_start, args.test_end, args.config)
            print(format_replay_table(train, title=f"Train window ({args.config})"))
            print()
            print(format_replay_table(test, title=f"Test window ({args.config})"))
            return 0

        if args.a or args.b:
            if not args.a or not args.b:
                raise SystemExit("--a and --b must be supplied together")
            left = replay(conn, args.start, args.end, args.a)
            right = replay(conn, args.start, args.end, args.b)
            print(format_ab_table(left, right))
            return 0

        result = replay(conn, args.start, args.end, args.config)
        print(format_replay_table(result))
        return 0
    finally:
        conn.close()


def _cmd_run_eod(args: argparse.Namespace) -> int:
    run_date = args.date or _date.today().isoformat()
    conn = db.init_db()
    stages = _load_stages()
    print(f"run-eod {run_date}: {len(stages)} stage(s) registered")
    for stage_name, fn in stages:
        try:
            fn(conn, run_date)  # type: ignore[operator]
            print(f"  [ok]   {stage_name}")
        except Exception as exc:  # per-stage isolation; one bad stage never kills the run
            print(f"  [FAIL] {stage_name}: {exc}")
    conn.close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="manas", description="Manas AI Trading OS")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("init-db", help="create manas.db schema").set_defaults(func=_cmd_init_db)
    eod = sub.add_parser("run-eod", help="run the end-of-day pipeline")
    eod.add_argument("--date", help="trade date YYYY-MM-DD (default: today)")
    eod.set_defaults(func=_cmd_run_eod)
    bf = sub.add_parser("backfill-snapshots", help="replay breadth_daily history into regime_snapshots")
    bf.add_argument("--start", help="earliest trade_date YYYY-MM-DD (default: all history)")
    bf.add_argument("--end", help="latest trade_date YYYY-MM-DD (default: all history)")
    bf.add_argument("--force", action="store_true", help="recompute dates that already have a snapshot")
    bf.set_defaults(func=_cmd_backfill_snapshots)
    rp = sub.add_parser("replay", help="replay setup candidates over a historical window")
    rp.add_argument("--start", default="2025-06-01", help="start date YYYY-MM-DD")
    rp.add_argument("--end", default=_date.today().isoformat(), help="end date YYYY-MM-DD")
    rp.add_argument("--config", default="legacy", choices=["legacy", "cascade"], help="single config to replay")
    rp.add_argument("--a", choices=["legacy", "cascade"], help="left config for A/B output")
    rp.add_argument("--b", choices=["legacy", "cascade"], help="right config for A/B output")
    rp.add_argument("--train-start", help="walk-forward train start YYYY-MM-DD")
    rp.add_argument("--train-end", help="walk-forward train end YYYY-MM-DD")
    rp.add_argument("--test-start", help="walk-forward test start YYYY-MM-DD")
    rp.add_argument("--test-end", help="walk-forward test end YYYY-MM-DD")
    rp.set_defaults(func=_cmd_replay)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
