"""Named detector registry (P2.3): each detector is separately disableable.

``evaluate_all`` runs the enabled subset only — a disabled detector is
absent from the result, never silently VALID. Unknown names fail closed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from unidesk.contracts.base import ContractError
from unidesk.momentum.detectors.momentum_burst import BurstRules, Detection, momentum_burst
from unidesk.momentum.detectors.setups import (
    base_breakout, episodic_pivot, inside_bar, ipo_base, power_play,
    pullback, reversal_reclaim,
)

DETECTOR_NAMES: tuple[str, ...] = (
    "momentum_burst",
    "episodic_pivot",
    "ipo_base",
    "inside_bar",
    "base_breakout",
    "pullback",
    "reversal_reclaim",
    "power_play",
)


@dataclass(frozen=True)
class DetectorConfig:
    """Enable-set for the eight P2.3 detectors. Default: all on."""

    enabled: frozenset[str] = frozenset(DETECTOR_NAMES)
    burst_rules: BurstRules = BurstRules()

    def __post_init__(self) -> None:
        unknown = set(self.enabled) - set(DETECTOR_NAMES)
        if unknown:
            raise ContractError(f"unknown detector name(s): {sorted(unknown)}")
        object.__setattr__(self, "enabled", frozenset(self.enabled))

    @classmethod
    def only(cls, names: Iterable[str], **kwargs) -> "DetectorConfig":
        return cls(enabled=frozenset(names), **kwargs)

    def is_enabled(self, name: str) -> bool:
        return name in self.enabled


def evaluate_detector(name: str, inputs: dict, *,
                      config: Optional[DetectorConfig] = None) -> tuple[Detection, tuple]:
    """Run one named detector over a frozen input dict."""
    if name not in DETECTOR_NAMES:
        raise ContractError(f"unknown detector: {name!r}")
    cfg = config or DetectorConfig()
    g = inputs.get
    if name == "momentum_burst":
        d = momentum_burst(
            adr_pct=g("adr_pct"), rs_rank=g("rs_rank"), rvol=g("rvol"),
            contraction_ratio=g("contraction_ratio"),
            avwap_extension_adr=g("avwap_extension_adr"),
            rules=cfg.burst_rules,
        )
        return d.detection, d.rule_failures
    if name == "episodic_pivot":
        return episodic_pivot(
            gap_pct=g("gap_pct"), rvol=g("rvol"),
            close_location=g("close_location"), delivery_ratio=g("delivery_ratio"),
        )
    if name == "ipo_base":
        return ipo_base(
            listing_age_sessions=g("listing_age_sessions"),
            base_depth_pct=g("base_depth_pct"),
            contraction_ratio=g("contraction_ratio"),
            rs_rank=g("rs_rank"),
            distance_from_listing_high_pct=g("distance_from_listing_high_pct"),
        )
    if name == "inside_bar":
        return inside_bar(
            is_inside_bar=g("is_inside_bar"),
            mother_range_pct=g("mother_range_pct"),
            volume_ratio_bar_to_mother=g("volume_ratio_bar_to_mother"),
            rs_rank=g("rs_rank"),
        )
    if name == "base_breakout":
        return base_breakout(
            breakout_rvol=g("breakout_rvol"),
            base_depth_pct=g("base_breakout_depth_pct"),
            contraction_ratio=g("base_breakout_contraction_ratio"),
            rs_rank=g("rs_rank"),
            close_cleared_pivot=g("close_cleared_pivot"),
            blue_sky=g("blue_sky"),
            overhead_room_adr=g("overhead_room_adr"),
        )
    if name == "pullback":
        return pullback(
            proximity_to_anchor_pct=g("proximity_to_anchor_pct"),
            pullback_volume_ratio=g("pullback_volume_ratio"),
            rs_rank=g("rs_rank"),
            adr_pct=g("adr_pct"),
        )
    if name == "reversal_reclaim":
        return reversal_reclaim(
            reclaimed=g("reclaimed"),
            volume_expansion=g("volume_expansion"),
            rs_improving=g("rs_improving"),
            failed_breakdown=g("failed_breakdown"),
        )
    if name == "power_play":
        return power_play(
            adr_pct=g("adr_pct"), rvol=g("rvol"),
            contraction_ratio=g("contraction_ratio"),
        )
    raise ContractError(f"unhandled detector: {name!r}")


def evaluate_all(inputs: dict, *,
                 config: Optional[DetectorConfig] = None) -> dict:
    """``name -> (Detection, failures)`` for every enabled detector."""
    cfg = config or DetectorConfig()
    out: dict = {}
    for name in DETECTOR_NAMES:
        if not cfg.is_enabled(name):
            continue
        out[name] = evaluate_detector(name, inputs, config=cfg)
    return out
