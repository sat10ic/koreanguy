"""Stock-quality snapshot (build manual Task P1.9).

Composes the deterministic momentum features into ONE explainable score with
hard properties:

* **Decomposable.** The score is a weighted mean of named contributors, each
  reported with its raw value, normalized 0..100 value, weight, and
  availability. No hidden arithmetic.
* **Nulls reduce coverage, never become zeros (R12).** An unavailable
  contributor is excluded from the numerator AND denominator, and its named
  reason lands in ``unknowns``. If available weight falls below
  ``min_coverage``, the score itself is None with ``INSUFFICIENT_DATA``.
* **Individually disableable (R15).** Weights come in as a caller-supplied
  mapping (config policy, R14 — nothing hard-coded here); a weight of 0 is
  the same as absence.
* **Hard gates ride beside the score.** Circuit UC/LC risk becomes a
  hard_gate; policy consumes gates separately from the score (veto authority
  is not a number).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Mapping, Optional, Sequence

from unidesk.contracts.base import ContractError, ensure_utc, require_str
from unidesk.momentum.features.circuit import CircuitRiskState
from unidesk.momentum.features.trend import TrendState

CONTRIBUTOR_NAMES = ("trend", "rs_rank", "rvol", "delivery_ratio", "room_to_52w_high", "circuit_safety")
_MIN_COVERAGE = 0.6  # below this share of weights available, no score at all

_TREND_SCORES = {
    TrendState.STRONG_UPTREND: 100.0,
    TrendState.UPTREND: 75.0,
    TrendState.TRANSITION: 40.0,
    TrendState.WEAK: 0.0,
}


@dataclass(frozen=True)
class Contributor:
    name: str
    available: bool
    normalized: Optional[float]     # 0..100; None when unavailable
    weight: float
    reason: Optional[str] = None    # named unavailability (R12), never a default


@dataclass(frozen=True)
class StockQualitySnapshot:
    symbol: str
    as_of: datetime
    score: Optional[float]          # 0..100; None = insufficient data (never a guess)
    coverage: float                 # available weight / total configured weight
    contributors: tuple
    unknowns: tuple                 # named reasons, deduplicated, order-stable
    hard_gates: tuple               # e.g. ("CIRCUIT_UC_RISK",) — policy consumes these
    feature_version: str
    config_hash: str

    def contributor(self, name: str) -> Optional[Contributor]:
        for c in self.contributors:
            if c.name == name:
                return c
        return None


def _clamp100(v: float) -> float:
    return max(0.0, min(100.0, v))


def _normalize_rvol(rvol: float, strong: float, exceptional: float) -> float:
    """0 at no participation, `strong` maps to 75, `exceptional`+ saturates 100."""
    if exceptional <= strong or strong <= 0:
        raise ContractError("require 0 < strong < exceptional for rvol normalization")
    scale = 75.0 / strong
    return _clamp100(rvol * scale if rvol <= exceptional else 100.0 + 0.0 * (rvol - exceptional))


def _normalize_room(pct: float, full_marks_at: float) -> float:
    """distance from the 52W high, in %: 0 (at the high) -> 100;
    `full_marks_at` (a positive %) below it -> 0. Linear in between."""
    if full_marks_at <= 0:
        raise ContractError("full_marks_at must be positive")
    return _clamp100(100.0 * (1.0 + pct / full_marks_at))


def stock_quality_snapshot(
    symbol: str,
    as_of: datetime,
    *,
    weights: Mapping[str, float],
    trend_state: Optional[TrendState],
    rs_rank: Optional[float],
    rvol: Optional[float],
    delivery_ratio: Optional[float],
    distance_52w_high_pct: Optional[float],
    circuit_state: Optional[CircuitRiskState],
    rvol_strong: float = 1.5,
    rvol_exceptional: float = 2.0,
    room_full_marks_at_pct: float = 25.0,
    min_coverage: float = _MIN_COVERAGE,
    feature_version: str = "",
    config_hash: str = "",
) -> StockQualitySnapshot:
    symbol = require_str(symbol, "symbol")
    as_of = ensure_utc(as_of, "as_of")
    feature_version = require_str(feature_version, "feature_version")
    config_hash = require_str(config_hash, "config_hash")

    unknown_weights = set(weights) - set(CONTRIBUTOR_NAMES)
    if unknown_weights:
        raise ContractError(f"unknown contributor weights: {sorted(unknown_weights)}")
    for name, w in weights.items():
        if not isinstance(w, (int, float)) or isinstance(w, bool) or w < 0:
            raise ContractError(f"weight for {name} must be a non-negative number")

    total_weight = sum(weights.values())
    if total_weight <= 0:
        raise ContractError("total configured weight must be positive")

    hard_gates = []
    if circuit_state in (CircuitRiskState.UC_RISK, CircuitRiskState.LC_RISK):
        hard_gates.append(f"CIRCUIT_{circuit_state.value}")

    raw: dict[str, tuple[bool, Optional[float], Optional[str]]] = {}

    if trend_state is None:
        raw["trend"] = (False, None, "TREND_STATE_UNAVAILABLE")
    else:
        raw["trend"] = (True, _TREND_SCORES[trend_state], None)

    raw["rs_rank"] = (
        (False, None, "RS_RANK_UNAVAILABLE") if rs_rank is None
        else (True, _clamp100(rs_rank), None)
    )
    raw["rvol"] = (
        (False, None, "RVOL_UNAVAILABLE") if rvol is None
        else (True, _normalize_rvol(rvol, rvol_strong, rvol_exceptional), None)
    )
    raw["delivery_ratio"] = (
        (False, None, "DELIVERY_RATIO_UNAVAILABLE") if delivery_ratio is None
        else (True, _normalize_rvol(delivery_ratio, rvol_strong, rvol_exceptional), None)
    )
    raw["room_to_52w_high"] = (
        (False, None, "DISTANCE_52W_UNAVAILABLE") if distance_52w_high_pct is None
        else (True, _normalize_room(distance_52w_high_pct, room_full_marks_at_pct), None)
    )
    if circuit_state is None:
        raw["circuit_safety"] = (False, None, "CIRCUIT_STATE_UNAVAILABLE")
    elif circuit_state is CircuitRiskState.UNKNOWN:
        raw["circuit_safety"] = (False, None, "CIRCUIT_BANDS_NOT_PUBLISHED")
    elif circuit_state is CircuitRiskState.NONE:
        raw["circuit_safety"] = (True, 100.0, None)
    else:  # UC/LC risk: available contributor scoring 0, plus the hard gate
        raw["circuit_safety"] = (True, 0.0, f"circuit_{circuit_state.value.lower()}")

    contributors = []
    available_weight = 0.0
    weighted_sum = 0.0
    unknowns: list = []
    for name in CONTRIBUTOR_NAMES:
        w = float(weights.get(name, 0.0))
        available, normalized, reason = raw[name]
        if w == 0.0:
            continue  # disabled via config (R15) — absent from the snapshot math
        contributors.append(Contributor(name=name, available=available,
                                        normalized=round(normalized, 3) if normalized is not None else None,
                                        weight=w, reason=reason))
        if available:
            available_weight += w
            weighted_sum += w * normalized
        else:
            unknowns.append(reason)

    coverage = available_weight / total_weight
    if coverage < min_coverage:
        unknowns.append("INSUFFICIENT_DATA")
        score = None
    else:
        score = round(weighted_sum / available_weight, 3)

    unknowns = list(dict.fromkeys(unknowns))  # dedupe, order-stable
    return StockQualitySnapshot(
        symbol=symbol,
        as_of=as_of,
        score=score,
        coverage=round(coverage, 3),
        contributors=tuple(contributors),
        unknowns=tuple(unknowns),
        hard_gates=tuple(hard_gates),
        feature_version=feature_version,
        config_hash=config_hash,
    )
