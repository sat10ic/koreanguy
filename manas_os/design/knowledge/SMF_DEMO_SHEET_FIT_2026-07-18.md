# SMF demo-sheet fit — calibration via production `manas.db` (2026-07-18)

**Scope:** reproduce/calibrate the vendor's "SMF Final Score" using the demo sheet + tutorial transcript, this time computed through the live production database (`manas_os/data/manas.db`) rather than the archived bhavcopy CSVs used in the 2026-07-14 audit. Read-only sqlite connection (`mode=ro`) used throughout; no writes to the repo DB.

## 0. Premise corrections (stated task inputs that were wrong)

**Certain — both corrections independently verified against the DB, not assumed:**

1. **DB coverage does not start ~2025-03-19.** `PRAGMA table_info` + a direct query show `daily_prices` (series='EQ', source='bhavcopy') spans **2024-09-02 to 2026-07-17**, 428 distinct dates, with 162 valid sessions in the 2024-09-02→2025-04-29 window — full coverage for all 37 demo-sheet dates (2025-03-03 to 2025-04-29) plus the 20-session lookback each of them needs. This is not a partial-overlap problem; it is the same official history the 2026-07-14 audit used (that report cites "162 valid sessions from 2024-09-02 through 2025-04-29" against the standalone bhavcopy CSVs — the counts match exactly, confirming `manas.db` and the archived CSVs are the same underlying data).
2. **`num_trades` is present**, not absent. Schema: `daily_prices(symbol, trade_date, series, open, high, low, close, prev_close, last_price, avg_price, volume, turnover, num_trades, delivery_qty, delivery_pct, source, ingested_at)`. `avg_trade_qty = volume / num_trades` is computable directly; this is not a blocker.

Because of (1), every one of the 37 demo dates was fit, not a 28-date subset.

## 1. Tutorial extraction (translated from Hinglish/Devanagari; quotes marked as translation)

Source: `NoteGPT_Transcript_How To Track Smart Money Footprint In Indian Stock Market Proper Step By Step Video.txt` (209 lines), a live Q&A session by the score's creator ("Abhay ji" is named as the data provider; the presenter "Vivek ji" is a subscriber demonstrating usage, not the score's author).

**What inputs the score uses (mechanism, as stated):**
- Line 41 (translated): *"Suppose 100 orders per day are being punched for a company... and on average each order's quantity was, say, 50. But when a big investor comes in, he can't trade in 50-50 quantity lots — he has to place a much bigger order quantity. So he'll place a large quantity, and that is exactly where Abhay ji's system catches it. Wherever a big order lands, his data captures it immediately."* This is the entire stated mechanism: **abnormal average order/trade quantity relative to the stock's own normal activity.** No other input (delivery %, price range, turnover) is named anywhere in this transcript as a scoring component.
- Line 43-45 (translated): *"If it's 2.8, that means activity is running very slow — normal. My view is: below 3.5, whatever activity is happening is normal activity. And above 3.5, wherever a stock shows activity, that's abnormal — meaning some big institution is involved."* — confirms the **3.5 threshold = abnormal** convention already used in `activity.py` (`ABNORMAL_LEVEL = 3.5`).
- Line 197 (translated, Q&A): *"What do the highest and lowest numbers indicate? — Highest means there is great, highest abnormal activity; lowest means there is no abnormal activity happening in the market. That's simple: the higher, the more abnormal activity happening."* Confirms the score is a **monotonic, unbounded activity magnitude**, not a bounded index.
- Line 205 (translated, Q&A, formula secrecy): *"How the data is calculated, what basis it's built on — I cannot tell you that, because that is my product."* The creator explicitly refuses to disclose the formula. No component weights, normalization method, or lookback window are ever given numerically.

**Persistence / filtering workflow (how the vendor actually uses the sheet, lines 47-57, translated):** filter last 3 days' scores > 3.5 → too many hits (200+) → tighten to >4 → still ~123 companies → tighten further (>5, or extend the day count) until the watchlist is small. This is a **user-side filter recipe**, not a scoring formula; it does confirm multi-day persistence is treated as a stronger signal than a single-day spike (also stated directly at lines 107-109: *"if activity happens on just one day... there can be a sharp move. But when such activity continues across multiple days, the stock will take a bigger range in whichever direction it goes"*).

**What is explicitly NOT in the free demo sheet (line 179, translated):** *"They're trying to add price and volume to the data sheet... if possible in future, it will definitely happen."* — confirms OHLCV was not yet a sheet column at recording time; the score sheet is score-only.

**Corporate actions (lines 61-65, 103-105, translated):** post-split data must be excluded — *"After a split you should not consider this data, because before that the stock's price was different, now the price is lower so activity will naturally look higher."*

**Direction is not in the score (line 167, translated):** *"This data is telling you activity, not telling you direction. Who tells you direction? Putting on the Volume Profile"* — the score-plus-chart workflow (Fixed Range Volume Profile) that occupies most of the transcript is entirely about **inferring direction after the score flags a stock**, and is a separate, chart-based tool, not a scoring input.

**Delivery %** is never mentioned in this transcript as a score input. (A separate marketing-screenshot addendum recorded in `SMF_DATA_COMPLETE_REVERSE_ENGINEERING_2026-07-14.md` §ADDENDUM 2026-07-18 shows the vendor's own dashboard computing a delivery metric from user-uploaded bhavcopy — but that is a display panel, not confirmed as a Final Score input. Using delivery_pct in our analogue is **our own modelling choice**, not a tutorial-sourced fact.)

## 2. Feature definitions (built from `daily_prices`, point-in-time only)

For each (symbol, date) with ≥20 prior bhavcopy sessions on or before that date:

```
avg_trade_qty(t)      = volume(t) / num_trades(t)
q_ratio(t)  = avg_trade_qty(t) / mean(avg_trade_qty, inclusive 20-session window ending t)
d_ratio(t)  = delivery_pct(t)  / mean(delivery_pct, prior 19-session window before t)
```

This is exactly `activity.py`'s `_score()` logic, run independently against `manas.db` via a read-only connection rather than importing the module.

## 3. Panel built

- Demo sheet parsed: 1,627 symbol rows × 37 date columns = 55,613 numeric score cells (matches the 2026-07-14 audit's independent parse exactly).
- `daily_prices` rows loaded (≤2025-04-29, EQ/bhavcopy, complete fields): 319,796 rows, 2,301 symbols.
- Feature rows with ≥20-session history on a demo date: 53,862.
- **Matched (symbol, date) pairs with both a demo score and our feature**: **53,280** — 1,478 symbols × all 37 dates. This is the identical observation count reported by the 2026-07-14 audit against the standalone CSVs, confirming `manas.db` reproduces that same official-data panel.

## 4. Fit table

| Model | Pooled Pearson | Pooled Spearman | Mean per-day cross-sectional Spearman (37 days) | MAE |
|---|---:|---:|---:|---:|
| **v2 — production `sat10ic_eod_activity_v2`** (as-is, no refit; calibrated on unrelated July 2026 screenshots) | 0.9779 | 0.9689 | 0.9779 | 0.1377 |
| v1 — 2026-07-14 full-panel exact-clone-search fit (`1.1049q + 1.0100d + 1.1731(qd)^0.825 − 0.14`) | 0.9777 | 0.9689 | 0.9778 | 0.1324 |
| q+d OLS — plain linear combo, same two features, no interaction term | 0.9733 | 0.9664 | 0.9751 | 0.1640 |
| q-only OLS — tutorial's *sole named* mechanism (avg-trade-qty ratio), single feature | 0.8855 | 0.8220 | 0.8137 | 0.3640 |

**Reading this honestly:**
- v1 and v2 are near-identical here even though v2 was never fit against this panel — it was calibrated on 15 unrelated July-2026 screenshot scores. That v2 still tracks the March/April demo sheet at Spearman 0.969 is a genuine out-of-sample validation of the two-feature (q, d) family, not a re-statement of the original in-sample v1 fit.
- Adding `d_ratio` (delivery participation) is doing real work: q-only OLS Spearman drops to 0.82 pooled / 0.81 per-day cross-section, versus ~0.97 with both features. This matters because **delivery is not a tutorial-stated input** — it is sat10ic's own addition, and it is empirically necessary to reach the ~0.97 correlation band. The tutorial's stated mechanism alone (order-size proxy) is a real but incomplete predictor.
- Rank correlation this high (~0.97) is **not** the same claim as the 2026-07-14 audit's "exact-clone" gate, which required exact two-decimal reproduction and found only 12.33% of cells matched exactly, with a worst-case error of 16.2. Both reports are consistent: the *ranking/relative-magnitude* structure of the vendor score is well captured by (q, d); the *exact numeric formula* is not recovered. This document does not re-run the exact-clone search — see that report for the full 7,500+-configuration search and its negative result.

## 5. Spike reproduction check

| Symbol | Date | Demo "Final Score" | Our q | Our d | Our v2 score | Cross-section size | Our v2 percentile |
|---|---|---:|---:|---:|---:|---:|---:|
| ICICIBANK | 2025-03-21 | 8.07 | 3.126 | 1.185 | **8.130** | 1,438 | **98.9th** |
| RELIANCE | 2025-03-21 | 5.29 | 1.762 | 1.238 | **5.351** | 1,438 | **93.0th** |

Both named spikes reproduce as top-decile in our v2 cross-section on the same date, and the absolute score values are within 0.06 (ICICIBANK) and 0.06 (RELIANCE) of the demo sheet — closer than the model's own average error (MAE 0.138) would predict. These two points are not cherry-picked in our favor beyond being the two the task specified; they were not used to fit v1, v2, or either OLS model above.

## 6. Honesty checks per the task's rules

- Fit does **not** plateau: pooled and per-day Spearman are ~0.97, well above the 0.6 "missing-variable-hypothesis-stands" bar. The two-feature (q, d) family is a strong ranking analogue.
- `num_trades` is present in `daily_prices` — **not** a blocker, contrary to the task brief's caveat. It has been the load-bearing column since `activity.py` v1.
- The one real missing piece, unchanged from the 2026-07-14 audit, is **exact-formula recovery**: 12.33% of cells match to 2 decimals, mean absolute error 0.13, and the March 20-26 period boundary in the source score behaves discontinuously (2.04% exact pre-boundary vs 21.80% exact post-boundary) — evidence of a hidden component, version change, or upstream feed change that (q, d) from aggregate bhavcopy cannot see (individual order size distribution, aggressor side, intraday sequence, or volume-at-price). This document reproduces that conclusion through the production DB path; it does not add new evidence resolving it.
- No fitted constant here is presented as "his formula." All four rows in the fit table are explicitly labelled as analogues/OLS fits, not the vendor's calculation.

## 7. Verdict

**Certain:** a calibrated two-feature analogue (avg-trade-qty ratio × delivery-ratio, nonlinear interaction — i.e., the existing `activity.py` v2) tracks the vendor's SMF Final Score at Spearman ≈0.97 pooled and per-day, on the full 53,280-observation demo panel, computed live from `manas.db`. Both magnitude spikes named in the task (ICICIBANK 8.07, RELIANCE 5.29, both 2025-03-21) land in our top-decile with near-exact score agreement.

**Certain:** the tutorial itself names only one scoring mechanism — abnormal average order/trade quantity — and explicitly withholds the formula. Delivery ratio is sat10ic's own addition; it is not sourced from this transcript, but it is empirically load-bearing (q-only Spearman 0.82 vs q+d 0.97).

**Likely (carried over from 2026-07-14, unchanged by this check):** the residual gap between "0.97 rank correlation" and "12% exact match" is a hidden variable and/or a source-side formula/feed change around 20-26 March 2025, not recoverable from aggregate bhavcopy fields.

**Verdict on viability:** the existing v2 analogue is viable as an **institutional-footprint ranking/flagging signal alongside our scans** — it reproduces the vendor's relative ordering and named spikes convincingly on real, out-of-sample-calibrated data pulled straight from production. It is **not** viable as a claim of formula equivalence, and must keep shipping with the existing shadow-only, direction-neutral, "abnormal activity, not institutional identity" framing already enforced in `activity.py` and the 2026-07-14 report's product-decision section.

**Exact next step, if any:** none required to keep using v2 as a ranking/flagging signal — it already clears this bar. Further work is warranted only if/when new evidence becomes available (per the 2026-07-14 report's §15 resumption checklist: original formula/component definitions, raw pre-final-score columns, the same tick/footprint feed, or explicit clarification of what changed around 20-26 March 2025). No broad coefficient re-search is justified from this data alone.

## Risks

- Spearman ≈0.97 is a strong ranking match but was computed on the same historical panel the vendor labelled; it says nothing about forward alpha, which remains untested (per 2026-07-14 report §14).
- The two named spike checks are a n=2 confirmation, not a systematic extreme-value audit; a fuller top-decile precision/recall pass across all 37 dates was not run here (out of this task's 35-tool-call budget) and would strengthen the "spikes reproduce" claim if needed later.
- Delivery ratio's empirical necessity does not prove the vendor's real formula uses delivery — it is equally consistent with delivery acting as a correlated proxy for whatever the vendor's actual second input is.
- This document does not repeat or supersede the 2026-07-14 audit's exact-clone search; it validates that search's data pipeline reproduces identically through the production DB and extends it with an out-of-sample v2 check plus the two requested spike checks.

## Sources / artifacts

- `C:\Users\satta\Downloads\DEMO SHEET - MARCH APRIL - Sheet1.csv`
- `C:\Users\satta\Downloads\NoteGPT_Transcript_How To Track Smart Money Footprint In Indian Stock Market  Proper Step By Step Video.txt`
- `C:\Users\satta\Downloads\koreanguy\manas_os\data\manas.db` (read-only)
- `C:\Users\satta\Downloads\koreanguy\manas_os\alpha\activity.py`
- `C:\Users\satta\Downloads\koreanguy\manas_os\design\SMF_DATA_COMPLETE_REVERSE_ENGINEERING_2026-07-14.md`
- Analysis script (scratch, not committed): `smf_fit.py` in this session's scratchpad
