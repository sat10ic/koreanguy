import json

from fastapi.testclient import TestClient

from manas_os import db
from manas_os.api import app as api_app
from manas_os.scanner import outcomes


def test_portfolio_heat_open_risk_and_half_size_mode(tmp_path, monkeypatch):
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    try:
        api_app._ensure_journal_table(conn)
        outcomes.ensure_setup_decisions_schema(conn)
        conn.execute(
            "INSERT OR REPLACE INTO regime_snapshots (snapshot_date, market_mode) VALUES ('2026-06-30', 'RISK_ON')"
        )
        conn.executemany(
            "INSERT INTO journal_trades (trade_date, symbol, setup, entry, stop, exit, r_result, mistake_tags_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, '[]')",
            [
                ("2026-06-30", "ACME", "Pullback", 100, 95, None, None),
                ("2026-06-30", "BETA", "Breakout", 200, 190, None, None),
                ("2026-06-01", "L1", "Pullback", 100, 95, 95, -1.0),
                ("2026-06-02", "L2", "Pullback", 100, 95, 95, -1.0),
                ("2026-06-03", "L3", "Pullback", 100, 95, 95, -1.0),
            ],
        )
        conn.executemany(
            "INSERT OR REPLACE INTO setup_decisions "
            "(scan_date, symbol, decision, qty, snapshot_json) VALUES (?, ?, 'taken', ?, ?)",
            [
                ("2026-06-30", "ACME", 10, json.dumps({"sector": "PHARMA"})),
                ("2026-06-30", "BETA", 20, json.dumps({"sector": "BANKS"})),
            ],
        )
        conn.commit()
    finally:
        conn.close()

    orig_connect = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: orig_connect(db_path))
    client = TestClient(api_app.app)

    payload = client.get("/api/portfolio/heat").json()
    # ACME: (100-95)*10/1,000,000*100 = 0.005; BETA: (200-190)*20/1,000,000*100 = 0.02; sum = 0.025.
    assert payload["open_risk_pct"] == 0.025
    assert payload["rolling_10_avg_r"] == {"value": -1.0, "n": 3}
    assert payload["half_size_mode"] is False

    conn = db.connect(db_path)
    try:
        conn.executemany(
            "INSERT INTO journal_trades (trade_date, symbol, setup, entry, stop, exit, r_result, mistake_tags_json) "
            "VALUES (?, ?, 'Pullback', 100, 95, 97.5, -0.5, '[]')",
            [(f"2026-06-{day:02d}", f"L{day}") for day in range(4, 11)],
        )
        conn.commit()
    finally:
        conn.close()

    payload = client.get("/api/portfolio/heat").json()
    assert payload["rolling_10_avg_r"]["n"] == 10
    assert payload["rolling_10_avg_r"]["value"] == -0.65
    assert payload["half_size_mode"] is True
