# Manas Visual Overhaul + Organic Watchlist Plan

## Summary
Rebuild Manas from a text-heavy dashboard into a visual trading cockpit: poster-style regime, visual setup cards, organic watchlist curation, near-miss learning, and journal/outcome visuals. Keep deterministic gates, but stop making them feel like a hard wall by adding near-miss tracking, override logging, and evidence-based calibration views.

Primary rule: every screen must answer "what should I do next?" visually before showing tables.

## Wireframes Are The Target
`WIREFRAMES.md` is not inspiration; it is the acceptance target for this overhaul. The app should converge on the wireframe contract screen by screen:

- Keep the global shell, header, five-tab navigation, staleness chip, and daily flow stepper.
- Regime must read as "today's law": governor first, visual market context second, detailed numbers behind accordions.
- Setups must read as "the feed that says NO": refusal funnel first, survivor cards second, near-misses as a visible workflow.
- Focus is not a separate engine; it is the same setup funnel filtered to IPO/EP catalyst families.
- Watchlist must read as "positions + heat": active positions and risk heat before manual watch rows.
- Journal must read as "the moat rendered": equity/R outcomes and cohort learning before raw trade tables.
- ChartDrawer remains the deep inspection surface: lightweight-charts, overlays, journal markers, and compact legend.

Acceptance rule: a screenshot of each implemented screen should be recognizable against the matching `WIREFRAMES.md` block without needing explanatory text.

## Why The Current Tool Diverged
The existing app is different from the wireframes because implementation followed available payloads and dashboard habits instead of the target product model:

- Frontend components optimized around current API facts, not visual-ready decision payloads. Result: tables, chips, and text cards became the default.
- Shared poster primitives were never created. Without `PosterCanvas`, `PosterBand`, `AnnotatedChart`, `MetricTape`, `StateRibbon`, and `VisualCard`, each screen fell back to bordered dashboard sections.
- Near-misses stayed as a refusal log. The intended operational loop needs persisted candidates, override logs, outcome trails, and "what would it take?" distances.
- Visual work was local and shallow. Regime, Journal, and Watchlist gained individual charts, but the core hierarchy remained report-first instead of decision-first.
- Deterministic gates leaked into the experience as a hard wall. The scanner can stay strict, but the UI needs calibration layers: near-miss lanes, gate proximity, cohort outcomes, refusal funnels, and override journals.
- The wireframes did not become testable acceptance criteria. Visual QC must now compare against the wireframe intent, not just check that components render.

Design guardrail: do not mark a screen "visually upgraded" if its first viewport is still mostly text, bordered cards, or raw rows.

## Key Changes

### 1. Visual System Rebuild
Replace bordered-card dashboard styling with a composed research-poster layout:

- large uppercase verdicts
- full-width chart bands
- annotated arrows/callouts
- state-colored backgrounds
- compact data tables only as secondary evidence

Create shared visual primitives:

- `PosterCanvas`
- `PosterBand`
- `AnnotatedChart`
- `MetricTape`
- `StateRibbon`
- `VisualCard`

Use ECharts everywhere except detailed candlestick charts, which stay in `lightweight-charts`.

Add mandatory visual QC: desktop and mobile screenshots for Regime, Setups, Watchlist, Journal, and ChartDrawer.

Add a wireframe parity checklist to every visual PR:

- Does the first viewport match the intended screen hierarchy?
- Is the primary chart/visual visible before tables?
- Is the next action visible without reading a paragraph?
- Are expert details secondary, collapsed, or visually de-emphasized?
- Are stale/data-down/exit states visible in both beginner and expert modes?

### 2. Regime Screen: Market Poster
Build a true poster screen and match `WIREFRAMES.md` section 1: governor hero first, top setup strip second, numbers accordion third.

Visualizations:

- Regime ribbon over 60 sessions, colored by `market_mode`.
- XP line with posture background bands.
- Breadth weather calendar.
- Swing/trend/bias sections with annotated mini charts.
- Sector rotation quadrant.
- Top indices performance strip.
- "Today's Law" visual governor: max cards, risk cap, allowed setup families, push on/off.
- Outcome overlay: journal entries/exits plotted on the regime ribbon.

### 3. Setups Screen: Visual Setup Cards
Replace current text cards with chart-led setup cards and match `WIREFRAMES.md` section 2: refusal funnel hero first, capped survivor cards second, near-miss lane visible below.

Required card behavior:

- Mini candlestick chart embedded directly on every setup card.
- Entry, stop, target, buy-zone, AVWAP, 21EMA, and measured move drawn visually.
- Gate dots become a six-gate visual rail with pass/fail/caution states.
- Risk box becomes a visual R:R ladder: entry to stop to target.
- Evidence chips become grouped "why this exists" sections: catalyst, price action, theme, delivery, risk.
- Add a setup storyboard strip: base to trigger to risk to action.
- Clicking a card still opens full ChartDrawer, but the card itself must be visually useful.

### 4. Organic Watchlist + Near-Miss System
Add a new Watch Candidates workflow. This is the missing bridge between the wireframe near-miss row and the user's request for organic watchlist maintenance.

Near-misses get their own visual lane below passed setups. Each near-miss shows:

- failed gate
- distance-to-pass
- "what would it take?" chip
- mini chart
- button: `Track`, `Ignore`, `Override Half Size`

Add server-side tables:

- `watchlist_candidates`
- `gate_overrides`
- `watchlist_candidate_outcomes`

Add endpoints:

- `GET /api/setups/near-misses`
- `POST /api/watchlist/candidates`
- `POST /api/setups/override`
- `GET /api/watchlist/organic`

Watchlist becomes three sections:

- Active positions
- Tracked near-misses
- Manual watchlist

Every watchlist item must have a reason, source, age, current gate status, and outcome trail. Manual watchlist is no longer the only watchlist. It becomes one lane beside tracked near-misses and active positions.

### 5. Journal + Learning Visuals
Add the visualizations from `VIZ_BRAINSTORM.md` and match `WIREFRAMES.md` section 5: equity/R hero first, learning visuals second, raw journal rows last.

Required visuals:

- Passed vs refused near-miss T+10 outcome chart.
- Gate proximity map.
- Refusal funnel over time.
- Stop-vs-ADR outcome scatter.
- Expectancy matrix evolution.
- Trade lifecycle river for open positions.
- Slippage tracker: planned entry vs actual fill.
- Mistake-tag Pareto.
- Regime ribbon with trades overlaid.
- Four-cohort strip:
  - taken
  - skipped
  - tracked near-miss
  - refused

### 6. ChartDrawer Wireframe Parity
ChartDrawer is the inspection layer for any symbol click:

- Keep `lightweight-charts` for the main candle surface.
- Add visible overlays: buy-zone band, entry, stop, target, EMA 10/21/50, AVWAP, pocket pivot markers when available, and journal entry/exit markers.
- Add compact one-line legend with setup family, stage, trail rule, and current gate state.
- Keep tabs for setup, trend, and exit context.
- The drawer must not be a larger text card; the chart must dominate.

### 7. Beginner / Expert Contract
The wireframes define beginner and expert as display modes, not separate products:

- Beginner mode shows flow stepper, governor, coach, capped cards, and plain English.
- Expert mode is a strict superset exposed through accordions or detail toggles.
- Safety states render identically in both modes: stale data, data down, exit alerts, broker disconnects.
- No core decision should require opening expert mode.

## API / Data Additions
- `GET /api/visuals/gate-health`
  - returns passed vs near-miss outcome series, refusal counts by gate, and rolling T+10 medians.
- `GET /api/setups/near-misses?date=YYYY-MM-DD`
  - returns top refused symbols with failed gate, evidence, distance-to-pass, and chart payload.
- `POST /api/setups/override`
  - logs user override with reason, forced half-size flag, and snapshot JSON.
- `GET /api/watchlist/organic`
  - returns manual watchlist, tracked near-misses, and open positions in one visual-ready payload.
- `GET /api/journal/visuals`
  - returns equity curve, R histogram, mistake Pareto, cohort outcomes, slippage, and regime overlay data.

## Test Plan
Backend:

- near-miss endpoint returns deterministic ranked refusals with distance-to-pass.
- override logging stores full snapshot and never changes original gate result.
- watchlist candidate outcomes backfill T+5/T+10/T+20.
- gate-health chart data matches persisted refusals/outcomes.

Frontend:

- Regime, Setups, Watchlist, Journal render with empty, stale, and populated data.
- Setup card mini charts show entry/stop/target correctly.
- Near-miss cards can be tracked/ignored/overridden.
- Organic watchlist separates manual, tracked, and active positions.

Visual QC:

- capture screenshots at desktop and mobile.
- fail if cards are mostly text, charts are blank, labels overlap, or lists truncate silently.
- compare screenshots against the corresponding `WIREFRAMES.md` block for hierarchy parity.
- fail if the first viewport does not expose the screen's primary decision.

## Implementation Waves

### Wave 1: Substrate + Current Pain Points
- Backend near-miss endpoint, candidate tables, override logging, organic watchlist endpoint.
- Shared poster primitives.
- Setups visual cards with mini charts, gate rail, R:R ladder, storyboard, and near-miss lane.
- Regime governor/poster hierarchy tightened to match the wireframe.

### Wave 2: Watchlist + Journal Learning Loop
- Organic watchlist split into active positions, tracked near-misses, manual watchlist.
- Candidate outcome backfill and T+5/T+10/T+20 outcome trails.
- Gate-health endpoint and Journal learning charts.
- Four-cohort strip and near-miss outcome comparison.

### Wave 3: ChartDrawer + Full Visual QC
- ChartDrawer overlay parity with the wireframe.
- Desktop/mobile screenshot capture for Regime, Setups, Watchlist, Journal, ChartDrawer.
- Visual regression checklist and failure notes for mostly-text screens, blank charts, overlap, truncation, and stale data states.

## Assumptions
- Keep the deterministic gate, but make it softer operationally through tracking and overrides.
- Overrides are always half-size and always logged; they never mutate the official gate.
- "As many visualizations as possible" means chart-dense but still decision-first, not decorative chart spam.
- First implementation wave should prioritize Setups + Near-Misses + Regime, because those are the current pain points.
