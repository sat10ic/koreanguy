"""N3 acceptance: adjust_series removes a confirmed split discontinuity."""
from datetime import date

import pytest

from unidesk.momentum.data.corp_actions import ConfirmedAction
from unidesk.momentum.data.splits import adjustment_kills_the_gap


def test_known_half_split_kills_the_raw_gap():
    # 2:1 split: 200 → 100 on 2026-01-04. Raw gap is 50%; adjusted gap ~0.
    sessions = [date(2026, 1, d) for d in (2, 3, 4, 5, 6)]
    closes = [200.0, 202.0, 101.0, 102.0, 103.0]
    action = ConfirmedAction("TRENT", date(2026, 1, 4), 0.5, "test-known-split")
    result = adjustment_kills_the_gap(closes, sessions, action)
    assert result["killed"] is True
    assert result["raw_gap"] == pytest.approx(0.5, abs=0.02)
    assert result["adjusted_gap"] < 0.03


def test_unadjusted_series_does_not_kill_the_gap():
    sessions = [date(2026, 1, d) for d in (2, 3, 4, 5)]
    closes = [200.0, 202.0, 101.0, 102.0]
    # Wrong factor: pretends it was not a split.
    action = ConfirmedAction("TRENT", date(2026, 1, 4), 1.0, "test-wrong-factor")
    result = adjustment_kills_the_gap(closes, sessions, action)
    assert result["killed"] is False
