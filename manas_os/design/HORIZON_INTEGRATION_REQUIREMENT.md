# sat10ic os — binding Horizon integration requirement

**Status:** BINDING PRODUCT REQUIREMENT  
**Source:** `C:\Users\satta\Downloads\horizon_consolidated\Horizon_Quant_Frameworks_Consolidated.md`  
**Purpose:** Make Horizon's research loop, regime-state reasoning, anti-overfit discipline and live edge monitoring first-class sat10ic os capabilities.

## Standing constraint

Horizon is not optional background reading and must not be compressed into a generic “use better validation” note.

Every Alpha/Quant implementation plan and handoff must explicitly map the six extractable Horizon frameworks to:

1. canonical records;
2. compute jobs;
3. APIs;
4. Alpha Lab UI;
5. Debate/Market linkage;
6. tests and promotion gates.

The centre of gravity remains Indian swing trading: regime detection, opportunity ranking, risk sizing, chart behavior, EP/PEAD, IPO bases, Stage-2/long bases, VCP/flags, pocket pivots, Strong Start and reversals. Horizon governs how those ideas are researched, rejected, monitored and improved. It does not turn sat10ic os into a next-price prediction product.

## Source-fidelity boundary

The supplied consolidated document has complete extractable prose for many concepts, but several exact formulas and thresholds exist only inside embedded images.

- Safe to implement directly from extractable prose: structural-edge question; trial-count requirement; performance-cone concept; 90-day rolling-Sharpe 5th-percentile early flag; drawdown depth/duration; trade-level drift; generate/test/score/feedback loop; IC; out-of-sample gate; state/transition framing; sticky/asymmetric regimes; ablation; parameter plateau at roughly ±10–20%; generator/evaluator/selector; failure memory; independent verifier.
- Requires a separately cited primary source or verified OCR before claiming exact Horizon fidelity: Deflated Sharpe Ratio formula; ICIR and factor half-life formulas shown only in charts; exact cut-size/pause/re-tune/retire breach thresholds; exact complexity-penalty equation; image-only appendix content.
- Project-defined implementations are allowed, but must be labelled `sat10ic definition`, versioned and never attributed as an exact Horizon formula.

## Why this fits sat10ic os

Horizon answers the parts currently missing between a named setup and a durable edge:

```text
Indian market hypothesis
-> formal point-in-time experiment
-> trial-aware validation
-> out-of-sample survival
-> live shadow observation
-> decay monitoring
-> failure diagnosis and memory
-> next constrained variant
```

This complements, rather than replaces:

- XP/MBI and breadth as the current regime authority;
- HMM as experimental state-transition context;
- cross-sectional ranking as the opportunity-selection layer;
- practitioner chart lenses as hypothesis generators;
- deterministic risk and tradability as final law;
- human/manual execution.

## Framework 1 — reject lucky strategies before promotion

### Horizon source

Article 1, lines 29–74:

- a setup is not a strategy;
- a strategy requires entry, exit, position size, market regime and a written reason it should make money;
- the first structural question is “Who is on the other side?”;
- the number of trials must be reported;
- Deflated Sharpe Ratio adjusts evidence for strategy-search multiplicity.

### Current sat10ic gap

- `alpha_experiments` records a hypothesis/spec/results but no family lineage, generation, trial number or total related trials.
- `alpha_model_registry` has validation JSON but no structural-edge thesis.
- `promotion_gates.py` does not compute or store a trial-aware statistic.

### Required records

Extend additively:

#### `alpha_hypothesis_families`

- `family_id`
- `name`
- `india_edge_domain`
- `structural_edge_json`:
  - `edge_one_sentence`
  - `other_side`
  - `behavioural_or_structural_reason`
  - `regimes_expected`
  - `entry_definition`
  - `exit_definition`
  - `sizing_policy_reference`
  - `decay_observation`
  - `falsification_test`
- `created_at`
- immutable after first frozen experiment; corrections create a new version.

#### Extend `alpha_experiments`

- `family_id`
- `parent_experiment_id`
- `generation`
- `variant_index`
- `hypothesis_signature`
- `trial_number_in_family`
- `trials_known_at_freeze`
- `generator_model`
- `evaluator_version`
- `verifier_version`
- `train_start`, `train_end`, `validation_start`, `validation_end`, `oos_start`, `oos_end`
- `fitness_definition_json`
- `promotion_gate_version`

### Required validation

- An experiment without the structural-edge record cannot run.
- A frozen result cannot omit `trials_known_at_freeze`.
- The trial count includes failed, rejected and nearby-parameter variants, not only survivors.
- Implement DSR only from a verified primary formula/library and add deterministic reference tests. Until then display `TRIAL-AWARE SCORE: NOT IMPLEMENTED`, never a fabricated DSR.
- Keep ordinary Sharpe visible beside the trial count so the user sees why raw Sharpe is insufficient.

### Alpha Lab UI

Research Bench experiment detail begins with:

```text
WHY THIS EDGE SHOULD EXIST
WHO IS ON THE OTHER SIDE
WHERE IT SHOULD WORK
WHAT WOULD KILL IT
TRIALS ATTEMPTED IN THIS FAMILY
```

Do not show a green “passed” state if multiplicity evidence is missing.

## Framework 2 — detect live edge decay before trusting it

### Horizon source

Article 2, lines 78–124:

- distinguish crowding, regime change and overfitting exposed live;
- compare live performance with the backtest-implied distribution;
- use resampled paths as a performance cone;
- monitor rolling 90-day Sharpe against the backtest distribution, with below the 5th percentile as an early flag;
- track drawdown depth and time underwater;
- track hit rate, profit factor and average win versus average loss.

### Current sat10ic gap

- model registry stores only an aggregate live-shadow-session count;
- no canonical live shadow equity/outcome series;
- no performance cone, time-underwater measure or decay classification;
- no separation of normal variance, regime mismatch and likely overfit failure.

### Required records

#### `alpha_shadow_observations`

- `observation_id`
- `model_id`, `model_version`
- `setup_family`, `regime`, `sector`, `theme`
- `decision_time`, `outcome_available_at`
- `gross_r`, `net_r`, `cost_r`
- `mfe_r`, `mae_r`, `holding_sessions`
- `prediction_or_rank_at_decision`
- `source_decision_id`
- immutable.

#### `alpha_health_snapshots`

- model/setup/cohort identity and `as_of_date`
- sample count
- rolling 90-session/trade Sharpe with denominator stated
- backtest percentile of live rolling Sharpe
- drawdown depth
- time underwater
- hit rate
- profit factor
- average win R, average loss R, payoff ratio
- live-versus-backtest drift for each metric
- performance-cone percentile
- `health_state`: `WARMING | HEALTHY | WATCH | PAUSE_RESEARCH | RETIRE_CANDIDATE`
- `diagnosis`: `NORMAL_VARIANCE | POSSIBLE_CROWDING | REGIME_MISMATCH | POSSIBLE_OVERFIT | INSUFFICIENT_DATA`
- definition/version provenance.

#### `alpha_performance_cones`

- cohort/model identity
- backtest cutoff and sample
- bootstrap method/version and deterministic seed
- path horizon
- percentile bands, stored as JSON
- created time.

### Compute rules

- Use block bootstrap for sat10ic performance cones so streaks/volatility clustering are not destroyed. This is a sat10ic implementation choice, not an exact Horizon instruction.
- Never mix unresolved live observations into resolved outcome metrics.
- Never compare gross live performance with net-of-cost backtests.
- The source's exact cut/pause/re-tune/retire thresholds are image-only. Define sat10ic thresholds in a versioned policy and label them as project rules.
- The extractable Horizon early flag is allowed directly: rolling Sharpe below the backtest 5th percentile -> at least `WATCH`.
- Health state cannot alter deterministic position sizing in the first release. It may block research promotion or remove a shadow ranking tilt.

### Alpha Lab UI

Add `IS THE EDGE STILL WORKING?`:

- one plain state: healthy, normal variance, weakening, regime mismatch, or likely broken;
- live curve inside/outside performance cone;
- drawdown depth plus time underwater;
- winners shrinking / losses growing drift;
- sample size and freshness;
- diagnosis evidence and next research action.

## Framework 3 — loop engineering for India-native factors

### Horizon source

Article 3, lines 128–161:

- one-shot prompting does not compound learning;
- use generate -> test -> score -> diagnose -> feed back;
- IC correlates a factor value today with future return;
- the out-of-sample gate is what separates iterative research from faster overfitting.

### Current sat10ic gap

- point-in-time feature snapshots exist, but there is no factor-evaluation series;
- experiments are passive records, not a running variant loop;
- no IC/Rank-IC history by horizon, regime or universe;
- no formal link from failed result to next proposed variant.

### First India-native research domains

Run only these initial families; do not add a generic factor zoo:

1. residual momentum after market and sector movement;
2. leadership diffusion/breadth acceleration;
3. stock resilience/acceleration versus theme and sector;
4. EP/PEAD gap retention and drift;
5. IPO-base maturity, contraction and first expansion;
6. chart-behavior sequences: long Stage-2 base, VCP/flag, pocket pivot, Strong Start preparation and failed-breakdown/reversal.

### Required records

#### `alpha_factor_scores`

- `factor_id`, `factor_version`
- `as_of_date`, `symbol`, `universe`
- raw value, z-score, percentile/rank
- source maximum date and feature cutoff
- missingness/quality.

#### `alpha_factor_evaluations`

- factor identity
- evaluation date
- forward horizon: 5, 10 or 20 sessions
- Pearson IC and Spearman Rank IC
- universe denominator
- turnover/churn
- regime, sector and listing-age cohort
- future-data-availability timestamp.

#### `alpha_factor_health`

- rolling mean IC
- rolling IC standard deviation
- `icir_sat10ic = mean(IC) / std(IC)` with explicit version label; do not call it Horizon's exact formula until the image definition is verified
- sign consistency
- cross-regime stability
- rank-persistence half-life using a separately documented sat10ic definition
- last updated and sample size.

### Loop job

```text
formal hypothesis family
-> generator proposes 2–3 bounded variants
-> strategy-spec validator rejects leakage/undefined fills
-> point-in-time batch evaluation
-> deterministic composite fitness
-> independent OOS verifier
-> selector retains at most one parent for next generation
-> failures diagnosed and stored
-> human reviews survivor
```

The generator may use a cheap/free LLM. The evaluator is deterministic Python, never an LLM opinion. The verifier uses an untouched time slice and cannot be the generator.

### Fitness definition

Do not optimize raw return or Sharpe alone. Version a composite using:

- Rank-IC/IC stability at the target swing horizon;
- net expectancy after Indian costs/slippage;
- drawdown and time underwater;
- trade/sample count;
- stability across walk-forward folds, regime and sector;
- turnover/churn;
- complexity penalty;
- calibration when the output is probabilistic.

Weights are a sat10ic research policy and must be frozen before each generation. The loop cannot tune its own scoring weights within the same experiment family.

### UI

Add an observable loop timeline:

```text
Hypothesis -> 3 variants -> 2 rejected -> OOS verifier -> shadow candidate
```

Clicking any rejection shows the failed gate and the distilled rule carried to the next generation.

## Framework 4 — Markov/HMM as regime transition intelligence

### Horizon source

Article 4, lines 165–204:

- do not predict tomorrow's price;
- infer current hidden market state and likelihood it changes;
- regimes are sticky;
- transitions are asymmetric;
- HMM infers the state from observable returns, volatility and volume/context.

### Current sat10ic scaffold

`regime/regime_hmm.py` already provides:

- causal Nifty/breadth features;
- expanding-window monthly walk-forward fitting;
- state probabilities for the decoded state;
- four labels mapped to the existing XP/MBI vocabulary;
- display warming gate;
- XP/MBI remains authoritative.

### Missing Horizon capability

The fitted transition matrix, full state-probability vector, expected persistence and asymmetric transition risk are not persisted or exposed.

### Required changes

Persist per nightly fit:

- raw state transition matrix;
- state-to-market-label map;
- full current state-probability vector;
- probability of remaining in the current state;
- probability distribution of next states;
- state age in sessions;
- expected duration derived from self-transition probability, with formula/version documented;
- largest adverse transition probability;
- fit cutoff, fold/scaler version and restart score.

Add tests that truncate history at T and reproduce all state/transition outputs <=T.

### Use in sat10ic

- MARKET: `Current state`, `state age`, `persistence`, `transition risk`, and whether HMM confirms/disagrees with XP/MBI.
- Ranking research: shadow-only regime prior for preferred setup families.
- Debate: one sentence such as “state is persistent” or “transition risk is rising,” with numbers in Expert expansion.
- Risk: no automatic sizing effect until separately promoted and explicitly approved. XP/MBI/governor remain law.

Never label transition probability as stock direction probability.

## Framework 5 — stop the research loop from overfitting

### Horizon source

Article 5, lines 208–245:

- loops accumulate decorative rules;
- ablation removes one component at a time;
- a real parameter should survive roughly ±10–20% neighboring values as a plateau;
- a sharp isolated optimum is a warning;
- apply a complexity penalty.

### Current sat10ic scaffold

`alpha/promotion_gates.py` already has:

- Indian cost assumption;
- minimum sample;
- walk-forward comparison;
- placebo/permutation;
- regime stability;
- subsample stability.

### Required additions

#### Ablation

- Every experiment declares named components/features/rules.
- Re-run OOS after removing each component.
- Record delta in fitness, IC, expectancy, drawdown and trade count.
- Classify `ESSENTIAL | CONTRIBUTING | DECORATIVE | HARMFUL` using a versioned sat10ic policy.
- Promotion fails when decorative components remain in the proposed live specification.

#### Parameter plateau

- Every tuned numeric parameter declares its meaningful valid range.
- Evaluate at minimum: -20%, -10%, chosen, +10%, +20%, subject to valid bounds.
- Store the whole grid, not only the best point.
- Detect isolated spikes versus raised neighborhoods using a versioned sat10ic plateau rule.
- Promotion fails on a sharp spike even if the chosen value has the best return.

#### Complexity

- Count active rules, free parameters, interactions and special-case branches.
- Store raw fitness and complexity-adjusted fitness.
- The exact Horizon penalty is image-only; implement and label a sat10ic formula with versioned tests, or leave the gate `NEEDS_DEFINITION`. Never claim exact Horizon fidelity without verified source.

### UI

Add `OVERFIT GAUNTLET` with:

- ablation ranking;
- parameter plateau heatmap/grid;
- raw versus complexity-adjusted fitness;
- placebo and walk-forward folds;
- trial count/DSR state;
- final rejection reason.

## Framework 6 — self-improving agents without self-deception

### Horizon source

Article 6, lines 249–301:

- model weights stay frozen;
- generator proposes, evaluator scores, selector keeps survivors;
- the scoring rule determines what improves;
- failure memory follows fail -> investigate -> distil -> consult;
- generator never grades itself;
- final grade comes from untouched OOS data;
- human retains judgment over 2–3 refined variants.

### Required architecture

#### Generator

- Receives a frozen family spec, prior failures and allowed parameter/rule budget.
- Proposes at most three variants per generation.
- Cannot alter universe, cost model, OOS period, fitness weights or risk constraints.
- Produces formal strategy specs, not executable free-form code with unrestricted access.

#### Evaluator

- Deterministic, point-in-time Python runner.
- Applies costs, fills, circuits, liquidity, listing age, survivorship and future-data-availability rules.
- Produces metrics and gate evidence; no qualitative preference.

#### Selector

- Applies the frozen composite fitness and hard gates.
- Retains no more than one parent for the next generation.
- Cannot promote to live; it can only nominate a shadow candidate.

#### Independent verifier

- Runs untouched OOS and leakage checks.
- Has no access to generator chain-of-thought or preferred result.
- A different model/process writes the qualitative failure diagnosis.

#### Failure memory

Add `alpha_failure_memories`:

- experiment/variant ID;
- failed gate;
- failure class: regime mismatch, costs, insufficient breadth, crowding proxy, leakage, fragile parameter, decorative feature, sample insufficiency, calibration, subgroup catastrophe;
- evidence;
- distilled reusable rule;
- search-space exclusion/signature;
- created time;
- immutable.

Every generator call retrieves relevant failure memories. Exact rediscovery of a failed signature is rejected before compute.

### Debate linkage

This research loop must improve the evidence given to debate, not let debate agents rewrite the strategy during a decision.

The compact Debate Research Context shows:

- opportunity rank and rank stability;
- HMM persistence/transition context;
- setup-family health state;
- live shadow sample/freshness;
- closest successful and failed analogues;
- whether the evidence is warming, healthy, watch or paused.

The debate agent may disagree, but must state why. It cannot modify the factor, model, risk or health record.

## APIs

Extend/add:

- `GET /api/alpha/hypotheses`
- `GET /api/alpha/hypotheses/{family_id}`
- `GET /api/alpha/experiments/{id}/lineage`
- `GET /api/alpha/experiments/{id}/metrics`
- `GET /api/alpha/experiments/{id}/ablation`
- `GET /api/alpha/experiments/{id}/plateau`
- `GET /api/alpha/experiments/{id}/failures`
- `GET /api/alpha/factors/{factor_id}/health`
- `GET /api/alpha/health`
- `GET /api/alpha/health/{model_or_setup}`
- `GET /api/alpha/regime-transition`
- SSE job events for generation, validation, ablation, plateau, OOS verification and memory distillation.

All endpoints are read-only except explicitly authorized experiment creation/run actions. Research actions never mutate deterministic scanner/risk law.

## Alpha Lab information architecture

Use the frozen Round-4 visual system and five research zones:

1. `WHAT MAY LEAD` — India-native factor/ranking evidence.
2. `WHY THE EDGE MAY EXIST` — structural thesis and other side.
3. `RESEARCH LOOP` — variants, scores, rejects, OOS survivor.
4. `OVERFIT GAUNTLET` — trials, DSR state, ablation, plateau, complexity.
5. `IS IT STILL WORKING?` — cone, rolling health, drawdown/time underwater, drift and diagnosis.

Add `FAILURE MEMORY` as an expandable ledger, not a sixth competing dashboard wall.

Beginner mode does not expose this full workspace. MARKET/DEBATE receive only the compact plain-English outputs described above.

## Delivery order

1. Trial lineage + structural-edge records.
2. Factor IC/Rank-IC evaluation records.
3. HMM transition persistence and API.
4. Ablation + parameter plateau + complexity state.
5. Generator/evaluator/selector + failure memory.
6. Live shadow observations + performance cones/health.
7. Alpha Lab UI and compact MARKET/DEBATE linkage.

Do not start with the UI. Empty model/experiment tables are a data/workflow gap, not a card-design problem.

## Acceptance tests

- Trial count includes rejected siblings and cannot be lowered after freeze.
- No DSR value appears without a cited implementation source and deterministic reference tests.
- Factor values and IC use only data available at each as-of date; truncation at T reproduces all prior values.
- OOS dates are invisible to generator and evaluator selection until final verification.
- HMM transition output is point-in-time reproducible and never labelled price prediction.
- Ablation removes exactly one declared component and reruns the identical OOS slice.
- Plateau grid includes neighboring values and stores failures, not only winners.
- Complexity-adjusted score identifies its sat10ic definition/version.
- Generator cannot change cost assumptions, universe, OOS period or fitness weights.
- Failed signatures are rejected before re-running.
- Performance cones are seeded and reproducible; live observations never enter the backtest baseline.
- Health states display sample, freshness and reason.
- No research result alters stop, quantity, open-risk cap, eligibility or Telegram live gate.
- Every Alpha Lab state has populated, warming, empty, stale and failed UI fixtures.

## Risks

- The Horizon source is educational and promotional; algorithms need independent primary-source verification before financial use.
- Several exact definitions are image-only. Claiming exact fidelity without OCR/primary verification would be fabrication.
- A self-improving loop can become an overfitting accelerator. Hard OOS, trial lineage and immutable failure memory must exist before generation is automated.
- Current history may be insufficient for sparse EP, IPO and reversal cohorts. They remain Bayesian/shadow-labelled.
- Horizon mechanisms govern research quality; they do not by themselves create an Indian-market edge.

