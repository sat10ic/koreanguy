"""Tests for Breadth Tier 0 integrations."""
from __future__ import annotations

import json
import sqlite3
import pytest
from fastapi.testclient import TestClient

from manas_os import db
from manas_os.api.app import app
from manas_os.agents import context_pack

DAILY_PRICES_DDL = """
CREATE TABLE IF NOT EXISTS daily_prices (
    symbol        TEXT NOT NULL,
    trade_date    TEXT NOT NULL,
    series        TEXT DEFAULT 'EQ',
    open          REAL, high REAL, low REAL, close REAL, prev_close REAL,
    PRIMARY KEY (symbol, trade_date, series)
);
"""

SECTOR_INDEX_PRICES_DDL = """
CREATE TABLE IF NOT EXISTS sector_index_prices (
    symbol        TEXT NOT NULL,
    trade_date    TEXT NOT NULL,
    close          REAL,
    PRIMARY KEY (symbol, trade_date)
);
"""

REGIME_SNAPSHOTS_DDL = """
CREATE TABLE IF NOT EXISTS regime_snapshots (
    snapshot_date       TEXT PRIMARY KEY,
    market_mode         TEXT,
    xp_value            REAL,
    mbi_day_color       TEXT,
    r10 REAL, r20 REAL, r50 REAL, r4p5 REAL,
    pillars_passed      INTEGER
);
"""

BREADTH_DAILY_DDL = """
CREATE TABLE IF NOT EXISTS breadth_daily (
    trade_date            TEXT PRIMARY KEY,
    advances              INTEGER,
    declines              INTEGER,
    up_4pct               REAL,
    down_4pct             REAL,
    up_25pct_month        REAL,
    down_25pct_month      REAL,
    up_50pct_month        REAL,
    down_50pct_month      REAL,
    pct_10dma_gt_20dma    REAL,
    pct_20dma_gt_40dma    REAL,
    -- Market Quadrant inputs, added 2026-07-30. Present here so this fixture
    -- keeps matching db/schema.sql; the endpoint selects them and a fixture
    -- that drifts from the schema fails with a bare "no such column".
    pct_above_10dma       REAL,
    pct_above_50dma       REAL,
    pct_above_200dma      REAL,
    new_highs_52w         INTEGER,
    new_lows_52w          INTEGER,
    net_new_highs_pct     REAL,
    nhnl_universe         INTEGER
);
"""

BREADTH_COUNTS_DDL = """
CREATE TABLE IF NOT EXISTS breadth_counts (
    trade_date            TEXT PRIMARY KEY,
    total_universe        INTEGER,
    up_4pct               INTEGER,
    down_4pct             INTEGER,
    high_vol               INTEGER,
    low_vol                INTEGER,
    range_contraction      INTEGER,
    range_expansion         INTEGER,
    close_upper_half        INTEGER,
    close_lower_half        INTEGER,
    breakouts               INTEGER,
    breakout_sustained      INTEGER,
    breakout_failed         INTEGER,
    breakdowns              INTEGER,
    breakdown_sustained     INTEGER,
    breakdown_failed        INTEGER,
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
    from_52wl_150pct_plus   INTEGER
);
"""

@pytest.fixture
def test_db(tmp_path):
    db_path = tmp_path / "test_manas.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(DAILY_PRICES_DDL)
    conn.execute(SECTOR_INDEX_PRICES_DDL)
    conn.execute(REGIME_SNAPSHOTS_DDL)
    conn.execute(BREADTH_DAILY_DDL)
    conn.execute(BREADTH_COUNTS_DDL)
    
    # Seed 12 trading days of data to satisfy the 10-day Fosback SMA requirement
    for i in range(1, 13):
        date_str = f"2026-07-{i:02d}"
        
        # Seed daily_prices for VIX (needs a row so VIX isn't None)
        conn.execute("""
            INSERT OR REPLACE INTO sector_index_prices (symbol, trade_date, close)
            VALUES ('INDIAVIX', ?, 15.0)
        """, (date_str,))
        
        # Seed regime_snapshots
        conn.execute("""
            INSERT OR REPLACE INTO regime_snapshots (snapshot_date, market_mode, xp_value, mbi_day_color)
            VALUES (?, 'SELECTIVE', 6.5, 'GREEN')
        """, (date_str,))
        
        # Seed breadth_daily
        conn.execute("""
            INSERT OR REPLACE INTO breadth_daily 
            (trade_date, advances, declines, up_4pct, down_4pct, up_25pct_month, down_25pct_month)
            VALUES (?, 600, 400, 15.0, 5.0, 2.0, 1.0)
        """, (date_str,))
        
        # Seed breadth_counts
        conn.execute("""
            INSERT OR REPLACE INTO breadth_counts
            (trade_date, total_universe, up_4pct, down_4pct, high_vol, low_vol, range_contraction, range_expansion,
             breakouts, breakout_failed, breakout_sustained, new_52wk_high, new_52wk_low, above_200dema,
             from_52wh_15pct, from_52wh_30pct, from_52wl_15pct, from_52wl_30pct)
            VALUES (?, 1000, 150, 50, 40, 20, 10, 15, 30, 10, 20, 25, 5, 650, 200, 300, 100, 200)
        """, (date_str,))
        
    conn.commit()
    conn.close()
    return db_path


def test_breadth_analytics_api_returns_extended_fields(test_db, monkeypatch):
    orig_connect = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: orig_connect(test_db))
    
    client = TestClient(app)
    resp = client.get("/api/regime/breadth-analytics", params={"days": 5, "date": "2026-07-12"})
    assert resp.status_code == 200
    body = resp.json()
    
    assert body["available"] is True
    assert len(body["rows"]) > 0
    
    latest_row = body["rows"][-1]
    # Check that new API fields exist
    assert "net_nh_nl" in latest_row
    assert "fosback_hl_logic_index" in latest_row
    assert "volatility_ratio" in latest_row
    assert "volume_ratio" in latest_row
    assert "bo_sf_ratio" in latest_row
    
    # Assert values match our seeded math:
    # nh=25, nl=5, univ=1000 -> net_nh_nl = (25/1000 - 5/1000)*100 = 2.0 pp
    assert latest_row["net_nh_nl"] == pytest.approx(2.0)
    
    # range_expansion = 15, range_contraction = 10 -> volatility_ratio = 1.5
    assert latest_row["volatility_ratio"] == pytest.approx(1.5)
    
    # high_vol = 40, low_vol = 20 -> volume_ratio = 2.0
    assert latest_row["volume_ratio"] == pytest.approx(2.0)
    
    # breakout_sustained = 20, breakout_failed = 10 -> bo_sf_ratio = 2.0
    assert latest_row["bo_sf_ratio"] == pytest.approx(2.0)


def test_debate_context_breadth_quality(test_db, monkeypatch):
    conn = sqlite3.connect(test_db)
    conn.row_factory = sqlite3.Row
    
    # Test context pack output directly
    pack = context_pack.build_pack(conn, "2026-07-12", shortlist=[])
    conn.close()
    
    assert "breadth_quality" in pack
    bq = pack["breadth_quality"]
    
    assert "bo_sf_line" in bq
    assert "fosback_line" in bq
    assert "volatility_line" in bq
    assert "dema_200_line" in bq
    
    # Verify plain-English messages contain seeded numbers
    assert "S/F ratio" in bq["bo_sf_line"]
    assert "Volatility ratio is 1.5" in bq["volatility_line"]
    assert "65.0%" in bq["dema_200_line"]
