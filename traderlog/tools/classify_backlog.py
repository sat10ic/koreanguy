"""Batch runner for the W2 classify backlog.

Classifies every post with no ``post_class`` row through the frozen cheap
tier (``llm.classify.classify_post``). Resumable by construction: the work
list is a plain ``SELECT ... WHERE NOT EXISTS`` query, so re-running this
script after any interruption -- Ctrl+C, a crashed shell, a rate-limit wall
-- simply continues where it left off. No separate state file.

This script NEVER re-classifies, overwrites, or deletes an existing
post_class row -- including the rows with run_id IS NULL left by the
unaudited path (a separate, already-known finding). It only inserts new
rows for posts that currently have none.

    python traderlog/tools/classify_backlog.py --dry-run       # count only
    python traderlog/tools/classify_backlog.py --limit 20       # smoke run
    python traderlog/tools/classify_backlog.py                  # full backlog
    python traderlog/tools/classify_backlog.py --db path/to.db  # non-prod DB

Sys.path shim matches run_w4.py / run_checks.py: this machine's python does
not honor PYTHONPATH, so `traderlog.*` only resolves with the repo's parent
directory pushed onto sys.path first.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from traderlog import config  # noqa: E402
from traderlog.db import init_db, now_iso  # noqa: E402
from traderlog.llm import classify as classify_mod  # noqa: E402
from traderlog.llm import provider  # noqa: E402

# Only posts with NO post_class row at all are in scope -- never touches an
# existing row (including the known run_id IS NULL backlog from the
# unaudited path). is_mock=1 and NULL/blank text are skipped per spec.
WORK_SQL = """
    SELECT p.post_id FROM posts p
     WHERE NOT EXISTS (SELECT 1 FROM post_class c WHERE c.post_id = p.post_id)
       AND p.is_mock = 0
       AND p.text IS NOT NULL AND trim(p.text) != ''
     ORDER BY p.ts_ist DESC, p.post_id DESC
"""
# Newest-first as of 2026-08-25. It was ORDER BY p.post_id, i.e. effectively
# oldest-first (X snowflake ids are chronological), so the backlog was worked
# from 2024 forward and the recent, position-dense posts were last in a
# ~5-hour queue. Radar reads classified posts, so oldest-first meant the screen
# stayed empty for the window the owner actually looks at. Resumability is
# unaffected: the NOT EXISTS predicate, not the ordering, is what makes a
# re-run continue rather than repeat.

# Free OpenRouter pools 429 often (see llm/provider.py's REASONING_HINTS
# comment and _recon_runner.py, which proved this pacing/backoff shape works
# against the same cheap-tier chain). Bounded at both ends so one stuck post
# can never consume the whole session: worst case backoff is
# 5+10+20+40+80+120 =~= 4.6 minutes before a post is logged as failed.
BACKOFF_BASE_S = 5.0
BACKOFF_CAP_S = 120.0
MAX_ATTEMPTS = 6
PACING_S = 2.5
PROGRESS_EVERY = 25


def _select_work(conn, limit: int | None) -> list[str]:
    ids = [r["post_id"] for r in conn.execute(WORK_SQL).fetchall()]
    if limit:
        ids = ids[:limit]
    return ids


def _assert_free_chain() -> None:
    """Hard-stop guard for the non-negotiable owner instruction: free models
    only. classify_post always calls tier='cheap' and this script never
    changes that -- this just re-verifies config.yaml itself is still every
    entry ending in ':free' before spending a single call."""
    models = provider.chain_for("cheap")
    non_free = [m for m in models if not m.endswith(":free")]
    if non_free:
        raise SystemExit(
            f"ABORT: llm.tiers.cheap contains non-free model(s) {non_free!r}. "
            f"Standing instruction is free models only -- refusing to run. "
            f"Fix config.yaml (or this guard) before retrying."
        )
    if not config.env("OPENROUTER_API_KEY"):
        raise SystemExit(
            "ABORT: OPENROUTER_API_KEY is not set (checked environment and "
            "repo-root .env). Every post would fail identically -- fix this "
            "before running, rather than burning the whole backoff budget "
            "per post for nothing."
        )


def _tracking_chat_fn(stats: dict):
    """Wrap provider.chat to capture cost/model without touching classify.py.

    classify_post accepts an injectable chat_fn (see tests/test_classify.py);
    this is the same seam, used here for accounting rather than fakes. It
    changes nothing about which models are called or in what order -- it
    only observes the ProviderResult that provider.chat already returns.
    """

    def _fn(**kwargs):
        result = provider.chat(**kwargs)
        cost = float(result.cost_usd or 0.0)
        stats["cost_usd"] += cost
        if cost > 0:
            stats["nonzero_cost_calls"].append((kwargs.get("ref_id"), result.model, cost))
        return result

    return _fn


def _classify_one(conn, post_id: str, stats: dict) -> tuple[bool, str | None, str | None]:
    """Classify one post with bounded exponential backoff on chain exhaustion.

    Returns (ok, reason, detail). reason is a short bucket key for the
    failure tally (exception type name); detail is the full message, kept
    for the per-post failure report. Never raises -- every exception path
    is a documented, caught failure so one bad post cannot kill the run.
    """
    last_exc: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            classify_mod.classify_post(conn, post_id, chat_fn=_tracking_chat_fn(stats))
            return True, None, None
        except provider.ProviderExhausted as exc:
            last_exc = exc
            if attempt < MAX_ATTEMPTS:
                wait = min(BACKOFF_BASE_S * (2 ** (attempt - 1)), BACKOFF_CAP_S)
                print(
                    f"    [{post_id}] chain exhausted (attempt {attempt}/{MAX_ATTEMPTS}); "
                    f"retry in {wait:.0f}s",
                    flush=True,
                )
                time.sleep(wait)
                continue
            return False, "ProviderExhausted", str(exc)
        except classify_mod.ClassificationValidationError as exc:
            return False, "ClassificationValidationError", str(exc)
        except Exception as exc:  # noqa: BLE001 - last-resort safety net
            return False, type(exc).__name__, str(exc)
    return False, "ProviderExhausted", str(last_exc)


def _kind_distribution(conn) -> list[tuple[str, int]]:
    rows = conn.execute(
        "SELECT kind, COUNT(*) c FROM post_class GROUP BY kind ORDER BY c DESC"
    ).fetchall()
    return [(r["kind"], r["c"]) for r in rows]


def _print_summary(conn, *, run_start: str, work_len: int, done: int, failed: int,
                    failures_by_reason: dict[str, int], failed_posts: list[tuple[str, str, str]],
                    tracked_cost: float, elapsed_s: float) -> None:
    verified_cost = conn.execute(
        "SELECT COALESCE(SUM(cost_usd), 0) FROM llm_runs WHERE task='classify' AND ts >= ?",
        (run_start,),
    ).fetchone()[0]
    print()
    print("=" * 78)
    print(
        f"CLASSIFY BACKLOG SUMMARY: attempted={done + failed}/{work_len} "
        f"succeeded={done} failed={failed} elapsed={elapsed_s / 60:.1f}m"
    )
    print(f"cost_usd tracked in-process: {tracked_cost:.6f}")
    print(f"cost_usd verified via llm_runs (task='classify', ts >= {run_start}): {verified_cost:.6f}")
    if failures_by_reason:
        print("failed-with-reason tally:")
        for reason, n in sorted(failures_by_reason.items(), key=lambda kv: -kv[1]):
            print(f"  {reason}: {n}")
        print("failed post_ids:")
        for post_id, reason, detail in failed_posts:
            short = (detail or "")[:200]
            print(f"  {post_id}  {reason}  {short}")
    print("post_class kind distribution (all rows, after this run):")
    for kind, n in _kind_distribution(conn):
        print(f"  {kind}: {n}")
    print("=" * 78, flush=True)


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limit", type=int, default=None, help="classify at most N posts (smoke run)")
    parser.add_argument("--dry-run", action="store_true", help="select the work and print the count; call no model")
    parser.add_argument("--db", type=Path, default=None, help="target a non-production DB (default: production traderlog.db)")
    args = parser.parse_args(argv)

    _assert_free_chain()

    conn = init_db(args.db)
    try:
        work = _select_work(conn, args.limit)
        print(
            f"classify backlog: {len(work)} posts selected"
            + (f" (--limit {args.limit})" if args.limit else "")
        )
        if args.dry_run:
            print("--dry-run: no model calls made")
            return 0
        if not work:
            print("nothing to do")
            return 0

        run_start = now_iso()
        stats = {"cost_usd": 0.0, "nonzero_cost_calls": []}
        done = failed = 0
        failures_by_reason: dict[str, int] = {}
        failed_posts: list[tuple[str, str, str]] = []
        t0 = time.monotonic()

        try:
            for i, post_id in enumerate(work, start=1):
                ok, reason, detail = _classify_one(conn, post_id, stats)

                if stats["nonzero_cost_calls"]:
                    pid, model, cost = stats["nonzero_cost_calls"][-1]
                    print(
                        f"ABORT: non-free model produced nonzero cost (${cost:.6f}) on "
                        f"post {pid} via {model}. Standing instruction is free models "
                        f"only -- stopping immediately rather than spending further.",
                        flush=True,
                    )
                    _print_summary(
                        conn, run_start=run_start, work_len=len(work), done=done, failed=failed,
                        failures_by_reason=failures_by_reason, failed_posts=failed_posts,
                        tracked_cost=stats["cost_usd"], elapsed_s=time.monotonic() - t0,
                    )
                    return 3

                if ok:
                    done += 1
                else:
                    failed += 1
                    failures_by_reason[reason] = failures_by_reason.get(reason, 0) + 1
                    failed_posts.append((post_id, reason, detail))
                    print(f"    FAILED [{post_id}]: {reason}: {(detail or '')[:300]}", flush=True)

                if i % PROGRESS_EVERY == 0 or i == len(work):
                    elapsed = time.monotonic() - t0
                    rate_per_min = (i / elapsed * 60) if elapsed > 0 else 0.0
                    remaining = len(work) - i
                    eta_min = (remaining / rate_per_min) if rate_per_min > 0 else float("inf")
                    print(
                        f"[{i}/{len(work)}] done={done} failed={failed} "
                        f"elapsed={elapsed / 60:.1f}m rate={rate_per_min:.1f}/min "
                        f"eta={eta_min:.1f}m",
                        flush=True,
                    )

                time.sleep(PACING_S)
        except KeyboardInterrupt:
            print("\nINTERRUPTED -- re-run this script to resume; already-written "
                  "post_class rows are untouched.", flush=True)
            _print_summary(
                conn, run_start=run_start, work_len=len(work), done=done, failed=failed,
                failures_by_reason=failures_by_reason, failed_posts=failed_posts,
                tracked_cost=stats["cost_usd"], elapsed_s=time.monotonic() - t0,
            )
            return 130

        _print_summary(
            conn, run_start=run_start, work_len=len(work), done=done, failed=failed,
            failures_by_reason=failures_by_reason, failed_posts=failed_posts,
            tracked_cost=stats["cost_usd"], elapsed_s=time.monotonic() - t0,
        )
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
