"""tests/test_breadth_analytics.py — test suite for the Breadth Analytics module.

Verifies mathematical formulas, division-by-zero guards, dynamic SMA logic,
competing metrics definitions, and the honest-empty rule.
"""
from __future__ import annotations

import sqlite3
import pytest

from manas_os.regime import breadth_analytics as ba

DDL = """
CREATE TABLE IF NOT EXISTS breadth_counts (
    trade_date            TEXT PRIMARY KEY,
    total_universe        INTEGER,
    up_4pct               INTEGER,
    down_4pct             INTEGER,
    high_vol               INTEGER,
    low_vol                INTEGER,
    range_contraction      INTEGER,  -- range <= 3%
    range_expansion         INTEGER,  -- range >= 5.01%
    close_upper_half        INTEGER,  -- expansion candles only
    close_lower_half        INTEGER,  -- expansion candles only
    breakouts               INTEGER,
    breakout_sustained      INTEGER,
    breakout_failed         INTEGER,
    breakdowns              INTEGER,
    breakdown_sustained     INTEGER,
    breakdown_failed        INTEGER,
    up_15pct_5d             INTEGER,
    down_15pct_5d           INTEGER,
    up_25pct_20d            INTEGER,
    down_25pct_20d          INTEGER,
    above_10pct_10dema      INTEGER,
    below_10pct_10dema      INTEGER,
    above_10dema            INTEGER,
    above_20dema            INTEGER,
    above_50dema            INTEGER,
    above_200dema           INTEGER,
    new_52wk_high           INTEGER,
    new_52wk_low            INTEGER,
    from_52wh_15pct         INTEGER,
    from_52wh_30pct         INTEGER,
    from_52wh_50pct         INTEGER,
    from_52wh_70pct         INTEGER,
    from_52wh_70pct_plus    INTEGER,
    from_52wl_15pct         INTEGER,
    from_52wl_30pct         INTEGER,
    from_52wl_50pct         INTEGER,
    from_52wl_90pct         INTEGER,
    from_52wl_150pct        INTEGER,
    from_52wl_150pct_plus   INTEGER,
    source                  TEXT DEFAULT 'breadth_counts',
    ingested_at             TEXT DEFAULT (datetime('now'))
);
"""

def seed_db(conn: sqlite3.Connection, rows: list[dict]):
    columns = [
        "trade_date", "total_universe", "up_4pct", "down_4pct", "high_vol", "low_vol",
        "range_contraction", "range_expansion", "close_upper_half", "close_lower_half",
        "breakouts", "breakout_sustained", "breakout_failed", "breakdowns", "breakdown_sustained",
        "breakdown_failed", "up_15pct_5d", "down_15pct_5d", "up_25pct_20d", "down_25pct_20d",
        "above_10pct_10dema", "below_10pct_10dema", "above_10dema", "above_20dema", "above_50dema",
        "above_200dema", "new_52wk_high", "new_52wk_low", "from_52wh_15pct", "from_52wh_30pct",
        "from_52wh_50pct", "from_52wh_70pct", "from_52wh_70pct_plus", "from_52wl_15pct",
        "from_52wl_30pct", "from_52wl_50pct", "from_52wl_90pct", "from_52wl_150pct", "from_52wl_150pct_plus"
    ]
    for r in rows:
        row_vals = [r.get(col) for col in columns]
        placeholders = ", ".join(["?"] * len(columns))
        col_names = ", ".join(columns)
        conn.execute(f"INSERT OR REPLACE INTO breadth_counts ({col_names}) VALUES ({placeholders})", row_vals)
    conn.commit()

@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute(DDL)
    c.commit()
    yield c
    c.close()

@pytest.fixture
def seeded_conn(conn):
    # 12-day seed data with various edge cases and normal scenarios
    rows = [
        {"trade_date": "2026-07-01", "total_universe": 1000, "new_52wk_high": 10, "new_52wk_low": 5, "range_expansion": 20, "range_contraction": 10, "high_vol": 50, "low_vol": 25, "breakouts": 30, "breakdowns": 15, "breakout_sustained": 12, "breakout_failed": 18, "breakdown_sustained": 6, "breakdown_failed": 9, "up_4pct": 12, "down_4pct": 6, "close_upper_half": 15, "close_lower_half": 5, "from_52wh_15pct": 200, "from_52wh_30pct": 300, "from_52wl_15pct": 100, "from_52wl_30pct": 200},
        {"trade_date": "2026-07-02", "total_universe": 1000, "new_52wk_high": 12, "new_52wk_low": 4, "range_expansion": 22, "range_contraction": 11, "high_vol": 60, "low_vol": 30, "breakouts": 32, "breakdowns": 16, "breakout_sustained": 16, "breakout_failed": 16, "breakdown_sustained": 8, "breakdown_failed": 8, "up_4pct": 16, "down_4pct": 8, "close_upper_half": 16, "close_lower_half": 6, "from_52wh_15pct": 210, "from_52wh_30pct": 310, "from_52wl_15pct": 110, "from_52wl_30pct": 210},
        {"trade_date": "2026-07-03", "total_universe": 1000, "new_52wk_high": 8, "new_52wk_low": 6, "range_expansion": 18, "range_contraction": 9, "high_vol": 40, "low_vol": 20, "breakouts": 28, "breakdowns": 14, "breakout_sustained": 14, "breakout_failed": 14, "breakdown_sustained": 7, "breakdown_failed": 7, "up_4pct": 14, "down_4pct": 7, "close_upper_half": 12, "close_lower_half": 6, "from_52wh_15pct": 190, "from_52wh_30pct": 290, "from_52wl_15pct": 90, "from_52wl_30pct": 190},
        {"trade_date": "2026-07-06", "total_universe": 1000, "new_52wk_high": 15, "new_52wk_low": 3, "range_expansion": 25, "range_contraction": 8, "high_vol": 70, "low_vol": 35, "breakouts": 35, "breakdowns": 17, "breakout_sustained": 21, "breakout_failed": 14, "breakdown_sustained": 10, "breakdown_failed": 7, "up_4pct": 20, "down_4pct": 8, "close_upper_half": 20, "close_lower_half": 5, "from_52wh_15pct": 220, "from_52wh_30pct": 320, "from_52wl_15pct": 120, "from_52wl_30pct": 220},
        {"trade_date": "2026-07-07", "total_universe": 1000, "new_52wk_high": 11, "new_52wk_low": 5, "range_expansion": 21, "range_contraction": 7, "high_vol": 50, "low_vol": 25, "breakouts": 31, "breakdowns": 15, "breakout_sustained": 15, "breakout_failed": 16, "breakdown_sustained": 7, "breakdown_failed": 8, "up_4pct": 15, "down_4pct": 7, "close_upper_half": 14, "close_lower_half": 7, "from_52wh_15pct": 200, "from_52wh_30pct": 300, "from_52wl_15pct": 100, "from_52wl_30pct": 200},
        {"trade_date": "2026-07-08", "total_universe": 1000, "new_52wk_high": 14, "new_52wk_low": 4, "range_expansion": 24, "range_contraction": 12, "high_vol": 80, "low_vol": 40, "breakouts": 34, "breakdowns": 18, "breakout_sustained": 17, "breakout_failed": 17, "breakdown_sustained": 9, "breakdown_failed": 9, "up_4pct": 17, "down_4pct": 9, "close_upper_half": 18, "close_lower_half": 6, "from_52wh_15pct": 230, "from_52wh_30pct": 330, "from_52wl_15pct": 130, "from_52wl_30pct": 230},
        {"trade_date": "2026-07-09", "total_universe": 1000, "new_52wk_high": 9, "new_52wk_low": 7, "range_expansion": 19, "range_contraction": 9, "high_vol": 44, "low_vol": 22, "breakouts": 29, "breakdowns": 15, "breakout_sustained": 12, "breakout_failed": 17, "breakdown_sustained": 6, "breakdown_failed": 9, "up_4pct": 13, "down_4pct": 6, "close_upper_half": 13, "close_lower_half": 6, "from_52wh_15pct": 195, "from_52wh_30pct": 295, "from_52wl_15pct": 95, "from_52wl_30pct": 195},
        {"trade_date": "2026-07-10", "total_universe": 1000, "new_52wk_high": 13, "new_52wk_low": 3, "range_expansion": 23, "range_contraction": 11, "high_vol": 66, "low_vol": 33, "breakouts": 33, "breakdowns": 16, "breakout_sustained": 18, "breakout_failed": 15, "breakdown_sustained": 10, "breakdown_failed": 6, "up_4pct": 18, "down_4pct": 6, "close_upper_half": 17, "close_lower_half": 6, "from_52wh_15pct": 225, "from_52wh_30pct": 325, "from_52wl_15pct": 125, "from_52wl_30pct": 225},
        {"trade_date": "2026-07-13", "total_universe": 1000, "new_52wk_high": 16, "new_52wk_low": 2, "range_expansion": 26, "range_contraction": 13, "high_vol": 90, "low_vol": 30, "breakouts": 36, "breakdowns": 18, "breakout_sustained": 24, "breakout_failed": 12, "breakdown_sustained": 12, "breakdown_failed": 6, "up_4pct": 24, "down_4pct": 6, "close_upper_half": 20, "close_lower_half": 6, "from_52wh_15pct": 240, "from_52wh_30pct": 340, "from_52wl_15pct": 140, "from_52wl_30pct": 240},
        {"trade_date": "2026-07-14", "total_universe": 1000, "new_52wk_high": 20, "new_52wk_low": 1, "range_expansion": 30, "range_contraction": 15, "high_vol": 100, "low_vol": 50, "breakouts": 40, "breakdowns": 20, "breakout_sustained": 30, "breakout_failed": 10, "breakdown_sustained": 15, "breakdown_failed": 5, "up_4pct": 30, "down_4pct": 5, "close_upper_half": 25, "close_lower_half": 5, "from_52wh_15pct": 250, "from_52wh_30pct": 350, "from_52wl_15pct": 150, "from_52wl_30pct": 250},
        {"trade_date": "2026-07-15", "total_universe": 1000, "new_52wk_high": 18, "new_52wk_low": 2, "range_expansion": 28, "range_contraction": 14, "high_vol": 80, "low_vol": 40, "breakouts": 38, "breakdowns": 19, "breakout_sustained": 28, "breakout_failed": 10, "breakdown_sustained": 14, "breakdown_failed": 5, "up_4pct": 28, "down_4pct": 5, "close_upper_half": 22, "close_lower_half": 6, "from_52wh_15pct": 245, "from_52wh_30pct": 345, "from_52wl_15pct": 145, "from_52wl_30pct": 245},
        # Row 12 contains zero-denominator values and test bounds. breakout_sustained is 35.
        {"trade_date": "2026-07-16", "total_universe": 1000, "new_52wk_high": 15, "new_52wk_low": 3, "range_expansion": 25, "range_contraction": 0, "high_vol": 70, "low_vol": 0, "breakouts": 35, "breakout_sustained": 35, "breakout_failed": 0, "breakdowns": 0, "breakdown_failed": 0, "up_4pct": 20, "down_4pct": 5, "close_upper_half": 20, "close_lower_half": 5, "from_52wh_15pct": 235, "from_52wh_30pct": 335, "from_52wl_15pct": 135, "from_52wl_30pct": 235}
    ]
    seed_db(conn, rows)
    return conn

def test_net_nh_nl(seeded_conn):
    # day 10: new_52wk_high = 20, new_52wk_low = 1, total_universe = 1000
    # net_nh_nl = (20 / 1000 - 1 / 1000) * 100 = 1.9
    res = ba.net_nh_nl(seeded_conn, "2026-07-14", 1)
    assert len(res) == 1
    assert res[0]["trade_date"] == "2026-07-14"
    assert pytest.approx(res[0]["value"]) == 1.9

    # Add a row with total_universe = 0
    seed_db(seeded_conn, [{"trade_date": "2026-07-17", "total_universe": 0, "new_52wk_high": 10, "new_52wk_low": 10}])
    res2 = ba.net_nh_nl(seeded_conn, "2026-07-17", 2)
    # The row for 2026-07-17 must be excluded (honest-empty rule)
    assert len(res2) == 1
    assert res2[0]["trade_date"] == "2026-07-16"

def test_fosback_hl_logic_index(seeded_conn):
    # 12 rows are seeded.
    # Daily logic values (min(nh, nl)/1000 * 100) are:
    # Row 1: 0.5, Row 2: 0.4, Row 3: 0.6, Row 4: 0.3, Row 5: 0.5
    # Row 6: 0.4, Row 7: 0.7, Row 8: 0.3, Row 9: 0.2, Row 10: 0.1
    # First 10-day sum = 4.0 -> SMA at Row 10 (2026-07-14) = 0.4
    res = ba.fosback_hl_logic_index(seeded_conn, "2026-07-16", 3)
    assert len(res) == 3
    assert res[0]["trade_date"] == "2026-07-14"
    assert pytest.approx(res[0]["value"]) == 0.4
    
    # 2026-07-15 logic value: min(18, 2)/1000 * 100 = 0.2
    # Row 2 to 11 sum = 4.0 - 0.5 + 0.2 = 3.7 -> SMA = 0.37
    assert res[1]["trade_date"] == "2026-07-15"
    assert pytest.approx(res[1]["value"]) == 0.37

    # 2026-07-16 logic value: min(15, 3)/1000 * 100 = 0.3
    # Row 3 to 12 sum = 3.7 - 0.4 + 0.3 = 3.6 -> SMA = 0.36
    assert res[2]["trade_date"] == "2026-07-16"
    assert pytest.approx(res[2]["value"]) == 0.36

    # Test short history window exception
    short_conn = sqlite3.connect(":memory:")
    short_conn.execute(DDL)
    seed_db(short_conn, [{"trade_date": "2026-07-01", "total_universe": 1000, "new_52wk_high": 10, "new_52wk_low": 5}])
    # 1 row only -> returns []
    assert ba.fosback_hl_logic_index(short_conn, "2026-07-01", 1) == []
    short_conn.close()

def test_volatility_ratio(seeded_conn):
    # day 10: range_expansion = 30, range_contraction = 15 -> ratio = 2.0
    res = ba.volatility_ratio(seeded_conn, "2026-07-14", 1)
    assert len(res) == 1
    assert res[0]["value"] == 2.0

    # day 12: range_contraction = 0 -> skipped
    res_skip = ba.volatility_ratio(seeded_conn, "2026-07-16", 1)
    assert res_skip == []

def test_volume_ratio(seeded_conn):
    # day 10: high_vol = 100, low_vol = 50 -> ratio = 2.0
    res = ba.volume_ratio(seeded_conn, "2026-07-14", 1)
    assert len(res) == 1
    assert res[0]["value"] == 2.0

    # day 12: low_vol = 0 -> skipped
    res_skip = ba.volume_ratio(seeded_conn, "2026-07-16", 1)
    assert res_skip == []

def test_bo_bd_ratios(seeded_conn):
    # day 10: breakouts=40, breakdowns=20, breakout_sustained=30, breakout_failed=10,
    # breakdown_sustained=15, breakdown_failed=5
    # bo_bd_ratio = 40/20 = 2.0
    # bo_sustained_ratio = 30/40 = 0.75
    # bo_failed_ratio = 10/40 = 0.25
    # bo_sf_ratio = 30/10 = 3.0
    # bd_sustained_ratio = 15/20 = 0.75
    # bd_failed_ratio = 5/20 = 0.25
    # bd_sf_ratio = 15/5 = 3.0
    res = ba.bo_bd_ratios(seeded_conn, "2026-07-14", 1)
    assert len(res) == 1
    day = res[0]
    assert day["trade_date"] == "2026-07-14"
    assert day["bo_bd_ratio"] == 2.0
    assert day["bo_sustained_ratio"] == 0.75
    assert day["bo_failed_ratio"] == 0.25
    assert day["bo_sf_ratio"] == 3.0
    assert day["bd_sustained_ratio"] == 0.75
    assert day["bd_failed_ratio"] == 0.25
    assert day["bd_sf_ratio"] == 3.0

    # day 12 checks denominators == 0 -> None
    res_zero = ba.bo_bd_ratios(seeded_conn, "2026-07-16", 1)
    assert len(res_zero) == 1
    day_zero = res_zero[0]
    # breakdowns is 0 -> bo_bd_ratio, bd_sustained_ratio, bd_failed_ratio should be None
    assert day_zero["bo_bd_ratio"] is None
    assert day_zero["bd_sustained_ratio"] is None
    assert day_zero["bd_failed_ratio"] is None
    # breakout_failed is 0 -> bo_sf_ratio is None
    assert day_zero["bo_sf_ratio"] is None
    # breakout_sustained is 35, breakouts is 35 -> bo_sustained_ratio = 35/35 = 1.0, bo_failed_ratio = 0/35 = 0.0
    assert day_zero["bo_failed_ratio"] == 0.0
    assert day_zero["bo_sustained_ratio"] == 1.0

def test_close_pct_ratios(seeded_conn):
    # day 10: up_4pct=30, breakouts=40, close_upper_half=25, range_expansion=30
    # up_close_pct = 30 / 40 = 0.75 (breakout-denominated)
    # up_close_pct_range_denom = 25 / 30 = 0.8333... (expansion-denominated)
    # down_close_pct = 5 / 20 = 0.25
    # down_close_pct_range_denom = 5 / 30 = 0.1666...
    res = ba.close_pct_ratios(seeded_conn, "2026-07-14", 1)
    assert len(res) == 1
    day = res[0]
    assert day["up_close_pct"] == 0.75
    assert pytest.approx(day["up_close_pct_range_denom"]) == 0.8333333333333334
    assert day["down_close_pct"] == 0.25
    assert pytest.approx(day["down_close_pct_range_denom"]) == 0.16666666666666666

def test_distance_band_pct(seeded_conn):
    # day 10: total_universe=1000, from_52wh_15pct=250, from_52wh_30pct=350, from_52wl_15pct=150
    # wh_15pct = 250 / 1000 * 100 = 25.0
    # wh_30pct = 350 / 1000 * 100 = 35.0
    # wl_15pct = 150 / 1000 * 100 = 15.0
    res = ba.distance_band_pct(seeded_conn, "2026-07-14", 1)
    assert len(res) == 1
    day = res[0]
    assert day["from_52wh_15pct"] == 25.0
    assert day["from_52wh_30pct"] == 35.0
    assert day["from_52wl_15pct"] == 15.0

def test_net_hl_spreads(seeded_conn):
    # day 10: wh15=250, wh30=350, wl15=150, wl30=250
    # net_15pct_hl = (250 - 150) / 1000 * 100 = 10.0
    # net_30pct_hl = ((250 + 350) - (150 + 250)) / 1000 * 100 = (600 - 400)/10 = 20.0
    res = ba.net_hl_spreads(seeded_conn, "2026-07-14", 1)
    assert len(res) == 1
    day = res[0]
    assert day["net_15pct_hl"] == 10.0
    assert day["net_30pct_hl"] == 20.0

def test_summary(seeded_conn):
    # Test summary for 2026-07-14
    summary_dict = ba.summary(seeded_conn, "2026-07-14")
    assert summary_dict["as_of"] == "2026-07-14"
    assert pytest.approx(summary_dict["net_nh_nl"]) == 1.9
    assert pytest.approx(summary_dict["fosback_hl_logic_index"]) == 0.4
    assert summary_dict["volatility_ratio"] == 2.0
    assert summary_dict["volume_ratio"] == 2.0
    assert summary_dict["up_close_pct"] == 0.75
    assert summary_dict["from_52wh_15pct"] == 25.0
    assert summary_dict["net_15pct_hl"] == 10.0
    assert summary_dict["net_30pct_hl"] == 20.0

    # Test summary on empty table / missing date
    empty_conn = sqlite3.connect(":memory:")
    empty_conn.execute(DDL)
    empty_conn.commit()
    
    assert ba.summary(empty_conn, "2026-07-14") == {}
    assert ba.net_nh_nl(empty_conn, "2026-07-14", 5) == []
    empty_conn.close()

def test_missing_table_graceful_handling():
    # If the table breadth_counts is missing entirely (OperationalError),
    # functions should return [] or {} instead of crashing.
    no_table_conn = sqlite3.connect(":memory:")
    # No DDL executed, table does not exist
    assert ba.net_nh_nl(no_table_conn, "2026-07-14", 5) == []
    assert ba.summary(no_table_conn, "2026-07-14") == {}
    no_table_conn.close()
