# HANDOFF — `blue_sky` degenerate-window fix — COMPLETED

Date: 2026-08-30. Executed by a Sonnet subagent; its task session ended
while waiting on a background test run it had itself started, before
writing this report or its attribution record. Orchestrator independently
verified the diff and finished the ritual — same pattern as three earlier
slices this session.

Attribution-ID: attr-unidesk-blue-sky-fix-claude-sonnet5-20260830-001

## The bug (from the Opus review, `HANDOFF_FIXES_AND_FORWARD_PLAN_REVIEW_COMPLETED.md`)

`blue_sky` in `inputs.py` claimed to mean "genuinely at a new listing
high," but was `max(h[:-1])` — the max of whatever window happened to be
loaded. For any symbol with `n <= base_window + 1` (≤21 bars), that slice
is identical to the pivot-check slice, so `close_cleared_pivot=True`
mechanically forced `blue_sky=True`, silently bypassing `base_breakout`'s
room-vs-ADR check for short-history symbols — the exact gameable path the
room rule exists to prevent.

## The fix (orchestrator-verified against the actual diff)

Chose **Option A** from the two offered in the brief: a minimum-history
floor (`BLUE_SKY_MIN_SESSIONS = 61`, matching `scan.py`'s own documented
"enough bars to trust a high" threshold — not an arbitrary new number)
before `blue_sky` can resolve at all. Below the floor, `blue_sky` is
`None` (unresolved), never a guessed `True`/`False`. Also fixed the
operator inconsistency Opus flagged: `blue_sky` now uses strict `>`,
matching `close_cleared_pivot`'s semantics (a close exactly at the prior
high is not yet a new one).

Two regression tests, both orchestrator-run and passing:
- `test_blue_sky_is_unresolved_not_a_coincidental_true_on_a_short_history_symbol`
  — reproduces the exact degenerate boundary (n = base_window+1 = 21),
  asserts `close_cleared_pivot=True` still holds (the old bug's
  precondition) but `blue_sky` is now `None`, and — the part that actually
  matters — that `base_breakout()` returns `INSUFFICIENT_DATA` rather than
  silently passing the room check, with `"missing:blue_sky"` in the
  failure reasons.
- `test_blue_sky_resolves_once_the_history_floor_is_reached` — sanity
  check on the other side of the floor: a genuine new high resolves
  `blue_sky=True`; a close exactly at (not above) the prior high resolves
  `False`, confirming the strict-`>` fix.

## Verification (orchestrator-independent)

```text
python -m pytest unidesk/tests/test_detector_registry.py
  unidesk/tests/test_gold_fixtures.py
  unidesk/tests/test_cleanroom_base_pattern.py -q
-> 17 passed
```

Full-suite run (`unidesk/tests orderflow/tests -q`) was in progress at the
time of writing this report; see the HANDOFF.md log entry for the final
combined count once it lands.

`unidesk/tests/fixtures/p2_3_gold.json` was NOT modified by this slice —
consistent with the fix only changing behaviour below a 61-session floor
that the gold fixtures evidently don't exercise; not independently
re-derived by the orchestrator beyond confirming no diff exists on that file.

## Files

`unidesk/momentum/detectors/inputs.py`, `unidesk/tests/test_detector_registry.py`.

## Still open

`setups.py`/`registry.py` were read but not modified — the fix lives
entirely in `inputs.py`'s computation and `setups.py`'s existing
`blue_sky is None` handling already did the right thing (confirmed by the
new test), so no change was needed there. Option B (threading a longer
true-history series into the computation) was explicitly not pursued —
the brief's own guidance was to only do so if Option A left `blue_sky`
`None` far more often than useful in practice; no evidence of that was
reported.
