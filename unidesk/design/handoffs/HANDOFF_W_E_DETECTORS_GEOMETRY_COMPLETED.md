# HANDOFF W-E detectors + geometry — COMPLETED

Date: 2026-08-29. Slice: all remaining setup detectors (manual P2.3) and the
trade-geometry modules (P2.5–P2.8).

Attribution-ID: attr-unidesk-we-detectors-geometry-glm53flash-20260829-001

## Outcome

- `unidesk/momentum/detectors/engine.py` — shared rule-composition engine:
  mandatory-vs-optional unavailable rules, named failures, honest
  skipped-notes inside VALID results.
- `unidesk/momentum/detectors/setups.py` — the seven remaining detectors
  (episodic pivot, IPO base, inside bar, base breakout, pullback,
  reversal/reclaim, power play), each thin rule composition over
  caller-computed point-in-time features; every threshold a parameter.
- `unidesk/momentum/features/geometry.py` — trigger/stop distance
  (signed), breakout room (+ADR units), initial R:R to the HURDLE with the
  manual's hurdle-vs-target distinction frozen in the docstring, and the
  correction-type classifier (TIME/PRICE/MIXED/UNKNOWN) — code, not prose.
- `unidesk/momentum/scoring/entry_quality.py` — entry-quality composite with
  band normalizers (room/RR/extension/trigger-proximity), config-supplied
  weights, coverage-honest missing-data handling (R12/R14/R15).
- 22 new tests (engine 5, detectors+geometry 17).

Six new tests initially failed on MY expectations (missing import; band
boundary at exactly 3.0 ADR scores 75 not 100) — implementations held.

## Files changed

- `unidesk/momentum/detectors/engine.py`, `unidesk/momentum/detectors/setups.py` (new)
- `unidesk/momentum/features/geometry.py` (new)
- `unidesk/momentum/scoring/entry_quality.py` (new)
- `unidesk/tests/test_detector_engine.py`, `unidesk/tests/test_detectors_geometry.py` (new)
- `unidesk/GOAL.md` (status)

## Verification

```text
.venv-orderflow/Scripts/python.exe -m pytest orderflow/tests unidesk/tests -q -> 199 passed
.venv-orderflow/Scripts/python.exe unidesk/run_checks.py -> exit 0
```

## Honest partials

- Gold fixtures per detector (P2.3 acceptance: positive AND negative real
  examples) are not yet authored — current tests use synthetic rule values.
- GBT scorer (P2.9) and similarity layer (P2.10) remain deferred-until-data
  by the manual's own rule.
- The 8-candidate scan output is a rule result, not a recommendation; the
  benchmark-less RS rank limitation stands until an index series is chosen.
