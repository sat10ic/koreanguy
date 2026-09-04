# Competitor study — earningspulse.ai (2026-07-25)

**Why this exists.** The user sent nine URLs with one line: *"look how simple they've
made the concepts I've asked since day 1."* Every page was opened and read live
(browser DOM extraction; WebFetch returned HTTP 429). Everything below is quoted or
counted from the rendered pages, not inferred from marketing copy.

**The verdict in one line:** the gap is **information architecture and copy**, not
visual polish or missing computation. They have ~9 pages each answering ONE question.
We have 6 tabs, one of which stacks **17 panels**.

---

## 1. Pages read

| URL | Title | One-line purpose (their words) |
|---|---|---|
| `/worm?market=IN&mode=nearhl` | Market Worms — Live Advance vs Decline | "Real-time breadth — is the broader market healthy, or are five names masking the picture?" |
| `/rrg?category=themes&window=12&tf=D` | Relative Rotation Graph | "Which sectors are gaining strength" |
| `/sector-cycles` | Sector Cycles — Weekly Industry-Group Cycle Tracker | "Simple sector phase: early, mature or weak" |
| `/markets/movers` | Top Gainers & Losers Today | "Stocks moving with price and turnover" |
| `/fii` | FII/DII Pulse | "Foreign/domestic buying and selling" |
| `/smart-money` | Smart Money Radar | "Large deals and insider activity" |
| `/brokerage-actions` | Ratings — Analyst Upgrades, Downgrades & Initiations | "Broker upgrades, downgrades and targets" |
| `/learn` | Pulse Academy | "Learn the Pulse stack and how regulars actually use it" |
| `/learn/ipo-tracker` | IPO Tracker guide | template example of a single guide |

Their full surface, from `/learn` (each with a plain-English one-liner):

- **Market state** — Market Worms, RRG Charts, Heatmap, Market Movers, FII/DII Flow,
  Smart Money, Analyst Ratings `NEW`, Sector Cycles `BETA`, Macro Maps,
  **Price Alert Scoreboard ("Did alerts lead to price moves?")**
- **Earnings** — Calendar, Screener, Concalls `BETA`, Earnings Heatmap, Sector Scorecard `NEW`
- **Catalysts** — Orders Screener `NEW`, Orders Heatmap, Market News, IPO Tracker, Filings/Insights
- **Telegram channels** — Street/IPO/Market/News/Concall Pulse, Earnings Pulse USA
- **AI tools** — Market Intelligence ("Daily market summary in simple language")

---

## 2. The repeated page template

Every page carries the same skeleton:

1. **Top learn-link**, with a subtitle naming exactly what the guide covers.
   - `/fii`: "New here? Learn how to read FII / DII flows — Foreign and domestic institutional cash flow — what to weight, what to discount"
   - `/smart-money`: "New here? Learn how to read bulk and block deals — Institutional vs HFT signals — which deals matter and which to discount"
   - `/worm`: "New to the worm? Learn how to read it — Anatomy, signal markers, divergence patterns and the day-type playbook"
2. **Title + one-sentence purpose**, jargon-free.
3. **Date stepper** — `← Today · 24 Jul →`, `↩ Latest`.
4. **Count chips** for instant shape, before any table.
5. **Freshness, explicit** — "Updated 0s ago", sync `5s/15s/30s/60s/Off`,
   "Last report: 30 Jun 2026", "This week's grid publishes Monday at 07:00 IST".
6. **The content** (chart / table / cards).
7. **Methodology block with real numbers** + a not-advice line.
8. **Guide & FAQ**, grouped, ending in external references.

Cross-page conventions: maturity labels `NEW` / `BETA`, tier labels `FREE` / `PRO` /
`STARTER`, market switch `🇮🇳 NSE / 🇺🇸 NYSE`, and a **"TV Watchlist"** export
(push symbols to TradingView).

---

## 3. Page-by-page detail

### 3.1 `/worm` — the best-designed page

Three modes, each labelled with a **question**, not a metric name:

| Mode | Label |
|---|---|
| Near H/L | "Where are stocks in today's range?" |
| A/D | "Broad Market" |
| NH/NL | "Are Breakouts working?" |

Inline threshold explanation with actual numbers:
> "Near H/L — Where are stocks in today's range? **Top 30% of range = pressure into
> highs; bottom 30% = pressure into lows.** The honest read of intraday strength on gap days."

**Headline verdict, then immediately undercut:**
> `🟢 Near High Leading  79.2% vs 20.8%  +4 · no conviction, choppy.`

**★ THE STANDOUT FEATURE — divergence detection ("Worms Disagree"):**
> "A/D is bullish (50.2%) but NH/NL disagrees (37.3%) — stocks are advancing but few
> are breaking out. Wide but shallow breadth."
> `→ What does Disagree mean?`

Stat row: `NRH/NRL 79% · ADV/DEC 1.01 · NH/NL 37% · Advancing 1,183 (49.5%) ·
Declining 1,171 (49.0%) · Unchanged 38 · New High 288 · New Low 485`.
Intraday time-series chart 10:00–15:00 with signal markers `★ ▲ ⚠` plotted on it.
Filters: cap `All/Large/Mid/Small`, day `Today/Prev Day`.

FAQ groups: Understanding the Chart · The Three Modes · Reading Signals (crossovers,
trend reversal, Disagree, Stretched) · Using the Tools · **Practical Playbook** ·
Further Reading (Investopedia, StockCharts, CME Group).

**Practical Playbook items are workflow, not definitions:**
"Morning routine — first 30 minutes" · "Spotting fake rallies with divergence" ·
"When extreme readings actually matter" · "Combining cap filters with signals".

### 3.2 `/rrg`

Controls: Market `India/Global` · category `Indexes/Themes/Sectors` · 16 presets ·
benchmark `vs Nifty 50 / Nifty 500 / Bank Nifty / Midcap 50 / Nifty Next 50` ·
quadrant filter `Leading/Improving/Weakening/Lagging` · TF `D/W/M` · scale
`Dynamic/Fixed` · tail length · **Animate** (time scrubber to replay rotation).
Axes labelled `JdK RS-Ratio` / `JdK RS-Momentum`, date range shown `2026-06-29 → 2026-07-24`.

**AI INSIGHTS** block names groups and states the rotation:
> "IT & Internet and Consumer sectors are leading, showing strong relative strength.
> NBFCs & Capital Markets, Real Estate & Cement, Pharma & Healthcare … are weakening,
> suggesting a rotation out of these sectors. Banks, Metals & Mining, and Energy are
> improving, indicating potential upward movement."

Per-ticker **direction arrows with words**: `↑ Accelerating`, `↗ Strengthening`,
`→ Decelerating`, `↘ Weakening`. FAQ explicitly kills the common misread:
*"Does 'Leading' on the RRG mean the sector is going up?"*

### 3.3 `/sector-cycles` — their most sophisticated page

"53 themes rolled into 15 sectors, each graded from Early Expansion through Mid, Late,
and Trough." Weekly, published Monday 07:00 IST. Honest empty state:
> "⏳ This week's grid publishes Monday at 07:00 IST. Showing the most recent published week (Monday, 13 July 2026)."

Columns: `CYCLE` label · `Position` 0–100 · Relative Strength · Earnings · KPIs ·
Flows · `Composite` · **`Aligned` (e.g. 1/3 — how many sub-themes agree)** · Reports ·
**LEADERS / LAGGARD named per sector**.

Sample rows:
```
Real Estate & Cement   LATE-TO-TROUGH   78   +4  1/3  37   PHOENIXLTD GREENLAM  | ULTRACEMCO
Pharma & Healthcare    LATE CYCLE       63   +3  1/3  42   LAURUSLABS NEULANDLAB| DRREDDY
NBFCs & Capital Mkts   EARLY-TO-MID EXP 33   +2  0/5  60   SHRIRAMFIN ANANDRATHI| MUTHOOTFIN
IT & Internet          MID-TO-LATE      32   -1  1/4  52   HFCL MOSCHIP         | HCLTECH
```
Methodology: "Each group carries **anchor stocks, a cycle driver, and empirical proof of
movement from the last 3 years** … an 11-label cycle scale (Early Expansion → Mid → Late
→ Trough → Inflection) with a 0–100 position along the cycle arc. This is a **comparison
workbench for sector rotation, not a tip service**."

### 3.4 `/markets/movers`

"Real-time movers with AI-inferred reasons · India every 5s, US every 10s".
Chips `18↑ 9↓ /1578`, clock `04:06:22 PM`, sort by `Activity / Change% / Turnover`,
cap tag per row (`L/M/S`), turnover in ₹cr.

**★ Every row has a source-tagged WHY — and admits ignorance:**
```
DBL        ₹738cr  +8.7%   AI·Stock-specific momentum
KPITTECH   ₹553cr  +5.9%   Filing·KPIT Technologies Q1 FY27 Earnings Call on July 29.
INDOBORAX  ₹441cr  +11.4%  AI·Indo Borax secures 'BBB+/Stable' credit rating
KABRAEXTRU ₹11.9cr +7.3%   AI·Kabra Extrusiontechnik suspends Daman operations due to heavy rainfall
WENDT      ₹35.5cr +8.7%   Earnings·Good Results
CNL        ₹557cr  +12.3%  AI·No specific news found     <-- HONEST
TECHNVISN  ₹13.4cr +14.6%  AI·No recent news             <-- HONEST
RAMCOSYS   ₹16.2cr -10.0%  Earnings·Weak Results
```

### 3.5 `/fii` — three layers on one page

1. **Daily flows** with buy/sell split shown as % bars, streak chips
   `📉 FII selling 3d` `📈 DII buying 2d`, and a `PROVISIONAL` label.
   `FII/FPI -₹3,892.77 Cr (43%/57%)` · `DII +₹5,453.55 Cr (58%/42%)` ·
   `COMBINED NET BUY +₹1,560.78 Cr`
2. **Cumulative FII net flow** (NSDL depository), `1M / 3M / 1Y`.
3. **Sector-wise FII net flow, fortnightly** — `% of AUM`, direction arrow,
   last-fortnight ₹, `1Y net flow` in both ₹ and %. E.g. Financial Services 28% of AUM,
   ▲ +15K Cr, 1Y −₹84,316 Cr (−3.9%); Sovereign 5.1% of AUM, ▲ +33K Cr, +22.3%.

### 3.6 `/smart-money`

Their "smart money" = **NSE bulk & block deals** (disclosure-based, verifiable).
Sections: `🔷 Block Deals — Pre-arranged trades` and `💰 Bulk Deals — Trades >0.5% of equity`.
Chips: `19 stocks · 11 Bullish · 3 Bearish · 1 Block · 6 Accum.`

**A prose summary that interprets TODAY and names names:**
> "Today's bulk deals demonstrate continued strong institutional and HFT accumulation in
> several stocks, notably Aastha Spintex, Asian Granito, Atal Realtech, Bluestone Jewel,
> Gandhar Oil Refine, Huhtamaki, Indoborax, and Suryoday Small Finance Bank … However,
> **Shadowfax Technologies experienced significant institutional selling**, indicating a
> bearish outlook, while Lotus Developers saw profit booking. Several other deals involved
> wash trades or pre-arranged block transfers, resulting in a neutral sentiment."

They also explain away a non-signal rather than dressing it up:
> "Pre-arranged block deal between SBI Mutual Fund and Nuvama Crossover Funds. Essentially
> a transfer of shares. **No net change in institutional ownership.**"

Per row: symbol · BUY/SELL · conviction `HIGH` · ₹ value · Bullish/Bearish/Neutral ·
↑/↓ split · deal price · %chg.

Methodology, with every threshold stated:
> "NSE bulk deals (trades > 0.5% of equity shares) are fetched daily after 6 PM IST. NSE
> block deals (pre-arranged trades ≥₹10Cr) after 2:30 PM IST. **Known HFT/arbitrage firms
> are filtered out, and bulk deals below ₹2 Crore are excluded.** Remaining deals are
> analyzed by AI to classify institutional intent (Bullish/Bearish/Block) and detect
> multi-day accumulation patterns across both deal types. This is not investment advice."

### 3.7 `/brokerage-actions`

`42 actions · 21 stocks · ⬆8 ⬇5 New 5 ● 20`, broker filter (21 named brokers),
columns `SYMBOL · BROKER · ACTION · RATING · TARGET · RECO PRICE · CMP · UPSIDE · MOVE ·
HEADLINE`, timestamps per row, grouped section `📊 INDICES & SECTOR CALLS`, nested
follow-on rows (`↳`). **We have no data source for this at all.**

### 3.8 `/learn` + `/learn/ipo-tracker` — the teaching layer

`/learn` is sequenced by workflow: *"Channels, briefs, tools and bots — explained in the
order they hand off to each other. Each guide is a **60-second read for the basics and a
5-minute deep read for the workflow**."*

Each guide follows a **rigid template**:

```
Breadcrumb: PULSE ACADEMY · FEATURE · FREE
Title + one-liner
"IF ANY OF THIS SOUNDS FAMILIAR / What this guide is for"
   PROBLEM            what breaks without this
   HOW PULSE HELPS    what the feature does about it
   USE WHEN           the right situation
   NOT FOR            <-- explicit ANTI-use
START LIKE THIS        3 numbered steps
USE IT WHEN
DO NOT CONFUSE IT WITH <-- explicit misuse warning
QUICK USE MANUAL
   WHAT YOU GET / HOW TO READ IT / HOW TO USE IT
QUESTIONS, ANSWERED    "The ones users ask first"
RECOMMENDED WORKFLOW   numbered
```

Their philosophy line, which matches this project's own standing rule:
> "**Separate information from decision-making; Pulse helps you organise the work, not
> outsource judgement.**"

And they write **Hinglish** for Indian retail:
> "IPO Tracker website par IPOs ko stage-wise dikhata hai: upcoming, open, listed."
> "GMP or subscription alone se decision mat lo."

---

## 4. Where we stand against it

| Concept | They | Us |
|---|---|---|
| Breadth / worm | dedicated page, 3 modes, divergence callout | ~10 panels, no cross-check |
| RRG | full page, animate/scrub, AI insight | plan item I2, never built |
| Sector cycles | 11-label scale, 0–100, leaders/laggards | none |
| Movers | reason + source tag on every row | symbol/%chg/price only |
| FII/DII | 3 layers incl. sector-wise AUM | 1 strip, daily only |
| Smart money | bulk/block deals + AI summary | **DEALS & FLOWS = panel 11 of 17, text cards** |
| Analyst actions | full page, 21 brokers | **no data source** |
| Self-scoring | "Price Alert Scoreboard" as a page | `manas scorecard` CLI, never run until today |
| Learn | academy + per-feature guides | none |
| Trade plan / sizing / journal | — | **we have these, they don't** |
| Tape-inferred accumulation | — | **we have this, they don't** |

**Data we already hold** for worm/breadth, movers, FII/DII (all three layers exist in
`fii_dii_daily` + NSDL-style history), sector RS, themes, IPO, and bulk/block deals.
**`ingest_nse_deals` is currently FAILING** (`ValueError: invalid literal for int() with
base 10: 'JU...'`), i.e. the one feed that maps 1:1 onto their flagship page is rotting.

**Data we do not hold:** analyst/brokerage actions, concalls, GMP, macro maps.

---

## 5. Ranked steal list

| # | Idea | Cost | Why |
|---|---|---|---|
| 1 | **Divergence detection** across existing breadth series | none — pure logic | We have 10 panels and never say two disagree. Task #64 |
| 2 | **Learn-guide template** (esp. `NOT FOR` / `DO NOT CONFUSE IT WITH`) | content only | Directly answers "explainers don't teach". Task #63 |
| 3 | **Question-shaped names + count chips + date stepper + freshness** | mechanical | Cheapest readability win on every surface. Task #63 |
| 4 | **Source-tagged WHY per mover**, incl. "no specific news found" | medium | Task #65. Template from DB rows — never free-form LLM |
| 5 | **Honest qualifier on the headline verdict** ("no conviction, choppy") | trivial | Matches our own honesty-layer rule |
| 6 | **`NEW` / `BETA` maturity labels** | trivial | Half our panels are unvalidated and unlabelled |
| 7 | **Methodology block with real thresholds** per page | small | Replaces scattered `[B]` captions |
| 8 | **One concept = one page** | large | The structural fix. Task #63 |
| 9 | Sector Cycles–style phase grid | large | Needs anchor stocks + 3yr proof per group |
| 10 | RRG page | large | `sector_index_prices` already has the inputs |

---

## 6. Cautions

- **Their AI summaries are their biggest risk, and would be ours.** Free-form prose that
  names stocks is exactly where fabrication lands — a subagent in this very session
  invented Sharpe/MAPE figures for papers it had misidentified, and our council text has
  been caught citing an RVOL that contradicted the DB. Any "why" we generate must be
  templated from a joined source row, with "no disclosed reason found" as the honest
  fallback. Never an LLM inventing the fact, only phrasing one that exists.
- **They are not a swing-trading decision tool.** No position sizing, no stop/R:R, no
  journal, no expectancy loop. Copy the presentation and the teaching, not the scope.
  Their own line — "not a tip service", "not outsource judgement" — is the same boundary
  this project already holds.
- **Do not copy breadth-metric names blindly.** Their "Near H/L" is intraday range
  position; our nearest equivalents are EOD. Same words, different measurement.
- **9 pages is more surface to keep alive**, and we currently fail to keep one pipeline
  running for two days. Reliability work (tasks #55, #59, #64's data inputs) has to keep
  pace or we ship nine stale pages instead of one.

---

## 7. Tasks opened from this study

- **#63** Restructure IA: one concept = one page, question-shaped names (controlling brief)
- **#64** Divergence detection across breadth metrics
- **#65** Source-tagged WHY on every mover, with honest "no reason found"
- reframes **#49** (Smart Money section) and **#62** (Expert-mode density)
