# Pre-loop safety pass + UI integration plan — COMPLETED

2026-08-30, Claude Sonnet 5, orchestrator.

## What was asked

Resume the unidesk build loop: check HANDOFF/plan for updates, consult Opus
if the build order looks foolproof, start coding each stage in a loop toward
completion, checking with Opus at major stages. Also asked, mid-turn: set an
hourly reminder to resume in case the session stalls, and build a plan for
how backend work integrates into the frontend UI over time.

## What was found and fixed

**Critical: no git history.** `unidesk/`, `orderflow/`, `plan/`,
`unidesk_terminal/` were entirely untracked — `git ls-files unidesk` returned
0, no `.gitignore` rule excluded them. Two days and four models of work had
zero rollback point; `STATE.json`'s `last_verified_commit` (`a1f50878`)
predates all of it and is meaningless for this tree. Ran a secret scan
(clean), then committed a baseline: `f5615227`, 230 files, no functional
change.

**Opus pre-flight review**, given the full DECISIONS.md (D1–D18) and the
integration plan, plus the current directive queue from HANDOFF.md. Findings,
folded into HANDOFF's "To continue" block:

- The queued N4 directive would have rebuilt `research/costs.py` and
  `research/leakage_suite.py`, both already complete.
- The actual leakage gap: `assert_feature_not_after_decision`,
  `same_symbol_embargo`, `same_event_collision` have exactly one caller each
  (a test file), zero production call sites. Declared, not enforced.
- Corporate-action adjustment basis is not tracked on frozen research events;
  `attach_outcomes` performs no basis-consistency check. Running the planned
  archive-wide outcome attach as-is would silently label the 194 unconfirmed
  CA candidates with catastrophic-loss outcomes indistinguishable from real
  losses — one stage before the N5 gate meant to catch exactly this.
  Corrected: this guard is now a hard condition on N4's archive attach, not
  only on N5.
- N5 verdict: NO-GO. Stated CA-series gate is unmet (4/198 confirmed); the
  project's own CP-3 owner-invoked leakage audit (named "highest-risk gate in
  the build" in GOAL.md) has not run.
- Two path errors (`design/DECISIONS.md`/`design/CANONICAL.md` should have no
  `design/` prefix) and one stale number (105 vs the corroborated 194
  detector candidates) corrected.
- `STATE.json`'s `wave` / `showing_synthetic_data` fields are hardcoded
  literals in `checks/runner.py`, not measurements — flagged so nobody cites
  STATE.json as build-stage evidence.

Full corrected directive queue is now `unidesk/HANDOFF.md`'s "To continue"
block; this file is a summary, not a duplicate of record.

**UI integration plan.** `unidesk_terminal/` has zero real data wiring
(`grep -rl "fetch(\|axios\|useQuery" unidesk_terminal/src` — nothing outside
`fixtures.ts`); the only backend artifact today is Markdown. Wrote
`unidesk/design/UI_BACKEND_INTEGRATION_PLAN.md`: emit a JSON sibling to the
existing report via the already-built `contracts.*.to_dict()`, then wire
screens one at a time, each gated on real backend coverage rather than
aesthetic ambition (Tonight/Candidates now; Stock waits on U-P0.3; History
waits on the N4 adjustment-basis fix; Research waits on N5 being lifted).

**Hourly resume reminder.** Scheduled via CronCreate, session-only,
auto-expires in 7 days, prompts a future turn to re-read HANDOFF/TASKS, run
`run_checks.py` + pytest for ground truth, and continue the next queued
directive.

## Verification

- `git log -1 --stat` shows commit `f5615227`, 230 files, on top of a clean
  secret scan.
- `python unidesk/run_checks.py` and `python -m pytest unidesk/tests
  orderflow/tests -q` were run for ground truth before any of the above
  (272 passed, 1 skipped; checks exit 0) — this slice did not change
  production code, so the same baseline holds after.
- HANDOFF.md's "To continue" block was replaced in place (verified via diff)
  and a dated log entry appended.

## What was not done

No code was written this slice — it is safety infrastructure, a corrected
plan, and a documentation deliverable. Stage-1 real coding (the corrected N4
scope) starts next, as its own attributed slice.

Attribution-ID: attr-unidesk-preloop-safety-and-ui-plan-claude-sonnet5-20260830-001
