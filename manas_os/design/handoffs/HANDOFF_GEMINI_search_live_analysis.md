# HANDOFF 7 — Universal search → on-demand analysis → LIVE debate stream (Gemini)

Repo `C:\Users\satta\Downloads\koreanguy`, branch `emergent`. Standing rules: HANDOFF_INDEX.md.
Closes the P0 gaps in `manas_os/design/UX_GAP_AUDIT.md` #1+#2 (+#3/#4). THE priority UX fix.

## The gap
Search (`desk/src/App.jsx submitSymbolSearch`) only navigates to DEBATE — a non-pool symbol shows
an empty panel. `agents/debate.py::push_symbol_debate(conn, symbol, date)` already runs a FULL
council debate for ANY symbol on demand (POST `/api/desk/debate/push`), but SYNCHRONOUSLY with no
live view. UI-2's jobs/events/SSE Live Work plumbing (`manas_os/live*`? no — `desk/src/livework/`
+ `/api/jobs/.../events/stream` + `useJobStream.js`) is built but not wired to it.

## Scope
1. **Backend — make on-demand debate a streamed JOB (not a blind sync wait).** Wrap
   `push_symbol_debate` so it runs inside the UI-2 jobs framework (see how run-eod emits — the jobs
   runner / `jobs.emit`): a POST that CREATES a job and runs the debate in a background thread,
   emitting an event per stage: context-pack built → each model seat's verdict as it returns
   ("deepseek-v4: TAKE c3") → chair adjudication → sizer → done. Return the job_id immediately.
   Keep the existing synchronous endpoint working (back-compat) OR add `?stream=1`. ANY valid NSE
   symbol must work (gate status is shown, NOT required — per ALPHA_LEARNING_CONSTRAINTS: study
   behaviour/reversals even when gates fail). Reject only truly unknown symbols (no price history),
   honestly.
2. **Search → analyze wiring.** `submitSymbolSearch` (and a search affordance reachable from the
   shell, `/` shortcut) calls the on-demand analyze: kicks the job, routes to DEBATE for that symbol
   in a "LIVE — analyzing…" state. Autocomplete/validate against known symbols (symbol_identity /
   daily_prices) so the user knows it's a real ticker before submit; honest "no data for X" if not.
3. **LIVE debate view.** DEBATE tab, for an in-progress on-demand symbol, streams the job events via
   `useJobStream`: a live council panel showing each model seat filling in as it reasons, then chair,
   then sizer — the user WATCHES the debate happen. On completion it resolves into the normal v5
   debate card (source='user_pushed' badge). The Live Work inspector also shows the job progress
   (reuse the existing inspector — this is its whole point). Keep last state visible; honest error
   state if a seat/LLM fails (partial debate, not a blank).
4. **Tests**: endpoint creates a job + streams ordered events (fixture LLM client); non-pool symbol
   analyzes end-to-end; unknown symbol rejected honestly; desk pure helpers (stream reducer) vitest.

## Guardrails
One-writer-for-risk (the pushed debate's sizer/plan are server-authored; UI shows verbatim). No
synthetic reasoning — stream REAL model output only; a seat with no result shows "pending/failed",
never invented text. Paper/manual unchanged. Do NOT touch gates/risk/snapshot. Money-math locked.
`.v5`-scoped CSS, plain SVG, a11y AA, reduced-motion. Real data only.

## Output
`HANDOFF_GEMINI_search_live_analysis_COMPLETED.md`: the job/endpoint contract, the event sequence,
search wiring, the LIVE debate view, test results, and REAL command/DOM output (not simulated —
paste actual curl + actual streamed events). Flag uncertainty rather than inventing.
