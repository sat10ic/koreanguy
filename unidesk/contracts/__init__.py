"""Shared desk contracts (build manual §4). Schema-only until Phases 1-3
produce real data; every contract validates fail-closed (unknown enums raise,
nulls stay null, as_of mandatory and tz-aware, versions/hashes mandatory)."""
from .base import ContractError, from_dict, to_dict
from .market import DailyBar, IntradayBar, SymbolMaster, Timeframe
from .candidate import (
    AvwapAnchor,
    AvwapRef,
    CandidateContext,
    MomentumContextSnapshot,
    TrendState,
)
from .setup import DetectionState, SetupCandidate, SetupType
from .geometry import CorrectionType, GeometryState, TradeGeometrySnapshot
from .flow import (
    FeedHealth,
    FlowDecision,
    FlowState,
    LiquidityState,
    OrderFlowAssessment,
)
from .social import ClaimType, ReviewState, SocialClaim, SocialContextSnapshot, TraderContext
from .decision import (
    ConfluenceGrade,
    ContextJudgeOutput,
    DecisionSnapshot,
    PolicyState,
    SocialRelevance,
)
from .research import ResearchEvent

__all__ = [
    "ContractError",
    "to_dict",
    "from_dict",
    "SymbolMaster",
    "DailyBar",
    "IntradayBar",
    "Timeframe",
    "MomentumContextSnapshot",
    "AvwapRef",
    "AvwapAnchor",
    "TrendState",
    "CandidateContext",
    "SetupCandidate",
    "SetupType",
    "DetectionState",
    "TradeGeometrySnapshot",
    "CorrectionType",
    "GeometryState",
    "OrderFlowAssessment",
    "FeedHealth",
    "LiquidityState",
    "FlowState",
    "FlowDecision",
    "SocialClaim",
    "SocialContextSnapshot",
    "TraderContext",
    "ClaimType",
    "ReviewState",
    "ContextJudgeOutput",
    "DecisionSnapshot",
    "ConfluenceGrade",
    "SocialRelevance",
    "PolicyState",
    "ResearchEvent",
]
