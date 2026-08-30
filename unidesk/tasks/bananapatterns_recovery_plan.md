# BananaPatterns clean-room recovery plan

## Slice 1 — containment and pure contracts

- [ ] Add additive detector trust metadata; preserve legacy detector values.
- [ ] Add BaseEpisode and ScreenMatcher contracts around the clean-room
  detector.
- [ ] Emit trust in nightly JSON and add unit coverage.

**Acceptance:** unsafe/questionable detectors are visibly non-actionable in
the new integration path; public-clean-room base fields and preset reasons are
reproducible from supplied bars.

**Verification:** focused pytest plus `py unidesk/run_checks.py`.

## Slice 2 — scan integration

- [ ] Wire universe eligibility, CA quarantine, regime and coverage before
  recomputing RS or enabling screen ranking.
- [ ] Emit BaseEpisode references and screen snapshots from the nightly run.

## Slice 3 — terminal integration

- [ ] Feed Stock with real OHLCV and versioned markers.
- [ ] Add Market and Screens views with explicit provenance and unknown states.

## Slice 4 — research validation

- [ ] Repair realised stop/cost labels in a new dataset generation.
- [ ] Production-wire leakage and interval-overlap guards.
- [ ] Re-run only after owner-gated corporate-action and CP-3 gates pass.
