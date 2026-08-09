# Reactor Scale Reverse-Engineering Audit

**Date:** 2026-07-14  
**Score source:** `C:\Users\satta\Downloads\DEMO SHEET - MARCH APRIL - Sheet1.csv`  
**Method source:** `REACTOR_SMART_MONEY_SOURCE_EXTRACT_2026-07-14.md`  
**Purpose:** decide whether sat10ic os can faithfully reproduce and correctly use
the supplied direction-neutral unusual-activity scale from local NSE data.

## Final full-panel verdict (current)

**Certain:** exact reconstruction from official daily bhavcopy fields was not
achieved. The bounded search now covers 53,280 matched score cells, 1,478 symbols
and all 37 dates using 162 validated official NSE sessions from 2024-09-02 through
2025-04-29. It tested more than 7,500 parsimonious configurations across rolling
means/medians/EMAs, inclusive and prior baselines, volume and trade-count ratios,
delivery quantity and percentage, order-size proxies, ADR/range, component
rounding, products, powers, z-scores and daily cross-sectional normalisation.

The strongest full-panel candidate is:

```text
q = today's average trade quantity / inclusive 20-session mean
d = today's delivery percentage / prior 19-session mean

score = 1.1048768252*q
      + 1.0099667732*d
      + 1.1730986222*(q*d)^0.825
      - 0.14
```

After rounding to two decimals it reproduces 6,572 of 53,280 cells exactly
(12.3348%). Its mean absolute error is 0.1324, median absolute error is 0.0364,
56.1280% of cells are within 0.05 and the maximum miss is 16.2113. A second,
standard-library verifier using Decimal `ROUND_HALF_UP` and `math.fsum` reproduced
the exact count and mean error independently.

That is a useful transparent analogue, but it is not the source formula. The
public Google workbook contains zero formula cells, the public site describes only
"Volume Footprint + ADR logic," and the supplied transcript says the owner declines
to disclose the proprietary calculation. The transcript's mechanism also refers
to catching an unusually large individual order/quantity. Daily bhavcopy exposes
total quantity and trade count, but not individual trade sizes or maximum order
quantity.

**Certain:** ordinary price-range ADR is not the missing EOD term in the tested
panel. The best literal Volume+ADR pair has an ADR coefficient of only 0.0167 and
reproduces 1.9956% exactly. Across all permitted ADR variants, the largest absolute
Pearson correlation with the best formula's residual is only 0.0433. The local
SwingEdge V2.2 analogue (40% volume, 35% range/ATR, 25% efficiency, then x2.2)
reproduces only 0.3814% and cannot produce the source values above its theoretical
maximum of 11; the CSV reaches 44.4.

### Evidence of a source/data discontinuity

The EOD relationship changes abruptly within the supplied sheet:

| Source period | Best period-specific exact share | Mean absolute error | Within 0.05 |
|---|---:|---:|---:|
| 2025-03-03 to 2025-03-19 | 2.0390% | 0.2532 | 16.1564% |
| 2025-03-20 to 2025-03-25 | 4.2398% | 0.1630 | 30.5995% |
| 2025-03-26 to 2025-04-29 | 21.8029% | 0.0259 | 87.7710% |

**Likely:** the publisher changed either the calculation or its upstream footprint
feed around 2025-03-20/26. This is an inference from the abrupt error break, not a
disclosed source fact. Fitting each period separately does not recover the early
block, so a versioned EOD formula still cannot clone the sheet.

Near-identical permitted inputs can also have materially different source scores.
For example, MAHSCOOTER on 2025-03-10 and KIRLPNU on 2025-04-22 have average-trade-
quantity ratios of 1.197662 and 1.197730, delivery ratios of 1.228552 and 1.228859,
and range/ADR ratios of 0.800311 and 0.798546, yet their supplied scores are 3.03
and 4.05. This is consistent with a missing footprint field or a source-version
change.

### Implementation decision

Do not ship any recovered formula as "Reactor Scale" or claim exact fidelity.
The defensible sat10ic implementation is a separately named, versioned
**EOD abnormal-activity analogue** based primarily on average/deliverable quantity
per trade, with its raw inputs shown. It must remain direction-neutral and be
validated for usefulness independently of similarity to this proprietary sheet.
Exact cloning requires the publisher's formula or the same order/tick-level
footprint feed used to create the source scores.

## Superseded initial six-date verdict

The following section records the earlier limited-history probe for audit history.
It is superseded by the full 162-session, all-date result above.

The transcript supplies the missing mechanism clue: the proprietary score is
described as detecting unusually large **quantity per order/trade relative to the
stock's normal activity**. That makes an EOD bhavcopy reconstruction materially
more feasible than the earlier delivery-heavy hypothesis suggested.

A five-feature transparent mimic now fits the overlapping source labels very
closely on a time split, but this is still a **near-clone, not an exact clone**.
Only six source dates currently have complete causal prior-20-session bhavcopy
features, and only the last two of those dates are held out. The original formula
also remains undisclosed.

The product must use two distinct stages:

1. **Reactor / Volume Footprint analogue:** detect abnormal activity without
   assigning buy or sell direction.
2. **Fixed Range Volume Profile:** use POC, VAH and VAL, together with price/volume
   response and higher-timeframe structure, to interpret direction and execution.

Do not label POC/VAH/VAL as Reactor components and do not label the EOD mimic as
the publisher's proprietary score until exact reproduction is demonstrated.

## Source profile

The score CSV contains:

- 1,627 unique NSE symbols;
- 37 dated score columns from 2025-03-03 through 2025-04-29;
- 55,613 populated scores out of 60,199 possible symbol-date cells;
- symbol, index bucket, sector, industry and segment metadata;
- no OHLCV, ADR, order-size component, formula or direction label.

The supplied score distribution has a median of 2.91. It contains 13,475 values
above 3.5, 332 values at or above 8, and a maximum value of 44.4. These are source
observations, not evidence that any threshold predicts future returns.

The transcript extraction is frozen separately with line-level provenance and a
SHA-256 checksum. Its critical direct claim is that the score reports activity,
not direction; accumulation and distribution are both possible.

## Local NSE inputs and their limits

`manas_os/data/manas.db.daily_prices` supplies daily:

- OHLC and previous close;
- total traded quantity and turnover;
- number of trades;
- delivery quantity and delivery percentage;
- source and ingest timestamps.

The raw bhavcopy fields include `TTL_TRD_QNTY`, `TURNOVER_LACS`,
`NO_OF_TRADES`, `DELIV_QTY` and `DELIV_PER`. They permit two unusually useful EOD
proxies:

```text
average trade quantity = total traded quantity / number of trades
average trade value    = turnover / number of trades
```

They do **not** reveal the largest individual order, buyer/seller aggressor,
volume-at-price, footprint delta or participant identity. “Institutional” remains
an interpretation, not an observable fact in this dataset.

The original database coverage began on 2025-03-19. This audit downloaded and
validated 162 official full-universe NSE bhavcopy sessions from 2024-09-02 through
2025-04-29, including enough causal history for all 37 supplied score dates. The
download manifest contains 162 valid trading sessions, 10 verified market-closed
dates and zero failures. Its date validator rejected NSE holiday URLs that served
a prior session under the requested URL rather than writing a misdated file.

The canonical files are present under `data/bhavcopy`. Database ingestion remains
pending because the live `python run_manas_cli.py run-eod` writer (PID 4160 at the
time of this audit) holds the SQLite write lock. The audit did not terminate or
interfere with that live job; all formula research reads the validated official
files directly.

## Initial six-date probe (superseded)

This section is retained to show how the hypothesis developed. Its 8,628-row
coverage and two-date holdout are superseded by the all-date results above.

The decisive feature is current average trade quantity divided by its own prior
20-session mean:

```text
avg_trade_qty_ratio20 =
    (today_volume / today_num_trades)
    / mean(previous_20_sessions(volume / num_trades))
```

Across the 8,628 complete symbol-date pairs, its Pearson correlation with the
supplied score is 0.8577 and its rank correlation is 0.8042. An independent
standard-library implementation reconstructed the same 8,628 pairs and produced
Pearson correlation 0.8577047119051358.

The main relationships on the same complete panel were:

| Causal EOD feature | Pearson | Spearman |
|---|---:|---:|
| Average trade quantity / prior-20 mean | 0.8577 | 0.8042 |
| Average trade value / prior-20 mean | 0.8215 | 0.7741 |
| Relative volume / relative trade count | 0.8397 | 0.7721 |
| Delivery percentage / prior-20 mean | 0.5965 | 0.6136 |
| Delivery quantity / prior-20 mean | 0.5422 | 0.6030 |
| Relative volume | 0.2036 | 0.3949 |
| ADR20 alone | -0.0582 | -0.0664 |

This supersedes the preliminary inference that delivery percentage was the primary
score driver. Delivery remains useful, but abnormal average trade size is much
closer to both the transcript description and the supplied labels.

## Transparent near-clone test

The lean model uses only:

- average trade quantity / its prior-20 mean;
- average trade value / its prior-20 mean;
- delivery percentage / its prior-20 mean;
- delivery quantity / its prior-20 mean;
- ADR20.

It trains through 2025-04-25 and tests only on 2025-04-28 and 2025-04-29:

| Result | Value |
|---|---:|
| Training rows | 5,732 |
| Held-out rows | 2,896 |
| Held-out mean absolute error | 0.0755 score points |
| Held-out R-squared | 0.9841 |
| Held-out rank correlation | 0.9910 |
| Recall for source scores above 3.5 | 0.9490 |

Mean absolute error, R-squared and threshold recall were recomputed by an
independent scalar calculation inside the harness and asserted equal to the
vectorised results. A second standalone program independently verified the key
single-feature correlation and pair count.

Exactness is materially weaker than the aggregate fit suggests:

| Held-out absolute-error band | Rows | Share of 2,896 rows |
|---|---:|---:|
| Exact after rounding to two decimals | 156 | 5.39% |
| Within 0.01 score points | 312 | 10.77% |
| Within 0.05 score points | 1,372 | 47.38% |
| Within 0.10 score points | 2,210 | 76.31% |
| Within 0.25 score points | 2,799 | 96.65% |
| Within 0.50 score points | 2,876 | 99.31% |

The median absolute error is 0.0525, the 95th-percentile error is 0.2110, and the
maximum is 1.8281. These counts and errors were independently recomputed by scalar
and vectorised routes. The model is therefore close enough to identify the score
family and approximate its ranking, but nowhere near the audit's exact two-decimal
reproduction gate.

Adding ADR20 to the single average-trade-quantity model changes almost nothing:
held-out mean absolute error remains 0.3287, and the fitted ADR coefficient is
-0.004936. ADR is useful for interpreting the *price response* and risk, but the
current evidence does not support ADR as the core scale driver.

The near-clone is strong evidence of the score's input family. It is not proof of
the exact proprietary formula: the feature ratios are collinear, the time sample
is narrow, and the untouched period is only two sessions.

## One-stock reconstruction: CSLFINANCE on 2025-04-29

This case follows the requested stock-by-stock method rather than relying only on
panel correlations.

| Source/input | Observed value |
|---|---:|
| Supplied Reactor score | 19.19 |
| OHLC | 335.00 / 335.00 / 308.00 / 322.15 |
| Total traded quantity | 307,118 |
| Number of trades | 1,361 |
| Average quantity per trade | 225.66 |
| Prior-20 average quantity per trade | 23.02 |
| Current/prior average-quantity ratio | 9.80x |
| Average trade value | ₹71,196.91 |
| Prior-20 average trade value | ₹6,485.60 |
| Current/prior average-value ratio | 10.98x |
| Delivery percentage | 94.46% |
| Prior-20 ADR | 6.63% |

The same symbol's source score was only 3.09 on the preceding session, when its
average-quantity ratio was 0.91x. This is direct case-level support for abnormal
average trade size as the main clue, while ADR changes little and therefore cannot
explain the score spike.

The five-feature model, trained only through 2025-04-25, estimates 21.02 for this
case versus the supplied 19.19, an absolute error of 1.83. The example is useful
precisely because it demonstrates both findings: the input family is very close,
but exact formula fidelity has not been reached.

## Volume Footprint and Volume Profile are separate

### Stage A — EOD Activity Reactor

Purpose: rank unusual participation without direction.

Candidate raw evidence:

- average trade quantity and its prior baseline;
- average trade value and its prior baseline;
- relative volume versus relative number of trades;
- delivery participation;
- persistence above the benchmark threshold;
- isolated extreme-spike state;
- corporate-action/data-quality flags.

Output states:

- abnormal activity, direction unresolved;
- persistent abnormal activity;
- isolated extreme activity;
- quarantined/corporate-action distorted;
- insufficient history.

### Stage B — Fixed Range Volume Profile

Purpose: interpret where value was accepted and whether price is accepting or
rejecting outside it.

- **POC:** the highest-volume price within the explicitly selected profile range.
  Price near it means acceptance/balance, not automatically accumulation.
- **VAL reaction:** a possible support/rejection event, not an automatic buy.
- **VAH break:** a possible continuation event, not an automatic breakout trade.
  Require acceptance above value, compatible structure/volume and invalidation.

POC, VAH and VAL depend on the chosen anchor range and the underlying bar
resolution. Every computed profile must therefore store start/end timestamps,
bar resolution, source, freshness and settings. The supplied transcript does not
state a universal value-area percentage or anchor algorithm.

Daily bhavcopy cannot reproduce a proper within-range volume-at-price profile.
Intraday bars can approximate it by allocating each bar's volume using a documented
method; true bid/ask footprint still requires trade/tick data.

### Stage C — Chart/debate interpretation

The chart reader receives both stages as evidence, never as a pre-written verdict.
It must state:

- higher-timeframe trend and market/theme context;
- whether activity looks like accumulation, distribution, absorption, exhaustion
  or remains unresolved;
- selected Fixed Range Volume Profile anchor and POC/VAH/VAL relationship;
- price response: acceptance, rejection, reclaim, failure or retest;
- execution lens, trigger, invalidation, stop structure and expected sequence;
- strongest contradictory evidence.

A high Reactor reading cannot silently override tradability, regime, liquidity,
portfolio heat or deterministic position sizing.

## Faithful sat10ic rebuild

### Data work

1. Official bhavcopy history is now validated back to 2024-09-02. Ingest it into
   SQLite after the active EOD writer releases the database lock; do not interrupt
   the live job merely to complete the backfill.
2. Preserve total quantity, turnover, trade count, delivery fields and raw source
   provenance without future-adjusted leakage.
3. Build split/bonus/corporate-action quarantine before scoring.
4. Backfill intraday bars for candidate profile ranges and record provider,
   completeness and bar resolution.
5. Keep EOD Reactor inputs and intraday Volume Profile inputs in separate canonical
   records.

### Research checks

1. The full-panel in-sample formula recovery is complete across all 37 dates; its
   current best is the explicitly recorded 12.3348%-exact analogue above.
2. Acquire the publisher's formula or equivalent order/tick-level footprint data
   before attempting another exact-clone claim. Repeating EOD coefficient searches
   cannot recover a variable that bhavcopy does not contain.
3. Test the separate sat10ic analogue's `>3.5` persistence and `>=8` spike cases.
4. Inspect analogue outcomes by liquidity, split status, sector and score magnitude.
5. Validate the analogue separately against future absolute movement, MFE/MAE and
   setup-conditioned outcomes; source-score mimicry is not alpha validation.
6. Publish a versioned sat10ic formula only after those alpha checks pass and label
   it as an analogue, not the proprietary Reactor Scale.

### UI contract

Each stock's activity panel shows:

- today's value, percentile, timestamp and model/formula version;
- a five-to-ten-session trail with persistence and spike states;
- raw average trade quantity/value, prior baselines and delivery context;
- permanent copy: “abnormal activity; direction not yet resolved”;
- corporate-action and missing-history warnings;
- Fixed Range Volume Profile chart with visible POC/VAH/VAL;
- visible anchor range, bar resolution, source and freshness;
- chart/debate conclusion with plain-English trigger and invalidation.

The UI must never render “price near POC = accumulation,” “VAL bounce = buy,” or
“VAH break = breakout trade” as unconditional rules. Those are candidate behaviours
that require price acceptance/rejection and context.

## Acceptance conditions

### Reverse-engineering search bar

Approximate ranking is not the finish line. Candidate formulas must be generated
from plausible NSE/footprint/ADR domain components and permutations—rolling
windows, mean/median/z-score baselines, volatility normalisation, delivery/trade
size interactions, transformations and explicit rounding—then ranked primarily
by exact two-decimal reproduction across many ticker-date cells in the supplied
CSV, using official bhavcopy data for those same dates. Recovering the sheet's
calculation is an in-panel reverse-engineering task; unseen-date/unseen-symbol
testing belongs to the later question of whether a recovered or analogous score
generalises and creates alpha, not to this formula-recovery gate.

The search must remain parsimonious and domain-grounded: primarily trade/volume
abnormality, delivery as a volume-related component, and ADR/range context. Search
rolling windows, baseline choices, transforms, interactions and rounding in loops,
but reject a many-factor black-box fit even when it reduces average error. Continue
until the supplied CSV scores are reproduced exactly or the available EOD fields
are proven insufficient by exhausted simple-domain candidates and residual evidence.

### Exact clone

Do not use that label until a frozen formula reproduces the supplied CSV cells to
two-decimal precision across its symbols and date blocks and preserves the source
persistence/spike classifications. The current analogue does not pass this
condition. Unseen-date and unseen-symbol testing is a later alpha/generalisation
gate, not a prerequisite for recovering a calculation from this fixed source panel.

### Functional analogue

A sat10ic-owned analogue can enter shadow mode after it:

- passes point-in-time and corporate-action leakage tests;
- beats plain ADR and relative-volume baselines on source-score reconstruction;
- is stable across dates, liquidity, sector and market-cap cohorts;
- demonstrates incremental future-path value beyond regime, RS and setup rank;
- distinguishes persistent activity, isolated spikes and unresolved direction;
- renders insufficient or stale inputs honestly.

## Reproducible artifacts

- `output/reactor_scale_audit/official_bhavcopy_manifest.json` — checksummed
  official-session download ledger.
- `output/reactor_scale_audit/domain_formula_search.py` — rolling baseline,
  coefficient and ADR residual search.
- `output/reactor_scale_audit/remaining_domain_search.py` — delivery-per-trade,
  turnover/trade, Volume+ADR and nonlinear search.
- `output/reactor_scale_audit/zscore_domain_search.py` — rolling z-score and
  same-day cross-sectional search.
- `output/reactor_scale_audit/exact_refine_nonlinear.py` — exponent and cent-level
  coefficient refinement for the best two underlying inputs.
- `output/reactor_scale_audit/period_formula_search.py` — early/transition/late
  formula-discontinuity test.
- `output/reactor_scale_audit/verify_final_reactor_search.py` — independent Decimal
  exact-count and `math.fsum` error verification.
- `output/reactor_scale_audit/final_reactor_search_verification.json` — passing
  independent verification record.
- `REACTOR_SMART_MONEY_SOURCE_EXTRACT_2026-07-14.md` — frozen transcript-derived
  doctrine with line provenance and source checksum.

## Required evidence for exactness

The older official history is now present and the all-date EOD search is complete.
The remaining shortest route is the original formula/component definitions or the
same order/tick-level footprint feed used by the publisher. Aggregate bhavcopy
cannot reveal the maximum individual order, participant identity, aggressor side
or a true order-flow footprint.

## Risks

- The source calculation/feed appears to change within the 37-date sheet; a single
  backfilled EOD formula may be structurally incapable of matching both blocks.
- Correlated quantity/value/delivery ratios can make coefficients unstable even
  when predictions fit well.
- Corporate actions and erroneous trade counts can create false extremes.
- Calling the analogue "smart money" would overstate what its EOD inputs observe.
- Approximate intraday Volume Profiles depend on anchor choice and volume-allocation
  method.
- Matching the proprietary labels does not establish tradable alpha; future,
  cost-aware outcomes remain a separate validation gate.

## 2026-07 current-screen extreme validation addendum

The four user-supplied current UI screenshots added 15 unambiguous selected-day
stock scores across 2026-07-01 and 2026-07-10, plus the visible previous-day,
four-day-average and ten-day-average fields. Reconstructing those aggregate fields
against the same bhavcopy sessions exposed a specific defect in v1: residual error
rose with the average-trade-quantity ratio. The high-end miss was therefore not a
generic clipping problem; the quantity leg was underweighted at extreme readings.

The separately versioned `sat10ic_eod_activity_v2` uses:

```text
1.165335*q + 1.04631*d + 1.152161*(q*d)^0.84 - 0.213928
```

where `q` is current average trade quantity divided by its inclusive 20-session
mean, and `d` is current delivery percentage divided by its prior-19-session mean.
The same formula was recomputed from persisted component ratios as an independent
arithmetic check; the largest persisted-versus-recomputed difference was 0.00.

On the 15 visible current-screen stock scores, v2 has mean absolute error 0.0767,
median absolute error 0.09, maximum absolute error 0.18, 11/15 readings within 0.10,
15/15 within 0.25, and 15/15 agreement at the 3.5 threshold. The extreme examples
are ETHOSLTD 22.76 versus 22.58, MAHLIFE 13.32 versus 13.42, TBOTEK 9.08 versus
8.95, URBANCO 8.91 versus 9.08, and MUKANDLTD 8.07 versus 8.16.

This improves the current-period analogue; it does not overturn the earlier exact-
clone failure across the full CSV. V2 remains shadow-only and direction-neutral.
The Stocks view also excludes date-matched unclassified instruments when the
canonical universe snapshot exists, then applies the existing probable-ETF guard;
this prevents EQ-series fund units from dominating a stock ranking. The guard is
explicitly heuristic on dates that lack a point-in-time universe classification.

Machine-readable verification:
`output/reactor_scale_audit/current_screenshot_extreme_validation_v2.json`.
