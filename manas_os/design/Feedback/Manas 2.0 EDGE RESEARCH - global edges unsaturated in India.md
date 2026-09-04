# Manas 2.0 — Global Edges Unsaturated in India (Research Brief)

*A follow-up to "Manas 2.0 GLM response.md". Where the first brief diagnosed the existing tool and sequenced fixes to data you already render, this brief surveys **proven global techniques that remain under-exploited in the Indian NSE cash market** — and maps each to your actual data, your rules-first constraint, and an honest buildability verdict.*

**Filter applied to every candidate:**
1. **Proven globally in recent literature** (post-2020 replication or 2024-2025 working papers preferred).
2. **Unsaturated in India for a structural, durable reason** — not just "nobody bothered." The reason matters: an edge that's unused because the *data is hard* is more durable than one that's unused because it's new (newness decays).
3. **Buildable on Manas's data stack** under rules-first (no black-box scores) and manual-execution (no latency arbitrage). If it needs data you lack, that's flagged honestly, not hand-waved.

The single most important finding is at the end (§3, the ranking) — but read §1-2 first, because *why* each edge works in India is what tells you whether to trust it after you've built it.

---

## 1. The six edges, in detail

### Edge A — Post-Earnings-Announcement Drift (PEAD) in under-covered small-caps
*The anchor edge. Highest expected impact. Already half-built in your `earnings_power` detector.*

**The global evidence.** PEAD is one of the most replicated anomalies in finance — prices drift in the direction of an earnings surprise for 5-60 sessions after the announcement because information diffuses slowly. Recent 2024-2025 work confirms it persists despite academic publication (anomaly non-arbitrage-away), and the [SCIRP India study](https://www.scirp.org/journal/paperinformation?paperid=88060) and [University of New Haven work](https://digitalcommons.newhaven.edu/cgi/viewcontent.cgi?article=2897&context=americanbusinessreview) confirm PEAD is alive in the Indian market specifically.

**Why it's unsaturated in India (and will stay so).** Three structural moats:
1. **Retail-dominated market with slow diffusion.** Institutions can't deploy into ₹500-5000cr names fast enough to close the gap; retail processes results over days, not milliseconds.
2. **No consensus estimates for small/mid-caps.** This is the counterintuitive key: **your lack of estimates data *is* the signal.** If you don't have analyst forecasts, neither does the broad market — so the "surprise" embedded in a gap-up is genuinely novel information that hasn't been pre-priced. Large-cap PEAD is mostly arbed; small-cap PEAD is wide open *because* small caps are under-covered.
3. **Operator/pump noise in the small-cap space means most screens run away from it** — leaving the genuine fundamental drift names under-followed even by the screens that could find them.

**Mechanism (rules-first).** A name qualifies when ALL hold:
- `earnings_power` detector fires (30% QoQ+YoY EPS+sales + gap-up) — *you have this.*
- `500 ≤ market_cap_cr ≤ 8000` (the under-covered zone; >8000cr is too well-followed, <500cr is pump territory).
- Gap fills < 40% intraday (quality gap, not distribution).
- Delivery_z ≥ +1.0 on the gap day (sustained accumulation, not a quick flip).
- Not in the [pump-signature exclusion](#edge-c--max-effect--lottery-stock-exclusion-the-natural-pair-to-pead).

**Data mapping.** `daily_prices` (OHLCV, delivery_pct, prev_close) · `symbol_quality.{eps_yoy, eps_qoq, sales_yoy, market_cap_cr, asm_stage}` · sector RS from `sector_metrics`. Everything present.

**Explainability.** "EP drift candidate: gapped 6.2% on 30%+ EPS+sales growth, ₹2,100cr cap (under-covered), delivery 1.4σ above normal, gap held. Historical T+10 hit rate for this cell: 0.62 (n=47)."

**Validation.** This is the **single highest-value backtest you can run** on existing data. Bucket every historical `earnings_power` hit by market-cap decile; small-cap EP should show materially higher T+10 forward_r than large-cap EP. The `outcomes` table already computes forward returns. If the small-cap decile shows ≥2× the median forward_r of the large-cap decile, you have your anchor setup and the thesis is confirmed on *your* data.

**Buildability: BUILD NOW.** This is the one edge worth re-architecting the feed around. It is the single most important research bet in the whole roadmap.

---

### Edge B — Residual / Idiosyncratic Momentum
*The "cleaner momentum" edge. Replaces the noisy raw-RS rank with a signal that survives in stressed markets.*

**The global evidence.** [Blitz-Huij-Hanauer (2020) revisited in 2023-2024 work](https://alphaarchitect.com/swedroe-spotlight-enhancing-momentum-strategies-via-idiosyncratic-momentum/) shows that ranking stocks on **residual** momentum — past returns *after regressing out market, size, value, and sector exposures* — delivers comparable returns to conventional momentum with **much lower volatility and dramatically lower crash risk** (conventional momentum has the famous "momentum crash" problem; residual momentum largely solves it). [Hanauer's comparative work](http://wp.lancs.ac.uk/mhf2019/files/2019/09/MHF-2019-076-Matthias-Hanauer.pdf) and [CXO Advisory's summary](https://www.cxoadvisory.com/momentum-investing/idiosyncratic-pure-or-residual-momentum-as-a-stock-return-predictor/) both find ~1.39% gross monthly with superior Sharpe. The [SSRN India paper "What Drives Short-Term Stock Returns in India?"](https://papers.ssrn.com/sol3/Delivery.cfm/6951339.pdf?abstractid=6951339) confirms momentum works in India (small-cap 0.903% vs large-cap 0.782%).

**Why it's unsaturated in India.** Every free Indian tool ranks on raw price momentum or absolute RS (Chartink, Screener.in, ChartsMaze itself). **None decompose momentum into "the part explained by the market/sector" vs "the part specific to this stock."** During sector rotations (which India does aggressively — pharma → banks → IT → PSU → caps), raw-RS leaders are often just *sector beta*, not stock-specific alpha. Residual momentum strips that. It's unsaturated because it requires a factor regression, which retail tools don't bother with — and it stays unsaturated because it's conceptually harder to explain, so the copycats won't follow quickly.

**Mechanism (rules-first).** For each candidate, compute:
1. A simple sector-relative return: `stock_63d_return − sector_index_63d_return` (the sector-decomposed version — simpler than a full Fama-French regression, and explains ~70% of what the full factor model captures, per the EFMA lead-lag work).
2. Use this **sector-adjusted momentum** as the tiebreak rank among gate-qualifiers, instead of the raw RS rating.

**Data mapping.** `daily_prices` for stock returns · `sector_index_prices` (already ingested — confirmed in `api/app.py`'s `_index_returns`) · `sector_metrics.rs_score`. The benchmark series exists. You're not building a new factor library — you're doing one subtraction.

**Explainability.** "RS rank 88, but +6.2% of that is just the pharma sector lifting all boats; sector-adjusted RS is 71. Stock-specific momentum is moderate, not strong." This *is* the no-black-box version of the edge — it decomposes the existing number into "sector" vs "stock."

**Validation.** Re-rank the last 18 months of candidates by raw RS vs sector-adjusted RS. The hypothesis: the sector-adjusted rank predicts T+10 forward_r better in rotation regimes (when the top-quartile sector is *changing*). Metric: forward_r spread between top-quintile and bottom-quintile names, raw vs adjusted.

**Buildability: BUILD NOW (with a caveat).** The caveat: this is the one edge where a "simpler proxy" (sector-relative return) genuinely captures most of the academic effect, because India's dominant factor structure *is* sector (not size/value). Don't over-engineer a five-factor model; one subtraction gets you 70% of the way. The full factor version is [available if you want it](https://repositorio.ucp.pt/bitstreams/185837aa-e37e-433f-ac1a-0d5d79027b8f/download), but it's diminishing returns for the extra complexity.

---

### Edge C — MAX effect / lottery-stock EXCLUSION (the natural pair to PEAD)
*An exclusion edge. Free alpha from refusing the names retail piles into.*

**The global evidence.** The [Bali-Cakici-Whitelaw MAX effect](https://www.tandfonline.com/doi/full/10.1080/1331677X.2021.1965000) and its 2024-2025 replications — notably the [NYU Shanghai thesis on China's A-shares (2025)](https://cdn.shanghai.nyu.edu/sites/default/files/honorsthesis2025_zijin_su.pdf) and [University of Vaasa work](https://osuva.uwasa.fi/server/api/core/bitstreams/4daceef9-5eb7-4700-9201-1ab2e1c46832/content) — find that stocks with the **highest maximum daily return in the prior month** (the "lottery-like" names) **systematically underperform** subsequently. This is the skewness-preference anomaly: retail overpays for the small chance of a moonshot, and those names mean-revert. [Alpha Architect's review](https://alphaarchitect.com/lottery-preferences-and-anomalies/) summarizes 16 lottery-preference measures; MAX is the simplest and most robust.

**Why it's unsaturated in India (and brutally so).** India is a **lottery-preference market on steroids** — retail chases penny stocks, operator-driven circuit hits, and "10x stories." Chartink/TradingView screens *rank these names highly* (top-gainers, momentum). **Every free tool points retail AT the high-MAX names; the edge is in pointing away from them.** The [EFMA 2025 MAX CAPM paper](http://www.efmaefm.org/0EFMAMEETINGS/EFMA%2520ANNUAL%2520MEETINGS/2025-Greece/papers/MAX_CAPM.pdf) formalizes why this is structurally durable in retail-heavy markets: it's a preference, not a mistake the average participant is incentivized to arbitrage.

**Mechanism (rules-first).** Hard exclusion gate:
- Compute `MAX1` = max daily return over the trailing 20 sessions.
- Compute `MAX5` = mean of the top-5 daily returns over trailing 60 sessions.
- **Exclude** if `MAX1 ≥ 18%` AND `market_cap_cr ≤ 3000` (small-cap lottery name) — the pump-signature.
- **Flag (don't exclude)** if `MAX5 / AVG_daily_return ≥ 6` (skewed return distribution = lottery preference) — show a red "lottery-profile" chip, let the user see it.

**Data mapping.** `daily_prices.close` over 20-60 sessions. Trivial — it's a `max()` and `mean()`.

**Explainability.** "Excluded — lottery profile: largest single-day move was +22% on [date], small-cap, classic operator-driven circuit. These names historically underperform over the next month. This is the feed refusing a trap, not missing a winner." The chip *teaches the user* why free sites are pointing them here and you're not.

**Validation.** Backtest: take every historical candidate, split by MAX1 (≥18% vs <18%) within the small-cap cohort. The high-MAX bucket should show *negative* median T+20 forward_r. If confirmed (it will be — this is one of the most robust findings in the literature), this is free exclusion alpha.

**Buildability: BUILD NOW.** This is the cheapest edge in the entire brief (a few lines of SQL/Python) and it directly attacks your pump-signature problem from the first brief. Pair it with PEAD — PEAD says yes to drift names, MAX says no to lottery names, and together they cleanly separate the two populations that today get muddled into one 80-card feed.

---

### Edge D — Net Insider Buying (opportunistic, not routine)
*A "follow the informed money" edge. Uses the un-ingested ChartsMaze insider feed.*

**The global evidence.** [Cohen, Malloy & Pomorski (2012)](https://www.nber.org/system/files/working_papers/w6656/w6656.pdf) is the key paper: **routine** insider trades (planned 10b5-1 sales, regular vesting) are uninformative, but **opportunistic** open-market purchases strongly predict positive future returns — and the effect persists post-Sarbanes-Oxley ([ScienceDirect 2024](https://www.sciencedirect.com/science/article/pii/S1544612324015435)). [2iQ Research's review](https://www.2iqresearch.com/blog/profiting-from-insider-transactions-a-review-of-the-academic-research) covers the applied literature; the [SMU paper](https://ink.library.smu.edu.sg/context/lkcsb_research/article/7800/viewcontent/BSZ_2022EFA.pdf) shows retail mimicking of insider buys aids price discovery. The [RePEc 2023 work](https://ideas.repec.org/a/kap/rqfnac/v60y2023i4d10.1007_s11156-023-01142-7.html) shows insider buying *before buyback announcements* is an especially strong combined signal.

**Why it's unsaturated in India.** SEBI requires insider-trade disclosures (the equivalent of Form 4), and ChartsMaze captures them — but **no retail tool ingests, cleans, and ranks on them.** Trendlyne shows the raw data; nobody turns "cluster of insider buys in the last 30 days at a small-cap near a base" into a setup. The information is public, free, and actionable — it's just plumbing that nobody has done for the retail single-user. The reason it stays unsaturated is the data is messy (name matching, filtering routine vs opportunistic, excluding promoter pledging) — exactly the kind of hard-cleaning work that repels copycats.

**Mechanism (rules-first).**
- Ingest the ChartsMaze insider feed (on-disk, un-ingested per STATE_OF_TOOL §1).
- Compute `insider_net_buy_30d` = sum of open-market *purchases* − *sales* by management/promoters (exclude routine ESOP/vesting patterns) over trailing 30 sessions.
- **Boost** (chip + tiebreak weight) when `insider_net_buy_30d > 0` AND ≥2 distinct insiders buying (a cluster, not one person).
- **Exclude** when there's heavy insider *selling* into a price rise (the inverse — informed distribution).

**Data mapping.** ChartsMaze insider-disclosure feed (on-disk) → new `insider_trades` table. Needs the cleaning step (the hard part).

**Explainability.** "Insider cluster: 3 promoters/management bought ₹4.2cr open-market in the last 22 sessions at an avg price of ₹285 (current ₹292). Insider buying historically precedes positive drift — these are the people who know."

**Validation.** Backtest the cleaned insider-buy signal: do names with net insider buying ≥ ₹X over 30 sessions outperform sector-matched controls over T+20/T+40? Start with a loose threshold and tighten. The Indian dataset will be smaller than the US studies, so require n-counts on every claim.

**Buildability: BUILD AFTER INGESTING THE FEED (medium effort).** The edge is real and the data is on disk; the work is the cleaning pipeline (dedupe, name normalization, routine-vs-opportunistic classification). This is genuinely additive — it's a signal nobody else has productized for retail India.

---

### Edge E — FII/DII flow as a regime governor (India-specific smart-money overlay)
*India's unique, free, daily "smart money" signal — used as a regime input, not per-stock.*

**The global evidence.** Institutional-flow data as a timing/regime signal is well-established globally. India's specific version — **FII (foreign) vs DII (domestic) net cash flow**, published daily by [NSE](https://www.nseindia.com/reports/fii-dii) — is structurally unique: most markets don't publish clean daily institutional flow at the cash-segment level. The academic and practitioner consensus ([Trendlyne](https://trendlyne.com/macro-data/fii-dii/latest/cash-pastmonth/), [Sensibull](https://web.sensibull.com/fii-dii-data)) is that sustained FII selling is a risk-off tell.

**Why it's unsaturated in India.** Everyone *looks* at FII/DII numbers, but almost nobody **quantifies them as a regime input** with thresholds and historical baselines. It's gut-feel commentary on TV, not a structured rule. The edge is in formalizing it: "FII net sell > ₹3,000cr for 3 consecutive sessions → suppress size one band" is a rule, not an opinion. Free sites show the number; nobody routes it into a posture governor.

**Mechanism (rules-first).** Two new regime inputs:
1. **FII cumulative flow, 5-session z-score.** `z = (sum_5d_FII_net − mean_60d) / std_60d`. Sustained negative z (< −1.5) → risk-off; sustained positive z (> +1.5) → risk-on tailwind.
2. **FII-DII divergence.** When FIIs sell heavily *and* DIIs buy heavily (the classic Indian standoff), it's neutral-to-cautious; when both sell, it's unambiguous risk-off.

**Data mapping.** New free source: scrape/download the [NSE FII/DII daily report](https://www.nseindia.com/reports/fii-dii) into a `institutional_flow` table (one row/day: fii_net_cr, dii_net_cr). ~30 lines of pipeline.

**Explainability.** "Regime overlay: FII cash flow is −2.1σ below its 60-day norm over the last 5 sessions (−₹4,800cr net sell). Historically, this posture precedes weak T+5 index returns 68% of the time. Size cap suppressed one band."

**Validation.** Walk-forward: bucket the last 18 months of trading days by FII 5d-z-score; do low-z days show lower median Nifty T+5 returns? This is directly backtestable once the flow table exists.

**Buildability: BUILD NOW (cheap, free data).** A small pipeline + two derived regime inputs. It plugs straight into the `regime.governor()` function from the first brief. The highest "edge per line of code" after MAX-exclusion.

---

### Edge F — 52-Week-High nearness (George-Hwang) as the *anti*-chase gate
*A classic that's especially potent in India because retail fixates on the LOW, not the high.*

**The global evidence.** [George & Hwang (2004)](https://www.bauer.uh.edu/tgeorge/papers/gh4-paper.pdf) is one of the most cited momentum papers ever: **nearness to the 52-week high** predicts future returns *better than past returns themselves*. The mechanism is anchoring/underreaction — investors anchor on the high, treat a name near it as "expensive," and underreact to positive news, leaving drift. [2021/2023/2025 follow-ups](https://www.sciencedirect.com/science/article/abs/pii/S1544612321004256) confirm it persists; [Lasfer (2023)](https://onlinelibrary.wiley.com/doi/10.1111/fire.12371) shows insiders exploit the same bias.

**Why it's unsaturated in India.** Indian retail culture is **anchored to the 52-week LOW** — the "bargain / available at discount" frame dominates TV, broker reports, and screeners. The nearness-to-high signal is almost unused domestically. There's also a clean *dual* use for you: (1) as an **entry-quality gate** (a base breakout near the 52w high is high-conviction; a "breakout" 40% below the high is just recovering), and (2) as an **anti-chase gate** (a name 5% off its high after a vertical run is the *sell*, not the buy).

**Mechanism (rules-first).**
- Compute `nearness_high = close / max(high, 252d)`.
- **Entry gate:** setup must have `nearness_high ≥ 0.85` (real base breakout, not a recovery rally).
- **Anti-chase gate:** flag if `nearness_high ≥ 0.97` AND rvol declining AND `dist_from_21ema > 8%` (the parabolic top, not an entry).

**Data mapping.** `daily_prices.high` over 252 sessions. One query.

**Explainability.** "Near 52w high: 0.94 (₹292 vs high ₹310). This is a genuine base breakout, not a recovery rally — high-conviction entry context." Or the inverse: "0.98 — parabolic, 9% above 21EMA with declining volume. This is where you sell, not buy."

**Validation.** Bucket historical base-breakouts by nearness-high; the ≥0.85 cohort should show materially higher T+10 hit rate than the <0.70 cohort.

**Buildability: BUILD NOW.** Trivial computation, strong global evidence, clean dual use (entry gate + anti-chase gate). Pairs perfectly with Edge B (residual momentum) — nearness-high says "where in its range," sector-adjusted momentum says "stock-specific strength."

---

## 2. Edges that are real but need data you don't have (flagged honestly)

These are proven globally but you can't build them today without a new data source. Listed so you can decide whether to acquire the data, not so you can build them on a wish.

| Edge | Why it works | What you lack | Honest verdict |
|---|---|---|---|
| **Analyst recommendation / price-target revisions drift** ([McLean 2024](https://haslam.utk.edu/wp-content/uploads/2022/09/Retail-Investors-and-Analysts-McLean-1.pdf), [ScienceDirect 2025](https://www.sciencedirect.com/science/article/pii/S1059056025009931)) | Retail underreacts to revision *velocity*, not levels | Consensus estimates + revision history (Trendlyne/Screener.in paid, or a scrape) | **Acquire data first.** Strong edge, especially in under-covered names where a single initiation moves the price. |
| **Earnings-volatility risk premium (event straddle)** | Implied vol systematically overestimates realized vol around earnings | **Options data** (you explicitly lack this) | Defer until/unless options data is sourced. |
| **Accrual quality / decelerating-revenue short** | High-accrual / decelerating names underperform | Full balance-sheet fundamentals (you lack) | Defer. |
| **Closing-auction imbalance** | Order-flow imbalance at the close predicts next-open | Historical auction-imbalance data (Fyers may have live; no history) | Premature; unvalidatable today. |
| **Lead-lag (large→small within sector)** | Sector leaders move before followers | Sector classification (have it) + clean within-sector return series | **Buildable but lower priority** — the [EFMA work](https://www.efmaefm.org/0EFMAMEETINGS/EFMA%2520ANNUAL%2520MEETINGS/2021-Leeds/papers/EFMA%25202021_stage-2049_question-Full%2520Paper_id-411.pdf) shows it's distinct from simple size autocorrelation but the effect size is smaller than A-F. |

---

## 3. The ranking (opinionated, by edge-density × buildability)

This integrates with the first brief's roadmap (#1-12). The new edges slot in as follows — ordered by how much they move the needle relative to effort:

| Rank | Edge | Type | Why this rank | Effort | New task |
|---|---|---|---|---|---|
| **1** | **PEAD in under-covered small-caps (A)** | Inclusion (anchor) | The single highest-impact edge; half-built already; structurally moated in India | M | **#13** |
| **2** | **MAX-effect / lottery-stock exclusion (C)** | Exclusion | Cheapest edge in the brief (a `max()`); directly kills the pump problem; pairs with PEAD | S | **#14** |
| **3** | **52w-high nearness as entry + anti-chase gate (F)** | Gate | Trivial to compute; dual use; classic robust anomaly; culturally underused in India | S | **#15** |
| **4** | **FII/DII flow as regime governor (E)** | Context | Free data; plugs into the regime governor from brief #1; India-specific structural edge | S | **#16** |
| **5** | **Sector-adjusted (residual-lite) momentum (B)** | Rank refinement | Replaces raw-RS with a cleaner signal; one subtraction captures ~70% of the academic effect | S-M | **#17** |
| **6** | **Net insider buying, opportunistic (D)** | Inclusion | Real edge nobody in retail India has productized; needs the ingest+clean pipeline first | M | **#18** |

**How this layers onto the first brief's sequencing:**

- **Phase 1 (make the gate refuse) — from brief #1:** readiness latlice (#1), risk/plan.py (#2), regime governor (#3), one-opinion reconciliation (#4), data-integrity clamps (#5). *Do these first.* A feed that refuses is the prerequisite — adding new inclusion edges to a feed that passes 80 cards just makes it 90.

- **Phase 2 (build the inclusion moat) — this brief:** once the gate refuses, layer in **PEAD-small-cap (#13) as the anchor setup** and **MAX-exclusion (#14)** as its pair. These two together cleanly partition the small-cap space into "drift names" (trade) and "lottery names" (refuse) — which is the cleanest alpha story the tool can tell.

- **Phase 3 (sharpen the gates) — both briefs:** 52w-high nearness (#15), FII/DII regime overlay (#16), sector-adjusted momentum (#17). Each is a small, additive refinement that improves precision without widening the feed.

- **Phase 4 (the data-moat edges):** insider buying (#18) once the ChartsMaze feed is ingested; analyst revisions only if you acquire estimate data.

---

## 4. The meta-pattern — what makes an edge durable in India

Looking across all twelve edges (brief #1's six + this brief's six), the durable-unsaturated pattern is consistent. An edge stays open in India when at least one of these holds:

1. **The data exists but is messy** (insider trades, bulk-deal footprints, ASM transitions). Copycats don't do the cleaning.
2. **The signal requires decomposition, not addition** (residual momentum, sector-relative strength, delivery_z vs absolute-60). Free tools add; the edge is in subtracting the shared component.
3. **The edge is an exclusion, not an inclusion** (MAX/lottery, pump-signature, ASM). Every incentive in retail-finance media points toward *more names, more action* — a tool that refuses has no natural competitor.
4. **The behavioral root is cultural and slow-moving** (52w-low anchoring, lottery preference, recency-chasing). These don't arbitrage away because they're *preferences*, not mistakes — the average participant isn't trying to do what you're doing.
5. **The structural data is India-unique** (delivery%, FII/DII cash flow, ASM/GSM). Global quant funds don't specialize in it; domestic tools don't quantify it.

Conversely, edges that are **saturated or theatre in India**: raw price momentum, basic RS, VCP/tight patterns, breadth dials, pocket-pivots, sector heatmaps — anything you can get by clicking one button on Chartink or TradingView. The first brief was right to flag these as commodity. **The whole game is moving from "what free tools show" to "what free tools structurally cannot show without the decomposition/cleaning/exclusion work."**

---

## 5. The one-line thesis (carry this into every build decision)

> In India, the edge is not in *seeing more* — it's in **seeing the same public data more precisely** (decomposed, z-scored, sector-adjusted), **refusing the names the crowd is paid to point you at** (lottery/pump/ASM), and **following the informed money the crowd ignores** (insider clusters, FII flow, PEAD in under-covered names). Every edge in this brief survives because it requires work free sites won't do: cleaning, decomposing, or excluding.

---

### Sources (key references per edge)

**PEAD (Edge A):** [Post-Earnings-Announcement Drift Anomaly in India (SCIRP)](https://www.scirp.org/journal/paperinformation?paperid=88060) · [Asymmetric Uncertainty Around Earnings Announcements (U New Haven)](https://digitalcommons.newhaven.edu/cgi/viewcontent.cgi?article=2897&context=americanbusinessreview) · [PEAD review (ResearchGate)](https://www.researchgate.net/publication/347976957_A_review_of_the_Post-Earnings-Announcement_Drift)

**Residual momentum (Edge B):** [Enhancing Momentum Via Idiosyncratic Momentum (Alpha Architect)](https://alphaarchitect.com/swedroe-spotlight-enhancing-momentum-strategies-via-idiosyncratic-momentum/) · [Residual Momentum Factor (QuantPedia)](https://quantpedia.com/strategies/residual-momentum-factor) · [Idiosyncratic Momentum as Return Predictor (CXO Advisory)](https://www.cxoadvisory.com/momentum-investing/idiosyncratic-pure-or-residual-momentum-as-a-stock-return-predictor/) · [What Drives Short-Term Stock Returns in India? (SSRN)](https://papers.ssrn.com/sol3/Delivery.cfm/6951339.pdf?abstractid=6951339) · [Comparative momentum analysis (Hanauer)](http://wp.lancs.ac.uk/mhf2019/files/2019/09/MHF-2019-076-Matthias-Hanauer.pdf)

**MAX/lottery exclusion (Edge C):** [Explaining Low Volatility in China A-shares (NYU Shanghai 2025)](https://cdn.shanghai.nyu.edu/sites/default/files/honorsthesis2025_zijin_su.pdf) · [IVOL: MAX or MIN effect in China (U Vaasa)](https://osuva.uwasa.fi/server/api/core/bitstreams/4daceef9-5eb7-4700-9201-1ab2e1c46832/content) · [Predictability of Extreme Daily Returns](https://www.tandfonline.com/doi/full/10.1080/1331677X.2021.1965000) · [Lottery Preferences and Anomalies (Alpha Architect)](https://alphaarchitect.com/lottery-preferences-and-anomalies/) · [MAX CAPM (EFMA 2025)](http://www.efmaefm.org/0EFMAMEETINGS/EFMA%2520ANNUAL%2520MEETINGS/2025-Greece/papers/MAX_CAPM.pdf)

**Insider buying (Edge D):** [Insider trading dataset (NIH/PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC10130014/) · [Profiting From Insider Transactions (2iQ)](https://www.2iqresearch.com/blog/profiting-from-insider-transactions-a-review-of-the-academic-research) · [Insider Filings as Trading Signals post-SOX (ScienceDirect 2024)](https://www.sciencedirect.com/science/article/pii/S1544612324015435) · [Repurchases + Insider Trading (RePEc 2023)](https://ideas.repec.org/a/kap/rqfnac/v60y2023i4d10.1007_s11156-023-01142-7.html) · [Are Insiders' Trades Informative? (NBER)](https://www.nber.org/system/files/working_papers/w6656/w6656.pdf) · [Retail learning from insiders (SMU)](https://ink.library.smu.edu.sg/context/lkcsb_research/article/7800/viewcontent/BSZ_2022EFA.pdf)

**FII/DII flow (Edge E):** [NSE FII/DII Reports (official)](https://www.nseindia.com/reports/fii-dii) · [Trendlyne FII/DII cash activity](https://trendlyne.com/macro-data/fii-dii/latest/cash-pastmonth/) · [Sensibull FII/DII data](https://web.sensibull.com/fii-dii-data)

**52-Week High (Edge F):** [George & Hwang 2004 (full PDF)](https://www.bauer.uh.edu/tgeorge/papers/gh4-paper.pdf) · [The Secret to Momentum is the 52-Week High (Alpha Architect)](https://alphaarchitect.com/the-secret-to-momentum-is-the-52-week-high/) · [State-dependent psychological anchors (ScienceDirect 2021)](https://www.sciencedirect.com/science/article/abs/pii/S1544612321004256) · [Insiders exploiting 52w-high anchoring (Lasfer 2023)](https://onlinelibrary.wiley.com/doi/10.1111/fire.12371)

**ASM/GSM (cross-cutting, India-specific):** [NSE Working Paper: Effectiveness of Additional Surveillance Measures](https://nsearchives.nseindia.com/s3fs-public/inline-files/Effectiveness%2520of%2520additional%2520surveillance%2520measures_WorkingPaper.pdf) · [Surveillance action efficacy (ScienceDirect 2026)](https://www.sciencedirect.com/science/article/abs/pii/S0927538X2600171X)

**Lead-lag (Edge context, lower priority):** [Factor-Driven Lead-Lag Effects (EFMA 2021)](https://www.efmaefm.org/0EFMAMEETINGS/EFMA%2520ANNUAL%2520MEETINGS/2021-Leeds/papers/EFMA%25202021_stage-2049_question-Full%2520Paper_id-411.pdf) · [Geographic Lead-Lag (AEA)](https://www.aeaweb.org/conference/2020/preliminary/paper/SfTyaRaf)
