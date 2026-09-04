<!-- Adopted 2026-08-29 as the research NORTH STAR (unidesk DECISIONS D11):
     the per-edge hypothesis portfolio (EP quality, IPO maturity, ignition,
     resilience, chop failure, reaction gap). Each AI edge is gated by its own
     baseline-kill rule and may only be attempted after the corresponding
     deterministic baseline from SWING_EDGES_TECHNICAL_SPEC.md exists. The
     unification artifact is the point-in-time state representation (feature
     vector per symbol-date): built once for deterministic scoring, reused by
     the analogue engine. Constitution (D14) now governs HOW these hypotheses
     are tested. Predictive AI is forbidden until Phase 0 acceptance.
     As-built tool: plan/UNIFIED_DESK_BUILD_MANUAL_V2.md. -->

# AI-Native Trading Edges for Indian Equity Swing & Momentum Trading

## Purpose

This note consolidates the ideas discussed for finding a **trading edge that exists specifically because AI can process information, chart structure, historical analogues, and cross-sectional relationships at a scale that is impractical for a human trader**.

The focus is Indian cash equities, especially swing and momentum trading in midcaps/smallcaps, where:

- the universe is broad,
- sector and thematic leadership is strong,
- price behaviour can be highly heterogeneous,
- IPOs and episodic pivots often matter,
- discretionary traders cannot realistically inspect every relevant chart every day,
- and a conventional screener usually reduces complex price paths into a few static conditions.

The central design principle is:

> **Use AI as a perception, pattern-recognition, ranking, and analogue-retrieval engine. Keep entries, exits, stops, sizing, and risk controls deterministic wherever possible.**

The strongest AI-native opportunity is not likely to be "predict tomorrow's candle."  
It is more likely to be:

> **Recognize rare, high-quality market states that humans cannot consistently identify across thousands of stocks, then attach measured historical expectancy to those states.**

---

# The Six Edge Hypotheses

1. **AI Information Reaction Gap**  
   Fundamental / cross-company information propagation.

2. **Bull Market: Pre-Breakout Ignition Detection**  
   Find bases that are approaching expansion before the obvious breakout.

3. **Bear Market: Downside Refusal / Future-Leader Detection**  
   Find stocks that repeatedly refuse to participate in market weakness.

4. **Sideways Market: Failed-Breakout Intelligence**  
   Identify likely traps and failed range expansions before the failure becomes obvious.

5. **IPO Base Maturity Engine**  
   Normalize newly listed stocks by "days since listing" and identify IPO bases approaching maturity.

6. **Episodic Pivot Quality Engine**  
   Distinguish persistent repricing events from exhaustion gaps using complete pre-gap, intraday, and post-gap geometry.

---

# 1. AI Information Reaction Gap

## The Edge

Detect an important event in **Company A**, identify **Company B/C/D** whose economics should be affected by that event, and find the linked stocks whose prices have **not yet reacted sufficiently**.

Conceptually:

```text
                    NEW INFORMATION
                           │
                           ▼
                 ┌──────────────────┐
                 │ Company A        │
                 │ event / earnings │
                 │ order / capex    │
                 └────────┬─────────┘
                          │
                    AI understands
                    economic meaning
                          │
              ┌───────────┴────────────┐
              ▼                        ▼
       Supplier B                 Beneficiary C
       35% exposure               same theme
              │                        │
       already moved?             already moved?
              │                        │
          NO ─┴─────────► REACTION GAP ◄─ NO
                              │
                              ▼
                     Momentum confirmation
                              │
                              ▼
                       SWING ENTRY
                        2–20 days
```

## Why It Could Exist

Indian listed-company information is abundant but fragmented across:

- NSE/BSE announcements
- quarterly results
- investor presentations
- earnings transcripts
- annual reports
- credit-rating reports
- order announcements
- tenders
- interviews
- industry data
- subsidiary disclosures

Humans usually process the event in the company where it originated.

The harder problem is:

> **Who else does this change the earnings trajectory for?**

Example structure:

```text
POWER CAPEX ACCELERATES

Generators
    ↓
Transmission
    ↓
Transformers
    ↓
Switchgear
    ↓
Cables
    ↓
Conductors
    ↓
Specialty components
```

AI can potentially maintain a live graph of these relationships rather than discovering the theme sequentially.

## Why AI Changes It

A conventional screener can know:

> Company X belongs to the transformer sector.

AI can potentially infer:

> Company X manufactures a specific high-voltage transformer category, recently added capacity, has exposure to transmission capex, and is likely to benefit from the exact demand bottleneck mentioned in today's event.

The useful architecture is a **confidence-weighted relationship graph**.

Example:

| Relationship | Confidence |
|---|---:|
| Explicitly named customer | 100 |
| Confirmed historical order | 95 |
| Revenue segment directly exposed | 85 |
| Same product / end-market | 65 |
| Pure LLM-inferred thematic link | 35 |

Low-confidence inferred relationships should not generate trades until validated.

## Reaction Gap

The signal is not merely "Company C benefits."

The signal is:

> **Economic significance minus current price reaction.**

Example:

```text
EVENT IMPACT SCORE

Company B     ███████████████████  91
Price reaction████████████████     82
Reaction gap                       9

Company C     ███████████████████  88
Price reaction█████                23
Reaction gap                      65
```

Company C is more interesting because the economic link appears meaningful while the stock has not yet repriced.

## Proposed AIRG Score

**AIRG = AI Information Reaction Gap**

Conceptually:

```text
AIRG
 =
Event Materiality
× Relationship Strength
× Economic Exposure
× Event Novelty
× Source Reliability
× Sector Confirmation

minus

Existing Price Reaction
```

High AIRG means:

> Something important happened, this company should economically care about it, and price seemingly has not cared enough yet.

## How to Test

Start small.

### Universe

- Nifty 500
- Next 500 / liquid smallcaps
- exclude chronic lower-circuit stocks
- exclude ASM/GSM or highly problematic securities
- exclude very low-liquidity names

### Events

Initially use only:

- quarterly earnings
- material orders/contracts

### Relationships

Initially use only:

- confirmed customer/supplier links
- direct industry relationships

Avoid fuzzy semantic inference during the first test.

### Measure

For every event in A:

```text
             EVENT AT A
                 │
        identify linked stocks
                 │
                 ▼
        B   C   D   E   F
                 │
          measure returns
                 │
     ┌───────────┼───────────┐
     ▼           ▼           ▼
    +1d         +5d         +20d
```

Compare against:

1. random stocks
2. same-industry controls
3. sector-matched controls
4. identical momentum controls
5. market-cap/liquidity matched controls

The key experiment:

```text
                    ECONOMIC EXPOSURE
             Low        Medium        High

Low reaction   ?           ?           ★★★★★
Medium         ?           ?            ?
High           ?           ?            ?
```

The expected strongest group should be:

> **High economic exposure + low initial reaction**

## What Would Disprove It

Kill the idea if:

- linked stocks do not outperform matched controls,
- the effect disappears after sector momentum adjustment,
- returns exist only in untradeable illiquid stocks,
- the signal requires look-ahead information,
- clean out-of-sample performance collapses,
- plain RS performs just as well,
- or AI-derived exposure adds no incremental value over price, volume, and sector strength.

---

# 2. Bull Market Edge: Pre-Breakout Ignition Detection

## The Edge

Most scanners identify the breakout **after it occurs**.

The more valuable problem is:

> **Among dozens of technically valid bases, which ones are actually approaching expansion?**

Suppose 70 stocks satisfy:

- above 20/50/200 DMA
- near 52-week high
- strong RS
- contracting ATR
- volume dry-up

A normal scanner returns 70 names.

The AI system tries to rank **compression maturity**.

Example setup:

```text
PRICE
                     ──────── resistance
           /\       /\   /\
          /  \_____/  \_/  \__
       __/                    \_
     _/
────────────────────────────────────

VOLATILITY
████████████
 ████████
   █████
      ███
        ██

VOLUME
███████
 █████
   ███
     ██

RS
        ╱
      ╱
    ╱
──╱────────────────────────────────
```

## What AI Looks For

### Price Geometry

- contraction sequence
- shrinking swing depth
- shrinking pullback duration
- closing-range improvement
- wick behaviour
- number of failed breakout attempts
- distance from pivot
- tightness near highs
- asymmetry between upswings and pullbacks

### Volume Geometry

- volume decay through contractions
- red-day vs green-day volume
- volume clustering near support
- evidence of selling absorption
- change in volume elasticity near the pivot

### Relative Strength

- RS slope
- RS acceleration
- RS new high before price
- behaviour on Nifty down days
- behaviour vs sector index
- persistence of RS, not just current percentile

### Multi-Timeframe Structure

```text
WEEKLY       DAILY       30 MIN
  │            │            │
Stage 2     tight base    micro coil
  │            │            │
  └────────────┼────────────┘
               ▼
         IGNITION SCORE
```

## The AI-Native Component

Represent each current chart state as an embedding.

```text
LIVE SETUP
    ↓
Chart / sequence embedding
    ↓
Search historical state library
    ↓
Find nearest analogues
    ↓
Measure what happened next
```

Example output:

```text
Historical analogues: 163
Broke out within 5 sessions: 61%
Median MFE: +9.4%
Median MAE: -2.1%

Strongest similarity:
✓ contraction geometry
✓ RS acceleration
✓ volume decay
✓ tightness near pivot
```

This is more useful than an LLM simply declaring that a chart "looks like a VCP."

## How to Test

Compare:

**AI-ranked bases**

versus

**deterministic VCP + RS + volume score**

Measure:

- 5-day breakout probability
- 10-day breakout probability
- 20-day breakout probability
- MFE
- MAE
- expectancy
- failure rate
- post-breakout follow-through

## What Would Disprove It

Kill the idea if AI cannot outperform a carefully engineered conventional VCP/RS composite.

---

# 3. Bear Market Edge: Downside Refusal / Future-Leader Detection

## The Edge

Do not try to predict the exact market bottom.

Instead identify stocks that behave **abnormally well while the market is under stress**.

Core idea:

> **Stress reveals sponsorship.**

Basic relative strength might show:

```text
NIFTY       ███████████████ -11%

STOCK A     █████████████    -9%

STOCK B     ███              -2%
```

The AI-native edge is to model **how** Stock B refuses to fall.

## What the AI Measures

- shallow reactions to index selloffs
- rapid recovery after market flushes
- repeated closes in upper daily range
- low downside volume expansion
- higher lows while index makes lower lows
- failed breakdowns
- tight ranges during panic
- quick reclaim of 10/20 DMA
- RS making highs during broad weakness
- weak beta on down days
- strong beta on recovery days
- duration of recovery after stress events

Example:

```text
When NIFTY falls >1%:

Stock response

Day 1     -0.7%
Day 2     +0.1%
Day 3     -0.2%
Day 4     +0.8%

Recovery half-life: very short
Downside participation: low
Upside participation: high

AI STRESS RESILIENCE = 92/100
```

## The Trade Logic

Do not buy simply because a stock is resilient.

Use a two-stage process:

```text
MARKET SELLOFF
      ↓
AI finds downside refusal
      ↓
3–10 day tight range
      ↓
Index stabilises
      ↓
Stock breaks range first
      ↓
LONG
```

The hypothesis is that the strongest stocks during the decline may become the first leaders of the next advance.

## How to Test

During every historical correction:

1. rank stocks by AI stress-resilience score near the weak phase,
2. freeze the ranking at that point,
3. measure subsequent 20/40/60-session performance,
4. measure whether the top decile disproportionately contains the next leadership cohort.

## What Would Disprove It

Kill the idea if plain RS vs Nifty performs just as well.

If that happens, AI has merely reinvented a relative-strength chart using more compute.

---

# 4. Sideways / Choppy Market Edge: Failed-Breakout Intelligence

## The Edge

In a choppy regime, classical breakout systems can repeatedly get trapped.

The AI problem becomes:

> **Which breakout attempts are statistically likely to fail?**

Typical false breakout:

```text
Resistance ─────────────────

                 ╱\
                ╱  \
        _______╱    │
_______╱             │
                     ▼
                  back inside
```

For long-only swing trading, the particularly useful variation is a failed breakdown reclaim:

```text
Support ───────────────────

             │
             ▼
─────────────┐
             ╲
              ╲__
                 ╲
                  ╲___
                     ╲
                     ╱
                  __╱
                 ↑
            reclaim range
```

## What AI Measures

### Range Maturity

- range age
- number of boundary touches
- directional efficiency
- ATR compression
- previous breakout failures
- volume expansion / contraction
- trend persistence
- sector confirmation
- distance from range midpoint
- time spent near upper/lower boundary

Example:

```text
Directional efficiency    LOW
Range age                 27 days
Boundary touches           6
ATR compression           HIGH
Breakout failures          3
Volume expansion           LOW
Trend persistence          LOW
Sector confirmation        LOW
```

Then classify:

```text
TRUE BREAKOUT       23%
FALSE BREAKOUT      77%
```

## Long Setup Variant

**Sweep → reclaim → AVWAP reclaim → range rotation**

```text
Range

HIGH  ──────────────────────
                    target ↑

MID   ─────────── AVWAP ────

LOW   ──────────────────────
              ↓
           breakdown
              ↓
             ╲╱
              ↑
          fast reclaim
              │
             BUY
```

## Why AI Helps

A scanner knows:

> price crossed support.

AI can compare the entire preceding 20–50-session path with thousands of historical:

- true breakouts
- false breakouts
- failed breakdowns
- liquidity sweeps
- range expansions
- range rejections

This is fundamentally a **sequence classification** problem.

## How to Test

Collect every:

- 20-day high breakout
- 30-day high breakout
- 40-day high breakout
- 20/30/40-day low breakdown

Measure:

- continuation probability
- close-back-inside probability
- time to failure
- reversal distance
- MFE/MAE after failure
- success of reclaim entries

The crucial test:

> Can the AI identify likely failures **before** the failure is visually obvious?

## What Would Disprove It

Kill the idea if simple rules such as:

- weak breakout distance,
- weak volume,
- close back inside range,
- poor sector confirmation,

capture nearly all the effect.

---

# 5. IPO Edge: AI IPO Base Maturity

## The Edge

New IPOs are awkward for conventional technical systems because they have:

- no 200 DMA history,
- limited RS history,
- unstable ATR,
- large listing volatility,
- little long-term support/resistance,
- rapidly changing volume characteristics.

Human traders compensate by visually interpreting the entire life of the stock since listing.

AI is naturally suited to that.

## Normalize Every IPO From Day 0

Instead of calendar history, normalize by listing age:

```text
LISTING
   │
   ▼

Day 0   Day 5   Day 10   Day 20   Day 40
 │        │       │        │        │
 ▼        ▼       ▼        ▼        ▼
██████████████████████████████████████
```

The AI learns how a healthy IPO transitions from price discovery into equilibrium.

Example:

```text
LISTING
   │
   │ huge volatility
   ▼
       /\        /
      /  \______/\
     /            \
____/              \____
                        \___
                           \__
                              ───────
                              ───────
                           BASE TIGHTENS
```

At the same time:

```text
DAILY RANGE

██████████████
██████████
████████
██████
████
███
██
```

and:

```text
VOLUME

████████████████
████████████
████████
██████
████
██
```

This represents price discovery gradually settling into equilibrium.

## IPO Base Maturity Features

| Component | Possible Interpretation |
|---|---|
| Volatility decay | speculation settling |
| Pullback depth decay | sellers losing control |
| Close-location improvement | demand |
| Volume dry-up | supply contraction |
| Listing AVWAP behaviour | participant profitability |
| IPO-high proximity | remaining overhead supply |
| Base symmetry | orderly consolidation |
| Failed breakdown count | absorption |
| Tight closes | equilibrium |
| RS since listing | emerging leadership |

Example output:

```text
IPO BASE MATURITY

Price discovery       ██████████  complete
Volatility decay      █████████   91
Supply contraction    ████████    84
RS                    █████████   93
Base tightness        ████████    87

BREAKOUT READINESS       89/100
```

## AI Analogue Retrieval

Compare an IPO at **Day 37** to every historical IPO at approximately the same listing age.

```text
Current IPO
Day 37

Nearest historical analogues:

IPO #122     similarity 94%
IPO #411     similarity 91%
IPO #207     similarity 89%
IPO #683     similarity 87%

Median subsequent 20D return: +11.8%
Failure probability: 24%
```

This is difficult for a human to do systematically across the complete IPO universe.

## How to Test

For historical IPOs:

- align all stocks by listing day,
- calculate only information available up to each day,
- create age-normalized chart states,
- compare outcomes after breakout-readiness signals.

Measure:

- 10/20/40-day breakout probability
- MFE
- MAE
- success rate
- time to breakout
- false breakout rate

## What Would Disprove It

Kill the idea if simple:

**listing AVWAP + 20-day high + volume contraction**

performs equally well.

---

# 6. Episodic Pivot Edge: Price-Only EP Quality Engine

## The Edge

Detecting an episodic pivot is easy.

A normal scanner can find:

```text
Gap > 4%
Volume > 3×
```

The harder and more valuable problem is:

> **Which EPs represent genuine persistent repricing and which are exhaustion events?**

Two +8% gaps can have completely different structure.

### EP A

```text
       ───────── close
      ╱
     ╱
    ╱
___╱
 OPEN

Gap
████████

Minimal retracement
High close
AVWAP held
```

### EP B

```text
         /\
        /  \
       /    \
______╱      ╲
 OPEN          ╲____
                   close
```

Same gap.

Same headline volume.

Very different internal quality.

---

## What AI Analyses

### Before the Gap

- prior compression
- distance from highs
- overhead resistance
- preceding trend
- volatility contraction
- volume dry-up
- prior failed breakout count

### Opening Behaviour

- gap relative to ADR
- opening drive
- open-to-low excursion
- first 15/30/60-minute structure
- volume acceleration
- AVWAP relationship

### Day-One Behaviour

- high-close percentage
- gap-fill percentage
- intraday pullback depth
- number of AVWAP violations
- closing tightness
- late-day demand
- volume concentration by time of day

### Day Two / Three

Potentially the most useful phase:

```text
EP DAY

        █████
       ██████
      ███████
____█████████


DAY +1

          ██
         ███
        ████

TIGHT


DAY +2

         ██
         ██
        ███

VOLUME DRIES UP

         ↓

       ENTRY
```

A genuine repricing event should often behave differently from a speculative gap.

The AI learns the **post-EP digestion pattern**.

## EP Quality Score

Conceptually:

```text
EPQ =

Gap significance
× Volume anomaly
× Close quality
× AVWAP integrity
× Prior compression
× Relative strength
× Post-gap tightness

−

Gap fill
− Overextension
− Selling-volume intensity
```

The weights should not necessarily be manually fixed.

The useful part of ML is learning interactions such as:

> A 7% gap after 12 days of compression may behave very differently from a 7% gap after a 35% four-week run.

A static screener struggles with that kind of context.

## How to Test

Build a historical library of EPs.

For every EP, store:

- pre-gap state
- opening path
- intraday path
- end-of-day state
- day +1
- day +2
- day +3
- subsequent 5/10/20-day outcomes

Then compare:

**AI EP quality ranking**

against

**simple gap + RVOL + close-location rules**

Measure:

- continuation rate
- MFE
- MAE
- false continuation rate
- time to first failure
- expectancy by EP quality decile

## What Would Disprove It

Kill the idea if a simple deterministic EP score produces equivalent results.

---

# Which Ideas Look Strongest?

| Edge | AI Advantage | Potential Durability | Difficulty | Priority |
|---|---:|---:|---:|---:|
| **EP Quality Engine** | ★★★★★ | ★★★★★ | ★★★ | **#1** |
| **IPO Base Maturity** | ★★★★★ | ★★★★★ | ★★★★ | **#2** |
| **Bull Ignition Detector** | ★★★★ | ★★★★ | ★★★ | **#3** |
| **Bear Downside Refusal** | ★★★★ | ★★★★ | ★★ | **#4** |
| **Choppy Failure Detector** | ★★★★ | ★★★ | ★★★★ | **#5** |
| **AI Information Reaction Gap** | ★★★★★ | ★★★★ | ★★★★★ | **Parallel / later** |

For a price-action-first Indian swing trader, the recommended build order would be:

```text
1. Episodic Pivots
       ↓
2. IPO Bases
       ↓
3. Bull Ignition
       ↓
4. Bear Resilience
       ↓
5. Choppy Failure Model
       ↓
6. Cross-company Reaction Gap
```

The first five can share a common technical engine.

---

# Unified Architecture

## AI Price-Action State Engine

```text
                       NSE UNIVERSE
                            │
                            ▼
                    MARKET REGIME
                            │
        ┌───────────┬───────┼─────────┬───────────┐
        ▼           ▼       ▼         ▼           ▼
      BULL        BEAR    CHOPPY     IPO          EP
        │           │       │         │           │
        ▼           ▼       ▼         ▼           ▼
    Ignition     Downside   Trap     Base       Repricing
     Model       Refusal   Model   Maturity     Quality
        │           │       │         │           │
        └───────────┴───────┴─────────┴───────────┘
                            │
                            ▼
                   HISTORICAL ANALOGUES
                            │
                            ▼
                 EXPECTANCY / MFE / MAE
                            │
                            ▼
                     RULE-BASED ENTRY
```

The Information Reaction Gap engine can sit beside this:

```text
                 PUBLIC INFORMATION
                        │
                        ▼
                 AI RELATIONSHIP GRAPH
                        │
                        ▼
                  REACTION GAP SCORE
                        │
                        ▼
                PRICE-ACTION CONFIRMATION
                        │
                        ▼
                    SAME RISK ENGINE
```

---

# The Core AI Capability: Historical State Retrieval

The most important shared component is not an LLM chat layer.

It is a **historical pattern-state library**.

For every stock and every date, generate a representation containing:

- normalized OHLC path
- volume path
- relative-strength path
- ATR / realized volatility
- distance to relevant pivots
- AVWAP relations
- range geometry
- market regime
- sector regime
- liquidity
- listing age if applicable
- EP state if applicable
- setup family

Then embed or otherwise represent that state.

For today's candidate:

```text
CURRENT MARKET STATE
        │
        ▼
State representation
        │
        ▼
Nearest historical analogues
        │
        ▼
Outcome distribution
        │
        ├── breakout probability
        ├── failure probability
        ├── median MFE
        ├── median MAE
        ├── time to breakout
        ├── time to failure
        └── expectancy
```

This lets the system answer something genuinely useful:

> **When the Indian market previously produced states that looked like this, what happened next?**

---

# Example User-Facing Output

The AI should not output:

> "XYZ looks bullish. Buy."

It should output something closer to:

```text
XYZ

Setup: EP continuation
Pattern confidence:       91%
Historical analogues:    286

5D continuation rate:     68%
Median MFE:              +8.7%
Median MAE:              -2.3%

Current conditions:
✓ strong close
✓ AVWAP held
✓ volume anomaly
✓ prior compression
✓ day-2 contraction
✓ sector RS positive

ENTRY TRIGGER:
Day-2 high + 0.1%

INVALIDATION:
Below EP AVWAP / defined structural low
```

For a bull-market base:

```text
ABC

Setup: Pre-breakout ignition
Compression maturity:     93
RS acceleration:          89
Volume contraction:       84
Historical analogues:    412

Breakout within 5D:       64%
Median 10D MFE:          +7.8%
Median 10D MAE:          -2.0%

Trigger:
Pivot + defined buffer

Invalidation:
Structural low / ATR rule
```

For bear-market resilience:

```text
DEF

Stress resilience:        94
Downside participation:   18%
Recovery speed:           91
RS vs Nifty:              96
RS vs sector:             92

Next-leader analogue set: 173

20D outperformance:
Top-decile historical median +6.3% vs benchmark
```

---

# Important Design Principle: Separate Prediction From Execution

The AI layer should answer:

- What setup is this?
- How mature is it?
- What historical states are most similar?
- What did those states do next?
- How unusual is today's configuration?
- How strong is the setup relative to alternatives?

The deterministic trading layer should decide:

- entry trigger
- stop
- position size
- max portfolio risk
- max sector exposure
- gap rules
- circuit / ASM / GSM exclusions
- liquidity requirements
- pyramiding
- partial exits
- trailing stop logic

This avoids turning the system into:

> "The model feels bullish."

---

# Suggested Research Order

## Phase 1 — Episodic Pivots

Why first:

- discrete event
- easy to label
- strong price/volume signature
- relevant to Indian momentum trading
- rich post-event geometry
- relatively clean backtesting

Questions:

1. Can AI rank EP quality better than static rules?
2. Does the ranking correlate monotonically with future expectancy?
3. Can the model identify the difference between repricing and exhaustion?
4. Does day +1 / day +2 behaviour add predictive power?

---

## Phase 2 — IPO Bases

Why second:

- conventional indicators are weakest here,
- age-normalized pattern recognition is naturally AI-friendly,
- Indian IPOs often show distinctive price-discovery cycles.

Questions:

1. Can listing-age normalization improve breakout prediction?
2. Does AI-detected maturity outperform listing AVWAP + breakout rules?
3. Can the model distinguish constructive volatility decay from dead-money drift?

---

## Phase 3 — Bull-Market Ignition

Questions:

1. Can AI identify which VCP-style bases are closest to expansion?
2. Does geometric maturity add information beyond ATR compression?
3. Does RS acceleration add more than RS percentile?
4. Do nearest-neighbour analogue outcomes improve ranking?

---

## Phase 4 — Bear-Market Resilience

Questions:

1. Which stocks consistently under-react to broad-market stress?
2. Which ones recover unusually quickly?
3. Do those names become the next leadership cohort?
4. Does the effect survive controlling for ordinary RS?

---

## Phase 5 — Choppy-Market Failure Detection

Questions:

1. Can sequence models detect false breakouts before obvious failure?
2. Can failed-breakdown reclaims be systematically traded?
3. Does range maturity predict whether the next boundary break will persist?
4. Does regime filtering materially improve expectancy?

---

## Phase 6 — Information Reaction Gap

This can be developed separately once the price-action architecture is stable.

Questions:

1. Do economically linked stocks show delayed price reactions in India?
2. Does AI identify useful relationships that static sector mapping misses?
3. Does price-action confirmation improve the raw propagation signal?
4. Is there incremental alpha after sector/RS controls?

---

# Minimum Viable Research Stack

A first prototype does not require an enormous platform.

## Data

- daily OHLCV
- optional 5/15/30-minute OHLCV for EP work
- index data
- sector-index data
- IPO listing dates
- corporate-action adjusted prices
- survivorship-safe historical universe if possible

## Feature Families

### Price

- returns
- swing geometry
- distance to highs/lows
- pivot distance
- gap size
- close location
- wick ratios
- trend efficiency

### Volatility

- ATR
- realized volatility
- contraction ratios
- range decay
- volatility-of-volatility

### Volume

- RVOL
- volume dry-up
- up-volume vs down-volume
- volume concentration
- volume trend

### Relative Strength

- stock vs Nifty
- stock vs sector
- RS slope
- RS acceleration
- RS percentile
- downside/upside capture

### Anchored Reference Levels

- listing AVWAP
- EP AVWAP
- breakout AVWAP
- major pivot AVWAP where useful

### Regime

- bull
- bear
- sideways/choppy
- transition

The regime classifier should itself be deterministic or at least independently validated.

---

# Backtesting Standards

Any apparent AI edge should be treated as guilty until proven innocent.

## Required Controls

- no look-ahead
- point-in-time universe
- adjusted historical data
- delisted stocks included where possible
- realistic slippage
- liquidity filters
- circuit constraints
- transaction costs
- walk-forward validation
- untouched holdout period
- multiple market regimes
- benchmark against simple deterministic baselines

## Every Model Must Beat a Simple Baseline

Examples:

| AI Model | Baseline It Must Beat |
|---|---|
| EP Quality | Gap + RVOL + close-location |
| IPO Maturity | Listing AVWAP + 20D high + volume contraction |
| Bull Ignition | VCP + RS + ATR contraction |
| Bear Resilience | Relative strength vs Nifty |
| Choppy Failure | breakout distance + volume + close-back-inside |
| Reaction Gap | sector RS + own-price momentum |

If the AI version cannot materially beat the baseline after costs, abandon it.

---

# What Would Count as a Real Edge?

Not simply higher accuracy.

A useful trading edge should demonstrate:

1. **monotonicity**  
   Higher model score should produce progressively better outcomes.

2. **incremental information**  
   It must add something beyond conventional technical factors.

3. **stability**  
   It should work across multiple years and market conditions.

4. **tradability**  
   The effect should survive liquidity constraints and slippage.

5. **out-of-sample survival**  
   The strongest test is performance on untouched data.

6. **reasonable breadth**  
   It should not depend on five freak historical examples.

7. **explainable failure conditions**  
   We should know when the model is likely to stop working.

---

# The Larger Thesis

The promising AI edge in Indian technical swing trading is not necessarily discovering a magical new indicator.

Indicators compress market information.

That often throws away precisely the information AI is best positioned to exploit:

- path geometry
- temporal ordering
- changing volatility
- interaction of volume and price
- multi-timeframe structure
- cross-sectional behaviour
- sequence similarity
- historical analogues

The more interesting architecture is therefore:

```text
RAW PRICE / VOLUME PATH
          │
          ▼
   AI STATE PERCEPTION
          │
          ▼
SETUP / REGIME CLASSIFICATION
          │
          ▼
HISTORICAL ANALOGUE RETRIEVAL
          │
          ▼
OUTCOME DISTRIBUTION
          │
          ▼
DETERMINISTIC ENTRY / RISK RULES
```

That is fundamentally different from:

```text
RSI > 60
AND
Price > 50DMA
AND
Volume > 2x
```

The second approach is useful, but already easy for everyone to replicate.

The first approach attempts to exploit something AI changes materially:

> **the ability to compare today's full market state against tens or hundreds of thousands of prior states, continuously, across the entire Indian equity universe.**

---

# Final Priority

For Indian swing/momentum trading, the most compelling practical R&D path is:

```text
EP QUALITY
    ↓
IPO BASE MATURITY
    ↓
BULL IGNITION
    ↓
BEAR RESILIENCE
    ↓
CHOPPY FAILURE DETECTION
    ↓
REACTION-GAP OVERLAY
```

The first five form a coherent **AI Price-Action State Engine**.

The sixth, the **AI Information Reaction Gap**, can later become a separate context layer that feeds technically confirmed opportunities into the same execution framework.

The eventual goal is not an AI that tells the trader what it "thinks."

It is an engine that says:

> **This market state has appeared 247 times before. These are the closest analogues. Here is how they behaved. Here is the distribution of upside, downside, failure, and time-to-resolution. Here is the deterministic trigger if you want to trade it.**

That is a much stronger foundation for a genuine AI-native trading edge.
