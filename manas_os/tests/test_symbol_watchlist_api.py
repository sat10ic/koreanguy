from fastapi.testclient import TestClient

from manas_os import db
from manas_os.api import app as api_app

from manas_os.tests.conftest import seed_confluent_symbol


from manas_os.tests.conftest import insert_price_ramp


def _insert_prices(conn, symbol="ACME", n=210):
    # 210 real-dated bars (200SMA computable); varied delivery for rvol/read paths.
    insert_price_ramp(conn, symbol=symbol, n=n, delivery=lambda i: 45.0 + (i % 20))


def test_symbol_timing_and_ohlc_contract(tmp_path, monkeypatch):
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    try:
        _insert_prices(conn)
    finally:
        conn.close()

    orig_connect = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: orig_connect(db_path))
    client = TestClient(api_app.app)

    timing = client.get("/api/symbol/ACME/timing", params={"date": "2026-06-30"})
    assert timing.status_code == 200
    t = timing.json()
    assert t["available"] is True
    assert t["symbol"] == "ACME"
    assert t["as_of"] == "2026-06-30"
    assert t["rvol"] is not None
    # shallow-ramp fixture: entry = 20-day pivot high + buffer, stop = 20-day low.
    # Assert the CONTRACT (sane geometry), not brittle magic numbers.
    assert t["entry"] is not None and t["stop"] is not None
    assert t["stop"] < t["entry"]
    stop_pct = (t["entry"] - t["stop"]) / t["entry"] * 100.0
    assert 1.0 <= stop_pct <= 8.0  # within the LOCKED stop band
    assert "price is" in t["read"]

    ohlc = client.get("/api/symbol/ACME/ohlc", params={"date": "2026-06-30", "n": 25})
    assert ohlc.status_code == 200
    payload = ohlc.json()
    assert payload["available"] is True
    assert payload["symbol"] == "ACME"
    assert payload["as_of"] == "2026-06-30"
    assert len(payload["candles"]) == 25
    assert {"date", "open", "high", "low", "close", "volume", "ema10", "ema15", "ema21", "ema50"} <= set(
        payload["candles"][-1]
    )
    assert "trail" in payload and "stage" in payload and "signals" in payload
    assert "pine_ports" in payload and "moving_average_rs" in payload["pine_ports"]


def test_watchlist_add_list_delete_contract(tmp_path, monkeypatch):
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    try:
        _insert_prices(conn)
    finally:
        conn.close()

    orig_connect = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: orig_connect(db_path))
    client = TestClient(api_app.app)

    add = client.post("/api/watchlist", json={"symbol": "acme", "note": "near pivot"})
    assert add.status_code == 200
    assert add.json() == {"ok": True, "symbol": "ACME"}

    listed = client.get("/api/watchlist", params={"date": "2026-06-30"})
    assert listed.status_code == 200
    payload = listed.json()
    assert payload["available"] is True
    assert payload["as_of"] == "2026-06-30"
    assert len(payload["items"]) == 1
    assert payload["items"][0]["symbol"] == "ACME"
    assert payload["items"][0]["note"] == "near pivot"
    assert payload["items"][0]["adr"] is not None
    assert payload["items"][0]["timing"]["available"] is True

    deleted = client.delete("/api/watchlist/ACME")
    assert deleted.status_code == 200
    assert deleted.json() == {"ok": True, "symbol": "ACME", "deleted": 1}
    assert client.get("/api/watchlist").json()["items"] == []


def test_setups_endpoint_returns_named_evidence_candidates(tmp_path, monkeypatch):
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    try:
        _insert_prices(conn)
        seed_confluent_symbol(conn, scan_date="2026-06-30")
    finally:
        conn.close()

    orig_connect = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: orig_connect(db_path))
    client = TestClient(api_app.app)

    res = client.get("/api/setups", params={"date": "2026-06-30"})
    assert res.status_code == 200
    payload = res.json()
    assert payload["available"] is True
    assert payload["as_of"] == "2026-06-30"
    assert len(payload["candidates"]) == 1
    candidate = payload["candidates"][0]
    assert candidate["symbol"] == "ACME"
    assert candidate["grade"] in {"A+", "A", "B", "C"}
    assert candidate["readiness"] > 0
    assert candidate["evidence"]
    assert all({"filter", "value"} <= set(e) for e in candidate["evidence"])
    assert "read" in candidate and candidate["read"]


def test_journal_add_and_stats_contract(tmp_path, monkeypatch):
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    conn.close()

    orig_connect = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: orig_connect(db_path))
    client = TestClient(api_app.app)

    first = client.post(
        "/api/journal",
        json={
            "trade_date": "2026-01-10",
            "symbol": "ACME",
            "setup": "Pullback",
            "entry": 100,
            "exit": 110,
            "stop": 95,
            "mistake_tags": [],
            "notes": "clean",
        },
    )
    assert first.status_code == 200
    assert first.json()["r_result"] == 2.0

    second = client.post(
        "/api/journal",
        json={
            "trade_date": "2026-01-11",
            "symbol": "BETA",
            "setup": "Breakout",
            "entry": 200,
            "exit": 190,
            "stop": 190,
            "mistake_tags": ["chased"],
        },
    )
    assert second.status_code == 200
    assert second.json()["r_result"] == -1.0

    res = client.get("/api/journal")
    assert res.status_code == 200
    payload = res.json()
    assert payload["available"] is True
    assert payload["stats"]["count"] == 2
    assert payload["stats"]["win_pct"] == 50.0
    assert payload["stats"]["avg_r"] == 0.5
    assert payload["stats"]["expectancy_r"] == 0.5
    assert payload["stats"]["top_mistake"] == "chased"
    assert [t["symbol"] for t in payload["trades"]] == ["BETA", "ACME"]

    trade_id = first.json()["trade_id"]
    updated = client.put(
        f"/api/journal/{trade_id}",
        json={
            "trade_date": "2026-01-12",
            "symbol": "ACME",
            "setup": "Pullback",
            "entry": 100,
            "exit": 115,
            "stop": 95,
            "mistake_tags": ["early-entry"],
            "notes": "edited",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["r_result"] == 3.0

    after_edit = client.get("/api/journal").json()
    assert after_edit["stats"]["count"] == 2
    assert after_edit["stats"]["avg_r"] == 1.0
    assert after_edit["trades"][0]["trade_date"] == "2026-01-12"
    assert after_edit["trades"][0]["mistake_tags"] == ["early-entry"]

    deleted = client.delete(f"/api/journal/{trade_id}")
    assert deleted.status_code == 200
    assert deleted.json() == {"ok": True, "trade_id": trade_id, "deleted": 1}
    after_delete = client.get("/api/journal").json()
    assert after_delete["stats"]["count"] == 1
    assert [t["symbol"] for t in after_delete["trades"]] == ["BETA"]
