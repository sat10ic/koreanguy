# CANONICAL — what is real in this repo

**Read this before touching anything.** Last verified: 2026-08-23, branch `emergent`.

This repo contains two products plus several dead ancestors that look alive. Every
fact below was verified by reading the files on 2026-08-23. If you change one of
these things, update this file **in the same commit** — a stale CANONICAL.md is
worse than none, because it is trusted.

Why this file exists: the session that designed TraderLog nearly built against an
abandoned frontend and a 4 KB dead database, because six directories and four
files share names with the real ones. Everything below is a trap that has already
caught somebody.

---

## 1. The two products

| | **Manas OS** | **TraderLog** |
|---|---|---|
| What | NSE swing-trading tool for the repo owner's own trading | Captures what OTHER traders post on X, reconstructs their trades |
| Root | `manas_os/` | `traderlog/` |
| Status | Live, in use | Under construction (see `traderlog/STATE.json`) |
| DB | `manas_os/data/manas.db` | `traderlog/data/traderlog.db` |
| API | `manas_os/api/app.py` :8000 | `traderlog/api/app.py` :8100 |
| UI | `manas_os/desk/` :5174 | `traderlog/ui/` :5180 |
| Tasks | `manas_os/TASKS.md` | `traderlog/TASKS.md` |

**They share no code.** TraderLog copies files it wants and owns the copies
(see §5). There is no `import manas_os` anywhere in `traderlog/`, and there must
never be one — a one-way door, same as Manas OS's rule about `legacy/`.

---

## 2. Databases — three of the four `manas.db` files are decoys

| Path | Size | Real? |
|---|---|---|
| `manas_os/data/manas.db` | ~717 MB | **YES — this is the live Manas OS database** |
| `manas.db` (repo root) | 4 KB | no — stale stub |
| `manas_os/db/manas.db` | 4 KB | no — stale stub |
| `manas_os/manas.db` | 0 bytes | no — empty |
| `traderlog/data/traderlog.db` | — | **YES — TraderLog's own, created by `traderlog.db.init_db()`** |

Never hardcode a DB path. Call `manas_os.db.connect()` or
`traderlog.db.connect()`. Both refuse to open the production DB from inside a
pytest run unless given an explicit path — that guard exists because the live
Manas OS DB was once polluted with synthetic ~100.0-close fixture rows by an
ad-hoc script that called `init_db()` with no argument.

---

## 3. Frontends — five directories, one is served

| Path | Status |
|---|---|
| `manas_os/desk/` | **LIVE.** Served by `manas_os/api/app.py` from `desk/dist`. React 18 + Vite, plain JS, plain CSS, light theme locked. 7 tabs. |
| `manas_os/deck/` | In-progress parallel rewrite. Only the TODAY screen exists. Not served. **Unresolved fork — do not add features here without deciding the fork first.** |
| `manas_os/terminal/` | Dead. One bulk commit (`28ce22ed`), never wired to any backend. Uses Tailwind + echarts, unlike the live app. |
| `manas_os/frontend/` | Dead. Superseded by `desk/` in July 2026. |
| `frontend/` (repo root) | Dead. Pre-`manas_os` SwingEdge era. |
| `legacy/frontend/` | Dead and quarantined. Source material only, never runtime. |
| `traderlog/ui/` | **LIVE for TraderLog.** |

---

## 4. Manas OS internals worth knowing

- **API shape:** one 9,000-line `manas_os/api/app.py`, 114 endpoints declared with
  `@app.get`/`@app.post` directly on `app`. No `APIRouter` anywhere. Business
  logic lives in `manas_os/<domain>/` packages; `app.py` is HTTP wiring only.
- **Schema:** `manas_os/db/schema.sql`, 888 lines, 51 tables, all
  `CREATE TABLE IF NOT EXISTS` so it re-runs harmlessly. Adding a column to an
  existing table goes through `_migrate_add_columns()` in `db/__init__.py`, not
  by editing the CREATE statement.
- **Ingestor contract:** every `manas_os/sources/*.py` exposes
  `run(conn, run_date) -> int`, does fetch → validate → upsert → log to
  `pipeline_runs`, and never raises. Registered in `_load_stages()` in
  `manas_os/cli/__init__.py`.
- **Scheduling:** Windows Task Scheduler, not cron and not APScheduler.
  "ManasOS-NightlyUpdate" at 19:15 IST.
- **Daily bars:** `bhavcopy_extractor/download_bhavcopy.py` (fetches NSE CSVs) →
  `manas_os/sources/bhavcopy.py` (parses + upserts `daily_prices`). Bhavcopy is
  canonical, **not** Fyers — Fyers is intraday `live_quotes` only and its rows
  lack delivery data.
- **LLM:** `manas_os/advisor/client.py`, OpenRouter over plain `urllib`, no SDK.
  Vision at `manas_os/agents/vision.py` (base64 `image_url` multimodal parts).
  Both gated off by default (`ai.enabled: false`, `agents.enabled: false`).
- **Telegram:** outbound only. `manas_os/alerts/outbox.py` is a real transactional
  outbox with a `delivery_ambiguous` state. **No inbound webhook exists** in
  either project.
- **Tests:** pytest, `manas_os/tests/` (132 files), run from inside `manas_os/`.

### Locked decisions that also bind TraderLog

Recorded in `manas_os/design/` and restated in `traderlog/design/DECISIONS.md`:

- **LLM proposes, never decides.** No model output may author a stop, a size, or
  a risk number.
- **Manual execution only.** No order routing, ever. Keeps the tools outside
  SEBI's algo framework and keeps the human veto.
- **No dormant code.** A module ships only if it is wired into a pipeline AND
  surfaced in the UI. Anything else gets deleted, not parked.
- **One writer per metric.** Exactly one module writes any given table column.
- **Adopt, never import** across the `legacy/` → `manas_os/` → `traderlog/`
  boundaries. Copy, rename, test, own it.
- **Light theme.** The dark reskin was cancelled (`RESKIN_DARK.md`).

---

## 5. What TraderLog adopts from Manas OS

Copies live in `traderlog/adopted/` with a provenance header naming the source
file and the date copied. Once copied they are TraderLog's, and drift between the
two copies is expected and fine.

| Adopted | From | Wave |
|---|---|---|
| Raw breadth counts (~38 metrics) | `manas_os/sources/breadth_counts.py` | W4 ✅ |
| Breadth ratio/analytics | `manas_os/regime/breadth_analytics.py` | Deferred — adopt only with a named API/UI consumer |
| Index-constituent breadth | `manas_os/sources/universe_breadth.py` + `manas_os/data/niftymidsml400_constituents.csv` | W4 ✅ |
| **XP dial reverse-engineering** | `manas_os/regime/xp.py` (whole file, 115 lines) | W4 ✅ |
| **MBI score reverse-engineering** | `manas_os/regime/snapshot.py:53-162` only — `ratio_from_pct_above`, `burst_ratio`, `band_ratio`, `band_r50`, `xp_band`, `band_r4p5`, `compute_mbi` | W4 ✅ |
| Volume reverse-engineering ("Reactor Scale") | `manas_os/alpha/activity.py`, `alpha/schema.py`, `engine/universe_filter.py` | W5 |
| Daily-bars ingestor | `manas_os/sources/bhavcopy.py` + `bhavcopy_extractor/` | W4 ✅ |
| OpenRouter client pattern | `manas_os/advisor/client.py` | W0 ✅ |
| Vision message shape | `manas_os/agents/vision.py` (≈15 lines, not the file) | W0 ✅ |
| Transactional outbox | `manas_os/alerts/outbox.py` | W7 |
| DB connect/init pattern | `manas_os/db/__init__.py` | W0 ✅ |
| Design tokens | `manas_os/desk/src/styles/tokens.v5.css` | W0 ✅ |

**Deliberately NOT adopted:** the desk app, the ML engine, positions, `scanner/`,
`risk/`, and — importantly — **the rest of `regime/snapshot.py`**: `compute_pillars`,
`market_mode`, `compute_quadrant`, `four_phase.py`, `choppy_brake.py`, and `run()`.
That is the *governor* layer, which exists to gate the user's own trading
decisions. TraderLog takes the XP and MBI **scores** and leaves the governor
behind: it measures other people's market reads, it does not gate anybody's
trades. The desk, ML engine, and positions were judged failures by the repo owner
and are not carried forward.

### Why XP and MBI are worth taking

Both are reverse-engineered practitioner constructs, and both are pure functions
over a `breadth_daily` row — together ~225 lines with no imports beyond `math`:

- **XP** (`regime/xp.py`) reproduces the finallynitin XP dial. It is a
  **recursion** on the prior day's XP and z-state:
  `z_state = 0.162·up4 + 0.838·z_prev`, then a six-term log model over
  `log(XP_prev)`, `log(z_state)`, `logit(10dma%)`, `log(decliners)`,
  `logit(20dma%)`. Two consequences: it needs a persisted prior value (seeded on
  first run from config), and **a gap in `breadth_daily` breaks the chain** —
  backfill in date order, never sparsely.
  Its docstring also warns that the advancer count must come from the same
  universe the weights were calibrated on (**NIFTYMIDSML400**), which is why
  `universe_breadth.py` and its constituents CSV are a hard dependency, not an
  optional extra.
- **MBI** (`regime/snapshot.py::compute_mbi`) reproduces the Stocksgeeks Market
  Breadth Indicator: `r10`/`r20`/`r50` from percent-above-DMA, `r4p5` as the
  4%-up/4%-down burst ratio, each banded GREEN/WHITE/RED (r50 uses its own 85/60
  cutoffs), summed into a day color and a warning-day flag when ≥3 bands are red.
  Source notes: `manas_os/design/knowledge/SG_MBI_DIGEST.md`.

For TraderLog they are the scoring spine of the BREADTH screen: a trader saying
"stay light today" can be scored against what XP and the MBI day color actually
were, and that agreement tracked over time. Without them the screen can only
quote opinions; with them it can grade them.

**Not the same thing as `MARKET_BREADTH_V2_REVERSE.md`.** That document
reverse-engineers Chhirag Kedia's Market Breadth Monitor V2.0 workbook, which
contains **no XP and no MBI column** — it is a separate count-and-ratio breadth
monitor whose flagship is the Fosback High-Low Logic Index. Useful later as
breadth *depth*; unrelated to the XP/MBI lift.

---

## 6. Single writer per TraderLog table

| Table | Sole writer |
|---|---|
| `traders` | `api/app.py` (user edits) + `seed_mock.py`; first-capture roster rows: `ingest/provisional_import.py` (owner-authorized 2026-08-23, atomic with capture) |
| `posts`, `post_media` | `ingest/xfetch.py` |
| `posts.deleted_at` | `ingest/deletions.py` |
| `post_class` | `llm/classify.py` |
| `post_media.vision_json` | `llm/vision.py` |
| `positions`, `position_events` | `llm/reconcile.py` |
| `review_queue` | `llm/link.py` (insert), `api/app.py` (resolve) |
| `breadth_notes`, `themes`, `edu_items` | `derive/insight_tables.py` (2026-08-25 wave; classify.py never wrote these) |
| `watch_ideas` | `derive/watchlists.py` |
| `edu_links` | `derive/preach.py` |
| `trader_style` | `derive/style.py` |
| `symbol_attention` | `derive/attention.py` |
| `attention_validation` | `derive/attention_validate.py` |
| `daily_prices` | `adopted/bhavcopy.py` |
| `breadth_counts`, `breadth_daily` | `adopted/breadth_counts.py` |
| `alpha_activity_signals` | `adopted/activity_pipeline.py` (W5 backfill; pure core + ported universe gates in `adopted/activity.py`) |
| `llm_runs` | `llm/provider.py` |
| `pipeline_runs` | any stage's `run()` |
| `telegram_outbox` | `adopted/telegram_outbox.py` (W7, 2026-08-25) |

If you need to write a table that is not yours, you are probably building the
wrong thing. Say so in `HANDOFF.md` rather than adding a second writer.

---

## 7. Where things belong

| Kind of artifact | Goes in |
|---|---|
| Locked decision | `traderlog/design/DECISIONS.md` (dated line) |
| Audit finding | `traderlog/design/AUDIT_LEDGER.md` (dated addendum, coded `C1`/`I1`) |
| Backlog item | `traderlog/TASKS.md` |
| Wave instructions for an executor model | `traderlog/design/handoffs/HANDOFF_<WAVE>_<topic>.md` |
| Executor's report back | the same name + `_COMPLETED.md` |
| Model-work provenance | `traderlog/design/MODEL_ATTRIBUTION.md` + append-only `design/MODEL_WORK_LOG.jsonl` |
| Standard completion report | `traderlog/design/handoffs/COMPLETION_TEMPLATE.md` |
| Session pickup state | `traderlog/HANDOFF.md` (prose) + `STATE.json` (generated) |
| Binding visual language | `traderlog/design/VISUAL_LANGUAGE.md` (read before `WIREFRAMES.md`) |
| Screen spec | `traderlog/design/WIREFRAMES.md` |
| Data/JSON contract | `traderlog/design/CONTRACTS.md` |
| Scratch scripts, one-off probes | **delete them when done.** Do not leave `_probe.py` at repo root — there are already ~15 there from Manas OS waves. |
