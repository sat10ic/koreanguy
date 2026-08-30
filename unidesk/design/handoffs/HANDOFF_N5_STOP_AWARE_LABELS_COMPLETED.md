# HANDOFF — N5 stop-aware outcome-label repair

Date: 2026-08-30.

Attribution-ID: attr-unidesk-n5-stop-aware-labels-gpt56sol-20260830-001

## Completed

- `long_outcome` retains maximum favourable excursion as
  `potential_r_multiple`, but `r_multiple` is now the conservative realised
  outcome: any OHLC stop touch records `-1R`. The result and attained-R flags
  cannot claim a positive captured trade after a stop touch.
- `stop_aware_return_bps` exits realised gross return at the stated stop when
  `stop_hit` is true. Both `simulate_long` and archived-candidate outcome
  attachment use it, so a later closing rally no longer overwrites a loss.
- `potential_r_multiple` is persisted alongside the stop-aware outcome so
  research can distinguish opportunity from a trade result.
- The IPO/results source-ingestor work is registered in `TASKS.md` and the
  BananaPatterns recovery plan. Official exchange documents are the intended
  authority; calendars remain schedule-only.
- The same tasks define event-anchored AVWAP as a research feature: first
  tradable IPO listing session, or first completed session after realised
  results dissemination in EOD mode. It is explicitly forbidden to anchor to
  a scheduled earnings date or to promote the feature into a screen without a
  held-out, net-of-cost comparison against the non-anchored baseline.

## Verification

1. RED: `test_stop_touch_fails_closed_even_when_later_ohlc_shows_a_large_mfe`
   failed against the prior implementation because `Outcome` had no separate
   potential field and reported `+2R` after a stop touch.
2. RED: `test_simulate_long_uses_the_stop_loss_not_a_later_close_after_a_stop_touch`
   failed with `gross_bps == 1100.0` instead of the expected `-500.0`.
3. GREEN: `py -m pytest unidesk/tests/test_labels.py
   unidesk/tests/test_n4_research_spine.py unidesk/tests/test_labels_future_only.py
   unidesk/tests/test_adjustment_basis_guard.py
   unidesk/tests/test_unconfirmed_ca_guard.py -q` returned **37 passed**.

## Limits

This EOD-only repair uses a conservative stop fill at the stated stop; it does
not claim intrabar ordering or gap-through-stop execution. The existing
archive contains legacy stop-blind labels and has not been regenerated. Net
returns remain unavailable to `attach_outcomes` until real order-value and ADV
inputs are supplied; no default capital, liquidity or cost is invented.
