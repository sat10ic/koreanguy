# TradeTM Nuances — Extraction Layer

Extraction pass over the TradeTM corpus (Anuragg Venkatakrishnan / Chirag Kedia, TradeTM blog +
video transcripts). Read in full: all 24 published TradeTM blog articles (`*_text.txt` PDF
extracts). Sampled in depth: 5 Hindi-language video transcripts from `New/` covering entry
framework, structure-break/exit reading, gap-down execution, price-action psychology, and
letting-go/R-multiple discipline. Raw long-form video transcripts (D2 Setup.txt, EP
Masterclass.txt, trading system.txt, choppy.txt, avg stocks.txt, ipo bases.txt, etc. — 23 files,
~2MB) were not fully read in this pass; they are largely earlier/rawer versions of material now
covered by the polished blog articles and the sampled videos (same author, overlapping topics:
D2 entry, EP, situational awareness, position sizing). Flagged as a residual gap below.

Format per entry: CLAIM / QUOTE (exact) / CITE / TOOL IMPLICATION / CODEABLE.

---

## A. Universe & Liquidity (India-specific market structure)

### A1. Circuit limits cap risk-free entry on EP gap days
- CLAIM: In Indian EP trading, gap-up + opening-range-high moves over 12% are skipped because the 5% circuit mechanism prevents the trade from becoming risk-free same-day.
- QUOTE: "I skip entries where the gap up plus opening range highs are more than 12%. This is because the circuit limit restrains the upmove and does not make my trade risk-free on the same day."
- CITE: Episodic Pivots: A Complete Guide for Indian Traders_text.txt, "On the day of EP"
- TOOL IMPLICATION: gate (EP setup filter should exclude >12% gap+ORB stocks); regime read
- CODEABLE: YES (compute gap% + first-5min-ORB% vs prior close; hard-skip >12%)

### A2. Stocks in the 5% circuit are avoided pre-trade
- CLAIM: Stocks sitting in the 5% circuit band fail the liquidity pre-trade filter entirely.
- QUOTE: "All stocks in the 5% circuit are avoided."
- CITE: The Cost of Illiquidity and Its Impact on Traders_text.txt, "Pre Trade"
- TOOL IMPLICATION: pool filter
- CODEABLE: YES (flag/exclude stocks whose daily band is 5% circuit type and price is pinned)

### A3. ~500 stocks is the realistic liquidity-filtered Indian universe at scale, vs ~2000 in the US
- CLAIM: At meaningful portfolio size, the tradeable Indian universe under a liquidity filter shrinks to roughly 500 names, a quarter of the ~2000 available to comparable US traders.
- QUOTE: "On my portfolio size, I rarely get more than 500 stocks in my liquidity filter (compared to ~2000 in the US)."
- CITE: Blend Fundamentals & Technicals for Better Trades ("Fundamentals and Themes...") _text.txt, "In scaling up portfolio"
- TOOL IMPLICATION: pool filter; regime read (India's universe is structurally smaller — don't import US backtests/frequency assumptions)
- CODEABLE: YES (surface a "current universe size after liquidity filter" stat)

### A4. ~70% of NSE free-float market cap sits in the top 100 stocks — the rest has poor spreads
- CLAIM: India's market cap is heavily concentrated in the top 100 names, so the remaining 2000+ listed companies carry structurally worse bid-ask spreads.
- QUOTE: "in the Indian context, where ~70% of the free-float market cap of NSE stocks is concentrated in the top 100 stocks, the spreads in the remaining 2000+ companies are noticeably poor."
- CITE: The Cost of Illiquidity and Its Impact on Traders_text.txt, part (a) Bid-ask spread
- TOOL IMPLICATION: pool filter / risk rule (spread-cost buffer scales with market-cap tier)
- CODEABLE: YES (tier stocks by market cap; apply wider slippage buffer outside top ~100-200)

### A5. Illiquid large holdings get liquidated via block deals, not the open market — even for a 200%+ winner
- CLAIM: A stock can be fundamentally strong and up 200%+ yet remain untradeable on-screen because large holders (e.g. mutual funds) exit via private/off-market block deals rather than through visible order flow.
- QUOTE: "the stock is absolutely illiquid and untradeable... the liquidation of a 700 crore holding, when the average turnover on BSE is less than 2 crore, would likely occur through private placements and off-market block deals."
- CITE: The Cost of Illiquidity and Its Impact on Traders_text.txt, "Price Impact" (Elantas Beck India example)
- TOOL IMPLICATION: pool filter (turnover floor, not just price return, must gate candidate inclusion)
- CODEABLE: YES (require min. 30-day avg turnover in ₹ regardless of price momentum)
- ⚠️ Note: specific company figures (Elantas Beck market cap ~₹9,400cr, Nippon stake ~₹700cr) are illustrative/dated; treat as example not live data.

### A6. Regulatory tightening (ASM/GSM-style measures, F&O margin cuts, expiry proliferation) concentrates liquidity into fewer stocks and index options
- CLAIM: SEBI measures meant to protect retail (curtailing MF inflows, "suffocating ASM/GSM measures," reduced F&O margins, near-daily option expiries) have the side effect of concentrating tradable liquidity into a narrower set of instruments, which structurally harms broad-based retail participation.
- QUOTE: "exchanges now offer option expiries almost every trading day, causing retail derivative volumes to skyrocket. Combine this with attempts to curtail mutual fund inflows, suffocating ASM/GSM measures, reduced F&O margins, and a plethora of taxes. This concentrates liquidity in fewer stocks, depleting the broad-based, stable liquidity that is crucial for a growing economy's capital market."
- CITE: The Cost of Illiquidity and Its Impact on Traders_text.txt, opening section
- TOOL IMPLICATION: regime read (structural liquidity backdrop); pool filter
- CODEABLE: NO (macro/regulatory read — judgment call, not backtestable rule) — but the *effect* (fewer liquid names) is CODEABLE as a periodic universe-size check.

### A7. SEBI's own risk-disclosure stats are structurally biased — "active trader" threshold is too low, sample is 98% options, and outlier-trimming erased half the winners
- CLAIM: The SEBI Jan-2023 study showing ~90% of F&O traders lose money undercounts genuine skill because it defines "active" as just 5+ trades/year, is 98% options-dominated, and its outlier-trimming methodology removed ~50% of profitable traders while adjusting only 6% of loss-makers.
- QUOTE: "the analysts trimmed the distribution by excluding the top and bottom 5 percentiles... As a result, nearly half of the profitable traders were excluded, while only 6% of the loss-making traders were adjusted for."
- CITE: How Probabilities Can Be Misleading in Trading_text.txt, Observations (a)-(e)
- TOOL IMPLICATION: coach line (contextualize survivorship stats for the user; don't treat "90% lose" as gospel) / regime read
- CODEABLE: NO (data-interpretation judgment, not a rule)

### A8. IPOs, EPs and reversal setups retain liquidity/scalability even in illiquid/choppy tape; reversal setups are rare and low-RR so seldom traded
- CLAIM: Among setup types, EPs and IPOs "naturally attract liquidity" and scale well; reversal setups also have good liquidity but poor risk-reward and low frequency, so the author rarely trades them.
- QUOTE: "Priority is given to setups like IPOs or Episodic Pivots... These setups naturally attract liquidity, are more scalable, and offer multiple entry points... Even reversal setups provide good liquidity, but they offer limited risk-reward opportunities and occur infrequently, so I seldom trade them."
- CITE: The Cost of Illiquidity and Its Impact on Traders_text.txt, "Pre Trade"
- TOOL IMPLICATION: gate / pool filter (setup-type prioritization by scalability)
- CODEABLE: YES (rank setup candidates by liquidity-scalability tier: EP/IPO > breakout > reversal)

### A9. EP volumes act as a "reverse network effect" — they bring liquidity to previously illiquid stocks
- CLAIM: When a stock has an Episodic Pivot, trading volume surges enough that previously untradeable/illiquid names become tradeable, expanding the effective universe.
- QUOTE: "Scalability - EP volumes create liquidity like a reverse network effect, bringing life to previously illiquid stocks. The tradeable universe expands as stocks that were once off-limits now offer easier fills."
- CITE: On Bear Markets and Episodic Pivots Explained_text.txt, "Should we prioritise EPs over other setups?"
- TOOL IMPLICATION: pool filter (dynamic liquidity re-scan after EP trigger, not just static filter)
- CODEABLE: YES (re-check liquidity filter post-EP-trigger rather than pre-trigger only)

---

## B. Entry Frameworks

### B1. EP core criteria: 30%+ YoY/QoQ EPS+sales growth, post-market results only, must gap up, stock must be neglected
- CLAIM: A valid Earnings EP requires (a) ~30%+ growth in both EPS and sales QoQ and YoY (soft rule), (b) results released after market close, (c) a gap-up/strong open the next day, and (d) the stock being neglected (in a base or downtrend) beforehand.
- QUOTE: "my primary focus is on a qoq and yoy growth of at least 30% in both EPS and sales... For a stock to be considered an EP, it must either gap up or open strongly the next day. If it fails to do so, then it cannot be considered as an EP... The stock must be neglected, meaning it is either in a big base consolidation or down trending."
- CITE: Episodic Pivots: A Complete Guide for Indian Traders_text.txt, "How to identify EP"
- TOOL IMPLICATION: gate (EP setup rule)
- CODEABLE: YES (screen: post-close results + next-day gap-up + prior-trend neglect + EPS/sales growth threshold; market cap floor >₹300cr)

### B2. EP entry mechanics: 5-min opening-range-high entry, day-low stop, <45% trigger same day but high quality when they do
- CLAIM: The empirically best EP entry (from the 1,688-gapup 2017-2022 deep dive) is on the 5-minute ORB high with the day-low as stop; fewer than 45% of EPs trigger on the gap day itself, but those that do give immediate risk-free entries.
- QUOTE: "we observed getting in on the 5 minute opening range highs with the day low stop loss (often the breakout bar low too) worked well... less than 45% of the EPs were triggered on the gap day. However, most of those that did trigger provided immediate risk-free, low-cost entries."
- CITE: Episodic Pivots: A Complete Guide for Indian Traders_text.txt, "On the day of EP"
- TOOL IMPLICATION: entry logic / debate prompt (EP execution rule)
- CODEABLE: YES (ORB-high trigger, day-low SL, 40-60% win-rate expectation band)

### B3. EP pullback entries cluster around the 10/21 EMA; exit on 21 EMA breach (or 50 DMA if close)
- CLAIM: When EPs don't trigger on gap day, the pullback entry zone is the 10/21 EMA; the exit rule is a breach of the bar-low that closes below the 21 EMA, or the 50 DMA if it's tracking close to the 21 EMA.
- QUOTE: "Most EPs will offer a pullback entry around the 10/21 EMA... I will exit the position if the 21 EMA is breached (i.e. if the low of the bar closing below the moving average is broken). Alternatively, if the distance between the 21 EMA and 50 DMA is not too large, I may use the latter to exit the position."
- CITE: Episodic Pivots: A Complete Guide for Indian Traders_text.txt, "EP Pullback" / "How to Sell EP"
- TOOL IMPLICATION: entry logic + exit rule
- CODEABLE: YES

### B4. EPs are <10% of trade count but >35% of 2-year returns — "all or nothing" holding beats frequency-style management
- CLAIM: Because only 10-20 strong EPs occur per year, treating them with an all-or-nothing (hold big) approach rather than frequency-trade management produced outsized portfolio contribution.
- QUOTE: "Even though EPs account for less than 10% of my total trades, they have contributed to more than 35% of my returns in the last 2 years."
- CITE: Episodic Pivots: A Complete Guide for Indian Traders_text.txt, "How to Sell EP"
- TOOL IMPLICATION: risk rule / trade-management-template selection (magnitude vs velocity)
- CODEABLE: NO (statistical outcome to track in journal, not a forward rule) — but the classification (EP = magnitude template) is CODEABLE.

### B5. D2 Entry: catch momentum on Day 2 of a fresh burst rather than waiting for a mature setup (flag/base) to form
- CLAIM: By the time a traditional flag/base has formed (3-4 weeks pole + 3-4 weeks consolidation), the most explosive part of the move is over; D2 entry captures momentum at the point of eruption.
- QUOTE: "when momentum is high, don't waste it waiting for a traditional setup to form... Consider what happened during the Covid rally: by the time conventional setups like flags formed... the easiest and most explosive part of the move was already over."
- CITE: D2 Entry: Every Question You Had, Answered_text.txt, Q1
- TOOL IMPLICATION: entry logic / gate (secondary momentum-chase gate distinct from base-breakout gate)
- CODEABLE: YES (screen: prior-day top gainers list, %move threshold)

### B5b. D2 scan criteria: 10%+ Day-1 move preferred, 20% circuit stocks from consolidation ideal, 4-6% Day-1 is weak, first-day-of-expansion preferred over Day 2/3
- QUOTE: "Moves of 10%+ are generally preferred. Ideally, look for 20% circuit stocks emerging from consolidations or pullbacks. A 4%-6% Day 1 move is usually weak... Preference is always for the first day of expansion, not the second or third day of a move that is already underway."
- CITE: D2 Entry: Every Question You Had, Answered_text.txt, Q2
- TOOL IMPLICATION: gate / entry logic
- CODEABLE: YES (Day-1 %-move screen with tiered thresholds; India-specific: reference to the 20% circuit band)

### B5c. D2 three Day-2 sub-setups depending on Day-1 close/Day-2 open: strong-close gap-up, "Wick Play" (weak close, gap-up open), gap-down reversal (bad news + prior Day-1 strength)
- QUOTE: "Weak close with a wick due to market pressure: Look for a strong open with a slight gap-up on Day 2. This is the Wick Play setup. Negative overnight news: Focus on stocks that showed exceptional Day 1 strength (circuit stocks, 10%+ movers) and look for a gap-down reversal setup on Day 2."
- CITE: D2 Entry: Every Question You Had, Answered_text.txt, Q4
- TOOL IMPLICATION: entry logic (branch by Day-1 close type)
- CODEABLE: YES (classify candidate into 3 sub-setup buckets by Day-1 close position + Day-2 open gap)

### B5d. D2 trail: 21/50 DEMA on 1-min intraday → shift to 21 DEMA on 5-min → shift to higher timeframe once initial burst plays out
- QUOTE: "Start with an intraday mindset, trailing the 21 or 50 DEMA on the 1-minute chart... shift to the 21 DEMA on the 5-minute chart... Once the initial burst plays out, we shift our bias from intraday to swing and move the trailing stop... to a higher timeframe chart."
- CITE: D2 Entry: Every Question You Had, Answered_text.txt, Q5
- TOOL IMPLICATION: exit rule (trail logic, timeframe-adaptive)
- CODEABLE: YES

### B6. Right Entry framework = Right Stock (value-driven) + Right Setup (built-up vs overhead supply distinction) + Right Entry (tactical) — range-bound stocks have no valid "structure"
- CLAIM: No chart pattern/structure concept (head-and-shoulders, etc.) is valid inside a range; patterns only have meaning in a trending stock because "built-up supply" (recent buyers taking profit on the way up) and "overhead supply" (trapped buyers from a prior top) only form once a trend exists.
- QUOTE: "जब तक स्टॉक ट्रेंड में नहीं होगा तब तक आपकी बिल्ड अप सप्लाई नहीं बनेगी। तब तक आपकी ओवरहेड सप्लाई नहीं बनेगी... कोई पैटर्न वहां पे बन नहीं सकता आपका।" [Until the stock is trending, built-up supply won't form. Overhead supply won't form. No pattern can form there (in a range).]
- CITE: New/How to Enter a Trade Like a Pro (A Complete Entry Framework) TradeTM.txt (~line 1560-1600)
- TOOL IMPLICATION: gate / debate prompt (reject pattern-recognition claims — H&S, double-top etc. — on range-bound/non-trending charts)
- CODEABLE: YES (require prior established trend direction before evaluating any reversal/continuation pattern)

### B7. "Trade your P&L, not the chart" — the strategic layer beats the tactical layer
- CLAIM: Learning has three layers — beginner theory, tactics (how-to), and strategic thinking (positioning so every move compounds into life-changing impact); most traders over-index on tactics (e.g. "tight stop loss") and never build the strategic layer, which is why chart-trading alone doesn't scale a portfolio.
- QUOTE: "आपको अपने पीएनएल को ट्रेड करना है... हम लोग सिर्फ चार्ट ट्रेड नहीं कर रहे। हम लोग अपने पीएनएल को बेसिकली ट्रेड कर रहे हैं।" [You have to trade your P&L. We're not just trading the chart — we're basically trading our P&L.]
- CITE: New/How to Enter a Trade Like a Pro (A Complete Entry Framework) TradeTM.txt (~line 760-800)
- TOOL IMPLICATION: coach line / debate prompt
- CODEABLE: NO (mindset framing, not a rule)

### B8. Structure-break exit reading: "eating your own bottom" — repeated small, non-decisive breaks below prior lows signal character change even without a sharp collapse
- CLAIM: A stock exiting a healthy trend often doesn't collapse violently; it "eats its own bottom" — each pullback quietly breaks slightly below the prior low instead of holding/pushing up — and this gradual erosion is itself the structure-break signal, distinct from a sharp shakeout-and-recover.
- QUOTE: "ये हर बार जो अपना बॉटम बना रहा है इसको ऐसा नहीं कि ये कोई डिसाइसिव तोड़ के ब्रेक दे रहा है... ये धीरे-धीरे नीचे की तरफ स्पिल ओवर हो रहा है। अपने बॉटम को खा रहा है।" [Every time it makes a bottom, it's not a decisive break — it's slowly spilling over downward, eating its own bottom.]
- CITE: New/Hold or exit How to spot a structural breakdown on charts (CG Power, Tejas, and more) TradeTM.txt (~line 505-525)
- TOOL IMPLICATION: exit rule / regime read for individual positions
- CODEABLE: YES (partial: flag "sequence of lower closing-lows without a sharp reversal bar" as a structure-decay signal, distinct from single-bar shakeout)

### B9. Distinguish real weakness from a sharp collapse-then-recover ("shakeout") — momentum stocks shake out because fear is "gunpowder"; a light pressure causes a big reaction, then they recover fast if buyers remain willing
- CLAIM: Momentum stocks are prone to sharp, scary one-day collapses that fully recover the next day because underlying fear is primed like gunpowder — light selling pressure triggers an outsized drop, but genuine demand steps back in fast. This is different from — and should not be confused with — genuine structural breakdown.
- QUOTE: "जो मोमेंटम के स्टक्स होते हैं उसमें शेक आउट इसलिए आता है क्योंकि उसमें फियर बहुत ज्यादा है... डर बारूद की तरह होता है। यदि डर बहुत ज्यादा है, हल्की सी तीले लगाएंगे तो बड़ा सा धमाका भी होगा।" [In momentum stocks, shakeouts happen because fear is very high — fear is like gunpowder; a small spark causes a big blast.]
- CITE: New/Hold or exit How to spot a structural breakdown on charts (CG Power, Tejas, and more) TradeTM.txt (~line 137-150)
- TOOL IMPLICATION: coach line / exit rule (don't panic-exit on single sharp-decline-then-recover bars if trend context intact)
- CODEABLE: NO (requires judgment on "recovers fast" vs "keeps sliding" — partially codeable as: don't exit solely on largest-single-day-decline if next-day reclaims >50% of the range)

### B10. "Tennis ball action" breaking down = structure break; the stock stops bouncing off short pullbacks
- CLAIM: A healthy momentum stock repeatedly makes small pullbacks and snaps back sharply ("tennis ball action" — green bars quickly recovering consolidation). When this stops — pullbacks deepen and don't recover — that is the structure break.
- QUOTE: "स्टॉक इज शोइंग द कैरेक्टरिस्टिक ऑफ अ टेनिस बॉल एक्शन... और वो टेनिस बॉल एक्शन जब एक्वायर कर ले, दैट इज व्हेयर द स्ट्रक्चर ब्रेक्स।" [The stock shows tennis-ball-action characteristics... and when that tennis-ball action breaks down, that's where the structure breaks.]
- CITE: New/Hold or exit How to spot a structural breakdown on charts (CG Power, Tejas, and more) TradeTM.txt (~line 270-290)
- TOOL IMPLICATION: exit rule
- CODEABLE: YES (pattern: bar recovers >X% of prior decline within 1-2 bars = "tennis ball"; failure to recover = flag)

### B11. Structural shorts work best on stocks with persistent momentum that then break — "popcorn trades" (moves same speed down as they did up)
- CLAIM: The best short setups occur in stocks that had strong persistent one-directional momentum before the structural break — the subsequent decline tends to mirror the speed of the prior advance.
- QUOTE: "जब आपका पर्सिस्टेंट मोमेंटम होता है राइट, एंड देन द स्ट्रक्चर ब्रेक्स डाउन, दीज़ आर परफेक्ट मैग्नीट्यूड प्लेट्स ऑन द शॉर्टर साइड... हम लोग इसको पॉपकर्न ट्रेड्स बोलते थे। ऊपर भी वैसे ही जाएगा, नीचे भी वैसे ही जाएगा।" [When you have persistent momentum and the structure breaks down, these are perfect magnitude trades on the short side... we called these popcorn trades — it goes down the same way it went up.]
- CITE: New/Hold or exit How to spot a structural breakdown on charts (CG Power, Tejas, and more) TradeTM.txt (~line 24-32, 620-627)
- TOOL IMPLICATION: entry logic (short-side setup identification); regime read
- CODEABLE: YES (partial — flag "prior persistent-momentum stock + first structural break" as short candidate)
- ⚠️ Note: primarily illustrated with a silver (commodity) short example, not an equity; principle stated as cross-asset.

### B12. EP is fundamentally a structural trick, same family as any Stage-2 breakout — it's "seeing a gap up and waiting for that gap up on a neglected stock"
- CLAIM: Conceptually, EP execution is not a separate technical category from ordinary Stage-2 structural entries — it's the same structure-based logic applied to a gap-up on a previously neglected stock.
- QUOTE: "इवन ईपी और एनी स्टेज टू राइट इज एक्चुअली अ स्ट्रक्चरल ट्रिक... यू आर एक्चुअली सीइंग अ गैप अप एंड देन यू आर वेटिंग फॉर दैट गैप अप ऑन अ नेगलेक्टेड स्टॉक।" [Even EP and any Stage-2 entry is actually a structural trick — you're seeing a gap-up and waiting for that gap-up on a neglected stock.]
- CITE: New/Hold or exit How to spot a structural breakdown on charts (CG Power, Tejas, and more) TradeTM.txt (~line 630-638)
- TOOL IMPLICATION: debate prompt (unify EP and Stage-2 breakout logic in the same evaluation lens)
- CODEABLE: NO (conceptual unification, not a discrete rule)

---

## C. Market Regime Reading (India-specific breadth / participant behaviour)

### C1. Four-phase regime model: Demand Domination / Supply Domination / Lack of Demand / Lack of Supply — most momentum-burst failures happen in "lack of demand," not other phases
- CLAIM: Market conditions should be read as one of four phases rather than binary bull/bear; most momentum-burst setup failures cluster in the "lack of demand" phase specifically, while after major supply exhaustion (entering "lack of supply"), long setups perform exceptionally well.
- QUOTE: "We can categorize market conditions into four phases: 1. Demand Domination... 2. Supply Domination... 3. Lack of Demand... 4. Lack of Supply... most failures in a momentum burst setup occur during the phase of lack of demand, more than in any other phase. Similarly, after major supply exhaustion, the market enters a phase of lack of supply, where many long setups perform exceptionally well."
- CITE: Situational Awareness & Trading: Smart Market Moves_text.txt
- TOOL IMPLICATION: regime read (core regime classifier — this is a strong candidate for the tool's regime-gauge logic, richer than simple bull/bear/choppy)
- CODEABLE: YES (define via breadth exhaustion signals: % stocks below/above key MAs, rate of change of that %, new-high/new-low ratio trend)

### C2. Bench-strength check during a correction: are most watchlist stocks exhausted (limited downside) or still actively distributing?
- CLAIM: To judge whether a correction is nearing exhaustion, check whether the majority of watchlist stocks show signs of demand/supply exhaustion (a bounce becomes likely even if temporary) — this indicates the market is entering "lack of supply" and downside risk is limited.
- QUOTE: "I analyze my watchlist to gauge the bench strength. Are most stocks exhausted, or are they in the process of exhausting, making a bounce inevitable (even if temporary)? If this is the case with the majority of stocks, I conclude that the downside risk in the market is limited."
- CITE: Situational Awareness & Trading: Smart Market Moves_text.txt
- TOOL IMPLICATION: regime read
- CODEABLE: YES (aggregate individual-stock exhaustion signals into a watchlist-level bench-strength score)

### C3. In "lack of demand" phases, gap-driven EPs fail more often — but base-and-break, late-reaction, and failure-reset EP variants perform better
- CLAIM: The classic gap-driven EP has a higher failure rate specifically during lack-of-demand phases; other EP variants (base-and-break, late reaction, failure reset) are less affected and should be favored in that regime.
- QUOTE: "the gap-driven setup of EPs may have a higher failure rate during a lack of demand phase, as breakouts can struggle, other forms of the EP setup—such as base and break, late reaction, or failure reset—tend to perform much better."
- CITE: Situational Awareness & Trading: Smart Market Moves_text.txt
- TOOL IMPLICATION: gate / regime-conditioned setup weighting
- CODEABLE: YES (define regime-conditioned setup-variant preference table)

### C4. "No setups = no trades" is a false constraint; the total tradeable market spans asset classes/timeframes/directions, not just the daily-timeframe VCP scan
- CLAIM: A trader whose scan only covers daily-timeframe equity VCPs is not observing "the market" — real opportunity includes other asset classes, shorts, and other timeframes even when the primary scan looks starved.
- QUOTE: "Your filter scan for daily timeframe VCPs in equities... that's not the Market universe. There are opportunities in the Market like how you traded EP in Oct and Nov when the Market was bad. Don't restrict yourself as a single asset, single direction, single timeframe trader."
- CITE: Situational Awareness & Trading: Smart Market Moves_text.txt (quoting @Anuragg_CA)
- TOOL IMPLICATION: regime read / gate (don't equate "empty scan" with "no opportunity" — check breadth in other frames/asset classes)
- CODEABLE: YES (add secondary scans: intraday timeframe, shorts, alternate asset classes as regime-appropriate fallbacks)

### C5. Six market types (Van Tharp): Bull Normal/Volatile, Bear Normal/Volatile, Sideways Quiet/Volatile — only volatile bear is truly "dead" for a long-only momentum trader
- CLAIM: For a long-only momentum trader, the only regime with no viable adaptation is a volatile bear market; all five other regimes (including normal bear) offer adaptable opportunities via timeframe arbitrage, sizing, or setup choice.
- QUOTE: "For a long-only momentum trader, the only truly 'dead' market is a volatile bear market—where stocks plummet with strong downward momentum and rare bounces... In all other market conditions, the paradox of market participation lies not in choosing when to trade, but in understanding how to trade differently."
- CITE: On Bear Markets and Episodic Pivots Explained_text.txt
- TOOL IMPLICATION: regime read (six-state classifier); gate (only fully stand down in Bear Volatile)
- CODEABLE: YES

### C6. Bear-market first-order opportunities in India: EPs/EP-pullbacks, high-RS survivors, shorts (Small/Mid-cap majority in Stage 3/4), parabolic-long bounces, IPOs (fresh narratives)
- QUOTE: "First-Order Opportunities: Episodic Pivots and EP pullbacks... High Relative Strength stocks... Shorts: More than half of the Small and Mid-cap universe is in Stage 4 or late Stage 3 decline. Parabolic Longs: Oversold stocks... IPO's: Fresh narratives unburdened by market history."
- CITE: On Bear Markets and Episodic Pivots Explained_text.txt
- TOOL IMPLICATION: gate (bear-regime setup menu)
- CODEABLE: YES (regime-conditioned setup list)

### C7. Second-order bear-market adaptations: timeframe arbitrage (5/15/60min visible when daily is invisible), smaller size, expect limited follow-through and sell quickly for small gains
- QUOTE: "Timeframe Arbitrage: What's invisible daily becomes visible in intraday timeframes - 5/15/60 min. Position Sizing: The art of staying small but staying present. Execution adaptations: Anticipate limited follow-through, buy at tight entries, and sell quickly for small gains."
- CITE: On Bear Markets and Episodic Pivots Explained_text.txt
- TOOL IMPLICATION: risk rule / exit rule (regime-conditioned position sizing + take-profit speed)
- CODEABLE: YES

### C8. EP frequency itself is a market barometer — how EP stocks react to catalysts (tepid reaction to strong beats, outsized reaction to modest beats) signals sentiment turns, as seen April 2023 and October 2024
- QUOTE: "The way EP stocks respond to catalysts—their initial surge, follow-throughs, and pullback quality—reveals the market's true appetite for risk... When strong results receive tepid reactions, or modest beats trigger outsized moves, it signals a change in major market sentiment."
- CITE: On Bear Markets and Episodic Pivots Explained_text.txt, "Market Barometer"
- TOOL IMPLICATION: regime read (use EP reaction quality as a leading indicator, feed into regime gauge)
- CODEABLE: YES (track EP reaction-to-quality ratio over rolling window as a regime signal)

### C9. Bull-market maturity signal: EPs become less frequent/less believable when deteriorating result quality meets a lack of genuine neglect — "like a turkey fed daily until Thanksgiving"
- QUOTE: "deteriorating result quality and management commentaries, paired with a lack of genuine neglect in charts and valuations, have created an environment where positive surprises are rare and less believable. This typically occurs in the late stages of bull markets... Like a turkey being fed daily until Thanksgiving, markets become increasingly skeptical of surface-level strength as bull markets mature."
- CITE: On Bear Markets and Episodic Pivots Explained_text.txt
- TOOL IMPLICATION: regime read (late-bull warning signal)
- CODEABLE: NO (requires qualitative "result quality" judgment) — the frequency-of-EP-decline metric is CODEABLE as a proxy.

### C10. During strong-uptrend pullbacks, price pausing near support (10/21 EMA) and resuming is the base-rate expectation — buying pullbacks near support beats buying resistance breakouts in such regimes
- QUOTE: "During pullbacks in a strong uptrend, our primary bias is for the price to pause near its support levels and then resume its upmove... The probabilities of buying pullbacks near support zones in high momentum stocks are better in such markets than buying resistance breakouts."
- CITE: Trading in Choppy Markets: Practical Tactics & Rules_text.txt
- TOOL IMPLICATION: entry logic / regime-conditioned entry preference
- CODEABLE: YES

### C11. Relative strength (RS) ≠ momentum: RS is visible during the decline (what holds up best), momentum is only confirmed after the stock has actually moved; absence of selling doesn't guarantee first-mover buying on the upswing
- QUOTE: "A stock with momentum almost always has relative strength, but a stock with relative strength doesn't always have momentum. You can determine relative strength easily by seeing what holds up the best during the decline, but you can only determine momentum AFTER the stock has moved."
- CITE: Trading in Choppy Markets: Practical Tactics & Rules_text.txt (quoting @AsymTrading)
- TOOL IMPLICATION: gate / debate prompt (don't conflate RS screening with momentum confirmation)
- CODEABLE: YES (define RS and momentum as separate, sequential filter stages)

### C12. Trader vigilance during a panic gap-down: most of the day's damage happens in the first minute, not later — "panic is contra opportunity because everyone is panicking on the same thought"
- CLAIM: When a stock/market gaps down sharply, the worst of the intraday damage typically occurs in the opening minute; if you survive the first ~10 minutes and let the first bounce establish a low, you can trail the stop to that low rather than reacting emotionally.
- QUOTE: "ज्यादातर डैमेज जो है ना वो आपका 15th मिनट में नहीं होगा... ज्यादातर यदि डैमेज होना है ना तो वो मिनट वन में होगा... पैनिकिक जितना ज्यादा होता है उतना ज्यादा मजा आता है मार्केट में... क्योंकि हर आदमी पैनिकिक कर रहा है।" [Most of the damage won't happen in the 15th minute — if damage is going to happen, it happens in minute one... the more panic there is, the more fun the market gets, because everyone is panicking on the same thought.]
- CITE: New/Market About to Gap Down Here's the Exact Framework Smart Traders Use to Prepare TradeTM.txt (~line 1-25, 115-135)
- TOOL IMPLICATION: coach line / exit rule (execution protocol for gap-down mornings)
- CODEABLE: YES (rule: wait ~10 min post-open before reacting to a gap-down; trail stop to first-bounce low, not pre-set fixed stop)

### C13. Pre-planned scenario trees ("if A then X, if B then Y") for volatile mornings remove real-time decision paralysis — this is "procedural memory," seeing the same setup enough times that uncertainty disappears
- QUOTE: "यार एग्जीक्यूशन फ्रेमवर्क होता क्या है ना, यू डू योर सिनेरियो एनालिसिस एंड फॉर ईच सिनेरियो यू हैव अ प्लान प्रिपेयर्ड... रियल टाइम डिसिशन मेकिंग इज़ ओनली टू वेदर यू हैव सीन इट अगेन एंड अगेन बिफोर।" [An execution framework is: you do your scenario analysis and have a plan prepared for each scenario. Real-time decision-making only works if you've seen it again and again before.]
- CITE: New/Market About to Gap Down Here's the Exact Framework Smart Traders Use to Prepare TradeTM.txt (~line 390-420, 686-695)
- TOOL IMPLICATION: coach line / gate (pre-market scenario planner feature)
- CODEABLE: YES (build a pre-market "if gap-down > X% then plan A; if flat-to-small-gap-down then plan B" branch generator)

### C14. Sectoral rotation check on volatile/news days: watch which sector index recovers first as a signal of where liquidity is rotating — but only as a confirmation, not a primary scan (your watchlist should already be sector-loaded)
- QUOTE: "सेक्टर में व्हेन देयर इज़ सम पर्टिकुलर न्यूज़ दैट यू वांट टू ट्रैक... सो इज़ देयर मोर लिक्विडिटी मूविंग टुवर्ड्स दिस सेक्टर? ...यदि मैं आईटी या बैंकिंग बुलिश हूं ना आई वोंट गो टू आईटी इंडेक्स... मेरे स्टॉक वॉच लिस्ट में आई वुड आइडियली वांट टू हैव स्टॉक्स व्हिच आर एनीवे इन थीम।" [When there's specific news you want to track for a sector — is more liquidity moving toward this sector? If I'm bullish on IT or banking, I won't go check the IT index — my stock watchlist should already have stocks that are in that theme.]
- CITE: New/Market About to Gap Down Here's the Exact Framework Smart Traders Use to Prepare TradeTM.txt (~line 20-40, 1339-1360)
- TOOL IMPLICATION: gate / debate prompt (sector index checks are a confirmation layer, not a discovery layer — watchlist construction should already be sector-aware)
- CODEABLE: YES (build watchlist with sector tags upfront; sector-index recovery speed as a secondary confirmation signal, not primary filter)

---

## D. Risk & Position Sizing

### D1. MTF risk is calculated on base (unleveraged) capital, never on leveraged capital — leverage funds capital requirement, not risk
- CLAIM: When using Margin Trading Facility (MTF), position size and risk-per-trade must be computed against the actual base portfolio value, not the leveraged exposure; leverage only reduces the capital blocked to take a given position, it does not change the risk being taken.
- QUOTE: "I don't include the leverage amount in my base capital while calculating position size... For me, MTF only funds the capital requirement, not the risk. The position size remains the same whether I use cash or MTF."
- CITE: Complete Guide to Position Sizing & Risk Management in MTF trading_text.txt
- TOOL IMPLICATION: risk rule (position-sizing formula: risk% × base capital ÷ (entry − stop), independent of leverage)
- CODEABLE: YES

### D2. Cap concurrent tight-SL position initiations at 3-4 to control open risk; typical per-trade risk ~0.65% keeps max open risk ~2-2.5%; broader portfolio open risk should never exceed ~4-5%
- CLAIM: Opening too many tight-stop positions at once (before earlier trades become risk-free) causes open risk to spike, so that a minor pullback can trigger multiple stops simultaneously; specific numeric bands: ~0.65% risk/trade, 3-4 concurrent tight-SL positions, 2-2.5% typical open risk, 4-5% portfolio-wide open-risk ceiling.
- QUOTE: "I avoid initiating more than 3–4 positions at a time (especially in velocity or hybrid trades with tight SLs). My typical risk per trade is ~0.65%, so maximum open risk stays around 2–2.5% at any given time... I ensure that total open risk never exceeds ~4–5%."
- CITE: Complete Guide to Position Sizing & Risk Management in MTF trading_text.txt
- TOOL IMPLICATION: risk rule (open-risk governor; explicit numeric ceilings)
- CODEABLE: YES

### D3. Open risk hitting the upper ceiling is itself a market-quality signal — it means setups are triggering but not following through
- QUOTE: "whenever open risk hits that upper limit, it usually signals a market where setups are triggering but not following through. Trades fail to become risk-free and instead hit SLs, causing compounding losses."
- CITE: Complete Guide to Position Sizing & Risk Management in MTF trading_text.txt
- TOOL IMPLICATION: regime read (feed open-risk-ceiling breaches back into regime gauge as a choppy-market signal)
- CODEABLE: YES

### D4. Initial stop loss above 4% materially reduces trade expectancy — prefer waiting for a better/tighter pivot over a wide stop
- QUOTE: "setting an initial stop loss above 4% can reduce the trade's expectancy. Instead, I prefer to wait for a better pivot and use a tighter stop loss."
- CITE: Position Sizing: The Key to Better Trading Results_text.txt
- TOOL IMPLICATION: gate / risk rule
- CODEABLE: YES

### D5. Position size cap: ~40% of portfolio per trade; reduce size ahead of results if there isn't an adequate profit cushion
- QUOTE: "As a general rule, I cap my per-trade position size at 40% of my portfolio. Additionally, if I do not have an adequate profit cushion before results, I will reduce my position size."
- CITE: Position Sizing: The Key to Better Trading Results_text.txt, "Caveats"
- TOOL IMPLICATION: risk rule
- CODEABLE: YES

### D6. Tighter stop + tighter (earlier) entry produces disproportionately larger trailing size than wider stop/later entry on the same eventual winner (JBMA and Prakash Industries case studies show 2-4x portfolio-impact differences from stop width alone)
- QUOTE: "using a moderate or wide stop loss and selling into strength significantly reduced the trailing size, resulting in a much lower impact on the portfolio (11.8%, 7.3% vs 30.4%)... A tighter stop loss would increase the volatility of your equity curve, but in a magnitude move which is sold in weakness, it has a big impact on your portfolio."
- CITE: Position Sizing: The Key to Better Trading Results_text.txt, Case Study #1 (JBMA)
- TOOL IMPLICATION: risk rule / debate prompt (stop-width directly determines achievable trailing size at equal $ risk)
- CODEABLE: YES (simulate trailing-size outcome under tight/moderate/wide stop scenarios for a given setup)

### D7. Don't apply US stop-loss norms (7-10%, per O'Neil/Ryan/Minervini) blindly — those were calibrated to a different (larger, more liquid, smaller-spread) universe
- QUOTE: "This could explain why renowned momentum traders such as O'Neil, Ryan, and Minervini implemented wider stop losses (7-10%), a practice that continues to be blindly followed without considering the current context... Don't replicate the rules of US traders, who have a 4x larger liquid stock universe than we have in India."
- CITE: The Cost of Illiquidity and Its Impact on Traders_text.txt / Position Sizing: The Key to Better Trading Results_text.txt
- TOOL IMPLICATION: risk rule / debate prompt (India-calibrated stop-width defaults, not imported US defaults)
- CODEABLE: YES (default SL bands should be a configurable India-context parameter set, not hardcoded to Western literature)

### D8. Even a small 2% slippage nearly doubles the initially-taken risk when base SL is 1-3% — add a 0.3-0.6% slippage buffer
- QUOTE: "I generally use tight stop losses (1%-3%), I still add a 0.3%-0.6% buffer to provide for slippages... Even a small 2% price slippage is nearly double the risk initially taken."
- CITE: The Cost of Illiquidity and Its Impact on Traders_text.txt, "Risk"
- TOOL IMPLICATION: risk rule
- CODEABLE: YES

### D9. Portfolio-scale threshold (~₹1cr+) forces a shift from tight-SL velocity/swing trading toward positional strategies in liquid stocks with longer holds and wider risk
- QUOTE: "Once your portfolio exceeds a certain size (1cr+), focusing exclusively on velocity or swing trades with tight stop-losses for rapid profit turnover isn't viable anymore. The focus shifts towards positional strategies with longer holding periods and higher risk and position sizes in liquid stocks."
- CITE: The Cost of Illiquidity and Its Impact on Traders_text.txt
- TOOL IMPLICATION: risk rule / gate (portfolio-size-conditioned setup-mix recommendation)
- CODEABLE: YES

### D10. Never set the actual trailing SL in-system if it's far from current price — use a 2-4% alert instead, to avoid getting shaken out on erratic moves while still capturing unrealised profit
- QUOTE: "If my trailing stop loss is far from the current market price, I don't set the stop loss in the system. Instead, I set alerts 2-4% away."
- CITE: The Cost of Illiquidity and Its Impact on Traders_text.txt, "Execution"
- TOOL IMPLICATION: exit rule / UI (alert-vs-hard-stop distinction)
- CODEABLE: YES — but conflicts partially with D-section rule "always keep a hard stop-loss in system" (see D11); record as two different regimes: near-price hard stop is mandatory, far-trailing-stop-as-alert is a discretionary refinement. Flag both, don't silently pick one.

### D11. "There is no such thing as a mental stop-loss" — always keep a hard stop-loss in the system at all times; a 50% portfolio drawdown case traced directly to relying on a mental stop
- CLAIM: A trader relying on a "mental" (unplaced) stop loss, out of fear of operator stop-hunting, is functionally a gambler; a documented case of a disciplined trader losing 50% of his portfolio traced directly to this practice. Stop-hunting by operators does happen but causes far less damage than mental-stop reliance.
- QUOTE: "anyone who doesn't implement a stop-loss in the system is not a trader—they're essentially a gambler and can't be trusted with serious money... a stoploss that gets hunted by operators will cause far less damage than the mental stoplosses that people rely on. KEEP THE DAMN STOPLOSS. KEEP IT IN THE SYSTEM AT ALL TIMES."
- CITE: Three Fatal Mistakes to Avoid in Stock Markets_text.txt, Mistake A
- TOOL IMPLICATION: risk rule / gate (hard requirement, non-negotiable)
- CODEABLE: YES (system-level enforcement: no position without a live SL order)
- ⚠️ See D10 for the narrower exception (far-trailing-stop as alert) — that exception applies once trailing far above the hard-stop level, not as a substitute for the initial hard stop.

### D12. Never trade with borrowed money from family/friends — a distinct, India-specific social-pressure risk pattern ("uncle/bhaiya lending a multiple of your own portfolio for profit share")
- QUOTE: "Enter the 'superstar Rajinikanth' of our story – the God-sent angel, whether it's an uncle, bhaiya, or friend, who comes with all the money and a desire to make a profit from the markets... never borrow money to trade in the market. If you need additional capital, trade on leverage through MIS or MTF with brokers, but never involve friends or family."
- CITE: Three Fatal Mistakes to Avoid in Stock Markets_text.txt, Mistake B
- TOOL IMPLICATION: coach line (onboarding/capital-source check, culturally specific to Indian family lending patterns)
- CODEABLE: NO (behavioral/social guidance, not a market rule) — though a simple onboarding prompt ("is this capital borrowed?") is trivially codeable as a UX nudge.

### D13. Don't confuse momentum with quality — momentum stocks without a stop-loss are the ones producing 30-80% drawdowns because holders mistake hype for safety ("the 80-50 rule": momentum stocks fall hardest in the next bear market)
- QUOTE: "As Mark Minervini suggests, these momentum stocks are often the ones that fall the hardest during the subsequent bear market (the 80-50 rule)... 'There is no such thing as a safe stock... all stocks are risky.'"
- CITE: Three Fatal Mistakes to Avoid in Stock Markets_text.txt, Mistake C
- TOOL IMPLICATION: gate / coach line (never waive the stop-loss rule for a stock just because of "quality" narrative)
- CODEABLE: YES (hard-enforce SL regardless of any "fundamentally strong" flag on a position)

---

## E. Exits

### E1. MAE/MFE journal analysis: >85% of the author's eventual-stop-outs had already breached 3% of buy price — an 8% SL was capturing no extra win-rate, only extra risk
- CLAIM: A granular MAE (max adverse excursion) / MFE (max favorable excursion) study of 2020 trades showed over 85% of trades that eventually hit an 8% stop loss had already dropped below 3% from entry; tightening the SL to 3% would not have changed win rate but would have quadrupled effective R-speed and doubled trailing size.
- QUOTE: "I noticed that more than 85% of the times, if the price dropped below 3% of my buy price, it would hit my 8% stop loss. Even if I had set my stop loss at 3% instead of 8%, my win rate wouldn't have been any different... My R-multiples are 4x faster (5R at 10% versus 40%)."
- CITE: Trade Journal Analysis and Post Reviews - MAE MFE Guide_text.txt
- TOOL IMPLICATION: risk rule / trade journal analysis feature (MAE/MFE tracked per trade to calibrate stop width)
- CODEABLE: YES (MAE/MFE calculator; feedback loop to recommend SL tightening from historical distribution)

### E2. Breaking the day's low often triggers a deeper stop before the % SL is hit — treat day-low break as its own trigger
- QUOTE: "Breaking the day's low often triggers even deeper stop losses, as buyers have failed to keep the price up on the range expansion day. This helped me prevent my capital from getting stuck in losing trades. Nearly all of my stop losses occur on the same day."
- CITE: Trade Journal Analysis and Post Reviews - MAE MFE Guide_text.txt
- TOOL IMPLICATION: exit rule
- CODEABLE: YES

### E3. Sell-in-strength ratio (how much to sell at 4R vs trail) is a portfolio-management decision, not purely chart-driven — over-selling into strength caps home-run impact; a real case shows a 25% portfolio confirmation-cost from selling 50% at 4R on a stock that later ran 105R
- QUOTE: "the initial sell-in strength at 4R came with a high confirmation cost of ~25% on my portfolio... Every sell in strength decision which compensates for your mental game gaps or process deficiencies, reduces the impact your home run winners will have on your portfolio."
- CITE: Fundamentals and Themes in Trading Explained_text.txt ("Blend Fundamentals & Technicals for Better Trades"), "In Selling"
- TOOL IMPLICATION: exit rule / debate prompt (sell-in-strength % should be tied to conviction/FAITH level, not a fixed default)
- CODEABLE: NO (the calibration of sell-% to conviction is judgment) — but tracking realized-vs-optimal sell ratio is CODEABLE as a journal metric.

### E4. Deep-stop-loss "let it fight back" tactic: when a stock keeps showing long lower wicks / recovering intraday pressure without breaking averages, hold with a much deeper stop; exit the instant that fighting-back behavior stops (a "visible change in behavior")
- CLAIM: While a momentum stock repeatedly absorbs selling pressure (long lower tails, closes in upper half of range, recovers from red opens) without breaking key moving averages, it's appropriate to widen the stop loss and hold through the volatility; the exit trigger is the first day the stock stops fighting back and instead shows one-way selling.
- QUOTE: "जितनी बार नीचे जा रहा है सब में लोअर विक्स आपको दिख रही है... द स्टॉक इज अटेमप्टिंग टू फाइट बैक... इस दिन मुझे एक विज़िबल इंट्यूशन वाइज एक विज़िबल चेंज इन बिहेवियर यह महसूस हुआ कि स्टॉक अब स्लिप कर रहा है इस केस। तो मैंने अगले दिन CG पावर को यहां पे निकाल दिया।" [Every time it goes down, you see lower wicks — the stock is attempting to fight back... on this day I felt a visible change in behavior — the stock is now slipping. So I exited CG Power the next day.]
- CITE: New/Hold or exit How to spot a structural breakdown on charts (CG Power, Tejas, and more) TradeTM.txt (~line 355-400)
- TOOL IMPLICATION: exit rule (discretionary but pattern-describable: track lower-wick frequency + close-position-in-range as a "fight-back" score; exit trigger = score reversal)
- CODEABLE: YES (partial — codify "fight-back" score from wick/close-position data; final exit call flagged as discretionary confirmation)

### E5. Intraday exit via momentum-loss reading on 1-min/5-min chart when the trade's objective was explicitly intraday — trailing 50 DEMA on 1-min, then 10/20 DEMA on 5-min
- QUOTE: "मैं एक तरह से मोमेंटम लॉस यूज कर रहा हूं ट्रेड करने के लिए 1 मिनट या 5 मिनट के चार्ट पे... चेंज इन बिहेवियर आया मोमेंटम खराब हुआ, आई एम एग्जिटिंग द स्टॉक। देयर इज नो क्वेश्चन... क्योंकि मेरा ऑब्जेक्टिव फुलफिल हो गया।" [I'm essentially using momentum loss to trade on the 1-min or 5-min chart. Behavior changed, momentum went bad, I'm exiting — no question about it, because my objective (an intraday trade) was already fulfilled.]
- CITE: New/Hold or exit How to spot a structural breakdown on charts (CG Power, Tejas, and more) TradeTM.txt (~line 410-505)
- TOOL IMPLICATION: exit rule (objective-conditioned trail timeframe: intraday objective → intraday MA trail; swing objective → higher-timeframe trail)
- CODEABLE: YES

### E6. R-multiple targets (4R/6R/10R) are indicative guides for scaling out, not hard-coded rules — the underlying stock's volatility changes what a given % move "means" in R-terms, so blend strategy with situational read
- CLAIM: A fixed R-multiple exit framework (e.g. always book at 4R) is not mechanically "correct" because R itself is a function of stop width, which itself varies with underlying volatility — a large-cap slow mover reaching 4R in a 3% move behaves very differently from a small-cap fast mover reaching 4R in a 15% move. The trader must blend the R-framework with situational judgment (own performance state, market condition, stock behavior) rather than applying it as an algorithm.
- QUOTE: "आर मल्टीपल इज़ नॉट समथिंग... यू ऑलवेज मेक रिटर्न इन मल्टीपल्स एंड यू लूज़ इन वन आर। दैट इज़ अ कॉन्सेप्चुअल कॉन्सेप्ट... इट इज़ नॉट अ वे जहां... स्टॉप लगा है, स्टॉप स्टॉप सिस्टम में है — देयर इज़ नो क्वेश्चन आस्क्ड। लेकिन जब प्रॉफिट लेना है — आई विल ऑलवेज हैव सम क्वेश्चंस दैट आई आस्क मायसेल्फ।" [The R-multiple isn't rigid — you always aim to make returns in multiples and lose in one R, that's a conceptual concept. It's not something where — a stop loss is placed, it's in the system, no question asked. But when it comes to taking profit, I'll always have questions I ask myself.]
- CITE: New/The Biggest Mistake Traders Make When Selling (Selling Is a Decision, Not a Rule) TradeTM.txt (~line 20-75, 155-180)
- TOOL IMPLICATION: exit rule / debate prompt (asymmetric rule: stop-loss execution = mechanical/non-negotiable; profit-taking = discretionary, situation-blended)
- CODEABLE: NO for the profit-take blend itself (explicitly discretionary by design) — but the SL-is-mechanical / profit-take-is-discretionary *asymmetry* is CODEABLE as a system design principle (hard-enforce SL orders, soft-suggest profit-take levels).

### E7. R-multiple is not comparable across stocks of different underlying volatility — a "4% bar" in a large slow-mover equals a much bigger proportional move than the same % in a smaller fast-mover; this is why Pradeep Bonde uses a dollar-breakout concept instead of pure %
- QUOTE: "परसेंटेज खुद में इक्वल नहीं होता है। परसेंटेज इज़ बेस्ड ऑन द अंडरलाइन वोलिटिलिटी ऑफ़ द स्टॉक... दैट इज़ व्हाई बॉन्डे यूज़ेज़ अ डॉलर ब्रेकआउट कॉन्सेप्ट।" [Percentage itself isn't an equal concept — percentage is based on the underlying volatility of the stock. That's why (Pradeep) Bonde uses a dollar-breakout concept.]
- CITE: New/The Biggest Mistake Traders Make When Selling (Selling Is a Decision, Not a Rule) TradeTM.txt (~line 152-160)
- TOOL IMPLICATION: risk rule / debate prompt (normalize R-multiple / breakout-magnitude comparisons by underlying stock volatility, not raw %)
- CODEABLE: YES (compute ATR-normalized or $-move-normalized R instead of raw % R)

### E8. Two kinds of "letting go": letting go of unrealized profit, and letting go of capital — scaling up requires the trader to let go of large unrealized profits (accept giving some back) in exchange for a shot at a much larger realized profit, and you never know in advance which trade that will be
- QUOTE: "देयर आर टू काइंड्स ऑफ़ लेटिंग गो। देयर इज़ अ लेटिंग गो ऑफ़ प्रॉफिट एंड देयर इज़ अ लेटिंग गो ऑफ़ कैपिटल। फॉर यू टू एक्चुअली स्केल अप... यू नीड टू लेट गो ऑफ़ अ लॉट ऑफ़ अनरियलाइज्ड प्रॉफिट्स टू गेट अ हायर रियलाइज्ड प्रॉफिट एंड यू डोंट नो व्हेन इट इज़ गोइंग टू हैपन इन विच ट्रेड।"
- CITE: New/The Biggest Mistake Traders Make When Selling (Selling Is a Decision, Not a Rule) TradeTM.txt (~line 20-27, 680-690)
- TOOL IMPLICATION: coach line / debate prompt
- CODEABLE: NO (mindset framing)

### E9. "If you scoop small change, you'll never get big" — regret over a missed early profit-take on a stock that later became a home run is the necessary cost of ever holding a real winner; comparing a spoiled trade (Blue Dart) to a persistent winner is a trap because both looked identical at day zero
- QUOTE: "यदि आप यह रिग्रेट करेंगे कि ब्लू डार्ट में मैं फोर आवर पे बुक कर लेता एंड आई वुड हैव मेड सम मनी। आई प्रॉमिस यू कि आप कभी पर्सिस्टेंट होल्ड नहीं कर पाएंगे... डे जीरो पर... ब्लू डार्ट में और पर्सिस्टेंट में क्या अंतर है? कोई अंतर नहीं है।" [If you regret not booking Blue Dart at 4R, I promise you'll never be able to hold a persistent winner. On day zero, there's no visible difference between a stock that fizzles (Blue Dart) and one that runs persistently.]
- CITE: New/The Biggest Mistake Traders Make When Selling (Selling Is a Decision, Not a Rule) TradeTM.txt (~line 540-560)
- TOOL IMPLICATION: coach line
- CODEABLE: NO

---

## F. Psychology / Process Rules

### F1. Anger and depression, not just fear/greed, are constant undertones and can be super-performance drivers if mapped via a structured framework (What's the problem → Why does it exist → What's flawed → What's the correction → What logic confirms it)
- QUOTE: "for nearly every trader I've encountered, including myself, anger and depression remain as constant undertones. They are the primary drivers of super performance."
- CITE: Trading Emotions: Managing Anger & Depression_text.txt
- TOOL IMPLICATION: coach line (journal prompt template: 5-step tilt-mapping framework, from Jared Tendler's Mental Game of Trading)
- CODEABLE: YES (structured journal-prompt sequence)

### F2. Prospect Theory in trading: pain of a stopped-out −1R exceeds joy of a +1R win even at identical magnitude — this is why a 35-65% win rate can still feel net-negative emotionally despite being profitable
- QUOTE: "The emotional toll of getting stopped out at (-) 1R is much higher than the satisfaction of a trade where you gain (+) 1R. Therefore, like most traders, if your win rate fluctuates between 35-65%, it still has a net negative impact on your emotional state."
- CITE: Trading Emotions: Managing Anger & Depression_text.txt
- TOOL IMPLICATION: coach line
- CODEABLE: NO

### F3. The Decision Bell Curve (A-game/B-game/C-game) and the "Inchworm" model of process improvement — improve the front (A-game ceiling) and back (C-game floor) alternately, and old B-game becomes new C-game
- QUOTE: "The A-game level... is the peak of your conscious competence... your C-game consists of the Known Knowns - mistakes that are so obviously wrong that you recognize them immediately... Consistent improvement happens by taking one step forward from the front of your bell curve... followed by another step forward from the back."
- CITE: Improving Trading Processes for Better Performance_text.txt (quoting Jared Tendler's "The Mental Game of Trading")
- TOOL IMPLICATION: coach line (framework for structuring trade-review/self-audit)
- CODEABLE: NO (self-assessment framework, not a market rule) — could be codeable as a categorization tag (A/B/C) applied to journal entries.

### F4. Feedback loop discipline: "build with frequency, build with speed" — start with velocity trades (faster feedback) rather than magnitude trades (IPO/EP) to build procedural memory quickly; frequency-first is efficient specifically at the *learning* stage, not as a permanent style
- QUOTE: "starting out with velocity trades (VCP, breakouts, pullbacks, reversals) are easier for building than magnitude trades (IPOs, EPs)... The shorter the feedback loops, the easier it is to replan."
- CITE: Developing Feedback Loops: Trader's Blueprint for Speed_text.txt
- TOOL IMPLICATION: coach line (onboarding/skill-stage-conditioned setup recommendation)
- CODEABLE: YES (tag setups by feedback-loop speed; recommend velocity-first for newer users)

### F5. Real journal insight examples: reducing SL from 8% to 3% wouldn't have changed win rate but would have yielded 71% more returns; 55% of winners didn't immediately go risk-free under range-breakout entries, fixed by entering closer to ORB rather than waiting for trendline/swing-high confirmation; 70% of biggest winners started with gap-ups from surprise earnings (→ EP focus)
- QUOTE: "The same trades would have yielded my 71% more returns than the actual returns... 55% of my winners did not immediately become risk-free (cross 2R+) as expected... 70% of my biggest winners started their momentum with gap-ups from surprise earnings, leading to FOMO and intensity in upmoves. This led me to focus more of my capital on EP setups."
- CITE: Developing Feedback Loops: Trader's Blueprint for Speed_text.txt
- TOOL IMPLICATION: coach line / trade journal analysis (these are worked examples of the journal-review methodology, not universal numbers)
- CODEABLE: NO (specific historical figures — not to be hardcoded; the *methodology* of asking these three journal questions is CODEABLE as a review-prompt template)

### F6. "There is no such thing as objective rules that fully define price action" — markets are driven by trader decisions/emotions, so intuition built through granular post-trade review beats rigid rule-following; excessive need for objectivity/perfection can unconsciously shrink risk appetite into pure "risk management" instead of "risk-taking"
- QUOTE: "Trader decisions cannot be governed by rigid rules, and as a result, price movement cannot be dictated by fixed rules... my natural risk appetite unconsciously started to decrease, to the point where I was only 'managing risk' instead of actively 'taking risk' for super performance."
- CITE: Trading Intuition Over Objective Rules Explained_text.txt
- TOOL IMPLICATION: debate prompt / coach line (caution against over-mechanizing the tool at the expense of trader judgment; the tool should support discretion, not replace it)
- CODEABLE: NO — this is a meta-caveat on the entire premise of an automated/gated system; worth surfacing to the user, not encoding as logic.

### F7. Seek the cause of price movement (order-flow decision points/stress zones), not just the effect (patterns/trendlines/indicators) — enter ahead of the crowd's decision point so their order flow adds to your position
- QUOTE: "It is more efficient to seek the cause and enter before them, allowing their order flow to add to ours and move our position into profit." (Allegory of the Cave framing: patterns/indicators are "shadows and echoes," not the underlying cause.)
- CITE: Trading Intuition Over Objective Rules Explained_text.txt
- TOOL IMPLICATION: debate prompt / entry logic philosophy
- CODEABLE: NO (interpretive framing)

### F8. 10,000 iterations, not 10,000 hours — for new traders, overtrading is a legitimate low-cost learning tool (not a flaw), because sitting on the sidelines waiting for "perfect" conditions is worse for skill development at that stage
- QUOTE: "Forget the 10,000-hour rule. It's about 10,000 micro-bets... Overtrading may be a problem for professionals, but for new traders, it can be a low-cost learning tool."
- CITE: On Bear Markets and Episodic Pivots Explained_text.txt
- TOOL IMPLICATION: coach line (stage-conditioned advice — differs for new vs. experienced users)
- CODEABLE: NO

### F9. Scaling a portfolio is a mental-barrier problem more than a technical one; even top traders (Qullamaggie, Minervini) had 10-50% drawdowns while scaling — "uncomfortably aggressive" positive-expectancy risk-taking, not raw probability comfort, differentiates outcomes
- QUOTE: "Even Qullamaggie faced drawdowns of ~50% while scaling up. What distinguishes successful traders are the intangibles. They've mastered being 'uncomfortably' aggressive, pushing themselves to where they have FAITH in their ability to recover without risking catastrophic losses."
- CITE: On Bear Markets and Episodic Pivots Explained_text.txt / How Probabilities Can Be Misleading in Trading_text.txt
- TOOL IMPLICATION: coach line
- CODEABLE: NO

### F10. Peer-group deep dives (5-8 trader groups sharing a spreadsheet of post-market results tracking, EPS/sales QoQ/YoY) is the concrete India-specific mechanism used to make EP tracking sustainable for working professionals
- QUOTE: "form a 5-6 member peer group to jointly fill in a Google sheet with the results - EPS and Sales (QoQ, MoY)... Collaborate with a small group of 6-8 traders to share the task of updating the spreadsheet."
- CITE: Setup Prioritization and EPs — EP Trading Guide Tips_text.txt / On Bear Markets and Episodic Pivots Explained_text.txt
- TOOL IMPLICATION: coach line (feature idea: shared EP-tracking sheet / community layer) 
- CODEABLE: YES (build a shared post-market-results tracker with EPS/sales QoQ-YoY fields, gap-up% sort — this is a literal workflow spec)

### F11. EP execution window is narrow and mechanical: 9:00-9:15am sort results by gap-up%, tile charts on second monitor for 9:07-9:30am execution — designed explicitly to fit a working professional's schedule, not require all-day screen time
- QUOTE: "Between 9.00-9.15 am, sort the results based on Gap up%... Trading execution happens primarily in the 9:07-9:30 AM window, freeing you from constant screen monitoring."
- CITE: On Bear Markets and Episodic Pivots Explained_text.txt
- TOOL IMPLICATION: gate / coach line (this is literally a UI workflow spec: results dashboard sortable by gap-up%, designed for a 20-30 min daily window)
- CODEABLE: YES

### F12. Setups don't inherently have a statistical "edge" — the payoff structure (win definition, stop definition, qualitative context) determines profitability, not the pattern itself; backtested win rates are meaningless without defining "flag," "win," and "stop" precisely, and without accounting for context (an EP-follow-through flag ≠ a climactic-move flag)
- QUOTE: "Setups don't have an edge. The moment we claim they do, we mistakenly attribute the outcome to the setup itself... A flag forming as a follow-through to an early-stage EP setup will likely have a completely different outcome compared to one forming during a climactic move."
- CITE: Creating a Setups Playbook for Smarter Trading_text.txt
- TOOL IMPLICATION: debate prompt (caution against treating any single setup-tag as having a fixed backtested win-rate; context must gate/modify it)
- CODEABLE: NO — but strongly implies CODEABLE requirement: any setup-scoring logic must include context tags (prior-move stage, market regime) alongside the raw pattern tag.

### F13. Setups Playbook build steps: one-line setup definition → model visual → 2-3 key qualitative criteria → 1-2 non-negotiable scan criteria → watchlist-stage framework → ≤4 trade-management rules (Velocity/Magnitude/Hybrid templates) → historical database (2 charts per example: pre-breakout + played-out) → feedback loop
- QUOTE: "Identify Trade Management Rules... I personally use three template frameworks—Velocity, Magnitude, and Hybrid—based on the intent behind the trade. It's also important to keep your trade management rules limited to four or fewer."
- CITE: Creating a Setups Playbook for Smarter Trading_text.txt
- TOOL IMPLICATION: tool architecture (the three trade-management templates — Velocity/Magnitude/Hybrid — map directly onto Manas OS's trade-management-template selection logic)
- CODEABLE: YES (this is close to a literal spec for a setup-registration workflow)

### F14. Database-building rule of thumb: prioritize sample richness over historical depth (very old pre-2016-17 data adds little given how much liquidity/info-speed has changed); include at least one full bull, one full bear, and 2-3 transition phases
- QUOTE: "very old data adds minimal incremental value compared to the huge effort it demands... I prefer to include at least one complete bull and one complete bear market in my database, along with two or three transformation phases."
- CITE: Creating a Setups Playbook for Smarter Trading_text.txt
- TOOL IMPLICATION: pipeline-hygiene / backtest-design guidance
- CODEABLE: YES (define backtest window selection heuristic: recency-weighted, cover both regime types + transitions, skip pre-2016 data by default)

### F15. Trade the market you are in, not the market you wish you were in — the closing refrain, tied to the Expectancy × Frequency framework and the "Swing Trader Fallacy" (India-specific: pure swing trading underperforms structurally in India's shallow/circuit-limited market vs. the US)
- QUOTE: "The portfolio return equation for any stock market player can be broken down into a simple formula: Expectancy × Frequency... swing trading often ends up becoming a half-assed, confused technique. It lacks both the agility of day trading and resilience of positional trading... Trade the market you are in, and not the market you wish you were in."
- CITE: Trade the Market You are in: Adapt to Win in India_text.txt
- TOOL IMPLICATION: coach line / debate prompt (core philosophy statement — most quoted principle across the corpus)
- CODEABLE: NO (philosophy) — but the underlying claim (pure-swing underperforms in India due to shallow liquidity + circuit limits) is the justification for CODEABLE gates elsewhere (A1-A4, D7).

### F16. Two failure modes from the Adaptability section: (1) managing high-expectancy setups (IPOs/EPs) too tightly like frequency trades → shakeouts; (2) taking an all-or-nothing approach on high-frequency lower-expectancy setups (momentum bursts) despite sentiment-dependence → squats
- QUOTE: "1) Managing high-expectancy setups like IPOs and EPs too tightly as if they were frequency trades, resulting in shakeouts. 2) Taking an all-or-nothing approach with high-frequency, lower-expectancy trades like momentum bursts, despite knowing that breakout success depends heavily on market sentiment—resulting in squats."
- CITE: Trade the Market You are in: Adapt to Win in India_text.txt
- TOOL IMPLICATION: gate / debate prompt (setup-type must dictate trade-management-template selection — mismatched management style is a named, specific failure mode)
- CODEABLE: YES (enforce setup-type → template mapping; flag when a magnitude-type setup is being risk-managed with velocity-tight rules or vice versa)

### F17. 90% of trade failures are entry failures, not setup/stock/technical-analysis failures — separates "technical analysis" (chart reading) from "trading" (execution) as genuinely distinct skills
- QUOTE: "आप अपने जर्नल में जाकर देखिए... आप ये पाएंगे कि 90% ऑफ ट्रेड्स... ट्रेड का फेलियर नहीं था, स्टॉक का फेलियर नहीं था, सेटअप का फेलियर नहीं था — वो एक एंट्री फेलियर था। ज्यादातर लोग ये मानते हैं कि टेक्निकल एनालिसिस और ट्रेडिंग एक है — दोनों बिल्कुल डिफरेंट चीजें हैं।" [Go look in your journal — you'll find 90% of trades: it wasn't a trade failure, stock failure, or setup failure — it was an entry failure. Most people think technical analysis and trading are the same thing — they're completely different.]
- CITE: New/How to Enter a Trade Like a Pro (A Complete Entry Framework) TradeTM.txt (~line 1-25)
- TOOL IMPLICATION: coach line / debate prompt (entry execution quality should be journaled/scored separately from setup-selection quality)
- CODEABLE: NO (specific "90%" figure is anecdotal, not to be hardcoded) — but the *separation of entry-quality from setup-quality* as two distinct journal metrics is CODEABLE.

### F18. "Trade what the market is giving you, not what I taught you" — static rule-memorization is "an enemy of understanding"; real markets show blended/ambiguous Stage transitions (e.g. Stage 4 merging directly into Stage 2, or Stage 3/4 indistinguishable) and traders must read the actual chart, not force it into a memorized template
- QUOTE: "यू नीड टू ट्रेड व्हाट द मार्केट इज़ गिविंग यू, नॉट व्हाट आई टॉट यू... मेमोराइजेशन इज़ एन एनिमी ऑफ़ अंडरस्टैंडिंग। ...स्टेज वन और टू के मिक्सचर के साथ, स्टेज थ्री और फोर के मिक्सचर के साथ... यू विल गेट अ लॉट ऑफ़ सिचुएशंस।" [You need to trade what the market is giving you, not what I taught you... memorization is an enemy of understanding... you'll get a lot of situations with mixtures of Stage 1&2, Stage 3&4, etc.]
- CITE: New/Price Doesn't Move Markets — People Do Stop misreading price action.txt (~line 87-146)
- TOOL IMPLICATION: debate prompt / coach line (Wyckoff/Weinstein-stage classification should allow ambiguous/blended states, not force a single discrete label)
- CODEABLE: YES (partial — stage classifier should output confidence/blend across adjacent stages rather than a hard single-label, per this explicit caution)

### F19. "Think in your anti-thesis" — a retail trader's default thesis is retail-framed; the discipline is to think as a fund manager would, then re-apply that lens as a retail participant (what are the other ~40 fund managers thinking that I'm missing?)
- QUOTE: "थिंकिंग एंटी थीसिस में क्या है पता है? मेनी टाइम्स योर थीसिस इज़ यू थिंकिंग एज अ रिटेलर, योर एंटी थीसिस इज़ यू थिंकिंग एज अ फंड मैनेजर एंड देन अप्लाइंग इट एज अ रिटेलर।" [You know what your anti-thesis is? Many times your thesis is thinking as a retailer; your anti-thesis is thinking as a fund manager and then applying it as a retailer.]
- CITE: New/Price Doesn't Move Markets — People Do Stop misreading price action.txt (~line 570-580)
- TOOL IMPLICATION: debate prompt (explicit design pattern for a "fund manager" debate persona / lens, distinct from the "retailer" default lens)
- CODEABLE: NO (framing device) — directly informs a debate-family design: add an institutional-perspective persona to the debate roster.

### F20. Frustration-cycle depth/duration matters for setup quality: a preferred setup shows a *long* frustration cycle (extended sideways time) with *shallow* depth (small pullback relative to visible chart width) — this combination, not raw pattern shape, differentiates a good base from a bad one; recovery width should be at least 1-1.5x the visible horizontal consolidation width
- QUOTE: "प्रेफर्ड ये है सेटअप में कि जो आपका डेप्थ है वो जो आपको नजर से दिखता है... उसका कम से कम एक से डेढ़ गुना आपका होना चाहिए [चौड़ाई]... जितनी फ्रस्ट्रेशन की साइकिल लंबी होगी और डेप्थ जितना कम होगा उतना बेटर होगा।" [The preferred setup is one where the depth you visually see... should be at least 1 to 1.5x [in width]. The longer the frustration cycle and the shallower the depth, the better the situation.]
- CITE: New/Price Doesn't Move Markets — People Do Stop misreading price action.txt (~line 550-566)
- TOOL IMPLICATION: gate (quantifiable base-quality heuristic: consolidation-width ÷ visible-depth ratio ≥ ~1-1.5)
- CODEABLE: YES (compute width:depth ratio of a consolidation and gate on a minimum threshold)

### F21. Timeframe changes the "human emotion cycle" that plays out — a daily-chart shakeout-and-recovery cycle does NOT replay identically on an intraday timeframe with the same %, because price is fractal only insofar as human emotion is fractal across that specific timeframe, not universally
- QUOTE: "प्राइस फ्रैक्टल इन नेचर इसलिए नहीं है क्योंकि प्राइस फ्रैक्टल इन नेचर — प्राइस फ्रैक्टल इन नेचर इसलिए है क्योंकि ह्यूमन इमोशंस आर फ्रैक्टल इन नेचर, बट प्राइस इज ड्रिवन बाय ह्यूमन इमोशन... जहां इमोशन टू इमोशन का अंतर है, वहां आपने इमोशन की एक साइकिल देखी, वो साइकिल यहां प्ले नहीं हो रही।" [Price is not fractal by itself — price is fractal because human emotions are fractal, and price is driven by human emotion. Where the emotion-to-emotion context differs, a cycle you saw at one timeframe won't replay at another.]
- CITE: New/Price Doesn't Move Markets — People Do Stop misreading price action.txt (~line 500-520)
- TOOL IMPLICATION: debate prompt (caution against mechanically transplanting a daily-chart pattern rule onto intraday, or vice versa, without re-deriving the underlying emotional-cycle logic)
- CODEABLE: NO (conceptual caution)

### F22. Concept vs process: adapting an idea (e.g. the "9-Million volume scan") to a new market requires understanding *why* it works, not copy-pasting the *process* — literally quoting Pradeep Bonde: "you have to understand the core idea and the concept, not just the process"
- QUOTE: "Pradeep sir put it well himself: you have to understand the core idea and the concept, not just the process. Without that understanding, having the process is of little use."
- CITE: 9 mil vol scan_text.txt
- TOOL IMPLICATION: coach line / debate prompt (design philosophy — any imported US technique should be re-derived for Indian market structure, not literally copied)
- CODEABLE: NO (meta-principle)

---

## G. Sector/Theme Rotation Habits

### G1. Two theme-identification approaches: Top-Down (sector RS chart → drill into stocks) vs. Bottoms-Up (spot stocks setting up in a common sector from the watchlist/top-movers) — author personally prefers Bottoms-Up as more effective despite higher effort
- QUOTE: "Top Down: In this method, you start by taking a bird's-eye view of the sectoral chart and drill down to the stocks within the sector... Bottoms Up: Identify stocks in your watchlist that are setting up or currently in momentum within a common sector... Although it may require more time and effort to develop, I find it to be the more effective method."
- CITE: Fundamentals and Themes in Trading Explained_text.txt ("Blend Fundamentals & Technicals for Better Trades")
- TOOL IMPLICATION: pool filter / theme-detection logic
- CODEABLE: YES (implement both scans; default-weight Bottoms-Up)

### G2. Sector-grouping tools (e.g. MarketSmith India) are "theoretically sound but practically useless" because of miscategorization (e.g. an "Auto Manufacturers" chart lumping Maruti with a ₹40L-market-cap radiator maker)
- QUOTE: "although many of their sector groupings though theoretically sound, are practically useless. (Eg.- the Auto Manufacturers chart includes Maruti, Bajaj Auto, Olectra, and a 40 Lakh MCap India Radiators)."
- CITE: Fundamentals and Themes in Trading Explained_text.txt
- TOOL IMPLICATION: pool filter (sector taxonomy must be curated, not taken as-is from a generic classification provider — directly relevant to Manas OS's own index/sector taxonomy work)
- CODEABLE: NO (specific critique of a third-party tool) — reinforces already-planned CODEABLE work: curated sector taxonomy, not vendor-default.

### G3. Successful theme traders (Qullamaggie, Dan Zanger, Mark Boucher) identify what's already moving first, then wait for entry — not the reverse; they pay a higher "confirmation cost" for entering later because these institutional trends persist for months
- QUOTE: "Qullamaggie, Dan Zanger, and Mark Boucher, the most successful theme traders identified what's moving and then waited for favourable entry points, rather than the other way around. They were willing to pay a higher cost for this buy confirmation, as these trends typically persist for many months."
- CITE: Fundamentals and Themes in Trading Explained_text.txt
- TOOL IMPLICATION: debate prompt / gate (theme confirmation should follow price action, not precede it — don't reward "predicting" the next theme over confirming an active one)
- CODEABLE: YES (theme-detection scan should be triggered by top-mover clustering, not a predictive sector forecast)

### G4. Fundamental catalyst identification is sector-specific and must be re-derived per sector, not generalized: agriculture (monsoons + govt policy), infra (debt restructuring/overdue receivables, e.g. Suzlon), chemicals (low capacity utilization + demand catalyst), new-age listings (profit metrics superseding user/transaction-count metrics), and macro liquidity waves (Fed printing → broad rally)
- QUOTE: "the agricultural sector is affected by both monsoons and government policies; infrastructure stocks can emerge from debt restructuring (such as Suzlon) or receipt of overdue debtors; Chemical stocks often move when there is low un-utilised manufacturing capacity and there is a catalyst to increase demand."
- CITE: Fundamentals and Themes in Trading Explained_text.txt
- TOOL IMPLICATION: gate / debate prompt (sector-specific catalyst checklist, India-specific examples)
- CODEABLE: NO (qualitative catalyst identification) — but the *category list itself* (monsoon/policy, debt-restructuring, capacity-utilization, profitability-metric shift, macro liquidity) is usable as a structured tag taxonomy — CODEABLE as tagging schema, not as an automated detector.

---

## H. Seasonality / Event-Driven Timing (results season, budget, expiry, IPOs)

### H1. Budget-day volatility should be treated as a temporary/known-event risk window, not a reason to avoid trading — pre-planned scenario branches for a 5-6% gap-down handle the event mechanically
- QUOTE: "सपोज द होल निफ्टी ओनली गैप्स डाउन बाय से 5 6% कल जैसे शाम को दिखा रहा था फॉर एग्जांपल... इफ दैट हैपेंस, ओके, देन इज़ द वर्स्ट केस डिस्काउंटेड।" [Suppose Nifty gaps down 5-6% like it showed yesterday evening — if that happens, that's the worst case, already discounted for.]
- CITE: New/Market About to Gap Down Here's the Exact Framework Smart Traders Use to Prepare TradeTM.txt (~line 511-520)
- TOOL IMPLICATION: gate / regime read (event-day pre-planning, not blanket avoidance)
- CODEABLE: YES (flag known macro-event days — budget, major elections, Fed days — and auto-generate the scenario-branch planner from C13)

### H2. Post-budget CG Power example: author held through budget-day volatility with a much deeper-than-usual stop because the stock was still "fighting back" against selling pressure (see E4); a specific-day 20 DMA breach visible on 1-min chart was the exit trigger
- CITE: New/Hold or exit How to spot a structural breakdown on charts (CG Power, Tejas, and more) TradeTM.txt (~line 330-345)
- TOOL IMPLICATION: exit rule (illustrative case, ties E4 to a specific India seasonal event)
- CODEABLE: NO (single anecdote)

### H3. EP frequency and quality is explicitly tied to quarterly results season — EP scan/tracking is only a live daily workflow during the post-results window, and "how good the EP season was" is itself used as a market-sentiment signal (see C8, C9)
- QUOTE: "This quarter, we have had one of the best EP seasons, with several stocks making strong post-result up moves... It was likely a good prelude to the bullish follow-through that was expected after a choppy consolidation of ~6 weeks."
- CITE: Setup Prioritization and EPs — EP Trading Guide Tips_text.txt
- TOOL IMPLICATION: regime read / gate (results-season calendar should gate when the EP scan is the "primary" active setup vs a secondary one)
- CODEABLE: YES (NSE results-calendar-aware EP-scan activation window)

### H4. April 7th 2025 cited twice independently as a landmark gap-down-then-reversal day (tariff-related) that created some of the best entries of the year, and again as a reference point for what the best follow-through pyramiding case looks like
- QUOTE: "The best study last year was for seventh of April because you see sixth of April... after that candle happened, a lot of pyramiding momentums were also created after that." / "अप्रैल सेवंथ कैंडल आई ऑलरेडी हैव अनरियलाइज्ड प्रॉफिट्स, इट गिव्स मी अ गुड पिरामिडिंग पोजीशन।"
- CITE: New/Market About to Gap Down Here's the Exact Framework Smart Traders Use to Prepare TradeTM.txt (multiple references, e.g. ~line 780-800, 990-1015)
- TOOL IMPLICATION: regime read (case study reference — sharp macro-driven gap-down days can produce the year's best pyramiding opportunities if the stock/theme was already in play)
- CODEABLE: NO (single historical case; illustrative)

---

## Residual Gap (flagged, not fabricated)

The following raw transcript files (~2MB, 23 files under `Tradetm/`) were NOT read in this pass:
`D2 Setup.txt`, `EP Masterclass.txt`, `Missed Execution.txt`, `Volume.txt`, `ai cant replace.txt`,
`avg stocks.txt`, `broken leaders.txt`, `choppy.txt`, `entry framework.txt`, `ep masterclass og.txt`,
`ep qna.txt`, `execution setup.txt`, `how pro traders.txt`, `ipo bases.txt`, `mae mfe.txt`,
`miss stocks.txt`, `missing.txt`, `peak trading.txt`, `prce act strat.txt`, `prio.txt`,
`right wrong.txt`, `short or positional.txt`, `trading system.txt`. Also not read: 17 additional
`New/` video transcripts beyond the 5 sampled (titles suggest: Minervini VCP notes, Qullamaggie
learnings, volume-trap/smart-money accumulation, tight-areas momentum edge, bar-by-bar real-time
skill, EP Q&A on success/failure/timing, drawdown psychology, missed-trades exercises, "personalized
trading system from scratch" full session, and a play-by-play session). A follow-up extraction pass
over this residual set is recommended before treating this document as fully exhaustive — it likely
contains additional IPO-base-specific and average-stock-behavior nuances not yet captured here,
plus more India-specific execution nuance in the untranslated Hindi material.

`manas_os/design/study/Tradetm/` (in-repo copy) was spot-checked and found to be the same corpus
(duplicate/subset of the `book/momentum-project` copy) — no additional unique files beyond
`main.md` and `How_Working_Professionals_Can_Build_a_Trading_System_for_Bull_Markets_Transcript.md`,
neither of which was read in this pass (also flagged as residual gap).

`Indian_Momentum_Trading_TradeTM.html` was not opened in this pass (residual gap) — flagged for a
follow-up pass; based on the filename it likely overlaps substantially with the blog articles
already extracted above (same publishing source/author), but should be verified, not assumed.
