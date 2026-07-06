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
- [x] T1.4 Rewire `scanner/candidates.py` (Opus hand-build: cascade + ordinal rank + one-opinion + OHLCV shortlist) (cascade + ordinal rank; kill additive score + 300-symbol union; one-opinion exit-state join; **detectors from OHLCV point-in-time per LEARNINGS finding**) — was #33/#34
- [x] T1.5 Refusal ledger + `/api/setups/refusals` + governor cap wired into /api/setups
- [x] T1.6 CHECKPOINT PASSED: fill-checked replay — pullback×SELECTIVE +0.44R median, 3.6% stops, 30% hit (n=73). Caveat on near-miss baseline logged in LEARNINGS. Phase 2 open.

## PHASE 2 — Edge modules + journal moat
- [x] T2.1 `sources/disclosures.py` (Codex parallel lane, QC'd green) (order-wins/announcements/bulk-deals/insider/circuit-bands/episodic-pivot → tables)
- [x] T2.2 PEAD study DONE (liquidity-decile; catalyst leg proven load-bearing — see LEARNINGS). EP neglected-base fix landed via Codex C2. Catalyst-conditioned sample accrues via journal.
- [x] T2.3a CAPTURE side done (Codex C3, QC'd): /api/setups/decision + setup_decisions snapshot + TAKEN/SKIPPED buttons. Expectancy math (T2.3b) DONE main-thread: scanner/expectancy.py (system+personal loops, k=25 shrinkage, trust ladder, chip_for) + pipeline stage. Was: TAKEN/SKIPPED capture + snapshot, MFE/MAE, `scanner/expectancy.py` + shrinkage, probation chips, LEARNINGS.md — was #36
- [x] T2.4 Adaptive exits (Codex C4, QC'd: trail_plan/two_strike/heat endpoint) (3 modes + two-strike + +1R breakeven/book-⅓) + portfolio heat endpoint + trailing replay validation
- [x] T2.5 Cheap-edge batch (Codex C1, QC'd): sector-adjusted momentum tiebreak, nearness/stacking/template chips, ADR% surface, range-expansion breakout confirm (breakout-day TR >= 1.2x ATR14 — else 'narrow-range breakout' caution chip; idea validated vs Elicherla01/breakoutscanner, repo itself not integrated: yfinance/Donchian duplicate of near-pivot) — was #31/#32

## PHASE 3 — Visual frontend rebuild (ECharts panels; shell kept)
- [ ] T3.1 Setups screen: refusal funnel hero + gate-matrix cards + TAKEN/SKIPPED
- [ ] T3.2 Regime screen: governor panel hero + expert accordion (breadth heatmap, rotation scatter)
- [ ] T3.3 Journal screen: equity curve (R), expectancy matrix, MFE/MAE scatter, four-cohort strip
- [ ] T3.4 Watchlist: heat gauge + sector donut + color-banded sortable table
- [x] T3.5 ChartDrawer → lightweight-charts (Codex C6; deps installed main-thread; browser QC pending) (kill hand-rolled SVG; zoom/volume fixes) — was #19
- [x] T3.6 AVWAP auto-anchor (Codex C5; swing-low strictness bug fixed in QC) (priority + anti-thrash guards) — was #30b
- [ ] T3.7 Focus Center filter fix + beginner/expert real enforcement (BEGINNER_EXPERT_SPEC) — was #29/#37
- [ ] T3.8 Guided Daily Flow (state-driven stepper, `/api/flow/today`)
- [ ] T3.9 Position Coach (hold/trim/exit hand-holding, early/late-exit guards, expectancy teaching)

## PHASE 4 — Telegram armed-list workflow
- [ ] T4.1 `alerts/telegram_engine.py` (digest/armed/push FSM per LIVE_LOOP_FABLE.md; replay-harness-first; paper month) — was #21

## Later / unscheduled
- [ ] Mentor checklists (Manas Arora) — was #17
- FII/DII flow overlay, insider-cluster boost (after T2.1), analog matching (expert, descriptive, n≥500)

## Execution log
- 2026-07-06: C1 verification could not be completed in this sandbox. `python` is not on PATH and the handoff fallback `C:\Users\satta\AppData\Local\Programs\Python\Python312\python.exe` returns Access is denied. `npm.cmd run build` starts Vite but esbuild cannot resolve `manas_os/frontend/vite.config.js` because reading `../../../..` is denied outside the workspace root. Implementation continued to C2; this is an environment blocker, not a skipped code task.
- 2026-07-06: C2 verification hit the same sandbox blockers: Python fallback Access is denied; `npm.cmd run build` fails in Vite/esbuild while reading `../../../..` outside the workspace root. Implementation continued to C3.
- 2026-07-06: C3 verification hit the same sandbox blockers: Python fallback Access is denied; `npm.cmd run build` fails in Vite/esbuild while reading `../../../..` outside the workspace root. Implementation continued to C4.
- 2026-07-06: C4 verification hit the same sandbox blockers: Python fallback Access is denied; `npm.cmd run build` fails in Vite/esbuild while reading `../../../..` outside the workspace root. Implementation continued to C5.
- 2026-07-06: C5 verification hit the same sandbox blockers: Python fallback Access is denied; `npm.cmd run build` fails in Vite/esbuild while reading `../../../..` outside the workspace root. Implementation continued to C6.
- 2026-07-06: C6 dependency install deviation: `npm.cmd i echarts` failed with EACCES while requesting `https://registry.npmjs.org/echarts` and could not write npm cache logs under `C:\Users\satta\AppData\Local\npm-cache\_logs`. ChartDrawer migration continued using existing `lightweight-charts`; the lower TTM/RS pane remains local React/CSS instead of ECharts.
- 2026-07-06: C6 verification hit the same sandbox blockers: Python fallback Access is denied; `npm.cmd run build` fails in Vite/esbuild while reading `../../../..` outside the workspace root. Visual browser QC is pending main-thread review.

## CODEX C-queue status
- [x] C1 Cheap-edge batch implemented.
- [x] C2 EP neglected-base fix implemented.
- [x] C3 Journal capture plumbing implemented.
- [x] C4 Adaptive exits + portfolio heat implemented.
- [x] C5 AVWAP auto-anchor implemented.
- [x] C6 ChartDrawer migration implemented; ECharts install blocked as logged above.

## Retired v1 board
v1 items #1-28 delivered (see git history); #29-37 superseded by the mapping above.
