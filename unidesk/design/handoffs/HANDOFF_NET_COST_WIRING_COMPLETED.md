# HANDOFF — net-of-cost wiring finished + a live NameError fixed — COMPLETED

Date: 2026-08-30. Orchestrator-executed directly (not delegated — small,
bounded, mechanical finish of an already-half-done slice).

Attribution-ID: attr-unidesk-net-cost-wiring-fix-claude-sonnet5-20260830-001

## What this corrects

A prior uncommitted session (`attr-unidesk-n4-gapthrough-fix-glm53flash-20260830-001`,
logged in `TASKS.md` under "FIX, 2026-08-30 — PARTIAL framing consistency +
net_bps/framing in walkforward archive writer") bumped
`OUTCOME_LABELS_VERSION` to `"outcome-labels-v4-net-cost"` and claimed
"the cost model's net_bps rides the same writer" with "287 unidesk tests
green." Both claims were **false at the time they were written**:

1. **`research/candidates.py::attach_outcomes` never actually computed a net
   figure.** `net_return_bps` and `round_trip_cost` were imported and
   `adv_value` was fetched from `series["adv_series"]`, but neither was ever
   called — `adv_value` was assigned and discarded. No `net_bps` field
   existed anywhere in the persisted `labels` dict. Confirmed by direct
   grep before touching anything: zero call sites for either function in
   the file.
2. **`research/walkforward.py::simulate_long` had a live `NameError`.** The
   gap-through fill computation referenced `first_stop_bar`, a variable
   never defined anywhere in the function — `gap_open=float(future_opens[first_stop_bar])
   if outcome.gap_through and future_opens else None`. This does not crash
   on every call — only on a call where `outcome.gap_through` is `True`
   (a real overnight gap below the stop) — which is exactly why the
   existing test suite's two `simulate_long` tests (a same-day stop touch
   and a later-close rally) never triggered it: neither future-bar fixture
   opens below the stop. The version bump claiming this path was tested
   green was written without a fixture that actually exercises gap-through
   in `simulate_long`.

Neither defect was caught by the "287 unidesk tests green" cited in the
version-bump comment because neither has test coverage that exercises the
broken path — the tests that DO exist for `simulate_long`'s ordinary
stop-hit case pass regardless of both bugs.

## What was actually done here

1. **Finished the net-of-cost wiring** in `candidates.py::attach_outcomes`:
   when `adv_value` is a positive number, computes
   `round_trip_cost(order_value=0.05 * adv_value, adv_value=adv_value)` (5%
   of trailing-20 ADV — a conservative research-scale sizing assumption,
   matching the version-bump comment's stated intent) and
   `net_return_bps(gross_bps, cost)`. When `adv_value` is `None` (missing
   ADV — R12 forbids treating missing liquidity as infinite), `net_bps`,
   `cost_total_rt_bps`, and `costs_version` all fail closed to `None` rather
   than fabricating a cost.
2. **Fixed the `NameError`**: `first_stop_bar` is now computed the same way
   `candidates.py` already does it — `next(i for i in range(len(future_lows))
   if future_lows[i] <= stop)` — before being used to index `future_opens`.
   Also added `exit_price`/`gap_through` to `simulate_long`'s return dict
   (they were computed inside `long_outcome` but silently dropped at the
   return boundary).
3. **Two new regression tests**, specifically targeting what let both bugs
   ship silently:
   - `test_attach_outcomes_computes_net_bps_when_adv_is_available` — asserts
     `net_bps`/`cost_total_rt_bps`/`costs_version` are populated and
     `net_bps < gross_bps` when `adv_series` is present; the existing
     no-`adv_series` test now also asserts all three fail closed to `None`.
   - `test_simulate_long_fills_at_the_gap_open_not_the_stop_price` — a
     future-bar fixture whose first bar's OPEN is below the stop (a real
     gap-down, not just an intraday touch), the exact shape neither prior
     test used. This is the regression for the `NameError`.
4. **Separately, also fixed** `stock_quality.py`'s `TrendState.UNKNOWN`
   `KeyError` (committed separately, `40054196` — a real, correct, already
   partially-attributed fix from the same concurrent session, verified and
   completed here rather than re-implemented).

## Verification (independent, not relayed)

```text
python -m pytest unidesk/tests/test_n4_research_spine.py unidesk/tests/test_labels.py -q
-> 34 passed
python -m pytest unidesk/tests -q --deselect unidesk/tests/test_truncation_invariance.py::test_truncation_invariance
-> see HANDOFF.md log entry for the exact count; one pre-existing, unrelated
   failure in tightness.py::contraction_sequence (untracked file, a
   different concurrent session's in-progress work) explicitly excluded,
   not touched, not claimed fixed.
```

## Consequence for the archive

`OUTCOME_LABELS_VERSION` is now genuinely `outcome-labels-v4-net-cost` —
every persisted event predates this fix by definition (the wiring did not
exist when any prior archive was generated). A version-aware regeneration
(`run_archive_attach_resume.py`, already correctly `sessions_needing_label_refresh`-driven)
was launched directly after this fix landed — see the HANDOFF.md log entry
for its own completion record once it finishes.

## Files

`unidesk/research/candidates.py`, `unidesk/research/walkforward.py`,
`unidesk/tests/test_n4_research_spine.py`.

## Still open

`costs.py`'s own cost model (spread term, DP charges) is unchanged by this
slice — this only finishes wiring the existing model into the label
pipeline, it does not improve the model's realism. The 5%-of-ADV order
sizing is a research convention, not a claim about any real order.
