# GEMINI HANDOFF QUEUE — execute strictly in this order (2026-07-12)

## Codex end-to-end repair checkpoint (2026-07-14)

`HANDOFF_CODEX_END_TO_END_REACTOR_HORIZON_2026-07-14.md` is the latest verified
runtime handoff. It covers the Gemini end-to-end review, Reactor activity
analogue, Horizon research governance, scanner count repair and final test
evidence. Read it before starting another implementation wave.

## Reactor research checkpoint (2026-07-14)

`HANDOFF_REACTOR_REVERSE_ENGINEERING_2026-07-14.md` records the completed
all-date official-bhavcopy formula-recovery search. It is a research checkpoint,
not an additional UI execution wave. Do not label the resulting approximation as
the proprietary Reactor Scale; exact recovery is blocked on the publisher's
formula or equivalent order/tick-level footprint input.

## Canonical continuation from 2026-07-13

The single next execution queue is
`HANDOFF_GEMINI_BEGINNER_MANAS_SYSTEM_REBUILD_2026-07-13.md`. It consolidates the
remaining beginner workflow, chart/debate, positions/journal and Alpha work; its
Wave 7 is bound to `../HORIZON_INTEGRATION_REQUIREMENT.md`.

The RAIN/STALLION correction is bound through
`../DECISION_LEARNING_FAILURE_AUDIT_2026-07-13.md`. Gemini may not close the
scanner/debate/learning waves with a prompt-only patch: the two-pass observer,
user-thesis record, all-decision outcome resolution and verdict-aware learning tests
must pass.

The canonical Debate user output and API responsibility split are bound through
`../DEBATE_ANALYSIS_OUTPUT_CONTRACT.md`. Gemini may not close the Debate rebuild with
only votes, conviction, `TAKE`/`SKIP` or a free-prose narrative. The chart thesis,
trigger, structural invalidation, expected sequence, contradiction, relative
behaviour, provenance and separately server-validated execution plan must render.

The older numbered queue below remains implementation history and source detail.
Pending items #8 and #9 are subsumed by the canonical continuation rather than run as
competing standalone rebuilds.

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
| 11 | HANDOFF_GEMINI_ux_defects_batch.md | shortlist verdict-contradiction, journal delete, positions debug/freshness, scanner offscreen (+fix8 slow presets), date dead-ends, URL routing, trade-plan chart/persist/log | DONE |
| 12 | HANDOFF_GEMINI_regime_history_hmm.md | replay regime history over 5y + fix HMM persistence/warming status | DONE (see _COMPLETED.md) |
| 13 | guided-system punch-list (A-D) | 409 guard + StatusBadge wiring + TRADE_PLAN header + order_ticket routing | **DONE + committed `0c0df56d`** (Sonnet build, maintainer caught+fixed async-guard-never-registered; live-DOM verified). REMAINING from GLM §6: Alpha/Debate/Shortlist legend + cross-badges + ALPHA row actions → next batch (#13b) |
| 14 | HANDOFF_GEMINI_v5_token_migration.md | ChartDrawer v5 restyle + single-theme cleanup | **DONE** (see _COMPLETED.md) — `desk_gate.py` 3/3 PASS, 0 hex findings, chart canvas LIGHT, tokens.css retired |
| 15 | HANDOFF_GEMINI_dewonk_BCD.md | de-wonk recovery (Waves B/C/D) | DONE (see _COMPLETED.md) |

UX ledgers driving 7-13: `manas_os/design/UX_AUDIT_FULL.md` (comprehensive, ranked) + `UX_GAP_AUDIT.md`
+ `GUIDED_SYSTEM_DESIGN.md` (GLM inspection §6 punch-list). Session handoffs:
`SESSION_HANDOFF_2026-07-12.md` + `SESSION_HANDOFF_UPDATE_2.md`.
Priority order next session: **13 (finish guided-system: 409 fix + punch-list) → 11 (defects) → 8 → 9.**

Session UPDATE-3 (2026-07-12, Fable): #13 (`0c0df56d`) + #13b legend/cross-badges/ALPHA
actions (`fce0b176`) DONE+committed → guided system complete. `scripts/desk_gate.py` added
(`b003d492`), baseline 53 findings = #14 debt. **UNFINISHED: UX craft audit subagent hit
session limit, wrote no file — RE-RUN first next session** (see `SESSION_HANDOFF_UPDATE_3.md`).
Then #14 → #11 → #12-QC → #8 → #9. No-subagent rule LIFTED; caveman replies ordered.

#14 (v5 token migration) DONE — `HANDOFF_GEMINI_v5_token_migration_COMPLETED.md`. UX-craft
audit re-run written: `UX_CRAFT_AUDIT_2026-07-12.md` (VERDICT: CONDITIONAL, 55 defects).
**#11 focused batch COMPLETED** (self-executed, no subagent): #31 reduced-motion guards,
#28 keyboard shortcuts, #19 debate pipeline note (already done), #23 positions origin-thesis
link, #49 no-thesis run-debate button, #25 journal add-trade + inline edit. Review:
`HANDOFF_GEMINI_ux_defects_focused_COMPLETED.md`. Gate 3/3 PASS, vitest 37 pass, build clean.
Manual lesson entry deferred (no POST /api/desk/lessons route).

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

## Leadership + choppy-tape + DII wave (added 2026-07-14, shadow-first)
Sequence after the SMF + de-wonk queue. All validate via promotion_gates / replay before ANY
gate/sizing influence (verified gaps: no RS-line, no prior-leg, aggregate-only FII/DII, no MF holdings):
- HANDOFF_GEMINI_rsline_priorleg.md — RS-line-new-high-before-price + prior-momentum-leg leadership features (shadow evidence -> gates)
- HANDOFF_GEMINI_breakout_climate_throttle.md — BO-follow-through "climate" throttles governor (BREADTH_ENRICHMENT Tier-1; replay-A/B gated; tighten-only)
- HANDOFF_GEMINI_dii_footprint.md — FII/DII divergence overlay + resilience-under-distribution + (staged) monthly MF-holdings ingest; direction-neutral, lag-labelled
