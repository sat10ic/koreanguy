"""Pure predicates for live confirmation and confirm-time revalidation.

Per LIVE_LOOP_FABLE.md §2.2 and the T4.1 build-plan restatement: live
confirmation (TRIGGERED -> ALERTED) = price clears trigger (checked by the
FSM itself before these predicates run) + first-15m holds OR-low/VWAP +
gap-fill <=33% + projected RVOL >=2.

Pure functions only -- no DB, no network -- so the same predicate is used
identically by the live session driver and the replay harness (the whole
point of the replay-first build order: one FSM, two drivers).
"""
from __future__ import annotations

GAP_FILL_MAX = 0.33
RVOL_MIN = 2.0


def live_confirmation_ok(tick: dict) -> tuple[bool, str]:
    """Evaluate the four-part live-confirmation bundle against one tick/bar.

    Expected tick fields (all caller-computed -- this module never derives
    them from raw prices, per the one-writer rule):
      in_first_15m_complete: bool -- no triggers count before the first
        15-minute bar has closed (LIVE_LOOP_FABLE §3, opening-window quality).
      holds_or_low_vwap: bool -- price has held above the opening-range low
        and VWAP through the first 15 minutes.
      gap_fill_pct: float in [0, 1] -- how much of today's opening gap has
        already been filled.
      rvol_projected: float -- time-of-day-normalized projected RVOL.
    """
    if not tick.get("in_first_15m_complete"):
        return False, "before_first_15m"
    if not tick.get("holds_or_low_vwap"):
        return False, "fails_or_low_vwap_hold"
    gap_fill = tick.get("gap_fill_pct")
    if gap_fill is None or gap_fill > GAP_FILL_MAX:
        return False, "gap_fill_exceeds_max"
    rvol = tick.get("rvol_projected")
    if rvol is None or rvol < RVOL_MIN:
        return False, "rvol_below_min"
    return True, "live_confirmation_passed"


def in_zone(ltp: float | None, zone_lo: float | None, zone_hi: float | None) -> bool:
    """Confirm = revalidation (LIVE_LOOP_FABLE §2.3): true only if the LTP at
    the moment of confirmation still sits inside the pre-committed zone."""
    if ltp is None or zone_lo is None or zone_hi is None:
        return False
    return zone_lo <= ltp <= zone_hi
