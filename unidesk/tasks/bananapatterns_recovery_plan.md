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

- [~] Add a versioned IPO listing-facts store: NSE symbol/ISIN, listing date,
  source URL, retrieved timestamp, and available-at timestamp. Use listing
  date for IPO-age rules; do not infer it from local bar history.
  **DONE:** `IPOListingFact` rejects missing provenance and future knowledge.
  **STILL OPEN:** official listing-notice ingestor and persisted raw archive.
- [ ] Evaluate `gagandt/ipo-ai` as a *reference importer*, not a production
  dependency. Preserve its raw source documents and reject unmatched records;
  its README documents both missing NSE past-issue records and unsafe name
  matching.
- [~] Add an NSE corporate-filings event store with received/disseminated
  timestamps, filing type, period ended, attachment hash, and parser version.
  EP eligibility uses the first public result timestamp, never a future
  estimated earnings date.
  **DONE:** `EarningsResultEvent` enforces realised-result availability and
  source hashing. **STILL OPEN:** official-filings ingestor and persisted raw
  archive.
- [ ] Treat `thekrishnasoni/nse_earnings_tracker` as a useful calendar/client
  reference only. Treat `manish70158/nse-earnings-analyzer` as exploratory:
  it combines NSE event discovery with Yahoo Finance estimates and fallback
  stock lists, so its surprise/consensus fields cannot enter a point-in-time
  research label without independently archived source evidence.

**Acceptance:** IPO and result-event records carry source and availability
timestamps; tests reject future knowledge, missing listing dates, and
unverifiable surprise values.

### Slice 6a — authoritative IPO and realised-results ingestors

- [ ] **IPO listing ingestor:** archive the official NSE/BSE listing notice or
  listing document; extract exchange symbol, ISIN, listing date and publication
  timestamp; hash the exact source. Reconcile against the earliest official
  bhavcopy session, but never derive the listing date from it. Reject a
  symbol-only or name-only match.
- [ ] **Realised-results ingestor:** archive NSE corporate filings and BSE
  corporate announcements; retain received/disseminated timestamps, result
  attachment, attachment hash, parser version and fiscal period. The NSE Results
  Calendar is schedule-only metadata; it cannot create an EP event or a
  surprise label.
- [ ] **Availability and revision policy:** records are append-only; a correction
  is a new version with its own retrieval timestamp. Failed source retrieval or
  a missing result attachment yields `UNRESOLVED`, never a guessed date,
  estimate, or backfilled availability time.
- [ ] **Event-anchored AVWAP research feature:** IPO candidates use an AVWAP
  beginning at the first tradable primary-listing session. EP candidates use
  an AVWAP beginning at the first completed session after the exchange
  dissemination timestamp (EOD mode); an eventual intraday mode must anchor to
  the first bar after dissemination. The announced calendar/board-meeting date
  is forbidden as an anchor. Preserve the anchor fact ID, source hash, session,
  adjustment basis and volume basis with every feature value.
- [ ] **Promotion gate for anchored AVWAP:** evaluate post-listing and
  post-results AVWAP distance/slope/hold separately by setup family and market
  regime, with an event-time embargo and held-out period. It is a displayed
  research feature only until net-of-cost, stop-aware walk-forward evidence
  beats the non-anchored baseline; it may not become an EP/IPO screen gate by
  intuition alone.

**Acceptance:** a fixture per exchange proves IPO age comes from an official
listing record (not bar count), and a result becomes visible only at its archived
dissemination timestamp. An outage or ambiguous match is rejected without an
IPO/EP candidate.

**Verification:** contract/importer fixtures, source-byte SHA-256 checks,
point-in-time reads before/after dissemination, and an archive-manifest check.
Anchored-AVWAP fixtures prove that a scheduled-but-not-disseminated result
cannot influence the anchor, and that a correction or corporate-action basis
mismatch is rejected rather than silently rebased.
