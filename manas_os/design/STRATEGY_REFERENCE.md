# Strategy Reference — source-faithful rules for detectors & features

This is the single durable reference for the trading-strategy logic behind the
detectors/tabs. Task descriptions in TASKS.md are the *distilled* version; when
building EP/IPO detectors, an agent MUST also read the SOURCE FILES below — the
courses carry nuance the distillation can lose (bar-by-bar reading, execution art).

## Source files (read these directly for #26 EP, #27 IPO)
- EP playbook: `C:\Users\satta\Downloads\book\momentum-project\book\Tradetm\Episodic Pivots_ A Complete Guide for Indian Traders_custom_rip.txt`
- IPO bases (bar-by-bar, Hindi): `C:\Users\satta\Downloads\book\momentum-project\book\Tradetm\ipo bases.txt`
- IPO trading transcript: `C:\Users\satta\Downloads\book\stocksgeeks\IPO_trading_transcript.md`
- Overnight-edge study (fwd-return + gap-acceptance defs for #18): `C:\Users\satta\Downloads\india_overnight_edge_study_technical_spec.md`
- Deepvue features (round 1): dashboard, RS, TTM-squeeze, launch-pad, market-navigator, AVWAP, stocks-from-open, bubble-charts — deepvue.com/indicators & /dashboard
- Deepvue features (round 2): post-market-movers, pre-market, theme-tracker, fundamental/composite/absolute-strength/EPS ratings, David-Ryan-ANTS, RMV — deepvue.com/ratings & /indicators

---
## EPISODIC PIVOT (EP) — #26
**Earnings EP (primary):** QoQ AND YoY growth >=30% in BOTH EPS and sales (StockBee rule; not strict — want unexpected positive growth). Results released AFTER market close. Stock MUST gap-up or open strongly next day (else market wasn't surprised → not an EP). Stock must be NEGLECTED — in a big base/consolidation (better) or downtrend. Market cap filter >300cr. Context (narrative shift) matters more than the gap size itself — "a new episode in the life of the company."
**Non-earnings EP:** order wins, govt policy (sugar/fertiliser), approvals. DEFER (NLP classification).
**Entry:** 5-min opening-range high, stop = day low (often breakout-bar low). SKIP if gap+ORH >12% (circuit caps upside, trade not risk-free same day). <45% of EPs trigger on gap day; those that do give risk-free entries. Win rate 40-60%, stop 2-4%.
**EP pullback:** most EPs offer a pullback to 10/21 EMA — high R:R entry + pyramiding, esp. when earnings mediocre but market reaction strong. Commonality: tight/negative bar near MAs, entry near prev-day high on strong start, stop near day low.
**Exit:** sell into weakness (trend new, urgency just begun); ~10-20 strong EPs/year; 'all or nothing' hold worked best. Pyramid every 10/21 EMA pullback. EXIT if 21 EMA breached (low of the bar that closed below the MA is broken); or use 50DMA if 21-50 gap small. Sell into strength only on temporary extension (15% from 10EMA).
**Our data:** EPS/sales growth = symbol_quality/results-calendar (have). Gap = bhavcopy. Neglected-base = RS+trend. 5-min ORH = needs #21 intraday (EOD version arms at night, entry refinement later).

## IPO BASES — #27
**Philosophy:** IPO bases are small (2 days–2 months) → PATTERN + candle reading dominates. Volume NOT important on first breakout of short bases (matters only as base grows >2 weeks). First breakout only; ref = listing-day candle. Trade the pattern as soon as it appears.
**Base-age buckets:** 0-2wk (candle-driven) / 2wk-2mo (pattern+volume) / >2mo (full big-base rules, out of scope). BSE→NSE migrations behave like IPOs.
**Six patterns (BUILD 2 first: mini-coil/inside-bar + TVCP; defer Hook/Fast-Flag; drop Cro-bar/inv-H&S):**
1. TVCP — tight range contraction (8%→5%→2% squeeze).
2. Inverted H&S (plain / on trendline).
3. Cro-bar — 1 big candle + 2-3 small sideways, price can't catch EMA.
4. Hook — pullback returns to 10/21 EMA and retests.
5. Fast-Flag — post-breakout sideways >5d, EMA catches up.
6. Mini-coil / inside-bar — candle-inside-candle; FIRST inside bar after listing = key trigger.
**Demand/strength confirmations:** long lower wicks = demand (shakeout); bottom-spring = down-day then engulfing outside-up at swing low; higher-low = strength / lower-low = weak (institution defending low); overlapping bars (up-small-sell, down-big-buy) = accumulation; <=50% retracement rule — a strong up/down candle must NOT retrace >50% (IPO-day candle 50% level = key support). Multi-TF daily+75m+15m — CUT per Fable (daily-only detection; intraday only at #21 entry).
**Stop/size/exit:** stop = day-low / prior-candle-low; HARD <=4% cap (skip if wider — "mathematically not good"); tighter stop → bigger size. Exit: hold min ~20%, sell half 15-20%, trail rest via 10/21. 20% upper-circuit WELCOMED (unlike EP's skip).
**Avoid:** breaks IPO-day low + closes below with follow-through (the true failure); overhead-supply/multi-hit resistance. A single dirty shakeout candle with NO downside follow-through = buy, not avoid.
**Entry is bar-by-bar VISUALIZATION** (see ipo bases.txt): anticipate the reversal — volatility contracting, ground not lost below, supply drying (overlapping bars), then a small expansion down that reverses = trigger. "Bar-by-bar is microscopic analysis," used at IPO start.
**Listing-date builder:** listing_date = first bhavcopy appearance; is_ipo = age<12mo. GUARDS: if first-row == archive-start-date → mark 'unknown' NOT ipo (survivorship); renames look like new listings (cross-check announcements); BSE→NSE = accept minor false-positive. IPO issue price unavailable → listing-day open proxy.

## DEEPVUE — adopted/dropped (Fable-ruled)
**Adopt:** Market Navigator → EXIT engine (#22, fired-rules not count, Intact/Weakening/Broken). Launch Pad → early-entry setup (#23). ANTS → accumulation confluence input (#25). Absolute Strength + realized-EPS-growth → readiness CHIPS not ranks (#24). AVWAP + RS Line/Phase + TTM histogram → chart overlays (#19, display-only). Pre-market gap-scan → into #21.
**Drop:** Fundamental/Composite/EPS *ratings* (competing rank + degraded black-box, need surprise/forward legs we lack). TTM Squeeze as a signal (redundant w/ RMV — keep only histogram pane). Post-Market Movers (no NSE post-market session). 4D bubble chart (sortable color-banded table faster). Theme Tracker (have RRG). Multi-TF 75m/15m for IPO.
**Merge:** ChartsMaze 'tight-setup' → VCP looser tier.
**Compression cluster roles (one each):** RMV = the metric; VCP = the pattern (absorbs tight-setup); Launch Pad = MA-convergence early-entry; TTM histogram = optional directional pane only.
