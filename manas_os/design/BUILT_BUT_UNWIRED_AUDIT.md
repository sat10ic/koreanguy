# BUILT-BUT-UNWIRED AUDIT — manas_os desk

Read-only audit. Repo `C:\Users\satta\Downloads\koreanguy`, branch `emergent`, snapshot taken while
two other agents were actively editing the tree (confirmed live: `api.js` gained
`fetchFyersStatus`/`fetchFyersAuthUrl`/`exchangeFyersAuthCode` and `App.jsx` gained a
`FyersConnectionCard` mid-audit — treat any FYERS-related line item below as a moving target,
verified as of the moment it was checked, not a static fact).

Method: enumerated every `@app.*` route in `manas_os/api/app.py` (line numbers below), then for
each traced endpoint → `api.js` helper (if any) → import site → whether the importing component is
mounted in `App.jsx`'s tab set and actually renders the data (not just fetches-and-drops). Cross-
checked the 21 `*_COMPLETED.md` handoffs in `manas_os/design/handoffs/`.

## Legend
- **WIRED** — backend + frontend, mounted & rendered, user can see/use it today.
- **PARTIAL** — backend done, `api.js` helper exists and is called, but the calling component is not
  mounted in `App.jsx` (dead component), OR the helper exists but is never called anywhere (dead helper).
- **ORPHAN** — backend endpoint exists, zero frontend reference of any kind (no helper, no raw
  `fetch()`, nothing).

---

## (A) Summary table

| Feature | Backend endpoint/module | Frontend status | Should surface in | Smallest wiring step |
|---|---|---|---|---|
| SMF / activity leaders | `GET /api/alpha/activity` (app.py:3792) | **WIRED** | ALPHA tab | none — `fetchAlphaActivity` used in `AlphaLab.jsx:100`, rendered as "UNUSUAL PARTICIPATION" panel. Only reachable in **expert mode** (ALPHA tab hidden from beginner nav, `App.jsx:778`). |
| Per-symbol activity trail | `GET /api/alpha/activity/{symbol}` (app.py:3819) | **WIRED** | DEBATE (symbol card), TRADE PLAN chart | none — `fetchAlphaActivitySymbol` used in `DebateAlphaCard.jsx:10` (mounted `DebateTab.jsx:706`, gated by `showExpert`) and `ChartDrawer.jsx:408`. |
| Regime-transition evidence | `GET /api/alpha/regime-transition` (app.py:3832) | **ORPHAN** | ALPHA tab, "Research Quality" panel | No `api.js` helper, no `fetch()` call anywhere in `desk/src`. `AlphaLab.jsx:229` only displays a `regime_transition` *key label* sourced from `/api/alpha/research-quality`'s `cards[]` array — the dedicated endpoint itself is never called. Add `fetchAlphaRegimeTransition()` to `api.js`, call it in `AlphaLab.jsx`, add a card. |
| Factor health | `GET /api/alpha/factors/health` (app.py:3843) | **ORPHAN** | ALPHA tab | No helper, no caller anywhere. Add `fetchAlphaFactorsHealth()`, render as a panel/badge in `AlphaLab.jsx`. |
| Research quality | `GET /api/alpha/research-quality` (app.py:3854) | **WIRED** | ALPHA tab | none — `fetchAlphaResearchQuality`, rendered `AlphaLab.jsx:224-233`. |
| Registered models | `GET /api/alpha/models` (app.py:3874) | **WIRED** | ALPHA tab | none — `fetchAlphaModels`, rendered in `ResearchBenchPanel` (`AlphaLab.jsx:21-89`). |
| Experiments | `GET /api/alpha/experiments` (+`/{id}` app.py:3883/3892) | **WIRED** (list only) | ALPHA tab | List wired via `fetchAlphaExperiments`. The `/{experiment_id}` detail route has **no** `api.js` helper and no caller — clicking an experiment row does nothing (no drill-in). |
| Scanner preset hit-counts (lazy) | `GET /api/scanners/preset-hits` (app.py:7171) | **PARTIAL — dead helper** | SCANNERS tab | `fetchScannerPresetHits` exists in `api.js:206` but is called **nowhere**. `ux_defects_batch` handoff claims this was wired for lazy per-preset hit loading, but current `ScannersTab.jsx:793` calls `fetchScannerPresets(date, true)` — bulk `include_hits=true` — so the lazy endpoint was superseded and is now genuinely dead code on both ends. No action needed unless bulk mode is later found too slow. |
| Scanner preset run | `GET /api/scanners/run` (app.py:7189) | **WIRED** | SCANNERS tab | none — `runScannerPreset`, called `ScannersTab.jsx:857/680`. |
| Trader profile (read/write) | `GET/PUT /api/trader-profile` (app.py:7218/7229) | **WIRED** | Global modal | none — `fetchTraderProfile`/`updateTraderProfile` in `TraderProfileModal.jsx`, mounted `App.jsx:928`. |
| Live refresh (force LTP pull) | `POST /api/live/refresh` (app.py:3804) | **ORPHAN** | Command strip / POSITIONS | No helper, no caller. |
| Live readiness (Fyers/TG/heartbeat) | `GET /api/live/readiness` (app.py:7046) | **WIRED** | Command strip | none — `App.jsx:234` calls it directly with raw `fetch()` (not through `api.js`) inside `LiveReadiness`, rendered in the header (`App.jsx:761`). |
| Live status | `GET /api/live/status` (app.py:1262) | **ORPHAN** | Command strip | No helper, no caller. |
| Live SSE stream (LTP ticker) | `GET /api/live/stream` (app.py:1280) | **ORPHAN** | POSITIONS, SHORTLIST, command strip ticker | No `EventSource`/`fetch` reference anywhere in `desk/src`. This is the endpoint `HANDOFF_GEMINI_live_stage2_COMPLETED.md` explicitly flags as unfinished ("Full shell/POSITIONS/SHORTLIST LTP ticker wiring not completed this pass"). Given the user's locked "live-first" decision, this is the single biggest gap: the whole desk is still EOD-driven even though the backend SSE feed is production-ready. |
| Batch live quotes | `GET /api/live/quotes` (app.py:1217) | **ORPHAN** | POSITIONS, SHORTLIST | No helper, no caller — the documented fallback for the SSE stream is also unused. |
| Near-miss setups | `GET /api/setups/near-misses` (app.py:2577) | **ORPHAN** | SHORTLIST or DEBATE ("close calls") | No helper, no caller. `DebateTab.jsx:515` only has a *comment* referencing near-misses conceptually; the endpoint itself is never fetched. |
| Refused setups | `GET /api/setups/refusals` (app.py:2537) | **ORPHAN** | SHORTLIST / JOURNAL (learning material) | No helper, no caller. |
| Portfolio heat | `GET /api/portfolio/heat` (app.py:2921) | **ORPHAN** | POSITIONS (risk summary header) | No helper, no caller anywhere. |
| Per-position coach | `GET /api/positions/{trade_id}/coach` (app.py:2324) | **ORPHAN** | POSITIONS card | No helper, no caller. Note: `PositionsTab`/`DeskTab` text like `"coach positions=..."` (`DeskTab.jsx:312`) is a regex parsing a **live-work log line**, unrelated to this endpoint — do not confuse the two. Position cards currently get their coach verdict from a field embedded in `/api/desk/positions`, not this dedicated route. |
| Advisor "today" note | `GET /api/advisor/today` (app.py:4157) | **ORPHAN** | MARKET tab / guided flow rail | No helper, no caller. |
| Advisor note action | `POST /api/advisor/note-action` (app.py:4190) | **ORPHAN** | MARKET tab | No helper, no caller. |
| Weekly-base-breakout setup | preset `weekly_base_breakout` (scanner_presets.py, surfaced via `/api/scanners/presets`) | **WIRED** | SCANNERS tab | none — `ScannersTab.jsx:64` has an explicit glyph/lane map entry for it; it renders through the same generic preset-card flow as all other presets. |
| Track record | `GET /api/desk/track-record` (app.py:4625) | **WIRED** | JOURNAL tab | none — `fetchTrackRecord`, `LedgerTab.jsx:770`, mounted as JOURNAL. |
| Lessons | `GET /api/desk/lessons` (app.py:4711) | **WIRED** | JOURNAL tab | none — `fetchLessons`, `LedgerTab.jsx:770`. |
| Per-symbol alpha memory (analogues) | `GET /api/alpha/memory/{symbol}` (app.py:3901) | **ORPHAN** | DEBATE symbol card / TRADE PLAN | No helper, no caller. This is the "outcome-weighted analogue retrieval" from `HANDOFF_GEMINI_alpha_memory_gates_COMPLETED.md` (Q·Sim·Rec·Conf scoring + anti-resonance) — fully built backend module (`alpha/memory.py`), zero UI surface. |
| Activity feed (`/api/desk/feed`) | `GET /api/desk/feed` (app.py:4794) | **PARTIAL — dead component** | MARKET tab | `fetchFeed` is called only inside `DeskTab.jsx`'s **default export** (`DeskTab.jsx:652-674`). `App.jsx` never imports that default export — it only imports the two *named* exports `LawRow`/`ModelsSayPanel` from the same file (`MarketHomeTab.jsx:11`) for a different purpose. The feed-rendering component is dead code sitting in a file that's otherwise partially alive. |
| Legacy watchlist (old shape) | `GET/POST/DELETE /api/watchlist` (app.py:2277/2347/2368) | **ORPHAN (superseded)** | — | Superseded by `/api/desk/watchlist*`, which is the one actually wired (`fetchWatchlist`, `addWatchlistSymbol` → `/api/desk/watchlist/add`). This old route family looks like dead backend surface, not a missing feature. |
| Watchlist candidates | `POST /api/watchlist/candidates` (app.py:2593) | **ORPHAN** | SHORTLIST | No helper, no caller. |
| Organic watchlist | `GET /api/watchlist/organic` (app.py:2670) | **ORPHAN** | SHORTLIST | No helper, no caller. |
| Gate-health visuals | `GET /api/visuals/gate-health` (app.py:2752) | **ORPHAN** | SCANNERS / DEBATE (gate funnel) | No helper, no caller. |
| Journal visuals | `GET /api/journal/visuals` (app.py:2802) | **ORPHAN** | JOURNAL tab | No helper, no caller — `LedgerTab.jsx` only calls journal/track-record/lessons. |
| EOD alerts | `GET /api/alerts/eod` (app.py:2907) | **ORPHAN** | MARKET / command strip | No helper, no caller. |
| Expectancy | `GET /api/expectancy` (app.py:3159) | **ORPHAN** | JOURNAL / ALPHA | No helper, no caller (note: `AlphaLab.jsx` computes a similar concept from `/api/alpha/overview.setup_expectancy`, but this dedicated `/api/expectancy` route is untouched). |
| Symbol timing | `GET /api/symbol/{symbol}/timing` (app.py:2186) | **ORPHAN** | TRADE PLAN | No helper, no caller. |
| Symbol OHLC (raw) | `GET /api/symbol/{symbol}/ohlc` (app.py:2200) | **ORPHAN** | Chart drawer | No helper, no caller — chart data actually comes from `/api/desk/chart-data` (`fetchChartData`, wired). This route looks unused/legacy. |
| Regime sectors/indices/summary (legacy) | `GET /api/regime/sectors`, `/indices`, `/summary` (app.py:1382/1564/1593) | **ORPHAN** | MARKET tab | No helper, no caller. `/api/desk/market` appears to be the live consumer for sector/index data instead (`fetchMarket`, wired). |
| Regime sector/industry stock drill-down | `GET /api/regime/sectors/{key}/stocks`, `/api/regime/industries/{name}/stocks` (app.py:1921/1943) | **ORPHAN** | MARKET (sector card click-through) | No helper, no caller. `fetchSectorStocks` in `api.js:129` hits a **different** route, `/api/desk/market/sector-stocks` (app.py:2055) — that one is wired. These two `/api/regime/...` variants are unused duplicates. |
| Screener presets (legacy) | `GET /api/desk/screener/presets` (app.py:5002) | **ORPHAN** | SCANNERS | No helper, no caller. Live consumer is `/api/scanners/presets` (`fetchScannerPresets`, wired) — this looks like an older, now-unused route. |
| Guru checklists (Arora entry discipline, 12 items) | `GET /api/mentor/checklists`, `GET /api/checklists/{id}/evaluate`, `POST /api/checklists/{id}/ticks` (app.py:4007/4066/4125) | **WIRED** | TRADE PLAN | none — `fetchMentorChecklists`/`fetchChecklistEvaluation`/`toggleChecklistTick` all called in `TradePlanTab.jsx:427-467`. |
| Breadth analytics (NH-NL, Fosback, BO/BD) | `GET /api/regime/breadth-analytics` (app.py:1783) | **WIRED** | MARKET tab | none — `fetchBreadthAnalytics`, `MarketHomeTab.jsx:490`. |
| Regime history (XP/MBI trend) | `GET /api/regime/history` (app.py:1707) | **WIRED** | MARKET tab | none — `fetchRegimeHistory`, `MarketHomeTab.jsx:373`. |
| Guided daily flow | `GET /api/flow/today` (app.py:2994) | **WIRED** | Guided rail (beginner) / collapsed strip (expert) | none — this was itself the subject of `HANDOFF_GEMINI_guided_system_COMPLETED.md` and is now fully wired in `App.jsx`. |
| Legacy pipeline run/status | `POST /api/pipeline/run`, `GET /api/pipeline/status` (app.py:3444/3477) | **PARTIAL — dead helpers** | — | `runPipeline`/`getPipelineStatus` exist in `api.js` but are called nowhere; superseded by the `/api/jobs` durable job framework (`createJob`, used in `useJobStream.js`, actively wired). Cosmetic dead code, not a missing feature. |
| Fyers connect flow | `GET /api/fyers/status`, `/auth-url`, `POST /exchange`, `/token` (app.py:3935-4006) | **WIRED (in progress during this audit)** | Header / settings | Being actively wired by a concurrent agent — `FyersConnectionCard` appeared in `App.jsx` mid-audit. Re-verify after that session lands. |

---

## (B) Prioritized ORPHAN + PARTIAL integration backlog

### MARKET
1. **`/api/live/stream` (SSE) + `/api/live/quotes`** — no LTP ticker anywhere in the desk despite the
   user's locked live-first decision. Edit: `App.jsx` (command strip) or a new `LiveTicker.jsx`
   component subscribed via `EventSource(jobEventsUrl-style URL)`. Done-test: a price updates on
   screen without a manual page refresh during market hours.
2. **`/api/desk/feed` (activity feed)** — component exists (`DeskTab.jsx` default export) but is
   never mounted. Edit: either import `DeskTab`'s default export into `MarketHomeTab.jsx` in an
   "activity feed" section, or delete the dead code if superseded. Done-test: a scrolling list of
   recent pipeline/decision events appears on MARKET.
3. **`/api/advisor/today` + `/api/advisor/note-action`** — zero UI. Edit: `MarketHomeTab.jsx`, add
   an "advisor note" card with an action button wired to `note-action`. Done-test: the advisor's
   daily note text renders and the action button posts successfully.
4. **`/api/alerts/eod`** — zero UI. Edit: `MarketHomeTab.jsx` or command strip banner. Done-test:
   an EOD alert (if any exist for the date) renders as a banner/list item.
5. **`/api/regime/sectors/{key}/stocks`, `/api/regime/industries/{name}/stocks`** — duplicate,
   unused routes; `/api/desk/market/sector-stocks` already covers this. No wiring needed — flag for
   backend cleanup instead.

### SCANNERS
6. **`/api/visuals/gate-health`** — zero UI. Edit: `ScannersTab.jsx`, add a funnel/gate-health strip
   showing pass/fail counts per gate. Done-test: gate pass-rate numbers render above/below the
   preset list.
7. **`/api/watchlist/candidates`, `/api/watchlist/organic`** — zero UI. Edit: `ScannersTab.jsx` or
   `ShortlistTab.jsx`, surface as an "organic candidates" sub-list distinct from scanner hits.
   Done-test: a labeled section shows organically-sourced watchlist candidates.

### SHORTLIST
8. **`/api/setups/near-misses`** — zero UI despite a code comment referencing the concept. Edit:
   `ShortlistTab.jsx`, add a "near misses" collapsible section using chair rank. Done-test: symbols
   that almost passed gates appear in a dedicated list with the reason they were excluded.
9. **`/api/setups/refusals`** — zero UI. Edit: `ShortlistTab.jsx` or `LedgerTab.jsx` (learning
   material framing per glossary.js:175). Done-test: refused setups list with refusal reason.

### TRADE PLAN / DEBATE
10. **`/api/alpha/memory/{symbol}` (analogue retrieval, Q·Sim·Rec·Conf + anti-resonance)** — fully
    built backend (`alpha/memory.py`), completely invisible in UI. This is the highest-value orphan:
    it's a mature research feature (promotion-gated, leakage-audited) with zero front door. Edit:
    `DebateAlphaCard.jsx` (same component that already renders `/api/alpha/activity/{symbol}`), add
    an "analogues" panel showing top-k similar historical outcomes and the anti-resonance flag.
    Done-test: a symbol's debate card shows 3-5 historical analogue trades with Q/Sim/Rec/Conf scores.
11. **`/api/alpha/regime-transition`** — zero direct call (only referenced indirectly through a
    research-quality card key). Edit: `AlphaLab.jsx`, call the endpoint directly and add a
    dedicated panel instead of piggybacking on the `research-quality` card label. Done-test: a
    regime-transition-specific panel with its own evidence appears in ALPHA.
12. **`/api/alpha/factors/health`** — zero UI. Edit: `AlphaLab.jsx`, add a factor-health status
    strip (which features are fresh/stale). Done-test: a health chip per factor renders.
13. **`/api/symbol/{symbol}/timing`** — zero UI. Edit: `TradePlanTab.jsx`, surface intraday-timing
    guidance if the endpoint returns something actionable. Done-test: timing hint text appears in
    the trade plan.
14. **`/api/alpha/experiments/{experiment_id}` (detail)** — list is wired, detail drill-in is not.
    Edit: `AlphaLab.jsx` `ResearchBenchPanel`, make experiment rows clickable, fetch detail on
    click. Done-test: clicking an experiment row expands hypothesis/verdict detail.

### POSITIONS
15. **`/api/portfolio/heat`** — zero UI. Edit: `PositionsTab.jsx`, add a portfolio-heat summary
    header (aggregate risk across open positions). Done-test: a heat number/gauge renders above the
    position list.
16. **`/api/positions/{trade_id}/coach`** — zero UI; note `/api/desk/positions` already embeds a
    coach verdict per position, so first confirm with backend whether this route is redundant or
    provides deeper per-position coaching text before wiring. Edit: `PositionsTab.jsx` position
    card, "expand for full coach reasoning" affordance. Done-test: expanding a card shows coach
    text sourced from this endpoint specifically (not the embedded summary field).
17. **`/api/live/refresh`** — zero UI. Edit: add a manual "force live refresh" button near
    `LiveReadiness` in `App.jsx` header. Done-test: clicking it triggers a visible refresh of live
    fields.

### JOURNAL
18. **`/api/journal/visuals`** — zero UI. Edit: `LedgerTab.jsx`, add a visual (equity curve / R
    distribution chart) fed by this endpoint if it differs from what's already computed client-side.
    Done-test: a chart renders using this endpoint's data.
19. **`/api/expectancy`** — zero UI (separate from the `/api/alpha/overview.setup_expectancy` used
    in ALPHA). Edit: `LedgerTab.jsx`, add an expectancy stat tile if this route's numbers differ in
    scope from what ALPHA already shows. Done-test: expectancy tile renders with a source note
    distinguishing it from the ALPHA lab's version.

### ALPHA
20. ALPHA tab itself is fully wired but **hidden from beginner-mode nav** (`App.jsx:778`,
    `TABS.filter(t => t !== "ALPHA")`). Given items 10-12 above live there, beginner users cannot
    reach any of this even after it's wired. Edit: `App.jsx`, either promote a beginner-safe subset
    of ALPHA into the guided flow rail, or add a plain-language entry point. Done-test: a beginner-
    mode user can reach at least the "opportunity ranking" panel without switching to expert mode.

---

## (C) Handoffs marked COMPLETED but NOT fully visible in the UI

These are the concrete "I asked for this feature and it doesn't show up" cases, cross-referenced
against the 21 `*_COMPLETED.md` handoffs:

1. **`HANDOFF_GEMINI_live_stage2_COMPLETED.md`** ("Live-default", 2026-07-12) — self-reports as
   "COMPLETED (partial desk UI)" and explicitly states: *"Full shell/POSITIONS/SHORTLIST LTP ticker
   wiring not completed this pass."* Confirmed still true: `/api/live/stream`, `/api/live/status`,
   `/api/live/quotes` have zero frontend references. This directly contradicts the user's locked
   "live-first" decision (`project-live-first-mode.md`) — the desk is still 100% EOD-driven for
   price data despite a production-ready SSE feed existing since 2026-07-12.
2. **`HANDOFF_GEMINI_alpha_memory_gates_COMPLETED.md`** ("Outcome-weighted analogue retrieval",
   2026-07-12) — backend fully shipped (`alpha/memory.py` scoring, `promotion_gates.py`,
   `leakage_audit.py`, experiment KB) and tested, but `/api/alpha/memory/{symbol}` has no `api.js`
   helper and no caller anywhere. Zero UI surface for a mature, gate-tested research feature.
3. **`HANDOFF_GEMINI_rf_breakout_outcome_model_COMPLETED.md`** (Random-forest breakout model) —
   backend model + walk-forward + promotion battery fully built and documented with real AUC/CV
   numbers. No dedicated endpoint or UI surface was found for this model's live predictions
   specifically (distinct from the generic `/api/alpha/models` registry list, which only shows
   metadata, not this model's actual output). **Unverified** which endpoint (if any) exposes this
   model's live scores — recommend the orchestrator grep `alpha/services.py` / `app.py` for the
   model's registered name to confirm whether it feeds `/api/alpha/leaders` silently or is
   genuinely surfaceless.
4. **`ux_defects_batch` (Fix 4/8, preset-hits lazy loading)** — handoff claims
   `/api/scanners/preset-hits` was added and wired for lazy per-preset hit counts. Current
   `ScannersTab.jsx` code path uses bulk `fetchScannerPresets(date, true)` instead — the lazy
   endpoint and its `api.js` helper are dead. Not user-missing functionality (bulk mode works), but
   the handoff's claim of "wired" is stale relative to current code.
5. Handoffs whose shipped surface **is** correctly visible (verified, no gap): `positions`
   (PositionsTab v5 rebuild), `GLM_journal` (LedgerTab v5 rebuild), `guru_checklists` (TradePlanTab
   checklist evaluation), `breadth_analytics` + `breadth_tier0` (MarketHomeTab NH-NL/Fosback/BO-BD
   panels), `regime_history_hmm` (MarketHomeTab regime gauge + HMM status), `guided_system`
   (guided flow rail), `backend_fields_batch` (TradePlanTab rupee_risk/management_contract,
   ShortlistTab family/trigger chips), `search_live_analysis` (symbol search → streamed debate).

---

## Notes on scope not fully covered

- Did not exhaustively verify every field *inside* an already-WIRED payload is rendered (e.g.
  whether every sub-field of `/api/desk/positions` reaches the DOM) — this audit is endpoint-level,
  not field-level. A field-level pass would likely surface additional partial gaps within already-
  "WIRED" rows.
- `manas_os/alpha/`, `manas_os/scanner/`, `manas_os/regime/`, `manas_os/engine/` were scanned for
  endpoint call sites via `app.py`, not walked module-by-module for internal functions that never
  got an endpoint at all (a separate, larger question: "computed but not even exposed via API").
- The RF breakout-outcome model's live-score exposure (item C.3 above) needs a follow-up grep pass
  before it can be classified with certainty.
