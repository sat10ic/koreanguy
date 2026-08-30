# Unified desk — backlog

Status: `[x]` done · `[~]` partial/in progress · `[ ]` pending.
Controlling plan: `plan/UNIFIED_DESK_INTEGRATION_PLAN.md` (crosswalk) and
`plan/UNIFIED_DESK_BUILD_MANUAL_V2.md` (design/build spec, as-built D14–D17).
V1 `UNIFIED_DESK_BUILD_MANUAL.md` is historical.

Rules (inherited from the TraderLog chain): keep this current **at every wave
close**, not at session end; titles stable, numbers not; `[~]` requires an
explicit **DONE / STILL OPEN** split; every closed item carries evidence (a
measured number, a file:line, or a command); nothing disappears silently —
killed items move to DROPPED with a reason. Unified tasks carry the `U-`
prefix (DECISIONS.md D3).

# OUTSTANDING

## U-P0 — Freeze contracts, audit data, start recording

- [x] **U-P0.2 — Shared contracts scaffold** (2026-08-28)
  **DONE:** 12 contract schemas implemented as validated frozen dataclasses in
  `unidesk/contracts/` (market/candidate/setup/geometry/flow/social/decision/
  research); unknown enums fail closed; nulls stay null; `as_of` tz-aware and
  mandatory on time-sensitive snapshots; version/hash fields mandatory; stable
  `to_dict()` serialization. Evidence: `python -m pytest unidesk/tests -q`.
  **STILL OPEN:** schemas are declarations until Phases 1–3 produce real data;
  any field the manual refines later is an append-only contract-version bump.
- [~] **U-P0.4 — FYERS capability audit (live half)** — blocked on owner session
  **DONE:** offline apparatus + synthetic run (see COMPLETED); protocol
  verification and venv preparation
  (`orderflow/design/handoffs/N1_LIVE_SESSION_PREP_STOP.md`,
  attr-orderflow-n1-prep-glm53flash-20260828-001); launcher + owner-side
  transport shim + R1 gate table built 2026-08-29
  (`orderflow/checks/run_live_session.py`, `scripts/fyers_live_transport.py`,
  attr-orderflow-n1-launcher-glm53flash-20260829-001); benign poll-timeout
  path added to the manager (quiet seconds no longer trigger reconnects).
  **STILL OPEN:** owner starts a session during NSE market hours (next: Mon
  2026-08-31 pre-market; 2026-08-29/30 is a weekend); symbol list is
  provisional pending owner sign-off; R1 gate table must be produced from a
  real session; 50-level TBT probe with evidence; live forced-disconnect
  test; depth-size scaling confirmation (first live sample).
- [~] **U-P0.5 — Continuous raw depth recorder** (offline core closed 2026-08-29)
  **DONE:** append-safe Parquet quote/depth/health/lifecycle/gap persistence
  with `date=/symbol=` partitions; DuckDB research views and canonical depth
  replay; batching; null preservation; reconnect recovery that requires fresh
  post-gap depth; recursive raw/error secret redaction; recorder-first owner
  launcher callbacks and periodic/final flush. Evidence: **84 orderflow tests
  passed**, **102 orderflow + unidesk tests passed**, compileall exit 0;
  `orderflow/design/handoffs/N2_OFFLINE_RECORDER_CORE_COMPLETED.md`.
  **STILL OPEN:** owner-run NSE session proving sustained writes, forced
  disconnect/resubscribe, visible real gaps, full-session replay, measured
  row/disk rate, and credential absence in real output. No live session was
  attempted; `capability.json` remains synthetic.
- [x] **U-P0.1 — Repository and data-authority map** (2026-08-29)
  **DONE:** read-only inventory formalized in
  `unidesk/design/DATA_AUTHORITY.json` + `.md`: 20 logical persistent stores
  have named owners/writers and accepted/provisional/quarantined/archive-only
  classes; 12 unified fields have exactly one authority or an explicit
  unresolved state; APIs/sources and reuse/copy/retire boundaries are named.
  TraderLog production was queried read-only: 18 current accepted positions / 12
  events, 305 deterministic quarantined positions / 436 events, zero claims and
  claim links. The validator prevents quarantined/archive stores from becoming
  field authorities and requires all four lifecycle classes. Evidence: 6 focused
  tests pass; `python unidesk/run_checks.py` reports `data_authority` pass; no
  production data was modified. Full combined regression: **109 passed**.
- [x] **U-P0.3 — Point-in-time market store** — **STALE CHECKBOX, actually
  DONE** (found 2026-08-30 while sweeping TASKS.md for open items; no new
  code, correcting the record). `InMemoryMarketStore.get_market_state(symbol,
  as_of)` (`momentum/data/market_store.py:118`) is fully implemented:
  resolves classification/daily/intraday state as of an instant, each read
  path filtering on both the observation's own date/timestamp AND
  `available_at <= as_of` (future-row invisibility). 9 tests in
  `test_momentum_market_store.py`, including the exact fixtures this item
  asked for (`test_future_and_same_session_eod_bars_are_hidden_until_available`,
  `test_intraday_never_returns_future_bar_or_future_revision`) — all pass.
  The persistent storage-home decision remains genuinely open (still an
  in-memory reference port per its own docstring) — that part of this item
  is real and unchanged.
- [~] **U-P0.6 — Authoritative IPO and realised-results ingestion** (planned
  2026-08-30)
  **DONE:** fail-closed source contracts exist in
  `research/market_events.py`: IPO facts require symbol/ISIN, listing date,
  HTTPS source, availability/retrieval timestamps and a SHA-256 source hash;
  realised results require received/disseminated/availability timestamps,
  attachment hash and parser version. **STILL OPEN:** append-only source
  archive and official importer: IPO listing notices/documents from NSE/BSE
  (cross-check earliest official bhavcopy, never infer from it), plus NSE
  corporate-filings and BSE announcements for realised results. The NSE
  Results Calendar remains schedule-only and may not create an EP label.
  **Pass condition:** every emitted IPO/EP fact carries archived source bytes,
  an ISIN-first identity link and a public availability timestamp; source
  failure or ambiguous mapping is refused, not guessed.
  **FOLLOW-ON (not a gate yet):** research event-anchored AVWAP from the first
  tradable IPO listing session or, for an EOD EP workflow, the first completed
  session after an archived realised-results dissemination timestamp. Persist
  the fact ID, source hash, anchor session, adjustment basis and volume basis.
  Validate distance/slope/hold against a non-anchored baseline with event-time
  embargo, held-out data, stop-aware outcomes and explicit net costs before it
  can rank or filter a screen; scheduled earnings dates are forbidden anchors.
  **PAUSED IN PROGRESS:** `research/event_anchors.py` defines the pure
  fact-backed anchor/AVWAP contract and tests; no source importer, feature-store
  persistence, screen integration, or held-out validation has been completed.

## N-WAVES — EOD-first build (Build Manual V2 §6)

- [~] **N1 — Nightly pipeline v1** — 2026-08-29
  **DONE:** `unidesk/momentum/scan.py` (universe scan, point-in-time),
  `report.py` (TONIGHT markdown per UI V2 §3), `nightly.py` (CLI:
  download→ingest→scan→report). Real run: 2,563 symbols scanned on
  2026-07-03, 65.9% above EMA50, 3 burst candidates, report on disk.
  Evidence: 209 tests; `data/market/reports/tonight_2026-07-03.md`.
  **STILL OPEN:** downloader subprocess tested only against the local
  backlog (network mirror run pending); candidate store persistence (N4);
  persistent store cache (re-ingests all files per run — 73 s, acceptable).
- [x] **N2 — Universe gates + missing primitives + R0 regime classifier** — 2026-08-29
  **DONE:** gates adopted by copy from activity.py (price/turnover floors,
  ETF heuristic, circuit-freeze heuristic, mcap-skip-surfaced);
  spec-library primitives (sma, median-RVOL, delivery_z, pocket_pivot,
  tight_ratio, stack_bull, stage2); R0 classifier (breadth-only mode,
  hysteresis 3d). Real-data proof: 233 sessions of breadth computed from
  the full backlog; late Jun/Jul 2026 classified BULL (0.56–0.64).
  Evidence: 222 tests. **STILL OPEN at N2 close:** index series. **Later
  closed by D16/D17:** Midcap 150 vs SMA50 when ≥50 sessions
  (`breadth_and_midcap150_sma50`); Nifty SMA200 computable, not in the
  label rule; VIX stored, 1y z-score not labelled.
- [~] **F2 audit finding — quality-score layer + R0 regime classifier had
  zero production call sites** — 2026-08-30 (attr-unidesk-quality-regime-wiring-claude-sonnet5-20260830-001)
  **CLOSED, stock-quality + regime:** `scan_universe` now calls
  `stock_quality_snapshot` per symbol (real `distance_52w_high_pct` from a
  252-session rolling high, real `circuit_state` from `DailyBar`'s own
  `upper_circuit`/`lower_circuit`), attached to `SymbolScan.stock_quality`
  and surfaced additively in `report_json.py`'s per-candidate dict.
  `nightly.py` now runs a real `RegimeClassifier` fed real breadth
  (`scan.pct_above_ema50`), replacing the hardcoded `regime_note="not built
  yet"` in both the Markdown and JSON reports. New `momentum/regime_state.py`
  persists hysteresis (`current`/`pending`/`pending_days`) across nightly
  runs via one JSON file, closing the "resets every night" gap a stateful
  classifier has in a fresh-process pipeline; idempotent same-session
  re-runs do not double-count a hysteresis day. Verified end-to-end against
  the real bhavcopy backlog (not just fixtures): real per-candidate scores,
  a real `BEAR` regime label, a real persisted-then-reloaded state file.
  **STILL OPEN:** `entry_quality_snapshot` is now correctly exported from
  `scoring/__init__.py` (its own `__all__` bug, plus a missing
  `Optional`/`Sequence` import that broke the module's import entirely) but
  NOT wired into the scan loop — its required `trigger`/`invalidation`/
  `hurdle` prices do not exist anywhere in this pipeline (checked
  `detectors/setups.py` and `features/geometry.py` directly; no production
  caller computes a real breakout trigger, stop, or confirmation-hurdle
  price). Wiring it would require inventing that geometry, which this
  project's own R12 discipline forbids — reported as an honest gap, not
  closed. Also open: `RegimeClassifier`'s Midcap-150-vs-SMA50 confirmation
  stays `breadth_only` in production because the index harvest
  (`data/market/reference/indices.parquet`) does not exist in this repo.
  Evidence: `unidesk/tests/test_quality_regime_wiring.py` (6 new tests) +
  full suite. Report:
  `unidesk/design/handoffs/HANDOFF_QUALITY_LAYER_REGIME_WIRING_COMPLETED.md`.
- [~] **N3 — Corporate-action adjustment + extended history + index/sector
  series** (Phase 0 data-build spec, D14/D15)
  **DONE this slice:** D15 archive home = `data/bhavcopy/` (503 files, 477
  sessions, 2024-09-02 → 2026-08-28, **1,004,896 bars**); nightly ingest
  default corrected to the downloader's target; Chartsmaze event tables
  (IPO listings, circuit revisions with PIT lookup, 10,972 announcements
  as a non-adjusting review queue, vendor breadth series); split detector
  + close-to-close confirmation (`adjustment_kills_the_gap`) on real 2:1
  names (ANANDRATHI 2026-06-03, BEML 2025-11-03, AGIIL 2025-02-07,
  ANUHPHR 2025-07-15). 194 open-gap candidates; open-gap ≠ confirmed.
  **DONE also:** D16 `ind_close_all` overlay; **D17 manas.db RO extract** —
  Nifty 50 + India VIX from 2021-06-01 (1,299 / 1,293 sessions), Midcap 150
  / 500 / Smallcap 250 from 2024-07-08 (533); overlay through 2026-08-28;
  18 dated universe snapshots (43,980 rows). SMA200 computable on Nifty 50.
  **DONE also:** **D18** nexus industry fill from
  `manas_os/data/nexus_industry_map.csv` (RO, no import): 349 names
  Chartsmaze lacked; Chartsmaze kept on 2,327 overlap (labels disagree).
  Map is 2,772 with `source_tier`. Spec: Build Manual V2 R-R / §12.8.1.
  **DONE also:** confirmed CA seed (ANANDRATHI, BEML, AGIIL, ANUHPHR 2:1)
  applied as a derived scan view; raw bhavcopy untouched; nightly loads
  `config/confirmed_actions.csv`. ASHOKLEY-style open-gap fills stay out.
  **STILL OPEN:** 2016-01-01 bhavcopy (manas `daily_prices` back to 2021 is
  inventoried, not adopted — D-decision); official CA-with-ratios; PIT
  membership before Jul 2026; ISIN/continuity_id; MTO; official bands; F&O
  PIT; `make rebuild` hashes.
- [x] **N3 directive-4 — CA-ratio review-queue artifact** — 2026-08-30
  (attr-unidesk-ca-review-queue-claude-sonnet5-20260830-001). Producing the
  queue was never owner-gated (only the ratio source is);
  `run_ca_review_queue.py` runs the existing detector across the full
  backlog, filters out confirmed `(symbol, ex_date)` pairs, writes
  `config/ca_review_queue.csv` — **190 unconfirmed candidates**, reconciling
  exactly with the documented 194 minus the 4 since-confirmed. No ratio
  inferred or recommended; owner (or a future official CA feed) confirms
  each row and moves it into `confirmed_actions.csv`.
- [~] **N4 — Research spine** (candidate store, cost model §1.4,
  walk-forward simulator, leakage suite P7.3) — 2026-08-29
  **DONE this slice:** freeze every detector decision (VALID and INVALID)
  as `ResearchEvent`; expanding walk-forward with 5-session embargo and
  next-bar fills; simulate_long reports gross AND net; P7.3 suite catches
  planted bugs (future bars, full-sample normalisation, today's
  membership, future gold); `run_checks` leakage smoke is live.
  **DONE also:** parquet `date=` event store; nightly freeze after scan;
  `attach_outcomes` (next-bar fill, UNRESOLVED if no future; decision bar
  excluded).
  **DONE 2026-08-30 (directive 1a-e, Claude Sonnet 5):** module-enumerating
  truncation-invariance test over `momentum/features|primitives|scoring`
  (40 callables enumerated via `pkgutil`, 19 real prefix-invariance checks,
  1 special-cased pivot check, 20 explicit reasoned skips, self-checking
  against drift — `tests/test_truncation_invariance.py`);
  `labels.py:assert_future_only` wired into `attach_outcomes`
  (`tests/test_labels_future_only.py`); `SymbolScan.adjusted` +
  `_snapshot()`/`config_hash_for()` now carry the confirmed-actions CONTENT
  hash + `costs.COSTS_VERSION` (`tests/test_adjustment_basis_guard.py`);
  `attach_outcomes` refuses on an adjustment-basis mismatch
  (`UNRESOLVED`/`adjustment_basis_mismatch`) and on an outcome window that
  spans one of the LIVE unconfirmed corporate-action candidates
  (`splits.py:unconfirmed_candidate_sessions`, tested against a real
  detector-flagged fixture with a negative control proving it's load-bearing
  — `tests/test_unconfirmed_ca_guard.py`). Report:
  `design/handoffs/HANDOFF_N4_LEAKAGE_GUARDS_COMPLETED.md`. Cost model and
  P7.3 suite untouched, confirmed already complete.
  **DONE also (2026-08-30):** candidate-store persistence verification
  (directive 1h) — `event_store.py`'s `snapshot_json` is a whole-dict JSON
  serialization, so the new `adjusted`/`ca_table_hash` fields already
  survive the round trip with no extra work, confirmed by direct read
  rather than assumed. Split-detector index bug (found during directive-1e
  test-writing) is FIXED — `corp_actions.py:detect_split_candidates_bars`
  now uses a carried `gap_index` instead of `closes.index()` value-lookup;
  8 of 194 real-archive candidates were mis-dated by the old code (up to
  ~9 months), confirmed by direct old-vs-new comparison. Real unconfirmed
  count is **190** (194 detected minus 4 confirmed) — use 190 for "the
  unconfirmed backlog size" going forward, 194 only for the raw detector
  total.
  **DONE (2026-08-30, corrected 2026-08-30):** directive-1(f), archive-wide
  outcome attach. `research/archive_attach.py` builds the future map with
  the same adjustment basis as the original scan (closing the Opus-flagged
  trap cleanly — zero `adjustment_basis_mismatch` cases in the real run).
  **The first-reported figure (702,369 events) was an UNDERCOUNT, not a
  complete run** — its background process was killed by the host after
  ~320/396 sessions and the committing session mistook the process's exit
  for a clean finish, not a kill; 76 sessions (2026-05-07 → 2026-08-26)
  were never attempted, not merely the one flagged-as-benign 2026-08-28 gap.
  A resume driver (`run_archive_attach_resume.py`) found and reprocessed
  all 78 stale/missing sessions. **Corrected, complete total: 904,221
  events across all 396 eligible sessions** — 844,872 RESOLVED, 24,889
  PARTIAL, 34,460 UNRESOLVED (31,255 no_future_bars + 3,205
  unconfirmed_corporate_action + 0 adjustment_basis_mismatch). Report:
  `design/handoffs/HANDOFF_N4_ARCHIVE_ATTACH_COMPLETED.md` (corrected in
  place).
  **Urgent finding, re-verified on the complete store:** 58.53% of resolved
  events (494,540 of 844,872) have `stop_hit=True` with a positive
  `r_multiple` recorded anyway. **FIXED IN THE LABEL CODE on 2026-08-30:**
  `r_multiple` now records conservative stop-first `-1R`, with MFE retained
  separately as `potential_r_multiple`; realised gross return also exits at
  the stop rather than a later close. **STILL OPEN:** the existing archive is
  legacy stop-blind output and must be regenerated before it is analysed; net
  returns require supplied order-value/ADV inputs and must not default them.
  **DONE, 2026-08-30 (resumed from a paused slice, verified, committed):**
  `OUTCOME_LABELS_VERSION` stamped on every outcome;
  `sessions_needing_label_refresh()` built for version-aware regeneration
  (not yet run against the archive). Report:
  `design/handoffs/HANDOFF_N5_LABEL_VERSION_EVENT_ANCHOR_COMPLETED.md`.
  Fact-backed IPO/EP AVWAP primitives (`event_anchors.py`) also committed,
  research-only, no production consumer yet.
  **DONE, 2026-08-30 — archive regenerated, stop-blind defect eliminated
  (verified, not just run).** `run_archive_attach_resume.py` adapted to use
  `sessions_needing_label_refresh` instead of its old `status`-key check;
  all 396 eligible sessions reprocessed (8122.7s wall clock). Verified
  directly from `load_events(root="data/market")` after completion: 396/396
  partitions, 863,771 events (807,516 RESOLVED / 23,192 PARTIAL / 33,063
  UNRESOLVED), **zero** events off the current label version, **zero**
  `stop_hit=True` events with a positive `r_multiple` — the prior 58.53%
  stop-blind figure is superseded. An uncommitted gap-through refinement
  found mid-run in `labels.py`/`candidates.py`/`walkforward.py` (a
  concurrent session's work, `attr-unidesk-n4-gapthrough-fix-glm53flash-
  20260830-001`) was confirmed NOT used by this run (no hot-reload) and
  confirmed not to affect the defect check either way; its
  `OUTCOME_LABELS_VERSION` was not bumped, so a future commit of it needs
  another regeneration to be detected as stale. Report:
  `design/handoffs/HANDOFF_N4_ARCHIVE_REGENERATION_COMPLETED.md`.
  **CORRECTION (2026-08-30, Cline junction audit): the "396/396 zero events
  off the current label version" claim above is NOT currently true from
  disk. A direct read of every partition today shows 162,962 events still on
  `outcome-labels-v2-stop-aware` (the 63 newest sessions, including
  2026-08-28), and two regen processes are concurrently re-writing the store
  right now (the exact near-miss the HANDOFF warned about). The 8122.7s pass
  above may have completed, but a later concurrent writer has since made the
  store label-mixed again. See the ⚠ AUDIT block in the "UI backend
  integration" entry for the full picture. The store must be re-verified
  all-v4 from disk and left to settle before any outcome research or History
  wiring is trusted.**
  **STILL OPEN:** 4y/1y folds (calendar too short until 2016 history);
  `assert_feature_not_after_decision`/`same_event_collision` remain
  test-only callers (used as internal assertions by other guards, not
  invoked from a top-level driver); ablation ladder P7.4 (directive 1g) —
  the archive is now current, but N5's other blockers (cost inputs,
  CA-ratio authority) are unchanged, so ablations still must not run yet.
- [x] **N5 blocker — same-symbol overlapping-horizon embargo control** —
  2026-08-30 (attr-unidesk-same-symbol-embargo-claude-sonnet5-20260830-001).
  `leakage.py::embargo_overlapping_events(events, calendar, window=60)`:
  greedily keeps the earliest event per same-symbol cluster, embargoes
  later same-symbol events inside the window, resets the window on each
  fresh keep (verified against a +0/+61/+122-session run that must stay
  fully independent). Outcome-blind by construction. **Honest limitation:**
  built and tested, NOT yet called from a running pipeline — the P7.4
  ablation ladder that would consume it does not exist yet. Closes the
  "control absent, unbuilt" half of this blocker; N5 stays NO-GO on
  CA-ratio authority and the in-progress archive regeneration regardless.
- [x] **DONE, 2026-08-30 — fixed the `-1.0` gap-through understatement in
  `labels.py`.** `opens` now threaded through `long_outcome` (required, not
  optional) / `attach_outcomes` / `simulate_long`; realized R uses
  `min(gap_open, stop)` on the stop bar; `exit_price`/`gap_through`
  persisted on every `Outcome`. See `attr-unidesk-n4-gapthrough-fix-glm53flash-20260830-001`
  and the orchestrator correction/completion at
  `attr-unidesk-net-cost-wiring-fix-claude-sonnet5-20260830-001`
  (`design/handoffs/HANDOFF_NET_COST_WIRING_COMPLETED.md`) — the first pass
  left a live `NameError` in `walkforward.py`'s gap-through fill, fixed
  there. Every persisted event predates this fix; reflected by the archive
  regeneration in progress (see HANDOFF.md for status).
- [x] **DONE, 2026-08-30 — `blue_sky` fixed.** `inputs.py` now requires
  `BLUE_SKY_MIN_SESSIONS=61` (matching `scan.py`'s own trust floor) before
  resolving `blue_sky` at all; below it, `None` (unresolved), never a
  guess. Operator fixed to strict `>`, matching `close_cleared_pivot`. Two
  regression tests including the exact n=21 degenerate boundary, proving
  `base_breakout()` now returns `INSUFFICIENT_DATA` rather than silently
  passing. Report: `design/handoffs/HANDOFF_BLUE_SKY_FIX_COMPLETED.md`.
- [ ] **N5 — Experiments A & B** (T1 vs raw breakout; T5 Path B vs
  gap-and-go) — pre-registered kill criteria, net-of-cost.
  **NO-GO as of 2026-08-30, THREE conditions now**: (a) CA-series gate
  unmet (4/198 confirmed); (b) the event archive must be regenerated from the
  stop-aware label code and evaluated with explicit cost inputs; (c)
  same-symbol overlapping-horizon control is still absent. CP-3 owner-invoked
  leakage audit (GOAL.md: "highest-risk gate in the build") has not run. See
  HANDOFF.md directive 3.
- [ ] **N6 — Surviving edges + preset pack (VCP/BlueSky/MultiYear/IPOBase)
  + AI analogue engine per-edge if baselines beaten.**
- [ ] **N8 — Terminal UI per UI manual V2** (report renderer first).
- [~] **UI backend integration** (2026-08-30 — see
  `design/UI_BACKEND_INTEGRATION_PLAN.md`) — `unidesk_terminal/` had zero
  real data wiring (fixtures.ts only).
  **DONE:** Step 1, `report_json.py` emits `tonight_<date>.json` alongside
  the Markdown report — built from `ScanResult`/`SymbolScan` directly, NOT
  via `contracts.*.to_dict()` (the plan's original premise was wrong;
  verified false before writing code — `report.py` never used the frozen
  contracts objects). Real output verified:
  `data/market/reports/tonight_2026-08-28.json`.
  **DONE also:** Step 2, Tonight/Candidates screens wired to all 268 real
  candidates (commit `6cd84a67`), distinguished from illustrative fixtures
  by a "REAL SCAN" badge, never blended. Real honesty-footer fields render
  live. Report:
  `design/handoffs/HANDOFF_UI_TONIGHT_CANDIDATES_WIRED_COMPLETED.md`.
  **A concurrent trading-logic audit found several detectors now visible
  through this UI have real logic defects (most severely `base_breakout`
  — no breakout condition, inverted room rule); the generic disclaimer
  covers this honestly but no per-detector warning exists yet — worth
  adding.**
  **STILL OPEN:** `UI_BACKEND_INTEGRATION_PLAN.md` needs the
  `contracts.*.to_dict()` correction folded in; a multi-date report picker
  (hardcoded to one report on disk); History waits on the N4 adjustment-basis
  guard AND the archive-attach future-map basis fix above;
  Research waits on N5 being lifted.
  **DONE, 2026-08-30 — Stock real-chart wiring.** The paused slice completed:
  `run_stock_history_export.py` (backend, from the paused slice) +
  `StockChart.tsx` now renders real point-in-time bhavcopy bars when supplied
  (`history?: Bar[]`), `Stock.tsx` calls `getRealHistory(symbol)` and shows a
  visible honesty header/footer on the real vs synthetic-fallback paths — no
  silent blend. Verified export: **235/235 tonight symbols, 29,979 bars,
  zero sessions after session_date 2026-08-28, zero last-close mismatches**;
  `npm run build` + `npm run lint` clean. Report:
  `design/handoffs/HANDOFF_STOCK_REAL_CHART_WIRING_COMPLETED.md` (attr-unidesk-stock-real-chart-wiring-cline-20260830-001).
  **GATE MET, next to wire:** History — the N4 adjustment-basis guard and the
  archive-attach future-map basis are both DONE (zero
  `adjustment_basis_mismatch`; store regenerated stop-aware + net-of-cost),
  so row 4 is no longer blocked on backend.
  **⚠ AUDIT, 2026-08-30 (Cline, junction review) — the archive is NOT
  actually label-clean right now, and is being regenerated concurrently.
  Do not wire History until this resolves.**
  A direct read of `data/market/research/events/date=*` (every partition,
  via `load_events`) shows **162,962 events (~19%) still on
  `outcome-labels-v2-stop-aware`** — the 63 newest sessions
  (2026-05-29 → 2026-08-28, including tonight's 2026-08-28). That contradicts
  the "396/396, zero events off the current label version" claim above (which
  came from `archive_attach_summary.json` — a counter that only tallies
  `status`/`reason` and **never reads `label_version`**, so it cannot detect
  exactly this). **Those newest-session labels predate the gap-through fix and
  carry no `net_bps`.**
  Cause: **two regen processes are running concurrently right now** — PIDs
  31472 (started 21:02) and 5036 (started 23:21), both
  `run_archive_attach_resume.py`, both writing the same partition dir, with
  non-monotonic partition mtimes proving interleaving. This is the exact
  near-miss HANDOFF.md documented (and it is happening *now*).
  Safe stall: no writer to `data/market/research/events/` may be added, and
  `History` (which would render stale v2 outcomes for the newest sessions)
  must stay **blocked** until the store is verified all-v4 from disk.
  Also: I did NOT kill either process; both stay live.
  **Status 2026-08-30 ~00:49 IST: still converging (87.6% v4 in the first5
  sample, unchanged since my last read). The regen is progressing through
  the archive (recent writes are moving through 2026-06). Do not wire
  History until the newest 63 sessions are all v4.**
  **DONE, same pass:** Settings real config surfacing (row 6) wired
  (costs/labels/universe-gates from code constants, detector trust table
  visible); per-detector trust chip wired into candidate cards + group
  headers; `same_event_collision` leakage guard production-wired into
  `scan_universe`. 70/70 scan+leakage+detector tests pass.

## U-P1+ — placeholders (definitions live in the build manual; do not start before the Phase 0 checkpoint)

- [ ] **U-P1.1–P1.10 — Momentum Context Engine** (daily universe, trend, RS,
  participation, ADR/ATR, AVWAP, sector/peer/theme, circuit risk, stock
  quality, Model A baseline).
- [ ] **U-P2.1–P2.10 — Setup detection + trade geometry.**
- [ ] **U-P3.1–P3.10 — OrderFlow integration** (tiers, trigger state machine,
  slow-feed-safe features, conditional fast features, liquidity/capacity,
  confidence+decision, validity window, alerts, replay, ablation).
  Implementation reference: `plan/ORDERFLOW_BUILD_MANUAL.md`.
- [ ] **U-P4.x — TraderLog Lite.** Owner-scope decisions required first
  (claim-extraction LLM inference is already blocked pending an owner call in
  traderlog's own chain).
- [ ] **U-P5.x — Context Judge + deterministic policy.**
- [ ] **U-P6.x — Unified terminal + alerts** (UI manual is the spec).
- [ ] **U-P7.x — Research spine** (event store, labels, leakage suite,
  ablation ladder A–J, promotion gates).
- [ ] **U-P8.x — Discipline/journal** (explicitly later).

# COMPLETED

- [x] **Orderflow Phase-0 apparatus** (= U-P0.4 offline half) — 2026-08-28
  Canonical schemas, sole-FYERS-aware adapter, provider-agnostic websocket
  manager, capability auditor with replay harness.
  **Evidence:** 62 tests pass (`python -m pytest orderflow/tests -q`);
  synthetic end-to-end `capability.json` with real histogram, per-bucket
  medians, 8.8 s disconnect gap recorded, boundary tests enforce FYERS-name
  confinement / no-order-routing / no-cross-imports.
  `orderflow/design/handoffs/P0.1_CAPABILITY_AUDIT_COMPLETED.md`,
  attr-orderflow-p01-capability-audit-glm53flash-20260828-001.
- [x] **U-P0 integration slice: manuals + governance chain + contracts** — 2026-08-28
  Unified manuals copied into `plan/` with adoption notes; `unidesk/`
  governance chain (CANONICAL/DECISIONS/TASKS/HANDOFF/STATE +
  machine-checked attribution) stood up; 12 shared contracts scaffolded;
  crosswalk + persisted Autoclaw handover written.
  **Evidence:** `python -m pytest unidesk/tests orderflow/tests -q`;
  `python unidesk/run_checks.py` exit 0.
  `unidesk/design/handoffs/HANDOFF_U_P0_GOVERNANCE_AND_CONTRACTS_COMPLETED.md`.
- [x] **N1 preparation (protocol verification + venv)** — 2026-08-28
  fyers-apiv3 3.1.16 wheel verified against the installed package; adapter
  mapping confirmed exact; transport design fixed (D7).
  **Evidence:** `orderflow/design/handoffs/N1_LIVE_SESSION_PREP_STOP.md`,
  attr-orderflow-n1-prep-glm53flash-20260828-001.
- [x] **F5 audit finding closed: universe scan was ungated** — 2026-08-30
  `momentum/scan.py` never imported the already-built
  `momentum/universe/gates.py` (price/turnover floors, probable-ETF
  keyword heuristic, circuit-lock heuristic); the cross-sectional RS-rank
  denominator every detector's `rs_rank >= N` gate depends on was computed
  over penny stocks, ETFs, and circuit-locked names. Wired gates in before
  `universe_returns` is built, same pattern as the existing CA-quarantine
  exclusion; new `apply_universe_gates` param (default `False` on
  `scan_universe`, `True` in `nightly.py`, the in-scope production entry
  point). Also fixed two real ETF-heuristic false positives confirmed
  against the actual archive: `ABSLAMC` (removed the bare `"ABSL"` keyword)
  and `JETFREIGHT` (added to a small confirmed-override set). Real archive
  run: universe shrinks 2,529 -> 1,380 tradeable symbols once gated
  (-45.4%), fully reconciled both ways.
  **Evidence:** `python -m pytest unidesk/tests -q` — 283 passed, 21
  skipped, 0 failed (new test:
  `test_scan_applies_universe_gates_before_rs_ranking`); `python
  unidesk/run_checks.py` all green.
  `unidesk/design/handoffs/HANDOFF_UNIVERSE_GATES_WIRED_COMPLETED.md`,
  attr-unidesk-universe-gates-wired-claude-sonnet5-20260830-001.

# DROPPED / DEFERRED BY DECISION

- [~] **W-F flow features + trigger state machine (live)** — DEFERRED to the
  optional live module (D10/D13, Build V2 §8, wave N7). The offline-reusable
  parts (spread/imbalance/persistence/price-response math) return as N7
  internals if that module is ever activated. Reason: EOD-first product
  (owner is a swing trader); nothing in the nightly cadence waits on it.

# USER-SIDE ONLY

- **Live FYERS session start (U-P0.4).** Owner performs token refresh
  out-of-band, fixes the >=8-symbol list across the four liquidity buckets,
  and starts `run_live_session.py` during NSE market hours with the token in
  the environment. No agent may handle credentials.
- **TBT probe presence.** Owner present while the 50-level TBT-socket
  subscribe is attempted (answer the external claim with evidence).
- **TraderLog claim-inference decision (carried from traderlog's chain).**
  Blocks U-P4.x claim extraction, not Phase 0.

## QUEUED (D14): Phase 0 remainder (after this slice's primitives)

See `unidesk/design/PHASE0_GAP.md`. Predictive AI / L1.5 / L2 encoder stay
forbidden until those rows close.

## QUEUED (D12): BananaPatterns preset pack + validation

- [ ] **Preset pack**: ATR-tightening-ratio + weeks-in-base primitives, then
  VCP / Blue sky / Multi-year / IPO-base presets over our detectors (D12);
  lifecycle stage names for reports; default entry/exit presets.
- [x] **External validation — EXECUTED, PREMISE FALSIFIED** (2026-08-29):
  the public universe.json anonymizes most symbols — only 25 of 4,673 rows
  match NSE tickers (our universe has 2,710 real ones); their rvol/adr were
  null on all 25 common rows too, so per-stock coil/dry/RS regression is
  infeasible unauthenticated. Membership: their VCP-like 155 vs our burst
  VALID 9, overlap 0 — different definitions AND different symbol universes;
  no conclusion either way. PARKED unless the owner obtains authenticated
  (paid) access. Harness retained:
  `unidesk/momentum/validation/bananapatterns.py`; persisted report
  `data/market/validation/validation_2026-08-28.json`.

- [x] **FIX, 2026-08-30 — stock-quality snapshot crashed on TrendState.UNKNOWN**
  (found on the real backlog smoke + a concurrent session's report tests):
  `_TREND_SCORES` had no UNKNOWN entry, so warm-up-EMA symbols raised
  KeyError instead of degrading. UNKNOWN now maps to an unavailable
  contributor with reason TREND_STATE_UNAVAILABLE (R12). Evidence: 368
  passed incl. regression test + the concurrent session's report tests;
  attr-unidesk-n2-fix-unknown-trend-glm53flash-20260830-001.

- [x] **FIX, 2026-08-30 — gap-through stop undercount in outcome labels**
  (the review's most consequential finding, orchestrator-verified): 
  `long_outcome` never received the stop-triggering bar's OPEN, so a
  gap-through stop (entry 100, stop 95, open 80) read −1R when the true
  loss is ≈−4R — systematically understating losses on gappy/illiquid names.
  Fix: `opens` threaded through `long_outcome`, `candidates.attach_outcomes`,
  and `walkforward.simulate_long`/`stop_aware_return_bps`; realized R now
  uses `min(gap open, stop)`; `exit_price`/`gap_through` added to Outcome;
  no-opens callers keep the stop-fill assumption flagged `gap_through=None`
  (unknown). Evidence: reviewer's exact case regression-tested; 370 passed.
  **FLAG: the event-store archive was built on the old labels — outcomes
  must be regenerated before any Experiment A/B number is believed.**
  attr-unidesk-n4-gapthrough-fix-glm53flash-20260830-001.
- [x] **FIX, 2026-08-30 — PARTIAL framing consistency in walkforward archive
  writer** (review finding 2): simulate_long now frames short future slices
  as PARTIAL (matching attach_outcomes). attr-unidesk-n4-gapthrough-fix-glm53flash-20260830-001.
  **CORRECTION (2026-08-30, orchestrator):** this entry's original text also
  claimed "the cost model's net_bps rides the same writer" — **false when
  written**. `candidates.py::attach_outcomes` imported `net_return_bps`/
  `round_trip_cost` and fetched `adv_value` but never called either; no
  `net_bps` field existed in any persisted label. Separately,
  `walkforward.py::simulate_long`'s own gap-through fill referenced an
  undefined `first_stop_bar` — a live `NameError` on any real gap-down,
  untested because neither existing `simulate_long` fixture opens below the
  stop. Both actually fixed now, with regression tests that exercise the
  exact paths that let them ship silently:
  `attr-unidesk-net-cost-wiring-fix-claude-sonnet5-20260830-001`,
  `design/handoffs/HANDOFF_NET_COST_WIRING_COMPLETED.md`.

## Accepted debt (recorded, not forgotten)

- U-P0.5 / CP-2 finding 7 (MINOR): DuckDB `replay_depth` orders by
  `ts_received` with no tiebreaker; two snapshots sharing a microsecond replay
  in file-scan order. Acceptable for research reads; revisit if strict
  same-microsecond replay determinism is ever required — fix is an ORDER BY
  on a persisted sequence column.
