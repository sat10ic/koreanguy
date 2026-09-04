# HANDOFF — Risk & Trade Management Engine (the uncertainty layer)

**Date:** 2026-09-04 · **Author:** Claude Opus 5 (spec role; no code written by this doc)
**Source spec:** `risk_trade_management_engine_technical_spec_v1.md` (owner-supplied)
**Containment:** `HANDOFF_2026-09-04_STRUCTURAL_LEVELS_KDE.md` §10 governs every surface here

---

## 0 · Verdict

**Buildable, and it targets the tool's real gap.** The desk is currently a *selection*
instrument — regime → sector → candidate → trigger, all "what to trade". This spec supplies
the missing half: how much, when to leave, what happens when wrong.

Three facts that make it the highest-value spec received so far:

- The tool's **worst measured number is a risk number** — median `stop_thrust_days` 0.67.
- The owner's **audited leaks** are late entries, late exits, micro-sizing, over-trading.
  Three of four are risk and exit management.
- **No exit logic exists anywhere.** A grep for `trail`, `partial_exit`, `scale_out`,
  `move_stop`, `take_profit` returns only trailing *windows*, never a trailing *stop*.

## 1 · Governance: one charter amendment is required before any code

`traderlog/CANONICAL.md` states: *"LLM proposes, never decides. No model output may author
a stop, a size, or a risk number."* `UI_BUILD_SPEC_V1` X-03 goes further for the playbook:
*"this mapping never emits a number — no size, no rupee amount, no position count."*

**Read literally, X-03 blocks this entire engine.** It should not, and the source spec
resolves it correctly in §1.2 / §22.1:

- **A model authoring risk is forbidden.** `AI score → risk multiplier` stays FORBIDDEN.
- **Deterministic arithmetic is not a model.** `qty = floor(risk_budget / risk_per_share)`
  is a calculator, not a prediction.

**Required before R-1:** record a dated amendment stating that X-03 scopes to the
*regime→playbook mapping*, and that the Risk Desk may emit deterministic, auditable,
user-parameterised risk numbers — while §22.1's AI wall stays absolute. Do not proceed on
an implied reading; write it down.

## 2 · What already exists — more than expected

| Present | Where |
|---|---|
| Positions register, exit alarm (D-02), risk cap (D-05), over-trading (D-06) | `screens/Desk.tsx`, `lib/positions.ts` |
| Gross exposure, "loss if all stops hit" | `Desk.tsx:284` — the portfolio-heat primitive exists |
| Deterministic input guardrails (invalidation ≥ entry, size > capital, future-dated entry) | Desk register |
| Broker tradebook, **472 buy fills, with `side: BUY \| SELL`** | `lib/broker.ts`, `data/broker/trades.json` |
| Audited baseline (entries/week, same-day round trips, revenge re-entries, late-exit cost) | `broker.ts:38-46` — hand-entered, sourced |
| Per-session ADV (trailing-20 median of close×volume) | `archive_attach.py:69` — liquidity cap input, already computed |
| Stop-aware outcome labels, R-multiples, gap-through handling | `research/labels.py` |

Phases 1-2 are largely **wiring existing primitives**, not new construction.

## 3 · The one unlock: round-trip matching

**Everything in Phase 4 (Risk Lab) depends on one missing piece.** The broker import
carries both BUY and SELL fills, but nothing matches them into round trips —
`sameDayRoundTrips: 64` in `broker.ts` is a hand-entered audit constant, not a computation.
The Desk says so: *"per-bucket realised P&L needs round-trip matching that the fills import
does not provide yet."*

**This is buildable from data already on disk** — FIFO (or the broker's own convention,
stated explicitly) matching over the fills. It is not a data-acquisition problem.

It unlocks, in one step: realised R per trade · MAE/MFE (price paths come from the archive)
· capture ratio · drawdown decomposition · the stop simulator · the entire Risk Lab.

**Build it first.** Nothing else in Phase 4-7 is reachable without it.

## 4 · Do not build the stop simulator twice

Source §17.5 (counterfactual stop simulator) and §17.4 (winner-MAE vs your median stop) are
**the same experiment** as N-17 in `HANDOFF_2026-09-04_STRUCTURAL_LEVELS_KDE.md` §4, viewed
from the other side:

- N-17 asks: *would structural stops beat the current rule on the archive?*
- §17.5 asks: *would a different stop distance have beaten it on my own trades?*

Same machinery — counterfactual re-labelling under an alternative stop, using only
information available after entry. **Share the implementation.** And §32.4 restates the rule
that matters: *no future swing low may be used to decide a historical trailing stop*, and a
stopped trade that later rallies **stays stopped** unless a re-entry rule is explicitly
modelled.

§17.4's output is also the likely explanation of the 0.67 finding, in reverse: where the
source's trader found most winners never needed the full stop, this desk will probably find
winners stopped out by noise.

## 5 · Phase map, with blockers named

| Phase | Content | Blocked by |
|---|---|---|
| **P0** Freeze definitions | risk ontology, objective enums, stop-candidate types, policy config, **source-preset registry** | §1 amendment |
| **P1** Trade Planner | Trade Contract, stop candidates, risk-based size, position cap, open-risk cap, portfolio impact preview | — |
| **P2** Portfolio Heat | capital / profit / stress risk, sector & theme clusters, event exposure | market-rotation groups for theme clusters; **sector clusters work today** |
| **P3** Live Trade Manager | state machine, current stop, protection event, profit-at-risk, partials, tranches, pyramiding | P1 |
| **P4** Journal Calibration | MAE/MFE, capture ratio, stop simulator, drawdown decomposition | **§3 round-trip matching** |
| **P5** Risk Governor | drawdown policy, loss-cluster and follow-through feedback | P4 evidence; **manual-confirm only in v1** |
| **P6** Analogue integration | analogue MAE/MFE as *evidence only* | L1.5 evaluated (roadmap step 3) |
| **P7** Challenger research | dynamic risk variants, offline | experiment harness |

**Data not available, do not fake:** ASM/GSM flags (audit ⛔), broker MTF haircuts and
margin rules (owner must supply), spreads. Circuit bands come from E-3 in the event-track
handoff. Render `—` with the named gap, never a substituted value.

## 6 · Constraints that must survive implementation

1. **Source presets are presets.** §2.3's numbers (0.3-0.5%, 1.5-2%, 2-2.5% open risk, 40%
   position caps, 4R partials, 70% capture) ship as **editable, labelled
   `SOURCE_PRESET`** with source, period and strategy context. Never silent defaults, never
   "best practice".
2. **The Risk Governor is the only component that acts on the owner's behalf.** Keep it
   **manual-confirm in v1** — it proposes a state change with its deterministic reason, the
   owner accepts. §12.4's multipliers are explicitly "product proposals, not source rules".
3. **Never render certainty language** (§39.5): no "safe trade", "guaranteed stop",
   "risk-free position". Use `CAPITAL PROTECTED UNDER CURRENT STOP` — gap and liquidity
   risk remain.
4. **MTF sizing uses base equity, never equity + borrowed** (§10.1). And never display
   "MTF does not increase risk" unqualified (§10.4).
5. **Planned risk, stress risk, open risk and profit at risk are four distinct fields.**
   Never one number called "risk" (§1.3, §41.3).
6. **Show the binding constraint** (§9.2). "Final qty 2,240 ← liquidity cap binding" is the
   whole value of the constraint engine; a bare number is not.
7. **Sample-size honesty** (§17.3): under 20 → insufficient, 20-49 exploratory, 50-99 use
   with caution. The desk already attaches `n` everywhere — keep that.
8. **`Observation`, not instruction** (§17.4). The Risk Lab says *"most winners did not
   require the full stop room"*, never *"tighten your stop"*.
9. **Every risk-changing event is an immutable audit record** (§30), answering *"why did my
   risk change?"*

## 7 · Owner-gated

- The §1 charter amendment.
- Any default risk fraction, position cap, or open-risk ceiling — these are the owner's
  capital, not a spec's defaults.
- Enabling any automatic Risk Governor action.
- Broker/MTF parameters.
- §14.3's "you cannot keep all four" copy is a **trade-off explanation**, acceptable; any
  wording that recommends a choice is not — the owner writes that or it stays out.

## 8 · Sequencing

This competes with `HANDOFF_2026-09-04_MARKET_ROTATION_FULL.md`. Both are large.

Stated once, then it is the owner's call: **rotation improves selection; this improves
survival.** The tool's measurably worst number and three of four audited leaks sit on this
side. §3's round-trip matching is also the cheapest high-value item on either board — it is
one matching function over data already on disk, and it turns 472 dormant fills into the
evidence base for every calibration in Phase 4.

In the build graph (`BUILD_GRAPH_2026-09-04.md`) this slots as a new wave after the
experiment harness; P6 explicitly depends on L1.5 being evaluated, so it cannot jump ahead
of roadmap step 3 regardless.
