"""Trade geometry (build manual Tasks P2.5–P2.8): trigger/invalidation
distances, breakout room, initial R:R, and the entry-quality composite.

A key frozen distinction (manual P2.6 note): the nearest resistance is a
CONFIRMATION HURDLE, not the profit target — initial R:R is computed against
the hurdle and labeled as such, never as a projected objective.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from unidesk.contracts.base import ContractError, require_float


def trigger_distance_pct(current: float, trigger: float) -> float:
    """Signed % distance to the trigger: positive = still below (waiting),
    negative = already through (chase assessment)."""
    current = require_float(current, "current")
    trigger = require_float(trigger, "trigger")
    if trigger <= 0 or current <= 0:
        raise ContractError("prices must be positive")
    return (trigger / current - 1.0) * 100.0


def stop_distance_pct(current: float, invalidation: float) -> float:
    """Positive % risk from current price to the invalidation level. Negative
    result means price is already below invalidation (invalid geometry)."""
    current = require_float(current, "current")
    invalidation = require_float(invalidation, "invalidation")
    if current <= 0:
        raise ContractError("current must be positive")
    return (current - invalidation) / current * 100.0


def breakout_room(entry: float, hurdle: float) -> float:
    """RoomPct = (hurdle − entry) / entry × 100. Negative = price already
    above the hurdle (no room)."""
    entry = require_float(entry, "entry")
    hurdle = require_float(hurdle, "hurdle")
    if entry <= 0:
        raise ContractError("entry must be positive")
    return (hurdle - entry) / entry * 100.0


def room_adr(room_pct: float, adr_pct: float) -> float:
    """Room expressed in ADR units (manual P2.6): <1 poor, 1–2 marginal,
    >2 good, >3 excellent — band LABELS are caller policy."""
    adr_pct = require_float(adr_pct, "adr_pct")
    if adr_pct <= 0:
        raise ContractError("adr_pct must be positive")
    return room_pct / adr_pct


def initial_rr(entry: float, invalidation: float, hurdle: float) -> float:
    """Initial structural R:R to the HURDLE (not a projected target)."""
    entry = require_float(entry, "entry")
    invalidation = require_float(invalidation, "invalidation")
    hurdle = require_float(hurdle, "hurdle")
    risk = entry - invalidation
    reward = hurdle - entry
    if risk <= 0:
        raise ContractError("entry must sit above invalidation for a long R:R")
    return reward / risk


class CorrectionType(Enum):
    TIME = "TIME"
    PRICE = "PRICE"
    MIXED = "MIXED"
    UNKNOWN = "UNKNOWN"


def correction_type(bars_since_swing_high: Optional[int],
                    retrace_pct: Optional[float],
                    *,
                    time_min_bars: int = 10,
                    price_min_pct: float = 10.0) -> CorrectionType:
    """TIME correction = sideways long enough (bars) without deep retrace;
    PRICE = deep retrace without the time; both = MIXED; insufficient
    structure = UNKNOWN. Time logic is code, not LLM prose (manual P2.7)."""
    if bars_since_swing_high is None or retrace_pct is None:
        return CorrectionType.UNKNOWN
    deep = retrace_pct >= price_min_pct
    long = bars_since_swing_high >= time_min_bars
    if deep and long:
        return CorrectionType.MIXED
    if deep:
        return CorrectionType.PRICE
    if long:
        return CorrectionType.TIME
    return CorrectionType.UNKNOWN
