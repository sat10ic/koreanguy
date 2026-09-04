# Tradl.in Discovery — Full Public Screen Catalog

Captured 2026-07-18 from a live logged-in session (tradl.in/stock-discovery).
Source: the page's own bulk data payload (`/api/samples/queries?query_type=screening`), which is
what the Discovery card grid renders from — not hand-copied cards, so criteria text is verbatim.

**Counts.** API returned **64 screen definitions** (all flagged public). The UI badge says
"Public Screens 50 / My Screens 1" — the extra ~13 are near-duplicate/legacy rows the UI
apparently dedupes (dup pairs flagged below) plus 2 entries with no sentiment tag.
Universe field says "Nifty 50" on every screen but member lists span the broad NSE universe —
that field is unreliable/vestigial on their side.

**Member format:** `SYMBOL +x.x%` = return since the stock was featured into the screen
(their "SINCE FEATURED IN" metric), date = featured date. Screens showing `—` had an empty
current-member snapshot at capture time.

**Data bug observed (theirs):** #24 "EMA 20 Crossover Bullish" carries the *bearish* criteria
text (identical to #23) — copy/paste defect in their catalog.

---

## Chart Patterns (13)

| # | Screen | Tag | Criteria (verbatim, trimmed) | Current members (since-featured %) |
|---|--------|-----|------------------------------|-------------------------------------|
| 9 | Near Breakout | bullish | Breaking above Pivot Point resistance (R1/R2/R3) today, cross above resistance with volume ≥1.5x avg | FEDERALBNK +3.4% (07-17) |
| 10 | Triple Bottom | bullish | Triple bottom; price crossing above 50-day MA, vol >1.5x 20d avg, RSI(14)>55, MACD positive, 6M return < -15%, within 10% of 52w low | — |
| 11 | Triple Top | bearish | Three peaks within 3% over 2-6 months, breaking below support with vol ≥1.3x 20d avg, RSI<40, MACD negative, prior +15% up-move | APLAPOLLO -8.0% (05-07); ASAHIINDIA +4.7% (03-17); CANFINHOME -3.2% (07-07); DCBBANK +2.9% (06-24) |
| 12 | Head & Shoulders | bearish | Three peaks, middle highest, breaking neckline with vol ≥1.3x 20d avg, RSI<50, MACD bearish cross | AGARWALEYE +10.9% (04-28); DYNAMATECH +1.7% (06-12); HINDALCO +2.0% (03-04); INDIANB -15.0% (02-25) |
| 13 | Cup & Handle | bullish | Rounded U bottom, handle pullback 5-15%, breaking handle resistance with vol ≥1.5x 20d avg, above 200-SMA | ABB +3.6% (06-04); AVANTIFEED -1.9% (07-17); CREDITACC 0.0% (06-25); HSCL +5.1% (06-17); JKPAPER 0.0% (07-14) |
| 40 | Death Crossover | bearish | 50-day MA crossed below 200-day MA recently | APLAPOLLO -1.6% (07-09); ASHOKLEY -1.0% (07-09); ASTRAL +4.5% (07-10); BANKINDIA +5.3% (07-09) |
| 41 | Golden Crossover | bullish | 50-day MA crossed above 200-day MA recently | — (0 stocks currently) |
| 48 | Tight Range Consolidation | bullish | 20-day high-low spread ≤10% lasting 10-30 days, declining volume, preceded by ≥10% move in prior month, price near range middle | AAVAS +0.9% (07-15); ABCAPITAL -1.1% (07-15); ABSLAMC +1.2% (07-17); ACE +0.3% (07-15) |
| 49 | Rising Wedge (Bearish) | bearish | Rising but converging highs/lows over 3-8 weeks, breaking lower trendline with vol ≥1.3x, RSI bearish divergence | — |
| 50 | Triple Bottom - Breakout | bullish | Three troughs within 3% over 2-6 months, breaking resistance with vol ≥1.5x, RSI>55, MACD positive (dup concept of #10) | ABFRL -12.1% (05-06); ACE +8.5% (04-10); AFCONS -13.9% (04-16); AFFLE +6.1% (04-16) |
| 51 | Triple Top - Breakdown | bearish | Dup of #11 | HINDALCO +8.4% (03-20); NTPC -2.7% (06-11); VEDL -61.9% (03-25) |
| 52 | Head & Shoulder - Breakdown | bearish | Dup of #12 | DELHIVERY +13.2% (06-10); MUTHOOTFIN -0.6% (07-16); ONGC -7.2% (06-03); PFC -6.7% (06-09) |
| 53 | W-Neckline Breakout | bullish | "W" pattern on daily over last 2 months, recently broke above W-neckline with decent volume | 3MINDIA +1.2% (07-03); AADHARHFC +5.9% (06-15); AARTIDRUGS -0.7% (07-15); ABBOTINDIA +1.4% (05-11) |

## Momentum & Technical (6, +1 legacy "Technical")

| # | Screen | Tag | Criteria | Members |
|---|--------|-----|----------|---------|
| 14 | Bullish Crossover Sustained | bullish | Price crossed above daily 200EMA within last 2 weeks with volume surge; uptrend still holding; next resistance headroom | ALKEM -1.3% (07-17); ANANTRAJ +1.6% (07-17); APOLLOTYRE -0.1% (07-17); APTUS +2.9% (07-16) |
| 54 | Golden Cross + Bullish Momentum | bullish | 50EMA crossing & closing above 200EMA recently + trend reversal + min 5% upside to prior high/resistance (category "Technical", legacy) | AADHARHFC +0.2% (07-17); AEGISLOG +2.6% (07-08); CARTRADE -6.0% (07-15) |
| 55 | Support Bounce with Volume Confirmation | bullish | Tested 10-20 day support low then bounced to close above 50EMA with strong bullish candle, vol ≥1.5x 20d avg on bounce day | — |
| 56 | Pullback in Strong Uptrend | bullish | Up ≥20% 6M and ≥30% 12M, above 100/200 EMA, recently fell 5-10% from 20-day high, RSI cooled to 45-60 | — |
| 57 | Trend + Volume Breakout | bullish | New 2-3 month high, above 50+200 EMA, last-3-session volume ≥1.5x 20d avg, ≥10% 6M return | — |
| 58 | Short-Term Reversal Bounce | bullish | Down >8% in last month, RSI bounced from <35 to 40-55, ≥5% above 52w low, today's vol ≥1.5x | — |
| 64 | Macro Momentum | (untagged) | Strongest 3-month and 6-month momentum | 3MINDIA; ABCAPITAL; ACUTAAS; AETHER; AIAENG |

## Multi-Factor (4)

| # | Screen | Tag | Criteria | Members |
|---|--------|-----|----------|---------|
| 7 | Quality + Momentum Fusion | neutral | Rank on quality (ROE/ROA/margins) and momentum (6M+12M returns), average scores, top 10%, D/E ≤1, mcap >1000 Cr | ADANIPORTS +0.4% (07-12); EICHERMOT +4.1% (07-14); INDIGO -1.0% (07-12); NESTLEIND +8.3% (02-25) |
| 8 | Risk-Adjusted Momentum Rank | neutral | 6M and 12M return / volatility, rank both, average ranks, top 20%, mcap >1000 Cr, above 200-SMA | ABB +3.5% (07-16); ABSLAMC +0.2% (07-15); ACMESOLAR +11.1% (06-22); ADANIENSOL +27.1% (05-20) |
| 59 | Volatility Breakout with Trend Filter | bullish | Above 200-SMA, BB width recently in bottom 20%, now closing above upper band or large ATR move with above-avg volume | — |
| 60 | Liquidity-Adjusted Momentum (High Turnover) | bullish | ≥15% 6M and ≥20% 12M return, top 40% by turnover, above 200-SMA | — |

## Price & Volume Action (10)

| # | Screen | Tag | Criteria | Members |
|---|--------|-----|----------|---------|
| 15 | Top Losers | bearish | Down >3% today | ACMESOLAR; ALKYLAMINE; AMBER; APARINDS (all 07-17) |
| 16 | Top Gainers | bullish | Up >3% today | BHARATFORG +1.2%; EXIDEIND; FEDERALBNK +1.5%; KALYANKJIL +1.5% (all 07-17) |
| 20 | Pullback in Uptrend | bullish | Above 200-SMA, pulled back to test 50-SMA or 20-EMA | 360ONE +0.8% (07-17); AAVAS -0.7% (07-17); ABB +9.7% (07-14) |
| 21 | Price Downtrend | bearish | Below 50 & 200 MA, 50<200, RSI<50 | ABFRL -4.0% (07-13); ABLBL -2.9% (07-14); AFCONS -1.3% (07-17) |
| 22 | Price Uptrend | bullish | Above 50 & 200 MA, 50>200, RSI>50 | 360ONE +0.9% (07-17); ABB +7.5% (07-15); ABCAPITAL +13.8% (06-12) |
| 28 | 52-Week Low | neutral | At/within 2% of 52w low | CELLO 0.0%; GODIGIT -5.9% (07-15); ICICIGI -1.4% (07-16); ITC -0.2% |
| 29 | 52-Week High | bullish | At/within 2% of 52w high | ADANIENSOL +5.9% (07-09); AJANTPHARM +0.3%; APOLLOHOSP +0.9% (07-08); ASTERDM +2.2% (07-09) |
| 31 | Volume Spike | neutral | Unusually high volume today vs average | 360ONE; BHEL -1.9%; FEDERALBNK +4.9%; HAVELLS +3.7% (all 07-17) |
| 32 | Volume Spike with Price Up | bullish | Up today with significantly above-avg volume (accumulation) | AXISBANK; DLF +0.4%; EXIDEIND +0.9%; FEDERALBNK +4.9% (07-17) |
| 33 | Volume Spike with Price Down | bearish | Down today with significantly above-avg volume (distribution) | ADANIGREEN -1.0%; BALKRISIND -0.1%; BHEL -2.9% (07-17) |

## Technical Indicators (23)

| # | Screen | Tag | Criteria | Members |
|---|--------|-----|----------|---------|
| 2 | Indicator Confluence Breakout | bullish | Above 50+200 SMA, MACD bullish cross, Supertrend bullish, RSI 50-70, breaking short-term resistance | ABBOTINDIA +0.3%; ANANTRAJ +0.2%; BAJFINANCE +0.4% (07-17) |
| 17 | ATR Expansion | neutral | ATR expanding vs recent levels in last 7 sessions (rising volatility) | 360ONE -0.1%; AARTIDRUGS -1.2%; AGARWALEYE +3.1%; AIIL +2.0% (07-17) |
| 18 | RSI Bearish Divergence | bearish | Price higher high, RSI lower high | 3MINDIA -3.9% (07-14); ACMESOLAR -4.3% (07-17); AEGISVOPAK -8.9% (07-14) |
| 19 | RSI Bullish Divergence | bullish | Price lower low, RSI higher low | AARTIDRUGS +25.1% (04-01); AARTIIND +20.9% (04-07); AAVAS +16.3% (02-25) |
| 23 | EMA 20 Crossover Bearish | bearish | Price crossed below 20-EMA | 360ONE +1.5% (07-08); AADHARHFC -0.4% (07-14); ABDL -3.4% (07-13) |
| 24 | EMA 20 Crossover Bullish | bearish(!) | **Bug: same bearish text as #23** | ADANIGREEN -0.6%; AIAENG -1.4%; ALKEM 0.0% (07-17) |
| 25 | Stochastic Bullish Cross | bullish | %K crossed above %D from oversold (<20) | ABDL; AFCONS; BBTC +0.7%; DBL +0.5% (07-17) |
| 26 | Stochastic Overbought | bearish | Stochastic >80 | AARTIDRUGS -0.5%; ABBOTINDIA +3.5% (07-10); ABREL +1.8% (07-17) |
| 27 | Stochastic Oversold | bullish | Stochastic <20 | AADHARHFC +0.4% (07-15); ABFRL -0.4%; AEGISVOPAK +2.0% (07-17) |
| 30 | Bollinger Lower Band Touch | bullish | Touched/near lower Bollinger Band | AAVAS +2.1% (07-14); ABB +10.1% (07-08); ABSLAMC +1.0% (07-16) |
| 34 | Bollinger Upper Band Breakout | bullish | Breaking above upper Bollinger Band | ACI +0.2%; AIIL +1.2%; AVANTIFEED +0.5%; BHARATFORG 0.0% (07-17) |
| 35 | Bollinger Band Squeeze | bullish | Tight BB squeeze, low volatility, breakout building | AARTIPHARM +0.5% (07-10); ABCAPITAL +0.8% (07-17); ACE -0.4% (07-17) |
| 36 | Supertrend Bullish Flip | bullish | Supertrend just flipped bearish→bullish | INDIACEM +2.7% (07-17) |
| 37 | Supertrend Bullish | bullish | Supertrend bullish, price above line | AARTIIND +4.8% (07-09); ABB +9.4% (07-14); ABSLAMC +22.7% (04-06); ACMESOLAR +24.2% (05-29) |
| 38 | Price Below All Moving Averages | bearish | Below 20/50/200 MA | ABFRL -3.4% (07-14); AFCONS -7.3% (06-25); ALOKINDS -4.0% (07-14) |
| 39 | Price Above All Moving Averages | bullish | Above 20/50/200 MA | 360ONE +0.3%; ABB +7.0% (07-15); ABCAPITAL +13.3% (06-12); ACMESOLAR +29.4% (05-25) |
| 42 | MACD Bearish Crossover | bearish | MACD just crossed below signal | ABFRL -0.5%; AEGISVOPAK +1.6%; APOLLOHOSP -0.8% (07-16/17) |
| 43 | MACD Bullish Crossover | bullish | MACD just crossed above signal | AIIL +2.0%; ANTHEM +0.8%; BAJFINANCE +0.9%; BPCL +1.3% (07-17) |
| 44 | MACD Bearish | bearish | MACD below signal | 360ONE +0.1% (07-15); AADHARHFC -3.1% (07-14); ABDL -6.4% (07-10) |
| 45 | MACD Bullish | bullish | MACD above signal | 3MINDIA +7.7% (06-17); AARTIDRUGS +11.7% (06-29); AARTIPHARM +10.5% (06-16) |
| 46 | RSI Oversold Bounce | bullish | RSI dipped <30 recently, now back above 30 | AARTIPHARM +1.1% (07-06); ABBOTINDIA +1.4% (07-16); ADVENZYMES +0.6% (07-03) |
| 47 | RSI Overbought Warning | bearish | RSI >70 | AARTIDRUGS -0.5%; ADANIENSOL +0.9%; APTUS +2.3%; ATHERENERG +0.1% (07-17) |
| 63 | Oversold CCI & RSI | (untagged) | Oversold CCI and RSI, potential reversal | ABDL; ABREL; ACE; ADANIENSOL; ADANIGREEN |

## Value & Quality (7)

| # | Screen | Tag | Criteria | Members |
|---|--------|-----|----------|---------|
| 1 | Balanced Trio: QVM Rank | neutral | Rank separately on value/quality/momentum, average into composite, top 10%, D/E ≤1.5, mcap >1000 Cr | BLUEJET -0.2% (07-17); CEMPRO +3.8% (07-10); SHAREINDIA +12.4% (07-07); SHREEJISPG +8.9% (07-13) |
| 3 | Efficient Capital Allocators | bullish | ROIC >12%, ROE >15%, sales/EBITDA growth ≥8% over 3y, capex-to-revenue in healthy 5-25% band | ACUTAAS +6.3%; AEGISLOG +9.2%; ANTHEM +3.2%; BALUFORGE -3.7% (07-10) |
| 4 | High Quality + Low PE | neutral | Cheapest 30% by PE, ROE >15%, ROA >8%, NPM >10%, D/E <1, interest coverage ≥3 | ABBOTINDIA +2.7%; AIIL +8.6%; ALKYLAMINE -6.1%; BLUEJET -6.2% (07-10) |
| 5 | High ROE + Earnings Momentum | bullish | ROE >15%, profit +10% 1y and +8% 3y, sales +20% 3y, quarterly profit +15% YoY preferred | 360ONE -1.7%; ACUTAAS +6.3%; AEGISLOG +9.2% (07-10) |
| 6 | Consistent Free Cashflow Generators | neutral | ≥60% of OCF becomes FCF, positive OCF margin, PAT-to-cashflow 0.8-1.3, ROE ≥12% | AFFLE +13.2% (02-25); AIAENG +21.5% (02-25); ALKYLAMINE +22.8% (02-25); ASHOKA -10.1% (02-25) |
| 61 | Low-PE, High-Quality | neutral | Dup of #4 | — |
| 62 | High ROE with Earnings Momentum | bullish | Dup of #5 | — |

**Duplicate pairs (counted once by their UI):** #4/#61, #5/#62, #10/#50, #11/#51, #12/#52, #41/#54 (golden-cross variants), #23/#24 (text bug).

---

## DELTA vs manas_os presets (~24: 16 registry incl. 2 BUILD + 5 ChartsMaze templates + conditions presets)

### Tradl screens with NO manas_os equivalent (concept gaps)

Grouped — 8 distinct concept gaps covering 35 of their 64 screens:

1. **Bearish/distribution lane — we have ZERO bearish screens** (Top Losers #15, Price Downtrend #21, Below All MAs #38, Death Crossover #40, Volume Spike w/ Price Down #33, Triple Top #11/#51, Head & Shoulders #12/#52, Rising Wedge #49). Gap concept: a short-side / avoid-list / distribution-warning lane. Relevant to us as a *refusal-evidence and exit-pressure* feed even if we never short.
2. **Composite multi-factor ranking screens** (Balanced Trio QVM #1, Quality+Momentum Fusion #7). Gap concept: rank-and-average factor composites vs our single-recipe screens. (Adjacent to our queued edge-stack score, but as a *screen generator*, not a per-symbol badge.)
3. **Risk-adjusted momentum** (Risk-Adjusted Momentum Rank #8: return/volatility rank). Gap concept: volatility-normalized momentum ranking — fits our dynamic ADR-relative-threshold memory note directly.
4. **Cash-flow/capital-discipline fundamental screens** (FCF Generators #6, Efficient Capital Allocators #3, Low-PE Quality #4/#61). Gap concept: fundamentals beyond Shashank's ROE/ROCE/D-E snapshot — FCF conversion, ROIC, capex band, interest coverage, PE-relative cheapness.
5. **Explicit multi-pivot pattern detectors** (Triple Bottom #10/#50, Triple Top #11/#51, H&S #12/#52, W-Neckline #53, Rising Wedge #49, Cup & Handle #13 as a *named detector with measured cup/handle geometry*). We detect bases/coils (VCP, weekly base) but no named multi-peak geometry detectors. (Overlaps our vision-training chart-geometry work — the detection specs there are the stronger version of this.)
6. **ATR-expansion volatility screen** (#17) — volatility regime change as a standalone signal; we use ADR as a filter/sort, never expansion-vs-own-history.
7. **Pivot-point (R1/R2/R3) breakout framing** (#9) — floor-trader pivot levels as breakout reference; we use base pivots/20-week highs instead.
8. **Oscillator/indicator screens** (RSI divergence/OB/OS #18/#19/#46/#47, MACD x4 #42-45, Stochastic x3 #25-27, Bollinger x3 #30/#34/#35, Supertrend x2 #36/#37, EMA20 cross #23/#24, Indicator Confluence #2, CCI #63, above/below-all-MAs #38/#39). No equivalent **by deliberate design** — indicator-soup screens conflict with our practitioner-cited, evidence-only doctrine. Listed for completeness, not as a recommendation. (Bollinger Squeeze #35 is the one respectable cousin — our VCP tightness already covers the concept with better logic.)

### Tradl screens that duplicate manas_os presets

| Tradl screen | Matching manas_os preset |
|---|---|
| Pullback in Uptrend #20, Pullback in Strong Uptrend #56 | Pullback To Rising MA / Pullback To 50MA |
| Tight Range Consolidation #48, Bollinger Squeeze #35 (concept) | VCP / Tightness + Anticipation WATCH |
| Top Gainers #16, Volume Spike #31, Volume Spike w/ Price Up #32 | Today's Movers (+ D2/Episodic day-1 burst) |
| Trend + Volume Breakout #57, Near Breakout #9 (concept) | Weekly Base Breakout / breakout scanner |
| Support Bounce w/ Volume #55, Short-Term Reversal Bounce #58 | Undercut & Recover (+ Long-Tail Candle) |
| Price Uptrend #22, Above All MAs #39 (concept) | Persistent Momentum (stricter: duration-in-trend, ADR-sorted) |
| Macro Momentum #64, Liquidity-Adj Momentum #60 | Arora Baseline (3M>30% + volume floor) / Hiren, Chhirag templates |
| High ROE + Earnings Momentum #5/#62 | Shashank template (EPS/sales/NP YoY, ROE/ROCE, D/E) + EP preset |
| 52-Week High #29 | Covered via ChartsMaze RS/Himanshu high-RS ingest (near-high framing) |
| Bullish Crossover Sustained #14, Golden Cross+Momentum #54 | Nearest: Persistent Momentum — partial only (reclaim-of-200EMA angle is not a preset) |
| Cup & Handle #13, W-Neckline #53 | Partial: VCP/Tightness + winners vision-training detection specs (no named detector preset) |

### Not worth counting as gaps
Top Losers/Gainers, EMA20 crossovers, 52-week high/low, price up/downtrend — trivial one-condition screens; padding in their catalog.
