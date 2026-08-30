# U-P0.1 — repository and data-authority map completed

Closed: 2026-08-29.

## Outcome

The repository's persistent data authority is now explicit and machine-checked:

- 20 logical stores/store families have a named owner, writer, unified-desk
  classification, and boundary note;
- 12 unified fields have exactly one accepted/provisional authority or an
  explicit unresolved state;
- lifecycle outputs explicitly cover accepted, provisional, quarantined, and
  archive-only classes;
- a quarantined or archive-only store cannot pass validation as a field
  authority;
- `STATE.json.blocked_on` now contains only explicit failed checks; a regression
  test prevents successful evidence strings from being misreported as blockers;
- package boundaries, external sources/APIs, and reuse/copy/retire decisions are
  written down;
- the unresolved U-P0.3 data-home and symbol-master choices remain owner
  decisions rather than being hidden inside an implementation.

The machine source is `unidesk/design/DATA_AUTHORITY.json`; the readable guide
is `unidesk/design/DATA_AUTHORITY.md`.

## Read-only observations

- TraderLog production: 3,395 posts, 2,588 media, zero claims, zero claim
  links, 18 positions / 12 events admitted by the current accepted predicate,
  and 305 positions / 436 events from the deterministic reconciler retained in
  quarantine.
- TraderLog market core: 1,344,791 daily-price rows across 3,995 symbols through
  2026-08-21, 431 regime sessions, and 535,991 activity rows.
- Manas OS: one active package-local database with 96 observed tables and
  1,601,818 daily-price rows; its `live_quotes` ended 2026-07-25 and is not a
  UniDesk live authority.
- Archive/duplicate scale observed: 45 TraderLog DB backup/staging files
  totalling 7,622,328,320 bytes, 1,831 ChartsMaze extractor-state files, 303
  bhavcopy files, 71 retired SwingEdge ChartsMaze files, and 8,122 data-like
  files under `legacy/`.

All database queries used SQLite read-only mode. No production file or database
was modified. Owner credential material was not read or inventoried by value.

## Verification

- `python -m pytest unidesk/tests/test_data_authority.py -q`: **6 passed**.
- `python -m pytest unidesk/tests/test_runner_state.py -q`: **1 passed**; this
  reproduced the false-blocker bug before the root-cause fix and passes after it.
- `python unidesk/run_checks.py`: `data_authority` pass — **20 stores
  owned/classified; 12 unified fields single-authority checked**.
- `python -m pytest orderflow/tests unidesk/tests -q`: **109 passed**.
- `python -m compileall -q orderflow scripts unidesk`: exit 0.
- Final attribution round trip after the append-only STATE-file correction:
  **7 records / 2 completed handoffs**, all green.

## Files

- `unidesk/design/DATA_AUTHORITY.json`
- `unidesk/design/DATA_AUTHORITY.md`
- `unidesk/checks/runner.py`
- `unidesk/tests/test_data_authority.py`
- `unidesk/tests/test_runner_state.py`
- `unidesk/CANONICAL.md`
- `unidesk/GOAL.md`
- `unidesk/TASKS.md`
- `unidesk/HANDOFF.md`
- `unidesk/STATE.json` (machine-written by the checks runner)
- `unidesk/design/MODEL_WORK_LOG.jsonl`
- `unidesk/design/handoffs/HANDOFF_U_P0_1_DATA_AUTHORITY_COMPLETED.md`
- `plan/UNIFIED_DESK_INTEGRATION_PLAN.md`
- `DESK.md`

## Still open

- Owner chooses the U-P0.3 point-in-time store home/sole writer and freezes the
  symbol-master source.
- Owner runs the U-P0.4/U-P0.5 live FYERS session and acceptance checks.
- The 18 legacy accepted TraderLog lifecycles are migration candidates, not
  automatic TraderLog Lite truth. The 305 deterministic rows remain excluded.

## Attribution

Attribution-ID: attr-unidesk-up01-data-authority-codex-20260829-001

Attribution-ID: attr-unidesk-state-file-correction-codex-20260829-001

Attribution-ID: attr-unidesk-state-blocked-fix-codex-20260829-001

The host exposed the GPT-5 family but no exact model variant in the system
prompt, environment, or harness fields checked for this task. The ledger uses
`exact-model-unavailable` with `identity_basis: unknown` rather than guessing.
