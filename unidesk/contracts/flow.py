"""Order flow contract (build manual §4.8): OrderFlowAssessment.

This is the desk-level output the orderflow package will produce in Phase 3;
`capability_version` ties every assessment to the measured feed capability
(`orderflow/capability.json`, schema_version), never to an assumption.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from .base import (
    ContractError,
    coerce_enum,
    ensure_utc,
    require_opt_float,
    require_opt_str,
    require_str,
    require_str_tuple,
    require_unit_interval,
)


class FeedHealth(Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    STALE = "STALE"
    DISCONNECTED = "DISCONNECTED"


class LiquidityState(Enum):
    PASS = "PASS"
    WARN = "WARN"
    REJECT = "REJECT"
    UNKNOWN = "UNKNOWN"


class FlowState(Enum):
    STRONG_CONFIRMATION = "STRONG_CONFIRMATION"
    CONFIRMING = "CONFIRMING"
    MIXED = "MIXED"
    WEAK = "WEAK"
    BREAKOUT_RISK = "BREAKOUT_RISK"
    UNTRUSTWORTHY_BOOK = "UNTRUSTWORTHY_BOOK"
    UNKNOWN = "UNKNOWN"


class FlowDecision(Enum):
    CONFIRM = "CONFIRM"
    NEUTRAL = "NEUTRAL"
    WARN = "WARN"
    VETO = "VETO"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class OrderFlowAssessment:
    assessment_id: str
    candidate_id: str
    symbol: str
    assessed_at: datetime
    valid_until: datetime
    feed_health: FeedHealth
    capability_version: str
    liquidity_score: Optional[float]
    liquidity_state: LiquidityState
    capacity_band: Optional[str]
    high_impact_band: Optional[str]
    raw_flow_score: Optional[float]
    flow_confidence: Optional[float]
    effective_flow_score: Optional[float]
    flow_state: FlowState
    decision: FlowDecision
    reason_codes: tuple
    feature_snapshot_id: Optional[str]
    flow_config_hash: str

    def __post_init__(self):
        _set = lambda n, v: object.__setattr__(self, n, v)  # noqa: E731
        _set("assessment_id", require_str(self.assessment_id, "assessment_id"))
        _set("candidate_id", require_str(self.candidate_id, "candidate_id"))
        _set("symbol", require_str(self.symbol, "symbol"))
        _set("assessed_at", ensure_utc(self.assessed_at, "assessed_at"))
        _set("valid_until", ensure_utc(self.valid_until, "valid_until"))
        if self.valid_until < self.assessed_at:
            raise ContractError("valid_until must not precede assessed_at (stale state is UNKNOWN, never persisted green)")
        _set("feed_health", coerce_enum(self.feed_health, FeedHealth, "feed_health"))
        _set("capability_version", require_str(self.capability_version, "capability_version"))
        for name in ("liquidity_score", "raw_flow_score", "effective_flow_score"):
            _set(name, require_opt_float(getattr(self, name), name))
        _set("liquidity_state", coerce_enum(self.liquidity_state, LiquidityState, "liquidity_state"))
        _set("capacity_band", require_opt_str(self.capacity_band, "capacity_band"))
        _set("high_impact_band", require_opt_str(self.high_impact_band, "high_impact_band"))
        _set("flow_confidence", require_unit_interval(self.flow_confidence, "flow_confidence"))
        _set("flow_state", coerce_enum(self.flow_state, FlowState, "flow_state"))
        _set("decision", coerce_enum(self.decision, FlowDecision, "decision"))
        if self.decision is FlowDecision.CONFIRM and self.flow_state is FlowState.UNKNOWN:
            raise ContractError("a CONFIRM decision cannot rest on an UNKNOWN flow state (manual R10)")
        if self.liquidity_state is LiquidityState.REJECT and self.decision is not FlowDecision.VETO:
            raise ContractError("liquidity REJECT must hard-veto (manual P3.5 acceptance)")
        _set("reason_codes", require_str_tuple(self.reason_codes, "reason_codes"))
        _set("feature_snapshot_id", require_opt_str(self.feature_snapshot_id, "feature_snapshot_id"))
        _set("flow_config_hash", require_str(self.flow_config_hash, "flow_config_hash"))
