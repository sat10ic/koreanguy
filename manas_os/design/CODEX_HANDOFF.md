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

---
# BATCH 3 - T3.9 Position Coach (the exit hand-holding layer). Same execution rules as
# BATCH 1/2 (in order, do NOT touch backtest/replay.py, scanner/gates.py, risk/plan.py,
# regime/governor.py). Reuse manas_os/engine/eod_detectors.trail_plan() and two_strike()
# as-is (already correct, tested, wired into /api/watchlist's coach field) - this batch
# turns that thin dict into the full per-position coach the plan (T3.9) specifies. One writer
# rule: coach is a PRESENTATION + GUARD layer over trail_plan/two_strike, never a second
# opinion - it must not recompute phase/action itself.

## C11 (=T3.9a) Dedicated coach endpoint - manas_os/api/app.py
Add GET /api/positions/{trade_id}/coach (trade_id = journal_trades.trade_id, the existing
PK). Look up the open trade (WHERE trade_id=? AND exit IS NULL); 404-shape
{"available": false, "reason": "no open position with that id"} if missing/closed. Load bars
via the existing _load_symbol_bars(conn, symbol, on_or_before=today, 80) helper (already used
at api/app.py ~L985), call trail_plan() + two_strike() exactly as /api/watchlist does today
(~L989-1001). Do not duplicate the setup_family inference logic - factor it into one shared
private helper _coach_for_open_trade(conn, trade_row, as_of) used by BOTH this new endpoint AND
the existing /api/watchlist coach field (delete the duplicated inline block at ~L978-1001, call
the helper instead - one writer, not two).
The helper's return dict adds three fields beyond what exists today:
- verdict: map trail_plan phase -> {"INITIATION": "HOLD", "TREND": "HOLD", "EXTENSION": "TRIM"},
  overridden to "EXIT" when two_strike().exit_now is True.
- plain_instruction: one sentence built from phase+action+trail_stop, reusing trail_plan's own
  action/why strings as the source of truth (do not invent new numbers). Examples: TREND ->
  "HOLD - trailing {ema_name} (now {trail_stop}). You're +{r}R." EXTENSION -> "TRIM 25-33% into
  strength; tighten stop to the 2-bar low ({trail_stop})." EXIT (two_strike fired) -> "EXIT TODAY
  - {N} exit rules fired ({fired joined}). Sell the full position near the close." INITIATION ->
  "HOLD - do nothing. Stop stays at {stop}. Wobble in the first few days is normal; the trade
  isn't wrong until the stop breaks." Exact wording is yours - keep it one plain sentence.
- fear_greed_note: OPTIONAL, only when personal expectancy data exists - call
  manas_os.scanner.expectancy.chip_for(conn, setup_family, regime); if the personal cell has
  n>=10, add e.g. f"your last {n} trades in this family averaged {mean_r}R" (read-only citation,
  never gates the verdict).
Response shape: {available, trade_id, symbol, phase, verdict, r, trail_stop, plain_instruction,
why, fired, exit_now, fear_greed_note}.
Test: manas_os/tests/test_position_coach_api.py - seed conftest insert_price_ramp +
seed_confluent_symbol, insert one open journal_trades row (entry/stop from the fixture), assert
200 + verdict in {"HOLD","TRIM","EXIT"}; a second test forces two_strike to fire (bars crafted
with 2 down-with-volume closes below 21EMA in the last 5) and asserts verdict=="EXIT" +
exit_now is True. A third test hits a closed/nonexistent trade_id and asserts available: false.

## C12 (=T3.9b) Early-exit guard - manas_os/api/app.py
Check first whether a position-close endpoint already exists (grep how Watchlist/Journal close
an open journal_trades row today - likely a PATCH/POST that sets exit/r_result). If closing
already goes through one endpoint, ADD the guard there; if it does not exist yet, add
POST /api/journal/trades/{trade_id}/close taking {exit_price, mistake_tag?}.
Guard logic: before writing the close, call _coach_for_open_trade (from C11) on the trade being
closed. If verdict == "HOLD" (engine says intact, not extended) AND no mistake_tag was supplied
in the request body, return 409 {"guard": true, "message": "The system reads this as a HOLD -
exiting now is the #1 beginner mistake (fear of giving back). If you still want to exit, pick a
reason.", "reasons": ["fear","need-cash","thesis-change","other"]} and do NOT write the close.
If a mistake_tag IS supplied (any value, including on a non-HOLD close), proceed: write the
close AND persist the tag into journal_trades.mistake_tags_json (append to the existing list,
JSON, don't overwrite). This guard NEVER blocks outright - it only requires one extra tap+tag
when against a HOLD read. Frontend (JournalPage.jsx or wherever the close action lives - grep
for the existing close-position UI call): on a 409 with guard:true, show the message + 4 reason
buttons inline, re-submit the same close request with the chosen mistake_tag.
Test: closing a HOLD-phase trade with no tag -> 409 + no DB write; closing with a tag -> 200 +
mistake_tags_json contains it; closing an EXIT-phase trade with no tag -> 200 (guard doesn't
apply when the engine already agrees).

## C13 (=T3.9c) Late-exit banner - manas_os/api/app.py + frontend
An EXIT verdict un-acted for >=2 sessions must be loud everywhere. Add column
first_exit_flag_date TEXT to journal_trades (additive migration in manas_os/db/schema.sql + a
guarded ALTER TABLE ... ADD COLUMN in db.init_db matching the existing pattern used for other
additive columns in that file - grep _ensure_watchlist_exit_columns in api/app.py for the
established idiom, mirror it as _ensure_journal_flag_column). In _coach_for_open_trade: when
exit_now is True and first_exit_flag_date is NULL, set it to as_of (first time seen). When
exit_now is True and first_exit_flag_date is already set and >=2 trading sessions old (use the
existing market_calendar helper the rest of the codebase uses for session counting - grep
market_calendar.py for the trading-day-diff function, do not hand-roll weekday math), add
"banner": "OVERDUE EXIT - flagged {N} sessions ago, still open" to the coach payload. When the
position is closed or exit_now goes back False, clear the column to NULL. Frontend: any screen
that renders coach.banner (Watchlist row + the Daily Flow's step 3 per T3.8 - reuse
FlowStepper.jsx's existing step-3 slot if it renders open positions, else add a small urgent
block above the table) shows it in the existing "urgent/red" token - no new color.
Test: fixture where exit_now stays True across 3 fake as_of dates 2 sessions apart -> banner
present with correct session count; position closes -> column clears (query the row after a
close call from C12).

VERIFY after each of C11/C12/C13: python -m pytest manas_os/tests -q (baseline 163 green, never
regress) and cd manas_os/frontend && npm run build. Update this file's checkboxes +
manas_os/TASKS.md (T3.9 rows) as you go. Report per-task: one-liner, pytest tail, npm tail,
files changed, deviations (should be none - if the close-endpoint or session-diff helper
genuinely doesn't exist as described, say so plainly and show what you found instead, don't
invent a parallel one).

---
# BATCH 4 - T4.1 slice 1: DIGEST generation only (plan Phase 4). No live WebSocket, no
# external creds, no push delivery yet - this is the deterministic, testable half: turn today's
# governor-capped candidates into the nightly Telegram DIGEST payload + persist an ARMED-list
# table. Runs ISOLATED from BATCH 3 (new file + one small addition to alerts/eod.py's ensure_schema
# pattern) - do not touch api/app.py, eod_detectors.py, or anything BATCH 3 owns.

## C14 (=T4.1a) alerts/telegram_engine.py (NEW FILE)  [x]
Follow the shape of `alerts/eod.py` (STAGE/SOURCE constants, `ensure_schema(conn)`,
a `run(conn, run_date)` pipeline stage registered in `manas_os/cli/__init__.py` next to
`eod_alerts`, writing a `pipeline_runs` row same as every other stage - grep any existing
`run()` in scanner/expectancy.py for the exact insert pattern to copy).
Schema: `CREATE TABLE IF NOT EXISTS armed_list (armed_date TEXT NOT NULL, symbol TEXT NOT NULL,
trigger REAL, stop REAL, qty INTEGER, setup_family TEXT, rank INTEGER, ttl_date TEXT,
created_at TEXT DEFAULT (datetime('now')), PRIMARY KEY(armed_date, symbol))`.
`build_digest(conn, run_date) -> dict`: load the SAME governor-capped, ranked candidates
`scanner_candidates.load_persisted_candidates(conn, run_date)` already returns (reuse it, don't
requery candidates yourself - one writer). Digest caps by regime (LOCKED, from the plan doc):
RISK_ON 5, SELECTIVE 3, DEFENSIVE 1, NO_TRADE 0 - apply as a second, TIGHTER truncation on top
of whatever the governor already capped to (governor caps the FEED; digest caps what's pushed,
which is <= the feed). Also count refusals for that date (`SELECT COUNT(*) FROM refusals WHERE
scan_date=?`) and include `f"...and {N} names refused"` in a `summary` string. For EVERY digest
candidate whose `plan_result`/card already carries entry+stop+qty (it does - these are on every
persisted card per T0.1), write one `armed_list` row with `ttl_date` = next trading session (use
the `market_calendar` helper for next-session, don't hand-roll). Return
`{"as_of": run_date, "market_mode": ..., "summary": str, "digest": [...], "armed_count": int}`.
`run(conn, run_date)`: ensure_schema, call build_digest, persist nothing beyond the armed_list
rows already written by build_digest (digest itself is NOT persisted, it's regenerated on
demand for the CLI/manual-send step), write the pipeline_runs row, return
`{"status": "ok", "armed_count": N}`.
Do NOT implement: any Telegram Bot API call, any network I/O, any credential loading - that is
explicitly future work once this deterministic half is proven (per the plan's own build-order
note: "FSM replay harness first, paper mode, then live"). If you're tempted to add a `send()`
function, stop - it's out of scope for this slice.
Tests: `manas_os/tests/test_telegram_engine.py` - seed conftest `insert_price_ramp` +
`seed_confluent_symbol`, run `cand.run` then `telegram_engine.run` at AS_OF; assert digest count
<= the regime's LOCKED cap even when more candidates passed the governor; assert armed_list rows
match digest symbols with correct trigger/stop/qty carried over from the candidate row; assert
summary string mentions the refusal count.

VERIFY: python -m pytest manas_os/tests -q (baseline 163+ from before this batch, never regress)
- no frontend change in this slice, skip npm build. Tick this file + TASKS.md T4.1 row (leave it
noted as "slice 1 of N - digest+armed only, no live push" rather than fully checked, since T4.1's
full scope is bigger). Report: one-liner, pytest tail, files changed, deviations.
IMPORTANT: if `python`/`py` is not on PATH in your sandbox, try the documented fallback
`C:\Users\satta\AppData\Local\Programs\Python\Python312\python.exe` (absolute path) before
reporting pytest as unrunnable - use it directly as the interpreter for both pip/test commands.

---
# BATCH 5 - Configurable mentor/guru checklists (#17 in TASKS.md). NEW isolated feature: one
# new table, one new endpoint, one new frontend panel. Does not touch anything BATCH 3/4 own
# (api/app.py gets ONE new route block appended at the end of the file, nothing existing edited).

## C15 (=#17) Mentor checklists  [x]
Data: `manas_os/design/mentor_checklists.yaml` (NEW, hand-authored by you, config-editable by the
user later - this is the point, "configurable"). Structure:
```yaml
checklists:
  - id: manas_arora_daily
    mentor: "Manas Arora"
    title: "Daily discipline checklist"
    items:
      - id: reviewed_regime
        text: "Did I check today's regime/governor before looking at any setup?"
      - id: no_fomo_entry
        text: "Am I entering because the plan says so, not because I'm afraid of missing out?"
      - id: sized_by_plan
        text: "Is my position size exactly what the risk plan computed, not bigger?"
      - id: exits_checked_first
        text: "Did I check my open positions' exit state BEFORE looking at new setups?"
      - id: logged_decision
        text: "Will I log this trade (taken or skipped) in the journal today?"
```
(5-8 items is enough; ground the wording in the discipline themes already in
`manas_os/docs/Tradetm/*.txt` - decision quality vs outcome, process over results,
review-and-improve loop - do not invent unrelated psychology content, keep each item a plain
yes/no question a beginner can self-answer in seconds.)
Backend: `manas_os/scanner/mentor_checklists.py` (NEW) - `load_checklists() -> list[dict]`
(parses the YAML, cached at module import, config path via `manas_os.config` if a path
override is set, else the default file above). Table
`CREATE TABLE IF NOT EXISTS checklist_responses (response_date TEXT NOT NULL, checklist_id TEXT
NOT NULL, item_id TEXT NOT NULL, checked INTEGER NOT NULL, created_at TEXT DEFAULT
(datetime('now')), PRIMARY KEY(response_date, checklist_id, item_id))`. `ensure_schema(conn)`.
API (append new routes at the END of `manas_os/api/app.py`, do not touch any existing route):
`GET /api/mentor/checklists` -> `{checklists: [...from YAML...]}`.
`GET /api/mentor/checklists/{checklist_id}/responses?date=` -> `{date, responses: {item_id:
bool}}` (defaults missing items to false, does not error if no rows yet).
`POST /api/mentor/checklists/{checklist_id}/responses` body `{date, item_id, checked: bool}` ->
upsert one row, return `{ok: true}`.
Frontend: NEW `manas_os/frontend/src/components/MentorChecklistPanel.jsx` - simple list of
checkboxes with the question text, one panel per checklist, persists on click (optimistic UI +
POST). Mount it on the Journal screen (below the existing content, its own bordered section
titled "Mentor checklist - {mentor}") - grep `JournalPage.jsx` for where sections are composed
and append there; use existing design tokens only, no new colors/components.
Tests: `manas_os/tests/test_mentor_checklists.py` - load_checklists() returns >=1 checklist with
>=3 items; POST a response then GET responses shows it checked=true; GET responses for a date
with no rows yet returns all items false (never errors).

VERIFY: python -m pytest manas_os/tests -q (baseline from before this batch, never regress) and
cd manas_os/frontend && npm run build. Tick this file + add a TASKS.md row for #17 (completed).
Report: one-liner, pytest tail, npm tail, files changed, deviations.

Batch 5/C15 status: [x] implemented. Verification attempted 2026-07-06; blocked by the existing sandbox
limits already logged in TASKS.md (`python`/`py` unavailable, documented Python fallback Access denied,
Vite/esbuild cannot read `../../../..` while loading vite.config.js).

---
# BATCH 6 - Regime history strip (#1 in TASKS.md, remaining piece only). PURE FRONTEND - the
# backend endpoints already exist and are unused (`GET /api/regime/history?days=` returns
# {available, rows:[{snapshot_date, xp_value, market_mode, mbi_day_color, warning_day, r4p5,
# r10, r20, r50}]}; `GET /api/regime/breadth-history?days=` returns {available, rows:[{trade_date,
# pct_above_20dma, pct_above_40dma, pct_above_50dma, advances, declines}]}). Do NOT add/modify
# any backend route - both already exist verbatim as described, confirm by reading
# manas_os/api/app.py around the `regime_history` and `regime_breadth_history` functions before
# writing frontend code, do not guess the shape.

## C16 (=#1) Regime history strip  [x]
File: `manas_os/frontend/src/components/RegimeSummary.jsx` (and `manas_os/frontend/src/api.js`
for the two new fetch functions `fetchRegimeHistory(days)` / `fetchRegimeBreadthHistory(days)`).
Add ONE new section below the existing governor panel / posture strip (expert-only, inside the
existing `<details>`/expert accordion this file already has from C8 - do not duplicate the
accordion, add a new panel inside it): a compact ECharts line chart, x-axis = snapshot_date
(last 60 rows from `/api/regime/history?days=60`), two series: `xp_value` (line) and a colored
background band per `market_mode` (RISK_ON/SELECTIVE/DEFENSIVE/NO_TRADE - map to the 4 existing
posture tokens already used elsewhere in this file, no new colors) rendered as
`markArea` segments. Below the chart, a one-line caption computed client-side from the last 5
rows' `pct_above_20dma` trend (from the breadth-history call): "breadth improving/declining N
of last 5 days" (simple client-side comparison, no new backend field). If either endpoint
returns `available:false`, render nothing (existing empty-state convention in this file - grep
how other panels in this file already handle `available:false`, match it).
Loading: fetch both on mount, once (not on every render); use the existing data-fetch pattern in
this file (grep how `sectors`/`indices` panels already fetch, mirror it - don't introduce a new
data-fetching convention).
Test: no backend test needed (no backend change). Just confirm `npm run build` stays clean and
do a quick manual sanity check that the component doesn't crash when `/api/regime/history`
returns `available:false` (pass an empty mock inline if you want to hand-verify, not required to
add an automated frontend test - this repo has none yet, don't introduce a test framework for
one component).

VERIFY: python -m pytest manas_os/tests -q (must not regress - this batch shouldn't touch any
Python file, so it should stay exactly at whatever the previous batch's genuine count was) and
cd manas_os/frontend && npm run build (must succeed). Tick this file + TASKS.md #1 (completed).
Report: one-liner, npm tail, files changed, deviations. If `python`/`py` not on PATH, use
C:\Users\satta\AppData\Local\Programs\Python\Python312\python.exe.
