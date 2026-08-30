"""Audit-backed consumer trust for raw detector verdicts.

Trust is deliberately separate from a detector's deterministic result: an
older raw scan must remain inspectable, while report consumers can refuse to
rank output from a detector known to be wrong-as-built.
"""
from __future__ import annotations

from types import MappingProxyType
from typing import Mapping


TRUST_VERSION = "audit-2026-08-30"


def _trust(status: str, reason: str, *, rankable: bool) -> dict[str, object]:
    return {
        "status": status,
        "reason": reason,
        "version": TRUST_VERSION,
        "rankable": rankable,
    }


_TRUST: Mapping[str, dict[str, object]] = MappingProxyType({
    "episodic_pivot": _trust("VERIFIED", "audit_passed", rankable=True),
    "inside_bar": _trust("VERIFIED", "audit_passed", rankable=True),
    "base_breakout": _trust(
        "BLOCKED", "missing_breakout_condition_and_inverted_room_rule", rankable=False
    ),
    "ipo_base": _trust("BLOCKED", "listing_age_is_not_verified", rankable=False),
    "pullback": _trust("BLOCKED", "anchor_proximity_has_no_direction", rankable=False),
    "reversal_reclaim": _trust(
        "BLOCKED", "historical_reclaim_uses_current_ema", rankable=False
    ),
    "momentum_burst": _trust(
        "REVIEW_REQUIRED", "avwap_extension_guard_is_inert", rankable=False
    ),
    "power_play": _trust(
        "REVIEW_REQUIRED", "universe_eligibility_not_yet_wired", rankable=False
    ),
})


def detector_trust(name: str) -> dict[str, object]:
    """Return a copy, including a fail-closed entry for unknown detectors."""
    item = _TRUST.get(name)
    if item is None:
        return _trust("BLOCKED", "unknown_detector_has_no_audit", rankable=False)
    return dict(item)


def detector_trust_map() -> dict[str, dict[str, object]]:
    """A JSON-safe snapshot for a nightly report."""
    return {name: dict(value) for name, value in _TRUST.items()}
