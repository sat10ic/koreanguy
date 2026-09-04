# ORCHESTRATOR PLAYBOOK — how to run the Manas OS build (for Opus/Fable main thread)

You ORCHESTRATE; you do not bulk-code. Executors (Codex via codex-rescue subagent, or
Sonnet subagents for mechanical work) build; you gate. The work queue is
EXECUTOR_PLAYBOOK.md (waves 0-6 + final); per-wave specs are named there.

## The loop (per batch)
1. PICK the next unchecked step from the current wave. ONE executor batch at a time —
   never fan out parallel Codex jobs (credit burn + merge collisions, user-flagged twice).
2. WRITE the batch prompt: point at the spec file + step number, restate only the
   guardrails (protected files, pytest baseline, "say so plainly if sandbox blocks
   execution", "do not tick STATUS lines — orchestrator ticks after verification").
   Specs are already zero-judgment; do NOT paraphrase their content into the prompt
   (drift risk) — reference it.
3. LAUNCH via the codex:codex-rescue subagent, background, --fresh (resume threads hang;
   two zombie "queued" jobs are known — ignore them, cancel is broken on Windows).
4. WAIT on the completion notification. Do not poll in a loop; schedule a wakeup
   (~12 min) as the fallback.
5. VERIFY YOURSELF — never trust the executor's self-report:
   - `python -m pytest manas_os/tests -q` from repo root (know your baseline number).
   - `cd manas_os/frontend && npm run build` when frontend touched.
   - UI work: preview servers via launch.json (manas-os-api :8000, manas-os-frontend
     :5173 — binds 0.0.0.0), then the TWO-DIRECTION audit vs WIREFRAMES.md at 1470px:
     (a) every ASCII block present in order; (b) NOTHING extra on screen. Use text
     snapshots for structure, screenshots for gestalt, and CROSS-CHECK RENDERED NUMBERS
     AGAINST THE API PAYLOAD with curl — presence-checking alone missed real bugs
     (risk-band 0.35 vs 0.50, rank/4 vs rank_of, hidden funnel gates).
   - Backend work: exercise the endpoint/stage against the real DB, not just tests.
6. On PASS: tick the spec checkbox + STATUS line yourself, sync TASKS.md, commit with a
   what+why message, push to `emergent`. One commit per verified batch.
7. On FAIL: write the exact defect list (file, block, expected vs rendered) into the spec
   file (DETAIL-AUDIT LEDGER pattern), launch ONE kickback batch. Defects the executor
   can't see (visual) must be described textually — executors cannot screenshot.

## Non-negotiable gates (learned the hard way — do not relax)
- REWRITE-don't-patch for any screen with layout drift (CODEX_WIREFRAME_BUILD.md rule).
  "Reuse existing components as building material" licenses patchwork — never write that.
- A visual task is NOT done at "build clean + tests green". Screenshot or it didn't happen.
- Persisted DB rows can predate a code fix — re-run the pipeline stage on current code
  before calling something a live bug (rr=2.0 false alarm).
- SQLite lock 500s: check for orphaned python.exe processes first (`tasklist`), not the
  visible background job. Long research jobs (replay, studies) run on a DB COPY in the
  scratchpad, never the live DB.
- If the user reports "old tool" while you see new: check server binding (vite must serve
  IPv4+IPv6 — --host 0.0.0.0), stale HMR after file deletions (restart dev server), and
  browser cache (incognito test) BEFORE doubting the build.
- LOCKED thresholds never change inside an executor batch. Calibration = replay A/B on a
  copy + LEARNINGS entry + one change per gate per quarter (EXECUTOR_PLAYBOOK W1.3).
- LIGHT THEME. Dark reskin cancelled (RESKIN_DARK.md). The differentiation the user wants
  is feature/viz completeness per WIREFRAMES.md + VIZ_BRAINSTORM.md.

## What you do yourself (never delegate)
- The two-direction + payload-cross-check audits (step 5).
- Architecture decisions, spec authoring, kickback defect lists.
- LEARNINGS.md verdict entries for studies (executors run studies; you write conclusions).
- Anything touching the four protected engine files (rare; hand-edit with tests).
- Final review of anything the user will rely on.

## Delegation ladder
- Codex: all feature/screen/module builds against a written spec.
- Sonnet subagent: bulky mechanical work (bulk file audits, fixture rewrites, data
  imports) and browser-driving verification legwork IF you spot-check its findings.
- Opus subagent (or main thread): judgment-heavy synthesis, study analysis drafts.
- Fable subagent: only for a critical review of the whole (rare, expensive) — always with
  "no subagents, answer directly" in its prompt (it loops otherwise).

## Session hygiene
- Start of session: read SESSION_HANDOFF.md, then `git log --oneline -10`, then pytest
  for the true baseline. CODEX_HANDOFF/CODEX_WIREFRAME_BUILD checkboxes may over- or
  under-claim — the suite + browser are the truth.
- Wakeups: schedule (~12-20 min) instead of polling; on wakeup, check status once, act.
- End of session (or on user request): update SESSION_HANDOFF.md "To continue" with the
  in-flight batch id + next unchecked step; push everything verified; never leave
  uncommitted verified work.
- User-visible reporting: lead with what landed + what's verified; one screenshot beats a
  paragraph; never claim done for unverified work (the checkbox-vs-reality gap destroyed
  trust once — "163 green, build clean" while three endpoints 500'd).

## Current position (2026-07-07, update this block each session)
- In flight: ADVISOR build (Codex), full-history replay on DB copy (background python).
- Next unchecked: WAVE 0 (verify D1-D5, FOCUS fields, advisor QC, drawer audit) → W1 edge
  verdict. UI status: SETUPS/REGIME/WATCHLIST two-direction verified; JOURNAL rebuilt
  (D4/D5 verify pending); FOCUS built (fields unverified); DRAWER unaudited.
