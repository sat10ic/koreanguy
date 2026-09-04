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
        "REVIEW_REQUIRED",
        "room_rule_was_inverted_fixed_20260830_pending_reaudit",
        rankable=False,
    ),
    "ipo_base": _trust(
        "VERIFIED",
        "listing_age_verified_via_listing_calendar_20260904_owner_approved",
        rankable=True,
    ),
    "pullback": _trust(
        "REVIEW_REQUIRED",
        "anchor_proximity_had_no_direction_fixed_20260830_pending_reaudit",
        rankable=False,
    ),
    "reversal_reclaim": _trust(
        "REVIEW_REQUIRED",
        "historical_reclaim_used_current_ema_fixed_20260830_pending_reaudit",
        rankable=False,
    ),
    "momentum_burst": _trust(
        "REVIEW_REQUIRED",
        "avwap_extension_guard_was_inert_fixed_20260830_pending_reaudit",
        rankable=False,
    ),
    "power_play": _trust(
        "REVIEW_REQUIRED",
        "universe_eligibility_now_wired_hazardous_cohort_pending_reaudit",
        rankable=False,
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
