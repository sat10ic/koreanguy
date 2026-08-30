# Phase 0 gap table

Controlling spec: `plan/PHASE0_DATA_BUILD_SPEC.md` (D14).
This file is the map from that spec onto the existing `unidesk/` tree.
It is not a second spec.

Last verified: 2026-08-29 (D15–D18: archive, indices, manas extract,
nexus industry fill; Build Manual V2 as-built design spec).

| Spec item | Status | Home |
|---|---|---|
| NSE CM bhavcopy ingest, EQ filter, PIT `available_at` | **extended archive** (D15): `data/bhavcopy/` 503 files, 477 sessions, 2024-09-02 → 2026-08-28, **1,004,896 bars** | `unidesk/momentum/data/bhavcopy.py`, nightly default |
| Date-aware UDiFF vs legacy adapter | not built (backlog is one schema) | N3 |
| History 2016-01-01 → latest | **partial** — 23.9 months local (Sep 2024 → Aug 2026); 2016–2024-08 still open | N3 `--all` |
| Trading calendar from observed sessions | **built this slice** | `unidesk/momentum/data/calendar.py` |
| OHLC / delivery invariants + quarantine | **built this slice** | `unidesk/momentum/data/invariants.py` |
| Cost model (spec §1.4 conservative cash) | **built this slice** | `unidesk/research/costs.py` |
| Decision-time + ±60-session embargo | **built this slice** | `unidesk/research/leakage.py` |
| Provenance stamp (effective/available/built/source) | **built this slice** | `unidesk/research/provenance.py` |
| Delivery same-session lag freeze | **policy + helper this slice** | `unidesk/research/delivery_lag.py`, DATA_POLICY.md |
| Corporate-action detect + adjust | detect/adjust exist; **close-to-close confirmation** on four 2:1 names. Seed table applied as a **derived scan view** (raw store untouched). 194 detector candidates remain unconfirmed (open-gap ≠ confirmed). | `corp_actions.py`, `splits.py`, `config/confirmed_actions.csv` |
| Official CA table (schema §12) | **seed:** 4 close-to-close names. Chartsmaze announcements (10,972) still have no ratios, never auto_adjustable. Official NSE CA feed still open. | `unidesk/config/confirmed_actions.csv` + `data/market/reference/confirmed_actions.parquet` |
| Index daily series (Nifty 50/500, Midcap 150, Smallcap 250, VIX) | **D17 extract + D16 overlay:** Nifty 50 / VIX 2021-06-01 → 2026-08-28 (1,299 / 1,293); Midcap 150 / 500 / Smallcap 250 from 2024-07-08 (533). Price index, not TRI. | `indices.parquet` via `manas_extract.py` |
| PIT index membership | **partial:** 18 dated `universe` snapshots (2026-07-10 → 2026-08-20, 43,980 rows). Not 2016–. Do not back-fill today's Nifty list. | `universe_snapshots.parquet` |
| Security-master history / ISIN / continuity_id | not built (symbol is still the working key). IPO listing dates: 175 Chartsmaze rows, store-length proxy no longer the only source. | `events.parse_ipo_listings` |
| Industry / sector mapping | **D18:** Chartsmaze **2,423** + nexus fill **349** (Chartsmaze wins on overlap; taxonomies disagree). Total **2,772**. Vendor labels, not NSE official. Not a 2016 PIT membership series. | `reference_ingest.py` → `industry_mapping.parquet` |
| MTO delivery files + source/calc QA | not built (DELIV_PER on bhavcopy only) | N3 |
| Price bands / circuit official files | **circuit-revision history ingested** (Chartsmaze, effective-dated, PIT lookup returns None before first revision). Official NSE band files still open. | `unidesk/momentum/data/events.py` |
| F&O eligibility PIT flag | not built | N3 |
| Raw/bronze/silver/gold lakehouse | parquet `date=` event store (`research/event_store.py`); freeze includes INVALID | N4 remainder: archive-wide outcome attach |
| `make rebuild DATE=` bit-identical hashes | not built | N4 remainder |
| Walk-forward + leakage suite | **expanding folds + planted-bug suite built**; 4y/1y refused until history lengthens | `unidesk/research/walkforward.py`, `leakage_suite.py` |
| R0 with index SMA50/SMA200 + VIX | Midcap 150 vs SMA50 wired; Nifty 50 SMA200 **computable** (1,299 sessions). VIX 1,293 sessions stored; 1y z-score not yet in the label rule. | `regime.py` + `indices.above_sma` |
| Availability ledger (20 sessions) | not built | owner + N3 |
| Predictive AI / L1.5 / L2 encoder | **forbidden** until Phase 0 acceptance | constitution |

Honest reading: Phase 0 is **not** complete. Index history and a short PIT
universe window were already in `manas_os/data/manas.db` (`manas_os/sources/`
wrote them). UniDesk copies those rows RO (D17). Remaining N3 work is
applying CA-with-ratios to bars, 2016 bhavcopy (or adopting manas
`daily_prices`), and membership before Jul 2026 — not more feature code.
