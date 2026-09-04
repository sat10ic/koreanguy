# Manas 2.0 — USIC Champions' Setups, Translated for India Long-Only

*Third brief in the series. Brief #1 diagnosed the tool. Brief #2 surveyed global quantitative edges unsaturated in India. This brief takes the other route to the same question: what are the best discretionary swing traders in the world actually doing right now (USIC / European competition winners 2023-2025), and which of their setups survive the translation to Indian NSE cash, long-only, on public data, with a human confirming every trade?*

**The five traders studied** (with their verified USIC results):
- **Tanmay Khandelwal** — +129% (2023, $1M+ division winner), TwoX Capital
- **Goverdhan Gajjala (GG)** — +805% (2023, stock division winner)
- **Martin Luk** — +283% (2024) → +969% / ~1358% (2025 champion), Hong Kong
- **J Law (Law Wai-Sum)** — +353% (2024) → +252% (2025), two-year record ~1499%, broke Minervini's mark
- **Marios Stamatoudis** — +291% (2023, top-5)

---

## 0. The punchline first

Across all five, the **indicators are commodity** (EMAs, volume, AVWAP, breakouts — all free on every platform). What actually generated the returns is identical across all of them, and it is *not* a setup. It is **five disciplines**, and these five map almost perfectly onto the gaps brief #1 found in Manas:

1. **Asymmetric R:R through tight stops, not high win rates.** Martin Luk won the 2025 championship with a **23% win rate** and 5:1 average payoff. His thesis, quoted directly: *"I can't predict my return — but I can control my risk."* This is the exact opposite of Manas's current readiness-100-everywhere feed, which optimizes for *signal count* (the 67 A+ cards) instead of *payoff asymmetry*.
2. **Theme/sector rotation as the primary alpha, not stock-picking.** All five trade "stocks in the hot sector," not "great stocks." Martin explicitly hunts "fast-moving stocks in hot sectors with ADR > 5%."
3. **Progressive exposure (anti-martingale).** Cut size after losses, add only after the equity curve confirms. None of them risk a fixed % regardless of recent results.
4. **Earnings/catalyst momentum beats price momentum.** Tanmay's stated edge verbatim: *"Our focus is not to find the stocks with the best momentum but to find the ones with the best **earnings momentum**."* This independently validates PEAD (brief #2, Edge A) as the anchor.
5. **Refusal to trade outside a narrow setup bucket.** Each champion has 2-4 setups and trades *nothing else*. Martin: pullback + EP. GG: bull-flag + EMA-kiss + horizontal-fade. Marios: breakout + EP + parabolic-short.

**The single most important translation insight:** in the US, the *penny/small-cap volatile name* (GG's, and partly Martin's, hunting ground) is a legitimate edge because US microcaps have real catalysts, options liquidity, and no daily circuit locks. **In India, the equivalent cohort is operator-driven pump territory** — that exact translation fails (and fails dangerously: ASM, circuit locks, no-bid exits). But the *mechanics* these traders use on quality names — pullbacks in uptrends, EP drift, tight-stop asymmetry — translate almost perfectly and map directly onto Manas's existing detectors. **Build the discipline, not the cohort.**

---

## 1. Per-trader breakdown with India long-only verdict

### Martin Luk (2025 champion, +969%) — **THE most translatable system**

This is the system worth studying in detail, because it is the one that survives the India translation with the least erosion.

**His actual setup (from his own write-up and the Trading Resource Hub interview):**
- **Three scanners** driving theme/rotation detection:
  1. *Pre-market scanner* — gap-ups on heavy volume (EP / catalyst detection).
  2. *Potent scanner* — prior day's strongest performers (theme ignition).
  3. *Leader scanner* — biggest movers over 30 days (confirmed leadership).
- **EMA stacking classification** of every candidate into one of three buckets:
  - *Lead*: `9EMA > 21EMA > 50EMA` (the only bucket he trades long).
  - *Mediocre*: mixed (e.g. 9>21 but <50).
  - *Lag*: `9<21<50` (never long).
- **Pullback entry** within an established uptrend: tight inside day / EMA convergence (9/21/50) / opening-range-high breakout / clean range expansion. Uses AVWAP + MAs + key support for entry timing.
- **Tight stops**: 1-3.5% typically, *never more than half the stock's ADR* (so a 5% ADR stock gets a max 2.5% stop). 80%+ of his 2024 trades used stops <3.5%.
- **The parabolic stop effect** (his core insight): halving the stop from 3% to 1.5% on a 25% winner *doubles* the R captured (8R → 16R). Tight stops aren't cosmetic — they are geometric.
- **Risk**: 0.5-1% per trade, max 35% portfolio exposure, *reduced* during drawdowns.
- **Exit**: sell into strength (trim 10-15% at 3R+) and into weakness (9EMA trail in strong trends, 21/50EMA otherwise).
- **Stats**: 23-25% win rate, ~5:1 payoff. *"Systematic execution beats prediction."*

**India long-only verdict: BUILD NEARLY ALL OF IT.** This is the closest match to what Manas should be. Specifically translatable:

| Luk element | India translation | Manas mapping | Build |
|---|---|---|---|
| EMA Lead/Mediocre/Lag classification | Direct: compute 9/21/50EMA stacking on every EQ symbol daily | `engine/eod_detectors.ema()` exists; just add the 3-bucket classifier as a hard gate (only "Lead" enters the long feed) | **S** |
| Three scanners (pre-market / potent / leader) | *Pre-market* = gap-ups → your `earnings_power` + a generic gap detector. *Potent* = prior-day top performers → trivial from `daily_prices.pct_change`. *Leader* = 30-day leaders → trivial. | New `scanner/theme_scanners.py`; one SQL each | **S** |
| Pullback entry (tight inside day, EMA convergence, AVWAP) | Direct translation. Tight-inside-day = your existing `ipo_base` "mini-coil" logic generalized. AVWAP exists (`avwap_auto_anchor`) but needs the anti-thrash fix flagged in brief #1. | Generalize the inside-bar detector; fix AVWAP anchor | **M** |
| Tight stops ≤ ½ ADR | **This is the fix for your 27% stop problem.** Stop = `min(trigger_low, entry − 0.5×ADR14)`. Bound by `max_stop_pct=7%`. | `risk/plan.py` from brief #1 | **S** |
| Parabolic-R size math | Once stops are tight, size = `capital × risk% / stop_dist` automatically gives more units of a tighter-stop name — the geometric effect Luk describes is free | `risk/plan.py` | **S** |
| Progressive exposure | Track recent trade R in journal; if rolling 10-trade avg R < 0, cut size to half-band; if > 0, full band | `journal_trades` + governor hook | **M** |
| 9EMA trailing exit / 21-50EMA in strong trends | Direct translation. Your `exit_state` uses 21EMA; add a 9EMA trail option for "in-profit" names | `eod_detectors.exit_state` extension | **S** |

**What doesn't translate:** Luk's small-account concentration (he ran $1,300 → used 35% in a single name). For a single-user Indian swing tool, cap single-name exposure lower (the regime-band caps from brief #1 handle this). Also: he trades intraday entries on 5-min charts for stop-tightening — that needs live Fyers data (you have the provider, the loop isn't built). The daily-timeframe version still works; you just give up some R-tightening.

### Tanmay Khandelwal (2023, +129%, $1M+ division) — **validates the PEAD anchor**

**His stated edge** (verbatim from his champion-strategy video): *"find the stocks with the best **earnings momentum**, not the best price momentum."* His approach is "structured stock selection + rigid risk control" — earnings acceleration as the primary filter, with strict risk rules.

**India long-only verdict: BUILD, and it directly confirms brief #2's Edge A (PEAD).** Tanmay is essentially running the PEAD-in-under-covered-names edge that brief #2 identified as your highest-impact research bet — but he ran it on US mid-caps. The India translation:

- **Earnings momentum filter** = your `earnings_power` detector (30% QoQ+YoY EPS+sales) + the under-covered market-cap band (₹500-8000cr) from brief #2. You already have the detector; the *cohort restriction* (small/mid-cap only) is the missing piece that makes it an edge instead of noise.
- **"Rigid risk control"** = the `risk/plan.py` module from brief #1.
- The reason Tanmay's edge works in the US is the same reason it works in India (per brief #2): **institutions can't deploy fast enough into the under-covered zone to close the drift**, and retail processes earnings slowly. His championship is independent, real-world confirmation of the PEAD thesis on a 12-month verified track record.

### Goverdhan Gajjala (2023, +805%) — **partial translation only; the dangerous one**

**His three setups:**
1. *Bull Flag Breakout* — breakouts from consolidation on rising volume.
2. *EMAs Kiss and Fly* — entries off moving-average confluence.
3. *Horizontal Fade* — reversals at horizontal levels.

He uses three indicators: EMA, Volume, Price Action. He trades **volatile small-caps and penny stocks intraday**.

**India long-only verdict: BUILD THE SETUPS, REFUSE THE COHORT.** This is the one translation that *partially fails*, and the failure is instructive:

- **The setups themselves work in India** on quality mid-caps — bull-flag breakouts, EMA-kiss pullbacks, and horizontal-level fades are universal and your existing `launch_pad`, `pullback`, and `pocket_pivot` detectors already cover this ground.
- **The cohort he trades DOES NOT translate.** US penny/small-caps have catalysts, options liquidity, and no hard daily circuit locks. The Indian equivalent (sub-₹100, sub-₹500cr names) is **operator/pump territory** — exactly the MAX-effect / lottery-stock population brief #2 Edge C says to *exclude*. GG's 805% came partly from a market microstructure (US small-cap volatility with clean exits) that **does not exist in India**. If you build GG's setup and aim it at GG's cohort in India, you are building the pump-trap feed.
- **The discipline translates, the venue doesn't.** Use his *setup shapes* on the *post-gate* quality cohort (the names that survive brief #1's risk gate + brief #2's MAX exclusion). Bull flags off a tight base in a ₹2000-10000cr earnings-growth name = yes. Bull flags in a ₹400cr circuit-hitting name = the trap.

**Bottom line on GG:** his setups add to your detector vocabulary (you largely have them), but his *edge source* (volatile micro-cap intraday momentum) is non-translatable and, worse, dangerous in India. Do not chase the 805% by emulating the cohort.

### J Law / Law Wai-Sum (2024-2025 two-year record holder) — **the CAN SLIM / trend-template translation**

**His approach** (from his teaching videos and the Hong Kong coverage): a William O'Neil / IBD-style **trend template** — strict technical criteria for "stock in a confirmed uptrend," combined with CAN SLIM fundamental screening. The classic trend-template rules:
- Price above 50-day and 200-day MA.
- 50-day above 200-day (golden-cross structure).
- Price within ~15% of 52-week high.
- RS rank in a high percentile.
- Confirmed market uptrend.

**India long-only verdict: BUILD AS A PRE-FILTER GATE.** This is the cleanest "quality filter" of the five, and it maps almost 1:1 onto the infrastructure you already have:

| Trend-template rule | Manas mapping | Status |
|---|---|---|
| Price > 50DMA > 200DMA | `eod_detectors.sma()` over 50/200; new gate | **build** |
| Within 15% of 52w high | Brief #2 Edge F (nearness-high ≥ 0.85) | **already scoped** |
| RS rank high percentile | `stock_rs_map` exists; tighten to ≥80 (brief #1) | **already scoped** |
| Confirmed market uptrend | `regime_snapshots.market_mode` (RISK_ON/SELECTIVE) | **exists** |
| CAN SLIM fundamentals | `symbol_quality.{eps_yoy, eps_qoq, sales_yoy}` + market cap | **partial** (you lack full C/A/N/S/L/I/M but have the earnings legs) |

J Law's edge is **selectivity by template** — he refuses anything that doesn't clear all five. That is the same thesis as brief #1's "make the gate refuse." His two-year record (~1499%, breaking Minervini) is the strongest real-world evidence that *a strict template beats a wide net*.

### Marios Stamatoudis (2023, +291%) — **two of three setups translate**

**His three setups:**
1. *Classic Breakouts* — base breakouts (bread and butter). **Translates fully.**
2. *Episodic Pivots* — event-driven moves (earnings, news). **Translates fully — this is PEAD/EP again.**
3. *Parabolic Shorts* — shorting overextended parabolics, ~85% reported win rate. **Does NOT translate** (India long-only; SLB is illiquid; small-cap futures don't exist).

**India long-only verdict: BUILD TWO, DROP THE THIRD.** Marios's first two setups are the same population Martin Luk and Tanmay trade — breakouts + EP — and they're already in your detector set (`pocket_pivot`, `earnings_power`, `launch_pad`). The parabolic short is the one to *invert*: instead of shorting the parabolic, **use the parabolic signature as an EXCLUSION filter for longs** (a name 2 ATR above its 21EMA after a vertical run is a *sell-the-trap*, not a *buy-the-breakout*). That's brief #1's anti-chase gate and brief #2's MAX-exclusion, restated.

---

## 2. The translation table — every setup, one verdict

| Trader | Setup | India long verdict | Why |
|---|---|---|---|
| Martin Luk | Pullback in uptrend (AVWAP + EMA convergence) | ✅ **BUILD** | Maps to existing pullback/AVWAP; tight-stop math solves the 27% stop |
| Martin Luk | EMA Lead/Mediocre/Lag classification | ✅ **BUILD** | One-line daily gate; only "Lead" bucket enters long feed |
| Martin Luk | Three-scanner theme detection (pre-mkt/potent/leader) | ✅ **BUILD** | Three SQL queries; gives you the theme-rotation alpha all champions rely on |
| Martin Luk | Tight stops ≤ ½ ADR + parabolic-R sizing | ✅ **BUILD** | This IS brief #1's `risk/plan.py` |
| Martin Luk | Progressive exposure (cut after losses) | ✅ **BUILD** | Needs journal wired (brief #1 #36) |
| Tanmay | Earnings-momentum anchor | ✅ **BUILD** | Confirms brief #2 Edge A; restrict to under-covered mcap band |
| J Law | Trend-template pre-filter (5 rules) | ✅ **BUILD** | Strict-selectivity gate; maps to existing infra + brief #2 Edge F |
| GG | Bull-flag breakout (setup) | ✅ BUILD on quality cohort | Setup is universal |
| GG | EMA kiss and fly (setup) | ✅ BUILD on quality cohort | Universal |
| GG | Horizontal fade (setup) | ⚠️ BUILD cautiously | Reversals are lower-win-rate; deprioritize vs pullback |
| GG | Penny/small-cap volatile cohort | ❌ **REFUSE** | US microcap microstructure ≠ India; = pump/MAX territory |
| Marios | Classic breakout | ✅ BUILD | Have it (`pocket_pivot`) |
| Marios | Episodic pivot (long) | ✅ **BUILD** | = PEAD anchor (brief #2 Edge A) |
| Marios | Parabolic short | ❌ **INVERT to exclusion** | Long-only India; use the parabolic signature to *exclude* longs instead |

**The honest non-translations** (what you cannot get from these champions in India):
1. **Penny-stock intraday momentum** (GG's, partly Martin's) — the US venue doesn't exist in India. Equivalents are ASM-bound pump traps.
2. **Parabolic shorting** (Marios's highest-win-rate setup) — India retail can't short small-caps. You get the *inverse* for free (exclusion), but not the short itself.
3. **Options-leveraged EP** (Martin's 2x ETF / leveraged EP trades) — out of scope for cash-only, manual execution.
4. **Intraday stop-tightening on 5-min charts** (Martin) — needs the live Fyers loop (deferred per brief #1). Daily-timeframe version works; you give up R-tightening until live data is wired.

---

## 3. How this layers into the existing architecture

The champions' collective playbook converges on a **single architecture** — and it happens to be the one brief #1 already specified. The contribution of this brief is to confirm the *discipline shape* and add two missing pieces (EMA-stacking gate, theme scanners) that are directly attributable to Martin Luk and J Law.

**The unified candidate pipeline, post-translation:**

```
1. THEME IGNITION (Martin's 3 scanners)
   ├─ pre-market gap-ups   → EP/catalyst detector
   ├─ potent (1d leaders)  → daily_prices pct_change top
   └─ leader (30d leaders) → daily_prices 22d pct_change top
   ──→ defines the "hot sector/theme" set for today

2. HARD GATE (J Law trend template + brief #1 disqualifiers)
   ├─ price > 50DMA > 200DMA           (J Law rule)
   ├─ EMA stacking = "Lead" only        (Martin Luk rule)
   ├─ nearness_52w_high ≥ 0.85          (brief #2 Edge F)
   ├─ sector in hot-theme set from (1)  (Martin Luk rule)
   ├─ best_valid_stop ≤ 7%              (brief #1)
   ├─ R:R ≥ 1.5                         (brief #1)
   ├─ delivery_z ≥ 0                    (brief #2 Edge B)
   ├─ NOT MAX-effect / lottery          (brief #2 Edge C)
   └─ regime allows this setup-type     (brief #1 governor)
   ──→ this is the gate that REFUSES

3. SETUP DETECTION (among survivors)
   ├─ pullback (Martin Luk / GG)         → existing pullback detector + AVWAP fix
   ├─ EP / PEAD drift (Tanmay / Marios)  → earnings_power + under-covered mcap band
   ├─ launch-pad / base breakout (Marios/J Law) → existing launch_pad
   └─ IPO-base                           → existing ipo_base

4. RISK PLAN (Martin Luk's asymmetry)
   ├─ stop = min(trigger_low, entry − 0.5×ADR14), capped at 7%
   ├─ size = capital × regime_risk% / stop_dist   (parabolic-R for free)
   ├─ progressive exposure: half-band if rolling-10-trade R < 0
   └─ refuse the trade if any of the above doesn't clear

5. EXIT (Martin Luk's adaptive trail)
   ├─ 0 to +1R: 21EMA or trigger-low trail, hold full
   ├─ +1R: stop to breakeven, book 1/3, switch to 9EMA trail
   ├─ +2R or extension: book another 1/3
   └─ 21EMA lost on volume: sell the turn
```

Every box is sourced either to (a) a brief #1 task, (b) a brief #2 edge, or (c) a specific champion's named discipline. **The whole pipeline decomposes into named rules — no black box — exactly as your founding principles require.**

---

## 4. The five disciplines, restated as measurable targets

These are the metrics that tell you the champions' edge has actually been captured, not just their indicators copied:

| Discipline | Source | Metric | Target |
|---|---|---|---|
| Asymmetric R:R | Martin Luk (23% win, 5:1) | avg winner R / avg loser R | ≥ 4.0 |
| Tight stops | Martin Luk (≤½ADR) | median stop distance on accepted setups | ≤ 4.5% (down from today's ~12-27%) |
| Selectivity | J Law / all champions | A+ cards per night | 3-8 (down from ~67) |
| Theme rotation | Martin Luk's scanners | % of accepted setups in top-2 hot sectors | ≥ 60% |
| Earnings momentum | Tanmay | EP setups' T+10 hit rate vs non-EP | EP ≥ 1.5× higher |
| Progressive exposure | Martin Luk | size reduction triggered within 5 trades of a drawdown | implemented + logged |
| One opinion per symbol | implied by all | readiness-vs-exit contradictions | 0 (reconciliation enforced) |

If those numbers move to target, you have not reskinned free data — you have productized the actual discipline that took five traders to the top of a verified worldwide competition.

---

## 5. What to build first (concrete next steps, ranked)

Layered onto brief #1's roadmap (#1-12) and brief #2's (#13-18):

| Priority | Task | Source | Effort |
|---|---|---|---|
| **Now** | `risk/plan.py` — tight-stop math + R:R + size, the single writer of size (brief #1 #2 + Martin Luk's ADR rule) | Martin Luk, brief #1 | M |
| **Now** | EMA Lead/Mediocre/Lag hard gate — only "Lead" (9>21>50) enters the long feed | Martin Luk | S |
| **Now** | Theme-ignition scanners (pre-market gap / 1d potent / 30d leader) → defines today's hot-sector set | Martin Luk | S |
| **Next** | Trend-template pre-filter gate (J Law's 5 rules) layered above the setup detectors | J Law | S |
| **Next** | EP/PEAD anchor setup restricted to under-covered mcap band (Tanmay's thesis + brief #2 Edge A) | Tanmay, brief #2 | M |
| **Next** | Adaptive exit trail (Martin's +1R/+2R booking + 9EMA trail) | Martin Luk | M |
| **Then** | Progressive exposure tied to journal rolling-R | Martin Luk | M (needs journal wired) |

**Do not** build GG's small-cap-cohort hunting, Marios's parabolic shorts, or any options-leveraged variant. They are real edges in their original venue and traps in India.

---

## 6. The one-paragraph thesis

> Every USIC champion of the last three years won with **the same five disciplines** — asymmetric R:R via tight stops, theme-rotation over stock-picking, progressive exposure, earnings-momentum preference, and ruthless setup refusal — *not* with secret indicators. The indicators are commodity; the discipline is the edge. Of the champions' specific setups, **Martin Luk's pullback-in-uptrend system translates almost intact to India** (and directly fixes Manas's 27%-stop and 67-card problems), **Tanmay's earnings-momentum thesis independently validates PEAD as the anchor setup** (brief #2 Edge A), and **J Law's trend template gives the strict-selectivity gate** brief #1 specified. The one translation that fails — Goverdhan Gajjala's penny-stock intraday momentum and Marios's parabolic shorts — fails because the *US small-cap venue* (catalysts, options, no circuit locks) has no Indian cash-market equivalent; the same names in India are the MAX-effect / ASM pump population brief #2 says to exclude. **Build the discipline and the quality-cohort setups; refuse the cohort that doesn't survive the translation.** The result is a tool whose pipeline — theme ignition → hard gate → setup detection → tight-risk plan → adaptive exit — is a named-rule productization of what five verified worldwide champions actually do, decomposed exactly as the no-black-box principle requires.

---

### Sources

**USIC official results & strategy deep-dives:**
- [USIC 2023 Final Results (BusinessWire)](https://www.businesswire.com/news/home/20240126217806/en/United-States-Investing-Championship-2023-Final-Results)
- [USIC previous standings (Financial Competitions)](https://financial-competitions.com/previousstandings)
- [2025 USIC First-Half Results (BusinessWire)](https://www.businesswire.com/news/home/20250730525524/en/2025-United-States-Investing-Championship-First-Half-Results)

**Tanmay Khandelwal:** [$1,000,000 Champion Investing Strategy (YouTube)](https://www.youtube.com/watch?v=eney0dClrpI) · [How he WON USIC — Face2Face (YouTube)](https://www.youtube.com/watch?v=2z399GcAyE8) · [TwoX Capital win statement (X)](https://x.com/twoxcapital/status/1750408674734997617)

**Goverdhan Gajjala:** [Deep-dive into the Momentum Masterclass (Substack)](https://retailtradersrepository.substack.com/p/goverdhan-gajjala-a-deep-dive-into) · [3 chart indicators for volatile stocks (Business Insider)](https://www.businessinsider.com/top-chart-indicators-trader-volatile-stocks-high-returns-in-2023-2024-1) · [Bull-Flag setups (Scribd)](https://www.scribd.com/document/787440615/Goverdhan-Gajjala-Setups-Bull-Flag-Breakout-Classic-Pullbac) · [Won USIC with 3 Setups (YouTube)](https://www.youtube.com/watch?v=uG8CzABsIPM)

**Martin Luk:** [The 22-Year-Old Who Returned 283% in USIC 2024 (Trading Resource Hub)](https://tradingresourcehub.substack.com/p/martin-luk-283-usic-2024-key-lessons) · [1358% Swing Trading Strategy breakdown (Financial Wisdom TV)](https://www.financialwisdomtv.com/post/martin-luk-s-1358-swing-trading-strategy-from-gamestop-blow-up-to-us-investing-champion) · [Pullback Strategy (YouTube)](https://www.youtube.com/watch?v=F0vssXyWizc) · [+969% Return deep-dive (YouTube)](https://www.youtube.com/watch?v=VKNEJA5r8zw) · [@martinlukkt (X)](https://x.com/martinlukkt)

**J Law (Law Wai-Sum):** [Two-year USIC record announcement (Yahoo Finance)](https://finance.yahoo.com/news/j-law-sets-two-record-143000498.html) · [J Law expands to Singapore (Yahoo Finance)](https://sg.finance.yahoo.com/news/u-investing-champion-j-law-013000512.html) · [J Law strategy course — Moving Averages (blog.forecho.com)](https://blog.forecho.com/jlaw-meta-strategy-ep4.html) · [China Daily profile](https://www.chinadailyhk.com/hk/article/619272)

**Marios Stamatoudis:** [+291% Swing Trading Strategy breakdown (LinkedIn)](https://www.linkedin.com/posts/marios-stamatoudis-3b996b185_291-swing-trading-strategy-the-3-powerful-activity-7159927969648390144-05Ue) · [TraderLion profile & interview](https://traderlion.com/profile/marios-stamatoudis/day-trading-to-swing-trading/) · [@stamatoudism (X)](https://x.com/stamatoudism)
