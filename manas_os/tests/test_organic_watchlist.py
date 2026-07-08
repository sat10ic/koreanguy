from fastapi.testclient import TestClient

from manas_os import db
from manas_os.api import app as api_app
from manas_os.tests.conftest import AS_OF, insert_price_ramp, seed_confluent_symbol


def test_organic_watchlist_active_positions_include_open_r_and_days_held(tmp_path, monkeypatch):
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    try:
        insert_price_ramp(conn, symbol="ACME", n=210)
        seed_confluent_symbol(conn, symbol="ACME", scan_date=AS_OF)
        conn.execute(
            "INSERT INTO journal_trades (trade_date, symbol, setup, entry, stop, exit, mistake_tags_json) "
            "VALUES (?, 'ACME', 'Pullback', 115.0, 105.0, NULL, '[]')",
            (AS_OF,),
        )
        conn.commit()
    finally:
        conn.close()

    orig_connect = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: orig_connect(db_path))
    monkeypatch.setattr(api_app, "_today", lambda: AS_OF)
    client = TestClient(api_app.app)

    res = client.get("/api/watchlist/organic")
    assert res.status_code == 200
    payload = res.json()

    assert payload["active_positions"]
    assert "open_r" in payload["active_positions"][0]
    assert "days_held" in payload["active_positions"][0]


def test_position_lifecycle_carries_per_session_r_and_phase_bands():
    # W2.3: the lifecycle river needs a per-session series with phase derived
    # from R (r<1 INITIATION, <2 TREND, else EXTENSION). entry=100 stop=95
    # -> risk=5. Hand-computed phases inline.
    from datetime import date, timedelta
    from manas_os.api.app import _position_lifecycle
    import sqlite3
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE daily_prices (symbol TEXT, trade_date TEXT, series TEXT, "
        "close REAL, source TEXT)"
    )
    d0 = date(2026, 1, 1)
    # entry day + 4 forward sessions; closes 100,101,103,106,108.
    # risk=5 -> R = 0.0, 0.2, 0.6, 1.2, 1.6 -> INITIATION,INITIATION,INITIATION,TREND,TREND
    closes = [100.0, 101.0, 103.0, 106.0, 108.0]
    rows = [("ACME", (d0 + timedelta(days=i)).isoformat(), "EQ", c, "test") for i, c in enumerate(closes)]
    conn.executemany("INSERT INTO daily_prices VALUES (?,?,?,?,?)", rows)
    series = _position_lifecycle(conn, "ACME", "2026-01-01", "2026-01-05", 100.0, 95.0)
    assert [p["r"] for p in series] == [0.0, 0.2, 0.6, 1.2, 1.6]
    assert [p["phase"] for p in series] == ["INITIATION", "INITIATION", "INITIATION", "TREND", "TREND"]


def test_position_lifecycle_empty_when_stop_invalid():
    from manas_os.api.app import _position_lifecycle
    import sqlite3
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE daily_prices (symbol TEXT, trade_date TEXT, series TEXT, close REAL, source TEXT)")
    # stop >= entry -> risk <= 0 -> empty series, no division by zero.
    assert _position_lifecycle(conn, "ACME", "2026-01-01", "2026-01-05", 100.0, 100.0) == []
    assert _position_lifecycle(conn, "ACME", "2026-01-01", "2026-01-05", 100.0, 105.0) == []


def test_organic_watchlist_active_positions_include_lifecycle(tmp_path, monkeypatch):
    # W2.3: the active position payload carries a lifecycle series the coach
    # card expand renders.
    from datetime import date, timedelta
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    try:
        insert_price_ramp(conn, symbol="ACME", n=210)
        seed_confluent_symbol(conn, symbol="ACME", scan_date=AS_OF)
        conn.execute(
            "INSERT INTO journal_trades (trade_date, symbol, setup, entry, stop, exit, mistake_tags_json) "
            "VALUES (?, 'ACME', 'Pullback', 115.0, 105.0, NULL, '[]')",
            (AS_OF,),
        )
        conn.commit()
    finally:
        conn.close()

    orig_connect = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: orig_connect(db_path))
    monkeypatch.setattr(api_app, "_today", lambda: AS_OF)
    client = TestClient(api_app.app)

    res = client.get("/api/watchlist/organic")
    assert res.status_code == 200
    position = res.json()["active_positions"][0]
    assert "lifecycle" in position
    assert isinstance(position["lifecycle"], list)
    if position["lifecycle"]:
        first = position["lifecycle"][0]
        assert {"date", "r", "phase"}.issubset(first.keys())
