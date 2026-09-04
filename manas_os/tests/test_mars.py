"""Tests for the pure MARS math (regime/sectors.py).

No I/O — compute_mars + classify_state + sma. Covers all 6 states with
synthetic bar lists, the SMA50 boundary, and benchmark-math correctness.
"""
from manas_os.providers.base import DailyBar
from manas_os.regime import sectors


def _bars(closes, start="2026-01-01"):
    """Build a DailyBar list from a close-price sequence (oldest first)."""
    from datetime import date, timedelta
    d0 = date.fromisoformat(start)
    return [DailyBar((d0 + timedelta(days=i)).isoformat(), 0, 0, 0, c, 0)
            for i, c in enumerate(closes)]


def _flat_then(n_flat, flat, last):
    """n_flat bars at `flat`, then one bar at `last` (so SMA50 = flat)."""
    return _bars([flat] * n_flat + [last])


def test_sma():
    assert sectors.sma([1, 2, 3, 4, 5], 3) == 4.0  # mean of last 3
    assert sectors.sma([1, 2], 3) is None          # too short


def test_compute_mars_too_short_returns_none():
    short = _bars([100] * 30 + [110])
    long_ = _bars([100] * 60 + [104])
    assert sectors.compute_mars(short, long_) == (None, None)
    assert sectors.compute_mars(long_, short) == (None, None)


def test_compute_mars_gross_outperformance():
    # Sector 10% above its flat MA, index flat at its MA → MARS = +10, both above → GROSS_OUT
    sector = _flat_then(50, 100.0, 110.0)
    index = _flat_then(50, 100.0, 100.0)  # exactly at MA → just above (close > ma false? =)
    val, state = sectors.compute_mars(sector, index)
    assert val is not None and val > 0
    # index close (100) > sma50 (100) is False (equal) → index_above_ma False.
    # sector above, index at → falls through to ABSOLUTE_OUT (aop rule).
    # Use a strictly-above index to hit GROSS_OUT cleanly:
    index2 = _flat_then(50, 100.0, 101.0)
    val2, state2 = sectors.compute_mars(sector, index2)
    assert val2 is not None and val2 > 0
    assert state2 == "GROSS_OUT"


def test_compute_mars_absolute_outperformance():
    # Sector above its MA, index BELOW its MA → ABSOLUTE_OUT (the rare-gold case)
    sector = _flat_then(50, 100.0, 110.0)
    index = _flat_then(50, 100.0, 95.0)
    val, state = sectors.compute_mars(sector, index)
    assert val is not None and val > 0  # sector +10%, index −5% → +15
    assert state == "ABSOLUTE_OUT"


def test_compute_mars_absolute_underperformance():
    # Sector below MA, index above → ABSOLUTE_UNDER
    sector = _flat_then(50, 100.0, 90.0)
    index = _flat_then(50, 100.0, 105.0)
    val, state = sectors.compute_mars(sector, index)
    assert val is not None and val < 0
    assert state == "ABSOLUTE_UNDER"


def test_compute_mars_gross_underperformance():
    # Both below MA, sector MORE below → GROSS_UNDER
    sector = _flat_then(50, 100.0, 88.0)   # −12%
    index = _flat_then(50, 100.0, 95.0)    # −5%
    val, state = sectors.compute_mars(sector, index)
    assert val is not None and val < 0     # −7
    assert state == "GROSS_UNDER"


def test_compute_mars_relative_outperformance():
    # Both below MA, sector LESS bearish → RELATIVE_OUT
    sector = _flat_then(50, 100.0, 97.0)   # −3%
    index = _flat_then(50, 100.0, 90.0)    # −10%
    val, state = sectors.compute_mars(sector, index)
    assert val is not None and val > 0     # +7
    assert state == "RELATIVE_OUT"


def test_compute_mars_relative_underperformance():
    # Both above MA, sector LESS bullish → RELATIVE_UNDER
    sector = _flat_then(50, 100.0, 103.0)  # +3%
    index = _flat_then(50, 100.0, 110.0)   # +10%
    val, state = sectors.compute_mars(sector, index)
    assert val is not None and val < 0     # −7
    assert state == "RELATIVE_UNDER"


def test_classify_state_all_six():
    # Exercise the 6-rule table directly with hand-picked booleans.
    assert sectors.classify_state(1, False, False) == "RELATIVE_OUT"
    assert sectors.classify_state(1, True, True) == "GROSS_OUT"
    assert sectors.classify_state(1, True, False) == "ABSOLUTE_OUT"
    assert sectors.classify_state(-1, True, True) == "RELATIVE_UNDER"
    assert sectors.classify_state(-1, False, False) == "GROSS_UNDER"
    assert sectors.classify_state(-1, False, True) == "ABSOLUTE_UNDER"


def test_compute_mars_benchmark_math():
    # White-box: MARS = sectorPct − indexPct, both measured against SMA50.
    # _flat_then(50, 100, X) makes 51 bars: 50 @100 + 1 @X. The last 50 closes
    # are 49@100 + 1@X, so sma50 = (49*100 + X)/50.
    # sector X=110 → sma50 = 100.2, sectorPct = 9.780%
    # index  X=104 → sma50 = 100.08, indexPct = 3.917%
    # MARS ≈ 5.864
    sector = _flat_then(50, 100.0, 110.0)
    index = _flat_then(50, 100.0, 104.0)
    val, _ = sectors.compute_mars(sector, index)
    assert val is not None
    assert abs(val - 5.86) < 0.05


def test_sector_indices_nonempty_and_benchmark_set():
    assert len(sectors.SECTOR_INDICES) >= 10
    assert sectors.BENCHMARK.startswith("NIFTY")
    assert all(isinstance(s, str) and s.startswith("NIFTY") for s in sectors.SECTOR_INDICES)
