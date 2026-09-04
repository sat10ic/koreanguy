# HANDOFF W-C Participation + ADR/ATR — COMPLETED

Date: 2026-08-29. Slice: momentum feature modules for build-manual Tasks
P1.4 (participation) and P1.5 (volatility/extension context), storage-neutral
per `unidesk/momentum/DATA_POLICY.md`.

Attribution-ID: attr-unidesk-wc-participation-adr-glm53flash-20260829-001

## Outcome

- `unidesk/momentum/features/participation.py` — `rvol` (exclusive prior
  mean; warm-up None), `delivery_volume` (Volume x Delivery%, requires BOTH
  inputs — volume alone never substitutes), `delivery_volume_ratio` (strict
  rule: ratio exists only when delivery data covers today AND the ENTIRE
  prior window; one missing day disables the ratio, never a half-baked
  baseline).
- `unidesk/momentum/features/adr_atr.py` — `adr` (exclusive prior range
  mean), `atr` (Wilder: TRs from index 1, SMA seed at index `span`, then
  RMA), `atr_pct`, `today_move_adr` (signed, needs prior close + ADR).
  Negative ranges and out-of-range delivery percentages rejected.
- 14 new tests; every expectation hand-computed. Warm-up is None — and one
  test deliberately distinguishes a REAL computed zero (flat day vs valid
  ADR) from a warm-up placeholder, the exact confusion R12 forbids.

The three sweep of test failures during this slice were all in my test
expectations (off-by-one window indices, a wrong TR hand-computation, an
invalid 120% delivery fixture, and a 0.0-vs-None confusion), not in the
implementations — each was fixed by recomputing by hand, which is the
second-route discipline working as intended.

## Files changed

- `unidesk/momentum/features/participation.py` (new)
- `unidesk/momentum/features/adr_atr.py` (new)
- `unidesk/tests/test_momentum_participation.py` (new, 8 tests)
- `unidesk/tests/test_momentum_adr_atr.py` (new, 6 tests)
- `unidesk/GOAL.md` (status)

## Verification

```text
.venv-orderflow/Scripts/python.exe -m pytest orderflow/tests unidesk/tests -q
  -> 141 passed
.venv-orderflow/Scripts/python.exe unidesk/run_checks.py -> exit 0
```

## Honest partials

- Definitions, not measurements: nothing has met real market data yet
  (W-D Model A is where they do).
- RS (market/sector/peer), AVWAP anchors, circuit risk, and the
  stock-quality snapshot are the remaining W-C modules.
- The momentum persistence adapter is still owner-gated (DATA_POLICY.md);
  these modules are intentionally storage-independent and unblock on that
  decision the moment it lands.
