# Manas OS — Next Steps (Opus synthesis; Fable subagent looped, so produced directly)

## Setups quality-candidate architecture (the crux — user point #4)

**Problem:** `/api/setups` ranks a raw symbol scan; quality gate (`universe_filter.py`)
built but unwired; ChartsMaze per-stock screener hits never ingested. Result: ETFs / bond
funds (LIQUIDBEES, GILT5BETA) at top.

**Fix — one new writer + a rewired feed:**

1. **Ingest screener hits (new source, one writer):** `manas_os/sources/chartsmaze_scanners.py`
   → new table `screener_hits(trade_date, symbol, screener, market_cap_cr, basic_industry)`
   from the 26 `scanners/*.csv` in the latest ChartsMaze dump. Register in run-eod after
   `ingest_chartsmaze`. Anti-mashup: single writer, one metric (screener membership).
   - Bonus columns: `Market Cap` (fills the gate's skipped mcap check) + `Basic Industry`.

2. **Rewire `/api/setups` → quality-ranked, explainable feed:**
   - HARD filter: `universe_filter.filter_universe` (now with real mcap from screener_hits)
     drops ETFs / <₹30 / <₹5cr turnover / <₹1000cr mcap / circuit-locked.
   - RANK by: `confluence` = COUNT(distinct screener per symbol) **+** trending-theme boost
     (symbol's industry in top-quartile sector RS) **+** Tier-1 price-action trigger
     (`price_action.signals_for_symbol`) **+** delivery%.
   - Require `confluence ≥ 2` (a real setup prints in multiple screens; a pump-dump micro
     usually shows only in top-gainers/volume-spike) — the pragmatic quality proxy.
   - Each card = evidence chips: which screeners ("VCP + tight + momentum = 3"), theme
     ("Capital Goods, RS top-quartile"), gate PASS, price-action signal. No black box.

3. **SME / bad-fundamental exclusion — HONEST GAP:** NSE SME series (≠ EQ) already dropped by
   the gate. Beyond that we have NO balance-sheet/fundamental data. "Shady SME with bad
   fundamentals" is approximated by: mcap floor + circuit-revision membership + confluence≥2.
   A true fundamental screen needs a data source we don't have — flag to user, don't fake it.

## Sequencing

- **Quick wins (parallel, low risk):** T15 sector/theme perf-flip (data in industry_metrics),
  T16 indices perf-flip (sector_index_prices, 1428 rows). Frontend + light API.
- **Core value chain (sequential — this is the product):**
  1. Ingest `screener_hits` (unblocks confluence).
  2. Rewire `/api/setups` = gate + confluence + theme (T5) → trustworthy feed.
  3. T11 chart depth: full ~400-bar history (stage computes), label every overlay + the
     pocket-pivot dot, entry arrows on triggers, exit arrow once journaled.
  4. T6 watchlist + position sizer, T7 journal → close the loop.
  5. T14 home: color-state + top-3-5 setups (needs T5 feed); T13 auto-update-to-latest.

## Gaps / risks
- No fundamental data → SME-quality is a proxy, not a real screen (see #3).
- ChartsMaze dumps are dated folders (fresh 07-05) vs bhavcopy/regime 07-03 — both recent, fine.
- Per-stock RS coverage = ChartsMaze universe (not all EQ names have RS).
- Screener freshness depends on the daily ChartsMaze extractor running (tie to staleness state).
