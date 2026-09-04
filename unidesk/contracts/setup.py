"""Setup contracts (build manual §4.5): SetupCandidate."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Optional

from .base import (
    ContractError,
    coerce_enum,
    ensure_date,
    ensure_utc,
    require_bool,
    require_float,
    require_int,
    require_non_negative,
    require_opt_float,
    require_opt_int,
    require_opt_str,
    require_str,
    require_str_tuple,
    require_unit_interval,
)


class SetupType(Enum):
    MOMENTUM_BURST = "MOMENTUM_BURST"
    EPISODIC_PIVOT = "EPISODIC_PIVOT"
    IPO_BASE = "IPO_BASE"
    INSIDE_BAR = "INSIDE_BAR"
    BASE_BREAKOUT = "BASE_BREAKOUT"
    PULLBACK = "PULLBACK"
    REVERSAL_RECLAIM = "REVERSAL_RECLAIM"
    POWER_PLAY = "POWER_PLAY"


class DetectionState(Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass(frozen=True)
class SetupCandidate:
    setup_id: str
    symbol: str
    detected_at: datetime
    setup_type: SetupType
    geometry_version: str
    pivot_price: float
    trigger_price: float
    structural_low: float
    setup_start: date
    setup_age_sessions: int
    base_depth_pct: Optional[float]
    contraction_ratio: Optional[float]
    rest_depth_atr: Optional[float]
    volume_dryup_ratio: Optional[float]
    gap_pct: Optional[float]
    breakout_rvol: Optional[float]
    distance_from_pivot_pct: Optional[float]
    deterministic_valid: DetectionState
    rule_failures: tuple
    setup_quality_score: Optional[float]
    model_probability: Optional[float] = None
    model_version: Optional[str] = None
    similarity_score: Optional[float] = None
    nearest_gold_case_id: Optional[str] = None

    def __post_init__(self):
        _set = lambda n, v: object.__setattr__(self, n, v)  # noqa: E731
        _set("setup_id", require_str(self.setup_id, "setup_id"))
        _set("symbol", require_str(self.symbol, "symbol"))
        _set("detected_at", ensure_utc(self.detected_at, "detected_at"))
        _set("setup_type", coerce_enum(self.setup_type, SetupType, "setup_type"))
        _set("geometry_version", require_str(self.geometry_version, "geometry_version"))
        for name in ("pivot_price", "trigger_price", "structural_low"):
            _set(name, require_non_negative(require_float(getattr(self, name), name), name))
        _set("setup_start", ensure_date(self.setup_start, "setup_start"))
        _set("setup_age_sessions", require_non_negative(require_int(self.setup_age_sessions, "setup_age_sessions"), "setup_age_sessions"))
        for name in ("base_depth_pct", "contraction_ratio", "rest_depth_atr",
                     "volume_dryup_ratio", "breakout_rvol", "distance_from_pivot_pct",
                     "setup_quality_score"):
            _set(name, require_opt_float(getattr(self, name), name))
        # A gap can be negative (down gap); only sanity-check it is finite.
        _set("gap_pct", require_opt_float(self.gap_pct, "gap_pct"))
        _set("deterministic_valid", coerce_enum(self.deterministic_valid, DetectionState, "deterministic_valid"))
        _set("rule_failures", require_str_tuple(self.rule_failures, "rule_failures"))
        if self.deterministic_valid is DetectionState.INVALID and self.setup_quality_score is not None:
            raise ContractError("an INVALID setup cannot carry a setup_quality_score (manual P2.4 acceptance)")
        _set("model_probability", require_unit_interval(self.model_probability, "model_probability"))
        _set("model_version", require_opt_str(self.model_version, "model_version"))
        _set("similarity_score", require_unit_interval(self.similarity_score, "similarity_score"))
        _set("nearest_gold_case_id", require_opt_str(self.nearest_gold_case_id, "nearest_gold_case_id"))
