# SESSION HANDOFF — pick up here (written 2026-07-12, outgoing session out of credits)

Repo `C:\Users\satta\Downloads\koreanguy`. Branch `emergent`. HEAD at handoff time: `19be2345`.
Working tree clean. Read this file FIRST, then `manas_os/design/handoffs/HANDOFF_INDEX.md` (the
live execution queue), then whichever ledger the current task points at.

## What the user actually wants (do not re-litigate)
An NSE swing-trading "edge workbench" that a BEGINNER can run end-to-end as a guided PROCESS, not
a pile of disconnected cards with tag-level explainers. This has been asked for since the start of
the project and repeatedly re-flagged. The orchestrator's biggest standing failure this arc was
running code/guardrail QC and declaring waves "done" while missing rendered usability holes until
the user pointed at a specific one — see `~/.claude memory feedback-proactive-ux-audit.md` (also
readable via the memory system if this session has it; otherwise the lesson is: ALWAYS run a
rendered "what can't the user do here" pass before calling anything done, unprompted).

## Current workflow constraint (still in effect unless the user lifts it)
`manas_os/design/handoffs/WORKFLOW_CURRENT.md`: NO subagents in this thread except one-off Fable
consults if genuinely needed for synthesis/audit. ALL coding ships as handoff .md files in
`manas_os/design/handoffs/`, addressed to Gemini or GLM (the user has accounts for both, pastes the
handoff into their chat, pastes the code back). The orchestrator's job is: author handoffs, then on
paste-back RECONCILE (wire any flagged backend fields into single-writer files like app.py/schema.sql
yourself), QC against real running data (curl/DOM — NOT the completion note's claimed proof, which
has been caught fabricating a "simulated" curl once already), commit, update HANDOFF_INDEX.md status,
move to the next queued handoff. If the user lifts the no-subagent rule, resume normal Agent-tool
delegation per the standing CLAUDE.md protocol (Fable directs/reviews, Sonnet/Codex execute).

## Architecture ground truth (verified, current)
- **Backend**: FastAPI `manas_os/api/app.py`, SQLite `manas_os/data/manas.db` (point-in-time,
  additive migrations only), pipeline orchestrated by `manas_os/cli/__init__.py::_load_stages()`
  (`python run_manas_api.py` starts the API on :8000).
- **Frontend**: React+Vite desk `manas_os/desk/` (:5174 via `npm run dev` in that dir). ALL 7 tabs
  now rebuilt on the v5 LIGHT design system (locked, do not re-litigate the aesthetic): tokens
  `desk/src/styles/tokens.v5.css`, 19+ primitives `desk/src/components/v5/` (import from index.js,
  do not re-create), pattern reference `DebateTab.jsx`/`MarketHomeTab.jsx`. Old App.css was cut from
  84KB to a much smaller shell-only stylesheet in UI-7; do not resurrect dark/Barlow — that thesis is
  superseded (see `UI_OVERHAUL_HANDOFF.md` §4 banner).
- **Money math is LOCKED**: `scanner/gates.py`, `risk/plan.py` (or wherever the deterministic
  sizer/plan lives), `regime/snapshot.py`, `regime/governor.py`, `scanner/candidates.py`,
  `agents/sizer.py` — these must show ZERO diff across any handoff. UI/analytics NEVER compute
  stop/qty/target/risk client-side; server values verbatim, one-writer discipline. This has held
  through 291+ commits this arc — keep it that way. Verify with `git diff --stat` on those files
  after every handoff before committing.
- **Paper-first LOCKED**: `manas_os/config.yaml` (gitignored, has Fyers/Telegram secrets — NEVER
  commit/echo/log them) `agents.telegram_live: false`. Live Telegram send is double-gated (flag AND
  a written graduation doc that does not exist). The live intraday loop (`manas_os/live/`,
  `alerts/live_fsm.py`) is built and green in PAPER mode only — do not flip telegram_live.
- **Alpha/shadow discipline LOCKED**: `manas_os/alpha/` (promotion_gates.py, leakage_audit.py,
  memory.py, resolver.py, symbol_identity.py) is SHADOW-ONLY — verified not imported by any
  gate/debate/risk/ranking code. No model is promoted. Keep it that way until the validated-
  promotion gates (walk-forward + 20 live shadow sessions + calibration) actually pass — see
  `manas_os/design/ALPHA_LEARNING_CONSTRAINTS.md`.
- **Live-first decision** (`manas_os/design/LIVE_FIRST_DECISION.md`, user-locked): LIVE is meant to
  be the default experience during market hours; EOD (bhavcopy/ChartsMaze) is the confirmatory
  evidence/gate layer. Desk live-default UI is PARTIAL (backend done, frontend incomplete) — see
  handoff 8.

## THE #1 finding of this session (verified, not guessed) — fix this first
`GET /api/flow/today` (app.py:2963) is a FULLY BUILT guided daily-flow endpoint — 6 steps
(data/regime/positions/setups/plan/done) with live status/blockers/actions (e.g. "1 position
flagged EXIT TODAY: HUDCO", "4 setups need TAKEN/SKIPPED"). It has **ZERO references anywhere in
`manas_os/desk/src/`** — built server-side, never rendered. This is why the tool reads as
disconnected cards instead of a guided system. **Handoff 10 renders it. Do this first if nothing
else gets done.**

## Full ranked UX findings
`manas_os/design/UX_AUDIT_FULL.md` — comprehensive, screen-by-screen, driven live on real
2026-07-10 data, each finding evidence-tagged [rendered]/[code]. Read before touching UI.
`manas_os/design/UX_GAP_AUDIT.md` — the earlier, narrower pass (search/live-debate gap).

## The live handoff queue (execute IN ORDER — shared-file collisions)
See `manas_os/design/handoffs/HANDOFF_INDEX.md` for the authoritative status table. As of this
handoff, DONE+committed: 0a,0b,1,2,3(partial),4,6(partial). PENDING, in priority order:

1. **`HANDOFF_GEMINI_guided_system.md` (#10) — DO FIRST.** Render `/api/flow/today` as a persistent
   guided-flow rail + standard per-tab "WHAT THIS IS / HOW TO READ / NEXT→" headers + an
   Alpha↔Debate↔Shortlist relationship legend (they show DIFFERENT stocks by design — Alpha=shadow
   whole-universe ranking, Debate=gate-passed council verdicts, Shortlist=user's own watch — nothing
   currently explains this, confirmed the #1 beginner-confusion complaint) + a LIVE/SHADOW/WARMING/
   NEEDS-DATA status-chip vocabulary so nothing (like the HMM regime state) renders blank/unexplained.
2. **`HANDOFF_GEMINI_search_live_analysis.md` (#7).** Wire the existing search box to the
   ALREADY-BUILT `agents/debate.py::push_symbol_debate` (on-demand debate of ANY symbol, currently
   unreachable from the UI) as a streamed job through the UI-2 jobs/SSE plumbing
   (`desk/src/livework/`, `/api/jobs/.../events/stream`) so the user WATCHES the council debate
   live instead of a blind synchronous wait.
3. **`HANDOFF_GEMINI_ux_defects_batch.md` (#11).** Shortlist verdict/waiting-on contradictions (a
   real one-opinion leak — verify and fix), JOURNAL delete button (backend `DELETE
   /api/journal/{trade_id}` at app.py:3352 already exists, just no UI — the user specifically asked
   to delete a test HUDCO entry and can't), POSITIONS debug-string leak ("dry-run: shown, not sent"
   shown raw) + missing live-price freshness marker, SCANNERS results rendering ~7000px offscreen
   with no scroll-to + duplicate preset fetches, date-scrubber dead-ends, no URL routing (back
   button exits the app), TRADE PLAN missing chart/checklist-persistence/log-to-journal.
4. **`HANDOFF_GEMINI_regime_history_hmm.md` (#12).** User asked "why doesn't HMM work despite tons
   of bhavcopy backlog" — diagnosed: NOT a bhavcopy problem, hmmlearn is installed. `regime_snapshots`
   only has 286 sessions (from 2025-03-19) even though `daily_prices` now spans 1238 sessions back to
   2021-07-12 (5y backfill already done, see commit `d3945e81`) — the regime series was never
   replayed over the extended history (`manas cli backfill-snapshots` exists, just needs running).
   ALSO `regime_hmm_states` table doesn't exist — the stage isn't persisting, root cause unknown,
   needs investigation. Fix both; make HMM honestly report WARMING if still data-short.
5. `HANDOFF_GEMINI_live_default_ui.md` (#8) — finish live stage-2 desk frontend (backend done).
6. `HANDOFF_GEMINI_guru_tradeplan_panel.md` (#9) — render the already-built mentor-checklist API
   (Arora-first, corpus-cited) as a panel on TRADE PLAN + DEBATE deep-dive.

## Also queued, lower priority (not urgent, don't forget)
- Task/wave **#44 Breadth-enrichment**: `manas_os/design/BREADTH_ENRICHMENT_WAVE.md` — Tier 0
  (debate context) is DONE (commit `4f39158a`); Tier 1 (regime-quality refinement behind a replay
  A/B gate) and Tier 2 (locked, needs explicit sign-off) are not started.
- **Fyers intraday backfill BLOCKED on auth** (handoff 5 completion note) — needs the user to
  re-authenticate (6am IST daily token expiry); machinery is ready, just never run against live creds.
- `manas_os/design/knowledge/EXTERNAL_ALPHA_ADOPTION_MAP.md` — 5 external repos reviewed
  (QuantGPT/xtquantai/vibe-bot-catalogue/claude-trading-skills/tradememory-protocol), top adoptions
  already coded into alpha/ (promotion_gates, leakage_audit, memory.py weighted retrieval); lower-
  priority items (two-tier cheap-triage routing, etc.) still just documented.
- Task #29 (Beginner/Expert toggle real) and #1 (Regime page trend/history strip) — old backlog
  items, may now be partially subsumed by handoff 10's work; re-check before starting fresh.

## Process rules that bit us this session (follow them)
1. **Gemini's completion notes have fabricated a "simulated" curl proof at least once** (breadth
   tier0 — the code was actually correct, but the proof was invented). ALWAYS re-verify every
   completion against the LIVE running app (restart API if needed, real curl, real DOM check) before
   committing — never trust a completion doc's proof at face value.
2. **Parallel external coders must own disjoint files** — GLM/Gemini handoffs explicitly list
   "NEW FILES ONLY" or the exact files they may touch; anything shared (app.py, schema.sql, tokens,
   cli) gets wired by the orchestrator on paste-back, never by two coders at once.
3. **Commit per-handoff, not in bulk** — makes QC/revert tractable; message states what changed +
   what was verified + what guardrail was checked.
4. **Never `git add -A`** — stage explicit paths; the repo accumulates stray junk (logs, scratch
   scripts) that must never be committed.
5. Windows console: never print the rupee glyph (cp1252 crash) — use "Rs". Absolute python
   interpreter paths in any Codex-sandbox context (bare `python`/`npm` can misresolve).

## Immediate next action for the incoming session
1. Read `manas_os/design/handoffs/HANDOFF_INDEX.md` for the current true status (it may have moved
   since this snapshot if the user pasted more completions before switching accounts).
2. If handoff 10 hasn't been fed to Gemini yet, that's the very next step — it's the highest-leverage
   fix in the whole backlog (turns the tool from cards into a system).
3. Restart both servers to verify baseline before doing anything: `python run_manas_api.py`
   (port 8000) and `cd manas_os/desk && npm run dev` (port 5174) — confirm `/api/pipeline/status`
   200s and the desk loads on real data before starting work.
4. Follow the standing CLAUDE.md protocol otherwise (it's unchanged): terse replies, verify before
   declaring done, real numbers not simulated ones, and — the lesson of this whole session —
   proactively run the rendered UX pass, don't wait to be told.
