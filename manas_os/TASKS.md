# MANAS 2.0 — Task Board (mirrors the approved plan)

Canonical spec: `C:\Users\satta\.claude\plans\c-users-satta-downloads-manas-os-v2-md-woolly-peacock.md`
(LOCKED thresholds live there — use verbatim). Research: `manas_os/design/Feedback/`.
Old v1 task numbering (#1-37) is retired; mapping noted where relevant.

Status: [x] done · [~] in progress · [ ] pending

## PHASE 0 — Truth & Measurement
- [x] T0.1 Data-integrity clamps (Codex build, Opus QC; fixtures corrected) — was #35
- [x] T0.2 Replay/backtest harness (Opus QC: fixed __init__ shadowing, rewrote tests to pluggable-generator boundary). CRITICAL finding in LEARNINGS.md: legacy generator has no screener history → T1.4 cascade must detect from OHLCV point-in-time.

## PHASE 1 — The Gate (refusal engine)
- [x] T1.1 `scanner/gates.py` deterministic cascade (hand-written by Opus; 19 tests)
- [x] T1.2 `risk/plan.py` single writer of stop/size/R:R (AGGRESSIVE default profile; hand-written by Opus)
- [x] T1.3 `regime/governor.py` regime as law (hand-written by Opus) — was #33
- [ ] T1.4 Rewire `scanner/candidates.py` (cascade + ordinal rank; kill additive score + 300-symbol union; one-opinion exit-state join; **detectors from OHLCV point-in-time per LEARNINGS finding**) — was #33/#34
- [ ] T1.5 Refusal ledger table + `/api/setups/refusals`
- [ ] T1.6 Validation checkpoint: replay A/B legacy-vs-cascade → LEARNINGS.md (GATE to Phase 2)

## PHASE 2 — Edge modules + journal moat
- [ ] T2.1 `sources/disclosures.py` (order-wins/announcements/bulk-deals/insider/circuit-bands/episodic-pivot → tables)
- [ ] T2.2 PEAD anchor cohort + mcap-decile backtest (+ EP neglected-base drift fix — was #30a)
- [ ] T2.3 Journal-as-loop: TAKEN/SKIPPED capture + snapshot, MFE/MAE, `scanner/expectancy.py` + shrinkage, probation chips, LEARNINGS.md — was #36
- [ ] T2.4 Adaptive exits (3 modes + two-strike + +1R breakeven/book-⅓) + portfolio heat endpoint + trailing replay validation
- [ ] T2.5 Cheap-edge batch: sector-adjusted momentum tiebreak, nearness/stacking/template chips, ADR% surface — was #31/#32

## PHASE 3 — Visual frontend rebuild (ECharts panels; shell kept)
- [ ] T3.1 Setups screen: refusal funnel hero + gate-matrix cards + TAKEN/SKIPPED
- [ ] T3.2 Regime screen: governor panel hero + expert accordion (breadth heatmap, rotation scatter)
- [ ] T3.3 Journal screen: equity curve (R), expectancy matrix, MFE/MAE scatter, four-cohort strip
- [ ] T3.4 Watchlist: heat gauge + sector donut + color-banded sortable table
- [ ] T3.5 ChartDrawer → lightweight-charts (kill hand-rolled SVG; zoom/volume fixes) — was #19
- [ ] T3.6 AVWAP auto-anchor rework (priority + anti-thrash guards) — was #30b
- [ ] T3.7 Focus Center filter fix + beginner/expert real enforcement (BEGINNER_EXPERT_SPEC) — was #29/#37
- [ ] T3.8 Guided Daily Flow (state-driven stepper, `/api/flow/today`)
- [ ] T3.9 Position Coach (hold/trim/exit hand-holding, early/late-exit guards, expectancy teaching)

## PHASE 4 — Telegram armed-list workflow
- [ ] T4.1 `alerts/telegram_engine.py` (digest/armed/push FSM per LIVE_LOOP_FABLE.md; replay-harness-first; paper month) — was #21

## Later / unscheduled
- [ ] Mentor checklists (Manas Arora) — was #17
- FII/DII flow overlay, insider-cluster boost (after T2.1), analog matching (expert, descriptive, n≥500)

## Retired v1 board
v1 items #1-28 delivered (see git history); #29-37 superseded by the mapping above.
