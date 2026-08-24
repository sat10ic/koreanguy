"""W4 — traderlog/adopted/xp.py and traderlog/adopted/mbi.py.

Covers:
  * XP recursion determinism (recompute a known date twice -> identical value).
  * The gap-break decision: a breadth_daily gap beyond the threshold reseeds
    rather than silently carrying a stale prior value forward.
  * Reseed-time z seeding (C8): the z-state seeds from the reseed session's
    own observed up_4pct (percent) — never the count-scale constant.
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


def test_xp_for_date_first_ever_date_reseeds_z_from_observed_up4pct(tmp_path):
    """C8 (design/AUDIT_LEDGER.md 2026-08-24): the first date of a series must
    NOT unwind the recursion from the count-scale constant z seed (20.0) — it
    seeds the z-state from this session's own observed up_4pct (percent
    scale). xp_prev still starts from the xp_seed config value (XP has no
    observable seed)."""
    conn = init_db(tmp_path / "traderlog.db")
    _insert_breadth(conn, "2025-01-01", up4=5.0, down4=2.0)
    conn.commit()
    # Explicit seeds are passed and must NOT win over the observed up_4pct.
    xp, z, reseeded = xp_for_date(
        conn, "2025-01-01", seeds={"xp_seed": 15.0, "xp_z_seed": 20.0},
    )
    assert reseeded is True
    # z_state = 0.162*5.0 + 0.838*5.0 = 5.0 — the session's own up_4pct.
    assert abs(z - 5.0) < 1e-9
    expected_xp, expected_z = compute_xp(5.0, 2.0, 60.0, 55.0, 15.0, 5.0)
    assert xp == expected_xp
    assert z == expected_z


def test_xp_for_date_reseed_refuses_null_up4pct_instead_of_fabricating(tmp_path):
    """C8 fallback contract: when a reseed point has NO observed up_4pct
    (NULL), the xp_z_seed config constant is the selected z seed, but feeding
    a missing advancer percent into compute_xp is REFUSED rather than
    fabricating a number — xp_for_date raises and backfill records the date
    as failed. (The real pipeline always writes >= 0.25, so this only fires
    on hand-inserted/legacy rows.)"""
    conn = init_db(tmp_path / "traderlog.db")
    _insert_breadth(conn, "2025-01-01", up4=None, down4=2.0)
    conn.commit()
    try:
        xp_for_date(conn, "2025-01-01", seeds={"xp_seed": 15.0, "xp_z_seed": 20.0})
    except (TypeError, ValueError):
        pass
    else:
        raise AssertionError("expected a failure, not a fabricated number")


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
    # Confirm it actually reseeded from observed data, not xp1/z1: the z-state
    # seeds from 2025-03-15's own up_4pct (5.0), xp_prev from the xp_seed
    # config value.
    expected_xp, expected_z = compute_xp(5.0, 2.0, 60.0, 55.0, 15.0, 5.0)
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


def test_xp_for_date_today_up4_down4_overrides_take_precedence(tmp_path):
    """The override params let a caller exercise the recursion mechanics in
    isolation (percent inputs — C6 retracted, design/AUDIT_LEDGER.md
    2026-08-24). When given, they override the raw breadth_daily percent
    columns AND are the z-seed source at a reseed point; when omitted, the
    raw percent columns are used and seed the z-state."""
    conn = init_db(tmp_path / "traderlog.db")
    _insert_breadth(conn, "2025-01-01", up4=1.0, down4=0.5, p10=60.0, p20=55.0)
    conn.commit()

    default_xp, default_z, _ = xp_for_date(conn, "2025-01-01")
    override_xp, override_z, _ = xp_for_date(
        conn, "2025-01-01", today_up4=4.0, today_down4=2.0,
    )
    # Override path: today's values 4.0/2.0, z seeded from the effective
    # observed up_4pct = 4.0.
    expected_xp, expected_z = compute_xp(4.0, 2.0, 60.0, 55.0, 15.0, 4.0)
    assert override_xp == expected_xp
    assert override_z == expected_z
    # Default path: raw percent columns 1.0/0.5, z seeded from row up_4pct = 1.0.
    expected_default_xp, expected_default_z = compute_xp(1.0, 0.5, 60.0, 55.0, 15.0, 1.0)
    assert default_xp == expected_default_xp
    assert default_z == expected_default_z
    assert override_xp != default_xp
    assert override_z != default_z


def test_xp_for_date_explicit_prior_wins_over_db_row_and_seeds(tmp_path):
    """Warm-up threading contract (C8 second half): an explicit ``prior``
    (xp_prev, z_prev) must take precedence over the DB prior lookup AND over
    config seeds, and is never a reseed."""
    conn = init_db(tmp_path / "traderlog.db")
    _insert_breadth(conn, "2025-01-01", up4=5.0, down4=2.0)
    _insert_breadth(conn, "2025-01-02", up4=6.0, down4=1.0, p10=62.0, p20=58.0)
    conn.commit()
    # Persist day 1 so the DB genuinely HAS a prior row to override.
    xp1, z1, _ = xp_for_date(conn, "2025-01-01")
    conn.execute(
        "INSERT INTO regime_daily (trade_date, xp_value, xp_z_state, ingested_at) VALUES (?,?,?,?)",
        ("2025-01-01", xp1, z1, now_iso()),
    )
    conn.commit()

    xp, z, reseeded = xp_for_date(
        conn, "2025-01-02",
        seeds={"xp_seed": 99.0, "xp_z_seed": 99.0},
        prior=(7.0, 3.0),
    )
    expected_xp, expected_z = compute_xp(6.0, 1.0, 62.0, 58.0, 7.0, 3.0)
    assert xp == expected_xp
    assert z == expected_z
    assert reseeded is False  # threading the chain is never a reseed
    # And the explicit prior differs from the DB-threaded path.
    db_xp, db_z, db_reseeded = xp_for_date(conn, "2025-01-02")
    assert xp != db_xp
    assert z != db_z
    assert db_reseeded is False


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
