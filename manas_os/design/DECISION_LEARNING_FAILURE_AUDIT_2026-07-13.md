# sat10ic os decision and learning failure audit

**Status:** binding diagnosis and rebuild requirement  
**Audit date:** 2026-07-13  
**Database inspected:** `manas_os/data/manas.db`  
**Latest stored market session:** 2026-07-10  
**Binding cases:** RAIN and STALLION

## 1. Conclusion

The current system does not yet self-improve in a decision-relevant sense. It has
memory, resolver and weighting scaffolds, but resolved outcomes do not reach the
live database, filtered/user-nominated names are excluded, and the existing model
weight formula does not test whether an agent's `TAKE` or `SKIP` was correct.

The RAIN/STALLION miss is primarily an upstream discovery/gate architecture failure.
Neither symbol reached an LLM verdict. Calling it an LLM reasoning failure alone
would diagnose the wrong layer.

## 2. Sources and fidelity boundary

- Live SQLite records in `manas_os/data/manas.db`, read-only on 2026-07-13.
- STALLION chart supplied by the user:
  `C:/Users/satta/AppData/Local/Temp/codex-clipboard-bc0dfc33-e69b-47a8-9669-8dcc648f9886.png`.
- RAIN chart supplied by the user:
  `C:/Users/satta/AppData/Local/Temp/codex-clipboard-10adb2e0-413c-4db2-ace6-7bef36fec5d6.png`.
- Current source paths and symbols listed below.

The screenshots demonstrate visible chart structure and the user's thesis. They do
not prove that a trade at an unspecified earlier time was executable. Performance
claims below use stored NSE bars and explicit dates.

## 3. Verified incident reconstruction

### RAIN

- `scan_candidates`: no survivor row.
- `refusals`, 2026-07-10: setup family `momentum`; failed gate `risk`;
  reason `stop 5.4% exceeds 5.0% cap (SELECTIVE)`.
- The same refusal evidence says regime, tradability, trend-template, fresh-leg and
  participation passed. The regime-family mismatch had already been reduced to a
  scored objection.
- `agent_verdicts`: zero RAIN rows. It was not debated.
- Stored close: 204.36 on 2026-07-09 and 207.05 on 2026-07-10, a +1.3163%
  close-to-close move.
- The supplied monthly chart visibly marks a breakout above key resistance, price
  above the 21 EMA, strong RS and a 185-150 support zone. This is a long-base/
  reversal-state thesis, not merely a generic daily momentum screen.

### STALLION

- `scan_candidates`: no survivor row.
- `refusals`, 2026-07-10: setup family `base/pattern`; failed gate
  `trend-template`; reason `insufficient history for 50/200SMA trend template`.
- `agent_verdicts`: zero STALLION rows. It was not debated.
- Stored close: 182.12 on 2026-07-09 and 204.88 on 2026-07-10, a +12.4973%
  close-to-close move. Open-to-close on 2026-07-10 was +11.0461%.
- The supplied daily chart visibly shows a recent-listing/IPO-age structure, a
  rounded recovery/base, descending resistance, rising support and a large-volume
  breakout bar. Requiring a conventional 200-session template erased the archetype
  the StocksGeeks lane exists to interpret.

### One-session council check

For chair decisions made on 2026-07-09 and evaluated at the next stored close:

| Chair decision | Names | Positive next close | Mean next-close return |
|---|---:|---:|---:|
| TAKE | 1 | 0 | -0.449929% |
| SKIP | 24 | 18 | +0.767609% |

The figures were recomputed by two independent routes: a SQLite aggregation and a
Python row-by-row calculation. They matched exactly. This is only one session and
cannot establish long-run expectancy, but it substantiates the reported ranking/
debate inversion and requires a false-negative audit.

## 4. Root causes in current code

### A. Debate selection is downstream of the verdict-producing filter

- `manas_os/scanner/candidates.py:1082` builds the live pool and sends each name
  through `candidate_for_symbol` and the gate cascade.
- `manas_os/agents/debate.py:214` loads survivors first, then fills only limited
  remaining slots with selected soft near-misses. Hard near-misses are excluded from
  debate.
- `manas_os/agents/debate.py:291` tells models to default a `NEAR_MISS` to `SKIP`.

Result: the same deterministic classification influences admission, the evidence
label and the expected answer. Multiple LLM seats can become correlated gate
paraphrasers rather than independent chart readers.

### B. Setup quality, entry readiness, eligibility and size are collapsed

- RAIN's setup disappeared because a 5.4% calculated stop exceeded a 5.0% width
  cap. That is an execution/risk-state fact, not proof that the long-base behaviour
  lacked quality.
- STALLION's recent-listing structure disappeared because a conventional 50/200-SMA
  history requirement was applied before an IPO-aware lane could assess it.

The product needs separate states for interesting behaviour, setup quality, trigger
readiness, live eligibility and permitted quantity.

### C. User conviction is not a canonical input

- `manas_os/data/labels/practitioner_picks.csv` contained STALLION but not RAIN before
  this audit.
- `push_symbol_debate` supports a one-off manual push, but there is no durable
  `user_theses` record with first mention, repeated mentions, thesis evolution and
  later outcome.
- A pushed symbol absent from `scan_candidates` is constructed as tier `PASSED` in
  `manas_os/agents/debate.py:672`, losing the real rejection context instead of
  separating setup opinion from eligibility.

Result: the user can identify a name repeatedly without earning a guaranteed fresh
chart review or creating a learnable counterexample.

### D. Comparative behaviour is too thin

`manas_os/agents/context_pack.py:438` gives the debate a scalar
`sector_adj_momentum`, but not aligned stock/theme/sector/Nifty price and RS paths.
The LLM cannot genuinely observe that a stock is holding while its group corrects,
leading its theme or breaking out before broader participation.

## 5. Why the current models are not self-improving

### Live database state

As inspected on 2026-07-13:

- 297 `agent_verdicts`; zero have non-null `outcome_r`.
- 32 `decision_memories`; zero `decision_memory_outcomes`.
- 1,184 `alpha_feature_snapshots`.
- Zero `alpha_predictions`, zero `alpha_model_registry` rows and zero
  `alpha_experiments`.

These counts mean that feature and memory infrastructure exists, but no resolved
feedback currently changes a later decision.

### Broken or disconnected feedback paths

1. `manas_os/agents/lessons.py:66` only resolves chair rows that join a
   `scan_candidates` survivor. Filtered names such as RAIN and STALLION cannot enter.
2. `lessons.py:132` writes one shared `outcome_r` to every agent on that symbol,
   regardless of whether the agent said `TAKE` or `SKIP`.
3. `lessons.py:259` writes lesson text only when the chair said `TAKE`. False
   negatives and gate-blocked opportunity costs are omitted.
4. `_tag` cannot emit `wrong-process-win`, although the tag is declared.
5. `manas_os/agents/chair.py:94` calls any row with `outcome_r >= 1` a hit without
   comparing the outcome with the model's verdict. A `SKIP` on a +1R move would
   increase the same raw hit counter as a correct `TAKE`.
6. `manas_os/alpha/resolver.py:225` has only test callers in the CodeGraph. It is not
   wired into the production nightly pipeline.
7. Memory analogue retrieval exists, but there are no resolved memory outcomes to
   provide outcome-weighted learning.

Therefore “self-improvement” is currently a scaffold, not an operating loop.

## 6. Correct operating loop

```text
Scanner discovery + user theses
-> independent blinded chart observer
-> parallel TradeTM / Manas / StocksGeeks execution lenses
-> explicit setup-quality + trigger-state ranking
-> deterministic tradability/risk overlay
-> TAKE / WATCH / SKIP / BLOCKED decision record
-> nightly path-dependent resolution for every decision
-> false-positive / false-negative / process-quality attribution
-> analogue retrieval and calibrated model/lens weights
-> weekly error cohorts and shadow research proposals
-> Horizon validation and human promotion
```

“Self-improve” means two controlled mechanisms:

1. **Fast memory adaptation:** later debates receive traceable comparable episodes
   and each model/lens receives calibrated reliability by regime and archetype.
2. **Slow governed research:** repeated error cohorts propose feature/gate/prompt
   changes, then undergo point-in-time walk-forward, anti-overfit and shadow-live
   tests. No live model rewrites its own prompt or risk rules.

## 7. Required records

### `user_theses`

- `thesis_id`, `symbol`, `first_seen_at`, `last_reiterated_at`, `mention_count`
- `source_type`, `source_ref`, `user_note`, `archetype_hypotheses_json`
- `trigger`, `invalidation`, `time_window`, `status`
- immutable revision lineage

### `decision_evaluations`

- decision/model/lens identity and point-in-time evidence ID
- verdict and calibrated confidence
- setup quality, trigger state, eligibility state and sizing state
- resolved path and decision-aware class:
  `TRUE_POSITIVE`, `FALSE_POSITIVE`, `TRUE_NEGATIVE`, `FALSE_NEGATIVE`,
  `NO_TRIGGER`, `RIGHT_PROCESS_LOSS`, `WRONG_PROCESS_WIN`
- attribution by regime, archetype, sector/theme and user/system source

### `error_cohorts`

- frozen cohort definition and members
- recurring failure explanation
- proposed correction and falsification test
- experiment/promotion state

## 8. Debate changes

1. Stage A receives chart/context evidence without `PASSED`, `NEAR_MISS`, refusal
   reason, scanner grade or other models' verdicts.
2. Stage A describes behaviour and assigns parallel archetype hypotheses with
   confirmation and contradiction.
3. Stage B execution lenses see the Stage-A observation and teacher-specific facts.
4. Stage C risk critic sees gate evidence and can set `EXECUTABLE_NOW=false` without
   deleting setup quality or watch priority.
5. The chair ranks expected opportunity conditional on trigger; it does not take a
   majority vote over correlated prompt copies.
6. The UI shows `Good setup, not executable yet` distinctly from `Poor setup`.

## 9. Acceptance tests

- RAIN fixture: a 5.4% stop versus a 5.0% live cap remains visible as a quality
  thesis and risk-blocked watch; it is not silently removed.
- STALLION fixture: a recent IPO is evaluated by listing-age/IPO-base rules and
  cannot fail solely for missing 200-session history.
- A user thesis bypasses no hard risk rule but always receives chart observation,
  a recorded decision and a later counterfactual outcome.
- The chart observer produces the same observation when gate labels are removed.
- The debate input contains aligned stock/theme/sector/Nifty paths with timestamps.
- A `SKIP` followed by +1R is stored as a false negative for that model/lens.
- A `TAKE` followed by +1R is stored as a true positive.
- Model weighting changes only after enough resolved, decision-aware observations;
  future outcomes are excluded by the as-of cutoff.
- Nightly production invokes the outcome resolver and exposes resolved/pending/
  failed counts in the run card.
- Alpha research cannot promote from the same sample that generated the correction.

## Risks

- A one-session miss can trigger overcorrection. RAIN and STALLION are regression
  cases, not proof that every blocked momentum or IPO name belongs in the portfolio.
- User nominations deserve guaranteed analysis and learning, not automatic priority
  in live sizing.
- Loosening risk gates to repair recall can create irreversible losses. Preserve the
  live risk governor while separating it from setup-quality ranking.
- Counterfactual outcomes require realistic trigger, gap, circuit, liquidity and
  slippage handling or the learning labels will be false.
