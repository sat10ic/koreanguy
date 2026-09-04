"""run_recon.py -- one entrypoint that chains every recon stage.

    python traderlog/run_recon.py [--skip-classify] [--skip-reconcile]
                                  [--skip-link] [--skip-insight]
                                  [--limit-per-stage N] [--pacing S]
                                  [--max-wait-minutes M] [--db PATH] [--yes]
                                  [--dry-run]

Chains the four recon stages in order. Each stage is skippable by flag and
resumable: every stage is idempotent, so interrupting and re-running this
script never duplicates work (the same discipline as run_w4.py / the adopted
ingestors).

  1. classify  -- posts with NO post_class row at all (NOT EXISTS), oldest
                 first, through llm/classify.classify_post (cheap tier). Posts
                 that already have a post_class row are NEVER re-processed,
                 even when run_id IS NULL: those rows carry audited
                 manual/provider labels that must not be overwritten by
                 provider output (AGENTS.md owner-directed manual-backfill
                 rule). Provenance backfill is deliberately out of scope.
  2. reconcile -- candidate roots: standalone trade_event posts with >=1
                 symbol in post_class.symbols and no existing positions row
                 for that root, through llm/reconcile.reconcile_thread (smart
                 tier). The reconciler's own thread_hash cache makes an
                 unchanged thread free on re-runs.
  3. link      -- llm/link.run_link_pass; structurally idempotent. Reports
                 eligible / queued / applied / failures plus posts excluded
                 by its fine filters (silent skips).
  4. insight   -- derive/insight_tables.run(conn, today); reports rows written.
                 (--limit-per-stage does not apply: this stage rematerialises
                 the whole corpus by design.)

Rate-wall resilience: free-tier OpenRouter 429 storms surface as
ProviderExhausted. Every item is paced (--pacing S, default 2.5s), and N
consecutive ProviderExhausted failures (default 4) enter a POOL-COOLDOWN:
sleep 90s, doubling per repeat, capped at 15 minutes, then the SAME item is
resumed -- never silently skipped, never crashed. --max-wait-minutes M caps
total waiting (0 = unlimited); when the budget is exceeded the run stops
cleanly and prints the exact resume state (every stage is resumable).

Item-level errors are isolated: one bad post/thread is logged and the pass
continues; the final summary reports ok / failed-by-reason / skipped per
stage, plus the vision-backlog count (media on trade_event/education posts
without vision_json). Vision backfill is a manual Gemini pass -- this runner
NEVER calls vision.

Production safety: the default database is production traderlog.db. Running
against it REQUIRES --yes; without it the runner refuses (exit 2) unless
--db points elsewhere. Take a backup before a first-ever production run.
--dry-run prints the planned scope with SELECTs only -- no writes, no LLM
calls.

Exit codes: 0 ok, 1 item failures recorded, 2 usage or production-gate
refusal, 3 stopped by --max-wait-minutes.
"""
from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from traderlog.db import DB_PATH, init_db, now_iso  # noqa: E402
from traderlog.derive.insight_tables import run as run_insight  # noqa: E402
from traderlog.llm import provider  # noqa: E402
from traderlog.llm.classify import classify_post  # noqa: E402
from traderlog.llm.link import run_link_pass  # noqa: E402
from traderlog.llm.reconcile import reconcile_thread  # noqa: E402

STAGE_CLASSIFY = "recon.classify"
STAGE_RECONCILE = "recon.reconcile"
STAGE_LINK = "recon.link"
STAGE_INSIGHT = "recon.insight"

# Pool-cooldown defaults are fixed by the recon spec (not CLI-tunable).
EXHAUSTION_THRESHOLD = 4    # N consecutive ProviderExhausted -> pool cooldown
COOLDOWN_BASE_S = 90.0      # first cooldown sleep
COOLDOWN_CAP_S = 900.0      # 15-minute ceiling; the sleep doubles per repeat
PACE_S = 2.5                # per-item pacing sleep between calls

_LINK_CHUNK = 25            # deadline-driven link passes run in idempotent chunks


class _BudgetExceeded(RuntimeError):
    """Raised by the rate guard when the --max-wait-minutes budget is gone."""


def _budget_exceeded(deadline: float | None) -> bool:
    return deadline is not None and time.monotonic() >= deadline


class _RateGuard:
    """Wraps one chat_fn with per-item pacing and pool-cooldown resilience.

    Pacing: sleep ``pacing`` seconds before every call (per-item cadence, so a
    batch survives free-tier limits). Pool-cooldown: N CONSECUTIVE
    ProviderExhausted failures (default 4) trigger a sleep of
    ``cooldown_base_s`` that doubles per repeat, capped at ``cooldown_cap_s``;
    after the sleep the SAME item is resumed -- never silently skipped, never
    crashed. A ``deadline`` (from --max-wait-minutes) stops the loop with
    _BudgetExceeded, asleep or awake, within ~1s of the budget.
    """

    def __init__(
        self,
        chat_fn: Callable[..., Any],
        *,
        pacing: float,
        threshold: int,
        cooldown_base_s: float,
        cooldown_cap_s: float,
        deadline: float | None,
        sleep: Callable[[float], None],
    ) -> None:
        self.chat_fn = chat_fn
        self.pacing = pacing
        self.threshold = threshold
        self.cooldown_base_s = cooldown_base_s
        self.cooldown_cap_s = cooldown_cap_s
        self.deadline = deadline
        self.sleep = sleep
        self.streak = 0            # consecutive ProviderExhausted since last healthy call
        self.cooldowns = 0         # how many pool cooldowns have fired
        self.exhaustion_count = 0  # total provider-exhausted calls, for reporting
        self.total_cooldown_s = 0.0
        self.budget_tripped = False

    def _bounded_sleep(self, wait_s: float) -> None:
        """Sleep up to ``wait_s`` in 1s slices so a budget stop lands promptly."""
        remaining = wait_s
        while remaining > 0.0:
            if _budget_exceeded(self.deadline):
                return
            step = min(remaining, 1.0)
            self.sleep(step)
            remaining -= step

    def __call__(self, **kwargs: Any):
        while True:
            if _budget_exceeded(self.deadline):
                self.budget_tripped = True
                raise _BudgetExceeded(
                    f"max-wait budget exhausted after {self.total_cooldown_s:.0f}s "
                    f"of pool cooldown and {self.exhaustion_count} "
                    "provider-exhausted call(s)"
                )
            if self.pacing > 0.0:
                self.sleep(self.pacing)
            try:
                result = self.chat_fn(**kwargs)
            except provider.ProviderExhausted as exc:
                self.exhaustion_count += 1
                self.streak += 1
                if self.streak >= self.threshold:
                    self.cooldowns += 1
                    wait = min(
                        self.cooldown_base_s * (2 ** (self.cooldowns - 1)),
                        self.cooldown_cap_s,
                    )
                    self.total_cooldown_s += wait
                    self.streak = 0
                    print(
                        f"    rate-wall: {self.threshold} consecutive ProviderExhausted; "
                        f"pool cooldown {wait:.0f}s (repeat #{self.cooldowns}); "
                        "resuming the same item",
                        flush=True,
                    )
                    self._bounded_sleep(wait)
                continue  # resume the SAME item -- never skip it
            except Exception:
                # Non-exhaustion errors do not count toward the exhaustion
                # streak; interrupt the run of "consecutive" failures.
                self.streak = 0
                self.cooldowns = 0
                raise
            self.streak = 0
            self.cooldowns = 0
            return result


# ---------------------------------------------------------------------------
# scope SQL -- each stage re-selects what it still owns on every run, which is
# what makes every stage resumable and idempotent.
# ---------------------------------------------------------------------------

_CLASSIFY_SCOPE_SQL = """
    SELECT p.post_id FROM posts p
     WHERE NOT EXISTS (SELECT 1 FROM post_class c WHERE c.post_id = p.post_id)
     ORDER BY (p.ts_ist IS NULL), p.ts_ist ASC, p.post_id ASC
"""

_RECONCILE_SCOPE_SQL = """
    SELECT p.post_id FROM posts p
     JOIN post_class c ON c.post_id = p.post_id
    WHERE p.in_reply_to IS NULL
      AND c.kind = 'trade_event'
      AND c.symbols IS NOT NULL AND c.symbols NOT IN ('', '[]')
      AND NOT EXISTS (SELECT 1 FROM positions pos WHERE pos.root_post_id = p.post_id)
    ORDER BY (p.ts_ist IS NULL), p.ts_ist ASC, p.post_id ASC
"""

_LINK_COARSE_SQL = """
    SELECT p.post_id FROM posts p
     JOIN post_class c ON c.post_id = p.post_id
    WHERE c.kind = 'trade_event' AND p.in_reply_to IS NULL
      AND NOT EXISTS (SELECT 1 FROM position_events e WHERE e.post_id = p.post_id)
      AND NOT EXISTS (SELECT 1 FROM review_queue r
                       WHERE r.kind = 'link_event' AND r.post_id = p.post_id)
    ORDER BY p.ts_ist, p.post_id
"""

_VISION_BACKLOG_SQL = """
    SELECT COUNT(*) FROM post_media m
     JOIN posts p ON p.post_id = m.post_id
    WHERE m.is_mock = 0 AND (m.vision_json IS NULL OR m.vision_json = '')
      AND EXISTS (SELECT 1 FROM post_class c
                   WHERE c.post_id = p.post_id
                     AND c.kind IN ('trade_event','education'))
"""


def _scoped(sql: str, limit: int) -> tuple[str, tuple]:
    if limit:
        return sql.rstrip() + " LIMIT ?", (limit,)
    return sql, ()


def _classify_scope(conn, limit: int) -> list:
    sql, params = _scoped(_CLASSIFY_SCOPE_SQL, limit)
    return conn.execute(sql, params).fetchall()


def _reconcile_scope(conn, limit: int) -> list:
    sql, params = _scoped(_RECONCILE_SCOPE_SQL, limit)
    return conn.execute(sql, params).fetchall()


def _link_coarse_count(conn) -> int:
    row = conn.execute(
        f"SELECT COUNT(*) FROM ({_LINK_COARSE_SQL.strip()})"  # noqa: S608 - fixed SQL
    ).fetchone()
    return int(row[0]) if row else 0


def _vision_backlog_count(conn) -> int:
    row = conn.execute(_VISION_BACKLOG_SQL).fetchone()
    return int(row[0]) if row else 0


# ---------------------------------------------------------------------------
# pipeline_runs logging -- same column set the adopted ingestors use
# (stage, run_date, status, rows, duration_ms, detail, ts).
# ---------------------------------------------------------------------------


def _log_run(conn, stage: str, run_date: str, status: str, rows: int,
             dur_s: float, detail: str) -> None:
    conn.execute(
        "INSERT INTO pipeline_runs (stage, run_date, status, rows, duration_ms, detail, ts) "
        "VALUES (?,?,?,?,?,?,?)",
        (stage, run_date, status, rows, int(dur_s * 1000), detail, now_iso()),
    )
    conn.commit()


@dataclass
class _StageReport:
    stage: str = ""                          # pipeline_runs stage name
    status: str = "ok"                       # pipeline_runs vocabulary: ok|skip|fail
    rows: int = 0                            # items processed ok (or rows written)
    detail: str = ""
    failed: int = 0
    reasons: dict[str, int] = field(default_factory=dict)
    skipped: int = 0                         # scope fine-filter exclusions (link)
    stopped: tuple | None = None             # (stage, item, remaining) budget stop


# ---------------------------------------------------------------------------
# per-item processing -- the shared loop for classify and reconcile
# ---------------------------------------------------------------------------


def _item_loop(conn, stage: str, rows: list, process: Callable[[str], Any],
               *, deadline: float | None, guard: _RateGuard) -> tuple:
    """Process ``rows`` one item at a time. Never raises: one bad item is
    logged and the pass continues; a budget stop returns ``stopped``."""
    ok = failed = 0
    reasons: dict[str, int] = {}
    stopped = None
    total = len(rows)
    for i, row in enumerate(rows, 1):
        if _budget_exceeded(deadline):
            stopped = (stage, row["post_id"], total - i + 1)
            break
        item_id = row["post_id"]
        try:
            process(item_id)
            ok += 1
        except _BudgetExceeded as exc:
            print(
                f"    max-wait exceeded: stopped in {stage} at {item_id}; "
                f"{total - i + 1} item(s) remain unprocessed",
                flush=True,
            )
            stopped = (stage, item_id, total - i + 1)
            break
        except Exception as exc:  # noqa: BLE001 - per-item isolation is the contract
            failed += 1
            reason = type(exc).__name__
            reasons[reason] = reasons.get(reason, 0) + 1
            print(f"    {stage} item {item_id} failed: {reason}: {exc}", flush=True)
        if i % 10 == 0 or i == total:
            print(f"    [{i}/{total}] ok={ok} fail={failed}", flush=True)
    return ok, failed, reasons, stopped


def _guard_stats(guard: _RateGuard) -> str:
    if not (guard.cooldowns or guard.exhaustion_count):
        return ""
    return (f" cooldowns={guard.cooldowns} "
            f"cooldown_s={guard.total_cooldown_s:.0f} "
            f"exhausted_calls={guard.exhaustion_count}")


def _classify_stage(conn, guard: _RateGuard, rows: list, deadline: float | None) -> tuple:
    return _item_loop(
        conn, STAGE_CLASSIFY, rows,
        lambda pid: classify_post(conn, pid, chat_fn=guard),
        deadline=deadline, guard=guard,
    )


def _reconcile_stage(conn, guard: _RateGuard, rows: list, deadline: float | None) -> tuple:
    return _item_loop(
        conn, STAGE_RECONCILE, rows,
        lambda rid: reconcile_thread(conn, rid, chat_fn=guard),
        deadline=deadline, guard=guard,
    )


def _link_stage(conn, guard: _RateGuard, limit: int, deadline: float | None) -> tuple:
    """run_link_pass, with clean budget stops when a deadline is set.

    Without a deadline this is one plain run_link_pass call. With a deadline
    the pass is driven in small idempotent chunks so a budget stop lands
    BETWEEN passes instead of grinding every remaining post as a failure.
    Returns (aggregate dict, budget_stopped).
    """
    if deadline is None:
        res = run_link_pass(conn, chat_fn=guard, limit=(limit or None))
        return (
            {"eligible": res.eligible, "queued": res.queued,
             "applied": res.applied, "failures": list(res.failures)},
            guard.budget_tripped,
        )
    chunk = _LINK_CHUNK if not limit else min(limit, _LINK_CHUNK)
    agg = {"eligible": 0, "queued": 0, "applied": 0, "failures": []}
    while not _budget_exceeded(deadline):
        res = run_link_pass(conn, chat_fn=guard, limit=chunk)
        agg["eligible"] += res.eligible
        agg["queued"] += res.queued
        agg["applied"] += res.applied
        agg["failures"].extend(res.failures)
        if guard.budget_tripped:
            return agg, True
        if res.eligible == 0:
            return agg, False
    return agg, True


# ---------------------------------------------------------------------------
# argparse-lite: the runner style matches run_w4.py / run_insight_tables.py
# ---------------------------------------------------------------------------

_SKIP_FLAGS = {
    "--skip-classify": "classify",
    "--skip-reconcile": "reconcile",
    "--skip-link": "link",
    "--skip-insight": "insight",
}
_VALUE_FLAGS = ("--limit-per-stage", "--pacing", "--max-wait-minutes", "--db")


def _parse_argv(argv: list[str]) -> dict | None:
    opts = {
        "skips": set(), "limit": 0, "pacing": PACE_S, "max_wait_min": 0.0,
        "yes": False, "dry": False, "db": DB_PATH, "raw_argv": list(argv),
    }
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in _SKIP_FLAGS:
            opts["skips"].add(_SKIP_FLAGS[arg])
            i += 1
        elif arg == "--yes":
            opts["yes"] = True
            i += 1
        elif arg == "--dry-run":
            opts["dry"] = True
            i += 1
        elif arg in _VALUE_FLAGS:
            if i + 1 >= len(argv):
                return None
            value = argv[i + 1]
            i += 2
            if arg == "--limit-per-stage":
                try:
                    opts["limit"] = max(0, int(value))
                except ValueError:
                    return None
            elif arg == "--pacing":
                try:
                    opts["pacing"] = max(0.0, float(value))
                except ValueError:
                    return None
            elif arg == "--max-wait-minutes":
                try:
                    opts["max_wait_min"] = max(0.0, float(value))
                except ValueError:
                    return None
            else:  # --db
                opts["db"] = Path(value)
        else:
            return None
    return opts


def _usage() -> None:
    print(
        "Usage:\n"
        "  python traderlog/run_recon.py [--skip-classify] [--skip-reconcile]\n"
        "                                [--skip-link] [--skip-insight]\n"
        "                                [--limit-per-stage N] [--pacing S]\n"
        "                                [--max-wait-minutes M] [--db PATH]\n"
        "                                [--yes] [--dry-run]\n"
        "\n"
        "Chains the four recon stages (classify -> reconcile -> link -> insight),\n"
        "each skippable and resumable. Default DB is production traderlog.db:\n"
        "running against it requires --yes (take a backup before a first-ever\n"
        "production run).\n"
        "\n"
        "  --skip-classify        do not classify unclassified posts\n"
        "  --skip-reconcile       do not reconcile new position roots\n"
        "  --skip-link            do not run the cross-thread link pass\n"
        "  --skip-insight         do not refresh themes/breadth_notes/edu_items\n"
        "  --limit-per-stage N    at most N items per stage (default 0 = no limit)\n"
        "  --pacing S             per-item sleep between LLM calls (default 2.5)\n"
        "  --max-wait-minutes M   cap on rate-wall waiting (default 0 = unlimited);\n"
        "                         stops cleanly with the exact resume state\n"
        "  --db PATH              target a non-production database\n"
        "  --yes                  confirm an intentional run against production\n"
        "  --dry-run              SELECT-only planning; no writes, no LLM calls\n"
        "\n"
        "Exit codes: 0 ok, 1 item failures recorded, 2 usage or gate refusal,\n"
        "3 stopped by --max-wait-minutes.",
        flush=True,
    )


def _is_prod(db_path: Path) -> bool:
    try:
        return Path(db_path).resolve() == Path(DB_PATH).resolve()
    except OSError:
        return False


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------

_VISION_REMINDER = (
    "vision backfill is a manual Gemini pass -- see design/VISION_BACKFILL_SPEC.md"
)


def _summarize(conn, reports: dict[str, _StageReport], skips: set[str],
               opts: dict, budget_stop: tuple | None) -> int:
    print()
    print("=" * 62)
    print("RECON SUMMARY")
    for stage, key in (
        (STAGE_CLASSIFY, "classify"),
        (STAGE_RECONCILE, "reconcile"),
        (STAGE_LINK, "link"),
        (STAGE_INSIGHT, "insight"),
    ):
        if key in skips:
            print(f"  {stage}: skipped by flag")
        elif stage in reports:
            rep = reports[stage]
            extra = f" failed-by-reason={rep.reasons}" if rep.reasons else ""
            print(f"  {stage}: ok={rep.rows} failed={rep.failed} "
                  f"skipped={rep.skipped}{extra}")
        else:
            print(f"  {stage}: did not run")
    backlog = _vision_backlog_count(conn)
    print(f"  vision backlog: {backlog} media row(s) on trade_event/education "
          "posts without vision_json")
    print(f"  {_VISION_REMINDER}. THIS RUNNER NEVER CALLS VISION.")
    if budget_stop is not None:
        stage, item, remaining = budget_stop
        print(f"  STOPPED at --max-wait-minutes budget: stage {stage}, "
              f"{remaining} item(s) remain (at {item or '-'})")
        print("  resume with the exact same command -- every stage is idempotent:")
        print(f"    python traderlog/run_recon.py {' '.join(opts['raw_argv'])}")
    print("=" * 62)
    if budget_stop is not None:
        return 3
    if any(rep.status == "fail" or rep.failed for rep in reports.values()):
        return 1
    return 0


# ---------------------------------------------------------------------------
# the run
# ---------------------------------------------------------------------------


def _run(conn, opts: dict, *, chat_fn: Callable[..., Any],
         sleep: Callable[[float], None], threshold: int,
         cooldown_base_s: float, cooldown_cap_s: float) -> int:
    run_date = date.today().isoformat()
    skips = opts["skips"]
    limit = opts["limit"]
    deadline = (
        time.monotonic() + opts["max_wait_min"] * 60.0
        if opts["max_wait_min"] > 0 else None
    )
    guard = _RateGuard(
        chat_fn, pacing=opts["pacing"], threshold=threshold,
        cooldown_base_s=cooldown_base_s, cooldown_cap_s=cooldown_cap_s,
        deadline=deadline, sleep=sleep,
    )
    reports: dict[str, _StageReport] = {}

    def log(rep: _StageReport, dur_s: float) -> None:
        _log_run(conn, rep.stage, run_date, rep.status, rep.rows, dur_s, rep.detail)

    def finish(budget_stop: tuple | None = None) -> int:
        return _summarize(conn, reports, skips, opts, budget_stop)

    if opts["dry"]:
        print("dry-run: planning only -- SELECTs, no writes, no LLM calls")
        for stage, key in (
            (STAGE_CLASSIFY, "classify"), (STAGE_RECONCILE, "reconcile"),
            (STAGE_LINK, "link"), (STAGE_INSIGHT, "insight"),
        ):
            if key in skips:
                print(f"  {stage}: skipped by flag")
                continue
            if key == "link":
                print(f"  {stage}: {_link_coarse_count(conn)} eligible-by-filter "
                      "post(s) would be proposed")
            elif key == "insight":
                n = conn.execute(
                    "SELECT COUNT(*) FROM posts p JOIN post_class c "
                    "ON c.post_id = p.post_id "
                    "WHERE c.kind IN ('theme','breadth','education')"
                ).fetchone()[0]
                print(f"  {stage}: {n} classified post(s) would materialise "
                      "themes/breadth_notes/edu_items")
            else:
                scope_fn = _classify_scope if key == "classify" else _reconcile_scope
                print(f"  {stage}: {len(scope_fn(conn, limit))} item(s) would "
                      "be processed")
        return finish()

    # --- 1/4 classify ------------------------------------------------------
    if "classify" in skips:
        print("[1/4] classify -- SKIPPED (--skip-classify)")
    else:
        rows = _classify_scope(conn, limit)
        suffix = f" (limit {limit})" if limit else ""
        print(f"[1/4] classify -- {len(rows)} unclassified post(s){suffix}")
        if rows:
            t0 = time.monotonic()
            ok, failed, reasons, stopped = _classify_stage(conn, guard, rows, deadline)
            rep = _StageReport(
                stage=STAGE_CLASSIFY,
                rows=ok, failed=failed, reasons=reasons,
                detail=(f"ok={ok} failed={failed} reasons={reasons}"
                        + _guard_stats(guard)),
                stopped=stopped,
            )
            if stopped:
                rep.status = "fail"
                rep.detail += (f" max-wait-exceeded stopped={stopped[1]} "
                               f"remaining={stopped[2]}")
            log(rep, time.monotonic() - t0)
            reports[STAGE_CLASSIFY] = rep
            print(f"      done: ok={ok} failed={failed} reasons={reasons}", flush=True)
            if stopped:
                return finish(stopped)
        else:
            rep = _StageReport(stage=STAGE_CLASSIFY, detail="scope empty")
            log(rep, 0.0)
            reports[STAGE_CLASSIFY] = rep
            print("      scope empty -- nothing to do", flush=True)

    # --- 2/4 reconcile -------------------------------------------------------
    if "reconcile" in skips:
        print("[2/4] reconcile -- SKIPPED (--skip-reconcile)")
    else:
        rows = _reconcile_scope(conn, limit)
        suffix = f" (limit {limit})" if limit else ""
        print(f"[2/4] reconcile -- {len(rows)} candidate root(s) with no "
              f"position{suffix}")
        if rows:
            t0 = time.monotonic()
            ok, failed, reasons, stopped = _reconcile_stage(conn, guard, rows, deadline)
            rep = _StageReport(
                stage=STAGE_RECONCILE,
                rows=ok, failed=failed, reasons=reasons,
                detail=(f"ok={ok} failed={failed} reasons={reasons}"
                        + _guard_stats(guard)),
                stopped=stopped,
            )
            if stopped:
                rep.status = "fail"
                rep.detail += (f" max-wait-exceeded stopped={stopped[1]} "
                               f"remaining={stopped[2]}")
            log(rep, time.monotonic() - t0)
            reports[STAGE_RECONCILE] = rep
            print(f"      done: ok={ok} failed={failed} reasons={reasons}", flush=True)
            if stopped:
                return finish(stopped)
        else:
            rep = _StageReport(stage=STAGE_RECONCILE, detail="scope empty")
            log(rep, 0.0)
            reports[STAGE_RECONCILE] = rep
            print("      scope empty -- nothing to do", flush=True)

    # --- 3/4 link pass ---------------------------------------------------------
    if "link" in skips:
        print("[3/4] link -- SKIPPED (--skip-link)")
    else:
        coarse = _link_coarse_count(conn)
        suffix = f" (limit {limit})" if limit else ""
        print(f"[3/4] link -- {coarse} eligible-by-filter post(s){suffix}")
        if coarse:
            t0 = time.monotonic()
            agg, budget_stopped = _link_stage(conn, guard, limit, deadline)
            dur = time.monotonic() - t0
            failed = len(agg["failures"])
            ok = agg["eligible"] - failed
            skipped = max(coarse - agg["eligible"], 0)
            detail = (
                f"eligible={agg['eligible']} queued={agg['queued']} "
                f"applied={agg['applied']} failures={failed} "
                f"skipped_by_filter={skipped}" + _guard_stats(guard)
            )
            rep = _StageReport(stage=STAGE_LINK, rows=ok, failed=failed,
                               skipped=skipped, detail=detail)
            if budget_stopped:
                rep.status = "fail"
                remaining = _link_coarse_count(conn)
                rep.stopped = (STAGE_LINK, "link-pass", remaining)
                rep.detail += " max-wait-exceeded"
            log(rep, dur)
            reports[STAGE_LINK] = rep
            print(f"      done: eligible={agg['eligible']} queued={agg['queued']} "
                  f"applied={agg['applied']} failures={failed} "
                  f"skipped_by_filter={skipped}", flush=True)
            if budget_stopped:
                return finish(rep.stopped)
        else:
            rep = _StageReport(stage=STAGE_LINK, detail="scope empty")
            log(rep, 0.0)
            reports[STAGE_LINK] = rep
            print("      scope empty -- nothing to do", flush=True)

    # --- 4/4 insight -------------------------------------------------------
    if "insight" in skips:
        print("[4/4] insight -- SKIPPED (--skip-insight)")
    else:
        t0 = time.monotonic()
        try:
            stats: dict = {}
            n = run_insight(conn, run_date, _stats_out=stats)
            rep = _StageReport(
                stage=STAGE_INSIGHT,
                rows=n,
                detail=(f"rows={n} themes={stats['themes']['written']} "
                        f"breadth_notes={stats['breadth_notes']['written']} "
                        f"edu_items={stats['edu_items']['written']}"),
            )
        except Exception as exc:  # noqa: BLE001 - log and report, never crash
            rep = _StageReport(stage=STAGE_INSIGHT, status="fail",
                               detail=f"{type(exc).__name__}: {exc}")
        log(rep, time.monotonic() - t0)
        reports[STAGE_INSIGHT] = rep
        print(f"      done: {rep.detail}", flush=True)

    return finish()


def main(argv: list[str] | None = None, *, chat_fn: Callable[..., Any] | None = None,
         sleep: Callable[[float], None] | None = None,
         cooldown_threshold: int = EXHAUSTION_THRESHOLD,
         cooldown_base_s: float = COOLDOWN_BASE_S,
         cooldown_cap_s: float = COOLDOWN_CAP_S) -> int:
    """Run the recon chain. ``argv`` defaults to sys.argv[1:].

    Keyword overrides exist for deterministic tests: ``chat_fn`` replaces the
    provider (never hit the network), ``sleep`` replaces time.sleep, and the
    cooldown knobs shrink so a cooldown test stays fast.
    """
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or "-h" in argv or "--help" in argv:
        _usage()
        return 0

    opts = _parse_argv(argv)
    if opts is None:
        print("run_recon: unrecognized argument or missing value", file=sys.stderr)
        _usage()
        return 2

    db_path = opts["db"]
    prod = _is_prod(db_path)
    if prod and not opts["yes"]:
        print(
            f"REFUSING: --db resolves to the production TraderLog database "
            f"({DB_PATH}). Pass --yes to confirm an intentional live run "
            "(take a backup first -- never run a first-ever production pass "
            "without one), or point --db at a disposable database.",
            file=sys.stderr,
        )
        return 2
    if prod:
        print(
            f"PRODUCTION run confirmed (--yes). REMINDER: take a backup of "
            f"{DB_PATH} before your first-ever production run.",
            flush=True,
        )

    conn = init_db(db_path)
    try:
        return _run(
            conn, opts,
            chat_fn=chat_fn if chat_fn is not None else provider.chat,
            sleep=sleep if sleep is not None else time.sleep,
            threshold=cooldown_threshold,
            cooldown_base_s=cooldown_base_s,
            cooldown_cap_s=cooldown_cap_s,
        )
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())