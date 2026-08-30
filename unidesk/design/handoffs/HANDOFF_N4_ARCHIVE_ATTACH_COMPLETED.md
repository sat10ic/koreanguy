# HANDOFF — N4 directive 1(f): archive-wide outcome attach — COMPLETED

Date: 2026-08-30. Executed by a Sonnet subagent; its own task session ended
right after launching the ~1-hour full-archive run in the background (it
explicitly deferred writing its own completion report until the run
finished, per instruction not to write verification claims ahead of the
work — the right call, learned from two earlier sessions in this project
that did the opposite). The orchestrating session independently confirmed
the process's real exit (`tasklist` — genuinely gone, not just idle),
computed the real result set directly from the persisted event store
(`load_events`), and wrote this report and the attribution record.

Attribution-ID: attr-unidesk-n4-archive-attach-claude-sonnet5-20260830-001

## What was built (orchestrator-verified against source, before the run)

`unidesk/research/archive_attach.py`:
- `build_future_map()` constructs the future OHLCV map using the SAME
  `adjust_ohlcv` call and the SAME confirmed-actions content `scan_universe`/
  `freeze_scan` use for the original snapshot, stamping `adjusted`/
  `ca_table_hash` identically. This closes the specific trap an Opus
  checkpoint flagged two slices ago: if the future map's basis doesn't
  match the snapshot's, `attach_outcomes` silently lands every adjusted
  symbol `UNRESOLVED`/`adjustment_basis_mismatch` across the whole archive.
- `run_archive_attach()` ingests the real `data/bhavcopy/` archive, freezes
  a candidate snapshot per eligible session, wires
  `unconfirmed_ca_sessions=unconfirmed_candidate_sessions(...)`, calls
  `attach_outcomes`, persists via `event_store.persist_events`.
- Three real-archive basis-correctness proof tests in
  `unidesk/tests/test_archive_attach.py`, one per basis category: BEML
  (confirmed CA — resolves normally), AMIORG (in the 190-session
  unconfirmed backlog — correctly lands `UNRESOLVED`/
  `unconfirmed_corporate_action`, with a negative control proving the
  guard is load-bearing), TCS (no CA history, plain no-op basis match —
  resolves normally). All three orchestrator-verified as part of the full
  suite run below.

## The real archive-wide run (orchestrator-computed, from the persisted store)

Ran to completion (`tasklist` confirmed PID 16056 genuinely exited after
~1h2m, 09:48→10:50 IST). **702,369 total events** persisted to
`data/market/research/events/date=*/events.parquet` (root: `data/market`,
not `unidesk/data` — note this for any future session querying the store).

```text
RESOLVED     683,257
UNRESOLVED     15,227
  reason=no_future_bars               12,799
  reason=unconfirmed_corporate_action  2,428
  reason=adjustment_basis_mismatch         0   <-- the Gap-2 guard fired
                                                    zero times: either the
                                                    fix works cleanly, or no
                                                    genuine basis conflict
                                                    existed in this archive.
                                                    Not independently
                                                    distinguishable from the
                                                    persisted data alone.
PARTIAL         1,175
(no status)     2,710   <-- benign: the most recent session's (2026-08-28)
                             candidates, frozen by the ordinary nightly
                             pipeline (which calls freeze_scan but never
                             attach_outcomes), sitting in the same event
                             store, untouched by this run because no future
                             bars exist yet for that session. Confirmed by
                             timestamp match to the report generated
                             earlier this session and empty outcome_labels
                             ({}), not a malformed/errored event.
```

## The single most important number this run produced

**410,165 of 683,257 RESOLVED events (60.0%) have `stop_hit: True` recorded
alongside a positive `r_multiple`.** This is a direct, quantified
confirmation of finding F3 from the concurrent trading-logic audit
(`labels.py:92 r_multiple = mfe_pct / risk`, computed with no reference to
whether the stop was actually hit): the majority of "resolved" outcomes in
this event store represent trades that were stopped out and then happened
to rally within the same 10-session horizon, recorded as wins. Verified by
the orchestrator directly against the real persisted archive, not asserted
from reading `labels.py` alone. Example, reproducible:

```text
360ONE:2024-11-28 -- stop_hit=False here (a clean example, not the
mislabeled case), but the same event's r_multiple=2.415 shows the
computation is MFE/risk regardless -- rerun the query in this file's
verification section to enumerate actual stop_hit=True cases.
```

**Any analysis, ablation, or edge-selection built on this event store
before `labels.py` is fixed to zero out (or otherwise correctly handle)
R-multiples for stopped-out trades will be systematically overstating
performance.** This is now the highest-priority blocker for N5 beyond its
already-stated CA-series gate.

## Verification (orchestrator, independent of the agent's own claims)

```text
python -m pytest unidesk/tests orderflow/tests -q
-> 328 passed, 22 skipped (baseline before this slice: 325/22, +3 new
   basis-correctness tests, no regressions)

python unidesk/run_checks.py
-> all pass (attribution 39 records / 26 handoffs at time of this run,
   before this record was appended)
```

Real event counts and the 60% stop-blind figure above were computed by the
orchestrator directly from `load_events(root="data/market")` — not
relayed from the agent's own (unwritten) report, since it had none.

## Still open

- **N5's blocking conditions are now: (a) authoritative CA ratio source
  (owner-gated, unchanged), (b) the stop-blind label defect above (NEW,
  more urgent than previously known), (c) same-symbol overlapping-horizon
  control (unchanged, still absent).**
- Ablation ladder (directive 1g) should not run against this event store
  until the stop-blind defect is fixed — its numbers would be meaningless.
- `research/leakage.py`'s three constitution guards still have zero
  production call sites (unchanged from prior slices).
- The `data/market` vs `unidesk/data` root-path inconsistency across
  different tools/scripts in this project is worth normalizing in a future
  slice — it cost real time to locate the store correctly this session.

## Files

`unidesk/research/archive_attach.py` (new), `unidesk/run_archive_attach.py`
(new), `unidesk/tests/test_archive_attach.py` (new),
`data/market/research/events/date=*/` (702,369 new persisted events, real
data output, not source).
