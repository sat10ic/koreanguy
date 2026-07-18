# SMF Final Score demo fit — independent Codex attempt

**Outcome:** public NSE bhavcopy fields reproduce the vendor score's ordering very well, but do not reproduce the two-decimal score; the best fitted bhavcopy-only model has pooled Pearson **0.975024**, pooled Spearman **0.967330**, and only **3.6921%** exact two-decimal matches.

**Execution deviation:** the managed Windows sandbox denied execution of every installed native `python.exe`, and no workspace-local Python existed. I used native Windows Node 24.11.0 plus its read-only SQLite API, never WSL. This changes the implementation language, not the data or statistical definitions. `_smf_codex/verify_results.mjs` independently recomputes the headline metrics from the emitted residual panel.

## Verdict in one paragraph

The observable family is clear: abnormal delivered quantity per trade—equivalently, average trade quantity combined with delivery participation—dominates. A nonlinear, capped, multihorizon model using every relevant daily bhavcopy field ranks the sheet extremely well, including ICICIBANK's 8.07 spike. It still misses 96.3079% of displayed values at two decimals and has structured early-period residuals. RELIANCE 5.29 cannot pass the requested top-decile gate because it is only at the 88.89th percentile in the vendor sheet itself. **Likely:** exact reproduction requires either a non-bhavcopy order-distribution variable, a vendor formula/feed version change, or both. A high-fidelity analogue is reproducible; the proprietary Final Score is not.

## 1. Sources and alignment

The SQLite connection was opened with `readOnly: true`, `PRAGMA query_only=ON`, and a read transaction. No database write statement was issued.

| Item | Verified value |
|---|---:|
| Demo CSV SHA-256 | `cadf01a671c4aeda13c0cdc40258b3bee568bc4a53f6c7447455ea105ddbb184` |
| Transcript SHA-256 | `818dc042fdf51d77b4b3e7b801c2105f6a508fd23dd137c9ee6e54fc31a94dfa` |
| Named rows in sheet | 1,627 |
| `Segment=F&O` symbols | 216 |
| Daily score columns | 37 |
| Date span | 2025-03-03 to 2025-04-29 |
| Nonmissing F&O labels | 7,992 |
| Common eligible cells used by every candidate | 7,963 |
| Eligible symbols / dates | 216 / 37 |
| Label median / p90 / p99 / maximum | 3.04 / 4.15 / 5.95 / 14.06 |

The 29 excluded labels lacked one or more inputs required by the common-cell gate, mostly sufficient valid rolling history. Every candidate below uses exactly the same 7,963 cells. The SQL query explicitly requires `source='bhavcopy'`; an initial diagnostic found mixed-source rows and the entire analysis was rerun after excluding them.

**Premise correction:** the current DB snapshot contains data for the full labeled window, starting 2025-03-03, rather than only from about 2025-03-19. `PRAGMA table_info(daily_prices)` confirms `turnover`, `num_trades`, `delivery_qty`, and `delivery_pct` exist. The sheet contains 216 F&O symbols, not approximately 100.

Date alignment was checked twice: the analysis parser left-padded five-digit headers (`90425` → `090425` → 2025-04-09), and a separate PowerShell `Import-Csv` pass confirmed all 37 headers plus the named 2025-03-21 values.

## 2. What the tutorial actually states

The complete quote/translation extraction is in [`_smf_codex/TRANSCRIPT_FORMULA_EXTRACT.md`](../../../_smf_codex/TRANSCRIPT_FORMULA_EXTRACT.md). The formula-relevant statements are:

| Source | Quote excerpt | Faithful translation / implication |
|---|---|---|
| Transcript L29, L41 | “100 ऑर्डर पर डे… एवरेज… पर ऑर्डर… 50 की क्वांटिटी… बड़ा… ट्रेड क्वांटिटी” | Illustrative example: usual quantity per order/trade is 50 across 100 daily orders; a large participant must trade larger quantity and the system detects it. The figures are examples, not disclosed formula thresholds. |
| L43 | “जितनी बड़ी एक्टिविटी… नंबर उतने बड़े” | More activity produces a larger score. |
| L43–45 | “अगर 2.8 है… नॉर्मल”; “3.5 के नीचे… नॉर्मल… 3.5 के ऊपर… एबनॉर्मल” | 2.8 is an example of normal activity; below 3.5 is normal and above 3.5 abnormal. Equality at 3.5 is unspecified. |
| L47–49 | “लास्ट… थ्री डेज… ग्रेटर देन 3.5” | Screening rule: latest three days each above 3.5; optionally add another two or three days. This is not a score-computation lookback. |
| L55 | “ग्रेटर देन फोर” | Optional stricter daily filter: score >4. |
| L107–109 | “तीन दिन… मल्टीपल डेज पे फोकस” | Focus on persistence over multiple days; three days is the worked example. |
| L127–129 | “लास्ट फोर डेज का एवरेज… ग्रेटर देन फाइव” | Explicit aggregate screen: four-day average >5. |
| L61–63, L105 | “स्टॉक स्प्लिट… डेटा को कंसीडर मत करिए” | Exclude split-distorted activity because quantity mechanically changes. |
| L165–167 | “बाय भी हो सकता है, सेल भी… एक्टिविटी… डायरेक्शन नहीं” | The score is direction-neutral: it can reflect accumulation or distribution. |
| L185 | “3 टू सिक्स मंथ का टाइम” | Users need 3–6 months to learn/observe it; this is not a formula lookback. |
| L187 | “अराउंड 1600… 1700… लिक्विड स्टॉक” | Claimed universe is roughly 1,600–1,700 liquid stocks; the supplied sheet's 1,627 rows agree. |
| L205 | “डाटा किस हिसाब से बनाई है… नहीं बता सकता… माय प्रोडक्ट” | The presenter explicitly refuses to disclose the calculation. |

The tutorial never states a numerical historical baseline, delivery input, turnover input, ADR term, sector normalization, cap, exponent, weight, or rounding sequence. Treating any of those as vendor doctrine would be invention.

## 3. Feature definitions and fit protocol

For symbol (i), session (t):

```text
ATQ  = volume / num_trades
ATV  = turnover / num_trades
DQPT = delivery_qty / num_trades

q  = ATQ_t / inclusive 20-session mean(ATQ)
d  = delivery_pct_t / prior 19-session mean(delivery_pct)
dq = DQPT_t / prior 20-session mean(DQPT)
atv = ATV_t / inclusive 20-session mean(ATV)
```

All rolling features are causal: only the current and earlier sessions enter. `q3/d3` and `q4/d4` are trailing three-/four-session means of `q/d`. Daily ranks use the eligible F&O cross-section on that same date. Candidate M5 alone uses the demo sheet's sector metadata and is therefore an auxiliary normalization test, not a bhavcopy-only clone.

Each candidate was fit by ridge/OLS on the identical panel. Five contiguous date blocks were also held out one at a time; those out-of-fold results test time-block stability, not live forward forecasting. Fitted performance identifies an approximation; it does **not** identify the vendor formula.

## 4. Six candidate formulas

Raw-scale equations are shown for the parsimonious fits. The M6 coefficient vector is preserved in `_smf_codex/results.json`; printing its 24 collinear basis weights as a compact “formula” would be misleading.

1. **M1 — own-history average-trade-size shock**  
   `score_hat = 0.651139 + 2.407530*q`

2. **M2 — delivery participation / delivered-size shock**  
   `score_hat = 1.262845 + 0.239434*d + 1.567481*dq`

3. **M3 — turnover/order-value proxy**  
   `score_hat = 0.584022 + 2.576136*atv - 0.129460*turnover_ratio20`

4. **M4 — multi-day accumulation**  
   `score_hat = -0.879753 + 2.061420*q + 2.059461*d - 0.053412*q3 - 0.004253*d3 - 0.065753*q4 - 0.044430*d4`

   The trailing-average coefficients are tiny beside current-day `q` and `d`. Persistence is useful for screening, but the fit gives no evidence that it is a large component of the daily Final Score.

5. **M5 — cross-sectional and sector-relative ranks**  
   Daily F&O percentile ranks for `q`, `d`, and `atv`, plus within-sector ranks for `q` and `d`. Raw-scale rank coefficients: 1.4192, 1.3920, 0.3796, -0.0830, and 0.0533. Sector-relative terms add little.

6. **M6 — maximal nonlinear/capped bhavcopy-only model**  
   Ridge basis: `q`, `d`, `dq`, `atv`, relative volume/turnover/trade count/range/absolute return, close location, 3-/4-day means, ((q d)^{0.5}), ((q d)^{0.825}), (q d), log transforms, caps, and daily F&O ranks. Sector metadata is excluded.

## 5. Correlation results

All numbers in this table are fitted on the common 7,963-cell panel. “Day P/S” are the mean and median of 37 daily cross-sectional correlations.

| Model | Pooled Pearson | Pooled Spearman | Day Pearson mean | median | Day Spearman mean | median | MAE | Exact at 2 dp |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| M1 ATQ shock | 0.834800 | 0.784103 | 0.815852 | 0.825303 | 0.773779 | 0.771815 | 0.344180 | 0.8791% |
| M2 delivered-size shock | 0.961243 | 0.956393 | 0.967900 | 0.982775 | 0.965268 | 0.986677 | 0.161048 | 2.1977% |
| M3 turnover/order-value | 0.836098 | 0.781592 | 0.816827 | 0.821012 | 0.766738 | 0.769095 | 0.346398 | 0.8665% |
| M4 multi-day accumulation | 0.969150 | 0.961059 | 0.974865 | 0.992551 | 0.969256 | 0.991494 | 0.136898 | 1.9339% |
| M5 cross-section/sector ranks | 0.837924 | 0.906882 | 0.899104 | 0.903230 | 0.952608 | 0.971590 | 0.281443 | 1.4316% |
| **M6 maximal public model** | **0.975024** | **0.967330** | **0.976485** | **0.991786** | **0.971130** | **0.994258** | **0.117934** | **3.6921%** |

M6's five-date-block out-of-fold pooled Pearson/Spearman are **0.971055 / 0.962261**, with MAE **0.130940**. The small fitted-to-held-out decline means the high correlation is not merely same-cell coefficient overfit.

### Existing analogue benchmarks

These were not refit on this panel; they are fixed formulas from the prior audit/current implementation.

| Benchmark | Pearson | Spearman | Day Pearson mean/median | Day Spearman mean/median | MAE | Exact at 2 dp | Within 0.10 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `activity_v1` | 0.971218 | 0.961864 | 0.976629 / 0.994302 | 0.971118 / 0.996011 | **0.112144** | **15.0948%** | 70.7020% |
| `sat10ic_eod_activity_v2` | 0.971249 | 0.961855 | 0.976595 / 0.994291 | 0.971081 / 0.995982 | 0.114601 | 13.0353% | 71.0536% |

The fixed v1 analogue has slightly lower correlation than M6 but better numeric calibration and many more exact values. Even its 15.09% exact share is a failed clone, not formula recovery.

## 6. Named spike checks

Percentiles are empirical shares at or below the named value. A separate PowerShell pass over all 216 F&O labels independently reproduced the ground-truth ranks; the fitted panel has 215 eligible names that day.

| Cell | Vendor | M6 prediction | Vendor percentile | M6 percentile | Top-decile verdict |
|---|---:|---:|---:|---:|---|
| ICICIBANK, 2025-03-21 | 8.07 | 7.8875 | 100.00% | 100.00% | **Pass** — top name under both. |
| RELIANCE, 2025-03-21 | 5.29 | 5.1136 | 88.89% in all 216 labels; 88.84% in 215 eligible | 88.84% | **Fail** — neither vendor nor model is top-decile. |

For ICICIBANK, `q=3.1256`, `dq=4.0970`, and the daily `q` percentile is 100%; the public proxy correctly sees an extreme order-size shock. RELIANCE has `q=1.7617`, `dq=2.2953`, and daily `q` percentile 89.30%; the prediction preserves its actual near-top-decile position.

## 7. Residual analysis of M6

### Largest misses

| Symbol/date | Vendor | Predicted | Residual | q | d | Shared trait |
|---|---:|---:|---:|---:|---:|---|
| MCX 2025-04-08 | 6.00 | 3.5583 | +2.4417 | 0.9853 | 1.2335 | Vendor spike with normal ATQ/ATV; clearest missing-input candidate. |
| OFSS 2025-03-17 | 5.77 | 7.7020 | -1.9320 | 2.2919 | 1.8293 | Aggregate order-size and delivery proxies are extreme, but vendor score is capped/lower. |
| BOSCHLTD 2025-03-05 | 4.20 | 5.7114 | -1.5114 | 1.9727 | 1.3513 | Early-period overprediction. |
| MRF 2025-03-13 | 3.07 | 4.4317 | -1.3617 | 1.1791 | 1.4954 | Strong delivery proxy not rewarded by vendor. |
| SOLARINDS 2025-03-06 | 4.22 | 5.5432 | -1.3232 | 1.6991 | 1.4578 | Early-period overprediction. |

### What the biggest misses share

- **Time block dominates:** 92.72% of the worst-error decile occurs on or before 2025-03-25, versus 37.69% of the remaining cells. The ten highest-MAE dates are all in March. M6 is negatively biased on those dates, while several individual high-proxy names are overpredicted.
- **They are more extreme:** the worst decile has mean vendor score 3.5193 versus 3.1399, mean `q` 1.2612 versus 1.0260, and mean `dq` 1.4707 versus 1.0234. Top-decile vendor labels constitute 20.20% of the worst residual decile versus 9.22% elsewhere.
- **Ordinary range is not the common cause:** mean range ratio is 0.9817 in the worst decile and 1.0060 elsewhere. M6 already includes range and return terms; they do not remove the period pattern.
- **Splits are not the general explanation:** only one of 797 worst-decile cells has an opening gap over 20%; none of the other 7,166 cells does. Corporate-action quarantine remains necessary, but it cannot explain the broad residual regime.
- **Near-neighbour contradictions remain:** e.g. YESBANK 2025-03-18 and CAMS 2025-03-06 are close across 12 standardized public features (distance 0.163) yet scores differ 4.83 versus 3.65. These are approximate, not identical, so this supports underdetermination but does not prove it alone.

## 8. Is a missing non-bhavcopy variable required?

### Tests

1. **Order-size proxy test — positive.** `volume/num_trades` alone reaches Pearson 0.8348. Delivered quantity per trade (`delivery_qty/num_trades`) plus delivery percentage reaches 0.9612/0.9564. The transcript's “large quantity per order” explanation and the data agree on the input family.
2. **Turnover proxy test — redundant.** Average value per trade performs almost identically to average quantity per trade (0.8361 Pearson) and adds little once quantity/delivery enter. A turnover-only hidden leg is not the answer.
3. **Multi-day test — mostly screening, not score construction.** M4 ranks well because it contains current `q` and `d`; fitted 3-/4-day coefficients are tiny. The tutorial's multiday rules describe shortlist persistence rather than the daily-score formula.
4. **Cross-sectional/sector test — rejected as the primary numeric scale.** M5 has strong daily rank Spearman (mean 0.9526) but pooled Pearson only 0.8379; sector-rank coefficients are near zero. Cross-sectional ranks may support ordering but do not generate the displayed score.
5. **Broad public-field test — plateaus.** M6 uses all available OHLC, volume, turnover, trade-count, delivery, multiday, nonlinear, capped, and daily-rank information. It keeps 0.9711/0.9623 correlations in date-block holdouts, yet matches only 3.69% at two decimals and misses by as much as 2.4417.
6. **Fixed-formula calibration test — also fails exactness.** The best fixed benchmark matches 15.09% exactly. Good MAE and rank do not turn that plateau into formula recovery.
7. **Residual regime test — positive for versioning.** Error concentrates sharply before March 26. A fixed public-input mapping does not explain the same inputs consistently across the supplied period.

### Verdict on necessity

**Certain:** the supplied public fields are sufficient for a strong functional analogue and are insufficient for the tested exact-clone candidates.

**Likely:** exact reproduction requires a missing non-bhavcopy variable—most plausibly the distribution/upper tail of individual order or trade quantities described in the tutorial—and/or a source formula/feed version change around late March. Daily bhavcopy exposes only aggregate quantity and number of trades, so it gives a mean, not the large-order tail the presenter says the system catches.

**Unverified:** a non-bhavcopy variable is mathematically mandatory. An unknown, highly complex, date-dependent formula using only public fields could fit a finite panel. The experiment rejects the tested transparent bhavcopy families; it cannot prove nonexistence of every possible public-data mapping.

## 9. Reproducibility artifacts

- `_smf_codex/analyze_smf.mjs` — source loading, read-only DB query, feature construction, six fits, date-block holdouts, spike and residual analysis.
- `_smf_codex/results.json` — full metrics, fitted parameters, hashes, residual summaries, fixed analogue benchmarks.
- `_smf_codex/best_model_residuals.csv` — 7,963-cell M6 prediction/residual panel.
- `_smf_codex/verify_results.mjs` and `_smf_codex/verification.json` — independent one-pass covariance/rank recomputation. Maximum discrepancy from the primary metrics is `2.96e-14`; verification passes.
- `_smf_codex/TRANSCRIPT_FORMULA_EXTRACT.md` — canonical quote/translation layer.

## 10. End-state summary

- **Best fitted model:** M6 maximal nonlinear/capped bhavcopy-only ridge.
- **Best fitted correlations:** pooled Pearson **0.975024**, pooled Spearman **0.967330**; daily cross-sectional Pearson mean/median **0.976485 / 0.991786**; daily Spearman mean/median **0.971130 / 0.994258**.
- **Best fixed numeric benchmark:** `activity_v1`, Pearson/Spearman **0.971218 / 0.961864**, MAE **0.112144**, exact two-decimal share **15.0948%**.
- **Spike verdict:** ICICIBANK passes top-decile reproduction; RELIANCE fails because the vendor label itself is only at the 88.89th percentile.
- **Residual story:** misses concentrate overwhelmingly in the early block and at extreme activity; MCX is a vendor spike without a public average-order-size spike, while several March names have extreme public proxies but much lower vendor scores.
- **Final reproducibility verdict:** public NSE bhavcopy can reproduce a high-quality SMF analogue and ranking, **not the vendor Final Score exactly**. Fitted is not the vendor formula.

## Risks:

- The DB is live; the report records the historical snapshot read during this run, but a later rerun can change if those historical rows are rewritten.
- Five contiguous block holdouts measure stability, not a future-only production backtest.
- Sector metadata in M5 comes from the demo sheet and is not part of a strict bhavcopy-only pipeline; M6 excludes it.
- Near-neighbour contradictions are evidence of underdetermination, not proof of an unavailable variable.
- The transcript uses “order” and “trade” informally; bhavcopy `num_trades` may not match the vendor feed's event definition.
