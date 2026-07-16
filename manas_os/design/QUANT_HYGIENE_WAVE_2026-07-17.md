# QUANT-HYGIENE WAVE — Horizon frameworks → Manas OS (2026-07-17)

Source: Horizon_Quant_Frameworks_Consolidated.md (user-supplied, 7 articles). User: "you
completely ignored adding in quant (which does not need heavy local compute)." Honest map:

## Already implemented (don't rebuild)
- **Art 4 (HMM/Markov regimes):** regime_history_hmm shipped; XP/MBI/governor = the regime layer.
- **Art 3+6 (loop engineering / self-improving agent):** alpha bench = generator/evaluator/selector
  with promotion_gates (separate verifier ✓), leakage_audit, replay OOS gate, experiments KB with
  fail→investigate→distil→consult (alpha/memory.py). Verifier-separation principle satisfied.
- Journal→outcomes→expectancy loop = the personal-trades side of the same machinery.

## The real gaps (all trivial compute — bootstrap/grids over SQLite)

### Q1. Deflated-Sharpe / trials accounting (Art 1) — the missing multiple-testing correction
Our promotion gates check OOS edge but NEVER COUNT HOW MANY CANDIDATES WE TRIED. With enough
experiments, a "passing" factor is expected by luck.
- Build: experiments KB already logs every run → `n_trials` per family; promotion gate adds the
  expected-max-Sharpe-under-null threshold (Bailey/López de Prado DSR) computed from n_trials +
  backtest length; a factor promotes only if it clears the DEFLATED bar, not the raw one.
- Where: alpha/promotion_gates.py + alpha/schema (trial counter). Compute: closed-form. 
- Done-test: a synthetic noise factor that passes the raw gate is REFUSED once 50 sibling trials
  are recorded.

### Q2. Signal-decay monitoring (Art 2) — the "is this screener dying" answer
We calibrate screener hit-rates but never test LIVE-vs-BASELINE drift. This is ALSO the user's
"tool should self-learn from its failed calls" ask, formalized.
- Build: weekly stage `signal_decay`: per setup-family/screener/factor — (a) performance cone:
  bootstrap-resample its historical outcome list (few thousand draws, milliseconds) → drawdown/
  time-underwater distribution; (b) rolling 90d hit-rate & median-R vs backtest percentile;
  (c) trade-level drift (winners shrinking N months running). Breach ladder (pre-decided):
  inside cone = weather → below 5th pctile = amber chip on that setup's cards → sustained breach
  = family auto-demoted to half-weight in rank + LEARNINGS entry (never silent).
- Where: scanner/expectancy.py sibling module + a chip in the setup card + ALPHA panel.
- Done-test: feed a family with degraded synthetic outcomes → amber then demotion fire; healthy
  family stays quiet.

### Q3. Ablation + parameter-plateau harness (Art 5) — prove our gates aren't decoration
The cascade has ~6 gates + dozens of thresholds (RS 80, delivery_z 0, stop caps, ADR bands...).
Never ablated. Some may be costume; some (per the FCL/NUVOCO/DIVISLAB false-negative probes) are
actively harmful.
- Build: replay modes `--ablate` (drop one gate at a time, compare refused-cohort-vs-passed T+10
  spread) and `--plateau <param>` (score grid ±10/20% around each threshold; flag SPIKES —
  thresholds that only work at the memorized value). Feeds threshold-loosening decisions with
  evidence instead of anecdotes.
- Where: backtest/replay.py flags + LEARNINGS.md entries. Compute: N replays of existing engine.
- Done-test: plateau report for RS-floor + delivery_z + stop-band produced on real history; at
  least one documented keep/loosen decision cites it.

### Q4. IC/ICIR + half-life on alpha factors (Art 3) — formalize factor health
factor_health exists; upgrade its scoring to information coefficient (corr of factor value vs
next-period return), ICIR (mean/std of rolling IC), and IC half-life (decay rate) so factors are
comparable and decay is a NUMBER, not a vibe. Compute: correlations over features_daily.
- Done-test: /api/alpha/factors/health returns {ic, icir, half_life_days, n} per factor; the
  activity/SMF factor's ICIR published in LEARNINGS.

## Sequencing + rails
After the rendered-UX audit fix wave (in flight). Order: Q2 (user-facing self-learning) → Q1
(gate correctness) → Q3 (feeds the discovery-threshold review) → Q4. All shadow/display first;
NOTHING changes gates/sizing except through the existing promotion path. Each lands with its
done-test + a LEARNINGS entry. No new deps (numpy already present; bootstrap = random.choices).
Honest scope note: these are hygiene/monitoring layers, not new alpha — they make the existing
edges trustworthy and self-auditing, which is the article series' actual point.
