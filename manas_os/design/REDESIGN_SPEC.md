# Manas AI Trading OS — UI Redesign Spec (v1)

> **Purpose.** A coding agent should be able to build this screen-by-screen with **no design judgment calls left open.** Every screen below gives: a wireframe, a component list (reuse / new), a data contract (endpoint → field → widget), Tailwind-token usage, and the five states (normal / empty / stale / auth / loading). Tokens in `design/design_guidelines.json` + `tailwind.config.js` are **LAW** — no new colors, radii, or fonts. Sans is used **only** for plain-English "READ" prose; everything else is mono.
>
> **North star:** a calm light trading terminal where *every number has a plain-English read beside it and an evidence trail behind it.* The fix for "data sources feel disconnected" is one shared **SymbolChip / SymbolCard** that fuses bhavcopy + ChartsMaze + Fyers on every screen, plus one shared **DataStamp** that says which source is as-of-when everywhere.

---

## 0. Global decisions (apply to all screens)

### 0.1 Navigation & shell
- Keep the top-tab shell in `App.jsx`. **Rename/retarget tabs** to the mandated IA:
  `Regime · Setups · Watchlist · Journal · Health`. (Current: `Regime · Screen(disabled) · Chart(disabled) · Journal(disabled) · Health`.)
  - `Setups` replaces `Screen`. `Watchlist` is new. `Chart` is **removed as a tab** — charting is now a **drawer**, not a destination (matches non-goal "not a free-form charting platform").
- **Header (56px), left→right:** app mark `MANAS OS` · `· <tab>` eyebrow · **posture badge (always visible)** · **DataStamp mini** (worst-source freshness dot + date) · **Beginner⇄Expert toggle** (new, global) · Refresh button · Fyers chip.
  - The posture badge already bubbles up via `RegimeSummary onPosture`. Keep that wire.
- **Global banners** render directly under the header, in this priority order (only the top-most applicable one shows, plus stale can co-exist):
  1. **Stale-data banner** (red) — any surface's primary source older than its threshold.
  2. **Fyers-auth banner** (orange) — `health.fyers_connected === false`. Already built in `App.jsx`; keep, reword to name what degrades ("live quotes + MARS run on fallback").

### 0.2 The three shared primitives (BUILD THESE FIRST — every screen depends on them)

**A) `<SymbolChip symbol=… density=…/>`** — the fused-source atom. This is the answer to complaint (e). It appears anywhere a ticker is named (drilldowns, setup cards, watchlist rows, journal rows). Compact inline form:
```
┌───────────────────────────────────────────────┐
│ RELIANCE   RS 82 ·  DLV 71%  ·  ▲+1.2% [LIVE]   │   ← click → opens ChartDrawer
└───────────────────────────────────────────────┘
   mono      blue    band-by    green/red   green dot
   ink       chip    threshold  live quote  = Fyers on
```
- **RS** (ChartsMaze `rs`) → blue info chip (`bg-info-bg text-info border-info-border`). Band by RS threshold: ≥50 bull / 40–49 muted / <40 bear — reuse existing drilldown thresholds.
- **DLV%** (bhavcopy delivery %) → conditional cell, threshold TBD (see Open Q1). Placeholder banding: ≥60 bull / 40–59 muted / <40 bear.
- **Live quote** (Fyers) → signed % chip green/red; a `[LIVE]` green dot when `fyers_connected`, else the chip is **absent** and a muted `·` placeholder shows (never a fake zero).
- **Source provenance is legible on hover** via `title`: `"RS 82 (ChartsMaze 2026-07-03) · Delivery 71% (bhavcopy 2026-07-03) · Quote live (Fyers)"`. This is the visible "connection between the three sources."
- Whole chip is a button → `onSelect(symbol)` opens the **ChartDrawer**.

**B) `<SymbolCard/>`** — the expanded block form of the same fusion (used on Setups + Watchlist cards). Same three source-bands, plus the metric grid for that screen. One left-rail band color = the card's headline verdict.

**C) `<DataStamp sources=[…]/>`** — one row of per-source freshness chips (generalize existing `DataCoverage.jsx`). Each chip: `SOURCE · date · dot`. Green ≤1d / amber ≤5d / red beyond-or-missing. Feeds off `/api/data/coverage`. Rendered as a thin footer strip on every screen so "as-of which source" is always answerable in one glance. **Replaces every ad-hoc `as of {date}` string currently scattered in components.**

**Verdict layer (`<Read>`):** a fixed slot component — `<Read verdict="SWING UP">plain-English sentence</Read>` renders a mono verdict chip + a dashed divider + a sans READ line (color `#3a414c`). Every data block gets exactly one. Build once, use everywhere.

### 0.3 Beginner⇄Expert toggle (global, new)
Segmented ink control in header. Stored in a React context (`DensityContext`). Effect:
- **Beginner (default):** plain-English leads; ≤3 raw numbers per card; hides raw columns (20R, 50R, ADR, raw RS rank).
- **Expert:** reveals raw columns app-wide; verdict READ lines shrink to one line. Same data, denser.

---

## 1. REGIME screen — "market control tower" (highest priority; all six complaints fixed here)

### 1.1 Wireframe
```
┌─ POSTURE COMMAND BAR ───────────────────────────────────────────────────┐  (a)
│  ┌──────────┐  Breadth 58% of stocks above 20-DMA — moderate, narrowing. │
│  │ SELECTIVE│  APPROACH: trade 2–3 positions max, half size, A-setups     │
│  │  badge   │  only. Risk 0.5–0.75% per trade.                            │
│  └──────────┘  ── READ ── One green light isn't a full tank; be picky.    │
│  [XP 46 ▸flip] [4.5R 88 ▸flip] [MBI WHITE] [breadth spark] [risk .5–.75%] │  (b)
└──────────────────────────────────────────────────────────────────────────┘
┌─ WHAT'S WORKING / WHAT'S NOT ──────────────────────────────────────────┐  (c)
│  PREFER  ▸ pullback-to-10EMA   ▸ flat-base breakout                      │
│  AVOID   ✕ extended-chase       ✕ falling-knife                          │
└──────────────────────────────────────────────────────────────────────────┘
┌─ MARKET QUADRANT (2×2) ────────────────────────────────────────────────┐
│  [Momentum]  [Swing]                                                     │
│  [Trend]     [Bias]        each: rail + state + question + conf + READ    │
└──────────────────────────────────────────────────────────────────────────┘
┌─ REGIME TREND (labelled) ──────────────────────────────────────────────┐  (d)
│  XP & Posture, last 60 sessions                                          │
│  ▁▂▄▆█  ← XP line (blue), y-axis 0–100 labelled, hover=value+date        │
│  ███░░▒ ← posture ribbon w/ LEGEND: ■risk-on ■selective ■defensive ■none │
│  ── READ ── XP rose from 31→46 over 2 weeks; posture firmed to Selective. │
└──────────────────────────────────────────────────────────────────────────┘
┌─ SECTORS & THEMES (unchanged core, restyled header) ───────────────────┐
│  tabs: Sectors | Themes    rows w/ RS bars, drill → SymbolChip lists     │
└──────────────────────────────────────────────────────────────────────────┘
   <DataStamp: breadth · bhavcopy · chartsmaze · regime>
```

### 1.2 Fix (a) — Posture Command Bar (replaces the vague 8-tile "Posture" StripCard)
**Problem:** current `Posture` is one tiny badge tile with no instruction.
**New `<PostureCommandBar/>`** — a Direction-B "briefing" banner (design §6/§7): big posture badge + a **two-line concrete instruction**, generated from fields already in `/api/regime/summary`:

| Line | Content | Source field |
|---|---|---|
| Breadth read | `"Breadth {pct}% of stocks above 20-DMA — {improving/narrowing}."` | `breadth` (latest of breadth-history) + slope |
| **APPROACH** | position-count + size guidance keyed to `market_mode` (table below) | `market_mode`, `allowed_risk_min/max_pct` |
| READ line | one plain-English sentence | `explanation_text` |

**Approach table (deterministic — code this literally, no judgment):**
| market_mode | Positions | Size | Setups | Risk chip |
|---|---|---|---|---|
| RISK_ON | up to 5 | full | A & B setups | `allowed_risk_*` (bull band) |
| SELECTIVE | 2–3 max | half | A-setups only | `allowed_risk_*` (warn band) |
| DEFENSIVE | 0–1 | quarter | flawless only | `allowed_risk_*` (bear band) |
| NO_TRADE | 0 | — | sit out | ink-inverted, "no new risk" |
| STALE/DEGRADED | — | — | wait for fresh data | gray |

Badge uses existing `POSTURE` class map from `RegimeSummary.jsx`. Banner tint = posture band bg.

### 1.3 Fix (b) — flip/trend affordance on XP and 4.5R dials
**Problem:** headline dials show only today's value; user wants recent trend.
**New `<FlipDial label value term history=[…] fmt/>`** — replaces the flat `StripCard` for XP and 4.5R (and reusable for any headline number). Two faces, click ▸flip icon or the tile to toggle:
- **Face 1 (default):** big headline number (mono 20px) + label + InfoDot.
- **Face 2:** a 10–15 session **mini-sparkline** of that metric + `Δ vs 10 sessions ago` signed chip + first/last value. No layout shift (same tile box).
- **Data:** XP ← `/api/regime/history?days=15` field `xp_value`. 4.5R ← **needs history** — currently `/api/regime/history` returns `xp_value, market_mode, mbi_day_color, warning_day` but **not `r4p5`** (see Open Q2). Until added, 4.5R flip shows today's value + "trend unavailable" empty face.
- Sparkline: reuse the `<Sparkline>` math already in `BreadthSparkline.jsx` — extract it into a shared `<MiniSpark values=… stroke=…/>` and delete the duplicate copy in `RegimeHistoryStrip.jsx`.

### 1.4 Fix (c) — Prefer/Avoid presentation
**Problem:** "stickers not looking good/organized."
**New `<SetupStickers preferred=[] avoid=[]/>`** — its own bordered card (not crammed into a strip tile), two labelled rows:
- Row `PREFER` — eyebrow label + green-band chips, each with a `▸` glyph.
- Row `AVOID` — eyebrow label + bear-band chips, each with `✕`.
- Chips: `rounded-chip border px-2 py-0.5 font-mono text-[10px]`. Prefer = `bull-bg/bull/bull-border`; Avoid = `bear-bg/bear/bear-border`. Wrap, aligned in a labelled grid (left 64px eyebrow column, right = wrapped chips) so it reads as two tidy rows, not a jumble.
- Empty state: `"No setup guidance for this regime — sit tight."`
- Data: `preferred_setups`, `avoid_setups` from `/api/regime/summary`.

### 1.5 Fix (d) — Regime history relabel (replaces `RegimeHistoryStrip.jsx` internals)
**Problem:** "Regime History 90D is vague, unlabelled, purpose unclear."
**Rework `<RegimeTrend/>`** (keep component, rewrite body):
- Default window **60D** (90 was too wide to read); Beginner caption states the window in words.
- **Title + subtitle:** `"XP & Posture — last 60 sessions"` / sans caption `"Blue line = XP dial (0–100). Colored ribbon below = market posture that day."`
- **XP line** gets a labelled y-axis: min/mid/max ticks (`0 · 50 · 100` or data-driven), a faint 50 gridline, and **hover tooltip** showing `date + XP`.
- **Posture ribbon** gets an explicit **LEGEND** row beneath: four swatches `■ Risk-On (green) ■ Selective (orange) ■ Defensive (red) ■ No-Trade (ink)` + a note that the white dot = warning day.
- **READ line** (new, generated): `"XP {rose/fell} {a}→{b} over {n} sessions; posture is {mode}."`
- Data: `/api/regime/history?days=60`. Already returns everything needed.

### 1.6 Component ledger — Regime
| Component | Verdict | Note |
|---|---|---|
| `RegimeSummary.jsx` | **REWORK** | becomes a thin container: renders PostureCommandBar + FlipDial strip + SetupStickers + MarketQuadrant. Strip 6-tile grid dissolved. |
| `StripCard` (inner) | **KILL** | replaced by FlipDial + fixed cells; posture tile → PostureCommandBar. |
| `QuadrantCard` (inner) | **KEEP** | already spec-correct (rail + state + question + conf + READ). Add InfoDot terms already present. |
| `RegimeHistoryStrip.jsx` | **REWORK → `RegimeTrend`** | relabel, legend, axis, hover, READ, 60D. |
| `BreadthSparkline.jsx` | **REWORK** | extract `<MiniSpark>`; keep the breadth caption logic. |
| `DivergenceFlag.jsx` | **KEEP** | good as-is; move to render inside PostureCommandBar footer so the caution sits with the posture read. |
| `SectorsThemesPanel.jsx` | **KEEP, minor** | swap inline stock-chip rendering in `StockDrilldown` for the shared `<SymbolChip>`; replace footer `as of` with `<DataStamp>`. |
| `<PostureCommandBar>` | **NEW** | §1.2 |
| `<FlipDial>` | **NEW** | §1.3 |
| `<SetupStickers>` | **NEW** | §1.4 |
| `<MiniSpark>` | **NEW** (extracted) | shared sparkline math |

---

## 2. SETUPS screen — scanner / candidate cards

### 2.1 Wireframe
```
┌─ FILTER BAR ───────────────────────────────────────────────────────────┐
│  posture-gated banner: "SELECTIVE — showing A-setups only"               │
│  [setup type ▾] [min RS ▾] [sector ▾]         sort: [readiness ▾]        │
└──────────────────────────────────────────────────────────────────────────┘
┌─ CANDIDATE GRID (cards, 2–3 col) ──────────────────────────────────────┐
│  ┌ SymbolCard ────────────────┐  ┌ SymbolCard ─────────────┐            │
│  │▎RELIANCE      READINESS 87 │  │▎TATAMOTORS   READINESS 74│            │
│  │  A+  pullback-to-10EMA     │  │  B   flat-base breakout  │            │
│  │  [mini chart + pivot line] │  │  ...                     │            │
│  │  RS82·DLV71%·▲+1.2%[LIVE]  │  │                          │            │
│  │  evidence: [RS>70][vol²]…  │  │                          │            │
│  │  PLAN entry 1420 stop 1380 │  │                          │            │
│  │  ── READ ── clean pullback │  │                          │            │
│  │  [+ Watchlist]  [Journal]  │  │                          │            │
│  └────────────────────────────┘  └──────────────────────────┘            │
└──────────────────────────────────────────────────────────────────────────┘
   <DataStamp>
```

### 2.2 Components & rules
- **`<CandidateCard/>`** (design §3): symbol (as SymbolCard header) · setup name · **Trade Readiness 0–100 + grade A+→C** · mini chart with pivot line (lightweight-charts, shared with drawer) · **evidence chips** (named filters that fired — blue chips; "no black-box scores") · trade-plan box (entry / stop / target — **plan only, NO buy button**, hard rule) · **[+ Watchlist]** one-click add + **[Journal]** 2-tap log.
- **Posture gate:** the filter bar reads `market_mode` and, in SELECTIVE/DEFENSIVE, pre-filters to A-grade (with a visible "why filtered" note). NO_TRADE → empty state, not a hidden grid.
- **`[+ Watchlist]`** writes to watchlist store (see Open Q3 — endpoint TBD).

### 2.3 Data contract
> **No candidate/setups endpoint exists yet in `api/app.py`.** This screen is blocked on backend (Open Q3). Spec the frontend contract so the endpoint can be built to fit:
```
GET /api/setups?date=&min_rs=&setup=&sector=&grade=
→ { available, as_of, posture_mode, candidates: [{
      symbol, setup, readiness (0-100), grade,
      rs, delivery_pct, last_quote?, pivot, entry, stop, target,
      evidence: [{filter, value}], read
   }] }
```
Reuse `<SymbolChip>` fusion inside each card; reuse `<Read>`; reuse `<DataStamp>`.

### 2.4 States
- **Empty:** `"0 setups tonight — market is {mode}, sit tight."` (the mandated §7 empty copy).
- **Stale / Auth / Loading:** shared banners + skeleton cards.

---

## 3. WATCHLIST screen — entry-timing + position sizing

### 3.1 Wireframe
```
┌─ POSITION SIZE CALCULATOR (sticky top) ────────────────────────────────┐
│  Capital [₹5,00,000]  Risk% [0.75]  Stop dist [auto/manual]              │
│  → Shares: 320   Position: ₹4.5L   Risk: ₹3,750                          │
│  ⚠ regime-gated: SELECTIVE caps risk at 0.75% — using cap.               │
└──────────────────────────────────────────────────────────────────────────┘
┌─ WATCHLIST TABLE ──────────────────────────────────────────────────────┐
│ SYMBOL      RVOL  GAP%  DIST-PIVOT  ADR   DLV%   [size]  [chart] [drop]  │
│ RELIANCE    1.8×  +0.4  -0.6%       2.1%  71%    …                       │
│  ── READ ── coiling right at pivot on rising delivery; RVOL building.     │
└──────────────────────────────────────────────────────────────────────────┘
   <DataStamp>
```

### 3.2 Position-size calculator (`<PositionSizer/>`) — the headline feature
- **Formula:** `shares = floor( (capital × riskPct/100) ÷ stopDistancePerShare )`. Position value = `shares × entry`. Risk ₹ = `shares × stopDistancePerShare`.
- **Regime-gated:** clamp `riskPct` to `min(userRisk, allowed_risk_max_pct)` from `/api/regime/summary`; show a warn note when clamped. In NO_TRADE, disable the calculator with `"No new risk in NO_TRADE regime."`
- Inputs mono, tabular-nums; output row big mono numbers. All plain-English labelled + InfoDots.

### 3.3 Entry-timing metrics per row
| Col | Meaning | Source | Band |
|---|---|---|---|
| RVOL | today vol ÷ avg vol | bhavcopy / Fyers intraday | ≥1.5 bull |
| GAP% | open vs prev close | bhavcopy / Fyers | signed |
| DIST-PIVOT | % from pivot | derived (needs pivot) | near-0 bull |
| ADR | avg daily range % | bhavcopy history | info |
| DLV% | delivery % | bhavcopy | ≥60 bull |
- Each row = `<SymbolCard>` inline variant + a `<Read>` line.

### 3.4 Data contract (blocked — Open Q3/Q4)
```
GET  /api/watchlist            → { items:[{symbol, entry, stop, ...metrics}] }
POST /api/watchlist  {symbol}  → add
DELETE /api/watchlist/{symbol} → drop
GET  /api/symbol/{sym}/timing  → { rvol, gap_pct, dist_pivot, adr, delivery_pct, quote? }
```
None exist yet. Sizer works client-side today off manually-entered entry/stop; metrics need the timing endpoint.

---

## 4. JOURNAL screen — trade log + expectancy

### 4.1 Wireframe
```
┌─ EXPECTANCY HEADER ────────────────────────────────────────────────────┐
│  Win% 48   Avg R +0.9   Expectancy +0.4R   Trades 63                     │
│  ── READ ── Small positive edge; biggest leak = "chased extended" (11×). │
└──────────────────────────────────────────────────────────────────────────┘
┌─ TRADE LOG TABLE ──────────────────────────────────────────────────────┐
│ DATE  SYMBOL   SETUP        R    MISTAKE-TAGS         RESULT             │
│ 07-01 RELIANCE pullback   +2.1  —                    win                 │
│ 06-28 TATAMOT  breakout   -1.0  [chased][late-stop]  loss                │
└──────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Components
- **`<ExpectancyHeader/>`** — Win%, Avg R, Expectancy (R), trade count, each a headline number + InfoDot; a READ line naming the top mistake tag. Bands: expectancy >0 bull / <0 bear.
- **`<TradeLogTable/>`** — sortable; symbol col uses `<SymbolChip>`; **mistake tags** = muted/bear chips from a fixed tag vocabulary (see Open Q5); R colored signed.
- **`<TradeEntryForm/>`** — add/edit a trade (date, symbol, setup, entry/exit/stop, mistake tags, notes). Modal, styled like `FyersSetupPanel`'s field pattern.

### 4.3 Data contract (blocked — Open Q3)
```
GET  /api/journal            → { trades:[…], stats:{win_pct, avg_r, expectancy_r, count} }
POST /api/journal {trade}    → add
```
No journal endpoint/table exists. Fully backend-blocked; frontend can be built against a stub.

---

## 5. CHART DRAWER — global, opens from any SymbolChip/Card

### 5.1 Behavior
- A right-side slide-over (not a tab). Opens on `onSelect(symbol)` from **any** SymbolChip/Card anywhere.
- **Content:** lightweight-charts candles + **10/21/50 EMA** overlays · **volume pane** with **pocket-pivot** markers · **price-action badges** (side) · a header SymbolCard (the fused RS/DLV/quote) so the three sources sit atop the chart · preset-locked overlays (switching preset never mixes overlays — design rule).
- **READ line** under the chart summarizing the setup.
- Close on `esc` / backdrop / ✕.

### 5.2 Data contract (blocked — Open Q4)
```
GET /api/symbol/{sym}/ohlc?tf=1D&n=250 → candles + volume
GET /api/symbol/{sym}/quote            → live Fyers quote (auth-gated)
```
No OHLC endpoint exists. Blocked on backend + the `lightweight-charts` dep (not yet in the frontend).

---

## 6. Failure states (designed, not asserted) — matrix

| State | Trigger | Design |
|---|---|---|
| **Loading** | any fetch pending | mono shimmer skeletons matching final layout; no layout shift. Reuse existing skeleton patterns. |
| **Empty** | `available:false` or 0 rows | dashed-border block, plain-English "nothing here + why + what to do." Setups: `"0 setups tonight — market is {mode}, sit tight."` |
| **Stale** | primary source older than threshold (Regime >4d already forced server-side via `days_behind`) | **loud red banner** + affected numbers `opacity-60 grayscale` + **posture hard-degrades to gray**. Banner says *what* is stale and whether re-running helps (Regime's already does this — reuse the honest copy). |
| **Auth-needed** | `health.fyers_connected === false` | orange reconnect banner (exists in `App.jsx`); live surfaces (quotes, MARS, RVOL/GAP intraday) marked with a muted `·` placeholder + `"needs Fyers"` title — never a fake number. |

Every screen renders `<DataStamp>` so "which source, as of when" is always answerable — this is the standing cure for "sources feel disconnected."

---

## 7. Kill / Keep / Rework — master ledger

**KILL**
- `StripCard` (inner of RegimeSummary) — dissolved into PostureCommandBar + FlipDial.
- The 6-tile decision-strip grid in `RegimeSummary.jsx`.
- Duplicated sparkline math in `RegimeHistoryStrip.jsx` (→ shared `<MiniSpark>`).
- `Chart` **tab** in `App.jsx` (charting becomes a drawer).
- Ad-hoc `as of {date}` footer strings across components (→ `<DataStamp>`).

**KEEP (as-is or near)**
- `InfoDot.jsx` + `GLOSSARY` — the beginner glossary pattern (extend vocab per new terms: rvol, gap, adr, delivery, readiness, expectancy, dist-pivot).
- `QuadrantCard`, `DivergenceFlag.jsx`, `FyersSetupPanel.jsx`, `HealthPage.jsx`.
- Tailwind config + tokens (untouched — LAW).
- `SectorsThemesPanel.jsx` core (drill logic, tabs, bars).

**REWORK**
- `RegimeSummary.jsx` → thin container (§1.6).
- `RegimeHistoryStrip.jsx` → `RegimeTrend` (labels/legend/axis/hover/READ/60D).
- `BreadthSparkline.jsx` → extract `<MiniSpark>`.
- `DataCoverage.jsx` → generalize to `<DataStamp>` used on every screen.

**NEW**
- Primitives: `<SymbolChip>`, `<SymbolCard>`, `<DataStamp>`, `<Read>`, `<MiniSpark>`, `<ChartDrawer>`, `DensityContext` + Beginner⇄Expert toggle.
- Regime: `<PostureCommandBar>`, `<FlipDial>`, `<SetupStickers>`.
- Setups: `<CandidateCard>`, `<FilterBar>`, `<EvidenceChips>`.
- Watchlist: `<PositionSizer>`, `<WatchlistTable>`.
- Journal: `<ExpectancyHeader>`, `<TradeLogTable>`, `<TradeEntryForm>`.

---

## 8. Build order (so a coding agent can sequence)
1. **Primitives first:** `<Read>`, `<MiniSpark>`, `<DataStamp>`, `DensityContext`/toggle, `<SymbolChip>` (Fyers/DLV fields degrade gracefully if endpoints missing).
2. **Regime rework** (all data exists today — ship this fully): PostureCommandBar → FlipDial(XP) → SetupStickers → RegimeTrend → wire SymbolChip into Sectors drilldown.
3. **Nav retarget** + Beginner⇄Expert.
4. **Backend-blocked screens** (Setups / Watchlist / Journal / ChartDrawer) — build UI against stubs; wire when endpoints land.

---

## 9. Open questions needing the user's call
1. **DLV% (delivery) banding thresholds** — what delivery % is "strong" for the SymbolChip? (Spec assumes ≥60 bull / 40–59 muted / <40 bear — confirm or give real thresholds.)
2. **4.5R history** — `/api/regime/history` doesn't return `r4p5`; the FlipDial trend for 4.5R needs it. Add `r4p5` to that query, or accept "trend unavailable" on the 4.5R dial?
3. **Backend for Setups / Watchlist / Journal** — none of `/api/setups`, `/api/watchlist`, `/api/journal` exist. Are these in scope for this pass, or is the pass **Regime-only** with the other three screens spec'd-but-stubbed? (Recommend: ship Regime now, stub the rest.)
4. **Chart data + dep** — no OHLC endpoint and `lightweight-charts` isn't in the frontend deps. Confirm we add the dep + an `/api/symbol/{sym}/ohlc` endpoint, or defer the ChartDrawer to a later pass (SymbolChips would then be non-clickable placeholders).
5. **Mistake-tag vocabulary** — Journal needs a fixed tag list (e.g. chased-extended, late-stop, oversized, no-plan, cut-winner-early, ignored-regime). Provide the canonical set, or should I propose one?
6. **Direction A vs B default** — design guidance recommends Dir-B (briefing) for Beginner default, Dir-A (instrument) for Expert. This spec builds the **briefing** PostureCommandBar as the default. Confirm that's the intended default, or do you want the dense instrument strip as default?
