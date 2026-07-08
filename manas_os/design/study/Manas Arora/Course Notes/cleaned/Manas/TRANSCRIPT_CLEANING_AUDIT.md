# Transcript Cleaning Audit

Generated/updated: 2026-07-02

Audit utility:

```text
Manas Arora/Course Notes/audit_transcript_loop.py
```

Run with:

```powershell
python "Manas Arora\Course Notes\audit_transcript_loop.py"
```

Note: the audit script forces UTF-8 stdout on Windows so unresolved-warning symbols do not crash console output.

## Current state

### Cleaned master chapters present

- `cleaned/Chapter_1.md`
- `cleaned/Chapter_2.md`
- `cleaned/Chapter_3.md`
- `cleaned/Chapter_4.md`
- `cleaned/Chapter_5.md`
- `cleaned/Chapter_6.md`
- `cleaned/Chapter_7.md`
- `cleaned/Chapter_8.md`
- `cleaned/Chapter_9.md`
- `cleaned/Chapter_10.md`
- `cleaned/Chapter_11.md`
- `cleaned/Chapter_12.md`
- `cleaned/Chapter_13.md`
- `cleaned/Chapter_14.md`
- `cleaned/Chapter_15.md`
- `cleaned/Chapter_16.md`
- `cleaned/Strong_Start_Tightness_Study.md` — supplemental source from `ss.md`

### Missing cleaned master chapters

- None from the expected CH1 / CH8-CH11 / CH12-CH16 / SS set.

## Loop work completed in recent passes

### Chapter 11 cleaned

Created:

- `cleaned/Chapter_11.md`
- `cleaned/Chapter_11_correction_log.md`

Added Chapter 11 query rows to:

- `TRANSCRIPT_QUERIES.md`

Added recurring garble patterns to:

- `TRANSCRIPT_CLEANING_LOOP.md`

New patterns:

- `apply breaks/bakes` -> `apply brakes`.
- `droughts` -> `drawdowns`.
- `emergency stock` -> `emergency stop`.

Ch11 content preserved:

- drawdown definition as decline from prior account peak;
- no trader escapes drawdowns;
- seasoned trader controls drawdown while new trader keeps trading the same way;
- example rule: down **3%** from top -> reduce size by half;
- example account top **₹10 lakh**;
- example risk cut from **1%** per trade to **0.5%**;
- another **2%** loss / total **5%** drawdown -> close trades, suspend trading and take a break;
- note that **3%**, **5%**, **7%** are customizable thresholds, not universal laws;
- sit-out power and full disconnection for emotionally uncontrolled beginners;
- drawdown baggage example: trader exits a valid trade because account pain changes perception;
- reduce risk size, but do not change valid execution/management purely because account balance hurts;
- recovery is not the final goal; good trades and good money are the goal;
- comeback process: tiny size, let one or two trades work, then increase only if traction returns;
- avoid daily balance watching;
- weight-loss discipline analogy;
- self-coaching requirement;
- trailing example with 20-moving-average line, closing basis, emergency stop and **355** mechanical-exit level;
- final rule set: clear rules for reducing, stopping and making a comeback.

### Chapter 10 cleaned

Created:

- `cleaned/Chapter_10.md`
- `cleaned/Chapter_10_correction_log.md`

Added Chapter 10 query rows to:

- `TRANSCRIPT_QUERIES.md`

Added recurring garble patterns to:

- `TRANSCRIPT_CLEANING_LOOP.md`

New patterns:

- `log gains` -> `lock gains`.
- `majority` -> `maturity` in behavioural-edge context.
- `grade trade` -> `great trade`.

Ch10 content preserved:

- edge is not merely a fancy indicator, chart-reading skill or 20-DMA setup;
- technical setup is necessary but insufficient;
- finding stocks above the 20-DMA can be learned relatively quickly;
- the real edge is behaviour between good trades;
- waiting for the right market scenario is edge;
- reducing size in poor conditions is edge;
- riding/adding in good conditions is edge;
- newcomer books **5%** quickly; professional may add if the context supports it;
- maturity comes from journaling and studying one's own data;
- RK Forge / Ramkrishna Forgings? chart-of-the-week example did nothing, so stop + sizing discipline mattered;
- mistake sheet, **+1** / **-1**, FOMO/chasing/entry/exit review;
- one oversized mistake after **11** green months can end the year red;
- setup-finder who never traded due fear shows that execution is part of edge;
- three-month mistake-sheet test.

### Chapter 9 cleaned

Created:

- `cleaned/Chapter_9.md`
- `cleaned/Chapter_9_correction_log.md`

Added Chapter 9 query rows to:

- `TRANSCRIPT_QUERIES.md`

Added recurring garble patterns to:

- `TRANSCRIPT_CLEANING_LOOP.md`

New patterns:

- `reading log sheet` -> `trading log sheet`.
- `net pi value` -> `net P&L value`.
- `best to do ratio` -> `reward-to-risk ratio`.
- `market bread` -> `market breadth`.

Ch9 content preserved:

- follower's double-digit portfolio-increase-after-tracking hook;
- "what you measure gets monitored";
- journal purpose: track performance, mistakes, patterns, mental issues and method validity;
- review cadence of **20-30 days** or **10-15 trades**;
- same-day/evening logging rule;
- sample capital **₹10 lakh**;
- **I** / **D** intraday-delivery distinction;
- sample spreadsheet columns;
- sample buy value **₹1,71,000**, return **3.58%** on investment, about **0.62%** on account;
- buy near **₹49**, stop **₹48.70**, account risk **0.15%**, reward-to-risk **4:1**;
- split-exit logic for Bajaj and ITI, including **14.6%**, **17.2%** and **0.36%**;
- sample month: **18** original trades, **28** visible rows, **11** winners, **7** losers, **61%** win rate, **39%** losing rate;
- average winner **3.82%**, average loser **0.71%**;
- market-breadth link between big winners and shares above 20-DMA;
- average allocation **16.25%** and average risk **0.27%**;
- source truncation note because raw `CH 9.md` ends mid-sentence.

### Chapter 8 cleaned

Created:

- `cleaned/Chapter_8.md`
- `cleaned/Chapter_8_correction_log.md`

Added Chapter 8 query rows to:

- `TRANSCRIPT_QUERIES.md`

Added recurring garble patterns to:

- `TRANSCRIPT_CLEANING_LOOP.md`

New patterns:

- `write` -> `ride` in sell-side / holding-winners context.
- `trading stock` -> `trailing stop`.
- `BQN` -> `breakeven`.
- `pure line` -> `period line` / moving-average line.
- `MNC stop` -> `emergency stop`.
- `TDPOW / trading power systems` -> `TD Power Systems`.

Ch8 content preserved:

- sell-side difficulty and profit-side confusion;
- young market vs old/extended market distinction;
- 29 March clue and early leaders before the market fully moved;
- trailing-stop and breakeven logic;
- 20-DMA trail, closing basis and emergency stop;
- old-base / high-angle / high-volume / many-green-bars extension warnings;
- NCC, TD Power Systems, Olectra, MRPL and JBM Auto examples with dates/prices/percentages flagged where needed;
- late-market rule: sell quicker, tighten trails or take partial profits; in young markets, ride leaders.

### Supplemental Strong Start Tightness Study cleaned

Created:

- `cleaned/Strong_Start_Tightness_Study.md`
- `cleaned/Strong_Start_Tightness_Study_correction_log.md`

SS content preserved:

- member-submitted Strong Start wins as a less-biased sample;
- repeated finding that the previous day before many successful Strong Starts was extremely tight;
- running counts including **six out of seven**, **seven out of eight**, **nine out of ten**, **10 out of 11**, **11 out of 12**, **12 out of 13**, **12 out of 14**, **13 out of 15**, and **more than 80%**;
- DLF/fourth-green-day example preserved as a working but invalid process trade;
- no fixed numeric tightness threshold;
- "memorize the pictures" / compare the candle to that stock's own recent bars;
- volatility contraction -> expansion logic.

### Earlier cleaned chapters

The following were already cleaned before this pass and remain in the cleaned folder:

- `Chapter_1.md`
- `Chapter_2.md`
- `Chapter_3.md`
- `Chapter_4.md`
- `Chapter_5.md`
- `Chapter_6.md`
- `Chapter_7.md`
- `Chapter_12.md`
- `Chapter_13.md`
- `Chapter_14.md`
- `Chapter_15.md`
- `Chapter_16.md`

## Query/flag state

Latest audit shows:

- Query rows detected: **102**
- Live unresolved flag lines in cleaned files: **115**

Some flagged lines are duplicated because both part files and combined master chapters preserve the same unresolved item. This is expected until the user answers the query and the fix is retro-applied.

## Highest-priority next work

1. Build source ledgers for cleaned Ch8-Ch11 before drafting them into the overhaul book.
2. Resolve high-value query rows before book-level rewrite uses them as firm examples:
   - Ch8: 29 March portfolio-count phrase; Olectra/Elecon split; Sonata Software; JBM Auto; NCC share count; MRPL partial-sale percentage; Mazdock/RVNL examples; 1:50 R-multiple phrasing.
   - Ch9: exact tweet wording; same-day/evening log garble; Zerodha broker reference; original-risk mismatch; row-count mismatch; high-breadth number; 13 August garbled winner; truncated ending.
   - Ch10: breadth-scenario wording; >1,000 breadth reading; RK Forge identity; MiMo/club channel label.
   - Ch11: close-at-market phrase; market-doing-good-again phrase; rising-DMA wording; **355** price level.
   - Ch12: HEG split/raw-price pair; `matchdoc` / Mazdock; `BSC` / BSE Ltd; `train` / Rain; `120% allocation` likely `20% allocation`.
   - Ch13: dashboard tool name; high-breadth aggression sentence; 200 vs 1,200 stocks down; 7/4/2020 date; 90/97 low-breadth reading; 1,300-1,500 zone; dropped final relative-strength clause.
   - Ch14: `Hyreg`; MarketSmith MA timeframe; `PSB`; `CIGB Technologies`; market-cap cutoff; `Same end stocks`; dropped final entry clause.
   - Ch15: high-bid/buy-stop wording; missing book titles; "this is my moment" phrase.
   - Ch16: `weak hands`; prior trade name/ticker; `100R trade`; probable Globus; probable Marksans Pharma; probable Astra Microwave; unnamed first gap-breakout candidate; probable Arvind SmartSpaces; 10/20-DMA garble.
   - SS: Birlasoft/Chennai Petroleum/date pair; `Fosnema`; 30 August ticker; 8 November tickers; ICIL; probable Kellton Tech; `any calm`; DLF/fourth-green-day example.
3. Integrate SS as a supporting source for Strong Start / timing.
4. Draft/integrate Ch8-Ch16 into the overhaul book using ledgers and fidelity gates.
5. After user answers queries, retro-apply confirmed mappings across all cleaned files and update the loop ledger.

## Do not forget

Numbers, prices, percentages, dates and ticker identities cannot be silently fixed. Use query rows.

The retrofit rule is mandatory: later transcript context must be used to clean earlier garbles, and once resolved, the fix must be applied across the whole file.
