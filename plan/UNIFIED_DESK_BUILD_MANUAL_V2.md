# Unified Momentum Desk — Build Manual V2

**Status:** controlling **design and build spec** — supersedes `UNIFIED_DESK_BUILD_MANUAL.md` (V1, retained as historical reference)
**Adopted:** 2026-08-29 (unidesk DECISIONS D13)
**As-built refresh:** 2026-08-29 (D14–D18). This file is the contract *and* the current map of the tool. Running status still lives in `unidesk/TASKS.md`; Phase 0 gaps in `unidesk/design/PHASE0_GAP.md`.
**Market:** NSE cash equities · **Style:** swing / momentum, 3–20 session horizon · **Cadence:** EOD nightly · **Execution model:** human-in-the-loop, no order routing
**Package:** `unidesk/` (Python). Sibling `unidesk_terminal/` is a fixture UI prototype, not N8.
**Research program:** `plan/SWING_EDGES_TECHNICAL_SPEC.md` (operating / deterministic champion) · `plan/AI_NATIVE_INDIAN_SWING_RESEARCH_CONSTITUTION.md` (AI constitution, D14) · `plan/PHASE0_DATA_BUILD_SPEC.md` (data-build spec for N3–N4) · `plan/AI_NATIVE_EDGES_NORTH_STAR.md` (six-hypothesis portfolio)
**Companion UI spec:** `plan/UNIFIED_DESK_UI_UX_MANUAL_V2.md`
**Task crosswalk:** `plan/UNIFIED_DESK_INTEGRATION_PLAN.md`

---

## 0. What changed since V1, and why this rewrite exists

V1 assumed a live-FYERS-first product: measure the feed, record depth, build
order-flow confirmation, and gate everything on that measurement. The owner
then clarified the actual product (D10): **he is a swing trader**. The EOD
nightly cadence is the product; the live feed is an optional later module.

Adopted since V1, now first-class in this rewrite:

* **D9/D10 — real data + EOD-first.** Nightly download + ingest, no login
  for the daily workflow. Live FYERS is optional (N7).
* **D11 — the research program.** Swing-edges spec = deterministic champion;
  AI-native edges = north star, per-edge gated.
* **D12 — BananaPatterns audit.** Preset pack + external validation answer
  key (licensing-cautious). Not yet fetched.
* **D13 — this V2 manual** supersedes V1.

---

## 0.1 As-built since V2 adoption (D14–D18) — do not re-plan

These landed the same day V2 was adopted. They change the data map, not the
product:

| Decision | What it locked |
|---|---|
| **D14** | AI constitution + Phase 0 data-build spec adopted. Predictive AI forbidden until Phase 0 acceptance. L1.5 analogue retrieval is mandatory *before* any neural encoder. Delivery from session T is not usable for a same-session 15:30 decision until a 20-session availability ledger exists. Parallel `src/` lakehouse tree is a **map**, not a second codebase. |
| **D14.5** | Do not back-fill today's Nifty / Midcap / Smallcap membership as if it were historical. Dated snapshots only. |
| **D15** | EOD archive home is `data/bhavcopy/` (the downloader's target): **1,004,896 bars**, 477 sessions, 2024-09-02 → 2026-08-28. The extractor folder is a stale subset. |
| **D16** | NSE `ind_close_all` via `nse-archives` (NikhilSuthar/indian-market-data) is the network adapter for index daily closes. Price index only — no TRI. Finstack MCP was not connected. niftyindices.com historical API failed Cloudflare JSON. |
| **D17** | `manas_os/data/manas.db` is a **read-only extract** source. UniDesk does not import `manas_os` (D4). Index history and dated universe snapshots are copied into UniDesk parquet. manas remains the sole writer of that DB. |
| **D18** | Chartsmaze is the **primary** symbol→industry table. `manas_os/data/nexus_industry_map.csv` fills names Chartsmaze never mapped (RO; no import). On overlap Chartsmaze wins — the taxonomies disagree and must not be mixed. `source_tier` records origin. |

**Built inventory (do not re-plan):**

* Governance + machine-checked attribution; 12 shared contracts.
* Momentum feature library (trend, RS, participation, ADR/ATR, AVWAP, circuit) + spec-library primitives (sma, median-RVOL, delivery_z, pocket_pivot, tight_ratio, stack_bull, stage2).
* Universe tradeability gates (adopted by copy from activity.py).
* R0 classifier: hysteresis 3d; Midcap 150 vs SMA50 when 50 sessions exist (`breadth_and_midcap150_sma50`); otherwise `breadth_only`.
* 8 setup detectors via a shared rule engine; each separately disableable; P2.3 gold fixtures (32 real cases).
* Clean-room `base_pattern` detector (public BananaPatterns metrics, YASHHV-calibrated). Not in the nightly registry. Not vendor-logic parity.
* Geometry + entry-quality composites; outcome labels (MFE/MAE/R-multiples/stop-hit/breakout hold).
* Nightly CLI: download → ingest → scan → TONIGHT report.
* Chartsmaze event tables: IPO listings, circuit revisions (PIT), announcement review queue (`auto_adjustable=False`), vendor breadth.
* Split detector + close-to-close confirmation on real 2:1 names.
* Confirmed CA table (4 names) applied as a **derived scan view**; raw bhavcopy is never rewritten. Official NSE CA-with-ratios still open.
* Cost model (spec §1.4 conservative cash); trading calendar from observed sessions; decision-time + ±60-session embargo; OHLC/delivery invariants.
* N4 spine: `ResearchEvent` freeze (includes INVALID), parquet `date=` event store, outcome attach from post-decision bars, expanding walk-forward + 5-session embargo, next-bar fills, planted-bug leakage suite (`run_checks` leakage smoke live).
* Index parquet: Nifty 50 + India VIX from **2021-06-01** (1,299 / 1,293 sessions); Midcap 150 / Nifty 500 / Smallcap 250 from **2024-07-08** (533 sessions); overlay through 2026-08-28. SMA200 is computable on Nifty 50.
* Dated universe snapshots: 18 PIT dates, 43,980 rows (2026-07-10 → 2026-08-20).
* Industry map: **2,772** names — Chartsmaze 2,423 kept + nexus fill 349 (D18). Chartsmaze wins on 2,327 overlap. Store `industry_mapping.parquet` with `source_tier`.
* Optional live apparatus (orderflow package) — N7, not on the EOD path.
* Parallel UI prototype `unidesk_terminal/` on fixtures — does **not** fulfill N8/W-H.

---

## 1. The product

A nightly desk that, every trading evening, answers:

```
1. Which stocks are strong?                    (momentum context)
2. Which ones have a valid setup tonight?      (8 detectors + presets)
3. Is the entry worth it?                      (geometry + entry quality)
4. Can we trade the size we need, and exit?    (liquidity + circuit gates)
5. What is the market regime backing this?     (R0 classifier)
6. What happened to yesterday's candidates?    (outcome labels, honesty)
7. What is unknown or missing in the data?     (named reasons, never zeros)
        → the human reads the report and decides
```

The primary artifact is **the Nightly Report** — a plain, honest document
(markdown now, screen later) listing candidates with every number named,
every gap admitted, and every decision traceable.

The **optional live module** (order-flow confirmation at the trigger; the
orderflow package + FYERS feed) exists outside this cadence. It is built
only if the owner later wants trigger-moment confirmation, and its own gate
(its capability audit, R1/R8) applies then. Nothing in phases N1–N5 depends
on it.

---

## 2. Non-negotiable rules (carried and renumbered)

| Rule | Statement |
|---|---|
| R-A | **Point-in-time truth.** A query at time T sees only data published by T. Every feature family gets a leakage test. |
| R-B | **Code owns numbers.** LLMs may summarize; they never author prices, triggers, scores, or sizes. |
| R-C | **Human owns the trade.** No order routing anywhere, ever. ELIGIBLE/WAIT/WARN/VETO/UNKNOWN are advisory states. |
| R-D | **Stock / setup / entry quality stay separate.** Never one opaque score. |
| R-E | **Missing is missing.** Absent data is null + named reason; stale state is UNKNOWN with a timestamp; zero is a measurement, not a placeholder. |
| R-F | **Config, not code.** Thresholds live in versioned config; weights are caller-supplied; each feature individually disableable. Detectors are separately disableable. |
| R-G | **Replay equals live.** Research calls the same functions production does. |
| R-H | **Kill criteria are commitments.** Each edge names its own death condition before testing. Negative results are published (research/NEGATIVE_FINDINGS.md) and features disabled. |
| R-I | **Sample-size honesty.** No claim from a tiny cell; always show n, coverage, missing rate. |
| R-J | **Costs before romance.** Every backtest reports gross AND net under the cost model; net is the only number that can accept a strategy. |
| R-K | **Capacity before romance.** A pattern that only works below ₹3 crore ADV is not an edge. |
| R-L | **One writer per store.** Integration via contracts, never cross-package writes. UniDesk does not import `manas_os` or `traderlog` (D4); adopt by copy or read-only extract. |
| R-M | **Credentials never enter the repo.** NSE bhavcopy and public archives need none; FYERS remains owner-only. |
| R-N | **India microstructure is signal, not footnote.** Circuits, delivery, pre-open, auctions are first-class fields. |
| R-O | **Delivery lag (D14).** Until a 20-session first-seen ledger exists, delivery printed for session T is usable only for a decision on T+1 or later. |
| R-P | **No predictive AI until Phase 0 acceptance (D14).** L1.5 engineered-state analogue retrieval is a mandatory control before any neural encoder. |
| R-Q | **Price index ≠ TRI.** Index series used for R0 are price closes. Do not mix TRI into the same SMA. |
| R-R | **Industry overlay (D18).** Chartsmaze is primary. Nexus fills unmapped names only. On overlap Chartsmaze wins; do not mix the two taxonomies for the same symbol. `source_tier` is mandatory on persisted rows. |

---

## 3. Data foundation (as-built)

| Source | Contents | Status |
|---|---|---|
| NSE bhavcopy `data/bhavcopy/` (D15; nightly downloader target) | OHLC, volume, turnover, delivery %, trades — **1,004,896 bars**, 477 sessions, 2024-09-02 → 2026-08-28 | ✅ ingest default, PIT `available_at` = session 18:00 IST |
| `manas_os/data/manas.db` read-only extract (D17) | Index history (Nifty 50 + VIX from 2021-06-01; Midcap 150 / 500 / Smallcap 250 from 2024-07-08); 18 dated universe snapshots | ✅ copied into UniDesk parquet; manas is sole writer of the DB |
| `manas_os/data/nexus_industry_map.csv` read-only (D18; not an import) | 2,676 themetracker industry labels (captured 2026-07-26) | ✅ **349** names Chartsmaze lacked, appended only. Chartsmaze wins on the 2,327 overlap. `source_tier=NEXUS_INDUSTRY_MAP`. Total map **2,772** |
| `manas_os/sources/` | Existing NSE ingest code (`nse_indices.py`, `bhavcopy.py`, disclosures, FII/DII, …) | reference only — **do not import**; adopt-by-copy or extract |
| NSE `ind_close_all` via nse-archives (D16) | Network fill for index days manas has not ingested yet (e.g. 2026-08-21 → 08-28) | ✅ overlay on the parquet |
| Chartsmaze dumps | sector/industry mapping, results calendar, IPO listings, circuit revisions, 10,972 announcements (review queue, no ratios), vendor breadth | ✅ parsed; `source_tier=SECONDARY_REPAIR`. Industry map: **2,423** Chartsmaze names |
| BananaPatterns public `universe.json` | coil / dry-up / screen membership | **queued** (D12, licensing-cautious) |
| Corporate actions with ratios | official NSE CA feed | **partial** — seed table of 4 close-to-close 2:1 names (`unidesk/config/confirmed_actions.csv`) applied as a derived scan view. Announcements still have no ratios; auto-adjust stays off; official feed still open |
| PIT index membership 2016– | official reconstitution files | **partial** — 18 dated universe snapshots only (Jul–Aug 2026). Do not back-fill today's Nifty list (D14.5). |
| F&O eligibility PIT, MTO delivery files, official price-band files | | **OPEN** |
| manas `daily_prices` (1.60M bars, 2021-07-12 → 2026-08-21) | longer EOD history than D15 bhavcopy | **inventoried, not copied** — D15 remains the bar home |

**Known data caveats, owned:** D15 bhavcopy raw prints stay unadjusted (four confirmed 2:1 names are applied as a derived scan view only); DELIV_PER blanks disable delivery features; same-session delivery cannot feed a 15:30 decision (R-O); EQ series only; index parquet is price not TRI; universe snapshots are 18 dates, not a 2016 membership history; industry labels are vendor (Chartsmaze + nexus themetracker), not NSE official, and the two taxonomies must not be mixed (R-R).

**Index parquet measured at D17 (do not re-harvest as if empty):**

| Series | Sessions | First → last | Notes |
|---|---:|---|---|
| Nifty 50 | 1,299 | 2021-06-01 → 2026-08-28 | SMA200 computable; last print below SMA50 and SMA200 |
| India VIX | 1,293 | 2021-06-01 → 2026-08-28 | last 10.68; 1y z-score not yet in the R0 label rule |
| Midcap 150 | 533 | 2024-07-08 → 2026-08-28 | last 23507.15, above SMA50 and SMA200 |
| Nifty 500 | 533 | 2024-07-08 → 2026-08-28 | |
| Smallcap 250 | 533 | 2024-07-08 → 2026-08-28 | |

D16 overlay filled 2026-08-21 → 08-28. One fetch fail: 2026-06-26.

---

## 4. Architecture (nightly)

```
download (public mirrors → data/bhavcopy/)
        → ingest (bhavcopy + Chartsmaze events + index parquet)
        → point-in-time store
        → feature jobs (confirmed CA derived view → universe gates → momentum features → regime R0)
        → detectors (8, disableable) + (presets still queued)
        → stock quality · entry quality · outcome labels for yesterday
        → freeze candidates (VALID and INVALID) for research
        → NIGHTLY REPORT
```

Index / VIX / dated universe snapshots are extracted from `manas.db` (RO)
and overlaid with `ind_close_all` fetches. They are not recomputed from
bhavcopy.

Industry mapping is a reference table, not rebuilt from bhavcopy:
Chartsmaze primary, nexus CSV fill for unmapped names (D18). The fill is
`fill_industry_mapping_from_nexus` — it is not yet a nightly CLI step. It
refuses to run if the Chartsmaze parquet is missing (fill, not replacement).

The optional live module (orderflow package) hangs off this same store and
is described in §8.

Implementation home: `unidesk/momentum/` (EOD path) and `unidesk/research/`
(labels, costs, leakage, freeze, walk-forward). There is no parallel `src/`
tree.

---

## 5. The seven research edges (adopted from the swing-edges spec)

| ID | Edge | As-built |
|---|---|---|
| R0 | Regime classifier (BULL/BEAR/CHOP, hysteresis) | ✅ built. Midcap 150 vs SMA50 when 50 sessions exist; SMA200 computable on Nifty 50 (1,299 sessions). VIX series stored (1,293 sessions); 1y z-score not yet in the label rule. |
| T1 | Tightness-scored continuation in RS leaders | momentum_burst + stock-quality; S_tight composite + VCP preset still to add |
| T2 | Failed pivots & undercut-and-rally (bear; shorts F&O-only) | detector family exists; F&O PIT flag open |
| T3 | Range fades & anti-chop isolation | detector family exists; edge-specific rules still to add |
| T4 | IPO first constructive base | ipo_base detector ✅; Chartsmaze listing dates parsed (store-length is no longer the only age proxy) |
| T5 | Episodic Pivot signature + first flag | episodic_pivot detector ✅; signature score still to add |
| F1 | Material filing drift (NLP) | **explicitly deferred** until T1/T5 experiments exist (spec §14) |

AI analogue engine (constitution L1.5 then L2) is after Model A, per-edge
gated, and **forbidden until Phase 0 acceptance**.

---

## 6. Waves (re-planned) and as-built status

| Wave | Content | Gate | Status 2026-08-29 |
|---|---|---|---|
| **N1** | Nightly pipeline: download→ingest→features→detectors→report | report on a real session | **[~]** report ran; downloader not live-mirror tested |
| **N2** | Universe gates + missing primitives + R0 | regime + gates fixture-tested | **[x]** complete; R0 later gained the midcap SMA50 gate (D16/D17) |
| **N3** | CA adjustment + extended history + index/sector series | known-split confirmation; index series | **[~]** D15 archive, D16/D17 indices, D18 industry fill (2,772 names), split confirmation, **4 confirmed 2:1 names applied as a derived scan view**. Still open: 2016 bhavcopy, official CA-with-ratios, full PIT membership, MTO/F&O/official bands |
| **N4** | Research spine: candidate store, cost model, walk-forward, leakage suite | replay=live; leakage tests fail on planted bugs | **[~]** freeze + parquet `date=` partitions + outcome attach (next-bar, UNRESOLVED if no future) + expanding folds + planted-bug suite. Still open: 4y/1y folds, attach across the 1M-bar archive, ablation ladder |
| **N5** | Experiments A & B (T1 vs raw breakout; T5 Path B vs gap-and-go) | pre-registered kill criteria, net-of-cost | **[ ]** not started — blocked on N3 CA-applied series for long-window backtests |
| **N6** | Surviving edges; preset pack; AI analogue per-edge if baselines beaten | per-edge | **[ ]** AI still forbidden (R-P) |
| **N7** | OPTIONAL live module | owner request + its own audit | deferred (D10/D13) |
| **N8** | Terminal UI (UI manual V2) | data exists for every panel | **[~]** parallel `unidesk_terminal/` prototype on fixtures; not a fulfillment of this gate |

---

## 7. Validation protocol (adopted wholesale from the swing-edges spec §10)

* Train/validate/holdout splits; holdout looked at once. Year-by-year reporting.
* Every edge vs its named dumb baseline, net of costs. Sector-neutral check (no silent beta).
* Diagnostics: CAR bands, pre-event drift (leakage), ADV-quintile and regime expectancy, cost-as-%-of-gross, MAE-vs-stop, parameter jitter.
* Tune budget: five numeric thresholds per strategy after spec freeze; more = new spec version.
* Two-implementer rule: a candidate rule another coder implements from the document alone.
* Kill criteria per edge, pre-registered. Parked ≠ deleted: findings published, code disabled behind flags.
* Walk-forward: expanding folds with a 5-session embargo are the working scheme. 4y/1y is specified and **refused** until the EOD bar calendar is long enough (D15 is 24 months; manas `daily_prices` back to 2021 is inventoried, not adopted).
* Leakage suite must fail planted bugs (future bars, full-sample normalisation, today's membership, future gold). A clean-path-only suite is not P7.3.

---

## 8. The optional live module (what V1 called "the product")

Retained, built, and gated — but off the critical path:

* Apparatus exists (adapter, manager, capability auditor, launcher, recorder core; live transport shim + validation pending the owner-run smoke session).
* If activated later: its own Phase-0 (measure feed → capability.json → R1 gate → recorder) runs first, exactly as the orderflow manual specifies. Its features (spread/imbalance/persistence/price-response) then serve as trigger-moment CONFIRMATION for swing entries — a veto layer, never a standalone system.
* Nothing in the nightly cadence waits on this module.

---

## 9. What V1 items are dropped or moved

| V1 item | Disposition |
|---|---|
| Live capability audit as THE critical-path gate | moved to optional live module (N7) |
| Continuous depth recording as Phase 0 blocker | moved to N7 |
| W-F flow features before swing edges | moved to N7 |
| Trigger-moment GO/WAIT/VETO as primary product | moved to N7; nightly report is primary |
| Intraday scalping, F&O selling, Nifty prediction, "AI feels bullish" | non-goals (spec §13), now explicit here too |
| Parallel `src/` lakehouse tree from the Phase 0 spec | **map, not a second codebase** (D14). Implementation lives in `unidesk/momentum/` + `unidesk/research/` + `data/market/` |

---

## 10. Definition of done for the whole build

The desk is done when, on any ordinary trading evening:

1. The report generates unattended from public data, with n and coverage on every list.
2. Every candidate names its setup, its numbers, its regime, and its unknowns.
3. Yesterday's candidates carry measured outcomes — wins and losses alike.
4. Every accepted edge has survived its pre-registered kill criteria, net of costs.
5. Any number on screen can be replayed from stored data with the same code.
6. Nothing anywhere can place an order.

Until then, the waves in §6 are the contract, and `unidesk/TASKS.md` is the running truth of where we are.

---

## 11. Package map (as-built)

| Path | Role |
|---|---|
| `unidesk/momentum/` | EOD features, 8 nightly detectors, clean-room `base_pattern`, scan, report, nightly, data adapters |
| `unidesk/research/` | labels, costs, leakage, candidates, walk-forward |
| `unidesk/contracts/` | frozen dataclasses; unknown enums fail closed |
| `unidesk/config/costs.yaml` | frozen cost-model assumptions (`costs-v1-spec-1.4`) |
| `unidesk/config/confirmed_actions.csv` | seed confirmed CA table (4 close-to-close 2:1 names) |
| `data/bhavcopy/` | EOD bar archive (D15) |
| `data/market/reference/` | `indices.parquet`, `universe_snapshots.parquet`, `industry_mapping.parquet` (D18: Chartsmaze + nexus fill) |
| `data/market/reports/` | TONIGHT markdown (`tonight_YYYY-MM-DD.md`) |
| `data/market/research/events/` | N4 parquet event store, partitioned `date=YYYY-MM-DD` |
| `manas_os/sources/` + `manas_os/data/manas.db` | upstream NSE ingest; UniDesk reads the DB RO (D17), never imports the package |
| `plan/` | this manual + constitution + Phase 0 spec + swing-edges spec |
| `unidesk_terminal/` | UI prototype on fixtures; separate wave tracking |
| `orderflow/` | optional live module |

Wave-close ritual: tests green (`orderflow/tests` + `unidesk/tests` via `.venv-orderflow`), `python unidesk/run_checks.py` exit 0, TASKS evidence, ledger record, HANDOFF.

PowerShell: from repo root `koreanguy`, run `& ".\.venv-orderflow\Scripts\python.exe" -m pytest orderflow/tests unidesk/tests -q`. Do not let PowerShell treat `.venv-orderflow` as a Python module.

---

## 12. As-built system design

This section is the design of the tool as it exists. Thresholds live in
callers / config (R-F); the code is the numeric authority (R-B).

### 12.1 Nightly pipeline (code)

Entry: `python -m unidesk.momentum.nightly`

```
--download-days N     public-mirror bhavcopy (default 1; --no-download skips)
--backlog PATH        default data/bhavcopy/ (D15)
--limit-files N       smoke ingest
--reports-dir PATH    default data/market/reports/
```

Steps in `run_nightly`: optional download → `ingest_directory` into
`InMemoryMarketStore` → `scan_universe` → `build_nightly_report` → write
`tonight_<session>.md`. No credentials. No orders.

A real run exists: 2026-07-03, 2,563 symbols, 65.9% above EMA50, 3 burst
candidates (`data/market/reports/tonight_2026-07-03.md`). Persistent store
cache is still open (full re-ingest per run).

The report renderer (`report.py`) still defaults the regime line to
`not built yet (wave N2)` unless the caller passes `regime_note`. R0 exists;
wiring it into the nightly CLI is remaining N1 polish, not a missing classifier.

Nightly loads `unidesk/config/confirmed_actions.csv` and passes it to
`scan_universe(..., actions=...)`. Adjusted OHLC is a derived view; the
in-memory store keeps raw prints.

### 12.2 Point-in-time store

`unidesk/momentum/data/market_store.py` — `InMemoryMarketStore`.

* Daily bars are EOD observations. `available_at` is publication time
  (session 18:00 IST for bhavcopy). A same-session pre-publication query
  must not see them.
* `(symbol, session, data_version)` duplicates fail.
* Missing delivery / circuit / surveillance stay `None`. Zero is never a
  placeholder (`DATA_POLICY.md`).
* Symbol charset includes `&` (M&M). Exchange prefixes are rejected.

Policy: `unidesk/momentum/DATA_POLICY.md`. Persistent adapter is still an
owner decision; the in-memory store is the working research path.

### 12.3 Universe gates

`unidesk/momentum/universe/gates.py` — adopted by copy from
`traderlog/adopted/activity.py` (itself a port of manas `universe_filter`).
No `import traderlog` / `import manas_os`.

Defaults: price ≥ ₹30, avg turnover ≥ ₹2 crore/day over 20 sessions, ETF
keyword heuristic, circuit-lock heuristic, mcap skipped-and-surfaced (never
a silent pass). Spec floors (₹8 crore ADV) are caller policy.

### 12.4 Feature library

Pure functions over chronological series. Warm-up is `None`, never zero.

| Module | What it computes |
|---|---|
| `features/trend.py` | EMA21/50 (SMA-seeded), `TrendState` STRONG_UPTREND / UPTREND / TRANSITION / WEAK / UNKNOWN |
| `features/rs.py` | relative-strength rank |
| `features/participation.py` | RVOL (mean), delivery ratio |
| `features/adr_atr.py` | ADR%, ATR% |
| `features/avwap.py` | anchored VWAP + extension in ADR |
| `features/circuit.py` | circuit-risk state (hard gate, not a score) |
| `features/geometry.py` | trigger / invalidation / room |
| `features/spec_library.py` | swing-edges frozen defs: `sma`, `rvol_median`, `delivery_z`, `pocket_pivot`, `tight_ratio`, `stack_bull`, `stage2` |
| `primitives/contraction.py` | contraction ratio |
| `primitives/pivots.py` | pivot geometry |

Where the spec's definition differs from an earlier UniDesk primitive
(median-RVOL vs mean-RVOL), **both exist**. Spec experiments must call the
spec-library function.

### 12.5 Detectors (eight, separately disableable)

Shared engine (`detectors/engine.py`): a detector is a named set of rules
over **caller-computed** features. No I/O inside a detector.

* any non-optional rule unavailable → `INSUFFICIENT_DATA`
* any available rule failed → `INVALID` with the named failure
* otherwise → `VALID` (optional skips recorded, not hidden)

Registry (`detectors/registry.py`): unknown names fail closed. A disabled
detector is absent from the result, never silently VALID.

| Name | Intent | Mandatory inputs (thresholds are parameters) |
|---|---|---|
| `momentum_burst` | T1-adjacent continuation | adr_pct, rs_rank, rvol, contraction_ratio, avwap_extension_adr |
| `episodic_pivot` | T5 | gap_pct ≥ 2.5, rvol ≥ 3, close_location ≥ 0.7; delivery_ratio optional |
| `ipo_base` | T4 | listing age 10–250 sessions, base depth ≤ 35%, contraction ≤ 0.8, rs ≥ 70, distance from listing high ≤ 25% |
| `inside_bar` | coil | inside-bar geometry, mother range ≥ 3%, volume ≤ mother, rs ≥ 70 |
| `base_breakout` | T1/T4 family | breakout rvol ≥ 1.5, depth ≤ 35%, contraction ≤ 0.8, rs ≥ 70, room_adr ≥ 1 |
| `pullback` | continuation | proximity to AVWAP/EMA21 ≤ 3%, pullback volume ≤ 0.8, rs ≥ 70, adr ≥ 3 |
| `reversal_reclaim` | T2 family | reclaimed level, volume expansion ≥ 1.3, RS improving; failed-breakdown optional |
| `power_play` | high-ADR continuation | adr ≥ 6, rvol ≥ 2, contraction ≤ 0.5 |

Gold fixtures: `unidesk/tests/fixtures/p2_3_gold.json` — 32 real cases
(2 positive + 2 negative per detector), harvested 2025-11-14 … 2026-07-03.

**Clean-room `base_pattern` (D12 research, not in the eight-detector
registry):** `unidesk/momentum/detectors/base_pattern.py`. Storage-neutral,
no-look-ahead approximation of *public* BananaPatterns metric definitions
(`baseStart`, pivot, depth, coil, dry, dry-depth, lifecycle verdict,
configurable 1–99 RS rank). Calibrated on the public YASHHV snapshot ending
2026-08-28 (base start 2026-07-14, pivot 1003.70, depth ~13.3%, coil ~0.86,
dry ~0.89, verdict `watch`). Explicitly **not** vendor-logic parity.
Not wired into `scan_universe` / nightly. Presets (VCP / BlueSky /
MultiYear / IPOBase) and licensed `universe.json` remain N6 / D12.

### 12.6 Quality stack (R-D)

* **Stock quality** (`scoring/stock_quality.py`) — decomposable weighted mean
  of trend, rs_rank, rvol, delivery_ratio, room_to_52w_high, circuit_safety.
  Nulls drop coverage; they never become zeros. Below 60% available weight
  the score is `None` / `INSUFFICIENT_DATA`. Weights are caller-supplied.
  Circuit UC/LC is a hard_gate beside the score, not inside it.
* **Entry quality** (`scoring/entry_quality.py`) — same discipline for
  trigger-timing contributors.
* **Setup quality** is the detector verdict + named rule failures, not a
  blended number.

### 12.7 R0 regime

`unidesk/momentum/regime.py`.

```
BULL   pct_above_50 >= 0.60  (and Midcap 150 ≥ SMA50 when that boolean is supplied)
BEAR   pct_above_50 <= 0.40  (and Midcap 150 < SMA50 when supplied)
CHOP   otherwise, or when breadth and Midcap disagree
```

Hysteresis default 3 sessions — no flicker. When Midcap SMA50 is available,
`source = breadth_and_midcap150_sma50`; otherwise `source = breadth_only`
and every row says so.

SMA200 is computable on Nifty 50 (1,299 sessions) but is **not yet in the
label rule**. VIX 1y z-score is stored, not labelled.

### 12.8 Events, splits, calendar, invariants

| Module | Role |
|---|---|
| `data/bhavcopy.py` | ingest EQ series from `data/bhavcopy/` |
| `data/events.py` | Chartsmaze IPO listings, circuit revisions (PIT lookup returns None before first revision), 10,972 announcements as a **non-adjusting** review queue (`auto_adjustable=False`), vendor breadth (calibration only) |
| `data/splits.py` | split detector; confirmation is **close-to-close**, not open-gap. Known 2:1 confirmations: ANANDRATHI 2026-06-03, BEML 2025-11-03, AGIIL 2025-02-07, ANUHPHR 2025-07-15. 194 open-gap candidates on the extended archive — open-gap ≠ confirmed. |
| `data/corp_actions.py` | confirmed table load/persist; `adjust_ohlcv` derived view. Scan/nightly apply the seed (4 names). Raw store untouched. Official NSE CA-with-ratios still open. |
| `data/calendar.py` | trading calendar from observed sessions |
| `data/invariants.py` | OHLC / delivery quarantine |
| `data/indices.py` | parquet persist + `above_sma`; D16 `ind_close_all` overlay |
| `data/manas_extract.py` | D17 sqlite RO copy of `sector_index_prices` and dated `universe` |
| `data/reference_ingest.py` | Chartsmaze sector/industry mapping; D18 nexus CSV fill-in (Chartsmaze wins on overlap) |

### 12.8.1 Industry map (D18)

Store: `data/market/reference/industry_mapping.parquet`
(`symbol`, `industry`, `source_tier`).

```
Chartsmaze stocks.csv  →  2,423 rows, source_tier=CHARTSMAZE
nexus_industry_map.csv →  2,676 labels offered
                         →  2,327 overlap: Chartsmaze kept (labels disagreed)
                         →    349 nexus-only appended, source_tier=NEXUS_INDUSTRY_MAP
                         →  2,772 total
```

Code: `parse_nexus_industry_map`, `overlay_industry_rows`,
`fill_industry_mapping_from_nexus` in `reference_ingest.py`. Primary table
must already exist — nexus will not invent it. Re-run is fill-only against
whatever is already persisted.

`sector_of` still rolls industry→sector via the Chartsmaze industries file.
A nexus-only industry with no Chartsmaze rollup is reported as the industry
string itself (honest fallback, not a guessed sector).

This is **not** PIT membership, **not** NSE official industry, and **not**
the manas `nexus_crosswalk.py` sector-key table (that file is not imported).

### 12.9 Research spine (N4)

| Module | Role |
|---|---|
| `research/candidates.py` | freeze every detector decision as `ResearchEvent` (`research-event-v1`), including INVALID and INSUFFICIENT_DATA. `attach_outcomes` uses bars **strictly after** the decision session (next-bar fill). Missing future/ATR → UNRESOLVED, never zeros. |
| `research/event_store.py` | parquet `date=YYYY-MM-DD/events.parquet`. Same-day rewrite, not mixed-hash append. Snapshot/outcomes stored as JSON strings. |
| `research/labels.py` | MFE/MAE, R-multiples, stop-hit first-touch, breakout hold/fail with UNRESOLVED |
| `research/costs.py` + `config/costs.yaml` | spec §1.4 conservative cash: brokerage+GST 15, STT 20, exch/stamp 5, impact cap 15/side, impact coef 8, T5 gap 25 bps. Version `costs-v1-spec-1.4`. Net is the only accepting number. |
| `research/walkforward.py` | expanding folds, 5-session embargo, next-bar fill, `simulate_long` gross+net. `4y/1y` **raises** on a short calendar — it does not fake it. |
| `research/leakage.py` | decision-time + ±60-session same-symbol embargo |
| `research/leakage_suite.py` | planted bugs the tests must catch: future bars, full-sample normalisation, today's membership, future gold |
| `research/delivery_lag.py` | R-O helper |
| `research/provenance.py` | effective / available / built / source stamp |

Nightly freezes the scan into the parquet store (outcomes empty until a later
`attach_outcomes` call with a future slice). Attaching outcomes across the
1M-bar archive is still open. Ablation ladder not started.

### 12.10 Contracts

Frozen dataclasses in `unidesk/contracts/`: `market`, `candidate`, `setup`,
`geometry`, `flow`, `social`, `decision`, `research`, plus `base`
(`ContractError`, fail-closed enums, tz-aware `as_of`). Unknown enums fail
closed. Nulls stay null. Version/hash fields mandatory on snapshots.

### 12.11 Governance

| File | Job |
|---|---|
| `unidesk/CANONICAL.md` | what is real vs decoy; read first |
| `unidesk/DECISIONS.md` | locked calls D1–D17 |
| `unidesk/TASKS.md` | running backlog |
| `unidesk/HANDOFF.md` | next-session intent |
| `unidesk/GOAL.md` | standing goal + wave queue |
| `unidesk/STATE.json` | machine-written by `run_checks.py` |
| `unidesk/design/DATA_AUTHORITY.json` | sole-writer map |
| `unidesk/design/MODEL_WORK_LOG.jsonl` | 14-key attribution, machine-checked |
| `unidesk/design/PHASE0_GAP.md` | Phase 0 spec → this tree |

Boundaries (D4): UniDesk may read `orderflow` one-way. Nothing imports
`manas_os` or `traderlog`. FYERS wire vocabulary lives only in
`orderflow/market_data/fyers_adapter.py`.

---

## 13. How to run (as-built)

From repo root `koreanguy`, using `.venv-orderflow`:

```text
# nightly (local archive, no download)
.\.venv-orderflow\Scripts\python.exe -m unidesk.momentum.nightly --no-download

# smoke ingest
.\.venv-orderflow\Scripts\python.exe -m unidesk.momentum.nightly --no-download --limit-files 5

# tests
.\.venv-orderflow\Scripts\python.exe -m pytest orderflow/tests unidesk/tests -q

# attribution + leakage smoke
.\.venv-orderflow\Scripts\python.exe unidesk/run_checks.py
```

`run_checks.py` is the wave-close gate. Full suite is
`orderflow/tests` + `unidesk/tests`. The clean-room base detector has its
own focused proof (`test_cleanroom_base_pattern.py`); it is not one of the
eight nightly detectors.

---

## 14. Open work (honest) — do not start AI or live unless asked

In order, matching `unidesk/HANDOFF.md`:

1. **N3 remainder.** Official NSE CA-with-ratios (announcements still have
   no ratios; 194 detector candidates stay unconfirmed). Optionally adopt
   manas `daily_prices` (2021–) as EOD history — that is a **D-decision**,
   not a silent copy. PIT membership before Jul 2026; ISIN/continuity_id;
   MTO; official bands; F&O PIT.
2. **N4 remainder.** Attach outcomes across the 1M-bar archive; 4y/1y folds
   only when the bar calendar is long enough; ablation ladder P7.4.
3. **D12.** BananaPatterns public `universe.json` (private research use).
   Clean-room `base_pattern` detector exists and is not in the nightly
   registry; licensed historical differential remains open.
4. **N5.** Experiments A/B — still want a longer CA-applied series than
   four names.
5. **N8.** Terminal against this spec's data, not fixtures.
6. **Do not** build L1.5 / L2 / live module unless the owner asks.
7. **Do not** create a parallel `src/` tree.

Phase 0 is **not** accepted. Spec refresh is documentation of as-built; it
does not close N5.

---

## 15. Companion documents in `plan/`

| File | Role after this refresh |
|---|---|
| `UNIFIED_DESK_BUILD_MANUAL.md` | V1, **superseded**. Live-first architecture. Historical. |
| `UNIFIED_DESK_UI_UX_MANUAL_V2.md` | Controlling UI/UX. Evening desk. Prototype does not fulfill N8. |
| `UNIFIED_DESK_UI_UX_MANUAL.md` | V1 UI, superseded. |
| `UNIFIED_DESK_INTEGRATION_PLAN.md` | Task-number crosswalk + EOD-first sequencing. Status lives in TASKS. |
| `SWING_EDGES_TECHNICAL_SPEC.md` | Frozen research definitions, costs, kill criteria. Champion. |
| `PHASE0_DATA_BUILD_SPEC.md` | Warehouse contract for N3–N4. No predictive AI. |
| `AI_NATIVE_INDIAN_SWING_RESEARCH_CONSTITUTION.md` | L0→L5, L1.5 before neural, 3-D promotion. Forbidden until Phase 0. |
| `AI_NATIVE_EDGES_NORTH_STAR.md` | Six-hypothesis portfolio. |
| `ORDERFLOW_BUILD_MANUAL.md` | Child spec for N7 internals only. |
| `TRADERLOG_V2_BUILD_MANUAL.md` | Sibling product; UniDesk does not import it. |
