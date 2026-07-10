# INDIA_PLAYBOOK — Synthesized NSE Swing Methodology for Manas OS

**Purpose.** One playbook that fuses the three source methodologies into a single India-aware
doctrine the tool can be built to. Every rule keeps its cite and is tagged **[CODEABLE]** (a
machine can compute/enforce it) or **[JUDGMENT]** (a coach/debate line for the human, not a
gate). Where sources conflict, the **backbone hierarchy** decides and the conflict is recorded
in-line so it is never silently resolved.

**Backbone hierarchy (locked by the user).**
1. **TradeTM** (Anuragg Venkatakrishnan / Chirag Kedia) — the BACKBONE. When any rule conflicts,
   TradeTM's version is the doctrine of record; the losing version is kept as an annotation.
2. **Manas Arora** — second. Fills entry-execution and live-read detail TradeTM leaves thin.
3. **Stocksgeeks (Umang)** — third. Breadth (MBI) and IPO/base micro-structure detail.

**Governing principle (most-quoted line in the corpus): "Trade the market you are in, not the
market you wish you were in."** [TTM-F15] — India's shallow, circuit-limited, ~500-liquid-name
tape is structurally different from the US; do not import US frequency, universe, or stop-width
assumptions.

**Citation keys.** `TTM-x` = `TRADETM_NUANCES.md` entry x (backbone). `TTM-Sn` =
`TRADETM_NUANCES_SHARDS.md` nugget n. `TTM-H-x` = `TRADETM_NUANCES_HINDI.md` nugget x (raw
Hindi/Hinglish transcripts — IPO bases + working-professional system). `AR-...` =
`ARORA_SHARDS_NUANCES.md`. `SG-...` =
`STOCKGEEKS_NUANCES.md`. `WK` = `WAVE_K_SPEC.md`. Each `TTM-*`/`AR-*`/`SG-*` entry carries the
original primary-source quote+file cite in its extraction file; those are the ground truth.

---

## 1. India Universe & Liquidity Law

The tool's universe is not "all NSE" — it is a liquidity-filtered subset. These rules define it.

| # | Rule | Cite | Tag |
|---|---|---|---|
| U1 | **NSE EQ only.** BSE/SME rejected for liquidity. Arora's baseline scan: NSE only. | AR-NSE-Only-Universe; WK (groww 3) | [CODEABLE] |
| U2 | **Price floor ₹30 hard; prefer ₹50+.** Sub-₹30 = illiquid, wide spread, execution risk. | AR-Minimum-Stock-Price | [CODEABLE] |
| U3 | **Turnover floor.** Backbone: require min 30-day avg turnover in ₹ regardless of price momentum (a 200%+ winner can still be untradeable — Elantas Beck). Arora: >₹1cr/day. WAVE_K operating value: **≥3cr** (CHARTSMAZE). A stock's price return never substitutes for turnover. | TTM-A5, TTM-S7; AR-Turnover; WK | [CODEABLE] |
| U4 | **Exclude 5%-circuit-band stocks entirely**, regardless of setup quality — risk is unmanageable. (Circuit *upgrade* 5%→10/20% is a bullish signal; *downgrade* to 5% = drop it.) | TTM-A2, TTM-S6; AR-5%-Circuit, AR-Circuit-Change | [CODEABLE] |
| U5 | **>12% gap+ORB EP skip.** On an EP gap day, skip if gap-up% + first-5min-ORB% > 12% of prior close — the 5% circuit prevents the trade going risk-free same day. | TTM-A1, TTM-S10 | [CODEABLE] |
| U6 | **~500-name reality.** At real portfolio size the liquidity-filtered Indian universe is ~500 names (vs ~2000 in the US). Surface "current universe size after liquidity filter" as a stat; do not import US-scale frequency/position-count assumptions. | TTM-A3, TTM-S56 | [CODEABLE] (stat) / [JUDGMENT] (assumption discipline) |
| U7 | **Top-100 liquidity cliff.** ~70% of NSE free-float mcap sits in the top 100 names; spreads outside it are structurally poor. Slippage buffer must widen by market-cap tier. | TTM-A4, TTM-S1, TTM-S3 | [CODEABLE] |
| U8 | **Intraday depth check.** A stock can pass a turnover scan yet have no depth: >3 consecutive low-volume/blank 3–5min bars = untradeable. | TTM-S5 | [CODEABLE] |
| U9 | **Institutional-volume universe.** To ride institutions you must be in names showing real volume (millions of shares); account size is irrelevant to this. | AR-Account-Size | [CODEABLE] |
| U10 | **EP/IPO liquidity re-scan.** EP volume is a "reverse network effect" — it makes previously-illiquid names tradeable. Re-check the liquidity filter *after* an EP trigger, not only pre-trigger. Setup-liquidity rank: EP/IPO > breakout > reversal. | TTM-A8, TTM-A9 | [CODEABLE] |
| U11 | **Regulatory backdrop (ASM/GSM, F&O margin cuts, daily expiries) concentrates liquidity into fewer names** — a periodic universe-size check captures the effect. | TTM-A6 | [JUDGMENT] (effect is [CODEABLE] as periodic count) |

**Why this is the law, not decoration:** pure swing trading "underperforms structurally in
India's shallow/circuit-limited market vs the US" [TTM-F15]; the universe rules above are the
justification for every downstream gate. Do NOT replicate US playbooks (Qullamaggie's 15
positions) into India's 3–4-position reality [TTM-S56].

---

## 2. The Four-Phase Regime Model (backbone) + how it maps onto XP/MBI

**Backbone regime model = TradeTM's four phases**, richer than binary bull/bear and the strongest
candidate for the tool's regime gauge:

1. **Demand Domination** (bull bias) — maximize setup frequency; bull markets are "the time for
   excessive trading." [TTM-C1, TTM-S20, TTM-S24]
2. **Supply Domination** (bear bias) — reduce frequency, "certain trades with large bets," high
   conviction only. [TTM-S24]
3. **Lack of Demand** (buyers exhausted) — **most momentum-burst failures cluster HERE**, more
   than any other phase. Gap-driven EPs fail more; favor base-and-break / late-reaction /
   failure-reset EP variants. [TTM-C1, TTM-C3, TTM-S21]
4. **Lack of Supply** (sellers exhausted) — after major supply exhaustion, long setups perform
   exceptionally well; bench-strength read confirms limited downside. [TTM-C1, TTM-C2]

**[CODEABLE]** via breadth-exhaustion signals: % stocks above/below key MAs, rate-of-change of
that %, new-high/new-low ratio trend, and watchlist-level bench-strength aggregation. [TTM-C1,
TTM-C2]

**Mapping onto the existing tool (XP/MBI modes — RISK_ON / SELECTIVE / DEFENSIVE / NO_TRADE):**

| Four-phase (backbone) | Existing XP/MBI mode | Note |
|---|---|---|
| Demand Domination | RISK_ON | all families on, max frequency |
| Lack of Supply (early turn) | RISK_ON / SELECTIVE | best long window; bench-strength gates entry |
| Lack of Demand | SELECTIVE | **do NOT hard-drop families** — swap momentum-burst → base-and-break EP variants |
| Supply Domination | SELECTIVE → DEFENSIVE | fewer, larger-conviction trades |
| Bear-Volatile only | NO_TRADE | the only truly "dead" regime for a long-only trader |

**Extensions the four-phase model adds over current XP/MBI:**
- **Six market types (Van Tharp):** only **Bear-Volatile** is truly dead for a long-only momentum
  trader; all five others are adaptable via timeframe arbitrage, sizing, or setup choice. Current
  code stands fully down in more regimes than the corpus warrants. [TTM-C5, TTM-C6, WK mismatch 6]
- **Regime is a soft gate, not a family kill.** D2/momentum work on individual strength even in
  muted tapes; reversals/strong-starts are bread-and-butter in all but NO_TRADE. → surface as a
  scored objection, not a silent drop. [TTM-C4, WK Stage-2] **CONFLICT w/ LOCKED
  `ALLOWED_FAMILIES` hard-drop — see PLAYBOOK_TO_TOOL_MAP conflicts list.**
- **EP reaction quality as a leading regime signal:** tepid reaction to strong beats (or outsized
  reaction to modest beats) signals a sentiment turn (April 2023, Oct 2024). Track EP
  reaction-to-quality ratio over a rolling window; feed into the gauge. [TTM-C8, TTM-C9] [CODEABLE proxy]
- **Open-risk-ceiling breach IS a regime signal:** when total open risk hits its ceiling, it means
  setups trigger but don't follow through = choppy tape. Feed back into the gauge. [TTM-D3]
- **Stocksgeeks MBI overlay** (breadth, not direction): burst-ratio bands — <50 red, 50–200 white
  (whipsaw/sit-out), 200–400 green, 400+ engage, 800+/1000+ very powerful (~90% setup hit-rate).
  A **warning day** = 3+ of 6 MBI columns red → expect full-red within 1–2 days; pause new
  positions unless warning-day high breaks on close OR 4.5% burst stays 400+. MBI turns green
  1–2 days *before* price confirms — deploy on green, don't wait for price. [SG-MBI, SG-Warning,
  SG-Green-Timing, SG-Significant-Burst] [CODEABLE]
- **Arora's difficulty read:** some tapes give 30–50% swings easily, others make 10% hard; and
  **3–4 stops in one week = market too tricky → take a 1–2 week break.** Market gets "tricky"
  the week *before* big events (elections/budget) — the collapse happens in that one week; wait
  1–2 weeks after for clarity. [AR-Market-Condition, AR-Poor-Market-Signal, AR-Before-Big-Events]
  [CODEABLE]

---

## 3. Entry Archetypes

Backbone framing: **only three valid chart-based entry concepts exist** — (1) Excessive Demand
(gaps/ORBs), (2) Supply Absorption (VCPs/tight areas), (3) Excessive Selling (reversals/parabolic
longs); everything else is a relabel. [TTM-S8] Also: **no pattern is valid inside a range** —
built-up/overhead supply (and therefore any pattern) only forms once a trend exists; reject
H&S/double-top claims on non-trending charts. [TTM-B6]

### 3.1 Episodic Pivot (EP) — full rule set (backbone; LENS_EP)
- **Criteria:** ~30%+ YoY AND QoQ growth in both EPS and sales (soft benchmark, not hard gate);
  results released **post-market-close**; must **gap up / open strongly** next session (no gap →
  no EP); stock **neglected** (base or downtrend) beforehand; market-cap floor ~₹300cr. [TTM-B1, TTM-S9]
- **Non-earnings EPs:** large new order wins (RVNL, JBMA), government policy (sugar/fertilizer) —
  filter for >30% expected revenue/earnings impact. [TTM-S51]
- **Day-0 entry:** breakout of the **first 5-min opening-range high** (NOT the gap-up price); stop
  = **day's low** (often the breakout-bar low). Skip if gap+ORB >12% (U5). <45% of EPs trigger on
  gap day; those that do give immediate risk-free entries; win rate 40–60%, initial stop 2–4%.
  [TTM-B2, TTM-S10]
- **Pullback entry (most common):** to the **10/21 EMA** — highest-R:R entry for core/pyramid.
  [TTM-B3, TTM-S11]
- **Follow-through is the real test, not Day 0.** [LENS_EP]
- **Execution window:** 9:00–9:15 sort results by gap-up%; tile charts; execute 9:07–9:30 —
  designed for a working professional's 20–30 min window. [TTM-F11]
- **EP holding = magnitude, all-or-nothing.** EPs are <10% of trades but >35% of 2-yr returns;
  sell into *weakness* (21EMA close + low break, or 50DMA if tight), NOT into strength, except a
  15%+ blow-off. [TTM-B4, TTM-S36] [CODEABLE except growth stat = JUDGMENT]

### 3.2 D2 Entry (three branches) (backbone)
- **Thesis:** catch momentum on Day 2 of a fresh burst rather than wait for a mature flag/base —
  by the time a flag forms the explosive part is over. [TTM-B5]
- **Scan:** Day-1 move **10%+ preferred** (20% circuit stocks out of consolidation ideal); 4–6%
  Day-1 is weak; **first day of expansion preferred over day 2/3.** [TTM-B5b]
- **Three Day-2 branches by Day-1 close / Day-2 open:** (a) strong-close → gap-up continuation;
  (b) **Wick Play** — weak close w/ wick, look for slight gap-up open; (c) **gap-down reversal**
  — bad overnight news on a Day-1 circuit/10%+ mover, morning low = max-pressure anchor, enter on
  break of early high, tight 1.5–2% stop. [TTM-B5c, TTM-S13] [CODEABLE — classify into 3 buckets]
- **Why tight stop is justified:** in high-momentum names outcome is binary in 15–30 min; tight
  stop is mathematically justified ONLY with an early, precise entry. [TTM-S12, TTM-S26]
- **Trail:** 21/50 DEMA on 1-min → 21 DEMA on 5-min → higher timeframe once initial burst plays
  out. [TTM-B5d]

### 3.3 Strong Start (Arora; 3-min rule) (LENS_STRONG_START)
- "Strong start is the new breakout." After a base, next day **opens at/above prior high (or ≥
  prior close and holds)**; **the low should not breach the prior day's close** (minor tick
  breaches OK). Entry = cross above prior-day high **after waiting 2–3 min** (don't buy at 9:15).
  [AR-Strong-Start, AR-Entry-Timing] [CODEABLE]
- **Bonus:** 8–10%+ of avg daily volume printed in first 2–3 min (RVOL) — tiebreaker between two
  equal setups. [LENS_STRONG_START]
- **Gap cap:** avoid if gap already 5–6%; more generally **don't chase >10% gap** (>7% = flag as
  secondary) — mid-move entry ruins the math. [AR-Gap-Limit] [CODEABLE]

### 3.4 Pullback-near-support > breakout (regime-conditioned) (backbone)
- In a **strong uptrend**, base-rate bias is price pausing near support (10/21 EMA) and resuming;
  **buying pullbacks near support beats buying resistance breakouts** in such regimes. [TTM-C10]
  [CODEABLE — regime-conditioned entry preference]
- Arora reinforcement: **only buy stocks that have recently undercut the 10 & 20 MA and
  recovered** — weak hands shaken out, cleaner next move. [AR-10-20-MA-Undercut,
  AR-Lower-Low-Defense] [CODEABLE]

### 3.5 IPO base / first-inside-bar (Stocksgeeks + backbone; LENS_IPO)
- IPO bases are **small (days–weeks)**; candle behavior outweighs volume/fundamentals early. VCP
  foundation: progressive range tightening (8→5→2pt), higher lows / held highs. [SG-VCP; LENS_IPO]
- **First inside bar = highest-prob trigger** near IPO-day level; **double inside bar = immediate
  trade** (80% of moves start next day — don't delay). Right-side triggers: inside bar / mini-coil.
  [SG-IPO-First-Inside-Bar, SG-Inside-Bar-Double] [CODEABLE]
- **Crow-bar / Hook / Fast-flag** classify by price-vs-EMA relationship — scale size accordingly
  (crow bar conservative, hook aggressive). [SG-Crow-Bar]
- IPOs work across regimes but are **sentiment-sensitive** (no price history); accept a **4% stop**
  as structurally normal, not "wide," when buying the rock-bottom of the base. [TTM-S25, TTM-S35]
- **J-curve / bar-by-bar (backbone, now with codeable triggers):** an IPO base is *designed* to
  look non-optimistic; bar-by-bar dissection is the microsurgical tool (context = contracting
  volatility; trigger = the downward expansion that releases pressure). [TTM-S48, TTM-S47, TTM-S50]
  Concrete signals from the raw transcripts:
  - **Overlap+contraction reversal signal:** 3+ consecutive bars with **>50% overlap** of the prior
    bar's range + **contracting range** + closes migrating inside = supply absorption → reversal
    imminent. [TTM-H-I3, TTM-H-I1] [CODEABLE — compute overlap % + range-contraction rate]
  - **J-curve entry pattern:** 3+ bars consolidating *down*, then 1 bar of upside expansion smaller
    than the consolidation width = valid entry trigger (not a failure). [TTM-H-I6] [CODEABLE]
  - **IPO 4% stop is TIGHT, not wide** — you're buying rock-bottom after a full reversal; use wider
    SL defaults for IPO (4–6%) than velocity setups (1–2%). [TTM-H-I2] [CODEABLE]
  - **Fire-power ↔ entry quality:** a loose/late entry needs a 20%+ move to go risk-free; a tight
    early entry needs only 2–3%. Flag entries requiring >15% upside-to-risk-free as suboptimal.
    [TTM-H-I5] [CODEABLE]
  - IPOs are high-momentum, low-data → **sentiment/breadth-weighted**, not chart-quality-alone;
    gate IPO confidence on regime/breadth (MBI, EP frequency). [TTM-H-I4] [JUDGMENT / breadth = CODEABLE]

### 3.6 Supply-absorption & squat variants (backbone)
- **VCP over-branding:** tightness (ATR contraction) IS the signal; pocket-pivot volume rules /
  arbitrary EMA-touch rules are noise. [TTM-S14] [CODEABLE — ATR tightness, not volume rule]
- **Downside-expansion failure = absorption buy:** a large red expansion bar (>2× avg range) that
  price then holds above = institutional absorption; buy near its low, stop just below. [TTM-S15]
- **Squat:** breakout candle closes weak → retail panic-sells → next day gaps up into weakness →
  enter on high of the red-open bar. [TTM-S16]
- **ORB only on clean charts + strong demand context** — ORBs on choppy names generate hundreds
  of failures. [TTM-S17]
- **Base quality heuristic (backbone):** consolidation width ÷ visible depth ≥ ~1–1.5; **long
  frustration cycle + shallow depth = better base**. [TTM-F20] [CODEABLE]
- **AOI (Stocksgeeks):** current consolidation must sit **above** the previous weekly
  consolidation; below = down-base w/ overhead supply (secondary tier). Reject if **>40–50% fall
  from recent high** (extreme overhead supply). [SG-AOI, SG-Down-Base, SG-50%-Fall] [CODEABLE]

### 3.7 Shorts (backbone, secondary)
- Best shorts = prior **persistent-momentum** names that then structurally break ("popcorn trades"
  — fall mirrors the rise speed). More than half the small/mid-cap universe sits in Stage 3/4
  decline in bear tapes. [TTM-B11, TTM-C6] [CODEABLE — flag candidate]

---

## 4. RS-then-Momentum: Sequential Filtering

**Backbone rule: RS and momentum are DIFFERENT and SEQUENTIAL, never conflated.** [TTM-C11]
- RS is visible **during the decline** (what holds up best / falls least / closes green on a red
  market day). Momentum is only confirmable **after** the stock has moved. A stock with momentum
  almost always has RS; a stock with RS does not always get momentum. → two separate, ordered
  filter stages. [TTM-C11, SG-High-RS, AR-RS-During-Falls] [CODEABLE]
- **RS is visual, not a rating.** No "RS ≥ 85" gate — a stock rising while the market falls IS the
  future leader, found before any rating catches up. [WK (CH3.1), TTM-S22] **CONFLICT w/ LOCKED
  `RS_FLOOR = 80` — backbone says remove the hard floor; see conflicts list.**
- **Buying-force anchor (Arora/WK):** measure strength as **≥30–35% up from the 65-day (3-month)
  LOW**, NOT nearness to the 52-week high. The 52w-high anchor is exactly what excludes rising-
  off-the-low reversals (BSOFT, Zentec, NCC). [WK (groww 2, CH3.1)] [CODEABLE] **CONFLICT w/
  LOCKED 52w-high pool anchor — see conflicts list.**
- **Velocity/ADR gate (his FIRST filter):** purple-dot count (a dot per >5% move on >5 lakh vol
  in 60d) or ADR20 in top universe percentile; **zero dots = skip regardless of setup.** No such
  gate exists in the tool today. [WK (groww 2, CH3.1)] [CODEABLE]

### 4.1 Persistent-Momentum Scan (backbone; EXACT thresholds — maps to ported `persistency` counts)
- **The scan (bar-count over EMAs, TradeTM-cited exact values):** close above the **10 EMA ≥20
  days, 20 EMA ≥30 days, 50 EMA ≥50 days, 200 EMA ≥150 days.** Bar counts (20/30/50/150) are
  calibrated to catch large structural trends while rejecting noise consolidations and tolerating
  natural pullbacks without a false exit. This maps DIRECTLY onto the already-ported
  `engine/manas_indicators` persistency counts. [TTM-H-III1] [CODEABLE — hard scan; bar counts as
  tuneables, default 20/30/50/150]
- **"Decisive exit" buffer** (Nitin Ranjan's "Trend Persistence vs Moving Averages" Pine script /
  AmiBroker AFL) filters false EMA breaches to avoid whipsaws — a breach is only counted if it is
  decisive. [TTM-H-III2] [CODEABLE]
- **Then sort by ADR** — ADR-descending on the persistent-momentum list separates explosive
  high-beta small/mid-caps from slow large-cap grinders; the ADR-ranked list is the daily trade
  universe. This is TradeTM's volatility filter for scans. [TTM-H-III3] [CODEABLE]
- **Working-professional entry discipline:** on persistent names, **buy pullbacks to the 20/50 EMA,
  don't chase breakouts** — a breakout entry often needs 15–20%+ upside to go risk-free; a pullback
  entry goes risk-free in 2–3%. [TTM-H-III4] [CODEABLE — alert within 1–2% of 20/50 EMA; suppress
  high-extension alerts]

---

## 5. Risk & Sizing Law (backbone-anchored)

The most conflict-dense section; backbone (TradeTM) values are the doctrine of record. Numeric
conflicts vs the tool's LOCKED profiles are listed here and carried to PLAYBOOK_TO_TOOL_MAP.

| # | Rule (backbone value) | Cite | Tag |
|---|---|---|---|
| R1 | **Position size = risk₹ ÷ (entry − stop).** Never a fixed % of account; size floats with stop width. | TTM-D1, TTM-S27, AR-Position-Size | [CODEABLE] |
| R2 | **Per-trade risk ~0.65% (velocity); ~0.5% baseline.** Keeps max open risk ~2–2.5%. | TTM-D2, TTM-S28 | [CODEABLE] **CONFLICT vs LOCKED aggressive 0.75–1.0% RISK_ON** |
| R3 | **Max 3–4 concurrent tight-SL initiations.** Adding beyond this before earlier trades go risk-free spikes open risk → correlated stop cascade. India ≠ US (Qullamaggie 15). | TTM-D2, TTM-S31, TTM-S56 | [CODEABLE] **CONFLICT vs LOCKED max_open_positions 5 (aggressive) / 6 (balanced)** |
| R4 | **Portfolio open-risk: ~2–2.5% typical, ~4–5% hard ceiling.** Ceiling breach = market-quality warning (setups trigger, don't follow through). | TTM-D2, TTM-D3, TTM-S30 | [CODEABLE] **CONFLICT: TTM 4–5% ceiling is HIGHER than LOCKED open_risk_cap RISK_ON 3.0 — both recorded** |
| R5 | **Initial stop >4% materially cuts expectancy** — wait for a tighter pivot instead. IPO/shakeout exception: 4% is structurally normal. | TTM-D4, TTM-S19, TTM-S35 | [CODEABLE] |
| R6 | **Per-trade position cap ~40% of portfolio.** Reduce size ahead of results without a profit cushion. Arora typical working size 25–30%. | TTM-D5, TTM-S29, AR-Growth-Formula | [CODEABLE] |
| R7 | **Stop width directly sets achievable trailing size at equal ₹-risk** — tighter stop + earlier entry yields 2–4× the portfolio impact on the same winner (JBMA/Prakash). Tight 2% stop → 25% position; wide 8% → 6.25%. | TTM-D6, TTM-S18, AR-Tight-Stop | [CODEABLE — scenario sim] |
| R8 | **Do NOT import US 7–10% stops** (O'Neil/Ryan/Minervini) — calibrated to a 4× larger, more-liquid, smaller-spread universe. India SL defaults must be a configurable India-context set; and **nature-relative** (small caps run wider than large caps). | TTM-D7, WK mismatch 3 | [CODEABLE] **CONFLICT vs LOCKED absolute stop caps 7.5/8.0 — see conflicts list** |
| R9 | **Slippage buffer 0.3–0.6%** on top of a 1–3% base stop — a 2% slip nearly doubles the risk taken. | TTM-D8, TTM-S4 | [CODEABLE] |
| R10 | **Portfolio-scale shift (~₹1cr+):** move from tight-SL velocity/swing toward positional strategies (longer holds, wider risk, liquid names). | TTM-D9 | [CODEABLE — size-conditioned setup mix] |
| R11 | **MTF funds capital, not risk** — size on base (unleveraged) capital only; leverage never scales the position. | TTM-D1, TTM-S34 | [CODEABLE] |
| R12 | **Hard stop always in the system — "no such thing as a mental stop-loss."** 50% drawdown case traced to a mental stop. Never waive it for a "quality"/fundamentally-strong narrative (80-50 rule). If stop hits: exit at market immediately, no second-guessing (incl. gap-downs below stop). | TTM-D11, TTM-D13, AR-Stop-Hit, AR-RVNL | [CODEABLE — no position without a live SL order] |
| R13 | **Far-trailing stop as alert (2–4% away), not a placed order** — avoids being shaken out on erratic moves while capturing unrealized profit. **Internal TTM conflict w/ R12** — resolved by backbone: the INITIAL near-price hard stop is mandatory (R12); the far-trailing-as-alert exception (R13) applies only once price has trailed well above the hard-stop level. | TTM-D10, TTM-S37 | [CODEABLE — distinguish initial vs far-trailing] |
| R14 | **Arora trailing math:** move stop ₹0.50 per ₹1 rise → break-even in a ~6–7% move (1R risk → 0.25R). **Pyramid: start 10%, add on proof, each add ≤ previous.** | AR-Trailing, AR-Pyramiding | [CODEABLE] |
| R14b | **Pyramid-to-30% ladder (backbone, working-professional):** initiate at **1% risk** on a clean pullback, then add up to ~4 more 1%-risk tranches on successive higher-lows as the trend proves — reaching **~30% portfolio allocation only after the trade is already in profit.** Stage the adds on breakeven + higher-low confirmation. | TTM-H-V1 | [CODEABLE — 1% entry + {1% per next pullback after +X%} ×4] |
| R15 | **Stocksgeeks portfolio DD hard stop (~3%):** halt ALL trading when hit — do not merely shrink size. Graduated deployment on MBI green: day1 10%, day2 2–4×, up to 70–80% if MBI+setup hold; anticipation entries at 0.1–0.2× size. | SG-Drawdown-Limit, SG-Size-Scaling, SG-Anticipation | [CODEABLE] |
| R16 | **Two viable India paths only:** (1) size big + hold magnitude, or (2) size big + many velocity trades. **Scatter of many small trades is mathematically doomed.** | TTM-S57 | [JUDGMENT] (strategy router) |

**R-multiple discipline (backbone):** R-targets (4R/6R/10R) are **indicative guides, not
algorithms** — R depends on stop width which depends on volatility, so a "4% move" means different
things across names. **Stop-loss execution = mechanical/non-negotiable; profit-taking =
discretionary/situation-blended.** Normalize R comparisons by ATR/₹-move, not raw %. [TTM-E6, TTM-E7,
TTM-D6] [CODEABLE: ADR-normalized R; JUDGMENT: the profit-take blend itself]

---

## 6. Trade-Management Templates by Setup Type (F13/F16 — backbone)

The backbone architecture: register each setup with **≤4 trade-management rules** under one of
**three templates keyed to trade intent**. [TTM-F13]

| Template | Intent | Setups | Management | Named failure mode if mismatched |
|---|---|---|---|---|
| **Velocity** | fast feedback, tight stop, quick turnover | momentum burst, D2, breakout, VCP, pullback | tight SL, trail LTF MA, sell into strength / quick small gains | — |
| **Magnitude** | hold the big move, all-or-nothing | EP, IPO base, high-conviction theme | wider structural stop, sell into *weakness* (21EMA break), pyramid on pullbacks | managing too tightly like a frequency trade → **shakeouts** |
| **Hybrid** | blend | context-dependent | mix per situation | — |

**The named failure modes (must be enforced as a mismatch flag):** (1) managing high-expectancy
IPO/EP setups too tightly like frequency trades → shakeouts; (2) all-or-nothing on high-frequency
lower-expectancy momentum bursts → squats. **Setup-type MUST dictate template.** [TTM-F16]
[CODEABLE — flag template/setup mismatch]

**Persistent vs Absolute momentum = OPPOSITE execution rules (backbone; critical).** The SAME
behavior (a pullback to a moving average) is a *buy* in a **persistent** (slow, sustained) trend
but a *stop-out* under **absolute** (explosive, high-velocity) rules. Applying a fixed-% stop to a
persistent name makes it "rotate around a moving average and hit your stop again and again."
→ tag each setup **persistent vs absolute at entry** and enforce the matching SL/trail: persistent
= wider structural stop, 50 DMA trail, buy pullbacks, pyramid; absolute = tight stop, LTF trail,
breakout entry, quick exit. This EXTENDS the Velocity/Magnitude split above and must gate template
selection. [TTM-H-II1] [CODEABLE — tag + enforce; flag mismatches]

**Character drives the template, not the pattern name.** "You don't have only one way to buy a
pullback." Read whether the stock is fast-and-spiky or slow-and-grinding (proxy via ADR/volatility
tier) and match execution to character; a 20% move in a slow name is managed completely differently
from 20% in a fast name. [TTM-H-IV2] [PARTIAL — flag character via ADR tier, recommend template;
final choice JUDGMENT]

**Story-bucket tagging over micro-DD.** Traders don't need granular fundamentals — bucket the
catalyst story-type (regulatory approval, turnaround, sector tailwind, new market/product) and use
it as a conviction/catalyst-strength signal. [TTM-H-IV1] [CODEABLE — story-bucket taxonomy tag]

**Setups have no inherent edge** — payoff structure (win/stop/context definition) does, and context
must gate any setup-tag (an EP-follow-through flag ≠ a climactic-move flag). Any setup-scoring
logic must carry context tags (prior-move stage, regime) alongside the pattern tag. [TTM-F12]

---

## 7. Exits

- **Day-low break is its own trigger** — often triggers a deeper stop before the % SL; nearly all
  stop-outs happen same-day. [TTM-E2] [CODEABLE]
- **MAE/MFE calibration (backbone methodology, not hardcoded numbers):** in the author's journal
  >85% of eventual 8%-stop-outs had already breached 3%; a 3% stop would not have changed win rate
  but doubled trailing size / 4×'d R-speed. Track MAE/MFE per trade to calibrate stop width from
  the user's *own* distribution — do not hardcode "3%". [TTM-E1, TTM-S43, TTM-F5] [CODEABLE — calc; the % is JUDGMENT/personal]
- **Objective-conditioned trail:** intraday objective → intraday MA trail (50 DEMA 1-min → 10/20
  DEMA 5-min); swing objective → higher-timeframe trail. [TTM-E5, TTM-B5d] [CODEABLE]
- **Structure-break reading (exit signals):** "eating your own bottom" (sequence of lower closing-
  lows without a decisive break) [TTM-B8]; "tennis-ball action" breaking down (stops snapping back
  from pullbacks) [TTM-B10]; the deep-stop "fight-back" tactic — hold with a wider stop while a
  name absorbs selling (long lower wicks, upper-half closes), exit on the first visible behavior
  change to one-way selling [TTM-E4]. [CODEABLE partial — wick/close-position "fight-back" score;
  final call JUDGMENT]
- **Shakeout vs real weakness:** momentum stocks shake out because "fear is gunpowder" — a small
  spark → big drop, then fast recovery if demand remains. Don't panic-exit on a single sharp-
  decline-then-recover bar with trend context intact. [TTM-B9] [JUDGMENT / partial]
- **Arora sell-into-strength:** sell 40% at first acceleration (90° move + ~6× volume), remainder
  at largest-volume bar / major resistance; **never sell on weakness** (for velocity trades).
  **Half-sell at 15–20% gain, trail the rest**, no predetermined target. [AR-Selling-Into-Strength,
  AR-90-Degree, AR-Half-Sell; SG-Trailing] [CODEABLE]
- **Sell-in-strength ratio is a portfolio decision, not chart-driven** — over-selling into strength
  caps home-run impact (a real 25% portfolio confirmation-cost from selling 50% at 4R on a 105R
  runner). Tie sell-% to conviction, not a fixed default. [TTM-E3] [JUDGMENT; track realized-vs-
  optimal ratio = CODEABLE]
- **Two kinds of letting go** (profit vs capital) and "if you scoop small change you'll never get
  big" — the regret of an early exit on a later home-run is the necessary cost of ever holding a
  real winner; a fizzler and a runner look identical at day zero. [TTM-E8, TTM-E9] [JUDGMENT]

---

## 8. India Calendar / Event Effects

- **Results season gates the EP workflow.** EP scan is the *primary* active setup only in the
  post-results window; "how good the EP season was" is itself a sentiment signal. Filter EP scan
  to after-hours results; activate on an NSE results-calendar-aware window. [TTM-H3, TTM-S53] [CODEABLE]
- **Known macro-event days (budget, elections, Fed):** pre-plan scenario branches, do NOT blanket-
  avoid. Auto-generate an "if gap-down >X% → plan A; if flat/small → plan B" branch planner.
  Budget-day 5–6% gap = worst case, already discounted. [TTM-C13, TTM-H1] [CODEABLE — event
  calendar + scenario planner]
- **Arora event caution:** market gets "tricky" and takes stops the week *before* big events;
  the damage is in the collapse week; wait 1–2 weeks after. Survived demonetization, COVID,
  elections, Brexit "only because of risk management." [AR-Before-Big-Events, AR-Indian-Conditions]
  [CODEABLE — pre/post-event pause flag]
- **Gap-down mornings:** most damage is in **minute one**, not the 15th; wait ~10 min post-open,
  trail stop to the first-bounce low rather than reacting emotionally — "panic is contra
  opportunity because everyone panics on the same thought." [TTM-C12] [CODEABLE]
- **Corporate actions (Arora):** earnings ≤3 days away → can still enter, but require ~8–10%
  cushion by earnings day else close pre-event; **dividends → usually hold through**; **splits →
  close BEFORE record date** (new shares take 10–15 days to credit; illiquid names leave you
  helpless). [AR-Earnings, AR-Dividends, AR-Stock-Splits; TTM-S32] [CODEABLE — calendar flags]
- **Market-crash correlation:** in a broad crash even the strongest stocks get pulled down (Oct
  2008 Nifty 6400→2600); RS is insufficient, tighten stops / cut size regardless of chart beauty.
  [TTM-S55] [CODEABLE]
- **April 7 2025** (tariff gap-down-then-reversal) cited as the year's best pyramiding day — sharp
  macro gap-downs can create the best entries if the theme was already in play. [TTM-H4] [JUDGMENT — case study]

---

## 9. Psychology → Coach-Line Bank (ready-made sentences with cites)

These are the **non-codeable** nuggets rendered as coach lines the tool can surface verbatim. All
[JUDGMENT].

- **"Trade the market you are in, not the market you wish you were in."** — the core refrain. [TTM-F15]
- **"Trade your P&L, not the chart."** Tactics (tight stop) don't scale a portfolio; the strategic
  layer does. [TTM-B7]
- **"90% of trade failures are entry failures — not stock, setup, or TA failures."** Journal entry-
  quality separately from setup-quality. [TTM-F17]
- **"Trade what the market is giving you, not what I taught you — memorization is the enemy of
  understanding."** Stages blend (2↔1, 3↔4); read the chart, don't force a template. [TTM-F18]
- **"Think in your anti-thesis"** — your thesis is retail-framed; think as a fund manager, then
  re-apply as a retailer. (→ dedicated "fund manager" debate persona.) [TTM-F19]
- **"It's not 10,000 hours, it's 10,000 iterations."** For new traders overtrading is a low-cost
  learning tool; build with frequency + speed (velocity trades first). [TTM-S41, TTM-F4, TTM-F8]
- **"Uncomfortably aggressive."** Scaling is a mental-barrier problem; even Qullamaggie/Minervini
  had 10–50% drawdowns scaling — FAITH in recovery, not probability-comfort, differentiates. [TTM-F9]
- **Prospect Theory:** the pain of a −1R exceeds the joy of a +1R, so a 35–65% win rate can feel
  net-negative even while profitable. Anger/depression (not just fear/greed) are the constant
  undertones and can be super-performance drivers if mapped via a 5-step tilt framework. [TTM-F1, TTM-F2]
- **Decision Bell Curve (A/B/C-game) + Inchworm** — improve the A-game ceiling and C-game floor
  alternately. [TTM-F3]
- **"There are no objective rules that fully define price action"** — over-mechanizing shrinks risk
  appetite into "managing risk" instead of "taking risk." The tool supports discretion, it does
  not replace it. [TTM-F6]
- **Seek the cause, not the effect** — enter ahead of the crowd's decision point so their order
  flow adds to your position (patterns/indicators are "shadows"). [TTM-F7]
- **Visualization** (chess metaphor: run scenarios without moving pieces; "flip the board" to the
  trapped seller's view). [TTM-S46, TTM-S49]
- **Distribution of outcomes:** ~5 losers, 3 small gains, 1–2 home runs per 10 — the 1–2 home runs
  carry the year; don't optimize against them. [AR-Distribution]
- **Regret is part of the business — stand by your decisions.** Confusion is not good for this
  business. [AR-Regret, AR-RVNL]
- **Screen-checking is fear-driven** — cut size below half and trade 5× to regain confidence. [AR-Screen-Checking]
- **Stopped-out ≠ dead** — track it on a separate watchlist; if it sets up again, re-enter
  (sometimes larger — weak hands are gone). [AR-Stopped-Out-Reentry]
- **Never trade with borrowed family/friend money** ("uncle/bhaiya" pattern) — use MTF/MIS if you
  need capital, never social lending. [TTM-D12]
- **Read O'Neil starting with the risk-management chapter (Ch 13).** [AR-Book-Recommendation]
- **Peer-group EP tracking** (5–8 traders sharing a QoQ/YoY EPS+sales sheet) is the concrete India
  mechanism that makes EP tracking sustainable for working professionals. [TTM-F10] (→ [CODEABLE]
  as a shared post-market-results tracker feature)
- **"Play dumb" in execution.** Intelligence belongs to the analysis phase; once in a trade, being
  "dumb enough" to mechanically follow predefined rules beats intellectual discretion. Reconciles
  with [TTM-F6]: intuition is *built* through post-trade review, but *execution* itself is
  mechanical → design principle = **hard-enforce rules, soft-suggest judgment calls.** [TTM-H-II2]
- **"Never doubt the trend."** Trend-following means you will always give back a part of the profit
  at exit — accept it; the only risk that matters is the stop loss, not the % giveback. [TTM-H-II4]
- **Quantify fear with a number.** "Ignorance creates fear" — the moment you assign the exact ₹ you
  will accept losing from the peak, the dread vanishes; you don't need to predict the top. Make
  "max ₹ loss I accept" a required input field on every trade. [TTM-H-II3] [metric = CODEABLE]

---

## 10. Cross-Source Meta-Cautions (design-level)

- **Concept over process** (Pradeep Bonde): any imported US technique (e.g. 9-Mn-volume scan) must
  be re-derived for Indian market structure, not copy-pasted. [TTM-F22]
- **Timeframe changes the emotion cycle** — a daily-chart shakeout pattern does not replay
  identically intraday; price is fractal only insofar as human emotion is fractal on that
  timeframe. Don't transplant a daily rule to intraday mechanically. [TTM-F21]
- **Stage classification should output a confidence/blend across adjacent stages**, not a hard
  single label. [TTM-F18] [CODEABLE partial]
- **Sector taxonomy must be curated, not vendor-default** (generic "Auto Manufacturers" lumps
  Maruti with a ₹40L radiator maker). Theme detection: **Bottoms-Up preferred** (top-mover
  clustering), confirm price-first, require **5–10+ names** moving to call a rotation. [TTM-G1,
  TTM-G2, TTM-G3, AR-Sector-Rotation, SG-Sector-Rotation] [CODEABLE: multi-name confirmation;
  JUDGMENT: catalyst identification]

---

*End INDIA_PLAYBOOK.md — every rule carries a cite; conflicts vs LOCKED thresholds are enumerated
in `PLAYBOOK_TO_TOOL_MAP.md`.*
