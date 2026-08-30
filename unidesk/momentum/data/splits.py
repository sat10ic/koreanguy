"""Split-candidate scan and adjustment continuity (N3 / Phase 0 spec §12.1).

Detection proposes; it never auto-adjusts. A known-split *validation*
applies a CONFIRMED factor and checks that the adjusted close does not
carry the raw overnight gap — the acceptance the manual asked for
before any backtest.
"""
from __future__ import annotations

from datetime import date
from typing import Sequence

from unidesk.contracts.base import ContractError, require_float
from unidesk.momentum.data.corp_actions import (
    ConfirmedAction, SplitCandidate, adjust_series, detect_split_candidates_bars,
)
from unidesk.momentum.data.market_store import InMemoryMarketStore


def scan_store_for_splits(store: InMemoryMarketStore, **kwargs) -> list[SplitCandidate]:
    """Run the conservative detector on every symbol in the store."""
    by_symbol: dict[str, list] = {}
    for item in store._daily:
        by_symbol.setdefault(item.bar.symbol, []).append(item)
    found: list[SplitCandidate] = []
    for symbol, bars in by_symbol.items():
        bars.sort(key=lambda b: b.bar.session)
        found.extend(detect_split_candidates_bars(bars, **kwargs))
    return found


def unconfirmed_candidate_sessions(
    candidates: Sequence[SplitCandidate],
    confirmed: Sequence[ConfirmedAction],
) -> dict[str, set]:
    """The "194 unconfirmed open-gap candidates" backlog (directive-1e),
    shaped for ``research.candidates.attach_outcomes``'s adjustment guard:
    symbol -> the set of gap sessions the detector flagged that have NOT
    been confirmed (matched by (symbol, ex_date) against the confirmed
    table -- a confirmed action's ``ex_date`` is the same gap session the
    detector flags for a real split, per ``adjustment_kills_the_gap``'s
    convention above).

    A research event whose outcome window spans one of these sessions must
    never be attached a real outcome: without the true ratio, the
    "outcome" would be a fabricated ~-50%-type catastrophic value
    indistinguishable from a genuine loss (HANDOFF directive-1e). This
    function only GROUPS the backlog; it infers no ratios and adjusts
    nothing.
    """
    confirmed_keys = {(a.symbol, a.ex_date) for a in confirmed}
    out: dict[str, set] = {}
    for c in candidates:
        if (c.symbol, c.session) in confirmed_keys:
            continue
        out.setdefault(c.symbol, set()).add(c.session)
    return out


def adjustment_kills_the_gap(
    closes: Sequence[float],
    sessions: Sequence[date],
    action: ConfirmedAction,
) -> dict:
    """Compare the raw overnight CLOSE gap at ``ex_date`` with the adjusted gap.

    Detection uses open/prev_close (a split prints at the open). Confirmation
    uses close-to-close: an open-only gap that the close fills is not a
    confirmed split. Acceptance: the absolute adjusted return across the
    ex-date is smaller than 5% of the raw close gap. Raises if the ex-date
    is not in the session list or has no prior bar.
    """
    if len(closes) != len(sessions):
        raise ContractError("closes and sessions must have equal length")
    try:
        i = list(sessions).index(action.ex_date)
    except ValueError:
        raise ContractError(f"ex_date {action.ex_date} not in sessions")
    if i < 1:
        raise ContractError("ex_date has no prior bar")
    raw_prev = require_float(closes[i - 1], "closes[i-1]")
    raw_ex = require_float(closes[i], "closes[i]")
    if raw_prev <= 0:
        raise ContractError("prior close must be positive")
    raw_gap = abs(raw_ex / raw_prev - 1.0)
    adjusted = adjust_series(closes, sessions, action.symbol, [action])
    adj_prev = adjusted[i - 1]
    adj_ex = adjusted[i]
    if adj_prev <= 0:
        raise ContractError("adjusted prior close must be positive")
    adj_gap = abs(adj_ex / adj_prev - 1.0)
    killed = adj_gap <= raw_gap * 0.05
    return {
        "raw_gap": round(raw_gap, 6),
        "adjusted_gap": round(adj_gap, 6),
        "killed": killed,
        "ex_date": action.ex_date.isoformat(),
        "symbol": action.symbol,
        "factor": action.factor,
    }
