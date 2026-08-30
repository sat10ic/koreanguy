"""The remaining seven setup detectors (build manual Task P2.3).

Same discipline as ``momentum_burst``: thin rule composition over
caller-computed, point-in-time feature values; every threshold is a
parameter (R14); failures are named; missing mandatory inputs give
INSUFFICIENT_DATA — never a guess. Inputs are documented per detector.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from unidesk.momentum.detectors.engine import Detection, Rule, evaluate_rules


def _r(name: str, value: Optional[float], *, op: str, limit: float,
       optional: bool = False, fmt: str = ".2f") -> Rule:
    """Helper: a threshold rule ``value <op> limit`` (e.g. value >= limit)."""
    import operator
    ops = {">=": operator.ge, "<=": operator.le, ">": operator.gt, "<": operator.lt}
    if value is None:
        return Rule(name=name, available=False, passed=None, optional=optional)
    passed = ops[op](value, limit)
    return Rule(
        name=name, available=True, passed=passed, optional=optional,
        detail=f"{name} {value:{fmt}} {op} {limit:g} failed" if not passed else "",
    )


def _bool(name: str, available: bool, passed: Optional[bool], detail: str = "",
          optional: bool = False) -> Rule:
    return Rule(name=name, available=available, passed=passed, detail=detail, optional=optional)


# ---------------------------------------------------------------- episodic pivot


def episodic_pivot(*, gap_pct: Optional[float], rvol: Optional[float],
                   close_location: Optional[float], delivery_ratio: Optional[float],
                   min_gap_pct: float = 2.5, min_rvol: float = 3.0,
                   min_close_location: float = 0.7) -> tuple[Detection, tuple]:
    """Inputs: gap over prior close (%), RVOL, close's location in the day
    range (0=low, 1=high), delivery ratio (optional context)."""
    rules = [
        _r("gap_pct", gap_pct, op=">=", limit=min_gap_pct),
        _r("rvol", rvol, op=">=", limit=min_rvol),
        _r("close_location", close_location, op=">=", limit=min_close_location),
        _r("delivery_ratio", delivery_ratio, op=">=", limit=1.0, optional=True),
    ]
    return evaluate_rules(rules)


# ---------------------------------------------------------------- IPO base


def ipo_base(*, listing_age_sessions: Optional[int], base_depth_pct: Optional[float],
             contraction_ratio: Optional[float], rs_rank: Optional[float],
             distance_from_listing_high_pct: Optional[float],
             min_age: int = 10, max_age: int = 250, max_base_depth_pct: float = 35.0,
             max_contraction_ratio: float = 0.8, min_rs_rank: float = 70.0,
             max_distance_from_high_pct: float = 25.0) -> tuple[Detection, tuple]:
    rules = [
        _r("listing_age_sessions", listing_age_sessions, op=">=", limit=min_age, fmt="d"),
        _r("listing_age_sessions", listing_age_sessions, op="<=", limit=max_age, fmt="d"),
        _r("base_depth_pct", base_depth_pct, op="<=", limit=max_base_depth_pct),
        _r("contraction_ratio", contraction_ratio, op="<=", limit=max_contraction_ratio),
        _r("rs_rank", rs_rank, op=">=", limit=min_rs_rank, fmt=".1f"),
        _r("distance_from_listing_high_pct", distance_from_listing_high_pct,
           op="<=", limit=max_distance_from_high_pct),
    ]
    return evaluate_rules(rules)


# ---------------------------------------------------------------- inside bar


def inside_bar(*, is_inside_bar: Optional[bool], mother_range_pct: Optional[float],
               volume_ratio_bar_to_mother: Optional[float], rs_rank: Optional[float],
               min_mother_range_pct: float = 3.0, max_volume_ratio: float = 1.0,
               min_rs_rank: float = 70.0) -> tuple[Detection, tuple]:
    rules = [
        _bool("inside_bar_geometry", is_inside_bar is not None,
              None if is_inside_bar is None else is_inside_bar,
              "bar is not an inside bar"),
        _r("mother_range_pct", mother_range_pct, op=">=", limit=min_mother_range_pct),
        _r("volume_ratio_bar_to_mother", volume_ratio_bar_to_mother,
           op="<=", limit=max_volume_ratio),
        _r("rs_rank", rs_rank, op=">=", limit=min_rs_rank, fmt=".1f"),
    ]
    return evaluate_rules(rules)


# ---------------------------------------------------------------- base breakout


def base_breakout(*, breakout_rvol: Optional[float], base_depth_pct: Optional[float],
                  contraction_ratio: Optional[float], rs_rank: Optional[float],
                  close_cleared_pivot: Optional[bool], blue_sky: Optional[bool],
                  overhead_room_adr: Optional[float],
                  min_breakout_rvol: float = 1.5, max_base_depth_pct: float = 35.0,
                  max_contraction_ratio: float = 0.8, min_rs_rank: float = 70.0,
                  min_room_adr: float = 1.0) -> tuple[Detection, tuple]:
    pivot_rule = _bool(
        "close_cleared_pivot",
        close_cleared_pivot is not None,
        close_cleared_pivot,
        "close did not clear the prior base pivot",
    )
    if blue_sky is None:
        room_rule = _bool("blue_sky", False, None)
    elif blue_sky:
        room_rule = _bool("blue_sky", True, True)
    else:
        room_rule = _r("overhead_room_adr", overhead_room_adr, op=">=", limit=min_room_adr)

    rules = [
        pivot_rule,
        _r("breakout_rvol", breakout_rvol, op=">=", limit=min_breakout_rvol),
        _r("base_depth_pct", base_depth_pct, op="<=", limit=max_base_depth_pct),
        _r("contraction_ratio", contraction_ratio, op="<=", limit=max_contraction_ratio),
        _r("rs_rank", rs_rank, op=">=", limit=min_rs_rank, fmt=".1f"),
        room_rule,
    ]
    return evaluate_rules(rules)


# ---------------------------------------------------------------- pullback


def pullback(*, proximity_to_anchor_pct: Optional[float], pullback_volume_ratio: Optional[float],
             rs_rank: Optional[float], adr_pct: Optional[float],
             max_proximity_pct: float = 3.0, max_pullback_volume_ratio: float = 0.8,
             min_rs_rank: float = 70.0, min_adr_pct: float = 3.0) -> tuple[Detection, tuple]:
    """Proximity to the EP/breakout AVWAP or EMA21 (|distance| in %);
    pullback_volume_ratio = pullback-session volume vs up-leg mean (<1 healthy)."""
    rules = [
        _r("proximity_to_anchor_pct", proximity_to_anchor_pct, op="<=", limit=max_proximity_pct),
        _r("pullback_volume_ratio", pullback_volume_ratio, op="<=", limit=max_pullback_volume_ratio),
        _r("rs_rank", rs_rank, op=">=", limit=min_rs_rank, fmt=".1f"),
        _r("adr_pct", adr_pct, op=">=", limit=min_adr_pct),
    ]
    return evaluate_rules(rules)


# ---------------------------------------------------------------- reversal / reclaim


def reversal_reclaim(*, reclaimed: Optional[bool], volume_expansion: Optional[float],
                     rs_improving: Optional[bool], failed_breakdown: Optional[bool],
                     min_volume_expansion: float = 1.3) -> tuple[Detection, tuple]:
    rules = [
        _bool("reclaimed_level", reclaimed is not None,
              None if reclaimed is None else reclaimed, "level not reclaimed"),
        _r("volume_expansion", volume_expansion, op=">=", limit=min_volume_expansion),
        _bool("rs_improving", rs_improving is not None,
              None if rs_improving is None else rs_improving, "RS not improving"),
        _bool("failed_breakdown", failed_breakdown is not None,
              None if failed_breakdown is None else failed_breakdown,
              "no failed-breakdown evidence", optional=True),
    ]
    return evaluate_rules(rules)


# ---------------------------------------------------------------- power play


def power_play(*, adr_pct: Optional[float], rvol: Optional[float],
               contraction_ratio: Optional[float],
               min_adr_pct: float = 6.0, min_rvol: float = 2.0,
               max_contraction_ratio: float = 0.5) -> tuple[Detection, tuple]:
    rules = [
        _r("adr_pct", adr_pct, op=">=", limit=min_adr_pct),
        _r("rvol", rvol, op=">=", limit=min_rvol),
        _r("contraction_ratio", contraction_ratio, op="<=", limit=max_contraction_ratio),
    ]
    return evaluate_rules(rules)
