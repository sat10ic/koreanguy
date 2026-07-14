# HANDOFF — DII / domestic-absorption footprint (Gemini)

Repo `C:\Users\satta\Downloads\koreanguy`, branch `emergent`. Standing rules: HANDOFF_INDEX.md.
SHADOW/display, direction-neutral, honest lag labels. Read `ALPHA_LEARNING_CONSTRAINTS.md`.

## Why + HONESTY FRAME (binding)
Current tape: FIIs net-selling, DIIs absorbing. Per-stock DII presence is NOT directly observable
without paid institutional data. This handoff builds the three legitimate PROXIES — each clearly
labelled as lagged/inferential, never stated as fact ("DIIs are buying X"). We already ingest
AGGREGATE FII/DII cash only (`sources/fii_dii.py` → `fii_dii_daily`); no per-stock, no MF holdings
(verified). Build, in priority order:

## Scope
1. **FII/DII divergence overlay (do first — data already here).** From `fii_dii_daily`: compute
   and expose a regime-context field `flow_divergence` (FII net vs DII net; classify days as
   FII-sell/DII-buy, both-buy, both-sell, etc.) + a short trend. Surface on the MARKET/regime
   payload as display ("FII net -Rs X cr, DII net +Rs Y cr — domestic absorption, 6th day"). This
   changes how index weakness is read; it is CONTEXT, not a gate.
2. **Resilience-under-distribution (conditional RS from data we have).** New feature
   (in `alpha/leadership.py` if that handoff landed, else a new module): on heavy-FII-sell days
   (index down materially, from `nse_indices` + the divergence classifier), flag stocks that HELD
   UP (positive/flat return) AND on high delivery% (`daily_prices` delivery fields) → candidate
   `domestic_absorption` evidence. Point-in-time; a per-(as_of,symbol) evidence chip
   "held up + high delivery on an FII-sell day (Nx in last 10)". Direction-neutral evidence, not a
   gate. Overlaps conceptually with the SMF avg-trade-qty signal — cite it, don't duplicate the math.
3. **Monthly MF-holdings ingest (staged — needs a real source).** Mutual funds disclose month-end
   portfolios (~10-15 day lag), more granular than quarterly shareholding. FIRST verify an
   accessible source (AMFI monthly portfolio disclosures / fund factsheet CSVs — check what's
   fetchable without auth; the repo's `sources/` pattern is the template). IF a real source exists:
   ingest → `mf_holdings(month, symbol, fund/aggregate, holding_value, shares, delta_vs_prior)`
   → per-stock DII-accumulation trend (MoM holding delta) as a lagged evidence chip. IF no clean
   free source: DO NOT scrape something unreliable — deliver items 1-2, and REPORT exactly what the
   MF source would require (URL pattern, format, lag) so the maintainer decides. Never fabricate.
4. **Validation for anything beyond display.** The resilience/absorption feature, if it is ever to
   tilt rank, must pass `alpha/promotion_gates.py` (does "absorption-flagged" beat baseline at T+10,
   cost-aware, walk-forward). Until then it's evidence-only. State the verdict if you run it.
5. Tests: divergence classifier on seeded fii_dii rows; resilience flag on a fixture (FII-sell day
   + a stock holding up on high delivery); MF ingest parser (if built) on a fixture; point-in-time.

## Guardrails
Everything shadow/display + direction-neutral + honestly lag-labelled. Not imported by
gates/sizer/ranking/verdict. Point-in-time (MF month M usable only after its disclosure date).
No money-math touch. No unreliable scraping — flag-and-stop if the MF source isn't clean.

## Output
`HANDOFF_GEMINI_dii_footprint_COMPLETED.md`: the divergence field + example on live data, the
resilience-under-distribution feature + a real current example, the MF-source finding (built, or
the exact acquisition spec if not), any promotion-gate verdict, grep proof of no live influence, tests.
