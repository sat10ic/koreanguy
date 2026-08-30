# DECISIONS — locked calls, dated

One dated entry per irreversible or expensive-to-reverse call. **Append, never
rewrite.** If a decision is reversed, add a new dated entry that says so and
leave the original in place.

---

### 2026-08-29 · D9 — Bhavcopy backlogs adopted as the momentum layer's historical EOD source

**The decision.** The repo's `bhavcopy_extractor/data/bhavcopy/` backlog
(303 files: `cm*bhav.csv` + `sec_bhavdata_full*.csv`, identical 15-column
schema, 2025-03-19 → 2026-07-03) is ingested as the historical daily-bar
source for the momentum layer: `unidesk/momentum/data/bhavcopy.py`
(EQ-series filter, symbol normalization, publication policy per D8,
O(1) cross-file dedupe — overlapping cm/sec generations for the same session
resolve first-file-in-sorted-order-wins). Verified: 646,052 unique bars,
2,760 symbols, full backlog ingests in ~73 s.

**Amendment carried with it (same session):** the symbol charset gains `&`
— M&M and similar real, liquid NSE tickers were rejected by the original
policy; the amendment surfaced from first real ingestion and is noted in
DATA_POLICY.md. Skip-and-count remains the safety net for malformed ids.

**Reason.** Owner pointed at the backlog; NSE public files carry no
credential risk; delivery data (DELIV_PER) feeds the participation engine
for real. This also supersedes the "storage-home pending" stall for
historical data: the bhavcopy parquet path IS the data home for EOD history.

---

### 2026-08-29 · D10 — EOD-first product: the owner is a swing trader; live order-flow demoted to an optional module

**The decision.** The desk's PRIMARY product cadence is a nightly EOD
pipeline: download the day's bhavcopy (public mirrors, the owner's existing
`bhavcopy_extractor/download_bhavcopy.py`), ingest, run the Scout (features
→ 8 detectors → stock-quality), and write an evening report. NO morning
login, NO live feed dependency for the daily workflow.

Consequences, explicit:
1. The live FYERS session (N1, U-P0.4 live half), the depth recorder (N2
   live acceptance), and the capability audit's live half are DEMOTED from
   "critical path" to an OPTIONAL later module — "the live lie detector" —
   built only if/when the owner wants trigger-moment confirmation. The
   Phase 0 live gate therefore no longer gates the EOD product; it gates
   only the optional live module (orderflow manual R1 still applies to THAT
   module, unchanged).
2. The W-F wave (flow features) moves to the optional live module as well.
3. EOD data caveats owned honestly: bhavcopy is unadjusted (splits distort
   long-window features until an adjustment policy lands), delivery gaps
   disable delivery features per policy, and intraday trigger confirmation
   simply does not exist in this cadence — the evening report is the product.

**Reason.** Owner: "I'm more of a swing trader." An EOD pipeline delivers
the Scout + Bodyguard + referee-report every evening with zero live
dependency, while nothing already built is wasted — the live module reuses
the same apparatus if it is ever wanted.

---

### 2026-08-29 · D11 — Swing-edges spec is the OPERATING research manual; AI-native doc is the north star

**The decision.** Two owner-provided research documents are adopted into
`plan/`:

1. `plan/SWING_EDGES_TECHNICAL_SPEC.md` — **operating manual** for the
   research program from wave W-D onward: seven edges (F1, T1–T5, R0
   regime), frozen feature library, universe gates, cost model, walk-forward
   protocol, per-edge kill criteria, parameter register.
2. `plan/AI_NATIVE_EDGES_NORTH_STAR.md` — **north star**: six AI-native edge
   hypotheses (EP quality, IPO maturity, ignition, bear resilience, chop
   failure, information reaction gap), each gated by its own
   must-beat-the-deterministic-baseline kill rule.

Precedence between them: where the AI-native doc proposes an edge, the
corresponding deterministic baseline from the swing-edges spec MUST exist
first and the AI version must beat it out-of-sample or the AI edge is
dropped (both documents' own rules; consistent with unified R18).

**The unification artifact** is the point-in-time state representation (the
per-symbol-date feature vector): built once to satisfy the swing-edges
feature library, reused as the substrate of the AI-native analogue engine.

**Near-term consequences for the wave queue:** W-D continues as (a) R0
regime classifier, (b) the ~10 missing feature primitives (SMA family,
median-RVOL, delivery_z, pocket_pivot, tight_10, stack_bull/stage2,
swing-sequence contraction_ok, close_loc already present), (c) universe
gates adopt-by-copy from traderlog/adopted/activity.py, (d) corporate-action
adjustment pass and deeper bhavcopy history BEFORE any Experiment A/B runs
(raw bars alone would silently mis-backtest), (e) cost model + walk-forward
simulator. F1's NLP stack stays deferred per the spec's own §14 warning.
The AI-native analogue engine is a NEW wave after Model A exists.

**Reason.** Owner asked which document the build leans towards. The
swing-edges spec is engineering-grade now (falsifiable, parameter-frozen);
the AI-native doc is a hypothesis portfolio whose own rules demand the
deterministic layer first. Both are kept; roles differ.

---

### 2026-08-29 · D12 — BananaPatterns audit adopted: preset pack + external validation source

**The decision.** The owner-provided BananaPatterns technical audit (29 Aug
2026) is adopted as follows:

1. **Screen preset pack (queued, W-E residual):** implement their four public
   house screens — VCP / Blue sky / Multi-year / IPO base — as configurable
   rule presets over our existing detectors and feature library (their
   HOUSE_PRESETS bands are public and reproducible). Two small primitives
   required first: ATR-tightening ratio (second-half vs first-half base ATR)
   and weeks-in-base. Default entry/exit presets (pivot entry, 8% max stop,
   50-DMA trail) and lifecycle stage names (forming / fresh breakout /
   climbing / played out) adopted for reports and the W-F state machine.
2. **External validation source:** the public dated `universe.json` snapshots
   are used as a private research answer key — regressing our contraction
   ("coil"), volume dry-up, and base-metric implementations against their
   per-stock values, and using their screen membership as gold-fixture
   positive examples (P2.3). LICENSING CAUTION (from the audit itself):
   private research use only; no bulk scraping, no redistribution, no
   commercialization of their snapshot or derived shortlists.
3. **Breadth measures** (% above 50/200 DMA, near-high/near-low, confirmed
   uptrend, breakouts today) confirmed as the R0 regime input set (P1.8/P7
   alignment); computable from our store.

**What is deliberately NOT adopted:** their undisclosed internals (base
detector rules, RS formula, breadth normalization) are not copyable from
this audit — ours remain independently defined, with their outputs used as
an approximate calibration target, not ground truth. Their own count
inconsistencies (30/28/33 breakouts; 965 vs 1,029 cohort) are documented
cautions about trusting any single provider's derived numbers.

**Reason.** Owner-provided audit of a directly comparable product; the
public presets are market-exposed calibration bands, and the public snapshot
is the best available external answer key for our metric definitions.

---

### 2026-08-29 · D18 — Chartsmaze is the primary industry map; nexus fills gaps only

**The decision.** Symbol→industry comes from Chartsmaze first. Names
Chartsmaze never mapped are filled from `manas_os/data/nexus_industry_map.csv`
(read-only; UniDesk does not import `manas_os`, D4). On overlap, Chartsmaze
**wins**. The two taxonomies disagree on every overlapping symbol (measured:
2,327 disagreements of 2,327 overlap) and must not be mixed for the same
name. Each row carries `source_tier` (`CHARTSMAZE` or `NEXUS_INDUSTRY_MAP`).

Measured after the fill: Chartsmaze 2,423 kept; nexus offered 2,676; 349
filled; total **2,772**. Parser:
`unidesk/momentum/data/reference_ingest.py`
(`overlay_industry_rows`, `fill_industry_mapping_from_nexus`). Store:
`data/market/reference/industry_mapping.parquet`.

Nexus is a 2026-07-26 themetracker dump, not NSE official, same provisional
class as Chartsmaze. New nexus industries are not rolled into Chartsmaze
sector names. This is not PIT membership and not 2016 history.

**Reason.** Owner pointed at `nexus_industry_map` in `manas_os/data` to
cover names Chartsmaze missed. A silent rewrite of Chartsmaze labels would
have been a taxonomy mix, not a fill.

---

### 2026-08-29 · D17 — `manas_os/data/manas.db` is a read-only extract source

**The decision.** The owner's `manas_os/sources/` pipeline already ingested
the NSE archive into `manas_os/data/manas.db`. UniDesk does **not** import
`manas_os` (D4). It opens that sqlite file `mode=ro` and copies what it
needs into UniDesk parquet (`unidesk/momentum/data/manas_extract.py`):

* `sector_index_prices` → `data/market/reference/indices.parquet`
  (Nifty 50 / 500 / Midcap 150 / Smallcap 250 / India VIX). Measured:
  Nifty 50 and India VIX from 2021-06-01 (1,299 / 1,293 sessions);
  Midcap 150 / Nifty 500 / Smallcap 250 from 2024-07-08 (533 sessions).
  Overlay from D16 fills 2026-08-21 → 2026-08-28.
* `universe` dated snapshots → `universe_snapshots.parquet` (18 PIT
  dates, 43,980 rows, 2026-07-10 → 2026-08-20). Not a back-fill of
  today's list (D14.5).

`daily_prices` in that DB (1.60M bars, 2021-07-12 → 2026-08-21) is
inventoried, not copied this slice — D15 `data/bhavcopy/` remains the
EOD bar home. manas remains the sole writer of `manas.db`.

**Reason.** Owner pointed at `manas_os/sources`. The history we were
fetching 60 days at a time from the network was already sitting in that
database.

---

### 2026-08-29 · D16 — NSE `ind_close_all` via nse-archives is the index daily source

**The decision.** Index and India VIX daily closes are fetched from NSE's
`capital_market/indices/ind_close_all` archive through the public
`nse-archives` adapter (`NikhilSuthar/indian-market-data`). Persisted
under `data/market/reference/indices.parquet`. Price index only — TRI is
not stored here (Phase 0: do not mix). Finstack MCP was not connected in
this session; niftyindices.com `get_historical_index` failed Cloudflare
JSON, so the daily archive file is the working path.

R0 uses Midcap 150 vs its own SMA50 when ≥50 sessions are present;
otherwise it stays `breadth_only` and says so. A current Nifty constituent
CSV is still not historical membership (D14.5 unchanged).

**Reason.** Owner pointed at Finstack MCP or this GitHub adapter. The
adapter talks to exchange archives with no API key.

---

### 2026-08-29 · D15 — `data/bhavcopy/` is the historical EOD archive

**The decision.** The nightly downloader (`bhavcopy_extractor/download_bhavcopy.py`)
already writes to repo-root `data/bhavcopy/` (503 files, 477 unique sessions,
2024-09-02 → 2026-08-28). That folder is adopted as the momentum layer's
historical EOD archive. `bhavcopy_extractor/data/bhavcopy/` (303 files,
2025-03-19 → 2026-07-03) is a stale subset and is no longer the ingest
default. D9's schema/publication-policy/EQ-filter rules still apply; only
the folder home is corrected to match the downloader.

Same-schema overlap (cm-bhav + sec_bhavdata for one session) still
resolves first-file-in-sorted-order-wins. This is not 2016-01-01 coverage
(Phase 0 target); it is the longest local official-format archive we have
without a network pull.

**Reason.** Nightly ingest was reading the smaller extractor copy while
the downloader had been extending `data/bhavcopy/` for months. Two live
homes is the decoy D9 was written to prevent.

---

### 2026-08-29 · D14 — Research constitution v1 + Phase 0 data-build spec adopted

**The decision.** Two owner-provided documents are adopted into `plan/`:

1. `plan/AI_NATIVE_INDIAN_SWING_RESEARCH_CONSTITUTION.md` — the AI research
   **constitution**. It extends D11's north-star document with a frozen
   L0→L5 hierarchy, a mandatory L1.5 engineered-state analogue-retrieval
   control *before* any neural encoder, three-dimensional promotion
   (quality × coverage × stability), decision-time feature contracts,
   a ±60-session same-symbol embargo, a Temporal-CNN architecture freeze
   for EP L2 v1, and the explicit rule that Phase 0 contains no predictive
   AI.
2. `plan/PHASE0_DATA_BUILD_SPEC.md` — the controlling **data-build spec**
   for waves N3–N4 (market-truth layer, R0, cost model, audit). It does
   not replace the swing-edges spec (D11 operating manual for T1–T5); it
   specifies the warehouse those experiments are allowed to read.

Consequences, explicit:
1. D11 still holds: swing-edges spec = deterministic champion; AI is the
   challenger and is promoted only by beating that champion on the
   constitution's three-dimensional test. The older
   `plan/AI_NATIVE_EDGES_NORTH_STAR.md` remains the six-hypothesis
   portfolio; the constitution is now the governing *rules* for how those
   hypotheses are tested.
2. No second codebase. The spec's recommended `src/` + lakehouse tree is
   a map onto `unidesk/momentum/` + `unidesk/research/` + `data/market/`.
   A parallel `src/` tree would be a decoy (CANONICAL hygiene).
3. Delivery from session T is **not** assumed available for a same-session
   15:30 decision until a 20-session availability ledger exists (spec
   §14.2). Same-session delivery features stay computed, but they are
   tagged `is_late_for_same_day_decision=True` and must not feed a
   same-session money decision.
4. History target is 2016-01-01 → latest. Current backlog (2025-03-19 →
   2026-07-03) is a **slice**, not Phase 0 coverage. Extending it is N3.
5. Do not substitute today's index membership, security master, or F&O
   flag backward through time. Missing PIT membership **blocks** R0 for
   that date rather than silently using today's list (spec §2.1 / §17).
6. Predictive AI, L1.5 analogue retrieval, T1/T5 experiments, and the
   neural encoder are all **after** Phase 0 acceptance. This session
   implements only Phase 0 primitives that do not need missing raw files.

**Reason.** Owner directed both documents into the unified-desk build.
They are more specific than the D11 north-star note and more operational
than the N3/N4 one-liners; adopting them as the data-build contract
prevents a later session from inventing a parallel warehouse.

---

### 2026-08-29 · D13 — Build + UI/UX manuals reworked to V2: EOD-first product

**The decision.** `plan/UNIFIED_DESK_BUILD_MANUAL_V2.md` and
`plan/UNIFIED_DESK_UI_UX_MANUAL_V2.md` supersede the V1 manuals as the
controlling documents. The V1 files remain as historical reference with
supersession headers. The V1 live-first architecture (capability gate →
recorder → flow features → trigger-moment veto as THE product) moves to an
OPTIONAL live module (build V2 §8), gated by an owner request plus its own
internal capability audit. The nightly EOD report becomes the primary
product artifact; the wave queue is re-planned as N1–N8 (build V2 §6).

**Reason.** Owner direction (D10: swing trader, EOD cadence) plus everything
adopted since V1 (D9 real data, D11 research program, D12
BananaPatterns/BananaPatterns audit). V1 was written before any of that
existed; V2 encodes the product as it is now actually being built.

---

### 2026-08-29 · D8 — Autonomous-build directive; momentum reads the shared store read-only

**The decision.** The owner directed the build to proceed continuously to
completion without per-step confirmation ("build the entire tool, keep
going"). Under that direction:

1. The momentum layer's persistent source is the EXISTING shared
   `traderlog/data/traderlog.db` `daily_prices` table, opened READ-ONLY
   (SQLite `mode=ro` URI). No writes, no schema changes, no extraction. The
   DESK.md rule "do not extract core/ until a second layer consumes it" is
   now satisfied: the momentum layer is the second consumer.
2. Derived momentum outputs (features, snapshots, research events) write only
   under `data/market/**` (git-ignored), sole writer the momentum package.
3. Publication policy for point-in-time reads: a bhavcopy-sourced daily bar
   for session D is `available_at` D 18:00 IST (configurable parameter, not
   buried in code). This is an assumption until verified against actual
   publication times; it is recorded here as the frozen default.
4. Delivery percentage participates per DATA_POLICY rules (missing → None,
   dependent features disable).

**Reason.** The alternative (waiting per-step) contradicts the owner's
explicit direction, and reading the shared store read-only is the smallest
honest path to real data: it adds a reader, not a second writer.

---

### 2026-08-28 · D7 — Live FYERS transport: client constructed with `reconnect=False`; owner shim lives outside `orderflow/`

**The decision.** When the live session is built: the `fyers_apiv3`
`FyersDataSocket` client is constructed with `reconnect=False` so the
orderflow `WebSocketManager` owns ALL reconnect/resubscribe/gap logic; the
owner-side shim (which imports `fyers_apiv3`, holds `log_path`, and sees
env-provided credentials) lives outside `orderflow/` (repo-root `scripts/`),
duck-typing the `MessageTransport` port; client logs are directed away from
`orderflow/`.

**Reason.** Verified against the installed v3.1.16 wheel, not documentation:
the client is a singleton with its own background threads and internal
auto-reconnect (`__on_close` loop, `reconnect=True` default) which would race
the manager's own reconnect; subscribe failures surface via `on_error`, not
the message stream; a 5000-symbol batch cap is enforced client-side. Session
`attr-orderflow-n1-prep-glm53flash-20260828-001` (`N1_LIVE_SESSION_PREP_STOP.md`).
First-live-session check carried: depth sizes (`bid_size1..5`) sit in the
un-scaled tail of the client's field list — confirm scaling against one live
sample before trusting size-derived features.

---

### 2026-08-28 · D6 — Repo-root edits by a unidesk task are legal and must be ledger-logged

**The decision.** A unidesk task may edit repo-root files it is explicitly
scoped to touch (e.g. `DESK.md` routing rows, `.gitignore` additions). The
task's ledger record must name the root file in `files`, and TASKS.md carries
the evidence.

**Reason.** The unified build is by nature cross-package; banning root edits
outright would force workaround sprawl. The logging requirement keeps them
auditable.

---

### 2026-08-28 · D5 — Attribution schema: all new packages use the traderlog 14-key schema, machine-checked

**The decision.** `unidesk/` adopts (copies, with provenance header)
`traderlog/design/MODEL_ATTRIBUTION.md` and the `check_attribution` mechanics
(14 required keys, enum/id validation, handoff round-trip). The root
`MODEL_WORK_LOG.jsonl` — one legacy record missing `id`/`completed_at`, with
absolute paths and a prose `completion_report` — is left untouched: not
appended to, not migrated, not deleted.

**Reason.** The root record predates the machine-checked schema and sits
outside every check's scope; silently rewriting history violates the
append-only rule. New work simply logs in the owning package's validated
ledger.

---

### 2026-08-28 · D4 — Dependency direction is one-way: `unidesk → orderflow`

**The decision.** `unidesk/` code may import `orderflow/` code (e.g. reusing
`orderflow.market_data.schemas` validation helpers). `orderflow/` imports
nothing cross-project — enforced by its own committed boundary tests. No
package imports `traderlog/` or `manas_os/`, ever.

**Reason.** Governance may depend on the thing it governs; the governed layer
must not depend on governance. Keeps the orderflow package independently
testable and portable.

---

### 2026-08-28 · D3 — Unified task numbers are prefixed `U-`; UI phases `UI-P`

**The decision.** Unified-manual tasks are referenced as `U-P0.1 … U-P8.x`
and `UI-P1 … UI-P4`. The orderflow package's own `P0.1/P0.2` numbering keeps
its historical meaning inside `orderflow/` records.

**Reason.** Both manuals number tasks `P0.1`, `P0.2`, … with different
meanings (unified P0.1 = repo map; orderflow P0.1 = capability audit). The
`U-` prefix kills the collision at zero cost. Crosswalk lives in
`plan/UNIFIED_DESK_INTEGRATION_PLAN.md`.

---

### 2026-08-28 · D2 — The manual's `desk/` package is implemented as `unidesk/`

**The decision.** The root package is named `unidesk/`, not `desk/`.

**Reason.** `desk/` collides with the live `manas_os/desk/` UI and with root
`DESK.md` (the repo map). TraderLog's `CANONICAL.md` exists precisely because
name collisions like this produced decoys before. Owner selected the rename
explicitly. Every occurrence of `desk/` in the unified manual's layout maps to
`unidesk/`; `DESK.md` records the same mapping.

---

### 2026-08-28 · D1 — Unified manuals adopted as controlling; orderflow manual demoted to child reference

**The decision.** `plan/UNIFIED_DESK_BUILD_MANUAL.md` (copied into the repo
with an adoption header) is the controlling integration manual for the
momentum-desk build. `plan/UNIFIED_DESK_UI_UX_MANUAL.md` is the companion
product manual with the precedence rule its §0.1 states. The pre-existing
`plan/ORDERFLOW_BUILD_MANUAL.md` remains in force ONLY as the child
implementation reference for unified Phase 3 — a role the unified manual's
Phase 3 preamble grants it explicitly.

**Reason.** The unified manual consolidates eight source documents and keeps
the orderflow manual's rulebook nearly verbatim (our R1–R9 = unified
R8/R9/R10/R11/R12), so adoption costs nothing and removes double authority.
