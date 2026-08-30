"""Point-in-time clean-room episode and preset contracts."""
from datetime import date, timedelta

from unidesk.momentum.detectors.base_episode import (
    BaseAnnotationKind,
    BasePreset,
    base_episode_from_bars,
    match_base_preset,
)
from unidesk.momentum.detectors.base_pattern import BaseRules, DailyBar


def _bar(i: int, close: float, high: float, low: float, volume: float) -> DailyBar:
    return DailyBar(
        day=date(2026, 1, 1) + timedelta(days=i),
        open=close, high=high, low=low, close=close, volume=volume,
    )


def _vcp_like_bars() -> list[DailyBar]:
    bars = [_bar(i, 80 + i, 81 + i, 79 + i, 1_000) for i in range(7)]
    bars.append(_bar(7, 100, 110, 99, 1_000))
    bars.extend(_bar(i, 95, 96, 90, 1_000) for i in range(8, 18))
    bars.extend(_bar(i, 96, 101 if i == 18 else 96, 94, 500) for i in range(18, 28))
    return bars


def test_episode_carries_stable_provenance_and_annotation_knowledge_dates():
    bars = _vcp_like_bars()
    episode = base_episode_from_bars(
        symbol="DEMO",
        bars=bars,
        rules=BaseRules(swing_left_right=2),
        rs_rank=85,
        adjustment_basis_hash="ca-v1",
    )

    assert episode is not None
    assert episode.episode_id == "DEMO:2026-01-09:cleanroom-base-v1:ca-v1"
    assert episode.base_start == date(2026, 1, 9)
    assert episode.as_of == episode.known_at == date(2026, 1, 28)
    squat = next(a for a in episode.annotations if a.kind is BaseAnnotationKind.SQUAT)
    assert squat.occurred_at == squat.known_at == date(2026, 1, 19)


def test_vcp_match_explains_inclusion_and_other_presets_fail_closed_when_context_is_missing():
    episode = base_episode_from_bars(
        symbol="DEMO", bars=_vcp_like_bars(), rules=BaseRules(swing_left_right=2),
        rs_rank=85, adjustment_basis_hash="ca-v1",
    )
    assert episode is not None

    vcp = match_base_preset(episode, BasePreset.VCP)
    assert vcp.included is True
    assert vcp.failed_rules == ()

    blue_sky = match_base_preset(episode, BasePreset.BLUE_SKY)
    assert blue_sky.included is False
    assert blue_sky.failed_rules == ("requires_52_week_high_context",)
