"""W4 — traderlog/adopted/xp.py and traderlog/adopted/mbi.py.

Covers:
  * XP recursion determinism (recompute a known date twice -> identical value).
  * The gap-break decision: a breadth_daily gap beyond the threshold reseeds
    from config rather than silently carrying a stale prior value forward.
  * MBI banding thresholds exactly as adopted: r50 uses 85/60, r10/r20 use
    75/50, r4p5 uses 50/200/400.
"""
from __future__ import annotations

import math

from traderlog.adopted import mbi
from traderlog.adopted.xp import compute_xp, xp_for_date
from traderlog.db import init_db, now_iso


def _insert_breadth(conn, trade_date, *, up4=5.0, down4=2.0, p10=60.0, p20=55.0, p50=50.0):
    conn.execute(
        "INSERT INTO breadth_daily (trade_date, up_4pct, down_4pct, pct_above_10dma, "
        "pct_above_20dma, pct_above_50dma, ingested_at) VALUES (?,?,?,?,?,?,?)",
        (trade_date, up4, down4, p10, p20, p50, now_iso()),
    )


# ---------------------------------------------------------------------------
# compute_xp — pure math, unchanged from manas_os
# ---------------------------------------------------------------------------

def test_compute_xp_is_pure_and_deterministic():
    a = compute_xp(5.0, 2.0, 60.0, 55.0, 15.0, 20.0)
    b = compute_xp(5.0, 2.0, 60.0, 55.0, 15.0, 20.0)
    assert a == b


def test_compute_xp_zero_decliners_does_not_blow_up_or_raise():
    # today_down4=0 would be log(0) without the _EPS domain guard.
    xp, z = compute_xp(10.0, 0.0, 60.0, 55.0, 15.0, 20.0)
    assert math.isfinite(xp)
    assert math.isfinite(z)


# ---------------------------------------------------------------------------
# xp_for_date — recursion determinism + gap handling
# ---------------------------------------------------------------------------

def test_xp_for_date_recompute_same_date_twice_is_identical(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    _insert_breadth(conn, "2025-01-01")
    _insert_breadth(conn, "2025-01-02")
    conn.commit()

    # First date reseeds (no prior); persist it like the orchestrator would.
    xp1, z1, reseeded1 = xp_for_date(conn, "2025-01-01")
    assert reseeded1 is True
    conn.execute(
        "INSERT INTO regime_daily (trade_date, xp_value, xp_z_state, ingested_at) VALUES (?,?,?,?)",
        ("2025-01-01", xp1, z1, now_iso()),
    )
    conn.commit()

    a = xp_for_date(conn, "2025-01-02")
    b = xp_for_date(conn, "2025-01-02")
    assert a == b
    assert a[2] is False  # continues the chain, 1-day gap


def test_xp_for_date_first_ever_date_reseeds_from_config(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    _insert_breadth(conn, "2025-01-01")
    conn.commit()
    xp, z, reseeded = xp_for_date(conn, "2025-01-01", seeds={"xp_seed": 15.0, "xp_z_seed": 20.0})
    assert reseeded is True
    expected_xp, expected_z = compute_xp(5.0, 2.0, 60.0, 55.0, 15.0, 20.0)
    assert xp == expected_xp
    assert z == expected_z


def test_xp_for_date_gap_beyond_threshold_reseeds_not_carries_forward(tmp_path):
    """The load-bearing gap test: a >5-day hole must NOT silently continue
    the recursion off a stale prior value."""
    conn = init_db(tmp_path / "traderlog.db")
    _insert_breadth(conn, "2025-01-01")
    _insert_breadth(conn, "2025-03-15")  # 73 days later — a real chain break
    conn.commit()

    xp1, z1, reseeded1 = xp_for_date(conn, "2025-01-01")
    assert reseeded1 is True
    conn.execute(
        "INSERT INTO regime_daily (trade_date, xp_value, xp_z_state, ingested_at) VALUES (?,?,?,?)",
        ("2025-01-01", xp1, z1, now_iso()),
    )
    conn.commit()

    xp2, z2, reseeded2 = xp_for_date(conn, "2025-03-15")
    assert reseeded2 is True  # MUST reseed, not continue off the 73-day-old value
    # Confirm it actually used the seed, not xp1/z1: recompute independently.
    expected_xp, expected_z = compute_xp(5.0, 2.0, 60.0, 55.0, 15.0, 20.0)
    assert xp2 == expected_xp
    assert z2 == expected_z
    # What WOULD have come out if the bug this test guards against were
    # present (continuing the recursion off the 73-day-old xp1/z1 instead of
    # reseeding) -- must NOT match what xp_for_date actually returned.
    would_have_continued_xp, would_have_continued_z = compute_xp(5.0, 2.0, 60.0, 55.0, xp1, z1)
    assert (xp2, z2) != (would_have_continued_xp, would_have_continued_z)


def test_xp_for_date_gap_within_threshold_continues_chain(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    _insert_breadth(conn, "2025-01-01")
    _insert_breadth(conn, "2025-01-05")  # 4-day gap: a long weekend, not a break
    conn.commit()

    xp1, z1, _ = xp_for_date(conn, "2025-01-01")
    conn.execute(
        "INSERT INTO regime_daily (trade_date, xp_value, xp_z_state, ingested_at) VALUES (?,?,?,?)",
        ("2025-01-01", xp1, z1, now_iso()),
    )
    conn.commit()

    xp2, z2, reseeded2 = xp_for_date(conn, "2025-01-05")
    assert reseeded2 is False
    expected_xp, expected_z = compute_xp(5.0, 2.0, 60.0, 55.0, xp1, z1)
    assert xp2 == expected_xp
    assert z2 == expected_z


def test_xp_for_date_raises_when_breadth_daily_row_missing(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    try:
        xp_for_date(conn, "2025-01-01")
    except ValueError as exc:
        assert "no breadth_daily row" in str(exc)
    else:
        raise AssertionError("expected ValueError")


# ---------------------------------------------------------------------------
# MBI banding — exact adopted thresholds
# ---------------------------------------------------------------------------

def test_band_ratio_uses_75_50_thresholds():
    assert mbi.band_ratio(75.0) == "GREEN"
    assert mbi.band_ratio(74.9) == "WHITE"
    assert mbi.band_ratio(50.0) == "WHITE"
    assert mbi.band_ratio(49.9) == "RED"
    assert mbi.band_ratio(None) is None


def test_band_r50_uses_85_60_thresholds():
    assert mbi.band_r50(85.0) == "GREEN"
    assert mbi.band_r50(84.9) == "WHITE"
    assert mbi.band_r50(60.0) == "WHITE"
    assert mbi.band_r50(59.9) == "RED"


def test_band_r4p5_uses_50_200_400_thresholds():
    assert mbi.band_r4p5(49.9) == "RED"
    assert mbi.band_r4p5(50.0) == "WHITE"
    assert mbi.band_r4p5(199.9) == "WHITE"
    assert mbi.band_r4p5(200.0) == "GREEN"
    assert mbi.band_r4p5(399.9) == "GREEN"
    assert mbi.band_r4p5(400.0) == "ORANGE"


def test_ratio_from_pct_above_and_burst_ratio():
    assert mbi.ratio_from_pct_above(75.0) == 300.0  # 75/25*100
    assert mbi.ratio_from_pct_above(-1) is None
    assert mbi.ratio_from_pct_above(101) is None
    assert mbi.burst_ratio(10, 5) == 200.0
    assert mbi.burst_ratio(10, 0) is None
    assert mbi.burst_ratio(10, None) is None


def test_xp_band_thresholds():
    assert mbi.xp_band(14.9) == "LOW"
    assert mbi.xp_band(15.0) == "BUILDING"
    assert mbi.xp_band(39.9) == "BUILDING"
    assert mbi.xp_band(40.0) == "STRONG"
    assert mbi.xp_band(99.9) == "STRONG"
    assert mbi.xp_band(100.0) == "EXTREME"
    assert mbi.xp_band(None) is None


def test_compute_mbi_warning_day_needs_three_red_bands():
    # r10/r20/r50 all below their RED cutoffs; r4p5 also RED.
    row = {"pct_above_10dma": 10.0, "pct_above_20dma": 10.0, "pct_above_50dma": 10.0,
           "up_4pct": 1.0, "down_4pct": 10.0}
    result = mbi.compute_mbi(row)
    assert result["bands"] == {"r10": "RED", "r20": "RED", "r50": "RED", "r4p5": "RED"}
    assert result["warning_day"] is True
    assert result["mbi_day_color"] == "RED"


def test_compute_mbi_green_day():
    row = {"pct_above_10dma": 90.0, "pct_above_20dma": 90.0, "pct_above_50dma": 90.0,
           "up_4pct": 20.0, "down_4pct": 5.0}
    result = mbi.compute_mbi(row)
    assert result["mbi_day_color"] == "GREEN"
    assert result["warning_day"] is False


def test_compute_mbi_is_deterministic():
    row = {"pct_above_10dma": 55.0, "pct_above_20dma": 45.0, "pct_above_50dma": 70.0,
           "up_4pct": 8.0, "down_4pct": 6.0}
    assert mbi.compute_mbi(row) == mbi.compute_mbi(row)
