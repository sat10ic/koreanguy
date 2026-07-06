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
