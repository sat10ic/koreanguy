"""Momentum Burst detector (build manual Task P2.3) — the first setup
detector: thin RULE COMPOSITION over already-computed features.

The detector owns no math: every input is a value computed by a feature
module or the caller (point-in-time, config-sourced thresholds). It returns
VALID / INVALID / INSUFFICIENT_DATA with named rule failures — never a score
(setup quality is P2.4, only after deterministic validity).

Inputs per the manual's Momentum Burst spec: prior expansion (adr_pct),
relative strength (rs_rank 0..100), participation (rvol), the current shelf
(contraction ratio), and AVWAP extension context. All thresholds are
parameters.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from unidesk.contracts.base import ContractError, require_float


class Detection(Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass(frozen=True)
class BurstRules:
    min_adr_pct: float = 3.0           # prior expansion: ADR20 at least this % of price
    min_rs_rank: float = 70.0          # leadership: universe percentile
    min_rvol: float = 1.5              # participation
    max_contraction_ratio: float = 0.8  # shelf: recent range contracting vs prior
    max_avwap_extension_adr: float = 3.0   # not too extended from the cost basis


@dataclass(frozen=True)
class BurstDecision:
    detection: Detection
    rule_failures: tuple
    rules: BurstRules


def momentum_burst(
    *,
    adr_pct: Optional[float],
    rs_rank: Optional[float],
    rvol: Optional[float],
    contraction_ratio: Optional[float],
    avwap_extension_adr: Optional[float],
    rules: BurstRules = BurstRules(),
) -> BurstDecision:
    for name, v in (("adr_pct", adr_pct), ("rs_rank", rs_rank), ("rvol", rvol),
                    ("contraction_ratio", contraction_ratio),
                    ("avwap_extension_adr", avwap_extension_adr)):
        if v is not None:
            require_float(v, name)

    missing = [n for n, v in (("adr_pct", adr_pct), ("rs_rank", rs_rank),
                              ("rvol", rvol), ("contraction_ratio", contraction_ratio))
               if v is None]
    if missing:
        return BurstDecision(Detection.INSUFFICIENT_DATA, tuple(f"missing:{m}" for m in missing), rules)
    # AVWAP extension is contextual: absent -> rule skipped, recorded as a
    # failure only if the caller wants strictness. Kept lenient here (P2.3
    # lists AVWAP extension as an input, but a burst without a nearby anchor
    # is not unknowable — it is unconstrained).

    failures = []
    if adr_pct < rules.min_adr_pct:                       # type: ignore[operator]
        failures.append(f"adr_pct {adr_pct:.2f} < {rules.min_adr_pct}")
    if rs_rank < rules.min_rs_rank:                       # type: ignore[operator]
        failures.append(f"rs_rank {rs_rank:.1f} < {rules.min_rs_rank}")
    if rvol < rules.min_rvol:                             # type: ignore[operator]
        failures.append(f"rvol {rvol:.2f} < {rules.min_rvol}")
    if contraction_ratio > rules.max_contraction_ratio:    # type: ignore[operator]
        failures.append(f"contraction_ratio {contraction_ratio:.2f} > {rules.max_contraction_ratio}")
    if avwap_extension_adr is not None and avwap_extension_adr > rules.max_avwap_extension_adr:
        failures.append(f"avwap_extension_adr {avwap_extension_adr:.2f} > {rules.max_avwap_extension_adr}")

    detection = Detection.VALID if not failures else Detection.INVALID
    return BurstDecision(detection, tuple(failures), rules)
