# TRADERLOG COMPLETE OVERHAUL — "make it actually useful"

Owner-approved direction (2026-08-26): a complete overhaul is needed to make
the tool actually useful. Recorded decisions from the owner:

- Access URL: `http://127.0.0.1:8100` (if the owner cannot see the RADAR tab /
  TradingView charts there, serving/caching/runtime is broken — diagnose, do
  not redesign blind).
- Daily engine: MANUAL for now ("will make it live when the overall tool is
  actually good enough"). No scheduler installation in this overhaul.
- LLM backlog (~293 un-reconciled threads): DEFERRED ("let's fix the tool's
  usefulness first"). No paid/smart-tier spend without explicit approval.

## Goal (one line)

Turn TraderLog from an untidy, partly-fabricated UI over a half-run pipeline
into an insight instrument whose every number is real, whose screens answer
"what are these traders doing RIGHT NOW", and whose engine one command can
refresh — with zero invented data and zero LLM spend until the owner approves
it.

## Ground truth established 2026-08-26 (verified read-only)

- The DB is NOT empty: 3,395 posts, 305 positions, 17 traders, breadth (431
  regime_daily rows), 549 edu_items, 1.34M daily_prices, 536k alpha signals.
  Batches landed Aug 24-26 (STATE.json agrees; pre-batch backups exist).
- A RADAR tab (replacing IDEAS) exists in source AND the built dist
  (2026-08-26), including a Stock Terminal with a real TradingView
  lightweight-charts candlestick (`ui/src/components/TradingViewChart.jsx`,
  `lightweight-charts ^5.2.1` installed) plus `derive/radar.py` + `derive/tape.py`.
- `run_recon.py` orchestrator exists (classify → reconcile → link → insight);
  W4 breadth (`run_w4.py`) and W5 activity (`run_w5.py`) have run.
- Real defects found by exploration:
  - `Traders.jsx` hardcodes fake fallback KPIs ("100%" win rate, "3d" median
    hold, "65%" stop discipline) when `trader_style` is empty.
  - `Breadth.jsx` hardcodes XP "42.0" / MBI "GREEN" / "3 of 4 bands"
    fallbacks, a hardcoded sample Theme Rotation Matrix, a hardcoded "284
    verified breadth notes" line, and imports BandLine/Ribbon that are
    computed but never rendered (dead code).
  - ~293 roots remain un-reconciled (rate-wall stopped paid calls);
    TASKS item (C) still open.
  - Nothing chains ingest → recon → breadth → insights daily; parts of the
    corpus were processed by ad-hoc scripts that no longer exist on disk.
  - Owner sees none of the new tabs on :8100 despite the dist containing
    them — serving/caching/runtime failure to be diagnosed, not assumed.

## Phases (execute in order; each has a done-test and closes with its own
verification + MODEL_WORK_LOG records per `design/MODEL_ATTRIBUTION.md`)

### PHASE 0 — Diagnose what :8100 actually serves (no code changes)

1. Verify the API process, served index.html vs dist on disk, asset 404s,
   browser-cache staleness; kill stale processes; establish ONE canonical
   serve command (`python traderlog/run_api.py`).
2. Real-browser sweep at 1920×1080 of every tab: console errors, failed API
   calls, render breakage — especially RADAR's Stock Terminal chart across
   top symbols (owner says charts don't exist; they are in the bundle — find
   out why they don't render).
3. Read-only DB audit: closed vs open positions, @iManasArora coverage (his
   posts vs reconciled positions vs closes vs the un-reconciled backlog),
   newest position/post dates — to size the "ledger is stale / nothing
   closed" complaint honestly.

Done-test: a written defect list with evidence; app loads clean at :8100 with
RADAR visible.

### PHASE 1 — Kill every lie (truth pass)

Files: `ui/src/screens/Traders.jsx`, `ui/src/screens/Breadth.jsx` (+ tests).

1. Remove ALL hardcoded fallback metrics — fake "100%/3d/65%" KPIs, fake XP
   42.0/MBI GREEN, sample theme matrix, "284 verified notes" copy. Every
   empty state says "not enough data yet" honestly; every number traces to a
   payload field.
2. Delete or wire the dead BandLine/Ribbon code in Breadth (real XP history +
   MBI ribbon exist in the payload — render them).
3. Regression tests asserting no fabricated values can render.

Done-test: grep shows zero hardcoded metric literals; screenshots show honest
empty states; suite green.

### PHASE 2 — LEDGER becomes the latest-moves engine

Files: `ui/src/screens/Ledger.jsx`, `api/app.py` (read-shape only if needed),
tests.

1. Default view = newest activity first (sort by latest event/thread
   timestamp, not opened_at), with open/closed filter chips and closed trades
   fully visible with stated results.
2. The shared-axis timeline becomes a "recent moves" band (last N weeks)
   instead of an unusable 305-row megachart; the table carries full history
   below with pagination/filter.
3. Honest backlog line: "N threads await reconciliation — approve LLM spend
   to finish" (from a real count; no silent gaps in Manas's record).

Done-test: browser test proves newest-first ordering, closed rows visible
with stated results, backlog count matches DB truth.

### PHASE 3 — FEED becomes an insight digest, not a post list

Files: `ui/src/screens/Feed.jsx` (+ api read join if a field is missing —
additive only), tests.

1. Top panel "MOVES" — since-last-look digest: new entries, adds, stop moves,
   partial/full exits, closed results, deleted posts (bias warning), across
   traders, built from existing `/api/feed` + `/api/positions` payloads
   (client-side; no new contract unless a gap is proven, then CONTRACTS.md
   first).
2. Below it, the existing thread workspace (kept from W3c) filtered to trade
   events by default; prose/insight hierarchy per VISUAL_LANGUAGE §1a.

Done-test: browser test proves the digest renders real recent moves with
citations; zero invented fields.

### PHASE 4 — RADAR + Stock Terminal as the analytics centerpiece

Files: `ui/src/screens/Radar.jsx`, `derive/radar.py` + `derive/tape.py` (read
paths), tests.

1. Fix whatever Phase 0 found breaking charts (asset/runtime/data gaps);
   charts must render for every convergent symbol with price history.
2. Make RADAR the default landing tab (FEED stays one click away), since
   "what are they converging on + price context" is the insight the owner
   actually wanted.
3. Deepen the terminal only with data that exists: event markers, vision S/R
   lines, forward returns (tape), attention context from alpha signals.

Done-test: every symbol card opens a chart or an honest "no price history"
state; zero console errors.

### PHASE 5 — Depth on TRADERS / BREADTH / LIBRARY with real data only

1. TRADERS: real trader_style stats (17 rows exist), CORE-lens for Manas (his
   open book, closes, un-reconciled count), practice-vs-preach only when
   edu_links have data — else honest empty states.
2. BREADTH: live regime history (BandLine), MBI ribbon, stance agreement from
   real breadth_notes; XP/MBI scoring footnote kept.
3. LIBRARY: wire the existing topic filter + search to the 549 items; link
   principles to positions where edu_links exist.

Done-test: each screen shows real rows or honest empty states; no
placeholders.

### PHASE 6 — One-command engine + backlog ready, no spend without approval

Files: `traderlog/run_daily.py` (new, thin), docs.

1. Single manual command chaining: xfetch (if profile ready) → run_recon
   (classify/reconcile/link/insight) → run_w4 breadth →
   style/watchlists/insight refresh; idempotent, resumable, prints a cost
   ledger BEFORE any paid stage and skips LLM stages unless `--spend` is
   passed.
2. `python traderlog/run_daily.py --resume-manas` prepared for the 293-thread
   backlog, NOT executed (owner decision: usefulness first; spend later).
3. HANDOFF/TASKS updated; MODEL_WORK_LOG records per phase per
   `design/MODEL_ATTRIBUTION.md`.

Done-test: dry-run of run_daily.py touches no paid API and exits clean; suite
+ run_checks green.

### PHASE 7 — Final acceptance

1920×1080 real-browser sweep of all tabs (screenshots to
`output/playwright/`), zero console errors/warnings, zero ≥400s,
`cd traderlog/ui && npm run build`, `pytest traderlog/tests -q` (175+),
`python traderlog/run_checks.py`, `git diff --check`. No commits — the
maintainer QCs.

## Constraints honored throughout

- Production DB never seeded/mutated by tests (disposable DBs only; read-only
  audits allowed).
- No X-capture automation (manual per owner answer).
- No LLM spend without explicit owner approval.
- No API contract change without CONTRACTS.md first.
- Repo governance followed (`traderlog/AGENTS.md`, `design/MODEL_ATTRIBUTION.md`
  ledger records, handoff completion reports, TASKS/HANDOFF updates at each
  close).
- Nothing committed.
