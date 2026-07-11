"""Unit tests for api.app._symbol_returns (UI_BUILD_DIRECTION 4b).

The DEBATE table's EOD/3D/7D/1M/3M returns + 30-bar spark are computed from
REAL daily_prices closes via the same trading-row-offset convention as
_index_returns. These tests pin: correct offsets, honest None on short
history, and an ascending spark of at most 30 closes.
"""
from manas_os import db
from manas_os.api import app as api_app
from manas_os.tests.conftest import insert_price_ramp, trading_dates


AS_OF = "2026-06-30"


def test_symbol_returns_computes_offsets_and_30bar_spark(tmp_path):
    conn = db.init_db(tmp_path / "m.db")
    try:
        # 70 sessions rising by +1.0/bar from 100 -> last close 170.
        last = insert_price_ramp(conn, symbol="ACME", n=70, start=100.0, step=1.0, end=AS_OF)
        returns, spark = api_app._symbol_returns(conn, "ACME", last)

        # closes: bar i has close = 100 + i (i=1..70) -> latest = 170.
        # offset k compares latest to the close k rows back (k sessions ago).
        assert returns["eod"] is not None and returns["eod"] > 0  # 170 vs 169
        assert returns["d3"] is not None and returns["d3"] > returns["eod"]
        assert returns["m3"] is not None  # 63 sessions of history available

        # spark is ascending (oldest -> newest) and capped at 30 closes.
        assert len(spark) == 30
        assert spark == sorted(spark)
        assert spark[-1] == 170.0
    finally:
        conn.close()


def test_symbol_returns_nulls_when_history_too_short(tmp_path):
    conn = db.init_db(tmp_path / "m.db")
    try:
        # Only 8 sessions -> m1 (21) and m3 (63) must be None, d7 (7) present.
        last = insert_price_ramp(conn, symbol="TINY", n=8, start=50.0, step=0.5, end=AS_OF)
        returns, spark = api_app._symbol_returns(conn, "TINY", last)

        assert returns["eod"] is not None
        assert returns["d7"] is not None  # exactly 8 rows -> offset 7 available
        assert returns["m1"] is None
        assert returns["m3"] is None
        assert len(spark) == 8  # fewer than 30 closes -> return what exists
        assert spark == sorted(spark)
    finally:
        conn.close()


def test_symbol_returns_empty_when_no_prices(tmp_path):
    conn = db.init_db(tmp_path / "m.db")
    try:
        returns, spark = api_app._symbol_returns(conn, "NOPE", AS_OF)
        assert returns == {"eod": None, "d3": None, "d7": None, "m1": None, "m3": None}
        assert spark == []
    finally:
        conn.close()
