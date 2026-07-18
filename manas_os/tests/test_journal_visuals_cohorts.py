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


def test_journal_includes_imported_zerodha_trade_with_inclusive_stats(tmp_path, monkeypatch):
    # A zerodha-import row has no stop, so r_result is NULL -- it must still
    # show up in /api/journal (not silently dropped), read as win/loss off
    # its own broker_realized_pnl (not "open"), and count toward win_pct.
    # avg_r/expectancy_r stay R-only, with an honest caption on how many of
    # the closed trades that R figure actually covers.
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    try:
        from manas_os.api.app import _ensure_journal_table
        _ensure_journal_table(conn)
        # One ordinary tool-logged trade with a real stop -> has r_result.
        conn.execute(
            "INSERT INTO journal_trades (trade_date, symbol, setup, entry, exit, stop, "
            "r_result) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("2026-01-01", "ACME", "breakout", 100.0, 115.0, 95.0, 1.5),
        )
        # One imported zerodha row: no stop -> r_result NULL, but it closed
        # with a broker-reported realized P&L.
        conn.execute(
            "INSERT INTO journal_trades (trade_date, exit_date, symbol, setup, entry, exit, "
            "qty, r_result, source, import_key, broker_realized_pnl, broker_return_pct, "
            "broker_direction, broker_holding_days) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?)",
            (
                "2026-02-01", "2026-02-11", "GROWW", "Zerodha FIFO", 100.0, 112.55, 10.0,
                "zerodha_import", "zerodha:test-key-1", 125.5, 12.55, "long", 10,
            ),
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
    trades = {t["symbol"]: t for t in payload["trades"]}

    imported = trades["GROWW"]
    assert imported["imported"] is True
    assert imported["source"] == "zerodha_import"
    assert imported["r_result"] is None
    assert imported["broker_realized_pnl"] == 125.5
    assert imported["broker_direction"] == "long"
    assert imported["broker_holding_days"] == 10
    # Must read as a win off the broker P&L, never as "open" -- the trade
    # closed, it just has no stop-derived R.
    assert imported["result"] == "win"

    tool_logged = trades["ACME"]
    assert tool_logged["imported"] is False
    assert tool_logged["result"] == "win"

    stats = payload["stats"]
    assert stats["count"] == 2
    assert stats["closed_count"] == 2  # both trades have a determined outcome
    assert stats["r_count"] == 1  # only the tool-logged trade has an R
    # win_pct is inclusive of the imported trade: both are wins -> 100%.
    assert stats["win_pct"] == 100.0
    # avg_r/expectancy_r stay R-only (computed over the 1 R-bearing trade).
    assert stats["avg_r"] == 1.5
    assert stats["realized_pnl_total"] == 125.5
    assert stats["r_stats_caption"] is not None
    assert "1 of 2" in stats["r_stats_caption"]


def test_journal_imported_holdings_excludes_negative_qty_and_joins_latest_price(tmp_path, monkeypatch):
    # broker_open_lots can carry negative-qty rows (a sell matched against a
    # buy the tradebook window never saw -- a pre-window FIFO artifact). Only
    # positive-qty lots are real open holdings and should surface.
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    try:
        from manas_os.api.app import _ensure_journal_table, _ensure_broker_open_lots_table
        _ensure_journal_table(conn)
        _ensure_broker_open_lots_table(conn)
        conn.executemany(
            "INSERT INTO broker_open_lots (symbol, qty, avg_cost, first_buy_date, import_key) "
            "VALUES (?, ?, ?, ?, ?)",
            [
                ("ACME", 10.0, 100.0, "2026-01-01", "zerodha-open:key-pos"),
                ("NEGART", -5.0, 50.0, "2026-01-01", "zerodha-open:key-neg"),
            ],
        )
        conn.execute(
            "INSERT INTO daily_prices (symbol, trade_date, series, close, high, low, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("ACME", "2026-02-01", "EQ", 110.0, 111.0, 109.0, "test"),
        )
        conn.commit()
    finally:
        conn.close()

    orig_connect = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: orig_connect(db_path))
    client = TestClient(api_app.app)

    res = client.get("/api/journal")
    assert res.status_code == 200
    holdings = res.json()["imported_holdings"]

    symbols = [h["symbol"] for h in holdings]
    assert "ACME" in symbols
    assert "NEGART" not in symbols  # negative-qty artifact excluded

    acme = next(h for h in holdings if h["symbol"] == "ACME")
    assert acme["qty"] == 10.0
    assert acme["avg_cost"] == 100.0
    assert acme["last_close"] == 110.0
    assert acme["unrealized_pct"] == 10.0  # (110-100)/100 * 100
    assert acme["unrealized_pnl"] == 100.0  # (110-100) * 10
