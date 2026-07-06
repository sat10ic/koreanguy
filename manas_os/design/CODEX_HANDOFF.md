# CODEX HANDOFF — Manas 2.0 execution queue (zero-judgment edition)

Rules: execute tasks IN ORDER (C1→C6). Every rule/threshold/test below is FINAL — do not
re-decide, do not "improve". If something is impossible as written, STOP that task, note it
in TASKS.md, continue to the next. After EVERY task: `python -m pytest manas_os/tests -q`
(baseline 139+ green, never regress) and `cd manas_os/frontend && npm run build`, then tick
the task here AND in TASKS.md. Windows: never print the rupee glyph to console (cp1252) —
'Rs' in prints; the glyph is fine inside code/JSON strings. Python fallback:
C:\Users\satta\AppData\Local\Programs\Python\Python312\python.exe.
Do NOT touch: backtest/replay.py, scanner/gates.py, risk/plan.py, regime/governor.py
(owned by the main thread this wave) — except where a task below names them explicitly.

---
## C1 — Cheap-edge batch (plan T2.5)  [x]

### C1.1 Range-expansion breakout confirm
File: `manas_os/scanner/gates.py` — EDIT ONLY `gate_participation` (allowed exception).
Add after the existing volume check, still inside `if breakout_day_entry:`:
```python
# range-expansion confirm: a real breakout bar EXPANDS. TR of the last bar
# must be >= 1.2 x ATR14, else flag (not refuse) as narrow-range breakout.
```
Compute `tr = max(high-low, abs(high-prev_close), abs(low-prev_close))` for the last bar and
`atr14` = mean of the last 14 TRs (reuse the pattern in `risk/plan.py:_atr`). If
`tr < 1.2*atr14`: DO NOT fail the gate — add `"narrow_range_breakout": True` into the
returned evidence kwargs (pass path). Also expose a module-level helper
`range_expansion(bars) -> dict {tr, atr14, expanded: bool}` for reuse.
TEST (add to `manas_os/tests/test_risk_gates_governor.py`): fixture with 20 flat bars
(high=low+1) then a last bar with high=low+4 → `range_expansion(bars)["expanded"] is True`;
last bar high=low+0.5 → expanded False and `gate_participation(bars, True)` still passes
with `evidence["narrow_range_breakout"] is True`.

### C1.2 ADR% surfaced
File: `manas_os/api/app.py` — the watchlist items builder (find where each watchlist row gets
`timing`): `symbol_timing` already returns `adr`. Ensure the row payload includes `"adr": t["adr"]`
top-level (not only nested in timing). File: `manas_os/frontend/src/components/WatchlistPage.jsx` —
add a sortable "ADR%" column rendering `item.adr?.toFixed(1) + '%'`, muted style, header title
attribute "Average daily range — how much this name moves in a day. Bigger = more swing per unit
time but wider stops." No new colors.
TEST: extend `test_symbol_watchlist_api.py::test_watchlist_add_list_delete_contract` — after add,
`payload["items"][0]["adr"] is not None`.

### C1.3 Stop-vs-ADR sanity chip
File: `manas_os/scanner/candidates.py`, inside `candidate_for_symbol` AFTER `plan_result` passes:
if `timing.get("adr")` and `plan_result["stop_pct"] > 0.75 * timing["adr"] * 1.0` — append
evidence `{"filter": "wide-stop-vs-ADR", "value": f"stop {plan_result['stop_pct']:.1f}% vs ADR {timing['adr']:.1f}%"}`.
(Note: timing['adr'] is already in %, no further scaling.)
TEST: none required beyond suite staying green (display chip only).

---
## C2 — EP neglected-base fix (plan T2.2a, source drift)  [x]

File: `manas_os/engine/eod_detectors.py`, function `earnings_power`.
REPLACE the current `neglected_base` logic (`prior_high` breakout test) with PRE-GAP QUIETNESS:
```python
# 'Neglected' = the stock was QUIET BEFORE the gap (base/consolidation), not
# already running. Test the 25 bars BEFORE the gap day:
pre = bars[-26:-1]
pre_closes = [c for c in (_num(b.get("close")) for b in pre) if c]
pre_highs  = [h for h in (_num(b.get("high"))  for b in pre) if h]
pre_lows   = [l for l in (_num(b.get("low"))   for b in pre) if l]
if len(pre_closes) < 20:
    return None
band_pct   = (max(pre_highs) - min(pre_lows)) / pre_closes[-1] * 100.0
drift_pct  = abs(pre_closes[-1] - pre_closes[0]) / pre_closes[0] * 100.0
neglected_base = band_pct <= 25.0 and drift_pct <= 10.0
```
Keep every other EP condition unchanged (growth checks, ASM, mcap>300, gap>0,
gap+range<=12). Update the detail string to include `f"pre-gap band {band_pct:.0f}%, drift {drift_pct:.0f}%"`.
TEST (edit `manas_os/tests/test_eod_detectors.py` EP tests if present, else add):
(a) 25 flat bars at 100 (band ~2%, drift 0) then a gap-up bar open=106, close=107, high=108,
low=105 with quality {eps_qoq:35, eps_yoy:40, sales_yoy:35, market_cap_cr:1000} → returns dict.
(b) same but pre-gap bars ramp 100→140 (drift 40%) → returns None.

---
## C3 — Journal capture plumbing (plan T2.3 capture-side ONLY; expectancy math is NOT yours)  [x]

### C3.1 Backend: decision capture
File: `manas_os/api/app.py`. New endpoint:
```
POST /api/setups/decision   body: {scan_date, symbol, decision: "taken"|"skipped",
                                   skip_reason?: str, entry_price?: float, qty?: int}
```
Behavior: look up the scan_candidates row (scan_date+symbol); 404 if absent. Insert into a new
table `setup_decisions(scan_date TEXT, symbol TEXT, decision TEXT, skip_reason TEXT,
entry_price REAL, qty INTEGER, snapshot_json TEXT, created_at TEXT DEFAULT (datetime('now')),
PRIMARY KEY(scan_date, symbol))` (CREATE IF NOT EXISTS in the endpoint via a small
ensure fn in `manas_os/scanner/outcomes.py`). snapshot_json = the FULL candidate row as JSON.
If decision == "taken": ALSO insert a journal_trades row (trade_date=scan_date, symbol,
setup=candidate.setup, entry=entry_price or candidate.entry, stop=candidate.stop, exit=NULL,
notes='auto-captured from setups', mistake_tags_json='[]') and return its trade_id.
Response: {ok, decision, trade_id?}.
TEST (new `manas_os/tests/test_setup_decisions.py`): seed via conftest helpers
(insert_price_ramp + seed_confluent_symbol + candidates.run at AS_OF), POST taken →
setup_decisions row exists with snapshot containing '"rank"', journal_trades has 1 row;
POST skipped with skip_reason='fear' → decision row, NO new journal row; POST unknown symbol → 404.

### C3.2 Frontend: TAKEN / SKIPPED buttons
File: `manas_os/frontend/src/components/SetupsPage.jsx`. On each candidate card add two small
buttons right-aligned in the header: `TAKEN` (bull token) and `SKIPPED ▾` (muted; on click show
an inline <select> of reasons: fear / risk-too-wide / regime-doubt / better-name / other, then
submit). POST to `/api/setups/decision` via a new `postSetupDecision` fn in
`manas_os/frontend/src/api.js`. After success: badge the card corner "LOGGED ✓ taken" /
"LOGGED ✓ skipped (fear)" and disable both buttons. No page reload.
VERIFY: npm build clean.

---
## C4 — Adaptive exits + portfolio heat (plan T2.4)  [x]

### C4.1 Trail-mode engine
File: `manas_os/engine/eod_detectors.py`. NEW function (do not modify exit_state):
```python
def trail_plan(bars, entry: float, stop: float, setup_family: str) -> dict
```
Compute open R = (last_close − entry) / (entry − stop). Determine phase + action by the FIRST
matching row (LOCKED):
| condition | phase | trail | action |
| r < 1.0 and bars_since_entry unknown → treat as INITIATION | INITIATION | original stop | "HOLD — structure stop; wobble is normal" |
| r >= 1.0 and r < 2.0 | TREND | max(breakeven=entry, EMA10 for setup_family=='catalyst' else EMA21) | "MOVE STOP to breakeven; BOOK 1/3; trail {ema}" (only the first time r crosses 1 — caller tracks booked state) |
| r >= 2.0 or close > 1.08*EMA21 or close > EMA10 + 2*ATR20 | EXTENSION | max(prior stop, 2-bar low) | "BOOK 25-33% into strength; tighten to 2-bar low" |
Return {phase, r: round, trail_stop, action, why: [strings citing the numbers]}.
Also: `two_strike(bars) -> {fired: [rule names], exit_now: bool}` where exit_now = ≥2 of these
within the last 5 bars: close below EMA21; downside-reversal bar (reuse exit_state's rule) on
volume > 1.3×20-bar avg; 2 distribution days in last 5; last low < min(prior 10 lows);
gap-down open < prev_low. Reuse exit_state internals where possible WITHOUT changing them.
TESTS (`test_eod_detectors.py`): fixture uptrend where last close = entry+1.5×risk → phase
TREND, trail_stop >= entry; last close = entry+2.5×risk → EXTENSION; flat r=0.2 → INITIATION.
two_strike: craft bars with EMA21 loss + fresh 10-day-low undercut → exit_now True; only one
rule → False.

### C4.2 Heat endpoint
File: `manas_os/api/app.py`. New `GET /api/portfolio/heat`:
open positions = journal_trades WHERE exit IS NULL. Per position risk_pct =
(entry−stop)/entry*qty*entry / capital *100 where capital = config `risk.capital` default
1_000_000 and qty from setup_decisions when present else 0 (risk 0 if qty unknown — honest).
Regime = latest regime_snapshots.market_mode. Return:
{open_risk_pct, cap_pct (governor(mode)["open_risk_cap_pct"]), positions: [{symbol, entry,
stop, qty, risk_pct, sector}], sector_counts: {...}, rolling_10_avg_r: mean of last 10 CLOSED
journal r_result (null if <10, plus n), half_size_mode: rolling_10_avg_r < 0 (false when null)}.
TEST (`test_portfolio_heat.py`): two open journal rows w/ decisions → open_risk_pct equals
hand-computed sum (write the arithmetic in the test comment); 3 closed losers avg −1R with
n=3 → rolling_10_avg_r reported with n=3 and half_size_mode false (needs n>=10 to trigger:
use 10 closed rows avg −0.5 → half_size_mode true).

### C4.3 Watchlist wiring
`/api/watchlist` rows for symbols with an OPEN journal trade: attach `coach = trail_plan(...)`
+ `two_strike(...)` output as `{phase, action, exit_now}`. Frontend WatchlistPage: render an
action line under such rows: exit_now → red "EXIT TODAY — {fired rules}"; else phase-colored
`{action}`. VERIFY: build clean.

---
## C5 — AVWAP auto-anchor to spec (plan T3.6)  [x]

File: `manas_os/engine/eod_detectors.py`, REWRITE `avwap_auto_anchor(bars, signals=None,
prev_anchor: dict | None = None)` to the LOCKED rule:
1. Candidate anchors, priority order (higher wins ties): (a) EARNINGS-GAP day: open/prev_close−1
   >= 4% with volume > 1.5×20-bar avg; (b) BREAKOUT day: close > max(high of prior 20 bars)
   with volume > 1.5×20-bar avg; (c) CONFIRMED SWING LOW: a bar whose low is the min of ±4
   bars around it (needs 4 bars after it to confirm).
2. Scan the last 120 bars; newest qualifying candidate per type; significance score:
   earnings-gap=3, breakout=2, swing-low=1, +1 if its volume > 2×avg.
3. If prev_anchor is None → pick highest significance (newest on tie).
4. REPLACE prev_anchor ONLY IF: new candidate is newer AND significance strictly greater AND
   prev_anchor age >= 15 bars AND the new candidate's date differs from prev by more than 5 bars
   (hysteresis). Otherwise KEEP prev_anchor (stability is default).
5. Return {anchor_date, anchor_type, significance, reason (one sentence with the numbers,
   e.g. "Re-anchored: earnings gap +6.2% on 2.3x vol supersedes swing-low (held 22 bars)"),
   series (VWAP cumulative from anchor), kept: bool}.
Persistence: caller-side; also write chosen anchor into a new table `avwap_anchors(symbol,
as_of, anchor_date, anchor_type, reason, PRIMARY KEY(symbol, as_of))` from the ohlc endpoint
(app.py) so tomorrow's call passes prev_anchor.
TESTS: (a) bars w/ swing low at idx −30 only → picks swing-low; (b) add earnings-gap at −5 with
prev_anchor swing-low aged 30 → replaces w/ reason containing "supersedes"; (c) same but
prev_anchor age 10 → kept=True; (d) two calls same data → identical anchor (idempotent).

---
## C6 — Frontend chart migration (plan T3.5) + ECharts dep  [x]

1. `cd manas_os/frontend && npm i echarts` (Phase 3 panels will use it; just install + verify
   build stays clean — do NOT build panels yet).
2. `ChartDrawer.jsx`: replace the hand-rolled SVG candle+volume rendering with
   **lightweight-charts** (already in package.json): createChart with candlestick series +
   volume histogram (separate pane scale), EMA 10/21/50 line series, AVWAP line series from the
   ohlc payload, priceLines for stop + buy-zone (entry ±1%) + measured_move (dashed, title
   "measured move (if it works)"), markers for entry/exit arrows + pocket-pivot dots
   (marker text 'PP', shape circle) — with ONE compact legend line listing colors. Keep the
   TTM histogram + RS line as a small ECharts or existing pane BELOW (your choice of the two,
   simplest wins). Zoom/pan/crosshair come native — remove all manual scaling code.
   DELETE the now-dead SVG chart helpers in the file.
VERIFY: npm build clean; `python -m pytest manas_os/tests -q` untouched-green; note in
TASKS.md that visual browser QC is pending main-thread review.

---
## Reporting
After the queue (or on any STOP): update this file's checkboxes + TASKS.md, then report:
per-task one-liner, pytest tail, npm tail, files changed, deviations (should be none).

---
# BATCH 2 — Phase 3 panels (C7-C10). Same rules as above. echarts + lightweight-charts ARE
# installed (import * as echarts from 'echarts'; init on ref'd div, dispose on unmount).
# Layouts: follow manas_os/design/WIREFRAMES.md ASCII panel-by-panel, verbatim. Tokens are law.
# Your sandbox may block npm build/python — implement anyway, mark "verification pending main
# thread" per task in TASKS.md, continue.

## C7 (=T3.1) SetupsPage.jsx  [x]
Hero: REFUSAL FUNNEL (echarts funnel): Universe → pool → gates → passed, from
/api/setups/refusals .by_gate + /api/setups .total_passed + .governor.max_cards; hover = per-gate
drop counts. Cards add: rank badge "N of M today" (rank/rank_of), SIX gate dots (green/red,
title=reason) from candidate.gates, plan block (entry/stop/rr/suggested_qty), expectancy chip
from candidate.expectancy (system line + personal_note if present). Keep TAKEN/SKIPPED.
Expert-only (useDensity): near-miss list = refusals[] top 10 with failed_gate named.

## C8 (=T3.2) RegimeSummary.jsx  [x]
Hero above posture bar: GOVERNOR PANEL — today's law from /api/setups .governor: max_cards,
risk_band base–hard_max %, allowed_families chips, "PUSHES ON/OFF". Then wrap ParticipationPanel,
BreadthGrid, SectorsThemesPanel, TopIndicesPanel, RegimeTrend in ONE expert-only <details>
"Show the numbers" (beginner = governor + posture + top-setups strip only). FIX the
contradiction: the "BREADTH / SWING STATE … Breadth unavailable" chip must derive from the SAME
/api/regime/summary payload as the posture line — delete its separate fetch/fallback.

## C9 (=T3.3) JournalPage.jsx + /api/expectancy  [x]
Backend (ONLY allowed backend change): GET /api/expectancy in api/app.py → latest
setup_expectancy rows as {as_of, system:[...], personal:[...]}; test
manas_os/tests/test_expectancy_api.py (TestClient; seed conftest insert_price_ramp +
seed_confluent_symbol + candidates.run + expectancy.run at AS_OF; assert 200 + keys).
Frontend above the trades table: equity curve in R (echarts line, cumulative r_result by
trade_date, drawdown shaded) · EXPECTANCY MATRIX (echarts heatmap: setup_family × regime,
cell=posterior_r, label=n, grey n<20) · R histogram (0.5R bins) · mistake-tag Pareto (from stats).

## C10 (=T3.4) WatchlistPage.jsx  [x]
Top row from /api/portfolio/heat: open-risk gauge (echarts gauge, open_risk_pct vs cap_pct) ·
sector donut (echarts pie, sector_counts) · progressive-exposure chip (rolling_10_avg_r; red
"HALF SIZE MODE" when half_size_mode). Table: clickable-sort headers (asc/desc cycle) for adr +
delivery_z-if-present. Keep the C4.3 coach lines.
