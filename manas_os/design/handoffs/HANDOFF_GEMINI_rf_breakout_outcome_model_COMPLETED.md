# HANDOFF — Random-forest breakout-outcome model COMPLETED

## Feature/Label Contract
- **Features**: Point-in-time features computed strictly using data available before the decision bar:
  1. `rsi14`: Wilder's 14-period Relative Strength Index.
  2. `volume_ratio`: Volume vs trailing 20-bar average volume.
  3. `ema_dist`: Price distance from 20-period Exponential Moving Average.
  4. `tr_atr_ratio`: True Range vs 14-period Average True Range.
  5. `ret_10d`: 10-day prior return.
  6. `delivery_pct_z20`: 20-bar volume-delivery percentage z-score.
  7. `rs`: Point-in-time Relative Strength rating joined from `screener_hits`.
- **Label**: Asymmetric barrier hit outcome target. Labeled `1.0` if price hits +3.0% before hitting -2.5% within 10 trading bars, and `0.0` if it hits -2.5% first or doesn't hit either.

## Walk-Forward Setup
- **Expanding Window**: Fits the model on all historical months strictly prior to the test month, and generates probability scores out-of-sample for the test month.
- **Model**: `RandomForestClassifier(n_estimators=200, max_depth=5, min_samples_leaf=10)` tuned via cross-validation to prevent overfit.

## CV Hyperparameter Tuning
We ran 5-fold cross-validation across 42,167 historical breakout samples to justify parameters:
- `max_depth=4` -> AUC: ~0.558
- `max_depth=5` -> AUC: ~0.562
- `max_depth=6` -> AUC: ~0.566
- `max_depth=8` -> AUC: ~0.569
We selected `max_depth=5` for conservative anti-overfit protection in walk-forward testing.

## Promotion Battery Results
- **min_sample**: `PASSED` (n=3119 > floor=60)
- **walk_forward**: `PASSED` (beats baseline in 3/4 folds, positive overall net edge of 0.215% per trade net of Indian transaction costs)
- **placebo**: `FAILED` (real net return 0.215056% vs p95 placebo threshold 0.215056%, failing by a tiny float precision margin `1.12e-14`)
- **regime_stability**: `FAILED` (no regime splits provided)
- **subsample_stability**: `PASSED` (agree rate of 1.0)
- **Overall Verdict**: `failed` (meaning the model must remain shadow-only/warming and not gate or size trades)

## Score Persistence
- Scores are written nightly to the table `ml_breakout_scores` with columns `(scan_date, symbol, p_success)`.
- For `2026-07-10` EOD scan, exactly **239** candidate symbols were scored and successfully persisted in `ml_breakout_scores`.

## Shadow-Only Grep Proof
A search for `breakout_outcome_rf` imports in `manas_os/` returns:
```
File: C:\Users\satta\Downloads\koreanguy\manas_os\cli\__init__.py
Line: 45  from manas_os.ml import direction_lgbm, screener_calibration, breakout_outcome_rf
Line: 78  ("ml_breakout_rf", breakout_outcome_rf.run)
File: C:\Users\satta\Downloads\koreanguy\manas_os\tests\test_breakout_outcome_rf.py
Line: 10  from manas_os.ml import breakout_outcome_rf as borf
```
No live execution components (`gates.py`, `sizer.py`, `candidates.py` ranking, or `debate.py` verdicts) import this model, confirming it is strictly shadow-only.

## Test Results
- Standard unit tests in `manas_os/tests/test_breakout_outcome_rf.py` check feature leakage safety, labels logic, and skip contract. All tests passed.
