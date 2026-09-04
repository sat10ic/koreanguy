"""Delayed EP detector (definition A: circuit-stalled repricing).

Detects stocks where a catalyst-driven repricing COMPLETES OVER k sessions
instead of day 0 — the pattern the current `episodic_pivot` detector is
structurally blind to (`gap_significance` scores a sequence of 5% circuit
locks near zero because each day's gap sits at the bottom of the 5–12%
band). The existing `circuit_ep` flag on `ep_signature.py` anticipated this
pattern (comment: "locked day — delayed-list candidate") but nothing
consumed it.

D1–D5 decisions (DECISIONS_ADOPTED_20260904.md):
  D1  definition A (circuit-stalled repricing)
  D2  anchor = announcement-knowable session (catalyst features) +
      first-movement session (price-structure features)
  D3  separate detector identity, REVIEW_REQUIRED at birth (never rides
      episodic_pivot's VERIFIED trust)
  D4  delay bound k = 10 sessions (repricing must complete within k
      sessions; owner-delegated default, override by editing the constant)
  D5  GLM builds (taken over from Sol's event track)

Pure function over pre-computed inputs (the caller supplies the bars' lock
states and catalyst matching). No announcements store read inside the
detector — the caller wires that (same pattern as `actions` in scan).
"""
from __future__ import annotations

from typing import Optional, Sequence

from unidesk.contracts.base import ContractError, require_float
from unidesk.momentum.detectors.engine import Detection, Rule, evaluate_rules


def episodic_pivot_delayed(
    *,
    consecutive_locked_sessions: Optional[int],
    sessions_since_catalyst: Optional[int],
    catalyst_type: Optional[str],
    close_above_pre_announcement_close: Optional[bool],
    min_locked_sessions: int = 2,
    max_delay_sessions: int = 10,
) -> tuple[Detection, tuple]:
    """Delayed EP: catalyst-corroborated repricing completing over ≥
    ``min_locked_sessions`` consecutive locked/sessions, within
    ``max_delay_sessions`` of the announcement.

    Inputs (all caller-supplied, pre-computed):
      consecutive_locked_sessions — count of consecutive sessions where the
        stock closed at a band limit or froze (from E-3's circuit_locked)
      sessions_since_catalyst — trading sessions since the catalyst
        announcement was knowable (from E-2's announcements store)
      catalyst_type — the classified catalyst (results / order-win / etc.)
      close_above_pre_announcement_close — is the current close above the
        close before the announcement? (repricing is real, not a fade)

    DETECTION RULES (all must hold for a VALID verdict):
      1. catalyst_type is not None (absence is not evidence — R12)
      2. sessions_since_catalyst is in [1, max_delay_sessions]
      3. consecutive_locked_sessions >= min_locked_sessions
      4. close_above_pre_announcement_close is True

    Rule 3+4 together define the pattern: the stock locked AND repriced.
    Either alone is ambiguous (a lock without repricing may be illiquidity;
    a repricing without a lock may be ordinary momentum).
    """
    rules = [
        Rule(
            name="catalyst_present",
            available=catalyst_type is not None,
            passed=catalyst_type is not None,
            detail="catalyst must be known (E-2 announcements store)" if catalyst_type is None else "",
        ),
        Rule(
            name="within_delay_window",
            available=sessions_since_catalyst is not None,
            passed=(sessions_since_catalyst is not None
                    and 1 <= sessions_since_catalyst <= max_delay_sessions),
            detail=f"needs 1..{max_delay_sessions} sessions since catalyst" if sessions_since_catalyst is not None else "",
        ),
        Rule(
            name="consecutive_locked_sessions",
            available=consecutive_locked_sessions is not None,
            passed=(consecutive_locked_sessions is not None
                    and consecutive_locked_sessions >= min_locked_sessions),
            detail=f"needs ≥{min_locked_sessions} consecutive locked sessions" if consecutive_locked_sessions is not None else "",
        ),
        Rule(
            name="close_above_pre_announcement_close",
            available=close_above_pre_announcement_close is not None,
            passed=close_above_pre_announcement_close is True,
            detail="repricing must be real (close > pre-announcement close)" if close_above_pre_announcement_close is not None else "",
        ),
    ]
    return evaluate_rules(rules)
