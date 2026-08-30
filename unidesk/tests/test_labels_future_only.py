"""Directive 1(b): every label computed in research/labels.py reads only
sessions strictly after the decision index.

``labels.py``'s functions (``long_outcome``, ``breakout_hold``) take
already-sliced future arrays and have no decision-index of their own -- the
caller (``research/candidates.py:attach_outcomes``) owns the point-in-time
slicing via ``future_after``. This file exercises the guard in both
directions: the companion assertion ``labels.assert_future_only`` fails
closed on a planted decision-bar-or-earlier leak (same pattern as
``research/leakage_suite.py``'s ``planted_gold_includes_future``), and the
real production call site (``attach_outcomes``) never manages to feed a
non-future session into a label even when the caller's future map is
poisoned with the decision-day bar itself.
"""
from datetime import date, datetime, timezone

import pytest

from unidesk.contracts.base import ContractError
from unidesk.contracts.research import ResearchEvent
from unidesk.research.candidates import attach_outcomes
from unidesk.research.labels import assert_future_only

UTC = timezone.utc


def test_assert_future_only_accepts_strictly_future_sessions():
    decision = date(2026, 1, 10)
    sessions = [date(2026, 1, 11), date(2026, 1, 12), date(2026, 1, 13)]
    assert_future_only(sessions, decision)  # must not raise


def test_assert_future_only_rejects_the_decision_session_itself():
    decision = date(2026, 1, 10)
    sessions = [date(2026, 1, 10), date(2026, 1, 11)]  # planted leak: includes decision bar
    with pytest.raises(ContractError, match="future-only violation"):
        assert_future_only(sessions, decision)


def test_assert_future_only_rejects_a_session_before_decision():
    decision = date(2026, 1, 10)
    sessions = [date(2026, 1, 9), date(2026, 1, 11)]  # planted leak: a past bar
    with pytest.raises(ContractError, match="future-only violation"):
        assert_future_only(sessions, decision)


def test_assert_future_only_empty_is_a_noop():
    assert_future_only([], date(2026, 1, 10)) is None


def _event(symbol: str, decision: date, *, close: float = 100.0, atr_pct: float = 2.0) -> ResearchEvent:
    ts = datetime(decision.year, decision.month, decision.day, 18, 0, tzinfo=UTC)
    return ResearchEvent(
        event_id=f"{symbol}:{decision.isoformat()}",
        candidate_id=f"{symbol}:{decision.isoformat()}",
        symbol=symbol,
        timestamp=ts,
        snapshot={
            "close": close, "atr_pct": atr_pct,
            "detectors": {"momentum_burst": {"detection": "VALID", "failures": []}},
        },
        config_hash="abcd",
        research_schema_version="research-event-v1",
        outcome_labels={},
    )


def test_attach_outcomes_never_uses_the_decision_bar_even_when_the_future_map_includes_it():
    """Poison the future map with the decision-day bar carrying a
    catastrophic, distinguishable value (a -90% low) that would corrupt MAE/
    stop-hit/R-multiple if it leaked in. attach_outcomes (via future_after +
    assert_future_only) must not let it through -- the resolved outcome must
    be computed purely from the two genuinely-future bars."""
    decision = date(2026, 1, 10)
    event = _event("X", decision)
    future = {
        "X": {
            "sessions": [date(2026, 1, 10), date(2026, 1, 11), date(2026, 1, 12)],
            "opens":  [100.0, 101.0, 102.0],
            "highs":  [101.0, 110.0, 112.0],
            "lows":   [1.0, 100.0, 101.0],     # decision-bar low is a planted catastrophic value
            "closes": [1.0, 109.0, 111.0],     # decision-bar close is a planted catastrophic value
        }
    }
    labeled = attach_outcomes([event], future, horizon=2)
    out = labeled[0].outcome_labels
    assert out["status"] == "RESOLVED"
    # entry is the NEXT bar's open (Jan 11), never the decision bar's own open.
    assert out["entry"] == pytest.approx(101.0)
    # mae_pct computed only from lows=[100.0, 101.0] relative to entry=101.0:
    # min((100/101 - 1)*100, (101/101 - 1)*100) = (100/101 - 1) * 100
    assert out["mae_pct"] == pytest.approx((100.0 / 101.0 - 1.0) * 100.0, abs=1e-3)
    # The catastrophic planted low of 1.0 would have produced an mae_pct
    # near -99% if it had leaked in -- it did not.
    assert out["mae_pct"] > -50.0


def test_attach_outcomes_raises_if_future_after_is_bypassed():
    """Defense-in-depth: even if a future call site stops using future_after
    and hands attach_outcomes' internals a session list that still contains
    the decision bar, assert_future_only is the second gate that fails
    closed. Simulated directly against the guard (attach_outcomes itself is
    already safe via future_after; this proves the second gate independently
    reacts to the same kind of leak the first one is meant to catch)."""
    decision = date(2026, 1, 10)
    leaked_sessions = [date(2026, 1, 10), date(2026, 1, 11)]
    with pytest.raises(ContractError):
        assert_future_only(leaked_sessions, decision)
