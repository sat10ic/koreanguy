# HANDOFF — Random-forest breakout-outcome model (shadow-only) (Gemini)

Repo `C:\Users\satta\Downloads\koreanguy`, branch `emergent`. Standing rules: see
`manas_os/design/handoffs/HANDOFF_INDEX.md` (no commit; write `_COMPLETED.md`; absolute python
paths; never print the rupee glyph — use "Rs"). LOW-MEDIUM PRIORITY — after the de-wonk/current UI
queue is clear.

## Context
Reviewed `github.com/Elicherla01/breakoutscanner`'s `ml_engine.py`: a `RandomForestClassifier`
(n_estimators=50, max_depth=5) predicting breakout success from RSI, volume-ratio, EMA-distance,
TR/ATR ratio, and 10-day prior return, labeled by whether the breakout hit +3% before -2.5% within
10 bars. Their implementation has NO train/test split (trains on all history) — that violates our
own discipline and would be rejected by our promotion gates as-is. The CONCEPT (a setup-outcome
probability model with an asymmetric target) is worth adding as a genuine research addition
alongside `manas_os/ml/direction_lgbm.py` — built OUR way, not ported.

## Governing constraints (read + follow exactly)
`manas_os/design/ALPHA_LEARNING_CONSTRAINTS.md` — point-in-time/no-leakage features, walk-forward
+ regime/sector/setup-family breakdowns, comparison vs a simple baseline, minimum-sample/stability
requirements, frozen experiment record, shadow/paper observation before ANY live influence. **No
model score directly controls position size or gates a trade — ever.**

## Scope
1. **Model**: new `manas_os/ml/breakout_outcome_rf.py`, mirroring the shape of
   `direction_lgbm.py` (read it first — same file structure/conventions: point-in-time feature
   build, train/predict functions, persistence, failure-safe skip if sklearn is unavailable).
   `RandomForestClassifier` (reasonable start: n_estimators=200, max_depth=4-6, min_samples_leaf
   tuned to avoid overfit — do NOT copy their n_estimators=50/max_depth=5 blindly, justify your
   choice with a quick CV check).
2. **Features** (point-in-time only, computed from data available strictly before the decision
   bar — reuse existing feature helpers where they exist, e.g. RSI/ATR/EMA likely already computed
   somewhere in `engine/` or `alpha/features.py`, do not duplicate): RSI, volume-ratio (vs 20-bar
   avg), EMA-distance, TR/ATR ratio, N-day prior return. Extend with 1-2 more if cheaply available
   (e.g. delivery_z, RS) — keep the feature set small and justified.
3. **Label**: asymmetric outcome target — did the setup hit +X% before -Y% within N bars (their
   3%/2.5%/10-bar is a reasonable start; tune per setup_family if it improves separation, but
   document the choice). Compute this from the SAME outcome-resolver machinery already built
   (`manas_os/alpha/resolver.py`) if it fits — do not build a second outcome-labeling path; reuse it.
4. **Training discipline (the part their repo skipped)**: a proper walk-forward split (train on
   past, test on strictly-future unseen data — reuse `alpha/promotion_gates.py`'s walk-forward
   pattern if applicable), NOT train-on-everything. Run the model's predictions through
   `promotion_gates.py`'s existing battery (walk-forward vs baseline after Indian costs, placebo/
   permutation, regime + subsample stability, min-sample floors) before it can be called "validated"
   for anything beyond shadow display.
5. **Output**: a probability score persisted per candidate/decision (new column or table, additive)
   — SHADOW/RESEARCH ONLY. Must NOT be read by gates.py, sizer, candidates.py ranking, or the debate
   verdict. If surfaced in the UI at all, it goes through the existing StatusBadge (SHADOW/WARMING)
   vocabulary on the ALPHA tab — never presented as a signal on SCANNERS/DEBATE without an explicit
   "unvalidated research model" label.
6. Tests: feature point-in-time correctness (no leakage — same style as `alpha/leakage_audit.py`),
   walk-forward split correctness, promotion-gate integration (model must go through the battery,
   not bypass it), honest failure-safe skip without sklearn installed.

## Guardrails
Shadow-only, zero live influence (verified by grep: NOT imported by gates.py/sizer/candidates.py
ranking/debate.py verdict logic). No new heavyweight dependency beyond scikit-learn (check it's
not already a dependency; if adding, note it). Real data only. No score ever "directly controls
position size" (constraints doc, verbatim rule).

## Output
`HANDOFF_GEMINI_rf_breakout_outcome_model_COMPLETED.md`: the feature/label contract, the
walk-forward setup, promotion-gate battery result (pass/fail per gate, honestly), where the score
is persisted, confirmation it's not imported anywhere live (grep proof), test results.
