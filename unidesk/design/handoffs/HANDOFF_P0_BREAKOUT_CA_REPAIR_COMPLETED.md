# P0 breakout and corporate-action repair

Attribution-ID: attr-unidesk-p0-breakout-ca-gpt56sol-20260830-001

## Completed slice

- Replaced the legacy base-breakout proxy with prior-only geometry. A setup
  must close above the prior 20-session pivot; depth and contraction exclude
  the decision bar. Blue-sky status is explicit and otherwise requires at
  least one ADR of overhead room.
- Recomputed the four affected gold fixtures from the local NSE bhavcopy
  archive. IGPL was reclassified from a breakout to an invalid case because
  its close did not clear the prior pivot and its prior-only contraction was
  0.827. FILATEX remains a valid case.
- Quarantined a symbol with an unresolved split/bonus-like candidate before
  feature computation and cross-sectional RS ranking. A confirmed action
  restores the symbol after adjustment.

## Verification

`py -m pytest unidesk/tests/test_detectors_geometry.py unidesk/tests/test_detector_registry.py unidesk/tests/test_gold_fixtures.py unidesk/tests/test_report_json.py unidesk/tests/test_base_episode.py unidesk/tests/test_cleanroom_base_pattern.py -q`

Result: 40 passed.

The corporate-action regression suite also passed: 25 tests across detector
registry, corporate actions, and the unconfirmed-action guard.

## Remaining P0 work

This slice does not add the actual liquidity/ETF eligibility gate, a
versioned stop-aware outcome-label generation, costs/slippage, IPO listing
metadata, or earnings-event ingestion. The BananaPatterns public snapshot is
an offline comparison source only; no vendor detector output is used at run
time.
