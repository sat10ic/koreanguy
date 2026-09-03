# RUNBOOK — how the desk goes from raw data to a self-verified UI

No scheduler exists. Every step below is a manual invocation (or the
localhost server's Run button, PART E). The order is real: each step
consumes the previous step's output. Skipped or failed steps leave the desk
stale — the refresh aborts loudly rather than shipping old data as current.

Environment: Windows, Python at
`C:\Users\satta\Downloads\koreanguy\.venv-orderflow\Scripts\python.exe`
(use the absolute path; bare `python` is a different interpreter).

## The chain (after B2-4)

```
run_desk_refresh.py
  ├─ 1. bhavcopy_extractor/download_bhavcopy.py --days 3     (skip: --no-download)
  ├─ 2. unidesk/run_nightly_background.py                    (skip: --exports-only)
  ├─ 3. SESSION-ADVANCE GATE — fails unless the newest report session
  │      advanced (skip the gate: --allow-no-new-session, for holidays)
  ├─ 4. export steps: stock histories, regime history, outcomes,
  │      broker trades, sector mapping  → unidesk_terminal/src/data/
  ├─ 5. unidesk/run_published_invariants.py                  (writes STATE.json checks.inv:*)
  ├─ 6. unidesk/run_export_desk_checks.py                    (writes src/data/desk_checks.json)
  └─ 7. npm run build (in unidesk_terminal/)
```

Steps 5-6 are INSIDE the refresh (B2-4): the UI's "Desk self-checks" panel
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
