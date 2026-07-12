# sat10ic os — Alpha Learning Constraints

Status: standing product constraint (user correction, 2026-07-11)

## Market rotation UI invariant

- Sector and theme rotation is core decision context, not expert-only detail. The Market screen must expose the broader Nifty indices, actual ChartsMaze sectors and industry/themes, FII/DII movement, movers/deals, and short-to-mid-term relative strength whenever their canonical history exists.
- NSE thematic/strategy indices are not a substitute for ChartsMaze industry/themes and must not be labelled as such. Missing taxonomy/history renders honestly; the browser must not fabricate ranks.

## Product intent

Deterministic filters are the eligibility, data-quality, tradability, and risk
governor. They are not the alpha engine. Passing a checklist is not evidence of
edge, and failing a conventional continuation template must not prevent the
system from studying a distinct, explicitly modelled reversal opportunity.

The debate layer must reason about a stock's observed price/volume behaviour in
context, including:

- its theme and sector behaviour relative to the market;
- the current Indian market regime and breadth phase;
- catalyst/event context (earnings, EP/PEAD, IPO age/base, deals and results);
- participation, urgency, supply absorption, trapped participants and failed
  moves;
- path and timing, not only endpoint indicators;
- parallel TradeTM, Manas Arora/Strong Start, and StocksGeeks/IPO execution
  mechanisms rather than one universal setup template;
- asymmetric reversal opportunities where the invalidation is tight and the
  plausible reward is a multiple of risk.

## Learning loop

Every debate decision, including TAKE, WATCH, SKIP and gate-blocked candidates,
must create an immutable decision record containing the evidence available at
decision time. Later market data must resolve that record with path-dependent
outcomes. Before a new debate, agents should retrieve comparable prior episodes
weighted by similarity, recency, sample size, data quality and realised outcome.

Memory may inform a thesis; it may not silently rewrite hard tradability or risk
rules. Learned claims remain hypotheses until validated out of sample. The UI
must distinguish sourced observations, retrieved analogues, model inference,
tested findings and untested hypotheses.

## Research discipline

An alpha research loop may propose new features, interactions and setup variants
from the local Indian dataset, but promotion requires:

1. point-in-time/casual feature construction with no future leakage;
2. realistic Indian costs, liquidity, circuits, ASM/GSM and manual-execution
   assumptions;
3. walk-forward and regime/sector/setup-family breakdowns;
4. comparison with a simple baseline and falsification/placebo checks;
5. minimum-sample and stability requirements;
6. a frozen experiment record, including failed ideas, to prevent repeated
   rediscovery and selection bias;
7. shadow/paper observation before any influence on live ranking.

No LLM confidence score directly controls position size. Deterministic money and
risk mathematics remain authoritative.

## Primary alpha hierarchy (user correction, 2026-07-11)

For Indian manual swing trading, the product must prioritize, in order:

1. regime and breadth-state recognition;
2. opportunity and leadership ranking;
3. chart/setup interpretation across valid archetypes;
4. risk context and uncertainty;
5. calibrated forecasts only as secondary supporting evidence.

The LLM debate is not a prose wrapper around gate results. It must receive a
causal behavioural description of the chart (EMA structure and slopes, volume
expansion/contraction, RS and ADR, base duration/depth/tightness, gap retention,
pocket pivots, failed moves and relative behaviour versus theme/sector) and use
that evidence to form a thesis, antithesis, trigger, invalidation and expected
path. EP, flags, VCP, earnings gap-and-go, IPO bases, long-base Stage-2
breakouts, pocket pivots and reversal asymmetry are parallel archetypes; no
single continuation checklist defines all of them.

## External projects — adopt concepts, not wholesale assumptions

- QuantGPT: hypothesis/expression generation, batch evaluation, failure
  diagnosis, anti-overfit tests, walk-forward validation, experiment knowledge
  base and independent cross-review. Rebuild around NSE data and Indian swing
  outcomes; do not import its WorldQuant/China-market assumptions as strategy.
- TradeMemory Protocol: decision/outcome audit model, comparable-condition
  retrieval and outcome-weighted memory. Prefer a native adapter over making an
  external service the source of truth; sat10ic's SQLite records remain canonical.
- claude-trading-skills: workflow/checklist and journal-review patterns. Extract
  useful reasoning templates, then ground them in TradeTM/Manas/StocksGeeks.
- xtquantai: useful research-to-backtest specification and look-ahead checks;
  its QMT execution runtime and China-specific universe are not adopted.
- Awesome Vibe Trading Bot: reference catalogue and cost-aware model-routing
  ideas only; it is not a validated alpha source.

## Non-negotiable UI evidence

For each debated stock, the user should be able to see:

- what the stock is doing now, in plain English;
- why that behaviour matters in this theme/regime;
- the best confirming and contradicting evidence;
- comparable historical episodes and how they resolved;
- which teacher/execution lens generated the thesis;
- the proposed trigger, invalidation, expected path and time window;
- what the system learned after the outcome matured.
