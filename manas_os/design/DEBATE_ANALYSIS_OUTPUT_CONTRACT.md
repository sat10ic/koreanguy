# sat10ic os Debate Analysis Output Contract

**Status:** binding product and implementation contract  
**Captured:** 2026-07-13  
**Applies to:** chart observer, execution-lens agents, chair, risk governor,
Debate API and Debate UI

## 1. Required outcome

The primary Debate result must read like a competent trader's chart plan, not a
model-vote transcript. The beginner must be able to understand:

1. what the chart is doing;
2. which setup family may apply;
3. what must happen before entry;
4. what would invalidate the idea;
5. what path is expected, over what trading-session window;
6. why the stock is behaving well or poorly versus its theme, sector and index;
7. whether the setup is good but not yet triggered, triggered but blocked by
   risk, executable now, or invalidated;
8. what the system will learn after the opportunity matures.

The existing `TAKE`/`SKIP`, conviction, rank and prose fragments are insufficient
as the primary user output. They may remain as internal compatibility fields while
the new contract is introduced.

## 2. Mandatory responsibility split

### LLM: observe and form a falsifiable chart thesis

The LLM may:

- name one or more plausible setup families;
- identify chart-observed trigger and acceptance zones;
- identify structural invalidation and nearby decision levels;
- describe EMA, volume, RS, ADR, gap, base and price-path behaviour;
- compare the stock with its theme, sector and broad index;
- propose an expected sequence and horizon measured in bars or trading sessions;
- state the strongest contradiction and a credible alternative reading;
- say that no clean setup is visible.

Every claimed level or fact must carry timeframe, as-of timestamp and evidence
provenance. A level inferred from visible structure must be labelled
`STRUCTURE_DERIVED`; it is not automatically an order level.

### Server: validate execution and own money mathematics

Only the deterministic server may publish:

- executable entry and stop;
- valid structural target or management checkpoint;
- R multiple and reward-to-risk;
- permitted quantity and rupee risk;
- portfolio-heat, liquidity, circuit, ASM/GSM and regime eligibility;
- final `EXECUTABLE_NOW` or `BLOCKED_BY_RISK` state.

An LLM may propose a structural invalidation, but it may not silently turn it into
the broker stop. An LLM-generated score may not control quantity, risk or gate
eligibility.

### UI/API: join the two without obscuring provenance

The rendered Decision Card combines the LLM analysis packet with the validated
server plan. It must label every level as one of:

- `OBSERVED` — directly present in point-in-time market data;
- `STRUCTURE_DERIVED` — inferred from a visible base, pivot, gap or swing;
- `SERVER_VALIDATED` — accepted by the deterministic trade-plan engine;
- `SYNTHETIC_RESEARCH_ONLY` — an ATR/model projection that cannot be presented as
  a broker-ready target.

## 3. Required decision states

Do not collapse the analysis to `TAKE` or `SKIP`. The public state must be one of:

- `PREPARE` — interesting structure; trigger is not close or not yet defined;
- `WATCH_FOR_TRIGGER` — valid setup and explicit trigger, not triggered yet;
- `TRIGGERED_AWAIT_ACCEPTANCE` — price crossed the trigger but confirmation is incomplete;
- `EXECUTABLE_NOW` — trigger and deterministic risk plan are valid;
- `GOOD_SETUP_BLOCKED_BY_RISK` — chart thesis survives; execution does not;
- `NO_CLEAN_SETUP` — evidence does not support a coherent opportunity;
- `INVALIDATED` — the stated structural thesis failed;
- `EXPIRED` — the trigger did not occur inside the declared review window.

This separation is required for false-negative learning. A risk-blocked stock remains
available to observation, counterfactual outcome resolution and later review.

## 4. LLM analysis packet

The observer and lens agents return structured data. Prose is rendered from these
fields; it is not the only durable record.

```json
{
  "symbol": "SYMBOL",
  "as_of": "point-in-time timestamp",
  "timeframes": ["1D", "1W"],
  "chart_read": {
    "plain_english": "What price and volume are doing now.",
    "market_structure": "Trend, base, reversal or transition state.",
    "participation": "Volume/turnover and supply-demand behaviour.",
    "relative_behaviour": {
      "theme": "Stock versus actual theme basket.",
      "sector": "Stock versus actual sector basket.",
      "index": "Stock versus relevant broad index."
    },
    "evidence": [
      {
        "claim": "A causal, observable fact.",
        "timeframe": "1D",
        "source_fields": ["close", "ema_21", "volume_ratio"],
        "as_of": "timestamp"
      }
    ],
    "strongest_contradiction": "The best evidence against the primary read.",
    "alternative_read": "A credible competing interpretation."
  },
  "hypotheses": [
    {
      "lens": "tradetm | manas_strong_start | manas_reversal | stocksgeeks_ipo | other_versioned_lens",
      "setup_family": "Versioned setup/archetype name.",
      "setup_quality": "STRONG | MIXED | WEAK",
      "trigger_state": "PREPARE | WATCH_FOR_TRIGGER | TRIGGERED_AWAIT_ACCEPTANCE | INVALIDATED | EXPIRED",
      "trigger": {
        "description": "Observable condition, not merely a price number.",
        "zone_low": null,
        "zone_high": null,
        "timeframe": "1D",
        "level_kind": "OBSERVED | STRUCTURE_DERIVED"
      },
      "structural_invalidation": {
        "description": "What price behaviour disproves the setup.",
        "zone_low": null,
        "zone_high": null,
        "timeframe": "1D",
        "level_kind": "OBSERVED | STRUCTURE_DERIVED"
      },
      "expected_sequence": [
        {
          "step": "The next behaviour that would confirm or weaken the thesis.",
          "window_bars_min": null,
          "window_bars_max": null,
          "timeframe": "1D"
        }
      ],
      "management_hypothesis": "Structural decision point or trailing approach.",
      "expiry_condition": "When to stop watching if no trigger appears.",
      "narrative": "A concise evidence-led synthesis."
    }
  ],
  "data_quality": {
    "freshness": "LIVE | EOD | STALE | INCOMPLETE",
    "missing_inputs": [],
    "chart_coverage": "timeframe and session coverage used"
  }
}
```

The schema must reject claims whose evidence timestamps occur after `as_of`. It
must also permit multiple parallel hypotheses rather than forcing TradeTM, Manas
and StocksGeeks into one averaged verdict.

## 5. Joined beginner Decision Card

The default card uses this information order:

```text
SYMBOL · Daily + Weekly · as of <timestamp>

READ
<plain-English chart behaviour>

SETUP
<teacher/execution lens> · <setup family>
State: <WATCH FOR TRIGGER / EXECUTABLE NOW / GOOD SETUP, BLOCKED BY RISK / ...>

TRIGGER
<retest acceptance, breakout/retest or another observable condition>

STRUCTURAL INVALIDATION
<what chart behaviour makes the thesis wrong>

EXPECTED SEQUENCE
1. <next confirming behaviour> · <window in bars/trading sessions>
2. <first decision point> · <window in bars/trading sessions>
3. <continuation, trail or failure condition>

WHY IT MAY WORK
<top confirming evidence, including relative behaviour>

WHAT COULD BREAK IT
<strongest contradiction and alternative read>

EXECUTION — SERVER VALIDATED
Entry: <validated level/zone or "not available">
Stop: <validated stop or "not available">
Decision point/target: <validated structure or management rule>
Quantity and risk: <server values or block reason>

LEARNING
<unresolved / trigger missed / +1R first / stop first / no trigger / expired>
```

Model identities, vote counts, prompt stages and raw JSON belong in Expert detail.
They must not appear above the chart plan in beginner mode.

## 6. Entries, stops, targets and ETA

### Entry

An entry is a conditional behaviour plus a level or zone. “Buy above X” is not
enough. The card states whether the condition is a retest with acceptance, a
breakout/retest, a reversal reclaim, a Strong Start trigger or another versioned
mechanism.

### Stop and invalidation

Display two separate concepts when they differ:

- **Structural invalidation:** the LLM's evidence-based statement of what makes the
  chart thesis wrong.
- **Executable stop:** the deterministic server's valid stop after gap, circuit,
  slippage, regime and risk checks.

If no safe executable stop exists, show `GOOD SETUP — BLOCKED BY RISK`; do not erase
the analysis and do not fabricate a tighter stop.

### Targets

Use real overhead structure or the teacher lens's explicit management method. If a
level is only estimated from visible structure, label it as such and require server
validation before it appears in the execution block. Momentum, catalyst or reversal
plays may use a trailing management checkpoint instead of a fixed price target.

### ETA

ETA is a falsifiable review window, not a promise. Preserve its native bar timeframe
and also render it in Indian trading sessions. Hour estimates are permitted only when
the source is an intraday setup with complete causal intraday bars. For daily/weekly
swing plans, the default user-facing unit is trading sessions. Every hypothesis also
needs an expiry condition.

## 7. Score contract

Keep the existing rule that the LLM cannot invent a numeric score.

The beginner card initially shows:

- setup quality: `STRONG`, `MIXED` or `WEAK` from the evidence rubric;
- trigger readiness: the explicit state from section 3;
- execution: server-validated `EXECUTABLE`, `WAIT` or `BLOCKED`;
- evidence quality: freshness, coverage and missing inputs.

A `/100` score may be added only after it is server-computed from versioned,
visible components, calibrated against resolved outcomes and shown with the component
breakdown. It remains descriptive and cannot change position size. Therefore an
opaque LLM-authored `81/100 (Tradable)` is not acceptable, even when the surrounding
narrative is useful.

## 8. Narrative contract

The narrative must:

- synthesize evidence rather than repeat scanner labels;
- distinguish observed facts from inference;
- mention the strongest contradiction;
- state why immediate entry may be inferior to waiting, when applicable;
- explain the stock's behaviour relative to theme/sector/index;
- avoid certainty language and price prediction;
- remain compact in beginner mode, with full evidence in Expert detail.

## 9. Learning contract

Persist the original analysis packet before risk criticism. After the horizon
matures, resolve each hypothesis independently:

- trigger occurred or never occurred;
- theoretical fill and slippage, if executable under the declared trigger;
- +1R/+2R/stop ordering;
- MFE, MAE and time to each event;
- expired, invalidated or unresolved;
- whether the setup read was correct even when execution was blocked;
- whether `NO_CLEAN_SETUP` missed a later qualifying opportunity.

Learning must update analogue retrieval and calibration by regime, setup family,
teacher lens, sector/theme and trigger state. It must not rewrite deterministic risk
law based on a single outcome.

## 10. Required implementation changes

1. Replace the current verdict-only LLM response schema with the analysis packet,
   retaining legacy fields only for migration.
2. Add a server join that validates proposed zones against causal price data and the
   existing risk-plan engine.
3. Persist observer output before scanner verdict and risk evidence are revealed.
4. Render the beginner Decision Card in section 5; move council mechanics below it.
5. Resolve outcomes for `TAKE`, `WATCH`, `SKIP`, gate-blocked and user-nominated ideas.
6. Keep parallel TradeTM, Manas/Strong Start/reversal and StocksGeeks/IPO hypotheses.

## 11. Acceptance tests

- A valid chart thesis survives as `GOOD_SETUP_BLOCKED_BY_RISK` when its stop is too
  wide; it is not converted to `NO_CLEAN_SETUP` or deleted.
- A recent IPO can be interpreted without a 200-session history requirement.
- Every displayed number has an as-of timestamp, timeframe, provenance and level kind.
- No LLM field can populate executable quantity, rupee risk or broker stop.
- Target-like structure is labelled estimated until the server validates it.
- ETA never uses wall-clock hours for a daily/weekly plan.
- The same point-in-time input produces the same joined execution state.
- Future bars and future outcomes are absent from observer prompts and memory retrieval.
- The UI can honestly render missing entry, stop, target, ETA, theme comparison or
  intraday coverage without blank cards or invented values.
- RAIN and STALLION remain binding missed-opportunity regression cases for discovery,
  independent observation and outcome learning.

## Risks

- A fluent narrative can still be wrong; structured causal evidence and later outcome
  resolution are mandatory.
- A structural chart level is not necessarily a safe executable stop or target.
- ETA cohorts will remain weak until enough point-in-time, path-dependent outcomes are
  resolved.
- A visible score can create false certainty; do not introduce `/100` until the
  versioned server rubric is calibrated.
