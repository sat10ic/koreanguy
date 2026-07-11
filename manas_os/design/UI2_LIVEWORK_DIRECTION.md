# UI-2 BUILD DIRECTION — Durable Live Work (jobs / events / SSE / inspector)

Date: 2026-07-11 · Author: Fable director pass · Status: **DIRECTION OF RECORD for the UI-2 slice**
Parents: `UI_OVERHAUL_HANDOFF.md` §2/§5/§6/§11 (P0-1, #1 blocker) · `CODEX_HANDOFF.md` §Q3, §2 LOCKED, §3 env quirks.

> **VISUAL AUTHORITY — USER-LOCKED:** UI-2c is not a new design pass. It must extend the
> Round-4 bakeoff source of truth at `design/bakeoff/round4/debate_merged_light.html` and the
> corresponding `UI_BUILD_DIRECTION.md` v5 LIGHT rules. Do not introduce a separate aesthetic,
> palette, typography, spacing language, or generic dashboard treatment for Live Work.
Audience: one Sonnet coder per sub-slice + code/UX reviewers running the §7 QC loop. This is
architecture + integration, **not code**. Deviations → flag, don't silently re-decide.

## 0. Goal and done-test

**Goal:** the user watches the nightly build happen — downloads, 26 stages, scans, agent
branches, chart generation, watchlist mutations, failures and retries — live, without refresh,
and the record survives an API restart.

**Done-test (from handoff §6 UI-2):** a fixture job and one real `run-eod` visibly progress in
the Live Work inspector without refresh; a client that disconnects/reconnects (or falls back to
polling) resumes with **zero duplicate and zero lost events**; previously confirmed desk data
stays on screen the whole time; `/api/pipeline/status` and the existing header string keep
working untouched until 2c swaps the consumers.

## 1. Verified current machinery (what we integrate WITH — do not rediscover)

- **Stage list:** `manas_os/cli/__init__.py::_load_stages()` — the single ordered registry of
  the 26 `(name, fn)` stages, `fn(conn, run_date)`, e.g. `ingest_bhavcopy … telegram_digest`.
  `_cmd_run_eod` iterates it with per-stage try/except isolation.
- **API runner:** `manas_os/api/app.py::_run_pipeline_thread` (~line 3105) runs the same
  stages in a daemon thread, mutating in-memory `_PIPELINE_STATUS` under `_PIPELINE_LOCK`.
  `_fetch_source_files` (~3130) adds two subprocess pre-steps `fetch_bhavcopy` /
  `fetch_chartsmaze`. `POST /api/pipeline/run` kicks off; `GET /api/pipeline/status` (~3202)
  derives `stage_index/total_stages/eta_seconds/data_live_hint/last_run`. **All state is
  in-memory → lost on restart. This is the gap.**
- **Existing per-stage ledger:** `pipeline_runs` table (schema.sql ~400) — stages themselves
  write one row each (status/rows_affected/duration_s). It stays the stage-health source of
  truth; jobs/events are a *narrative* layer, not a replacement.
- **Frontend today:** `desk/src/App.jsx` — `pollRef` interval hits `getPipelineStatus()` after
  a run is triggered and renders only `pipeline running - <stage>` (~line 459).
  `desk/src/MarketHomeTab.jsx::PipelineProgress` (line 169) fetches status **once on mount**
  (bar can never advance); "Activity log" placeholder at lines 338-339.
- **v5 system:** `desk/src/styles/tokens.v5.css` + `desk/src/components/v5/` (Panel,
  SectionLabel, StatusChip, VerdictChip, Sparkline, CommandStrip, TickerTape, LaneCard,
  GateCell, StruckNote, …). Build the inspector from these.
- **DB conventions:** `db/schema.sql` idempotent `CREATE TABLE IF NOT EXISTS`, ISO dates,
  append/point-in-time discipline; column adds via guarded `_migrate_add_columns` in
  `db/__init__.py`. New tables = append to schema.sql. **No destructive migration.**

## 2. Architecture in one paragraph

A new module `manas_os/jobs.py` owns a `jobs / job_steps / job_events / job_artifacts` layer in
`manas.db`. The **only writer** of job state is the thread already running the pipeline (API
runner thread or CLI process) via a `JobEmitter` handle; stages are untouched (fixed
`fn(conn, run_date)` signature) — the emitter wraps the existing loop, plus an *optional*
module-level `jobs.emit(type, **payload)` (contextvar-bound, no-op when no active job) that a
handful of high-value inner call-sites use for sub-stage events. `job_events.event_id`
(AUTOINCREMENT) is the monotonic cursor; events are append-only facts, never updated. Reads —
`GET /api/jobs/{id}/events` (cursor page) and `.../events/stream` (SSE) — are both implemented
as the **same cursor query**; SSE is just the server tailing that query on a short interval and
pushing rows, so replay, polling fallback, and restart recovery are one mechanism, not three.
`_PIPELINE_STATUS` and `/api/pipeline/status` are left byte-for-byte alone during the migration.

## 3. SCHEMA (sub-slice 2a) — additive, append to `db/schema.sql`

```sql
-- UI-2 Q3: durable Live Work. Append-only narrative layer over pipeline_runs.
CREATE TABLE IF NOT EXISTS jobs (
    job_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    kind          TEXT NOT NULL,                 -- 'run_eod' (only kind in UI-2)
    run_date      TEXT,                          -- ISO trade date the job builds
    status        TEXT NOT NULL DEFAULT 'queued',-- queued|running|succeeded|partial|failed|cancelled|interrupted
    requested_by  TEXT DEFAULT 'ui',             -- 'ui' | 'cli' | 'schtask'
    params_json   TEXT,                          -- {fetch_sources: bool, ...}
    pid           INTEGER,                       -- writer process id (orphan detection)
    started_at    TEXT, finished_at TEXT,
    heartbeat_at  TEXT,                          -- runner touches every stage boundary
    error         TEXT,
    created_at    TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_jobs_kind_date ON jobs(kind, run_date);

CREATE TABLE IF NOT EXISTS job_steps (
    step_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id      INTEGER NOT NULL REFERENCES jobs(job_id),
    seq         INTEGER NOT NULL,                -- 1-based position in the planned rail
    name        TEXT NOT NULL,                   -- 'fetch_bhavcopy' | stage name from _load_stages()
    attempt     INTEGER NOT NULL DEFAULT 1,      -- retry appends attempt=2 row; never mutates attempt 1
    status      TEXT NOT NULL DEFAULT 'pending', -- pending|running|ok|fail|skip|cancelled
    started_at  TEXT, finished_at TEXT,
    duration_s  REAL, rows_affected INTEGER,
    detail      TEXT, error TEXT,
    UNIQUE (job_id, seq, attempt)
);
CREATE INDEX IF NOT EXISTS idx_job_steps_job ON job_steps(job_id);

CREATE TABLE IF NOT EXISTS job_events (
    event_id    INTEGER PRIMARY KEY AUTOINCREMENT, -- THE monotonic cursor (global, gapless-enough, strictly increasing)
    job_id      INTEGER NOT NULL REFERENCES jobs(job_id),
    step_id     INTEGER,                           -- null for job-level events
    event_type  TEXT NOT NULL,                     -- enum, §4
    payload_json TEXT,                             -- small; big things are artifacts
    created_at  TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_job_events_job ON job_events(job_id, event_id);

CREATE TABLE IF NOT EXISTS job_artifacts (
    artifact_id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id      INTEGER NOT NULL REFERENCES jobs(job_id),
    step_id     INTEGER,
    kind        TEXT NOT NULL,                   -- 'chart'|'file'|'summary'|'route'
    ref         TEXT NOT NULL,                   -- API route / repo-relative path — never absolute machine paths
    label       TEXT, meta_json TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_job_artifacts_job ON job_artifacts(job_id);
```

Design invariants (reviewer checks these):
- **Append-only truth:** rows in `job_events`/`job_artifacts` are never UPDATEd or DELETEd.
  `jobs`/`job_steps` rows update *status columns only*, and every status transition also
  appends a corresponding event — the event log alone can reconstruct the job.
- **Cursor:** `event_id` AUTOINCREMENT is strictly increasing per DB; "give me everything after
  cursor C for job J" is `WHERE job_id=? AND event_id>? ORDER BY event_id` — restart-safe and
  duplicate-free by construction. No timestamps as cursors (same-second collisions).
- **Retry = new attempt row + new events.** Nothing is rewritten, matching point-in-time
  discipline; UI shows attempt 2 after a visible `retry_started`.
- **Orphan recovery:** on API startup (and on `GET /api/jobs` reads), any job with
  `status='running'` whose `pid` is not alive (or `heartbeat_at` > 15 min stale) is finalized
  to `interrupted` with a terminal `job_finished {status:'interrupted'}` event. Honest state —
  never leave a zombie "running".
- `pipeline_runs` untouched; stages keep writing it exactly as today (two ledgers, two
  different writers, no overlap of columns of authority).

## 4. EVENT EMISSION (sub-slice 2a) — thin hooks, zero pipeline rewrite

**One writer discipline:** the only code that writes jobs tables is `manas_os/jobs.py`, and the
only caller of its write API is the thread/process running the job. Stages never get a new
parameter; the emitter is ambient.

New module `manas_os/jobs.py`:
- `class JobEmitter` — holds the job's *own* sqlite connection (the runner already owns one),
  methods `job_started/step_started/step_finished/step_failed/event(type, **payload)/
  artifact(kind, ref, ...)/job_finished(status)`. Each write is one small INSERT/UPDATE +
  commit (short transactions; the DB is also being written by stages — never hold a
  transaction across a stage call).
- `emit(event_type, **payload)` + `add_artifact(...)` — **module-level, contextvar-bound**
  no-ops unless a `JobEmitter` is active. This is the entire "hook API" inner code sees; it can
  never fail the pipeline (all writes wrapped, exceptions swallowed + logged — telemetry must
  not break the run).
- `run_stages(conn, run_date, stages, *, requested_by, fetch_sources)` — shared runner used by
  BOTH `api/app.py::_run_pipeline_thread` and `cli/__init__.py::_cmd_run_eod`, so UI-triggered
  and scheduled/CLI runs both produce jobs. It reproduces today's loop semantics exactly
  (per-stage try/except isolation, continue on failure).

### Integration points (exact, and only these in 2a)

| Event type | Emitted from | Payload |
|---|---|---|
| `job_started` | `jobs.run_stages` entry; plans the full rail (INSERT one `job_steps` row per stage, `pending`) | {run_date, total_steps, fetch_sources} |
| `source_fetch_started/finished` | `api/app.py::_fetch_source_files::_step` (wrap the two `_step` calls; they become planned steps seq 1-2 when `fetch_sources`) | {name, status, exit/timeout detail} |
| `stage_started` | runner loop, before `fn(conn, run_date)` — same spot that sets `_PIPELINE_STATUS["current_stage"]` today | {name, seq} |
| `stage_finished` | runner loop after success; copies `rows_affected/duration_s/detail` for this stage+date from the `pipeline_runs` row the stage just wrote (read-back, not re-computed) | {name, seq, rows_affected, duration_s} |
| `stage_failed` | runner loop `except` branch — the existing per-stage isolation IS the failure hook; capture `repr(exc)` (no secrets: never echo config values) | {name, seq, error} |
| `retry_started` | `POST /api/jobs/{id}/steps/{step_id}/retry` handler (2b) before re-running that one stage as attempt+1 | {name, attempt} |
| `job_finished` | runner `finally` | {status: succeeded / partial (any stage failed) / failed (job-level crash) / cancelled / interrupted, ok_count, fail_count} |

### Inner (sub-stage) emissions — optional calls to `jobs.emit()`, small diffs, no signatures changed

Instrument in 2a only if trivially clean, otherwise defer to 2b polish; each is 1-3 lines at an
existing call-site:
- **Scan narrowing:** `scanner/candidates.py` end of `run` — `emit("scan_summary",
  pool=..., refused=..., actionable=...)` (the 2370→237→0 funnel numbers it already computes).
- **Agent/mechanism branches:** `agents/debate.py` where it already writes
  `scan_agent_logs` / per-model verdicts — `emit("agent_branch", symbol, teacher/mechanism
  (post-Q2; model name until then), model, verdict, latency_ms)`. Mirror of an existing log
  write, not new computation.
- **Watchlist mutations:** `agents/watchlist.py` where PROMOTE/HOLD/DEMOTE/DROP events are
  persisted — `emit("watchlist_event", symbol, action, reason)`.
- **Chart generation:** wherever nightly chart images/routes are produced —
  `add_artifact("chart", ref=<existing chart API route>, label=symbol)`. If charts are
  render-on-demand only, skip: **never invent an artifact**.
- **Warnings:** failure-safe skips (mars/fii_dii/hmm "graceful skip") — `emit("warning",
  name, reason)` where the skip is decided, so "skipped, why" is visible, not silent.

Rule for the coder: an inner emit that would require refactoring to reach the data **is out of
scope** — flag it instead. Emission is decoration on existing seams.

## 5. API: SSE + cursor polling fallback (sub-slice 2b)

Endpoints (per Q3), all in `api/app.py`:
- `POST /api/jobs` `{kind:'run_eod', date?, fetch_sources?}` — thin alias over the existing
  `pipeline_run` body: same lock, same thread, but the thread now runs `jobs.run_stages`.
  Returns `{job_id, started:true}` (or the running job's id with `started:false` — one job at a
  time, as today).
- `GET /api/jobs?limit=N` — recent jobs incl. orphan-finalized ones (feeds "last night's
  activity" when idle).
- `GET /api/jobs/{id}` — job row + all `job_steps` (the rail snapshot) + latest cursor.
- `GET /api/jobs/{id}/events?after=<cursor>&limit=500` — **the polling fallback and the replay
  primitive.** Returns `{job, events:[{event_id, event_type, step_id, payload, created_at}],
  next_cursor}`. Strict `event_id > after` ordering; a page never contains a duplicate.
- `GET /api/jobs/{id}/events/stream?after=<cursor>` — SSE (`text/event-stream`). Honors
  `Last-Event-ID` header (browser auto-reconnect) with `after` param as fallback. Generator
  loop: open a **short-lived read connection per tick** (don't hold locks against a
  scan-writing pipeline; `busy_timeout` small, skip a tick on lock), `SELECT … event_id>cursor
  ORDER BY event_id LIMIT 200`, yield each row as `id: <event_id>\nevent: <type>\ndata:
  <json>\n\n`; every ~15s a `: ping` comment; when the job row is terminal AND no rows remain →
  `event: done` then close. Tail interval ~0.7s — no in-process pub/sub, no queues: **SSE is a
  server-side tail of the exact same cursor query the fallback uses.**
- `POST /api/jobs/{id}/cancel` — cooperative: sets a cancel flag row/column; the runner checks
  it between stages (never mid-stage), finalizes `cancelled`. In-flight stage completes.
- `POST /api/jobs/{id}/steps/{step_id}/retry` — allowed only on a terminal job's failed step;
  re-runs that single stage (stages are idempotent upserts by natural key — that's what makes
  this safe) as `attempt+1` in a short-lived thread, emitting `retry_started` → step events →
  `job_finished` update if it flips partial→succeeded.

**Restart-safe replay, end to end:** client remembers `last event_id` (in-memory + router
state). On reconnect — same process or a restarted API — it asks `after=<cursor>`; because the
cursor is a DB primary key, the answer is identical either way. A client with no cursor does
`GET /api/jobs/{id}` (rail snapshot + latest cursor) then streams from there — snapshot-then-
tail, so a full event replay isn't needed to paint the rail.

**Fallback trigger (env quirk §3: the sandbox browser can't hold streams / fetch to :8000):**
frontend tries `EventSource`; if it doesn't reach `readyState OPEN` within 4s, or errors twice
within 30s, tear it down and switch to 2s cursor polling of `/events`. Both paths feed one
reducer keyed by `event_id`; the reducer ignores `event_id <= lastSeen` — belt-and-braces dedup
even though the server contract already guarantees it.

## 6. FRONTEND: Live Work inspector (sub-slice 2c) — v5 system

New `desk/src/livework/`:
- `useJobStream.js` — the hook: resolve active/latest job (`GET /api/jobs?limit=1` + refresh
  when a run is triggered) → snapshot (`GET /api/jobs/{id}`) → SSE-with-fallback tail →
  `{job, steps[], events[], artifacts[], transport:'sse'|'poll', cursor}` via a single reducer.
  One instance at app level (context), consumed by all surfaces — replaces the current
  scattered `pollRef` logic as the *one* live-work state owner.
- `LiveWorkInspector.jsx` — right-side inspector per handoff §5 Shell. Since the full shell
  recompose is not yet done (§11), 2c mounts it as a **right-side drawer** toggled from the
  Wave-1 `CommandStrip` (and auto-opened when a run starts), built so UI-3's shell can adopt it
  as the permanent inspector pane unchanged. On narrow screens it is a bottom sheet.
  Composition (v5 primitives; new primitives only if listed):
  - **Header band:** job kind + run_date, elapsed, `StatusChip` (RUNNING/PARTIAL/DONE/
    INTERRUPTED — honest states, interrupted is shown as interrupted, never as done),
    ETA line reusing the server's `eta_seconds` idiom, cancel button.
  - **Stage rail** (new primitive `StageRail.jsx` + `StepRow.jsx`): the planned 26(+2 fetch)
    steps from `job_steps`, filling top-down — pending (ink-faint tick), running (single subtle
    pulse), ok / fail / skip (`StatusChip` semantics, never colour-only: glyph + label).
    Numbers (`duration_s`, rows) in Plex Mono via existing token classes.
  - **Event feed:** newest-first inserts under the running step (spatial continuity); rows are
    plain-language (`"Scan narrowed 2,370 → 237 candidates"`, `"GROWW: chair verdict SKIP"`,
    `"ingest_mars skipped — Fyers unavailable"`). Failures render inline with the error detail
    behind a disclosure; a failed stage never hides subsequent progress.
  - **Artifacts:** `job_artifacts` rows as small reveal chips (chart thumbnails via existing
    chart route, ChartDrawer on click). Reveal, don't autoplay.
  - **Idle state:** last completed job's summary + its final events ("Built 2026-07-10 desk at
    19:42 — 24 ok · 1 skip · 1 fail") — this **replaces the Activity-log placeholder** content.
- **No full-surface loading, ever:** the inspector renders over/next to confirmed desk data;
  its own loading is skeleton rows inside the drawer only. Confirmed tab data is never
  unmounted by job activity.

### Replacements (the point of 2c)
1. `App.jsx` header `pipeline running - <stage>` span + `pollRef` interval → deleted; the
   header shows a compact live dot + stage count sourced from `useJobStream` context, click =
   open inspector. (`/api/pipeline/status` itself remains live for anything not yet migrated.)
2. `MarketHomeTab.jsx::PipelineProgress` (one-shot fetch, frozen bar) → deleted; MARKET shows a
   thin live strip fed by the same context (full MARKET inspector integration is UI-3's job).
3. `MarketHomeTab.jsx` lines 338-339 Activity-log placeholder → last-job summary block from
   `useJobStream` (real backend reads at last).
Superseded code is deleted in the same wave (pipeline-hygiene), *after* screenshot parity.

### A11y / motion
- `prefers-reduced-motion`: rail segments fill **once** (no looping/indeterminate shimmer
  anywhere — even without reduced-motion the running pulse is a single 150-250ms mark-change,
  the house idiom); event inserts appear without slide animation.
- Feed is `role="log"` `aria-live="polite"`; step statuses are text+glyph, not colour-only;
  drawer is keyboard-openable/closable with focus trap; counts/ETA readable at AA contrast
  (no `--ink-faint` for essential copy).
- Never animate money numbers (nothing here should touch them anyway — see §7).

## 7. GUARDRAILS (binding; reviewer rejects violations)

1. **`run-eod` behaviour is unchanged.** Same stages, same order, same per-stage isolation,
   same `pipeline_runs` writes. If `jobs.py` import or any emit raises, the run continues —
   telemetry is sacrificial. Proof: pytest green + one real `run-eod` diff of `pipeline_runs`
   rows pre/post-change shape.
2. **`/api/pipeline/status` keeps working byte-compatible** through 2a-2c (the in-memory
   `_PIPELINE_STATUS` updates stay in place beside the emitter). It is retired only in a later
   wave after nothing consumes it.
3. **No money-math touch.** Nothing in this slice imports or is imported by `risk/plan.py`;
   events carry *narrative* about stop/size decisions only if a stage already surfaces them —
   never recomputed, never mutated (one-writer invariant, CODEX §1).
4. **Append-only truth** (§3 invariants). Retries append; nothing rewrites history; honest
   terminal states incl. `interrupted` and `partial` — a partial night must say so, not decorate.
5. **Secrets:** event payloads/errors must never include config values (telegram token, Fyers
   creds — repo is PUBLIC). Error capture is `repr(exc)` of stage exceptions only; extractor
   subprocess output is truncated to exit-status detail.
6. **DB discipline:** additive schema only; tests never touch prod `manas.db` (fixture DB via
   explicit path per §3 env quirks); no long transactions from readers (SSE tick opens
   short-lived read connections); never run a fixture full-scan concurrently with API writes.
7. **Env quirks honored:** API needs manual restart per backend change (`build_sha ==
   repo_head` before any "verified live" claim); sandbox browser can't fetch/hold streams →
   SSE proof is curl-level (`curl -N`) + the poll fallback is the sandbox-verifiable path;
   `PYTHONIOENCODING=utf-8`, no `₹` in console prints.
8. **v5 only:** inspector uses tokens.v5.css + `components/v5`; the only new primitives are
   `StageRail`/`StepRow` (+ `EventRow` if needed), added to `components/v5` with the same
   conventions. No new chart/animation deps (ECharts remains rejected).

## 8. WAVE BREAKDOWN — three Sonnet-sized sub-slices, §7 QC loop each

### 2a — Schema + jobs module + emit hooks + poll read API
- **Files:** `db/schema.sql` (append §3 tables), `manas_os/jobs.py` (new),
  `api/app.py` (`_run_pipeline_thread`/`_fetch_source_files` call the shared runner; add
  `POST /api/jobs`, `GET /api/jobs`, `GET /api/jobs/{id}`, `GET /api/jobs/{id}/events` —
  poll only), `cli/__init__.py::_cmd_run_eod` (route through `jobs.run_stages`),
  optional 1-3-line inner emits per §4 table (each independently skippable),
  `tests/test_jobs_schema.py`, `tests/test_jobs_runner.py` (fixture stages: happy path,
  mid-stage failure → `stage_failed`+`partial`, emit-raises → run unaffected, orphan
  finalization, cursor paging returns strictly-increasing no-dup pages).
- **Acceptance:** pytest green (only the known standing failure); real `run-eod --date`
  produces a job with full rail + events; `pipeline_runs` rows unchanged in shape;
  `/api/pipeline/status` responses byte-identical to before (curl diff); curl proof of the
  four endpoints on real data; API restart mid-fixture-run → job finalized `interrupted`.
- **QC gate:** §7 loop; reviewer specifically audits one-writer discipline, append-only,
  secret-free payloads, and that no stage file gained a signature change.

### 2b — SSE stream + replay + cancel/retry + restart recovery
- **Files:** `api/app.py` (`/events/stream` SSE, `/cancel`, `/steps/{id}/retry`, startup
  orphan sweep), `tests/test_jobs_sse.py` (ordering, `Last-Event-ID` resume with zero
  dup/loss, heartbeat, `done` on terminal, locked-DB tick-skip), retry/cancel tests
  (attempt rows append; cancel between stages only).
- **Acceptance:** `curl -N` shows live events during a real run; kill API mid-run → restart →
  `GET /events?after=<old cursor>` returns the tail exactly once and job reads `interrupted`;
  retry of a failed stage appends attempt 2 and can flip `partial→succeeded`;
  `/api/pipeline/status` still untouched.
- **QC gate:** §7 loop + an explicit reconnect-storm check (three overlapping clients at
  different cursors each receive a consistent, duplicate-free sequence).

### 2c — Live Work inspector (frontend) + placeholder/poll replacement
- **Files:** `desk/src/livework/useJobStream.js`, `desk/src/livework/LiveWorkInspector.jsx`
  (+ `StageRail.jsx`, `StepRow.jsx` in `components/v5`, styles in `primitives.v5.css` /
  a scoped `livework.v5.css`), `desk/src/api.js` (job endpoints), `App.jsx` (context mount,
  drawer, delete header poll string + `pollRef`), `MarketHomeTab.jsx` (delete
  `PipelineProgress`, replace Activity-log placeholder), vitest for the reducer
  (dedup-by-cursor, SSE→poll fallback switch, idle last-job state).
- **Acceptance (== the UI-2 done-test):** fixture job + one real update progress visibly
  without refresh; disconnect/reconnect and forced-poll-fallback show zero duplicate/lost
  events; confirmed desk data stays on screen throughout; reduced-motion pass (rail fills
  once); keyboard + `role="log"` pass; `npm run build` + vitest green; real-data screenshots
  at 1470×900 / 1024×768 / 390×844, beginner + expert; every rendered number cross-checked
  against `/api/jobs/{id}` payloads (entirety review, not "does it render").
- **QC gate:** §7 loop; UX reviewer answers "what can't the user do here?" against handoff §1
  bullet "must see work happening… without refreshing".

Sequencing: 2a → 2b → 2c strictly (each consumes the previous contract). One code writer at a
time; commit per sub-slice with explicit paths; orchestrator verifies before the next launches.

## 9. Explicit non-goals (scope fence)
- No Fyers/tick streaming (separate wave — `FYERS_LIVE_LOOP_PLAN.md`; there is no WebSocket
  client to adopt).
- No MARKET recomposition (UI-3 consumes this stream; 2c only removes the dead
  PipelineProgress/placeholder and mounts the drawer).
- No retirement of `/api/pipeline/status` or `_PIPELINE_STATUS` in this slice.
- No generic job framework (one `kind='run_eod'`; scanner-run/chart jobs adopt the same tables
  later only if a real surface needs them).
