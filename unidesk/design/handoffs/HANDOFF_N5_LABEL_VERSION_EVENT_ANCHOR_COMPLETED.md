# HANDOFF — label-version tagging + event anchors — COMPLETED

Date: 2026-08-30. Started by a session (gpt56sol) that was explicitly
paused by the owner before testing/committing — see
`HANDOFF_N5_LABEL_VERSION_EVENT_ANCHOR_PAUSED.md` for its own honest
"not done" list. Resumed and completed by the orchestrating session per
the owner's explicit "pick up from" instruction.

Attribution-ID: attr-unidesk-n5-label-version-event-anchor-claude-sonnet5-20260830-001

## What this closes

The stop-aware label fix (`03778ecd`) changed `labels.py`'s `r_multiple`
computation, but the 904,221-event archive persisted by directive-1(f)
(`44c126fb`) was computed *before* that fix — every one of those events
still reflects the old, stop-blind formula. Nothing distinguished a
current-schema event from a stale one until this slice.

## What was verified before committing (orchestrator-independent)

- `OUTCOME_LABELS_VERSION = "outcome-labels-v2-stop-aware"` in `labels.py:21`,
  stamped onto every outcome by `candidates.py:286`
  (`labels = {"label_version": OUTCOME_LABELS_VERSION, **labels}`).
- `archive_attach.py:97 sessions_needing_label_refresh()` exists and
  defaults to `expected_version=OUTCOME_LABELS_VERSION` — confirmed by
  direct grep before trusting the paused handoff's own description.
- Focused tests (the paused handoff's own exact command):
  `pytest unidesk/tests/test_event_anchors.py
  unidesk/tests/test_n4_research_spine.py unidesk/tests/test_labels.py
  unidesk/tests/test_labels_future_only.py
  unidesk/tests/test_adjustment_basis_guard.py
  unidesk/tests/test_unconfirmed_ca_guard.py -q` → **41 passed** (paused
  handoff reported ~39 before its own uncommitted additions).
- Full suite: `pytest unidesk/tests orderflow/tests -q` → **342 passed, 22
  skipped**, up from 328 before the earlier `cb67bc91`/`334ab9a6`/`03778ecd`
  fixes landed — no regression.
- `python unidesk/run_checks.py` → all green, attribution 45 records / 31
  handoffs (before this record).
- `git diff --check unidesk` → clean, no whitespace errors.
- **Directly confirmed the staleness the paused handoff warned about**:
  `load_events(root="data/market")` over all 904,221 persisted events —
  **zero** carry `potential_r_multiple` (the new schema's marker field).
  The entire archive predates the stop-aware fix and must be regenerated
  before any of its numbers (including the 58.53% stop-blind figure in
  the prior HANDOFF entry) are cited as current.

## Still open (per the paused handoff's own list, unchanged by this slice)

1. **Regenerate every eligible partition using `sessions_needing_label_refresh`,
   NOT the existing `run_archive_attach_resume.py` unchanged** — that
   script only checks whether a `status` key exists, which every stale
   partition already has; it would treat old-schema partitions as done and
   skip them. This is the next slice, not done here.
2. Read every regenerated partition and verify: current label version on
   every row, all 396 eligible sessions present, and — the actual
   correctness bar — zero `stop_hit=True` rows with a positive
   `r_multiple`.
3. N5 stays blocked: net labels need supplied order value and ADV;
   CA-ratio authority (owner-gated) and the same-symbol overlapping-horizon
   embargo/collision guard remain open, unchanged from prior slices.
4. Event-anchor work (`event_anchors.py`) is research-only per the paused
   handoff: no official NSE/BSE ingestor exists yet, and anchored AVWAP
   stays research-only until held-out, event-time-embargoed, stop-aware,
   net-of-cost validation beats the non-anchored baseline. Not attempted
   this slice.

## Files

`unidesk/research/labels.py`, `unidesk/research/candidates.py`,
`unidesk/research/archive_attach.py`, `unidesk/research/event_anchors.py`
(new), `unidesk/tests/test_n4_research_spine.py`,
`unidesk/tests/test_event_anchors.py` (new),
`unidesk/run_archive_attach_resume.py` (new — the version-aware resume
driver for the next slice's regeneration work).
