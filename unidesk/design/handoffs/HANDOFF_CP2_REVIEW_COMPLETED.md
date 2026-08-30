# HANDOFF CP-2 review — COMPLETED (findings dispositioned)

Date: 2026-08-29. Checkpoint CP-2 per `unidesk/GOAL.md`: independent
fresh-context subagent review of W-A (U-P0.5 recorder core) and W-B
(U-P0.1/U-P0.3 groundwork).

## Attribution

Attribution-ID: attr-unidesk-cp2-review-glm53flash-20260829-001

Attribution-ID: attr-unidesk-cp2-fixes-glm53flash-20260829-001

Reviewer identity note (honest basis): the reviewer was a fresh-context
subagent spawned by the same harness; its model identity is `self_reported`
(the harness does not expose per-subagent model selection to the executor).
This is the weaker elevation form by design — CP-1/CP-3/CP-6 are the
owner-model ★ gates.

## Outcome

- **W-A: PASS.** Nulls preserved at the Arrow layer; gaps persisted with
  clock-proven duration; partitions asserted; replay round-trips; credential
  allowlist fail-closed and tested across all parquet cells; STALE/DISCONNECTED
  transitions clock-driven, not inspection.
- **W-B: PASS with one MAJOR.** Point-in-time tests actively discriminate
  against look-ahead bugs (effective-but-unavailable, revision-invisibility,
  pre-publication bars). No leakage hole found.

## Findings and disposition

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | MAJOR | DATA_AUTHORITY declared `orderflow/data/raw/**`; launcher writes `data/orderflow/{raw,parquet}` | FIXED: manifest (.json + .md) updated to the real path |
| 2 | MINOR | monitor `_start_at` / lifecycle sequence per-instance (restart semantics undocumented) | ACCEPTED as documented behavior for single-process sessions; revisit if cross-restart continuity is ever required |
| 3 | MINOR | gap left open if stream ended mid-outage | FIXED: `stream_end` closes an open gap (recorder.py) |
| 4 | MINOR | empty level list conflated with NULL | FIXED: empty lists stored as `[]` (replay mapping already tolerant) |
| 5 | MINOR | `surveillance_state=()` vs None distinction untested | FIXED: test added (test_momentum_market_store.py) |
| 6 | MINOR | `tick()` had zero coverage | FIXED: test added (quiet-period DEGRADED verdict persisted) |
| 7 | MINOR | DuckDB replay ORDER BY lacks tiebreaker | ACCEPTED DEBT: recorded in unidesk/TASKS.md under "Accepted debt" |
| 8 | MINOR | launcher reached into `manager._transport` | FIXED: public `transport` property added; launcher migrated |

## Files changed

- `unidesk/design/DATA_AUTHORITY.json`, `unidesk/design/DATA_AUTHORITY.md` — store path corrected.
- `orderflow/storage/recorder.py` — stream_end closes open gaps.
- `orderflow/storage/parquet_writer.py` — empty level lists stored as [].
- `orderflow/market_data/websocket_manager.py` — public `transport` property.
- `orderflow/checks/run_live_session.py` — uses the public property.
- `orderflow/tests/test_recorder.py`, `unidesk/tests/test_momentum_market_store.py` — new tests.
- `unidesk/GOAL.md`, `unidesk/TASKS.md` — status + accepted debt.

## Verification

```text
.venv-orderflow/Scripts/python.exe -m pytest orderflow/tests unidesk/tests -q
  -> 127 passed
.venv-orderflow/Scripts/python.exe unidesk/run_checks.py -> exit 0
```

## Honest partials

- The reviewer's model identity is self-reported (see Attribution note); the
  ★ owner-model gates (CP-1/CP-3/CP-6) remain the strong form of elevation.
- All verification is offline; live-session acceptance items are unchanged
  and owner-gated (Mon 2026-08-31).
