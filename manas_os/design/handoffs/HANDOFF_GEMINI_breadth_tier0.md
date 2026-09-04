# HANDOFF 1 — Breadth Tier 0: live panels + debate context (Gemini)

Repo `C:\Users\satta\Downloads\koreanguy`, branch `emergent`. Standing rules: see HANDOFF_INDEX.md.

## Context
`breadth_counts` (38 daily count metrics, 85+ sessions backfilled) and `regime/breadth_analytics.py`
(net NH-NL, Fosback HL-Logic-Index, volatility/volume ratios, BO/BD S/F ratios, distance bands,
`summary()`) are LIVE in the DB. Two consumers still don't use them. Governing docs:
`manas_os/design/BREADTH_ENRICHMENT_WAVE.md` (Tier 0 = council CONTEXT, never a gate) and
`manas_os/design/ALPHA_LEARNING_CONSTRAINTS.md`.

## Scope
1. **API**: extend `api/app.py`'s `/api/regime/breadth-analytics` (or add fields beside it) to
   expose the `regime/breadth_analytics.py` series/summary (NH-NL, Fosback, volatility ratio,
   volume ratio, BO/BD S/F, distance bands). One writer: all computation stays in
   `breadth_analytics.py`; app.py only reads/serializes. Honest `{available:false}` pre-backfill dates.
2. **MARKET panel**: in `desk/src/MarketHomeTab.jsx`, replace the "NEEDS INGEST" placeholder
   cards (NH-NL / Fosback / volatility / BO-S-F) with real plain-SVG trend panels off the new
   fields, matching the existing breadth-panel idiom (threshold bands, mono numerals, titled "—").
   Keep panels that still lack data as honest placeholders.
3. **DEBATE context (Tier 0)**: in `agents/context_pack.py` (or wherever the debate context/
   run-card breadth block is assembled — grep `r4p5` in agents/), append a compact
   `breadth_quality` block: BO-sustained/failure ratio + trend, Fosback value + 10d trend,
   volatility ratio, %-above-200DEMA — labelled as CONTEXT with one plain-English line each
   (e.g. "breakouts are following through (S/F 1.22)" / "both NH and NL elevated — internally
   conflicted tape"). It must NOT change any gate/verdict logic — prompt context only. Values
   must be IDENTICAL to what the MARKET panel shows (one-opinion).
4. **Tests**: API field test (seeded rows); context-pack test asserting the block appears and
   matches breadth_analytics output; MARKET vitest-safe (pure helpers if any).

## Do NOT
Touch regime/snapshot.py, market_mode, scanner/gates.py, sizer, or any threshold. No client-side
derivation of the analytics.

## Output
`HANDOFF_GEMINI_breadth_tier0_COMPLETED.md` per standing rules, incl. curl proof of the new
fields and a DOM note that MARKET's former needs-ingest cards now render real values.
