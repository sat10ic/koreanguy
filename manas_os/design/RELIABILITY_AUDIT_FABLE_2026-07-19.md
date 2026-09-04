# RELIABILITY AUDIT — Fable, 2026-07-19

Scope: why this tool needs human intervention several times a day. Evidence = 15+ real
incidents from the last two weeks (all reproduced/diagnosed in-session) + targeted code
checks. Not a feature review. Every defect carries the smallest durable fix.

## TOP 10 RELIABILITY DEFECTS (ranked: user pain x recurrence)

1. **Code deploys by process murder.** The only way a backend change reaches :8000 is
   killing the process and trusting the supervisor loop; __pycache__ has served stale
   bytecode even after restarts. Frontend needs `npm run build` + a hard refresh.
   *Incidents: 6+ this week.* **Fix:** run uvicorn under the supervisor with
   `--reload` watching manas_os/ (dev-grade but this IS a single-user tool), or a
   `/api/admin/reload` endpoint that execs a clean restart; delete __pycache__ in
   start_tool.cmd before every launch (one line).
2. **The browser can silently run a different app.** A stale Vite dev server (:5174)
   served weeks-old code; index.html caching served pre-fix bundles on :8000. The
   offline-fallback bundle then renders BAKED July-10 data with a subtle banner —
   failure masked as staleness. *Incidents: 3, including two "tool is broken" user
   reports that were actually this.* **Fix:** (a) start_tool.cmd kills any :5174/:8000
   listeners it does not own; (b) serve index.html with Cache-Control: no-store
   (app.py:7841 mount has no header control — wrap it); (c) frontend polls
   /api/desk/latest build_sha and shows a "new version — click to refresh" bar on
   mismatch; (d) offline fallback becomes a full-screen state, not a banner over
   plausible-looking stale data.
3. **In-memory job guards outlive their jobs.** `_PIPELINE_STATUS` (app.py:3766)
   returned "already running" for every Update click after a wedged job — across a
   restart it silently blocked the user's mornings. Debate runs show the same class
   today (seats stuck "Waiting", run banner "model errors" with no surfaced error).
   **Fix:** every long-running guard gets (a) DB-backed state, (b) a staleness rule —
   running + no event for N min = failed with reason, auto-cleared, (c) the /status
   payload always includes started_at so the UI can render "stuck for 43 min" honestly.
4. **Failures are swallowed at the seam between stages.** screener gap-fill wedged the
   nightly pipeline for hours (fixed w/ circuit breaker); debate context-pack can hang
   a run with no per-seat error; SSE dropped seat_verdict events for weeks (registered
   listener missing) with polling silently papering over it. **Fix rule (repo-wide):**
   no stage may block >its budget without emitting a failed-with-reason event; every
   background thread wraps in a top-level try/except that persists the traceback to the
   events table. Grep-able standard, enforce in review.
5. **Two writers, one SQLite, long transactions.** WAL + busy_timeout=30s ARE set
   (db/__init__.py:42-43 — good), but a 530MB DB with the API thread + pipeline thread
   + ad-hoc importers still hit "database is locked" when a writer holds a transaction
   >30s (broker import did). **Fix:** importers/backfills batch commits every N rows;
   pipeline writes chunked; never wrap a multi-minute loop in one transaction. Optional:
   a single writer queue for bulk jobs.
6. **Entrypoints depend on cwd + sys.path luck.** `python -m manas_os.cli` fails from
   the repo root on this machine; every ops script needs sys.path hacks; the supervisor
   and scheduled task each construct their own environment. **Fix:** a real
   pyproject.toml with `pip install -e .` and console_scripts (`manas ...`) — one
   30-minute change kills the whole class.
7. **No rendered smoke test.** A ReferenceError (undefined handler) shipped and
   white-screened TRADE_PLAN; only the error boundary saved the session. Nothing
   exercises tabs post-build. **Fix:** the existing Playwright config + a 7-line spec:
   open each tab, assert no error boundary and no console errors. Run after npm build
   in the same script.
8. **Auth expiry is a daily ambush.** Fyers token dies 6am IST daily; the UI has said
   "app id missing · secret missing" when only the token was gone (status conflation)
   and live-dependent panels degrade with generic errors. **Fix:** one status source
   (/api/fyers/status is correct — the header chip must use it verbatim), an 8:45am
   scheduled pre-warning (Telegram/notification: "paste today's token"), and copy that
   says exactly that.
9. **Log chaos, no health surface.** Dozens of api_restart*.log / *_err.log at repo
   root; no rotation; the only health view is asking the assistant. **Fix:** logs to
   manas_os/data/logs/ with date-stamped rotation (logging.handlers, 10 lines); a
   /api/admin/health endpoint aggregating: port owner, build sha, data freshness, last
   pipeline stage+status, token state, stuck-job detector — and a tiny STATUS strip in
   the UI header driven by it (partially exists; complete it).
10. **Scheduled path ≠ interactive path.** The 19:15 task, the supervisor, and manual
    runs execute different code paths with different cwd/env (incident 6 + the
    scheduled task fetching before ingest was retrofitted). **Fix:** everything calls
    the same `manas run-eod` console script (after #6); the scheduled task becomes a
    2-line wrapper.

## THE RESTART PROBLEM — target design
One owner: start_tool.cmd = single instance lock -> purge __pycache__ -> kill foreign
listeners on 8000/5174 -> uvicorn --reload. Frontend: vite build --watch into dist (or
rebuild on demand) + build-sha polling + refresh bar. Result: a code change reaches the
browser with zero human ritual; a crash self-recovers; a second server cannot exist.

## SELF-HEALING CHECKLIST (all cheap)
- [ ] stuck-job detector (any 'running' >10 min without events -> failed + cleared)
- [ ] single-instance lock + foreign-listener kill at boot
- [ ] __pycache__ purge at boot
- [ ] data-freshness alarm in-UI when last trading session unprocessed by 20:00
- [ ] token pre-warning 08:45 IST + one-line paste flow
- [ ] /api/admin/health + header STATUS strip
- [ ] nightly log rotation
- [ ] post-build tab smoke test

## TELEGRAM-READINESS VERDICT
NOT ready for time-critical pushes until: #1 (no manual deploys), #3 (no zombie
guards), #4 (no silent stage death), #8 (token pre-warning) are done, plus the P4
heartbeat ("09:20 heartbeat absent = the alert"). Testable bar: 10 consecutive trading
days where (a) data lands by 19:45 unattended, (b) zero manual restarts, (c) every
failure that occurred surfaced in-UI with a reason. Then trust alerts.

## QUICK WINS (<1h each)
pycache purge in start_tool.cmd · foreign-listener kill · Cache-Control: no-store on
index.html · build-sha refresh bar · stuck-job staleness rule on _PIPELINE_STATUS ·
log rotation · fyers status copy fix · Playwright tab smoke.
