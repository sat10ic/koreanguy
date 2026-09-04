"""leg_linearity + base_symmetry — the two shape reads added 2026-07-25.

User doctrine that day: what he screens on now is "Market Environment / Strong
Sector / Strong Institutional Leg & Shallow Pullback / Liquidity Rush /
Symmetry / Linearity", not the pattern names he used ten years ago. An audit
found the tool measured four of the six; these two had zero implementation.

Both are SHADOW metrics — persisted into discovery_bucket.metrics_json, never
consulted by an archetype or a gate. These tests pin the maths and the honest
None-returns, not any threshold, because no threshold has been earned yet.
"""
from __future__ import annotations

import math

from manas_os.scanner import discovery_metrics as dm


def _bar(i, close, high=None, low=None, vol=100_000):
    return {
        "trade_date": f"2026-01-{(i % 28) + 1:02d}",
        "open": close, "close": close,
        "high": high if high is not None else close * 1.01,
        "low": low if low is not None else close * 0.99,
        "volume": vol,
    }


# --------------------------------------------------------------------- linearity

def test_perfect_exponential_advance_scores_r2_one():
    """A constant % advance is a straight line in LOG space, which is exactly
    why the fit is on log(close): a raw-price fit would penalise a clean
    compounder for curving."""
    bars = [_bar(i, 100.0 * (1.02 ** i)) for i in range(40)]
    out = dm.leg_linearity(bars)
    assert out["r2"] is not None
    assert out["r2"] > 0.999
    assert math.isclose(out["slope_pct_per_bar"], 2.0, abs_tol=0.05)


def test_choppy_advance_scores_lower_than_smooth_advance():
    """Same start, same end, same total return — different path. This is the
    whole point of the metric: the tool previously could not tell them apart."""
    smooth = [_bar(i, 100.0 * (1.02 ** i)) for i in range(40)]
    # zig-zag around the identical trend line
    choppy = [_bar(i, 100.0 * (1.02 ** i) * (1.12 if i % 2 else 0.88)) for i in range(40)]
    assert dm.leg_linearity(smooth)["r2"] > dm.leg_linearity(choppy)["r2"]


def test_leg_anchors_at_the_low_not_the_window_start():
    """A V-shape must not be scored as non-linear because of the decline that
    preceded the leg — the fit starts at the leg's own low."""
    down = [_bar(i, 200.0 - i * 5.0) for i in range(20)]                # 200 -> 105, low at idx 19
    up = [_bar(20 + i, 105.0 * (1.02 ** (i + 1))) for i in range(30)]   # clean advance from 107.1
    out = dm.leg_linearity(down + up)
    assert out["r2"] > 0.99
    # 31, not 30: the leg INCLUDES its anchor bar (the low itself) plus the 30
    # advancing bars. Measuring from the low exclusive would drop the very bar
    # the move started from.
    assert out["bars"] == 31
    assert out["anchor_date"] == down[19]["trade_date"]


def test_linearity_returns_nones_when_history_is_thin():
    out = dm.leg_linearity([_bar(i, 100.0) for i in range(5)])
    assert out["r2"] is None and out["bars"] == 0


def test_linearity_survives_none_and_zero_closes():
    bars = [_bar(i, 100.0 + i) for i in range(30)]
    bars[3]["close"] = None
    bars[7]["close"] = 0
    out = dm.leg_linearity(bars)
    assert out["r2"] is not None  # bad bars skipped, not fatal


# --------------------------------------------------------------------- symmetry

def test_identical_halves_score_perfect_price_symmetry():
    bars = [_bar(i, 100.0, high=102.0, low=98.0) for i in range(20)]
    out = dm.base_symmetry(bars)
    assert math.isclose(out["price_symmetry"], 1.0, abs_tol=1e-6)
    assert math.isclose(out["volume_symmetry"], 1.0, abs_tol=1e-6)


def test_one_violent_half_scores_low_price_symmetry():
    """A base that is one big event plus a drift is NOT the same as an even
    two-sided contraction, even when the overall range matches."""
    wide = [_bar(i, 100.0, high=120.0, low=80.0) for i in range(10)]
    tight = [_bar(10 + i, 100.0, high=101.0, low=99.0) for i in range(10)]
    out = dm.base_symmetry(wide + tight)
    assert out["price_symmetry"] < 0.5
    assert out["first_half_range_pct"] > out["second_half_range_pct"]


def test_volume_symmetry_is_independent_of_price_symmetry():
    """A base can look symmetric in price while all participation sits on one
    side — that is a different failure and gets its own number."""
    a = [_bar(i, 100.0, high=102.0, low=98.0, vol=1_000_000) for i in range(10)]
    b = [_bar(10 + i, 100.0, high=102.0, low=98.0, vol=50_000) for i in range(10)]
    out = dm.base_symmetry(a + b)
    assert math.isclose(out["price_symmetry"], 1.0, abs_tol=1e-6)
    assert out["volume_symmetry"] < 0.5


def test_symmetry_returns_nones_when_window_too_short():
    out = dm.base_symmetry([_bar(i, 100.0) for i in range(4)])
    assert out["price_symmetry"] is None and out["bars"] == 0


def test_both_metrics_are_shadow_only():
    """Guard the decision this shipped under: neither name may appear in the
    gate/archetype path. If a future wave wants to rank on them, that is a
    deliberate change and this test should fail loudly first."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    for rel in ("scanner/gates.py", "risk/plan.py", "regime/governor.py"):
        src = (root / rel).read_text(encoding="utf-8", errors="replace")
        assert "leg_linearity" not in src, f"{rel} must not gate on linearity yet"
        assert "base_symmetry" not in src, f"{rel} must not gate on symmetry yet"
