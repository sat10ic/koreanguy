# BREADTH ENRICHMENT WAVE — Market Breadth V2.0 datapoints → decision support

Planned 2026-07-11. Scope: take the richer breadth analytics reverse-engineered from
`Market Breadth V2.0.xlsm` beyond regime-panel DISPLAY and let them SUPPORT the other modules
(regime read, DEBATE context, scans/governor, exits) — via a **staged, validated** path, never a
silent rewire. Sources of truth: `manas_os/design/study/REVERSE_ENGINEERING.md` (verified formulas)
+ `manas_os/design/knowledge/MARKET_BREADTH_V2_REVERSE.md` (DB mapping HAVE/COMPUTE/NEW-DATA).

## Why this is separate from UI-3
UI-3 ships the breadth as **display only** in the regime panel (safe, no cascade). Feeding breadth
into DECISIONS touches the locked chain (`regime/snapshot.py` → `market_mode` → `gates.py`
ALLOWED_FAMILIES → candidates → debate → sizer). Regime-law + money-math are LOCKED, so each wiring
is its own validated change with evidence — not a UI side-effect.

## Guardrails (binding)
- **One breadth universe:** compute every new analytic from OUR `breadth_daily`/universe (same
  source XP/MBI use), NOT the Kedia manual clipboard dump. Two breadth universes that disagree =
  one-opinion violation (task #34). Reconcile overlaps: our MBI r4.5/r10/r20/r50 ALREADY are the
  Stockbee burst-ratio core — do not create a second "net breadth".
- **Reproduce workbook math, corrected:** honor REVERSE_ENGINEERING.md §12 (CHG% `/prev`, 52wk-low
  bands from the low). Note choices.
- **No silent gate change:** Tier-1/2 wiring requires a replay A/B showing the refined cohort beats
  baseline at T+10 (plan T1.6 discipline). Money-math/regime-law changes need a WAVE_L-style
  proposal + user sign-off + replay evidence.

## Step 0 — INGEST (prerequisite; ~26 NEW-DATA metrics)
Most workbook metrics need counts we don't store yet (volume>1.5x/<0.5x 20d, range <3%/>=5.01%,
close-upper/lower-half on expansion, breakouts/breakdowns + sustained/failure at 4%-from-prev-close,
15/25% moves over 5/20d, %-above-10/20/50/200-DEMA, 52wk NH/NL + distance bands). Add an EOD stage
computing these daily counts from our universe → new columns/table (additive, point-in-time). Also
populate the currently-EMPTY `regime_universe_metrics.new_highs/new_lows` (unlocks Net NH-NL +
Fosback HL-Logic-Index = min(NH%,NL%)*100). Tests: counts match the workbook definitions on a spot
date.

## Tier 0 — DEBATE context enrichment (low risk, do first after ingest)
Add the new analytics to the DEBATE run-card breadth CONTEXT (it already reads xp/mbi/r4p5/r10/r20/
r50 and cites `AR-Poor-Market-Signal`): BO-Sustained/Failure ratio (do breakouts follow through?),
Fosback HL-Logic-Index (internal conflict/transition), volatility ratio (choppy vs trending),
%-above-200-DEMA trend. This is CONTEXT for the council's reasoning, NOT a hard gate → no cascade.
Keep values identical to the regime panel (one-opinion).

## Tier 1 — regime-quality refinement (validate, then wire)
Feed regime-level breadth quality into the four-phase classifier / governor as a refinement:
- BO-Sustained-ratio → follow-through quality (Arora poor-market-signal, formalized).
- Fosback transition flag → distribution/transition posture.
- Volatility ratio → choppy-environment selectivity.
Gate: replay A/B (refined-regime cohort vs baseline, T+10 median_r + cards/day within caps) BEFORE
it influences what scans surface. Log to LEARNINGS.md.

## Tier 2 — locked (sign-off required)
Anything touching `market_mode` thresholds, gate pass/fail, `governor` risk bands / max-cards, or
sizing. WAVE_L-style proposal + replay evidence + explicit user sign-off. Do NOT touch without it.

## Sequence
Step 0 ingest → Tier 0 debate context → Tier 1 (replay-gated) → Tier 2 (sign-off). UI-3 ships the
display in parallel and does not block on this.
