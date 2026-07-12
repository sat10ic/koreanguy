# UX / USABILITY GAP AUDIT — rendered "what can't the user DO here?" pass (2026-07-12)

Orchestrator applying the interface-design / feature-vs-ask lens that the prior QC (code-correctness
+ guardrails) skipped. Grounded in the actual shipped code, not assumed. Workflow lens:
SEARCH → ANALYZE → WATCH-IT-WORK → SCAN → WATCH(shortlist) → DECIDE(debate) → PLAN → MANAGE → LEARN.

## P0 — the holes the user hit (real workflow blockers)
1. **No on-demand analysis of an arbitrary stock.** A search box exists (`App.jsx submitSymbolSearch`)
   but it only NAVIGATES to the DEBATE tab — if the symbol wasn't in the nightly pool you land on an
   empty panel. Yet `agents/debate.py::push_symbol_debate` already runs a full council debate for ANY
   symbol on demand (POST `/api/desk/debate/push` exists). GAP = search is not wired to it. A user
   cannot type "RAIN" and get it analyzed.
2. **No "watch the debate happen" + no progress for on-demand work.** `push_symbol_debate` runs
   SYNCHRONOUSLY ("LLM latency is the caller's wait") — the UI just blocks with no visibility. The
   user cannot see the models reasoning or the chair adjudicating live, and there is no progress
   surface for on-demand analysis. UI-2's jobs/events/SSE Live Work plumbing is BUILT but never
   wired to the on-demand debate — the exact "see the work happening" feature, left unconnected.

## P1 — likely holes (verify on your screen; strong candidates)
3. **Chart-from-anywhere.** Can the user open any symbol's annotated chart (EMA/vol/RS/base) from
   the search box or a debated row, for a symbol not in a table? ChartDrawer exists; confirm it's
   reachable for an arbitrary searched symbol, not only table rows.
4. **Re-run / refresh a symbol on demand** without waiting for the nightly run (re-debate after new
   intraday behaviour). Tied to #1/#2.
5. **Compare two candidates** side by side (behaviour + plan) — no comparison view.
6. **Beginner guided flow** (task #29) — is the step-by-step "what do I do next" stepper real, or
   still labels+hiding? The whole beginner spine depends on it.
7. **Watchlist → why is it here / what changed** — provenance + next-trigger now exist (backend
   fields batch); confirm the SHORTLIST row actually surfaces them prominently.

## P2 — polish (note, don't rush)
8. Empty/loading/stale/error states consistent across all 7 v5 tabs (spot-check each).
9. Keyboard: is the search box focus-reachable (/) shortcut; are table rows keyboard-actionable.
10. Mobile/tablet layouts (deferred through the overhaul) — deliberate later pass.

## Fix plan
- **HANDOFF_GEMINI_search_live_analysis.md** closes P0 #1+#2 (+#3/#4): search → on-demand analyze →
  push_symbol_debate wrapped as a UI-2 job emitting per-seat events → Live Work inspector + a
  live-debate progress view stream the council reasoning → DEBATE renders the LIVE→resolved result.
- P1 #5-#7 and P2 → a follow-up UX wave after the P0 anchor + the two pending follow-ups
  (live-default UI, guru panel) land.

## Process correction (self)
Repeat miss against standing memory (feature-vs-ux-review-not-pipeline-qc, ship-grade-wave-close-
review): every wave close MUST include the rendered "what can't the user do here" pass with the
design skills, not only code/guardrail QC. Re-instated as a mandatory wave-close lens.
