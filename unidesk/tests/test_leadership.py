"""N-26/N-27 — leadership lifecycle + concentration/density/size guard."""
from __future__ import annotations

import pytest

from unidesk.research.leadership import (
    candidate_density, final_leadership_state, raw_leadership_state,
    theme_size_guard, top3_contribution,
)


# --- N-26: raw lifecycle states ---

def test_leading_breadth_60_plus_with_positive_accel():
    assert raw_leadership_state(65.0, 0.001) == "LEADING"


def test_mature_breadth_60_plus_with_negative_accel():
    assert raw_leadership_state(65.0, -0.001) == "MATURE"


def test_emerging_45_to_60_positive_accel():
    assert raw_leadership_state(50.0, 0.001) == "EMERGING"


def test_fading_45_to_50_negative_accel():
    assert raw_leadership_state(47.0, -0.001) == "FADING"


def test_awakening_30_to_45_positive_accel():
    assert raw_leadership_state(35.0, 0.001) == "AWAKENING"


def test_weak_below_30_or_negative_accel():
    assert raw_leadership_state(20.0, 0.001) == "WEAK"
    assert raw_leadership_state(35.0, -0.001) == "WEAK"


def test_dormant_when_breadth_none():
    assert raw_leadership_state(None, 0.001) == "DORMANT"
    assert raw_leadership_state(None, None) == "DORMANT"


# --- N-26: hysteresis ---

def test_hysteresis_holds_old_state_until_min_sessions():
    # raw says EMERGING but prior is LEADING with age 1 < 3 → stays LEADING
    final, _, age = final_leadership_state("EMERGING", "LEADING", 1)
    assert final == "LEADING" and age == 2
    # age reaches 3 → flips
    final, _, age = final_leadership_state("EMERGING", "LEADING", 3)
    assert final == "EMERGING" and age == 0


def test_hysteresis_same_state_increments_age():
    final, _, age = final_leadership_state("LEADING", "LEADING", 5)
    assert final == "LEADING" and age == 6


# --- N-27: concentration + density + size guard ---

def test_top3_contribution_broad():
    # 10 groups with equal share → top3 = 30% → BROAD
    groups = {f"g{i}": 10 for i in range(10)}
    assert top3_contribution(groups) == "BROAD"


def test_top3_contribution_mixed():
    groups = {"a": 25, "b": 25, "c": 25, "d": 15, "e": 10}
    assert top3_contribution(groups) == "MIXED"  # top3 = 75% (0.5 ≤ 0.75 < 0.8)


def test_top3_contribution_concentrated():
    groups = {"a": 85, "b": 5, "c": 5, "d": 5}
    assert top3_contribution(groups) == "CONCENTRATED"


def test_top3_contribution_zero_candidates_is_broad():
    assert top3_contribution({}) == "BROAD"


def test_candidate_density_none_when_no_members():
    assert candidate_density(5, 0) is None


def test_candidate_density_computed():
    assert candidate_density(2, 20) == 0.1


def test_theme_size_guard():
    assert theme_size_guard(3) == "LOW_SAMPLE"
    assert theme_size_guard(4) == "OK"
    assert theme_size_guard(50) == "OK"
