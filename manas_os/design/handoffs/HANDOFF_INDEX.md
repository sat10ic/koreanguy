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
| 7 | HANDOFF_GEMINI_search_live_analysis.md | **P0 UX** — universal search → on-demand analyze → LIVE debate stream + progress | BUILT + committed (`6b670f52`/`9971bde7`); ⚠ OPEN: `test_debate_push_idempotency` 409-in-flight FAILS; live path not QC'd |
| 8 | HANDOFF_GEMINI_live_default_ui.md | finish live stage-2 desk frontend (live-tick default) | pending |
| 9 | HANDOFF_GEMINI_guru_tradeplan_panel.md | guru checklist panel on TRADE PLAN + DEBATE | pending |

| 10-DESIGN | HANDOFF_GLM_guided_system_DESIGN.md | GLM inspection of the built system (not a from-scratch design) — `GUIDED_SYSTEM_DESIGN.md` + contrast proof | DONE (excellent; drives the punch-list below) |
| 10 | HANDOFF_GEMINI_guided_system.md | **P0 CENTERPIECE** — render /api/flow/today guided rail + per-tab headers + legend + status chips | BUILT + committed; 3 a11y contrast P0s FIXED by maintainer; ⚠ PUNCH-LIST → #13 |
| 11 | HANDOFF_GEMINI_ux_defects_batch.md | shortlist verdict-contradiction, journal delete, positions debug/freshness, scanner offscreen (+fix8 slow presets), date dead-ends, URL routing, trade-plan chart/persist/log | pending |
| 12 | HANDOFF_GEMINI_regime_history_hmm.md | replay regime history over 5y + fix HMM persistence/warming status | BUILT (regime_hmm.py) + committed; ⚠ not live-QC'd (persists states or WARMING?) |
| 13 | guided-system punch-list (A-D) | 409 guard + StatusBadge wiring + TRADE_PLAN header + order_ticket routing | **DONE + committed `0c0df56d`** (Sonnet build, maintainer caught+fixed async-guard-never-registered; live-DOM verified). REMAINING from GLM §6: Alpha/Debate/Shortlist legend + cross-badges + ALPHA row actions → next batch (#13b) |
| 14 | (WRITE THIS) ChartDrawer v5 restyle + single-theme cleanup | `scripts/desk_gate.py` (new mechanical wave-gate: hardcode-lint + WCAG contrast + locked-file diff, adopted from plugin87/ux-ui-agent-skills doctrine) found 47 raw dark-theme hex in `desk/src/ChartDrawer.jsx` — the exact "legacy black island in the light shell" the user LOCKED as a release blocker (AESTHETIC_BAR 2026-07-11 §1), and it mounts on 5 tabs. Also: legacy `desk/src/tokens.css` is a second live theme source (imported in main.jsx) — migrate ChartDrawer + MarketTab(3) + viz.js(3) + DebateTab.v5.css(1) to v5 tokens, then retire tokens.css. Done-test: `python scripts/desk_gate.py` prints 3/3 PASS. | pending — after #13 |

UX ledgers driving 7-13: `manas_os/design/UX_AUDIT_FULL.md` (comprehensive, ranked) + `UX_GAP_AUDIT.md`
+ `GUIDED_SYSTEM_DESIGN.md` (GLM inspection §6 punch-list). Session handoffs:
`SESSION_HANDOFF_2026-07-12.md` + `SESSION_HANDOFF_UPDATE_2.md`.
Priority order next session: **13 (finish guided-system: 409 fix + punch-list) → 11 (defects) → 8 → 9.**

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
- **`python scripts/desk_gate.py` on every desk wave** (mechanical gate: raw-hex lint vs v5
  tokens, WCAG contrast on locked token pairs, money-math zero-diff). Known baseline debt =
  #14's 54 findings; a wave may not ADD findings, and #14 closes them to 3/3 PASS. Mechanical
  gates complement — never replace — the rendered DOM/browser QC pass ("gates don't prove
  pixels": render and look, both the maintainer and the audit doctrine require it).
