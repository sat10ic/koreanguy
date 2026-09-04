# MBI-Style Breadth Backfill — Report

**Generated:** 2026-07-27 · **Script:** `manas_os/scripts/backfill_mbi_breadth.py`
**Source data:** `manas_os/data/manas.db` → `daily_prices` (series='EQ', close vs prev_close)
**Outputs:** table `mbi_breadth_daily` (source='manas_backfill') + `manas_os/data/mbi_breadth_backfill.csv`
**Reference sheet:** `…/stocksgeeks-book/_ledgers/MBI_sheet_main.csv` (trader's published MBI breadth)

This is a **new** dataset. The existing `breadth_daily` table (4% bands, niftymidsml400_bhavcopy,
1,246 rows) was left untouched and verified intact.

---

## 1. Headline verdict

- **Universe: all EQ-series symbols** (no liquidity filter). Simplest, fully reproducible,
  best/near-best on the most metrics. A bottom-quartile liquidity floor helped the 4.5%
  metric marginally on thin-history days but *worsened* the moving-average level match, so
  it was rejected as over-tuning.
- **Moving averages: SMA, not EMA.** SMA beats EMA vs the sheet on every window and both
  universe regimes, decisively at the long windows. **The sheet header ("sma") is correct;
  the conflicting "ema" claim is wrong.**
- **Reproducibility:** the sheet is **near-exactly reproducible on full-market days** and
  only *approximable* on days where our DB holds a thin core (see §3). The limiting factor
  is **data coverage, not method**.

---

## 2. Calibration table (our table vs sheet, overlapping dates)

`corr` = Pearson; `mae` = mean abs error (percentage points); `bias` = mean(ours − sheet).
280 dates overlap (2021-07-12 → 2026-07-21). Split by universe regime:

### Full-market days (universe_count > 1000; n = 63) — the meaningful comparison
| metric            | corr  | mae (pts) | bias  |
|-------------------|-------|-----------|-------|
| pct_up_4_5        | 0.993 | 0.29      | −0.22 |
| pct_down_4_5      | 0.996 | 0.38      | −0.35 |
| ratio_4_5 (4.5 r) | 0.972 | *(large — see note)* | |
| pct_above_sma10   | 0.921 | 3.06      | +2.87 |
| pct_above_sma20   | 0.894 | 3.75      | +3.68 |
| pct_above_sma50   | 0.988 | 3.19      | +3.19 |
| pct_above_sma200  | 0.802 | 4.68      | +4.68 |
| pct_52w_high      | 0.527 | 1.39      | +1.29 |
| pct_52w_low       | 0.730 | 0.34      | +0.28 |

On real full-market days the **4.5% up/down breadth is reproduced almost exactly**
(corr ≈ 0.99, error < 0.4 pt). MA metrics track well (corr 0.80–0.99) with a small,
consistent **+3 to +5 pt upward offset** — expected, since our exact universe and price
source (raw close, not corporate-action-adjusted) differ from the trader's.

### All overlap days (n = 280) — diluted by thin-core history
| metric           | corr  | mae   | bias  |
|------------------|-------|-------|-------|
| pct_up_4_5       | 0.863 | 2.09  | −1.91 |
| pct_down_4_5     | 0.880 | 1.80  | −1.62 |
| pct_above_sma50  | 0.959 | 5.05  | +3.08 |
| pct_above_sma200 | 0.930 | 8.43  | +7.53 |

The lower "all-days" correlations are an artifact of the pre-2024-09 thin universe
(~330 symbols → coarse 0.3%-per-stock granularity), **not** a method flaw.

### SMA vs EMA (full-market days, %-above)
| window | SMA corr | SMA mae | EMA corr | EMA mae |
|--------|----------|---------|----------|---------|
| 10     | 0.921    | 3.06    | 0.881    | 5.58    |
| 20     | 0.894    | 3.75    | 0.852    | 6.86    |
| 50     | 0.988    | 3.19    | 0.752    | 6.03    |
| 200    | 0.802    | 4.68    | 0.564    | 6.18    |

SMA wins on every row. **Verdict: SMA.**

> **Ratio MAE note:** `ratio_4_5` = 100·%up/%down blows up whenever %down is near zero
> (a single-digit count on a quiet day), so its MAE is meaningless; correlation (0.97) is
> the honest measure. Consumers should read the raw `pct_up_4_5`/`pct_down_4_5`, not the ratio,
> on low-volatility days.

---

## 3. Known gaps (NOT backfillable from this DB)

1. **History starts 2021-07-12.** The sheet goes back to 2015 (rows to `1.1.15`). All
   pre-2021-07 sheet rows are **not** reproducible from `daily_prices` — that data does
   not exist in this DB.
2. **Thin core before 2024-09.** From 2021-07 through Aug-2024 `daily_prices` holds only a
   continuous **~280–360-symbol core** (large/mid-cap), not the full market. Breadth % on
   those days is computed on that core and is coarser/noisier than the sheet's full-market
   figure (still directionally correlated, corr ~0.87). Full-market coverage (~1,850–2,500
   symbols) begins **2024-09**.
3. **Sporadic thin days after 2024-09.** ~15–20 scattered days (e.g. 2025-05-xx, 2026-01-xx,
   2026-05-xx) have only the core ~370–400 symbols ingested — days the full bhavcopy was
   missed. **`universe_count` is stored on every row** precisely so consumers can filter
   these out (e.g. `WHERE universe_count > 1000` for reliable full-market breadth).
4. **Raw (unadjusted) prices.** `daily_prices` close/prev_close are not corporate-action
   adjusted; the trader's source likely is. This is the main driver of the residual
   +3–5 pt MA offset.

---

## 4. Metric definitions & min-history handling

Per trading day, each metric's denominator is **its own** valid universe (stated choice):

- **pct_up_4_5 / pct_down_4_5** = % of symbols (with a valid prev_close) whose day-return
  is ≥ +4.5% / ≤ −4.5%. `ratio_4_5` = 100·pct_up/pct_down (the sheet's "4.5 r").
- **pct_above_smaW / emaW** (W = 10/20/50/200) = % above the MA, among symbols with **≥ W
  prior closes** (`min_periods=W`). Symbols lacking history are excluded from that window's
  denominator (denominators grow over time as symbols mature — matches how the sheet is kept).
  Both SMA and EMA columns are stored; **SMA is the calibrated primary**.
- **pct_52w_high / low** = % whose close equals the rolling 250-session max / min,
  `min_periods=100` (a symbol needs ≥100 sessions before it can register).

Rerunnable: the script drops+recreates `mbi_breadth_daily` and rewrites the CSV each run.

---

## 5. Spot-verification (independent second route: raw SQL COUNT vs pandas pipeline)

Direct `SELECT COUNT(...)` on `daily_prices` vs the values written to `mbi_breadth_daily`:

| date       | route | N    | up | down | %up    | %down  |
|------------|-------|------|----|------|--------|--------|
| 2021-12-01 | SQL   | 315  | 19 | 3    | 6.0317 | 0.9524 |
| 2021-12-01 | table | 315  | 19 | 3    | 6.0317 | 0.9524 |
| 2023-06-15 | SQL   | 337  | 15 | 1    | 4.4510 | 0.2967 |
| 2023-06-15 | table | 337  | 15 | 1    | 4.4510 | 0.2967 |
| 2026-07-21 | SQL   | 2390 | 87 | 30   | 3.6402 | 1.2552 |
| 2026-07-21 | table | 2390 | 87 | 30   | 3.6402 | 1.2552 |

**All three match exactly** (counts identical; ratio differs only in the 2nd decimal from
rounding %up/%down before dividing). For 2026-07-21 the sheet reads 4.05%up / 1.29%down; our
all-EQ gives 3.64 / 1.26 — down-side essentially exact, up-side 0.4 pt under, within the
approximation envelope (§2, full-market band).

---

## 6. Files

- Script: `manas_os/scripts/backfill_mbi_breadth.py`
- Table:  `mbi_breadth_daily` in `manas_os/data/manas.db` — 1,248 rows, 2021-07-12 → 2026-07-24
- CSV:    `manas_os/data/mbi_breadth_backfill.csv`
