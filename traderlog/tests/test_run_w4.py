"""W4 runner stage boundaries: upstream failure must block dependent output."""
from __future__ import annotations

from traderlog import run_w4
from traderlog.db import init_db, now_iso


def _insert_eq_price(db_path):
    conn = init_db(db_path)
    try:
        conn.execute(
            "INSERT INTO daily_prices "
            "(symbol, trade_date, series, open, high, low, close, prev_close, volume, "
            "turnover, num_trades, delivery_pct, source, ingested_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("FOO", "2025-04-01", "EQ", 100, 101, 99, 100, 99, 1000, 1, 1, 50, "test", now_iso()),
        )
        conn.commit()
    finally:
        conn.close()


def test_bhavcopy_failure_blocks_all_later_stages(tmp_path, monkeypatch):
    db_path = tmp_path / "traderlog.db"
    calls = []
    monkeypatch.setattr(run_w4, "DB_PATH", db_path)
    monkeypatch.setattr(run_w4.bhavcopy, "discover_dates", lambda: ["2025-04-01"])
    monkeypatch.setattr(
        run_w4.bhavcopy,
        "backfill",
        lambda conn, dates: {"dates": 1, "rows": 0, "failed": ["2025-04-01"]},
    )
    monkeypatch.setattr(run_w4.breadth_counts, "run", lambda *args: calls.append("counts"))
    monkeypatch.setattr(run_w4.universe_breadth, "run", lambda *args: calls.append("universe"))
    monkeypatch.setattr(run_w4.regime_daily, "backfill", lambda *args: calls.append("regime"))

    assert run_w4.main([]) == 1
    assert calls == []


def test_breadth_count_failure_blocks_universe_and_regime_stages(tmp_path, monkeypatch):
    db_path = tmp_path / "traderlog.db"
    _insert_eq_price(db_path)
    calls = []
    monkeypatch.setattr(run_w4, "DB_PATH", db_path)
    monkeypatch.setattr(run_w4.bhavcopy, "discover_dates", lambda: ["2025-04-01"])
    monkeypatch.setattr(run_w4.bhavcopy, "backfill", lambda conn, dates: {"dates": 1, "rows": 0, "failed": []})
    monkeypatch.setattr(
        run_w4.breadth_counts, "run", lambda *args: {"status": "fail", "detail": "bad counts"}
    )
    monkeypatch.setattr(run_w4.universe_breadth, "run", lambda *args: calls.append("universe"))
    monkeypatch.setattr(run_w4.regime_daily, "backfill", lambda *args: calls.append("regime"))

    assert run_w4.main([]) == 1
    assert calls == []


def test_universe_failure_blocks_regime_stage(tmp_path, monkeypatch):
    db_path = tmp_path / "traderlog.db"
    _insert_eq_price(db_path)
    calls = []
    monkeypatch.setattr(run_w4, "DB_PATH", db_path)
    monkeypatch.setattr(run_w4.bhavcopy, "discover_dates", lambda: ["2025-04-01"])
    monkeypatch.setattr(run_w4.bhavcopy, "backfill", lambda conn, dates: {"dates": 1, "rows": 0, "failed": []})
    monkeypatch.setattr(run_w4.breadth_counts, "run", lambda *args: {"status": "ok"})
    monkeypatch.setattr(
        run_w4.universe_breadth, "run", lambda *args: {"status": "fail", "detail": "coverage"}
    )
    monkeypatch.setattr(run_w4.regime_daily, "backfill", lambda *args: calls.append("regime"))

    assert run_w4.main([]) == 1
    assert calls == []
