"""Research contract stub (build manual §7 / Task P7.1).

Lean versioned envelope for the frozen decision-time state. The full
Research Event Store (labels, ablation ladder, negative-findings wiring) is
Phase 7 work; this stub exists so later phases cannot invent an unversioned
shape.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping

from .base import ContractError, ensure_utc, require_str


@dataclass(frozen=True)
class ResearchEvent:
    event_id: str
    candidate_id: str
    symbol: str
    timestamp: datetime
    snapshot: Mapping[str, Any]
    config_hash: str
    research_schema_version: str
    outcome_labels: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        _set = lambda n, v: object.__setattr__(self, n, v)  # noqa: E731
        _set("event_id", require_str(self.event_id, "event_id"))
        _set("candidate_id", require_str(self.candidate_id, "candidate_id"))
        _set("symbol", require_str(self.symbol, "symbol"))
        _set("timestamp", ensure_utc(self.timestamp, "timestamp"))
        if not isinstance(self.snapshot, Mapping) or not self.snapshot:
            raise ContractError("snapshot must be a non-empty mapping of the frozen decision-time state")
        _set("config_hash", require_str(self.config_hash, "config_hash"))
        _set("research_schema_version", require_str(self.research_schema_version, "research_schema_version"))
        if not isinstance(self.outcome_labels, Mapping):
            raise ContractError("outcome_labels must be a mapping (may be empty until P7.2 labels run)")
