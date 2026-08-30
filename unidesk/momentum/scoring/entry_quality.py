"""Entry-quality composite (build manual Task P2.8) — the same
coverage-honest contributor pattern as the stock-quality snapshot, with
BAND normalizers that are caller parameters (R14), mapping:

    room_adr            <1 poor 0 · 1–2 marginal 40 · 2–3 good 75 · >3 excellent 100
    initial_rr          1:1 -> 33 · 2:1 -> 66 · 3:1+ -> 100 (linear, clamped)
    ema21_extension_pct 0 -> 100 · 15%+ -> 0 (chase risk), linear, clamped
    trigger_proximity   0–0.5% of trigger -> 100 · 3%+ -> 20 (waiting, not fatal)

Hard honesty: a negative trigger distance (already through the trigger) and
a negative room are AVAILABLE contributors scoring by the same bands — the
geometry state, not the score, decides tradeability.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Sequence

from unidesk.contracts.base import ContractError, ensure_utc, require_str
from unidesk.momentum.features.geometry import (
    breakout_room, initial_rr, room_adr, trigger_distance_pct,
)

CONTRIBUTOR_NAMES = ("room_adr", "initial_rr", "ema21_extension", "trigger_proximity")


@dataclass(frozen=True)
class EntryQualitySnapshot:
    symbol: str
    as_of: datetime
    score: Optional[float]
    coverage: float
    unknowns: tuple
    feature_version: str
    config_hash: str


def _clamp100(v: float) -> float:
    return max(0.0, min(100.0, v))


def _band(v: float, bands: Sequence[tuple]) -> float:
    """bands: ordered [(upper_bound_inclusive, score)] — first band whose
    bound >= v wins; the last band is the ceiling."""
    for bound, score in bands:
        if v <= bound:
            return float(score)
    return float(bands[-1][1])


def entry_quality_snapshot(
    symbol: str,
    as_of: datetime,
    *,
    current: float,
    trigger: float,
    invalidation: float,
    hurdle: float,
    adr_pct: float,
    ema21_extension_pct: Optional[float],
    weights: dict,
    min_coverage: float = 0.75,
    feature_version: str = "",
    config_hash: str = "",
) -> EntryQualitySnapshot:
    symbol = require_str(symbol, "symbol")
    as_of = ensure_utc(as_of, "as_of")
    feature_version = require_str(feature_version, "feature_version")
    config_hash = require_str(config_hash, "config_hash")
    unknown_weights = set(weights) - set(CONTRIBUTOR_NAMES)
    if unknown_weights:
        raise ContractError(f"unknown contributor weights: {sorted(unknown_weights)}")
    total = sum(weights.values())
    if total <= 0:
        raise ContractError("total configured weight must be positive")

    room_pct = breakout_room(current, hurdle)
    ra = room_adr(room_pct, adr_pct)
    rr = initial_rr(current, invalidation, hurdle)
    tp = trigger_distance_pct(current, trigger)

    values = {
        "room_adr": _band(max(ra, 0.0), [(1.0, 0.0), (2.0, 40.0), (3.0, 75.0), (float("inf"), 100.0)]),
        "initial_rr": _clamp100(rr / 3.0 * 100.0),
        "ema21_extension": None if ema21_extension_pct is None
        else _clamp100(100.0 - (ema21_extension_pct / 15.0) * 100.0),
        "trigger_proximity": None if tp < 0 else _clamp100(
            100.0 - (tp / 3.0) * 80.0),  # 0–0.5% ≈ 87–100; 3%+ floors near 20
    }
    reasons = {
        "ema21_extension": "EMA21_EXTENSION_UNAVAILABLE",
        "trigger_proximity": "TRIGGER_ALREADY_PASSED",
    }

    available_weight = 0.0
    weighted = 0.0
    unknowns: list = []
    for name in CONTRIBUTOR_NAMES:
        w = float(weights.get(name, 0.0))
        if w == 0:
            continue
        v = values[name]
        if v is None:
            unknowns.append(reasons[name])
            continue
        available_weight += w
        weighted += w * v

    coverage = available_weight / total
    score = None
    if coverage < min_coverage:
        unknowns.append("INSUFFICIENT_DATA")
    else:
        score = round(weighted / available_weight, 3)

    return EntryQualitySnapshot(
        symbol=symbol, as_of=as_of, score=score, coverage=round(coverage, 3),
        unknowns=tuple(dict.fromkeys(unknowns)),
        feature_version=feature_version, config_hash=config_hash,
    )
