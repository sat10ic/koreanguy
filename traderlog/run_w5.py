"""sys.path shim for W5 volume reverse-engineering (Reactor Scale adoption).

    python traderlog/run_w5.py                 # backfill everything, idempotent
    python traderlog/run_w5.py --dry-run       # report scope, write nothing
    python traderlog/run_w5.py --db path/to.db # target a non-production DB

Backfills ``alpha_activity_signals`` from ``daily_prices`` (series='EQ') via
``adopted/activity_pipeline.py`` — the pure Reactor Scale core lives in
``adopted/activity.py`` (provenance + drift documented there). Every eligible
symbol-date is recomputed; the pipeline deletes our own formula_version rows
and upserts the fresh set inside one transaction, so re-running is safe and
converges to identical content.

PRODUCTION NOTE: this writes the production ``traderlog/data/traderlog.db`` by
default — take a backup FIRST (e.g. copy it to
``traderlog/data/traderlog.db.backup-pre-w5-<date>``) before the first
production run, per AGENTS.md.

Scope model (same as run_w4.py's stage ordering, single stage here):
  1. ``adopted/activity_pipeline.py`` -- Reactor Scale signals, one backfill
"""
from __future__ import annotations

import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from traderlog.adopted import activity, activity_pipeline  # noqa: E402
from traderlog.db import DB_PATH, init_db  # noqa: E402


def _dry_run_report(db_path: Path) -> int:
    """Read-only scope report: universe size, date range, history spread,
    ETF-name symbols the ported gate would exclude. Opens the DB read-only
    (``mode=ro`` URI) so a dry-run can never create a file or write anything."""
    try:
        conn = sqlite3.connect(
            f"file:///{db_path.resolve().as_posix()}?mode=ro", uri=True
        )
    except sqlite3.OperationalError as exc:
        print(f"cannot open database read-only: {exc}")
        return 1
    conn.row_factory = sqlite3.Row
    try:
        eq = conn.execute(
            "SELECT COUNT(DISTINCT symbol) n, MIN(trade_date) a, MAX(trade_date) b, "
            "COUNT(*) rows FROM daily_prices WHERE series='EQ'"
        ).fetchone()
        if not eq or not eq["n"]:
            print("no EQ daily_prices rows — nothing to backfill")
            return 0
        hist = conn.execute(
            "SELECT MIN(c) min_sessions, MAX(c) max_sessions, "
            "SUM(CASE WHEN c < 21 THEN 1 ELSE 0 END) symbols_under_21 "
            "FROM (SELECT symbol, COUNT(*) c FROM daily_prices "
            "      WHERE series='EQ' GROUP BY symbol)"
        ).fetchone()
        etf_names = [
            r[0] for r in conn.execute(
                "SELECT DISTINCT symbol FROM daily_prices WHERE series='EQ'"
            ).fetchall()
            if activity.is_probable_etf(r[0])
        ]
        print(f"EQ universe: {eq['n']} distinct symbols, {eq['rows']} session rows")
        print(f"  date range: {eq['a']} .. {eq['b']}")
        print(f"  sessions per symbol: min {hist['min_sessions']} "
              f"max {hist['max_sessions']}")
        print(f"  symbols with <21 sessions (can never write a signal, all warm-up): "
              f"{hist['symbols_under_21']}")
        print(f"  ETF-name symbols the ported gate excludes: {len(etf_names)} "
              f"(e.g. {etf_names[:5]}{' ...' if len(etf_names) > 5 else ''})")
        print(f"  formula_version: {activity.FORMULA_VERSION} — Q={activity.Q_COEFFICIENT} "
              f"D={activity.D_COEFFICIENT} I={activity.INTERACTION_COEFFICIENT} "
              f"E={activity.INTERACTION_EXPONENT} intercept={activity.INTERCEPT}")
        return 0
    finally:
        conn.close()


def _distribution_report(conn) -> None:
    dist = activity_pipeline.distribution(conn)
    print("score distribution (adopted formula_version only):")
    print(f"  rows={dist['rows']} symbols={dist['symbols']} dates={dist['dates']}")
    print(f"  date range: {dist['date_first']} .. {dist['date_last']}")
    print(f"  activity_score: min {dist['score_min']} | median {dist['score_median']} "
          f"| mean {dist['score_mean']} | max {dist['score_max']}")
    print(f"  at/above abnormal ({activity.ABNORMAL_LEVEL}): {dist['abnormal']}  "
          f"at/above extreme ({activity.EXTREME_LEVEL}): {dist['extreme']}")
    if dist["rows"] and dist["score_min"] == dist["score_max"]:
        print("  ⚠ DEGENERATE: single-value score distribution — investigate "
              "before trusting (XP/C8 lesson: validate before declaring success)")


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    dry_run = "--dry-run" in argv
    db_path = DB_PATH
    if "--db" in argv:
        db_path = Path(argv[argv.index("--db") + 1])

    if dry_run:
        return _dry_run_report(db_path)

    conn = init_db(db_path)
    try:
        t0 = time.monotonic()
        result = activity_pipeline.backfill(conn)
        print(f"[1/1] alpha_activity_signals: {result['rows']} rows over "
              f"{result['dates']} dates, {result['symbols_with_signals']} symbols "
              f"({time.monotonic() - t0:.1f}s)")
        print(f"      warmup_skipped={result['warmup_skipped']} "
              f"excluded_universe={result['excluded_universe']} "
              f"guards_skipped={result['guards_skipped']} "
              f"invalid_sessions={result['invalid_sessions']}")
        if result["status"] == "skip":
            print(f"      {result['detail']}")
            return 0
        _distribution_report(conn)
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())