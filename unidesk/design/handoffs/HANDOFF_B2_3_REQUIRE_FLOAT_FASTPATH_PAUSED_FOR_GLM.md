# Handoff — B2-3 require-float hot-path measurement (paused for GLM)

**Date:** 2026-09-04 20:32 IST  
**Status:** paused by owner request; do not resume anything automatically.  
Attribution-ID: attr-unidesk-b23-require-float-fastpath-codex-20260904-001
Attribution-ID: attr-unidesk-b23-target1-glm53flash-20260904-001

> **GLM continuation 2026-09-04 (complete):** gate 4/4 passed → fastpath KEPT;
> after-profile recorded (`unidesk/_profile_scan_session.txt`); split-detection design
> note at `unidesk/design/B2_3_SPLIT_DETECTION_INCREMENTAL_NOTE.md`. **Archive writer
> restart now awaits the owner's explicit go** — 149 rejected-basis partitions remain
> of 1,603.

## Owner priority and done test

The 4a profile, not prior guesses, now drives the work.  Its three-session
measurement was 739s total: `scan_universe` 665s, `require_float` 262s across
374,929,071 calls, `participation._series` 163s, and the two split-candidate
functions 217s combined.  Target 1 is complete only when the
`participation._series` fast path has preserved validation exactly, the required
heavy store-equivalence gate passes, and a before/after profile is recorded.

Target 2 (split detection) must not be implemented until Target 1 has a measured
after-profile.  Before any cache implementation, write whether appending one
bar can alter historical candidate detection; a symbol-only memo is forbidden.
4c remains a memory/concurrency reliability task, not a promised speed win.

## Current archive state

The B2-3 attempt-3 worker stopped silently; it is not running.  Its last stdout
line was:

```
[archive-attach] 96/249 session=2026-01-09 events_so_far=83884 status={'RESOLVED': 83529, 'PARTIAL': 114, 'UNRESOLVED': 241}
```

`unidesk/_b23_resume_attempt3.err.log` was empty.  After it stopped, a persisted
Parquet scan found **1,603 partitions**: **1,454** on current
`d1b585eb60fd4f82`, **149** on rejected `191ac96a61cdfae7`, and **0 mixed
partitions**.  This is the authoritative restart point; do not infer completion
from the stale `unidesk/_b23_resume.log`.

The watchdog `b2-3-archive-attach-watchdog` is already **PAUSED**.  The B2-3
launcher PID 33756 and worker PID 39076 are gone.  Do not start an archive writer
until the owner explicitly resumes it after the Target-1 measurement.

## Target-1 change already applied

Only these source/test files were changed in this slice:

- `unidesk/momentum/features/participation.py`
- `unidesk/tests/test_momentum_participation.py`

`participation._series` now has this deliberately narrow fast path:

```python
if type(v) is float and math.isfinite(v):
    out.append(v)
else:
    out.append(require_float(v, f"{name}[{i}]"))
```

Why it is narrow: exact built-in finite `float` is the archive common case.
Integers, bools, strings, NaN/infinity, subclasses, and NumPy scalars all retain
the old slow-path call and its exact `name[index]` error message.  Do not widen
this to `isinstance(v, float)` without a fresh semantic proof: on this runtime
`numpy.float64(1.25)` is accepted by the legacy validator and must remain so.

The tests were added **before** the production edit and then run after it:

```
.venv-orderflow\Scripts\python.exe -m pytest unidesk/tests/test_momentum_participation.py -q
15 passed in 0.17s
```

They explicitly cover finite built-in floats, NaN, positive/negative infinity,
bool, string, NumPy float scalar, and exact `values[0]` `ContractError` text.

## Required continuation, in order

1. Confirm no `run_archive_attach_resume.py` process is live.  Do not inspect or
   mutate `data/market/research/events/**` while one is live.
2. Run the owner-required equivalence gate once, with no duplicate test runner:

   ```powershell
   $env:UNIDESK_HEAVY_TESTS = '1'
   .venv-orderflow\Scripts\python.exe -m pytest unidesk/tests/test_store_equivalence.py -q
   ```

   `test_builders_agree` must pass.  It requires byte-identical frozen events.
   If it fails, revert the fast path; do not weaken or update the assertion.
   Two exploratory invocations were deliberately stopped when the owner paused;
   they produced **no usable pass/fail result**.  Do not cite them as evidence.
3. Re-profile Target 1 with the same three-session command and save the complete
   before/after comparison:

   ```powershell
   .venv-orderflow\Scripts\python.exe unidesk/profile_scan_session.py --sessions 3
   ```

   This profiler calls `run_archive_attach` for its three probe sessions and
   therefore writes those sessions.  Run it only with no archive-resume worker;
   record that it was the user-prioritized Target-1 measurement, then use the
   same optimized source for any later B2-3 resume.
4. Compare, at minimum: total/session wall time, `require_float` cumulative time
   and calls, `participation._series` cumulative time, and the unchanged
   split-detection cost.  Report measured values; do not predict a multiplier.
5. Only after that measurement, analyse split detection in a separate written
   design note.  The bar window grows each session, so a cache keyed only by
   symbol can return stale candidates.  Establish an incremental update rule or
   prove historical output cannot change before adding a cache.
6. Do not start Target 2 or 4c while this owner pause remains in force.

## Eager f-string inventory (observed, not yet changed)

The requested string search found other per-element `require_float` candidates:
`momentum/detectors/inputs.py`, `features/avwap.py`,
`momentum/detectors/base_pattern.py`, `momentum/primitives/contraction.py`,
`momentum/primitives/pivots.py`, `research/event_anchors.py`,
`features/event_relative.py`, `research/labels.py`, `features/spec_library.py`,
`features/rs.py`, `scoring/tightness.py`, `features/trend.py`, and
`momentum/data/corp_actions.py`.  No `require_int` per-element candidate was
identified by this search.  Do not batch-optimize these before isolating and
measuring the present slice.

## Scope / hygiene

- No archive process is currently running; no archive writer was modified.
- No commit was made.
- Existing unrelated working-tree changes and handoffs are not this slice.
- `unidesk/_b23_require_float_equivalence_*.log` artifacts from the paused
  exploratory test runs are non-evidence; do not treat them as a result.
- Append a new attribution record for any GLM work; preserve this record.
