# Manas AI Trading OS — State of the Tool (2026-07-06)

A single-user NSE (Indian) cash-market swing-trading cockpit. This document
describes every section: what it does, how it works, the data behind it, its
current state, and where it is going wrong. Written after a critical review that
scored the tool's *edge* at **3/10 — "a well-built reskin of free data."**

---

## 0. Vision & non-negotiable constraints
- **Purpose:** answer, each day, "how aggressive can I be?" (regime) → "what specifically do I trade?" (setups) → "how do I enter/size/exit?" (chart + sizer) → "what did I learn?" (journal). For a beginner, with expert depth on demand.
- **Founding principles (binding):** rules-first / **no black-box scores** (every number decomposes into visible evidence) · **manual execution only** (no order routing, ever — keeps it outside SEBI's algo framework + preserves the human veto) · single-user localhost · public data only · **anti-mashup** (one writer per metric, one ranked number per screen, no parallel engines, no dormant code).
- **The intended moat** (mostly NOT built yet): a feed that *refuses* most names (regime-gated selectivity), one explainable opinion per symbol, and a **compounding private journal→outcome→learnings loop** — proprietary data a competitor copying the UI cannot start with.

## 1. Data sources
| Source | Gives | State |
|---|---|---|
| **NSE bhavcopy** (`sec_bhavdata_full`) | daily OHLCV + **delivery %** per EQ symbol | ingested to 2026-07-03; ~862k rows, 2025-03→2026-07 |
| **ChartsMaze dumps** | per-stock **RS ratings**, 26 technical screeners (VCP/tight/momentum/shakeout/gap/etc), sector+industry RS, RRG, **ASM surveillance flags**, per-stock **EPS/sales/OPM growth** (QoQ/YoY), disclosure feeds (order-wins, announcements, bulk-deals, insider, circuit-revision, episodic-pivot), partial market cap | screeners ingested (07-05); disclosure feeds mostly on-disk, un-ingested |
| **Fyers API** | live + intraday candles, websocket, quotes | provider exists; live loop not built; pre-open coverage unconfirmed |
| **We LACK** | full balance-sheet fundamentals (ROE/D-E/P-E/book value/margins), consensus/forward estimates, options data, tick history beyond Fyers | — |

## 2. Architecture
FastAPI backend (:8000) + React/Vite/Tailwind frontend (:5173) + one SQLite `manas.db`. One EOD pipeline (`manas run-eod`) orders the stages: ingest bhavcopy → NIFTYMIDSML400 breadth → ChartsMaze sectors/screeners → indicators → MARS → regime snapshot → scanner candidates → outcomes backfill. Every metric has exactly one writer. Point-in-time (never overwrites history). 109 backend tests, frontend builds clean.

---

## 3. Sections

### 3.1 Regime page (flagship — "how aggressive today")
- **Does:** posture verdict (RISK_ON / SELECTIVE / DEFENSIVE / NO_TRADE) + concrete approach ("trade 2-3 max, half size, A-setups, risk 0.35-0.5%"); XP energy dial + band; MBI breadth ratios (20R/50R/4.5R) with day-color; since-yesterday deltas; 20-session breadth color grid; 60-session participation chart; sectors & themes leaderboard (RS + perf-flip 1D/1W/1M/3M); top-indices panel; regime history.
- **How:** XP = recursive log-space breadth formula on NIFTYMIDSML400 (400-stock) universe (median ~7, capped 250). MBI ratios from advance/decline + %>MA counts. market_mode from pillars + breadth + warning-day. Calendar-aware staleness (weekends ≠ stale).
- **Data:** breadth_daily (bhavcopy-derived), regime_snapshots, sector_metrics.
- **Where it's going wrong:** **too dense for a beginner** — leads with internals (XP/MBI/grids) not the one decision. **Self-contradicts** — "Breadth 67% strong" renders inches above "Breadth unavailable" (a stale/null path double-renders). The posture *says* SELECTIVE but the Setups feed it links to serves 80 names (see 3.2) — the regime's discipline isn't enforced downstream.

### 3.2 Setups feed (the daily candidate list)
- **Does:** confluence-ranked, quality-gated list of tradeable setups; ONE readiness number (0-100) + grade; evidence chips (which screeners, theme, ASM-clear, EPS growth, price-action signal); score-breakdown; trade-plan advisor (entry trigger/stop/measured-move/watch-for per setup type); add-to-watchlist.
- **How:** candidate pool = symbols in ≥2 ChartsMaze screeners (confluence); hard quality gate excludes ETFs / <₹30 / <₹5cr turnover / microcaps / circuit-locked / ASM-flagged; ranked by confluence + trending-theme boost + earnings-growth + delivery + price-action + RS. Detectors: VCP, pocket-pivot, shakeout, near-pivot, EMA touch/cross/reclaim, Launch Pad, ANTS accumulation, EP (earnings episodic pivot), IPO-base (mini-coil/TVCP).
- **Where it's going wrong (THE core failure):** **the gate doesn't gate.** On a SELECTIVE day it returns **80 cards, 67 graded A+, top 12 all ≥97.5/100, ~80% one theme (pharma).** A filter that passes everything is a screener, not an opinion — and this is exactly the free-data experience. Readiness is **saturated** (too many 100s → the number is meaningless). **Garbage values leak** ("EPS +55250%", "+-5%" sign bug). A #1 pick shows a **27% stop** with no R:R and no size — an un-actionable "plan."

### 3.3 Focus Center (IPO + EP)
- **Does:** a filtered lens on the Setups feed showing only EP (episodic-pivot earnings) + IPO-base setups — India's strongest growth mechanisms. Columns: pattern-label, readiness, base-age/days-since-listing, tight-stop RR, growth chip, circuit state.
- **How:** `filter(setups where setup_type in [ep, ipo_base])` — same rows/one number, no second engine. EP detector = 30% QoQ+YoY EPS+sales + gap-up + neglected base. IPO-base = mini-coil/inside-bar + TVCP, ≤4% stop, listing-date derived from first bhavcopy appearance.
- **Where it's going wrong:** showed **"0 setups tonight"** while the main feed had ipo-tagged cards — the lens filter and detector tags disagree; looks broken on day one. EP "neglected base" logic conflates a breakout with "neglected" (source drift).

### 3.4 Watchlist + position sizer
- **Does:** watchlist table with entry-timing metrics (RVOL, gap%, dist-from-pivot, delivery%) + exit-state (Intact/Weakening/Broken from the Market Navigator engine) + a position-size calculator (capital × risk% ÷ stop-distance → qty + ₹ risk, regime-gated caps).
- **Where it's going wrong:** exit-state can **contradict Setups** (a name is "EXIT WEAKENING" here and "readiness 100" there). The sizer isn't pre-filled onto the setup cards where the decision is actually made.

### 3.5 Journal (the un-copyable asset — currently inert)
- **Does (intended):** log trades, mistake tags, expectancy (win rate, avg R); the compounding private dataset that becomes the moat.
- **Where it's going wrong:** it's an **empty manual form.** No link from setups (no one-click capture), no auto-context, no outcome backfill wired to the UI, no expectancy fed back onto cards. The one thing free sites can't replicate — and it's a stub. **This is the single biggest missed opportunity.**

### 3.6 Chart drawer
- **Does:** click any symbol → candles + EMAs (10/21/50) + volume + pocket-pivot marker + buy-zone/stop + AVWAP + RS line + TTM histogram + entry/exit arrows + Weinstein stage + trailing-stop read.
- **How:** real arithmetic shown (stage from 150-day SMA structure, AVWAP anchored, pocket-pivot from volume rules). Switched to lightweight-charts for zoom/pan.
- **Where it's going wrong:** volume rendering + zoom + measured-move-line position need browser QC. AVWAP auto-anchor is naive (missing the anti-thrash spec). Historically over-labelled.

### 3.7 Health + Beginner/Expert toggle
- **Health:** data coverage per source, staleness, Fyers auth state, pipeline runs. Works but should be a header chip, not a tab.
- **Toggle:** intended progressive disclosure (beginner = one decision; expert = full depth). **Currently cosmetic — the DOM is byte-identical in both modes** (only one component reads the density flag). Two header buttons that lie.

---

## 4. Detector / signal inventory (what the feed can "see")
Price-action: EMA touch/cross/reclaim, 15/21-EMA trailing stop, shakeout (undercut+reclaim), pocket-pivot, Weinstein stage. Patterns: VCP, tight-setup, Launch Pad (MA-coil), IPO mini-coil/TVCP. Accumulation: ANTS (15-day price+volume+up-days), delivery%. Catalyst: EP (earnings gap + 30% growth). Exit: Market Navigator (below/cross 21EMA, 50/200SMA loss, distribution days/clusters, lower lows, downside-reversal → Intact/Weakening/Broken). Context chips: RS rating, Absolute Strength percentile, EPS-growth percentile, RMV compression, confluence count, trending-theme.

## 5. The edge gap (why it's 3/10 today)
Everything currently *rendered* — RS, delivery, pullbacks, pocket-pivots, breadth, sector heat — is free on Chartink / TradingView / ChartsMaze (the scraped source). The three things that would BE an edge exist only as stubs or are actively broken:
1. **Selectivity** — the gate passes 80 names; a real edge is a feed that says NO.
2. **One trustworthy opinion per symbol** — the app contradicts itself (readiness vs exit-state; breadth vs breadth-unavailable), which is fatal for a *judgment* tool.
3. **The compounding journal→learnings loop** — the only un-copyable asset, currently an empty form.

Plus: regime discipline isn't enforced downstream, data-integrity leaks (absurd EPS, 27% stops) kill credibility, and the beginner/expert switch does nothing.

## 6. Built vs stub
- **Built + working:** regime posture command bar, XP/MBI computation, evidence chips, exit-state engine, chart-drawer math, position sizer, EOD pipeline, quality-gate *mechanism* (just miscalibrated), IPO/EP/ANTS/chip detectors (wired, need tuning).
- **Stub / broken / planned:** the gate actually refusing (miscalibrated), one-opinion reconciliation, journal-as-loop, live intraday Telegram loop, real beginner/expert toggle, mentor checklists, weekly learnings retro, data-integrity clamps.

## 7. What "turning it into an edge" means concretely
Not more detectors (the feed is already over-wide). The edge is: **a regime-gated feed that refuses most days + pre-committed trade plans with real risk math + a journal that learns YOUR per-setup/per-regime expectancy and feeds it back** — plus a disciplined live-alert loop (manual-confirm) so the process is executed, not just displayed. The alpha is in *selectivity, discipline, and the compounding private dataset*, not in the indicators (which are commodities).
