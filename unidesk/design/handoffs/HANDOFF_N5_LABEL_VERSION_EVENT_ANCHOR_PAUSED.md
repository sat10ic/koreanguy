# HANDOFF — N5 paused: stale-label protection and event anchors

Date: 2026-08-30. Status: paused by owner before the new code was fully tested
or committed.

Attribution-ID: attr-unidesk-n5-paused-label-version-event-anchor-gpt56sol-20260830-001

## Working-tree files to preserve

- `unidesk/research/labels.py`: adds `OUTCOME_LABELS_VERSION`.
- `unidesk/research/candidates.py`: stamps every outcome mapping with that
  version.
- `unidesk/research/archive_attach.py`: adds version-aware stale-partition
  discovery.
- `unidesk/tests/test_n4_research_spine.py`: current/legacy partition test and
  outcome-version assertion.
- `unidesk/research/event_anchors.py`: fact-backed IPO/EP anchor and
  prefix-limited EOD AVWAP primitive.
- `unidesk/tests/test_event_anchors.py`: primary-listing, post-dissemination,
  prefix-invariance and adjustment-basis tests.

## State and evidence

- Commit `03778ecd` is the prior completed stop-aware repair.
- Before the listed working-tree changes, 39 focused tests passed and
  `python unidesk/run_checks.py` was green.
- The new event-anchor test first failed because the module did not exist.
- No claim is made that the current uncommitted code passes. Run:

```text
py -m pytest unidesk/tests/test_event_anchors.py unidesk/tests/test_n4_research_spine.py unidesk/tests/test_labels.py unidesk/tests/test_labels_future_only.py unidesk/tests/test_adjustment_basis_guard.py unidesk/tests/test_unconfirmed_ca_guard.py -q
```

## Exact continuation order

1. Run the listed tests. Confirm all outcome paths, including `UNRESOLVED`,
   carry the current label version.
2. Commit the label-version + event-anchor slice only after focused tests,
   `python unidesk/run_checks.py`, `git diff --check`, attribution and a
   completion report pass.
3. Regenerate every eligible `data/market/research/events/date=*/events.parquet`
   partition. Do not use the existing untracked
   `run_archive_attach_resume.py` unchanged: it checks only `status` and would
   call legacy stop-blind partitions current. It must call
   `sessions_needing_label_refresh` (or equivalent) first.
4. Read every regenerated partition from disk. Verify every row has
   `outcome-labels-v2-stop-aware`, every eligible session is present, and no
   `stop_hit=True` row has positive `r_multiple`.
5. Keep N5 blocked: net labels need supplied order value and ADV; CA-ratio
   authority and production same-symbol collision/embargo guards remain open.
6. Build official NSE/BSE source ingestors before consuming IPO/EP anchors.
   Anchored AVWAP remains research-only until held-out, event-time-embargoed,
   stop-aware, net-of-cost validation beats the non-anchored baseline.

## Not done

No official NSE/BSE network ingestor, source-byte archive, event store,
feature-store persistence, screen integration, held-out validation, full archive
regeneration, production same-symbol embargo/collision wiring, or CA-ratio
authority work was performed in this paused slice.
