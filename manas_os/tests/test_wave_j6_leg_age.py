"""Tests for WAVE_J J6: real leg-age wired into gate_fresh_leg as a SHADOW
evidence field (enforce_staleness=False) with zero behavior change.
"""
from __future__ import annotations

from manas_os.scanner import candidates, gates


def _bar(i, close, high=None, low=None):
    return {
        "date": f"2026-01-{i + 1:02d}",
        "open": close,
        "high": high if high is not None else close * 1.01,
        "low": low if low is not None else close * 0.99,
        "close": close,
        "volume": 1_000_000,
    }


def _uptrend(n, start=100.0, step=0.3):
    return [_bar(i, start + i * step) for i in range(n)]


# --- candidates._compute_breakout_age --------------------------------------------

def test_compute_breakout_age_finds_recent_crossover():
    bars = _uptrend(20, start=90.0, step=1.0)  # closes: 90, 91, ..., 109
    pivot = 100.0  # crossed between bar index 9 (99) and 10 (100)? close>pivot strictly
    age = candidates._compute_breakout_age(bars, pivot)
    # close[10]=100 not >100; close[11]=101>100, prior close[10]=100<=100 -> crossover at idx 11
    assert age == (len(bars) - 1) - 11


def test_compute_breakout_age_none_when_no_pivot():
    bars = _uptrend(10)
    assert candidates._compute_breakout_age(bars, None) is None


def test_compute_breakout_age_none_when_never_crossed():
    bars = _uptrend(10, start=50.0, step=0.1)  # closes stay well below pivot
    assert candidates._compute_breakout_age(bars, 1000.0) is None


def test_compute_breakout_age_none_thin_bars():
    assert candidates._compute_breakout_age([_bar(0, 100.0)], 90.0) is None


# --- gate_fresh_leg shadow behavior -----------------------------------------------

def test_gate_fresh_leg_shadow_records_would_refuse_without_refusing():
    bars = _uptrend(60, step=0.05)
    stale_age = gates.PULLBACK_AGE_MAX + 5
    r = gates.gate_fresh_leg(bars, pivot=bars[-1]["close"] * 0.99, breakout_age=stale_age,
                              enforce_staleness=False)
    assert r["pass"] is True  # zero behavior change
    assert r["evidence"]["would_refuse_stale"] is True
    assert r["evidence"]["leg_age"] == stale_age


def test_gate_fresh_leg_enforce_staleness_true_actually_refuses():
    bars = _uptrend(60, step=0.05)
    stale_age = gates.PULLBACK_AGE_MAX + 5
    r = gates.gate_fresh_leg(bars, pivot=bars[-1]["close"] * 0.99, breakout_age=stale_age,
                              enforce_staleness=True)
    assert r["pass"] is False
    assert "bars old" in r["reason"]


def test_gate_fresh_leg_non_stale_age_would_refuse_stale_false():
    bars = _uptrend(60, step=0.05)
    r = gates.gate_fresh_leg(bars, pivot=bars[-1]["close"] * 0.99, breakout_age=3,
                              enforce_staleness=False)
    assert r["pass"] is True
    assert r["evidence"]["would_refuse_stale"] is False
    assert r["evidence"]["leg_age"] == 3


def test_gate_fresh_leg_default_enforce_staleness_is_false():
    bars = _uptrend(60, step=0.05)
    stale_age = gates.PULLBACK_AGE_MAX + 5
    r = gates.gate_fresh_leg(bars, pivot=bars[-1]["close"] * 0.99, breakout_age=stale_age)
    assert r["pass"] is True


# --- cascade wiring: same fixture passes identically before/after ----------------

def test_run_cascade_same_fixture_passes_identically_with_real_age():
    """Simulates the pre-J6 (breakout_age=None) vs post-J6 (real age,
    enforce_staleness=False) cascade call for the fresh-leg gate only —
    identical pass/fail, evidence now carries leg_age."""
    bars = _uptrend(60, step=0.05)
    pivot = bars[-1]["close"] * 0.99

    before = gates.gate_fresh_leg(bars, pivot=pivot, breakout_age=None)
    after = gates.gate_fresh_leg(bars, pivot=pivot, breakout_age=gates.PULLBACK_AGE_MAX + 10,
                                  enforce_staleness=False)

    assert before["pass"] == after["pass"] is True
    assert "leg_age" not in before["evidence"] or before["evidence"]["leg_age"] is None
    assert after["evidence"]["leg_age"] == gates.PULLBACK_AGE_MAX + 10
    assert after["evidence"]["would_refuse_stale"] is True
