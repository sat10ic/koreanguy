- [x] Task: Add failing clean-room base detector tests.
  - Acceptance: Tests specify measured fields, no-look-ahead, annotations,
    lifecycle, and RS rank.
  - Verify: The test module fails before implementation because the detector
    module does not exist.
  - Files: `unidesk/tests/test_cleanroom_base_pattern.py`.

- [x] Task: Implement the storage-neutral detector.
  - Acceptance: Tests pass with all non-public choices exposed in `BaseRules`.
  - Verify: Run the targeted pytest command.
  - Files: `unidesk/momentum/detectors/base_pattern.py`.

- [x] Task: Validate and record boundaries.
  - Acceptance: Existing primitive tests continue to pass and the calibration
    result is documented with known non-parity areas.
  - Verify: Run the listed regression tests and `unidesk/run_checks.py`.
  - Files: spec, plan, TODO, completion handoff, attribution ledger.
