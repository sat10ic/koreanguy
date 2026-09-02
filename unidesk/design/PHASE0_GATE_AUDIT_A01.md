# A-01 — Phase 0 §53 Acceptance Checklist Audit

**Date:** 2026-09-01 · **Auditor:** GLM-5.3-Flash via ZCode (session evidence
only; no long jobs launched for this audit beyond the in-flight archive
regen noted below).
**Spec:** `plan/PHASE0_DATA_BUILD_SPEC.md` §53 (Phase 0 Acceptance
Checklist). Verdict values: **PASS** (item verified in-repo),
**FAIL** (required item missing or contradicted by evidence),
**PARTIAL** (built, with a named open remainder).

> Phase 0 contains no predictive AI (spec §0). Until this table is all-PASS,
> every PART-13 task (A-02..A-07) stays BLOCKED — see UI_BUILD_SPEC_V1
> PART 13.

## Market Truth

| # | §53 item | Verdict | Evidence |
|---|---|---|---|
| 1 | Immutable raw archive exists | **PARTIAL** | `data/bhavcopy/` holds 4,034 raw NSE files (legacy `cm*bhav.csv` + `sec_bhavdata_full_*.csv`) and `data/market/bhavcopy/` partitions; raw files are written once. Not immutable-by-policy: no write-protection or retention contract; UDiFF-format files not present (legacy format only, pre-migration corpus). |
| 2 | SHA256 manifest populated | **FAIL** | No `source_manifest.parquet` (spec §30) anywhere under `data/` or `unidesk/`. The CA table hash (`confirmed_actions_content_hash`, `unidesk/momentum/data/corp_actions.py:36`) is the only content hash in production use. |
| 3 | Legacy and UDiFF bhavcopy adapters pass | **PARTIAL** | Legacy adapter built and in production (`unidesk/momentum/data/bhavcopy.py`, parses `cm*bhav.csv` + `sec_bhavdata_full_*.csv`, incl. `DELIV_PER`). UDiFF adapter: absent (no UDiFF-format file in corpus to test against). |
| 4 | Security identity is effective-dated | **FAIL** | Scan/feature keys are SYMBOL strings throughout (`scan.py` by_symbol); no `security_id`/`continuity_id` model (spec §8). Symbol-change continuity is not handled (see the F&O row of the as-built inventory: "ISIN/continuity_id … not built"). |
| 5 | Symbol/series history preserved | **FAIL** | No series-change history store. Series filtering is heuristic (EQ series in bhavcopy parse); renamed symbols appear as new keys (ALPHAGEO/UJJIVAN staleness found by the 2026-09-01 audit is a symptom of exactly this gap). |
| 6 | Trading calendar complete | **PASS (corpus-scoped)** | Calendar derived from bhavcopy sessions themselves; `unidesk/research/walkforward.py` TradingCalendar + `years_4_1_folds`/`expanding_folds` refuse short calendars rather than fake folds. Coverage limited to the on-disk corpus (2021→2026 mixed; full-archive regen in progress extends it to 2010+). 2016 target: FAIL (see row 23). |
| 7 | Corporate actions ingested | **PARTIAL** | Split detection + close-to-close confirmation (`unidesk/momentum/data/splits.py`, `corp_actions.py`); confirmed-actions CSV (4 actions, hash `d1b585eb60fd4f82`) applied as a derived scan view; quarantine of 51 auto-confirmed actions (2026-08-31). Official NSE CA-with-ratios feed still open. |
| 8 | Structural adjustment factors auditable | **PASS** | Every adjusted series stamps its adjustment basis: `adjust_ohlcv` + `confirmed_actions_content_hash` on both scan snapshots (`research/candidates.py:138,154`) and archive future maps (`research/archive_attach.py`). Basis mismatch refuses (UNRESOLVED, not silent). The B-05 fix (2026-09-01) added the missing staleness detector half. |
| 9 | Delivery parsed and timestamped | **PARTIAL** | `DELIV_PER` parsed per bar; `available_at = session 18:00 IST` is ASSUMED (`market_store.load_into_store`), not measured; the ≥1-session delivery-lag guard exists (`research/delivery_lag.py`) but is wired only in tests, not the scan path (B-09 finding, 2026-09-01). |
| 10 | Price bands ingested | **PARTIAL** | Circuit bands arrive via bhavcopy columns (`upper_circuit`/`lower_circuit`, consumed by `circuit_risk_state` in scan.py). Chartsmaze revision history for PIT bands referenced in design docs; no standalone canonical band store. |
| 11 | Circuit proxies explicitly named as proxies | **PASS** | `unidesk/momentum/features/circuit.py` + scan comments name the daily-close proxies as proxies; detectors consume `circuit_risk_state` with explicit `CIRCUIT_PROXIMITY_PCT_DEFAULT`. |
| 12 | F&O dynamic-band distinction present | **FAIL** | No F&O data in the repo (also blocks OI features, R-09); no dynamic-band flag. |
| 13 | Index prices complete | **PARTIAL** | D16/D17 harvests: Nifty 50 / VIX from 2021-06-01, Midcap/Smallcap from 2024-07-08 (`data/market/reference/`, per as-built inventory). 2016 start missing; R0's Midcap-SMA50 input degrades honestly to `breadth_only` (`momentum/nightly.py` regime block). |
| 14 | PIT membership reconstructed | **FAIL** | 18 dated universe snapshots, 2026-07-10 → 2026-08-20 only; 2016→2026-06 missing (as-built inventory row 3). Do-not-backfill rule (D14.5) respected. |
| 15 | No current-membership survivorship | **PARTIAL** | The scan universe is reconstructed from each session's own bhavcopy rows (no membership forward-fill), which avoids the worst survivorship error; but without PIT index membership (row 14) any index-anchored screen would be survivorship-biased. |

## Features

| # | §53 item | Verdict | Evidence |
|---|---|---|---|
| 16 | MAs / ATR / returns / RVOL / delivery z / liquidity point-in-time | **PASS** | All features computed from bars available at `available_at <= as_of` (`scan.py:221`); window functions (`ema`, `atr`, `rvol`, `delivery_volume_ratio`) are causal; truncation invariance is tested (`tests/test_truncation_invariance.py`). |
| 17 | RS foundation built | **PASS (with B-01 fix)** | Cross-sectional 20d-return percentile (`scan.py`); 2026-09-01 B-01 fix excludes no-print symbols from the percentile universe itself (previously only from candidates), closing the dead-name distortion. |
| 18 | Universe eligibility generated daily | **PASS** | `evaluate_gates` (price floor, turnover floor, ETF heuristic, circuit-lock) applied in the nightly (`nightly.py` opts in); per-reason skip buckets disclosed in the report footer. |

## R0

| # | §53 item | Verdict | Evidence |
|---|---|---|---|
| 19 | Breadth uses PIT Nifty 500; denominator stored | **FAIL (degraded honestly)** | R0 breadth denominator is the gated scan universe (`honesty_footer.above_ema21_of`), NOT PIT Nifty 500 — membership does not exist (row 14). The classifier emits `source="breadth_only"` and stores its denominator, which is the spec's honest degrade path, but the §53 item as written fails. |
| 20 | <90% coverage blocks R0 | **PARTIAL** | Coverage check not implemented against a 90% floor; `regime_built` reflects classifier state. Hysteresis unit-tested (`tests/test_quality_regime_wiring.py`); regime state persisted cross-run (`regime_state.py`). |
| 21 | Midcap SMA50 uses prior 20 sessions | **N/A (degraded)** | Input unavailable (no Midcap history pre-2024-07); classifier runs breadth-only. |
| 22 | Raw labels deterministic; flips/year reported; confidence diagnostic | **PASS** | `RegimeClassifier` deterministic + hysteresis; regime history export reports labels per session (`run_export_regime_history.py`); confidence not shown anywhere in the UI. |

## Costs

| # | §53 item | Verdict | Evidence |
|---|---|---|---|
| 23 | Conservative profile frozen; impact unit-tested; ADV stored; no missing-ADV trades; no circuit execution assumed | **PARTIAL** | `unidesk/research/costs.py` (costs-v1-spec-1.4 frozen in `settings_<date>.json`); labels v4 carry cost fields but net_bps is null on 11,430/11,591 outcome rows (writer gap — the "v4-net-cost" stamp does not mean net is populated); ADV participation stored per event snapshot (`adv_series`); circuit execution not assumed. |

## Audit

| # | §53 item | Verdict | Evidence |
|---|---|---|---|
| 24 | Source manifest | **FAIL** | Absent (row 2). |
| 25 | Build manifest | **FAIL** | Absent (spec §31); runs log to ad-hoc `.log` files only. |
| 26 | Availability ledger (20-session first-seen) | **FAIL** | Absent; `available_at` is an assumption (row 9). |
| 27 | QA report | **PARTIAL** | `run_checks.py` (attribution, data-authority, leakage, contracts) is green at time of writing; the research-coverage probe (`run_research_coverage_export.py`) reports label homogeneity. Not a published QA report artifact. |
| 28 | Leakage tests | **PASS** | `leakage_suite.py` + planted-future-bar test green (`run_checks.py` `[leakage] pass`); embargo primitive exists (`leakage.py::embargo_overlapping_events`, still unwired pending L1.5). |
| 29 | Regression fixtures | **PARTIAL** | 319 pytest tests green at 2026-09-01 (14 pre-existing failures documented, unrelated suites); no frozen regression fixture pack for the data build itself. |
| 30 | Deterministic rebuild hashes | **FAIL** | `make rebuild` (spec §2.2) not implemented; no canonical/feature hash pair emitted. |
| 31 | Release tagged `PHASE0_DATA_V1.0.0` | **FAIL** | Not tagged (correctly — everything above). |

## Headline

**PASS 6 · PARTIAL 10 · FAIL 9 · N/A 1** (of the §53 items, grouped as
numbered rows above). **The Phase 0 gate is NOT passed.** The largest
structural gaps: security identity model (§8), manifests + availability
ledger (§30/§31/§14.2), PIT membership/index history (§17), and
deterministic rebuilds (§2.2). Until these close, PART 13 (A-02..A-07)
stays BLOCKED — which is the gate working as designed.

In-flight at audit time: the full-archive outcome regen
(`unidesk/run_regen_full.py`, ~3,878 sessions at ~4,000-session corpus,
2026-09-01) re-bases every event partition onto the verified CA table
`d1b585eb60fd4f82` and the B-01 liveness-corrected RS universe. It directly
advances rows 7, 8, and 17, and extends corpus coverage toward (not to) the
2016 target.
