# Codex Visual Redesign Handoff

Status: paused by user after first implementation pass.

This handoff is for the next coding tool/agent resuming the Manas visual overhaul. The design source of truth is now `manas_os/design/codex visual plan.md`, which explicitly makes `manas_os/design/WIREFRAMES.md` the acceptance target.

## Design Target
The redesign should make Manas feel like a visual trading cockpit, not a table dashboard.

Primary acceptance rule:

- Every screen must answer "what should I do next?" visually before showing tables.
- A screenshot of each screen should be recognizable against the matching block in `WIREFRAMES.md`.
- Do not call a screen upgraded if the first viewport is still mostly text, bordered cards, or raw rows.

Key wireframe contracts:

- Regime: "today's law" governor first, market visuals second, detailed numbers behind expert accordions.
- Setups: "the feed that says NO" refusal funnel first, chart-led survivor cards second, actionable near-miss lane below.
- Watchlist: active positions + risk heat + tracked near-misses + manual watchlist.
- Journal: equity/R and cohort learning before raw journal rows.
- ChartDrawer: chart-dominant inspection surface with overlays, compact legend, setup/trend/exit tabs.

## Why The Tool Drifted
The current app diverged from the wireframes because:

- Components were built around existing API facts instead of visual-ready decision payloads.
- Shared poster primitives did not exist, so screens fell back to card/table layouts.
- Near-misses were only a refusal log, not an operational workflow.
- The deterministic gates leaked into UX as a hard wall instead of a learning/calibration loop.
- Visual upgrades were not treated as acceptance-tested wireframe parity.

These points have been added to `manas_os/design/codex visual plan.md`.

## Work Completed In This Pass

### Backend substrate
File: `manas_os/api/app.py`

Added helper schema/functions:

- `_ensure_organic_watchlist_schema`
- `_mini_chart_payload`
- `_distance_to_pass`
- `_upsert_candidate_outcome`
- `_near_miss_items`

Added tables via runtime schema creation:

- `watchlist_candidates`
- `gate_overrides`
- `watchlist_candidate_outcomes`

Added endpoints:

- `GET /api/setups/near-misses`
- `POST /api/watchlist/candidates`
- `POST /api/setups/override`
- `GET /api/watchlist/organic`
- `GET /api/visuals/gate-health`
- `GET /api/journal/visuals`

Important intended behavior:

- Overrides are logged half-size and do not mutate official scanner pass/fail.
- Near-misses include failed gate, reason, distance-to-pass, chart payload, tracking/override status, and outcome shell.
- Outcome backfill is opportunistic from `daily_prices`; it returns nulls until T+5/T+10/T+20 data exists.

### Frontend API client
File: `manas_os/frontend/src/api.js`

Added client functions:

- `getSetupsNearMisses`
- `trackWatchlistCandidate`
- `overrideSetup`
- `getOrganicWatchlist`
- `getGateHealth`
- `getJournalVisuals`

### Shared visual primitives
File: `manas_os/frontend/src/components/poster/Primitives.jsx`

Added:

- `PosterCanvas`
- `PosterBand`
- `AnnotatedChart`
- `MetricTape`
- `StateRibbon`
- `VisualCard`

Note: build passes, but the visual taste still needs browser review and refinement.

### Setups redesign first pass
File: `manas_os/frontend/src/components/SetupsPage.jsx`

Changed:

- Uses `PosterCanvas`, `PosterBand`, `MetricTape`, `VisualCard`, `AnnotatedChart`.
- Fetches `/api/setups/near-misses`.
- Candidate cards now include mini ECharts candlestick charts using `/api/symbol/{symbol}/ohlc`.
- Added chart overlays for entry, stop, target, and 21EMA where payload supports it.
- Gate dots became a horizontal gate rail.
- Trade plan text was replaced visually by `RiskLadder`.
- Added `SetupStoryboard`.
- Added grouped `EvidenceGroups`.
- Near-misses are now visible cards with:
  - mini chart
  - failed gate
  - distance-to-pass
  - "what would it take?"
  - `Track`
  - `Ignore`
  - `Override half size`

Known caveat:

- The card is more visual now, but not yet polished enough for final aesthetic bar. Needs browser screenshots and layout tuning.

### Watchlist organic lanes
File: `manas_os/frontend/src/components/WatchlistPage.jsx`

Added `OrganicWatchlistPanel` with three lanes:

- Active positions
- Tracked near-misses
- Override half-size

Manual watchlist remains below.

Known caveat:

- Organic lane cards are visual placeholders, not final wireframe polish. Add charts/sparklines and stronger risk heat treatment next.

### Journal learning visuals
File: `manas_os/frontend/src/components/JournalPage.jsx`

Added:

- Fetch for `/api/journal/visuals`
- Fetch for `/api/visuals/gate-health`
- `LearningVisuals` section
- Four-cohort metric strip
- Refusal funnel over time chart
- T+10 cohort median chart
- Slippage tracker chart

Known caveat:

- This wires the loop, but it needs real browser review and better empty states.

## Verification Done

Commands run:

- `python -m py_compile manas_os\api\app.py`
- `npm run build` from `manas_os/frontend`

Results:

- Python compile passed.
- Frontend build passed.
- Vite emitted only the existing large bundle warning.

Not yet done:

- Backend endpoint tests.
- Frontend unit tests.
- Browser visual QC.
- Desktop/mobile screenshots for Regime, Setups, Watchlist, Journal, ChartDrawer.
- Live API smoke tests against `http://127.0.0.1:8000`.

## Files Modified

- `manas_os/design/codex visual plan.md`
- `manas_os/api/app.py`
- `manas_os/frontend/src/api.js`
- `manas_os/frontend/src/components/poster/Primitives.jsx`
- `manas_os/frontend/src/components/SetupsPage.jsx`
- `manas_os/frontend/src/components/WatchlistPage.jsx`
- `manas_os/frontend/src/components/JournalPage.jsx`

## Recommended Resume Plan

### 1. Run backend smoke tests
Start API and hit:

- `/api/setups/near-misses`
- `/api/watchlist/organic`
- `/api/visuals/gate-health`
- `/api/journal/visuals`

Check for runtime SQL issues and payload shape mismatches.

### 2. Add backend tests
Add focused tests for:

- near-miss endpoint returns deterministic refusals with distance-to-pass
- `POST /api/watchlist/candidates` persists tracking and ignore states
- `POST /api/setups/override` logs half-size override and does not alter `refusals`
- candidate outcomes populate where enough future bars exist
- gate-health returns refusal counts and medians without failing on empty outcome data

### 3. Browser visual QC
Run the app and capture desktop/mobile screenshots for:

- Regime
- Setups
- Watchlist
- Journal
- ChartDrawer

Fail the pass if:

- charts are blank
- cards are mostly text
- near-miss actions are hidden
- labels overlap
- mobile truncates silently
- first viewport does not expose the primary decision

### 4. Continue visual polish
Priority order:

1. Setups card polish: stronger chart hierarchy, tighter action strip, better mini chart annotations, less text density.
2. Near-miss lane: make distance-to-pass visually obvious, add gate proximity bars.
3. Regime: convert existing regime page to explicit `PosterCanvas`/`PosterBand` hierarchy and add `StateRibbon`.
4. Watchlist: add mini charts/sparklines to organic lane cards.
5. Journal: improve empty states and add gate proximity map / stop-vs-ADR scatter.
6. ChartDrawer: overlay parity with the wireframe.

## Important Cautions

- Do not revert unrelated dirty worktree changes.
- The current backend schema additions are runtime `CREATE TABLE IF NOT EXISTS`; if this project has a migration convention, convert them into the proper migration later.
- `/api/watchlist/organic` currently reuses the existing `watchlist()` route function for manual rows. This works conceptually but should be smoke-tested because it opens its own DB connection.
- The visual work builds, but build success is not design success. Browser screenshots are mandatory before calling the redesign implemented.
