from datetime import date, timedelta

from fastapi.testclient import TestClient

from manas_os import db
from manas_os.api import app as api_app
from manas_os.scanner.candidates import ensure_refusals_schema
from manas_os.scanner.outcomes import ensure_setup_decisions_schema


def test_journal_visuals_refused_cohort_uses_last_20_sessions(tmp_path, monkeypatch):
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    try:
        ensure_refusals_schema(conn)
        ensure_setup_decisions_schema(conn)
        start = date(2026, 1, 1)
        for idx in range(25):
            scan_date = (start + timedelta(days=idx)).isoformat()
            for n in range(idx + 1):
                conn.execute(
                    "INSERT INTO refusals (scan_date, symbol, setup_family, failed_gate, reason, evidence_json) "
                    "VALUES (?, ?, 'vcp', 'risk', 'wide stop', '{}')",
                    (scan_date, f"SYM{idx:02d}{n:02d}"),
                )
        conn.commit()
    finally:
        conn.close()

    orig_connect = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: orig_connect(db_path))
    client = TestClient(api_app.app)

    res = client.get("/api/journal/visuals")
    assert res.status_code == 200
    payload = res.json()

    assert payload["cohort_counts"]["refused"] == sum(range(6, 26))


def test_journal_visuals_exposes_per_trade_mfe_mae(tmp_path, monkeypatch):
    # W1.5: /api/journal computes per-trade MFE/MAE in R over the holding
    # window from daily_prices (the Journal scatter reads trade.mfe_r/mae_r).
    # entry=100 stop=95 risk=5. Closed trade exit_date=2026-01-04. Forward highs
    # over [01-02,01-04]: 102,103,105 -> max 105 -> MFE=+1.0R. Lows: 99,97,96
    # -> min 96 -> MAE=-0.8R.
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    try:
        from manas_os.api.app import _ensure_journal_table
        _ensure_journal_table(conn)
        ensure_refusals_schema(conn)
        ensure_setup_decisions_schema(conn)
        conn.execute(
            "INSERT INTO journal_trades (trade_date, symbol, setup, entry, exit, stop, "
            "r_result, exit_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("2026-01-01", "ACME", "Near pivot", 100.0, 103.0, 95.0, 0.6, "2026-01-04"),
        )
        conn.executemany(
            "INSERT INTO daily_prices (symbol, trade_date, series, close, high, low, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                ("ACME", "2026-01-01", "EQ", 100.0, 100.0, 100.0, "test"),
                ("ACME", "2026-01-02", "EQ", 101.0, 102.0, 99.0, "test"),
                ("ACME", "2026-01-03", "EQ", 102.0, 103.0, 97.0, "test"),
                ("ACME", "2026-01-04", "EQ", 103.0, 105.0, 96.0, "test"),
                ("ACME", "2026-01-05", "EQ", 104.0, 106.0, 95.0, "test"),  # past exit_date, ignored
            ],
        )
        conn.commit()
    finally:
        conn.close()

    orig_connect = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: orig_connect(db_path))
    client = TestClient(api_app.app)

    res = client.get("/api/journal")
    assert res.status_code == 200
    payload = res.json()
    trade = payload["trades"][0]
    assert trade["mfe_r"] == 1.0  # (105 - 100) / 5, over [01-02, 01-04]
    assert trade["mae_r"] == -0.8  # (96 - 100) / 5


def test_journal_visuals_open_trade_uses_latest_price_for_excursion(tmp_path, monkeypatch):
    # W1.5: an open trade (exit_date NULL) computes excursion through the
    # latest available price date, not a fixed window.
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    try:
        from manas_os.api.app import _ensure_journal_table
        _ensure_journal_table(conn)
        ensure_refusals_schema(conn)
        ensure_setup_decisions_schema(conn)
        conn.execute(
            "INSERT INTO journal_trades (trade_date, symbol, setup, entry, stop) "
            "VALUES (?, ?, ?, ?, ?)",
            ("2026-01-01", "ACME", "Near pivot", 100.0, 95.0),
        )
        conn.executemany(
            "INSERT INTO daily_prices (symbol, trade_date, series, close, high, low, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                ("ACME", "2026-01-01", "EQ", 100.0, 100.0, 100.0, "test"),
                ("ACME", "2026-01-02", "EQ", 101.0, 102.0, 99.0, "test"),
                ("ACME", "2026-01-03", "EQ", 102.0, 103.0, 97.0, "test"),
            ],
        )
        conn.commit()
    finally:
        conn.close()

    orig_connect = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: orig_connect(db_path))
    client = TestClient(api_app.app)

    res = client.get("/api/journal")
    assert res.status_code == 200
    trade = res.json()["trades"][0]
    assert trade["mfe_r"] == 0.6  # (103 - 100) / 5
    assert trade["mae_r"] == -0.6  # (97 - 100) / 5
