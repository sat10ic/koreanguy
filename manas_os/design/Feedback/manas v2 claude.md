# Manas AI Trading OS — Consolidated Direction Report

*A single reference bringing together three threads from our discussion, with nothing removed:*
*(1) how to turn the tool from a "3/10 free-data reskin" into a real edge, (2) the comparative*
*survey of trading setups that have worked in India recently, and (3) the crucial correction about*
*how evidence quality should — and should not — govern which setups the tool trusts.*

*This is a synthesis of conclusions we reached together, grounded in the tool's actual state and*
*data. It is a design/direction document, not financial advice; every base rate here is a prior to*
*be validated on your own journal before you trust size to it.*

---

# PART A — Turning Manas into a Real Edge (the tool roadmap)

## A.0 The starting diagnosis (your own honest self-assessment)
The tool scored **3/10 on edge — "a well-built reskin of free data."** Everything currently
rendered — RS, delivery %, pullbacks, pocket-pivots, breadth, sector heat — is free on
Chartink / TradingView / ChartsMaze. The three things that would *be* an edge exist only as stubs
or are actively broken:

1. **Selectivity** — the gate passes 80 names; a real edge is a feed that says **NO**.
2. **One trustworthy opinion per symbol** — the app contradicts itself (readiness vs exit-state;
   "Breadth 67% strong" rendered inches above "Breadth unavailable"), which is fatal for a
   *judgment* tool.
3. **The compounding journal → outcome → learnings loop** — the only un-copyable asset, currently
   an empty form.

Plus: regime discipline isn't enforced downstream, and data-integrity leaks (EPS +55250%, a 27%
stop on the #1 pick, the "+-5%" sign bug) kill credibility.

## A.1 The core reframe
The alpha is in **selectivity, discipline, and the compounding private dataset — not in the
indicators**, which are commodities. Concretely, the target is: *a regime-gated feed that refuses
most days + pre-committed trade plans with real risk math + a journal that learns YOUR
per-setup/per-regime expectancy and feeds it back — plus a disciplined live-alert loop
(manual-confirm via Telegram) so the process is executed, not just displayed.*

## A.2 Binding constraints (any recommendation must respect these)
- **Rules-first / no black-box scores** — every number decomposes into visible, named evidence a
  beginner can inspect. No opaque ML confidence as the trigger.
- **Manual execution only** — the tool proposes; a human confirms every entry/exit (app or
  Telegram). No auto-order routing, ever (keeps it outside SEBI's retail-algo framework and
  preserves the human veto). Human-in-the-loop is a *feature*.
- **Single-user, localhost, public data only.**
- **Anti-mashup** — one metric = one number app-wide; one ranked number per screen; no competing
  scores; no parallel engines; no dormant code.

## A.3 Data you HAVE vs LACK (every recommendation is tied to this)
**Have:**
- **NSE bhavcopy** (`sec_bhavdata_full`): daily OHLCV + **delivery %** per EQ symbol (~862k rows,
  2025-03 → 2026-07).
- **ChartsMaze dumps**: RS ratings, 26 technical screeners (VCP/tight/momentum/shakeout/gap etc.),
  sector + industry RS, RRG, **ASM surveillance flags**, per-stock EPS/sales/OPM growth (QoQ/YoY),
  disclosure feeds (order-wins, announcements, bulk-deals, insider, circuit-revision,
  episodic-pivot), partial market cap. **Disclosure feeds are mostly on-disk, un-ingested.**
- **Fyers API**: live + intraday candles, websocket, quotes. Live loop not built; pre-open coverage
  unconfirmed.

**Lack:** full balance-sheet fundamentals (ROE/D-E/P-E/book value/margins), consensus/forward
estimates, options data, tick history beyond Fyers. *Do not build a thesis on data you don't have;
where a technique needs it, use a proxy from what you have.*

## A.4 The five improvement areas (with the two special-focus engines)

### Area 1 — High-accuracy ENTRY signals (feed + Telegram)
- **Fix score saturation with multiplicative veto-gates, not additive points.** Additive scoring
  saturates (80 cards, 67 graded A+, top 12 all ≥97.5). Replace with veto/multiplicative logic so
  **100 is rare** and a single failed condition caps the score. Calibrate so grades mean something.
- **Regime is a hard gate on which entries even qualify** (not a cosmetic dial) — see Area 4.
- **"Fresh-leg" detection** — enter near the *origin* of a move, not extended: bar/base counting,
  distance-from-breakout, leg-number logic (avoid entering at "bar six").
- **Gap-acceptance vs gap-rejection** for episodic pivots (gap up + close in top of range = accepted).
- **Opening-range / pre-open behavior** for next-day entries (you have Fyers intraday + websocket).
- **The measurable question:** what separates a 60%+ setup from a 40% one in *this* market —
  answered by confluence that raises *precision*, not breadth.
- **SPECIAL FOCUS — the Telegram signal engine:** define what triggers a **push** vs a **digest**;
  exact alert payload fields (symbol, setup type, evidence chips, entry trigger, stop, size at
  risk %, R:R, regime context); a human-confirm flow (app or Telegram); spam/alert-fatigue
  prevention; and a way to **measure alert precision** over time. Keep the runtime deterministic;
  any ML stays offline (calibration/validation), never the live trigger.

### Area 2 — Tight RISK planning & management
- **Stops both tight and valid:** day-low / ATR / structure-based; default to structural.
- **Hard cap on stop distance** — you currently leak 27% stops. Impose a maximum acceptable swing
  stop (research pointed to roughly an **~8% cap**) and a rule: **the tool refuses to log or alert
  a trade whose risk math doesn't clear the bar.**
- **Position sizing tied to stop distance and capital risk %**, with **regime-adjusted risk caps**
  and a **half-Kelly ceiling** (fractional Kelly, computed off the journal, never full Kelly).
- **Pyramiding rules** on pullbacks; India-specific hazards baked in (circuit limits capping
  same-day risk-free exits, illiquid-name slippage, ASM/GSM freeze risk).

### Area 3 — PROFIT maintenance / drawdown avoidance
- **Trailing methods** (10/21-EMA, ATR, structure) and *when to switch between them*.
- **Partial booking into strength vs holding**; the "sell into weakness on a new trend / sell into
  strength on extension" heuristic.
- **Exit-signal composites** (distribution days, MA loss, downside-reversal).
- **SPECIAL FOCUS — the portfolio loss-avoidance engine:** total **open-heat caps**, **per-sector
  caps**, **correlation clustering** from the price data you have, **daily-loss circuit breakers**,
  **equity-curve-based throttling** (reduce size after drawdown), and recovery rules — so a
  single-user account never takes a large drawdown. The asymmetry that compounds: keep more of each
  winner, get stopped small on losers.

### Area 4 — Smart REGIME awareness (made actionable, enforced downstream)
- Beyond a breadth dial: the regime should dynamically govern the **whole tool** — how many names
  the feed shows, what stop/size is allowed, which setup types are favored vs suppressed, and when
  to sit out entirely.
- Inputs: breadth/participation, index trend structure, volatility regime, sector rotation (RRG),
  and **"days like today" historical-analog matching** against your own history.
- **Hard wiring (the key fix):** regime → max cards in feed → max open risk → alert thresholds →
  eligible setup types. This is what makes "SELECTIVE" actually serve fewer, not 80, names.

### Area 5 — Market-MECHANICS awareness (Indian NSE specifics — the structural edges)
- **Circuit dynamics** (2/5/10/20% bands; circuit-to-circuit momentum; distinguishing
  information-driven from operator-driven circuits).
- **Delivery %** as an accumulation / pump-detection signal.
- **ASM/GSM transitions** as regime signals.
- **Post-announcement drift (PEAD)** in under-covered small caps — the informational edge (your
  order-win/announcement disclosure feeds, currently un-ingested).
- **Bulk/block-deal footprints**; **defensive "pump-signature" detection** as an exclusion filter.
- These are the real structural edges a retail single-user can exploit that institutions and free
  sites don't systematically work.

## A.5 The cross-cutting moat — the journal → outcome → learnings loop
Log every taken/skipped setup → T+5/10/20 forward returns → per-setup/per-regime expectancy fed
back onto future signals. Design it to sharpen accuracy over time **without overfitting a small
sample**: Bayesian shrinkage / hierarchical pooling toward priors, walk-forward validation, and a
**minimum sample size before its output is trusted**. This is the un-copyable asset and the single
biggest missed opportunity today (it's currently an empty form).

## A.6 "AI" under the no-black-box constraint
Reconcile AI/ML with full explainability: use interpretable models (monotonic constraints,
scorecards, GAMs, decision lists), and keep **ML for offline calibration/validation while the
runtime stays deterministic and rules-decomposable.** No opaque confidence number is ever the
trigger.

## A.7 Benchmarks worth borrowing from (not copying)
Finviz (Elite), Deepvue, MarketSmith/MarketSurge (IBD), TrendSpider, TradingView alerts, Chartink,
and newer swing-copilot/AI-screener entrants — for signal delivery, watchlist heat, portfolio risk,
and alert UX. Synthesize original solutions; don't limit to them.

## A.8 The "banned features" line (from the tool-review discussion)
The most valuable "AI feature" is the willingness to say **"no read — wait"** when signals conflict
or data is missing. Never ship confident astrology — "smart money anchor at ₹267.67," "ML consensus
flipped bullish / detecting accumulation ahead of price discovery," simultaneous contradictory
labels (Accumulation + Distribution), confidence % on discretionary calls, or auto-generated
paisa-precise "trade plans." When a field is missing, print **"N/A from source,"** don't invent it.

---

# PART B — Setups That Have Worked in India (comparative evidence survey, 2018–2026)

*Emphasis 2020–2026. Two evidence tiers throughout: **quantified/backtested** vs
**practitioner-documented** (anecdotal/unverified). Ranked by evidence quality below.*

## B.1 The evidence-quality ranking (strongest → weakest)
1. **Cross-sectional momentum** — *strongest*. Live, investable proof exists: the **Nifty 500
   Momentum 50** and **Nifty Midcap150 Momentum 50** factor indices. Backtested and index-replicated.
2. **Post-earnings-announcement drift (PEAD)** — *strong, academically supported*. Indian studies
   find meaningful drift (roughly **~4.8–6%**) after earnings surprises, concentrated in
   under-covered small/mid caps.
3. **52-week-high breakouts / Stage-2 Weinstein breakouts** — reasonable evidence, tied to the
   momentum literature.
4. **Pullback-to-rising-MA entries, pocket pivots, VCP** — practitioner-standard; some backtest
   coverage; effectiveness is regime-dependent.
5. **Mean reversion / short-term reversal** — mixed academic evidence in India (short-term reversal
   exists but is a different beast from momentum; costs and execution matter).
6. **IPO bases** — *weak evidence*, heavily survivorship-inflated; India's 2021–2026 IPO/SME wave
   produced glamorous winners *and* a graveyard nobody tallies.
7. **High-tight flags / high-ADR discretionary momentum** — *weakest formal evidence*; most
   operator-prone and regime-dependent; the "doubled in 8 weeks" names sit in the low-float tier.

## B.2 Setup-by-setup

### IPO bases
- **What:** first base after listing, deeper primary bases, IPO shakeout-then-recover, mini-coil /
  TVCP-style tight IPO structures.
- **Evidence:** *Quantified* — thin; IPO anomaly literature exists but clean base-breakout base
  rates for India are scarce. *Practitioner* — heavily promoted by Indian educators; track records
  are self-reported and survivorship-inflated.
- **When/where:** thrived in the 2021 and 2023–24 primary-market booms; concentrated in mid/small/SME
  tiers — exactly the operator-prone, ASM/GSM-risk, circuit-locked tier.
- **Failure modes:** the loudest-marketed, least-measured setup; the denominator (failed IPO bases)
  is invisible.

### High-ADR momentum names
- **What:** Qullamaggie-style preference for high Average-Daily-Range movers.
- **Evidence:** *Quantified* — momentum works in India, but the specific high-ADR *preference* is
  not well-established here. *Contested practitioner view:* **lower-ADR names may scale better in
  India** — an explicit reversal of the US preference. Investigate both; don't hard-code the US view.
- **Where:** high-ADR concentrates in small/mid, the operator tier — highest edge and highest
  manipulation in the same place.

### Mean reversion / short-term reversal
- **What:** oversold bounces, snap-backs, undercut-and-rally, gap-down reversals, 7+ down-day
  reversals in uptrending stocks.
- **Evidence:** *Quantified* — short-term reversal is documented in Indian equities but is
  regime-sensitive and cost-sensitive; momentum generally dominates over swing horizons. *Practitioner*
  — the reversal/"U-turn after 7+ down days" bucket is used by discretionary Indian traders.
- **When:** more useful in choppy/defensive tapes than in strong trends.

### Flags & tight continuation (bull flags, high-tight flags, VCP, inside-bar coils, Darvas)
- **What:** bull flags; **high-tight flag** (O'Neil/Soreide: ~90–100% move in 4–8 weeks then a
  shallow tight flag); VCP (volatility contraction); tight-range coils; Darvas boxes.
- **Evidence:** *Quantified* — sparse for the discretionary variants (they're illegible to clean
  backtesting). *Practitioner* — VCP and flags are the core of the Minervini/Qullamaggie-influenced
  Indian scene; track records self-reported.
- **Caveat:** the high-tight flag's defining trait (double in weeks) selects for the low-float /
  surveillance / operator tier where the tight stop is least reliable.

### Episodic Pivots (EP) / PEAD
- **What:** earnings gap-ups on neglected stocks (Qullamaggie/Bonde-style), order-win/announcement
  gaps, and post-earnings-announcement drift.
- **Evidence:** *Quantified* — **the best-supported "glamorous-adjacent" setup**: Indian PEAD studies
  show real drift (~4.8–6%), strongest in under-covered small/mid caps. *Practitioner* — widely used.
- **India complications:** circuit limits lock catalyst gaps (entry compresses into pre-open + first
  15 min); the drift window (T+5/10/20) is exactly what your journal loop measures.

### Other setups with Indian evidence
- **52-week-high breakouts, Stage-2 Weinstein breakouts** — tied to momentum evidence.
- **Pocket pivots, pullback-to-rising-MA (10/21/50 EMA) entries** — practitioner-standard.
- **Sector-rotation leaders / thematic momentum baskets** — the **PSU/defence/railways run of
  2022–24** was one of the most documented Indian momentum phenomena; sector-RS/RRG-driven (data you
  already compute).
- **Rerating breakouts after long bases; ANTS-style accumulation; anchored-VWAP reclaims.**
- **Momentum-index replication** — the Nifty Momentum indices are the cleanest live proof of factor
  momentum in India.

## B.3 Comparative synthesis
- **Strongest, most defensible in India recently:** cross-sectional momentum (index-proven) and PEAD
  (academically supported, structurally available to retail).
- **Regime-dependent:** breakouts/flags/thematic momentum thrive in the DII/SIP shallow-correction
  era but die in corrections; mean reversion is the choppy-tape tool.
- **Contested:** high-ADR preference (lower-ADR may win in India).
- **Likely overhyped / least-measured:** IPO bases and high-tight flags — glamorous, promoted,
  survivorship-inflated, operator-prone.
- **Structural backdrop:** the post-2020 DII/SIP flow shift made corrections shallower (~10–12%) and
  trends more persistent — favouring continuation/momentum — **but this is a regime, not a law**;
  if domestic flows reverse, deep corrections and the harsher old pattern can return.
- **Practical fit (long-only, T+1, STT costs, no overnight shorting):** momentum + PEAD + thematic
  leadership fit a retail cash swing trader best; short-reliant and deep-reversal styles fit worst.

---

# PART C — The Direction Correction: Let Evidence Set Priors, Let the Journal Set Grades

*This is the most important conclusion, and it revises Part A's naive reading of Part B.*

## C.1 The first-pass direction (from the survey)
Read literally, the survey inverts the tool's current emphasis: the tool leads with **IPO bases,
high-tight flags, high-ADR** (bottom of the evidence pyramid) while underweighting **cross-sectional
momentum + PEAD** (top). The first-pass redirection was:
1. **Re-anchor the feed on evidence-graded setups; make evidence tier a visible property of every
   card,** and cap a setup's score ceiling by how good the evidence for that setup *type* is in
   India. (Attacks saturation *and* aligns with what works.)
2. **Ingest the disclosure feeds and build the PEAD engine — highest-ROI move.** PEAD in
   under-covered Indian small/mid caps is the one edge that's *both* academically supported *and*
   structurally available to a retail single-user; the feeds are already on disk, un-ingested. EP
   done properly = catalyst (disclosure) + drift window (T+5/10/20, which the journal measures).
3. **Turn "high-ADR" into a question the journal answers, not a default** — tag ADR tier, let the
   expectancy loop report which tier pays *for you*; don't hard-code the US preference. Gate the
   low-float "doubled in weeks" names through delivery-%/ASM/pump-signature exclusion first.
4. **Wire regime-dependence per setup, not just globally** — in DEFENSIVE, suppress breakout/flag
   setups and (if anything) favour supported mean-reversion snap-backs; in RISK_ON, open up
   continuation/EP. Regime changes *which setup types* are eligible, not just *how many* cards.
5. **Add a thematic-momentum-basket lens** — the PSU/defence/railways-style phenomenon is
   sector-RS/RRG-driven, which you already compute.

## C.2 The objection (yours, and it's correct)
**Absence of evidence isn't evidence of absence.** Momentum and PEAD have strong "evidence" partly
because they're *researchable* — mechanical, backtestable, publishable. The glamorous setups
(IPO bases, high-tight flags, high-ADR discretionary trades) resist study because they're
judgment-heavy and rare. So a naive "evidence quality" ranking rewards **legibility** — how easy
something is to study — and can punish setups whose edge is real but lives in discretion. That
distortion is real and was under-weighted in the first pass.

## C.3 But the objection cuts both ways (the decisive point)
The glamorous setups don't just lack *academic* papers — they lack **disconfirming** evidence too,
because their only track record is **self-reported by people selling the setup.** Nothing stops a
hundred educators from posting five winning flags and never the fifty that failed. So "not much
research" doesn't make them neutral-unknown — it makes them **unmeasured**, and
**unmeasured-but-loudly-marketed is a worse epistemic position than unmeasured-and-quiet**, because
that's the exact condition under which survivorship bias runs wild (no denominator anywhere).

## C.4 The resolved direction (this supersedes C.1's naive version)
- **The evidence-graded ranking tells you where the base rate is *known and defensible*** (momentum,
  PEAD) — anchor on that.
- **It does NOT tell you the glamorous setups don't work** — only that nobody, including their
  promoters, has proven they do. Treat them as **unmeasured, not disproven.**
- **The right response to "unmeasured" is to measure them yourself.** Your journal → outcome →
  expectancy loop **is a research engine** — it can generate the missing evidence that academia
  never will, on exactly the discretionary setups the papers can't touch. Give it a year and you'll
  hold something almost nobody in India has: a **private, honest base rate for the glamorous setups —
  including the losers the educators never show.**

**The rule:**
> **Don't let evidence-quality decide which setups you *trade* — let it decide which ones you
> *trust on day one* versus which ones you *trade on probation* until your own journal rules on
> them.**

- **Momentum & PEAD:** weight from external evidence **plus** your journal (start with real prior).
- **Flags, IPO bases, high-ADR:** weight **only** from your journal — they start on a **short leash**
  (smaller size, flagged *"unproven — building sample"*), and earn their grade purely from your own
  measured expectancy, not from a paper, from me, or from an educator.

This resolves the tension cleanly: **academic evidence sets the priors for the legible setups; your
journal *manufactures* the missing evidence for the illegible ones** — the one thing your tool can
do that neither the papers nor the YouTube educators can.

## C.5 The one non-negotiable guardrail
On probation, the glamorous setups trade **small** — because "unmeasured" **plus** "operator-prone
low-float tier" (where flags and hot IPOs live) is precisely where the fat-tail losses hide. Small
size while the journal builds the base rate isn't skepticism — **it's the price of finding out.**

---

# PART D — How the three threads fit together (one page)

1. **The edge was never the indicators** (Part A) — it's selectivity, one honest opinion per symbol,
   and the compounding journal. Everything rendered today is free elsewhere.
2. **The survey (Part B)** tells you *where the known base rates are*: momentum and PEAD are proven
   and structurally available; IPO/flag/high-ADR are glamorous but unmeasured and operator-prone.
3. **The correction (Part C)** tells you *how to use that*: don't demote the glamorous setups for
   lacking papers — put them on probation and let the **journal (the Part A moat)** manufacture their
   missing evidence, small-size, while momentum + PEAD carry real weight from day one.

**The single throughline:** the fix to the "3/10 reskin" problem, the answer to "which setups,"
and the resolution of "but the papers are biased" are **the same mechanism** — a regime-gated,
evidence-weighted feed whose grades are ultimately earned on your own private
journal → outcome → expectancy loop. Build that loop first; it is simultaneously the moat, the
selectivity engine, and the only fair court in which the glamorous setups can be tried.

## Immediate priority order (synthesised)
1. **Build the journal → outcome → expectancy loop** (one-click capture from setups, auto-context,
   T+5/10/20 backfill, expectancy fed back onto cards). *Moat + research engine + the court for
   probation setups.*
2. **Fix the gate** (multiplicative veto scoring so 100 is rare; regime hard-wired to max cards and
   max open risk) and **the data-integrity clamps** (kill the 27% stops, absurd EPS, sign bugs) —
   credibility first.
3. **Ingest the disclosure feeds → build the PEAD/EP engine** — highest-ROI new edge, from data
   already on disk.
4. **Build the risk + portfolio loss-avoidance engine** (hard stop cap ~8%, fractional-Kelly sizing
   off the journal, open-heat + per-sector caps, drawdown circuit-breakers).
5. **Wire per-setup regime eligibility + the thematic-basket lens.**
6. **Ship the manual-confirm Telegram loop** (push vs digest, defined payload, precision tracked) —
   so the process is executed, not just displayed.
7. **Put glamorous setups on small-size probation** with the "unproven — building sample" flag; let
   the journal promote or demote them on measured expectancy.

*Reminder throughout: external base rates (Part B) are priors, not verdicts. The journal's
per-setup, per-regime expectancy on YOUR trades is the final authority. Not financial advice; verify
all India-specific rules and current data/broker/SEBI constraints before risking capital.*
