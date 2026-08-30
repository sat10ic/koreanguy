"""Detector + geometry tests: one VALID/INVALID path per detector,
hand-computed geometry, entry-quality bands and coverage honesty."""
import pytest
from datetime import datetime, timezone

from unidesk.contracts.base import ContractError
from unidesk.momentum.detectors.momentum_burst import Detection
from unidesk.momentum.detectors.setups import (
    base_breakout, episodic_pivot, inside_bar, ipo_base, power_play,
    pullback, reversal_reclaim,
)
from unidesk.momentum.features.geometry import (
    breakout_room, correction_type, initial_rr, room_adr,
    stop_distance_pct, trigger_distance_pct, CorrectionType,
)
from unidesk.momentum.scoring.entry_quality import entry_quality_snapshot

UTC = timezone.utc
T0 = datetime(2026, 6, 30, 10, 0, tzinfo=UTC)


def test_episodic_pivot_paths():
    ok = episodic_pivot(gap_pct=4.0, rvol=4.0, close_location=0.9, delivery_ratio=1.2)
    assert ok[0] is Detection.VALID
    bad = episodic_pivot(gap_pct=1.0, rvol=1.0, close_location=0.4, delivery_ratio=None)
    assert bad[0] is Detection.INVALID and len(bad[1]) == 3
    part = episodic_pivot(gap_pct=None, rvol=4.0, close_location=0.9, delivery_ratio=None)
    assert part[0] is Detection.INSUFFICIENT_DATA


def test_ipo_base_two_sided_age_window():
    ok = ipo_base(listing_age_sessions=30, base_depth_pct=20.0, contraction_ratio=0.6,
                  rs_rank=80.0, distance_from_listing_high_pct=10.0)
    assert ok[0] is Detection.VALID
    too_fresh = ipo_base(listing_age_sessions=5, base_depth_pct=20.0, contraction_ratio=0.6,
                         rs_rank=80.0, distance_from_listing_high_pct=10.0)
    assert too_fresh[0] is Detection.INVALID
    too_old = ipo_base(listing_age_sessions=400, base_depth_pct=20.0, contraction_ratio=0.6,
                       rs_rank=80.0, distance_from_listing_high_pct=10.0)
    assert too_old[0] is Detection.INVALID


def test_inside_bar_geometry_rule():
    ok = inside_bar(is_inside_bar=True, mother_range_pct=4.0,
                    volume_ratio_bar_to_mother=0.7, rs_rank=80.0)
    assert ok[0] is Detection.VALID
    not_inside = inside_bar(is_inside_bar=False, mother_range_pct=4.0,
                            volume_ratio_bar_to_mother=0.7, rs_rank=80.0)
    assert not_inside[0] is Detection.INVALID
    assert not_inside[1][0] == "bar is not an inside bar"


def test_base_breakout_room_rule():
    ok = base_breakout(breakout_rvol=2.0, base_depth_pct=25.0, contraction_ratio=0.7,
                       rs_rank=85.0, room_adr=2.0)
    assert ok[0] is Detection.VALID
    no_room = base_breakout(breakout_rvol=2.0, base_depth_pct=25.0, contraction_ratio=0.7,
                            rs_rank=85.0, room_adr=0.5)
    assert no_room[0] is Detection.INVALID
    assert any("room_adr" in f for f in no_room[1])


def test_pullback_and_reversal_paths():
    ok = pullback(proximity_to_anchor_pct=1.5, pullback_volume_ratio=0.6,
                  rs_rank=80.0, adr_pct=4.0)
    assert ok[0] is Detection.VALID
    rev_ok = reversal_reclaim(reclaimed=True, volume_expansion=1.6,
                              rs_improving=True, failed_breakdown=True)
    assert rev_ok[0] is Detection.VALID
    rev_opt = reversal_reclaim(reclaimed=True, volume_expansion=1.6,
                               rs_improving=True, failed_breakdown=None)
    assert rev_opt[0] is Detection.VALID
    assert rev_opt[1] == ("skipped:failed_breakdown",)


def test_power_play_paths():
    ok = power_play(adr_pct=8.0, rvol=3.0, contraction_ratio=0.4)
    assert ok[0] is Detection.VALID
    tight = power_play(adr_pct=4.0, rvol=1.5, contraction_ratio=0.9)
    assert tight[0] is Detection.INVALID and len(tight[1]) == 3


# ------------------------------------------------------------------ geometry


def test_trigger_and_stop_distances_signed():
    assert trigger_distance_pct(100.0, 102.0) == pytest.approx(2.0)    # waiting above
    assert trigger_distance_pct(103.0, 102.0) == pytest.approx(-100/103*1.0)  # already through
    assert stop_distance_pct(100.0, 95.0) == pytest.approx(5.0)
    assert stop_distance_pct(94.0, 95.0) < 0                            # below invalidation


def test_room_and_rr_hand_computed():
    assert breakout_room(100.0, 115.0) == pytest.approx(15.0)
    assert room_adr(15.0, 5.0) == pytest.approx(3.0)
    assert initial_rr(entry=100.0, invalidation=95.0, hurdle=115.0) == pytest.approx(3.0)
    with pytest.raises(ContractError):
        initial_rr(entry=94.0, invalidation=95.0, hurdle=115.0)   # stop above entry


def test_correction_type_table():
    assert correction_type(3, 12.0, time_min_bars=10) is CorrectionType.PRICE
    assert correction_type(15, 4.0, time_min_bars=10) is CorrectionType.TIME
    assert correction_type(15, 12.0, time_min_bars=10) is CorrectionType.MIXED
    assert correction_type(3, 4.0, time_min_bars=10) is CorrectionType.UNKNOWN
    assert correction_type(None, None, time_min_bars=10) is CorrectionType.UNKNOWN


# ------------------------------------------------------------------ entry quality


def test_entry_quality_bands_and_score():
    w = {"room_adr": 25, "initial_rr": 25, "ema21_extension": 25, "trigger_proximity": 25}
    # room exactly 3.0 ADR -> 75 (band boundary <=3.0); RR 4:1 -> clamped 100;
    # extension 0% -> 100; trigger 0.5% -> 100 - (0.5/3)*80 = 86.67
    s = entry_quality_snapshot(
        "TRENT", T0, current=100.0, trigger=100.5, invalidation=95.0,
        hurdle=115.0, adr_pct=5.0, ema21_extension_pct=0.0,
        weights=w, feature_version="fv", config_hash="cfg")
    assert s.coverage == 1.0
    assert s.score == pytest.approx((75 + 100 + 100 + 86.667) / 4, abs=0.1)
    assert s.unknowns == ()


def test_entry_quality_missing_extension_reduces_coverage():
    w = {"room_adr": 25, "initial_rr": 25, "ema21_extension": 25, "trigger_proximity": 25}
    s = entry_quality_snapshot(
        "TRENT", T0, current=100.0, trigger=100.5, invalidation=95.0,
        hurdle=115.0, adr_pct=5.0, ema21_extension_pct=None,
        weights=w, feature_version="fv", config_hash="cfg")
    assert s.coverage == 0.75
    assert "EMA21_EXTENSION_UNAVAILABLE" in s.unknowns
    assert s.score == pytest.approx((75 + 100 + 86.667) / 3, abs=0.1)


def test_entry_quality_unknown_weights_rejected():
    with pytest.raises(ContractError):
        entry_quality_snapshot(
            "TRENT", T0, current=100.0, trigger=100.5, invalidation=95.0,
            hurdle=115.0, adr_pct=5.0, ema21_extension_pct=0.0,
            weights={"vibes": 50}, feature_version="fv", config_hash="cfg")
