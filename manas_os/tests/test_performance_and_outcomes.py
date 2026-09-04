from datetime import date, timedelta

from fastapi.testclient import TestClient

from manas_os import db
from manas_os.api import app as api_app
from manas_os.scanner import outcomes


def test_regime_sectors_exposes_timeframe_contract(tmp_path, monkeypatch):
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    try:
        conn.execute(
            "INSERT INTO industry_metrics "
            "(snapshot_date, name, perf_1d, perf_1w, perf_1m, perf_3m, rank_1m, rank_3m, num_stocks) "
            "VALUES ('2026-01-31', 'Private Banks', 1.0, 2.0, 3.0, 4.0, 1, 1, 12)"
        )
        conn.commit()
    finally:
        conn.close()

    orig_connect = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: orig_connect(db_path))
    client = TestClient(api_app.app)

    res = client.get("/api/regime/sectors", params={"date": "2026-01-31"})
    assert res.status_code == 200
    payload = res.json()
    assert payload["available"] is True
    row = payload["industries"][0]
    assert row["performance"] == {"1d": 1.0, "1w": 2.0, "1m": 3.0, "3m": 4.0, "6m": None}
    assert payload["unavailable_timeframes"]["6m"]


def test_regime_indices_returns_timeframe_performance(tmp_path, monkeypatch):
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    try:
        rows = []
        d0 = date.fromisoformat("2026-01-01")
        for i in range(130):
            rows.append(("NIFTY 50", (d0 + timedelta(days=i)).isoformat(), 100.0 + i, None))
        conn.executemany(
            "INSERT INTO sector_index_prices (symbol, trade_date, close, sma50) VALUES (?, ?, ?, ?)",
            rows,
        )
        conn.commit()
    finally:
        conn.close()

    orig_connect = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: orig_connect(db_path))
    client = TestClient(api_app.app)

    res = client.get("/api/regime/indices", params={"date": (date.fromisoformat("2026-01-01") + timedelta(days=129)).isoformat()})
    assert res.status_code == 200
    payload = res.json()
    assert payload["available"] is True
    idx = payload["indices"][0]
    assert idx["symbol"] == "NIFTY 50"
    assert idx["name"] == "Nifty 50"
    assert idx["returns"]["1d"] is not None
    assert idx["returns"]["6m"] is not None


def test_candidate_outcomes_persist_and_backfill(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        candidate = {
            "symbol": "ACME",
            "setup": "Near pivot",
            "readiness": 80,
            "grade": "A",
            "entry": 100.0,
            "stop": 95.0,
            "sector": "AUTO",
            "industry": "Auto Components",
            "evidence": [{"filter": "test", "value": "hit"}],
        }
        outcomes.persist_candidate_snapshot(conn, "2026-01-01", candidate)
        rows = [
            ("ACME", "2026-01-01", "EQ", 100.0, "test"),
            ("ACME", "2026-01-02", "EQ", 101.0, "test"),
            ("ACME", "2026-01-03", "EQ", 102.0, "test"),
            ("ACME", "2026-01-04", "EQ", 103.0, "test"),
            ("ACME", "2026-01-05", "EQ", 104.0, "test"),
            ("ACME", "2026-01-06", "EQ", 110.0, "test"),
        ]
        conn.executemany(
            "INSERT INTO daily_prices (symbol, trade_date, series, close, source) VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        written = outcomes.backfill_forward_returns(conn, through_date="2026-01-31")
        assert written == 3
        complete = conn.execute(
            "SELECT horizon, as_of_date, forward_return_pct, forward_r, status "
            "FROM outcomes WHERE horizon = 5"
        ).fetchone()
        assert complete["as_of_date"] == "2026-01-06"
        assert complete["forward_return_pct"] == 10.0
        assert complete["forward_r"] == 2.0
        assert complete["status"] == "complete"
        pending = conn.execute("SELECT status FROM outcomes WHERE horizon = 10").fetchone()
        assert pending["status"] == "pending"
    finally:
        conn.close()


def test_outcomes_mfe_mae_match_hand_computed_values(tmp_path):
    # W1.4: MFE = max favorable excursion in R over the horizon window;
    #       MAE = max adverse excursion in R. Hand-computed below.
    # Fixture: entry=100, stop=95 -> risk=5. Five forward bars with explicit
    # highs/lows. T+5 closes on the 5th bar (2026-01-06, close=104).
    #   bar1 (01-02): high 101 low 99
    #   bar2 (01-03): high 103 low 97
    #   bar3 (01-04): high 102 low 96   <- min low 96 -> MAE = (96-100)/5 = -0.8R
    #   bar4 (01-05): high 105 low 98   <- max high 105 -> MFE = (105-100)/5 = +1.0R
    #   bar5 (01-06): high 104 low 100
    # So MFE_r = +1.0, MAE_r = -0.8 (hand-computed, two routes checked).
    conn = db.init_db(tmp_path / "manas.db")
    try:
        candidate = {
            "symbol": "ACME", "setup": "Near pivot", "readiness": 80, "grade": "A",
            "entry": 100.0, "stop": 95.0, "sector": "AUTO", "industry": "Auto",
            "evidence": [{"filter": "test", "value": "hit"}],
        }
        outcomes.persist_candidate_snapshot(conn, "2026-01-01", candidate)
        conn.executemany(
            "INSERT INTO daily_prices (symbol, trade_date, series, close, high, low, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                ("ACME", "2026-01-01", "EQ", 100.0, 100.0, 100.0, "test"),
                ("ACME", "2026-01-02", "EQ", 101.0, 101.0, 99.0, "test"),
                ("ACME", "2026-01-03", "EQ", 102.0, 103.0, 97.0, "test"),
                ("ACME", "2026-01-04", "EQ", 103.0, 102.0, 96.0, "test"),
                ("ACME", "2026-01-05", "EQ", 104.0, 105.0, 98.0, "test"),
                ("ACME", "2026-01-06", "EQ", 104.0, 104.0, 100.0, "test"),
            ],
        )
        outcomes.backfill_forward_returns(conn, through_date="2026-01-31")
        row = conn.execute(
            "SELECT mfe_r, mae_r, status FROM outcomes WHERE horizon = 5"
        ).fetchone()
        assert row["status"] == "complete"
        assert row["mfe_r"] == 1.0  # (105 - 100) / 5
        assert row["mae_r"] == -0.8  # (96 - 100) / 5
    finally:
        conn.close()


def test_managed_exit_stop_hit_day2_prints_near_minus_1r(tmp_path):
    # E1-FIX: stop-exit modeling. Entry fills at the next session's open
    # (100, no gap); day 2's low (94) trades through the stop (95, risk=5).
    # Exit = stop * (1 - 0.2% slippage) = 94.81 -> r = (94.81-100)/5 = -1.038.
    conn = db.init_db(tmp_path / "manas.db")
    try:
        candidate = {
            "symbol": "ACME", "setup": "Near pivot", "readiness": 80, "grade": "A",
            "entry": 100.0, "stop": 95.0, "sector": "AUTO", "industry": "Auto",
            "evidence": [{"filter": "test", "value": "hit"}],
        }
        outcomes.persist_candidate_snapshot(conn, "2026-01-01", candidate)
        conn.executemany(
            "INSERT INTO daily_prices (symbol, trade_date, series, open, high, low, close, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("ACME", "2026-01-01", "EQ", 100.0, 100.0, 100.0, 100.0, "test"),
                ("ACME", "2026-01-02", "EQ", 100.0, 101.0, 99.0, 100.5, "test"),
                ("ACME", "2026-01-03", "EQ", 100.0, 100.5, 94.0, 96.0, "test"),
                ("ACME", "2026-01-04", "EQ", 96.0, 97.0, 95.5, 96.5, "test"),
                ("ACME", "2026-01-05", "EQ", 96.5, 98.0, 96.0, 97.0, "test"),
                ("ACME", "2026-01-06", "EQ", 97.0, 98.0, 96.5, 97.5, "test"),
            ],
        )
        outcomes.backfill_forward_returns(conn, through_date="2026-01-31")
        row = conn.execute(
            "SELECT entry_fill, exit_date, exit_reason, managed_r, hit_1r, hit_2r "
            "FROM outcomes WHERE horizon = 5"
        ).fetchone()
        assert row["entry_fill"] == 100.0
        assert row["exit_date"] == "2026-01-03"
        assert row["exit_reason"] == "stop"
        assert row["managed_r"] == -1.038
        assert row["managed_r"] >= -1.05  # a stop-honored exit cannot be much worse than -1R
        assert row["hit_1r"] == 0 and row["hit_2r"] == 0
    finally:
        conn.close()


def test_managed_exit_runner_hits_2r_and_holds_to_horizon_close(tmp_path):
    # Entry=100, stop=90 (risk=10), never touches the stop; the high on day 4
    # reaches 120 (+2R) before closing the T+5 window at 118 (+1.8R).
    conn = db.init_db(tmp_path / "manas.db")
    try:
        candidate = {
            "symbol": "ACME", "setup": "Near pivot", "readiness": 80, "grade": "A",
            "entry": 100.0, "stop": 90.0, "sector": "AUTO", "industry": "Auto",
            "evidence": [{"filter": "test", "value": "hit"}],
        }
        outcomes.persist_candidate_snapshot(conn, "2026-01-01", candidate)
        conn.executemany(
            "INSERT INTO daily_prices (symbol, trade_date, series, open, high, low, close, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("ACME", "2026-01-01", "EQ", 100.0, 100.0, 100.0, 100.0, "test"),
                ("ACME", "2026-01-02", "EQ", 100.0, 105.0, 99.0, 104.0, "test"),
                ("ACME", "2026-01-03", "EQ", 104.0, 110.0, 103.0, 108.0, "test"),
                ("ACME", "2026-01-04", "EQ", 108.0, 120.0, 107.0, 115.0, "test"),
                ("ACME", "2026-01-05", "EQ", 115.0, 117.0, 112.0, 116.0, "test"),
                ("ACME", "2026-01-06", "EQ", 116.0, 119.0, 115.0, 118.0, "test"),
            ],
        )
        outcomes.backfill_forward_returns(conn, through_date="2026-01-31")
        row = conn.execute(
            "SELECT exit_reason, managed_r, managed_mfe_r, hit_1r, hit_2r "
            "FROM outcomes WHERE horizon = 5"
        ).fetchone()
        assert row["exit_reason"] == "horizon_close"
        assert row["managed_r"] == 1.8  # (118 - 100) / 10
        assert row["managed_mfe_r"] == 2.0  # (120 - 100) / 10
        assert row["hit_1r"] == 1 and row["hit_2r"] == 1
    finally:
        conn.close()


def test_managed_exit_gap_through_stop_recorded_worse_than_minus_1r(tmp_path):
    # Entry=100, stop=95 (risk=5), but the fill session itself opens at 80 --
    # already gapped through the stop before the trade could be managed. The
    # honest r is far worse than -1R, not silently dropped or floored at -1R.
    conn = db.init_db(tmp_path / "manas.db")
    try:
        candidate = {
            "symbol": "ACME", "setup": "Near pivot", "readiness": 80, "grade": "A",
            "entry": 100.0, "stop": 95.0, "sector": "AUTO", "industry": "Auto",
            "evidence": [{"filter": "test", "value": "hit"}],
        }
        outcomes.persist_candidate_snapshot(conn, "2026-01-01", candidate)
        conn.executemany(
            "INSERT INTO daily_prices (symbol, trade_date, series, open, high, low, close, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("ACME", "2026-01-01", "EQ", 100.0, 100.0, 100.0, 100.0, "test"),
                ("ACME", "2026-01-02", "EQ", 80.0, 82.0, 78.0, 81.0, "test"),
                ("ACME", "2026-01-03", "EQ", 81.0, 83.0, 79.0, 82.0, "test"),
                ("ACME", "2026-01-04", "EQ", 82.0, 84.0, 80.0, 83.0, "test"),
                ("ACME", "2026-01-05", "EQ", 83.0, 85.0, 81.0, 84.0, "test"),
                ("ACME", "2026-01-06", "EQ", 84.0, 86.0, 82.0, 85.0, "test"),
            ],
        )
        outcomes.backfill_forward_returns(conn, through_date="2026-01-31")
        row = conn.execute(
            "SELECT entry_fill, exit_reason, managed_r FROM outcomes WHERE horizon = 5"
        ).fetchone()
        assert row["entry_fill"] == 80.0
        assert row["exit_reason"] == "gap_through_stop"
        # exit = 80 * (1 - 0.002) = 79.84 -> r = (79.84-100)/5 = -4.032
        assert row["managed_r"] < -1.0
        assert row["managed_r"] == -4.032
    finally:
        conn.close()


def test_outcomes_mfe_mae_null_when_window_incomplete(tmp_path):
    # W1.4: MFE/MAE are None when the forward window doesn't have enough bars
    # (same pending rule as forward_r). Only 2 bars after candidate_date ->
    # T+5 is pending and carries no excursion.
    conn = db.init_db(tmp_path / "manas.db")
    try:
        candidate = {
            "symbol": "ACME", "setup": "Near pivot", "readiness": 80, "grade": "A",
            "entry": 100.0, "stop": 95.0, "sector": "AUTO", "industry": "Auto",
            "evidence": [{"filter": "test", "value": "hit"}],
        }
        outcomes.persist_candidate_snapshot(conn, "2026-01-01", candidate)
        conn.executemany(
            "INSERT INTO daily_prices (symbol, trade_date, series, close, high, low, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                ("ACME", "2026-01-01", "EQ", 100.0, 100.0, 100.0, "test"),
                ("ACME", "2026-01-02", "EQ", 101.0, 102.0, 99.0, "test"),
                ("ACME", "2026-01-03", "EQ", 102.0, 103.0, 100.0, "test"),
            ],
        )
        outcomes.backfill_forward_returns(conn, through_date="2026-01-31")
        row = conn.execute(
            "SELECT mfe_r, mae_r, status FROM outcomes WHERE horizon = 5"
        ).fetchone()
        assert row["status"] == "pending"
        assert row["mfe_r"] is None
        assert row["mae_r"] is None
    finally:
        conn.close()


def test_outcomes_mfe_mae_adverse_only_when_never_rises_above_entry(tmp_path):
    # W1.4: a name that only goes down has MFE = 0 or negative (if no bar's
    # high exceeds entry), MAE negative. entry=100 stop=95 risk=5; every bar
    # stays under 100. Forward highs: 98,96,94,95,93 -> max 98 -> MFE=-0.4R.
    # Forward lows: 96,94,92,93,91 -> min 91 -> MAE=(91-100)/5=-1.8R.
    conn = db.init_db(tmp_path / "manas.db")
    try:
        candidate = {
            "symbol": "ACME", "setup": "Near pivot", "readiness": 80, "grade": "A",
            "entry": 100.0, "stop": 95.0, "sector": "AUTO", "industry": "Auto",
            "evidence": [{"filter": "test", "value": "hit"}],
        }
        outcomes.persist_candidate_snapshot(conn, "2026-01-01", candidate)
        conn.executemany(
            "INSERT INTO daily_prices (symbol, trade_date, series, close, high, low, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                ("ACME", "2026-01-01", "EQ", 100.0, 100.0, 100.0, "test"),
                ("ACME", "2026-01-02", "EQ", 97.0, 98.0, 96.0, "test"),
                ("ACME", "2026-01-03", "EQ", 95.0, 96.0, 94.0, "test"),
                ("ACME", "2026-01-04", "EQ", 93.0, 94.0, 92.0, "test"),
                ("ACME", "2026-01-05", "EQ", 94.0, 95.0, 93.0, "test"),
                ("ACME", "2026-01-06", "EQ", 92.0, 93.0, 91.0, "test"),
            ],
        )
        outcomes.backfill_forward_returns(conn, through_date="2026-01-31")
        row = conn.execute(
            "SELECT mfe_r, mae_r, status FROM outcomes WHERE horizon = 5"
        ).fetchone()
        assert row["status"] == "complete"
        assert row["mfe_r"] == -0.4  # (98 - 100) / 5
        assert row["mae_r"] == -1.8  # (91 - 100) / 5
    finally:
        conn.close()
