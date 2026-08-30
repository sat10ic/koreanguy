"""Candidate contracts (build manual §4.4, §4.7): MomentumContextSnapshot,
CandidateContext."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Optional

from .base import (
    coerce_enum,
    ensure_date,
    ensure_utc,
    require_float,
    require_opt_float,
    require_opt_int,
    require_opt_str,
    require_str,
    require_str_tuple,
)


class TrendState(Enum):
    STRONG_UPTREND = "STRONG_UPTREND"
    UPTREND = "UPTREND"
    TRANSITION = "TRANSITION"
    WEAK = "WEAK"
    UNKNOWN = "UNKNOWN"


class AvwapAnchor(Enum):
    EP = "EP"
    BREAKOUT = "BREAKOUT"
    IPO_LISTING = "IPO_LISTING"
    SWING_LOW = "SWING_LOW"
    EARNINGS = "EARNINGS"
    FIFTY_TWO_W_BREAKOUT = "52W_BREAKOUT"
    ATH_BREAKOUT = "ATH_BREAKOUT"


@dataclass(frozen=True)
class AvwapRef:
    avwap_value: float
    distance_pct: float
    distance_adr: float
    anchor_date: date
    anchor_type: AvwapAnchor

    def __post_init__(self):
        _set = lambda n, v: object.__setattr__(self, n, v)  # noqa: E731
        _set("avwap_value", require_non_neg(self.avwap_value, "avwap_value"))
        _set("distance_pct", require_float(self.distance_pct, "distance_pct"))
        _set("distance_adr", require_float(self.distance_adr, "distance_adr"))
        _set("anchor_date", ensure_date(self.anchor_date, "anchor_date"))
        _set("anchor_type", coerce_enum(self.anchor_type, AvwapAnchor, "anchor_type"))


def require_non_neg(value, field):
    out = require_float(value, field)
    if out < 0:
        from .base import ContractError
        raise ContractError(f"{field} must be non-negative, got {out}")
    return out


@dataclass(frozen=True)
class MomentumContextSnapshot:
    snapshot_id: str
    symbol: str
    as_of: datetime
    market_regime: str
    market_breadth: Optional[float]
    ema21: Optional[float]
    ema50: Optional[float]
    trend_state: TrendState
    rs_market: Optional[float]
    rs_sector: Optional[float]
    rs_rank: Optional[int]
    peer_rank: Optional[int]
    sector_rs: Optional[float]
    sector_breadth: Optional[float]
    theme_context: Optional[str]
    rvol: Optional[float]
    delivery_volume_ratio: Optional[float]
    adr20: Optional[float]
    atr14: Optional[float]
    today_move_adr: Optional[float]
    avwap_refs: tuple
    nearest_avwap: Optional[float]
    avwap_extension_adr: Optional[float]
    distance_52w_high_pct: Optional[float]
    distance_ath_pct: Optional[float]
    liquidity_baseline_score: Optional[float]
    circuit_risk_state: Optional[str]
    surveillance_flags: tuple
    stock_quality_score: Optional[float]
    feature_version: str
    config_hash: str

    def __post_init__(self):
        _set = lambda n, v: object.__setattr__(self, n, v)  # noqa: E731
        _set("snapshot_id", require_str(self.snapshot_id, "snapshot_id"))
        _set("symbol", require_str(self.symbol, "symbol"))
        _set("as_of", ensure_utc(self.as_of, "as_of"))
        _set("market_regime", require_str(self.market_regime, "market_regime"))
        for name in ("market_breadth", "ema21", "ema50", "rs_market", "rs_sector",
                     "sector_rs", "sector_breadth", "rvol", "delivery_volume_ratio",
                     "adr20", "atr14", "today_move_adr", "nearest_avwap",
                     "avwap_extension_adr", "distance_52w_high_pct",
                     "distance_ath_pct", "liquidity_baseline_score",
                     "stock_quality_score"):
            _set(name, require_opt_float(getattr(self, name), name))
        _set("trend_state", coerce_enum(self.trend_state, TrendState, "trend_state"))
        for name in ("rs_rank", "peer_rank"):
            _set(name, require_opt_int(getattr(self, name), name))
        _set("theme_context", require_opt_str(self.theme_context, "theme_context"))
        _set("circuit_risk_state", require_opt_str(self.circuit_risk_state, "circuit_risk_state"))
        if not isinstance(self.avwap_refs, tuple) or any(
            not isinstance(r, AvwapRef) for r in self.avwap_refs
        ):
            raise ValueError("avwap_refs must be a tuple of AvwapRef")
        _set("surveillance_flags", require_str_tuple(self.surveillance_flags, "surveillance_flags"))
        _set("feature_version", require_str(self.feature_version, "feature_version"))
        _set("config_hash", require_str(self.config_hash, "config_hash"))


@dataclass(frozen=True)
class CandidateContext:
    """The frozen handoff consumed by OrderFlow and the Context Judge.
    OrderFlow must never rediscover the setup from scratch (manual R7-era)."""

    candidate_id: str
    as_of: datetime
    symbol: str
    setup_id: str
    setup_type: str
    momentum_snapshot_id: str
    geometry_snapshot_id: str
    stock_quality_score: Optional[float]
    setup_quality_score: Optional[float]
    entry_quality_score: Optional[float]
    trigger_price: float
    invalidation_price: Optional[float]
    market_regime: str
    sector_state: Optional[str]
    theme_context: Optional[str]
    rs_market: Optional[float]
    rs_sector: Optional[float]
    rvol: Optional[float]
    adr20: Optional[float]
    circuit_risk_state: Optional[str]
    surveillance_flags: tuple
    context_version: str
    config_hash: str

    def __post_init__(self):
        _set = lambda n, v: object.__setattr__(self, n, v)  # noqa: E731
        _set("candidate_id", require_str(self.candidate_id, "candidate_id"))
        _set("as_of", ensure_utc(self.as_of, "as_of"))
        _set("symbol", require_str(self.symbol, "symbol"))
        _set("setup_id", require_str(self.setup_id, "setup_id"))
        _set("setup_type", require_str(self.setup_type, "setup_type"))
        _set("momentum_snapshot_id", require_str(self.momentum_snapshot_id, "momentum_snapshot_id"))
        _set("geometry_snapshot_id", require_str(self.geometry_snapshot_id, "geometry_snapshot_id"))
        for name in ("stock_quality_score", "setup_quality_score", "entry_quality_score",
                     "invalidation_price", "rs_market", "rs_sector", "rvol", "adr20"):
            _set(name, require_opt_float(getattr(self, name), name))
        _set("trigger_price", require_non_neg(self.trigger_price, "trigger_price"))
        _set("market_regime", require_str(self.market_regime, "market_regime"))
        _set("sector_state", require_opt_str(self.sector_state, "sector_state"))
        _set("theme_context", require_opt_str(self.theme_context, "theme_context"))
        _set("circuit_risk_state", require_opt_str(self.circuit_risk_state, "circuit_risk_state"))
        _set("surveillance_flags", require_str_tuple(self.surveillance_flags, "surveillance_flags"))
        _set("context_version", require_str(self.context_version, "context_version"))
        _set("config_hash", require_str(self.config_hash, "config_hash"))
