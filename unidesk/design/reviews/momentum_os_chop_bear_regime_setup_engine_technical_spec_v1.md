# Momentum OS — Regime-Adaptive Setup Engine
## Chop & Bear Regime Extension Technical Specification v1.0

**Status:** Proposed  
**Market:** Indian equities, NSE cash-first  
**Primary holding styles:** intraday, swing, short positional  
**Source doctrine:** Chhirag Kedia + Manas Arora + Sakatas Homma/Prakash + Umang/StocksGeeks manuals  
**External research role:** validate/add regime ideas where the four manuals are incomplete; never overwrite source teachings silently  
**Core design principle:** **do not force a momentum-breakout system to keep behaving like a momentum-breakout system when the market stops rewarding momentum breakouts.**

---

# 0. Executive Verdict

Momentum OS currently has a natural bias toward:

```text
BULL / EXPANSION
      │
      ▼
leaders
      │
      ▼
tight setup
      │
      ▼
breakout / momentum continuation
```

That is appropriate when the market is paying continuation traders.

It becomes structurally wrong when the market transitions into:

```text
CHOP
→ breakout failure
→ range rotation
→ repeated reclaims
→ mean reversion
→ shorter follow-through

BEAR
→ persistent downside
→ scarce continuation longs
→ violent countertrend bounces
→ stock-specific EP / IPO exceptions
→ capital preservation becomes a strategy
```

The solution is **not** to weaken the quality threshold until ordinary breakouts begin passing again.

The solution is a **Regime-Adaptive Setup Router**.

```text
                         MARKET STATE
                              │
               ┌──────────────┼───────────────┐
               ▼              ▼               ▼
             BULL            CHOP            BEAR
               │              │               │
               ▼              ▼               ▼
        continuation      reversion /      defence /
        expansion         range /          exceptions /
        persistence       failed moves     reversal
               │              │               │
               └──────────────┼───────────────┘
                              ▼
                       SETUP-SPECIFIC
                    RISK + EXIT POLICY
```

The system should ask:

> **What behavior is the market currently rewarding?**

not:

> **Which of our bull-market scans can still find something?**

---

# 1. Source Doctrine

The four manuals remain the primary trading doctrine.

External research is used for:

- regime validation,
- liquidity effects,
- market microstructure,
- short-selling feasibility,
- India-specific surveillance constraints,
- challenger hypotheses.

Every setup in this specification receives one of three provenance tags:

```text
[M]  MANUAL-DERIVED
[R]  EXTERNAL-RESEARCH-DERIVED
[P]  PRODUCT / RESEARCH PROPOSAL
```

A setup can have multiple tags.

Example:

```text
Range-Low Undercut & Reclaim
[M] Manas Busted
[M] Prakash Shakeout
[M] Umang Fakeout / Reset
[P] formalized as a chop-specific engine
```

This prevents the product from attributing our own synthesis to a trader.

---

# 2. What the Four Manuals Already Give Us

## 2.1 Chhirag

Relevant regime teachings:

- situational awareness should change strategy priority;
- broad-market context changes the opposing force a stock must overcome;
- bull pullback, early bear, mature bear and flash-crash behavior should not be treated identically;
- future leaders can begin basing during late bear phases;
- reversal family includes bottom bounce, undercut-and-rally and failure reversal;
- short-side family includes Weak Structure Short and Parabolic Short;
- EP can operate as a stock-specific exception;
- sell-strength and sell-weakness objectives differ;
- repeated breakout failure and stop-outs are market information.

**What this contributes to the engine:**

```text
REGIME
→ strategy family changes

STOCK CYCLE
can differ from market cycle

BEAR
does not imply
"every stock is equally bad"
```

---

## 2.2 Manas

Relevant teachings:

- price reaction matters more than prediction;
- falling knives / bottom bounces are a legitimate strategy family after severe weakness;
- reversal candidates should preferably have been strong before the fall;
- Busted exploits a fast failed break at an obvious level;
- Strong Start is an entry trigger, not the whole setup;
- repeated failures in the trader's own positions are a market signal;
- second and third attempts can be valid if the setup rebuilds;
- a squat is not automatically failure;
- high-quality daily context must precede lower-timeframe execution.

**Contribution:**

```text
CHOP
→ failed expectations can create edge

BEAR
→ reversal candidates should be
former strength, not random weakness
```

---

## 2.3 Sakatas Homma / Prakash

Relevant teachings:

- breadth is a risk dial;
- pullback trading can be more appropriate than chasing breakouts;
- oversold breadth can identify bounce conditions;
- shakeout count can rise near reversals;
- ACR / support confluence / AVWAP can create low-risk pullback locations;
- DTL breakout is anticipation, not proof of reversal;
- squat management should change with market quality;
- sell-on-strength is more useful in choppy / pullback-prone markets;
- progressive exposure should respond to market feedback;
- market price remains primary even when breadth is useful.

**Contribution:**

```text
CHOP
→ buy location and sell strength
can matter more than breakout confirmation

BEAR / WASHOUT
→ breadth can identify
countertrend opportunity windows
```

---

## 2.4 Umang

Relevant teachings:

- MBI / 4.5R determine aggression;
- 4.5R measures upside vs downside burst asymmetry;
- ordinary mid-market intraday setups should be avoided when 4.5R is weak;
- IPO and EP are treated as relatively "timeless" stock-specific opportunities;
- fakeout / shakeout / reset is particularly useful in difficult markets;
- oversold-reversal framework requires increasingly extreme conditions during a mature decline;
- prior-low undercut is preferred in reversal attempts;
- high-RS stocks and strong sectors should be prioritized during early recovery;
- Spot Burst requires a first leg and an above-VWAP base;
- intraday opening is more productive than midday in his process;
- normal VWAP respect across candidates gives real-time market feedback.

**Contribution:**

```text
BEAR
→ IPO / EP / exceptional RS

CHOP
→ intraday only when burst / tape supports it

REVERSAL
→ progressively stricter
as bear trend matures
```

---

# 3. External Research Findings That Matter

## 3.1 Momentum and reversal both exist in Indian equities

A 2023 peer-reviewed study using 3,956 BSE-listed stocks from 2000–2021 reports:

- intermediate and long-horizon momentum in Indian equities;
- stronger momentum among high-turnover / liquid stocks;
- short/intermediate reversal effects concentrated more heavily among illiquid stocks;
- the reversal effect is shorter-lived than momentum.

**Product implication:**

> Do not interpret "mean reversion exists in India" as permission to buy random collapsed smallcaps.

The academically stronger reversal effect occurs in the exact liquidity bucket where Momentum OS faces:

- slippage,
- circuits,
- trade-to-trade risk,
- ASM/GSM,
- exit uncertainty.

Therefore the production chop engine should focus on:

```text
MEAN REVERSION OF QUALITY

not

MEAN REVERSION OF JUNK
```

This is one of the most important design constraints in the spec.

---

## 3.2 Regime dependence is a valid research hypothesis

A 2026 Indian-equity working paper reports momentum signals weakening in crash states while reversal signals strengthen.

This is **preliminary / working-paper evidence**, not enough to hard-code production thresholds.

Use it as a challenger hypothesis:

```text
CALM / TREND
→ momentum weight ↑

PANIC / CRASH
→ reversal candidate weight ↑
```

Validate independently on the Momentum OS point-in-time NSE dataset.

---

## 3.3 NSE intraday liquidity is U-shaped

Published NSE microstructure research finds intraday liquidity / volume patterns are broadly U-shaped:

```text
OPEN          MIDDAY          CLOSE
high             low            high
```

This supports the manual observation that:

- opening trades have different execution characteristics;
- midday trades should require more selectivity;
- time-of-day must be part of the intraday setup definition.

It does **not** prove Umang's exact setup thresholds.

---

## 3.4 India-specific surveillance must be part of setup eligibility

NSE currently operates multiple surveillance mechanisms including:

- ASM,
- GSM,
- Trade-for-Trade,
- periodic call auctions,
- price-band reviews,
- enhanced surveillance.

GSM stages can involve:

- 100% margin,
- 5% or lower price bands,
- Trade-for-Trade,
- additional surveillance deposits,
- weekly-only trading at higher stages.

Therefore:

```text
a statistically attractive reversal
can still be operationally untradeable.
```

The tradeability gate must run **before** the setup ranker.

---

# 4. Primary Product Principle

The engine should not think in only:

```text
BULL
CHOP
BEAR
```

That is too coarse.

Use **regime + substate**.

---

# 5. Regime Taxonomy v2

```text
REGIME
│
├── BULL
│   ├── BULL_EXPANSION
│   ├── BULL_PULLBACK
│   └── BULL_LATE
│
├── CHOP
│   ├── CHOP_BALANCED
│   ├── CHOP_BULLISH
│   ├── CHOP_DISTRIBUTIVE
│   └── CHOP_WASHOUT
│
├── BEAR
│   ├── BEAR_TREND
│   ├── BEAR_PANIC
│   ├── BEAR_RALLY
│   └── BEAR_LATE_BASEBUILD
│
└── TRANSITION
    ├── RECOVERY
    └── DETERIORATION
```

This matters because:

```text
CHOP_BALANCED
and
CHOP_DISTRIBUTIVE

may both look sideways on NIFTY
but should not trade the same.
```

---

# 6. Regime Inputs

Regime classification should remain deterministic.

Suggested inputs:

```yaml
price:
  nifty_trend:
  nifty_midsmall_trend:
  distance_20dma:
  distance_50dma:
  slope_20dma:
  slope_50dma:
  swing_structure:

breadth:
  pct_above_10dma:
  pct_above_20dma:
  pct_above_50dma:
  pct_above_200dma:
  new_high_new_low:
  net_4pct:
  mbi_state:
  burst_4_5r:
  breadth_direction:

momentum:
  index_roc:
  cross_sectional_momentum:
  breakout_followthrough:
  median_mfe_5d:
  failure_rate_3d:

leadership:
  leading_sector_count:
  leader_density:
  rs_persistence:
  sector_concentration:

volatility:
  index_atr_percentile:
  cross_sectional_atr:
  gap_frequency:
```

---

# 7. Do Not Let the LLM Classify Regime From Narrative

The local TA model may explain:

```text
why the current state behaves like chop
```

but the state itself must come from deterministic data.

```text
DATA
  ↓
REGIME ENGINE
  ↓
CHOP_DISTRIBUTIVE
  ↓
LLM explanation
```

not:

```text
chart screenshot
  ↓
LLM opinion
  ↓
"looks choppy"
```

---

# 8. Setup Router

Every setup receives:

```yaml
setup_id:
family:
provenance:
allowed_regimes:
preferred_substates:
forbidden_substates:
required_context:
entry_model:
stop_model:
management_model:
max_holding_intent:
risk_class:
tradeability_requirements:
validation_status:
```

Example:

```yaml
setup_id: CHOP_RANGE_RECLAIM
family: RANGE_MEAN_REVERSION
provenance: [M, P]
allowed_regimes:
  - CHOP_BALANCED
  - CHOP_BULLISH
preferred_substates:
  - CHOP_BALANCED
forbidden_substates:
  - BEAR_TREND
entry_model: UNDERCUT_RECLAIM
management_model: MIDRANGE_THEN_STRENGTH
```

---

# 9. Regime × Setup Matrix

Legend:

```text
A = primary
B = secondary / reduced risk
C = exceptional only
X = disabled
```

| Setup family | Bull expansion | Bull pullback | Chop balanced | Chop distributive | Bear trend | Bear panic | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| Base Breakout | A | B | C | X | X | X | B |
| Momentum Burst | A | B | C | X | X | X | B |
| Pocket Pivot | A | A | B | C | C | X | A |
| Linear Pullback | A | A | A | B | C | X | A |
| EP | A | A | A | B | B | C | A |
| IPO Base | A | A | A | B | B | C | A |
| Power Play | A | B | C | X | X | X | B |
| Range-Low Reclaim | C | B | A | B | C | B | B |
| Range Rotation | X | C | A | C | X | X | C |
| Busted / Failed Breakdown | B | A | A | B | C | A | A |
| Shakeout / Reset | B | A | A | A | B | A | A |
| Leader Mean-Reversion Pullback | B | A | A | B | C | B | A |
| Oversold Breadth Bounce | X | C | B | B | C | A | A |
| Bottom Bounce | X | C | B | B | C | A | A |
| Intraday VWAP Reclaim | B | B | A | B | B | A | A |
| Intraday Spot Burst | A | A | B* | C* | C* | C* | A |
| Strong Start | A | A | A | B | B | B | A |
| Weak Structure Short | X | X | Optional | Optional | Optional | Optional | Optional |

`*` requires real-time burst / breadth confirmation.

This matrix is a **research starting point**, not a frozen production truth.

---

# PART I — CHOP ENGINE

# 10. What "Chop" Means Operationally

Chop is not simply:

```text
NIFTY flat for 20 days
```

The strategy-relevant definition is:

```text
price repeatedly reverses
before directional expansion compounds
```

Typical evidence:

- index trapped in overlapping range;
- breakout follow-through deteriorates;
- many stocks trigger then squat/fail;
- breadth oscillates rather than trends;
- sector leadership rotates rapidly;
- MFE arrives quickly then gives back;
- breakout-to-stop latency shortens;
- mean distance from short moving averages repeatedly compresses.

---

# 11. Chop Failure Mode of a Bull-Market System

```text
tight base
   ↓
breakout
   ↓
+1R
   ↓
reversal
   ↓
stop / breakeven
   ↓
next breakout
   ↓
same thing
```

The setup detector may still be "correct."

The **management objective is wrong**.

This is why the regime layer must alter:

- entry location,
- profit expectation,
- partial-taking behavior,
- holding period,
- number of attempts.

---

# 12. CHOP Setup 1 — Range-Low Undercut & Reclaim

**Provenance:** [M] Manas Busted + [M] Prakash Shakeout + [M] Umang Fakeout/Reset + [P] range formalization

## Objective

Exploit a failed breakdown at the lower edge of a well-established range.

```text
RANGE HIGH
────────────────────────
      /\        /\
     /  \      /  \
    /    \____/    \
────────────────────────
RANGE LOW
                ↓ break
                 \__
                    \↑ reclaim
```

The trade is not:

> "price is cheap."

It is:

> "an expected downside continuation failed at a level where failure matters."

---

# 13. Range-Low Requirements

Required:

```text
[ ] established horizontal / gently rising range
[ ] at least 2 prior reactions near lower boundary
[ ] stock is not in clear Stage-4 / persistent downtrend
[ ] sufficient liquidity
[ ] no severe ASM/GSM/Trade-for-Trade restriction
[ ] lower-bound violation
[ ] fast reclaim
```

Preferred:

```text
[ ] prior stock quality / RS
[ ] sector not collapsing
[ ] AVWAP / 20EMA / 50DMA confluence
[ ] lower-tail or Busted-type intraday reaction
[ ] breadth not accelerating lower
```

---

# 14. Entry

Two variants.

## A. Busted Entry

```text
support breaks
      ↓
fast rejection
      ↓
entry > rejection-bar high
stop  < reaction low
```

## B. Close Reclaim

For less active users:

```text
daily close back inside range
      ↓
next-session tight trigger
```

---

# 15. Exit Objective

Do **not** assume range breakout.

Default chop target hierarchy:

```text
ENTRY
  ↓
MID-RANGE
  ↓
decide:
  ├─ take majority
  └─ retain small runner if breadth improves
```

Optional:

```text
upper-range supply
→ sell strength
```

This is intentionally different from bull-regime management.

---

# 16. Invalidation

Cancel / stop when:

- reclaim fails quickly;
- price accepts below range;
- market changes from balanced chop to distributive decline;
- lower boundary becomes repeated pivot-cut noise;
- circuit/liquidity conditions make the stop unreliable.

---

# 17. CHOP Setup 2 — Leader Mean-Reversion Pullback

**Provenance:** [M] Chhirag linear pullback + [M] Manas prior-force reversal selection + [M] Prakash pullback/confluence + [P] chop-specific routing

This is the preferred mean-reversion family.

It is **not loser mean reversion**.

---

# 18. Concept

Find a stock that is:

```text
good stock
+
temporarily stretched down
+
still structurally intact
```

rather than:

```text
bad stock
+
down a lot
```

ASCII:

```text
STRONG PRIOR TREND
        /
       /
      /
     /
    /\
   /  \__
--/------\---------- 20/21 EMA / AVWAP
            ↑
        controlled turn
```

---

# 19. Required Context

```text
[ ] prior force / momentum exists
[ ] stock was leader or high RS
[ ] current pullback is not structural collapse
[ ] stock remains near relevant trend / support
[ ] selling force contracts
[ ] liquid enough for planned size
```

Preferred support cluster:

```text
21EMA
+
AVWAP
+
prior breakout
+
range midpoint / lower quartile
```

Do not require every level.

---

# 20. Trigger Families

Possible trigger:

- Strong Start;
- Busted;
- bullish rejection;
- lower-timeframe mini-base;
- PBC;
- first higher low;
- VWAP reclaim intraday.

The setup is the **pullback context**.

The trigger is only entry timing.

---

# 21. Management

In CHOP:

```text
+2R to +4R / extension
→ partial sell

runner
→ short structural trail
```

Exact R thresholds must come from strategy research, not manual dogma.

The principle is manual-supported:

> in choppy / pullback-prone conditions, sell-on-strength becomes more attractive.

---

# 22. CHOP Setup 3 — Range Rotation

**Provenance:** [P] with manual support from support/reversal frameworks

This is the most "classic" range setup.

Use only in truly balanced chop.

```text
UPPER SUPPLY
────────────────────────
      sell / reduce zone

        FAIR VALUE
- - - - - - - - - - - -

      buy / trigger zone
────────────────────────
LOWER DEMAND
```

---

# 23. Why This Must Be Separate From Range-Low Reclaim

Range Rotation does not require an actual breakdown.

It requires:

```text
repeated range behavior
+
sufficient distance from equilibrium
+
evidence of a turn
```

Because it lacks a trapped-breakdown catalyst, it should normally rank **below** a clean undercut-and-reclaim.

---

# 24. Range Rotation Entry Zone

Do not buy simply at "support."

Calculate:

```text
range_percentile =
(price - range_low)
/
(range_high - range_low)
```

Research initial zone:

```text
lower 20–35% of established range
```

Then require turn evidence.

The percentile is [P], not source-derived.

---

# 25. Range Rotation Exit

Default:

```text
first objective = range midpoint
second objective = upper quartile
```

This prevents the engine from converting every mean-reversion trade into an attempted breakout.

---

# 26. CHOP Setup 4 — Failed Breakout → Reset → Re-entry

**Provenance:** [M] Manas second attempt / squat + [M] Umang fakeout-reset + [M] Chhirag failed-poke logic

The wrong implementation:

```text
breakout fails
→ revenge buy
```

Correct:

```text
breakout fails
   ↓
weak hands removed
   ↓
structure remains valid
   ↓
new tight reset forms
   ↓
fresh trigger
```

ASCII:

```text
pivot ─────────────────────
          ↑ break
           \ fail
            \____
                 └── tight reset
                        ↑
                     new entry
```

This can work well in chop because the first obvious breakout is often crowded and the later reset improves entry geometry.

---

# 27. Reset Requirements

```text
[ ] original higher-timeframe setup remains intact
[ ] failed breakout did not create structural damage
[ ] price reclaims important level
[ ] new contraction / base forms
[ ] new stop is definable
[ ] second attempt is a new trade
```

Do not increase risk because the first attempt lost.

---

# 28. CHOP Setup 5 — AVWAP / Value Reclaim

**Provenance:** [M] Prakash AVWAP + [M] Umang VWAP behavior + [P] chop routing

Useful anchors:

- major breakout;
- earnings / EP;
- swing low;
- range impulse start.

Structure:

```text
ANCHOR
  ↓
AVWAP ──────────────────────
            \
             \ below
              \__
                 \↑ reclaim
```

The idea:

> price returns to an economically meaningful average cost and proves acceptance back above it.

---

# 29. AVWAP Reclaim Requirements

```text
[ ] anchor has a clear reason
[ ] AVWAP intersects meaningful structure
[ ] stock is not simply trending down through every reference
[ ] reclaim is decisive enough to create nearby invalidation
```

Better:

```text
AVWAP
+
range support
+
relative strength
```

than random AVWAP fitting.

---

# 30. CHOP Setup 6 — Intraday VWAP Reclaim / First Bounce

**Provenance:** [M] Prakash first AVWAP bounce + [M] Umang VWAP respect

Use for liquid candidates with clear intraday strength.

```text
OPENING FORCE
      /
     /
    /
---/---------------- VWAP
   \__
      \↑ first clean bounce
```

Preferred:

- first meaningful test;
- strong daily candidate;
- high thrust / liquidity;
- sector active;
- market tape not collapsing.

Repeated fourth/fifth bounces should rank lower.

---

# 31. CHOP Setup 7 — Intraday Spot Burst

**Provenance:** [M] Umang

Only allow when:

```text
first leg
+
base above VWAP
+
adequate liquidity
+
intraday burst environment
```

In chop, **4.5R / equivalent burst breadth matters more**.

```text
CHOP + weak 4.5R
→ disable ordinary Spot Burst

CHOP + strong opening burst
→ allow selectively
```

---

# 32. CHOP Setup 8 — EP / IPO Exception

**Provenance:** [M] all four manuals, especially Umang/Chhirag

A choppy index does not invalidate a stock-specific repricing event.

Prioritize:

```text
fresh EP
fresh IPO
major news repricing
sector-wide catalyst
```

But management should still respect chop:

```text
quick follow-through?
  ├─ yes → retain
  └─ no  → de-risk faster
```

---

# 33. What NOT to Add to Chop

Do not add production setups such as:

```text
"RSI < 30 → buy"
"down 10% this week → mean revert"
"touch lower Bollinger → buy"
"three red candles → bounce"
```

without context.

Why:

- generic mean reversion can concentrate in poor-liquidity names;
- price can remain oversold;
- deteriorating chop can become a bear trend;
- circuits can dominate theoretical expectancy.

---

# PART II — BEAR ENGINE

# 34. Bear Market Prime Directive

The engine must allow:

```text
NO TRADE
```

as a successful decision.

This is critical.

```text
BEAR
  │
  ├── ordinary continuation long? → mostly disabled
  ├── stock-specific exception?   → inspect
  ├── panic reversal?             → inspect
  ├── recovery leader?            → inspect
  └── nothing valid?              → CASH
```

A regime router that always finds a setup is broken.

---

# 35. Bear Substates

## BEAR_TREND

Persistent lower highs/lower lows, breadth poor, downside not yet washed out.

Best default:

```text
cash
+
EP/IPO/high-RS exceptions
+
intraday only selectively
```

## BEAR_PANIC

Extreme downside burst / washed-out breadth.

Potential:

```text
bottom bounce
oversold reversal
failed breakdown
```

## BEAR_RALLY

Countertrend advance after panic.

Potential:

```text
high-RS leaders
first pullbacks
event leaders
short swing windows
```

## BEAR_LATE_BASEBUILD

Broad market still poor, but future leaders stop falling.

Potential:

```text
watchlist building
early RS
Stage-1/early Stage-2 transition
selective entries
```

---

# 36. BEAR Setup 1 — EP / Event Repricing

**Provenance:** [M]

This is the highest-priority long exception.

```text
BEAR MARKET
     │
     ▼
company-specific event
     │
     ▼
stock refuses market gravity
```

Required:

- actual event or event-like repricing;
- strong price reaction;
- liquidity;
- structure allowing defined risk.

Preferred:

- sector confirmation;
- repeated demand after initial reaction;
- strong relative behavior.

---

# 37. Bear EP Management

Do not assume a bear-market EP deserves bull-market holding periods.

Default logic:

```text
event works immediately
   ↓
protect capital sooner
   ↓
let exceptional stock earn
the right to become positional
```

This fits the manuals' uncertainty-first approach.

---

# 38. BEAR Setup 2 — IPO Exception

**Provenance:** [M]

Fresh IPOs can trade on their own lifecycle.

But bear-market eligibility should be stricter:

```text
[ ] fresh enough that old overhead supply is limited
[ ] liquidity acceptable
[ ] no severe surveillance restriction
[ ] pattern/candle behavior strong
[ ] relative strength obvious
```

Do not treat "IPO" as a permanent bonus after the stock has already matured.

---

# 39. BEAR Setup 3 — High-RS Refuge / Future Leader

**Provenance:** [M] all four manuals

The key bear-market scan is not:

```text
which stock is cheapest?
```

It is:

```text
which stock refuses to fall?
```

Examples of desirable behavior:

```text
Market  -15%
Stock    -2%

Market makes new low
Stock makes higher low

Market panic
Stock closes flat / green
```

---

# 40. Future-Leader State

Candidate states:

```text
RS_REFUGE
BASEBUILDING
EARLY_RECOVERY
```

Do not automatically enter `RS_REFUGE`.

It is often a **watchlist state**.

Entry still requires:

- structure,
- trigger,
- risk geometry.

---

# 41. BEAR Setup 4 — Bottom Bounce

**Provenance:** [M] Manas + Chhirag

This is a **countertrend trade**, not a declaration that the bear market ended.

Structure:

```text
INTENSE SELLING
    ↓
multiple weak days
    ↓
panic / exhaustion
    ↓
turn
    ↓
1–3 day bounce objective
```

The Chhirag/Manas material explicitly distinguishes this from normal Stage-2 continuation.

---

# 42. Bottom-Bounce Candidate Selection

Prefer:

```text
strong stock before decline
+
temporary extreme selloff
```

over:

```text
persistent Stage-4 collapse
```

Both can bounce.

But the former offers a better chance of durable demand.

---

# 43. Bottom-Bounce Trigger

Possible:

- Strong Start;
- Busted;
- undercut/reclaim;
- opening flush followed by reclaim;
- first higher low;
- VWAP reclaim.

Do not buy the falling bar itself simply because breadth is oversold.

---

# 44. Bottom-Bounce Holding Intent

Default:

```text
COUNTERTREND
```

not:

```text
POSITIONAL
```

Initial product policy:

```text
expected duration
1–3 sessions
```

as a manual-derived working family, then validate empirically.

If the stock develops a new base later:

```text
new trade thesis
```

not extension of the old bounce.

---

# 45. BEAR Setup 5 — Umang Oversold Reversal

**Provenance:** [M] Umang

This should be implemented as a special strategy module.

Conditions:

```text
current oversold episode
must be more extreme
than prior oversold episode

prefer panic

prefer prior-low undercut

avoid extreme gap volatility

later bear attempts
require more extreme readings
```

ASCII:

```text
Oversold #1       20
     ↓ bounce
lower high
     ↓
Oversold #2       12
     ↓ bounce
lower high
     ↓
Oversold #3        6

threshold becomes stricter
as bear trend matures
```

The exact numbers depend on Umang's indicator implementation and should not be universalized.

---

# 46. Oversold Reversal Safety Gate

Required:

```text
[ ] regime = BEAR_PANIC / CHOP_WASHOUT
[ ] breadth extreme
[ ] no huge untradeable gap
[ ] liquid stock
[ ] structurally meaningful reclaim
```

Reject:

```text
oversold oscillator alone
```

---

# 47. BEAR Setup 6 — Failed Breakdown / Busted

**Provenance:** [M] Manas + Prakash + Umang

This is often superior to blind bottom fishing because the market provides a defined invalidation.

```text
OBVIOUS LOW
──────────────
      ↓ breakdown
       \__
          \↑ immediate reclaim
```

The failed expectation can create:

- trapped shorts / breakdown traders;
- forced exits;
- new reversal buyers.

---

# 48. BEAR Setup 7 — Bear Rally First Pullback

**Provenance:** [M] manual synthesis + [P] regime formalization

After a valid panic reversal:

```text
PANIC LOW
   ↓
THRUST
   ↓
FIRST CONTROLLED PULLBACK
```

Prefer:

- stocks that led the bounce;
- high RS before/during panic;
- sector groups participating;
- low-volume pullback;
- first test of 10/20/21EMA or AVWAP.

This is **not** the same as a fresh bull-market continuation.

Management remains more defensive until regime improves.

---

# 49. BEAR Setup 8 — Intraday Strong Start

**Provenance:** [M]

A bear market can still produce:

- earnings gaps;
- sector squeezes;
- stock-specific order/news bursts.

Strong Start can direct attention.

But:

```text
Strong Start
≠ automatic long
```

Require:

- valid higher-timeframe context;
- liquidity;
- tight intraday invalidation.

---

# 50. BEAR Setup 9 — Intraday VWAP Reclaim After Flush

**Provenance:** [M] + [P]

Structure:

```text
OPEN
 │
 ▼
flush
  \
   \
----\-------------- VWAP
     \__
        \↑ reclaim
```

Best candidates:

- prior leaders;
- stock-specific catalyst;
- sector strength;
- broad panic followed by tape improvement.

Avoid if:

```text
VWAP repeatedly fails
+
4.5R / breadth remains poor
```

---

# PART III — OPTIONAL SHORT-SIDE MODULE

# 51. Default Product Position

Momentum OS is currently **NSE cash-equity long-first**.

Therefore:

```text
SHORT SETUPS
should not contaminate
the default candidate ranking.
```

Create a separate optional module:

```text
BEAR_SHORT_LAB
```

---

# 52. Indian Short-Selling Constraint

SEBI permits short selling, but naked short selling is not permitted; delivery obligations must be met.

For overnight / multi-day short exposure, practical implementation generally requires:

- F&O,
- or Securities Lending & Borrowing (SLB),
- plus broker support and eligibility.

NSE SLB currently supports fixed tenures and is concentrated largely in securities also traded in F&O.

Therefore:

```text
cash-only swing tool
≠ frictionless US-style short scanner
```

---

# 53. Optional Short Families

Manual-derived candidates:

```text
Chhirag
- Weak Structure Short
- Parabolic Short

Manas-style behavioral analogue
- failed rally / failed expectation

Prakash
- reversal concepts can be mirrored,
  but long-side manual is primary
```

Do not enable until:

- execution venue defined,
- borrow/F&O eligibility verified,
- costs modeled,
- short-specific backtests passed.

---

# 54. Weak Structure Short

Concept:

```text
fast decline
    ↓
weak corrective bounce
    ↓
bounce loses force
    ↓
short turn
```

Prefer:

- mature / damaged former leader;
- weak relative strength;
- bear market;
- no nearby earnings event unless event itself drives thesis.

This should remain **conceptual / optional** in a cash-first product.

---

# 55. Parabolic Short

Only for:

```text
mature extreme extension
+
clear failure
+
weak bounce / breakdown
```

Never:

```text
fresh Stage-2 leader
just because it "looks expensive"
```

---

# PART IV — REGIME-ADAPTIVE RISK ENGINE

# 56. Setup Eligibility Is Only Half the Job

A chop setup with bull-regime management can still fail.

Regime must alter:

```text
risk
holding intent
partial policy
profit giveback
number of simultaneous trades
re-entry tolerance
```

---

# 57. Risk Multiplier Policy

Do **not** hard-code source traders' personal risk.

Use configurable multipliers against the user's base risk.

Research starting grid:

```text
BULL_EXPANSION        1.00×
BULL_PULLBACK         0.75–1.00×
CHOP_BULLISH          0.75×
CHOP_BALANCED         0.50–0.75×
CHOP_DISTRIBUTIVE     0.25–0.50×
BEAR_TREND long       0–0.25×
BEAR_PANIC reversal   0.25–0.50×
BEAR_RALLY            0.50×
RECOVERY              0.50–0.75×
```

These values are [P] and must be validated.

---

# 58. Why Risk Must Fall Faster Than Setup Count

In chop/bear, you may still see many apparent setups.

That does not mean total open risk should remain constant.

Use:

```text
setup quality
×
regime compatibility
×
portfolio feedback
```

to determine allowed risk.

---

# 59. Regime Profit-Giveback Policy

## Bull

```text
allow more giveback
for magnitude / persistent trades
```

## Chop

```text
sell more strength
reduce runner size
```

## Bear reversal

```text
treat profit as fragile
unless market state improves
```

This directly integrates the Risk Desk's profit-at-risk model.

---

# 60. Maximum Holding Intent

Each setup declares:

```yaml
holding_intent:
  INTRADAY
  1_3_DAY
  SWING
  POSITIONAL
```

Regime can cap the intention.

Example:

```text
Bottom Bounce
setup allows: 1_3_DAY

BEAR_PANIC
→ 1_3_DAY

RECOVERY evolves
→ later new setup can become SWING
```

Do not silently extend a countertrend trade.

---

# PART V — SETUP SCORING

# 61. Do Not Use One Universal Setup Score

A 90/100 breakout score is meaningless in a regime where breakouts are not being paid.

Use:

```text
Intrinsic Setup Quality
+
Regime Fit
+
Tradeability
+
Entry Efficiency
```

---

# 62. Candidate Score Decomposition

```yaml
quality:
  stock_quality: 0-100
  structure_quality: 0-100
  setup_readiness: 0-100

context:
  regime_fit: 0-100
  sector_fit: 0-100
  breadth_fit: 0-100

execution:
  entry_efficiency: 0-100
  liquidity: 0-100
  stress_exitability: 0-100
```

Do not allow AI to invent these scores.

---

# 63. Regime Fit Score

Example deterministic policy:

```text
Range-Low Reclaim
CHOP_BALANCED       100
CHOP_BULLISH         90
CHOP_DISTRIBUTIVE    55
BEAR_TREND           20
BULL_EXPANSION       30
```

These mappings are product policy subject to backtesting.

---

# 64. Candidate UI Should Explain the Fit

Bad:

```text
Setup Score: 88
```

Better:

```text
WHY THIS IS A CHOP TRADE

✓ established 7-week range
✓ lower-bound undercut reclaimed
✓ RS still top decile
✓ 21EMA + AVWAP nearby
✓ breakout follow-through market-wide is poor
✓ target assumes range rotation, not breakout
```

---

# PART VI — CHOP / BEAR UI

# 65. Tonight Page

Add:

```text
REGIME
CHOP · BALANCED

WHAT IS WORKING
Range Reclaims       ↑
Leader Pullbacks     ↑
EP / IPO             →
Breakouts            ↓
Momentum Burst       ↓
```

This is more useful than:

```text
CHOP
```

alone.

---

# 66. Setup Family Cards

```text
CHOP PLAYBOOK

┌──────────────────────┐
│ RANGE RECLAIM        │
│ 6 candidates         │
│ High fit             │
└──────────────────────┘

┌──────────────────────┐
│ LEADER PULLBACK      │
│ 4 candidates         │
│ High fit             │
└──────────────────────┘

┌──────────────────────┐
│ EP / IPO             │
│ 3 candidates         │
│ Medium-high fit      │
└──────────────────────┘

BREAKOUTS
temporarily de-prioritized
```

---

# 67. Stock Card — Regime-Aware Explanation

```text
ABC LTD

REGIME FIT
CHOP RANGE RECLAIM · HIGH

     range high  ₹540
     ─────────────────
              ...
     midpoint    ₹505
     - - - - - - - - -
              ...
     range low   ₹472
     ─────────────────
                 ↓ undercut
                   ↑ reclaim

ENTRY AREA      ₹477–482
INVALIDATION    below reclaimed low
FIRST OBJECTIVE midpoint region

NOT A BREAKOUT TRADE
```

Exact order levels must come from deterministic engine.

---

# 68. Bear Screen

```text
BEAR MODE

DEFAULT
CASH / DEFENSIVE

EXCEPTIONS TODAY

EP / EVENT             3
IPO                     2
HIGH-RS REFUGE          5
BOTTOM BOUNCE           1
FAILED BREAKDOWN        2

Ordinary Breakouts
DISABLED
```

This prevents the system from feeling broken merely because it is not producing 40 candidates.

---

# 69. Intraday Panel

```text
INTRADAY TAPE

4.5R             612
ORBO / ORBD      1.8×
VWAP RESPECT     GOOD
Sector bursts    Defence · Pharma

ALLOWED
✓ Spot Burst
✓ VWAP first bounce
✓ Strong Start

MIDDAY
reduced quality
```

---

# PART VII — DETECTORS

# 70. Range Detector

Candidate range requirements:

```text
minimum duration
minimum reaction count
maximum slope
maximum width
```

Initial research formulation:

```text
duration >= 15 sessions
boundary touches >= 2 each side
linear-regression slope small relative to ATR
range width enough to support reward after costs
```

Do not freeze thresholds before backtest.

---

# 71. Undercut-Reclaim Detector

```text
low_t < range_low
AND
close_t > range_low
```

Optional stronger condition:

```text
close_t > previous_close
```

Intraday Busted variant:

```text
level breach
+
reclaim within N bars
```

`N` should be setup-specific; Manas source examples favor fast rejection.

---

# 72. Leader Mean-Reversion Detector

Required deterministic fields:

```text
RS percentile
prior trend return
trend maturity
distance from 20/21EMA
distance from AVWAP
pullback depth
pullback volume ratio
structural-damage flag
```

No single RSI threshold.

---

# 73. Oversold Breadth Detector

Inputs:

```text
pct above 10EMA
pct above 20EMA
pct above 50EMA
net 4% movers
4.5R
new lows
index ATR expansion
```

Output:

```text
NORMAL
STRETCHED
OVERSOLD
PANIC
```

The local Qwen model can explain but must not assign the state.

---

# 74. Panic Detector

Potential components:

```text
large negative breadth
large index true range
high cross-sectional downside burst
gap frequency
new-low expansion
```

Do not define "panic" with one red candle.

---

# 75. Regime Transition Detector

Most important transitions:

```text
BULL → CHOP
CHOP → BEAR
BEAR → RECOVERY
CHOP → BULL
```

Use:

- breadth direction;
- breakout success rate;
- leader density;
- market structure;
- median MFE;
- stop-out clustering.

---

# PART VIII — PORTFOLIO FEEDBACK

# 76. The Portfolio Is a Sensor

Across the manuals, trade feedback is repeatedly emphasized.

Add:

```text
recent qualified-trade hit rate
median 3D MFE
stop-out cluster
squat rate
time-to-1R
```

to regime context.

---

# 77. Feedback Rule

Example:

```text
REGIME = CHOP_BALANCED

but

last 8 high-quality reclaims:
6 failed quickly
breadth deteriorating
sector leadership shrinking

→ downgrade to CHOP_DISTRIBUTIVE
```

This should be deterministic and statistically smoothed.

---

# PART IX — INDIA TRADEABILITY GATE

# 78. Run Before Setup Detection

```text
SECURITY
   │
   ▼
SURVEILLANCE / LIQUIDITY GATE
   │
   ├─ fail → EXCLUDE
   └─ pass
        ▼
   SETUP ENGINE
```

---

# 79. Required India Fields

```yaml
series:
price_band:
asm_stage:
gsm_stage:
esm_status:
trade_for_trade:
periodic_call_auction:
adv_cr:
median_spread:
amihud:
circuit_distance:
delivery_pct:
```

---

# 80. Mean-Reversion Danger Flag

Specifically for reversal setups:

```text
illiquid
+
near lower circuit
+
GSM / T2T
+
high reversal score
```

must produce:

```text
REJECT
```

not:

```text
"high opportunity"
```

This directly addresses the Indian empirical reversal/liquidity paradox.

---

# PART X — RESEARCH PROGRAM

# 81. Do Not Assume These Setups Work

The four manuals are doctrine / hypotheses.

External papers are evidence / hypotheses.

Momentum OS must validate all production setup families point-in-time.

---

# 82. Primary Target Set

For every candidate at decision time:

```text
cont_3d
cont_5d
cont_10d
fail_1d
fail_3d
mfe_1d
mfe_3d
mfe_5d
mfe_10d
mae_1d
mae_3d
mae_5d
time_to_1R
time_to_stop
```

Use the existing research constitution's leakage protections.

---

# 83. Range-Reclaim Evaluation

Compare:

```text
A
all undercut/reclaims

B
liquid only

C
high-RS only

D
high-RS + sector-neutral/strong

E
high-RS + AVWAP confluence
```

Measure whether each filter adds value.

---

# 84. Mean-Reversion Evaluation

Do **not** define mean reversion as "loser portfolio."

Test separately:

```text
Leader pullback
Range-low reclaim
Oversold bounce
Failed breakdown
Random recent losers
```

The last cohort is a control.

Hypothesis:

```text
structured / quality reversion
should outperform
generic loser reversion
after costs and circuit filters
```

---

# 85. Chop Management Research

For the same entries compare:

```text
A hold 5D
B sell at midrange
C partial at 2R
D partial at 3R
E structural trail
F time stop
```

This is critical.

The entry may work but the **bull-style exit may destroy expectancy**.

---

# 86. Bear-Reversal Evaluation

Segment by:

```text
first oversold episode
second
third+

prior RS
prior trend quality
panic present?
undercut present?
gap size
```

This directly tests Umang/Manas/Chhirag reversal nuance.

---

# 87. Intraday Research

Segment by:

```text
opening
midday
close

4.5R bucket
VWAP respect
sector strength
thrust power
liquidity
```

The NSE U-shaped liquidity finding provides a reason to expect time-of-day effects, but the exact setup behavior must be measured on your data.

---

# 88. Regime-Specific Validation

Every setup report must include:

```text
Bull
Chop balanced
Chop distributive
Bear trend
Bear panic
Recovery
```

A setup is not "good" merely because aggregate expectancy is positive.

---

# 89. Walk-Forward

Use:

```text
train
embargo
validation
embargo
test
```

and point-in-time security status.

Do not accidentally use today's ASM/GSM classification for historical dates.

---

# 90. Slippage / Circuit Stress

For mean-reversion and bear strategies, report:

```text
normal fill P&L
+
stress fill P&L
+
circuit-impaired P&L
```

because reversal strategies systematically trade during abnormal volatility.

---

# PART XI — LOCAL QWEN MODEL ROLE

# 91. What the TA Model Can Add

The local model can explain:

```text
why this is a range reclaim
why this is not a clean bottom bounce
why the stock had prior leadership
why two manual rules conflict
why the current setup is countertrend
```

It should not decide:

```text
regime
quantity
risk multiplier
target
```

unless those values are supplied by deterministic code.

---

# 92. New Training Tasks

Add hard negatives:

```text
range support
but accepted breakdown
→ not reclaim

oversold
but persistent Stage-4 collapse
→ not preferred bottom-bounce candidate

VWAP reclaim
but no prior force
→ weak mean-reversion context

Spot Burst
but no first leg
→ reject

Busted
but reclaim takes too long
→ reject

Bear rally
but breadth still making new panic lows
→ countertrend quality low
```

---

# 93. Regime Explanation Task

Input:

```text
regime = CHOP_DISTRIBUTIVE
setup = BASE_BREAKOUT
```

Expected:

```text
The setup may be structurally valid,
but current regime historically penalizes
ordinary breakout follow-through.

Do not reinterpret the chart as bad.
Interpret regime fit as weak.
```

This distinction is useful for Momentum OS.

---

# PART XII — ALERT ENGINE

# 94. Regime Alert

```text
REGIME SHIFT

BULL_PULLBACK
→ CHOP_BALANCED

Breakout follow-through has weakened.
Range-reclaim and leader-pullback families
are now prioritized.
```

---

# 95. Setup Alert

```text
ABC · RANGE RECLAIM

✓ 6-week range
✓ lower boundary undercut
✓ daily close reclaimed
✓ RS 91
✓ sector neutral-positive

First objective:
range midpoint

This is a mean-reversion trade,
not a breakout call.
```

---

# 96. Bear Alert

```text
PANIC MODE

Breadth reached extreme downside.
No general long signal.

Watching:
3 high-RS former leaders
2 failed-breakdown candidates
1 EP

Risk governor remains REDUCED.
```

---

# PART XIII — ACCEPTANCE CRITERIA

# 97. Regime Engine

Must demonstrate:

```text
stable deterministic classification
no lookahead
reproducible historical states
clear substate transitions
```

---

# 98. Setup Engine

For each production family:

```text
minimum sample size documented
positive OOS expectancy after costs
no single year dominates
regime-specific edge demonstrated
stress/slippage tested
```

---

# 99. Mean-Reversion Safety

Production mean-reversion setup must not depend on:

```text
illiquidity
GSM/ASM distortion
lower-circuit entrapment
untradeable fills
```

If its edge disappears after removing those stocks:

> reject the strategy.

---

# 100. Bear Long Acceptance

Bear-long setup must outperform:

```text
cash
```

on the relevant decision horizon after costs and stress exits.

This is a much harder hurdle than merely having positive gross returns.

---

# 101. Short Module Acceptance

Do not enable until:

```text
eligible universe defined
borrow / F&O route defined
transaction costs modeled
gap risk modeled
broker execution tested
```

---

# PART XIV — IMPLEMENTATION PLAN

# 102. Phase 0 — Regime Audit

Before adding a new setup:

1. reconstruct historical regime states;
2. measure existing setup performance by regime;
3. quantify how badly ordinary breakouts degrade in chop/bear.

This tells us whether the problem is real and how large it is.

---

# 103. Phase 1 — Manual-Derived Chop Setups

Implement detectors:

```text
Range-Low Reclaim
Leader Mean-Reversion Pullback
Failed Breakout Reset
AVWAP Reclaim
Intraday VWAP Reclaim
EP / IPO exception
```

No new generic indicator strategy yet.

---

# 104. Phase 2 — Bear Long Setups

Implement:

```text
High-RS Refuge
Bottom Bounce
Oversold Reversal
Failed Breakdown / Busted
Bear-Rally First Pullback
EP / IPO exception
```

---

# 105. Phase 3 — Research-Derived Range Rotation

Only after the manual-derived families are benchmarked.

Implement balanced-range rotation with:

- range percentile,
- time-in-range,
- volatility,
- liquidity,
- turn trigger.

---

# 106. Phase 4 — Intraday Regime Layer

Add:

```text
4.5R
ORBO/ORBD
VWAP respect
time of day
sector burst
```

to setup eligibility.

---

# 107. Phase 5 — Risk Integration

Connect to Risk Desk:

```text
regime risk multiplier
profit giveback budget
holding-intent cap
open-risk ceiling
stress-risk ceiling
```

---

# 108. Phase 6 — Optional Short Lab

Research only.

Do not surface in default cash UI.

---

# 109. Phase 7 — Local Qwen Integration

Fine-tune / RAG hard-negative examples around:

- regime fit;
- reversal vs breakdown;
- range vs trend;
- countertrend expectations;
- setup scope.

---

# PART XV — FINAL OPERATING MODEL

```text
                         MOMENTUM OS
                              │
                              ▼
                       REGIME ENGINE
                              │
       ┌──────────────────────┼──────────────────────┐
       ▼                      ▼                      ▼
     BULL                    CHOP                   BEAR
       │                      │                      │
       ▼                      ▼                      ▼
 continuation            reversion /           exceptions /
 momentum                failed moves          reversal /
 persistence             range                 defence
       │                      │                      │
       └──────────────────────┼──────────────────────┘
                              ▼
                    INDIA TRADEABILITY GATE
                              │
                              ▼
                     SETUP-SPECIFIC DETECTOR
                              │
                              ▼
                        REGIME FIT
                              │
                              ▼
                       ENTRY GEOMETRY
                              │
                              ▼
                         RISK DESK
                              │
                              ▼
                         LIVE TRADE
                              │
                              ▼
                      MAE / MFE / CAPTURE
                              │
                              ▼
                         RESEARCH LOOP
```

---

# 110. Final Setup Priorities

## Bull

Primary:

```text
Base Breakout
Momentum Burst
Pocket Pivot
Power Play
Linear Pullback
EP
IPO
```

## Chop

Primary:

```text
Range-Low Undercut & Reclaim
Leader Mean-Reversion Pullback
Failed Breakout Reset
AVWAP / Value Reclaim
EP / IPO
Intraday VWAP / selective Spot Burst
```

Secondary:

```text
Range Rotation
Oversold bounce
```

Ordinary breakout:

```text
de-prioritized unless
regime substate / sector proves otherwise
```

## Bear

Default:

```text
CASH
```

Selective long:

```text
EP
IPO
High-RS Refuge
Bottom Bounce
Oversold Reversal
Failed Breakdown / Busted
Bear-Rally First Pullback
Intraday Strong Start / VWAP reclaim
```

Optional separate short lab:

```text
Weak Structure Short
Parabolic Short
```

---

# 111. The Most Important Design Rule

Do not optimize the system for:

> **finding something to trade every day.**

Optimize it for:

> **matching the trade family to the behavior the market is currently rewarding.**

In a bull regime, that may mean pressing continuation.

In chop, that may mean buying better locations and selling strength.

In panic, that may mean a short-duration reversal.

In a persistent bear trend, the highest-quality signal may simply be:

```text
NO POSITION
```

That is not a missing feature.

It is a valid regime output.

---

# Appendix A — Provenance Map

## Manual-derived concepts

### Chhirag Kedia
- situational awareness
- regime strategy priority
- bull pullback vs bear phase distinctions
- bottom bounce
- undercut-and-rally
- failure reversal
- EP
- linear pullback
- weak-structure short
- sell-strength vs sell-weakness
- independent stock cycle

### Manas Arora
- falling knives / bottom bounce
- prior-strength reversal selection
- Busted
- Strong Start
- squat
- second attempts
- market feedback through positions

### Sakatas Homma / Prakash
- breadth risk dial
- oversold breadth
- shakeout
- AVWAP
- support confluence
- pullback confirmation
- sell-on-strength in chop
- progressive exposure
- squat management

### Umang / StocksGeeks
- MBI
- 4.5R
- oversold sequence
- prior-low undercut
- fakeout / shakeout / reset
- IPO / EP in weak markets
- high-RS recovery stocks
- VWAP respect
- Spot Burst
- time-of-day intraday framework

---

# Appendix B — External Research References

## Chui, Ranganathan, Rohit & Veeraraghavan (2023)
**Momentum, reversals and liquidity: Indian evidence.**  
Pacific-Basin Finance Journal, Volume 82.

Used for:

- coexistence of momentum and short-term reversal in Indian equities;
- liquidity-conditioned momentum;
- stronger reversal evidence in illiquid stocks;
- warning against naive loser mean-reversion.

## Sahi (2026 working paper)
**Regime-Dependent Price Formation in Indian Equities: Evidence from Factor Information Coefficients and Portfolio Microstructure.**

Used only as:

- preliminary support for testing regime-dependent momentum vs reversal;
- not a production rule.

## Krishnan & Mishra (2013)
**Intraday liquidity patterns in Indian stock market.**  
Journal of Asian Economics.

Used for:

- NSE intraday U-shaped liquidity/volume behavior;
- rationale for treating opening, midday and close separately.

## NSE / SEBI current surveillance framework

Used for:

- ASM / GSM / Trade-for-Trade gates;
- price-band/circuit considerations;
- periodic call-auction / surveillance constraints.

## SEBI short-selling framework / NSE SLB

Used for:

- separating default cash-long system from optional short research;
- recognizing delivery / borrow constraints for multi-day shorts.

---

# Appendix C — Research Questions to Freeze Before Build

1. Does `CHOP_BALANCED` actually improve mean-reversion expectancy versus a generic sideways definition?
2. Does high RS improve Range-Low Reclaim outcomes?
3. Does AVWAP confluence add anything after controlling for range support?
4. Is the first VWAP/AVWAP bounce materially better than later bounces?
5. Does 4.5R add predictive value to intraday Spot Burst after liquidity and sector controls?
6. Does a failed breakout reset outperform first-breakout entries in chop?
7. Do former leaders outperform random losers in bottom-bounce setups?
8. Does Umang's "more extreme oversold on later bear legs" survive point-in-time testing?
9. Does sell-on-strength materially improve capture ratio in chop?
10. At what liquidity threshold do reversal edges disappear after realistic slippage?
11. Does `cash` outperform bear-long strategy families after stress costs?
12. Does `BEAR_LATE_BASEBUILD` identify future bull leaders early enough to matter without excessive false starts?

---

# Appendix D — Freeze-Ready v1 Decisions

The following can be frozen immediately:

```text
1. Add CHOP and BEAR setup routers.
2. Keep ordinary breakout logic regime-specific.
3. Mean reversion = quality/structure reversion, not generic loser buying.
4. Make CASH a valid BEAR output.
5. EP / IPO remain regime exceptions, not regime-independent guarantees.
6. Oversold alone is never a trigger.
7. Tradeability gate runs before reversal ranking.
8. Intraday setup eligibility includes time-of-day and real-time breadth.
9. Risk and exit policy change with regime.
10. Short setups remain isolated from the cash-long default engine.
11. LLM explains regime/setup fit; deterministic code owns regime, levels and risk.
12. Every new setup must pass point-in-time, OOS, cost and stress validation.
```
