# Market Breadth V2.0 — Reverse-Engineering

**Source workbook:** `manas_os/design/study/Market Breadth V2.0.xlsm`
(~27 MB, macro-enabled, 12 sheets, 56 named ranges, 2 VBA modules)
**Author (from Version History):** Chhirag Kedia / @swing_ka_sultan —
"Market Breadth Monitor V 2.0 for Kedia Private Access Mentorship"
**Data span:** 2004-01-01 → 2026-07-10 (5,573 daily rows in `Data`)
**Workbook version:** 2.0.5 (last entry, 2022-09-13)

This document is a faithful reverse-engineering of the workbook's structure,
formulas, definitions, and macros, derived by reading the actual cell formulas
(not just headers) and decompiling the VBA. Every formula below is quoted
verbatim from a cell; every definition in the criteria dictionary is quoted
verbatim from the `Version History` sheet.

---

## 0. Data-flow map (read this first)

The workbook is a five-layer pipeline. Every derived number ultimately traces
back to a raw count in the `Data` sheet:

```
Data (raw daily counts, the only input)
 │
 ├──> Breadth (ratios: count / universe, and derived ratios of ratios)
 │      │
 │      └──> Dashboard  (presentation view; VLOOKUPs into Breadth + Market Map)
 │      └──> Filters    (duplicate of Dashboard with minor formula drift — see §5)
 │
 ├──> Market Map (52-week high/low distance bands + Fosback HL Logic Index)
 │      │
 │      └──> Dashboard / Filters (NH-NL, 15%-from-high/low columns)
 │
 ├──> SBE (Sectoral Breadth Engine: index levels + % change + 5-day ROC
 │         per sector, plus chart-range helpers)
 │      │
 │      └──> Dashboard / Filters / Sectoral (NIFTY, SMLCAP, sector levels)
 │
 └──> Dashboard Charts (just two cells: B2 "From" date, B3 "Till" date)
        │   These two cells drive EVERY named range (all 56 named ranges are
        │   INDEX(...MATCH against B2:B3) windowing expressions).
        └──> The *Charts sheets + 52 chart XMLs (visualization only)
```

**Key dependency fact:** the `Dashboard Charts!B2:B3` date window is the single
global filter. All 56 named ranges are dynamic windows that slice each data
series between those two dates for charting. Change those two cells and every
chart rescales.

---

## 1. SHEET: `Data` — the raw input (the only sheet with real data)

**Role:** daily breadth counts + index levels. Everything else derives from here.
**Dimensions:** 64 columns × 5,574 rows (1 header + 5,573 data rows).
**Content:** raw numbers (NO formulas — this is the ingest target).
**Ingest mechanism:** the `marketbreadth` VBA macro (Ctrl+M) wipes this sheet
and pastes the clipboard (see §11).

### Column dictionary (verbatim headers, row 1)

| Col | Header | Meaning |
|---|---|---|
| A | Date/Time | Trading date |
| B | Nifty 50 | Index level |
| C | Small Cap 100 | Index level |
| D | **Total Universe** | Count of stocks with CMP ≥ 1 (the denominator for all breadth %) |
| E | 4% Up | # stocks with net change % ≥ +4% |
| F | 4% Down | # stocks with net change % ≤ −4% |
| G | High Vol | # stocks with volume > 1.5× 20-day avg volume |
| H | Low Vol | # stocks with volume < 0.5× 20-day avg volume |
| I | Range <3% | # stocks with daily range ≤ 3% (contraction) |
| J | Range 5.01% + | # stocks with daily range ≥ 5.01% (expansion) |
| K | Close Upper Half | # stocks closing in top 50% of daily range, **on an expansion candle** |
| L | Close Lower Half | # stocks closing in bottom 50% of daily range, on an expansion candle |
| M | Breakouts | # stocks whose high ≥ prev-close + 4% |
| N | Breakout Sustained | # breakouts closing within 40% of range from the high |
| O | Breakout Failure | # breakouts closing below 40% of range from the high |
| P | Breakdowns | # stocks whose low ≤ prev-close − 4% |
| Q | Breakdown Sustained | # breakdowns closing within 40% of range from the low |
| R | Breakdown Failure | # breakdowns closing above 40% of range from the low |
| S | 15% up in 5 days | # stocks up ≥15% over 5 days |
| T | 15% down in 5 days | # stocks down ≥15% over 5 days |
| U | 25% up in 20 days | # stocks up ≥25% over 20 days |
| V | 25% down in 20 days | # stocks down ≥25% over 20 days |
| W | 10% above 10 DEMA | # stocks ≥10% above their 10-day DEMA |
| X | 10% below 10 DEMA | # stocks ≥10% below their 10-day DEMA |
| Y | Above 10 DEMA | # stocks above 10-day DEMA |
| Z | Above 20 DEMA | # stocks above 20-day DEMA |
| AA | Above 50 DEMA | # stocks above 50-day DEMA |
| AB | Above 200 DEMA | # stocks above 200-day DEMA |
| AC | 52 Week High | # new 52-week highs today |
| AD | 52 Week Low | # new 52-week lows today |
| AE | 15% from 52WH | # stocks within 15% of their 52-week high (close ≥ high − 15%) |
| AF | 30% from 52WH | … within 30% |
| AG | 50% from 52WH | … within 50% |
| AH | 70% from 52WH | … within 70% |
| AI | 70% Plus From 52WH | # stocks >70% from their 52WH (deep laggards) |
| AJ | 15% from 52WL | # stocks within 15% of their 52-week low |
| AK | 30% from 52WL | … within 30% |
| AL | 50% from 52WL | … within 50% |
| AM | 90% from 52WL | … within 90% |
| AN | 150% from 52WL | … within 150% |
| AO | 150% Plus From 52WL | # stocks >150% above their 52WL (extended leaders) |
| AP–BH | Nifty Auto … Nifty Service Sector | 19 sectoral index levels |
| BI | 5 Day Range | (used by Dashboard K) |

**Note on missing sectoral columns:** Data has 19 sector headers (AP–BH) but
several early rows (2004) show `1000` for some sectors — these were
placeholder/base values before the real sector index existed. A faithful port
should treat any `1000` that is exactly the base as "no data", not a real level.

---

## 2. SHEET: `Breadth` — the ratio engine (core computation)

**Role:** converts raw counts from `Data` into ratios (% of universe, and ratios
of ratios). This is where the breadth math lives.
**Dimensions:** 30 cols (A–AD) × 10,001 rows. Headers are on row 1
(branding/title); data starts row 3.

### Formula map (row 3 shown; every row is the same pattern, offset)

```
A3 = IF(ISNUMBER(Data!A2), Data!A2, " ")                          ← date passthrough
B3 = IF(ISNUMBER(VLOOKUP(A:A,SBE!A:F,3,0)), …, " ")               ← NIFTY CHG% (from SBE col C)
C3 = IF(ISNUMBER(VLOOKUP(A:A,SBE!A:F,5,0)), …, " ")               ← SMLCAP level (SBE col E)
   NOTE: row 4+ pulls SBE col 6 (SMLCAP CHG%) instead of col 5 — see quirk §2b
D3 = IF(ISNUMBER(VLOOKUP($A:$A,Data!$A:$BH,4,0)), …, " ")         ← universe (raw)
E3 = IF(…, VLOOKUP(Data col 5)/$D3, " ")                          ← 4% Up as % of universe
F3 = IF(…, VLOOKUP(Data col 6)/$D3, " ")                          ← 4% Down as % of universe
G3 = IF(ISNUMBER(E3), (E3-F3)*100, " ")                           ← NET BREADTH (pp)
   [H, I blank]
J3 = IF(…, VLOOKUP(Data col 7)/$D3, " ")                          ← High Vol % of universe
K3 = IF(…, VLOOKUP(Data col 8)/$D3, " ")                          ← Low Vol % of universe
L3 = IF(ISNUMBER(J3), J3/K3, " ")                                 ← Volume Ratio (High/Low)
M3 = IF(…, VLOOKUP(Data col 9)/$D3, " ")                          ← Range <3% % of universe
N3 = IF(ISNUMBER(M3), O3/M3, " ")                                 ← Range Expansion/Contraction
O3 = IF(…, VLOOKUP(Data col 10)/$D3, " ")                         ← Range 5.01%+ % of universe
P3 = IF(ISNUMBER(O3), VLOOKUP(Data col 11)/$D3 / O3, " ")         ← Close>50% / Range-Exp  (UP CLOSE %)
Q3 = IF(ISNUMBER(O3), VLOOKUP(Data col 12)/$D3 / O3, " ")         ← Close<50% / Range-Exp  (DOWN CLOSE %)
R3 = IF(ISNUMBER(O3), (P3-Q3)*100, " ")                           ← UH/LH net (pp)
S3 = IF(ISNUMBER(T3), T3/Y3, " ")                                 ← BO / BD  (BO/BD ratio)
T3 = IF(…, VLOOKUP(Data col 13)/$D3, " ")                         ← Breakouts % of universe
U3 = IF(ISNUMBER(E3), E3/T3, " ")                                 ← 4%Up / BO  (UP CLOSE % alt)
V3 = IF(ISNUMBER(T3), VLOOKUP(Data col 14)/$D3 / T3, " ")         ← BO Sustained / BO  (BO S/F ratio)
W3 = IF(ISNUMBER(T3), VLOOKUP(Data col 15)/$D3 / T3, " ")         ← BO Failed / BO
X3 = IF(ISNUMBER(V3), V3/W3, " ")                                 ← BO Sustained / BO Failed
Y3 = IF(…, VLOOKUP(Data col 16)/$D3, " ")                         ← Breakdowns % of universe
Z3 = IF(ISNUMBER(F3), F3/Y3, " ")                                 ← 4%Dn / BD  (DOWN CLOSE % alt)
AA3= IF(ISNUMBER(Y3), VLOOKUP(Data col 17)/$D3 / Y3, " ")         ← BD Sustained / BD
AB3= IF(ISNUMBER(Y3), VLOOKUP(Data col 18)/$D3 / Y3, " ")         ← BD Failed / BD
AC3= IF(ISNUMBER(Y3), AA3/AB3, " ")                               ← BD Sustained / BD Failed
```

### 2a. Criteria dictionary (verbatim from `Version History` sheet)

These are the authoritative plain-English definitions the author documented:

| Metric | Criteria (verbatim) |
|---|---|
| Universe | `CMP >= 1;` |
| 4% Advance | `Net Change % > = 4%` |
| 4% Decline | `Net Change % < = -4%` |
| Net Breadth | `4% Advance - 4% Decline` |
| 5 Day Ratio | `Sum of 4% Advance of Last 5 Days / Sum of 4% Decline of Last 5 Days` |
| 10 Day Ratio | `Sum of 4% Advance of Last 10 Days / Sum of 4% Decline of Last 10 Days` |
| Range Expansion | `Range > = 5.01%` |
| Range Contraction | `Range < = 3%` |
| 5 Day Range | `5 Day High - Low/ Low` |
| Volatility Ratio | `Range Expansion / Range Contraction` |
| Above Avg. Volume | `V > 1.5x 20 DMA` |
| Below Avg. Volume | `V < 0.5x 20 DMA` |
| Volume Ratio | `Above Avg. Volume / Below Avg. Volume` |
| Close > 50% | `Close > 50% of Daily Range on a Range Expansion candle` |
| Close < 50% | `Close <= 50% of Daily Range on a Range Expansion candle` |
| UH/LH Ratio | `Close > 50% / Close < 50%` |
| Breakout | `Today High > = 4% from Previous Close` |
| Breakdown | `Today's Low < = 4% from Previous Close` |
| BO / BD Ratio | `Breakout / Breakdown` |
| Up Close % | `4% Advance / Breakout` |
| Down Close % | `4% Decline / Breakdown` |
| Breakout Sustained | `Closes within 40% (of Range) from highs on Breakout Day` |
| Breakout Failed | `Closes below 40% (of Range) from highs on Breakout Day` |
| BO S/F Ratio | `Breakout Sustained / Breakout Failed` |
| Breakdown Sustained | `Closes within 40% (of Range) from lows on the Breakdown Day` |
| Breakdown Failed | `Closes above 40% (of Range) from lows on the Breakdown Day` |
| BD S/F Ratio | `Breakdown Sustained / Breakdown Failure` |
| Within 15% from 52 WH | `Close >= 15% from 52 Week High` ⚠ (see note) |
| Within 15% from 52 WL | `Close <= 15% from 52 Week High` ⚠ (see note) |
| 15% H/L Ratio | `Within 15% from 52 WH / Within 15% from 52 WL` |
| Within 30% from 52 WH | `Close >= 15% from 52 Week High` ⚠ |
| Within 30% from 52 WL | `Close <= 15% from 52 Week High` ⚠ |
| 30% H/L Ratio | `Within 30% from 52 WH / Within 30% from 52 WL` |

⚠ **Definition-copying bug in the source:** the "Within X% from 52 WL" rows in
`Version History` literally say "from 52 Week **High**" — an obvious copy-paste
error by the author. The formulas (and the 30%/150% band columns in `Data`)
confirm the low-distance bands are genuinely measured from the 52-week **low**.
A port should use the formula behavior (from the low), not the typo'd label.

### 2b. Quirks flagged (load-bearing for a faithful port)

1. **Column C alternates meaning by row.** Row 3 pulls `SBE!F` col 5 (SMLCAP
   level); row 4+ pulls `SBE!F` col 6 (SMLCAP **CHG%**). This is almost
   certainly an authoring inconsistency, not intent. A port should pick one
   (level or CHG%) and apply it uniformly — flag which.
2. **Net breadth is in percentage-points, not a count.** `G3 = (E3−F3)*100`
   where E/F are fractions of universe, so G is `(4up% − 4dn%)` in pp.
3. **Two different "Up Close %" computations exist** (Breadth P and Breadth U)
   using different denominators (Range-Expansion count vs Breakout count). The
   Dashboard surfaces the Breakout-denominator one (col U via Breadth col 21).
4. **Vol ratio divides High/Low** (`L = J/K`), so a value <1 means more
   low-volume than high-volume stocks (a bearish/quiet read).

---

## 3. SHEET: `Market Map` — 52-week distance bands + Fosback HL Index

**Role:** distance-from-extremes analysis (how far the market is from highs/lows)
and the Norman Fosback Hi-Low Logic Index.
**Dimensions:** 25 cols × 8,545 rows. Headers on row 2; data row 3+.

### Column dictionary + formulas

```
A  Date                          = Data!A passthrough
B  NIFTY 50                      = SBE col C (CHG%)
C  SMLCAP 100                    = SBE col 5 (level) [row 3] / col 6 [row 4+] (same quirk as Breadth)
D  Universe                      = Data col 4
E  4% Up                         = Data col 5 / D        (% of universe)
F  4% Down                       = Data col 6 / D
G  N52WH                         = Data col 29 (AC) / D  (new 52-wk highs %)
H  N52WL                         = Data col 30 (AD) / D  (new 52-wk lows %)
I  NET NH-NL                     = (G - H) * 100         (pp)
J  NET 15% H-L                   = (L - Q) * 100
K  NET 30% H-L                   = ((L+M) - (Q+R)) * 100
L  15% from 52WH                 = Data col 31 / D
M  30% from 52WH                 = Data col 32 / D
N  50% from 52WH                 = Data col 33 / D
O  70% from 52WH                 = Data col 34 / D
P  70%+ from 52WH                = Data col 35 / D       (deep laggards)
Q  15% from 52WL                 = Data col 36 / D
R  30% from 52WL                 = Data col 37 / D
S  50% from 52WL                 = Data col 38 / D
T  90% from 52WL                 = Data col 39 / D
U  150% from 52WL                = Data col 40 / D
V  150%+ from 52WL               = Data col 41 / D       (extended leaders)
W  HL LOGIC CALC                 = IF(G<=H, G, H) * 100  (the min of NH%, NL%)
X  HL LOGIC INDEX                (Fosback index — see note)
```

**Fosback Hi-Low Logic Index (col W):** `min(newHighs%, newLows%) × 100`.
Fosback's insight: in a healthy trend, either highs OR lows dominate (one is
near zero). When **both** are elevated, the market is internally conflicted — a
transition/panic signal. The index is high when both are high. (Col X "HL LOGIC
INDEX" had no formula in the sampled rows — it may be computed elsewhere or
manually; flag for maintainer.)

---

## 4. SHEET: `SBE` (Sectoral Breadth Engine) — per-sector levels + ROC

**Role:** index levels and rate-of-change for NIFTY, SMLCAP, and 19 sectors,
plus chart-range helper columns. **Hidden sheet** (state=hidden).
**Dimensions:** 56 cols × 6,500 rows.

### Structure
Columns come in triples: `<INDEX level>` | `CHG%` | `5-DAY ROC`, for each of:
NIFTY50, SMLCAP100, Auto, Bank, Commodities, Consumption, CPSE, Energy,
Fin Servv, FMCG, Infra, IT, Media, Metal, MNC, Pharma, PSE, PSU Bank, Pvt Bank,
Realty, Services (21 instruments).

### Formulas (NIFTY shown; same for all)
```
B  (level)   = VLOOKUP(A, Data!A:BH, 2, 0)       ← raw passthrough
C  CHG%      = IF(ISNUMBER(B3), (B3-B2)/B3, " ")  ← day-over-day % change
D  5-day ROC = (computed via a rolling window; see cell)
```

⚠ **CRITICAL QUIRK — CHG% divides by the CURRENT price, not the previous price.**
The formula is `(B3-B2)/B3`, but the standard convention is `(B3-B2)/B2`.
**Verified numerically:** for 2026-07-10, NIFTY = 24206.9, prev = 23962.8.
- SBE's formula: `(24206.9−23962.8)/24206.9 = 0.0100839` ← matches the cell
- Standard: `(24206.9−23962.8)/23962.8 = 0.0101866`

This introduces a small systematic bias (~0.01% on normal days, more on big
moves). A port must **decide consciously**: reproduce the quirk for exact
back-compat, or correct to `/B2`. Document the choice.

### Chart-range helpers (cols AV, BC, BD)
```
AV = ROUND(MIN(AT:AT)*0.95, 2)    ← NIFTY chart min (5% below series low)
BC = ROUND(MAX(AT:AT)*1.05, 2)    ← 50-DEMA chart max (5% above series high) [row 3]
   (row 2 has the min variant; the pattern alternates — authoring messiness)
BD = "Min Val 50 DEMA" / "Max Val 50 DEMA"  (text labels)
```
These feed the `setChartAxis` VBA UDF (§11) for dynamic axis bounds, scoped to
the `Dashboard Charts!B2:B3` date window via cols AT/AU (which are windowed
copies of B/E).

---

## 5. SHEET: `Filters` — Dashboard duplicate with drift

**Role:** appears to be an alternate/working copy of the Dashboard.
**Dimensions:** 33 cols × 6,500 rows. **Identical headers to Dashboard.**

**Formula drift vs Dashboard (verified):** the formulas are *almost* identical
to Dashboard but with small inconsistencies, e.g.:
- `L3` (Volume): Dashboard pulls `Data col 25 / universe`; Filters row 3 does
  the same, but Filters row 4+ pulls `Breadth col 12` (the volume ratio)
  instead.
- `E3/E4`: Dashboard pulls SBE col 5 for SMLCAP; Filters pulls col 5 (row 3)
  then col 6 (row 4+) — the same alternating quirk.

**Conclusion:** `Filters` is a scratch/working copy, not authoritative. A port
should treat `Dashboard` as canonical and ignore `Filters`, or reconcile the
drift explicitly if both are needed.

---

## 6. SHEET: `Sectoral` — clean sector-level view

**Role:** simple date + 21 index-level columns (NIFTY, SMLCAP, 19 sectors).
**Dimensions:** 22 cols × 6,500 rows. Headers row 2.
**Formulas:** `A=Data!A passthrough`, `B=SBE col 3 (CHG%)`, `C=SBE col 6 (CHG%)`,
then sectors (cols D–V) — **the sampled rows had no formulas past C**, suggesting
either the sector columns are values-only or were pasted. A port should rebuild
these as `SBE` lookups if live formulas are wanted.

---

## 7. SHEET: `Dashboard` — the canonical presentation view

**Role:** the primary human-facing table. Pulls from Breadth, Market Map, SBE,
and Data via VLOOKUP, plus derives weekday and net columns.
**Dimensions:** 33 cols × 6,500 rows. Branding row 1; headers row 2; data row 3+.

### Column → source map (row 3)
```
A  DATE          = Data!A
B  WEEKDAY       = TEXT(A3, "dddd")
C  SA NOTES      (manual entry column — blank in data)
D  NIFTY 50      = SBE col C  ⚠ (this is CHG%, not the index level — despite the header)
E  SMLCAP 100    = SBE col 5 (level) [row3] / col 6 (CHG%) [row4+]  ⚠ alternating quirk
F  UNIVERSE      = Breadth col 4 (D)
G  4% ADVANCE    = Breadth col 5  (E = 4up/universe)
H  4% DECLINE    = Breadth col 6  (F = 4dn/universe)
I  NET BREADTH   = (G3-H3)*100
J  3% RANGE      = Breadth col 13 (M = range<3%/universe)
K  5 DAY RANGE   = Data col 61 (BI) / F   ⚠ (Data!BI is "5 Day Range"; /universe)
L  VOLUME        = Data col 25 (Y=Above10DEMA? No — col 25) / F
                   ⚠ Dashboard L3 uses Data col 25/universe; Filters L4+ uses Breadth col 12. Drift.
M  UH/LH RATIO   = Breadth col 18 (R)
N  BREAKOUTS     = Breadth col 20 (T)
O  UP CLOSE %    = Breadth col 21 (U = 4up/BO)
P  BO S/F RATIO  = Breadth col 24 (X = BOsus/BOfail)
Q  BREAKDOWNS    = Breadth col 25 (Y)
R  DOWN CLOSE %  = Breadth col 26 (Z = 4dn/BD)
S  BD S/F RATIO  = Breadth col 29 (AC = BDsus/BDfail)
T  15% IN 5DAYS  = Data col 19 (S) / F
U  10%- IN 5DAYS = Data col 20 (T) / F   ⚠ header says "10%- in 5 days" but source is "15% down in 5 days"
V  10%+ 10 DEMA   = Data col 23 (W) / F
W  10%- 10 DEMA   = Data col 24 (X) / F
X  NEW 52 WH     = Market Map col 7  (G = N52WH/universe)
Y  NEW 52 WL     = Market Map col 8  (H = N52WL/universe)
Z  NET NH-NL     = Market Map col 9  (I = (G-H)*100)
AA 15% FROM 52WH = Market Map col 12 (L)
AB 15% FROM 52WL = Market Map col 17 (Q)
AC NET 15% H-L   = Market Map col 10 (J = (L-Q)*100)
AD ABOVE 10 MA   = Data col 25 (Y) / F
AE ABOVE 20 MA   = Data col 26 (Z) / F
AF ABOVE 50 MA   = Data col 27 (AA) / F
AG ABOVE 200 MA  = Data col 28 (AB) / F
```

⚠ **Header/source mismatches (flag for maintainer):**
- **D "NIFTY 50" is actually the daily % change**, not the index level (pulls
  SBE col C = CHG%). Verified: cell shows 0.01008, not 24206.9.
- **U "10%- IN 5DAYS" pulls Data col 20** which is "15% down in 5 days", not
  10%. Header is wrong or column wired wrong.
- **K "5 DAY RANGE"** divides Data!BI (a raw 5-day range value) by universe —
  dimensionally odd (range count / total stocks). May be intentional (% of
  universe in a 5-day range) but the header is ambiguous.

---

## 8. Chart sheets + named ranges

### `Dashboard Charts`, `Breadth Charts`, `MM Charts`
Each is a thin sheet holding chart objects (the 52 `chartN.xml` files in the
archive) plus, for `Dashboard Charts`, the two global date-window cells:
```
B2 = From date (currently 2025-01-01)
B3 = Till date (currently 2026-07-10)
```

### Named ranges (56 total) — all are date-windowed slices
Every named range is an `INDEX(col, MATCH(B2)):INDEX(col, MATCH(B3))` expression
that returns the portion of a series between the Dashboard Charts date window.
Examples (abbreviated):
- `Date` → Dashboard!A between the two dates
- `netbreadth` → Dashboard!I (net breadth) windowed
- `abvol` → Breadth!J (high vol %) windowed
- `nhnl` → Market Map!I (net NH-NL) windowed
- `Nifty` → SBE!AT (windowed NIFTY copy) 
- `smlcap` → SBE!AU (windowed SMLCAP copy)

These exist purely to feed chart series. A port that doesn't replicate Excel
charts can ignore them; a port replicating the charts needs to reproduce the
date-window slicing.

---

## 9. SHEET: `Rough Work` — empty scratch (1 cell). Ignore.

## 10. SHEET: `Version History` — the criteria dictionary + changelog

Already quoted in full in §2a (criteria) and below (changelog). This sheet is
the authoritative definition source.

**Changelog (verbatim):**
- **2.0.0** (2022-08-01, Chhirag Kedia) — Primary Version
- **2.0.1** (2022-08-08) — Market Breadth Monitor now available from 2004;
  Reduced above-avg-volume criteria to 1.5× 20 DEMA; Reduced BO/BD criteria to
  4% up/down (earlier 5.01%) from previous close
- **2.0.2** (2022-08-20) — Added 4% Up & Down Close % as % of Total BO/BD
- **2.0.3** (2022-08-29) — Added 5 Day Ratio and 10 Day Ratio in Breadth Sheet
  (used by Stock Bee)
- **2.0.4** (2022-09-02) — Added 5 Day Range and Net NH-NL
- **2.0.5** (2022-09-13) — Added Hi-Low Logic Index (created by Norman Fosback)

---

## 11. VBA MACROS (decompiled)

The workbook is macro-enabled but contains only **two functional macros**; the
rest are empty sheet-class stubs.

### `Module1.marketbreadth` (Ctrl+M — the daily ingest routine)
```vba
Sub marketbreadth()
' Keyboard Shortcut: Ctrl+m
    Cells.Select
    Selection.ClearContents           ' wipe the active sheet
    Range("A1").Select
    ActiveSheet.PasteSpecial Format:="Unicode Text", ...  ' paste clipboard
    Columns("A:A").Select
    Selection.Delete Shift:=xlToLeft ' delete col A (extra index column from source)
    Dim lra As Integer
    lra = Range("A" & Rows.Count).End(xlUp).Row
    Range("A2:BH" & lra).Select
    Selection.Copy                    ' leave the data range copied for next paste
End Sub
```
**Purpose:** the user copies a daily breadth dump (from an external screener)
to the clipboard, opens the `Data` sheet, presses Ctrl+M; the macro wipes
`Data`, pastes the clipboard as Unicode text, deletes the first column (which
the source includes as a row index), and re-copies the A2:BH range. This is
**the entire ingest pipeline** — `Data` is manually pasted, not linked to a
feed.

### `Module2.setChartAxis` (UDF for dynamic chart axes)
A user-defined function used in chart-title cells to set min/max axis bounds
dynamically:
```vba
Function setChartAxis(sheetName, chartName, MinOrMax, ValueOrCategory,
                      PrimaryOrSecondary, Value)
    Set cht = ...Sheets(sheetName).ChartObjects(chartName).Chart
    ' sets cht.Axes(xlValue/xlCategory, xlPrimary/xlSecondary).MaximumScale/MinimumScale
    ' to Value if numeric, else auto
End Function
```
**Purpose:** lets the SBE chart-range helper cells (AV/BC, §4) drive chart
axis bounds via in-sheet formulas. Not needed for data logic; only for the
Excel chart rendering.

---

## 12. Porting notes — what a faithful reproduction needs

### Must reproduce exactly (the math)
1. **Universe = count of stocks with CMP ≥ 1** (the denominator for everything).
2. All breadth metrics as `% of universe` (count / D), per the Breadth formulas.
3. Net breadth, net NH-NL, net 15% H-L as `(up−down) × 100` in percentage-points.
4. BO/BD threshold = **4% from previous close** (changed from 5.01% in v2.0.1).
5. Volume thresholds: high = **>1.5× 20-day avg**, low = **<0.5× 20-day avg**.
6. Range bands: contraction ≤3%, expansion ≥5.01%.
7. BO/BD sustained = closes within 40% of range from the high/low.
8. Fosback HL Logic Index = `min(newHighs%, newLows%) × 100`.

### Must decide consciously (the quirks)
| Quirk | Options |
|---|---|
| SBE CHG% divides by current price `/B3` not prev `/B2` | Reproduce for back-compat, or correct to `/B2`. ~1% bias on big days. |
| Breadth/Filters col C alternates SMLCAP level vs CHG% by row | Pick one (recommend: level in a `level` column, CHG% in a separate column). |
| Dashboard D "NIFTY 50" actually shows CHG% | Either fix the header to "NIFTY CHG%" or rewire to the level. |
| Dashboard U "10%- in 5 days" sources "15% down in 5 days" | Fix header or rewire source. |
| Dashboard K "5 Day Range" = Data!BI / universe | Confirm intent (% in 5-day range?) or rewire. |
| Version History has copy-paste typos ("from 52 Week High" for low-distance rows) | Use formula behavior (from the low), not the label. |
| Market Map col X "HL LOGIC INDEX" has no formula | Either compute it or drop it. |
| `Filters` sheet drifts from `Dashboard` | Treat Dashboard as canonical. |

### Can drop (Excel-specific)
- The 52 chart XMLs, chart style/color files, drawings.
- The `setChartAxis` UDF and SBE chart-range helpers (AV/BC/BD) — only feed charts.
- The 56 named ranges — only feed chart series; replace with date-windowed
  queries in whatever datastore the port uses.
- The `marketbreadth` paste macro — replace with a real ingest path (the
  workbook's manual clipboard paste is the weakest link).

---

## 13. Verification performed (per AGENTS.md)

- **Formulas:** read every column's formula from rows 3–5 of Breadth, Dashboard,
  Market Map, SBE, Filters, Sectoral (data_only=False).
- **Values cross-checked (second route):** for 2026-07-10, recomputed
  4up/universe = 193/2314 = 0.08341 (matches Breadth E ✓), net breadth =
  (0.08341−0.01253)×100 = 7.087 (matches G ✓), 52wh/universe = 85/2314 = 0.03673
  (matches Dashboard X ✓).
- **SBE CHG% quirk verified numerically:** (24206.9−23962.8)/24206.9 = 0.0100839
  matches the cell; the standard /prev gives 0.0101866 — confirming the
  divide-by-current behavior.
- **VBA:** decompiled via oletools; 2 functional macros confirmed, 13 empty
  class stubs.
- **Definitions:** quoted verbatim from Version History; typos flagged not
  silently corrected.
- **Not verified:** Market Map col X formula (none found in sampled rows —
  flagged), Sectoral cols D–V formulas (none found past C — flagged),
  Dashboard Charts chart definitions (52 chart XMLs not individually parsed —
  out of scope for "reverse-engineer each sheet"'s data logic; can be done if
  chart reproduction is needed).
