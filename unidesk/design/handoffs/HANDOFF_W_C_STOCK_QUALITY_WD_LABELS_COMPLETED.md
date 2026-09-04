# HANDOFF W-C stock quality + W-D outcome labels — COMPLETED

Date: 2026-08-29. Two slices: the P1.9 stock-quality snapshot (closes W-C)
and the P7.2 outcome-label engine (opens W-D).

Attribution-ID: attr-unidesk-wc-stockquality-wd-labels-glm53flash-20260829-001

## Outcome

- `unidesk/momentum/scoring/stock_quality.py` — the P1.9 snapshot: a
  decomposable weighted-mean score over six named contributors (trend,
  rs_rank, rvol, delivery_ratio, room_to_52w_high, circuit_safety), each
  reported with availability, normalized value, weight, and named reason.
  Nulls reduce coverage — never zeros (R12). Below `min_coverage` the score
  is None with `INSUFFICIENT_DATA`. Weights are a caller-supplied mapping
  (config policy, R14); a zero weight = feature disabled (R15). Circuit
  UC/LC risk emits hard_gates beside the score — veto authority is not a
  number.
- `unidesk/research/labels.py` — P7.2 outcome labels: MFE/MAE over a
  caller-sliced future window, first-touch stop_hit, potential-R r_multiple
  with 1R/2R/3R attainment, and breakout hold/fail with an honest UNRESOLVED
  state (fewer than min_sessions completed above the trigger is "not decided
  yet", never a default). The leakage line is explicit: the caller owns the
  point-in-time slicing; P7.3's suite will enforce it.

One implementation bug found by its own test: breakout_hold declared HOLD on
fewer than min_sessions bars — fixed to return the UNRESOLVED state; every
other failure this slice was test-expectation arithmetic, fixed by hand.

## Files changed

- `unidesk/momentum/scoring/__init__.py`, `unidesk/momentum/scoring/stock_quality.py` (new)
- `unidesk/research/__init__.py`, `unidesk/research/labels.py` (new)
- `unidesk/tests/test_stock_quality.py` (8 tests), `unidesk/tests/test_labels.py` (5 tests) (new)
- `unidesk/GOAL.md` (status)

## Verification

```text
.venv-orderflow/Scripts/python.exe -m pytest orderflow/tests unidesk/tests -q
  -> 167 passed
.venv-orderflow/Scripts/python.exe unidesk/run_checks.py -> exit 0
```

## Honest partials

- The snapshot's normalizers encode simple linear mappings (documented,
  parameterized); they are provisional until calibrated on recorded outcomes.
- The Model A harness cannot run end-to-end until the owner picks the
  point-in-time data home (DATA_POLICY.md gate) — labels are ready, data is not.
- Sector-membership source for the RS module remains the same open decision.
