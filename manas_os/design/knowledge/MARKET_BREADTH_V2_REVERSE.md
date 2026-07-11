# Market Breadth V2.0 — Reverse-Engineering Spec

Reverse-engineering of **`manas_os/design/study/Market Breadth V2.0.xlsm`** (Chhirag
Kedia's "Market Breadth Monitor V 2.0", `@swing_ka_sultan`) + two Chartink dashboards
(`chartink.com/dashboard/11543`, `.../10361`), mapped against what Manas OS already
computes, to produce a build spec of NEW datapoints / analytics / visualizations for the
regime panel.

Sources of record for the mapping:
- `manas_os/regime/snapshot.py` — MBI ratios (r10/r20/r50/r4p5), bands, day-color, warning-day, four-phase, quadrant.
- `manas_os/regime/xp.py` — XP dial recursion (finallynitin weighting).
- `manas_os/sources/breadth_sheet.py` — the Google-sheet columns we ingest into `breadth_daily`.
- `manas_os/db/schema.sql` — `breadth_daily`, `regime_snapshots`, `regime_universe_metrics`, `sector_metrics`, `sector_index_prices` tables.
- `manas_os/desk/src/viz.js` — plain-SVG render idioms already available (`sparklinePoints`, `colorScale`, `squarifyTreemap`, `REGIME_GAUGE_ZONES`); no chart libs.
- `manas_os/desk/src/DeskTab.jsx` `RegimeStrip` — current regime tiles (confirmed gap at lines ~119-124: **no historical XP/regime series is fetched anywhere on the page**, so the XP trend arrow was removed rather than faked).

**Tag legend:** `[HAVE]` already computed/persisted · `[COMPUTE]` derivable from existing
tables, no new ingest · `[NEW-DATA]` requires a data source we do not currently ingest.

> **Framework note (read first):** This workbook is a *count-and-ratio breadth monitor*. It
> contains **no XP and no MBI column** — those are separate constructs in Manas OS (XP =
> finallynitin recursion; MBI = our snapshot.py bands). The workbook's own headline
> composite is the **High-Low Logic Index (Fosback)**, plus Stockbee 5/10-day ratios and
> 52-week-high/low structure. So this is additive breadth *depth*, not a re-derivation of
> XP/MBI. See NEEDS FABLE/HUMAN.

---

## 0. Workbook structure (what's inside the zip)

| Part | Contents |
|---|---|
| `xl/worksheets/` | 12 sheets: **Filters, Dashboard, Dashboard Charts, Breadth, Breadth Charts, Market Map, MM Charts, Sectoral, Data, SBE (hidden), Rough Work, Version History** |
| `xl/charts/` | **52 charts** (`chart1..52.xml`) + paired `styleN`/`colorsN`. All line/bar/combo — no gauge, scatter, area, or pie. |
| `xl/drawings/` | 3: `drawing1`=Dashboard Charts (charts 1-16), `drawing2`=Breadth Charts (17-32), `drawing3`=MM Charts (33-52) |
| `xl/pivotCache/` | **none** (no pivot tables) |
| `xl/vbaProject.bin` | **present, 52,224 bytes** — macro logic may live here; not decompiled. Likely the "paste today's counts" / refresh automation. Flag: derived logic *could* hide here, but every visible analytic is a worksheet formula (below). |
| `xl/externalLinks/externalLink1.xml` | one stale external-workbook link (see NEEDS FABLE) |

**Data flow:** `Data` (raw pasted counts, no formulas, one row/day since 2004-01-01) →
`SBE` (index levels, %chg, 5-day ROC, date-windowed copies) + `Breadth` (ratio engine) +
`Market Map` (52wk structure) + `Sectoral` (sector ROC) → `Dashboard`/`Filters`
(consolidated display table) → 52 charts driven by **date-windowed named ranges** keyed to
the `Dashboard Charts!$B$2` (From) / `$B$3` (Till) selector cells. Every chart auto-rescales
to that window.

---

## 1. Datapoint inventory (tagged)

### 1A. `Data` sheet — raw daily counts (the ground-truth inputs, cols A-BI)

| Datapoint | Manas status | Where / how |
|---|---|---|
| Date/Time | `[HAVE]` | `breadth_daily.trade_date` |
| Nifty 50 level | `[HAVE]` | `breadth_daily.nifty` |
| Small Cap 100 level | `[NEW-DATA]` | not ingested (we track NIFTYMIDSML400 in market context, not SMLCAP100) |
| Total Universe (count) | `[NEW-DATA]` | workbook normalizes everything by this; we store no daily universe size |
| 4% Up / 4% Down (counts) | `[HAVE]` | `breadth_daily.up_4pct` / `down_4pct` |
| High Vol / Low Vol counts (>1.5×20DMA / <0.5×20DMA) | `[NEW-DATA]` | not ingested |
| Range <3% (contraction) / Range 5.01%+ (expansion) | `[NEW-DATA]` | not ingested |
| Close Upper Half / Close Lower Half | `[NEW-DATA]` | not ingested |
| Breakouts / Breakout Sustained / Breakout Failure | `[NEW-DATA]` | not ingested |
| Breakdowns / Breakdown Sustained / Breakdown Failure | `[NEW-DATA]` | not ingested |
| 15% up in 5 days / 15% down in 5 days | `[NEW-DATA]` | we have 25%/50% *monthly*, not 15%/5-day |
| 25% up/down in 20 days | `[COMPUTE?]` | close cousin of `up_25pct_month`/`down_25pct_month` (window differs 20d vs "monthly") — confirm window before reuse |
| 10% above / below 10 DEMA (counts) | `[NEW-DATA]` | not ingested (distinct from % *above* 10 DEMA) |
| Above 10 / 20 / 50 / 200 DEMA (counts) | `[HAVE]` for 10/20/50; `[NEW-DATA]` for 200 | `pct_above_10dma/20dma/50dma`; **200-DMA not stored** |
| 52 Week High / 52 Week Low (counts) | `[NEW-DATA]` | not ingested — gates NH-NL and HL-Logic |
| 15/30/50/70/70%+ from 52WH (distance buckets) | `[NEW-DATA]` | not ingested |
| 15/30/50/90/150/150%+ from 52WL (distance buckets) | `[NEW-DATA]` | not ingested |
| Per-sector Nifty sub-index levels (Auto…Service) | `[COMPUTE]` | `sector_index_prices.close` holds sector index closes |

### 1B. `Breadth` sheet — normalized ratios (fraction of universe)

| Datapoint | Manas status | Notes |
|---|---|---|
| 4% Up% / 4% Down% (as fraction of universe) | `[COMPUTE]` | we store counts, not universe → % needs universe size `[NEW-DATA]`; but the burst *ratio* r4p5 = up/down `[HAVE]` |
| **Net Breadth** `(up% − down%)×100` | `[COMPUTE]` | classic A-D; from `advances`/`declines` or up_4pct/down_4pct |
| **5 Day Ratio** (Stockbee) | `[COMPUTE]` | rolling: Σ5(4%up) / Σ5(4%down) — from `breadth_daily` history. **NEW** (we only have single-day r4p5) |
| **10 Day Ratio** (Stockbee) | `[COMPUTE]` | rolling Σ10/Σ10 |
| Above/Below avg volume %, Vol Ratio | `[NEW-DATA]` | |
| <3% Range%, >5.01% Range%, **Volatility Ratio** = exp/contract | `[NEW-DATA]` | candidate feed for our currently-UNKNOWN volatility pillar |
| Close >50% / <50%, **UH/LH Ratio** `(P−Q)×100` | `[NEW-DATA]` | thrust indicator on expansion days |
| BO/BD Ratio, Breakouts%, Up-Close%, BO S/F Ratio | `[NEW-DATA]` | |
| Breakdown%, Down-Close%, BD S/F Ratio | `[NEW-DATA]` | |

### 1C. `Market Map` sheet — 52-week structural breadth

| Datapoint | Manas status | Notes |
|---|---|---|
| N52WH% / N52WL% | `[NEW-DATA]` | `regime_universe_metrics` has `new_highs`/`new_lows` columns **but they are unpopulated** (reserved) |
| **Net NH-NL** `(NH%−NL%)×100` | `[NEW-DATA]` | classic new-high/new-low line — highest-value missing breadth series |
| Net 15% H-L, Net 30% H-L | `[NEW-DATA]` | |
| 15/30/50/70/70%+ from 52WH (%) | `[NEW-DATA]` | |
| 15/30/50/90/150/150%+ from 52WL (%) | `[NEW-DATA]` | |
| **HL Logic Calc** = min(NH%,NL%)×100 | `[NEW-DATA]` | daily component |
| **HL Logic Index** = 10-day avg of HL Logic Calc | `[NEW-DATA]` | **Fosback High-Low Logic Index** — workbook's flagship topping/distribution signal |

### 1D. `Sectoral` / `SBE` sheets

| Datapoint | Manas status | Notes |
|---|---|---|
| Per-sector 5-Day ROC% (19 Nifty sub-indices) | `[COMPUTE]` | from `sector_index_prices.close` (5-row % change); `sector_metrics.rs_score` is a related-but-different measure |
| Nifty / SmallCap %chg, 5-Day ROC | `[HAVE]`/`[COMPUTE]` | Nifty %chg = `nifty_chg_pct`; 5-day ROC computable from `nifty` history; SmallCap `[NEW-DATA]` |

### 1E. `pct_10dma_gt_20dma`, `pct_20dma_gt_40dma`

`[HAVE]` and **NOT in the workbook** — these are a Manas-only trend-breadth pair we already
ingest (used by `compute_pillars` trend proxy). No action; noted so we don't "add" them.

### 1F. Chartink dashboards (visual reference)

**Dashboard 11543 ("Atlas Market Matrix")** — 20 widgets, publicly viewable (no login), but
**10 chart widgets failed to render** unauthenticated (premium realtime gate); their visual
sub-type is inferred from titles only. Breadth-relevant widgets:

| Widget | Data | Viz | Manas status |
|---|---|---|---|
| % abv 20 / 50 / 200 SMA | % of stocks above each SMA | gauge/chart (didn't render) | 20/50 `[HAVE]`, 200 `[NEW-DATA]` |
| % at 52-wk high / low | % of universe at extremes | gauge | `[NEW-DATA]` |
| New high vs low count | NH vs NL bar/line | chart | `[NEW-DATA]` |
| Stocks above/below VWAP | intraday breadth split | gauge/donut | `[NEW-DATA]` (intraday, out of EOD scope) |
| Intraday % abv Pivot | intraday breadth | chart | `[NEW-DATA]` (intraday) |
| Futures Advancing vs Declining | A/D for futures | donut/bar | `[NEW-DATA]` |
| RSI distribution | histogram of RSI | chart | `[NEW-DATA]` |
| Monthly Sector Advances % | sector ranking | **table (rendered)** | `[COMPUTE]` from `sector_index_prices` / `sector_metrics` |
| Index stats / Top gainers / losers | Nifty/BankNifty LTP, movers | tables | `[HAVE]` via market context |

**Dashboard 10361 ("Atlas Nitin Agarwal-85")** — 11 widgets, **all ticker-list scan tables**
(5-min breakouts, 1-min volume surge, near circuits, RSI oversold, above VWAP, 52-wk-low
proximity). No aggregate breadth visualizations. These are *scanner* outputs, not regime
breadth — **out of scope for the regime panel** (they map to the scanner tab, not here).

**Net from Chartink:** the only regime-panel-relevant additions beyond the workbook are the
**% above SMA gauges** and **% at 52wk high/low gauges** as a compact gauge idiom — but every
underlying datapoint is already covered by the workbook inventory above. No unique new
datapoint. VWAP/pivot/RSI-distribution are intraday and out of EOD scope.

---

## 2. Analytics / formula inventory

Formulas are the literal worksheet formulas (row 3 pattern; `$F`/`$D` = day's universe
count). "Manas compute" = how to reproduce here.

| Analytic | Workbook formula (verbatim) | Plain English | Manas compute |
|---|---|---|---|
| **Net Breadth** | `=(E3−F3)*100` where E=4%up%, F=4%down% | Advancers minus decliners (thrust), ×100 | `[COMPUTE]` `(up_4pct−down_4pct)` or `advances−declines`; ×100 needs universe. Store as line. |
| **5 Day Ratio** (Stockbee) | `=SUM(E3:E7)/SUM(F3:F7)` | 5-day sum of strong-up ÷ 5-day sum of strong-down; >1 bullish thrust, mean-reversion tool | `[COMPUTE]` rolling window over `breadth_daily.up_4pct/down_4pct`. **NEW** — we only have single-day `r4p5`. |
| **10 Day Ratio** | `=SUM(E3:E12)/SUM(F3:F12)` | 10-day version, smoother regime read | `[COMPUTE]` same, window=10 |
| **Volume Ratio** | `=J3/K3` (aboveAvgVol% / belowAvgVol%) | Participation-by-volume ratio | `[NEW-DATA]` |
| **Volatility Ratio** | `=O3/M3` (expansion% / contraction%) | Range-expansion vs contraction — a breadth-based volatility gauge | `[NEW-DATA]`; **candidate to fill the UNKNOWN volatility pillar** in `compute_pillars` |
| **UH/LH Ratio** | `=(P3−Q3)*100` on expansion days | Net upper-half vs lower-half closes ×100; intraday conviction | `[NEW-DATA]` |
| **BO/BD Ratio** | `=T3/Y3` | Breakouts ÷ breakdowns | `[NEW-DATA]` |
| **Breakout S/F Ratio** | `=V3/W3` (sustained/failed) | Follow-through quality of breakouts (sustained = close within 40% of range from high) | `[NEW-DATA]` — high methodology value (Stockbee/Arora follow-through) |
| **Breakdown S/F Ratio** | `=AA3/AB3` | Mirror for breakdowns | `[NEW-DATA]` |
| **Up Close %** | `=E3/T3` | Of breakout stocks, fraction that also closed 4%+ | `[NEW-DATA]` |
| **Net NH-NL** | `=(G3−H3)*100` (NH%−NL%) | New-highs minus new-lows breadth line — canonical regime health | `[NEW-DATA]` (need NH/NL counts) |
| **Net 15% H-L** | `=(L3−Q3)*100` | Net(within-15%-of-high − within-15%-of-low) | `[NEW-DATA]` |
| **Net 30% H-L** | `=((L3+M3)−(Q3+R3))*100` | Cumulative within-30% net | `[NEW-DATA]` |
| **HL Logic Calc** | `=(IF(G3<=H3,G3,H3))*100` | Daily min(NH%,NL%)×100 | `[NEW-DATA]` |
| **HL Logic Index (Fosback)** | `=AVERAGE(W3:W12)` | 10-day SMA of daily min(NH%,NL%). High = many stocks hitting *both* new highs AND new lows simultaneously = internal split / distribution / topping | `[NEW-DATA]` — needs NH/NL counts, then trivial rolling mean |
| **% Change** | `=((B3−B2)/B3)` | 1-day index return | `[HAVE]` `nifty_chg_pct` |
| **5-Day ROC** | `=((B7−B2)/B2)` | 5-bar rate of change (index & each sector) | `[COMPUTE]` from `nifty`/`sector_index_prices` history |
| **Chart date-window** | `INDEX(col, MATCH(From)):INDEX(col, MATCH(Till))` per named range | Every series is a dynamic slice between From/Till selector cells | Our analog: an `/api/regime/history?from&to` window param |
| **Axis floor** | `=ROUND(MIN(range)*0.95,2)` | Y-axis floor at 95% of windowed min, for readable index overlays | Render detail for dual-axis overlays |

**Manas analytics NOT in the workbook (keep, don't duplicate):** XP recursion (`xp.py`),
MBI bands & day-color & warning-day (`snapshot.py` `compute_mbi`), four-phase classifier,
choppy brake, HMM confirmation, quadrant. The workbook has none of these — they are the
Manas layer *on top of* this kind of breadth data.

---

## 3. Visualization inventory (52 charts → regime-panel candidates)

All charts are **line / bar / combo, dual-axis where an index is overlaid**. No gauges, no
shaded threshold bands (buckets are separate line series, not shaded regions), no trendlines.
Consistent color code: green=`00B050` bullish, red=`FF0000` decline, yellow=`FFFF00`
secondary index, orange=`FFC000` failure/lower-half, blue=`4472C4` HL-Logic bars.

| # | Title | Type | Series (named range) | Manas status of series | Regime-panel candidate |
|---|---|---|---|---|---|
| 1 | Net Breadth (G) + Volume (Y) | combo bar+bar | netbreadth, volume | COMPUTE / NEW | ✔ net-breadth line |
| 2 | Net UH/LH Ratio | bar | rer | NEW | |
| 3 | **Above 10 DEMA** | line | abvten | HAVE (`pct_above_10dma`) | ✔ trend line + band |
| 4/5 | **Above 50 / 200 DEMA + Nifty** | combo line, dual-axis | abvffty/abvthndr + Nifty | 50 HAVE, 200 NEW | ✔ flagship (50 now, 200 later) |
| 6/7 | Above 50/200 DEMA + SmallCap | combo line | + smlcap | NEW (smlcap) | |
| 8 | **Above 20 DEMA** | line | abvtwnty | HAVE (`pct_above_20dma`) | ✔ |
| 9 | 10% Up from 10 DEMA | bar | tnuptn | NEW | |
| 10 | **4% Advance (G) / 4% Decline (R)** | bar (2 series) | up4perc/down4perc | HAVE (counts) | ✔ A/D bars |
| 11 | **5 Day Ratio / 10 Day Ratio** | combo bar+line | fivdr/tndr | COMPUTE | ✔ Stockbee ratio line |
| 12/13 | 15% up in 5d / 10% down in 5d | bar | upfftn/dnten | NEW | |
| 14 | 10% Up/Down from 10 DEMA | bar | tndntn (one series only) | NEW | (see NEEDS FABLE) |
| 15 | Nifty 50 + SmallCap 100 | combo line | Nifty/smlcap | HAVE/NEW | |
| 16 | **Net New High / New Low** | bar | nhnl | NEW | ✔ (needs NH/NL) |
| 17 | BO/BD Ratio | line | bobd | NEW | |
| 18 | Volume Ratio | line | volume(=Breadth!L VolRatio) | NEW | |
| 19 | Range Expansion | line | re | NEW | |
| 20-32 | Breakouts / UH / LH / vol / BO&BD sustained/failure & ratios | line | breakout, rep, ren, abvol, blvol, bos, bof, bds, bdf, bosf, bdr | NEW | S/F ratios high-value |
| 33-41 | Nifty/SmallCap + 52wk-H/L distance & ratios | combo line | fwhfftn, fwlfftn, nfftytwoh/l, fftnratio, thrtyratio | NEW | |
| 42-50 | 52wk distance buckets (15/30/50/70/90/150%) | line | thrtyfrmh, fftyfrmh, svntyfrmh, byndsvnty, fftnfrmlow, thrtyfrml, fftyfrml, nntyfrml, onefftyfrml, byndoneffty | NEW | distribution/accumulation histogram candidate |
| 51/52 | **Nifty / SmallCap (Y) + HL Logic Index (B)** | combo bar+line, dual-axis | HLLI + Nifty/smlcap | NEW | ✔ Fosback overlay (needs NH/NL) |

**Idiom to reuse for all of these (no new libs):** `viz.js`'s `sparklinePoints()` for the
line paths, a small `<rect>` band layer for thresholds, `colorScale()` for green/red
intensity, and the `REGIME_GAUGE_ZONES` pattern for the day-color ribbon. Dual-axis index
overlays = two `sparklinePoints` calls sharing a viewBox with independent min/max.

---

## 4. Prioritized "add to regime panel" shortlist

Ranked by (value to a beginner-legible-but-detailed regime read) × (buildable now from data
we already persist). The user specifically asked for **medium/short-term TREND views of XP and
MBI** — items 1-3 deliver exactly that and are all `[COMPUTE]` from `regime_snapshots` history
(which is already written daily but never read back for a series). This directly closes the
`DeskTab.jsx` gap where the XP trend arrow was removed for lack of a series.

**Prereq for #1-4:** one new read endpoint `GET /api/regime/history?from=&to=` returning the
last N `regime_snapshots` rows (`snapshot_date, xp_value, xp_z_state, mbi_day_color,
warning_day, r10, r20, r50, r4p5, market_mode, four_phase_json`). No new compute, no new
ingest — pure SELECT. This is the single unlock.

1. **XP trend line (medium-term)** — `[COMPUTE]` from `regime_snapshots.xp_value` over
   60-90d. Plain-SVG line (`sparklinePoints`) with 4 horizontal threshold **bands** drawn as
   `<rect>`s at the existing `xp_band` cutoffs (LOW<15, BUILDING<40, STRONG<100, EXTREME) from
   `snapshot.py`. Endpoint dot colored by `colorScale`. **This is the #1 add** — it's the
   flagship dial and today it has zero history on screen.

2. **MBI day-color ribbon** — `[COMPUTE]` from `regime_snapshots.mbi_day_color` history. A
   horizontal strip of daily cells (green/white/red `<rect>`s, one per session), mirroring
   the workbook's "day-color" concept and directly showing regime persistence/turns at a
   glance. Warning-days (`warning_day=1`) get a marker. Reuses `DAY_COLOR_HEX` already in
   `DeskTab.jsx`. Beginner-legible, dense, cheap.

3. **Breadth-ratio trend (r10 / r20 / r50)** — `[COMPUTE]` from persisted `r10/r20/r50`. Small
   multiples or one multi-line SVG with the existing band thresholds (75 green / 50 white per
   `band_ratio`; 85/60 for r50 per `band_r50`) shaded as `<rect>`s. This is the Manas analog
   of the workbook's "Above 10/20/50 DEMA" line charts (charts 3,4,8) and turns four static
   tiles into trend context.

4. **5-Day / 10-Day Ratio (Stockbee)** — `[COMPUTE]` NEW analytic from
   `breadth_daily.up_4pct/down_4pct` rolling sums. Line with a `1.0` reference line. High
   methodology value: the backbone is Stockbee/Arora and Version History explicitly credits
   "used by Stock Bee". Gives a smoothed thrust read the single-day `r4p5` can't. Compute in
   a small helper (mirrors `burst_ratio`), persist or compute-on-read.

5. **Net Advance-Decline line + cumulative A-D** — `[COMPUTE]` from
   `breadth_daily.advances/declines` (or up_4pct/down_4pct). Daily net-breadth bars (chart 1/10
   idiom) plus a **cumulative A-D line** (running sum) as a McClellan-style trend backbone.
   Classic, beginner-recognizable, and entirely from data on hand.

**High-value but `[NEW-DATA]` (stage behind an ingest task, not buildable now):**
- **% above 200 DMA + Nifty overlay** (workbook charts 5/7) — the single most-cited long-term
  regime chart; needs a `pct_above_200dma` feed (the schema comment already anticipates a
  "Participation panel"; column exists on `breadth_daily` as `pct_above_50dma` only).
- **Net NH-NL line** and **Fosback HL Logic Index** (charts 16/51/52) — need daily
  new-52wk-high / new-low counts. `regime_universe_metrics.new_highs/new_lows` columns exist
  but are unpopulated — populate them and both analytics fall out cheaply (HL-Logic = 10-day
  mean of min(NH%,NL%)).
- **Volatility Ratio** (expansion%/contraction%) — could finally fill the structurally-UNKNOWN
  volatility pillar in `compute_pillars`; needs range-bucket counts.
- **52-week distance-bucket histogram** (charts 42-50) — an accumulation/distribution profile;
  needs the from-52WH/WL bucket counts.

---

## 5. NEEDS FABLE / HUMAN

Do not guess these — the maintainer resolves:

1. **Framework reconciliation (biggest one).** This workbook (Chhirag Kedia / Kedia
   Mentorship) contains **no XP and no MBI**. Manas's XP (`xp.py`, finallynitin weighting) and
   MBI (`snapshot.py` bands) are *different* constructs bolted onto similar breadth inputs.
   Decision needed: do we (a) keep XP/MBI as the headline and treat the workbook's
   HL-Logic/Stockbee-ratio/NH-NL analytics as *supporting depth*, or (b) surface the workbook's
   own composites as co-equal regime reads? The shortlist above assumes (a). Confirm.

2. **`VOLUME` vs `ABOVE 10 MA` col-25 collision.** On `Filters`/`Dashboard`, both column L
   ("VOLUME") and column AD ("ABOVE 10 MA") read `Data!` **column 25** (`Above 10 DEMA` per
   the Data header). The "VOLUME" series therefore looks miswired/mislabeled in the source
   workbook. Is chart 18's "Volume Ratio" the intended series, or is VOLUME meant to point at a
   real volume column? Reported as-found, not fixed.

3. **Chart 14 ("10% Up (G) / Down (O) from 10 DEMA")** exposes only one data series (`tndntn`)
   in the XML despite a two-color/two-series title. Second series may have been deleted with the
   title left stale, or overridden via a mechanism the parse didn't capture. Confirm intent
   before replicating.

4. **`n52wh` stale external link.** The `n52wh` defined name points at
   `'[1]Dashboard Charts'!$B$2` (external `externalLink1.xml`) while its near-duplicate
   `nfftytwoh` uses the local sheet. `n52wh` looks like a stale copy from the workbook this file
   was derived from. Use `nfftytwoh` (local) as the New-52wk-High source; ignore `n52wh`.

5. **Version History rows 33/34** ("Within 30% from 52 WH / WL") repeat the *15%* wording — a
   copy-paste error in the source's own glossary. Confirm the 30% bucket definitions
   (`Data` cols 32/37) are truly "15%-to-30%" bands as the Market Map bucket structure implies.

6. **`vbaProject.bin` (52 KB).** Not decompiled. If any datapoint above turns out *not* to be a
   worksheet formula, its logic may live in VBA (likely just the refresh/paste macro). Flag only
   if a needed analytic can't be reproduced from the worksheet formulas documented here.

7. **25%/20-day vs "monthly" window.** `Data` has "25% up/down in 20 days"; `breadth_daily` has
   `up_25pct_month`/`down_25pct_month`. Confirm whether "monthly" == 20 trading days before
   treating them as the same series.
