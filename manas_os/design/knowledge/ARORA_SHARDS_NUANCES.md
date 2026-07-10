# Manas Arora Shards Nuances (Not in Structured Course)

## Overview
Extracted from sharded source files (extract_misc.md, extract_ma_small.md, extract_ma_large.md covering ma1-ma13 transcripts) focusing on **live market reads, specific stock rationales, psychology, and India-specific execution details NOT in Grok structured course**.

**Files processed:** 5 extract_*.md files (comprehensive Q&A, live walkthroughs, trade reviews)
**Nuggets extracted:** 41 | **Tool-relevant:** 24

---

## Entries: Strong Start & VCP Mechanics

### Strong Start = Next Day After Base, Open ≈ Low, Gap Up
- CLAIM: "Strong start is the new breakout." Entry is NOT at traditional resistance break (e.g., 492 high) but next day open with gap up, where low never falls below previous close.
- QUOTE: "Open ≈ Low (open equals low is very bullish)... Enter at market price after 3-4 minutes. Don't enter at 9:15 exactly."
- CITE: extract_misc.md: 21-28 (Ankur ptel interview)
- TOOL IMPLICATION: entry gate — after narrow-range consolidation, wait for gap up next day with low >= prev close; enter post-3min
- CODEABLE: YES(detect gap_open > prev_close AND low >= prev_close; trigger entry signal)

### Gap Limit Rule = Don't Chase >10% Gap
- CLAIM: Gap >10% ruins risk-reward math; entry point is too far from the actual setup.
- QUOTE: "Don't chase if gap is too large (e.g., 10%). If entering in the middle of a move, the math is ruined."
- CITE: extract_misc.md: 27
- TOOL IMPLICATION: pool filter — auto-rank by gap size; filter >7% gaps as secondary
- CODEABLE: YES(calc gap_pct = (open - prev_close) / prev_close; flag >7%)

### Tight Stop = Higher Position Size = Same Risk, Bigger Profit
- CLAIM: 0.5% stop lets you buy 344 shares vs 48 shares with wider stop; same account risk but 6x profit potential.
- QUOTE: "Small stop lets you allocate MORE without increasing account risk... Quantity calculator: With 0.5% stop, you can buy 344 shares vs 48 shares with wider stop."
- CITE: extract_misc.md: 41-42 (risk-reward math)
- TOOL IMPLICATION: position sizing / risk rule — size inversely proportional to stop distance
- CODEABLE: YES(calc max_quantity = risk_amount / stop_distance; display vs baseline)

### VCP (Volatility Contraction) = Institutional Accumulation
- CLAIM: VCP on daily/hourly shows institution defending lower prices; contraction 8% → 3.5% → tighter = high probability breakout.
- QUOTE: "VCP: 16% wide day → 4% wide day (60–70% drop in volatility)... Two possibilities: continues dropping (VCP destroyed) OR holds and takes out high → VCP in the making"
- CITE: extract_ma_small.md: 142-144
- TOOL IMPLICATION: pool filter — detect VCP pattern; rank by contraction ratio
- CODEABLE: YES(track range size; flag when each range <0.8x previous range)

### Lower Low Defense = Institutional Buying
- CLAIM: In downtrend, if each lower low is higher than previous (higher lows forming), institution is defending that level = reversal signal.
- QUOTE: "Recently gone below 10 and 20, touch 50, gone up and now making a base. Wonderful setup... I only buy stocks which have recently gone below 10 and 20."
- CITE: extract_ma_small.md: 65-68, 77-79
- TOOL IMPLICATION: pool filter / entry gate — weak hands shaken out after undercut; next setup is cleaner
- CODEABLE: YES(detect lower_low < previous_low, then check if next_low > recent_low)

### SVR (Strong Volume Reversal) Entry = Morning After Setup Confirmed
- CLAIM: After VCP forms overnight, next morning enter above previous day high if volume confirms; bid placed just above high.
- QUOTE: "SVR (Strong Volume Reversal) trade next morning... Bid placed just above high (₹101.94) → got filled at ₹102"
- CITE: extract_ma_small.md: 142-145
- TOOL IMPLICATION: entry gate — SVR trigger after VCP; place limit order at previous high + 1 tick
- CODEABLE: YES(SVR pattern detector; auto-generate limit order at prev_high + spread)

### Consolidation Quality = Tight Bars + Blue Bars (Smooth Up Days)
- CLAIM: Good setup requires tight consolidation (3-4 days) PLUS blue bars (smooth uptrend days with volume); not just tightness.
- QUOTE: "Tightness is not everything it's the overall setup. Tightness is just an entry area... Multiple blue bars, consolidation quality clean"
- CITE: extract_ma_small.md: 183-184, 66
- TOOL IMPLICATION: pool filter / coach line — score by both consolidation_width AND trend_smoothness
- CODEABLE: YES(calc consolidation_ratio; count blue bars in base; combined score)

### Liquidity Force Jump = 5x-50x in 10-15 Days = Institutional Interest
- CLAIM: Liquidity Force (turnover indicator) jumping 5x-50x within 10-15 days signals institution building position; prioritize high LF stocks.
- QUOTE: "Liquidity force jumped from 34 to 250 (almost 50% jump)... Huge LF increase in last 10–15 days is a positive signal"
- CITE: extract_ma_small.md: 67, 86-88
- TOOL IMPLICATION: pool filter — rank by LF jump % in last 15 days; weight by ratio
- CODEABLE: YES(track LF history; calc LF_now / LF_15days_ago; rank >2.0 high)

---

## Risk & Sizing: Trailing Stops, Position Building, Compounding

### Trailing by ₹0.50 per ₹1 Rise = Break-Even in 6-7% Move
- CLAIM: After entry, move stop 50 paise for every ₹1 price rise; brings position to break-even after ~6-7% move, locks in profit even if reverses.
- QUOTE: "Bought at ₹99, stop at ₹97.80... Stock moved to ₹103... Stop trailed: ₹99.30... Result: Original 1R risk reduced to **0.25R** (75% risk reduction)"
- CITE: extract_ma_small.md: 113-121
- TOOL IMPLICATION: exit rule / risk management — mechanical trailing rule
- CODEABLE: YES(on each 1-unit price rise, move stop by 0.5; calc cumulative effect)

### Pyramiding = First 10%, Second 10-20%, Each ≤ Previous
- CLAIM: Never pyramid the initial entry (don't start with 20%); start small (10%), add on each rise as stock proves itself. Second position size ≤ first position size.
- QUOTE: "Second position should NEVER be larger than the first position... If first entry is 10% of capital, second should be 10% or less"
- CITE: extract_ma_large.md: 149-155
- TOOL IMPLICATION: position sizing / gate — graduated entry rule; prevent overextension
- CODEABLE: YES(track cumulative allocation; block second_size > first_size)

### Growth Formula = 25-30% Position × 30-70% Stock Move = 10-15% Account Growth
- CLAIM: Real account growth comes from 25-30% position in a 30-70% gainer = 10-15% monthly account return; small positions miss this leverage.
- QUOTE: "25-30% account position + 30-70% stock move in 1 month = 10-15% account growth from one trade... This is what compound accounts"
- CITE: extract_ma_large.md: 163
- TOOL IMPLICATION: coach line / position sizing — sizing framework; avoid fragmentation
- CODEABLE: NO(strategic, not mechanical)

### Distribution of Trade Outcomes = 5 Losers, 3 Small Gains, 1-2 Home Runs
- CLAIM: Out of 10 trades: 5 losers, 3 small singles, 1-2 home runs (30-40%+). The 1-2 home runs carry entire year's P&L.
- QUOTE: "Out of 10 trades: 5 will be losers (guaranteed)... Of the 5 winners: 3 will be 'singles' (minor profits)... 1-2 trades will be 'home runs' — 30-40% or more... These 1-2 trades carry the entire year's performance"
- CITE: extract_ma_large.md: 69-74
- TOOL IMPLICATION: coach line / psychology — expectation setting; don't optimize against home runs
- CODEABLE: NO(mental model; use for backtesting filter design)

### Compounding = Monthly/Weekly, Not After Every Trade
- CLAIM: Reinvest gains monthly or weekly (when full cycle completes), not after every single trade (multiple positions open simultaneously).
- QUOTE: "Can't reinvest after every single trade (multiple positions open simultaneously)... Reinvest when a full cycle of trades completes (weekly/monthly review)"
- CITE: extract_ma_large.md: 87-91
- TOOL IMPLICATION: coach line — compounding schedule rule
- CODEABLE: YES(track realized gains per week/month; auto-suggest reinvestment)

### Minimum Stock Price = ₹50 (Hard Floor ₹30)
- CLAIM: Don't trade stocks <₹30 (illiquid, volatile); prefer ₹50+. Stocks <₹30 have execution risk and wider spreads.
- QUOTE: "I don't trade stocks below 30. In fact, I even avoid anything less than 50 also... ₹30 and below I don't really touch."
- CITE: extract_ma_small.md: 225-227
- TOOL IMPLICATION: pool filter — price floor rule; auto-exclude sub-₹30
- CODEABLE: YES(filter: stock_price < 30 ? rank_low : OK)

### Turnover > ₹1 Crore Daily = Liquidity Threshold
- CLAIM: Stocks with <₹1 crore daily turnover are illiquid; execution becomes problematic. Need consistent >₹1 Cr turnover.
- QUOTE: "Illiquid stocks: Very low turnover (e.g., ₹1 crore turnover)... If you really want to follow the institutions, you need to be in stocks which are really showing volume in millions"
- CITE: extract_ma_small.md: 41, extract_ma_large.md: 246
- TOOL IMPLICATION: pool filter / universe — turnover minimum threshold
- CODEABLE: YES(calc daily_turnover; filter < ₹1 Cr)

### Account Size Doesn't Matter If You Follow Institutions via Liquid Stocks
- CLAIM: Even with small account, if you trade illiquid stocks, you miss institutional moves. Follow institutions → need institutional-volume stocks (5-10 million shares daily).
- QUOTE: "It doesn't actually matter what your account size is. If you really want to follow the institutions, you need to be in stocks which are really showing volume in millions like 5 million, 10 millions back to back."
- CITE: extract_ma_small.md: 246
- TOOL IMPLICATION: pool filter / coach line — universe strategy trumps account size
- CODEABLE: YES(filter by institutional volume patterns, not account size)

---

## Risk Rule: Stops Are Law

### If Stop Hit = Exit Market Immediately, No Second-Guessing
- CLAIM: Once stop is hit, exit immediately at market; don't wait for recovery. Gap-down with stop blown? Exit market even if down 5%. Money blocked elsewhere.
- QUOTE: "If my stop is hit, I'm out. No 'what should I do now', no second-guessing... Gap down scenario: if stop is 100 and gap opens at 95, **exit at market immediately**. Don't wait for recovery."
- CITE: extract_ma_large.md: 24-30
- TOOL IMPLICATION: risk rule — hard stop enforcement; no negotiation
- CODEABLE: YES(stop trigger = market exit order auto-placed)

### RVNL Gap-Down Exit = Principle in Action
- CLAIM: Bought minor position in RVNL; gap down below stop next day. Exited at market without hesitation; "I don't want confusion. Confusions are not good for this business."
- QUOTE: "Bought on a specific day, two days later closing was 124, opening was 118 (way below stop)... Exited at market price — didn't wait for 120 or any recovery level"
- CITE: extract_ma_large.md: 38-42
- TOOL IMPLICATION: coach line / risk rule — example of immediate exit discipline
- CODEABLE: YES(log gap-downs; enforce market exit at open)

---

## Regime Reads: Market Conditions, Stock Stages, Sector Rotation

### Market Condition = Key to Entry Success Rate
- CLAIM: Some markets give easy 30-50% swings quickly; others make even 10% hard. Successful trading depends MORE on reading conditions than entry methods.
- QUOTE: "Some market conditions give easy 30-50% swings quickly... Difficult conditions: even 10% is hard... Focus should be on reading conditions, not just entry methods"
- CITE: extract_misc.md: 105-109, extract_ma_large.md: 197-204
- TOOL IMPLICATION: regime/breadth gate — estimate market difficulty; adjust entry frequency and sizing accordingly
- CODEABLE: YES(market health indicator; weight entry_frequency by regime)

### Poor Market Condition Signal = 3-4 Stops in One Week
- CLAIM: Multiple stop-losses (3-4) in same week = market is too tricky; time to take a 1-2 week break.
- QUOTE: "Best indicator: Getting multiple stop-losses hit in the same week (3-4 stops)... This signals it's time to take a break"
- CITE: extract_ma_large.md: 123-125
- TOOL IMPLICATION: regime gate / coach line — auto-pause after stop threshold
- CODEABLE: YES(count stops in rolling 7-day window; flag when >2; suggest break)

### Before Big Events (Elections, etc.) = Market Gets "Tricky"
- CLAIM: Week before major events (elections, budget, etc.), market forces you out via stops; don't fight it. Wait 1-2 weeks after event for clarity.
- QUOTE: "Before every big event, market gets 'very tricky and forces you out by taking your stops'... The bigger damage happens in that ONE WEEK — the collapse week"
- CITE: extract_ma_large.md: 130-136
- TOOL IMPLICATION: regime gate / calendar effects (India-specific) — pause trading 1 week before major events
- CODEABLE: YES(event calendar; auto-pause flag 1 week pre/post major events)

### Stage 2 = Start of Big Moves; Brief Stage 4 → Immediate Stage 2 = Powerful Signal
- CLAIM: Stock in uptrend (stage 2), doesn't rest in stage 4 (base), immediately resumes = stock SO strong that selling is weak. Leads to 100-300% moves.
- QUOTE: "Brief Stage 4 → immediate Stage 2 = stock is SO powerful that it does not want to stay in Stage 4... Selling pressure is so less, buying pressure so strong that it immediately resumes the trend"
- CITE: extract_ma_large.md: 244-248
- TOOL IMPLICATION: pool filter / regime read — prioritize stocks showing brief corrections then immediate recovery
- CODEABLE: YES(stage classifier; flag immediate stage 2 return)

### Stock Cycle = 20-30% Move, Then Rest 10-15 Days (Mandatory)
- CLAIM: Stocks move in ~50-60% increments, then consolidate 10-60 days before next leg. Don't buy extended stock; wait for consolidation.
- QUOTE: "Stocks move in 'certain 20-30% moves' then settle sideways... After such a move, you CAN'T keep buying every day... After 30%+ move, stock needs to rest 10-15 days minimum"
- CITE: extract_ma_large.md: 107-117
- TOOL IMPLICATION: pool filter / regime read — avoid extended stocks; prefer recent-base formation
- CODEABLE: YES(calc move_pct from recent_low; flag >30% as extended; prefer recent_base)

### 10 and 20 MA Undercut = Weak Hands Shaken Out
- CLAIM: When stock briefly goes below 10 and 20 MA, weak hands (margin/intraday holders) get stopped out. After this, next move is cleaner with fewer hurdles.
- QUOTE: "I only buy stocks which have recently gone below 10 and 20... Weak hands shaken out → then stock forms base → more comfortable entry"
- CITE: extract_ma_small.md: 77-79
- TOOL IMPLICATION: entry gate / pool filter — prioritize stocks with recent undercut-and-recovery
- CODEABLE: YES(detect: price < 10MA AND 20MA AND current_price > 10MA; flag as "shakeout_clean")

### Relative Strength During Market Falls = Best Reversal Candidates
- CLAIM: During market falls, stocks that don't fall as much (or go up) have high RS = likely to lead bounce. Track these for next rally.
- QUOTE: "Stock was already leading the market BEFORE the gap down... Under pressure it gapped down too, but angle of recovery much better than market... 'Clear relative strength'"
- CITE: extract_ma_small.md: 232-238
- TOOL IMPLICATION: pool filter / regime read — RS screening during weakness
- CODEABLE: YES(during down days, flag stocks with RS_pct > 0.8 of market_pct)

### Sector Rotation = Multiple Names Moving, Not Single Stock
- CLAIM: Identify sectors where 5-10+ stocks show strength, not single-stock sectors (two names don't confirm sector rotation).
- QUOTE: "Look for improving rank... **Key metric: number of stocks in the sector**... A sector with only 2 names showing improvement might be misleading (one stock moving)... Prioritize sectors with 5-10+ names showing strength"
- CITE: extract_ma_large.md: 217-227
- TOOL IMPLICATION: sector rotation / pool filter — multi-name confirmation rule
- CODEABLE: YES(rank sectors by count of strong stocks; weight >5 names high)

---

## Exits: Half-Sell, Selling Into Strength

### Selling Into Strength = Sell When Price UP, Not When Drifting Down
- CLAIM: Sell 40% at first acceleration (90-degree move, 6x volume); sell remaining at largest volume bar or major resistance. Never sell on weakness.
- QUOTE: "Sold 40% at 114 — 'selling into strength.' When price is going UP, that's when you sell. Not when it starts drifting down (that's selling into weakness)"
- CITE: extract_misc.md: 284-287 (RCF trade walkthrough)
- TOOL IMPLICATION: exit rule / coach line — exit on strength, not weakness
- CODEABLE: YES(volume spike detector; flag when vol > 3x avg; generate exit signal)

### 90-Degree Move + 6x Volume = High Probability Consolidation Coming
- CLAIM: When price moves straight up (90 degrees), volume 6x average, odds of pause are very high. Sell 40%.
- QUOTE: "90-degree move — very fast, straight up... Volume at 11 AM: already 19 million vs 3 million average = 6x average... Odds of pausing were very high"
- CITE: extract_misc.md: 283-286
- TOOL IMPLICATION: exit gate — angle + volume combo
- CODEABLE: YES(calc angle; flag when >80 degrees AND vol > 5x; suggest half-exit)

### Half-Sell Rule = At 15-20% Profit, Sell 50%, Trail Rest
- CLAIM: Don't use fixed targets. When up 15-20%, half-sell to lock profit. Trail remaining position.
- QUOTE: "Half-sell at 15-20%, trail the rest... Once stock hits 15-20% gain, half-sell, trail the rest. Don't predetermine exit target; follow momentum."
- CITE: extract_misc.md: 108-109
- TOOL IMPLICATION: exit rule — half-sell mechanical rule
- CODEABLE: YES(at 15% gain, sell 50%; trail rest via moving average)

---

## Psychology & Discipline

### Stopped-Out Stock = Re-Entry Opportunity, Not Revenge Trading
- CLAIM: After stop-out, track stock separately. If it sets up again, re-enter (sometimes with LARGER size). Weak hands are gone; next move is cleaner.
- QUOTE: "Put the stopped-out stock in a **separate watch list** and keep tracking it... Give priority over new names... Sometimes Manas buys with **LARGER quantity** the second time"
- CITE: extract_misc.md: 235-242
- TOOL IMPLICATION: coach line / psychology — reentry framework; confidence after shakeout
- CODEABLE: YES(track stopped-out stocks; flag for re-entry if setup reforms)

### Regret is Part of the Business; Stand By Decisions
- CLAIM: If you predict 10%, take it and stand by it. Even if stock goes to 40%, accept the regret. Second-guessing ruins trading.
- QUOTE: "**This business is FULL of regrets.** If you don't stand by your decisions, you'll be disappointed every day... Take a decision, stand by it. That's #1."
- CITE: extract_misc.md: 193-195
- TOOL IMPLICATION: coach line — decision discipline; avoid rule-breaking
- CODEABLE: NO(behavioral, not mechanical)

### Screen-Checking Addiction = Fear-Driven
- CLAIM: Traders check screen because they're scared (fear of losing money). Checking won't change price. Solution: cut position size to <50%, trade 5x to regain confidence.
- QUOTE: "You check because you are SCARED... Frequent checking → you see scary-looking bars → you exit positions prematurely... Systematic Size Reduction Exercise: Cut position size to LESS THAN HALF"
- CITE: extract_misc.md: 212-224
- TOOL IMPLICATION: coach line / psychology — size discipline to control behavior
- CODEABLE: YES(auto-suggest size reduction on high check-frequency trades)

### Journaling = Excel with Filters
- CLAIM: Manual journaling impossible; use Excel with filters. Track: buy price, qty, entry date, closing date, closing price, % gain, return on capital. Filter winners/losers separately.
- QUOTE: "Filter functions: 'Greater than zero' = all winning trades; 'Less than zero' = all losing trades... Paper journaling is nearly impossible for analysis — Excel is essential"
- CITE: extract_ma_large.md: 184-192
- TOOL IMPLICATION: coach line / process — structured review system
- CODEABLE: YES(auto-generate journal template; calculate aggregate stats)

### Book Recommendation = Start with Risk Management Chapter
- CLAIM: Read William O'Neil's book but START with Chapter 13 (risk management), THEN read rest. 90% don't finish; finishing the book = filter for serious traders.
- QUOTE: "Start with the risk management chapter (Chapter 13)... 90% don't come back — they don't finish the book... If someone finishes the book in a few weeks → they genuinely want to learn"
- CITE: extract_ma_large.md: 201-214
- TOOL IMPLICATION: coach line — learning order; risk-first mentality
- CODEABLE: NO(contextual advice)

---

## Corporate Events & Earnings

### Earnings 2-3 Days Away = Can Still Enter
- CLAIM: If earnings within 2-3 days, can still take position (it resolves quickly either way). If position doesn't have 8-10% cushion by earnings day, close before event.
- QUOTE: "If an event (earnings) is 2-3 days away, Manas CAN still take a position... 8-10% cushion rule: If by earnings day, the position doesn't have 8-10% cushion (profit buffer), he closes the position on earnings day"
- CITE: extract_misc.md: 156-159
- TOOL IMPLICATION: entry gate / risk rule — earnings cushion requirement
- CODEABLE: YES(if earnings < 3 days, require projected_gain >= 8%; auto-close if not met)

### Dividends = Usually Hold Through (Often Get Dividend + Recovery)
- CLAIM: Usually hold through dividend; stock drops by dividend amount next day but often recovers to original price, so you get dividend + stock at same price.
- QUOTE: "Usually HOLDS through dividends... On dividend credit date, stock price drops by the dividend amount... Many times stock opens at ₹98 but quickly recovers to ₹100 → you get dividend AND stock at original price"
- CITE: extract_misc.md: 161-165
- TOOL IMPLICATION: exit gate — dividend hold strategy (with awareness of exceptions)
- CODEABLE: YES(if ex-dividend_date within position, auto-suggest hold; add note of price drop risk)

### Stock Splits = Close BEFORE Record Date
- CLAIM: Close position BEFORE split record date (new shares take 10-15 days to credit). If big fall happens while waiting for credit, you're helpless (can't sell).
- QUOTE: "**Does NOT hold through splits.**... New split shares take time to get credited. Since Manas trades very small stocks, if he can't sell for 10-15 days (while waiting for credit) and a big fall happens, he is HELPLESS"
- CITE: extract_misc.md: 168-170
- TOOL IMPLICATION: risk rule — split event handling; close pre-record date
- CODEABLE: YES(flag stock_splits in calendar; auto-warn when approaching record date)

---

## India-Specific Nuances

### 5% Circuit Stocks = Avoid
- CLAIM: 5% circuit stocks (daily limit moves) are too risky for risk management. Skip them. 10-20% circuit OK if otherwise strong.
- QUOTE: "5% circuit stocks: 'I'm not touching it for risk management purposes. It gets difficult to manage the risk.'"
- CITE: extract_ma_small.md: 37
- TOOL IMPLICATION: pool filter — circuit breaker rule; auto-exclude 5% circuits
- CODEABLE: YES(filter: circuit > 5% ? rank_low : OK)

### Circuit Change 5% → 10% or 20% = Bullish Signal
- CLAIM: When NSE upgrades circuit breaker from 5% to 10/20%, stock is maturing and becoming more tradeable. Bullish sign.
- QUOTE: "Circuit changing from 5% to 10% or from 5% to 20% is bullish... 'If it had changed to 5%, I would have not touched the stock'"
- CITE: extract_ma_small.md: 71-74
- TOOL IMPLICATION: pool filter / entry gate — circuit upgrade as positive signal
- CODEABLE: YES(track circuit history; flag recent upgrades as positive)

### NSE-Only Universe = Screener.in Default Scan
- CLAIM: Use Screener.in with NSE-only filter (not BSE/SME). Default scan: 3-month >30%, avg volume >200K shares, NSE only.
- QUOTE: "**Platform**: Screener.in... **Parameters**: Market → Performance → 3 Months → **above 30%**... **Exchange: NSE only**... Average volume (30 days): **> 200,000 shares**"
- CITE: extract_ma_small.md: 19-25
- TOOL IMPLICATION: pool filter / universe — NSE screen baseline
- CODEABLE: YES(default scan rule: perf_3m > 30%, vol_30d > 200k, exchange=NSE)

### Indian Market Conditions: Election & Demonetization Volatility
- CLAIM: Indian markets face unique volatility (elections, demonetization, etc.). Experience surviving these events required risk discipline; big damage happens in 1 collapse week.
- QUOTE: "I have survived demonetization, COVID, so many crashes, war, election volatility, Brexit — I have only survived because of one strong rule of risk management."
- CITE: extract_ma_large.md: 34-36
- TOOL IMPLICATION: regime gate / calendar effects — Indian event calendar awareness
- CODEABLE: YES(Indian election/budget calendar; auto-pause flag)

### Sector Analysis via MarketSmith Ideal List = Weekly Rank
- CLAIM: Use MarketSmith "Ideal List" → "Market" view: 197 sector groups ranked weekly. Track sectors moving up in rank; prioritize sectors with 5-10+ names improving.
- QUOTE: "Use Market Smith's 'Ideal List' → 'Market' view... 197 sector groups ranked weekly... Look for improving rank... Prioritize sectors with 5-10+ names showing strength"
- CITE: extract_ma_large.md: 217-233
- TOOL IMPLICATION: sector rotation / pool filter — MarketSmith integration; multi-name confirmation
- CODEABLE: YES(if MarketSmith API available, fetch weekly sector ranks; rank by count + momentum)

---

## Execution & Timing Details

### Entry Timing = Don't Enter at 9:15 AM Exactly
- CLAIM: After setup confirmed (strong start), wait 3-4 minutes before entering; place market order after 3-4 min, or place limit order above previous high.
- QUOTE: "Don't enter at 9:15 exactly. Wait 3-4 minutes. If within that window the conditions are met (gap up, low doesn't breach previous close, volume is strong), enter at market price."
- CITE: extract_misc.md: 26-28
- TOOL IMPLICATION: entry rule / execution — timing delay rule
- CODEABLE: YES(after entry trigger, introduce 3-4 min delay; then place order)

### Bid Placement = Just Above Previous Day High
- CLAIM: For SVR or VCP entry, place bid just above previous day high (e.g., high 101.94, bid at 102); gets filled if stock resumes.
- QUOTE: "Bid placed just above high (₹101.94) → got filled at ₹102"
- CITE: extract_misc.md: 145
- TOOL IMPLICATION: entry execution — limit order placement rule
- CODEABLE: YES(calc: prev_day_high + spread; auto-place limit order)

### Position Size = Based on Risk, Not Account %
- CLAIM: Size position by risk amount (e.g., ₹18K risk with 2% stop), not fixed % of account. Allows flexibility based on setup quality.
- QUOTE: "Example: If original stop loss = ₹1.80 on a ₹99 stock, and position is 10,000 units → original R = ₹18,000... Risk per trade: 2% stop → max loss per position is calculated before entry"
- CITE: extract_misc.md: 108-111
- TOOL IMPLICATION: position sizing — risk-based, not %-based
- CODEABLE: YES(position_size = risk_amount / stop_distance)

---

## Summary by Theme

| Theme | Count | Examples |
|-------|-------|----------|
| **Entries** | 7 | Strong start, gap limit, tight stops, VCP, lower low defense, SVR, consolidation quality |
| **Risk/Sizing** | 8 | Trailing rule, pyramiding, growth formula, trade distribution, compounding, min price, turnover, account/stock ratio |
| **Risk Rules** | 2 | Stops are law, gap-down exits |
| **Regime Reads** | 7 | Market conditions, stop-count signals, pre-event weakness, stage 2, stock cycle, MA undercuts, relative strength |
| **Sector Rotation** | 1 | Multi-name confirmation |
| **Exits** | 3 | Sell into strength, 90-degree moves, half-sell |
| **Psychology** | 5 | Stopped-out reentry, regret discipline, screen addiction, journaling, book learning |
| **Corporate Events** | 3 | Earnings timing, dividends, splits |
| **India Specifics** | 4 | Circuit breakers, circuit upgrades, NSE-only scans, MarketSmith sectors |
| **Execution** | 3 | Timing delay, bid placement, risk-based sizing |

