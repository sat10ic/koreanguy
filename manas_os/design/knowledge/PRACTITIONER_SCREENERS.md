# PRACTITIONER_SCREENERS — extracted 2026-07-11 from corpus (Sonnet); feeds V4 SCANNERS design

Cross-checked against `manas_os/scanner/discovery.py` (9 archetypes: `ep_ipo`, `recent_listing`, `persistent_momentum`, `pullback_to_rising_ma`, `pullback_to_50ma`, `reversal`, `busted_reversal`, `strong_start_ready`, `d2_episodic`), `scanner/discovery_metrics.py`, `scanner/gates.py`, `engine/eod_detectors.py`, `regime/snapshot.py`, and ChartsMaze CSVs at `legacy/SwingEdge/data/chartsmaze/<date>/`.

**ChartsMaze template inventory found on disk** (deduped across dates): `Chhirag Template`, `Himanshu Template`, `Hiren Template`, `Nitin Template`, `Shashank Template` (trader-named screens) plus generic screens: Momentum Scanner, VCP, Tight Setup (Daily/Weekly), Inside Bar (Daily/Weekly), Shakeout (10/21/50/200 EMA), Flags & Pennants, Gap Filling, Horizontal Resistance, RS High Before Price High, Highest Volume/HVY, Volume Footprint, Volume Spike, IPO Setups, Earnings Gap Up, Positive Earnings Reaction, Episodic Pivot, Order Wins, Bulk/Block/Insider Deals, ASM, Circuit Revision History, Sector Analytics (MA/Near-52w-High/RS), RRG (industry/stocks, daily/weekly/monthly), Market Breadth, Results Calendar, Shorting Scanner, Top Gainers, Past Winners/IPO Listings. These are the team's own ChartsMaze screener subscriptions — the corpus text does not explicitly cite ChartsMaze by name as a practitioner-described tool (see note at bottom).

---

## Table 1 — Manas Arora

| NAME | EXACT CRITERIA (verbatim) | WHEN | WHAT DONE WITH HITS | CITE | STATUS |
|---|---|---|---|---|---|
| **Screener.in NSE baseline scan** | "Market → Performance → 3 Months → **above 30%**... Exchange: **NSE only**... Average volume (30 days): **> 200,000 shares**" | Not stated explicitly; implied a standing/base universe refresh | Builds base candidate list for individual chart review (VCP quality, consolidation check) | ARORA_SHARDS_NUANCES.md, extract_ma_small.md:19-25 | **Absent** as a literal named query; universe filter has NSE-only (done) but no discrete "3m>30%, vol>200k" screen |
| **MarketSmith India "Ideal List" sector scan** | "Market Smith's 'Ideal List' → 'Market' view... 197 sector groups ranked weekly... Look for improving rank... Prioritize sectors with **5-10+ names** showing strength" | Weekly | Rank sectors; multi-name confirmation before drilling into individual stocks | extract_ma_large.md:217-233 | **Absent** — no MarketSmith integration or weekly sector-rank feature |
| **Liquidity Force (LF) jump screen** | "Liquidity force jumped from 34 to 250... Huge LF increase in last 10–15 days is a positive signal"; "5x-50x" jump = institutional interest | Recurring, applied to watchlist names | Prioritize/rank candidates by LF jump ratio | extract_ma_small.md:67, 86-88 | **Absent** — no Liquidity Force indicator anywhere in codebase |
| **VCP contraction visual scan** | "16% wide day → 4% wide day (60–70% drop in volatility)... contraction 8%→3.5%→tighter" | Routine chart review (nightly, implied) | Flag as high-probability breakout candidate | extract_ma_small.md:142-144 | **Partially implemented** — `range_contraction_flag()` / `_pullback_to_rising_ma` D3 gate capture ATR-based tightness, not the exact %-contraction sequence Arora describes |
| **10 & 20 MA undercut-and-recover screen** | "I only buy stocks which have recently gone below 10 and 20 [MA]... gone up and now making a base" | Recurring buy-universe filter | Weak-hands-shaken-out names get priority for entry | extract_ma_small.md:65-68, 77-79 | **Implemented** — `reversal` and `busted_reversal` archetypes encode undercut-recover demand-bar logic (K7/K10) |
| **Circuit-band upgrade tracker** | "Circuit changing from 5% to 10% or from 5% to 20% is bullish" (downgrade to 5% = drop) | Recurring check on watchlist names | Treat recent upgrade as a positive signal, boost priority | extract_ma_small.md:71-74 | **Absent** — circuit-tier exclusion (5%) exists in `gate_tradability`, but no upgrade-history tracker |
| **Relative-strength-during-falls screen** | "Stock was already leading the market BEFORE the gap down... angle of recovery much better than market" | During market weakness/corrections | Flag as leading-bounce candidate for next rally | extract_ma_small.md:232-238 | **Absent** as an explicit "RS on down-days" scan (general `rs_rating`/`RS_FLOOR` gate exists but not this specific during-fall read) |
| **Stopped-out separate watchlist** | "Put the stopped-out stock in a separate watch list and keep tracking it... Give priority over new names" | Ongoing, after every stop-out | Re-entry candidate, sometimes with larger size | extract_misc.md:235-242 | **Absent** — no persisted "stopped-out watchlist" feature found |
| **Sector rotation multi-name check** | "A sector with only 2 names... might be misleading... Prioritize sectors with 5-10+ names showing strength" | Ongoing | Weight sectors by breadth of names moving | extract_ma_large.md:217-227 | **Absent** as automated gate (sector_rs_quartile is Top-Down RS ranking, not multi-name-count confirmation) |

---

## Table 2 — TradeTM (Anuragg Venkatakrishnan / Chirag Kedia)

| NAME | EXACT CRITERIA (verbatim) | WHEN | WHAT DONE WITH HITS | CITE | STATUS |
|---|---|---|---|---|---|
| **Episodic Pivot (EP) scan** | ~30%+ YoY+QoQ EPS+sales growth (soft); results **post-market-close**; must **gap up/open strongly** next day (else invalidated); stock **neglected** pre-news (base/downtrend); mcap floor **~₹300cr**; skip if **gap+5-min-ORB > 12%** of prior close | Daily, **9:00–9:15am** sort by gap-up%, execute **9:07–9:30am** | Day-0: buy 5-min ORB high, stop=day low. If no Day-0 trigger (<45% do): pullback entry at 10/21 EMA | TRADETM_NUANCES.md B1/B2/B3, F11; SHARDS #9/#10/#11 | **Partially implemented** — `ep_ipo` archetype exists; the 12%-gap-cap (U5), post-close-only filter, and explicit EPS/sales growth% gate NOT confirmed present |
| **Peer-group EP tracking sheet** | 5-8 traders jointly maintain a Google Sheet of EPS/Sales QoQ/YoY post-results, sorted by gap-up% | Results season, daily 9:00-9:15am | Shared crowdsourced EP shortlist | TRADETM_NUANCES.md F10 | **Absent** — no shared/community tracker feature |
| **D2 (Day-2) scan** | Prior-day top-gainer list; Day-1 move **10%+ preferred** (20%-circuit-out-of-consolidation ideal); 4-6% Day-1 = weak; **first day of expansion** preferred over Day 2/3 | Daily, post-close review of yesterday's movers | 3 Day-2 sub-setups by close/open type: strong-close gap-up, "Wick Play," gap-down reversal | TRADETM_NUANCES.md B5/B5b/B5c | **Partially implemented** — `d2_episodic` archetype exists (M7 added 3-branch); exact 10%+ Day-1 threshold verify |
| **Persistent Momentum Scan** (AmiBroker Explore / TradingView Pine "Trend Persistence vs Moving Averages" — Nitin Ranjan's public script) | Close **>10EMA ≥20 days, >20EMA ≥30 days, >50EMA ≥50 days, >200EMA ≥150 days**; "decisive exit" buffer filters false breaches; then **sort by ADR descending** | Implied ongoing/weekly (working-professional workflow) | ADR-sorted list = daily trade universe; buy pullbacks to 20/50 EMA on it, don't chase breakouts | TRADETM_NUANCES_HINDI.md III1-III4 | **Implemented** — `persistency_counts()`/`is_persistent_momentum()` map directly; `adr20()` implemented; `persistent_momentum` archetype wires both |
| **"9-Million Volume" scan** (Pradeep Bonde-derived) | Referenced only as a concept — exact numeric criteria not captured in the extraction layer | Not stated | Not stated | TRADETM_NUANCES.md F22; source `9 mil vol scan_text.txt` | ⚠️ **Criteria not fully extracted from source** — flagged, not fabricated; STATUS unknown |
| **Live Market Scan / watchlist reprioritization session** | Reads participant commitment: does a gap-down/shakeout fail to flush committed holders? ("supply absorption is about... are non-committed buyers still there") | Routine, implied daily | Reprioritize existing watchlist, not build a new universe | TRADETM_NUANCES_COMPLETION.md F1-F5 | **Absent** — no gap-down-survival-rate / commitment-proxy metric |
| **Bench-strength watchlist check** | "I analyze my watchlist to gauge the bench strength. Are most stocks exhausted...?" | During market corrections | Judge whether downside risk is limited (regime read) | TRADETM_NUANCES.md C2 | **Absent** as an aggregated feature |
| **Sector rotation — Bottoms-Up** (preferred) vs Top-Down | Bottoms-Up: "identify stocks in your watchlist that are setting up... within a common sector" (author's preferred, more effort, more effective) | Ongoing | Theme-based watchlist construction | TRADETM_NUANCES.md G1 | **Absent** (Bottoms-Up clustering) / **Partial** (Top-Down: `sector_rs_quartile()`) |
| **IPO bar-by-bar reversal scan** | 3+ consecutive bars with **>50% overlap** of prior bar's range + contracting range + closes migrating inside = supply absorption; **J-curve**: 3+ down-consolidation bars then 1 smaller up-expansion bar | Applied to fresh IPO bases, ongoing | Flag as valid reversal-entry trigger (not a failure) | TRADETM_NUANCES_HINDI.md I1, I3, I6 | **Absent** — no overlap%/range-contraction-sequence detector; only generic `range_contraction_flag` |

---

## Table 3 — StocksGeeks (Umang)

| NAME | EXACT CRITERIA (verbatim) | WHEN | WHAT DONE WITH HITS | CITE | STATUS |
|---|---|---|---|---|---|
| **MBI (Market Breadth Indicator)** | 6-column composite; bands: **<50 red, 50–200 white** (whipsaw/sit-out), **200–400 green**, **400+** engage, **800+/1000+** very powerful (~90% hit rate); **Warning Day = 3+ of 6 columns red** → expect full-red within 1-2 days unless warning-day high breaks or burst stays 400+ | Daily / continuous EOD monitoring | Regime gate: engage vs sit out; MBI green triggers deployment 1-2 days **before** price confirms | STOCKGEEKS_NUANCES.md (MBI section) | **Implemented** — regime/snapshot.py `burst_ratio()`, `warning_day` (red_count≥3), color bands, r4p5, r10/r20/r50 — direct match |
| **Three-Condition Engagement Filter** | MBI green **AND** burst ratio **≥400** (4.5% band) **AND** "volume feedback working" | Daily, gates new entries | Score/rank candidates; scale sizing only when all 3 hold | STOCKGEEKS_NUANCES.md | **Partial** — MBI+burst exist; standalone "volume feedback" third gate not confirmed |
| **IPO First/Double Inside Bar scan** | Fresh-listed IPO near IPO-day level makes **first inside bar** = highest-prob trigger; **double inside bar = immediate trade** (80% of moves start next day) | Event-driven, as new IPOs list | Immediate execution, don't wait | STOCKGEEKS_NUANCES.md (IPO entry) | **Absent** — `recent_listing`/`ep_ipo` flag recent IPOs but no inside-bar-count detector |
| **Long-tail candle scan** | Tail length **>1.5x body**; entry 1% above wick low if MBI green | Recurring chart review of watchlist | Entry trigger tag | STOCKGEEKS_NUANCES.md (Long-Tail) | **Absent** — no wick/tail-ratio detector |
| **AOI (Area of Interest) / down-base scoring** | Current consolidation must sit **above** previous weekly consolidation (else = down-base, secondary tier); score by base-size, fall%, distance-from-high; **reject if >40-50% fall from recent high** | Base-analysis routine | Down-bases with gentle fall + close to high = tradeable; else reject | STOCKGEEKS_NUANCES.md (AOI) | **Partial** — `correction_depth_from_leg_high()`/`_180d_high()` echo the 40-50% rejection; "above previous weekly base" comparison missing |
| **Crow-Bar / Hook / Fast-Flag classification** | Post-breakout consolidation typed by price-vs-EMA relationship (price fails to catch EMA / EMA catches price / EMA lags price) — sizing scaled per type | Applied to already-identified candidates | Position-size scaling (conservative→aggressive) | STOCKGEEKS_NUANCES.md (Crow Bar) | **Absent** |
| **Multi-timeframe cascade (Daily > 75min > 15min)** | Daily-pattern legitimacy → 75min refinement → 15min timing; 15min entries without daily support fail 60%+ | Intraday execution | Reject 15min triggers lacking confirmation | STOCKGEEKS_NUANCES.md (Multi-TF) | **Absent** — EOD tool; behind Fyers intraday layer (#21) |
| **Sector rotation during crash** | Identify RS-holding sectors during a fall (e.g., pharma/FMCG in 2020) | During market corrections | Focus IPO/reversal entries in those sectors | STOCKGEEKS_NUANCES.md (Sector Rotation) | **Absent** — no crash-conditioned sector RS screen |
| **Strong-candle-in-crash flag** | Stock closes positive (or ≪ negative) on a day market falls 5-10% | On crash days | Flag as reversal-bounce leader | STOCKGEEKS_NUANCES.md (Sector & Theme Timing) | **Absent** |

---

## Third-party screeners explicitly cited in the corpus

- **Screener.in** (Arora) — "Market → Performance → 3 Months → above 30%," NSE-only, avg vol >200k/30d.
- **MarketSmith India** — used positively by Arora ("Ideal List" weekly sector rank); critiqued by TradeTM for miscategorized sector groupings.
- **AmiBroker** (Explore/AFL) and **TradingView Pine Screener** (Nitin Ranjan's public "Trend Persistence vs Moving Averages" script) — TradeTM's persistent-momentum tooling.
- **Chartink** — not cited anywhere in the 8 knowledge files (not fabricating a reference).
- **ChartsMaze** — not cited by name in the practitioner corpus; it is the team's own screener subscription on disk (inventory above).

---

## Gap list — ranked by how often the practitioner leans on the screen

1. **MBI (Umang)** — most load-bearing continuous gate; already well implemented (verify threshold parity 50/200/400/800).
2. **Persistent Momentum Scan (TradeTM)** — heavily emphasized; implemented — verify defaults (20/30/50/150) match code.
3. **EP scan + 12% gap/ORB cap (TradeTM)** — EPs "<10% of trades but >35% of 2-yr returns"; circuit-cap + post-close-only filters still gaps.
4. **10&20 MA undercut screen (Arora)** — covered by `reversal`/`busted_reversal`.
5. **Screener.in baseline scan (Arora)** — his literal default universe query; not a discrete screen yet.
6. **AOI/down-base scoring (Umang)** — "above previous weekly base" comparison missing.
7. **Sector rotation Bottoms-Up / multi-name confirmation (TradeTM + Arora)** — repeatedly stressed; largely absent.
8. **Liquidity Force jump screen (Arora)** — completely absent.
9. **IPO inside-bar / bar-by-bar reversal detectors (Umang + TradeTM)** — concrete codeable criteria; none implemented.
10. **Multi-timeframe intraday cascade (Umang)** — out of scope until intraday layer (#21).
11. **MarketSmith weekly sector-rank (Arora)**, **Stopped-out watchlist (Arora)** — lower citation frequency, absent.
