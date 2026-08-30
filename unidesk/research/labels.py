"""Outcome labels (build manual Task P7.2 / P1.10 outcomes): MFE, MAE,
R-multiples, breakout hold/fail, stop hit.

Pure functions over CHRONOLOGICAL FUTURE series (the caller owns the
point-in-time guarantee: the future slice must be sliced at decision time,
which is the leakage suite's job — P7.3). Horizon semantics: the first
``horizon`` bars AFTER the entry bar.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional, Sequence

from unidesk.contracts.base import ContractError, ensure_date, require_float


def assert_future_only(sessions: Sequence[date], decision_session: date) -> None:
    """Fail closed: every session about to feed a label (MFE/MAE/R-multiple/
    stop-hit/breakout-hold) must be strictly AFTER the decision session --
    the decision bar itself is not future (directive-1b / HANDOFF N4).

    This is the labels-side companion to the leakage suite's
    ``gold_known_at`` pattern (``research/leakage_suite.py``): that module
    filters gold examples to ``session < query``; this asserts the mirror
    condition on the FUTURE side that ``long_outcome``/``breakout_hold``
    actually consume. Call this at the point the future slice is assembled
    (``research/candidates.py:attach_outcomes`` is the one production call
    site today) -- before any label function runs on it.
    """
    decision_session = ensure_date(decision_session, "decision_session")
    for i, session in enumerate(sessions):
        session = ensure_date(session, f"sessions[{i}]")
        if session <= decision_session:
            raise ContractError(
                f"label input session {session.isoformat()} at index {i} is not "
                f"strictly after decision session {decision_session.isoformat()} "
                "-- future-only violation (labels.py reads only indices > "
                "decision index)"
            )


def _future(highs: Sequence[float], lows: Sequence[float], horizon: int) -> tuple[list, list]:
    if horizon < 1:
        raise ContractError("horizon must be >= 1")
    h = [require_float(v, f"highs[{i}]") for i, v in enumerate(highs[:horizon])]
    l = [require_float(v, f"lows[{i}]") for i, v in enumerate(lows[:horizon])]
    return h, l


@dataclass(frozen=True)
class Outcome:
    mfe_pct: float           # max favorable excursion, %
    mae_pct: float           # max adverse excursion, % (negative or 0)
    stop_hit: bool
    r_multiple: Optional[float]   # MFE expressed in stop units (potential R)
    attained_1r: bool
    attained_2r: bool
    attained_3r: bool


def long_outcome(
    *,
    entry: float,
    stop: float,
    highs: Sequence[float],
    lows: Sequence[float],
    horizon: int,
) -> Outcome:
    """Long-side outcome over the next ``horizon`` bars.

    R semantics: ``r_multiple`` is the POTENTIAL R (MFE / risk-unit) — what
    the trade offered within the horizon, not what was captured. 1R/2R/3R
    attainment = MFE reached that multiple of the stop distance. A stop touch
    within the horizon sets ``stop_hit`` (first-touch, not sequenced against
    MFE — intrabar ordering is unknowable from OHLC and we do not pretend,
    R11-era honesty)."""
    entry = require_float(entry, "entry")
    stop = require_float(stop, "stop")
    if entry <= 0:
        raise ContractError("entry must be positive")
    if stop >= entry:
        raise ContractError("stop must be below entry for a long")
    risk = entry - stop
    h, l = _future(highs, lows, horizon)
    if not h:
        raise ContractError("no future bars within the horizon")

    mfe_pct = max((hi / entry - 1.0) * 100.0 for hi in h)
    mae_pct = min((lo / entry - 1.0) * 100.0 for lo in l)
    stop_hit = any(lo <= stop for lo in l)
    r_multiple = mfe_pct / (risk / entry * 100.0)
    return Outcome(
        mfe_pct=round(mfe_pct, 4),
        mae_pct=round(mae_pct, 4),
        stop_hit=stop_hit,
        r_multiple=round(r_multiple, 4),
        attained_1r=r_multiple >= 1.0,
        attained_2r=r_multiple >= 2.0,
        attained_3r=r_multiple >= 3.0,
    )


def breakout_hold(
    future_closes: Sequence[float],
    *,
    trigger: float,
    min_sessions: int = 3,
) -> tuple[Optional[bool], tuple]:
    """Did price ACCEPT above ``trigger``? Returns (hold|fail|None, reasons).

    None = unresolved (fewer than ``min_sessions`` completed bars above —
    an honest 'not decided yet', never a default). FAIL on any close back
    below the trigger within the window; HOLD when ``min_sessions`` closes
    stay at/above it."""
    trigger = require_float(trigger, "trigger")
    closes = [require_float(c, f"future_closes[{i}]") for i, c in enumerate(future_closes)]
    above = [c >= trigger for c in closes]
    if not above or not above[0]:
        return False, ("never_cleared_trigger",)
    window = above[:min_sessions]
    if False in window:
        return False, ("closed_back_below_trigger",)
    if len(window) < min_sessions:
        return None, ("insufficient_sessions",)
    return True, ()
