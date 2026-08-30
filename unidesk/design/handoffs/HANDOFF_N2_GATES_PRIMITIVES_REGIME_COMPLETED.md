# HANDOFF N2 gates + primitives + R0 — COMPLETED

Date: 2026-08-29.

Attribution-ID: attr-unidesk-n2-gates-primitives-regime-glm53flash-20260829-001

## Outcome

- `unidesk/momentum/universe/gates.py` — universe tradeability gates adopted
  by copy from traderlog/adopted/activity.py (price floor ₹30, avg-turnover
  floor ₹2cr/20 sessions, ETF keyword heuristic, circuit-freeze heuristic,
  mcap check skipped-and-surfaced). Drift documented in the module header.
- `unidesk/momentum/features/spec_library.py` — the swing-edges §1.5
  primitives that were missing: sma (running window), rvol_median (spec's
  median definition), delivery_z (full-window rule), pocket_pivot
  (down-day-volume benchmark), tight_ratio (spec's tight_10), stack_bull,
  stage2 (1.15× premium, 126d window, 50d slope).
- `unidesk/momentum/regime.py` — R0 classifier: breadth-driven
  BULL/BEAR/CHOP with 3-day hysteresis, breadth_only mode until the index
  series lands (source recorded per row; spec §2.4 kill test applies once
  T1 exists).
- **Real-data proof:** 233 sessions of breadth computed from the ingested
  backlog (fraction of universe above EMA50); Jun/Jul 2026 classified BULL.
- Bug during the slice: pocket_pivot warm-up off-by-one (i <= lookback) —
  caught by its own test, fixed to i < lookback.

## Files changed

- `unidesk/momentum/universe/gates.py`, `unidesk/momentum/features/spec_library.py`,
  `unidesk/momentum/regime.py` (new)
- `unidesk/tests/test_n2_gates_primitives_regime.py` (13 tests, new)
- `unidesk/TASKS.md`, `unidesk/GOAL.md`, this handoff

## Verification

```text
.venv-orderflow/Scripts/python.exe -m pytest orderflow/tests unidesk/tests -q -> 222 passed
.venv-orderflow/Scripts/python.exe unidesk/run_checks.py -> exit 0
Real breadth run: 233 sessions classified; Jun/Jul 2026 = BULL
```

## Honest partials

- R0 runs breadth_only: the spec's Midcap-150-vs-SMA50 leg needs the index
  series (N3 reference item). The source field on every row records this.
- The regime output is a classifier, not a forecast — its own §2.4 kill test
  runs after T1 exists.
- Gate heuristics (ETF keywords, circuit freeze) are the adopted original's
  approximations — cheap pre-filters, never ground truth.
