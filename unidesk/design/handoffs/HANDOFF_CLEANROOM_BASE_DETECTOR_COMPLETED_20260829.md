# Clean-room base detector — completion record

Attribution-ID: attr-unidesk-cleanroom-base-gpt56sol-20260829-001
Attribution-ID: attr-unidesk-cleanroom-base-solreview-20260829-002

## Outcome

A storage-neutral, point-in-time clean-room detector now derives daily
`baseStart`, `pivot`, depth, coil, dry, dry-depth, directional-volume
measurements, squat and failed-poke annotations, lifecycle verdict, and a
configurable 1--99 cross-sectional RS rank. It is expressly not claimed to be
an identical BananaPatterns implementation.

## Evidence-backed calibration

On the public YASHHV OHLC snapshot ending 2026-08-28, the detector produces:

| Field | Clean-room output | Public output |
|---|---:|---:|
| base start | 2026-07-14 | 2026-07-14 |
| base sessions / weeks | 34 / 6.8 | 6.8 weeks |
| pivot | 1003.70 | 1003.70 |
| depth | 13.3108% | 13% (rounded) |
| coil | 0.8573 | 0.86 (rounded) |
| dry | 0.8872 | 0.89 (rounded) |
| dry depth | 0.5361 | 0.54 (rounded) |
| verdict | watch | watch |

The public definitions and chart field semantics are measured faithfully. The
selection of the operative base is a documented heuristic: confirmed fractal
highs, a configurable rebase-maturation gate, and no future session use.

## Verification

- Red proof: the new test module initially failed with the intended missing
  `base_pattern` import.
- Green tests: `py -m pytest unidesk/tests/test_setup_primitives.py
  unidesk/tests/test_detectors_geometry.py
  unidesk/tests/test_cleanroom_base_pattern.py -q` → 27 passed.
- Repository checks: `py unidesk/run_checks.py` → all green; stale-state and
  provenance are honestly reported by the project as `not_built_yet`.
- Independent Sol review: it confirms the base-scoped definitions and warns
  against reusing the existing rolling depth/contraction primitives. It calls
  for an eventual event-sourced episode detector, broader walk-forward
  validation, and versioned selection policies.

## Files and boundaries

- Implementation: `unidesk/momentum/detectors/base_pattern.py`.
- Tests: `unidesk/tests/test_cleanroom_base_pattern.py`.
- Contract and limits: `unidesk/design/CLEANROOM_BASE_DETECTOR_SPEC.md`.

No production scanner, persistence schema, network dependency, or investment
advice surface was changed. Exact proprietary base selection, pivot ratchets,
failed-poke merge rules, RS horizons/weights/universe eligibility, and
historical vendor adjustments remain unverified. Public outputs are used only
for one-time calibration, not as a production input or fallback.
