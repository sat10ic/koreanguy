# GEMINI HANDOFF QUEUE — execute strictly in this order (2026-07-12)

Shared-file collision rule: several handoffs touch `api/app.py` / desk files, so run ONE at a
time, in this order. After each: write its `_COMPLETED.md`, do NOT git commit — the maintainer
QCs and commits before you start the next.

| # | File | Scope | Status |
|---|---|---|---|
| 0a | HANDOFF_GEMINI_UI7_hardening.md | UI-7 close-out | DONE (awaiting maintainer QC) |
| 0b | HANDOFF_GEMINI_outcome_resolver.md | alpha outcome resolver | DONE (awaiting maintainer QC) |
| 1 | HANDOFF_GEMINI_breadth_tier0.md | breadth analytics → MARKET live cards + DEBATE context | DONE (awaiting maintainer QC) |
| 2 | HANDOFF_GEMINI_backend_fields_batch.md | small flagged backend fields + small bug fixes | DONE (see _COMPLETED.md) |
| 3 | HANDOFF_GEMINI_live_stage2.md | desk live-default + armed-zone schema | DONE partial desk UI (see _COMPLETED.md) |
| 4 | HANDOFF_GEMINI_alpha_memory_gates.md | analogue retrieval + anti-overfit battery + leakage audit + experiment KB | DONE (see _COMPLETED.md) |
| 5 | HANDOFF_GEMINI_fyers_intraday_backfill.md | tiered intraday backfill run + coverage UI | BLOCKED auth (see _COMPLETED.md) |
| 6 | HANDOFF_GEMINI_guru_checklists.md | configurable mentor checklists (Arora first) | DONE API/seed; panel = #9 |
| 7 | HANDOFF_GEMINI_search_live_analysis.md | **P0 UX** — universal search → on-demand analyze → LIVE debate stream + progress | pending (PRIORITY) |
| 8 | HANDOFF_GEMINI_live_default_ui.md | finish live stage-2 desk frontend (live-tick default) | pending |
| 9 | HANDOFF_GEMINI_guru_tradeplan_panel.md | guru checklist panel on TRADE PLAN + DEBATE | pending |

| 10 | HANDOFF_GEMINI_guided_system.md | **P0 CENTERPIECE** — render /api/flow/today guided rail + per-tab purpose headers + Alpha/Debate/Shortlist legend + status-chip vocabulary | pending (HIGHEST) |
| 11 | HANDOFF_GEMINI_ux_defects_batch.md | shortlist verdict-contradiction, journal delete, positions debug/freshness, scanner offscreen, date dead-ends, URL routing, trade-plan chart/persist/log | pending |
| 12 | HANDOFF_GEMINI_regime_history_hmm.md | replay regime history over 5y + fix HMM persistence/warming status | pending |

UX ledgers driving 7-12: `manas_os/design/UX_AUDIT_FULL.md` (comprehensive, ranked) + `UX_GAP_AUDIT.md`.
Priority order: **10 (guided system) → 7 (search+live-debate) → 11 (defects) → 12 (HMM data) → 8 → 9.**

Standing rules for every handoff (repeat-binding):
- Do NOT git commit. Write `<handoff>_COMPLETED.md` with files changed, test results, wiring
  notes, assumptions, flagged uncertainties.
- Money-math LOCKED: UI/analytics never compute stop/target/qty/risk — server/persisted plan
  values verbatim. Deterministic risk final. Paper gate on Telegram stays.
- Real data only; honest empty/"needs ingest"/PENDING states; no synthetic series; no new chart
  libs (plain SVG); `.v5`-scoped CSS with tokens only; a11y AA; reduced-motion.
- Additive DB migrations only (guarded CREATE/ALTER); point-in-time discipline; append-only for
  events/decisions/outcomes.
- Never print the rupee glyph to a Windows console — use "Rs". Never log/commit secrets
  (config.yaml is gitignored).
- `python -m pytest manas_os/tests -q` green (known allowed fail: sector-downside baseline;
  use an absolute python path) + `cd manas_os/desk && npm run build` + `npx vitest run` when
  desk files are touched.
