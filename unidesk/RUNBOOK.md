# RUNBOOK — how the desk goes from raw data to a self-verified UI

No manual scheduling needed anymore: since B2-7 the nightly is registered as
the Windows task **`UniDesk-NightlyRefresh`** (weekdays 19:30, interactive
logon). Everything below is what that task runs — the same chain, one
definition (`unidesk/server/jobs.py`), three fronts: the scheduled task, the
CLI, and the localhost server's Run button.

Environment: Windows, Python at
`C:\Users\satta\Downloads\koreanguy\.venv-orderflow\Scripts\python.exe`
(use the absolute path; bare `python` is a different interpreter and fails
under Task Scheduler).

## The scheduled task (B2-7)

```powershell
schtasks /Create /TN "UniDesk-NightlyRefresh" `
  /TR "C:\Users\satta\Downloads\koreanguy\unidesk\nightly_desk.cmd" `
  /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 19:30 /F
schtasks /Query /TN "UniDesk-NightlyRefresh" /V /FO LIST   # inspect
schtasks /Run    /TN "UniDesk-NightlyRefresh"              # trigger now
schtasks /Delete /TN "UniDesk-NightlyRefresh" /F           # remove
```

Every run appends nothing to the console but writes:
- `unidesk/logs/nightly_<timestamp>.log` — the full chain output, including
  the failed stage and its output tail on failure (newest 30 kept);
- `unidesk/last_run.json` — machine-readable outcome (status, exit_code,
  failed_stage, session produced). `/api/health` exposes it as
  `last_scheduled_run`, and the UI shows a banner when the last scheduled
  run failed or the newest session is stale.

**OWNER DECISION FLAGGED (B2-7, not decided unilaterally):** the
session-advance gate is currently an ERROR unless
`--allow-no-new-session` is passed, and the scheduled wrapper does NOT pass
it — so a trading holiday produces a logged, visible failure. Wiring the
existing `TradingCalendar` into the freshness gate (or demoting
"no new session on a weekday" to a warning) is the owner's call; until then
the failure is honest and named, not silent.

## The chain (after B2-4)

```
run_desk_refresh.py  /  run_scheduled_refresh.py  /  POST /api/refresh
  ├─ 1. bhavcopy_extractor/download_bhavcopy.py --days 3     (skip: --no-download)
  ├─ 2. unidesk/run_nightly_background.py                    (skip: --exports-only)
  ├─ 3. SESSION-ADVANCE GATE — fails unless the newest report session
  │      advanced (skip the gate: --allow-no-new-session, for holidays)
  ├─ 4. export steps: stock histories, regime history, outcomes,
  │      broker trades, sector mapping  → unidesk_terminal/src/data/
  ├─ 5. unidesk/run_checks.py                                (governance checks)
  ├─ 6. unidesk/run_published_invariants.py                  (writes STATE.json checks.inv:*)
  ├─ 7. unidesk/run_export_desk_checks.py                    (writes src/data/desk_checks.json)
  └─ 8. npm run build (in unidesk_terminal/)
```

Steps 5-7 are INSIDE the refresh (B2-4): the UI's "Desk self-checks" panel
is always produced by the same run that produced the data. **Fail-fast: the
first failed step aborts the whole refresh — no bundling, no build, no
"DONE" line.** A `DONE — session <date>` line is only printed when every
step exited zero, so `DONE` is the daily health signal.

## Typical invocations

```powershell
# normal end-of-day refresh (download + nightly + exports + checks + build)
.venv-orderflow\Scripts\python.exe unidesk\run_desk_refresh.py

# holiday / no new session expected — acknowledge the advance gate
.venv-orderflow\Scripts\python.exe unidesk\run_desk_refresh.py --allow-no-new-session

# re-bundle + re-verify only (no download, no nightly)
.venv-orderflow\Scripts\python.exe unidesk\run_desk_refresh.py --exports-only
```

## Periodic (not nightly): research-archive basis repair

```
unidesk/run_archive_attach_resume.py
```

Re-attaches outcome labels for archive partitions whose `ca_table_hash` or
`label_version` no longer matches the current confirmed-actions basis.
Run it when `sessions_needing_label_refresh(data/market)` reports sessions —
e.g. after the confirmed-actions table changes, or after B2-3-class
remediations. Hard rules learned the expensive way:

- Run it **detached**, and verify progress from **persisted partition
  counts on disk** — never from process absence. A killed process and a
  clean exit look identical from outside.
- Never run it inside a UI/refresh wave; it is a multi-hour, memory-heavy
  job (full-corpus ingest ≈ 6 GB). Sequence it alone.

## PART E (localhost desk server)

```
.venv-orderflow\Scripts\python.exe -m uvicorn unidesk.server.app:app --host 127.0.0.1 --port 8181
```

Serves reports/derived JSON from disk and runs the same chain as
`run_desk_refresh.py` via `POST /api/refresh` (see `unidesk/server/jobs.py`
— one definition of the chain, shared with the CLI). With the server up,
`npm run build` is no longer required to see new data; the static bundle
remains the labelled offline fallback.

## Known supply-chain note (no action taken; owner's call)

The wired-in downloader `bhavcopy_extractor/download_bhavcopy.py` pulls from
**third-party GitHub mirrors** (`tilak999/NSE-Data-bank`,
`girishg4t/bhavCopy-downloader`). `unidesk/fetch_nse_bhavcopy.py`, which
hits the official `archives.nseindia.com`, is **orphaned** — referenced only
in the work log, invoked by no driver. Swapping the chain to the official
fetcher (or validating the mirror output against it) is an owner decision.
