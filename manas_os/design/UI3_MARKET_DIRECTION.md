# UI-3 MARKET — build direction (regime panel, user-locked composition)

Date 2026-07-11. Slice UI-3 of `UI_OVERHAUL_HANDOFF.md` §11. Design language = locked v5 LIGHT
(`tokens.v5.css`, round-4). Real data only, plain SVG (no chart libs), one-writer-for-risk,
honest NO_TRADE/0-actionable, keep freshness/stale/offline warnings, a11y AA, reduced-motion.

Target file: `manas_os/desk/src/MarketHomeTab.jsx` (v5 rebuild; keep route/props). New layout CSS
`MarketHomeTab.v5.css` (`.v5`-scoped, tokens only). Compose the Wave-1 v5 primitives; new
sub-components only where a primitive is missing (define them in-tab, scoped).

## Composition (top → bottom) — USER LOCKED
1. **Regime headline** — verdict/stance + four-phase path + the ONE question "Can I take risk
   today, and where?" (verdict/action before metrics). Keep the existing stance/verdict/law text
   (server values). This stays the top read.
2. **XP + MBI — trend charts AND current values** (the headline enrichment the user asked for):
   - XP: a medium/short-term trend line with regime band rects + the current XP number.
   - MBI: day-color ribbon + burst-ratio (r4.5 / r10 / r20 / r50) trend + current values +
     warning-day flag (red_count≥3).
   - Source: `regime_snapshots` ALREADY persists XP + MBI daily — read back, do NOT recompute.
     Backend add: `GET /api/regime/history?from=&to=` returning the daily series (date, xp,
     mbi_day_color, r4p5, r10, r20, r50, warning_day, market_mode). (First verify whether a
     regime-history / breadth-history endpoint already exists — task #8 touched breadth-history;
     extend it rather than duplicate.)
3. **Market Breadth V2.0 panels — BENEATH XP/MBI** (Stockbee framework, complementary; the user's
   "add all the datapoints/analytics/visualizations"). Read the two VERIFIED specs and tag each
   element HAVE / COMPUTE / NEW-DATA:
   - `manas_os/design/study/REVERSE_ENGINEERING.md` — faithful workbook formulas (verified correct
     to the digit; use its "must-reproduce" math + honor its quirk decisions).
   - `manas_os/design/knowledge/MARKET_BREADTH_V2_REVERSE.md` — the Manas DB mapping + panel
     shortlist (~8 HAVE / ~6 COMPUTE / ~26 NEW-DATA).
   BUILD NOW (HAVE + COMPUTE): net breadth, 5/10-day AD ratios, % above 10/20/50/200 DEMA trend,
   52wk structure (NH-NL, 15%-from-H/L), volume ratio, volatility ratio, BO/BD S/F ratios where
   the inputs exist. Each as a plain-SVG trend/ratio panel with the workbook's threshold bands.
   STAGE (NEW-DATA — clearly labelled "needs ingest", NOT faked): the volume/range/breakout-failure
   count families, and populating the currently-EMPTY `regime_universe_metrics.new_highs/new_lows`
   which unlock Net NH-NL + the Fosback HL-Logic-Index = min(NH%,NL%)·100 (workbook flagship).
   Money-math rules: reproduce the workbook math faithfully; where the workbook has a documented
   quirk (SBE CHG% `/current` not `/prev`; Version-History "from 52 Week High" typo on the
   low-distance bands) follow REVERSE_ENGINEERING.md §12 "must-decide" — default to the CORRECTED
   behavior (`/prev`, from-low) and note the choice; never silently reproduce a bug.
4. **Sectors / Themes — KEEP the existing section** (sector RS + 1D/1W/1M/3M/6M returns). User wants
   it retained; it does NOT conflict with the workbook's sector 5-day ROC (different window/source).
   Only add the breadth sector 5-day ROC if non-duplicative; otherwise leave as-is.
5. **Opportunity map** — which mechanisms are rewarded NOW (not just allowed-family text), + the
   237→0 funnel as SUPPORTING evidence (not hero) + ONE primary action (review most relevant scan).
6. **Live Work inspector** — mount the UI-2 `livework/LiveWorkInspector.jsx` (via `useJobStream`,
   `/api/jobs/{id}/events/stream`) as the right-side inspector, REPLACING the placeholder Activity
   Log + one-shot PipelineProgress. Keep last-confirmed data visible (no full-surface Loading).

## BACKEND ADDITIONS (single-writer app.py; define the contract before coding)
- `GET /api/regime/history?from=&to=` — daily XP + MBI series from `regime_snapshots` (read-back).
- Breadth COMPUTE analytics: extend the market/regime payload (or a `GET /api/regime/breadth`
  endpoint) with the HAVE+COMPUTE Stockbee metrics as time series (net breadth, AD 5/10-day,
  %-above-DEMA, NH-NL, ratios) computed from `breadth_daily` / existing tables — one writer, no
  client-side derivation. Every graphed number must exist in a payload.
- (Staged) populate `regime_universe_metrics.new_highs/new_lows` ingest → unlocks NH-NL + Fosback.
  Label these panels "needs ingest" until wired; do not fabricate.

## BUILD SUB-SLICES (Codex-sized; one at a time; QC gate each per §7)
- **3a** — backend `GET /api/regime/history` + the breadth COMPUTE payload + tests; curl-proof the
  series is real. (No UI yet.)
- **3b** — MARKET v5 rebuild: regime headline + XP/MBI trend charts+values (consuming 3a) +
  keep Sectors/Themes + opportunity map + funnel-as-support.
- **3c** — Market Breadth V2.0 panels beneath (HAVE+COMPUTE built; NEW-DATA labelled) + Live Work
  inspector wiring (replace placeholder activity log).

## ACCEPTANCE / QC
- `python -m pytest manas_os/tests -q` (only known sector-downside fail allowed) + new endpoint
  tests; `npm run build` clean + vitest; API restart + curl-prove `/api/regime/history` and the
  breadth payload return REAL series; DOM-check MARKET renders XP/MBI trends + values on 2026-07-10.
- Every value real (entirety review): XP/MBI trends match `regime_snapshots`; breadth numbers match
  the workbook math on a spot date; NO_TRADE/0-actionable still an honest valid answer; funnel is
  supporting not hero; no synthetic series; a11y AA (contrast, focus-visible, non-color-only, titled
  "—" nulls, reduced-motion on the ribbons/lines).
