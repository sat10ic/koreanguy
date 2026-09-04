<!-- Adopted 2026-08-29 as the AI RESEARCH CONSTITUTION (unidesk DECISIONS D14).
     Extends D11's north-star role: L0→L5 hierarchy, L1.5 engineered-state
     analogue retrieval as a mandatory control before any neural encoder,
     three-dimensional promotion (quality × coverage × stability),
     decision-time contracts, ±60-session same-symbol embargo, Temporal-CNN
     architecture freeze for EP L2 v1. Predictive AI remains forbidden until
     Phase 0 (plan/PHASE0_DATA_BUILD_SPEC.md) passes. The swing-edges spec
     remains the deterministic champion (D11). Canonical copy lives here;
     the Downloads original is the owner's source, not the build input.
     As-built tool map: plan/UNIFIED_DESK_BUILD_MANUAL_V2.md. Embargo +
     leakage primitives exist; L1.5/L2 must not be started. -->

# v1.0 Research Constitution Addendum — AI-Native Indian Equity Swing & Momentum Research

## Executive Summary

This revision incorporates the latest feedback and tightens the architecture around five things that must be frozen before model training:

1. **Representation objective**
2. **Decision-time contracts**
3. **Embargo and leakage rules**
4. **Experiment budget**
5. **Delivery-aware state vectors**

It also adds a mandatory intermediate control:

> **L1.5 — engineered-state analogue retrieval**

This separates the value of **historical retrieval** from the value of **learned representation learning**.

The governing principle remains:

> **The deterministic technical specification is the scientific control. The AI architecture is the challenger.**

The target is not to prove that AI can describe charts. It is to prove that a learned representation of Indian price-action states adds measurable, stable, tradable information beyond deterministic technical features.

---

# 1. Core Research Principle

The final hierarchy is:

```text
L0
Raw technical rule

 ↓

L1
Engineered score

 ↓

L1.5
Engineered-state analogue retrieval

 ↓

L2
Supervised learned representation

 ↓

L3
Learned-space analogue retrieval

 ↓

L4
Empirical outcome distribution

 ↓

L5
Deterministic trade execution
```

This structure isolates three separate questions:

### Question A
Do simple deterministic rules work?

### Question B
Does historical retrieval add anything when using only engineered technical features?

### Question C
Does a learned sequence representation add incremental information beyond those engineered features?

Only if the answer to Question C is yes does the AI layer deserve promotion.

---

# 2. Representation Objective — Freeze for EP v1

“Learned sequence representation” is too vague to train responsibly.

For EP v1, use a **supervised multi-task sequence model**.

Targets:

```text
cont_10d       binary
fail_3d        binary
mfe_10d        continuous
mae_10d        continuous
```

The shared encoder learns one latent representation.

Conceptually:

```text
                     EP STATE
                        │
                        ▼
                  SHARED ENCODER
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
   P(cont_10d)      P(fail_3d)       MFE / MAE
```

## Important Constraint

Analogue retrieval should use the **penultimate latent representation**, not merely the model's predicted outputs.

Otherwise two setups could be labelled “similar” simply because the model predicts similar returns for both, which makes the analogue layer circular.

Therefore:

> **Train representation using outcomes. Retrieve using latent state. Display historical outcomes of retrieved neighbours.**

Contrastive learning and autoencoders are deferred to later versions.

---

# 3. Champion–Challenger Structure

| Object | Champion — Deterministic | Challenger — AI |
|---|---|---|
| Bull base | `S_tight` | AI ignition |
| EP | `S_ep` + flag rules | AI EP quality |
| IPO | Listing AVWAP + base rules | AI maturity |
| Bear leadership | RS rank | AI stress resilience |
| Chop | range/failure rules | AI failure classifier |
| Information | F1 filing drift | F2 AIRG |
| F2 graph | verified links | AI-inferred link expansion |

The AI model is promoted only if it produces a material, statistically persistent improvement over its deterministic champion.

---

# 4. Promotion Must Be Three-Dimensional

A simple expectancy lift is not enough.

Promotion should be assessed across:

```text
QUALITY
net expectancy / MAE / drawdown

      ×

COVERAGE
how many champion trades survive

      ×

STABILITY
folds / years / bootstrap
```

This prevents misleading cases such as:

```text
+40% expectancy lift
but
only 6% of T5 trades retained
```

That may still be useful, but it should be classified correctly.

## Three Possible Outcomes

### Ranker
Improves the full candidate distribution.

### Sniper Filter
Exceptional top-tail performance but low coverage.

### No Edge
Cannot produce either reliably.

This classification should be part of the evaluation.

---

# 5. Decision-Time Contracts

These must be explicit and enforced in code.

| Model | Earliest Money Decision | Features Allowed |
|---|---|---|
| T5 Day-1 AI | EP day 15:30 | History + completed EP-day bars |
| T5 Path-B AI | Day +2 15:30 initially | Pre-EP + event + Day +1/+2 |
| A1 Bull ignition | 15:30 before breakout | No future pivot break |
| A4 IPO maturity | Current session 15:30 | Listing → current completed session |
| T6 Stress Leadership | Last stress-regime day before R0 flip | No post-flip bars |
| A3 Chop failure | Break-day 15:30 | No Day +1 onward |
| F1 | Defined filing/tape timestamp | Only public information available then |
| F2 | Defined event/relationship timestamp | Only graph edges known then |

Every generated feature row should satisfy:

```python
assert feature_timestamp <= decision_timestamp
```

This should be a hard validation rule, not merely documentation.

---

# 6. Embargo and Leakage Rules

## 6.1 Same-Symbol Embargo

For any query state:

```text
Query date ±60 trading sessions
→ forbidden analogue
```

This reduces contamination from overlapping windows and nearby setup repetitions in the same name.

## 6.2 Same Event

Multiple states from the same EP episode cannot appear across training and validation as independent samples.

## 6.3 Same Sector + Week Concentration

Neighbour sets should not be dominated by one thematic mania.

Suggested v1 rule:

```text
Maximum 20% of neighbours
from the same industry + calendar week
```

Do not optimize this percentage on the final holdout.

## 6.4 Point-in-Time Normalization

All:

- z-scores
- percentiles
- volatility ranks
- universe ranks
- sector ranks

must be computed strictly using information available at time `t`.

No full-sample normalization.

---

# 7. Mandatory Phase 2.5 — L1.5 Similarity

Before training any neural representation, test historical retrieval using only engineered features.

## Engineered EP Vector

Example:

```text
gap_pct
rvol_20
close_loc
prior_atr_percentile
S_ep
RS
delivery_z
extension
liquidity
market_regime
```

Then:

```text
engineered vector
      ↓
distance metric
      ↓
nearest historical EPs
      ↓
outcome distribution
```

This creates three competitors:

```text
T5 SCORE
   │
   ▼
Baseline


T5 + L1.5 ANALOGUES
   │
   ▼
Do hand-crafted features + retrieval help?


T5 + L2 LEARNED STATE
   │
   ▼
Does learned representation add more?
```

Example interpretation:

```text
T5                  1.00×
L1.5 analogue       1.18×
L2 encoder          1.19×
```

Most of the gain came from retrieval, not representation learning.

Versus:

```text
T5                  1.00×
L1.5 analogue       1.03×
L2 encoder          1.28×
```

Now the learned representation is adding genuine incremental information.

---

# 8. Intraday Data — Separate Phase 3A and 3B

Intraday event-path data may be valuable, but it should not block the project.

## Phase 3A — Daily-Only L2

Use:

```text
20–40d pre-state
EP daily bar
Day +1 / +2 state
```

Question:

> Can L2 beat T5 using clean daily data alone?

## Phase 3B — Add Intraday Event Geometry

Only after Phase 3A shows promise.

Use clean 5-minute or 15-minute bars on the subset where data quality is sufficient.

Possible intraday features:

```text
opening drive
open-to-low excursion
VWAP behaviour
AVWAP behaviour
intraday MFE / MAE
volume timing
retracement structure
closing structure
```

Important:

> Compare Phase 3A vs 3B on the **same subset of names/events**.

Otherwise the model may appear better simply because only larger/liquid names have complete intraday history.

---

# 9. Delivery Must Be in the State Vector

For India, delivery data should not sit merely in Layer 1 plumbing.

Where available by decision time, include:

```text
delivery_qty
delivery_pct
delivery_qty_z20
delivery_pct_z20
delivery / traded-volume trend
EP delivery shock
post-EP delivery retention
```

For bull bases:

```text
delivery during contractions
delivery on accumulation bars
delivery on breakout attempts
```

If official delivery data arrives only after the relevant trading decision, it cannot be used for that decision.

The data lag itself must be represented in the feature contract.

---

# 10. Freeze the AI Architecture Budget

Section-level language such as “limit architecture experiments” is insufficient.

For EP L2 v1, freeze:

## Encoder Family

**Temporal CNN**

Rationale:

- smaller sample
- fewer degrees of freedom
- easier to train
- good at local temporal geometry
- lower risk of architecture-search overfitting

Transformers become a later challenger.

## Sequence Lengths

Only:

```text
20 sessions
40 sessions
```

## Neighbour Counts

Only:

```text
k = 25
k = 50
```

## Distance Metric

Only:

```text
cosine
```

## Normalization

One frozen procedure.

No expansion to extra architectures, sequence lengths, or distance functions until a new research version is declared.

---

# 11. EP v1 Research Flow

```text
                    HISTORICAL EPs
                         │
                         ▼
                 T5 eligibility rules
                         │
                         ▼
                ┌────────┴─────────┐
                ▼                  ▼
           S_ep ranking      L1.5 neighbours
                │                  │
                └────────┬─────────┘
                         │
                  CONTROL RESULTS
                         │
                         ▼
                Temporal-CNN L2
                         │
                         ▼
                multitask outcomes
                         │
                         ▼
                  latent state
                         │
                         ▼
                  L3 analogues
                         │
                         ▼
              OUT-OF-SAMPLE TEST
                         │
               ┌─────────┴─────────┐
               ▼                   ▼
          material lift          no lift
               │                   │
           PROMOTE AI          DELETE L2
```

---

# 12. EP State Decomposition

## 12.1 Pre-EP State

20–40 daily bars.

```text
compression
RS trajectory
trend
extension
volume behaviour
distance from highs
volatility path
pullback geometry
delivery trend
```

## 12.2 Event State

Daily first. Intraday later.

```text
gap
RVOL
close location
range shock
delivery shock
EP-day VWAP / AVWAP relation
opening drive
retracement depth
```

## 12.3 Post-EP State

Day +1 through Day +5.

```text
gap retention
AVWAP hold
range contraction
volume decay
delivery retention
flag quality
RS persistence
failed breakdowns
selling-volume behaviour
```

This decomposition lets us test where the incremental signal actually lives.

---

# 13. IPO Model — Two Clocks

IPO maturity should not be based only on calendar days.

Use:

```text
CALENDAR CLOCK
Days since listing

       +

MARKET CLOCK
Freely traded sessions
excluding locked circuits / abnormal auctions
```

Example:

```text
IPO A
Day 20
20 normal sessions

IPO B
Day 20
8 freely traded sessions
12 circuit-dominated sessions
```

These are different lifecycle states.

## IPO State Coordinates

```text
calendar_age
free_trade_age
cumulative_turnover / free_float
volatility_decay
volume_decay
distance_from_listing_AVWAP
distance_from_IPO_high
pullback_depth_decay
tightness
RS_since_listing
lock-in_proximity
```

The deterministic T4 rules remain the champion.

The AI model must beat:

> Listing AVWAP + base rules + volume contraction + breakout

on an age-normalized holdout test.

---

# 14. Bear Model — T2 and T6 Stay Separate

## T2

Question:

> What can I trade now in a bear regime?

This remains the tactical sleeve.

## T6 — Stress Leadership

Question:

> Which stocks become leaders after the market heals?

Target label:

> **Top-quartile leader during the first 20–60 sessions after regime improvement.**

Possible features:

```text
market down-day capture
recovery speed
RS persistence
sector-relative resilience
volume on recovery
failed-break frequency
tightness during stress
upside/downside beta
delivery behaviour
```

Baseline:

> Plain RS rank vs Nifty

If T6 cannot beat that, do not promote the AI model.

---

# 15. T6 Sample-Size Gate

Before modelling T6, count independent bear-to-heal transitions.

Freeze an interpretation rule such as:

```text
<20 independent transitions
→ descriptive study only

20–40
→ simple pooled model / strong regularization

>40
→ candidate for formal challenger research
```

The exact thresholds can be adjusted before research starts, but the principle must be fixed.

Thousands of stocks inside one market correction are not thousands of independent regime events.

---

# 16. Chop Model — Leakage Boundary

This remains the highest-risk model for accidental leakage.

Prediction timestamp:

```text
15:30 TODAY

Everything known:
████████████████████████│

Future:
                         │████████████
                         ↑
                     forbidden
```

Question:

> At today's close, how likely is this boundary break to fail?

No t+1, t+2, or t+3 features may enter the prediction.

Build deterministic range / second-touch rules first.

Only then allow the AI classifier to compete.

---

# 17. F1 and F2 Must Remain Separate

## F1 — Same-Company Filing Drift

```text
Company A files
       ↓
AI interprets materiality
       ↓
Tape confirms
       ↓
Trade A
```

## F2 — Read-Through / Reaction Gap

```text
                    EVENT AT A
                        │
              ┌─────────┴───────────┐
              ▼                     ▼
             F1                    F2
        Does A drift?         Who else cares?
                                   │
                          ┌────────┼─────────┐
                          ▼        ▼         ▼
                          B        C         D
                                   │
                                   ▼
                             Reaction gap
```

F2 signal:

```text
economic relationship
        ×
event significance
        ×
reaction gap
        ×
technical state
```

---

# 18. F2 Relationship Whitelist for v1

Only allow high-confidence relationships.

## Tier 1

Explicit named customer / supplier.

## Tier 2

Confirmed historical order relationship.

## Tier 3

Reported segment exposure with a direct economic link.

Do not allow:

```text
"AI believes these companies are thematically connected"
```

in the first test.

Later, even F2 can use champion–challenger:

```text
F2 CHAMPION
verified relationship graph

          VS

F2 CHALLENGER
AI-inferred graph additions
```

---

# 19. Statistical Promotion Rule

“Materially beats” must be defined statistically.

A possible v1 promotion rule:

1. AI lift persists in at least **3 of 5 walk-forward folds**
2. block-bootstrap **90% confidence interval** for expectancy difference excludes zero
3. commercial hurdle also passes:
   - ≥15–20% net expectancy improvement, **or**
   - materially lower MAE / drawdown at similar expectancy

The exact statistical procedure should be frozen before the final holdout.

No promotion based on one good aggregate number.

---

# 20. Coverage Must Be Reported

Every AI result should report:

```text
candidate count
trade count
coverage vs champion
top-decile coverage
sector concentration
year concentration
ADV distribution
```

This distinguishes a broad ranker from a low-frequency sniper filter.

A small but powerful top-tail edge may still be useful, but it should be described honestly.

---

# 21. Analogue Pool Conditioning

Historical neighbours should be filtered or conditioned by relevant market state.

Possible dimensions:

- regime
- liquidity bucket
- market-cap bucket
- setup family
- sector
- listing age
- circuit / free-trading state
- F&O vs cash-only
- event type

Otherwise the engine may match superficially similar but structurally different events.

---

# 22. Trader-Facing Output

The product should not expose:

```text
cosine similarity
latent cluster IDs
embedding norms
```

It should show:

```text
RECLTD                                      EP CONTINUATION

SETUP QUALITY                                      92

Historical matches                                186
Strong matches                                     43

Continuation within 10D                            71%
Typical upside                                     +9.6%
Typical adverse move                               -2.4%

WHY IT RANKS HIGH

✓ EP gap held
✓ Strong close
✓ AVWAP defended
✓ Day-2 range contracted
✓ Selling volume disappeared
✓ Delivery remained elevated
✓ Sector remains strong

──────────────────────────────────────────────────────

ENTRY

First-flag high                              ₹xxx.xx

RISK LINE

EP AVWAP / structural low                   ₹xxx.xx
```

And ideally a few historical analogues:

```text
CURRENT                  ANALOGUE #1
   /\                        /\
__/  \___                ___/  \__

ANALOGUE #2              ANALOGUE #3
    /\                       /\
___/  \__                ___/ \___
```

Analogues are a decision-support interface, not proof by themselves.

---

# 23. Final System Architecture

## Layer 1 — Market Truth

```text
NSE data
corporate actions
delivery
circuits
auctions
index membership
IPO lifecycle
sector data
liquidity
```

No AI.

## Layer 2 — Deterministic Champions

```text
R0   Regime
T1   Bull tightness
T2   Bear tactical
T3   Chop/range
T4   IPO base
T5   EP
F1   Filing drift
```

## Layer 3 — AI Challengers

```text
A1   Bull ignition
A2   Stress leadership
A3   Breakout failure probability
A4   IPO maturity
A5   EP quality
F2   AIRG
```

## Layer 4 — Historical State Engine

```text
CURRENT STATE
      │
      ▼
engineered or learned representation
      │
      ▼
historical state library
      │
      ▼
conditioned neighbours
      │
      ▼
empirical outcome distribution
```

## Layer 5 — Deterministic Execution

```text
entry
stop
size
portfolio risk
liquidity
circuits
sector exposure
exit
```

---

# 24. Final Research Constitution

The final mental model is:

```text
                       MARKET DATA
                           │
                           ▼
                 DETERMINISTIC FILTER
                           │
                    "Is it valid?"
                           │
                           ▼
                    AI PERCEPTION
                           │
                  "How good is it?"
                           │
                           ▼
                HISTORICAL ANALOGUES
                           │
                "What happened before?"
                           │
                           ▼
                 OUTCOME DISTRIBUTION
                           │
                           ▼
                DETERMINISTIC EXECUTION
                           │
                  "How do we trade it?"
```

The project succeeds under either outcome:

### Outcome A — AI Wins

A learned representation produces stable, monotonic, economically meaningful incremental lift over deterministic controls.

That is evidence of a genuine AI-enabled technical edge.

### Outcome B — AI Loses

L0/L1 or L1.5 performs just as well.

Then the learned layer is deleted and the simpler system is retained.

That is also a successful research outcome.

---

# 25. Repo README Principle

> **Deterministic scores are the champion. Learned representations are guilty until proven useful. Analogues are a user interface on a space that has already been shown to rank outcomes. Execution never listens to a vibe.**

