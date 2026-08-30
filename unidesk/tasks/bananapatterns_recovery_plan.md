# BananaPatterns clean-room recovery plan

## Slice 1 — containment and pure contracts

- [x] Add additive detector trust metadata; preserve legacy detector values.
- [x] Add BaseEpisode and ScreenMatcher contracts around the clean-room
  detector.
- [x] Emit trust in nightly JSON and add unit coverage.

**Acceptance:** unsafe/questionable detectors are visibly non-actionable in
the new integration path; public-clean-room base fields and preset reasons are
reproducible from supplied bars.

**Verification:** focused pytest plus `py unidesk/run_checks.py`.

## Slice 2 — scan integration

- [~] Wire universe eligibility, CA quarantine, regime and coverage before
  recomputing RS or enabling screen ranking.
- [x] Emit BaseEpisode references from the nightly run.

**Completed:** unresolved split/bonus candidates are now quarantined before
features and RS; a matching confirmed action restores the symbol. General
liquidity/ETF eligibility, regime, coverage, and ScreenSnapshot are still
open.

## Slice 3 — terminal integration

- [ ] Feed Stock with real OHLCV and versioned markers.
- [ ] Add Market and Screens views with explicit provenance and unknown states.

## Slice 4 — research validation

- [ ] Repair realised stop/cost labels in a new dataset generation.
- [ ] Production-wire leakage and interval-overlap guards.
- [ ] Re-run only after owner-gated corporate-action and CP-3 gates pass.

## Slice 5 — external comparison harness (offline only)

- [ ] Archive one BananaPatterns public universe snapshot per run, recording
  fetch time, SHA-256, URL, source date, and the exact clean-room config.
- [ ] Build an ISIN-first crosswalk and compare only overlapping symbols and
  sessions; unresolved mapping is a reported exclusion, never a fuzzy match.
- [ ] Compare base membership and fields separately: top-K/Jaccard overlap,
  pivot/base-start date distance, depth/coil/dry error, RS rank correlation,
  and verdict confusion matrix. Publish a per-symbol disagreement table with
  the input evidence needed to reproduce it.
- [ ] Hold out at least one archived snapshot for acceptance. Tune only on
  earlier snapshots; the held-out report must state recall, precision, and
  coverage, not a single blended score.

**Acceptance:** the report is reproducible from archived inputs and confirms
that vendor fields are never read by the production scanner, ranker, or UI
recommendation path.

**Verification:** fixture tests prove source hashing, point-in-time filtering,
and crosswalk failures; one saved benchmark report passes its schema check.

## Slice 6 — IPO and earnings event foundations

- [ ] Add a versioned IPO listing-facts store: NSE symbol/ISIN, listing date,
  source URL, retrieved timestamp, and available-at timestamp. Use listing
  date for IPO-age rules; do not infer it from local bar history.
- [ ] Evaluate `gagandt/ipo-ai` as a *reference importer*, not a production
  dependency. Preserve its raw source documents and reject unmatched records;
  its README documents both missing NSE past-issue records and unsafe name
  matching.
- [ ] Add an NSE corporate-filings event store with received/disseminated
  timestamps, filing type, period ended, attachment hash, and parser version.
  EP eligibility uses the first public result timestamp, never a future
  estimated earnings date.
- [ ] Treat `thekrishnasoni/nse_earnings_tracker` as a useful calendar/client
  reference only. Treat `manish70158/nse-earnings-analyzer` as exploratory:
  it combines NSE event discovery with Yahoo Finance estimates and fallback
  stock lists, so its surprise/consensus fields cannot enter a point-in-time
  research label without independently archived source evidence.

**Acceptance:** IPO and result-event records carry source and availability
timestamps; tests reject future knowledge, missing listing dates, and
unverifiable surprise values.
