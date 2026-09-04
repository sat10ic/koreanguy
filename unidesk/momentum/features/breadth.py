"""Breadth analytics — pure functions adopted from market-breadth reverse
engineering (HANDOFF_GEMINI_breadth_analytics_COMPLETED.md).

Formulas reverse-engineered from Market Breadth V2.0.xlsm, implemented as
pure Python over a ``counts`` dict (not SQLite, so unidesk does not import
manas_os or traderlog per D4). Each function takes a counts dict with the
standard breadth-count keys and returns a float or None.

Adopted from manas_os/regime/breadth_analytics.py on 2026-08-31.
"""
from __future__ import annotations

from typing import Optional


def net_nh_nl(counts: dict) -> Optional[float]:
    """Net (new-52wk-high% - new-52wk-low%) * 100."""
    univ = counts.get("total_universe", 0)
    if univ <= 0:
        return None
    nh = counts.get("new_52wk_high")
    nl = counts.get("new_52wk_low")
    if nh is None or nl is None:
        return None
    return (nh / univ - nl / univ) * 100.0


def volatility_ratio(counts: dict) -> Optional[float]:
    """range_expansion / range_contraction (universe cancels out)."""
    rc = counts.get("range_contraction", 0)
    if rc <= 0:
        return None
    re = counts.get("range_expansion", 0)
    if re is None:
        return None
    return re / rc


def volume_ratio(counts: dict) -> Optional[float]:
    """high_vol / low_vol (universe cancels out)."""
    lv = counts.get("low_vol", 0)
    if lv <= 0:
        return None
    hv = counts.get("high_vol", 0)
    if hv is None:
        return None
    return hv / lv


def bo_bd_ratio(counts: dict) -> Optional[float]:
    """Breakout / Breakdown ratio."""
    bd = counts.get("breakdowns", 0)
    if bd <= 0:
        return None
    bo = counts.get("breakouts", 0)
    if bo is None:
        return None
    return bo / bd


def up_down_close_pct(counts: dict) -> Optional[float]:
    """Close upper half % / lower half %."""
    lh = counts.get("close_lower_half", 0)
    if lh <= 0:
        return None
    uh = counts.get("close_upper_half", 0)
    if uh is None:
        return None
    return uh / lh * 100.0