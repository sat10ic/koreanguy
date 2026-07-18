# SMF / Reactor data — complete reverse engineering

**Date:** 2026-07-14  
**Scope:** supplied March–April score sheet, supplied teaching transcript, official NSE bhavcopy history, formula-search artifacts, July screenshots, and the current sat10ic implementation  
**Decision:** exact proprietary-formula recovery has **not** been achieved. The observable score family is dominated by abnormal average quantity per trade and delivery participation; ordinary price-range ADR is not the missing explanatory term. sat10ic's current score is a useful, direction-neutral **analogue**, not the source SMF/Reactor score.

---

## 1. Status language used in this report

- **Certain:** directly observed in the supplied source, official files, executable code, or independently recomputed artifacts.
- **Likely:** the best explanation of multiple observations, but not disclosed by the score owner.
- **Assumption:** an explicit modelling choice made by sat10ic.
- **Unverified:** evidence is presently insufficient.

This distinction matters because “smart money” is an interpretation. Aggregate NSE data cannot identify the participant, aggressor side, or intent behind a trade.

## 2. Executive conclusion

### What has been recovered

**Certain:** the closest recoverable EOD mechanism is:

1. Estimate each session's average quantity per reported trade:

   ```text
   average_trade_quantity = total_traded_quantity / number_of_trades
   ```

2. Compare today's average trade quantity with the stock's own recent baseline.
3. Compare today's delivery percentage with its recent baseline.
4. Combine both ratios with a nonlinear interaction term.

The best single clue in the initial causal study was the 20-session average-trade-quantity ratio: Pearson correlation 0.8577 and rank correlation 0.8042 over 8,628 matched observations. Relative volume alone was much weaker. This is consistent with the transcript's description of unusually large quantity relative to a stock's normal activity.

### What has not been recovered

**Certain:** no tested formula reproduces the supplied sheet exactly. The strongest full-panel candidate matches only 6,572 of 53,280 usable ticker-date observations after two-decimal rounding: 12.3348% exact. Its mean absolute error is 0.1324, but its worst miss is 16.2113.

**Certain:** the public workbook contains no formula cells. The transcript explicitly says the calculation is proprietary. Official daily bhavcopy does not expose individual order size, maximum order quantity, bid/ask aggressor, footprint delta, participant identity, or true volume-at-price.

**Likely:** the score formula or upstream footprint feed changes around 20–26 March 2025. A separately fitted EOD formula is only 2.0390% exact in the early block but 21.8029% exact in the late block. This discontinuity is too large to treat as ordinary fitting noise.

### Product decision

The production-safe output is:

```text
sat10ic EOD Activity Score
```

It must remain:

- direction-neutral;
- shadow/research labelled;
- accompanied by its raw quantity and delivery ratios;
- separated from POC/VAH/VAL and Volume Profile;
- prevented from changing deterministic eligibility, stop placement, position sizing, or portfolio heat by itself.

It must not be marketed as the proprietary SMF/Reactor formula or proof of institutional buying.

---

## 3. Frozen evidence set

| Evidence | Role | Integrity / state |
|---|---|---|
| `C:\Users\satta\Downloads\DEMO SHEET - MARCH APRIL - Sheet1.csv` | Supplied score labels | SHA-256 `CADF01A671C4AEDA13C0CDC40258B3BEE568BC4A53F6C7447455EA105DDBB184` |
| `C:\Users\satta\Downloads\NoteGPT_Transcript_How To Track Smart Money Footprint In Indian Stock Market  Proper Step By Step Video.txt` | Source semantics and workflow | 209 lines; SHA-256 `818DC042FDF51D77B4B3E7B801C2105F6A508FD23DD137C9EE6E54FC31A94DFA` |
| `design/REACTOR_SMART_MONEY_SOURCE_EXTRACT_2026-07-14.md` | Frozen, line-mapped transcript extraction | Canonical doctrine source for this report |
| `output/reactor_scale_audit/DEMO_SHEET_PUBLIC_EXPORT.xlsx` | Public workbook export | SHA-256 `B63AF5D48D90C8A4E9A2D81DE5E615767F533A36409164B0CFCDA9D17DFC1CD0`; direct OOXML inspection found zero `<f>` formula cells |
| `data/bhavcopy/sec_bhavdata_full_*.csv` | Official daily NSE inputs | 162 valid sessions from 2024-09-02 through 2025-04-29; 10 closed dates; zero failed downloads |
| `output/reactor_scale_audit/final_reactor_search_verification.json` | Independent final-fit verification | SHA-256 `7EB91D0EDA16AEFB01877D34D1EB75A48299EBCB35A92F26704CA5A72ACDD30B` |
| `output/reactor_scale_audit/current_screenshot_extreme_validation_v2.json` | July extreme-score check | SHA-256 `E7F1C1E2A44A587373672C7B79D5D7E717A9A617BC38D892BB02C7A5C55AC33A` |

The transcript extraction is used rather than repeatedly reinterpreting the raw transcript. Its line mapping preserves what the speaker claims without converting promotional or interpretive statements into market facts.

---

## 4. What the supplied score sheet actually contains

Independent CSV parsing and the workbook inspection agree on the following:

| Field | Observed value |
|---|---:|
| Stock rows | 1,627 |
| Date columns | 37 |
| Date range | 2025-03-03 to 2025-04-29 |
| Possible ticker-date cells | 60,199 |
| Numeric scores | 55,613 |
| Nonnumeric/unusable cells | 4,586 |
| Median numeric score | 2.91 |
| Minimum / maximum | 0.17 / 44.40 |
| Scores above 3.5 | 13,475 (24.23%) |
| Scores at least 8 | 332 (0.60%) |
| Segment labels | 1,411 Equity; 216 F&O |

The 4,586 unusable cells are not all truly blank. Their exact exported contents are:

| Exported value | Count |
|---|---:|
| `#VALUE!` | 1,628 |
| `#######` | 1,552 |
| `#N/A` | 799 |
| `#####` | 507 |
| `######` | 100 |

**Certain:** these are not score values and were excluded from fitting. Hash-filled CSV cells are especially important: they may be display/export damage rather than missing source calculations, but their original numeric values cannot be reconstructed from this export.

The final official-data research panel contains 53,280 observations across 1,478 symbols and all 37 dates—95.80% of the sheet's numeric labels. The remaining 2,333 numeric labels lack a complete match under the causal official-history and symbol-quality requirements.

The sheet supplies sector, industry, segment and partial index-bucket metadata. It does not supply OHLCV, trade count, delivery data, ADR inputs, component values, direction labels, or formulas.

---

## 5. What the source says the score means

The frozen transcript extraction supports the following semantic contract:

1. **Activity, not direction.** A high score may accompany accumulation or distribution. The chart is needed to infer direction. Source extract: transcript lines 51–61 and 164–167.
2. **Relative abnormality.** The explanation centres on unusually large quantity relative to the stock's ordinary activity. Source extract: lines 31–43.
3. **Threshold convention.** Below 3.5 is treated as ordinary and above 3.5 as abnormal. Source extract: lines 43–55.
4. **Persistence matters.** The teaching example filters for at least three consecutive abnormal sessions; the user may tighten the threshold or run length. Source extract: lines 43–55.
5. **Extreme and persistent states differ.** An isolated very high reading may precede a sharp move; repeated readings may accompany a longer move. These are hypotheses to validate, not guaranteed outcomes. Source extract: lines 107–109.
6. **Corporate actions distort quantity.** Splits and related changes can create false readings and must be quarantined. Source extract: lines 61–65 and 103–105.
7. **Structure decides execution.** Higher-timeframe trend, price response, selected range, volume behaviour, stop structure and position sizing still determine whether a trade exists. Source extract: lines 67–101 and 113–127.
8. **The formula is withheld.** The owner declines to disclose it. Source extract: lines 203–205.

Therefore, “above 3.5 is favourable” can only mean favourable for **further investigation**. It cannot faithfully mean bullish or buyable.

---

## 6. Volume Footprint, the EOD analogue, and Volume Profile are different objects

### Source-described Volume Footprint / SMF

The teaching explanation refers to unusual order/trade quantity and abnormal candle activity. The exact proprietary feed and transformation are unknown.

### sat10ic EOD Activity Score

This is an approximation using aggregate official daily fields:

- total traded quantity;
- number of trades;
- turnover;
- delivery quantity;
- delivery percentage;
- OHLC for tested range/ADR alternatives.

It cannot see individual orders or aggressor direction.

### Fixed Range Volume Profile

POC, VAH and VAL are calculated over a selected price range and are used later to interpret acceptance/rejection and execution. They are not demonstrated score inputs.

- POC means the highest-volume price in the chosen range, not automatic accumulation.
- A VAL reaction is a possible rejection/support event, not an automatic buy.
- A VAH break is a possible continuation event, not an automatic trade.

The profile anchor, bar resolution, source, completeness and value-area settings must be visible. Daily bhavcopy cannot reproduce true within-range volume-at-price.

---

## 7. Candidate input construction

The official bhavcopy fields allow these principal proxies:

```text
average_trade_quantity = TTL_TRD_QNTY / NO_OF_TRADES

average_trade_value_rupees =
    TURNOVER_LACS * 100000 / NO_OF_TRADES

relative_volume =
    current_volume / rolling_baseline(volume)

relative_trade_count =
    current_number_of_trades / rolling_baseline(number_of_trades)

quantity_per_trade_pressure =
    relative_volume / relative_trade_count
```

The last expression is algebraically related to abnormal average quantity per trade. Delivery percentage and delivery quantity provide context about how much exchange volume resulted in delivery, but still do not identify the participant.

Price-range ADR candidates were built from daily high, low and close. They were tested as direct terms, interactions and residual explanations; they did not recover the missing score behaviour.

All rolling features used point-in-time history only. The research tested prior and inclusive baselines where specified; future sessions were not used to calculate earlier features.

---

## 8. Reverse-engineering search conducted

The bounded search tested more than 7,500 parsimonious, domain-grounded configurations. It deliberately avoided unconstrained black-box models because a black-box fit would not recover an auditable formula.

Search families included:

- rolling mean, median and EMA baselines;
- prior-only and inclusive windows;
- volume and trade-count ratios;
- average quantity and value per trade;
- delivery percentage, delivery quantity and delivery-per-trade variants;
- ADR/range and volume-range interactions;
- products and fractional powers;
- log, square-root and z-score variants;
- daily cross-sectional normalisation;
- component and final-score rounding variants;
- coefficient/intercept and nonlinear-exponent refinement;
- early, transition and late period-specific fits.

The exact-clone gate was two-decimal reproduction across the supplied panel. MAE, rank correlation and threshold agreement were supporting diagnostics, not substitutes for exactness.

---

## 9. Findings by research stage

### 9.1 Initial causal feature study

Across 8,628 matched observations with the then-available history:

| Feature | Pearson | Spearman |
|---|---:|---:|
| Average trade quantity / prior-20 mean | 0.8577 | 0.8042 |
| Average trade value / prior-20 mean | 0.8215 | 0.7741 |
| Relative volume / relative trade count | 0.8397 | 0.7721 |
| Delivery percentage / prior-20 mean | 0.5965 | 0.6136 |
| Delivery quantity / prior-20 mean | 0.5422 | 0.6030 |
| Relative volume | 0.2036 | 0.3949 |
| ADR20 alone | -0.0582 | -0.0664 |

This overturned the early delivery-first hypothesis. Delivery helps, but abnormal average quantity per trade is the principal observable driver.

### 9.2 The attractive but misleading short holdout

A five-feature linear approximation trained through 25 April and tested on 28–29 April produced:

- 2,896 held-out rows;
- MAE 0.0755;
- R² 0.9841;
- rank correlation 0.9910;
- recall 0.9490 for source scores above 3.5.

However, only 156 rows—5.39%—were exact to two decimals. Median absolute error was 0.0525 and maximum error was 1.8281.

**Lesson:** excellent R² and ranking can coexist with failure to recover the actual formula. The late-period holdout also sits in the block that is easiest for EOD inputs to mimic.

### 9.3 Best full-panel candidate

Define:

```text
q = today's average trade quantity
    / inclusive 20-session mean of average trade quantity

d = today's delivery percentage
    / prior 19-session mean of delivery percentage
```

The best formula by exact two-decimal matches is:

```text
score_v1 = 1.1048768252*q
         + 1.0099667732*d
         + 1.1730986222*(q*d)^0.825
         - 0.14
```

| Metric | Result |
|---|---:|
| Matched observations | 53,280 |
| Symbols / dates | 1,478 / 37 |
| Exact after two-decimal rounding | 6,572 |
| Exact share | 12.3348% |
| Mean absolute error | 0.1324 |
| Median absolute error | 0.0364 |
| Within 0.05 | 56.1280% |
| Within 0.10 | 67.7271% |
| Maximum absolute error | 16.2113 |

The exact count and MAE were independently reproduced using Python's standard-library CSV reader, `Decimal` with `ROUND_HALF_UP`, and `math.fsum`. Both agree with the vectorised search to better than `1e-12` for MAE.

Derived behaviour of this analogue, not source doctrine:

- when `q = 1` and `d = 1`, the score is approximately 3.1479;
- with delivery fixed at baseline, the score crosses 3.5 near `q = 1.1710` and 8 near `q = 3.4816`;
- because today's quantity is included in its 20-session denominator, the quantity ratio is naturally bounded toward 20 when earlier sessions remain positive.

### 9.4 ADR rejection

**Certain:** ordinary price-range ADR is not the missing EOD term in the supplied panel.

- The best literal Volume+ADR candidate gives ADR a coefficient of only 0.0167 and matches 1.9956% exactly.
- Across tested ADR variants, the largest absolute correlation with the best model's residual is 0.0433.
- The earlier SwingEdge-style 40% volume / 35% range-ATR / 25% efficiency score, scaled by 2.2, matches 0.3814% exactly.
- That construction cannot exceed 11, while the source sheet reaches 44.4.

**Unverified:** the publisher may use “ADR” as a proprietary acronym or a differently defined component. The evidence only rejects conventional daily price-range ADR as the missing explanation.

### 9.5 Period discontinuity

| Source block | Rows fitted | Best exact share | MAE | Within 0.05 |
|---|---:|---:|---:|---:|
| 2025-03-03 to 2025-03-19 | 17,312 | 2.0390% | 0.2532 | 16.1564% |
| 2025-03-20 to 2025-03-25 | 5,755 | 4.2398% | 0.1630 | 30.5995% |
| 2025-03-26 to 2025-04-29 | 30,207 | 21.8029% | 0.0259 | 87.7710% |

**Likely:** either the source calculation, a scaling/normalisation step, or the upstream footprint feed changes. The evidence does not identify which.

A near-identical-input counterexample reinforces the missing-variable/version conclusion:

- MAHSCOOTER on 2025-03-10 and KIRLPNU on 2025-04-22 have quantity ratios 1.197662 and 1.197730;
- delivery ratios 1.228552 and 1.228859;
- range/ADR ratios 0.800311 and 0.798546;
- supplied scores 3.03 and 4.05.

The visible EOD inputs are essentially the same while the labels differ by 1.02.

### 9.6 One-stock reconstruction: CSLFINANCE, 2025-04-29

| Evidence | Value |
|---|---:|
| Supplied score | 19.19 |
| OHLC | 335.00 / 335.00 / 308.00 / 322.15 |
| Traded quantity / number of trades | 307,118 / 1,361 |
| Average quantity per trade | 225.66 |
| Prior-20 average quantity per trade | 23.02 |
| Quantity ratio | 9.80x |
| Average trade value | ₹71,196.91 |
| Prior-20 average trade value | ₹6,485.60 |
| Value ratio | 10.98x |
| Delivery percentage | 94.46% |
| Prior-20 ADR | 6.63% |

The previous session's source score was 3.09 and its quantity ratio was 0.91x. The case strongly supports the recovered input family. The five-feature approximation still estimated 21.02 rather than 19.19, showing why family recovery is not exact formula recovery.

---

## 10. Current-period calibration: `sat10ic_eod_activity_v2`

The July screenshots exposed that the full-panel v1 analogue underweighted the quantity leg at extreme readings. A separately versioned current-period calibration uses the same two observable inputs:

```text
score_v2 = 1.165335*q
         + 1.04631*d
         + 1.152161*(q*d)^0.84
         - 0.213928
```

On 15 unambiguous screenshot scores from 1 and 10 July 2026:

| Metric | Result |
|---|---:|
| Mean / median absolute error | 0.0767 / 0.09 |
| Maximum absolute error | 0.18 |
| Within 0.10 | 11 of 15 |
| Within 0.25 | 15 of 15 |
| Agreement at 3.5 threshold | 15 of 15 |
| Persisted-component recomputation difference | 0.00 |

Selected extreme checks:

| Symbol | Source | v2 analogue |
|---|---:|---:|
| ETHOSLTD | 22.58 | 22.76 |
| MAHLIFE | 13.42 | 13.32 |
| TBOTEK | 8.95 | 9.08 |
| URBANCO | 9.08 | 8.91 |
| MUKANDLTD | 8.16 | 8.07 |

This is strong **current-screen approximation** evidence, but weak formula-identification evidence: 15 selected observations are small, not a complete cross-section, and do not prove full-panel exactness. v2 supersedes v1 for sat10ic's current analogue; it does not become the proprietary source formula.

Derived v2 behaviour, not source doctrine:

- baseline `q = d = 1` gives approximately 3.1499;
- with delivery at baseline, 3.5 occurs near `q = 1.1651` and 8 near `q = 3.3922`.

---

## 11. Why exact reconstruction is presently underdetermined

At least one of the following is missing:

1. **Individual order/trade distribution:** bhavcopy supplies aggregate trade count, not the maximum or upper-tail order quantity described in the teaching explanation.
2. **Intraday sequence:** identical daily totals may arise from one block, many medium trades, or activity spread across the session.
3. **Aggressor/side information:** daily data cannot distinguish buying pressure from selling pressure.
4. **Volume-at-price:** OHLCV does not reveal where inside the daily range the volume traded.
5. **Universe or cross-sectional normalisation:** the owner may normalise against a changing universe or liquidity bucket.
6. **Corporate-action adjustments:** splits and symbol events can change quantity distributions.
7. **Versioning:** the March/April error break is consistent with a formula/feed change.
8. **Hidden rounding/capping:** component-level rounding or caps may exist before the displayed score.

More coefficient permutations over the same aggregate fields cannot recover a variable that is not present. Exact-clone research should resume only when the formula/component definitions or equivalent order/tick-level feed becomes available.

---

## 12. Current sat10ic implementation audit

The implementation lives in `alpha/activity.py` and is intentionally documented as a direction-neutral, shadow-only approximation.

### Correctly implemented

- Versioned formula: `sat10ic_eod_activity_v2`.
- Requires 20 valid bhavcopy sessions.
- Uses only rows on or before the requested date.
- Uses total quantity / number of trades and delivery percentage.
- Persists formula version, score, percentile, components, source and quality status.
- Defines abnormal at 3.5 and extreme at 8.
- Exposes previous score, four-session average, ten-session average and trail.
- Excludes date-stale observations from a requested cross-section.
- Keeps the explanatory note: abnormal activity, direction unresolved.
- Automated tests cover causal calculation, future-bar exclusion, insufficient history, persistence gaps, trend fields, formula-version isolation and intended ETF exclusion.

### Fidelity and data-quality gaps found

1. **Persistence mismatch.** The source workflow describes at least three consecutive abnormal sessions. Current code changes `abnormal` to `persistent_abnormal` at two sessions. Source-faithful UI should either require three or label two-day and three-day streaks separately.
2. **Fund-unit contamination in persisted runtime data.** On 2026-07-14, the API's latest v2 cross-section resolved to 2026-07-13 with 2,341 instruments, 488 abnormal, 24 extreme and 182 persistent. Its top five included `SBIBPB`, `TOP10ADD` and `HDFCNIFBAN`, which are fund-like instruments rather than ordinary operating-company stocks. The code now has point-in-time universe and ETF guards, but the persisted date must be recomputed and the guard expanded/verified before the leaderboard can be trusted as a Stocks view.
3. **Corporate-action quarantine is not proven in this scoring module.** The source explicitly requires ignoring split-distorted readings. A visible per-row quarantine reason is still required.
4. **Current calibration evidence is small.** v2's July fit should remain shadow-only until it is tested on complete current cross-sections rather than selected screenshot leaders.
5. **No demonstrated alpha yet.** Matching the source score does not prove future returns, favourable direction, or better swing outcomes.

The runtime counts above are an as-observed system snapshot, not stable research statistics.

---

## 13. Faithful UI and debate contract

Each stock row/card should show:

- score and formula version;
- as-of session and data source;
- cross-sectional percentile and denominator;
- prior score, four-day average, ten-day average and consecutive streak;
- average quantity per trade, its 20-session baseline and ratio;
- delivery percentage, its baseline and ratio;
- quality flags, corporate-action quarantine and insufficient-history state;
- permanent wording: **“Abnormal activity; direction unresolved.”**

The chart/debate stage then determines:

- higher-timeframe trend and market/theme context;
- whether price response suggests accumulation, distribution, absorption, exhaustion, or remains unresolved;
- whether the stock is strengthening or weakening relative to its sector/theme/index;
- Fixed Range Volume Profile anchor and POC/VAH/VAL relationship;
- trigger, invalidation, stop structure and expected sequence;
- strongest contradiction.

The score must never silently alter position size. Existing regime, liquidity, gap/circuit, stop, portfolio-heat and deterministic risk rules remain authoritative.

---

## 14. Validation still required before alpha use

Formula similarity and tradable value are separate experiments. A sat10ic-owned Activity Score should remain shadow-only until it passes:

1. point-in-time and future-data leakage tests;
2. complete-universe stock/ETF/suspended-symbol classification;
3. split, bonus, merger and symbol-change quarantine;
4. stability by date, sector, liquidity and market-cap cohort;
5. future absolute-move tests for isolated extremes and persistent runs;
6. direction tests only after conditioning on chart behaviour, regime and relative strength;
7. incremental-value tests beyond relative volume, RS, setup rank and regime;
8. cost-aware MFE, MAE, time-to-trigger, +1R-before-stop and stop-first outcomes;
9. at least one full current-period labelled panel, not only top-score screenshots;
10. live shadow observation before any ranking influence is promoted.

Recommended baselines are plain relative volume, average-trade-quantity ratio alone, delivery ratio alone, and the combined v2 analogue. The nonlinear score must beat these simpler alternatives out of sample to justify its complexity.

---

## 15. Exact-clone resumption checklist

Do not run another broad coefficient search unless at least one new source becomes available:

- original formula or component definitions;
- raw component columns before the final score;
- the same tick/order/footprint feed;
- complete source panels spanning the March discontinuity and a current period;
- clarification of what “ADR” means in the proprietary product;
- version dates and rounding/capping rules.

With new evidence, freeze an untouched copy first, hash it, map its date/universe coverage, and rerun the existing exact two-decimal verification. Never overwrite prior formula versions or validation artifacts.

---

## 16. Reproducible artifact map

- Source doctrine: `design/REACTOR_SMART_MONEY_SOURCE_EXTRACT_2026-07-14.md`
- Original detailed audit: `design/REACTOR_SCALE_REVERSE_ENGINEERING_AUDIT_2026-07-14.md`
- Workbook inspection: `output/reactor_scale_audit/inspect_reactor.mjs`
- Official history manifest: `output/reactor_scale_audit/official_bhavcopy_manifest.json`
- Initial quantity study: `output/reactor_scale_audit/order_size_probe.py`
- Full-universe construction: `output/reactor_scale_audit/universe_reverse_engineer.py`
- Domain formula search: `output/reactor_scale_audit/domain_formula_search.py`
- Remaining-domain search: `output/reactor_scale_audit/remaining_domain_search.py`
- Z-score/cross-sectional search: `output/reactor_scale_audit/zscore_domain_search.py`
- Nonlinear exact refinement: `output/reactor_scale_audit/exact_refine_nonlinear.py`
- Period discontinuity analysis: `output/reactor_scale_audit/period_formula_search.py`
- Independent verifier: `output/reactor_scale_audit/verify_final_reactor_search.py`
- Verified final metrics: `output/reactor_scale_audit/final_reactor_search_verification.json`
- Current extreme validation: `output/reactor_scale_audit/current_screenshot_extreme_validation_v2.json`
- Current implementation: `alpha/activity.py`
- Implementation tests: `tests/test_alpha_activity.py`

---

## 17. Final verdict

**Certain:** the source labels are primarily consistent with abnormal average quantity per trade plus delivery participation, combined nonlinearly.

**Certain:** conventional price-range ADR, relative volume alone, or a simple weighted Volume+ADR score cannot reproduce the sheet.

**Certain:** the full-panel exact-clone gate fails; 12.3348% exact is not formula recovery.

**Likely:** a hidden footprint variable and/or source version change explains the remaining discrepancy, especially the early block and extreme misses.

**Certain:** `sat10ic_eod_activity_v2` is close on the 15 visible July examples but remains a small-sample functional analogue.

**Unverified:** whether the source score itself adds future swing-trading alpha after regime, relative strength, setup quality and costs are controlled.

## Risks

- Calling abnormal aggregate activity “institutional buying” would overstate the data.
- Current stored leaderboard data still shows fund-like instruments and needs a guarded recomputation.
- Two-session persistence in code does not match the three-session teaching filter.
- Corporate actions and bad trade counts can manufacture extreme scores.
- The March/April discontinuity may make one universal clone structurally impossible.
- A close score mimic may preserve the source's errors without creating predictive value.
- Intraday Volume Profile remains anchor- and data-resolution-dependent and must not be folded into the EOD score without a separately validated specification.

## ADDENDUM 2026-07-18 (marketing screenshots)
- Their stock panel computes delivery from USER-UPLOADED NSE CSV (bhavcopy) -- confirms the delivery leg is public-data; only the order-size leg stays private.
- Leaked display bands: %% delivery-to-traded >=50 STRONG / 25-50 MODERATE / <25 WEAK -- adopt for our activity chip display.
- Their dashboard = the shock-movers layout user referenced (daily score, 4d/10d avg, streak, surge-day, 10d trend bars) -- our queued shock-movers upgrade mirrors it on our own gated score.
- Decision 2026-07-18: subscription NOT purchased (recommendation: save; optional 6m shadow-test protocol documented in chat -- IC vs our v2 baseline, pre-registered kill rule).
