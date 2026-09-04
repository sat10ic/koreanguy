from fastapi.testclient import TestClient
import json

from manas_os import db
from manas_os.api import app as api_app
from manas_os.tests.conftest import AS_OF, insert_price_ramp, seed_confluent_symbol, trading_dates


def _client(db_path, monkeypatch):
    orig_connect = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: orig_connect(db_path))
    monkeypatch.setattr(api_app, "_today", lambda: AS_OF)
    return TestClient(api_app.app)


def _open_trade(conn, symbol="ACME", setup="Pullback", entry=115.0, stop=105.0):
    cur = conn.execute(
        "INSERT INTO journal_trades (trade_date, symbol, setup, entry, stop, exit, mistake_tags_json) "
        "VALUES (?, ?, ?, ?, ?, NULL, '[]')",
        (AS_OF, symbol, setup, entry, stop),
    )
    conn.commit()
    return cur.lastrowid


def _seed_position_db(db_path, symbol="ACME"):
    conn = db.init_db(db_path)
    try:
        insert_price_ramp(conn, symbol=symbol, n=210)
        seed_confluent_symbol(conn, symbol=symbol, scan_date=AS_OF)
        return _open_trade(conn, symbol=symbol)
    finally:
        conn.close()


def test_position_coach_open_trade_returns_verdict(tmp_path, monkeypatch):
    db_path = tmp_path / "manas.db"
    trade_id = _seed_position_db(db_path)
    client = _client(db_path, monkeypatch)

    res = client.get(f"/api/positions/{trade_id}/coach", params={"date": AS_OF})
    assert res.status_code == 200
    payload = res.json()

    assert payload["available"] is True
    assert payload["trade_id"] == trade_id
    assert payload["symbol"] == "ACME"
    assert payload["verdict"] in {"HOLD", "TRIM", "EXIT"}
    assert {"phase", "r", "trail_stop", "plain_instruction", "why", "fired", "exit_now"} <= set(payload)


def test_position_coach_two_strike_overrides_to_exit(tmp_path, monkeypatch):
    db_path = tmp_path / "manas.db"
    trade_id = _seed_position_db(db_path)
    dates = trading_dates(210, AS_OF)
    conn = db.connect(db_path)
    try:
        conn.execute(
            "UPDATE daily_prices SET open=121, high=122, low=78, close=80, volume=900000 "
            "WHERE symbol='ACME' AND trade_date=?",
            (dates[-2],),
        )
        conn.execute(
            "UPDATE daily_prices SET open=82, high=83, low=76, close=79, volume=1200000 "
            "WHERE symbol='ACME' AND trade_date=?",
            (dates[-1],),
        )
        conn.commit()
    finally:
        conn.close()
    client = _client(db_path, monkeypatch)

    res = client.get(f"/api/positions/{trade_id}/coach", params={"date": AS_OF})
    assert res.status_code == 200
    payload = res.json()

    assert payload["verdict"] == "EXIT"
    assert payload["exit_now"] is True
    assert len(payload["fired"]) >= 2


def test_position_coach_missing_or_closed_returns_unavailable(tmp_path, monkeypatch):
    db_path = tmp_path / "manas.db"
    trade_id = _seed_position_db(db_path)
    conn = db.connect(db_path)
    try:
        conn.execute("UPDATE journal_trades SET exit=120, r_result=1.0 WHERE trade_id=?", (trade_id,))
        conn.commit()
    finally:
        conn.close()
    client = _client(db_path, monkeypatch)

    closed = client.get(f"/api/positions/{trade_id}/coach", params={"date": AS_OF}).json()
    missing = client.get("/api/positions/999999/coach", params={"date": AS_OF}).json()

    assert closed == {"available": False, "reason": "no open position with that id"}
    assert missing == {"available": False, "reason": "no open position with that id"}


def test_close_hold_trade_without_tag_returns_guard_and_does_not_write(tmp_path, monkeypatch):
    db_path = tmp_path / "manas.db"
    trade_id = _seed_position_db(db_path)
    client = _client(db_path, monkeypatch)

    res = client.post(f"/api/journal/trades/{trade_id}/close", json={"exit_price": 119})
    assert res.status_code == 409
    payload = res.json()
    assert payload["guard"] is True
    assert payload["reasons"] == ["fear", "need-cash", "thesis-change", "other"]

    conn = db.connect(db_path)
    try:
        row = conn.execute("SELECT exit, r_result FROM journal_trades WHERE trade_id=?", (trade_id,)).fetchone()
        assert row["exit"] is None
        assert row["r_result"] is None
    finally:
        conn.close()


def test_close_hold_trade_with_tag_writes_close_and_appends_tag(tmp_path, monkeypatch):
    db_path = tmp_path / "manas.db"
    trade_id = _seed_position_db(db_path)
    client = _client(db_path, monkeypatch)

    res = client.post(
        f"/api/journal/trades/{trade_id}/close",
        json={"exit_price": 119, "mistake_tag": "fear"},
    )
    assert res.status_code == 200
    assert res.json()["ok"] is True

    conn = db.connect(db_path)
    try:
        row = conn.execute(
            "SELECT exit, r_result, mistake_tags_json FROM journal_trades WHERE trade_id=?",
            (trade_id,),
        ).fetchone()
        assert row["exit"] == 119
        assert row["r_result"] == 0.4
        assert "fear" in json.loads(row["mistake_tags_json"])
    finally:
        conn.close()


def test_close_exit_phase_trade_without_tag_writes_close(tmp_path, monkeypatch):
    db_path = tmp_path / "manas.db"
    trade_id = _seed_position_db(db_path)
    dates = trading_dates(210, AS_OF)
    conn = db.connect(db_path)
    try:
        conn.execute(
            "UPDATE daily_prices SET open=121, high=122, low=78, close=80, volume=900000 "
            "WHERE symbol='ACME' AND trade_date=?",
            (dates[-2],),
        )
        conn.execute(
            "UPDATE daily_prices SET open=82, high=83, low=76, close=79, volume=1200000 "
            "WHERE symbol='ACME' AND trade_date=?",
            (dates[-1],),
        )
        conn.commit()
    finally:
        conn.close()


def test_overdue_exit_banner_after_two_sessions_and_close_clears_flag(tmp_path, monkeypatch):
    db_path = tmp_path / "manas.db"
    trade_id = _seed_position_db(db_path)
    dates = trading_dates(210, AS_OF)
    down_dates = dates[-4:]
    conn = db.connect(db_path)
    try:
        for idx, d in enumerate(down_dates):
            conn.execute(
                "UPDATE daily_prices SET open=?, high=?, low=?, close=?, volume=? "
                "WHERE symbol='ACME' AND trade_date=?",
                (122 - idx, 123 - idx, 78 - idx, 80 - idx, 900000 + idx * 150000, d),
            )
        conn.commit()
    finally:
        conn.close()
    client = _client(db_path, monkeypatch)

    first = client.get(f"/api/positions/{trade_id}/coach", params={"date": down_dates[1]}).json()
    second = client.get(f"/api/positions/{trade_id}/coach", params={"date": down_dates[2]}).json()
    third = client.get(f"/api/positions/{trade_id}/coach", params={"date": down_dates[3]}).json()

    assert first["exit_now"] is True
    assert "banner" not in first
    assert "banner" not in second
    assert third["banner"] == "OVERDUE EXIT - flagged 2 sessions ago, still open"

    close = client.post(f"/api/journal/trades/{trade_id}/close", json={"exit_price": 77})
    assert close.status_code == 200
    conn = db.connect(db_path)
    try:
        row = conn.execute(
            "SELECT first_exit_flag_date FROM journal_trades WHERE trade_id=?",
            (trade_id,),
        ).fetchone()
        assert row["first_exit_flag_date"] is None
    finally:
        conn.close()
    client = _client(db_path, monkeypatch)

    # a closed trade cannot be closed again
    res = client.post(f"/api/journal/trades/{trade_id}/close", json={"exit_price": 79})
    assert res.status_code == 404

    conn = db.connect(db_path)
    try:
        row = conn.execute("SELECT exit, r_result FROM journal_trades WHERE trade_id=?", (trade_id,)).fetchone()
        assert row["exit"] == 77
        assert row["r_result"] == -3.8
    finally:
        conn.close()
