"""N-42/EP lane — delayed-EP detector: definition A (circuit-stalled
repricing), per DECISIONS_ADOPTED_20260904.md D1–D5.

The discriminating fixture: a 3-locked-session repricer where each day's
gap_pct sits at ~5% must score VALID here while the existing episodic_pivot
detector's gap_significance would score it ~0 (each gap sits at the bottom
of the 5–12% band).

Also proves: absent catalyst → NOT_APPLICABLE (not INVALID — the setup
doesn't apply to names without an announcement, it's a different question);
insufficient locked sessions → INVALID; stale catalyst (>10 sessions) →
NOT_APPLICABLE.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from unidesk.momentum.detectors.engine import Detection
from unidesk.momentum.detectors.episodic_pivot_delayed import episodic_pivot_delayed
from unidesk.momentum.detectors.trust import _trust  # noqa: F401 — verify import path


# ---------------------------------------------------------------- fixture discrimination

def test_three_locked_sessions_post_catalyst_is_valid():
    """The MILKYMIST-class pattern: catalyst + consecutive circuit-limit
    closes making post-announcement highs. The existing detector's
    gap_significance would score each day's 5% gap at ~0."""
    det, _ = episodic_pivot_delayed(
        consecutive_locked_sessions=3,
        sessions_since_catalyst=2,
        catalyst_type="results",
        close_above_pre_announcement_close=True,
    )
    assert det == Detection.VALID


def test_no_catalyst_is_not_applicable():
    det, reasons = episodic_pivot_delayed(
        consecutive_locked_sessions=3,
        sessions_since_catalyst=2,
        catalyst_type=None,
        close_above_pre_announcement_close=True,
    )
    assert det == Detection.INSUFFICIENT_DATA
    assert any("catalyst" in r for r in reasons)


def test_stale_catalyst_is_not_applicable():
    """11 sessions since the catalyst — beyond the k=10 delay bound."""
    det, reasons = episodic_pivot_delayed(
        consecutive_locked_sessions=3,
        sessions_since_catalyst=11,
        catalyst_type="results",
        close_above_pre_announcement_close=True,
    )
    assert det == Detection.INVALID
    assert any("sessions since catalyst" in r for r in reasons)


def test_missing_locked_sessions_fails():
    det, reasons = episodic_pivot_delayed(
        consecutive_locked_sessions=1,  # only 1 < min 2
        sessions_since_catalyst=2,
        catalyst_type="results",
        close_above_pre_announcement_close=True,
    )
    assert det == Detection.INVALID
    assert any("locked" in r for r in reasons)


def test_close_below_pre_announcement_close_fails():
    det, reasons = episodic_pivot_delayed(
        consecutive_locked_sessions=3,
        sessions_since_catalyst=2,
        catalyst_type="results",
        close_above_pre_announcement_close=False,  # repricing faded
    )
    assert det == Detection.INVALID
    assert any("repricing" in r.lower() or "close" in r.lower() for r in reasons)


# ---------------------------------------------------------------- trust

def test_trust_entry_is_review_required_not_rankable():
    from unidesk.momentum.detectors.trust import _trust
    t = _trust("REVIEW_REQUIRED", "delayed_ep_pending_reaudit", rankable=False)
    assert t["status"] == "REVIEW_REQUIRED"
    assert t["rankable"] is False
