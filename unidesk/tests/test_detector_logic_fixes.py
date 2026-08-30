"""Regression tests for the 2026-08-30 detector trading-logic fixes.

Each test targets one audit finding (Opus cross-model + trading-logic audit,
2026-08-30) and pins the corrected behavior:

1. base_breakout room rule was INVERTED (>= min_room_adr selected laggards,
   rejected genuine breakouts) — now <= max_room_adr.
2. pullback's anchor proximity had no direction (a stock 2.5% ABOVE EMA21
   satisfied a rule meant to require a decline) — now signed distance +
   minimum decline from the recent high.
3. reversal_reclaim compared PAST closes to TODAY'S EMA21 (collapsed into a
   continuation screen) — now each day's own EMA21.
4. momentum_burst's AVWAP anti-chase guard was structurally inert (input
   always None) — compute_setup_inputs now measures a swing-low-anchored
   AVWAP extension in ADR units.
"""
import pytest

from unidesk.momentum.detectors.inputs import compute_setup_inputs
from unidesk.momentum.detectors.registry import evaluate_detector
from unidesk.momentum.detectors.setups import base_breakout, pullback


def _series(closes, volumes=None, start=100.0):
    """Build OHLCV lists from closes: open=prev close, high/low straddle."""
    o, h, l = [], [], []
    prev = start
    for c in closes:
        o.append(prev)
        h.append(max(prev, c) * 1.005)
        l.append(min(prev, c) * 0.995)
        prev = c
    v = volumes or [1_000_000.0] * len(closes)
    return o, h, l, list(closes), v


def _uptrend(n=80, drift=1.0):
    closes = [100.0 * (1 + drift / 100.0) ** i for i in range(n)]
    return _series(closes)


# ------------------------------------------------------------- base_breakout


def test_base_breakout_accepts_genuine_near_pivot_breakout():
    # Near the pivot (0.5 ADR of overhead room), everything else passes.
    det, failures = base_breakout(
        breakout_rvol=2.0, base_depth_pct=15.0, contraction_ratio=0.6,
        rs_rank=85.0, close_cleared_pivot=True, blue_sky=False,
        overhead_room_adr=0.5,
    )
    assert det.value == "VALID"
    # blue_sky passes the room rule outright (no overhead supply above a new high).
    det2, _ = base_breakout(
        breakout_rvol=2.0, base_depth_pct=15.0, contraction_ratio=0.6,
        rs_rank=85.0, close_cleared_pivot=True, blue_sky=True,
        overhead_room_adr=None,
    )
    assert det2.value == "VALID"


def test_base_breakout_rejects_laggard_with_large_overhead_room():
    # The audit's exact defect: 8.46 ADR underwater passed as a "breakout"
    # under the inverted >= rule. It must now fail the room rule.
    det, failures = base_breakout(
        breakout_rvol=2.0, base_depth_pct=15.0, contraction_ratio=0.6,
        rs_rank=85.0, close_cleared_pivot=True, blue_sky=False,
        overhead_room_adr=8.46,
    )
    assert det.value == "INVALID"
    assert any("overhead_room_adr" in f for f in failures)


def test_base_breakout_via_registry_laggard_is_invalid():
    det, _ = evaluate_detector("base_breakout", {
        "breakout_rvol": 2.0, "base_breakout_depth_pct": 15.0,
        "base_breakout_contraction_ratio": 0.6, "rs_rank": 85.0,
        "close_cleared_pivot": True, "blue_sky": False, "overhead_room_adr": 8.46,
    })
    assert det.value == "INVALID"


# ------------------------------------------------------------------ pullback


def test_pullback_rejects_stock_extended_above_anchor_without_decline():
    # The audit's exact case: 2.5% ABOVE EMA21 satisfied the old abs rule.
    # With the new inputs present (stock extended above anchor, no decline),
    # the directional rules fail it.
    det, failures = pullback(
        proximity_to_anchor_pct=2.5, pullback_volume_ratio=0.7,
        rs_rank=80.0, adr_pct=4.0,
        pullback_signed_anchor_pct=+2.5,     # above the anchor
        pullback_from_high_pct=0.2,          # no real decline
    )
    assert det.value == "INVALID"
    assert any("pullback_signed_anchor_pct" in f for f in failures)
    assert any("pullback_from_high_pct" in f for f in failures)


def test_pullback_accepts_proper_pullback_to_anchor():
    det, failures = pullback(
        proximity_to_anchor_pct=1.2, pullback_volume_ratio=0.7,
        rs_rank=80.0, adr_pct=4.0,
        pullback_signed_anchor_pct=-1.2,     # dipped just below the anchor
        pullback_from_high_pct=2.5,          # real decline from the 10s high
    )
    assert det.value == "VALID"
    assert not [f for f in failures if not f.startswith("skipped:")]


def test_pullback_without_directional_inputs_keeps_replaying_stored_fixtures():
    # Old stored-input replays (gold fixtures) lack the new measurements:
    # the directional rules are optional-on-missing -> skipped notes, and the
    # detector verdict is unchanged (VALID here).
    det, failures = pullback(
        proximity_to_anchor_pct=1.2, pullback_volume_ratio=0.7,
        rs_rank=80.0, adr_pct=4.0,
    )
    assert det.value == "VALID"
    assert all(
        f.startswith("skipped:") and "pullback_" in f for f in failures
    ), failures


def test_pullback_inputs_are_signed_and_carry_decline():
    # Dipping series: last close below its own EMA21 -> signed distance is
    # negative and a real decline from the 10-session high is measured.
    closes = [100.0] * 30 + [101.0, 102.0, 103.0, 104.0, 105.0, 102.0, 100.5]
    o, h, l, c, v = _series(closes)
    inputs = compute_setup_inputs(opens=o, highs=h, lows=l, closes=c, volumes=v)
    assert inputs["pullback_signed_anchor_pct"] is not None
    assert inputs["pullback_signed_anchor_pct"] < 0
    assert inputs["proximity_to_anchor_pct"] == pytest.approx(
        abs(inputs["pullback_signed_anchor_pct"]), abs=1e-6
    )
    assert inputs["pullback_from_high_pct"] is not None
    assert inputs["pullback_from_high_pct"] > 0


# ---------------------------------------------------------- reversal_reclaim


def test_reversal_reclaim_input_no_longer_fires_on_a_plain_uptrend():
    # Old bug: past closes compared to TODAY'S EMA21 fired "reclaimed" every
    # session of an uptrend (each past close sits below today's higher EMA).
    # Fixed: each day's own EMA21 — in a clean uptrend nothing was ever
    # below its own EMA, so reclaimed must be False.
    o, h, l, c, v = _uptrend(80)
    inputs = compute_setup_inputs(opens=o, highs=h, lows=l, closes=c, volumes=v)
    assert inputs["reclaimed"] is False


def test_reversal_reclaim_input_fires_on_a_real_reclaim():
    # Flat, then a decline below the EMA, then a strong close back above it:
    # the prior sessions were genuinely below their own-day EMAs.
    closes = [100.0] * 40 + [98.0, 97.0, 96.0, 95.5, 95.0, 103.0]
    o, h, l, c, v = _series(closes)
    inputs = compute_setup_inputs(opens=o, highs=h, lows=l, closes=c, volumes=v)
    assert inputs["reclaimed"] is True


# ------------------------------------------------------------ AVWAP extension


def test_avwap_extension_is_measured_not_inert():
    # Swing low then a strong rally: the anchored VWAP extension must be a
    # real positive number in ADR units (the old code always shipped None,
    # so momentum_burst's anti-chase guard never fired).
    closes = [100.0] * 30 + [92.0, 90.0, 94.0, 99.0, 106.0, 115.0, 125.0, 134.0]
    o, h, l, c, v = _series(closes)
    inputs = compute_setup_inputs(opens=o, highs=h, lows=l, closes=c, volumes=v)
    assert inputs["avwap_extension_adr"] is not None
    assert inputs["avwap_extension_adr"] > 0


def test_avwap_extension_unresolved_below_minimum_history():
    closes = [100.0, 101.0, 102.0]
    o, h, l, c, v = _series(closes)
    inputs = compute_setup_inputs(opens=o, highs=h, lows=l, closes=c, volumes=v)
    assert inputs["avwap_extension_adr"] is None