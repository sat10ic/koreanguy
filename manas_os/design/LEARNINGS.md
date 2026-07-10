# LEARNINGS.md — threshold changes, replay results, calibration log (Manas 2.0)

Every gate/threshold change and every replay/validation result gets one entry.
No silent reweighting.

## 2026-07-06 — Phase 0 complete (T0.1 clamps + T0.2 replay harness)
- Growth clamp [-200, +500] + untrusted flag live; "+-" sign bug fixed; stop bound
  1-8% enforced at candidate build (out-of-band stops dropped with named reason);
  rr + suggested_qty required on every persisted candidate. (Codex build, Opus QC.)
- Replay harness live (`manas_os/backtest/replay.py`): per (setup_family × regime)
  cells, A/B configs, thin-cell suppression (n<20), look-ahead guard tested.
- Fixed in QC: `backtest/__init__.py` re-export shadowed the `replay` submodule;
  replay tests rewritten to a pluggable fake generator (right unit boundary);
  three test fixtures used a +1/day ramp whose 20-day-low stop was ~16% — the new
  bound correctly refused them; ramps flattened to 0.1/day (the code was right).
- delivery_z gained a 1pp dispersion floor: constant-delivery history had std=0,
  masking a 60→20 collapse (z forced to 0). Found by test.

## 2026-07-06 — CRITICAL replay finding (shapes T1.4)
`replay('legacy', 2026-05-01..2026-07-03)` = **zero completed observations**: the
legacy candidate pool requires ChartsMaze `screener_hits`, which exist only for
the dated dump folders (2026-03-23 → 2026-07-05, 7 dates). Historical sessions
have no screener data → no candidates → no backtest.
**Consequence (binding for T1.4):** the `cascade` generator must derive setup
detection from OHLCV point-in-time (daily_prices covers all ~282 sessions), with
screener-confluence as an optional boost when a dump date is available — otherwise
the validation loop (T1.6) and the expectancy moat (T2.3) have no history to learn
from. Going forward, daily ChartsMaze dumps accumulate real confluence history.

## 2026-07-06 — Phase 1 core built (T1.1–T1.3, hand-written + tested)
- `scanner/gates.py`: deterministic cascade (regime → tradability(ASM/MAX/pump) →
  trend-template(50>200, EMA Lead, nearness≥0.85, RS≥80) → fresh-leg state machine →
  participation(delivery_z≥0, breakout vol 1.2×) → risk). Fail-fast with named
  reasons; 19 tests.
- `risk/plan.py`: single writer of stop/size/R:R; 3-stop hierarchy; LOCKED caps
  (6/5/4%, EP-IPO 7.5%, abs 8%, floor 1%); R:R≥1.5; AGGRESSIVE default profile
  (0.75/0.50/0.30 base risk, heat caps 3.0/2.0/1.0, ≤5 positions); sector
  concentration (≤2, 3rd half-size); circuit-band feasibility hook.
- `regime/governor.py`: feed caps 8/4/2/0, allowed families, risk bands,
  push_allowed; unknown mode degrades to NO_TRADE (never permissive).
- Suite: 135 passed.

## 2026-07-06 — T1.4/T1.5 live QC (first real cascade run, session 2026-07-03)
- THE GATE REFUSES: pool ~600 → 23 passed / 577 refused. By gate: tradability 301,
  regime 222 (SELECTIVE suppressing momentum family), trend-template 19, participation 18,
  risk 11, fresh-leg 6. Governor then caps display at 4 (SELECTIVE). Top names carried
  delivery_z up to +3.8 with 2.0 R:R plans.
- QC catch 1: HDFCNEXT50 (index fund) passed — ETF keyword set lacked NEXT50/NIFTY/SETF
  generics. Keywords extended.
- QC catch 2: every card graded B — the one-opinion cap fired on mere `below-21EMA`,
  which IS the entry condition of a pullback. Cap now requires real weakness
  (distribution / lower-low / downside-reversal / crossed-below-21EMA).
- PERF: absolute_strength_percentiles ran one query PER symbol (~2,400/session) — replay
  timed out. Rewritten as a single window-function query. Scan ≈ 60s/session (bar-loading
  is the next bottleneck if replay needs to be faster).
- KNOWN LIMIT (not fixed): measured_move = entry + 2×risk ⇒ rr is uniformly 2.0, so the
  R:R≥1.5 floor never bites. Structural targets (prior high / base measured-move) are the
  right fix — queue for T2 follow-up before trusting rr in expectancy math.

## 2026-07-06 — T1.6 CHECKPOINT: PASSED (with one flagged caveat)
Replay v2 (fill-checked entries + near-miss baseline), 13 sessions 2026-06-09..27, all SELECTIVE:
- pullback×SELECTIVE: n=73, hit(≥+1R@T10) 30.1%, median +0.44R, median stop 3.6%, ~5.6 passed/day
  (governor displays top 4). 56 phantom "trades" (trigger never touched) removed by the fill
  check — v1's −0.35R verdict was an artifact of fictional fills at unfilled pivots.
- Positive median R on 3.6% stops BEFORE trail/partial logic → the passed cohort has drift.
- Gate distribution stable: ~600 pool → ~23 pass/day pre-governor.
- CAVEAT (open): near-miss refused baseline median +2.52% (n=517) vs passed ~+1.6% price-basis
  on this window. Dominated by trend-template refusals of EXTENDED names in a rising June tape —
  10-day horizon flatters chasing. Action: per-gate baseline split + full-history window before
  reading anything into it. Do NOT loosen the fresh-leg/template gates off one flattering
  fortnight — that is exactly the trap the gates exist for.
- ipo_base/shakeout cells too thin (n<20). Momentum family unmeasurable until a RISK_ON stretch
  is replayed (June was SELECTIVE throughout). Full-history replay (~2h) queued for an idle slot.
GATE TO PHASE 2: OPEN. Next: T2.2 PEAD mcap-decile backtest on the same harness.

## 2026-07-06 — T2.2 PEAD/gap-drift study (1,209 events, 2025-04..2026-06)
Price-only gap events (gap>=4% + vol>=1.5x + quiet 25-bar base), forward from event close:
- LIQUIDITY GRADIENT IS THE FINDING (monotonic): illiquid <5cr turnover: -2.50% T+10 / -4.50%
  T+20 (n=804, 67% of all events!) · 5-25cr: -0.49% · 25-100cr: +0.24% · >100cr: +1.73% T+10,
  40.5% hit. Illiquid gap-ups are exit-liquidity traps; follow-through lives in LIQUID names.
- Bigger gaps are not better (>10% gaps median -2.12%).
- Micro-cap bucket -8.65%/-11.63% → MAX/lottery + pump exclusions strongly validated.
- VERDICT on the naive small-cap-PEAD thesis: NOT confirmed for price-only gaps — the CATALYST
  leg (30% EPS+sales growth) is load-bearing, not optional. Catalyst-conditioned drift is
  untestable historically (growth data exists only for dump dates); the journal loop will
  build that sample live. ACTIONS: (1) EP keeps all legs, never relax to price-only gaps;
  (2) turnover floor Rs5cr re-validated; (3) consider liquidity-tier boost inside EP ranking
  (liquid EP > thin EP) — queued, one-change-per-quarter rule applies.

## 2026-07-06 — R:R=2.0 root-cause fix (integrity, pre-Phase-3)
The synthetic measured move `entry + 2*risk` made every candidate's R:R uniformly 2.0, so
the `validate()` R:R>=1.5 floor never bit (flagged in T1.6/T2.2 entries above). Fixed by
replacing it with a STRUCTURAL target — `risk/plan.py:structural_target()` (the single
writer, anti-mashup), mirroring `choose_stop`'s shape:
- Hierarchy: prior swing high (±4 local max over trailing 90 sessions) → base ceiling
  (trailing 20-bar high excl. trigger) → entry+1 ATR volatility projection (synthetic,
  flagged; EP/IPO accept this more readily, non-exceptional requires ATR>=1.5*risk).
- Returns `{target, method, synthetic}`; when nothing is visible the target is None and
  `validate()` refuses with "no measured move — R:R unknowable" (honest refusal, not a
  manufactured pass).
- The R:R floor now ACTUALLY GATES: a tight-target name (prior swing high only 2% above
  entry with a 4% stop → R:R 0.5) is now refused. End-to-end test added
  (`test_structural_target_makes_rr_floor_actually_gate`).
- Fixture consequence: `insert_price_ramp` in conftest now injects a prior swing high
  ~40 bars from the end (real base-breakout geometry — a prior peak the breakout clears
  and races toward). Without it the ramp's most recent highs are always highest and the
  structural target degrades to the synthetic ATR path. Tests stayed green (160 passed).
DO NOT regress this: the synthetic 2x projection must not come back. If a future change
makes the structural target unreliable, refuse the trade rather than manufacture a number.

## 2026-07-06 — T3.7a Focus Center "0 setups" fix
Root cause: the EP/IPO lens filtered the governor-CAPPED candidate list (4 cards in
SELECTIVE). When the top-4 ranked were pullbacks, the lens found 0 EP/IPO even though 6
existed below the cap (STATE_OF_TOOL §3.3). Fix: backend `/api/setups` now returns a
`focus_candidates` slice pulled from the FULL ranked list (pre-cap, EP/IPO-base only,
capped at 6); the frontend lens renders from that slice. The "All" view still respects
the governor cap — the Focus Center's whole purpose is to surface catalyst names that
rank below the display cap.

## 2026-07-06 — T3.7b beginner/expert toggle made real
The toggle was cosmetic (only `Read.jsx` consumed `useDensity`, per STATE_OF_TOOL §3.7).
Made it genuinely functional on the Regime flagship per BEGINNER_EXPERT_SPEC: beginner
hides GovernorPanel (diagnostic internals) and collapses the numbers block behind a
`<ShowDetails>` affordance; expert renders GovernorPanel + full internals inline +
technical_detail expanded. Added shared primitives `densityLabels.js` (label swap map)
and `ShowDetails.jsx` (reusable expander). InfoDot dimmed in expert (Axis F). TechnicalDetail
now accepts `defaultOpen` (Axis E). DOM is now demonstrably different between modes.
DEFERRED: Setups/Watchlist column-axis (Axis D) — lower-impact, follow-up.

## 2026-07-06 — Ground-truth verification pass (post wave-4 commit)
DB lock ("database is locked" on /api/expectancy, /api/setups, /api/portfolio/heat) was NOT
the full-year replay finishing slowly — it was ~10 stale `python.exe` processes (dead
replay/study child runs, zero CPU, `16 K` mem each) left over from earlier background jobs,
plus the live API server itself holding a stale connection. Killed the stale processes,
restarted the API server (`run_manas_api.py`), all three endpoints now return 200 clean.
Lesson: a long-running background job finishing is not the only way a SQLite lock clears —
check for orphaned child processes via `tasklist` before assuming "just wait."

Also verified `risk_plan.structural_target()` (the rr=2.0 fix) live, not just via unit tests.
The persisted `candidates` rows from 2026-07-03 all showed rr exactly 2.0 — looked like the fix
hadn't landed. Root cause: those rows were scanned BEFORE the fix (2026-07-03 data, fix dated
2026-07-06 per the code comment). Re-ran `candidates.run()` on the same historical date against
current code: rr now varies (2.0, 4.0, 5.18, 2.44, 1.62 seen across one session's cohort) —
the fix is real and live, the stale row confusion was a timing artifact, not a code defect.
Lesson: when live data looks wrong, check whether it predates the fix before treating it as a
live bug — re-run the pipeline stage on current code before concluding.

## 2026-07-06 — Fable consult + integrity bug in structural_target()
Consulted Fable for an independent progress re-score against the original 3/10 review.
Verdict: 6.5/10 — the refusal cascade, risk writer, and expectancy math are now genuinely real
(verified in code, not just claimed), but the edge itself is statistically unproven (n=73, one
regime) and ~10 Phase-3 checkboxes (C7-C16) are ticked `[x]` without an actual npm build or
browser QC pass (Codex's sandbox blocked verification every time and it was never followed up
by the main thread — a real process gap, not a code defect).

Fable also caught a genuine integrity bug in `risk/plan.structural_target()` (`risk/plan.py`):
the swing-high scan used `max(swing, h)`, picking the FARTHEST qualifying overhead resistance
instead of the nearest — inflating the measured move and therefore R:R for every candidate with
more than one swing high in the 90-session window. Compounding bug found while fixing it: the
local-max test used `h >= n` (non-strict), so flat/tied bars all qualified as "swing highs" too
— the same degenerate-tie pattern already fixed once this build in the AVWAP anchor's swing-low
detection (`eod_detectors.py`). Fixed both: swing-high test now requires strict `h > n`, and
among genuine swing highs above entry the nearest (minimum) is chosen, not the maximum.
`test_structural_target_picks_prior_swing_high` only used a single swing high per fixture so
neither bug was caught by existing tests — worth a follow-up test with two swing highs at
different distances to lock in the "nearest wins" contract. 170 tests green after the fix
(was 167 when Fable checked — BATCH 3-6 added tests in between).

## 2026-07-07 — Near-miss cohort, per-gate interim verdict (full-history refusals, n=20,115)
Sampled 781 refusals (every 25th) across the four near-miss gates; forward return = T+10
close-to-close from daily_prices (NOT R-adjusted — see caveat). Passed-cohort comparison
pending (the earlier full replay persisted only refusals; re-running on a DB copy now, no
live-DB lock this time).
- refused@fresh-leg:      n=11  median -7.03%  win 27%  — the anti-chase gate is STRONGLY
  vindicated: extended names it refused fell hard. Small n, but the direction is emphatic.
- refused@trend-template: n=691 median -0.04%  win 50%  — refusals are a coin flip; the gate
  costs nothing and buys structure. Fine as-is.
- refused@participation:  n=54  median -0.06%  win 48%  — neutral; delivery gate not yet
  proven either way at this horizon.
- refused@risk:           n=25  median +3.51%  win 68%  — risk-gate refusals RISE. CAVEAT:
  this is raw %, not R. These were refused for wide stops / poor R:R — a +3.5% move on a
  name needing an 8-12% stop is still a bad trade in R terms. Do NOT loosen the risk gate on
  this number; the honest test is R-adjusted expectancy using the stop the plan would have
  set, which the replay-on-copy run will produce.
Action: full replay on the copy → passed vs refused verdict in R terms; then (and only then)
a calibration decision. This entry supersedes nothing; it frames the question precisely.

## 2026-07-07 - W4 Telegram paper-mode start
Telegram entry automation is paper-only from this point. The live FSM persists `paper_mode=1`
by default, and nightly digest delivery remains `telegram.dry_run: true` unless explicitly
overridden in gitignored `config.yaml`. Graduation rule: do not enable real intraday entry
pushes until at least one full calendar month of paper-mode sessions has been reviewed with
zero duplicate entry alerts, correct TAKE/SKIP capture into `setup_decisions`, `/halt`
blocking entry pushes while preserving exit alerts, and no material mismatch between armed
triggers and the order tickets produced by the daily flow.

## 2026-07-10 — E1-PERSIST: full-history replay finally persisted to setup_expectancy
`setup_expectancy` had 0 rows despite two prior full-history replay attempts (2026-07-07,
`_w1_replay.py`/`_replay_copy.py`) — both computed real cells but only as an in-memory/JSON
result that was never written to the table (the copy-DB attempt also crashed mid-run,
"database disk image is malformed", after ~165k refusals ledgered). The bug was structural:
`replay()` in `backtest/replay.py` returns cells, it never persisted them, and `expectancy.run()`
(the actual `setup_expectancy` writer) only ever read from the `candidates`/`outcomes` tables —
which had 23 rows total, because the daily `scan_candidates.run()` writer had only ever been
exercised for the last ~week, not backfilled across history.

Fix: `backtest/replay.persist_replay(conn, start, end)` (new; wired to `manas replay --persist`)
makes one `scan_candidates()` call per historical session (2025-03-19..2026-07-09, 285 EQ
sessions), persists every PASSED survivor via the existing P2 writer
(`scanner.candidates.persist_candidates`, exactly the live-pipeline path — no parallel writer),
then backfills `outcomes` (T+5/10/20) and calls `expectancy.run()`. Runtime: 36.3 min for the
full 285-session backfill. REFUSED cohort has no entry/stop in the `refusals` ledger (only
symbol/gate/reason), so instead of fabricating an R-multiple it reuses the close-to-close
%-return baseline already established and caveated on 2026-07-07, computed straight from the
now-complete `refusals` ledger (167k+ rows spanning the same window) — grouped by
(family, regime) instead of one aggregate this time. `setup_expectancy` now carries a `cohort`
column (`passed`|`refused`) folded into its PRIMARY KEY; `chip_for()` and the new
`_system_expectancy_ledger()` (backing `/api/desk/track-record`) look up each cohort/loop pair
at ITS OWN latest `as_of` (not one global MAX) so the daily `expectancy.run()` refresh can never
silently hide the richer historical replay-derived refused-cohort rows.

**The honest numbers (as_of 2026-07-09, T+10, full 16-month history):**

| family | regime | cohort | n | hit/win rate | avg return | trust |
|---|---|---|---|---|---|---|
| base/pattern | SELECTIVE | passed (R) | 21 | 9.5% | -1.29R | directional |
| base/pattern | SELECTIVE | refused (%, no stop) | 19,065 | 47.9% | +0.30% | operational |
| catalyst | DEFENSIVE | passed (R) | 5 | 20.0% | -2.49R | descriptive (UNPROVEN) |
| catalyst | DEFENSIVE | refused (%, no stop) | 256 | 51.2% | +0.58% | operational |
| catalyst | SELECTIVE | passed (R) | 29 | 10.3% | -1.15R | directional |
| catalyst | SELECTIVE | refused (%, no stop) | 1,436 | 53.3% | +1.58% | operational |

Passed and refused are NOT directly comparable (R-multiple vs raw %, since refused names never
had a stop set) but the direction is unmistakable and uncomfortable: every PASSED cohort lost
money on average (-1.15R to -2.49R, hit rate 9.5-20%) across the full replay, while every
REFUSED cohort's raw price action was flat-to-positive. This is the opposite of "refused
underperforms" — the gate cascade's survivors are currently the worse bucket. Two honest
readings, not yet disambiguated: (a) the cascade's ranking/family-tagging logic has a real
defect worth auditing before trusting any card's chip, or (b) survivorship in the passed sample
is thin (5-29) and concentrated in a chase-y regime window. Recommendation: do NOT loosen or
tighten any gate off this run alone — audit `candidate_for_symbol`'s family assignment and entry
timing against a handful of the 21 base/pattern SELECTIVE losers by hand before drawing a
calibration conclusion. Only `base/pattern`/`catalyst` × `SELECTIVE`/`DEFENSIVE` produced any
cell at all — `momentum`, `accumulation`, and the `RISK_ON`/`NO_TRADE` regimes never had a
passed survivor in 285 sessions, which is itself a data point about how selective the cascade
currently is.

Rerun is idempotent (`DELETE ... WHERE as_of=? AND cohort=?` before each insert, keyed by
family+regime); re-running `manas replay --persist` over the same window reproduces the same
six rows.

## 2026-07-10 — E1-FIX: stop-exit modeling replaces the impossible-to-honor unmanaged hold

Audit trigger: the E1-PERSIST numbers above showed the PASSED cohort averaging -1.15R to
-2.49R at hit rates of 9.5-20%. That is mechanically impossible for a stop-honored trade: a
plan that risks 1R per share cannot lose more than -1R (plus slippage) if the stop is actually
respected. The methodology was the bug, not the setups -- `forward_r`
(`manas_os/scanner/outcomes.py`) graded an UNMANAGED T+10 close-to-close hold in R units (no
stop-out, no fill check, same-day entry at the plan's pivot price), so a name that gapped down
hard and never came back could print -7R to -11R on a single observation and drag the whole
cell's average past the floor a real stop would enforce.

Fix: additive stop-exit-modeled columns on `outcomes` (legacy forward_r/mfe_r/mae_r untouched,
still the same one writer, `outcomes.py`). Honest entry = the NEXT session's open after
candidate_date (recorded as `entry_fill`, diagnostic only). The R unit's denominator AND
numerator reference price are the PLAN's own entry/stop (not re-derived from the fill), so a
name that gaps through its stop before the fill even happens prints an honest R far worse than
-1 instead of being silently dropped or laundered into a near-zero "the bad fill absorbed the
gap" reading. Each day the walk checks gap-through-stop (open <= stop) before intraday stop
(low <= stop) before favorable excursion (documented conservative convention -- no intraday
sequencing available); stop fills take a 0.2% slippage haircut; no touch within the window
exits at the T+10 close (`horizon_close`). New columns: `entry_fill`, `exit_date`,
`exit_price`, `exit_reason` (stop|gap_through_stop|horizon_close), `managed_r`,
`managed_mfe_r`, `managed_mae_r`, `hit_1r`, `hit_2r`. `expectancy._system_observations()` now
reads `managed_r` (falls back to `forward_r` only for legacy rows predating the new columns).

Reran the full backfill and `expectancy.run()` over the same as_of (2026-07-09), idempotent,
rows updated in place -- same 55 completed T+10 observations as before (92 persisted
candidates total; the rest still pending/incomplete window).

**Corrected numbers (managed / stop-exit-modeled R, same 55 observations):**

| family | regime | n | stop-exit rate | avg R | median R | avg MFE | avg MAE | hit_1R% |
|---|---|---|---|---|---|---|---|---|
| base/pattern | SELECTIVE | 21 | 95.2% | -1.29R | -1.19R | -1.11R | -1.38R | 4.8% |
| catalyst | DEFENSIVE | 5 | 100.0% | -1.62R | -1.16R | -1.62R | -1.72R | 0.0% |
| catalyst | SELECTIVE | 29 | 93.1% | -1.13R | -1.06R | -0.43R | -1.33R | 13.8% |

Exit reasons across all 55: stop 32, gap_through_stop 20, horizon_close 3.

What the old numbers measured vs the new: the old -1.15R/-2.49R was the average of an
unmanaged, never-exited hold to T+10 close, inflated by a handful of extreme same-name losers
(ETERNAL alone printed +7.58R and +11.0R unmanaged on the same two dates that come out at
-1.20R/-0.12R once stop-managed -- an 8-12R swing from methodology alone). The new -1.13R to
-1.62R is bounded the way a real stop-honored system must be: never far below -1R except via
the specific, named failure mode (gap-through-stop), never above +1R on average.

Honest verdict on the gate: still no edge. Hit rate at +1R is 0-14% and every cell's mean R is
solidly negative. Managed exits fixed the measurement, not the setups -- the passed cohort is
not shown to have an edge under honest, stop-respecting execution. No gate threshold changed.

Three most plausible causes, from the data, in order of how much of the loss they explain:
1. Entry-gap cost dominates. 20 of 55 exits (36%) are gap_through_stop -- the very next session
   already opened through the stop before the trade could be managed at all. This is the
   single largest driver of the loss and is a genuine cost of trading NSE small/mid names off a
   T+0 signal with a next-open fill assumption; a same-day intraday entry (if the live system
   actually offers one) would cut this materially.
2. Stops may be tight relative to this regime's volatility for these families. 93-100% of
   trades in every cell hit the stop (vs hit_1R% of 0-14%) -- an almost-binary stop-or-nothing
   outcome distribution, the signature of a stop placed inside the name's normal noise band
   rather than beyond it, not of a directionally wrong setup.
3. Regime window characteristics (2025-03..2026-07). All three cells with any observations are
   SELECTIVE/DEFENSIVE regimes -- the cascade produced zero passed survivors in RISK_ON or
   NO_TRADE across the full 285-session replay. A gate this selective, firing only in cautious
   regimes, may be systematically catching falling-knife setups rather than the momentum
   continuation the family names imply; worth auditing `candidate_for_symbol`'s entry timing
   against a handful of hand-picked losers (as the E1-PERSIST entry already recommended, and
   which this fix does not supersede).

Tests: `manas_os/tests/test_performance_and_outcomes.py` gained three fixture cases (stop hit
day 2 -> ~-1.04R, runner -> +1.8R realized / +2.0R MFE with hit_2r=1, gap-through-stop ->
-4.03R recorded honestly, not floored or hidden). 343 passed (was 340), no regressions.

## 2026-07-10 — SHIP-1 #8: screener-hit forward-return calibration (`manas_os/ml/screener_calibration.py`)
New writer: `screener_calibration(as_of, screener, horizon, n, avg_excess_pct, median_excess_pct,
win_rate, baseline_win_rate, baseline_n)`. Per ChartsMaze `screener` key, per T+5/T+10/T+20
horizon: entry = next session's open after the hit's `trade_date` (same honest-fill convention
as `scanner/outcomes.py`), exit = the horizon-th session's close (unmanaged -- a screener hit
carries no stop/plan, unlike a persisted setup candidate). Baseline (documented choice): a
deterministic stride-sampled universe baseline (alphabetical, every Nth EQ symbol, capped at 60
names/date), pooled across every distinct hit-date and shared globally per horizon -- NOT a
per-screener exact-date-matched baseline, and NOT the full ~2000-symbol universe (too slow
nightly). n<30 rows are computed and persisted (never dropped) but flagged `unproven` at read
time via `TRUST_FLOOR_N=30`, matching the `scanner/expectancy.py` trust-ladder convention.
Wired into `run-eod` as its own pipeline stage (`screener_calibration`, failure-safe, after
`candidate_outcomes`) and surfaced on `/api/desk/track-record` -> `screener_calibration` (top-10
horizon, ranked desc by avg_excess_pct) -> LEDGER tab's new "WHICH SCREENERS PREDICT" panel.

**Actual result on the real DB, run 2026-07-10: the ranked table is EMPTY (0 rows, every
horizon).** Root cause is the same one already logged 2026-07-06 above: `screener_hits` only
has 5 distinct trade_dates (2026-07-05, 07, 08, 09, 10 -- ChartsMaze scanner ingestion is brand
new), and `daily_prices` only has 3 trading sessions after the earliest hit date (07-06, 07-07,
07-09) -- not even a full T+5 window exists yet for any hit, let alone T+10/T+20. This is a real,
honest finding, not a bug: the pipeline_runs row for this stage logs `status=ok, rows_affected=0`
(a correct "nothing computable yet" result, not a failure). Once ChartsMaze scanner dumps
accumulate ~20+ more trading sessions, T+5 cells will start populating; T+20 needs ~4 more weeks
of daily ingestion before any screener clears the n>=30 trust floor. No screener can be verdicted
yet -- re-run `python -m manas_os.ml.screener_calibration` (or the `run-eod` stage) periodically
and check back once the dates above have real closes past them.

Tests: `manas_os/tests/test_screener_calibration.py` (4 new) -- hand-checked excess-return math
against a seeded price ramp (screener hit vs baseline symbol, both fed through the same
compound-return formula), n<30 suppression flagged via `unproven`, idempotent rerun (same as_of
does not duplicate rows), and a pending-hit-with-no-full-window case correctly excluded from
`compute()`. 347 passed (was 343), no regressions.

## 2026-07-10 — SHIP-1 #7: LightGBM direction classifier, walk-forward validated (`manas_os/ml/direction_lgbm.py`)
New writer: per-(symbol, trade_date) feature builder from data <= date only (leakage-safe by
construction — every feature is a pandas rolling/pct_change/ewm computation, which is backward-
looking; only the label uses future rows, verified by `test_feature_builder_unchanged_when_future_rows_added`).
Features: `ret_5d/20d/60d`, `vol_20d` (rolling std of daily returns), `delivery_pct` level +
20d z-score, `volume_z20`, `dist_from_52w_high` (252d rolling max, `min_periods=60` since this
DB only has ~285 sessions total), `ema_stack_state` (bullish/bearish/neutral EMA5>20>50 stack),
`sector_rel_ret_20d`, `fii_dii_net5d_z`, `bulk_deal_flag_5d`. Target: sign of forward 10-session
return (binary). Trained with LightGBM, walk-forward validated ONLY (expanding window, monthly
refit, scored OOS) — no in-sample number is reported anywhere.

**Data-reality caveats (own the approximations, don't hide them):**
- `daily_prices` (871,954 rows, EQ series only used) is the only full-history table — 285
  sessions, 2025-03-19..2026-07-09, ~2,761 symbols with 200+ days. Price/volume/delivery
  features are the real signal.
- `fii_dii_daily` has 21 rows (2026-06-09..07-08) — the FII/DII z-score feature is 0 (neutral)
  for the ~93% of history before that window. `disclosures` (bulk_deal) starts 2026-01-13 — the
  deal flag is 0 for everything before. Both are real features for the recent months only.
- No point-in-time sector/industry table exists (`universe` is empty on this DB;
  `screener_hits.basic_industry` only covers 2026-07-05..10). `sector_rel_ret_20d` uses a
  STATIC map (each symbol's most-recently-seen `basic_industry`, applied across all history) —
  an approximation, not a point-in-time-correct sector tag. Documented in the module docstring.

**Walk-forward result on the real DB (2,116 EQ symbols, 10 monthly OOS folds, 2025-09..2026-06,
min_train_rows=2000):**

```
month       n      AUC     hit    baseline
2025-09  41038   0.554  0.518  0.460
2025-10  40793   0.568  0.572  0.450
2025-11  38875   0.550  0.582  0.300
2025-12  46071   0.599  0.581  0.447
2026-01  41976   0.654  0.632  0.409
2026-02  41930   0.625  0.684  0.274
2026-03  39727   0.590  0.563  0.462
2026-04  41027   0.599  0.381  0.668
2026-05  36225   0.510  0.579  0.408
2026-06  33740   0.541  0.405  0.627
POOLED      401402   0.544  0.553  0.448
```

Honest verdict: AUC clears 0.5 ("always up" has no AUC — it is a constant predictor) in **10/10**
folds, pooled AUC 0.544. Pooled hit-rate 0.553 vs the naive always-up baseline's 0.448 (+10.5pp),
and the model beats baseline hit-rate in 8/10 folds. It LOSES on hit-rate in exactly the two
strongly trending-up months (2026-04: 0.381 vs 0.668 baseline; 2026-06: 0.405 vs 0.627 baseline)
— unsurprising, since "always up" is trivially strong precisely when the market mostly goes up,
and a real classifier that sometimes calls "down" will underperform it in those months by
construction. The consistent >0.5 AUC across every fold (never a coin flip, never inverted) is
the more meaningful signal here than the hit-rate swings. This is a modest, real, but not
spectacular edge — display threshold (SHIP-1 item 7: "if pooled OOS beats baseline meaningfully")
is judged MET on the strength of the 10/10-fold AUC consistency and the +10.5pp pooled hit-rate,
not a strong claim of alpha. Labeled EXPERIMENTAL everywhere it surfaces, per AD8.

**What got wired (display threshold met):**
- `ml_scores(scan_date, symbol, p_up_10d, top_drivers_json)` table (`db/schema.sql`).
- `ml_direction` pipeline stage in `run-eod` (after `screener_calibration`, before `eod_alerts`)
  — trains on all data strictly before `run_date` (no leakage into today's score), scores the
  current `watchlist` (or an injected shortlist), writes SHAP top-3 drivers. Failure-safe: any
  missing `lightgbm`/error is logged as `pipeline_runs.status='skip'`, never `fail`, and `run()`
  never raises.
- `agents/context_pack.py` `_symbol_block` gains an optional `ml` field (only present if
  `ml_scores` has a row for that symbol/scan_date) with a formatted line: `"ML: P(up 10d)=0.63
  [EXPERIMENTAL] drivers: delivery_z+, sector_rs+"`.
- `/api/desk/debate` (in `api/app.py`) exposes the same `ml` object per symbol; `DebateTab.jsx`
  renders it as an `MlChip` next to the base-rate chip, always carrying the `[EXPERIMENTAL]` tag.
- AD8 grep-verified clean: no import of `direction_lgbm`/`ml_scores`/`manas_os.ml` in
  `scanner/gates.py`, `agents/sizer.py`, `risk/plan.py`, `agents/chair.py`, or `agents/debate.py`.
  This module is read-only-downstream: a fact chip, never a gate/size/composite-score input.

Tests: `manas_os/tests/test_ml_direction_lgbm.py` (7 new) — feature-builder leakage (identical
values at date D whether or not later rows exist in the input frame), label correctly uses
future rows (only the label, not any feature), walk-forward split correctness (every fold's
train max trade_date < that fold's test min trade_date, no overlap/inversion), a synthetic-data
walk-forward smoke run, and three run()-level skip contracts (`lightgbm` absent, empty
shortlist, unexpected exception) all landing a `skip` `pipeline_runs` row and returning `0`
without raising. 354 passed (was 347), no regressions.

## SHIP-1 #9 — delivery% accumulation/distribution tag (fact-only, lift-validation PENDING)

Wrote a rolling ACCUMULATION/DISTRIBUTION tag to `engine/indicators.py` (`_delivery_accum_flag`,
the one writer for this metric — computed alongside every other per-symbol daily feature in
`compute_indicators_for_symbol` and persisted into `features_daily.feature_json` as
`delivery_flag`). Rule, over the trailing N=10 sessions: ACCUMULATION when the 10d avg delivery%
is rising (vs. 10d avg 10 sessions earlier) AND avg delivery% on up-days exceeds avg delivery%
on down-days AND the 10d price return is positive; DISTRIBUTION is the exact mirror. Anything
else (including insufficient history) is NEUTRAL/omitted — never fabricated.

Surfaced in two read-only places, both reading the same `features_daily` row (no recomputation,
no second writer):
- `agents/context_pack.py` `_symbol_block` gains an optional `delivery` field
  (`{"flag": ..., "line": "delivery: ACCUMULATION - rising delivery on up days"}`), omitted
  entirely for NEUTRAL/no-data.
- `/api/desk/debate` (`api/app.py`) exposes a matching fact-only `delivery` chip
  (`{"flag": "ACCUMULATION"}`) per symbol next to the ML/base-rate chips.

**Explicitly NOT done, and not claimed:** no lift/forward-return validation against this tag
has been run. Do not treat ACCUMULATION/DISTRIBUTION as predictive until a screener-hit-style
calibration (per SHIP-1 item 8's pattern: T+5/10/20 excess return vs baseline, n-floored) has
been logged here. Until then this is a fact chip only, same posture as the SHIP-1 #7 ML chip.

Tests: `manas_os/tests/test_indicators.py` gains 3 fixture tests (`test_delivery_flag_accumulation_fixture`,
`test_delivery_flag_distribution_fixture`, `test_delivery_flag_absent_without_delivery_column`)
using synthetic bars engineered to trip each branch. 359 passed (was 352), no regressions.

## 2026-07-10 — Round-4 gate-recalibration EVIDENCE replays (counterfactual, thresholds NOT touched)

Context: the E1-FIX audit above found the gate-PASSED cohort (n=55, window 2025-03..2026-07,
every single one fired SELECTIVE/DEFENSIVE) stopping out 93-100% of the time with avg MFE
mostly never favorable and 36% gap-through-stop. This entry is EVIDENCE ONLY, per explicit
scope: run counterfactual exit-rule replays on the SAME persisted cohort and log honest
numbers so a later, separate recalibration decision has data. No gate/plan threshold was
changed by this work.

**Machinery (new, additive):** `manas_os/backtest/exit_variants.py` — pure functions
(`find_entry_bar`, `walk_managed_exit`) that recompute a managed-exit outcome for one
candidate's already-known bars under a `(stop_multiplier, entry_mode)` variant, reusing the
exact stop-checked-before-favorable sequencing convention and R-vs-plan-entry reference price
documented in `scanner/outcomes._managed_exit`. `x1.0`/`next_open` reproduces that baseline
exactly (verified by construction). Driver script `_gate_recal_evidence.py` (repo-root scratch,
not shipped) pulls the same n=55 cohort (`candidates` JOIN `outcomes WHERE horizon=10 AND
managed_r IS NOT NULL`) used by the E1 audit and re-walks each candidate's own `daily_prices`
bars under every variant below — no rescan, no look-ahead (each variant only reads bars from
the candidate date forward, and only that bar's own OHLC per decision).

**E-A — stop width x1.0 / x1.5 / x2.0 (entry unchanged, next-session open):**

| stop_mult | n  | stopout% | avgR  | medR  | avgMFE | avgMAE | hit_1r% |
|-----------|----|----------|-------|-------|--------|--------|---------|
| x1.0 (baseline) | 55 | 94.5% | -1.24 | -1.08 | -0.80 | -1.39 | 9.1% |
| x1.5      | 55 | 87.3%    | -0.95 | -1.04 | -0.24  | -1.19  | 9.1%    |
| x2.0      | 55 | 72.7%    | -0.76 | -1.03 |  0.07  | -1.06  | 10.9%   |

Per-family (x1.0 -> x2.0): `ipo_base` (n=34) stopout 94.1%->79.4%, avgR -1.20->-0.84;
`pullback_to_ema` (n=20) stopout 95.0%->60.0%, avgR -1.26->-0.62; `shakeout` (n=1, thin)
stopout stays 100%. Wider stops DO convert some MFE into survivals (stopout% drops
materially, avgMFE turns from -0.80 to +0.07) but **median R barely moves** (-1.08 -> -1.03):
the typical trade is still a loser at ~-1R even at x2.0 — the mean improvement is a tail
effect (a few names that eventually recover), not a shift in the typical outcome. hit_1r%
stays flat at 9-11% throughout. Verdict: wider stops mostly buy TIME before the same
structural failure, at 1.5-2x the capital-at-risk per trade for a near-identical median
outcome — not a free win.

**E-B — entry timing: next-open (baseline) vs buy-stop confirmation (skip if next session
never trades above the plan entry/pivot):**

| entry_mode | n  | skipped | stopout% | avgR  | medR  | avgMFE | avgMAE | hit_1r% |
|------------|----|---------|----------|-------|-------|--------|--------|---------|
| next_open (baseline) | 55 | 0  | 94.5% | -1.24 | -1.08 | -0.80 | -1.39 | 9.1%  |
| buy_stop   | 36 (of 55) | 16 | 83.3% | -0.87 | -1.09 | -0.07  | -1.26  | 25.0%   |

Buy-stop confirmation skips 16/55 (29%) candidates outright — these never traded above their
own pivot within the window, i.e. more than a quarter of the "passed" cohort was never a real
breakout to begin with. Of the 36 that DO confirm, stopout% drops 94.5%->83.3% and hit_1r%
roughly triples (9.1%->25.0%), but **median R is unchanged to slightly worse** (-1.08 vs
-1.09) — requiring confirmation filters out some of the worst gap-through-stop names (36%
baseline gap-through rate) but the survivors still lose ~1R more often than not. Read
plainly: buy-stop confirmation does NOT "kill the gap-through-stop cohort" so much as it
removes the ones that were never going to fill live in the first place; it does not fix the
remaining trades' typical outcome.

**E-C — combined (best-of A+B):**

| variant | n (skipped) | stopout% | avgR  | medR  | avgMFE | avgMAE | hit_1r% |
|---------|-------------|----------|-------|-------|--------|--------|---------|
| x1.5 stop + buy_stop | 36 (16) | 69.4% | -0.55 | -1.05 | 0.52 | -1.10 | 25.0% |
| x2.0 stop + buy_stop | 36 (16) | 52.8% | -0.36 | -1.03 | 0.59 | -0.97 | 19.4% |

Best combined variant available (x2.0 + buy_stop): stopout% down to 52.8% (from 94.5%),
avgMFE flips solidly positive (+0.59), yet **median R is STILL negative** (-1.03) and barely
moved from baseline (-1.08). One family cell breaks even in this variant (`pullback_to_ema`,
n=10, medR +0.51 — but n<20, thin, do not generalize) while `ipo_base` (n=25) stays solidly
negative (medR -1.05). Combining both levers roughly doubles capital-at-risk per trade
(x2.0 stop) and discards 29% of the cohort (buy-stop skip) to get avgR to breakeven-adjacent
territory while medR never crosses zero in any pooled cut. This is the ceiling these two
exit-side levers can reach on this cohort.

**E-D — regime split (SELECTIVE vs DEFENSIVE), baseline and two variants:**

| variant | regime | n | stopout% | avgR | medR | avgMFE | avgMAE | hit_1r% |
|---------|--------|---|----------|------|------|--------|--------|---------|
| baseline (x1.0/next_open) | SELECTIVE | 50 | 94.0% | -1.20 | -1.07 | -0.71 | -1.35 | 10.0% |
| baseline (x1.0/next_open) | DEFENSIVE | 5  | 100.0%| -1.62 | -1.16 | -1.62 | -1.72 | 0.0% |
| E-A x2.0/next_open | SELECTIVE | 50 | 72.0% | -0.80 | -1.03 | 0.05 | -1.05 | 10.0% |
| E-A x2.0/next_open | DEFENSIVE | 5  | 80.0% | -0.41 | -1.06 | 0.36 | -1.15 | 20.0% |
| E-B buy_stop/x1.0  | SELECTIVE | 32 | 81.2% | -0.80 | -1.08 | 0.11 | -1.23 | 28.1% |
| E-B buy_stop/x1.0  | DEFENSIVE | 4  | 100.0%| -1.44 | -1.38 | -1.44 | -1.54 | 0.0% |

DEFENSIVE is worse on every metric in every variant tried (still 80-100% stopout even at
x2.0 stop width; 0% hit_1r in 2 of 3 variants) — directionally consistent with "DEFENSIVE is
poison," but **n=4-5 is far too thin to certify this** (below the THIN_N=20 floor used
elsewhere in this codebase). The cohort never fired outside SELECTIVE/DEFENSIVE in this
window (matching the E1 finding), so this split cannot speak to REGULAR/other modes at all.

**5-line verdict:**
1. No exit-side lever tried (wider stop, confirmation entry, or both combined) moves median
   managed R above roughly -1.0 to -1.1 for this cohort — only the MEAN improves, driven by a
   thin tail of eventual recoveries, not a change in the typical trade.
2. Wider stops buy time and cut stopout%, at the cost of 1.5-2x capital-at-risk per trade,
   for a near-identical median outcome — not a free win.
3. Buy-stop confirmation correctly identifies that 29% of the "passed" cohort never traded
   above its own pivot (never a real breakout) but does not fix the remaining trades' median.
4. DEFENSIVE regime looks directionally worse everywhere tried, but n=4-5 per cell is too
   thin (below THIN_N=20) to certify — flag for a larger-window rerun, not a verdict.
5. **The detectors, not the exits, are wrong.** Every exit-side lever available (stop width,
   entry confirmation, or both) tops out with median R still negative on this exact cohort —
   the honest reading is that entry-quality work (what the gates let through in the first
   place) is where the next investigation belongs, not further tuning of how a losing trade
   is exited. Thresholds remain LOCKED per this task's scope; this is evidence for a later,
   separate recalibration decision.

New: `manas_os/backtest/exit_variants.py` (pure functions, one writer) +
`manas_os/tests/test_exit_variants.py` (9 new fixture tests: baseline-reproduces-x1.0,
wider-stop-survives-same-dip, stop-multiplier-scales-denominator, buy-stop-skip-when-never-
confirmed, buy-stop-fills-on-gap vs -intraday-cross, invalid-plan/incomplete-window guards,
gap-through-stop still recorded honestly). 390 passed (was 378 at task handoff baseline; the
delta above 378+9=387 is pre-existing untracked `test_sources_fii_dii.py` additions already in
the working tree, unrelated to this task), no regressions.

## SHIP-1 #17 (I5) — HMM regime confirmation gate (2026-07-10)

Built `manas_os/regime/regime_hmm.py`: 4-state GaussianHMM (hmmlearn, 10
random restarts kept by best training log-likelihood), features = log
return, 5d/20d realized vol, breadth z (net advances-declines rolling
20d z — **substituted for "volume z"**: NIFTY 50 in sector_index_prices
carries no volume column, only close/sma50), 10d momentum. Fold-scoped
StandardScaler fit on the TRAIN fold only, monthly expanding-window
walk-forward (same discipline as vol_har.py/direction_lgbm.py). State->label
mapping is deterministic and post-hoc: rank states by
`mean_return - 0.5*mean_vol_20d` on the TRAIN fold, map rank 0..3 onto the
SAME vocabulary regime_snapshots.market_mode already uses (RISK_ON /
SELECTIVE / DEFENSIVE / NO_TRADE) so the agreement check is apples-to-apples.

**Real-data validation (285 causally-backfilled sessions, 2025-03-19 ..
2026-07-09; feature frame bounded to that window since breadth_daily starts
there even though NIFTY 50 prices go back to 2024-07-08):**

- Walk-forward: 9 monthly folds, 265 clean feature rows -> 165 out-of-fold
  labeled sessions. **Flip rate 17.7%** (state changes on ~1 session in 6) —
  reasonably sticky, not flapping every day.
- **Contingency vs XP/MBI market_mode, n=165, agreement_rate = 18.8%.**
  This is WORSE than the ~25% a 4-way random guess would get on this sample
  — read plainly, the HMM's own state ranking (by risk-adjusted mean return)
  does NOT track XP/MBI's label on this window. Table (rows=HMM label,
  cols=market_mode count): DEFENSIVE-HMM mostly landed on SELECTIVE-market_mode
  (68/96); RISK_ON-HMM landed on SELECTIVE 13/22 and DEFENSIVE 8/22 (barely
  ever matching market_mode's own DEFENSIVE reads); market_mode's NO_TRADE
  sessions were scattered almost evenly across all 4 HMM labels. **This
  history's market_mode distribution itself has no RISK_ON at all** (only
  SELECTIVE/DEFENSIVE/NO_TRADE occur, see regime_snapshots query) — the HMM's
  4th, most-bullish rank has nothing to agree WITH there, which mechanically
  caps agreement_rate on this sample; this is a genuine finding about label
  taxonomy mismatch, not just noise, and would need re-running once RISK_ON
  sessions exist in the live history.
- **Regime-conditional forward-5d NIFTY return** (validation-only, never fed
  to the HMM): RISK_ON n=22 mean +0.43%/median +0.56%; DEFENSIVE n=91 mean
  +0.06%/median -0.16% (flat, largest bucket); SELECTIVE n=24 mean
  -0.65%/median -0.62%; NO_TRADE n=23 mean -1.02%/median -0.81%. RISK_ON vs
  NO_TRADE ordering is directionally sane (best vs worst), but SELECTIVE
  reading WORSE than DEFENSIVE inverts the market_mode ordering intuition —
  another honest sign the HMM's own internal ranking doesn't line up with
  the desk's existing semantics for the middle two labels.

**Verdict:** the HMM state sequence is stable (low flip rate) and its two
extreme labels (RISK_ON/NO_TRADE) carry directionally sensible forward-return
information, but it does NOT currently confirm XP/MBI market_mode
(agreement_rate 18.8%, below chance) and its middle two labels are
inverted relative to market_mode's own risk ordering on this sample. Per the
locked RENDER RULE this is exactly why the label stays hidden behind the
20-live-session `display_gate()` regardless of this agreement number — XP/MBI
remains the sole authority, and this is logged so a future re-run (once
RISK_ON sessions exist and n grows past 165) isn't a surprise if the
disagreement persists.

New: `manas_os/regime/regime_hmm.py` (one writer) + `manas_os/tests/test_regime_hmm.py`
(15 new tests: feature causality, state-label mapping determinism x3, display-gate
n<20/n==20/backfill-source-excluded, caption text x3, stage skip w/o hmmlearn + w/
insufficient history x2, end-to-end walk-forward+validation smoke, end-to-end run()
persists a row). Wired: `hmm_regime` table (db/schema.sql), `regime_hmm` nightly stage
(cli/__init__.py, after `regime_vol_har`), `hmmlearn>=0.3` (requirements.txt),
`run_card._regime()` now calls `regime_hmm.get_display_caption()` and adds
`hmm_caption`/`hmm_display_allowed`/`hmm_sessions_counted` to the card's `regime` block,
`DeskTab.jsx` renders that caption verbatim via a new `HmmCaption` component (never the
raw label). 410 passed (was 395 baseline + 15 new), no regressions.

## 2026-07-10 — WAVE_J entry-quality counterfactual evidence (J3/J4): NEGATIVE, no threshold change proposed

**Scope guard honored:** no gate/plan/gates.py threshold touched. All refusals
(`scanner/entry_quality.py`) and the composer (`backtest/entry_variants.py`) run in
counterfactual replay only, over the SAME n=55 persisted candidates/outcomes cohort
(horizon=10, `managed_r IS NOT NULL`) used by the Round-4 gate-recalibration evidence.
Driver: `_wave_j_entry_evidence.py` (repo-root scratch, mirrors `_gate_recal_evidence.py`;
read-only against `manas_os/data/manas.db`; prints tables, persists nothing).

**Baseline (no refusals): medR = -1.08, n=55, stopout 94.5%, hit_1r% 9.1%** — reproduces
the E1 finding exactly (this is the same cohort, same walk_managed_exit, entry_mode
next_open/stop_mult 1.0).

**Cohort composition caveat (binding on everything below):** the persisted cohort is
almost entirely `IPO Base` (43/55) and `Pullback-to-EMA` (11/55), one `Shakeout`; nearly
every family x regime cell is n<20 (THIN) even at baseline, and NONE of the H4/H5/H6-
inclusive variants clear n>=20 — every richer combination is data-starved, not just
insufficiently improved. RISK_ON regime is absent from the whole 2025-07..2026-06 window
(same limitation the HMM entry above already logged for this history).

**Per-variant results (ALL rows, family x regime cells all THIN <20 except where noted):**

| variant | n | stopout% | avgR | medR | avgMFE | hit1r% |
|---|---|---|---|---|---|---|
| baseline | 55 | 94.5% | -1.24 | -1.08 | -0.80 | 9.1% |
| H1 (compression) | 28 | 92.9% | -1.10 | -1.06 | -0.44 | 14.3% |
| H2 (leg-freshness) | 29 | 89.7% | -1.17 | -1.08 | -0.77 | 10.3% |
| H3 (buy-stop confirm) | 36 | 83.3% | -0.87 | -1.09 | -0.07 | 25.0% |
| H1+H2 | 13 | 84.6% | -1.05 | -1.08 | -0.32 | 23.1% |
| H1+H2+H3 | 7 | 71.4% | -0.88 | -1.08 | 0.39 | 42.9% |
| H1+H2+H3+H4 | 0 | — | — | — | — | — |
| +H5 | 0 | — | — | — | — | — |
| +H6 | 0 | — | — | — | — | — |

H4's trigger-day-quality bar (strong_start AND gap<=5% AND close-upper-half AND
volume-confirm) refuses every single one of the 7 H1+H2+H3 survivors — the combined
bundle has ZERO eligible trades. This is itself informative (H4 is the tightest filter
in the cascade by far on this cohort) but leaves nothing to evaluate for H4/H5/H6-
inclusive bundles; H5's own data coverage is separately capped (`NIFTYMIDSML400` in
`sector_index_prices` only reaches back to 2026-01-01 — 25 of the H1+H2+H3+H4-surviving-
minus-refused candidates predate that and were excluded from H5 runs as a DATA GAP, not
a refusal, and logged separately from the removed-cohort table per WAVE_J_SPEC §4).

**Removed-cohort (paired) test, WAVE_J_SPEC §3.4(3):** the removed cohort's own
standalone (unrefused) R never sits clearly worse than the kept cohort's — H1's removed
standalone medR=-1.19 vs H1-kept medR=-1.06 (removed<=kept: **True**, the only variant
where this pans out); H2 kept medR=-1.08 vs removed standalone medR=-1.08 (roughly tied,
**False**); H3, H1+H2, H1+H2+H3 all show removed<=kept **False** (the refusal is not
reliably dropping the worse names — it's thinning close to randomly on this n).

**Two-sub-window replication, WAVE_J_SPEC §3.4(4):** cohort dates only span
2025-07-09..2026-06-23 (not the full 2025-03..2026-07 spec window — no candidates exist
before 2025-07-09), so "2025-03..2025-12" in practice means 2025-07..2025-12 here (n=9-15
per variant) vs "2026-01..2026-07" (n=4-40). Both sub-windows are negative for every
variant (medR always <= -0.74, `both windows >=0: False` on every row) — same sign
(both negative) but neither ever approaches +0 let alone +0.3R.

**§3.4 pass/fail per hypothesis (all four criteria required in an n>=30 cell):**
- H1 (compression): (1) medR -1.06 < +0.3R **FAIL**. (2) hit_1r% 14.3% < 33% **FAIL**.
  (3) removed<=kept **PASS** (only hypothesis to pass this leg). (4) both windows
  negative, not >=0 **FAIL**. **Overall: FAIL**, 3/4 criteria miss; n=28 also misses the
  n>=30 trust floor.
- H2 (leg-freshness): (1) **FAIL** (medR -1.08). (2) **FAIL** (10.3%). (3) **FAIL**
  (removed roughly tied with kept). (4) **FAIL**. n=29, still below floor. **Overall: FAIL.**
- H3 (buy-stop confirm): (1) **FAIL** (medR -1.09, unchanged from baseline — confirms the
  spec's own prediction that H3 moves hit_1r%/trade-count, not the median). (2) hit_1r%
  25.0% closer to the 33% bar but still **FAIL**. (3) **FAIL**. (4) **FAIL**. n=36 clears
  the floor but the bar itself is not cleared. **Overall: FAIL**, though hit_1r% direction
  is the most encouraging single number in this wave (25% vs 9.1% baseline, avgMFE flips
  from -0.80 to -0.07) — worth a mention in a future proposal, not a pass today.
- H1+H2 / H1+H2+H3 (coherent bundle, pre-registered as most-likely): n=13 and n=7 —
  never approach the n>=30 floor; every §3.4 criterion **FAIL** or unmeasurable at this n.
  **Overall: FAIL** (data-starved, cannot be evaluated to the bar regardless of direction).
- H4 (trigger-day quality): combined with H1+H2+H3 -> n=0. **Overall: FAIL / UNMEASURABLE**
  — cannot evaluate any §3.4 criterion with zero survivors.
- H5 (mswing) / H6 (burst exhaustion): both stacked on an already-empty H1+H2+H3+H4
  population -> n=0. **Overall: FAIL / UNMEASURABLE.** H5 additionally has its own
  independent data-coverage ceiling (index history only from 2026-01-01) that would cap
  it even with survivors upstream.

**Verdict (5 lines):**
1. No variant clears the §3.4 bar; this is a genuine negative/directional result, not a
   near-miss — most cells are THIN (<20) or empty, and the honest read is "not enough
   surviving trades to judge," not "no edge."
2. H3 (buy-stop confirmation) is the closest to directionally interesting — hit_1r%
   9.1%->25.0% and avgMFE -0.80->-0.07 with n=36 (above the floor) — but median managed R
   is flat, exactly matching the E-B finding this spec cites; not sufficient alone.
3. H1 is the only hypothesis whose removed cohort is confirmed worse than its kept
   cohort (§3.4 criterion 3 passes) — directionally consistent with the compression-gap
   diagnosis, but the other three criteria still fail and n=28 misses the floor.
4. H4 eliminates the ENTIRE H1+H2+H3 survivor set (7->0) — either H4's thresholds are
   too strict for this cohort's family mix (dominated by IPO Base, which the trigger-day
   quality check may not suit) or the population genuinely never had a qualifying
   trigger day; cannot distinguish those from n=55 alone.
5. What would be needed: an order of magnitude more candidates per family x regime cell
   (n>=30 per cell, not per whole-cohort total — so roughly 150-300+ total candidates
   given the current family mix) plus RISK_ON-regime sessions (absent from this window
   entirely) and NIFTYMIDSML400 index history back-filled to 2025-03 before H5 can even
   be attempted on the earlier sub-window. No threshold change is proposed; J5 is not
   written.

New: `_wave_j_entry_evidence.py` (scratch, not shipped). No production files touched by
J3/J4 (scanner/entry_quality.py and backtest/entry_variants.py were J1/J2, already landed
and unchanged here). Full suite re-run after this evidence pass: 454 passed (unchanged
from the J1/J2/J6 baseline — no test or production code was modified in J3/J4).


## 2026-07-10 — WAVE_J7 sample-expansion replay: expanded counterfactual cohort (n=19,001), §3.4 bar STILL FAILS, direction confirmed for H3, H2 flips negative at scale

**Why:** the J3/J4 entry above failed the pre-registered §3.4 bar mostly on starved cells
(n=55 total; every cell THIN). This wave expands the cohort per (family x regime) cell to
well past the 150-300 target by replaying the FULL confluence pool per session and keeping
every name that either passed all gates or failed ONLY a soft gate (trend-template /
fresh-leg / participation — the same SOFT_GATES set the debate stage uses). Thresholds
UNCHANGED, a-priori, same §3.4 bar, same driver, same walk_managed_exit exit modeling
(WAVE_J_SPEC §4 no-tuning honored; nothing in gates.py/plan.py touched).

**Plumbing (one writer each, scan_candidates stays pure):**
- `sector_index_prices` backfilled from NSE ind_close_all archives for 2025-03..2026-01
  (all 185 indices; NIFTYMIDSML400 now 358 rows 2025-03-03..2026-07-09, India VIX 333,
  NIFTY 50 unchanged full 2y) — the H5 data-gap named in the J3/J4 entry is CLOSED.
- `backtest/replay.py persist_counterfactual(conn, start, end)`: per session, re-runs the
  IDENTICAL `candidate_for_symbol` cascade (same plan path — entry/stop are the real
  one-writer numbers, no second formula) over the confluence pool + detector shortlist,
  and persists survivors + soft-gate-only refusals into NEW tables
  `counterfactual_candidates` / `counterfactual_outcomes` (schema.sql). Idempotent
  (delete-then-insert per session). NEVER writes scan_candidates/candidates/outcomes/
  refusals — tested (`tests/test_wave_j7_counterfactual.py`, 3 tests: purity guard,
  idempotency, managed-exit fixture on the new table).
- `scanner/outcomes.py backfill_counterfactual_outcomes`: same `_managed_exit` walk as the
  real cohort (shared exit-model writer), horizon=10 only.

**Coverage (task 3):** 285-session window 2025-03-19..2026-07-09; 233 sessions produced
counterfactual candidates (52 sessions had no confluence pool rows — screener history does
not cover every early-2025 session); 20,408 candidates persisted, 19,001 with a complete
T+10 managed outcome. n per (family x regime), pre-hypothesis:

| cell | n | vs 150-300 target |
|---|---|---|
| base/pattern x SELECTIVE | 18,160 | cleared (60x) |
| catalyst x SELECTIVE | 703 | cleared |
| catalyst x DEFENSIVE | 138 | just under 150 — directional |

(The n=55 cohort's ipo_base/pullback families do not appear as cells here because family
is the CASCADE's setup_family of the pool name at scan time, and the near-miss population
is overwhelmingly generic base/pattern. RISK_ON remains absent from the entire tape —
unmeasurable, as pre-registered.)

**SELECTION-EFFECT CAVEATS (binding on interpretation, named per task):**
1. **Refused-population bias:** 18,946 of 19,001 are names the live cascade REFUSED at a
   soft gate. They are not survivors; a soft-gate refusal is correlated with exactly the
   staleness/weak-trend/low-participation defects the entry hypotheses probe. Effects
   measured here may be larger (more junk to remove) or smaller (junk already labeled)
   than they would be on a true survivor population.
2. **Synthetic plans:** their entry/stop come from the same one-writer plan code, but no
   human/agent ever acted on them; no debate/chair overlay ever filtered them.
3. **Survivorship asymmetry vs n=55:** the real cohort passed rank/grade assignment and
   persistence timing; counterfactuals skip all of that. Baseline medR here is -1.38 vs
   -1.08 for the real n=55 — the populations measurably differ before any hypothesis runs.
4. **One-tape bias unchanged:** still one 16-month SELECTIVE/DEFENSIVE tape.

**Expanded-cohort results (ALL row per variant; baseline medR -1.38, hit_1r 7.5%):**

| variant | n | stopout% | avgR | medR | avgMFE | hit1r% |
|---|---|---|---|---|---|---|
| baseline | 19,001 | 92.6% | -1.48 | -1.38 | -1.19 | 7.5% |
| H1 (compression) | 3,032 | 94.1% | -1.32 | -1.25 | -1.12 | 4.9% |
| H2 (leg-freshness) | 13,078 | 93.4% | -1.61 | -1.54 | -1.34 | 6.9% |
| H3 (buy-stop confirm) | 11,462 | 63.1% | -0.24 | -1.04 | +0.84 | 38.3% |
| H1+H2 | 1,775 | 95.5% | -1.41 | -1.35 | -1.26 | 3.7% |
| H1+H2+H3 | 1,053 | 61.7% | -0.28 | -1.04 | +0.74 | 37.4% |
| H1+H2+H3+H4 | 3 | 0.0% | +0.33 | +0.25 | +2.02 | 66.7% (THIN) |
| +H5 / +H6 | 1 | 0.0% | +0.25 | +0.25 | +3.37 | 100% (THIN) |

Best n>=30 sub-cell: catalyst/SELECTIVE under H1+H2+H3 — n=46, medR -0.36, hit_1r 47.8%,
stopout 41.3%. Removed-cohort paired tests: H1 removed standalone medR -1.42 vs kept
-1.25 (**True**); H3 removed -1.82 vs kept -1.05 (**True**, and by a wide margin);
H1+H2+H3 removed -1.39 vs kept -1.04 (**True**); H2 removed -1.11 vs kept -1.54
(**False — INVERTED**: on this population H2 keeps the WORSE names).

**Two-sub-window replication:** every variant negative in BOTH windows (2025-03..12 and
2026-01..07), same sign, medians -1.03..-1.56 — stable, but §3.4(4) requires both >= 0:
fails everywhere. H1+H2+H3 second window avgR +0.04 is the only positive mean anywhere at
n>=30; median still -1.03.

**§3.4 verdicts (UNCHANGED thresholds; all four criteria in an n>=30 cell):**
- **H1: FAIL** — (1) medR -1.25 FAIL; (2) 4.9% FAIL (hit_1r actually WORSENS vs baseline
  on this population, opposite of the n=55 direction); (3) removed<=kept PASS; (4) FAIL.
- **H2: FAIL, now with evidence of harm** — kept cohort (medR -1.54) is WORSE than both
  baseline and its own removed cohort (-1.11). At n=13,078 this is no longer a small-n
  ambiguity: on soft-gate near-misses, the leg-freshness refusal removes the better names.
  (Caveat 1 applies — a stale-leg refusal may behave differently on true survivors — but
  as counterfactual evidence goes this is a genuine red flag for H2 as specced.)
- **H3: FAIL on the bar, direction CONFIRMED at scale** — (1) medR -1.04 FAIL; (2) hit_1r
  38.3% PASSES the 33% leg (n=11,462; also 38.4/31.2/38.5% in all three cells separately);
  (3) kept -1.05 vs baseline -1.38 = +0.33R short of the +0.5R leg (FAIL), removed<=kept
  PASS with the removed cohort at -1.82 (phantom entries are catastrophically worse, as
  E-B predicted); (4) FAIL (both windows negative). 2 of 4 legs pass, replicated across
  both sub-windows and all cells.
- **H1+H2+H3 bundle: FAIL** — same shape as H3 alone (medR -1.04, hit_1r 37.4%); adding
  H1+H2 on top of H3 buys nothing on this population (H2 subtracts).
- **H4/H5/H6: UNMEASURABLE even at n=19k** — H4 stacked on H1+H2+H3 leaves n=3. H4's
  strong-start bar is near-unpassable for this population; that is now established on a
  19k sample, not a 55 one. H5/H6 never got a population to act on (H5's former data gap
  is closed — the n=1 is upstream starvation, not missing index history).

**Verdict (5 lines):**
1. The pre-registered §3.4 bar FAILS on the expanded cohort for every hypothesis — with
   cells 60x past the trust floor, this is now a REAL negative, not a data-starved one.
2. H3 (buy-stop confirmation) is the one live finding: hit_1r 38% (> the 33% leg) at
   n=11,462, replicated in both sub-windows and every cell, and its removed cohort
   (never-confirmed phantoms, medR -1.82) is by far the worst population identified in
   any Manas replay to date. It moves hit-rate and MFE, not the median — exactly as
   pre-registered. Not proposable alone under §3.4, but the strongest candidate for a
   future re-specced bar.
3. H2 as specced is evidence-of-harm on this population (keeps worse than it removes at
   n=13k) and H1 worsens hit_1r at scale — the n=55 directional reads for both were
   small-n noise. The H1+H2 half of the "coherent bundle" is dead on this evidence.
4. Median managed R stays pinned near -1.0 under EVERY entry filter — whatever is wrong
   with this population, entry selection alone cannot push the median positive; the
   phantom-removal (H3) + everything-else-stops-out signature says most of these names
   simply stop out even after confirmation.
5. Selection effects (caveats 1-3 above) cap what this cohort can prove: near-misses are
   not survivors. But the direction of the caveat cuts AGAINST rescuing H1/H2 (they had
   maximal junk available to remove and still failed) and does not manufacture H3's
   phantom finding, which is mechanical. No threshold change proposed; J5 stays unwritten.

New/changed: `backtest/replay.py` (+persist_counterfactual), `scanner/outcomes.py`
(+ensure_counterfactual_schema/+backfill_counterfactual_outcomes), `db/schema.sql`
(2 new tables), `tests/test_wave_j7_counterfactual.py` (3 tests),
`_wave_j_entry_evidence.py` extended (Part A n=55 preserved verbatim for comparison,
Part B expanded cohort), `scripts/import_nse_index_history.py` run against manas.db
(NSE alias row "Nifty MidSmallcap 400" merged into NIFTYMIDSML400). Known side effect:
`test_sector_downside.py::test_walk_forward_..._beats_baseline` now FAILS because its
locked hyperparameters were grid-searched against the PRE-backfill (VIX-history-starved)
panel — flagged for a separate re-tuning wave; the backfilled data is real and stays.

## 2026-07-10 — WAVE K2: BASELINE RECALL vs practitioner picks (the number behind the complaint)
Label set: 19 practitioner picks (CHARTGYM headers, Tightness Study, 6 Manas Entry, GROWW,
RAIN); 12 mappable to our price history. Method: rebuild the CURRENT candidate pool
(confluence_pool UNION detector_shortlist) point-in-time for each pick's entry date.
RESULT:
- Pool recall (either entry day or day-before): 3/12 = 25% (COALINDIA, CHENNPETRO, GROWW).
- GATE-SURVIVOR recall: 0/12 = 0%. Not one of the master's actual trades would have been
  surfaced as a candidate by the tool.
- 9/12 never entered the pool at all: every reversal (BSOFT, ZENTEC x3, NCC), every
  pullback/strong-start off-highs name (PARAGMILK, TATAINVEST, EMS, INTELLECT) — consistent
  with WAVE K mismatch 1 (52w-high anchor) and 2 (no velocity gate).
- GROWW: in pool both days, killed by risk gate (absolute stop cap + nearest-resistance
  R:R). RAIN (separate autopsy): found daily by screeners, regime-family-killed 5x —
  fixed 2026-07-10 (regime -> soft gate + momentum-ranked debate slots).
VERDICT: the user's complaint is quantified — survivor recall 0%. WAVE K Stage-1 sensitive
bucket (K3/K4) is judged against this 25%/0% baseline; target: pool recall >= 90% of
mappable picks, survivor/debate-surface recall >= 60%.

## 2026-07-10 — WAVE K3+K4+K6: Stage-1 SENSITIVE BUCKET built + recall delta (HONEST: target missed)
Built: `scanner/discovery_metrics.py` (K3 one-writer metrics: adr20, purple_dot_count_60d
[>5% on >5L vol, groww2/CH3.1], pct_up_from_65d_low, correction_depth_from_leg_high,
prev_day_tightness_pctile, range_contraction_flag, persistency counts via ported
manas_indicators; 15 unit tests) and `scanner/discovery.py` (K4 build_bucket per
PLAYBOOK_TO_TOOL_MAP §B; COUNTERFACTUAL ONLY -> new `discovery_bucket` table; nightly
stage registered after scan_candidates, failure-safe; 4 tests). All thresholds
corpus-cited in code comments; none invented, none tuned post-hoc.

RECALL DELTA (12 mappable practitioner picks, entry day OR day-1):
| metric                  | baseline (K2) | new Stage-1 bucket |
|-------------------------|---------------|--------------------|
| pool/bucket recall      | 3/12 = 25%    | 3/12 = 25%         |
| gate-survivor recall    | 0/12 = 0%     | n/a (no gating this wave) |
Per-label-archetype: busted_reversal 2/4 (was 0/4), strong_start 1/6 (was 2/6),
reversal 0/1 (was 0/1), ipo_velocity 0/1 (was 1/1).
Caught: PARAGMILK (pullback_to_rising_ma+reversal+strong_start_ready), ZENTEC 13-Mar
and 16-Mar (pullback_to_rising_ma). GROWW: NOT in bucket — pct_up_from_65d_low 28.7%
vs the >=30% floor (knife-edge miss; mom_pctile 55.5 vs 60). RAIN (separate autopsy,
2026-07-09): IS in bucket via persistent_momentum.

MISSED (9/12) — exact failing condition (both entry day and day-1):
- CHENNPETRO 17-Oct: buying force (16.5% off 65d low; mom_pctile 48.6)
- COALINDIA 10-Oct: buying force (4.3%; mom_pctile 52.9)
- EMSLIMITED 6-Nov: BASE eligibility — 30d avg vol 1.27L < 2 lakh floor
- INTELLECT 21-Aug: passed force+velocity but NO archetype fired (tightness_pctile 95
  on entry day — the Tightness-Study "tight prev day" is not visible in our daily bars
  for this date; persistency counts reset by a recent 10/21EMA break)
- TATAINVEST 5-Jun: buying force (24.3%; mom_pctile 46.1)
- BSOFT 12-Jun: buying force (3.1%; mom63 -14.9%)
- NCC 10-Mar: buying force (7.4%; mom63 -13.8%)
- ZENTEC 24-Feb: buying force (8.3%; mom_pctile 51.5)
- GROWW 9-Jul: buying force (28.7% vs 30%)
ROOT CAUSE, stated plainly: the spec's own Stage-1 AND-structure (buying force AND
velocity AND archetype) re-kills the reversal/pullback picks the wave exists to admit.
Arora buys these names 3-5 red days INTO a correction — exactly when pct_up_from_65d_low
is at its lowest and 63d momentum is negative. The buying-force gate is measured at the
worst possible moment for a reversal entry. A recall >=90% bucket needs buying force
measured on the PRIOR leg (e.g. pct-up-from-65d-low as of the leg high / before the
pullback), or buying-force waived for reversal/pullback archetypes — both are THRESHOLD-
STRUCTURE changes requiring a corpus re-read, NOT a number to quietly fiddle. Left for
the next wave with this evidence.

BUCKET SIZE: 181-428/day (median 362, sample = every 3rd of last 60 sessions; 0/20 in
the 30-80 target band). Oversized mainly via pullback_to_rising_ma + persistent_momentum
tag frequency (3.9k tags each across sample). Sensitivity was the K4 instruction
(recall-optimized), but 30-80 needs Stage-2 ranking (K5) or archetype tightening.
Files: scanner/discovery_metrics.py, scanner/discovery.py, db/schema.sql
(+discovery_bucket), cli/__init__.py (+discovery_bucket stage),
tests/test_discovery_metrics.py, tests/test_discovery_bucket.py,
_wave_k_recall_baseline.py (extended), _wave_k_miss_diagnosis.py, _wave_k_bucket_sizes.py.
Tests: 483 passed, 1 known sector_downside failure (pre-existing, flagged WAVE J7).

## 2026-07-10 — WAVE K7: reversal re-anchor + size-control fix (recall 2/12 -> 5/12, sizes ~120)
STRUCTURAL CAUSE (confirmed by the updated _wave_k_miss_diagnosis.py, which now mirrors the
real per-archetype branching instead of treating buying force as a hard early gate):
Arora's reversal/pullback buys sit at momentum BOTTOMS (BSOFT +1.5% off 65d low with
mom_pctile 5; NCC +7.4%; ZENTEC +8.3%) — any current-force OR current-momentum requirement
structurally excludes them, and even K4.1's leg_force_from_65d_low (60d window) fails when
the prior leg predates the lookback (month-long corrections). Fixes, all corpus-cited in
code:
1. Reversal archetype (scanner/discovery.py): NO current-force. (a) prior strength = 180d
   max high >= 1.5x the 252d low OR 63d momentum top-40pctile at ANY point in the last 120
   sessions (rolling max vs today's pctile-cutoff value, computed cheaply); (b) correction
   15-40% off the 180d high; (c) trigger = 3-5 consecutive down days on lighter-than-
   20d-avg volume followed by an up day, OR first close above the 10SMA after >=10
   sessions below [6 Manas Entry: strong prior uptrend on a longer frame + 3-5 down days
   on declining volume + first strength day].
2. Pullback-to-rising-MA: 180d prior-strength branch added as an alternative to the 60d
   leg-force gate (band <=40% off the 180d high); PLUS an actual-pullback requirement
   (>=3 down closes in the last 5 sessions, 6 Manas Entry "3-5 down days") — without it
   the archetype tagged 280-400 names/day (any name drifting near a rising MA).
3. Strong-start uptrend: current 63d momentum > 0 OR ema200 persistency > 0 (the
   Tightness Study examples contract exactly when 63d momentum reads flat/negative).
4. SIZE CONTROL (the honest hard part): removed the UNBOUNDED immunities (top-quartile +
   any multi-archetype name) that drove buckets to 315-470/day. Hard top-20 per archetype;
   proximity-to-trigger ranking per the spec: pullback = ascending MA-distance, reversal +
   strong_start_ready = ascending prev-day tightness pctile (Tightness Study), liveness
   (ADR pctile + purple dots) as tiebreak; remaining archetypes velocity-ranked.

ITERATION TABLE (definitive 12-pick set, entry day OR day-before):
| iteration     | recall | caught                                                  | sizes/day        |
|---------------|--------|---------------------------------------------------------|------------------|
| K4.1 (pre-K7) | 2/12   | PARAGMILK, GROWW                                        | 315-470          |
| K7 final      | 5/12   | INTELLECT (reversal), BSOFT (reversal), ZENTEC 13-Mar + | 101-133, med ~119|
|               |        | 16-Mar (pullback), GROWW (ep_ipo+pm+recent_listing)     |                  |
Full 23-row label set: 7/23 = 30.4% (adds STALLION via strong_start_ready, SKYGOLD via
persistent_momentum). NBIFIN negative control: correctly EXCLUDED (turnover floor). RAIN:
verified in-bucket in the K4.1 run via persistent_momentum (that ranker unchanged in K7).

HONEST MISSES (12-set) with the measured failing condition:
- PARAGMILK 16-Jun: tightness pctile 25 = borderline; ranks 133/143 (SSR) and 141/187
  (pullback) — was only ever "caught" pre-K7 by the unbounded immunity that caused the
  size blowup.
- TATAINVEST 5-Jun: MA-distance 0.88% but 115 names sit closer — pullback crowd is dense.
- NCC 10-Mar: 6 consecutive down days (outside the corpus's stated 3-5); no 10SMA reclaim.
- ZENTEC 24-Feb: 10SMA and 20SMA both FALLING — "rising MA" legitimately fails.
- CHENNPETRO 17-Oct: prev-day range pctile 65-100 in OUR daily bars — the study's tight
  day is not visible in this data for this date.
- COALINDIA 10-Oct: 0 purple dots, ADR pctile 0.6 — killed by the corpus's own "ZERO dots
  = skip"; the tension with it being a Tightness-Study example is real, left for a corpus
  re-read on large-cap nature-relativity.
- EMSLIMITED 6-Nov: prior-strength ratio 1.48 vs 1.5 and leg force 26.8 vs 30 — knife
  edges; NOT retuned without corpus evidence.
LESSON: recall-vs-cap is now the binding constraint. Further recall must come from better
archetype SPECIFICITY (shrinking the ~200/day pullback crowd), not looser thresholds.
Files: scanner/discovery.py, scanner/discovery_metrics.py (+high_180d, low_252d,
correction_depth_from_180d_high, rolling_max_momentum_120d), tests/test_discovery_metrics.py
(+8 tests), tests/test_discovery_bucket.py (reworked size-control tests + reversal fixture),
_wave_k_miss_diagnosis.py (rebuilt to mirror current eligibility), _wave_k7_recall.py
(scratch harness copy of _wave_k41_recall.py pointing at wave_k7_postfix.db).
Tests: 539 passed + 1 known sector_downside failure (pre-existing, flagged WAVE J7).

## K8 + baseline correction (2026-07-10, cycle 71)
- CORRECTION: K7's reported 5/12 recall was measured against stale pre-backfill prices. The
  2026-07-04/05 full-history bhavcopy backfill (INSERT OR REPLACE, 929K rows) corrected
  daily_prices to ground truth (verified: CHENNPETRO 2025-10-17 close 723.60 == raw
  cm17OCT2025bhav.csv; recomputed SMA10 distance -7.12% is mathematically right). TRUE
  baseline = 3/12 (INTELLECT, BSOFT, GROWW). CHENNPETRO/COALINDIA never actually passed the
  3% near-MA test on correct data; PARAGMILK/TATAINVEST hits were also stale-data artifacts.
  Pre-backfill values unrecoverable (no DB backup). Rule reaffirmed: recall scores only valid
  against the data vintage they were scored on; re-score after ANY price backfill.
- K8 (72671a14): D1 volume-character + D2 undercut-recover + D3 contraction + D4 leg-force
  ranking. Recall-neutral (3/12 -> 3/12, same hit set), crowd-shrink real (~200 -> 41-57/day
  pullback pre-cap). PARAGMILK fails D1 by 0.004 (up/down vol ratio 0.996 on 15-Jun vs >=1.0);
  TATAINVEST clears D1-D3 but ranks 38/57 on leg-force (41.5% vs 20+ names at 50-114%) —
  pure cap casualty. No tuning done per spec rule.
- Open: on CORRECT data the misses are now honest signal — CHENNPETRO/COALINDIA-class needs
  either a wider corpus-cited near-MA branch (they sat 5.8-7.1% away) or a different archetype
  read (their entries may be strong_start, not pullback); TATAINVEST needs cap/rank rethink.
  Next recall work must cite corpus for any change; 3/12 is the number to beat.
