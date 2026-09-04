# HANDOFF — Breakout-follow-through "climate" throttle (Gemini)

Repo `C:\Users\satta\Downloads\koreanguy`, branch `emergent`. Standing rules: HANDOFF_INDEX.md.
This is **Tier-1 of `manas_os/design/BREADTH_ENRICHMENT_WAVE.md`** — read it; it defines the
replay-A/B-gate discipline this MUST follow (this one DOES touch the decision chain, so it is
gated, not silent).

## Why
"Choppy" = market-wide breakouts are FAILING. Every momentum trader's rule is "sit out when
breakouts stop working." We already compute the breakout sustained/failed ratio (BO-S/F) in
`manas_os/regime/breadth_analytics.py` (breadth Tier-0, live). It is NOT yet used to modulate
selectivity. Wire the market's own recent breakout-success-rate into the governor so the feed
auto-tightens in chop instead of the user guessing.

## Scope
1. **Climate metric** (new, in breadth_analytics or a small `regime/breakout_climate.py`, one
   writer): a smoothed market breakout-follow-through state from the existing BO-sustained /
   BO-failed history — e.g. 10-session mean of `bo_sf_ratio` + trend, mapped to
   `climate ∈ {HEALTHY, MIXED, HOSTILE}` with documented thresholds. Point-in-time. Persist it.
2. **SHADOW FIRST**: expose climate on the MARKET/regime payload as display + StatusBadge; do NOT
   change the governor yet. Show "breakout climate: HOSTILE — breakouts failing (BO S/F 0.7, 10-day
   falling)".
3. **Replay A/B gate (the gate to influence)**: using `manas_os/backtest/replay.py`, compare the
   existing governor vs a governor that tightens one notch (fewer max_cards / stricter families /
   smaller risk band per the LOCKED governor table) when climate=HOSTILE. Metrics: T+10 median_r
   of the passed cohort, cards/day within caps, drawdown of taken-cohort — HOSTILE-tightened must
   beat baseline out of sample. Log to `LEARNINGS.md`.
4. **Wire into governor ONLY IF the replay passes** (`regime/governor.py`): climate becomes a
   modifier on max_cards/selectivity — never a new money-math term, never overriding the locked
   regime table's hard caps (it can only tighten, never loosen). If replay fails, it stays
   display-only and you say so.
5. Tests: climate mapping on seeded BO-S/F fixtures; replay A/B harness runs; governor tighten-only
   invariant (climate can reduce but never increase max_cards / risk).

## Guardrails
Regime-law + money-math LOCKED: climate may only TIGHTEN selectivity, never loosen or change risk
math; must clear the replay gate before touching the governor (no silent decision-chain change —
that is exactly what the anti-mashup rules forbid). Point-in-time; additive. Failure-safe: a bad
climate calc must not break run-eod or the governor (fall back to the plain regime table).

## Output
`HANDOFF_GEMINI_breakout_climate_throttle_COMPLETED.md`: the climate definition + thresholds, the
replay A/B numbers (baseline vs tightened, honest), whether it earned the governor wire-in or
stayed display-only, LEARNINGS.md entry, tests.
