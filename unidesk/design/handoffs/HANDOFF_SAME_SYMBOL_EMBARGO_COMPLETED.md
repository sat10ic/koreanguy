# HANDOFF — same-symbol overlapping-horizon embargo control — COMPLETED

Date: 2026-08-30. Orchestrator-executed directly.

Attribution-ID: attr-unidesk-same-symbol-embargo-claude-sonnet5-20260830-001

## What this closes (and what it does NOT close)

N5's three blockers were CA-ratio source (owner-gated), the stop-blind
label fix reflected in a regenerated archive (in progress separately —
see HANDOFF.md), and "same-symbol overlapping-horizon control (still
absent, unbuilt)." `research/leakage.py`'s constitution guards
(`assert_feature_not_after_decision`, `same_symbol_embargo`,
`same_event_collision`) had zero production call sites — test-only,
per the 6:07am status note this session started from.

**This closes the "unbuilt" half.** It does NOT wire the control into a
running production pipeline, because there is no such pipeline yet to
wire it into: the P7.4 ablation ladder (the thing that would actually
assemble a sample set and need this embargo) is itself still unbuilt and
explicitly out of scope until N5's other two blockers clear. Calling this
"production-wired" would overclaim; it is "built, tested, and ready for
the ablation ladder to call" — the honest state.

## What was built

`research/leakage.py` gained `embargo_overlapping_events(events, calendar,
window=60)`. Groups events by symbol, sorts each symbol's events by
decision session, and greedily keeps the earliest event in each cluster —
every later same-symbol event within `window` trading sessions of an
already-kept one is embargoed, and a freshly-kept event resets the window
(so three events at +0/+61/+122 sessions are all mutually independent even
though they form one dense-looking run; a naive "distance from the first
event" check would wrongly merge them). The greedy choice is deliberately
outcome-blind — it decides what to keep from decision dates only, never
from any event's `r_multiple`/`net_bps`/etc., so it cannot be gamed into
keeping whichever sample looks best.

Returns `(kept, embargoed)` — `embargoed` pairs each dropped event with
the session that embargoed it, so a caller can report *why* the sample
count shrank, not just that it did. Asserts
`same_event_collision([e.event_id for e in kept])` is `False` before
returning — defense-in-depth against a bug in this function's own
grouping logic, same pattern as `attach_outcomes`'s `assert_future_only`.

## Verification

```text
python -m pytest unidesk/tests/test_phase0_primitives.py -q
-> 11 passed (2 new: a same-symbol cluster all within 60 sessions collapses
   to one kept event with the correct two embargoed; a same-symbol run at
   +0/+61/+122 sessions stays fully independent -- the window-reset case)
```

Full suite result: see HANDOFF.md log entry for the count (run in
background alongside this report).

## Files

`unidesk/research/leakage.py`, `unidesk/tests/test_phase0_primitives.py`.

## Still open

The ablation ladder (P7.4) that would actually call this function does
not exist. N5 remains NO-GO: CA-ratio source is still owner-gated
(the review queue this session also produced, `config/ca_review_queue.csv`,
is the input to that step, not a resolution of it); the archive
regeneration under the real v4 label version is still running as of this
entry.
