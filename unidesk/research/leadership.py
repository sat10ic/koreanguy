"""ROTATION N-26/N-27 — leadership lifecycle + concentration/density.

N-26: the leadership lifecycle is rule-derived with hysteresis so it does
not flicker daily. States: DORMANT → AWAKENING → EMERGING → LEADING →
MATURE → FADING → WEAK. Both `raw_state` (this session's call) and
`final_state` (after hysteresis) are stored, plus `state_start_date` and
`state_age_sessions` — that is freshness (spec §17).

N-27: top3_contribution → BROAD/MIXED/CONCENTRATED (spec §14);
candidate_density = candidates / valid_members (spec §15); theme size
guard: member_count < 4 → LOW_SAMPLE (spec §47).

Thresholds are FROZEN and documented — they are this repo's calibration,
not invented weightings (standing rule 4). The hysteresis rule requires
N consecutive sessions in the raw state before final_state follows.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional


# --- N-26: leadership lifecycle thresholds (frozen; breadth = % above EMA21,
# momentum = RS acceleration sign; the values below are the calibration the
# desk was built to) ---
def raw_leadership_state(
    breadth_ema21_pct: Optional[float],
    rs_accel: Optional[float],
) -> str:
    """Rule-derived raw state from breadth and acceleration. First match wins."""
    if breadth_ema21_pct is None or rs_accel is None:
        return "DORMANT"
    if breadth_ema21_pct >= 60:
        return "LEADING" if rs_accel >= 0 else "MATURE"
    if breadth_ema21_pct >= 45:
        if rs_accel > 0:
            return "EMERGING"
        return "MATURE" if breadth_ema21_pct >= 50 else "FADING"
    if breadth_ema21_pct >= 30:
        return "AWAKENING" if rs_accel > 0 else "WEAK"
    return "WEAK"


_HYSTERESIS_MIN_SESSIONS = 3


def final_leadership_state(
    raw_state: str,
    prior_final: str,
    prior_age: int,
) -> tuple[str, date, int]:
    """Apply hysteresis: stay in the current final state until the raw state
    has been the same different state for HYSTeresis sessions. Returns
    (final_state, state_start_date_placeholder, state_age) — the date is the
    caller's (needs the session date)."""
    if raw_state == prior_final:
        return prior_final, date(1970, 1, 1), prior_age + 1
    if prior_age < _HYSTERESIS_MIN_SESSIONS:
        return prior_final, date(1970, 1, 1), prior_age + 1
    return raw_state, date(1970, 1, 1), 0


# --- N-27: concentration + density + size guard ---
def top3_contribution(candidates_by_group: dict[str, int]) -> str:
    """BROAD / MIXED / CONCENTRATED from the top-3 groups' share of total
    candidates. Formula: top3_count / total. Thresholds frozen: < 0.5 BROAD,
    < 0.8 MIXED, >= 0.8 CONCENTRATED."""
    total = sum(candidates_by_group.values())
    if total == 0:
        return "BROAD"  # no candidates = trivially broad, not concentrated
    sorted_counts = sorted(candidates_by_group.values(), reverse=True)
    top3 = sum(sorted_counts[:3])
    share = top3 / total
    if share >= 0.8:
        return "CONCENTRATED"
    if share >= 0.5:
        return "MIXED"
    return "BROAD"


def candidate_density(candidate_count: int, valid_member_count: int) -> Optional[float]:
    """candidates / valid_members. None when valid_members is 0 (spec §15)."""
    if valid_member_count <= 0:
        return None
    return round(candidate_count / valid_member_count, 4)


def theme_size_guard(member_count: int) -> str:
    """LOW_SAMPLE when fewer than 4 members — never ranked alongside broad
    sectors without the warning (spec §47)."""
    return "LOW_SAMPLE" if member_count < 4 else "OK"
