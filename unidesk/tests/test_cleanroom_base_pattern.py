"""Clean-room base detector contracts.

These tests define a storage-neutral, no-look-ahead approximation of the
publicly observable BananaPatterns behavior. They intentionally do not claim
parity with its undisclosed base-window or RS-weighting policy.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from unidesk.momentum.detectors.base_pattern import (
    BaseRules,
    BaseVerdict,
    DailyBar,
    classify_base_verdict,
    detect_base_pattern,
    relative_strength_ranks,
)


def _bar(i: int, close: float, high: float, low: float, volume: float) -> DailyBar:
    day = date(2026, 1, 1) + timedelta(days=i)
    return DailyBar(day=day, open=close, high=high, low=low, close=close, volume=volume)


def _forming_base(*, add_breakout: bool = False) -> list[DailyBar]:
    """A prior swing high, followed by a 20-session 10%-deep contracting base."""
    bars = [_bar(i, 80 + i, 81 + i, 79 + i, 1_000) for i in range(7)]
    bars.append(_bar(7, 100, 110, 99, 1_000))  # structural high; base starts next session
    # First half: 10-point daily ranges and heavier volume.
    bars.extend(_bar(i, 95, 96, 90, 1_000) for i in range(8, 18))
    # Second half: 4-point ranges and half the volume. Day 18 is a squat.
    bars.extend(_bar(i, 96, 101 if i == 18 else 96, 94, 500) for i in range(18, 28))
    if add_breakout:
        bars.append(_bar(28, 101, 103, 96, 2_000))
    return bars


def test_detects_confirmed_base_and_publicly_defined_measurements():
    pattern = detect_base_pattern(_forming_base(), rules=BaseRules(swing_left_right=2))

    assert pattern.verdict is BaseVerdict.WATCH
    assert pattern.base_start == date(2026, 1, 9)  # one session after the confirmed swing high
    assert pattern.base_sessions == 20
    assert pattern.base_weeks == pytest.approx(4.0)
    assert pattern.pivot == pytest.approx(96.0)
    assert pattern.depth_pct == pytest.approx((96 - 90) / 96 * 100)
    assert pattern.coil_ratio < 0.6
    assert pattern.dry_ratio == pytest.approx(0.5)
    assert pattern.dry_depth_ratio == pytest.approx(2 / 3)
    assert pattern.squat_dates == (date(2026, 1, 19),)
    assert pattern.breakout_date is None


def test_breakout_uses_the_prior_base_pivot_not_the_breakout_close():
    pattern = detect_base_pattern(
        _forming_base(add_breakout=True),
        rules=BaseRules(swing_left_right=2, fresh_breakout_sessions=3),
    )

    assert pattern.verdict is BaseVerdict.BREAKOUT
    assert pattern.pivot == pytest.approx(96.0)
    assert pattern.breakout_date == date(2026, 1, 29)
    assert pattern.base_sessions == 20  # the breakout bar is not part of the base measurement


def test_forming_incumbent_is_not_replaced_by_a_nested_one_day_breakout():
    bars = _forming_base()
    # A later confirmed high starts a short nested base. Its final close clears
    # that nested pivot, but remains below the older incumbent's ceiling.
    bars.append(_bar(28, 95, 105, 94, 900))
    bars.extend(_bar(i, 93, 94, 90, 400) for i in range(29, 44))
    bars.append(_bar(44, 95, 96, 92, 1_500))

    pattern = detect_base_pattern(bars, rules=BaseRules(swing_left_right=2))

    assert pattern.verdict is BaseVerdict.WATCH
    assert pattern.breakout_date is None


def test_unconfirmed_or_short_history_refuses_to_invent_a_base():
    bars = [_bar(i, 100 + i, 101 + i, 99 + i, 1_000) for i in range(8)]
    pattern = detect_base_pattern(bars, rules=BaseRules(swing_left_right=3))

    assert pattern.verdict is BaseVerdict.INSUFFICIENT_DATA
    assert "no_confirmed_base" in pattern.notes


def test_lifecycle_is_explicit_and_parameterized():
    rules = BaseRules(ma_period=3, fresh_breakout_sessions=1, running_extension_pct=5.0)
    assert classify_base_verdict(
        closes=[95, 96], pivot=100, breakout_index=None, rules=rules
    ) is BaseVerdict.WATCH
    assert classify_base_verdict(
        closes=[95, 101], pivot=100, breakout_index=1, rules=rules
    ) is BaseVerdict.BREAKOUT
    assert classify_base_verdict(
        closes=[95, 101, 107], pivot=100, breakout_index=1, rules=rules
    ) is BaseVerdict.RUNNING
    assert classify_base_verdict(
        closes=[95, 101, 107, 90], pivot=100, breakout_index=1, rules=rules
    ) is BaseVerdict.EXITED


def test_rs_ranks_are_cross_sectional_and_use_the_full_1_to_99_scale():
    ranks = relative_strength_ranks(
        {
            "WEAK": [100, 90, 80, 70],
            "MID": [100, 100, 100, 100],
            "STRONG": [100, 110, 120, 130],
        },
        lookbacks=(3,),
        weights=(1.0,),
    )

    assert ranks["WEAK"] == 1
    assert ranks["MID"] == 50
    assert ranks["STRONG"] == 99
