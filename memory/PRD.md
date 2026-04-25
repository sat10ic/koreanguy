# SwingEdge Lite — Dashboard PRD

## Original Problem Statement
> "Build me a dashboard for this tool.. understand the tool first"

The "tool" is **SwingEdge Lite**: a daily NSE swing-trading screener built on
Manas Arora's bread-and-butter setup combined with the Korean builder's
5-stage architecture (Regime → Screen → Verify → Track → Alert). Read-only
paper trading; no broker execution. Single-user analyst tool.

## User Choices (locked)
- **Architecture**: React + FastAPI dashboard (option 1A)
- **Data source**: Live data pipeline against the entire Nifty 500 universe.
  Primary fetcher = `yfinance` (works without auth in this container);
  Fyers REST + NSElib remain compatible drop-ins per spec.
- **Design**: Free design — sharper Bloomberg-terminal feel (option 3B)

## Architecture
```
fetch_yf.py    → ohlcv.db        (yfinance EOD bars; ~395 NSE syms + ^NSEI)
indicators.py  → features.db     (SMA/EMA/ATR/RSI/PD via custom pandas)
regime.py      → regime_today.json
screen.py      → screen_today.csv (full universe, graded)
verify.py      → candidates.csv  (Layer A + Layer B passes) + svro_arm_today.json
track.py       → portfolio_state.db (PENDING_CONFIRM → ACTIVE → EXITED_*)
─────────────────────────────────────────────────────────────────────
backend/server.py → FastAPI (reads everything above; exposes /api/*)
frontend/        → React + Tailwind + Recharts (terminal aesthetic)
```

## User Personas
- **Sunit** (the only user) — Indian equity swing trader who wants a 4-week
  ramp-up tool. Reads RS grids, candle setups, ATR multiples nightly. Trades
  manually on signals.

## Core Requirements (static)
- Display today's regime (RISK_ON/CAUTION/RISK_OFF) with 4 pillars
- Show universe breadth (bullish vs bearish bucket) and sector breakdown
- List primary verified candidates (watchlist trades) and secondary
- Track paper positions through the state machine, show P&L and stats
- Render the full Nifty 500 RS grid with all 16 grade columns (A+ to G)
- Manage watchlist (add/remove) and trigger the full daily pipeline manually

## What's been implemented (2026-04-25)
1. **Live data pipeline** — `scripts/fetch_yf.py` (yfinance), `indicators.py`
   (custom SMA/EMA/ATR/RSI), `run_pipeline.py` orchestrator chains all 6
   stages with progress callbacks. ~5 min for full Nifty 500 backfill (~250d).
2. **Universe expanded** to ~430 well-known Nifty 500 symbols with sector
   and industry tags in `universe.csv`.
3. **FastAPI backend** (`/app/backend/server.py`) with 17 endpoints:
   regime, universe/summary, screen, rs_grid, candidates,
   candidates/history, positions, watchlist (GET + POST add/remove),
   svro/arms, symbol/{symbol}, pipeline/status, pipeline/run, universe,
   config, health.
4. **React dashboard** (`/app/frontend`) — IBM Plex Sans + JetBrains Mono,
   pitch black background, 1px sharp borders, Bloomberg-terminal look.
   Components: RegimePanel, UniverseSummary, CandidatesPanel,
   PositionsPanel, RSGridPanel, WatchlistPanel, PipelineControl,
   HistoryChart, SymbolDrawer.
5. **Pipeline UI control** — header button triggers full daily run with
   live progress (`[FETCH] 135/426 32%`).
6. **Symbol detail drawer** — click any symbol anywhere → opens chart
   (close + SMA50 + SMA200), stat strip, recent 12-session table.
7. **Demo seeding** (one-time) — `scripts/seed_demo.py` populates 8
   realistic positions across all states + 30 days of history-chart data.
8. **Bug fixes** (iteration 2): watchlist NaN→500 fixed via robust
   coercion + universe validation; trash-icon Remove button fixed
   (removed `window.confirm`).

## Test Results
- iteration_1: 17/18 backend pass + 2 real bugs (watchlist 500, remove btn)
- iteration_2: 20/20 backend pass, frontend remove button works end-to-end

## Prioritized Backlog
### P0 — done
- Pipeline e2e + dashboard ✅
- Watchlist add/remove validation ✅
### P1 — next
- Re-fetch failed yfinance symbols (~30 / 426 had ticker mismatch)
- Persist pipeline run history (dates, stage durations) for the chart
- Sector concentration cap on primary list (max 3 per sector)
- Schedule auto-pipeline at NSE close (cron / supervisor task)
### P2 — later
- Phase 2 SVRO intraday monitor (per `LIVE_DATA_FLOW.md`)
- Cloudflare Pages mobile-friendly export
- Trailing stop at 20DMA + scale-in logic
- India VIX as 5th regime pillar
- Walk-forward replay UI
- Telegram alerts integration (the `notify.py` script exists but not surfaced)

## Known Limitations
- yfinance ticker mismatches: ~30 NSE symbols failed (e.g., AVENUE / SPICEJET — yahoo
  uses different suffixes). Re-fetch path planned.
- 8 positions are demo-seeded (`scripts/seed_demo.py`, idempotent) for the
  initial wow moment; clear with `DELETE FROM positions WHERE notes LIKE '%DEMO_SEED%'`.
- Today's primary candidates count is **0** — genuine output: only 4 stocks
  passed `setup_pass` and none had A-tier grade stability. Per spec, this is
  the intended strict behavior.
- NSE & niftyindices.com block the cloud IP — that's why nselib/Fyers can't
  fetch from this container. yfinance works because it routes via Yahoo.

## Next Action Items
- Re-run pipeline daily once user supplies Fyers token (or accept yfinance EOD)
- Calibrate Layer A thresholds after 30 sessions per `decisions.md` #6
- Build out historical candidate count from real pipeline runs (replace demo seed)
