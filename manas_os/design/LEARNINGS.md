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
