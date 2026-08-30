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
- [ ] **U-P0.3 — Point-in-time market store**
  `get_market_state(symbol, as_of)` over stored OHLCV/delivery/circuit data;
  future-row invisibility fixtures. Depends on U-P0.2 (done) and a decision
  on the storage home (likely `data/market/`, writer TBD in CANONICAL when
  built).

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
  inventoried, not adopted — D-decision); official CA-with-ratios; remaining
  194 detector candidates unconfirmed; PIT membership before Jul 2026;
  ISIN/continuity_id; MTO; official bands; F&O PIT; `make rebuild` hashes.
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
  **STILL OPEN:** 4y/1y folds (calendar too short until 2016 history);
  attaching outcomes across the real 1M-bar archive — the guards that
  gated it now exist, are tested, and are fed correct dates, but wiring
  `unconfirmed_ca_sessions=unconfirmed_candidate_sessions(...)` and a real
  CA-basis-aware future map into an actual archive-wide run is still open
  (HANDOFF.md directive 1f) — **and an Opus checkpoint found a second,
  still-unfixed trap for this run**: if the future-outcome map doesn't
  itself carry a matching `adjusted`/`ca_table_hash` basis, every
  genuinely-adjusted symbol lands `UNRESOLVED` across the whole archive,
  silently green. Fix that before running (f), not after; constitution
  guards (`assert_feature_not_after_decision`, `same_symbol_embargo`,
  `same_event_collision`) STILL have zero production call sites, only test
  callers — proving feature-side prefix-invariance (directive 1a) is a
  different, also-necessary property, not production wiring of these three;
  ablation ladder P7.4 (directive 1g).
- [ ] **N5 — Experiments A & B** (T1 vs raw breakout; T5 Path B vs
  gap-and-go) — pre-registered kill criteria, net-of-cost.
  **NO-GO as of 2026-08-30**: CA-series gate unmet (4/198 confirmed); CP-3
  owner-invoked leakage audit (GOAL.md: "highest-risk gate in the build")
  has not run. See HANDOFF.md directive 3 for the three lift conditions.
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
  **STILL OPEN:** Step 2, wiring Tonight/Candidates screens in
  `unidesk_terminal/` to read it (zero frontend files touched so far);
  `UI_BACKEND_INTEGRATION_PLAN.md` needs the `contracts.*.to_dict()`
  correction folded in; Stock waits on U-P0.3; History waits on the N4
  adjustment-basis guard AND the archive-attach future-map basis fix above;
  Research waits on N5 being lifted.

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

## Accepted debt (recorded, not forgotten)

- U-P0.5 / CP-2 finding 7 (MINOR): DuckDB `replay_depth` orders by
  `ts_received` with no tiebreaker; two snapshots sharing a microsecond replay
  in file-scan order. Acceptable for research reads; revisit if strict
  same-microsecond replay determinism is ever required — fix is an ORDER BY
  on a persisted sequence column.
