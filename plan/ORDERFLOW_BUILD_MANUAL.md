# Order-Flow Engine — build manual

> **Status update 2026-08-29:** with D10 (EOD-first product), this manual now
> governs the OPTIONAL live-confirmation module only (Build V2 §8) — off the
> critical path until the owner requests trigger-moment confirmation.
> **Status update 2026-08-28:** this manual is now the **child implementation
> reference for Phase 3** of `UNIFIED_DESK_BUILD_MANUAL.md` (which states this
> role explicitly). Its Phase 0 tasks map to unified U-P0.4/U-P0.5; its rules
> R1–R9 survive verbatim as unified R8/R9/R10/R11/R12. Crosswalk:
> `plan/UNIFIED_DESK_INTEGRATION_PLAN.md`.

Status: controlling build manual for the `orderflow/` layer.
Created: 2026-08-28. Nothing is built yet — this is greenfield, verified.
Repo map: [`DESK.md`](../DESK.md). Read that first.

This is an execution manual. Follow it in order. Do not implement a downstream
task while an upstream checkpoint is red.

---

## 0. What is being built, and what is not

An **entry-quality and failure-detection layer** for Indian midcap/smallcap
momentum trading, fed by FYERS live market data.

It answers one question:

> An already-strong momentum setup is at its trigger. Is near-price market
> behaviour confirming the entry, neutral, or warning us away?

**It is not** a stock-selection engine, an HFT system, a scalping DOM, a
tick-by-tick exchange reconstruction, or an order router. It never places
orders.

### 0.1 The design decision that shapes everything

Order flow is a **veto and confirmation layer, not a ranking weight.**

The reasoning is arithmetic, from the owner's own audit review: a flow score
swinging 84 → 20 is a 64-point move, which at a 12% weight shifts the final
score by 7.7 points — often not even one band. As a ranker it is noise; as a
veto it is decisive.

```
  MOMENTUM ENGINE    finds the candidate       (EOD, separate layer)
  LIQUIDITY ENGINE   decides tradability + position capacity
  ORDER-FLOW ENGINE  judges whether the entry is healthy
                            │
                     CONFIRM / WARN / VETO
```

Flow gets a small numeric weight (~5%) and strong veto authority.

---

## 1. Non-negotiable rules

**R1 — Measure the feed before designing on it.** No feature window is
implemented before Phase 0 has measured that the feed supports it. This inverts
the original spec and is the single most important rule here.

**R2 — Record before you analyse.** OHLCV can be backfilled forever; **order-book
history cannot be reconstructed after the fact.** The recorder ships before the
feature stack.

**R3 — Never present stale state as live.** If depth is stale past threshold:
`order_flow_enabled = false`, `flow_state = UNKNOWN`. Never display the last
known bullish/bearish reading.

**R4 — Never claim what the feed cannot prove.** These are forbidden as
assertions: institutional buying, FII/HNI activity, spoofing, iceberg size,
hidden liquidity, broker identity, queue position, true aggressor side. Use
probabilistic labels: `buyer aggression estimate`, `seller absorption
likelihood`, `manipulation-like behaviour`, `sweep-like event`.

**R5 — Missing source fields are null, never invented.** If FYERS does not
supply a field, store `null`, disable dependent features, and surface the
capability gap.

**R6 — Reactor Scale is context, never a risk input.** Per its own header in
`traderlog/adopted/activity.py`, its output *"must never be presented as
institutional identity, trade direction, or a risk input."* Display the activity
score and percentile beside a candidate; **never** fold it into a weighted entry
score.

**R7 — Credentials never touch the repo.** FYERS app id, secret and access token
live in git-ignored config or environment. Never committed, never logged, never
put in a handoff or screenshot, never handled by an agent. The owner performs
any interactive auth.

**R8 — No order routing, no position sizing advice to the user.** The liquidity
engine may compute a *capacity ceiling* (what size the book can absorb); it does
not tell the user what to trade or how much.

**R9 — Publish negative results.** If ablation shows flow adds nothing, record
that in the audit ledger and drop the feature. See TraderLog finding N1 for the
worked example of a metric that failed and was published as failed.

---

## 2. Layout

```
orderflow/
  CANONICAL.md            which DB/files are live, single-writer map
  config.example.yaml     thresholds + feature flags (real config git-ignored)
  capability.json         WRITTEN BY PHASE 0 — the feed's measured capability
  market_data/
    fyers_adapter.py      raw FYERS → canonical models. The ONLY file that
                          knows FYERS field names.
    websocket_manager.py  connect, subscribe, reconnect, heartbeat
    schemas.py            QuoteUpdate, DepthLevel, DepthSnapshot
  universe/
    builder.py            daily candidate universe
    filters.py            port the gates from traderlog/adopted/activity.py
  storage/
    parquet_writer.py     raw + derived, partitioned by date/symbol
    duckdb_repo.py        research query layer
  features/
    liquidity.py  spread.py  imbalance.py  persistence.py  price_response.py
  scoring/
    flow.py  gates.py  penalties.py
  checks/
    feed_health.py  capability_audit.py  __main__.py
  tests/
  data/
    raw/date=YYYY-MM-DD/symbol=SYM/{quotes,depth}.parquet
```

**Boundary:** no `import traderlog`, no `import manas_os`. Adopt by copying with
a provenance header (the worked example is `traderlog/adopted/activity.py`).

---

## 3. Canonical data models

The adapter's job is that nothing downstream ever sees a FYERS field name.

```python
QuoteUpdate:
    ts_exchange, ts_received, symbol
    ltp, open, high, low, prev_close
    session_volume
    last_trade_qty          # optional; null if absent

DepthLevel:
    price, quantity, order_count   # order_count optional

DepthSnapshot:
    ts_exchange, ts_received, symbol
    bids: list[DepthLevel]         # up to 5, or up to 50 if TBT
    asks: list[DepthLevel]
    total_buy_qty, total_sell_qty  # optional
    feed_latency_ms
```

Every optional field is `null` when unavailable (R5), and the capability file
records which are actually populated.

---

## Task P0.1 — Feed capability audit  ← START HERE

**Nothing else may be built until this is green.**

Files allowed: `market_data/fyers_adapter.py`, `market_data/websocket_manager.py`,
`market_data/schemas.py`, `checks/capability_audit.py`, `capability.json`,
`tests/test_capability_audit.py`.

**Steps**

1. Connect using the existing `fyers_apiv3` auth pattern (see
   `.claude/worktrees/*/scripts/refresh_token.py` for the token-refresh flow).
   The owner supplies credentials out-of-band.
2. Subscribe to a deliberately mixed sample — highly liquid midcap, moderately
   liquid midcap, liquid smallcap, thin smallcap. At least 8 symbols.
3. Log every quote and depth message with `ts_exchange` and `ts_received`, raw,
   for one full session.
4. Measure and write `capability.json`:
   - depth inter-arrival histogram (0–100ms / 100–250 / 250–500 / 500–1000 / >1000)
   - median and p95 update interval, **per liquidity bucket**
   - quote/depth synchronisation
   - burstiness and stale periods
   - subscription limits actually enforced
   - which optional fields are populated (`order_count`, `total_buy_qty`, `last_trade_qty`)
   - **whether 50-level TBT is provisioned for NSE cash on this account** —
     `Unverified:` today. An external review claims FYERS added it; that claim
     has not been tested here and must not be assumed.

**Acceptance**

- [ ] `capability.json` exists with a real measured histogram, not a placeholder.
- [ ] Per-bucket medians recorded — a feature can be valid in liquid midcaps and
      useless in thin smallcaps, and one global number hides that.
- [ ] Every optional field marked present/absent from observation.
- [ ] TBT availability answered with evidence either way.

**The gate this sets:**

| Measured median depth interval | 5s | 15s | 1m | 5m |
|---|---|---|---|---|
| ~1 Hz or slower | research only | low confidence | valid | valid |
| materially faster | valid | valid | valid | valid |
| 50-level TBT active | primary | primary | context | context |

The feature engine **reads `capability.json` at runtime** and disables windows
the feed does not support. Capability-aware, never hard-coded.

---

## Task P0.2 — Recorder

Files allowed: `storage/parquet_writer.py`, `storage/duckdb_repo.py`,
`checks/feed_health.py`, `tests/`.

Record every session from now on, continuously, before any feature work (R2).

**Steps**

1. Write canonical quotes and depth to Parquet, partitioned
   `date=YYYY-MM-DD/symbol=SYM/`.
2. DuckDB query layer over the Parquet for research.
3. Feed-health state machine: `HEALTHY / DEGRADED / STALE / DISCONNECTED`, with
   last-quote age, last-depth age, reconnect count, duplicate detection, clock
   skew, out-of-order timestamps, nonsensical quantities.
4. Reconnect with subscription recovery.

**Acceptance**

- [ ] A forced disconnect mid-session reconnects and resubscribes; the gap is
      visible in the data, not silently interpolated.
- [ ] Replaying one session's Parquet reproduces the canonical book state.
- [ ] Stale depth sets `flow_state = UNKNOWN` (R3) — proven by a test that
      advances a clock, not by inspection.
- [ ] No credential appears in any written file or log (R7).

---

## Task P1.1 — Universe and subscription tiers

Files allowed: `universe/builder.py`, `universe/filters.py`, `tests/`.

Do not subscribe blindly to the whole exchange. Three tiers:

```
  Tier A  WATCH         200–400 symbols   quote only
  Tier B  ARMED          30–80 symbols    quote + depth
  Tier C  TRIGGER ZONE    5–30 symbols    full processing, alerts enabled
```

Port the tradeability gates already written in
`traderlog/adopted/activity.py` — price floor, average-turnover floor, ETF-name
exclusion, circuit-lock. Copy with a provenance header; do not import.

**Acceptance:** tier membership is deterministic and reproducible from a given
date's EOD data; symbols move between tiers on measured criteria, never manually.

---

## Task P1.2 — Features that survive a slow feed

Files allowed: `features/*.py`, `tests/`.

Build **only** these first. They depend on persistent state and price response
rather than exact event ordering, so they survive ~1 Hz sampling:

- spread, spread %, spread percentile, spread volatility
- liquidity quality: top-1 / top-5 depth value, turnover, order-count quality
- book concentration (`largest_level_share`) and stability
- weighted imbalance (distance-weighted; nearer levels matter more)
- imbalance **persistence** across windows — never a single snapshot
- **price response efficiency** — the highest-value feature in this layer: is
  aggressive participation actually moving price?

Each feature needs a unit test, a deterministic definition, explicit null
handling, a confidence input and a named window.

### Deferred to `RESEARCH_ONLY` until Phase 0 justifies them

Ask depletion · aggression inference · estimated delta · sweep-like detection ·
rapid depth velocity · fast absorption transitions.

**Store them; do not score them.** The original spec gave ask depletion a 20%
weight; that is too aggressive when event ordering is uncertain. Start at ~5% or
research-only, and raise only if TBT validation proves identification quality.

---

## Task P1.3 — Liquidity gate with position capacity

`PASS / WARN / REJECT` is insufficient for smallcaps. The gate must also output:

```
  Liquidity score            0–100
  Liquidity state            PASS / WARN / REJECT
  Suggested position ceiling ₹
  High-impact zone           > ₹
```

Prioritise **exit** liquidity, not entry. Calibrate empirically from recorded
data; a fixed percentage of visible depth is not a calibration.

This is capacity, not advice (R8).

---

## Task P2.1 — Flow score, confidence, and state

```
  effective_flow_score = raw_flow_score × flow_confidence
```

`flow_confidence` (0–1) depends on feed freshness, liquidity quality, depth
completeness, book stability, sample count and feature agreement. Scoring a
noisy smallcap book confidently is the failure this prevents.

States: `STRONG CONFIRMATION · CONFIRMING · MIXED · WEAK · BREAKOUT RISK ·
UNTRUSTWORTHY BOOK · UNKNOWN`.

**Hard vetoes override any momentum score:** liquidity `REJECT`; absorption
`HIGH`; confirmed breakout failure; spread deterioration past threshold; book
confidence too low; severe instability; severe exit-liquidity risk.

---

## Task P2.2 — Ablation, before anything reaches production scoring

```
  Model A   momentum baseline (EOD: RS, ADR, RVOL, theme, setup)
  Model B   A + liquidity
  Model C   B + core flow features
  Model D   C + flow vetoes
```

Measure expectancy, median R, MFE, MAE, false-breakout rate, stop-out rate,
1R/2R/3R attainment, drawdown, precision at top-N.

**Sequencing rule — pooled first.** Do not immediately segment. The arithmetic:
~10 triggers/day × 125 sessions ≈ 1,250 events; split across 4 setups × 3
regimes × 3 liquidity buckets = 36 cells ≈ 35 events per cell before uneven
distribution. That is too thin to conclude anything. Stage 1 pooled; Stage 2 by
broad setup; Stage 3 fully bucketed only when counts justify it.

**Order flow earns its complexity only if C/D beat A/B out-of-sample.** If it
does not, publish the negative result and drop it (R9).

---

## 4. Validation method

```
  Training / exploratory  →  Validation  →  Walk-forward  →  Live paper
```

Never tune thresholds on the full historical sample. All thresholds live in
`config.yaml`, never in code. All feature modules are independently switchable
via feature flags, so ablation is a config change.

---

## 5. Verification — every phase

- Each feature: unit test, deterministic definition, null handling, window,
  confidence.
- Feed: reconnects safely; no stale state shown as live; raw persisted without
  gaps; canonical state matches provider messages.
- Scoring: weights configurable; penalties explainable; hard gates override
  numeric scores; a score decomposes into its contributors.
- A test asserts `activity_score` (Reactor Scale) appears nowhere in a weighted
  entry score (R6).
- A test asserts no order-placement call exists anywhere in the package (R8).
- Research: every live signal reproducible from stored data; every feature
  disableable for ablation.
- Secret scan clean across source, logs and any screenshot.

---

## 6. Honest expectations

**Phase 0 may kill the interesting half of this project.** If FYERS depth
arrives at roughly 1 Hz and 50-level TBT is not provisioned, then ask depletion,
sweep detection and short-window aggression are not supportable, and what
remains is a liquidity-quality and price-response layer.

That would still be worth having — it is the part that vetoes bad entries in
thin smallcaps, which is the real risk in this market. But it is a materially
smaller product than the original spec describes, and the manual should not
pretend otherwise.

Decide that on the measurement, not on the spec.
