# HANDOFF W-C RS + AVWAP + circuit risk — COMPLETED

Date: 2026-08-29. Slice: momentum feature modules for build-manual Tasks
P1.3 (relative strength), P1.6 (AVWAP), P1.8 (circuit/structural risk).
Storage-neutral per `unidesk/momentum/DATA_POLICY.md`.

Attribution-ID: attr-unidesk-wc-rs-avwap-circuit-glm53flash-20260829-001

## Outcome

- `unidesk/momentum/features/rs.py` — `window_return` (no look-ahead),
  `rs_excess` (arithmetic, signed, None-safe), `percentile_rank` (mid-rank on
  ties), and `rs_snapshot`: one symbol's market/sector/peer context at one
  instant over a POINT-IN-TIME universe. Missing sector membership disables
  sector/peer comparisons with the named reason `NO_SECTOR_MEMBERSHIP` —
  never a silent fallback to the market figure (R12).
- `unidesk/momentum/features/avwap.py` — `typical_price` (validates low<=high)
  and `avwap`: cumulative cost basis from a caller-resolved anchor index;
  None before the anchor (back-filled cost basis would be invented history);
  zero cumulative volume stays None. Anchor DETECTION is setup-primitives
  work (P2.x), not here; confluence keeps source levels separate.
- `unidesk/momentum/features/circuit.py` — `circuit_risk_state` from OFFICIAL
  bands only (never inferred from depth, per P1.8 acceptance): UC_RISK /
  LC_RISK / NONE / UNKNOWN with `CIRCUIT_BANDS_NOT_PUBLISHED` named for
  missing data. Proximity is BAND-relative; the threshold is a caller
  parameter (config policy lives outside feature code, R14).

Six of thirteen new tests initially failed on MY expectations (hand-computed
arithmetic slips, a wrong sector-membership assumption, band- vs
price-relative proximity, and a test-variable reuse) — each fixed by
recomputation against the frozen definitions. The implementations held.

## Files changed

- `unidesk/momentum/features/rs.py` (new)
- `unidesk/momentum/features/avwap.py` (new)
- `unidesk/momentum/features/circuit.py` (new)
- `unidesk/tests/test_momentum_rs_avwap_circuit.py` (new, 13 tests)
- `unidesk/GOAL.md` (status)

## Verification

```text
.venv-orderflow/Scripts/python.exe -m pytest orderflow/tests unidesk/tests -q
  -> 154 passed
.venv-orderflow/Scripts/python.exe unidesk/run_checks.py -> exit 0
```

## Honest partials

- `rs_snapshot.window` is a placeholder (0) — the caller owns the window
  length; a real window label arrives with the Model A harness (W-D).
- Sector membership must be supplied point-in-time by the caller; the
  persistent source of that membership is the still-open storage-home/
  reference-data decision.
- Stock-quality snapshot (P1.9) — the composition of trend + RS +
  participation + ADR + AVWAP + circuit into a decomposable score — is the
  remaining W-C module.
