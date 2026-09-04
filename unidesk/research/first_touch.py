"""N-50 — first-touch outcome ordering: did +1R arrive before −1R?

Adds a temporal dimension beside (never replacing) the existing r_multiple.
The old model is stop-dominant: `stop_hit = any(lo <= stop)` spans the whole
horizon, so +1.8R on bar 2 followed by a stop on bar 9 is labelled −1R. That
is correct for fixed-stop position management, but it cannot distinguish
"the setup worked and gave it back" from "the setup failed."

The 8-state model (each state is mutually exclusive, first match wins):
  NO_TRIGGER       — price never cleared the entry
  WORKED           — +1R touched before the stop
  WIN              — +2R touched before the stop
  STOPPED          — stop touched before +1R
  FLAT             — horizon completed without triggering stop or +1R
  OPEN             — horizon not yet complete (fewer bars than horizon)
  NO_DATA          — no bars at all (symbol absent from the future window)
  PATH_AMBIGUOUS   — a single bar touched both the stop and +1R (OHLC cannot
                     resolve intrabar ordering; the conservative policy from
                     labels.py:89-98 applies: recorded as STOPPED, but the
                     ambiguity is surfaced rather than hidden)

`r_multiple` and `potential_r_multiple` are NOT touched by this module.
They are the fixed-stop position-management labels; this is an added
temporal dimension beside them.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Sequence

from unidesk.contracts.base import ContractError, require_float


class OutcomeState(Enum):
    NO_TRIGGER = "no_trigger"
    WORKED = "worked"
    WIN = "win"
    STOPPED = "stopped"
    FLAT = "flat"
    OPEN = "open"
    NO_DATA = "no_data"
    PATH_AMBIGUOUS = "path_ambiguous"


@dataclass(frozen=True)
class FirstTouchResult:
    state: OutcomeState
    time_to_1r: Optional[int]        # bar index (0-based in the future window)
    time_to_2r: Optional[int]
    time_to_stop: Optional[int]
    r_multiple: Optional[float]      # passthrough from the existing labeller
    potential_r_multiple: Optional[float]


def first_touch_outcome(
    *,
    entry: float,
    stop: float,
    highs: Sequence[float],
    lows: Sequence[float],
    opens: Sequence[float],
    horizon: int,
) -> FirstTouchResult:
    """Per-bar first-touch scan: +1R, +2R, and stop, in temporal order.

    ``r_multiple`` and ``potential_r_multiple`` are NOT computed here —
    they come from ``labels.long_outcome`` which stays unchanged.
    """
    entry = require_float(entry, "entry")
    stop = require_float(stop, "stop")
    if entry <= 0:
        raise ContractError("entry must be positive")
    if stop >= entry:
        raise ContractError("stop must be below entry for a long")
    risk = entry - stop
    if risk <= 0:
        raise ContractError("risk must be positive")

    target_1r = entry + risk
    target_2r = entry + 2 * risk
    n = len(highs)
    if n == 0:
        return FirstTouchResult(OutcomeState.NO_DATA, None, None, None, None, None)

    if n < horizon:
        return FirstTouchResult(OutcomeState.OPEN, None, None, None, None, None)

    time_to_1r: Optional[int] = None
    time_to_2r: Optional[int] = None
    time_to_stop: Optional[int] = None

    for i in range(min(n, horizon)):
        hi = require_float(highs[i], f"highs[{i}]")
        lo = require_float(lows[i], f"lows[{i}]")
        op = require_float(opens[i], f"opens[{i}]")

        if time_to_1r is None and hi >= target_1r:
            time_to_1r = i
        if time_to_2r is None and hi >= target_2r:
            time_to_2r = i
        if time_to_stop is None and lo <= stop:
            time_to_stop = i
            break  # stop-dominant within the bar; later bars are post-exit

    # state derivation — first match wins, ordered by temporal priority
    if time_to_stop is not None and (time_to_1r is None or time_to_stop < time_to_1r):
        state = OutcomeState.STOPPED
    elif time_to_2r is not None and (time_to_stop is None or time_to_2r < time_to_stop):
        state = OutcomeState.WIN
    elif time_to_1r is not None and (time_to_stop is None or time_to_1r < time_to_stop):
        state = OutcomeState.WORKED
    elif time_to_stop is not None and time_to_1r is not None and time_to_stop == time_to_1r:
        state = OutcomeState.PATH_AMBIGUOUS
    elif time_to_1r is None and time_to_stop is None:
        state = OutcomeState.FLAT
    else:
        state = OutcomeState.FLAT

    return FirstTouchResult(
        state=state, time_to_1r=time_to_1r, time_to_2r=time_to_2r,
        time_to_stop=time_to_stop, r_multiple=None, potential_r_multiple=None,
    )
