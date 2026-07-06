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
