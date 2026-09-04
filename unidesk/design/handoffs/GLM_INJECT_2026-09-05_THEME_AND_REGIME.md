# INJECTION 2 — theme spec + chop/bear regime engine (paste into the running loop)

**Do not restart the loop. Do not re-plan the graph. Finish the node you are on, record it
normally, then apply this at your next step 1.**

Supersedes nothing in `GLM_INJECT_2026-09-05_OUTCOME_WAVE.md` — that injection still stands.

---

## 0 · Already done for you — do not redo

- `BUILD_GRAPH_2026-09-04.md` gained **§11 (Addendum 4)** and **§12 (Addendum 5)**.
- `BUILD_STATE.json` now holds **99 nodes**. N-69..N-78 and N-80..N-95 are registered `TODO`.
- **N-61, N-64 and N-67 have amended notes.** Read them — the N-64 amendment is a correctness
  fix, not a nicety.
- Both specs are vendored: `unidesk/design/reviews/sector_theme_linkage_cross_product_technical_spec.md`
  and `unidesk/design/reviews/momentum_os_chop_bear_regime_setup_engine_technical_spec_v1.md`.
  §-numbers in §11/§12 refer to those files.
- **Do not renumber. Do not touch existing node ids.**

## 1 · Addendum 4 enlarges the theme wave — it does NOT start a second one

N-61..N-68 keep their ids and meaning. N-69..N-78 add what Addendum 3 did not cover. **If you
find yourself building a second theme system beside the first, stop — you have misread this.**

**The one correctness fix, on N-64:** theme membership becomes **temporal** — every record
carries `effective_from`, `effective_to`, `available_at` (spec §87-88). Without it, backfilling
today's "AI/Datacenter" membership onto 2024 dates is textbook lookahead and would silently
corrupt N-67's verdict. Addendum 3 missed this.

Two more amendments, in the node notes: N-61's ≥5 floor is spec §69's `LOW_SAMPLE` rule (same
implementation as N-54 — build it once); N-67 validates **per setup family**, and an EP is
never penalised for missing peer confirmation (§16, §102.9).

Already covered elsewhere, do not duplicate: §64-§67 → N-56/N-57 · §68 → N-53 · §95 → N-54 ·
§82-§84 → N-58 · §72 → N-64(b).

## 2 · Addendum 5 — three measured facts invert the spec's own build order

I verified these against the last 10 reports and `tonight_2026-09-03.json`. **The spec does not
know them, and its Phase 0 is blocked by a node it never lists.**

1. **Regime is `breadth_only`.** The footer literally reads
   `regime_note=CHOP (breadth 55.4% above EMA50, breadth_only)` — one input against ~30 in
   spec §6, and four flat states against the spec's 13 substates.
2. **Historical regime states do not exist.** The footer says
   `HISTORICAL 30-day backfill: CHOP/BULL/BEAR not persisted per day`. So spec §102's Phase 0
   regime audit — *"measure existing setup performance by regime"* — **cannot run at all**
   until N-82 reconstructs regime point-in-time.
3. **The tradeability gate has no data.** `contracts/candidate.py:94-95` already declares
   `circuit_risk_state` and `surveillance_flags`; the report emits them on **0 of 62 rows**,
   and `stock_quality.unknowns` already carries `CIRCUIT_BANDS_NOT_PUBLISHED`. Spec §78-§80 is
   an **ingestion problem (N-84) before it is a logic problem (N-85)**.

**Therefore the order is N-80 → N-81 → N-82 → N-83, and N-83 decides whether N-86..N-95 are
worth building at all.** Do not implement six detectors first. If ordinary breakouts do not
measurably degrade in chop on this dataset, most of Addendum 5 is unjustified — **that is a
legitimate outcome and you must record it rather than build around it.**

Two more facts worth having: **`reversal_reclaim` already exists** (12 occurrences over 10
sessions) — N-86 extends it, never duplicates it. And the detector mix is **471 of 643
`inside_bar` (73%)** — the eight-family spread is one detector plus tails.

## 3 · Priority — where this sits against everything else

The Addendum 2 override still holds and still comes first:

```
current node  ->  N-50, N-51  ->  N-52  ->  then normal queue order
```

Addendum 4 and 5 do **not** jump that queue. Within them the internal order is fixed:
`N-80 → N-81 → N-82 → N-83` gates all of Addendum 5, and N-61 gates all of Addendum 4.

## 4 · New escalations — append to §4

| # | Decision | Why it is not yours |
|---|---|---|
| E11 | Enabling **any** short-side setup, even in a lab | no execution route exists; the product is manual-execution cash-long |
| E12 | Freezing regime **substate thresholds** after seeing per-substate performance | fitting the regime definition to the result — same failure as E8 |
| E13 | Promoting a CHOP or BEAR family into the default candidate feed | needs N-83 plus its own validation; E6 applies |

**E10 (theme membership) still stands** — you may build the schema, loader, maths and
clustering *proposals*; the owner authors the list.

## 5 · Explicitly not built

- **The short module** (spec §51-§55, Part III). §101 gates it on an eligible universe,
  borrow/F&O route, modelled costs, gap risk and broker execution — none exist. It also
  contradicts the standing manual-execution-only rule. Do not build, do not surface.
- **Intraday families** (§30-§31, §106) — the order-flow wave is last by owner directive.
- **Generic oversold triggers** (§33): `RSI<30`, "down 10% this week", lower-Bollinger touch,
  three red candles. The spec bans them and so does §2.4.

## 6 · The traps in this pair

- **Do not weaken quality thresholds until breakouts pass again** (spec §0). That is the exact
  failure this wave exists to prevent.
- **Mean reversion is not "buy the losers."** Spec §3.1 and §84: the academic reversal effect
  is strongest in precisely the illiquid bucket where circuits, GSM and slippage make it
  untradeable. Quality reversion only, with `random recent losers` kept as the control cohort.
- **Provenance tags `[M]/[R]/[P]` are mandatory** (§1). Never attribute our own synthesis to a
  named trader.
- **A router that always finds something is broken** (§34). `NO TRADE` and `CASH` are valid
  outputs.
- **Never use today's ASM/GSM status on a historical date** (§89).
- **§97 density rule**: one compact secondary line per candidate row, metrics in tooltip. Not
  a panel per stock. Theme context must not turn every row into a paragraph.
- **A breadth or density percentage is never displayable without its denominator** (§12, §93).
- **No single universal score** (§61). A 90/100 breakout in a regime that does not pay
  breakouts is the `setup_quality = 100` degeneracy in a new place.

## 7 · Then

Resume §1 step 1. Report per §6. Standing rules §2.1-§2.7 apply to every node here; §2.3
(truncation REGISTRY) and §2.5 (no dormant code) are the two this pair will tempt you to skip
— `rotation.json` is already 351 KB of shipped code with zero consumers, which is how §2.5
gets violated in practice.
