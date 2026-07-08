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
- [x] Mentor checklists (Manas Arora) — was #17
- FII/DII flow overlay, insider-cluster boost (after T2.1), analog matching (expert, descriptive, n≥500)

## Execution log
- 2026-07-07: WAVE 5 complete for current source availability. W5.1 Finstack MCP smoke proved real fundamentals for five NSE symbols (RELIANCE/TCS/INFY/HDFCBANK/SBIN: P/E, ROE, market cap, debt/equity nullable for banks) and yfinance-backed `manas_os/sources/fundamentals.py` now writes additive point-in-time quarterly `symbol_fundamentals` rows keyed by symbol/report_date/as_of, with `pipeline_runs` logging and run-eod registration after ChartsMaze scanner quality. Real local DB smoke for 2026-07-07 wrote 25 quarterly rows across the 5 symbols and logged `symbols=5 rows=25 failures=0`. W5.2 scanner growth now uses `fundamentals.growth_for(symbol, as_of)` first and falls back to compact `symbol_quality`, preserving missing-fundamentals behavior. W5.3 skipped with source note: no forward earnings-calendar source exists in current imports (`ADVISOR_SPEC.md` says true future earnings calendar is absent; existing results-calendar data is historical fundamentals only), so no Watchlist/advisor future-event chip was fabricated. Verification: targeted fundamentals/scanner tests 12 passed; full `python -m pytest manas_os/tests -q` 213 passed; `npm run build` clean with only the existing large chunk warning.
- 2026-07-07: WAVE 4 complete. W4.1 added `alerts/live_fsm.py` with a replayable IDLE/ARMED/TRIGGERED/ALERTED/CONFIRM_PENDING/CONFIRMED-or-EXPIRED state machine, 25-minute TTL, paper_mode=1 default, persisted transitions, and zero-new-transition duplicate replay behavior. W4.2 extended `alerts/telegram_engine.py` with single-message digest rendering, `telegram:` config keys in `config.example.yaml`, dry-run default, injectable sender for tests, and failure-safe `pipeline_runs` fail rows on send errors. W4.3 added `alerts/replies.py`: TAKE/SKIP replies reuse the existing `setup_decisions`/`journal_trades` contract, push dedupe caps entry pushes at 1/symbol/day, and `/halt` blocks entry pushes while `exit_alerts_allowed()` remains true. W4.4 paper-mode graduation criterion written to `design/LEARNINGS.md`. Verification: targeted Telegram tests 8 passed; full `python -m pytest manas_os/tests -q` 208 passed; `npm run build` clean with only the existing large chunk warning.
- 2026-07-07: WAVE 3 complete. W3.1 `/api/flow/today` now implements the six T3.8 steps: data, regime, positions, setups review, order_ticket, done. Setups review is gated by logged TAKEN/SKIPPED decisions; a TAKEN setup unlocks a backend-authored copyable ticket (`BUY ... | QTY ... | STOP ...`) from persisted candidate/decision fields; NO_TRADE skips ticket explicitly; Friday weekly review remains in done detail. W3.2 Position Coach verified against CODEX_HANDOFF C11-C13: `/api/positions/{trade_id}/coach` shape, early-exit 409 guard + Journal retry reasons, mistake-tag persistence, first_exit_flag_date overdue banner and close/reset behavior. W3.3 Axis D already completed. Verification: targeted W3 tests 14 passed; full `python -m pytest manas_os/tests -q` 201 passed; `npm run build` clean with only the existing large chunk warning.
- 2026-07-07: W3.3 completed Beginner/Expert Axis D for Setups + Watchlist. Setups shared CandidateCard now renders beginner readiness/plain-read/decision plan without expert-only raw diagnostics; Expert restores full plan math, expectancy block, raw evidence values, and near-misses. Watchlist now imports useDensity and uses one table with BEGINNER_COLS (SYM, trade health, action) vs EXPERT_COLS appending RS, ADR%, dlv_z, dist-pivot, exit-state, trail, days, open R. Safety/stale/Fyers banners, heat row, and position coach cards remain identical across modes. Verification: pytest 200 passed; frontend build clean; Playwright snapshots showed Setups beginner plan only vs expert full math/near-misses, and Watchlist expert header `SYM trade health action RS ADR% dlv_z dist-pivot exit-state trail days open R` vs beginner header `SYM trade health action`. Only console error was favicon.ico 404.
- 2026-07-07: WAVE 0 verified in main-thread sandbox (Python 3.12 on PATH, node 24/npm 11.6 — the sandbox blockers logged for C1–C19 do NOT reproduce here). Baseline pytest 182 green, `npm run build` green. D1–D5 all landed (evidence: SetupsFunnelCard iterates all by_gate desc; RegimeSummary uses rank/rank_of; gate dots title-attr carries gateEvidence; Journal TradeLogTable has clean 12-col grid DATE|SYM|SETUP|R|MISTAKE|RESULT|ACTIONS, no chip cluster; refused cohort scoped to last-20-session subquery in api/app.py:1899–1908). FOCUS tab exists (App.jsx:6,26,192; FocusPage.jsx) with base_age/days_since_listing already persisted. W0.2 FIX: `circuit_state` was missing from the candidate payload — added one-writer server-side attach in scanner/candidates.py:load_persisted_candidates (latest circuit_bands.band_pct as-of scan_date, null when no band), +2 tests in test_scanner_candidates.py. ADVISOR module conforms to ADVISOR_SPEC.md: 6 mock-only tests green, guard rejects novel numbers + imperatives, run() no-ops without api_key, /api/advisor/today + /note-action endpoints live, AdvisorStrip muted with the advisory chip and beginner-collapsed/expert-expanded. ChartDrawer (Screen 6) has all spec elements: 3-tab preset switch (SETUP ema10/21/50, TREND ema50, EXIT ema15/21), lightweight-charts candles+vol, AVWAP+anchor reason, buy-zone band + stop line + entry/exit arrows + pocket-pivot markers, one-line ChartLegend, RS+TTM LowerPane. Final W0 counts: pytest 184 passed (182 baseline + 2 new), build clean.
- 2026-07-06: C1 verification could not be completed in this sandbox. `python` is not on PATH and the handoff fallback `C:\Users\satta\AppData\Local\Programs\Python\Python312\python.exe` returns Access is denied. `npm.cmd run build` starts Vite but esbuild cannot resolve `manas_os/frontend/vite.config.js` because reading `../../../..` is denied outside the workspace root. Implementation continued to C2; this is an environment blocker, not a skipped code task.
- 2026-07-06: C2 verification hit the same sandbox blockers: Python fallback Access is denied; `npm.cmd run build` fails in Vite/esbuild while reading `../../../..` outside the workspace root. Implementation continued to C3.
- 2026-07-06: C3 verification hit the same sandbox blockers: Python fallback Access is denied; `npm.cmd run build` fails in Vite/esbuild while reading `../../../..` outside the workspace root. Implementation continued to C4.
- 2026-07-06: C4 verification hit the same sandbox blockers: Python fallback Access is denied; `npm.cmd run build` fails in Vite/esbuild while reading `../../../..` outside the workspace root. Implementation continued to C5.
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
