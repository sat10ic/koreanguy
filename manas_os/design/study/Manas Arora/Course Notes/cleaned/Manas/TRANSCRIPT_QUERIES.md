# Transcript Queries — Unresolved ASR Ambiguities

These are the ASR garbles that still need human confirmation. I have now added my **probable correction** wherever possible, including low-confidence guesses, so future cleaning/book-building passes have a working hypothesis without silently promoting guesses into facts.

Use the **Your correction** column to confirm, correct, or mark “unclear / leave unnamed.”

Legend: 🎯 = ticker/company/name · 🔢 = number/price garble · 📉 = unnamed example · 🧠 = semantic/phrase garble

Confidence labels:

- **High probable** = I would use this unless contradicted.
- **Medium probable** = likely, but needs your eye.
- **Low probable** = best guess only; do not use as confirmed in the book.
- **No safe fix** = I can suggest handling, but not a responsible identity.

---

## Ch 1 — Fear Management

| # | Type | Raw ASR | My probable correction / best guess | Context | Your correction |
|---|------|---------|-------------------------------------|---------|-----------------|
| 1-a | 🔢 | “I lost on 5% in the whole last one year” | **High probable:** “I lost only around 5% in the whole last one year.” | First-year survival example; Manas says staying roughly near capital is fine if learning is intact. | |
| 1-b | 🔢 | “my first 20-hour trade ever” | **High probable:** “my first 20R trade ever.” | Trading-performance context; followed by “two 20-hour trades.” “Hour” is likely ASR for “R.” | |
| 1-c | 🎯 | “GBMA” | **Low probable:** GMM Pfaudler / GMM? If not, leave as unnamed stock. | Same process-following example; stock up 80% by June 26; portfolio around 20% up in three months. | |
| 1-d | 🔢/🧠 | “I also entered in a first one person lower” | **High probable:** “I also entered first, 1% lower.” | Commenter entered before/lower, booked 3%; Manas bought at 80 and sold at 100. | |

---

## Ch 2.1 — Basic Foundation and Cycles

| # | Type | Raw ASR | My probable correction / best guess | Context | Your correction |
|---|------|---------|-------------------------------------|---------|-----------------|
| 2.1-a | 🔢 | “price dropped from 30 to 100 to 2900, almost a 10% drop” | **High probable:** ₹3,100 → ₹2,900. | Adani pullback after a 7-bar run; “30 to 100” is almost certainly “3100.” | |
| 2.1-b | 🔢 | “six, seven months, three months” | **High probable:** “six, seven bars, three bars.” | He is counting bars on an hourly/intraday frame, not months. | |
| 2.1-c | 📉 | “a very popular stock in London from 2018” | **Medium probable:** Linde India. “London” may be ASR for “Linde.” | 7-year Stage-1 base, then 150 → 5,000 in ~15–16 months / ~30x. | |

---

## Ch 2.2 — Magnitude and Market Cap

| # | Type | Raw ASR | My probable correction / best guess | Context | Your correction |
|---|------|---------|-------------------------------------|---------|-----------------|
| 2.2-a | 🎯 | “ETM” | **No safe fix:** keep as unnamed ETM-garbled small-cap unless chart/source confirms. Possible ticker-like garble, but no responsible single candidate. | Small-cap used to show 15–20% magnitude legs: 15%, 12%, 36%, 15%. | |
| 2.2-b | 🎯 | “JVMA” | **Medium probable:** JBM Auto (`JBMAUTO`). | Small-cap up 80–90% overall, in legs of 10%, 17%, 14%, 19%, 15%. “JVMA” sounds close to JBM/JBMAuto. | |
| 2.2-c | 🎯 | “Electra” | **High probable:** Elecon Engineering (`ELECON`). | Three-day runs of 23% and 41%; range 19–47% in 3 days. Recurs in Ch 3.1 and Ch 4.1. | |

Resolved in this file: “Ptm” → Paytm; “Tadani” → Adani.

---

## Ch 2.3 — Market Cycles and Base Counting

| # | Type | Raw ASR | My probable correction / best guess | Context | Your correction |
|---|------|---------|-------------------------------------|---------|-----------------|
| 2.3-a | 📉 | “very popular stock in London” | **Medium probable:** Linde India. “London” may again be ASR for “Linde.” | Second cycle example: ₹42 → ₹700 in two years. Same “London” pattern as 2.1-c. | |

Resolved: JSL and IDFC were already clean.

---

## Ch 3.1 / 3.2 — Screen Layout & Scanning

| # | Type | Raw ASR | My probable correction / best guess | Context | Your correction |
|---|------|---------|-------------------------------------|---------|-----------------|
| 3-a | 🎯 | “Altaibilla Capital” / “Alta...Capital” | **High probable:** Aditya Birla Capital (`ABCAPITAL`). | Appeared in the 52-week-high scan result list. “Altaibilla” is very likely ASR collapsing “Aditya Birla.” | |
| 3-b | 🎯 | “Kanaka Bank” | **Medium probable:** Karnataka Bank (`KTKBANK`). Alternate: Karur Vysya Bank. | Volume-breakout scan: bank up 9% on very high volume. “Kanaka” phonetically fits Karnataka better than Karur. | |
| 3-c | 🎯 | “ITT Cementation” | **High probable:** ITD Cementation (`ITDCEM`). | NSE-vs-BSE liquidity example: 780,000 shares on NSE vs 40,000 on BSE same day. | |

Resolved: “First Source Solution” → Firstsource Solutions; “VNL” → RVNL; “Electra” → Elecon ×2.

---

## Ch 4.1 / 4.2 — Market Environment

| # | Type | Raw ASR | My probable correction / best guess | Context | Your correction |
|---|------|---------|-------------------------------------|---------|-----------------|
| 4-a | 🎯 | “Argonin” | **Low probable:** Archean Chemical? If not, leave unnamed. | “Members bought this while indices were still falling” passage. No safe correction from transcript alone. | |
| 4-b | 🎯 | “Elektra” / “multiple in Elektra” | **High probable:** Elecon Engineering (`ELECON`). | One of the 6–7 names he added to aggressively in Feb–June 2023 alongside Zen Tech, NCC, Paytm. Same as 2.2-c. | |
| 4-c | 🎯 | “Jyoti” | **Medium probable:** Jyoti Resins (`JYOTIRES`). Alternate: Jyoti Structures. Not Jyoti CNC if the example is 2023, since Jyoti CNC listed later. | Named as a position that hit its stop ~4 days before an 8% correction, in the “Adani canary” section. | |

Resolved: “Zendtech” / “ZTEK” → Zen Technologies (`ZENTEC`); “NC” → NCC; “VNL” → RVNL.

---

## Ch 5.1 — The Continuation Setup

| # | Type | Raw ASR | My probable correction / best guess | Context | Your correction |
|---|------|---------|-------------------------------------|---------|-----------------|
| 5.1-a | 🎯 | “Trade 3” / ticker never clear | **High probable:** Kaynes Technology (`KAYNES`). | Bought 23 May at ₹682; 81% up from 3-month low; prior move 98% in 10 days; dead ~47 days; later +40% in 20 days; open at +41% at recording. This strongly resembles Kaynes around that period. | |
| 5.1-b | 🎯 | “Perla soft” / “Parle Soft” | **Low probable:** Saksoft? Alternate: leave unnamed ₹33.4 reversal example. | Reversal example: bought at ₹33.4; 31% up from 3-month low; 41% in 33 days; 5 red days; +6% in 12 days. “Soft” likely belongs to the real name, but not enough confidence. | |
| 5.1-c | 🔢 | “333” | **High probable:** 33.3. | Result figure next to ₹33.4 entry; likely decimal dropped. | |

Resolved / clean: Parag Milk ₹110, Paytm, MLPL, Amber ~₹2,049, Sonata Software ₹750.

---

## Ch 5.2 — Stock Selection and Watchlist

| # | Type | Raw ASR | My probable correction / best guess | Context | Your correction |
|---|------|---------|-------------------------------------|---------|-----------------|
| 5.2-a | 🎯 | “Boros sell” | **Medium probable:** Borosil Renewables. Alternate: Borosil Ltd. | Reversal candidate: 40% up, 4 red days together. “Boros sell” is likely ASR for Borosil. | |

Additional likely ticker normalisations from this chapter:

- **Kiloska** → **Kirloskar Oil Engines** is my best guess; alternates: Kirloskar Brothers / Kirloskar Ferrous.
- **JWL** → **Jupiter Wagons** is high probable.
- **TPL** → **Tamilnad Petroproducts** is medium probable, but needs confirmation.
- **Indian Mart** → **IndiaMART** is high probable.

---

## Ch 6 — When to Buy (Timing)

| # | Type | Raw ASR | My probable correction / best guess | Context | Your correction |
|---|------|---------|-------------------------------------|---------|-----------------|
| 6-a | 🎯 | “JK tire” | **High probable:** JK Tyre (`JKTYRE`). | Breakout-definition example: highest point ₹173, next box breakout above ₹208; dates 27 June / 28 April. | |
| 6-b | 🎯 | “BSC” trade, 2021 | **High probable:** BSE Ltd (`BSE`). | Bought 15 November 2021, half-percent stop, stock went +65%, “more than 100× the risk.” This matches how “BSC” would be heard for BSE. | |
| 6-c | 🎯 | “let’s call it ___” | **No safe fix:** likely intentionally unnamed chart example. Use as unnamed 22 June setup unless source/audio confirms. | 22 June evening setup: uptrend goes down, comes back, goes tight; entered via strong start or Busted. | |
| 6-d | 🔢/🧠 | “SSA should not breach the previous day’s close” | **High probable:** “the low should not breach the previous day’s close.” | Strong-start rule: next day’s low should not break previous close; ideally open = low. | |

---

## Ch 7 — Position Sizing

| # | Type | Raw ASR | My probable correction / best guess | Context | Your correction |
|---|------|---------|-------------------------------------|---------|-----------------|
| 7-a | 🔢 | “Start with 1” | **High probable:** start with **0.1% risk per trade**. | He then says not to start with 0.5%, implying a smaller beginner risk fraction. | |
| 7-b | 🎯 | “BSC” in illiquid micro-cap example | **High probable:** BSE, the exchange — “BSE-only stocks.” | “Very illiquid micro-cap BSC stocks are where 20% gap-downs happen.” Context is exchange/liquidity, not a ticker. | |

---

## Ch 8 — Ride or Sell

| # | Type | Raw ASR | My probable correction / best guess | Context | Your correction |
|---|------|---------|-------------------------------------|---------|-----------------|
| 8-a | 🧠/🎯 | `C295` / `C295 out of my portfolio, 56 names` | **No safe fix:** possible “new highs” / 52-week highs / portfolio-count phrase. | 29 March observation: several portfolio names were already making new highs before the market fully moved. | |
| 8-b | 🎯 | `Electra` / `Olectra` | **High probable for ₹682 example:** Olectra Greentech. Earlier “Electra” in other chapters may be Elecon, so confirm by chart. | Trade-management example bought around ₹682, sold 75% around 9:40 on 13 June. | |
| 8-c | 🎯 | `Solata software` | **High probable:** Sonata Software. | List of names working in young market with Zen Tech, Paytm, TD Power Systems, KPIT. | |
| 8-d | 🎯 | `GBMA` / `JBMA` | **Medium probable:** JBM Auto in some contexts, but not guaranteed. | Member-trade/leader references; JBM Auto is later explicit. | |
| 8-e | 🎯 | first long ride example / `intake trade` | **Medium probable:** Zen Technologies. | Example includes young breakout, 20-DMA trail, ₹340 sale, base-count reset; context resembles Zen Tech. | |
| 8-f | 🔢 | `sold 607` in MRPL | **Medium-high probable:** sold **60%** / possibly 60-70%. | MRPL bought ₹66.45; on 19 June after 22% in three days he took partial profit and kept remaining 40%. | |
| 8-g | 🔢 | NCC `closed 28` after 78,000 shares | **Medium probable:** closed 28,000 shares. | NCC position management: around seven positions / 78,000 shares; sold first on 3 May, more on 5 May, majority on 8 May. | |
| 8-h | 🎯 | `Masdoc` | **High probable:** Mazdock / Mazagon Dock. | Final-summary list of big movers needing good market weather, alongside JBM Auto and RVNL. | |
| 8-i | 🎯 | `RBNL` | **High probable:** RVNL. | Final-summary list of big movers needing good market weather. | |
| 8-j | 🔢/phrase | `1 is to 500` | **High probable:** 1:50 R-multiple discussion. | Same sentence says 1:50 and room for 15 mistakes/risks; raw likely garbled “1 is to 50.” | |

---

## Ch 9 — Journal

| # | Type | Raw ASR | My probable correction / best guess | Context | Your correction |
|---|------|---------|-------------------------------------|---------|-----------------|
| 9-a | 🧠 | `double-digit increasing portfolio in a month since I started tracking` | **High probable:** double-digit portfolio increase in a month after starting to track trades. | Follower tweet used to introduce journaling benefit; exact tweet wording unavailable. | |
| 9-b | 🧠 | `what's marked the role?` | **No safe fix:** likely means log the trade immediately / same evening as a rule. | Timing instruction: if not immediately, at least update journal in the evening before memory decays. | |
| 9-c | 🎯 | `zero` as broker reference | **High probable:** Zerodha. | Brokerage adjustment section: “if you're with zero...” likely broker name. Confirm before naming in final book. | |
| 9-d | 🔢 | original-risk mismatch: `0.21`, `0.15`, `1.15` | **Medium probable:** the manual original-risk cell should be 0.15%, not the displayed value. | Spreadsheet sample; number-sensitive and should be verified against video/sheet. | |
| 9-e | 🔢 | `25, 27 trades` vs later `28 trades` / entries | **Medium probable:** rough row-count examples; actual original-trade count remains 18. | Split exits create more rows than original trades. Final book should avoid treating row counts as precise if source conflicts. | |
| 9-f | 🔢 | `900,000` shares above 20-DMA | **No safe numeric fix:** likely 900 / high breadth reading, but confirm against sheet. | Market-breadth example for 4 August sample data; 900,000 listed shares is implausible. | |
| 9-g | 🎯 | `7% manure` | **No safe fix:** garbled stock/example name. | Second meaningful winner checked against 13 August market breadth. | |
| 9-h | 🧠 | raw transcript ends at `every month you can know where you` | **No safe fix:** source is truncated mid-sentence. | Missing final remarks need audio/video recovery if available. | |

---

## Ch 10 — Understanding Your Edge

| # | Type | Raw ASR | My probable correction / best guess | Context | Your correction |
|---|------|---------|-------------------------------------|---------|-----------------|
| 10-a | 🧠 | `This is the breath scenario` | **Medium probable:** market-breadth scenario. | He is discussing market environment and where easy money does/does not come. | |
| 10-b | 🔢/🧠 | `most of the stocks are above thousand` | **Medium probable:** breadth reading above 1,000 / many stocks above 20-DMA. | Good-condition example where 20-DMA setups are more likely to work and 20-40% moves come more easily. | |
| 10-c | 🎯 | `RKForge` | **High probable:** RK Forge / Ramkrishna Forgings (`RKFORGE`). | "Chart of the week" example that did nothing despite looking good. Confirm before final book table/use. | |
| 10-d | 🧠 | `memo, like on the club channel` | **Medium probable:** MiMo / members' club channel. | Where he shared the RK Forge chart of the week; not essential to trading logic. | |

---

## Ch 11 — Drawdowns

| # | Type | Raw ASR | My probable correction / best guess | Context | Your correction |
|---|------|---------|-------------------------------------|---------|-----------------|
| 11-a | 🧠 | `close that traded market` | **Medium probable:** close that trade at market. | Drawdown-baggage example where trader interferes and exits a valid trade. | |
| 11-b | 🧠 | `How do you make a comeback? And how do you know Mark's doing good again?` | **High probable:** "How do you know the market is doing good again?" | Comeback protocol: take small trades and increase only when one or two start working. | |
| 11-c | 🧠 | `rising DML` | **High probable:** rising DMA. | Trailing-stop lesson with 20-moving-average line and emergency stop. | |
| 11-d | 🔢 | `at 355` | **Medium probable:** 355 price level. | Example of mechanical 20-MA exit before the stock bounced; verify against chart/video before final table. | |

---

## Ch 12 — How Fast Can You Really Grow Your Account?

| # | Type | Raw ASR | My probable correction / best guess | Context | Your correction |
|---|------|---------|-------------------------------------|---------|-----------------|
| 12-a | 🔢 | HEG: “2072 all the way to 5000” and later “200 to 3000” | **Medium probable:** use **₹200 → ₹3,000** as the split-adjusted teaching move; preserve note that raw transcript also says 2072→5000. | Same HEG 2017–Jan 2018 example; both number pairs appear. The 200→3000 line better matches “more than 10 times.” | |
| 12-b | 🎯 | unnamed example after HEG | **No safe fix:** leave unnamed unless chart/source confirms. | Weekly-base example: 257→400 from Mar–Sep 2021, then 374→681 from Jan–Apr 2022. | |
| 12-c | 🎯 | unnamed 2014 winner | **No safe fix:** leave unnamed unless chart/source confirms. | Huge weekly breakout: ₹25→₹86 from Apr–Sep 2014. | |
| 12-d | 🎯 | “matchdoc” | **High probable:** Mazagon Dock Shipbuilders (`MAZDOCK`). | Recent winner: ₹300→₹900 from Aug 2022 to Nov 2022. “Matchdoc” sounds like Mazdock. | |
| 12-e | 🔢 | Rain: “more than a percent” | **High probable:** “more than 100%.” | Rain example: ₹58→₹122 from Jan–Mar 2017. The math supports >100%. | |
| 12-f | 🎯 | “BSC” | **High probable:** BSE Ltd (`BSE`). | Manas says he traded it: ₹200→₹470 Jun–Aug 2021, then another ~100% Sep–Dec 2021; later ₹205 cost and ₹200→₹400. Same likely identity as 6-b. | |
| 12-g | 🎯 | unnamed 2022 example | **No safe fix:** leave unnamed unless chart/source confirms. | Says even in 2022 some names rose while market was not; Oct/Nov 2021→Jan 2022, then ₹250→₹500 Jun–Aug. | |
| 12-h | 🔢/🧠 | “my cost is some down by points... four points overall... down by two points” | **Medium probable:** after selling half at ₹18 from a ₹12 entry, he is describing effective/psychological cost reduction, roughly “new cost around ₹10.” Do not present exact arithmetic as confirmed. | Mirza impact calculation; cleaned version preserves the concept but flags wording. | |
| 12-i | 🧠 | “the all is again I’m stopped out here” | **Medium probable:** “if it goes below / fails around the 20-DMA again, I am stopped out here.” | Mirza 20-DMA trailing explanation after a close below the 20-DMA and next-day bounce. Direction is important; confirm before final. | |
| 12-j | 🎯 | “train” | **Medium probable:** Rain Industries (`RAIN`). | Portfolio-impact calculation with cup-and-handle/VCP, average cost around ₹60, 89% in 33 trading days, later 93% move. Could be the same Rain example from earlier. | |
| 12-k | 🔢 | “120 percent allocation” | **High probable:** **20% allocation**. | 93% stock move gives ~18% portfolio return, which mathematically implies ~20% allocation, not 120%. | |

---

## Ch 13 — Market Breadth

| # | Type | Raw ASR | My probable correction / best guess | Context | Your correction |
|---|------|---------|-------------------------------------|---------|-----------------|
| 13-a | 🧠 | “trading also” / “charting also” has a similar market breadth dashboard | **Medium probable:** TradingView / Chartink. I slightly prefer Chartink for free breadth dashboards, but TradingView is also mentioned nearby. | Manas says the user can create/run market-breadth dashboards/screeners instead of using his exact sheet. | |
| 13-b | 🧠 | “If you are 1500, I’m very careful, I’m aggressively trading my trades” | **High probable:** “If we are near 1500, I become very careful; I am not aggressively trading.” | Meaning inversion risk: high breadth extreme should make him defensive, not aggressive. | |
| 13-c | 🔢 | “After 200 stocks down, 740 were up” | **Medium probable:** “After 1,200 stocks down, 740 were up.” | Previous sentence says around 1,200 stocks were down; next day was a super bounce. Raw says 200, so confirm. | |
| 13-d | 🔢 | “7th, 4th, 2020” | **High probable:** 7 April 2020. | 127 stocks up 20% in five days; index had four green days in a row; likely Indian date format. | |
| 13-e | 🔢 | “The 97 will not really stay for long” | **Medium probable:** low breadth reading around 90/97 does not stay long. | He is contrasting fast bottoms with extended high-breadth tops. Earlier low number was 90. | |
| 13-f | 🔢/phrase | “13 to 1500 trades markets have stayed for days” | **High probable:** “1,300 to 1,500 breadth zone; markets have stayed there for days.” | Explaining that high breadth can persist, so do not close everything on first 1,300/1,400 reading. | |
| 13-g | 🧠 | Transcript ends: “Find stocks with relative...” | **High probable:** “Find stocks with relative strength.” | End-of-transcript dropped clause after “focus on indices/sectors.” | |

---

## Ch 14 — Outperforming Sectors

| # | Type | Raw ASR | My probable correction / best guess | Context | Your correction |
|---|------|---------|-------------------------------------|---------|-----------------|
| 14-a | 🎯 | `Hyreg` in consumer electronics examples with Dixon and Orient Electric | **No safe fix:** possible Havells / HIRECT / another consumer-electronics stock. | 2019 tweet: three consumer-electronics stocks broke out of long-term bases around same time. | |
| 14-b | 🧠 | `10 moving average line` on MarketSmith group chart | **Medium probable:** 10-week moving average. | Group chart / MarketSmith weekly-style group view; price below MA means group trend not very strong. | |
| 14-c | 🎯 | `PSB very low priced` | **Medium probable:** Punjab & Sind Bank, or generic PSU bank/PSB reference. | Bank group scan; low-priced bank skipped. | |
| 14-d | 🎯 | `CIGB technologies` | **High probable:** Cigniti Technologies. | IT group relative-strength examples alongside Sonata, Cyient, Zensar, KPIT, Saksoft, R Systems. | |
| 14-e | 🔢/phrase | `one lap market cap` | **Medium probable:** “one lakh crore market cap” or a market-cap sorting depth; exact unit unclear. | He says he keeps going down the group list by market cap and selecting names. | |
| 14-f | 🎯 | `Same end stocks` | **Medium probable:** cement stocks. | Current strong groups listed as IT, construction, oil; phrase sounds like “cement.” | |
| 14-g | 🧠 | transcript ends: `then you select proper...` | **High probable:** “then you select proper entry.” | Final sentence after selecting best RS names from strong groups; entry is said to be a separate topic. | |

---

## Ch 15 — Daily Routine and Final Advice

| # | Type | Raw ASR | My probable correction / best guess | Context | Your correction |
|---|------|---------|-------------------------------------|---------|-----------------|
| 15-a | 🧠 | `place the high bit above the high of the previous day` | **High probable:** “place the bid / buy-stop above the high of the previous day.” | Morning strong-start execution; exact order type/wording should be confirmed before book-level rules. | |
| 15-b | 🎯 | recommended books visible on screen but not named in transcript | **No safe fix:** need screenshot/video context; leave as unnamed books unless identified. | He says “these are the books I recommend,” but ASR contains no titles. One mindset book reframes losses as cost of doing business. | |
| 15-c | 🧠 | `this is my moment` in system-evolution section | **Low probable:** “this is my method” / “this is my zone.” | He is saying that after studying your own data, you know what works for you and what you are comfortable with. | |

---

## Ch 16 — Live Watchlist Construction

| # | Type | Raw ASR | My probable correction / best guess | Context | Your correction |
|---|------|---------|-------------------------------------|---------|-----------------|
| 16-a | 🧠 | `not a lot of weekends got out here` | **High probable:** “not a lot of weak hands got out here.” | Weekly has barely rested after a run; point is that shallow profit booking has not flushed sellers/weak holders. | |
| 16-b | 🎯 | `prequired trade` | **No safe fix:** likely a prior trade/ticker mentioned in another video; leave as unresolved unless video confirms. | Used as comparison for a young trend where position was created early. | |
| 16-c | 🔢/🧠 | `100 hour trade` | **High probable:** “100R trade.” | He says you must buy out of a U-shaped base near the start to get this kind of big risk-multiple trade. Unit matters, so confirm before formal book use. | |
| 16-d | 🎯 | `no globus also` | **Medium probable:** Globus / Globus Spirits. | Choppy candidate with no clean trend, mediocre force, and poor 10/20-DMA surfing. | |
| 16-e | 🎯 | `muck son farmer` | **High probable:** Marksans Pharma. | Rejected after acceleration from roughly 22-degree to 77-degree moving-average angle; likely pharma ticker garble. | |
| 16-f | 🎯 | `astra micro` / `extra micro` | **High probable:** Astra Microwave Products. | Candidate with ~42% force, linear 10/20-DMA behaviour, fresh weekly, selected as second name. | |
| 16-g | 🎯 | first selected huge-gap base-breakout candidate; raw later mentions `skipper` nearby | **No safe fix:** may be Skipper or a similar gap-breakout name; do not assign ticker without video/chart confirmation. | Selected first: huge base breakout with gap, ~70% force, multiple purple dots, weekly ~12-15% away from average. | |
| 16-h | 🎯 | `urban smart places` | **High probable:** Arvind SmartSpaces. | Rejected because force is only ~14%. | |
| 16-i | 🧠 | `not really surfing the internet 20 a lot` | **High probable:** “not really surfing the 10-DMA and 20-DMA well.” | Choppy-stock rejection near the end; same recurring ASR garble as 10/20-DMA phrases elsewhere. | |

---

## SS — Strong Start Tightness Study

| # | Type | Raw ASR | My probable correction / best guess | Context | Your correction |
|---|------|---------|-------------------------------------|---------|-----------------|
| SS-a | 🎯 | `somebody would be sold on 12th June` / repeated garbled list opening | **High probable:** Birlasoft on 12 June. | Member-submitted Strong Start wins list; later raw clearly says “Birla Soft, on 12th June.” | |
| SS-b | 🎯/🔢 | `watching a petron 17th August/October` | **Medium-high probable:** Chennai Petroleum on 17 October. | Same submitted-winners list; date appears garbled/inconsistent in overlap. Confirm before book example table. | |
| SS-c | 🎯 | `Fosnema` | **No safe fix.** | Example Manas says he would not have taken / would discuss as problematic or invalid. | |
| SS-d | 🎯 | `it gone on 30th August` | **No safe fix.** | Submitted Strong Start winner list; ticker unclear. | |
| SS-e | 🎯 | `it cost on 8th November` | **No safe fix.** | Submitted Strong Start winner list; ticker unclear. | |
| SS-f | 🎯 | `Ghibli on 8th November` | **No safe fix.** | Submitted Strong Start winner list; ticker unclear. | |
| SS-g | 🎯 | `ICIL` | **Medium probable:** ICIL as heard, but confirm exact listed ticker. | Submitted Strong Start winner list. | |
| SS-h | 🎯 | `back to the Keltan` | **Medium-high probable:** Kellton Tech. | Submitted Strong Start winner list; acoustic fit but needs chart/thread confirmation. | |
| SS-i | 🎯 | `any calm` | **No safe fix.** | Later tight-day example. Ticker unclear. | |
| SS-j | 🎯 | DLF / fourth-green-day invalid Strong Start example | **Medium-high probable:** DLF, but confirm. | Worked Strong Start but invalid for Manas’s process because entry came on the fourth green day. | |

---

## Semantic / context errors

| # | Chapter | Raw phrase | My probable correction / best guess | Context | Your correction |
|---|---------|------------|-------------------------------------|---------|-----------------|
| S-1 | Ch 3 | scan named “Rising Goals” | **Medium probable:** “Rising Stars.” Alternate: could be Manas’s own Hindi/English scan label. | Name of volume-breakout scan / Scan 3. | |
| S-2 | Ch 5 | “no focal volume” | **Medium probable:** “no follow-up volume” or “no notable volume.” I slightly prefer **follow-up volume** if he is discussing whether the move has continuation confirmation. | Describing purple-dot / high relative-volume candle. | |

---

## Fixes already applied

These were high-confidence acoustic errors already corrected inline in the cleaned masters:

- **Ch 4:** “tangle breakout” → **triangle breakout**.
- **Ch 6:** “7–8 games ready for tomorrow” → **7–8 names**.
- **Ch 2:** “a big green bus” → **a big green bar**.
- **Ch 12:** “write these moves” / “writing the position” → **ride these moves / riding the position**.
- **Ch 12:** “20 dmr / dm a” → **20-DMA**.
- **Ch 12:** “one or two games” → **one- or two-day gains**.
- **Ch 13:** repeated “bread” → **breadth** in market-breadth context.
- **Ch 13:** “Europe” → **here** in “go high from here.”
- **Ch 13:** “setters” → **sectors** in index/sector context.
- **Ch 13:** “basis old” → **bases old** in base-counting context.
- **Ch 14:** “good rates” → **good trades** in sector-RS context.
- **Ch 14:** “Bank of Oda” → **Bank of Baroda**.
- **Ch 14:** “20 DM / DML” → **20-DMA**.
- **Ch 14:** “low lows” → **lower lows**.
- **Ch 15:** “57 names” → **5–7 names** in daily shortlist context.
- **Ch 15:** “trailing stock” → **trailing stop**.
- **Ch 15:** “repeat terms” → **rupee terms**.
- **Ch 15:** “you will enjoy yourself” → **you will injure yourself** in progressive-overload analogy.
- **SS:** “grades” → **trades** in Strong Start sample context.
- **SS:** “Cool India” → **Coal India**.
- **SS:** “1020%” → **10–20%** in move-size context.
- **SS:** “six member / six on six” → **six out of six** in sample-count context.
- **Ch 8:** “write / writing a trade” → **ride / riding a trade** in sell-side context.
- **Ch 8:** “trading stock” → **trailing stop** in stop-management context.
- **Ch 8:** “BQN” → **breakeven** in stop-moving context.
- **Ch 8:** “TDPOW / trading power systems / ED Power System” → **TD Power Systems**.
- **Ch 8:** “20 pure line” → **20-period line / 20-DMA**.
- **Ch 8:** “MNC stop” → **emergency stop**.
- Ticker corrections already applied or strongly suspected:
  - Tadani → Adani
  - Ptm → Paytm
  - Zendtech / ZTEK → Zen Technologies (`ZENTEC`)
  - NC → NCC
  - VNL → RVNL
  - First Source Solution → Firstsource Solutions
  - Kanaka Bank → probably Karnataka Bank, but confirm
  - Electra / Elektra → probably Elecon Engineering, but confirm
  - CYE NT → probably Cyient
  - Zinsar Tech → probably Zensar Tech
  - KBIT → probably KPIT
  - Sacksoft → probably Saksoft
  - CIGB Technologies → probably Cigniti Technologies

---

## How to reply

Easiest: reply with row numbers and corrections, for example:

```text
2.2-b = JBM Auto
3-b = Karnataka Bank
5.1-a = Kaynes
6-b = BSE Ltd
12-d = Mazagon Dock
12-k = 20% allocation
```

Anything left blank stays flagged as unverified in cleaned transcripts and book drafts.
