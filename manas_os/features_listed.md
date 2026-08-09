# Manas OS — Audited Feature Inventory

**Outcome:** The repository contains a substantial reusable operating substrate; the failed part is the recommendation authority, not the entire product.  
**Audit date:** 2026-08-03  
**Risks:** This is a code-and-project-document inventory, not a live production certification. “Wired” means an active UI/API/code path exists; it does not prove current data availability, predictive edge, or successful operation on every date.

## Status legend

- **Wired:** present in the active desk/API or registered pipeline.
- **Backend only / partial:** implemented substrate exists but the current primary UI does not fully expose it, or the feature is explicitly incomplete.
- **Experimental / quarantined:** implemented research path, not proven recommendation authority.
- **Legacy / superseded:** still useful for audit or baseline comparison, but contradicted by later evidence or no longer the desired product authority.
- **Pending:** recorded in the active task board or documentation but not complete.

## 1. Active desktop product

### Application shell and shared behavior — Wired

- Seven current work areas in `desk/src/App.jsx`: Market, Scanners, Shortlist, Debate, Alpha, Positions, and Journal, plus a full-screen Trade Plan route.
- Beginner/expert density modes and beginner labels: Today, Prepare, Watch, Decide, Manage, Review.
- Guided-flow rail, date navigation, symbol search, push-to-debate behavior, keyboard shortcuts, error boundaries, and degradation/freshness banners.
- Trader-profile modal and capital/experience-mode confirmation.
- Live-work/job overlay using durable backend jobs and events.
- Fyers connection/status affordance and ChartsMaze status handling.

### Market Home — Wired

- Regime headline and market mode.
- MBI/XP presentation with history/ribbon behavior.
- Breadth section and breadth analytics/history.
- Sector and industry drilldowns.
- Sector/theme and opportunity sections.
- Model commentary as an expert-mode addendum, not the only market read.
- Live-work/data-status section.
- Index candle and broader market endpoints exist in the API.

### Scanners — Wired, authority superseded

- Preset scanner lanes/stages and result rows with chart thumbnails/glyphs.
- Custom condition builder and saved user screens.
- Activity pane, practitioner/research-library presentation, and community templates.
- Earnings calendar/season panel.
- Tonight queue, shortlist actions, Strong Start actions, chart opening, and push-to-debate.
- The scanner remains useful for retrieval and exploration; its current qualification/rank semantics are not validated edge.

### Shortlist — Wired

- Watchlist/shortlist list management, reasons, chart thumbnails, timeline, and removal.
- Focus/Strong Start list management.
- Push to council/debate and open Trade Plan.
- Smart Money Flow Board is actively mounted here and opens the selected symbol chart.

### Debate — Wired, recommendation authority superseded

- Regime context/ring, model lanes, governor/risk-gate presentation, decision banner, table, hero/deep dive, and lens detail.
- Symbol push box and streamed/durable job status.
- Council TAKE/SKIP and final ranking exist, but later edge tests invalidate treating these as proven top-pick authority.

### Trade Plan — Wired

- Signal guide, debate evidence, mechanical actionability, entry/stop/target/R:R display, and copyable order-ticket behavior.
- Do-not-trade conditions, broker checklist, management contract, evidence inspector, and mentor checklist panel.
- Server-side mechanical decision gating and setup-decision persistence.
- Numeric behavior is protected; this inventory makes no recommendation to alter money math.

### Positions — Wired

- Open-position cards, P&L/R display, R-path sparkline, R thermometer, verdict, original thesis, freshness, and Telegram mirror.
- Add/update/close behavior and close modal.
- Position-coach and live-monitoring substrate exists; some dedicated coaching endpoints remain more complete than the visible surface.

### Journal — Wired

- Journal trade CRUD, editable/deletable history, broker/imported holdings, and add-trade workflow.
- Stat rail, win/loss bar, equity curve, R bars, broker P&L, expectancy tables, track record, screener calibration, and lessons diary.
- Journal/outcome data is a core asset for the rebuild.

### Alpha Lab — Wired as research UI; authority experimental

- Overview/status, leaders, activity, per-symbol alpha trail, research quality, factor health, model registry/list, and experiment list.
- Research bench/stage tracker and model/experiment summaries.
- Several deeper alpha-memory, transition, and experiment-detail capabilities are backend-only or partial.

### Chart Drawer — Wired

- Weekly/daily OHLC charts using lightweight charts.
- Volume and overlays including moving averages/AVWAP and trade landmarks where data is available.
- Entry/exit and pocket-pivot-style markers, RS/TTM-style secondary panes, alpha/activity evidence, and HMM state display.
- This is reusable as the basis for deterministic AI chart packs, but current interactive rendering is not yet an immutable model-input artifact.

## 2. Smart Money / activity footprint

### Canonical activity score — Wired

- `alpha/activity.py` writes `alpha_activity_signals`; `scanner/footprint.py` explicitly treats it as the only activity-score writer.
- Score history, delivery percentage, formula versioning, factor-health/alpha views, and symbol trail are present.

### Footprint driver — Wired, partly assumption-calibrated

- Joins activity signals to exact-date EQ prices and persists `footprint_daily`.
- Computes score tier, abnormal-score streak, four-day average, delivery band, volume ratio, daily direction/context, split-suspect flag, 20-day accumulation/distribution counts, and delivery-weighted net silent flow.
- Classifies five lanes: silent accumulation, absorption, public markup, retail churn, and silent offloading.
- Absorption containment was empirically calibrated over 96,591 symbol-days as documented in code.
- Other thresholds such as EXTREME and VOLUME_LOW are explicitly labeled assumptions pending replay calibration.

### Flow Board — Wired

- Five-lane, score × volume × direction UI in `desk/src/components/v5/FlowBoard.jsx`.
- Displays symbol, footprint tier/sticker, score, abnormal streak, accumulation/distribution balance, and net silent-flow bar.
- Scope is the union of scan candidates, discovery bucket, and watchlist.
- Current UI doctrine correctly says the score only identifies where to look; it does not size or author risk.
- Currently mounted in Shortlist, not Market Home.

## 3. Data ingestion and canonical substrate

### Registered EOD pipeline — Wired

The current registry includes:

- live quote refresh;
- bhavcopy prices;
- alpha symbol identity;
- FII/DII flow;
- universe breadth and optional breadth counts;
- ChartsMaze data and scanner ingestion;
- universe classification;
- fundamentals;
- disclosures;
- NSE bulk/block deals;
- earnings calendar;
- indicators;
- NSE indices;
- MARS;
- regime snapshot;
- optional HAR/HMM/ML stages;
- alpha features and footprint driver;
- candidate scan, optional discovery/focus-theme/theme-pulse stages;
- agent debate, alpha memory, coach, expectancy, advisor;
- candidate outcomes, setup-regime history, screener calibration;
- optional ML direction/breakout models;
- EOD alerts and Telegram digest.

Registration proves intended execution order, not that every optional provider supplies fresh data on every run.

### Market and security data — Wired or registered

- Daily/intraday prices, indicators, index histories/candles, relative-strength inputs, liquidity/universe classification, sector/industry mappings, and symbol identity.
- Breadth series, regime snapshots, HMM/transition tables, setup-regime daily history, and theme pulse.
- Fundamentals, disclosures, NSE deals, earnings calendar, delivery/activity, and ChartsMaze-derived data.
- Live quotes, live heartbeat, provider state, Fyers auth/status, and refresh/readiness endpoints.

### Known data gaps/pending work

- Theme/industry taxonomy and source coverage are not fully resolved.
- Some breadth enrichment/divergence work remains on the active task board.
- ChartsMaze OTP/session renewal is user-side and can produce degraded data.
- ETF exclusion and historical footprint recomputation remain task-board concerns.
- Stale historical rows and changing code versions require explicit version/freeze discipline.

## 4. Current recommendation path

### Candidate generation — Wired, legacy authority

- Deterministic universe filter, setup detectors, candidate gates/cascade, candidate scoring/rank, discovery bucket, focus list/themes, refusals, near misses, overrides, and organic/watchlist candidates.
- Candidate records include setup family/type, evidence/gates, plan fields, grade, rank, sector/industry, and outcomes.
- Later pre-registered testing found the late gate had no edge while the upstream discovery pool separated from random. Preserve retrieval and audit data; supersede the late gate as authority.

### Multi-model debate — Wired, legacy authority

- Multiple configured models return TAKE/SKIP, conviction, rank, bull/bear cases, and lens detail.
- Agent request/log tables persist model, prompt hash, latency, validation, and errors.
- Model weights use historical outcomes after a minimum history; a deterministic weighted aggregate creates the base verdict.
- Chair LLM may strike on portfolio concentration/correlation/event-risk grounds.

### Vision stage — Wired but incorrectly ordered for the new goal

- Renders daily and weekly charts for chair TAKE finalists only.
- A vision model can promote/demote rank, veto, or hold and stores its observation/reasoning.
- Because it runs after chair selection and only over TAKE finalists, it cannot be the primary chart-discovery authority.

### Sizer and signals — Wired

- Sizer consumes chair TAKE rows, validates plan/portfolio constraints, persists final quantity and TAKE/SKIP.
- Signal generator consumes sizer TAKE rows, formats evidence/risk/plan, stores signals, and optionally enqueues Telegram alerts.
- Transactional outbox, post-commit delivery, retry/failure states, reply capture, manual-execution notice, and live-disabled-by-default behavior are strong reusable reliability features.

## 5. Risk, trade planning, and live controls

### Risk engine — Wired and protected

- Single-writer trade-plan/risk calculations, regime governor, portfolio heat, position-size logic, stop/target/R:R and suggested quantity fields.
- Trader profile/account capital, position limits, exposure and heat behavior.
- Mechanical server-side actionability and TAKEN/SKIPPED decision records.
- No numeric change is authorized by the chart-first proposal.

### Live loop — Wired/partial

- Telegram digest, armed-list workflow, live FSM state/transitions, trigger/reply controls, outbox, push logs, and halt/kill-switch behavior.
- Live quote status/readiness/refresh/stream endpoints and heartbeat tables.
- Open lots/positions and position coach.
- Live entry pushes remain disabled by default; end-to-end live-data readiness still depends on provider/auth state.

## 6. Learning, audit, and research

### Decision/outcome ledger — Wired

- Candidates and candidate outcomes.
- Setup decisions, refusals, near misses, overrides, counterfactuals, watchlist candidates/outcomes, and position verdicts.
- Journal trades and open lots.
- Agent verdict outcomes, scorecard/funnel reports, track record, lessons, and screener calibration.

### Alpha/research schema — Wired or experimental

- Feature snapshots, activity signals, predictions, model registry, experiments, lineage, factor evaluation/health, ablations, plateau/failure memories, performance cones, decision memories/outcomes, and analogues.
- Alpha overview/leaders/activity/symbol/model/experiment APIs and active Alpha Lab views.
- Alpha memory, analogues, HMM/HAR, ML direction/breakout, and sector-downside models are experimental until separately validated.

### Edge testing — Wired as evidence/documentation

- Replay/backtest tools, edge finding reports, pre-registration, scorecards, outcome capture, and gate-comparison evidence.
- Current documented conclusion: late gate/council selection is not proven edge; discovery remains worth preserving and testing.

## 7. API and operations

### API breadth — Wired

Active routes cover:

- health/admin, live quote status/stream/refresh/readiness;
- regime, sectors, industries, indices, MBI/XP-related market payloads, breadth history/analytics;
- market desk, chart/chart-data/OHLC/search, focus/run card/track record/lessons/feed;
- scanners/presets/custom screens, watchlist, focus list, setups, decisions, refusals, near misses, overrides, organic candidates;
- debate/push, signal guide, positions, portfolio heat, flow, expectancy, journal;
- pipeline status/run and durable jobs/events/SSE/cancel/retry;
- coverage, ChartsMaze status, agent-model health;
- alpha overview/leaders/activity/research/model/experiment/symbol/memory endpoints;
- Fyers auth, mentor/guru checklists, advisor, footprint board/symbol, and trader profile.

### Durable work execution — Wired

- Scheduled update/orchestration, per-stage pipeline runs, durable job manifests, completion state, job events, SSE, retry, and cancellation.
- Data coverage/readiness/freshness mapping and visible degraded-state handling.
- Suitable for reusing as the chart-review job substrate.

## 8. Backend-only, partial, duplicate, or stale surfaces

The older built-but-unwired audit is not fully current, so these are classified conservatively:

- Regime-transition, experiment-detail, and some alpha-memory/analogue views have richer backend support than active UI.
- Near-miss/refusal, gate-health, journal-visual, EOD-alert, timing, portfolio-heat, advisor-note, and some position-coach routes are not all first-class destinations in the current active information architecture.
- Live quote SSE/readiness/refresh capability exists beyond what the ordinary user sees.
- Legacy watchlist and other duplicate route families remain and should be consolidated only after caller tracing.
- A dead/older `MarketTab` contains ideas not equivalent to the active `MarketHomeTab`; its presence does not prove those panels are mounted.
- `BUILT_BUT_UNWIRED_AUDIT.md` itself warns that it is endpoint-level and can become stale; current code was used where conflicts were found.

## 9. Design and documentation assets

### Frozen v5 design — Wired/protected

- Source of truth: `design/bakeoff/round4/debate_merged_light.html`.
- v5 tokens/primitives, typography, radius, shadows, accessibility constraints, and tab-scoped presentation.
- Current rebuild should change information architecture and authority semantics while retaining this visual language.

### Product/research documentation — Present

- Task board and owner/state guides.
- Edge findings, pre-registration, results, reconciliation, learnings, reliability/integrity audits, playbooks, footprint spec, and setup doctrine.
- `THE_ONE_SETUP.md`/PB-1 is a frozen research protocol with protected money numbers, not automatically the new live authority.

## 10. Rebuild disposition summary

| Capability | Disposition |
|---|---|
| Breadth layout, MBI/XP, index/sector/industry context | Keep and elevate |
| Activity score and Smart Money Flow Board | Keep as discovery/context; calibrate assumptions |
| Data ingestion, integrity, freshness, jobs, provider health | Keep |
| ChartDrawer/chart data and renderers | Keep; convert into immutable chart packs |
| Journal, outcomes, refusals, near misses, lessons | Keep as learning moat |
| Risk engine, portfolio heat, trade plan, position workflow | Keep; protect approved arithmetic |
| Telegram outbox/FSM/manual controls | Keep |
| Scanner/discovery lanes | Rebuild as broad high-recall retrieval |
| Deterministic pattern gates and candidate rank | Legacy baseline/features only |
| Multi-model debate/chair TAKE-SKIP | Retire as recommendation authority |
| Vision-after-chair stage | Replace with chart-first reviewer before final rank |
| HMM/HAR/ML/analogues/advisor | Quarantine/challenger research |
| Scanners + Shortlist + Debate navigation | Consolidate into Chart Queue |
| Alpha Lab | Reframe as Edge Lab tied to live decisions/evaluation |

## 11. Confidence statement

Certain: the files, active imports, route families, registered stages, schemas, and current council-to-sizer-to-signal path listed above exist in the audited repository.  
Likely: some backend-only features can be reused cheaply, but their field-level correctness and current data coverage must be verified during implementation.  
Unverified: predictive edge, live provider readiness on a given date, and the future accuracy of the proposed Chart AI.
