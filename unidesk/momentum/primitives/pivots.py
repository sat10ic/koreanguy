"""Pivot/swing primitives (build manual Task P2.1).

Fractal pivots with an explicit CONFIRMATION LAG: a pivot high at index ``i``
exists only if ``highs[i]`` is the strict maximum of the window
``i-k .. i+k``. The pivot is KNOWN at index ``i+k`` — never earlier
(``known_at`` is part of the pivot record; manual acceptance: "no future
swing confirmation is used earlier than its confirmation timestamp").

These are primitives, not setups (P2.1). Deterministic: equal neighbors
(ties) reject the pivot (strict comparison), so the same series always
yields the same pivots.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from unidesk.contracts.base import ContractError, require_float


class PivotKind(Enum):
    HIGH = "HIGH"
    LOW = "LOW"


@dataclass(frozen=True)
class Pivot:
    index: int
    price: float
    kind: PivotKind
    known_at: int   # first index at which this pivot is observable


def fractal_pivots(highs: Sequence[float], lows: Sequence[float], k: int) -> list[Pivot]:
    """All k-bar fractal pivots, ordered by index. Strict comparisons: ties
    in the window disqualify the pivot (deterministic, no tie-breaking
    invention)."""
    if k < 1:
        raise ContractError("k must be >= 1")
    h = [require_float(v, f"highs[{i}]") for i, v in enumerate(highs)]
    l = [require_float(v, f"lows[{i}]") for i, v in enumerate(lows)]
    if len(h) != len(l):
        raise ContractError("highs and lows must have equal length")

    out: list[Pivot] = []
    n = len(h)
    for i in range(k, n - k):
        window_h = h[i - k:i + k + 1]
        if h[i] == max(window_h) and window_h.count(h[i]) == 1:
            out.append(Pivot(index=i, price=h[i], kind=PivotKind.HIGH, known_at=i + k))
        window_l = l[i - k:i + k + 1]
        if l[i] == min(window_l) and window_l.count(l[i]) == 1:
            out.append(Pivot(index=i, price=l[i], kind=PivotKind.LOW, known_at=i + k))
    return out


def pivots_known_at(pivots: Sequence[Pivot], as_of_index: int) -> list[Pivot]:
    """The subset observable at ``as_of_index`` — the point-in-time filter
    every downstream consumer MUST apply before using pivots."""
    return [p for p in pivots if p.known_at <= as_of_index]
