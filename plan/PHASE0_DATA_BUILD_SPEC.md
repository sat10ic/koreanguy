<!-- Adopted 2026-08-29 as the controlling DATA-BUILD spec for waves N3–N4
     (unidesk DECISIONS D14). Parent constitution:
     plan/AI_NATIVE_INDIAN_SWING_RESEARCH_CONSTITUTION.md.
     Phase 0 contains no predictive AI. Implementation lives in
     unidesk/momentum + unidesk/research (existing package layout; this spec's
     recommended src/ tree is a map, not a second codebase). As-built map:
     plan/UNIFIED_DESK_BUILD_MANUAL_V2.md §0.1 / §3 / §6. Gap table:
     unidesk/design/PHASE0_GAP.md. Canonical copy lives here. -->

# Phase 0 Implementation & Data Build Specification
## AI-Native Indian Equity Swing & Momentum Research

**Version:** 1.0  
**Status:** BUILD SPEC — Phase 0 (not accepted; as-built is partial)  
**Parent:** `AI-Native Indian Swing Research Constitution v1.0`  
**Market:** NSE cash equities, Indian swing / momentum research  
**Primary horizon supported later:** ~3–20 sessions  
**Phase 0 purpose:** Build the point-in-time market-truth layer, R0 regime series, cost model, delivery/circuit infrastructure, and audit controls required before T1/T5 research begins.  
**As-built home:** `unidesk/momentum/` + `unidesk/research/` + `data/market/` (D14: this spec's `src/` tree is a map, not a second codebase). Gap table: `unidesk/design/PHASE0_GAP.md`. Controlling product spec: `plan/UNIFIED_DESK_BUILD_MANUAL_V2.md`.

### As-built inventory (2026-08-29, D14–D18) — Phase 0 is NOT complete

| This spec | Built | Still open |
|---|---|---|
| NSE CM bhavcopy, EQ, PIT `available_at` | D15 `data/bhavcopy/` 1,004,896 bars, 477 sessions, 2024-09-02 → 2026-08-28 | 2016-01-01 history; UDiFF vs legacy adapter |
| Index / VIX daily (price, not TRI) | D17 manas RO extract + D16 `ind_close_all` overlay. Nifty 50 / VIX from 2021-06-01 (1,299 / 1,293); Midcap 150 / 500 / Smallcap 250 from 2024-07-08 (533) | 2016 index history; TRI stays out of this parquet (do not mix) |
| PIT membership | 18 dated universe snapshots, 43,980 rows, 2026-07-10 → 2026-08-20 | 2016–Jun 2026. Do not back-fill today's list (D14.5) |
| Industry / sector mapping | D18: Chartsmaze 2,423 + nexus fill 349 = **2,772**. Chartsmaze wins on overlap. Vendor labels, not NSE official. | PIT industry history; official classification files |
| Trading calendar, OHLC/delivery invariants, cost model, embargo, provenance, delivery-lag policy | built (D14 primitives) | 20-session first-seen availability ledger |
| Corporate actions | split detect + close-to-close confirmation on four 2:1 names; seed table applied as a derived scan view (raw prints untouched); Chartsmaze announcements as non-adjusting review queue | official CA-with-ratios; remaining detector candidates unconfirmed |
| Circuits | Chartsmaze revision history, PIT lookup | official NSE band files |
| F&O PIT, MTO, ISIN/continuity_id, `make rebuild` hashes | not built | N3/N4 remainder |
| Research event store | parquet `date=` partitions; freeze includes INVALID; attach_outcomes next-bar | archive-wide outcome attach; `make rebuild` hashes |
| Predictive AI / L1.5 / L2 | **forbidden** until this spec's Definition of Done (§2) passes | — |

manas `daily_prices` (1.60M bars, 2021-07-12 → 2026-08-21) is inventoried, not adopted as the EOD bar home. Adopting it is a D-decision.

---

# 0. Governing Rule

> **Phase 0 contains no predictive AI.**

Its job is to make later claims falsifiable.

The build is successful when the same historical date can be reconstructed repeatedly with:

- the securities that genuinely existed then,
- the symbol/series that applied then,
- the prices and volumes known then,
- the delivery data available then,
- the price-band/circuit state that applied then,
- the index membership that applied then,
- the corporate actions known then,
- the cost assumptions frozen then,
- and an R0 regime value computed without information from the future.

If any downstream model requires silently replacing this history with today's metadata, Phase 0 has failed.

---

# 1. Phase 0 Scope

Phase 0 builds five things:

```text
                     PHASE 0
                        │
       ┌────────────────┼────────────────┐
       ▼                ▼                ▼
 MARKET TRUTH        R0 REGIME        COST MODEL
       │
       ├──── delivery
       ├──── circuits / price bands
       ├──── corporate actions
       ├──── security identity
       ├──── index membership
       ├──── index / VIX history
       └──── point-in-time universe
                        │
                        ▼
                AUDIT + QA LAYER
```

## 1.1 Included

- NSE cash-equity daily market data
- security master history
- symbol / series changes
- point-in-time index membership
- Nifty index histories
- India VIX history
- corporate actions
- price adjustments required for technical research
- security-wise delivery data
- price-band / circuit metadata
- circuit-event proxies on daily data
- F&O eligibility flag where obtainable point-in-time
- trading calendar
- daily research-universe reconstruction
- shared deterministic daily features needed by R0 and Phase 1/2
- R0 regime classifier
- conservative cost and impact model
- provenance, checksums, first-seen timestamps
- historical backfill
- data-quality tests
- reproducible rebuilds

## 1.2 Explicitly Not Included

Phase 0 does **not** build:

- T1 signals
- T5 signals
- L1.5 analogue retrieval
- neural encoders
- intraday EP models
- F1 filing NLP
- F2 relationship graphs
- trading UI
- broker execution
- portfolio optimization
- SME strategies
- options strategies
- stock-futures short logic

Those belong after the market-truth layer passes acceptance.

---

# 2. Definition of Done

Phase 0 is complete only when all of the following hold.

## 2.1 Historical Coverage

Target research history:

```text
2016-01-01 → latest available session
```

Required coverage:

| Dataset | Phase 0 target |
|---|---:|
| Trading calendar | 100% |
| NSE daily OHLCV for eligible research securities | ≥99.5% expected rows, with every gap classified |
| Index daily series used by R0 | 100% trading sessions |
| India VIX | ≥99.5%, explicit missing flags |
| Delivery | ≥98% where the exchange report exists; missing days explicitly flagged |
| Corporate actions | all detected events affecting securities in research universe |
| Price-band state | all dates where source file is available; fallback logic explicitly marked |
| PIT Nifty 500 membership | complete enough to compute R0; otherwise R0 date is BLOCKED |
| PIT Midcap 150 / Smallcap 250 membership | sufficient for research-universe reconstruction |

No silent forward-fill of membership, delivery, price bands, or corporate actions across unknown periods.

## 2.2 Reproducibility

Running:

```bash
make rebuild DATE=2024-06-14
```

twice from identical raw files must produce identical canonical and feature-layer hashes.

## 2.3 Point-in-Time Safety

Every derived row must contain:

```text
effective_date
available_at
built_at
source_version
```

Every feature intended for a decision must satisfy:

```python
assert feature_timestamp <= decision_timestamp
```

## 2.4 R0

Phase 0 must output one auditable R0 row for every valid market session for which the required PIT inputs exist.

## 2.5 QA

No unresolved **BLOCKER** severity data-quality failures may remain in dates used by Phase 1/2 backtests.

---

# 3. Source-of-Truth Hierarchy

Do not treat a convenient Python library as the source of truth.

Priority:

```text
1. Official exchange / index-provider files
2. Official exchange historical archives
3. Frozen locally archived copies of those files
4. Secondary vendor only for gap repair
5. Manual review for irreducibly complex corporate actions
```

Any secondary repair must be tagged:

```text
source_tier = SECONDARY_REPAIR
```

and may not overwrite the official raw record.

---

# 4. Verified Official Source Catalogue

The names below are the source identifiers the ingestion layer should target. Exact website routes may change; the collector should therefore be adapter-based rather than embedding assumptions throughout the codebase.

## 4.1 NSE Capital-Market Bhavcopy

**Current preferred report:**  
`CM-UDiFF Common Bhavcopy Final`

Current file naming is of the form:

```text
BhavCopy_NSE_CM_0_0_0_YYYYMMDD_F_0000.csv.zip
```

The older common bhavcopy format was discontinued in 2024. The parser therefore needs a **date-aware format registry**, not one CSV schema for the entire 2016+ history.

### Required action

```text
date < UDiFF migration cutoff
→ legacy CM bhavcopy adapter

date >= UDiFF migration cutoff
→ UDiFF CM bhavcopy adapter
```

Do not normalize raw files in-place.

---

## 4.2 Security-Wise Delivery Positions

Official NSE report:

```text
CM - Security-wise Delivery Positions
```

Historical file naming commonly uses:

```text
MTO_DDMMYYYY.DAT
```

Required canonical fields:

```text
trade_date
symbol
series
traded_qty
deliverable_qty
delivery_pct
```

Store the source-reported percentage and independently recompute:

```text
delivery_pct_calc = deliverable_qty / traded_qty * 100
```

The difference becomes a QA field.

---

## 4.3 NSE MII Security File

Use the daily security master report where available:

```text
CM - MII - Security File
```

Current naming resembles:

```text
NSE_CM_security_DDMMYYYY.csv.gz
```

Purpose:

- point-in-time symbol
- series
- instrument/security metadata
- listed-security inventory
- identity reconciliation
- security status fields where exposed

Do not use today's security master to reconstruct 2018.

---

## 4.4 Series Changes

Ingest the NSE series-change report where available.

Purpose:

```text
EQ → BE
BE → EQ
symbol/series status transitions
trade-to-trade periods
```

A security's current `EQ` status cannot be retroactively applied to past dates.

---

## 4.5 Corporate Actions

Preferred source:

```text
NSE Corporate Actions / Corporate Filings — Corporate Actions
```

Minimum stored fields:

```text
symbol
company_name
series
purpose_raw
face_value
ex_date
record_date
book_closure_start
book_closure_end
source_published_at
```

Normalize into an event taxonomy later in the pipeline.

---

## 4.6 Price Bands / Circuit State

Preferred sources:

```text
NSE Daily Price Bands / Complete List of Price Bands
NSE surveillance / security files where band information is exposed
```

Phase 0 must support:

```text
2%
5%
10%
20%
NO_STATIC_BAND
DYNAMIC_OPERATING_RANGE
UNKNOWN
```

Securities with eligible derivatives require separate treatment because they do not behave like ordinary static-band cash securities.

---

## 4.7 Index and VIX History

Preferred official sources:

```text
NSE / Nifty Indices historical index data
Historical India VIX
Nifty 50
Nifty Midcap 150
Nifty Smallcap 250
Nifty 500
sector indices required later
```

Store price index and total-return index separately if both are collected.

R0 uses the price/index series explicitly declared in the configuration. Do not mix TRI and price-index history within one moving average.

---

## 4.8 Point-in-Time Index Membership

Required indices:

```text
NIFTY_500
NIFTY_MIDCAP_150
NIFTY_SMALLCAP_250
```

Preferred reconstruction method:

1. official constituent snapshots
2. official reconstitution notices / effective dates
3. archived official constituent files
4. secondary source only to fill a documented gap

Each membership row must be effective-dated.

If PIT membership is unavailable for a period, do **not** substitute today's constituent list.

---

## 4.9 F&O Eligibility

Maintain:

```text
has_stock_futures
```

as an effective-dated field where reliable historical contract membership can be reconstructed.

Phase 0 does not require futures backtesting, but later T2 logic must not infer current F&O eligibility backward through time.

---

# 5. Repository Layout

Recommended structure:

```text
repo/
│
├── CONSTITUTION.md
├── PHASE0_SPEC.md
├── README.md
├── pyproject.toml
├── Makefile
│
├── config/
│   ├── phase0.yaml
│   ├── sources.yaml
│   ├── r0.yaml
│   ├── costs.yaml
│   ├── universe.yaml
│   └── schemas/
│
├── data/
│   ├── raw/
│   │   ├── nse_cm_bhavcopy/
│   │   ├── nse_delivery/
│   │   ├── nse_security_master/
│   │   ├── nse_series_changes/
│   │   ├── nse_corporate_actions/
│   │   ├── nse_price_bands/
│   │   ├── nse_surveillance/
│   │   ├── index_prices/
│   │   ├── index_membership/
│   │   └── vix/
│   │
│   ├── bronze/
│   ├── silver/
│   ├── gold/
│   └── quarantine/
│
├── metadata/
│   ├── source_manifest.parquet
│   ├── build_manifest.parquet
│   ├── availability_log.parquet
│   └── data_quality_results.parquet
│
├── src/
│   ├── ingest/
│   ├── parsers/
│   ├── identity/
│   ├── adjustments/
│   ├── canonical/
│   ├── features/
│   ├── regime/
│   ├── costs/
│   ├── universe/
│   ├── quality/
│   └── cli/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── fixtures/
│   ├── leakage/
│   └── regression/
│
├── reports/
│   ├── quality/
│   ├── coverage/
│   ├── regime/
│   └── rebuild/
│
└── notebooks/
    └── exploratory_only/
```

`notebooks/` may never become the only implementation of a production feature.

Every feature used in research must live in `src/`.

---

# 6. Storage Architecture

Use a simple layered lakehouse model.

```text
OFFICIAL FILE
     │
     ▼
RAW / IMMUTABLE
     │
     ▼
BRONZE / SOURCE-NATIVE PARSE
     │
     ▼
SILVER / CANONICAL MARKET TABLES
     │
     ▼
GOLD / FEATURES + R0 + UNIVERSE
```

## 6.1 Raw Layer

Store files exactly as downloaded.

Never alter.

Path convention:

```text
data/raw/<source_name>/trade_date=YYYY-MM-DD/<original_filename>
```

For each file record:

```text
sha256
downloaded_at
first_seen_at
source_name
source_report_name
trade_date
http_status
byte_size
parser_version_expected
```

## 6.2 Bronze Layer

One row-per-source-record.

No cross-source joins.

Purpose:

- parse source schema
- normalize datatypes
- preserve source column names
- expose parsing errors

## 6.3 Silver Layer

Canonical tables:

```text
security_master_history
daily_security
daily_delivery
daily_price_band
corporate_action
index_daily
index_membership_history
trading_calendar
fno_membership_history
data_availability
cost_schedule
```

## 6.4 Gold Layer

Research-ready tables:

```text
daily_security_panel
daily_universe
daily_shared_features
r0_daily
cost_model_daily
```

---

# 7. Technology Choice

Phase 0 data volume does not justify a distributed stack.

Recommended:

```text
Python 3.12+
Parquet
DuckDB
Polars or Pandas
PyArrow
Pydantic
pytest
```

Optional:

```text
SQLite / DuckDB for metadata catalogue
```

Avoid adding:

- Spark
- Kafka
- Kubernetes
- vector databases
- feature stores
- ML orchestration

before the deterministic warehouse exists.

The entire daily equity panel is small enough to remain boring. That is a feature.

---

# 8. Security Identity Model

This is one of the highest-risk areas.

Never use `symbol` as the permanent primary key.

## 8.1 Keys

Use:

```text
security_id
```

derived primarily from the point-in-time exchange identity / ISIN where available.

Also maintain:

```text
continuity_id
```

for economically continuous price histories across identity changes.

### Rule

Do not auto-chain continuity across:

- mergers
- demergers
- reverse mergers
- schemes of arrangement
- materially changed economic entities

Those require manual review.

## 8.2 Security Master History

Schema:

```text
security_id
continuity_id
exchange
isin
symbol
series
security_name
instrument_type
listing_date
delisting_date
effective_from
effective_to
is_sme
is_etf
is_reit_invit
is_active
source_file_id
```

This is an SCD Type-2 style dimension.

The same symbol can therefore exist in multiple effective periods without corrupting old data.

---

# 9. Trading Calendar

Canonical table:

```text
trade_date
is_trading_day
session_open
session_close
is_special_session
is_muhurat_session
is_half_day
previous_trade_date
next_trade_date
```

Timezone:

```text
Asia/Kolkata
```

Do not generate sessions from weekdays alone.

Use actual exchange sessions.

Every rolling-window function must operate on trading sessions, not calendar days.

---

# 10. Canonical Daily Security Table

## 10.1 Core Schema

```text
trade_date
security_id
continuity_id
symbol
series
isin

open_raw
high_raw
low_raw
close_raw
prev_close_raw

volume_raw
traded_value_raw
trades_count

vwap_source
vwap_calc

price_adjustment_factor
open_struct_adj
high_struct_adj
low_struct_adj
close_struct_adj
volume_struct_adj

corporate_action_flag
corporate_action_type

circuit_band_pct
upper_band_price
lower_band_price
band_type

upper_band_touch
lower_band_touch
upper_band_close
lower_band_close
circuit_lock_proxy

has_stock_futures
asm_gsm_flag
surveillance_flag

source_file_id
available_at
built_at
```

## 10.2 OHLC Invariants

For every valid row:

```text
high >= max(open, close)
low <= min(open, close)
high >= low
volume >= 0
traded_value >= 0
```

Rows violating invariants go to quarantine.

---

# 11. Raw Price vs Research Price

The system needs more than one price view.

## 11.1 `*_raw`

Use raw exchange prices for:

- actual fills
- raw gaps
- price-band tests
- circuit logic
- auction / limit events
- execution simulation

## 11.2 `*_struct_adj`

Use structurally adjusted prices for:

- moving averages
- ATR
- swing geometry
- long historical returns
- high/low comparisons
- technical pattern continuity

### Automatically supported in v1

- split
- bonus
- consolidation

### Conditional / manual review

- rights issues
- demergers
- mergers
- schemes of arrangement
- unusual capital restructurings

### Cash dividends

Do not silently back-adjust `struct_adj` for ordinary cash dividends in v1 unless a verified adjustment factor exists.

Instead:

```text
corporate_action_flag = DIVIDEND
```

and later event logic must know the date was mechanically affected.

Large / special dividends require explicit review because they can fabricate false gaps.

---

# 12. Corporate Action Table

Schema:

```text
ca_id
security_id
symbol_at_event
purpose_raw
ca_type

announcement_date
ex_date
record_date

ratio_num
ratio_den
cash_amount
face_value_before
face_value_after

auto_adjustable
adjustment_factor
manual_review_required
review_status

source_file_id
available_at
```

Normalized `ca_type`:

```text
SPLIT
BONUS
CONSOLIDATION
RIGHTS
DIVIDEND
SPECIAL_DIVIDEND
BUYBACK
MERGER
DEMERGER
SCHEME
SYMBOL_CHANGE
FACE_VALUE_CHANGE
OTHER
```

## 12.1 Adjustment Audit

For every applied factor store:

```text
factor_before
factor_after
method
source
reviewer
code_version
```

No adjustment should be irreproducible.

---

# 13. Volume Adjustment Policy

Raw share volume can become discontinuous after splits / bonuses.

Maintain:

```text
volume_raw
volume_struct_adj
traded_value_raw
```

For split/bonus/consolidation events:

```text
volume_struct_adj = volume_raw / price_adjustment_factor
```

using the same continuity convention as price.

Research should prefer:

- traded value for liquidity,
- normalized volume ratios,
- and adjusted share volume where multi-year share-count comparability matters.

---

# 14. Delivery Data Contract

Canonical schema:

```text
trade_date
security_id
symbol
series

traded_qty_source
deliverable_qty
delivery_pct_source
delivery_pct_calc

delivery_qty_z20
delivery_pct_z20

source_file_id
available_at
is_late_for_same_day_decision
quality_status
```

## 14.1 Validation

Require:

```text
0 <= deliverable_qty <= traded_qty
0 <= delivery_pct <= 100
```

Allow small rounding difference between source and recomputed percentage.

Suggested QA:

```text
abs(delivery_pct_source - delivery_pct_calc) <= 0.2 percentage points
```

Larger differences generate a warning or quarantine depending on scale.

## 14.2 Availability Rule

Historical files rarely tell us their exact first-public timestamp.

Therefore build a live **availability ledger**.

For at least 20 normal trading sessions, record:

```text
source_name
trade_date
first_poll_at
first_success_at
file_hash
```

Until this empirical availability study exists:

> **Delivery from trade date T is safe only for a next-session decision, not assumed available at 15:30 or 15:45 on T.**

This protects the constitution's decision-time rule.

---

# 15. Price Bands and Circuit State

Official static cash-equity band families include:

```text
2%
5%
10%
20%
```

Certain derivative-eligible securities require dynamic operating-range treatment instead of ordinary fixed static bands.

## 15.1 Canonical Fields

```text
trade_date
security_id
band_type
circuit_band_pct
base_price
upper_band_price
lower_band_price

upper_band_touch
lower_band_touch
upper_band_close
lower_band_close

circuit_lock_proxy
circuit_proxy_confidence

source_file_id
available_at
```

`band_type`:

```text
STATIC_2
STATIC_5
STATIC_10
STATIC_20
DYNAMIC
NONE
UNKNOWN
```

## 15.2 Daily-Only Circuit Proxies

Daily OHLC cannot prove that a security was locked for the entire session.

Therefore distinguish:

```text
upper_band_touch
upper_band_close
circuit_lock_proxy
```

Example conservative proxy:

```text
upper_band_touch =
    abs(high_raw - upper_band_price) <= tick_tolerance

upper_band_close =
    abs(close_raw - upper_band_price) <= tick_tolerance

circuit_lock_proxy =
    upper_band_close
    AND high_raw == low_raw
    AND close_raw == upper_band_price
```

This is a **proxy**, not a claim that the stock was untradeable all day.

Intraday confirmation belongs later.

## 15.3 Circuit-Locked EP Family

When T5 is built later:

> Circuit-dominated EPs must be treated as a separate setup family.

Do not impute ordinary `close_loc` semantics to a day whose price path was mechanically constrained.

---

# 16. Series / Trade-to-Trade Handling

Preserve every observed series.

For primary research eligibility:

```text
series == EQ
```

at the decision timestamp unless a later strategy explicitly permits another series.

Periods in:

```text
BE
BZ
or other trade-to-trade / surveillance series
```

remain in raw history but are not silently treated as ordinary EQ sessions.

Create:

```text
series_changed_today
days_since_series_change
```

for later research diagnostics.

---

# 17. Point-in-Time Index Membership

Schema:

```text
index_id
security_id
effective_from
effective_to
membership_source
source_document_date
source_file_id
verified
```

Required index IDs:

```text
NIFTY_50
NIFTY_500
NIFTY_MIDCAP_150
NIFTY_SMALLCAP_250
```

Sector indices can be added as separate rows.

## 17.1 Reconstruction Rule

A membership is active on date `t` only if:

```text
effective_from <= t <= effective_to
```

No current-membership backfill.

## 17.2 R0 Blocker

If PIT Nifty 500 membership coverage is incomplete enough to alter breadth materially:

```text
r0_status = BLOCKED_MEMBERSHIP
```

Do not substitute the current Nifty 500 list.

A separate clearly named research proxy may be built, but it may not be called canonical R0.

---

# 18. Daily Research Universe

The warehouse stores broad NSE history.

The **tradable research universe** is a separate daily table.

## 18.1 Primary Membership Logic

A security is a primary candidate if it is:

```text
current member of Nifty Midcap 150
OR
current member of Nifty Smallcap 250
OR
was a member of either during the prior 12 months
```

using PIT membership.

Optional research tail:

```text
other Nifty 500 / Total Market securities
```

that pass liquidity.

## 18.2 Exclusions

Default exclusion flags:

```text
ETF
REIT / InvIT
SME
suspended
non-EQ series
price < ₹30
known data corruption
unsupported corporate-action discontinuity
```

Do not physically delete excluded securities.

Store flags so exclusions can be audited.

---

# 19. Liquidity Fields

Compute, point-in-time:

```text
median_volume_20
median_traded_value_20
adv_value_20
median_range_pct_20
spread_proxy_20
```

Primary gates from the frozen strategy spec:

```text
median daily traded value >= ₹8 crore
median daily volume >= 100,000 shares
median spread proxy <= 25 bps
price >= ₹30
```

The gate is stored as:

```text
liquidity_pass_v1
```

along with each component.

Do not use current liquidity to decide whether a 2018 trade was eligible.

---

# 20. Shared Daily Feature Layer

Phase 0 computes only shared deterministic primitives needed immediately or by T1/T5.

## 20.1 Moving Averages

```text
sma_10
sma_21
sma_50
sma_150
sma_200
ema_10
ema_21
```

Use `close_struct_adj`.

## 20.2 ATR

Use standard True Range on structural-adjusted OHLC:

```text
TR_t = max(
    high_t - low_t,
    abs(high_t - close_t-1),
    abs(low_t - close_t-1)
)
```

Then:

```text
atr_14
atrp_14 = atr_14 / close_struct_adj
```

Freeze the smoothing implementation in code and regression tests.

## 20.3 Returns

```text
ret_1
ret_5
ret_10
ret_20
ret_63
ret_126
ret_252
```

Point-in-time only.

## 20.4 Volume

```text
rvol_20 = volume_struct_adj / median(volume_struct_adj, prior 20 sessions)
rvol_50
```

Also retain traded-value normalization.

## 20.5 Delivery

Where available:

```text
delivery_pct
delivery_qty_z20
delivery_pct_z20
delivery_expand
```

## 20.6 Highs / Lows

```text
high_20
high_50
high_252
low_20
low_50
```

Use structural-adjusted prices.

## 20.7 Trend Flags

```text
stack_bull =
close > ema10 > ema21 > sma50 > sma200

stage2 =
close > sma200
AND sma200 slope over 50 sessions > 0
```

Do not yet tune strategy thresholds.

---

# 21. Relative Strength Foundation

Phase 0 stores enough data for later T1/T5 work.

For stock `i` vs benchmark `b`:

```text
rs_ratio = close_i / close_b
```

Compute:

```text
rs_ratio_nifty
rs_ratio_sector
rs_slope_20
rs_slope_63
```

Cross-sectional `rs_rank` must use only the universe active on that date.

If sector mapping is not point-in-time reliable, mark sector-relative fields unavailable rather than using today's sector classification retroactively without disclosure.

---

# 22. R0 Regime Classifier — Frozen v1

R0 is deterministic.

Primary breadth universe:

```text
PIT Nifty 500
```

Primary trend index:

```text
Nifty Midcap 150
```

## 22.1 Inputs

For every date:

```text
pct_above_20
pct_above_50
pct_above_200
nh_nl_20

mid150_close
mid150_sma50
mid150_sma200
mid150_sma50_slope_20

nifty50_close
nifty50_sma50
nifty50_sma200

india_vix
vix_z_252

nifty_realized_vol_20
nifty_realized_vol_median_252
```

## 22.2 Breadth

For every active PIT Nifty 500 constituent with sufficient history:

```text
above_200_i = close_i > sma200_i
```

Then:

```text
pct_above_200 =
count(above_200_i == true) /
count(valid_200d_constituents)
```

Store denominator:

```text
breadth_valid_n
breadth_membership_n
breadth_coverage = breadth_valid_n / breadth_membership_n
```

If breadth coverage falls below:

```text
0.90
```

default:

```text
r0_status = BLOCKED_INSUFFICIENT_BREADTH
```

Do not calculate a confident regime from half a universe.

## 22.3 Midcap Trend

Freeze:

```text
mid150_sma50_rising =
mid150_sma50_t > mid150_sma50_t_minus_20_sessions

mid150_sma50_falling =
mid150_sma50_t < mid150_sma50_t_minus_20_sessions
```

## 22.4 Raw Label

```text
BULL if:
    mid150_close > mid150_sma50
    AND mid150_sma50_rising
    AND pct_above_200 >= 0.60

BEAR if:
    mid150_close < mid150_sma50
    AND mid150_sma50_falling
    AND pct_above_200 <= 0.40

otherwise:
    CHOP
```

No ML.

No discretionary override.

## 22.5 Hysteresis

Require three consecutive sessions in a new raw state before changing final regime.

State machine:

```text
raw_regime != final_regime
        │
        ▼
pending_regime = raw_regime
pending_count += 1
        │
        ├── count < 3 → keep final_regime
        │
        └── count == 3 → switch final_regime
```

If raw label changes before count reaches three:

```text
pending_count = 1
pending_regime = new raw label
```

## 22.6 R0 Output

```text
trade_date
raw_regime
regime
regime_age_sessions

pending_regime
pending_count

pct_above_20
pct_above_50
pct_above_200
breadth_valid_n
breadth_membership_n
breadth_coverage

mid150_close
mid150_sma50
mid150_sma50_slope_20

nh_nl_20
vix_z_252
nifty_realized_vol_20
nifty_realized_vol_median_252

regime_confidence
r0_status

available_at
build_version
```

## 22.7 Regime Confidence

`regime_confidence` is **diagnostic only** in Phase 0 and cannot gate trades.

Freeze a transparent distance score rather than model confidence.

Example:

```text
bull_breadth_strength =
clip((pct_above_200 - 0.50) / 0.20, 0, 1)

bear_breadth_strength =
clip((0.50 - pct_above_200) / 0.20, 0, 1)
```

Combine only with matching Midcap trend direction.

For CHOP:

```text
chop_confidence =
1 - max(bull_confidence, bear_confidence)
```

This field is for diagnostics/UI only.

---

# 23. R0 QA

Required tests:

## 23.1 No Lookahead

No constituent membership after date `t`.

No future price.

No full-sample z-score.

## 23.2 Hysteresis

Test synthetic sequences:

```text
B B B → switches to BULL
B C B → does not switch
BEAR BULL BULL BULL → switches only on third BULL
```

## 23.3 Flip Count

Report:

```text
regime_flips_per_year
```

If:

```text
>12/year
```

flag R0 for review per the parent strategy spec.

Do not optimize thresholds merely to reduce flips after observing strategy returns.

---

# 24. Cost Model — Phase 0

The cost engine is separate from market data.

Every backtest later calls the same function.

## 24.1 Cost Profiles

Maintain effective-dated profiles.

At minimum:

```text
CONSERVATIVE_RESEARCH_V1
```

The constants below are research assumptions inherited from the frozen strategy specification. They are **not a claim about the exact statutory fee schedule on every historical date**.

Recommended configurable defaults:

```text
brokerage_plus_gst_roundtrip_bps = 10
stt_delivery_roundtrip_bps       = 20
exchange_sebi_stamp_roundtrip_bps = 4
```

Also store low/high sensitivity values matching the original ranges.

## 24.2 Impact

Frozen v1 impact function from the strategy specification:

```text
impact_side_bps =
min(
    15,
    8 * (order_value / adv_value)
)
```

Apply on each side.

Store:

```text
participation_rate = order_value / adv_value
```

## 24.3 Gap-Entry Slippage

Phase 0 supports the field but T5 later decides when to apply:

```text
gap_entry_extra_bps = 10–25
```

No strategy-specific value is selected during Phase 0.

## 24.4 Circuit Exit Rule

If an exit would be required while the security is effectively non-executable at a limit:

```text
do not assume fill
```

Daily-only Phase 0 cannot perfectly reconstruct order-book availability.

Therefore store circuit state and require later execution simulators to distinguish:

```text
normal
limit_touch
limit_close
lock_proxy
```

---

# 25. Actual Costs vs Research Costs

Keep two concepts separate.

```text
RESEARCH COST MODEL
conservative fixed assumptions for honest comparison

ACTUAL HISTORICAL CHARGE MODEL
effective-dated statutory / broker schedule
```

Phase 0 requires the first.

The second can be added later without changing strategy labels.

This prevents endless fee-table work from blocking the first scientific tests.

---

# 26. Data Availability Ledger

Every source needs an availability record.

Schema:

```text
source_name
trade_date
expected
first_poll_at
first_success_at
last_success_at
file_hash
file_size
status
```

Status:

```text
ON_TIME
LATE
MISSING
REVISED
REPLACED
```

## 26.1 Why This Matters

A field can be associated with trade date T while not being public until after the intended decision timestamp.

The warehouse must distinguish:

```text
event/effective date
```

from:

```text
information availability time
```

Without that distinction, later AI tests can leak simply by using an EOD file too early.

---

# 27. Daily Ingestion Workflow

Suggested operational sequence:

```text
MARKET CLOSE
    │
    ▼
START EOD POLLING
    │
    ├── bhavcopy
    ├── security master
    ├── delivery
    ├── price bands
    ├── index data
    └── VIX
    │
    ▼
RAW ARCHIVE + HASH
    │
    ▼
PARSE TO BRONZE
    │
    ▼
RUN QA
    │
    ├── pass → canonical
    │
    └── fail → quarantine
    │
    ▼
BUILD SILVER TABLES
    │
    ▼
BUILD GOLD FEATURES
    │
    ▼
BUILD R0
    │
    ▼
EMIT QUALITY REPORT
```

## 27.1 Retry Policy

Use configurable polling/retry.

Example operational default:

```text
start after market close
retry every 15 minutes
stop same-day retries at configured cutoff
retry again next morning
```

Do not encode a fictitious promise that every NSE file exists at exactly 15:45.

The availability ledger will teach us the real release distribution.

---

# 28. Backfill Workflow

Backfill must be restartable and idempotent.

Pseudo-command:

```bash
python -m src.cli.backfill \
    --from 2016-01-01 \
    --to 2026-08-29 \
    --sources all
```

For each date:

```text
download if raw hash absent
parse
validate
canonicalize
build identity joins
build corporate-action state
build delivery state
build price-band state
```

Do not calculate rolling gold features until the silver history has passed basic coverage checks.

---

# 29. Date-Aware Parser Registry

The source format changes over time.

Implement:

```python
PARSER_REGISTRY = {
    "cm_bhavcopy": [
        (date_start_legacy, date_end_legacy, LegacyCMBhavcopyParser),
        (date_start_udiff, None, UDiffCMBhavcopyParser),
    ],
}
```

Every bronze row stores:

```text
parser_name
parser_version
```

A parser change therefore does not silently rewrite history.

---

# 30. Source Manifest

Every raw file gets a manifest row:

```text
file_id
source_name
report_name
trade_date
original_filename
local_path
sha256
byte_size
downloaded_at
first_seen_at
parser_version
source_tier
```

If an official source later republishes the same date with a different hash:

```text
status = REVISED
```

Keep both versions.

Do not overwrite the first-seen file.

---

# 31. Build Manifest

Every transformation run stores:

```text
build_id
git_commit
config_hash
input_manifest_hash
started_at
completed_at
status
output_hash
```

This is what allows an old backtest to be reconstructed instead of merely remembered.

---

# 32. Data Quality Framework

Severity:

```text
BLOCKER
ERROR
WARN
INFO
```

## 32.1 BLOCKER Examples

- duplicate `security_id + trade_date`
- impossible OHLC
- PIT membership unavailable for R0 breadth
- missing benchmark index
- future-dated membership used
- adjustment factor changes price history without audit record
- feature timestamp after decision timestamp
- same source date parsed by conflicting schema without resolution

## 32.2 ERROR Examples

- delivery qty > traded qty
- price-band file says 5% but computed band appears inconsistent
- unexplained 50% overnight move with no corporate action or circuit context
- missing 20+ consecutive sessions for an active liquid security

## 32.3 WARN Examples

- delivery missing for one session
- price-band source missing but reconstructable
- short series-change gap
- source revised after first publication

---

# 33. Core QA Assertions

## 33.1 Daily Price

```python
assert high >= open
assert high >= close
assert low <= open
assert low <= close
assert high >= low
assert volume >= 0
```

## 33.2 Delivery

```python
assert deliverable_qty >= 0
assert deliverable_qty <= traded_qty
assert 0 <= delivery_pct <= 100
```

## 33.3 Identity

```python
assert one active point-in-time identity
       per security/exchange/series/date
```

## 33.4 Membership

```python
assert membership_effective_from <= trade_date
assert trade_date <= membership_effective_to
```

## 33.5 Features

```python
assert max(source_available_at) <= feature_timestamp
```

## 33.6 R0

```python
assert breadth_coverage >= 0.90
```

otherwise:

```text
R0 BLOCKED
```

---

# 34. Corporate-Action Discontinuity Test

For each extreme raw return:

```text
abs(raw_ret_1) >= 20%
```

check:

```text
corporate action?
price-band event?
series transition?
listing/relisting?
data error?
```

Every such move should have a reason code.

Suggested output:

```text
EXTREME_MOVE_CA
EXTREME_MOVE_CIRCUIT
EXTREME_MOVE_LISTING
EXTREME_MOVE_REAL
EXTREME_MOVE_UNKNOWN
```

Unknown large moves become a review queue before T5 labels are created.

---

# 35. Daily Panel Grain

The canonical panel grain is:

```text
one row
per
security_id × trading session
```

Do not create artificial rows for non-trading securities.

Use explicit status fields:

```text
traded_today
suspended
series_active
```

Rolling calculations must decide how to treat non-trading sessions rather than assuming a zero return.

---

# 36. Missing-Data Policy

Never generic-forward-fill OHLCV.

## Allowed

- effective-dated metadata carried within its known validity period
- prior corporate-action state
- membership until explicit effective end date
- static config

## Forbidden

- missing price
- missing delivery
- missing VIX
- missing index close
- unknown circuit band
- unknown future membership

Missing inputs produce:

```text
NULL + quality flag
```

not invented data.

---

# 37. Point-in-Time Universe Table

Schema:

```text
trade_date
security_id

in_nifty500
in_midcap150
in_smallcap250
was_mid_or_small_last_12m

series_eq
liquidity_pass_v1
price_pass_v1
circuit_history_pass_v1
data_quality_pass

primary_universe_pass
exclusion_reason
```

This table is the only source strategies may use for historical eligibility.

---

# 38. Circuit History Gate

From the parent specification:

```text
not frozen on a 5% band
for >=3 of last 5 sessions
```

Phase 0 cannot perfectly know “frozen” from daily bars, so create both:

```text
five_pct_band_close_count_5
five_pct_lock_proxy_count_5
```

Later strategy code must name which proxy it uses.

Do not collapse a probabilistic daily proxy into a definitive `frozen=true` label.

---

# 39. Surveillance / ASM / GSM

Where official historical surveillance indicators can be ingested reliably, store them point-in-time:

```text
asm_stage
gsm_stage
surveillance_flag
effective_from
effective_to
```

If historical coverage is incomplete:

- preserve what is known,
- mark unknown dates,
- do not backfill today's surveillance status.

Phase 0 should make the field available without making incomplete surveillance history a blocker for the initial T1/T5 research unless the frozen strategy gate explicitly requires it.

---

# 40. R0 Diagnostic Report

Generate after every full rebuild.

Required charts/tables later may include:

```text
date
regime
pct_above_200
Midcap150 vs SMA50
regime flips
VIX z-score
breadth coverage
```

Required summary:

```text
BULL days %
BEAR days %
CHOP days %
flips/year
longest regime duration
blocked dates
```

This is validation, not performance analysis.

Do not examine strategy returns while tuning R0 during Phase 0.

---

# 41. Cost-Model Unit Tests

Test deterministic examples.

Example:

```text
order_value = ₹100,000
ADV = ₹10,000,000
participation = 1%
```

Expected impact:

```text
8 * 0.01 = 0.08 bps per side
```

subject to the v1 cap.

Also test:

- zero ADV → trade invalid
- negative ADV → invalid
- missing ADV → no simulated trade
- very large participation → capped impact
- costs never negative

---

# 42. Availability-Time Tests

Construct fixture:

```text
trade date: 2026-08-20
delivery first seen: 2026-08-20 18:10 IST
decision: 2026-08-20 15:30 IST
```

Expected:

```text
delivery feature unavailable
```

For next-day open decision:

```text
delivery feature available
```

This test should exist before any EP model is trained.

---

# 43. Leakage Test Suite

Create a dedicated `tests/leakage/`.

Tests should deliberately insert future information and confirm rejection.

Examples:

```text
future index membership
future corporate action factor
delivery file with late available_at
full-sample RS percentile
future symbol mapping
post-event circuit state
```

Build must fail if these appear in a decision-time feature.

---

# 44. Regression Fixtures

Freeze a small basket of known securities and dates.

Suggested categories:

```text
normal liquid stock
symbol-change stock
split event
bonus event
large dividend
5% circuit stock
20% circuit stock
F&O stock
IPO
BE/EQ series transition
delivery-missing day
```

For each fixture, store expected canonical rows.

Any parser or adjustment change must pass these.

---

# 45. Phase 0 Work Packages

## P0.1 — Repository + Config + Manifests

Deliver:

- repo skeleton
- config hashing
- source manifest
- build manifest
- CLI
- logging
- pytest scaffold

Acceptance:

```text
raw file can be archived and reproduced by hash
```

---

## P0.2 — Security Identity + Calendar

Deliver:

- trading calendar
- security master history
- symbol/series history
- continuity mapping framework

Acceptance:

```text
historical date resolves correct symbol + series
```

---

## P0.3 — Daily Market Data

Deliver:

- legacy bhavcopy adapter
- UDiFF bhavcopy adapter
- silver daily security table
- OHLCV QA

Acceptance:

```text
2016→latest backfill
coverage report
no duplicate date/security
```

---

## P0.4 — Delivery

Deliver:

- MTO parser
- canonical delivery table
- delivery z-score primitives
- availability ledger

Acceptance:

```text
delivery coverage quantified
late-data logic tested
```

---

## P0.5 — Corporate Actions + Adjustments

Deliver:

- CA ingestion
- normalized taxonomy
- split/bonus/consolidation factors
- manual-review queue
- raw vs structural-adjusted price

Acceptance:

```text
known split/bonus fixtures show continuous adjusted charts
raw series remains untouched
```

---

## P0.6 — Price Bands + Circuits

Deliver:

- price-band ingestion
- daily band state
- touch/close/lock proxies
- F&O dynamic-band distinction

Acceptance:

```text
known limit days correctly classified
no claim of full-session lock from OHLC alone
```

---

## P0.7 — Index Prices + PIT Membership

Deliver:

- Nifty 50
- Midcap 150
- Smallcap 250
- Nifty 500
- VIX
- PIT index membership

Acceptance:

```text
R0 breadth can be calculated without current-member survivorship
```

---

## P0.8 — Shared Features + Universe

Deliver:

- rolling MAs
- ATR
- returns
- RVOL
- delivery features
- highs/lows
- liquidity
- daily universe table

Acceptance:

```text
all rolling features point-in-time
```

---

## P0.9 — R0

Deliver:

- raw label
- 3-day hysteresis
- audit fields
- coverage gate
- flip report

Acceptance:

```text
one deterministic R0 row per valid session
```

---

## P0.10 — Cost Engine

Deliver:

- conservative research profile
- impact function
- participation
- effective-dated config model

Acceptance:

```text
same trade input always produces same cost output
```

---

## P0.11 — Full QA + Freeze

Deliver:

- coverage dashboard/report
- leakage test suite
- regression fixtures
- rebuild hashes
- Phase 0 release tag

Acceptance:

```text
PHASE0_DATA_V1
```

can be frozen and used by T1/T5 without editing raw history.

---

# 46. Dependency Order

```text
P0.1 Repo / manifests
      │
      ▼
P0.2 Identity + calendar
      │
      ▼
P0.3 Daily market data
      │
      ├──────────────┬───────────────┐
      ▼              ▼               ▼
P0.4 Delivery    P0.5 Corp Acts   P0.6 Circuits
      │              │               │
      └──────────────┴──────┬────────┘
                            ▼
                  P0.7 Indices / PIT
                            │
                            ▼
                   P0.8 Features
                            │
              ┌─────────────┴────────────┐
              ▼                          ▼
           P0.9 R0                  P0.10 Costs
              │                          │
              └─────────────┬────────────┘
                            ▼
                       P0.11 FREEZE
```

---

# 47. CLI Contract

Suggested commands:

```bash
# Ingestion
python -m src.cli.ingest --source cm_bhavcopy --date 2026-08-20
python -m src.cli.ingest --source delivery --date 2026-08-20

# Backfill
python -m src.cli.backfill --from 2016-01-01 --to 2026-08-29

# Canonical build
python -m src.cli.build-silver --date 2026-08-20

# Features
python -m src.cli.build-features --date 2026-08-20

# Regime
python -m src.cli.build-r0 --date 2026-08-20

# Quality
python -m src.cli.qa --date 2026-08-20
python -m src.cli.qa --from 2016-01-01 --to 2026-08-29

# Full deterministic rebuild
python -m src.cli.rebuild --date 2026-08-20
```

---

# 48. Configuration Freeze

Example `phase0.yaml`:

```yaml
timezone: Asia/Kolkata
history_start: 2016-01-01

breadth:
  index: NIFTY_500
  min_coverage: 0.90

r0:
  bull_breadth: 0.60
  bear_breadth: 0.40
  sma_window: 50
  slope_sessions: 20
  hysteresis_sessions: 3

liquidity:
  min_median_value_20_cr: 8
  min_median_volume_20: 100000
  max_spread_proxy_bps: 25
  min_price: 30

costs:
  profile: CONSERVATIVE_RESEARCH_V1
  brokerage_gst_rt_bps: 10
  stt_delivery_rt_bps: 20
  exchange_sebi_stamp_rt_bps: 4
  impact:
    slope_bps: 8
    cap_bps_each_side: 15
```

Any change after Phase 0 freeze requires a version bump.

---

# 49. Data Versioning

Release naming:

```text
PHASE0_DATA_V1.0.0
```

Semantic intent:

```text
MAJOR
historical interpretation changes
e.g. adjustment methodology

MINOR
new source/field added without changing existing meaning

PATCH
parser/data repair that preserves schema meaning
```

Every backtest records:

```text
data_release
git_commit
strategy_spec_version
config_hash
```

---

# 50. What Phase 1 Is Allowed to Assume

After Phase 0 is frozen, T1 may assume:

- point-in-time universe exists
- daily OHLCV is canonical
- adjusted prices are available
- delivery is timestamp-safe
- liquidity is point-in-time
- R0 exists
- sector/index history exists
- costs are callable
- circuit state is available
- corporate-action false signals are identifiable

T1 may **not** change Phase 0 history to improve a backtest.

If T1 discovers a data defect, repair it as a Phase 0 data-version change and rerun all affected research.

---

# 51. What Phase 2 Is Allowed to Assume

T5 additionally requires:

- raw gap-safe prices
- corporate-action event flags
- circuit-family flags
- delivery shocks
- EP event timestamps derived only from completed daily data
- structural-adjusted pre-event features
- next-open cost model

Intraday data is not required for the first T5 champion.

---

# 52. Stop Conditions

Stop Phase 0 and repair before moving on if any of these occur:

```text
PIT Nifty 500 membership cannot be reconstructed reliably
```

or:

```text
corporate-action adjustments create unexplained discontinuities
```

or:

```text
delivery history is too sparse to support claimed historical features
```

or:

```text
security identity cannot survive symbol/series changes
```

or:

```text
rebuilds are non-deterministic
```

or:

```text
feature availability timestamps are not enforceable
```

The project does not solve these by hoping the backtest averages them out.

---

# 53. Phase 0 Acceptance Checklist

## Market Truth

- [ ] Immutable raw archive exists
- [ ] SHA256 manifest populated
- [ ] Legacy and UDiFF bhavcopy adapters pass
- [ ] Security identity is effective-dated
- [ ] Symbol/series history preserved
- [ ] Trading calendar complete
- [ ] Corporate actions ingested
- [ ] Structural adjustment factors auditable
- [ ] Delivery parsed and timestamped
- [ ] Price bands ingested
- [ ] Circuit proxies explicitly named as proxies
- [ ] F&O dynamic-band distinction present
- [ ] Index prices complete
- [ ] PIT membership reconstructed
- [ ] No current-membership survivorship

## Features

- [ ] MAs point-in-time
- [ ] ATR point-in-time
- [ ] returns point-in-time
- [ ] RVOL point-in-time
- [ ] delivery z-scores point-in-time
- [ ] liquidity fields point-in-time
- [ ] RS foundation built
- [ ] universe eligibility generated daily

## R0

- [ ] breadth uses PIT Nifty 500
- [ ] breadth denominator stored
- [ ] <90% coverage blocks R0
- [ ] Midcap 150 SMA50 slope uses prior 20 sessions
- [ ] raw labels deterministic
- [ ] hysteresis unit-tested
- [ ] regime flips/year reported
- [ ] confidence is diagnostic only

## Costs

- [ ] conservative profile frozen
- [ ] impact function unit-tested
- [ ] ADV participation stored
- [ ] no trade simulated with missing ADV
- [ ] circuit execution is not assumed

## Audit

- [ ] source manifest
- [ ] build manifest
- [ ] availability ledger
- [ ] QA report
- [ ] leakage tests
- [ ] regression fixtures
- [ ] deterministic rebuild hashes
- [ ] release tagged `PHASE0_DATA_V1.0.0`

---

# 54. Phase 0 Release Gate

Only after every required checklist item passes:

```text
PHASE 0
   │
   ▼
DATA FREEZE
   │
   ▼
PHASE 1 — T1 CHAMPION
   │
   ▼
PHASE 2 — T5 CHAMPION
   │
   ▼
PHASE 2.5 — L1.5 EP ANALOGUES
   │
   ▼
FIRST MOMENT OF TRUTH
```

No learned model should be trained before this gate.

---

# 55. Research Constitution Reminder

> **Deterministic scores are the champion. Learned representations are guilty until proven useful. Analogues are a user interface on a space that has already been shown to rank outcomes. Execution never listens to a vibe.**

Phase 0 exists to make that sentence enforceable in code.

---

# Appendix A — Current Source Notes

As verified during preparation of this specification:

- NSE currently publishes a **CM-UDiFF Common Bhavcopy Final** report, and the older common bhavcopy was discontinued in 2024. The ingestion system therefore requires date-aware legacy/UDiFF adapters.
- NSE's daily reports continue to expose **Security-wise Delivery Positions**.
- NSE exposes an **MII Security File** for listed capital-market securities.
- Official NSE price-band documentation distinguishes static 2%, 5%, 10%, and 20% bands and different treatment for derivative-eligible securities.
- NSE's historical-report area exposes historical index data and India VIX data.
- Corporate actions are available through NSE's corporate-action reporting interface.

Exact web routes should live only in `config/sources.yaml`, not be scattered through transformation code.

---

# Appendix B — First Engineering Ticket

The first ticket should **not** be “download ten years of prices.”

It should be:

## `P0.1 — Build immutable source archive + manifest`

Acceptance:

1. Download one chosen NSE report for one date.
2. Preserve original filename.
3. Save raw bytes unchanged.
4. Calculate SHA256.
5. Record `downloaded_at` and `first_seen_at`.
6. Parse into bronze without modifying raw.
7. Rerun and prove idempotence.
8. Change the raw file and prove the hash/version system detects it.

Once that works, scaling ingestion is mechanical.

Without it, ten years of downloads merely creates a larger pile of files whose provenance nobody can prove.
