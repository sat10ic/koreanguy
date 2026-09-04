# N2 — offline recorder core completed

Closed: 2026-08-29. Parent task: UniDesk U-P0.5 / W-A.

## Outcome

The offline-provable recorder core is built and fixture-tested:

- canonical quote and depth rows are buffered and appended to Parquet under
  `date=YYYY-MM-DD/symbol=...` partitions;
- feed-health, lifecycle, reconnect-gap, and subscription events are persisted;
- DuckDB views expose the recorded tables and reconstruct exact depth snapshots;
- disconnect recovery remains `UNKNOWN` until a fresh post-reconnect depth
  snapshot arrives;
- raw/error capture recursively redacts secret-shaped fields;
- the owner live-session launcher records before capability analysis and flushes
  recorder state during normal operation and shutdown.

The inherited partial recorder files had no completion record. Their exact prior
authorship is unknown, so this report does not reattribute them. This slice
repaired, extended, tested, and closed the offline implementation as it exists.

## Acceptance evidence

- `.venv-orderflow\Scripts\python.exe -m pytest orderflow/tests -q`:
  **84 passed**.
- `.venv-orderflow\Scripts\python.exe -m pytest orderflow/tests unidesk/tests -q`:
  **102 passed**.
- `.venv-orderflow\Scripts\python.exe -m compileall -q orderflow scripts unidesk`:
  exit 0.
- `.venv-orderflow\Scripts\python.exe unidesk/run_checks.py`:
  exit 0 before the documentation close; rerun after attribution is part of the
  wave-close gate.
- No live FYERS connection was made and no credentials were read or written.
  `orderflow/capability.json` remains synthetic.

## Files in the completed slice

- `orderflow/storage/parquet_writer.py`
- `orderflow/storage/duckdb_repo.py`
- `orderflow/storage/recorder.py`
- `orderflow/storage/__init__.py`
- `orderflow/checks/feed_health.py`
- `orderflow/checks/run_live_session.py`
- `scripts/fyers_live_transport.py`
- `orderflow/tests/test_recorder.py`
- `orderflow/tests/test_capability_audit.py`
- `unidesk/CANONICAL.md`
- `unidesk/GOAL.md`
- `unidesk/TASKS.md`
- `unidesk/HANDOFF.md`
- `unidesk/STATE.json` (machine-written by the checks runner)
- `orderflow/design/MODEL_WORK_LOG.jsonl`
- `unidesk/design/MODEL_WORK_LOG.jsonl`

## Still open

U-P0.5 is **partial**, not fully accepted. A real owner-run NSE session must
still prove sustained writes, a forced disconnect/resubscribe cycle, visible
gaps, session replay, real disk/row-rate behavior, and absence of credentials in
actual output. Phase 0 therefore remains blocked at its owner/live gate.

## Attribution

Attribution-ID: attr-orderflow-n2-offline-recorder-codex-20260829-001

Attribution-ID: attr-unidesk-wa-recorder-close-codex-20260829-001

The host exposed the GPT-5 family but no exact model variant in the system
prompt, environment, or harness fields checked for this task. The ledger uses
`exact-model-unavailable` with `identity_basis: unknown` rather than guessing.
