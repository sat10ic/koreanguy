"""W4 — traderlog/adopted/universe_breadth.py.

The NIFTYMIDSML400 constituent breadth that feeds XP/MBI. Confirms the real
constituents CSV loads, and that compute_breadth/run only count constituents
present in daily_prices for the given date (never the whole daily_prices
universe -- feeding XP a different universe's advancer counts is the
documented failure mode this module exists to prevent).
"""
from __future__ import annotations

from traderlog.adopted import universe_breadth as ub
from traderlog.db import init_db, now_iso


def test_load_constituents_reads_the_real_copied_csv():
    symbols = ub.load_constituents()
    assert len(symbols) == 400
    assert "360ONE" in symbols
    assert all(s == s.upper() for s in symbols)


def test_load_constituents_empty_when_file_absent(tmp_path):
    assert ub.load_constituents(tmp_path / "missing.csv") == []


def _insert_price(conn, symbol, trade_date, *, close, prev_close, high=None, low=None):
    conn.execute(
        "INSERT OR REPLACE INTO daily_prices "
        "(symbol, trade_date, series, open, high, low, close, prev_close, volume, "
        " turnover, num_trades, delivery_pct, source, ingested_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            symbol, trade_date, "EQ", close, high if high is not None else close,
            low if low is not None else close, close, prev_close, 100000,
            10.0, 500, 50.0, "bhavcopy", now_iso(),
        ),
    )


def _insert_minimum_coverage(conn, trade_date):
    symbols = [f"S{i:03d}" for i in range(400)]
    for symbol in symbols[:340]:
        _insert_price(conn, symbol, trade_date, close=105.0, prev_close=100.0)
    return symbols


def test_compute_breadth_only_counts_the_given_symbol_list(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    # ONLY_IN is a real symbol but NOT in our fake constituent list below.
    _insert_price(conn, "IN_UNIVERSE", "2025-04-01", close=110.0, prev_close=100.0)  # +10% burst
    _insert_price(conn, "ONLY_IN_DAILY_PRICES", "2025-04-01", close=200.0, prev_close=100.0)
    conn.commit()

    b = ub.compute_breadth(conn, "2025-04-01", symbols=["IN_UNIVERSE"])
    assert b is not None
    assert b["constituents"] == 1
    assert b["advances"] == 1
    assert b["up_4pct"] > 0  # floored at 0.25 min, but real move here is 100%


def test_compute_breadth_none_when_no_constituent_data(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    assert ub.compute_breadth(conn, "2025-04-01", symbols=["NOPE"]) is None


def test_run_writes_breadth_daily_row_at_85_percent_coverage_floor(tmp_path, monkeypatch):
    conn = init_db(tmp_path / "traderlog.db")
    symbols = _insert_minimum_coverage(conn, "2025-04-01")
    monkeypatch.setattr(ub, "load_constituents", lambda: symbols)
    conn.commit()

    result = ub.run(conn, "2025-04-01")
    assert result["status"] == "ok"
    row = conn.execute(
        "SELECT trade_date, advances, declines, universe_size, source FROM breadth_daily "
    ).fetchone()
    assert row["universe_size"] == 340
    assert row["source"] == "niftymidsml400_bhavcopy"


def test_run_is_idempotent_at_accepted_coverage(tmp_path, monkeypatch):
    conn = init_db(tmp_path / "traderlog.db")
    symbols = _insert_minimum_coverage(conn, "2025-04-01")
    monkeypatch.setattr(ub, "load_constituents", lambda: symbols)
    conn.commit()
    ub.run(conn, "2025-04-01")
    ub.run(conn, "2025-04-01")
    assert conn.execute("SELECT COUNT(*) FROM breadth_daily").fetchone()[0] == 1


def test_run_fails_when_configured_constituents_have_no_data(tmp_path, monkeypatch):
    conn = init_db(tmp_path / "traderlog.db")
    symbols = [f"S{i:03d}" for i in range(400)]
    monkeypatch.setattr(ub, "load_constituents", lambda: symbols)
    result = ub.run(conn, "2025-04-01")
    assert result["status"] == "fail"
    assert "0/400" in result["detail"]
    assert "85%" in result["detail"]
    assert conn.execute("SELECT COUNT(*) FROM breadth_daily").fetchone()[0] == 0


def test_run_skips_only_when_constituent_configuration_is_absent(tmp_path, monkeypatch):
    conn = init_db(tmp_path / "traderlog.db")
    monkeypatch.setattr(ub, "load_constituents", lambda: [])

    result = ub.run(conn, "2025-04-01")

    assert result == {"status": "skip", "rows": 0, "detail": "no configured constituents"}
    assert conn.execute("SELECT COUNT(*) FROM breadth_daily").fetchone()[0] == 0


def test_run_rejects_constituent_coverage_below_85_percent(tmp_path, monkeypatch):
    conn = init_db(tmp_path / "traderlog.db")
    symbols = [f"S{i:03d}" for i in range(400)]
    monkeypatch.setattr(ub, "load_constituents", lambda: symbols)
    for symbol in symbols[:339]:
        _insert_price(conn, symbol, "2025-04-01", close=105.0, prev_close=100.0)
    conn.commit()

    result = ub.run(conn, "2025-04-01")

    assert result["status"] == "fail"
    assert "339/400" in result["detail"]
    assert "85%" in result["detail"]
    assert conn.execute("SELECT COUNT(*) FROM breadth_daily").fetchone()[0] == 0
