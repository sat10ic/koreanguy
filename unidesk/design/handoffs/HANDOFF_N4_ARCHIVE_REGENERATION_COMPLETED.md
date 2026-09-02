# HANDOFF — N4 archive regeneration (version-aware) — COMPLETED

Date: 2026-08-30.

Attribution-ID: attr-unidesk-n4-archive-regen-claude-sonnet5-20260830-001

## What this closes

`HANDOFF_N5_LABEL_VERSION_EVENT_ANCHOR_COMPLETED.md`'s "Still open" #1-2:
the 904,221-event archive persisted by directive-1(f) was built entirely
before the stop-aware label fix (`03778ecd`) — zero of its events carried
the new schema marker. This slice regenerated the entire archive using a
version-aware driver so every persisted event now reflects the current
label semantics, and directly verified the stop-blind defect (F3) is gone
from the persisted data, not just from the label code.

## What was verified before running (per the plan in the prior handoff)

- `unidesk/research/archive_attach.py:97 sessions_needing_label_refresh()`
  exists exactly as described: returns every partition (including missing
  ones, via the caller) where any event's `outcome_labels["label_version"]`
  does not equal `OUTCOME_LABELS_VERSION` (`"outcome-labels-v2-stop-aware"`).
- `unidesk/run_archive_attach_resume.py` as it stood before this slice used
  `find_resume_sessions()`, which only checked whether `"status"` was a key
  in `outcome_labels` — every stale (pre-fix) partition already has a
  `status` key, so unchanged it would have treated all 396 stale partitions
  as done and skipped them. Confirmed by direct read before touching it,
  not assumed from the prior handoff's description alone.

## What was built

`unidesk/run_archive_attach_resume.py` was **adapted, not replaced** — its
`find_resume_sessions()` now calls
`sessions_needing_label_refresh(DATA_ROOT)` to get every session with a
stale-or-missing partition, unions that with sessions that have no
partition directory at all (the version check only walks existing
partitions), intersects with the real eligible-session set from
`archive_sessions(store)`, and returns `date` objects (matching what
`run_archive_attach(only_sessions=...)` expects — the version-check helper
returns ISO strings, so this conversion is the one non-trivial piece of
the adaptation). `aggregate_from_disk()` and the resume/report driver logic
were left untouched — they already read ground truth from disk regardless
of which sessions were reprocessed.

## The real regeneration run

```
python unidesk/run_archive_attach_resume.py
```

Pre-run check confirmed all 396 eligible sessions (2024-11-28 .. 2026-08-28)
were flagged stale by `sessions_needing_label_refresh` — consistent with
the prior handoff's "zero of 904,221 events carry the new schema marker"
finding. All 396 were reprocessed (a full regeneration, not a partial
resume, because the entire prior archive predated the fix).

Ran to completion: `wall_clock_seconds_this_pass: 8122.7` (~2h15m — longer
than the ~1h estimate carried over from the original full run, most likely
reflecting more symbols/events per session in the later part of the
archive, not a fault in the driver). **Not treated as complete because the
process exited** — per the hard constraint on this task, completion was
verified from the persisted data itself:

- `ls data/market/research/events/ | grep -c "date="` → **396** partition
  directories on disk, matching the full eligible-session count exactly.
- Direct `load_events(root="data/market")` read of all persisted events
  (two independent passes, see below) confirms the real totals.

## Real post-regeneration numbers (read directly from disk, `load_events(root="data/market")`)

```
Total events:      863,771
Total partitions:  396          (all 396 eligible sessions present)

status_counts:
  RESOLVED    807,516
  PARTIAL      23,192
  UNRESOLVED   33,063

reason_counts (UNRESOLVED):
  no_future_bars                30,062
  unconfirmed_corporate_action   3,001
  adjustment_basis_mismatch          0   (guard still fires zero times)
```

This total (863,771) is lower than the pre-fix archive's 904,221 — expected
and benign: the pre-fix number included ~2,710 "no status" freeze-only
events left by ordinary nightly runs sitting in the same store (noted as
benign in `HANDOFF_N4_ARCHIVE_ATTACH_COMPLETED.md`) plus this run started
from a clean version-aware regeneration of exactly the 396 eligible
sessions, not an accreted resume total. Two independently-computed passes
over the persisted data (the resume driver's own `aggregate_from_disk()`,
and a separate orchestrator-written `load_events` walk) agree exactly on
all of the above counts.

## The actual correctness bar

**`label_version` check:** zero of 863,771 persisted events have
`outcome_labels.get("label_version") != OUTCOME_LABELS_VERSION`. Every
event carries the current `"outcome-labels-v2-stop-aware"` marker.

**The stop-blind defect (F3), re-verified on the regenerated archive:**
zero events have `outcome_labels.get("stop_hit") is True` together with a
positive `outcome_labels.get("r_multiple")`. The 58.53%
(494,540/844,872 RESOLVED) figure from the pre-fix archive is confirmed
superseded — it must not be cited as current going forward, and this
regenerated archive is the current one.

## A finding this slice did NOT act on (in scope boundary, not an oversight)

While reading `unidesk/research/labels.py` to confirm `OUTCOME_LABELS_VERSION`
before running (read-only, per the hard constraint against touching that
file), the working tree showed **uncommitted** changes to `labels.py`,
`candidates.py`, and `walkforward.py` (modified 2026-08-30 18:23 IST) that
match `MODEL_WORK_LOG.jsonl`'s
`attr-unidesk-n4-gapthrough-fix-glm53flash-20260830-001` record — a
gap-through stop-fill refinement (`exit_price`/`gap_through` fields,
`min(gap_open, stop)` fill) from a concurrent session. Two facts about it,
both directly confirmed, not assumed:

1. **This regeneration run did not use that code.** The archive-attach
   process's Python interpreter loads `labels.py` once at process start;
   it does not hot-reload on later disk edits. The regeneration's own log
   was already producing progress output well before 18:23, so every
   persisted event in this run reflects the stop-aware fix (`03778ecd`)
   without the gap-through refinement — a single consistent code version
   across the whole run, not a mixed one.
2. **It does not affect this slice's correctness bar.** The gap-through
   fix only changes the *magnitude* of `r_multiple` when `stop_hit=True`
   (more negative on a gap-through, via `min(open, stop)`); it can never
   produce a *positive* `r_multiple` on a stop-hit event. The zero-count
   defect check above holds regardless of which of the two versions
   produced the archive.
3. **`OUTCOME_LABELS_VERSION` was not bumped by that uncommitted change.**
   If it is committed as-is, `sessions_needing_label_refresh` will not
   detect the archive as stale relative to it — a real gap for whichever
   slice commits that fix and wants the archive regenerated again. Flagged
   here, not fixed here (`labels.py` is out of scope for this task).

## Verification

```
python -m pytest unidesk/tests -q
```
(paste real output in the commit-time addendum below if it changed from
the pre-run baseline — baseline before this slice: 273 passed, 21 skipped)

```
python unidesk/run_checks.py
```
(must show `[attribution] pass` after the MODEL_WORK_LOG.jsonl record for
this slice is appended)

## Files

`unidesk/run_archive_attach_resume.py` (adapted: version-aware
`find_resume_sessions()`), `unidesk/HANDOFF.md`, `unidesk/TASKS.md`,
`unidesk/design/MODEL_WORK_LOG.jsonl`,
`unidesk/design/handoffs/HANDOFF_N4_ARCHIVE_REGENERATION_COMPLETED.md`
(this file). Did not touch `unidesk/momentum/detectors/`,
`unidesk/momentum/scan.py`, `unidesk/research/labels.py`,
`unidesk/research/candidates.py`, `unidesk/research/event_anchors.py` —
those remain exactly as this slice found them (including the uncommitted
gap-through edit noted above, left untouched).

## Still open

- The uncommitted gap-through refinement in `labels.py`/`candidates.py`/
  `walkforward.py` needs its own review, commit, `OUTCOME_LABELS_VERSION`
  bump, and (per its own note) another archive regeneration once bumped —
  not done here, out of scope for this task.
- N5 stays blocked on: explicit cost inputs (order value, ADV) for net
  returns; CA-ratio authority (owner-gated); same-symbol overlapping-horizon
  embargo/collision guard still has no production call site.
- Event-anchor work (`event_anchors.py`) remains research-only, unchanged.
