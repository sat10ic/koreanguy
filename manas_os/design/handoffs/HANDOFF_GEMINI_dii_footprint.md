# HANDOFF — EARLY accumulation footprint (pre-breakout institutional lead) (Gemini)

Repo `C:\Users\satta\Downloads\koreanguy`, branch `emergent`. Standing rules: HANDOFF_INDEX.md.
SHADOW/evidence, direction-neutral, honest. Read `ALPHA_LEARNING_CONSTRAINTS.md`.

## Reframed goal (user steer 2026-07-14)
Arora's edge = spot institutional accumulation EARLY (in the quiet base, BEFORE the breakout) to
ride the whole move. Therefore MF/quarterly disclosures are LATE CONFIRMATION, not a lead —
demoted below. We need signals with ~0 lag from EOD data we already ingest. Verified gaps:
`ants_accumulation` fires only AFTER a ~15% move (post-move, not early); bulk/block/insider are
used only DEFENSIVELY (pump-exclusion in gates.py), never as a positive lead; no F&O open-interest
at all (only an `is_fno` flag). Build the early leads, in priority order.

## Scope
### 1. QUIET pre-move accumulation detector (the earliest EOD lead — do first)
New `manas_os/engine/quiet_accumulation.py` (pure, point-in-time). Detect the Wyckoff/absorption
footprint that PRECEDES a move, distinct from ANTS (which needs the move to have happened):
- price still RANGE-BOUND / in a tight base (low ADR-normalized range over N bars, not yet broken
  out — reuse tightness/RMV helpers), WHILE
- `delivery_z` elevated and RISING over the window (institutions taking delivery, not churning), AND
- **absorption-on-weakness**: on down/flat sessions in the base, delivery% stays high / volume
  doesn't dry on the down days (supply being absorbed quietly), AND
- volume character: contraction then pockets of above-avg delivery volume (pocket-pivot-like) WITHIN
  the base.
Emit `{quiet_accum: bool, strength, evidence[]}` per (as_of, symbol). This is a WATCHLIST lead
(pre-breakout), surfaced as an evidence chip "quiet accumulation — delivery rising in a tight base",
NOT an entry and NOT a gate. Feeds the pre-breakout watch, so the user is early when the breakout comes.

### 2. F&O open-interest buildup (NEW DATA — early institutional positioning, ~0 extra lag)
NSE publishes the **F&O bhavcopy daily** (same cadence as cash) with per-contract open interest.
- FIRST verify the fetchable source (NSE F&O bhavcopy / `fo` UDiFF file — check the pattern the
  existing `sources/bhavcopy.py` uses; if a clean file exists, ingest it; if not, report the exact
  source spec and STOP — no unreliable scraping).
- Ingest per-underlying aggregate OI (futures + near options) → `fno_oi_daily(trade_date, symbol,
  oi, oi_chg, ...)`. Compute the classic states from price + OI: **long buildup** (price↑ + OI↑),
  short buildup (price↓ + OI↑), short covering (price↑ + OI↓), long unwinding (price↓ + OI↓).
- Long-buildup on an F&O name in/near a base = early institutional positioning → evidence chip.
  F&O names only; cash names get nothing here (honest).

### 3. Bulk/block/insider/promoter buying as a POSITIVE early footprint (rewire, not re-ingest)
We already ingest disclosures (used only for pump-exclusion). Add a POSITIVE read: a recent bulk/
block deal on the BUY side, or promoter/insider/director purchase, or an order-win, in/near a base
= a named, same-day, hard institutional footprint → evidence chip "block-deal buy 2d ago" /
"insider buy". Direction-neutral labelling of the fact; do NOT assert intent. Keep the existing
defensive pump use intact.

### 4. FII/DII divergence overlay (context, from data we have — keep)
From `fii_dii_daily`: expose `flow_divergence` (FII net vs DII net; classify FII-sell/DII-buy etc.)
on the MARKET/regime payload as display context ("FIIs selling, DIIs absorbing, 6th day"). Context,
not a gate.

### 5. MF-monthly holdings — DEMOTED to LATE CONFIRMATION (optional, do last / skip if no clean source)
Only as a lagged confirmation chip on names ALREADY flagged early by 1-3 ("DIIs added MoM, per last
disclosure — lagged"). NOT a lead. If no clean free source, skip and report the spec.

## Validation (gate to any influence beyond display)
The quiet-accumulation + OI-buildup features, to ever tilt rank/watch-priority, must pass
`alpha/promotion_gates.py`: does "quiet-accum flag" (or "long-buildup") at T0 beat baseline forward
returns to the eventual breakout / T+10/T+20, walk-forward, cost-aware, vs a delivery_z/RVOL
baseline? Until then, evidence-only.

## Guardrails
Everything shadow/evidence + direction-neutral; not imported by gates/sizer/ranking/verdict
(grep-prove). Point-in-time (only data <= as_of; F&O month/day usable only after publish). No
money-math touch. Additive DB only. No unreliable scraping — flag-and-stop if a source isn't clean.

## Output
`HANDOFF_GEMINI_dii_footprint_COMPLETED.md`: the quiet-accumulation contract + a REAL current
example (a basing name with rising delivery), the F&O-OI source finding (ingested or exact spec) +
long-buildup example, the positive-disclosure rewire, the divergence field, promotion-gate verdict
if run, grep proof of no live influence, tests (fixtures for quiet-accum, OI states, absorption-on-
weakness, point-in-time).
