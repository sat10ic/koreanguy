"""Trade geometry contracts (build manual §4.6): TradeGeometrySnapshot."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from .base import (
    coerce_enum,
    ensure_utc,
    require_float,
    require_non_negative,
    require_opt_float,
    require_opt_str,
    require_str,
    require_str_tuple,
)


class CorrectionType(Enum):
    TIME = "TIME"
    PRICE = "PRICE"
    MIXED = "MIXED"
    UNKNOWN = "UNKNOWN"


class GeometryState(Enum):
    CLEAN = "CLEAN"
    ACCEPTABLE = "ACCEPTABLE"
    EXTENDED = "EXTENDED"
    POOR_ROOM = "POOR_ROOM"
    BAD_RR = "BAD_RR"
    INVALID = "INVALID"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class TradeGeometrySnapshot:
    geometry_id: str
    setup_id: str
    as_of: datetime
    current_price: float
    trigger_price: float
    trigger_distance_pct: float
    invalidation_price: Optional[float]
    stop_distance_pct: Optional[float]
    nearest_resistance: Optional[float]
    resistance_source: Optional[str]
    breakout_room_pct: Optional[float]
    breakout_room_adr: Optional[float]
    ema21_extension_pct: Optional[float]
    avwap_extension_pct: Optional[float]
    avwap_extension_adr: Optional[float]
    correction_type: CorrectionType
    initial_rr_to_resistance: Optional[float]
    entry_quality_score: Optional[float]
    geometry_state: GeometryState
    reason_codes: tuple
    geometry_version: str
    config_hash: str

    def __post_init__(self):
        _set = lambda n, v: object.__setattr__(self, n, v)  # noqa: E731
        _set("geometry_id", require_str(self.geometry_id, "geometry_id"))
        _set("setup_id", require_str(self.setup_id, "setup_id"))
        _set("as_of", ensure_utc(self.as_of, "as_of"))
        for name in ("current_price", "trigger_price"):
            _set(name, require_non_negative(require_float(getattr(self, name), name), name))
        _set("trigger_distance_pct", require_float(self.trigger_distance_pct, "trigger_distance_pct"))
        for name in ("invalidation_price", "nearest_resistance", "breakout_room_pct",
                     "breakout_room_adr", "ema21_extension_pct", "avwap_extension_pct",
                     "avwap_extension_adr", "initial_rr_to_resistance",
                     "entry_quality_score"):
            _set(name, require_opt_float(getattr(self, name), name))
        _set("stop_distance_pct", require_opt_float(self.stop_distance_pct, "stop_distance_pct"))
        _set("resistance_source", require_opt_str(self.resistance_source, "resistance_source"))
        _set("correction_type", coerce_enum(self.correction_type, CorrectionType, "correction_type"))
        _set("geometry_state", coerce_enum(self.geometry_state, GeometryState, "geometry_state"))
        _set("reason_codes", require_str_tuple(self.reason_codes, "reason_codes"))
        _set("geometry_version", require_str(self.geometry_version, "geometry_version"))
        _set("config_hash", require_str(self.config_hash, "config_hash"))
