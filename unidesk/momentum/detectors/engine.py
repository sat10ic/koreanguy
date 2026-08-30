"""Rule-composition engine for setup detectors (build manual Task P2.3).

Every detector is a named set of rules over caller-computed features. No
detector contains math or I/O; thresholds arrive as parameters (R14). The
shared evaluation:

* any non-optional rule that is unavailable → ``INSUFFICIENT_DATA``
* any failed (available) rule → ``INVALID`` with the named failure
* otherwise → ``VALID``
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Sequence

from unidesk.contracts.base import ContractError
from unidesk.momentum.detectors.momentum_burst import Detection


@dataclass(frozen=True)
class Rule:
    """One named deterministic rule. ``available=False`` means the caller
    could not compute the input (missing data — R12); ``optional=True`` rules
    may be unavailable without forcing INSUFFICIENT_DATA (their absence is
    recorded as a skipped rule)."""

    name: str
    available: bool
    passed: Optional[bool]
    detail: str = ""
    optional: bool = False


def evaluate_rules(rules: Sequence[Rule]) -> tuple[Detection, tuple]:
    missing = [r.name for r in rules if not r.available and not r.optional]
    if missing:
        return Detection.INSUFFICIENT_DATA, tuple(f"missing:{m}" for m in missing)
    failures = []
    skipped = []
    for r in rules:
        if not r.available:
            skipped.append(f"skipped:{r.name}")
            continue
        if r.passed is False:
            failures.append(r.detail or r.name)
    if failures:
        return Detection.INVALID, tuple(failures)
    if skipped:
        return Detection.VALID, tuple(skipped)  # valid, with honest skipped notes
    return Detection.VALID, ()
