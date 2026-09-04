from manas_os import db
from manas_os.scanner import candidates as cand
from manas_os.sources import fundamentals
from manas_os.tests.conftest import AS_OF, insert_price_ramp, seed_confluent_symbol


def _rows(symbol: str, as_of: str):
    return [
        {
            "symbol": symbol,
            "report_date": "2026-03-31",
            "as_of": as_of,
            "period": "quarterly",
            "revenue": 1000.0,
            "operating_income": 180.0,
            "net_income": 120.0,
            "eps": 12.0,
            "operating_margin": 18.0,
            "sales_yoy": 20.0,
            "eps_yoy": 25.0,
            "opm_yoy": 2.0,
            "roe": 18.5,
            "pe_ratio": 22.0,
            "debt_to_equity": 35.0,
            "market_cap_cr": 50000.0,
            "source": "test",
        },
        {
            "symbol": symbol,
            "report_date": "2025-12-31",
            "as_of": as_of,
            "period": "quarterly",
            "revenue": 900.0,
            "operating_income": 150.0,
            "net_income": 100.0,
            "eps": 10.0,
            "operating_margin": 16.67,
            "sales_yoy": None,
            "eps_yoy": None,
            "opm_yoy": None,
            "roe": 18.5,
            "pe_ratio": 22.0,
            "debt_to_equity": 35.0,
            "market_cap_cr": 50000.0,
            "source": "test",
        },
    ]


def test_fundamentals_run_populates_history_and_logs_pipeline(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        result = fundamentals.run(
            conn,
            AS_OF,
            symbols=["TCS", "INFY"],
            fetcher=lambda symbol, as_of: _rows(symbol, as_of),
        )

        assert result == {"status": "ok", "rows": 4, "symbols": 2, "failures": []}
        rows = conn.execute(
            "SELECT symbol, report_date, as_of, eps_yoy, roe, pe_ratio, debt_to_equity, market_cap_cr "
            "FROM symbol_fundamentals ORDER BY symbol, report_date DESC"
        ).fetchall()
        assert len(rows) == 4
        assert rows[0]["symbol"] == "INFY"
        assert rows[0]["report_date"] == "2026-03-31"
        assert rows[0]["as_of"] == AS_OF
        assert rows[0]["eps_yoy"] == 25.0
        assert rows[0]["roe"] == 18.5
        assert rows[0]["pe_ratio"] == 22.0
        assert rows[0]["debt_to_equity"] == 35.0
        assert rows[0]["market_cap_cr"] == 50000.0

        latest = fundamentals.latest_snapshot(conn, "tcs", AS_OF)
        assert latest["report_date"] == "2026-03-31"
        run = conn.execute(
            "SELECT status, rows_affected, detail FROM pipeline_runs WHERE stage = ?",
            (fundamentals.STAGE,),
        ).fetchone()
        assert run["status"] == "ok"
        assert run["rows_affected"] == 4
        assert "symbols=2 rows=4 failures=0" in run["detail"]
    finally:
        conn.close()


def test_fundamentals_run_skips_when_no_symbols_available(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        result = fundamentals.run(conn, AS_OF, fetcher=lambda _symbol, _as_of: [])

        assert result == {"status": "skip", "rows": 0, "symbols": 0}
        run = conn.execute(
            "SELECT status, rows_affected, detail FROM pipeline_runs WHERE stage = ?",
            (fundamentals.STAGE,),
        ).fetchone()
        assert run["status"] == "skip"
        assert run["rows_affected"] == 0
        assert run["detail"] == "no symbols available"
    finally:
        conn.close()


def test_growth_for_prefers_fundamentals_and_falls_back_when_missing(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        fundamentals.ensure_schema(conn)
        fundamentals.upsert(conn, _rows("FG0", AS_OF))
        conn.commit()

        growth = fundamentals.growth_for(
            conn,
            "FG0",
            AS_OF,
            {"eps_yoy": -40.0, "eps_qoq": -20.0, "sales_yoy": -10.0, "opm_yoy": -5.0},
        )
        assert growth["eps_yoy"] == 25.0
        assert growth["eps_qoq"] == 20.0
        assert growth["sales_yoy"] == 20.0
        assert growth["opm_yoy"] == 2.0

        fallback = {"eps_yoy": 4.0, "eps_qoq": 3.0, "sales_yoy": 2.0, "opm_yoy": 1.0}
        assert fundamentals.growth_for(conn, "NOPE", AS_OF, fallback) == fallback
    finally:
        conn.close()


def test_scan_candidates_still_runs_without_symbol_fundamentals_rows(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        insert_price_ramp(conn, symbol="NF0", n=210, start=100)
        seed_confluent_symbol(conn, symbol="NF0", scan_date=AS_OF)
        conn.execute(
            "INSERT OR REPLACE INTO regime_snapshots (snapshot_date, market_mode) VALUES (?, 'RISK_ON')",
            (AS_OF,),
        )
        fundamentals.ensure_schema(conn)

        result = cand.run(conn, AS_OF)

        assert result["status"] == "ok"
        assert result["rows"] > 0
        assert conn.execute("SELECT COUNT(*) FROM symbol_fundamentals").fetchone()[0] == 0
    finally:
        conn.close()


def test_scan_candidates_prefers_symbol_fundamentals_growth(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        insert_price_ramp(conn, symbol="FG1", n=210, start=100)
        seed_confluent_symbol(conn, symbol="FG1", scan_date=AS_OF)
        conn.execute(
            "INSERT OR REPLACE INTO symbol_quality "
            "(trade_date, symbol, market_cap_cr, asm_stage, eps_qoq, eps_yoy, sales_yoy, opm_yoy, is_fno, exchange) "
            "VALUES (?, 'FG1', 5000, NULL, -90, -80, -70, -60, 1, 'NSE')",
            (AS_OF,),
        )
        fundamentals.ensure_schema(conn)
        rows = _rows("FG1", AS_OF)
        rows[0]["eps_yoy"] = 120.0
        rows[0]["sales_yoy"] = 55.0
        rows[0]["opm_yoy"] = 8.0
        rows[0]["eps"] = 22.0
        rows[1]["eps"] = 20.0
        fundamentals.upsert(conn, rows)
        conn.commit()

        result = cand.scan_candidates(conn, AS_OF)

        assert result["available"] is True
        candidate = result["candidates"][0]
        growth = candidate["score_breakdown"]["growth"]
        assert growth["eps_yoy"]["value"] == 120.0
        assert growth["eps_qoq"]["value"] == 10.0
        assert growth["sales_yoy"]["value"] == 55.0
        assert growth["opm_yoy"]["value"] == 8.0
        assert any(item["filter"] == "EPS YoY" and item["value"] == "+120%" for item in candidate["evidence"])
    finally:
        conn.close()
