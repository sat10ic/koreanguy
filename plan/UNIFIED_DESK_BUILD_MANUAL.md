<!-- SUPERSEDED 2026-08-29 (unidesk DECISIONS D13): this document is retained as
     historical reference for the controlling integration manual of the LIVE-FIRST architecture. The controlling
     documents are now UNIFIED_DESK_BUILD_MANUAL_V2.md / UNIFIED_DESK_UI_UX_MANUAL_V2.md
     (EOD-first product). Unchanged details referenced by V2 remain valid; live-module
     sections apply only if the optional live module is activated. -->

<!-- In-repo adoption note (2026-08-28) — added when this manual was copied into the repo.
Original: user-supplied, dated 2026-08-28. Adopted as the controlling integration
manual for the unified build per unidesk/DECISIONS.md D1.
Repo mapping: the layout's `desk/` package is implemented as `unidesk/` (D2).
`plan/ORDERFLOW_BUILD_MANUAL.md` remains the child implementation reference for
Phase 3 internals, as this manual's Phase 3 preamble itself states. -->

# Unified Momentum Trading Desk — Step-by-Step Build Manual

**Status:** SUPERSEDED 2026-08-29 (D13). Historical reference for the live-first architecture. Controlling spec is `plan/UNIFIED_DESK_BUILD_MANUAL_V2.md` (EOD-first, as-built D14–D17).  
**Created:** 2026-08-28  
**Primary market:** Indian equities, NSE cash market first  
**Primary trading style:** swing / momentum / momentum-burst trading in midcap and smallcap equities  
**Execution model:** human-in-the-loop; no order routing  
**Primary live market source:** FYERS  
**Primary research store:** Parquet + DuckDB  
**Primary application pattern:** deterministic measurement → rules/models → advisory synthesis → human decision  

This manual consolidates and updates the useful parts of the following source documents:

- `Technical Specification_ India Momentum Context Engine.md`
- `fyers_momentum_orderflow_technical_spec(1).md`
- `orderflow_spec_audit_feedback_review(1).md`
- `ORDERFLOW_BUILD_MANUAL.md`
- `TRADERLOG_V2_BUILD_MANUAL.md`
- `Trading_Analysis_Agentic_AI_Setup_Detection_v2(1).pdf`
- `momentum_swing_screenshot_assessments(1).md`
- `high_fidelity_llm_rnd_workflow(1).md`

It intentionally does **not** preserve every feature or ceremony in those documents. The objective is a smaller, falsifiable trading desk in which each layer has one job.

---

# 0. What is being built

The system is a decision-support stack for Indian momentum trading.

It must answer, in order:

```text
1. Is this stock worth attention?
2. Is there a valid momentum setup?
3. Is the setup attractive at the current price?
4. Is the stock actually tradable and exit-capable?
5. Is live near-price behaviour confirming or warning?
6. Is there useful external/social context?
7. Are any hard risks or unknowns present?
8. What facts should the human see before deciding?
```

The architecture is:

```text
╔══════════════════════════════════════════════════════════════════╗
║                     UNIFIED TRADING DESK                         ║
╚══════════════════════════════════════════════════════════════════╝

                         DATA FOUNDATION
                               │
                 OHLCV / NSE / FYERS / events
                               │
                               ▼
                ┌──────────────────────────┐
                │ MOMENTUM CONTEXT ENGINE  │
                │                          │
                │ Trend / EMA              │
                │ RS / sector / peers      │
                │ Theme / breadth          │
                │ ADR / ATR                │
                │ RVOL / delivery          │
                │ AVWAP / participant cost │
                │ circuit / surveillance   │
                └────────────┬─────────────┘
                             │
                             ▼
                 ┌────────────────────────┐
                 │     SETUP DETECTOR     │
                 │                        │
                 │ deterministic geometry │
                 │ GBT classifier later   │
                 │ similarity later       │
                 └───────────┬────────────┘
                             │
                       SETUP QUALITY
                             │
                             ▼
                 ┌────────────────────────┐
                 │     TRADE GEOMETRY     │
                 │                        │
                 │ trigger                │
                 │ extension              │
                 │ overhead supply        │
                 │ breakout room          │
                 │ invalidation           │
                 │ initial R:R            │
                 └───────────┬────────────┘
                             │
                       ENTRY QUALITY
                             │
               ┌─────────────┴─────────────┐
               ▼                           ▼
      ┌──────────────────┐        ┌──────────────────┐
      │  TRADERLOG LITE  │        │    ORDER FLOW    │
      │                  │        │                  │
      │ posts / claims   │        │ liquidity        │
      │ themes           │        │ spread           │
      │ trader actions   │        │ persistence      │
      │ evidence         │        │ price response   │
      └────────┬─────────┘        │ failure detect   │
               │                  └────────┬─────────┘
               │                           │
          SOCIAL CONTEXT             CONFIRM/WARN/VETO
               │                           │
               └──────────────┬────────────┘
                              ▼
                    ┌────────────────────┐
                    │   CONTEXT JUDGE    │
                    │   advisory LLM     │
                    └─────────┬──────────┘
                              │
                              ▼
                    ┌────────────────────┐
                    │   DECISION CARD    │
                    │                    │
                    │ Stock quality      │
                    │ Setup quality      │
                    │ Entry quality      │
                    │ Liquidity state    │
                    │ Flow state         │
                    │ Social context     │
                    │ Risks / unknowns   │
                    └─────────┬──────────┘
                              │
                         HUMAN DECIDES
                              │
                              ▼
                    DISCIPLINE / JOURNAL
                         later phase
```

The system is **not**:

- an HFT engine,
- a queue-position model,
- a broker/dealer identity tool,
- an institutional-flow detector,
- an autonomous trader,
- an order router,
- a replacement for human trade authorization,
- an LLM that “looks at a chart and decides.”

---

# 1. Authority order and source lineage

## 1.1 Authority

When implementation documents disagree, use this order:

1. Directly measured market/provider behaviour.
2. Point-in-time stored data and reproducible test output.
3. This manual's non-negotiable invariants.
4. Module-specific canonical contracts.
5. Existing module build manuals where they do not conflict with this manual.
6. Old concept notes and historical designs.

Never resolve a contradiction silently.

Record it in:

```text
desk/DECISIONS.md
```

with:

```text
date
decision_id
documents_in_conflict[]
evidence
chosen_rule
reason
affected_modules[]
```

## 1.2 Source-derived design decisions retained

The following are retained directly from the supplied material:

- stock quality, setup quality and entry quality are separate concepts;
- AVWAP is participant-cost context, not a stand-alone signal;
- RS must include market, sector and peer comparisons;
- RVOL and delivery measure participation;
- ADR/ATR measure volatility and extension context;
- setup detection starts with deterministic geometry;
- trained GBT/LightGBM models are optional second-stage scorers, not the first authority;
- DTW/matrix-profile similarity is optional evidence, not a signal by itself;
- LLMs synthesize already-computed information and must not invent trading numbers;
- order flow is principally a confirmation/warning/veto layer;
- feed capability must be measured before short-window flow features are trusted;
- depth must be recorded before research depends on it;
- missing/stale inputs become `UNKNOWN`, not fabricated values;
- TraderLog claims must remain evidence-backed, reviewable and provenance-aware;
- only accepted social claims may materialize trader lifecycles;
- every useful layer must prove incremental value and may be deleted if it does not.

## 1.3 New integration decisions introduced by this manual

These are integration choices for the unified system rather than claims copied from one source:

- one shared `CandidateContext` contract between momentum, geometry and flow;
- one shared `DecisionSnapshot` for the UI and research ledger;
- TraderLog becomes **TraderLog Lite**, preserving claims/evidence while removing most of the heavier V2 analytics/UI scope;
- social context is advisory and cannot override hard market/liquidity/flow vetoes;
- a dedicated Trade Geometry layer sits between Setup Quality and Entry Quality;
- a common Research Ledger stores the exact state seen at each decision timestamp;
- the advisory LLM is a separate Context Judge, never the owner of numeric calculations;
- Discipline/Journal analysis is a later optional phase.

---

# 2. Non-negotiable system rules

## R1 — Point-in-time truth

Every historical feature must be computable using only information available at that timestamp.

Forbidden:

```text
future candles
future corporate-action knowledge not yet available
future sector membership
future social replies
future earnings outcomes
post-hoc setup labels used as live features
```

A leakage test is required for every feature family.

---

## R2 — Code owns numbers

The LLM must never originate:

```text
price
trigger
stop
R:R
RS
RVOL
ADR
ATR
AVWAP
breadth
delivery ratio
position capacity
flow score
spread
depth imbalance
MFE
MAE
```

These are computed by deterministic code or an explicitly trained numeric model.

The LLM may explain or compare already-computed values.

---

## R3 — Human owns the trade

No package may place an order.

No Context Judge response may be treated as order authorization.

The terminal may display:

```text
ELIGIBLE
WAIT
WARN
VETO
UNKNOWN
```

but the human decides whether to trade.

---

## R4 — Keep three quality layers separate

Never collapse these into one opaque score:

```text
STOCK QUALITY
SETUP QUALITY
ENTRY QUALITY
```

Example:

```text
Stock quality  96
Setup quality  92
Entry quality  43

Result:
excellent stock
excellent setup
poor current entry
```

---

## R5 — Market context does not create geometry

Strong RS, theme or earnings cannot manufacture a setup that does not exist.

The Setup Detector must first find valid geometry.

---

## R6 — Social context cannot rescue a bad market setup

Trader attention may add context.

It cannot override:

```text
invalid setup
liquidity REJECT
circuit risk hard gate
flow VETO
stale market data
missing trigger
unacceptable entry geometry
```

---

## R7 — Order flow is a confirmation/risk layer

Order flow does not select the strongest stock.

It answers:

```text
Is this already-valid entry healthy,
neutral,
deteriorating,
or unsafe?
```

It gets small numeric influence and strong veto authority.

---

## R8 — Measure the FYERS feed before trusting microstructure

No 5-second/15-second feature is production-active before actual update behaviour is measured.

Capability is written from observation, not assumed from documentation.

---

## R9 — Record depth before research

Historical depth cannot be reconstructed reliably later.

The recorder ships before the flow feature stack.

---

## R10 — Never show stale flow as live

If depth exceeds the stale threshold:

```text
order_flow_enabled = false
flow_state = UNKNOWN
```

The last bullish/bearish state must not remain on screen as if current.

---

## R11 — Do not claim what the feed cannot prove

Forbidden factual labels include:

```text
institutional buying
FII buying
HNI buying
spoofing
iceberg size
hidden liquidity
broker identity
queue position
true aggressor side
```

Use probabilistic labels where justified:

```text
buyer_aggression_estimate
seller_absorption_likelihood
manipulation_like_behaviour
sweep_like_event
```

---

## R12 — Missing values are not zero

Use:

```text
value = null
reason = <named reason>
```

Examples:

```text
NO_DELIVERY_DATA
NO_SECTOR_INDEX
DEPTH_STALE
TBT_NOT_PROVISIONED
INSUFFICIENT_SAMPLES
UNRESOLVED_SOCIAL_CLAIM
```

---

## R13 — Evidence remains attached

For social data:

```text
claim
  -> source post
  -> source media if applicable
  -> exact quoted/displayed evidence
```

Vision output is evidence extraction, not truth.

---

## R14 — Configuration, not code

No major threshold belongs inline in feature code.

All thresholds live in versioned configuration.

Every decision snapshot stores the configuration hash.

---

## R15 — Every feature is independently disableable

Feature flags are required for ablation.

A layer that cannot be disabled cannot be scientifically tested.

---

## R16 — Every decision is reproducible

A stored decision must reference:

```text
market_data_version
candidate_version
feature_version
setup_rule_version
geometry_version
flow_config_version
social_pipeline_version
judge_prompt_version
decision_policy_version
```

---

## R17 — Replay must match live logic

Research must call the same feature and policy functions as production.

No separate notebook-only “research interpretation” of a live signal.

---

## R18 — Negative results are product results

If a feature/layer fails to improve out-of-sample outcomes:

```text
record finding
disable feature
do not quietly retain it
```

---

## R19 — Sample-size honesty

Do not publish setup-specific rates or model claims from tiny cells.

Always show:

```text
n
coverage
missing rate
confidence interval or uncertainty label where applicable
```

---

## R20 — No silent cross-module mutation

Each persistent table has exactly one writer.

Integration occurs via contracts/events/API, not arbitrary direct writes across packages.

---

# 3. Target repository layout

Recommended logical structure:

```text
/
├── DESK.md
├── desk/
│   ├── CANONICAL.md
│   ├── DECISIONS.md
│   ├── STATE.json
│   ├── config.example.yaml
│   ├── contracts/
│   │   ├── market.py
│   │   ├── candidate.py
│   │   ├── setup.py
│   │   ├── geometry.py
│   │   ├── flow.py
│   │   ├── social.py
│   │   ├── decision.py
│   │   └── research.py
│   ├── integration/
│   │   ├── event_bus.py
│   │   ├── snapshot_builder.py
│   │   └── versioning.py
│   ├── api/
│   │   ├── app.py
│   │   ├── routes_candidates.py
│   │   ├── routes_symbol.py
│   │   ├── routes_decisions.py
│   │   └── routes_research.py
│   └── checks/
│       ├── leakage.py
│       ├── stale_state.py
│       ├── provenance.py
│       └── __main__.py
│
├── momentum/
│   ├── market/
│   │   ├── regime.py
│   │   ├── breadth.py
│   │   └── sectors.py
│   ├── features/
│   │   ├── trend.py
│   │   ├── rs.py
│   │   ├── rvol.py
│   │   ├── delivery.py
│   │   ├── adr_atr.py
│   │   ├── avwap.py
│   │   ├── extension.py
│   │   ├── volume_contraction.py
│   │   └── liquidity_baseline.py
│   ├── universe/
│   │   ├── symbol_master.py
│   │   ├── builder.py
│   │   └── surveillance.py
│   └── scoring/
│       └── stock_quality.py
│
├── setups/
│   ├── primitives/
│   │   ├── pivots.py
│   │   ├── swings.py
│   │   ├── contraction.py
│   │   ├── trendlines.py
│   │   └── volume_dryup.py
│   ├── detectors/
│   │   ├── momentum_burst.py
│   │   ├── episodic_pivot.py
│   │   ├── ipo_base.py
│   │   ├── inside_bar.py
│   │   ├── base_breakout.py
│   │   ├── pullback.py
│   │   ├── reversal_reclaim.py
│   │   └── power_play.py
│   ├── models/
│   │   ├── gbt.py
│   │   └── similarity.py
│   └── scoring/
│       └── setup_quality.py
│
├── geometry/
│   ├── trigger.py
│   ├── invalidation.py
│   ├── extension.py
│   ├── overhead_supply.py
│   ├── breakout_room.py
│   ├── rr.py
│   ├── correction_type.py
│   └── entry_quality.py
│
├── orderflow/
│   ├── CANONICAL.md
│   ├── capability.json
│   ├── market_data/
│   ├── storage/
│   ├── universe/
│   ├── features/
│   ├── scoring/
│   ├── replay/
│   ├── alerts/
│   └── tests/
│
├── traderlog/
│   ├── archive/
│   ├── claims/
│   ├── lifecycle/
│   ├── social_context/
│   ├── adapters/
│   ├── api/
│   └── tests/
│
├── judge/
│   ├── contract.py
│   ├── prompt.md
│   ├── evaluator.py
│   ├── policy.py
│   └── tests/
│
├── research/
│   ├── event_store.py
│   ├── outcomes.py
│   ├── labels.py
│   ├── ablation.py
│   ├── walkforward.py
│   ├── reports/
│   └── tests/
│
├── journal/                     # later phase
│   ├── events.py
│   ├── process_rules.py
│   └── weekly_review.py
│
└── data/
    ├── market/
    ├── orderflow/
    ├── research/
    └── social/
```

### Boundary rule

`orderflow/` must not import `traderlog/`.

`traderlog/` must not write momentum or order-flow tables.

Shared information passes through `desk/contracts/*`.

---

# 4. Core canonical contracts

All contracts are versioned Pydantic/dataclass-style schemas.

---

## 4.1 SymbolMaster

```python
SymbolMaster:
    symbol
    exchange
    instrument_token
    company_name
    sector
    industry
    market_cap_bucket
    index_membership[]
    theme_tags[]
    surveillance_flags[]
    listing_date
    active
    valid_from
    valid_to
```

Point-in-time fields such as sector/index membership must not silently use today's classification for old history.

---

## 4.2 DailyBar

```python
DailyBar:
    symbol
    session
    open
    high
    low
    close
    volume
    turnover
    delivery_quantity        # nullable
    delivery_percentage      # nullable
    upper_circuit            # nullable
    lower_circuit            # nullable
    data_version
```

---

## 4.3 IntradayBar

```python
IntradayBar:
    symbol
    ts
    timeframe
    open
    high
    low
    close
    volume
    data_version
```

Primary supported decision timeframes:

```text
1m
5m
15m
```

---

## 4.4 MomentumContextSnapshot

```python
MomentumContextSnapshot:
    snapshot_id
    symbol
    as_of

    market_regime
    market_breadth

    ema21
    ema50
    trend_state

    rs_market
    rs_sector
    rs_rank
    peer_rank

    sector_rs
    sector_breadth
    theme_context

    rvol
    delivery_volume_ratio

    adr20
    atr14
    today_move_adr

    avwap_refs[]
    nearest_avwap
    avwap_extension_adr

    distance_52w_high_pct
    distance_ath_pct

    liquidity_baseline_score
    circuit_risk_state
    surveillance_flags[]

    stock_quality_score
    feature_version
    config_hash
```

No field may be substituted with an invented fallback.

---

## 4.5 SetupCandidate

```python
SetupCandidate:
    setup_id
    symbol
    detected_at
    setup_type

    geometry_version

    pivot_price
    trigger_price
    structural_low
    setup_start
    setup_age_sessions

    base_depth_pct
    contraction_ratio
    rest_depth_atr
    volume_dryup_ratio
    gap_pct
    breakout_rvol
    distance_from_pivot_pct

    deterministic_valid
    rule_failures[]
    setup_quality_score

    model_probability         # nullable
    model_version             # nullable

    similarity_score          # nullable
    nearest_gold_case_id      # nullable
```

---

## 4.6 TradeGeometrySnapshot

```python
TradeGeometrySnapshot:
    geometry_id
    setup_id
    as_of

    current_price
    trigger_price
    trigger_distance_pct

    invalidation_price
    stop_distance_pct

    nearest_resistance
    resistance_source
    breakout_room_pct
    breakout_room_adr

    ema21_extension_pct
    avwap_extension_pct
    avwap_extension_adr

    correction_type
        TIME
        PRICE
        MIXED
        UNKNOWN

    initial_rr_to_resistance
    entry_quality_score

    geometry_state
        CLEAN
        ACCEPTABLE
        EXTENDED
        POOR_ROOM
        BAD_RR
        INVALID
        UNKNOWN

    reason_codes[]
    geometry_version
    config_hash
```

Important: old high/resistance is not automatically the final profit target. It is often a confirmation hurdle. The system must distinguish:

```text
resistance_hurdle
vs
projected_momentum_objective
```

The latter is optional context and must never be invented by an LLM.

---

## 4.7 CandidateContext

This is the frozen handoff consumed by OrderFlow and the Context Judge.

```python
CandidateContext:
    candidate_id
    as_of

    symbol
    setup_id
    setup_type

    momentum_snapshot_id
    geometry_snapshot_id

    stock_quality_score
    setup_quality_score
    entry_quality_score

    trigger_price
    invalidation_price

    market_regime
    sector_state
    theme_context

    rs_market
    rs_sector
    rvol
    adr20

    circuit_risk_state
    surveillance_flags[]

    context_version
    config_hash
```

OrderFlow must never rediscover the setup from scratch.

---

## 4.8 OrderFlowAssessment

```python
OrderFlowAssessment:
    assessment_id
    candidate_id
    symbol
    assessed_at
    valid_until

    feed_health
    capability_version

    liquidity_score
    liquidity_state
    capacity_band
    high_impact_band

    raw_flow_score
    flow_confidence
    effective_flow_score

    flow_state
        STRONG_CONFIRMATION
        CONFIRMING
        MIXED
        WEAK
        BREAKOUT_RISK
        UNTRUSTWORTHY_BOOK
        UNKNOWN

    decision
        CONFIRM
        NEUTRAL
        WARN
        VETO
        UNKNOWN

    reason_codes[]
    feature_snapshot_id
    flow_config_hash
```

---

## 4.9 SocialClaim

```python
SocialClaim:
    claim_id
    post_id
    media_idx

    handle
    subject_type
    subject

    claim_type
        entry
        add
        stop_set
        stop_move
        target
        partial_exit
        full_exit
        result_statement
        watch
        theme
        market_view
        lesson

    stated_at
    direction

    price
    price_from
    price_to
    quantity_pct
    result_pct

    text_quote
    confidence

    review_state
        provisional
        accepted
        unresolved
        rejected
        superseded

    source_kind
    source_model
    evidence_json
    unresolved_json
    supersedes_claim_id
```

Rules:

- numbers must exist in source evidence;
- source timestamp, not model timestamp;
- chart-only numeric claims require media evidence;
- unreadable media contributes no numeric claim.

---

## 4.10 SocialContextSnapshot

```python
SocialContextSnapshot:
    snapshot_id
    symbol
    as_of

    accepted_entry_count_5d
    accepted_add_count_5d
    accepted_exit_count_5d

    independent_trader_count
    attention_trend

    theme_mentions[]
    disagreement_present

    recent_claim_ids[]
    recent_evidence_refs[]

    trader_context[]
        handle
        recent_action
        historical_sample_n
        specialization_tags[]

    coverage_state
    unresolved_count
    social_pipeline_version
```

This is context only.

No field here may override a market hard gate.

---

## 4.11 ContextJudgeOutput

The LLM receives only validated structured inputs.

```python
ContextJudgeOutput:
    judge_id
    candidate_id
    created_at

    summary
    confluence_grade
        A
        B
        C
        D
        UNKNOWN

    strongest_supporting_factors[]
    strongest_risks[]
    contradictions[]
    unknowns[]

    social_context_relevance
        MATERIAL
        MINOR
        NONE
        UNKNOWN

    explanation

    prompt_version
    model_name
    model_version
    input_hash
```

Forbidden judge output fields:

```text
new stop
new target
new trigger
new position size
new numeric score
```

---

## 4.12 DecisionSnapshot

The UI reads this, not raw component state.

```python
DecisionSnapshot:
    decision_id
    candidate_id
    as_of

    stock_quality
    setup_quality
    entry_quality

    liquidity_state
    flow_state
    flow_confidence

    social_context_state
    judge_grade

    policy_state
        ELIGIBLE
        WAIT
        WARN
        VETO
        UNKNOWN

    hard_gates[]
    warnings[]
    unknowns[]

    source_snapshot_ids[]
    config_hash
    policy_version
```

`policy_state` is deterministic policy output, not LLM opinion.

---

# 5. Scoring philosophy

The system may expose scores, but scores are explanatory summaries, not truth.

## 5.1 Stock Quality

Inputs may include:

```text
trend
RS market
RS sector
peer rank
sector breadth
RVOL
delivery
ADR
distance from 52W/ATH
AVWAP state
liquidity baseline
circuit/surveillance risk
```

## 5.2 Setup Quality

Inputs depend on setup type.

Examples:

| Setup | Primary inputs |
|---|---|
| Momentum Burst | RS + RVOL + ADR + AVWAP extension + contraction |
| Episodic Pivot | gap + EP AVWAP + RVOL + delivery |
| IPO Base | IPO AVWAP + RS + contraction + ADR |
| Inside Bar | range contraction + volume dry-up + RS |
| Base Breakout | base geometry + breakout AVWAP + RVOL + sector breadth |
| Pullback | AVWAP + declining volume + RS stability |
| Reversal/Reclaim | AVWAP reclaim + volume + RS improvement |
| Power Play | ADR + RVOL + contraction |

## 5.3 Entry Quality

Inputs include:

```text
distance to trigger
extension from EMA21
extension from relevant AVWAP
breakout room
nearby resistance
stop distance
initial R:R
current correction type
session VWAP execution state if intraday
gap/chase risk
```

## 5.4 No global mega-score requirement

The UI should preferentially show:

```text
Stock  92
Setup  88
Entry  54
Flow   WARN
```

rather than:

```text
FINAL SCORE = 76.4
```

A combined research score may exist for experiments, but it must not hide the components.

---

# 6. Configuration

Example only; all thresholds are provisional until validated.

```yaml
system:
  market: NSE_CASH
  order_routing: false

relative_strength:
  benchmark: NIFTY500
  strong_rs: 90
  elite_rs: 95

rvol:
  strong: 1.5
  exceptional: 2.0

adr:
  period: 20
  extended_adr: 2.0
  severely_extended_adr: 3.0

avwap:
  confluence_max_width_pct: 2.5
  confluence_min_levels: 3

geometry:
  min_breakout_room_adr: 1.0
  preferred_breakout_room_adr: 2.0
  trigger_zone_pct: 0.50

sector:
  breadth_period: 20
  strong_score: 70
  elite_score: 85

orderflow:
  stale_ms: null                 # written after capability audit
  windows:
    - 5s
    - 15s
    - 1m
    - 5m

features:
  delivery: true
  volume_profile: false
  gbt_setup_model: false
  similarity_model: false
  social_context: true
  context_judge: false

research:
  require_config_hash: true
  require_point_in_time: true
```

Any threshold activated in production must have:

```text
source
date introduced
reason
validation sample
version
```

---

# 7. Execution protocol for coding agents

This manual keeps the useful discipline of the existing build manuals without reproducing all their ceremony.

For every task:

## Before editing

1. Read `DESK.md`.
2. Read `desk/CANONICAL.md`.
3. Read the task dependency and acceptance criteria.
4. Run focused baseline tests.
5. Confirm persistent tables/files the task may write.
6. State the pass/fail check before implementation.

## During implementation

1. Add or update a failing test first for logic changes.
2. Keep the task narrow.
3. Do not mutate unrelated modules.
4. Do not hard-code production thresholds.
5. Do not create a second implementation of an existing canonical calculation.
6. Do not write production data from a test.

## Before closing

1. Run focused tests.
2. Run full Python tests for the affected package.
3. Run `desk/checks`.
4. Run leakage/provenance checks when relevant.
5. Rebuild UI if changed.
6. Record unresolved items.
7. Stop if an upstream checkpoint is red.

Mandatory stop conditions:

- future data is required to make a live feature work;
- a value cannot be traced to its source;
- a feed field is missing but downstream code assumes it;
- a social numeric claim cannot be evidenced;
- raw depth is being interpolated across a gap;
- a model is being trained on an unverified point-in-time dataset;
- a supposedly deterministic result is not reproducible;
- implementation requires order placement.

---

# PHASE 0 — Freeze contracts, audit data and start recording

**Goal:** establish trustworthy data and module boundaries before building intelligence.

---

## Task P0.1 — Repository and data-authority map

### Description

Create one canonical map of existing packages, stores, feeds and writers.

### Files

```text
DESK.md
desk/CANONICAL.md
desk/DECISIONS.md
desk/STATE.json
```

### Steps

1. Inventory current databases, Parquet roots and APIs.
2. Identify the single writer for each persistent table/file.
3. Mark old TraderLog lifecycle outputs as:
   - accepted,
   - provisional,
   - quarantined,
   - archive-only.
4. Record current OrderFlow status.
5. Record current market-data sources.
6. Define package ownership boundaries.
7. Define which existing code is reused, copied or retired.

### Acceptance

- [ ] Every persistent store has a named owner.
- [ ] No two packages claim canonical ownership of the same field.
- [ ] Quarantined TraderLog lifecycle data cannot be mistaken for accepted truth.
- [ ] OrderFlow has a clear input contract.
- [ ] No production data was modified.

---

## Task P0.2 — Shared contracts

### Dependencies

P0.1.

### Files

```text
desk/contracts/*.py
desk/tests/test_contracts.py
desk/CANONICAL.md
```

### Steps

Implement and validate:

```text
SymbolMaster
DailyBar
IntradayBar
MomentumContextSnapshot
SetupCandidate
TradeGeometrySnapshot
CandidateContext
OrderFlowAssessment
SocialClaim
SocialContextSnapshot
ContextJudgeOutput
DecisionSnapshot
```

### Acceptance

- [ ] Unknown enum values fail validation.
- [ ] Nulls remain null.
- [ ] `as_of` is required for every time-sensitive snapshot.
- [ ] Version/hash fields are mandatory where specified.
- [ ] Same serialized input produces stable schema output.

---

## Task P0.3 — Point-in-time market store

### Dependencies

P0.2.

### Files

```text
momentum/universe/symbol_master.py
momentum/data/*
research/tests/test_point_in_time.py
```

### Steps

1. Store daily OHLCV.
2. Store intraday OHLCV where available.
3. Store delivery data where available.
4. Store circuit bands and surveillance flags where available.
5. Version symbol classification.
6. Add corporate-action/data-adjustment policy to canonical docs.
7. Write a point-in-time fetch function:
   ```python
   get_market_state(symbol, as_of)
   ```
8. Add fixtures proving future rows are not visible.

### Acceptance

- [ ] A 2025 query cannot see a 2026-only classification.
- [ ] No future bar is returned.
- [ ] Missing delivery remains null.
- [ ] Duplicate sessions are rejected or explicitly versioned.

---

## Task P0.4 — FYERS capability audit

### Dependencies

P0.2.

### Files

Use the existing OrderFlow Phase-0 paths.

### Steps

1. Subscribe to at least 8 symbols across liquidity buckets.
2. Record quote and depth messages for a full session.
3. Measure:
   - inter-arrival histogram,
   - median/p95 update interval,
   - quote/depth synchronization,
   - stale periods,
   - burstiness,
   - subscription limits,
   - optional field availability,
   - NSE cash 50-level TBT availability on the actual account.
4. Write `orderflow/capability.json`.
5. Do not infer availability from claims in old specs.

### Acceptance

- [ ] Real measured histogram exists.
- [ ] Per-liquidity-bucket medians exist.
- [ ] Optional fields are marked observed/missing.
- [ ] TBT status has direct evidence.
- [ ] Short-window feature eligibility is computed from capability.

---

## Task P0.5 — Continuous raw depth recorder

### Dependencies

P0.4.

### Steps

Persist:

```text
quotes
depth
feed health
reconnect events
gaps
```

Partition:

```text
date=YYYY-MM-DD/symbol=SYM/
```

Use Parquet plus DuckDB research views.

### Acceptance

- [ ] Forced disconnect reconnects and resubscribes.
- [ ] Gaps remain visible.
- [ ] No stale state is interpolated.
- [ ] One session can be replayed.
- [ ] Credentials never appear in storage/logs.

---

## PHASE 0 CHECKPOINT

Do not continue unless:

- [ ] contracts are canonical;
- [ ] point-in-time market retrieval works;
- [ ] raw depth is recording;
- [ ] feed capability is measured;
- [ ] missing fields remain honest nulls;
- [ ] no module can place orders.

---

# PHASE 1 — Momentum Context Engine

**Goal:** establish the deterministic stock-quality baseline before setup detection and order flow.

---

## Task P1.1 — Daily tradable universe

### Inputs

```text
NSE listed equities
price
turnover
volume
market cap bucket
surveillance flags
circuit history
listing age
```

### Filters

At minimum:

```text
minimum price
minimum median turnover
ETF/fund exclusion
suspended/inactive exclusion
surveillance flags
extreme circuit/exit-risk gate
```

### Output

```text
DailyUniverse
WATCH
EXCLUDE
reason_codes[]
```

### Acceptance

- [ ] Same date/input produces same universe.
- [ ] Exclusions are reason-coded.
- [ ] No manual symbol silently bypasses hard surveillance rules.

---

## Task P1.2 — Trend engine

Calculate:

```text
EMA21
EMA50
optional EMA150/200 context
price vs EMA
EMA slope
52W/ATH distance
```

State examples:

```text
STRONG_UPTREND
UPTREND
TRANSITION
WEAK
```

No trend state creates a buy signal by itself.

### Acceptance

- [ ] All calculations have deterministic fixtures.
- [ ] Corporate-action handling is tested.
- [ ] No look-ahead smoothing.

---

## Task P1.3 — Relative Strength engine

Required:

```text
stock vs NIFTY500
stock vs sector
sector vs NIFTY500
stock vs peers
```

Windows:

```text
5D
20D
60D
120D
250D
```

Outputs:

```text
rs_market
rs_sector
rs_rank
peer_rank
```

### Acceptance

- [ ] Benchmark calendars align correctly.
- [ ] Missing sector benchmark is named, not replaced.
- [ ] Cross-sectional rank uses the point-in-time trade universe.

---

## Task P1.4 — Participation engine

Calculate:

```text
RVOL
volume expansion
volume contraction
delivery percentage
delivery volume
delivery volume ratio
```

Key rule:

```text
DeliveryVolume = Volume × Delivery%
```

Store percentage and volume separately.

### Acceptance

- [ ] Delivery data absence disables dependent features only.
- [ ] Delivery volume is not reconstructed from unavailable fields.
- [ ] RVOL baseline is point-in-time.

---

## Task P1.5 — ADR / ATR / extension engine

Calculate:

```text
ADR20
ATR14
ATR%
today_move_adr
```

Use for:

```text
volatility
extension
stop sanity
contraction
risk context
```

Not as a setup trigger.

### Acceptance

- [ ] Same OHLC window reproduces identical ADR/ATR.
- [ ] Warm-up periods return unavailable, not zero.

---

## Task P1.6 — AVWAP / participant-cost engine

Supported anchors:

```text
EP
BREAKOUT
IPO_LISTING
SWING_LOW
EARNINGS
52W_BREAKOUT
ATH_BREAKOUT
```

For each:

```text
avwap_value
distance_pct
distance_adr
anchor_date
anchor_type
```

Confluence may combine multiple reference levels but must preserve original components.

Session VWAP is separate and primarily execution context.

### Acceptance

- [ ] Anchors are reproducible.
- [ ] Future event knowledge cannot create an old anchor.
- [ ] Multiple active AVWAPs remain separately inspectable.
- [ ] Confluence does not destroy source levels.

---

## Task P1.7 — Sector / peer / theme engine

At minimum calculate:

```text
sector_rs
sector_breadth
peer_rank
peer_breadth
sector_acceleration
```

Theme tags may come from deterministic metadata or a separate evidence-backed source.

Do not turn theme chatter into a numeric predictive score unless separately validated.

### Acceptance

- [ ] Sector membership is point-in-time.
- [ ] Peer group definition is versioned.
- [ ] Theme source is disclosed.

---

## Task P1.8 — Circuit and structural-liquidity risk

Inputs where available:

```text
upper/lower circuit
circuit band
average turnover
historical UC/LC frequency
market cap
surveillance flags
trade-to-trade state
```

Outputs:

```text
circuit_risk_state
exit_risk_state
reason_codes[]
```

### Acceptance

- [ ] Hard risk states can block a candidate.
- [ ] Missing surveillance data is visible.
- [ ] Circuit risk is not inferred from depth alone.

---

## Task P1.9 — Stock Quality snapshot

Combine the above into an explainable stock-quality summary.

Requirements:

```text
score decomposition
reason codes
unknown fields
snapshot IDs
config hash
```

### Acceptance

- [ ] A score can be decomposed.
- [ ] Null inputs do not become zeros.
- [ ] Each feature is individually disableable.

---

## Task P1.10 — Baseline historical test

This is **Model A**.

Example feature set:

```text
market regime
sector/theme context
stock RS
ADR
RVOL
stock quality
basic setup proxy only if available point-in-time
liquidity proxies
```

Store outcomes:

```text
MFE 1D/3D/5D/10D/20D
MAE 1D/3D/5D/10D/20D
1R/2R/3R
stop hit
breakout hold/fail
```

### Acceptance

- [ ] Baseline exists before order-flow claims are made.
- [ ] No flow/social/LLM feature contaminates Model A.
- [ ] Research set and validation set are separated.

---

## PHASE 1 CHECKPOINT

- [ ] daily universe works;
- [ ] trend/RS/RVOL/delivery/ADR/AVWAP are deterministic;
- [ ] sector/peer/circuit context is available;
- [ ] stock-quality snapshot is reproducible;
- [ ] baseline performance is measured.

---

# PHASE 2 — Deterministic Setup Detection and Trade Geometry

**Goal:** identify real candidate structures and distinguish good stocks from good entries.

---

## Task P2.1 — Pivot and swing primitives

Implement:

```text
swing highs/lows
pivot detection
rolling extrema
ATR-normalized distance
ZigZag-like swing abstraction
```

These are primitives, not setups.

### Acceptance

- [ ] Same series produces same pivots.
- [ ] No future swing confirmation is used earlier than its confirmation timestamp.
- [ ] Every pivot has `known_at`.

---

## Task P2.2 — Contraction and volume-dry-up primitives

Calculate:

```text
base duration
base depth
range contraction
ATR-normalized rest depth
volume_dryup_ratio
tight-close ratio
volatility contraction
```

### Acceptance

- [ ] Definitions are written in docs and tests.
- [ ] No visual/LLM judgement is needed.

---

## Task P2.3 — Setup detectors

Build deterministic first-pass detectors for:

```text
Momentum Burst
Episodic Pivot
IPO Base
Inside Bar
Base Breakout
Pullback
Reversal / Reclaim
Power Play / Tight Continuation
```

Each detector returns:

```text
VALID
INVALID
INSUFFICIENT_DATA
```

plus reasons.

### Setup-specific requirements

#### Momentum Burst

Inputs:

```text
prior expansion
RS
RVOL
ADR
current shelf/contraction
AVWAP extension
```

#### Episodic Pivot

Inputs:

```text
gap
exceptional RVOL
close location
event/earnings context if known
EP AVWAP
delivery
```

#### IPO Base

Inputs:

```text
IPO AVWAP
base depth
base duration
volume contraction
RS
ADR
distance from listing high
```

#### Inside Bar

Inputs:

```text
inside-bar geometry
mother-bar size
range contraction
volume contraction
RS
sector strength
AVWAP proximity
```

#### Base Breakout

Inputs:

```text
base duration
base depth
contraction
breakout RVOL
breakout AVWAP
RS
sector momentum
distance to resistance
```

#### Pullback

Inputs:

```text
EP/breakout AVWAP
EMA21
pullback volume
ADR
sector state
RS stability
```

#### Reversal / Reclaim

Inputs:

```text
AVWAP reclaim
EMA reclaim
volume expansion
RS improvement
sector turn
failed breakdown
```

### Acceptance

- [ ] Gold fixtures exist for positive and negative examples.
- [ ] Each detector is separately disableable.
- [ ] No LLM or chart screenshot is required to detect the setup.

---

## Task P2.4 — Setup Quality

Score only after deterministic validity.

Possible contributors:

```text
geometry cleanliness
contraction
volume behaviour
RS
sector alignment
AVWAP relation
trigger clarity
```

Output:

```text
setup_quality_score
feature contributions
rule failures
```

### Acceptance

- [ ] An invalid setup cannot receive a high setup-quality score.
- [ ] Contributors are visible.
- [ ] Thresholds are configurable.

---

## Task P2.5 — Trigger and invalidation engine

For every setup create deterministic:

```text
trigger_price
trigger_type
structural_invalidation
trigger_known_at
```

Do not let the Context Judge invent these.

### Acceptance

- [ ] Trigger is reproducible.
- [ ] Trigger uses only known data.
- [ ] Missing structural invalidation remains unresolved.

---

## Task P2.6 — Overhead supply and breakout room

Detect relevant resistance using approved deterministic sources:

```text
recent swing highs
52W/ATH
volume-profile node if enabled
accepted social level as context only
```

Calculate:

```text
RoomPct = (Resistance - Entry) / Entry × 100
Room_ADR = RoomPct / ADR20
```

Illustrative context labels:

```text
<1 ADR   poor room
1–2 ADR  marginal
>2 ADR   good
>3 ADR   excellent
```

These labels remain configurable.

### Acceptance

- [ ] Resistance source is stored.
- [ ] Conflicting resistance levels remain visible.
- [ ] Room is not calculated against an invented target.

---

## Task P2.7 — Extension and correction type

Calculate:

```text
distance EMA21
distance EMA50
distance relevant AVWAP
distance in ADR
```

Classify correction:

```text
TIME
PRICE
MIXED
UNKNOWN
```

Time correction logic must be defined in code, not described loosely by the LLM.

### Acceptance

- [ ] A strong stock can be marked extended.
- [ ] Extension can reduce Entry Quality without reducing Stock Quality.

---

## Task P2.8 — Initial R:R and Entry Quality

Calculate an initial structural R:R using:

```text
candidate entry/trigger
structural invalidation
nearest relevant hurdle
```

Do not assume the hurdle is the final target.

Entry Quality incorporates:

```text
trigger cleanliness
extension
room
stop distance
initial R:R
intraday VWAP state where relevant
gap/chase risk
```

### Acceptance

- [ ] Entry Quality can be low while Stock and Setup Quality remain high.
- [ ] Output reason codes explain why.
- [ ] R:R numbers are deterministic.

---

## Task P2.9 — Optional GBT setup scorer

**Deferred until the gold corpus is large enough and point-in-time labels are verified.**

Inputs:

```text
engineered geometry only
```

Preferred model families:

```text
LightGBM
XGBoost
```

Labels may use a leak-free triple-barrier or explicitly defined outcome scheme.

Rules:

- deterministic detector remains candidate generator;
- model outputs calibrated probability, not truth;
- model never sees future data;
- model version is stored;
- feature importance is retained.

### Acceptance

- [ ] Training corpus passes leakage checks.
- [ ] Sample size is reported.
- [ ] Out-of-sample calibration is measured.
- [ ] Model beats or adds value to deterministic baseline.
- [ ] Otherwise feature flag remains off.

---

## Task P2.10 — Optional similarity layer

Use:

```text
DTW
matrix profile / STUMPY
shapelet-style nearest neighbours
```

Purpose:

```text
"Which historical gold setup is this most similar to?"
```

Not:

```text
"Therefore buy."
```

### Acceptance

- [ ] Similarity is explainable.
- [ ] Gold examples are point-in-time safe.
- [ ] Similarity adds value out-of-sample or remains research-only.

---

## PHASE 2 CHECKPOINT

- [ ] deterministic setup detection works;
- [ ] setup score cannot override invalid geometry;
- [ ] trigger/invalidation are explicit;
- [ ] breakout room and extension are calculated;
- [ ] stock/setup/entry scores remain separate;
- [ ] optional models remain off until evidence supports them.

---

# PHASE 3 — OrderFlow and live entry-quality confirmation

**Goal:** judge live entry health only after a valid candidate exists.

The existing `ORDERFLOW_BUILD_MANUAL.md` remains the child implementation reference for low-level feed/feature details. This phase defines how it integrates with the unified desk.

---

## Task P3.1 — Subscription tiers

Use:

```text
Tier A WATCH         200–400  quote only
Tier B ARMED          30–80   quote + depth
Tier C TRIGGER ZONE    5–30   full processing
```

Tier movement is deterministic.

CandidateContext controls promotion.

---

## Task P3.2 — Trigger-state machine

Implement:

```text
FAR
 │
 ▼
APPROACHING
 │
 ▼
TESTING
 ├───────────────┐
 ▼               ▼
CONFIRMED       FAILED
 │               │
 ▼               ▼
FOLLOW_THROUGH  REJECT/WATCH
```

### FAR

No intensive flow processing.

### APPROACHING

Look for:

```text
stable spread
improving depth quality
rising participation
```

### TESTING

Require actual trigger contact/test.

Evaluate:

```text
persistence
price response
spread
replenishment
book stability
```

### CONFIRMED

Require:

```text
price acceptance above trigger
constructive flow
no immediate reversal
no severe spread expansion
```

### FAILED

Typical evidence:

```text
return below trigger
ask replenishment
bid weakening
spread widening
price-response deterioration
```

### Acceptance

- [ ] State is reproducible from replay.
- [ ] A stale feed forces `UNKNOWN`, not CONFIRMED.
- [ ] State transition timestamps are stored.

---

## Task P3.3 — Slow-feed-safe features

Build first:

```text
spread %
spread percentile
spread volatility
top-1/top-5 depth value
book concentration
book stability
weighted imbalance
imbalance persistence
price-response efficiency
```

`price-response efficiency` is prioritized over raw imbalance.

Each feature requires:

```text
definition
window
null handling
confidence
unit test
```

---

## Task P3.4 — Conditional fast features

Remain `RESEARCH_ONLY` unless capability supports them:

```text
ask depletion
bid depletion
estimated aggression
estimated delta
rapid replenishment
sweep-like activity
rapid absorption
depth velocity
```

If 50-level TBT is active and empirically valid, feature flags may be promoted.

---

## Task P3.5 — Liquidity and capacity

Output:

```text
liquidity_score
liquidity_state
capacity_band
high_impact_band
```

Prefer exit liquidity over entry convenience.

Avoid false precision.

Example:

```text
LOW IMPACT
MODERATE
HIGH
VERY HIGH
```

with assumptions and confidence.

### Acceptance

- [ ] Liquidity REJECT hard-vetoes the candidate.
- [ ] Capacity output is clearly a market-capacity estimate, not position advice.
- [ ] Calibration uses recorded outcomes rather than arbitrary visible-depth percentages.

---

## Task P3.6 — Flow confidence and decision

```text
effective_flow_score =
raw_flow_score × flow_confidence
```

Confidence depends on:

```text
feed freshness
liquidity quality
depth completeness
book stability
sample count
feature agreement
```

Hard veto examples:

```text
liquidity REJECT
severe exit-liquidity risk
confirmed breakout failure
spread deterioration
book confidence too low
severe instability
high absorption/failure evidence
```

### Acceptance

- [ ] Veto overrides any momentum score.
- [ ] Low confidence cannot create strong confirmation.
- [ ] Every flow decision has reason codes.

---

## Task P3.7 — Validity window

Every flow assessment must have:

```text
assessed_at
valid_until
```

When expired:

```text
decision = UNKNOWN
```

No old green state persists indefinitely.

---

## Task P3.8 — Alerts and suppression

Alert types:

```text
approaching trigger
flow-confirmed breakout
absorption/failure warning
liquidity deterioration
failed breakout
feed degraded
```

Suppress with:

```text
cooldown
state-change-only
confidence minimum
score-change threshold
duplicate suppression
trigger-zone requirement
```

### Acceptance

- [ ] No repeated identical alerts.
- [ ] Correction/reversal states supersede prior alerts.
- [ ] Stale state never triggers confirmation.

---

## Task P3.9 — Replay engine

Replay raw session data through the production feature stack.

Required:

```text
original timestamps
gaps
stale transitions
feature snapshots
state transitions
alerts
```

### Acceptance

- [ ] Replayed state equals live recorded state for sampled sessions.
- [ ] No notebook-only feature logic exists.
- [ ] Config/version can be swapped for research without altering raw data.

---

## Task P3.10 — OrderFlow ablation

Compare:

```text
Model A  Momentum baseline
Model B  A + liquidity
Model C  B + core flow
Model D  C + flow vetoes
Model E  D + TBT-only features   # only if provisioned
```

Metrics:

```text
expectancy
median R
MFE
MAE
false-breakout rate
stop-out rate
1R/2R/3R attainment
drawdown
precision at top-N
```

Sequence:

```text
pooled
→ broad setup
→ regime/liquidity buckets only when n is adequate
```

### Acceptance

- [ ] C/D must beat A/B out-of-sample before promotion.
- [ ] E must independently justify TBT complexity.
- [ ] Negative result is published and feature disabled.

---

## PHASE 3 CHECKPOINT

- [ ] flow is trigger-aware;
- [ ] stale feed becomes UNKNOWN;
- [ ] liquidity hard gates work;
- [ ] replay matches live;
- [ ] OrderFlow proves incremental value before becoming authoritative.

---

# PHASE 4 — TraderLog Lite / Social Intelligence

**Goal:** keep the valuable evidence/claim machinery while avoiding the full V2 product sprawl.

TraderLog Lite has four jobs:

```text
1. archive source evidence
2. extract/validate trade claims
3. reconstruct accepted trader lifecycles
4. provide compact symbol/theme/trader context
```

It does **not** need the full V2 Radar/Playbook/Market-Chorus product before it can be useful.

---

## Task P4.1 — Freeze legacy truth and start a clean Lite projection

Do not treat old deterministic lifecycle rows as accepted.

Recommended:

```text
existing raw posts/media  -> immutable archive
accepted audited evidence -> eligible for migration
old questionable positions -> archive/quarantine
new claims                -> canonical Lite layer
```

### Acceptance

- [ ] Raw evidence is preserved.
- [ ] Old questionable lifecycles are excluded by default.
- [ ] Migration requires source evidence.
- [ ] Production raw archive is not rewritten.

---

## Task P4.2 — Pluggable source adapter

Define:

```python
SocialSourceAdapter:
    fetch_since(handle, watermark)
    fetch_thread(post_id)
    fetch_media(post_id)
```

Adapters may include approved sources such as:

```text
official API
local/manual manifest
browser-backed collection where operationally permitted
```

The rest of TraderLog must not depend on the transport.

### Acceptance

- [ ] Source adapter can be swapped without changing claim logic.
- [ ] Watermarks are advanced only after successful archive.
- [ ] Credentials never enter prompts/logs.

---

## Task P4.3 — Immutable post/media archive

Store:

```text
post_id
handle
timestamp
text
permalink/reference
conversation_id       nullable
parent_id             nullable
media hashes
raw metadata
source adapter
ingested_at
```

Unknown ancestry remains unknown.

### Acceptance

- [ ] Same post does not duplicate.
- [ ] Media hashes are stable.
- [ ] Missing parent/conversation is not invented.

---

## Task P4.4 — Evidence bundle

For each post:

```text
exact text
thread context if known
archived media
vision transcription
source metadata
```

Vision is never accepted as truth automatically.

### Acceptance

- [ ] Unreadable image returns no numeric claim.
- [ ] Contradictory text/image remains unresolved.

---

## Task P4.5 — Claim extraction

Produce zero or more provisional claims.

Required types:

```text
entry
add
stop_set
stop_move
target
partial_exit
full_exit
result_statement
watch
theme
market_view
lesson
```

Process newest-first for live utility.

Cache by evidence hash so unchanged evidence costs zero model calls.

### Acceptance

- [ ] Entry/add/stop/partial/full fixtures pass.
- [ ] Symbol-less close stays unresolved.
- [ ] Chart-only price cites media.

---

## Task P4.6 — Claim validation

Before persistence:

```text
handle matches source
timestamp matches source
quote exists verbatim
symbol is evidenced or unresolved
numeric values are visible/stated
post/media citation resolves
```

### Acceptance

- [ ] Unsupported assertions fail before canonical acceptance.
- [ ] Corrected claims create supersession history.
- [ ] Same payload is idempotent.

---

## Task P4.7 — Claim linkage and lifecycle

Priority evidence:

```text
exact parent/conversation
explicit permalink/reference
same verified handle + symbol + one compatible lifecycle
otherwise unresolved
```

Never use time proximity alone as proof.

Only accepted claims and accepted links may materialize lifecycle.

Rules:

```text
entry -> starts
add -> attaches to accepted compatible lifecycle
partial_exit -> partial
full_exit -> closed
market stop breach != trader-stated close
ambiguous close -> unresolved
```

### Acceptance

- [ ] Partial and full exits remain distinct.
- [ ] Every event has claim_id and post_id.
- [ ] Ambiguous close cannot silently close a lifecycle.

---

## Task P4.8 — Social Context API

Build compact outputs for the unified desk:

```text
recent accepted trader actions
independent trader count
theme mentions
attention trend
disagreement
coverage state
unresolved count
evidence refs
```

Do not create a composite “credibility” score.

### Acceptance

- [ ] Context opens exact evidence.
- [ ] Social context cannot write market scores.
- [ ] Missing coverage is explicit.

---

## Task P4.9 — Lite Ledger UI

Minimal layout:

```text
latest accepted events
selected lifecycle
source evidence
unresolved count
```

Keep:

```text
entry/add/stop/partial/full distinction
evidence thumbnails
source links
null = not stated
```

Defer:

```text
complex Radar
playbook generation
market chorus
heavy trader scoring
large historical migration
```

---

## Task P4.10 — Social incremental-value test

Research questions:

```text
Does independent trader attention improve candidate outcomes?
Does accepted trade commitment add more value than mentions?
Does same-theme multi-trader convergence help?
Does social disagreement predict poorer follow-through?
Does any effect remain after controlling for momentum context?
```

Test:

```text
baseline
+ social attention
+ accepted commitment
+ trader-history context
```

### Acceptance

- [ ] Social features must prove incremental value.
- [ ] If predictive value is absent, retain them as descriptive context only.
- [ ] No recommendation language is derived solely from social activity.

---

## PHASE 4 CHECKPOINT

- [ ] source archive is immutable;
- [ ] claims are evidence-backed;
- [ ] lifecycles use accepted claims only;
- [ ] social context is compact and inspectable;
- [ ] social data cannot override hard market gates.

---

# PHASE 5 — Context Judge and deterministic Decision Policy

**Goal:** use an LLM where it is strongest: synthesizing heterogeneous validated context, not producing market numbers.

---

## Task P5.1 — Judge input contract

Input contains only:

```text
MomentumContextSnapshot
SetupCandidate
TradeGeometrySnapshot
OrderFlowAssessment
SocialContextSnapshot
known event-risk flags
```

Every input field is serialized.

No chart screenshot is needed for setup detection.

---

## Task P5.2 — Judge prompt

The prompt instructs:

```text
1. Do not create or modify numbers.
2. Do not invent missing facts.
3. Treat UNKNOWN as meaningful.
4. Separate supporting factors from risks.
5. Identify contradictions.
6. Social information is context, not authority.
7. OrderFlow veto/liquidity hard gates cannot be argued away.
8. Do not issue an order or position size.
9. Keep explanation short enough for live use.
```

Required output is strict JSON/schema.

---

## Task P5.3 — Deterministic Decision Policy

The LLM does **not** produce the final policy state.

Example policy precedence:

```text
if market data stale:
    UNKNOWN

elif setup invalid:
    VETO

elif circuit/liquidity hard gate:
    VETO

elif entry geometry invalid:
    WAIT or VETO

elif flow VETO:
    VETO

elif flow UNKNOWN:
    WARN or UNKNOWN

else:
    ELIGIBLE / WARN
```

Exact mapping is configuration-controlled and validated.

---

## Task P5.4 — Context Judge evaluation

Log:

```text
candidate_id
judge output
policy state
human action if recorded
realized outcome
```

Test whether the Judge adds value over the deterministic policy.

Examples:

```text
Does judge downgrade identify weaker outcomes?
Do judge contradictions predict failure?
Do human decisions improve with judge context?
```

### Kill rule

If the Judge does not improve decision quality after an adequate sample, disable it.

A minimum review window may begin around 50–100 completed decisions, but promotion must depend on actual sample quality rather than the number alone.

---

## Task P5.5 — Independent audit sample

Adapt the evidence/audit principle:

For a random/stratified sample:

```text
input snapshot
judge output
actual source fields
policy output
outcome
```

Review for:

```text
invented facts
numeric drift
overstatement
ignored unknowns
contradictions omitted
```

### Acceptance

- [ ] Judge never authors a numeric trading field.
- [ ] Schema violations fail closed.
- [ ] Cached identical input gives reproducible structured output where possible.
- [ ] Model/prompt versions are stored.

---

## PHASE 5 CHECKPOINT

- [ ] policy remains deterministic;
- [ ] LLM is advisory only;
- [ ] all judge inputs are traceable;
- [ ] judge output is measured, not assumed useful.

---

# PHASE 6 — Unified Terminal and Alerts

**Goal:** present decision-quality information without turning the product into a dashboard museum.

---

## Task P6.1 — Candidate list

Default columns:

```text
Symbol
Price
Setup
Stock Q
Setup Q
Entry Q
Trigger distance
Liquidity
Flow
Social
Policy
```

Sort options:

```text
Entry Quality
Setup Quality
trigger proximity
RS
policy state
```

No default sort should imply that social or flow alone ranks stocks.

---

## Task P6.2 — Decision Card

Example:

```text
┌──────────────── ABC LTD ────────────────┐
│ Price                    ₹812.40         │
│ Setup                  Base Breakout     │
│ Trigger                   ₹814.00        │
│ Distance                    0.20%        │
│                                          │
│ STOCK QUALITY                  92        │
│ SETUP QUALITY                  88        │
│ ENTRY QUALITY                  71        │
│                                          │
│ Liquidity                     PASS       │
│ Flow                     CONFIRMING      │
│ Flow confidence                78%       │
│ Social                    3 traders      │
│                                          │
│ Risks                                    │
│ - resistance 1.3 ADR away               │
│ - sector breadth weakening              │
│                                          │
│ Unknowns                                  │
│ - delivery unavailable today            │
│                                          │
│ POLICY                         WARN      │
└──────────────────────────────────────────┘
```

The card must answer:

```text
good stock?
good setup?
good entry?
live confirmation?
what can go wrong?
what is unknown?
```

---

## Task P6.3 — Symbol workbench

Panels:

```text
1. price chart
2. setup geometry
3. momentum context
4. trade geometry
5. order flow
6. social evidence
7. research history
```

Chart overlays should remain restrained:

```text
candles
EMA21
EMA50
relevant AVWAPs
volume
trigger/invalidation
```

No indicator wall.

---

## Task P6.4 — OrderFlow detail

Show:

```text
window
spread
weighted imbalance
persistence
price response
book stability
liquidity
confidence
state
```

Fast/TBT-only features appear only if capability permits them.

---

## Task P6.5 — Social evidence rail

Show:

```text
accepted claim
author
time
claim type
stated/displayed level
evidence
review state
```

Contradictory claims remain separate.

---

## Task P6.6 — Alerts

Unified alert categories:

```text
Candidate armed
Approaching trigger
Entry geometry improved
Flow confirmation
Flow warning/veto
Liquidity deterioration
Failed breakout
Accepted trader claim
Policy-state change
```

Apply:

```text
cooldown
dedupe
state transition requirement
confidence minimum
```

No alert should contain an LLM-invented trading number.

---

## Task P6.7 — UI honesty

Rules:

```text
0 is visible
null is unknown
stale shows timestamp
empty is one factual line
no fabricated fallback
no decorative KPI
no hidden errors
```

Desktop acceptance target may use 1920×1080, while runtime may remain responsive.

---

## PHASE 6 CHECKPOINT

- [ ] candidate screen is scanable;
- [ ] Decision Card exposes separate quality layers;
- [ ] no stale/unknown value masquerades as valid;
- [ ] every social claim can open evidence;
- [ ] flow panel respects capability state;
- [ ] alerts are deduplicated.

---

# PHASE 7 — Common Research, Validation and Promotion Gates

**Goal:** make every layer earn its complexity.

This phase is implemented throughout the project, but no advanced feature is considered production-worthy until these requirements pass.

---

## Task P7.1 — Research Event Store

For every historical/live candidate store the **frozen decision-time state**.

```text
event_id
candidate_id
symbol
timestamp

market context
stock quality inputs
setup features
setup quality
trade geometry
entry quality

liquidity
flow
social context
judge output
policy state

config/version hashes
```

Store failed and vetoed candidates too.

Do not build a dataset containing only successful trades.

---

## Task P7.2 — Outcome labels

For each event calculate where relevant:

```text
MFE 5m / 15m / 30m
MAE 5m / 15m / 30m
session close return
next-day return
3D / 5D / 10D / 20D
breakout hold/fail
stop hit
1R / 2R / 3R
time to 1R
time below trigger
```

For swing setup modelling, an explicitly defined triple-barrier label may be added.

Every label definition is versioned.

---

## Task P7.3 — Leakage suite

Tests include:

```text
future bars hidden
future replies hidden
future sector membership hidden
future earnings outcome hidden
future setup confirmation hidden
model training fold isolated
normalization fit only on training data
gold library excludes future examples
```

Leakage failure blocks research claims.

---

## Task P7.4 — Ablation ladder

Recommended unified ladder:

```text
A  Momentum Context baseline

B  A + deterministic Setup Quality

C  B + Trade Geometry / Entry Quality

D  C + Liquidity

E  D + core OrderFlow

F  E + flow vetoes

G  F + Social Context

H  G + Context Judge

I  H + optional GBT setup model

J  I + optional similarity layer
```

Do not assume later is better.

At every step ask:

```text
Did the layer improve outcomes?
Did it reduce bad trades?
Did it improve calibration?
Did it add enough value for its complexity?
```

---

## Task P7.5 — Metrics

At minimum:

```text
expectancy
median R
win rate
MFE
MAE
1R/2R/3R attainment
false-breakout rate
stop-out rate
drawdown
precision at top-N
calibration
coverage
turnover/candidate count
```

For veto layers also measure:

```text
outcome of vetoed candidates
false-veto rate
avoided-loss rate
missed-winner rate
```

---

## Task P7.6 — Validation sequence

Use:

```text
Exploration / training
        ↓
Validation
        ↓
Walk-forward
        ↓
Live paper
        ↓
Limited production advisory
```

Never tune thresholds on the final evaluation sample.

---

## Task P7.7 — Sample-size policy

Start pooled.

Only segment when sample sizes justify it.

Example sequence:

```text
all valid triggers
→ broad setup families
→ market regime
→ liquidity bucket
→ setup × regime × liquidity
```

Every report shows `n`.

---

## Task P7.8 — Negative Findings Ledger

Maintain:

```text
research/NEGATIVE_FINDINGS.md
```

Record:

```text
feature/layer
hypothesis
sample
result
reason rejected
date
config/version
```

A failed feature is not deleted from history; it is disabled and documented.

---

## Task P7.9 — Promotion policy

A research feature may become production-active only when:

- [ ] definition is deterministic;
- [ ] point-in-time safe;
- [ ] null/stale policy exists;
- [ ] replay works where relevant;
- [ ] out-of-sample evidence exists;
- [ ] contribution is explainable;
- [ ] config is versioned;
- [ ] feature flag exists;
- [ ] failure mode is documented.

---

# PHASE 8 — Discipline and Journal Engine — later

**Status:** explicitly deferred until the selection/entry stack is stable.

**Goal:** analyze execution discipline and right-tail preservation, not predict prices.

---

## Task P8.1 — Trade Plan snapshot

When a human records a trade, store:

```text
decision_id
entry
initial stop
planned framework
setup type
risk unit
thesis notes
```

The system does not auto-place the order.

---

## Task P8.2 — Journal events

Record:

```text
entry
add
stop move
partial exit
full exit
manual override
cancelled setup
```

---

## Task P8.3 — Process-rule checks

Examples:

```text
stop widened?
winner cut before framework condition?
unplanned add?
late chase?
trade taken after veto?
repeated over-trading?
```

These are behavioural/process checks.

---

## Task P8.4 — Weekly LLM review

The LLM may summarize:

```text
repeated rule breaches
premature exits
late entries
ignored warnings
setup categories over-traded
right-tail truncation
```

It may not invent optimal stop parameters.

Parameter tuning is quantitative research.

---

## Task P8.5 — Discipline-layer validation

Measure whether process feedback changes:

```text
average R
right-tail capture
rule violation rate
premature-exit rate
drawdown
```

If not useful, do not expand it.

---

# 8. Data storage strategy

Use the right store for the right job.

## Parquet

Use for:

```text
daily bars
intraday bars
quotes
depth
derived time-series snapshots
research event exports
```

Partition by date/symbol where appropriate.

## DuckDB

Use for:

```text
research
feature queries
ablation
outcomes
walk-forward datasets
```

## SQLite/PostgreSQL-style transactional DB

Use for:

```text
social posts
claims
claim links
lifecycles
decision metadata
journal records
configuration registry
```

For MVP, existing SQLite may remain if integrity and write ownership are clear.

Do not add Redis/Celery/distributed infrastructure unless a measured bottleneck requires it.

---

# 9. Suggested runtime stack

Backend:

```text
Python 3.11+
FastAPI
Pydantic
asyncio
Polars or pandas
NumPy
DuckDB
PyArrow / Parquet
scikit-learn
LightGBM or XGBoost later
STUMPY/DTW later
pytest
```

Frontend:

```text
preserve existing React if already in use
Lightweight Charts for price panes
```

Avoid rewriting the UI stack merely for architectural neatness.

---

# 10. Unified API target

Suggested endpoints:

```text
GET /api/health
GET /api/universe
GET /api/candidates
GET /api/candidates/{id}

GET /api/symbol/{symbol}
GET /api/symbol/{symbol}/momentum
GET /api/symbol/{symbol}/setup
GET /api/symbol/{symbol}/geometry
GET /api/symbol/{symbol}/flow
GET /api/symbol/{symbol}/social

GET /api/decisions
GET /api/decisions/{id}

GET /api/social/ledger
GET /api/social/traders/{handle}

GET /api/research/ablation
GET /api/research/features/{feature}
```

Every endpoint must include where relevant:

```text
as_of
data_version
config_hash
stale/coverage state
stable empty arrays
```

---

# 11. Observability

Runtime metrics:

```text
market feed status
quotes/sec
depth updates/sec
feed latency
stale symbols
reconnect count

watch/armed/trigger-zone counts
candidate generation rate
setup detector counts
invalid setup reasons

flow UNKNOWN rate
flow veto rate
liquidity reject rate

social ingestion freshness
unresolved claim rate
vision coverage

LLM call count
LLM schema-failure rate
judge latency
judge cache hit rate

alerts/session
decision snapshots/session
```

Research health:

```text
event count
coverage
missing-feature rate
outcome-label completion
sample size per setup
leakage test status
active feature versions
```

---

# 12. Security and secrets

Rules:

```text
FYERS credentials -> environment/git-ignored config
social credentials -> local secure config
no secret in prompt
no secret in log
no secret in screenshot
no secret in handoff
```

The owner performs any interactive authentication.

Agents may operate only on already-authorized sessions/interfaces.

---

# 13. Failure and graceful-degradation policy

## If order flow fails

```text
Momentum remains active
Setup remains active
Entry Geometry remains active
Flow = UNKNOWN
Policy cannot claim confirmation
```

## If social data fails

```text
Market stack remains active
Social = UNKNOWN
No stale trader signal shown as current
```

## If delivery data is absent

```text
delivery features = UNKNOWN
other participation features continue
```

## If sector mapping is missing

```text
sector context = UNKNOWN
no generic benchmark substitution unless configured
```

## If Context Judge fails

```text
deterministic policy continues
judge = unavailable
```

## If UI panel fails

One panel failure must not crash the full terminal.

---

# 14. Testing strategy

Each feature requires:

```text
unit test
null test
stale/coverage test
point-in-time test
version/config test
```

Each module requires:

```text
gold fixtures
negative fixtures
replay/integration fixtures where relevant
```

System-level tests:

```text
good stock + bad setup
good stock + good setup + bad entry
good entry + liquidity reject
good entry + flow veto
good entry + social disagreement
flow stale
social unresolved
judge unavailable
all context healthy
```

Expected policy states must be explicit.

---

# 15. Example end-to-end candidate

```text
SYMBOL: EXAMPLE

STOCK CONTEXT
────────────────────────────
Trend                   strong
RS market                   97
RS sector                   91
Peer rank                 2/31
RVOL                      2.1x
Delivery expansion        1.6x
ADR20                     5.4%
Sector breadth              78

STOCK QUALITY                93

SETUP
────────────────────────────
Type              Base Breakout
Base duration              18d
Base depth                 9.2%
VDU                       0.58x
Trigger                 ₹514.00

SETUP QUALITY                89

TRADE GEOMETRY
────────────────────────────
Current                  ₹512.8
Trigger distance           0.23%
EMA21 extension             6.1%
Breakout AVWAP extension    2.2%
Room to hurdle           1.8 ADR
Structural stop          ₹497.5
Initial R:R                 1.7

ENTRY QUALITY                72

ORDER FLOW
────────────────────────────
Liquidity                  PASS
Flow                  CONFIRMING
Confidence                   0.78
Spread                     stable
Price response             strong

SOCIAL
────────────────────────────
Independent traders             3
Accepted recent entries          1
Theme mentions             rising
Unresolved claims                2

CONTEXT JUDGE
────────────────────────────
Grade                           B+
Support
- stock and sector leadership
- valid contraction
- constructive live response

Risks
- room only moderate
- two unresolved social claims

POLICY
────────────────────────────
WARN / ELIGIBLE-BUT-NOT-CLEAN

Human decides.
```

The important feature is not the final label.

It is that the terminal preserves:

```text
excellent stock
good setup
only moderate entry
constructive flow
known risks
known unknowns
```

instead of blending everything into one opaque score.

---

# 16. Recommended build order

The strict recommended order is:

```text
PHASE 0
contracts + point-in-time data + depth recorder

        ↓

PHASE 1
Momentum Context baseline

        ↓

PHASE 2
deterministic Setup Detection
+ Trade Geometry

        ↓

PHASE 3
OrderFlow / Liquidity
+ replay / ablation

        ↓

PHASE 4
TraderLog Lite
claims + social context

        ↓

PHASE 5
Context Judge
+ deterministic policy comparison

        ↓

PHASE 6
Unified terminal / alerts

        ↓

PHASE 7
promotion / walk-forward / live-paper
continuously applied to every layer

        ↓

PHASE 8
Discipline / Journal later
```

Parallel work allowed after Phase 0:

```text
Momentum Context historical backfill
and
TraderLog raw-evidence cleanup
and
OrderFlow recording
```

But production decision logic must respect the phase gates.

---

# 17. Minimum useful V1

A practical V1 should **not** wait for every advanced module.

Ship when this exists:

```text
1. point-in-time daily data
2. EMA21/50
3. RS market/sector/peer
4. RVOL
5. ADR20
6. AVWAP core
7. sector breadth
8. circuit/basic liquidity
9. deterministic setup detector
10. setup quality
11. trade geometry
12. stock/setup/entry split
13. FYERS recorder
14. slow-feed-safe flow features
15. liquidity gate
16. flow confirm/warn/veto
17. unified Decision Card
18. research event store
```

TraderLog Lite and the Context Judge may follow once the market stack is stable.

---

# 18. V2

Add only after V1 has recorded enough data:

```text
delivery analytics
volume profile
automatic event/EP anchors
IPO-specific analytics
session VWAP execution states
TBT-only order-flow features if available
setup-specific order-flow validation
clean TraderLog claims/lifecycles
social context
GBT setup classifier
similarity layer
Context Judge
```

---

# 19. V3 / optional research

Only if evidence justifies it:

```text
market-cap-specific thresholds
setup-specific flow models
regime-conditioned models
sector-specific liquidity baselines
dynamic trigger zones
operator-risk classifier
advanced theme clustering
model-based feature combination
Kronos/meta-labeling experiments
synthetic-path stop research
discipline/journal intelligence
```

No V3 feature is promoted because it sounds sophisticated.

---

# 20. Program-level Definition of Done

The unified desk is considered functionally complete when:

- [ ] market data is point-in-time and reproducible;
- [ ] candidate generation is deterministic;
- [ ] Stock Quality, Setup Quality and Entry Quality are separate;
- [ ] setup geometry can be audited without an LLM;
- [ ] trigger/invalidation are explicit;
- [ ] breakout room and extension are calculated;
- [ ] OrderFlow consumes a frozen CandidateContext;
- [ ] feed capability controls flow feature eligibility;
- [ ] stale flow becomes UNKNOWN;
- [ ] liquidity hard gates work;
- [ ] replay reproduces flow decisions;
- [ ] TraderLog Lite claims retain exact evidence;
- [ ] unresolved social claims remain unresolved;
- [ ] social context cannot override hard market gates;
- [ ] Context Judge never authors numbers;
- [ ] deterministic policy works without the LLM;
- [ ] every decision snapshot is versioned;
- [ ] failed/vetoed candidates are retained for research;
- [ ] MFE/MAE/R outcomes are stored;
- [ ] leakage tests are green;
- [ ] each advanced layer has an ablation result;
- [ ] useless layers can be disabled without breaking the product;
- [ ] no order-placement call exists;
- [ ] human authorization remains the final action.

---

# 21. Completion report template

Use this lighter template for each task:

```markdown
# <TASK_ID>_COMPLETED

Status: complete | partial | blocked

## Goal
<one sentence>

## Dependencies
- <checkpoint/task>

## Files changed
- <path> — <purpose>

## Baseline
- focused tests:
- known pre-existing failures:

## Implementation
1. ...
2. ...

## Acceptance evidence
- [PASS/FAIL] criterion
- [PASS/FAIL] criterion

## Data impact
- stores touched:
- before counts:
- after counts:
- integrity:
- point-in-time check:

## Versions
- config hash:
- feature/rule version:
- model version if applicable:

## Verification
- focused tests:
- package tests:
- desk checks:
- UI build if applicable:

## Unresolved
- ...

## Safety
- no order placement
- no invented market fields
- no future-data dependency
- no stale value presented as live
```

---

# 22. Final product philosophy

The desk should behave like this:

```text
STRONG STOCK
     │
     ▼
VALID SETUP
     │
     ▼
GOOD CURRENT GEOMETRY?
     │
     ├── NO  -> WAIT
     │
     ▼
TRADABLE / EXIT-CAPABLE?
     │
     ├── NO  -> VETO
     │
     ▼
LIVE FLOW HEALTHY?
     │
     ├── BAD -> VETO/WARN
     │
     ▼
SOCIAL / EVENT CONTEXT
     │
     ▼
ADVISORY SYNTHESIS
     │
     ▼
HUMAN DECISION
```

The system should become **less** impressed by complexity as it matures, not more.

If a simpler stack:

```text
Momentum Context
+ Setup Geometry
+ Trade Geometry
+ Liquidity
```

performs as well as:

```text
Momentum
+ Flow
+ Social
+ LLM
+ models
```

then the simpler stack wins.

That is not a failed project.

That is the project discovering where the actual edge is.
