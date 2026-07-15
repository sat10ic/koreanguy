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
- [x] T3.1 Setups screen: refusal funnel hero + gate-matrix cards + TAKEN/SKIPPED — verification pending main thread
- [x] T3.2 Regime screen: governor panel hero + expert accordion (breadth heatmap, rotation scatter) — verification pending main thread
- [x] T3.3 Journal screen: equity curve (R), expectancy matrix, MFE/MAE scatter, four-cohort strip — verification pending main thread
- [x] T3.4 Watchlist: heat gauge + sector donut + color-banded sortable table — verification pending main thread
- [x] T3.5 ChartDrawer → lightweight-charts (Codex C6; deps installed main-thread; browser QC PASSED main-thread: 7 canvases, legend, zero console errors) (kill hand-rolled SVG; zoom/volume fixes) — was #19
- [x] T3.6 AVWAP auto-anchor (Codex C5; swing-low strictness bug fixed in QC) (priority + anti-thrash guards) — was #30b
- [x] T3.7 Focus Center filter fix (focus_candidates pre-cap slice) + beginner/expert toggle made real (RegimeSummary flagship + InfoDot + ShowDetails + densityLabels; Setups/Watchlist Axis-D completed in W3.3) — was #29/#37
- [x] Regime history strip (Codex C16 ECharts XP + posture bands in RegimeSummary) — was #1
- [x] Batch 7 C17 poster type primitives (Archivo display/body fonts + poster primitives) — verification pending main thread
- [x] Batch 7 C18 Regime poster rebuild (POSTURE/SWING/TREND/BIAS editorial sections) — verification pending main thread
- [x] Batch 7 C19 poster grammar pass on Setups/Watchlist/Journal/Health — verification pending main thread
- [x] T3.8 Guided Daily Flow (six-step state-driven stepper, `/api/flow/today` + copyable order ticket)
- [x] T3.9 Position Coach (hold/trim/exit hand-holding, early/late-exit guards, expectancy teaching)

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
- [x] T3.1 Setups screen: refusal funnel hero + gate-matrix cards + TAKEN/SKIPPED — verification pending main thread
- [x] T3.2 Regime screen: governor panel hero + expert accordion (breadth heatmap, rotation scatter) — verification pending main thread
- [x] T3.3 Journal screen: equity curve (R), expectancy matrix, MFE/MAE scatter, four-cohort strip — verification pending main thread
- [x] T3.4 Watchlist: heat gauge + sector donut + color-banded sortable table — verification pending main thread
- [x] T3.5 ChartDrawer → lightweight-charts (Codex C6; deps installed main-thread; browser QC PASSED main-thread: 7 canvases, legend, zero console errors) (kill hand-rolled SVG; zoom/volume fixes) — was #19
- [x] T3.6 AVWAP auto-anchor (Codex C5; swing-low strictness bug fixed in QC) (priority + anti-thrash guards) — was #30b
- [x] T3.7 Focus Center filter fix (focus_candidates pre-cap slice) + beginner/expert toggle made real (RegimeSummary flagship + InfoDot + ShowDetails + densityLabels; Setups/Watchlist Axis-D completed in W3.3) — was #29/#37
- [x] Regime history strip (Codex C16 ECharts XP + posture bands in RegimeSummary) — was #1
- [x] Batch 7 C17 poster type primitives (Archivo display/body fonts + poster primitives) — verification pending main thread
- [x] Batch 7 C18 Regime poster rebuild (POSTURE/SWING/TREND/BIAS editorial sections) — verification pending main thread
- [x] Batch 7 C19 poster grammar pass on Setups/Watchlist/Journal/Health — verification pending main thread
- [x] T3.8 Guided Daily Flow (six-step state-driven stepper, `/api/flow/today` + copyable order ticket)
- [x] T3.9 Position Coach (hold/trim/exit hand-holding, early/late-exit guards, expectancy teaching)

## PHASE 4 — Telegram armed-list workflow
- [x] T4.1 Telegram armed-list workflow complete for W4: digest+armed list, FSM replay harness, dry-run send path, TAKE/SKIP reply capture, `/halt` kill-switch, and paper-mode criterion logged. Live entry pushes remain disabled by default. — was #21

## Later / unscheduled
- [x] T5.1 FUNDAMENTALS INGEST: W5 complete for available sources. Finstack smoke pull returned ROE/P-E/D-E/mcap for 5 NSE symbols (bank debt/equity nullable); `sources/fundamentals.py` now writes point-in-time quarterly rows to `symbol_fundamentals`, is registered in run-eod, and scanner growth reads through `fundamentals.growth_for()` before falling back to `symbol_quality`. W5.3 earnings-calendar chip skipped: no forward earnings-calendar source exists in current imports; only historical results-calendar/growth data is available.
- 2026-07-06: C5 verification hit the same sandbox blockers: Python fallback Access is denied; `npm.cmd run build` fails in Vite/esbuild while reading `../../../..` outside the workspace root. Implementation continued to C6.
- 2026-07-06: C6 dependency install deviation: `npm.cmd i echarts` failed with EACCES while requesting `https://registry.npmjs.org/echarts` and could not write npm cache logs under `C:\Users\satta\AppData\Local\npm-cache\_logs`. ChartDrawer migration continued using existing `lightweight-charts`; the lower TTM/RS pane remains local React/CSS instead of ECharts.
- 2026-07-06: C6 verification hit the same sandbox blockers: Python fallback Access is denied; `npm.cmd run build` fails in Vite/esbuild while reading `../../../..` outside the workspace root. Visual browser QC is pending main-thread review.
- 2026-07-06: C7 verification pending main thread. `npm.cmd run build` and direct esbuild hit sandbox Access denied while reading `../../../..`; `python` is not on PATH and fallback Python returns Access is denied.
- 2026-07-06: C8 verification pending main thread. Same sandbox blockers as C7.
- 2026-07-06: C9 verification pending main thread. Same sandbox blockers as C7.
- 2026-07-06: C10 verification pending main thread. Same sandbox blockers as C7.
- 2026-07-06: C14 implemented T4.1 slice 1 digest+armed only, no live push. Verification blocked in this sandbox: `python`/`py` are not on PATH and fallback Python returns Access is denied.
- 2026-07-06: C15 implemented mentor checklists (#17). Verification blocked in this sandbox: `python`/`py` are not on PATH, fallback Python returns Access is denied, and `npm.cmd run build` fails in Vite/esbuild while reading `../../../..`.
- 2026-07-06: C16 implemented Regime history strip (#1) in RegimeSummary. Verification blocked in this sandbox: fallback Python returns Access is denied, and `npm.cmd run build` fails in Vite/esbuild while reading `../../../..`; direct esbuild transform of touched frontend files passed.
- 2026-07-07: C17 implemented poster font system and primitives. Verification blocked in sandbox: `npm.cmd run build` fails in Vite/esbuild while reading `../../../..`.
- 2026-07-07: C18 rebuilt RegimeSummary as a four-section poster. Verification blocked in sandbox: `npm.cmd run build` fails in Vite/esbuild while reading `../../../..`; direct esbuild transform of RegimeSummary passed.
- 2026-07-07: C19 applied poster grammar headers to Setups, Watchlist, Journal, and Health. Verification blocked in sandbox: `npm.cmd run build` fails in Vite/esbuild while reading `../../../..`; direct esbuild transform of all touched JSX files passed.

## CODEX C-queue status
- [x] C1 Cheap-edge batch implemented.
- [x] C2 EP neglected-base fix implemented.
- [x] C3 Journal capture plumbing implemented.
- [x] C4 Adaptive exits + portfolio heat implemented.
- [x] C5 AVWAP auto-anchor implemented.
- [x] C6 ChartDrawer migration implemented; ECharts + lightweight-charts installed main-thread (Codex npm was network-blocked); build green.
- [x] C7 Setups Phase 3 panel implemented; verification pending main thread.
- [x] C8 Regime Phase 3 panel implemented; verification pending main thread.
- [x] C9 Journal Phase 3 panel and /api/expectancy implemented; verification pending main thread.
- [x] C10 Watchlist Phase 3 heat row and sortable table implemented; verification pending main thread.
- [x] C14 Telegram digest generation and armed_list persistence implemented; verification pending main thread.
- [x] C15 Mentor checklists implemented; verification blocked in sandbox pending main thread.
- [x] C16 Regime history strip implemented; verification blocked in sandbox pending main thread.
- [x] C17 Type system + poster primitives implemented; verification blocked in sandbox pending main thread.
- [x] C18 Regime poster rebuild implemented; verification blocked in sandbox pending main thread.
- [x] C19 Poster grammar pass implemented; verification blocked in sandbox pending main thread.

## Retired v1 board
v1 items #1-28 delivered (see git history); #29-37 superseded by the mapping above.
