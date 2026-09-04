# Stocksgeeks — "Consistency in Stock Swing Combinations" (article, user-shared 2026-07-17)

Source: stocksgeeks article + 5 marked charts (WOCKPHARMA/NETWEB/PARAS/ASTRAMICRO/KIRLPNU) +
Trading System Part 3 video (youtu.be/_OEjobCmsdU). Methodology backbone rank #3
(TradeTM > Arora > Stocksgeeks). Context: traders missed the defence rally by hopping
combinations; his edge = ONE fixed combination, traded with nuance, sized by trump-card.

## The 4 factor categories → our tool (engineering map)

| Factor | Meaning | Our state |
|---|---|---|
| **X-Factor: Sector** | leading sector/industry tailwind | PARTIAL — ChartsMaze RS + industry_metrics exist; industry-first hero (N.E.X.T wave) pending |
| **X-Factor: EP** | episodic pivot catalyst | HAVE — EP detector + earnings wave in flight |
| **X-Factor: High RS** | RS floor ("automatic — I trade only Upbase") | HAVE — RS gate/chips |
| **X-Factor: HVE/HVY** | Highest Volume Event/Year zones | GAP — we score delivery_z/volume spikes but no explicit HVE/HVY marker + zone memory |
| **X-Factor: IPO** | recent listing | HAVE — ipo_base + listing universe |
| **Nature: Thrust Power** | strength of impulse legs (MANDATORY for him) | GAP — no explicit thrust metric (≈ big up-day ratio in leg / our 4.5R-style burst per stock) |
| **Nature: Linearity** | clean low-chop trend | GAP — computable (pullback depth vs ADR, up-day consistency) |
| **Nature: Pivot Cutter** | stock's HISTORY of slicing through pivots vs respecting them | GAP — novel + computable from our own breakout-age/outcome data |
| **Base: Area of Interest** | prior HVE/support confluence under the base | PARTIAL — overhead-supply gate + AVWAP anchors approximate it |
| **Base: Strong Volume Activity** | accumulation signature (MANDATORY) | HAVE — delivery_z, volume footprint, ANTS |
| **Readiness: Pattern** | flag/base/etc (MANDATORY) | HAVE — detectors |
| **Readiness: Pivot Level** | clean pivot, avoid "ultra cheat areas" (too-early deep-in-base entries) | PARTIAL — pivot exists; cheat-area classification missing |

## His combination (verbatim logic)
Sector/EP/IPO (≥1, more is better) + High RS + High Thrust Power (mandatory) +
Linearity/Pivot-Cutter-clean (≥1, pref 2) + Upbase (mandatory) + Strong Volume Activity
(mandatory) + Pattern (mandatory) + clean Pivot Level (no ultra-cheat).

## Nuances (the avoid-list — REAL negative controls, dated)
- Straight-up **3rd flag** → avoid (THERMAX 18-Jun-2026). Flag-COUNT within a leg is countable.
- **Choke / low-liquidity** setups (AYE 25-May & 2-Jun, SKMEGG 16-Jun) → we already refuse (liquidity gate ✓).
- **Multi-year-base multi-hit** (MIDHANI) → pivot hit-count metric, computable.
- **Tilted flag** (RUBICON 15-Jun-2026) → flag-slope check, computable.
- Dirty bases get FASTER SL; cleaner bases get room → per-combination trade management (coach hook).

## Trump card ("parabolic movers" — where he sizes UP)
High Liquidity + High Thrust + Great Linearity + Strong Volume + EP/Strong Sector →
hold longer + pyramid (Swing/Spurt/Recursion) for impact. Maps to: an explicit
**parabolic-mover tag** on A+ candidates gating pyramiding coach + longer trail mode.
Classic case: defence stocks (the current leading-sector rally).

## Market gate — the validation of our architecture
"99% I trade only when **EM > 15**" (rarely ≥12 for exceptional setups). EM = the same
market-energy dial family as our XP. This is EXACTLY our regime-governor design — third
independent practitioner confirming regime-first. Action: calibrate/display an XP threshold
band equivalent to his EM 12/15 lines (offline calibration when EM sheet is shared; until
then document XP percentile bands that match "tradeable vs sit-out").

## Backtest cohort (12 recent impact winners, all same combination)
WOCKPHARMA · NETWEB · PARAS · ASTRAMICRO · KIRLPNU (charted, approx entries in
practitioner_picks.csv) + CMPDI · AEROFLEX · BAJAJCON · CEMPRO · DATAPATTNS · PREMEXPL
(symbol unresolved on NSE — verify) · DREDGECORP (no chart dates). Defence theme central.

## Derived backlog (in priority order, all replay-validatable)
1. **Thrust Power metric** (impulse-leg strength: up-day dominance + leg gain/ADR) — his ONLY
   universal mandatory we lack; also feeds the parabolic-mover tag.
2. **Linearity metric** (chop-free trend score) — pairs with thrust; both are rank tiebreak
   candidates, gates only after replay proves them.
3. **Flag-count + tilted-flag + pivot-hit-count** classifiers → avoid-chips (not hard gates;
   the coach carries the con — "3rd flag of this leg; he'd skip or tighten SL").
4. **HVE/HVY zone memory** (highest-volume event/year marks → area-of-interest confluence
   under bases; upgrades overhead-supply/AVWAP layer).
5. **Parabolic-mover tag** + per-combination management style in the coach (faster SL on dirty
   bases, room + pyramiding steps on trump-card names).
6. **XP↔EM band calibration** on the regime page (display: "his EM>15 ≈ our XP > ~N").
Validation: replay the 12 winners' entry windows — the combination scorer must rank them
top-decile on their entry days; THERMAX/RUBICON/MIDHANI must trip their avoid-chips on the
cited dates.
