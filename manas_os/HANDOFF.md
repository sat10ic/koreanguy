# HANDOFF — Manas OS, session 2026-07-04

Status snapshot at the end of the session. Read this before continuing.
For scope/philosophy see `README.md`; for deferred scope see `FUTURE.md`.

## TL;DR

P0 was already done coming in. This session **built P1's first user-facing
surface — the Sectors & Themes panel** — end-to-end (backend → API → frontend),
plus a real **MARS (Moving Average Relative Strength)** pipeline that replaces
a weak breadth chip with benchmark-relative sector strength. All green: 40
tests, ruff clean, frontend builds. Two real bugs were caught and fixed in QC.

The rest of P1 (the XP/MBI/quadrant regime snapshot itself) is **not started**.

## What shipped this session

### 1. Sectors & Themes panel (the legacy `IndustryPanel.jsx` reborn)
A two-tab panel (Sectors / Themes) with horizontal color-coded bars, matching
the reference screenshot the user shared.

- **Backend** — `sources/chartsmaze.py` extended: new `parse_industry_analytics()`
  (pure, BOM-tolerant), `read_industry_analytics()`, and `run()` rewired to
  populate `sector_metrics` (RS% + MA breadth) and a new `industry_metrics`
  table (112 industries: 1D/1W/1M/3M perf, ranks, num_stocks, mcap, % from 52w high).
- **Schema** — `db/schema.sql`: added `industry_metrics` table.
- **API** — `api/app.py` + `api/__main__.py` (NEW, the dir was empty):
  FastAPI app, CORS for Vite, `GET /api/regime/sectors` (falls back to most-recent
  snapshot; `{available:false}` empty state). `python -m manas_os.api` → uvicorn :8000.
- **Frontend** — scaffolded from scratch (the dir was empty): Vite + React 18 +
  Tailwind. **`tailwind.config.js` maps `design/design_guidelines.json` tokens 1:1**
  (band colors, JetBrains Mono, hairlines, radii). `SectorsThemesPanel.jsx` +
  `App.jsx` shell. Honors design §7 state matrix (loading / empty / error / stale).

### 2. MARS pipeline (replaced the MA% chip)
The user pasted a Pine "Moving Average Relative Strength" script (© finallynitin,
concept dman103) and asked whether MARS would beat the MA-participation chip.
Answer: yes — MARS is benchmark-relative outperformance + structure, strictly
more informative. Built the full pipeline:

- **Math** — `regime/sectors.py` (NEW, pure): `compute_mars()`, 6-way
  `classify_state()` (Absolute/Relative/Gross × Out/Underperformance),
  `SECTOR_INDICES` (16 NSE sector indices), `BENCHMARK = NIFTYMIDSML400`.
  Adopted from the Pine source, not imported.
- **Provider** — `providers/fyers.py`: `fyers_symbol()` extended to map
  `NIFTY AUTO`/`NIFTYMIDSML400`/etc → `NSE:…-INDEX`; new `get_index_history()`.
- **Ingest** — `regime/mars_ingest.py` (NEW): 5th `run-eod` stage. Fetches sector
  + benchmark history, caches closes + SMA50 in new `sector_index_prices` table,
  computes + writes `mars_score`/`mars_state`. **Graceful skip when no Fyers token.**
- **Schema** — new `sector_index_prices` table; `mars_score`/`mars_state` columns
  on `sector_metrics` via idempotent in-place migration (`db/_migrate_add_columns`).
- **API** — `mars_score` + `mars_state` added to sector objects.
- **Frontend** — MA% chip → MARS chip: signed `+x.x`, 6-state band color
  (Absolute Outperformance = blue per Pine; Gross/Relative Out = green; under = red/orange),
  tooltip with plain-English state, **MA% fallback when MARS null**.

### 3. Tests added
`tests/test_chartsmaze.py` (+3), `tests/test_mars.py` (NEW, 10 — all 6 states +
SMA boundary + benchmark math), `tests/test_mars_ingest.py` (NEW, 3 —
success/skip/short-history). **40 tests total, all passing.**

## Bugs caught in QC (both fixed)

1. **Sector breadth never populated.** `sector-analytics-Moving Average-sectors.csv`
   carries `pct` as a string `"64%"`; my `isinstance(v,(int,float))` filter dropped
   every value. Also was wrongly writing one value into both `breadth_20_pct` and
   `breadth_50_pct`. Fix: parse via `_to_float`, store once as `breadth_50_pct`.
   Verified: 21/21 sectors now have breadth.
2. **Staleness overclaim → made real.** Panel docstring claimed stale detection
   but only rendered a caption. Implemented actual `isStale()` (>3 days) +
   `<StaleBanner>` (pulsing dot, warn band, 60% row dimming).
3. **API SELECT missing columns** (caught during MARS e2e). Added `mars_score`/
   `mars_state` to the row dict but not the SELECT clause → `sqlite3.Row`
   `IndexError`. The pytest suite missed it (different code path); only the real
   API call caught it. Fix: SELECT now includes all six columns.

## Current state

- **Tests:** `pytest -q` → **40 passed**.
- **Lint:** `ruff check` clean on all files touched this session.
- **Frontend:** `npm run build` → 1.4s, 33 modules.
- **Live data verified** against `legacy/SwingEdge/data/chartsmaze/2026-07-04/`:
  21 sectors + 112 industries populate; MARS compute verified via fixtures +
  fake provider.

## How to run

```bash
# 1. populate manas.db (chartsMaze data is at legacy/SwingEdge/data/chartsmaze/;
#    repoint sources.chartsmaze_dir in config.yaml, or run chartsmaze_migrate)
python manas.py run-eod --date 2026-07-04

# 2. for live MARS: log into Fyers once (token caches ~6am IST daily)
python -m manas_os.providers.fyers_auth

# 3. backend
python -m manas_os.api              # → 127.0.0.1:8000

# 4. frontend (other terminal)
cd manas_os/frontend && npm run dev # → localhost:5173
```

## Open / next

- **`manas_os/` is entirely untracked in git.** Should be committed.
- **MARS is wired but not live-verified** — no Fyers token cached this session.
  Compute path is fixture-verified; the real fetch runs next login + `run-eod`.
- **Sector label mismatch (known, deferred):** ChartsMaze labels sectors
  "Capital Goods" / "Healthcare"; MARS labels them "NIFTY AUTO" / "NIFTY IT".
  They show as two separate populations in the Sectors tab (37 rows, not ~15
  merged). A `sector_key` alias map would merge them — not done, decision pending.
- **Rest of P1 not started:** the XP dial math exists (`regime/xp.py`) but the
  MBI layer (4.5R, day-color, warning-day), the 4-pillar quadrant, and wiring
  the regime snapshot stage into `run-eod` are all still TODO.
- **Pre-existing ruff issues** in files not touched this session: 3 line-length
  in `providers/fyers.py`, unused import in `tests/test_bhavcopy.py`, import
  ordering in `cli/__init__.py`. Trivial cleanup if desired.
```
