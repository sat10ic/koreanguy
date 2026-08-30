"""Social contracts (build manual §4.9–4.10): SocialClaim,
SocialContextSnapshot. Context only — no field here may override a market
hard gate (R6)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from .base import (
    ContractError,
    coerce_enum,
    ensure_utc,
    require_bool,
    require_int,
    require_non_negative,
    require_opt_float,
    require_opt_int,
    require_opt_str,
    require_str,
    require_str_tuple,
    require_unit_interval,
)


class ClaimType(Enum):
    ENTRY = "entry"
    ADD = "add"
    STOP_SET = "stop_set"
    STOP_MOVE = "stop_move"
    TARGET = "target"
    PARTIAL_EXIT = "partial_exit"
    FULL_EXIT = "full_exit"
    RESULT_STATEMENT = "result_statement"
    WATCH = "watch"
    THEME = "theme"
    MARKET_VIEW = "market_view"
    LESSON = "lesson"


class ReviewState(Enum):
    PROVISIONAL = "provisional"
    ACCEPTED = "accepted"
    UNRESOLVED = "unresolved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


@dataclass(frozen=True)
class SocialClaim:
    claim_id: str
    post_id: str
    media_idx: Optional[int]
    handle: str
    subject_type: str
    subject: str
    claim_type: ClaimType
    stated_at: datetime
    direction: Optional[str]
    price: Optional[float]
    price_from: Optional[float]
    price_to: Optional[float]
    quantity_pct: Optional[float]
    result_pct: Optional[float]
    text_quote: str
    confidence: Optional[float]
    review_state: ReviewState
    source_kind: str
    source_model: Optional[str]
    evidence_json: str
    unresolved_json: Optional[str]
    supersedes_claim_id: Optional[str]

    def __post_init__(self):
        _set = lambda n, v: object.__setattr__(self, n, v)  # noqa: E731
        _set("claim_id", require_str(self.claim_id, "claim_id"))
        _set("post_id", require_str(self.post_id, "post_id"))
        _set("media_idx", require_opt_int(self.media_idx, "media_idx"))
        _set("handle", require_str(self.handle, "handle"))
        _set("subject_type", require_str(self.subject_type, "subject_type"))
        _set("subject", require_str(self.subject, "subject"))
        _set("claim_type", coerce_enum(self.claim_type, ClaimType, "claim_type"))
        _set("stated_at", ensure_utc(self.stated_at, "stated_at"))
        _set("direction", require_opt_str(self.direction, "direction"))
        for name in ("price", "price_from", "price_to", "quantity_pct", "result_pct"):
            _set(name, require_opt_float(getattr(self, name), name))
        _set("text_quote", require_str(self.text_quote, "text_quote"))
        _set("confidence", require_unit_interval(self.confidence, "confidence"))
        _set("review_state", coerce_enum(self.review_state, ReviewState, "review_state"))
        _set("source_kind", require_str(self.source_kind, "source_kind"))
        _set("source_model", require_opt_str(self.source_model, "source_model"))
        _set("evidence_json", require_str(self.evidence_json, "evidence_json"))
        _set("unresolved_json", require_opt_str(self.unresolved_json, "unresolved_json"))
        _set("supersedes_claim_id", require_opt_str(self.supersedes_claim_id, "supersedes_claim_id"))


@dataclass(frozen=True)
class TraderContext:
    handle: str
    recent_action: str
    historical_sample_n: int
    specialization_tags: tuple

    def __post_init__(self):
        _set = lambda n, v: object.__setattr__(self, n, v)  # noqa: E731
        _set("handle", require_str(self.handle, "handle"))
        _set("recent_action", require_str(self.recent_action, "recent_action"))
        _set("historical_sample_n", require_non_negative(require_int(self.historical_sample_n, "historical_sample_n"), "historical_sample_n"))
        _set("specialization_tags", require_str_tuple(self.specialization_tags, "specialization_tags"))


@dataclass(frozen=True)
class SocialContextSnapshot:
    snapshot_id: str
    symbol: str
    as_of: datetime
    accepted_entry_count_5d: Optional[int]
    accepted_add_count_5d: Optional[int]
    accepted_exit_count_5d: Optional[int]
    independent_trader_count: Optional[int]
    attention_trend: Optional[str]
    theme_mentions: tuple
    disagreement_present: Optional[bool]
    recent_claim_ids: tuple
    recent_evidence_refs: tuple
    trader_context: tuple
    coverage_state: str
    unresolved_count: int
    social_pipeline_version: str

    def __post_init__(self):
        _set = lambda n, v: object.__setattr__(self, n, v)  # noqa: E731
        _set("snapshot_id", require_str(self.snapshot_id, "snapshot_id"))
        _set("symbol", require_str(self.symbol, "symbol"))
        _set("as_of", ensure_utc(self.as_of, "as_of"))
        for name in ("accepted_entry_count_5d", "accepted_add_count_5d",
                     "accepted_exit_count_5d", "independent_trader_count"):
            _set(name, require_opt_int(getattr(self, name), name))
        _set("attention_trend", require_opt_str(self.attention_trend, "attention_trend"))
        _set("theme_mentions", require_str_tuple(self.theme_mentions, "theme_mentions"))
        if self.disagreement_present is not None:
            _set("disagreement_present", require_bool(self.disagreement_present, "disagreement_present"))
        _set("recent_claim_ids", require_str_tuple(self.recent_claim_ids, "recent_claim_ids"))
        _set("recent_evidence_refs", require_str_tuple(self.recent_evidence_refs, "recent_evidence_refs"))
        if not isinstance(self.trader_context, tuple) or any(
            not isinstance(t, TraderContext) for t in self.trader_context
        ):
            raise ContractError("trader_context must be a tuple of TraderContext")
        _set("coverage_state", require_str(self.coverage_state, "coverage_state"))
        _set("unresolved_count", require_non_negative(require_int(self.unresolved_count, "unresolved_count"), "unresolved_count"))
        _set("social_pipeline_version", require_str(self.social_pipeline_version, "social_pipeline_version"))
