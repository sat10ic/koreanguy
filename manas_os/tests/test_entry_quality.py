"""Unit tests for scanner/entry_quality.py (WAVE_J J1).

Per-function, per-branch coverage (pass + each refusal reason). Where the
underlying manas_indicators computation is complex/stateful (rmv, mswing,
burst_power), we patch the wrapped indicator call directly — this is a
white-box test of entry_quality's OWN pass/fail/evidence logic at the module
boundary, not a re-test of manas_indicators (already covered by
test_manas_indicators.py). For leg_fresh and strong_start_quality, whose logic
is simple enough to drive with real bars, we hand-build bar fixtures.
"""
from __future__ import annotations

from unittest.mock import patch

from manas_os.scanner import entry_quality as eq


def _bar(o, h, l, c, v=1_000_000):
    return {"open": o, "high": h, "low": l, "close": c, "volume": v}


def _flat_bars(n, price=100.0, v=1_000_000):
    return [_bar(price, price + 1, price - 1, price, v) for _ in range(n)]


# --- rmv_eligible ------------------------------------------------------------

def test_rmv_eligible_pass_on_rank():
    with patch.object(eq.mi, "rmv", return_value=[{"rank": 1, "rmv": 40.0,
                                                     "tightness_setup": False, "vdu_setup": False}]):
        result = eq.rmv_eligible(_flat_bars(5))
    assert result["pass"] is True
    assert result["reason"] is None
    assert result["evidence"]["rank"] == 1


def test_rmv_eligible_pass_on_tight_rmv():
    with patch.object(eq.mi, "rmv", return_value=[{"rank": 3, "rmv": 10.0,
                                                     "tightness_setup": True, "vdu_setup": False}]):
        result = eq.rmv_eligible(_flat_bars(5))
    assert result["pass"] is True


def test_rmv_eligible_refuse_no_coil():
    with patch.object(eq.mi, "rmv", return_value=[{"rank": 4, "rmv": 45.0,
                                                     "tightness_setup": False, "vdu_setup": False}]):
        result = eq.rmv_eligible(_flat_bars(5))
    assert result["pass"] is False
    assert "no coil" in result["reason"]


def test_rmv_eligible_no_bars():
    result = eq.rmv_eligible([])
    assert result["pass"] is False
    assert "no bars" in result["reason"]


# --- leg_fresh -----------------------------------------------------------------

def test_leg_fresh_pass():
    bars = _flat_bars(30)
    with patch.object(eq.mi, "persistency", return_value=[{"count": 2}] * 30):
        result = eq.leg_fresh(bars)
    assert result["pass"] is True
    assert result["reason"] is None


def test_leg_fresh_refuse_stale_persistency():
    bars = _flat_bars(30)
    with patch.object(eq.mi, "persistency", return_value=[{"count": 9}] * 30):
        result = eq.leg_fresh(bars)
    assert result["pass"] is False
    assert "stale" in result["reason"]


def test_leg_fresh_refuse_4th_green_day():
    # 5 strictly rising closes -> streak of 4 -> hard refusal, regardless of persistency
    closes = [100, 101, 102, 103, 104]
    bars = [_bar(c - 0.5, c + 0.5, c - 1, c) for c in closes]
    with patch.object(eq.mi, "persistency", return_value=[{"count": 1}] * 5):
        result = eq.leg_fresh(bars)
    assert result["pass"] is False
    assert "green day" in result["reason"]
    assert result["evidence"]["green_streak"] >= eq.GREEN_STREAK_MAX


# --- strong_start_quality -------------------------------------------------------

def _ss_bars(gap_pct, close_pos, vol_state, strong_start=True):
    """Build a 2-bar window: prior close 100, trigger day with the given gap%,
    close-position-in-range, and volume state (patched via simple_volume)."""
    prev = _bar(99, 101, 98, 100)
    open_ = 100 * (1 + gap_pct / 100.0)
    low = open_ - 1.0
    high = open_ + 4.0
    close = low + close_pos * (high - low)
    trigger = _bar(open_, high, low, close)
    return [prev, trigger], vol_state, strong_start


def _patched_strong_start(gap_pct, close_pos, vol_state, strong_start=True, expanded=False):
    bars, vs, ss = _ss_bars(gap_pct, close_pos, vol_state, strong_start)
    with patch.object(eq.mi, "ss_rvol", return_value=[{}, {"strong_start": ss}]), \
         patch.object(eq.mi, "simple_volume", return_value=[{}, {"state": vs}]), \
         patch.object(eq, "_range_expansion", return_value=expanded):
        return eq.strong_start_quality(bars)


def test_strong_start_quality_pass():
    result = _patched_strong_start(gap_pct=2.0, close_pos=0.8, vol_state="bull_pp")
    assert result["pass"] is True
    assert result["reason"] is None


def test_strong_start_quality_refuse_not_strong_start():
    result = _patched_strong_start(gap_pct=2.0, close_pos=0.8, vol_state="bull_pp", strong_start=False)
    assert result["pass"] is False
    assert "not a Strong Start" in result["reason"]


def test_strong_start_quality_refuse_gap_too_wide():
    result = _patched_strong_start(gap_pct=7.0, close_pos=0.8, vol_state="bull_pp")
    assert result["pass"] is False
    assert "gap" in result["reason"]


def test_strong_start_quality_refuse_close_lower_half():
    result = _patched_strong_start(gap_pct=2.0, close_pos=0.2, vol_state="bull_pp")
    assert result["pass"] is False
    assert "close position" in result["reason"]


def test_strong_start_quality_refuse_weak_volume_no_expansion():
    result = _patched_strong_start(gap_pct=2.0, close_pos=0.8, vol_state="noise", expanded=False)
    assert result["pass"] is False
    assert "volume state" in result["reason"]


def test_strong_start_quality_pass_via_range_expansion():
    result = _patched_strong_start(gap_pct=2.0, close_pos=0.8, vol_state="noise", expanded=True)
    assert result["pass"] is True


def test_strong_start_quality_no_bars():
    with patch.object(eq.mi, "ss_rvol", return_value=[]), patch.object(eq.mi, "simple_volume", return_value=[]):
        result = eq.strong_start_quality([_bar(100, 101, 99, 100)])
    assert result["pass"] is False


# --- mswing_ok -------------------------------------------------------------------

def test_mswing_ok_pass_up():
    with patch.object(eq.mi, "mswing", return_value=[{"color": "up", "mswing": 5.0, "index_mswing": 2.0}]):
        result = eq.mswing_ok(_flat_bars(3), _flat_bars(3))
    assert result["pass"] is True


def test_mswing_ok_pass_neutral_positive():
    with patch.object(eq.mi, "mswing", return_value=[{"color": "neutral_positive", "mswing": 1.0, "index_mswing": 2.0}]):
        result = eq.mswing_ok(_flat_bars(3), _flat_bars(3))
    assert result["pass"] is True


def test_mswing_ok_refuse_down():
    with patch.object(eq.mi, "mswing", return_value=[{"color": "down", "mswing": -5.0, "index_mswing": -2.0}]):
        result = eq.mswing_ok(_flat_bars(3), _flat_bars(3))
    assert result["pass"] is False
    assert "down" in result["reason"]


def test_mswing_ok_refuse_neutral_negative():
    with patch.object(eq.mi, "mswing", return_value=[{"color": "neutral_negative", "mswing": -1.0, "index_mswing": 2.0}]):
        result = eq.mswing_ok(_flat_bars(3), _flat_bars(3))
    assert result["pass"] is False


def test_mswing_ok_no_bars():
    with patch.object(eq.mi, "mswing", return_value=[]):
        result = eq.mswing_ok([], [])
    assert result["pass"] is False


# --- burst_exhausted -------------------------------------------------------------

def test_burst_exhausted_pass():
    with patch.object(eq.mi, "burst_power", return_value={"count_19": 0, "rounded": 2, "power_value": 2.0}):
        result = eq.burst_exhausted(_flat_bars(5))
    assert result["pass"] is True


def test_burst_exhausted_refuse_count19():
    with patch.object(eq.mi, "burst_power", return_value={"count_19": 1, "rounded": 3, "power_value": 3.0}):
        result = eq.burst_exhausted(_flat_bars(5))
    assert result["pass"] is False
    assert "count_19" in result["reason"]


def test_burst_exhausted_refuse_rounded():
    with patch.object(eq.mi, "burst_power", return_value={"count_19": 0, "rounded": 9, "power_value": 9.0}):
        result = eq.burst_exhausted(_flat_bars(5))
    assert result["pass"] is False
    assert "rounded" in result["reason"]
