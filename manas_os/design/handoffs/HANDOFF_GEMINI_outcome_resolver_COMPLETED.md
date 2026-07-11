# Handoff: Alpha Outcome Resolver [COMPLETED]

This document records the completion of the backend Alpha outcome resolver module.

## Summary of Changes

1. **Resolution Logic:**
   - Implemented `resolve_all_outcomes(conn) -> int` in `manas_os/alpha/resolver.py`.
   - The resolver queries all pending decisions in `decision_memories` and walks forward their prices day-by-day to determine trigger availability and trade outcomes.
   - Saves final resolutions into `decision_memory_outcomes` using `resolve_outcome` from `manas_os/alpha/memory.py` with point-in-time available dates.

2. **Decision Trigger and Path Walkthrough:**
   - **Trigger Availability:** Checks `open_t` and `low_t` against `invalidation` (stop) and `high_t` against `confirmation` (trigger) during the `time_window` validity sessions.
     - `GAP_OVER_INVALIDATION` if day open is below stop.
     - `INVALIDATED` if low is below stop before trigger is hit.
     - `RESOLVED` if triggered, setting entry fill to `max(open_t, confirmation)`.
     - `NO_TRIGGER` if the window expires without triggering.
   - **Path Exits:** Once filled, walks forward up to 20 sessions. Exits if `open <= invalidation` (gap-through-stop) or `low <= invalidation` (stop). Otherwise exits at T+20 close (`horizon_close`).
   - **Excursions & Gaps:** Tracks session-by-session MFE/MAE in R units, time-to-1R, time-to-2R, time-to-stop, and sum of overnight adverse gaps.
   - **Horizons:** Resolves terminal return at T+5, T+10, T+20.

3. **Verification:**
   - Created the test suite `manas_os/tests/test_alpha_resolver.py`.
   - Seeded in-memory DB and verified:
     - `NO_TRIGGER` logic.
     - `INVALIDATED` logic.
     - `GAP_OVER_INVALIDATION` logic.
     - `RESOLVED` with same-day stop hit (MAE first).
     - `RESOLVED` runner with +2R hit and overnight adverse gap calculation.
     - `PENDING` states (insufficient bars or unknown symbols).
     - `Idempotency` checks (resolving twice writes 0 new rows).

## Automated Tests
- Running the tests verifies all 7 cases pass successfully:
  `python -m pytest manas_os/tests/test_alpha_resolver.py -v`
