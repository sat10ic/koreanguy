# CRITICAL REVIEW — Manas AI Trading OS (Fable, end-to-end browser walkthrough)

Date: 2026-07-06. Method: walked the live app (localhost:5173, backend :8000) — Regime,
Setups, IPO+EP Focus, Watchlist (added a symbol), Journal, Health, the CAPLIPOINT chart
drawer (Setup/Trend/Exit tabs), and the Beginner/Expert toggle. Every claim below cites
something actually seen on screen.

---

## 1. THE EDGE VERDICT

**Today this is a well-built free-data reskin with the skeleton of an edge, not an edge.**
On a spectrum from "free-data reskin" (0) to "irreplaceable" (10), it sits at **3/10**.

The user's suspicion is correct. Everything currently *rendered* — RS ranks, delivery %,
EMA pullbacks, pocket pivots, sector breadth, index returns — is available free on
Chartink, Screener.in, TradingView, and ChartsMaze itself (which is literally the data
source being scraped). Screening + charting + a market-mood dial is the table-stakes
layer of every free Indian scanner.

**But the verdict is not "no edge is possible" — it's "the three things that would be an
edge exist only as stubs":**

1. **Selectivity is promised, not delivered.** The regime bar says "SELECTIVE — trade
   2–3 max positions, A-setups only", and then the Setups feed serves **80 cards, 67 of
   them A+, twelve of them scored 97.5–100/100**. A quality gate that passes 80 names
   with near-identical scores is not a gate; it is Chartink with a percentile veneer.
   The single most alienating thing on the screen.
2. **The journal — the only truly un-copyable asset — is an empty CSV form.** WIN% / AVG R /
   EXPECTANCY / mistake tags, all "—", no connection to the setups feed, no capture of
   *why* a trade was taken. The compounding loop (#18b) that the design docs correctly
   identify as the real moat does not exist in the product yet.
3. **The tool contradicts itself across panels** (details in §3), which destroys the one
   thing a paid-attention single-user tool must have over free sites: **trustworthy
   synthesis**. If the same symbol is simultaneously "readiness 100/100 A+" and
   "EXIT WEAKENING — distribution-days", the user is back to doing the synthesis in
   their own head — i.e., back to free sites.

The honest framing: **the raw ingredients (multi-source ingestion, explainable evidence
chips, exit-state engine, stage/AVWAP analysis) are better than free sites. The
synthesis — one coherent, selective, personalized opinion — is not built. Synthesis IS
the product.**

---

## 2. WHERE THE REAL MOAT IS (or must be)

Free sites can replicate any indicator. They cannot replicate three things:

### Moat 1 — The private journal→outcome→learnings loop (the compounding asset)
A year of "you took 14 pullback-to-EMA trades in SELECTIVE regimes; your expectancy in
them is −0.3R; your pocket-pivot trades in RISK-ON average +1.1R; your #1 mistake tag is
'chased entry'" is data **no site on earth has**, and it gets more valuable every trade.
Today's journal is a manual form with zero linkage: no "TAKEN" button on a setup card, no
auto-capture of (readiness, regime posture, setup type, evidence chips) at entry, no
per-setup-type / per-regime expectancy cut, no feedback into the feed ("you historically
lose on this pattern — flagged"). **This is build priority #1 and it is mostly plumbing,
not research.**

### Moat 2 — Regime-gated selectivity actually enforced (the discipline machine)
Free scanners show you everything and let you hang yourself. The un-copyable behavior is
a tool that **refuses**: SELECTIVE regime → the feed shows *five* names, says "these are
the only 2–3 worth your capital today, here's the full plan for each, everything else is
hidden behind 'show the 75 that didn't make it'". The pieces exist (posture, grades,
confluence); the enforcement doesn't. A tool that says NO is a product; a tool that says
"here are 80 A+ ideas" is a screener.

### Moat 3 — Pre-committed plan → execution audit (discipline, again)
Entry/stop/measured-move already print on cards. The moat version: one click freezes that
plan into the journal *before* the trade, then the exit-state engine audits the live
position against the frozen plan ("you planned stop 1950; price closed 2100 and state is
WEAKENING — your plan says hold"). Plan-vs-behavior deltas become mistake tags
automatically. No free site can do this because no free site holds your plans.

### What is table-stakes to de-emphasize
Sector % bars, Top Indices 1D/1W/1M returns, the participation chart, the breadth color
grid — all fine as *expert* evidence, all free elsewhere, none of it deserves prime real
estate. They currently occupy ~70% of the Regime scroll.

---

## 3. PER-PANEL CRITIQUE (as actually seen)

### 3.1 Regime (home)
- **Works:** PostureCommandBar is genuinely good — "SELECTIVE" badge, plain APPROACH line
  ("TRADE 2–3 MAX POSITIONS, HALF SIZE, A-SETUPS ONLY. RISK 0.35%–0.5% PER TRADE"), a
  one-sentence READ, since-yesterday deltas. This is the best component in the app and
  the correct anchor. InfoDots ("What does xp mean?") everywhere is the right instinct.
- **Doesn't:**
  - **Self-contradiction on one screen:** the posture bar says "Breadth 67% of stocks
    above 20-DMA — strong" while the BREADTH/SWING STATE card two inches below says
    "Breadth unavailable · swing up." Same screen, same metric, two answers.
  - The READ admits its own thinness: "1 of 1 known checks are favourable" — the flagship
    regime verdict is resting on **one** check and says so out loud.
  - Below the fold it's an indicator dump: XP dial (10.2 LOW), 4.5R burst (113), MBI with
    20R/50R ratio rows, breadth sparkline, participation, breadth grid, sectors list
    (a wall of red % chips), Top Indices, quadrant, trend — ~9 panels, unconditioned,
    identical in both modes (verified byte-identical, §4).
- **Highest-value fix:** kill the contradiction (one breadth source of truth), then
  implement §3.1 of BEGINNER_EXPERT_SPEC — verdict + 3 plain sentences + top setups,
  everything else expert-gated.

### 3.2 Setups
- **Works:** the card anatomy is the strongest evidence design in the app: confluence
  count ("6 SCREENS / CONFLUENCE 6X"), theme chip ("PHARMA & HEALTHCARE (TOP-QUARTILE)"),
  EPS YoY, RS, delivery, trigger signal, named screen chips (chhirag/himanshu/hiren…),
  ASM-clear, entry/stop/measured-move with the honest caption "if it works — not a
  promise". Filter bar (setup type / min RS / min grade) works. "+ WATCHLIST" works.
- **Doesn't:**
  - **Grade inflation kills it:** 80 cards, 67 A+, top 12 all ≥97.5/100. The scores do
    not discriminate; "A+" means nothing when it's the mode. The whole feed reads
    top-quartile-pharma because the theme boost swamps everything (9 of the first 11
    cards are pharma).
  - **Data-quality trust-killers on the flagship surface:** "EPS YOY +-5%" (sign bug),
    "EPS YOY +6575%", "+55250%" (base-effect garbage rendered as evidence). One absurd
    chip poisons trust in every chip.
  - **Trade plans that can't be executed:** CAPLIPOINT (rank #1, 100/100) prints ENTRY
    2675 / STOP 1950 — a **27% stop** on a swing trade, ~2R to the measured move. No R:R
    shown, no position size on the card; the sizer lives on a different tab and shares
    nothing with the card.
  - Screen names (chhirag, himanshu, hiren, shashank) are private jargon with no InfoDot.
- **Highest-value fix:** make the gate a gate — cap the feed at N by regime posture
  (SELECTIVE → 5), force a score distribution (an A+ should be rare), and sanity-clamp
  EPS chips.

### 3.3 IPO+EP Focus Center
- **Works:** honest framing ("Filtered lens on the same Setups feed. Same rows, same
  readiness number") — good anti-mashup discipline. Empty state carries the regime
  context ("Market is SELECTIVE; sit tight").
- **Doesn't:** it showed **"0 SETUPS TONIGHT"** while the main feed had cards chip-tagged
  `ipo-setups` / `past-IPO-listings` / `positive-earnings-reaction` (SUDEEPPHRM, CORONA,
  PIRAMALFIN…). So the detectors and the lens disagree about what counts as IPO/EP — the
  new flagship tab looks broken on day one. No "what would qualify" explainer, no recent
  historical qualifiers to prove it ever fires. Note: it is a sub-toggle inside Setups,
  not the nav-level tab the roadmap implies — fine, but then the empty state must sell it.
- **Highest-value fix:** reconcile lens criteria with the chips users can already see, and
  show "last 5 names that qualified + what happened" so an empty night still teaches.

### 3.4 Watchlist
- **Works (best synthesis in the app):** added CAPLIPOINT — the row delivered exit-state
  ("EXIT WEAKENING" + reasons: downside-reversal-bar, distribution-days), RVOL 0.50×,
  gap +0.5%, dist-pivot −5.1%, ADR 4%, DLV 33%, and a plain READ ("volume is not yet
  expanded; price is still below pivot"). Position sizer works (83 shares, ₹2,490 risk).
- **Doesn't:**
  - **The killer contradiction:** the same CAPLIPOINT is the #1 setup at 100/100 A+ on
    the Setups tab. Readiness and exit-state never see each other. Which panel do I
    believe? (Answer: neither — I go back to TradingView.)
  - Sizer is disconnected: clicking "+ WATCHLIST" on a setup card carries none of the
    card's entry/stop into the sizer; user re-types numbers the app already has.
  - No holdings concept: watch-candidates and open positions are the same list, so
    "EXIT WEAKENING" fires on something never bought.
- **Highest-value fix:** one symbol, one opinion — setups readiness must be suppressed or
  reconciled when exit-state is Weakening/Broken; and "+ WATCHLIST" should pre-fill the
  sizer from the card's plan.

### 3.5 Journal
- **Works:** the right primitives exist — expectancy (with InfoDot), R, mistake tags; the
  empty-state copy names the point ("see expectancy and repeat mistakes").
- **Doesn't:** it is a disconnected manual form. No path from setup card → "I took this"
  → journal row; no auto-capture of setup type/readiness/regime at entry (columns exist
  for SETUP but hand-typed); no per-regime or per-setup expectancy; no learnings surfaced
  anywhere else in the app. **The moat is a stub.**
- **Highest-value fix:** the TAKEN button (freeze plan + context into the journal in one
  click). Everything else in §2-Moat-1 follows from having that data.

### 3.6 Health
- **Works:** DATA UPDATED UNTIL stamps (breadth/bhavcopy/ChartsMaze/regime dates) are
  honest and repeated at every page bottom — genuinely good hygiene most free sites lack.
  UPDATE TO LATEST explains what it does and that it's slow.
- **Doesn't:** "No EOD alerts generated yet. Run refresh after scan_candidates is
  available" — raw internal identifiers leaking to the UI; no per-source freshness
  warning coloring (regime is 3 days old on a Monday and nothing looks stale).
- **Highest-value fix:** staleness should change state app-wide (spec §3-shared already
  demands this), not just print dates.

### 3.7 Chart drawer (clicked CAPLIPOINT)
- **Works — expert depth is real here:** Setup/Trend/Exit tabs with different EMA presets;
  buy-zone/stop/measured-move bands; Stage-2 analysis with the actual arithmetic ("close
  2538.1 vs 150-day SMA 1887.11… moved from 1829.24 over 20 bars"); TRAIL HOLD verdict;
  auto-AVWAP anchor with reason ("breakout/pocket-pivot anchor beat older anchor"); an
  event log where every pocket pivot shows its volume math. This is the most
  differentiated surface in the app.
- **Doesn't:** the Exit tab is just a 15/21-EMA re-skin of the same panel — no exit
  verdict, no trailing-stop level, no tie to the exit-state engine that the watchlist
  clearly has ("EXIT WEAKENING" never appears in the drawer for the same symbol!). The
  ALL-CAPS legend explains what a candle is on every open (beginner copy shown to
  everyone, again the toggle doing nothing). "RS PHASE — insufficient history" for a
  symbol the feed ranks RS 90.
- **Highest-value fix:** the Exit tab should render the exit-state engine verdict +
  current trail level, i.e., the answer to "do I stay in?"

---

## 4. BEGINNER vs EXPERT FLOW

**Measured, not assumed:** on Regime I captured `main.innerText` in beginner mode and
expert mode — **byte-identical (3,955 = 3,955, `identical: true`)**. The toggle changes
nothing on the flagship screen. It is two header buttons that lie.

**As a nervous beginner ("what do I do today?"):** the first 400px are genuinely good —
SELECTIVE, trade 2–3 max, half size, risk 0.35–0.5%, plain READ. If the app ended there
plus five setups, the beginner flow would work. Instead: scroll reveals XP 10.2 LOW,
4.5R 113, MBI 20R/50R ratio rows, quadrants, a red wall of sector percentages — and the
setup cards speak "chhirag hit; himanshu hit; hiren hit", which is meaningless without
tribal knowledge. Then the #1 recommendation asks them to risk 27% to the stop. A
beginner leaves confused and, worse, mis-calibrated.

**As an expert ("give me depth"):** the depth exists (drawer stage math, AVWAP
reasoning, confluence chips) but the expert is *punished* by inflation and incoherence:
80 A+ cards means the expert must re-rank manually; readiness vs exit-state disagreement
means re-verifying every name elsewhere; +55250% EPS chips mean auditing the data. The
expert's actual need — "trust the shortlist" — is the same as the beginner's.

**Does spec #29 fix it?** The BEGINNER_EXPERT_SPEC is unusually good (decision-per-screen
rule, six mechanical axes, safety states never gated, anti-fork guardrails) and would fix
the *presentation* problem. It will NOT fix: grade inflation (a beginner shown "the top 5
of 80 A+'s" is still shown noise), cross-panel contradictions (G4/G5 gate rendering, not
truth), or private screen-name jargon (spec's glossary covers ep/ants/avwap but not
chhirag/himanshu/hiren). **Build #29, but the selectivity and coherence fixes rank above
it — a beautiful progressive disclosure of an incoherent opinion is lipstick.**

---

## 5. TOP 5 IMPROVEMENTS, RANKED BY IMPACT-ON-EDGE

1. **Make the gate a gate (selectivity = the product).** Feed cap tied to posture
   (SELECTIVE → 5 shown, rest behind "75 didn't make it — show why"); recalibrate scoring
   so A+ is rare (force a distribution or raise the bar until <10% qualify); cap the theme
   boost so one sector can't be 80% of the feed. Without this, nothing else matters —
   this is the difference between a screener and an opinion.
2. **One symbol, one opinion (cross-panel coherence).** A single per-symbol verdict object
   (readiness ⊕ exit-state ⊕ RS availability ⊕ staleness) consumed by Setups, Watchlist,
   and the drawer. CAPLIPOINT must never be 100/100 and EXIT-WEAKENING at once; the
   posture bar and the swing card must share one breadth value. This is pure anti-mashup
   doctrine applied to outputs, not just writers.
3. **The TAKEN button → journal auto-capture → learnings surfacing (#18b).** One click on
   a setup card freezes plan + context (readiness, posture, setup type, chips) into the
   journal; on close, outcome joins context; per-setup-type/per-regime expectancy renders
   in Journal AND feeds back as a chip on future cards ("your history with this setup:
   +0.8R avg, 6 trades"). This is the only feature on the roadmap free sites can never
   copy, and it compounds with every trade. Start now precisely because it needs months
   of data to bloom.
4. **Trade-plan integrity.** Sanity-bound stops (flag any plan risking >8–10% to stop);
   show R:R on the card; carry entry/stop into the sizer on "+ WATCHLIST"; clamp/suppress
   absurd EPS chips (+55250%) and fix the "+-5%" sign bug. Every impossible number visible
   on a card taxes trust on all of them.
5. **Ship #29 progressive disclosure — after 1–2.** The spec is ready and correct;
   additionally glossary the private screen names (chhirag/himanshu/hiren → what the
   screen actually checks, e.g. "trend-template screen: price > 50/150/200MA, RS > 70"),
   and make the drawer Exit tab render the exit-state verdict + trail stop.

**Cut/merge candidates:** Top Indices and the sector %-bar list should collapse into one
expert-only "market internals" accordion (they are free-site content occupying prime
space). Health merges into a header staleness indicator + settings page; it does not
earn a nav slot. Focus Center stays a lens inside Setups (as built) but must show
historical qualifiers or it reads as broken.

---

## 6. THE ONE HARD TRUTH

**You are building the wrong half first.** The current app is the half that Chartink,
TradingView, and ChartsMaze already give away — screens, indicators, sector heat, market
mood — rebuilt more elegantly, and elegance is not an edge. The half that would be an
edge — a tool that *refuses* to show you 80 ideas, holds you to a pre-committed plan,
and learns YOUR statistics trade by trade until it knows your edge better than you do —
exists only in the design docs. Meanwhile the surfaces that are built undermine each
other in public (100/100 vs EXIT WEAKENING on the same symbol; "breadth 67%" vs "breadth
unavailable" on the same screen; a toggle that provably does nothing), and a tool whose
job is judgment cannot afford to be caught contradicting itself even once. Stop adding
detectors — every new detector widens the already-inflated feed. The next quarter should
produce exactly three things: a feed that says NO, one opinion per symbol, and a journal
that remembers. That is the product; everything else is décor.
