"""Decision contracts (build manual §4.11–4.12): ContextJudgeOutput,
DecisionSnapshot. The LLM never authors a numeric trading field; policy_state
is deterministic policy output, not judge opinion (R2/R3)."""
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
    require_str,
    require_str_tuple,
    require_unit_interval,
)
from .flow import FlowState, LiquidityState


class ConfluenceGrade(Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    UNKNOWN = "UNKNOWN"


class SocialRelevance(Enum):
    MATERIAL = "MATERIAL"
    MINOR = "MINOR"
    NONE = "NONE"
    UNKNOWN = "UNKNOWN"


class PolicyState(Enum):
    ELIGIBLE = "ELIGIBLE"
    WAIT = "WAIT"
    WARN = "WARN"
    VETO = "VETO"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ContextJudgeOutput:
    judge_id: str
    candidate_id: str
    created_at: datetime
    summary: str
    confluence_grade: ConfluenceGrade
    strongest_supporting_factors: tuple
    strongest_risks: tuple
    contradictions: tuple
    unknowns: tuple
    social_context_relevance: SocialRelevance
    explanation: str
    prompt_version: str
    model_name: str
    model_version: str
    input_hash: str

    def __post_init__(self):
        _set = lambda n, v: object.__setattr__(self, n, v)  # noqa: E731
        _set("judge_id", require_str(self.judge_id, "judge_id"))
        _set("candidate_id", require_str(self.candidate_id, "candidate_id"))
        _set("created_at", ensure_utc(self.created_at, "created_at"))
        _set("summary", require_str(self.summary, "summary"))
        _set("confluence_grade", coerce_enum(self.confluence_grade, ConfluenceGrade, "confluence_grade"))
        for name in ("strongest_supporting_factors", "strongest_risks",
                     "contradictions", "unknowns"):
            _set(name, require_str_tuple(getattr(self, name), name))
        _set("social_context_relevance", coerce_enum(self.social_context_relevance, SocialRelevance, "social_context_relevance"))
        _set("explanation", require_str(self.explanation, "explanation"))
        _set("prompt_version", require_str(self.prompt_version, "prompt_version"))
        _set("model_name", require_str(self.model_name, "model_name"))
        _set("model_version", require_str(self.model_version, "model_version"))
        _set("input_hash", require_str(self.input_hash, "input_hash"))


@dataclass(frozen=True)
class DecisionSnapshot:
    decision_id: str
    candidate_id: str
    as_of: datetime
    stock_quality: Optional[float]
    setup_quality: Optional[float]
    entry_quality: Optional[float]
    liquidity_state: LiquidityState
    flow_state: FlowState
    flow_confidence: Optional[float]
    social_context_state: str
    judge_grade: ConfluenceGrade
    policy_state: PolicyState
    hard_gates: tuple
    warnings: tuple
    unknowns: tuple
    source_snapshot_ids: tuple
    config_hash: str
    policy_version: str

    def __post_init__(self):
        _set = lambda n, v: object.__setattr__(self, n, v)  # noqa: E731
        _set("decision_id", require_str(self.decision_id, "decision_id"))
        _set("candidate_id", require_str(self.candidate_id, "candidate_id"))
        _set("as_of", ensure_utc(self.as_of, "as_of"))
        for name in ("stock_quality", "setup_quality", "entry_quality"):
            _set(name, require_opt_float(getattr(self, name), name))
        _set("liquidity_state", coerce_enum(self.liquidity_state, LiquidityState, "liquidity_state"))
        _set("flow_state", coerce_enum(self.flow_state, FlowState, "flow_state"))
        _set("flow_confidence", require_unit_interval(self.flow_confidence, "flow_confidence"))
        _set("social_context_state", require_str(self.social_context_state, "social_context_state"))
        _set("judge_grade", coerce_enum(self.judge_grade, ConfluenceGrade, "judge_grade"))
        _set("policy_state", coerce_enum(self.policy_state, PolicyState, "policy_state"))
        for name in ("hard_gates", "warnings", "unknowns", "source_snapshot_ids"):
            _set(name, require_str_tuple(getattr(self, name), name))
        _set("config_hash", require_str(self.config_hash, "config_hash"))
        _set("policy_version", require_str(self.policy_version, "policy_version"))
        if self.liquidity_state is LiquidityState.REJECT and self.policy_state is not PolicyState.VETO:
            raise ContractError("liquidity REJECT must surface as policy VETO (R6/R7: social context cannot rescue, flow cannot be argued away)")
