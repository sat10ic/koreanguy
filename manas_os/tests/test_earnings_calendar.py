"""Tests for the forward earnings calendar (EARNINGS_SEASON_HANDHOLD step 1).

Fixture-based throughout: a canned BSE JSON payload is parsed and ingested
into a scratch DB, then read back through the /api/earnings/upcoming
endpoint. No live network calls anywhere in this file.
"""
from fastapi.testclient import TestClient

from manas_os import db
from manas_os.api import app as api_app
from manas_os.sources import earnings_calendar


def _client(db_path, monkeypatch):
    orig_connect = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: orig_connect(db_path))
    return TestClient(api_app.app)


# A canned BSE Corpforthresults/w-shaped payload (see sources/earnings_calendar.py
# docstring for the real field names, confirmed via the unofficial BSE API client).
_BSE_PAYLOAD = [
    {
        # resolves via normalized company-name match (short_name deliberately
        # does NOT equal the NSE symbol, forcing the name-lookup path).
        "scrip_Code": "500410",
        "short_name": "ACCLTD",
        "Long_Name": "ACC Ltd.",
        "meeting_date": "23 Oct 2026",
        "URL": "https://www.bseindia.com/stock-share-price/acc/acc/500410/",
    },
    {
        # resolves via the short_name fast-path: Long_Name is deliberately
        # garbled (would NOT normalize-match the master), but short_name is
        # exactly the NSE symbol.
        "scrip_Code": "600001",
        "short_name": "3MINDIA",
        "Long_Name": "3M INDIA SOMETHING ELSE ENTIRELY",
        "meeting_date": "24 Oct 2026",
        "URL": "https://www.bseindia.com/x",
    },
    {
        # unresolvable: neither short_name nor company name matches the
        # constituents master -> must be skipped, not guessed.
        "scrip_Code": "999999",
        "short_name": "UNKNOWNXYZ",
        "Long_Name": "Totally Unknown Company Pvt Ltd.",
        "meeting_date": "25 Oct 2026",
        "URL": "https://www.bseindia.com/y",
    },
    {
        # malformed date -> dropped silently (not an unresolved-name case).
        "scrip_Code": "500410",
        "short_name": "ACCLTD",
        "Long_Name": "ACC Ltd.",
        "meeting_date": "",
        "URL": "https://www.bseindia.com/z",
    },
]


def test_parse_bse_calendar_resolves_both_paths_and_skips_unknown():
    rows, unresolved = earnings_calendar.parse_bse_calendar(_BSE_PAYLOAD)

    assert unresolved == 1
    got = {(r["symbol"], r["meeting_date"], r["purpose"]) for r in rows}
    assert ("ACC", "2026-10-23", "Results") in got
    assert ("3MINDIA", "2026-10-24", "Results") in got
    assert len(rows) == 2  # unknown company + malformed date both dropped


def test_resolve_symbol_prefers_short_name_fast_path():
    master = {"ACC": "ACC", "3M INDIA": "3MINDIA"}
    assert earnings_calendar.resolve_symbol("garbled name", "3MINDIA", master) == "3MINDIA"
    assert earnings_calendar.resolve_symbol("ACC Ltd.", "NOTASYMBOL", master) == "ACC"
    assert earnings_calendar.resolve_symbol("Nobody Ltd.", "NOBODY", master) is None


def test_load_symbol_master_reads_real_constituents_file():
    master = earnings_calendar.load_symbol_master()
    assert master  # the real niftymidsml400_constituents.csv ships in the repo
    assert master.get("ACC") == "ACC"


def test_parse_nse_calendar_flags_results_purpose_from_free_text():
    raw = [{
        "bm_symbol": "SIYSIL",
        "bm_date": "30-Oct-2026",
        "bm_purpose": "to consider and approve the Quarterly Unaudited Financial results",
        "bm_desc": "Board Meeting Intimation",
        "sm_name": "Siyaram Silk Mills Limited",
    }]
    rows = earnings_calendar.parse_nse_calendar(raw)
    assert rows == [{
        "symbol": "SIYSIL", "meeting_date": "2026-10-30", "purpose": "Results",
        "source": earnings_calendar.SOURCE_NSE, "company_name": "Siyaram Silk Mills Limited",
    }]


def test_run_ingests_bse_rows_and_is_idempotent_on_rerun(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        def bse_fetcher():
            return _BSE_PAYLOAD

        def nse_fetcher():
            raise PermissionError("NSE event-calendar blocked (401) — cookie wall")

        written = earnings_calendar.run(conn, "2026-10-01", bse_fetcher=bse_fetcher, nse_fetcher=nse_fetcher)
        assert written == 2

        rows = conn.execute(
            "SELECT symbol, meeting_date, source FROM earnings_calendar ORDER BY symbol"
        ).fetchall()
        assert {(r["symbol"], r["meeting_date"], r["source"]) for r in rows} == {
            ("ACC", "2026-10-23", "bse_board_meetings"),
            ("3MINDIA", "2026-10-24", "bse_board_meetings"),
        }

        # Re-run must upsert, not duplicate (idempotent on symbol/meeting_date/source).
        written_again = earnings_calendar.run(conn, "2026-10-02", bse_fetcher=bse_fetcher, nse_fetcher=nse_fetcher)
        assert written_again == 2
        count = conn.execute("SELECT COUNT(*) FROM earnings_calendar").fetchone()[0]
        assert count == 2

        run_row = conn.execute(
            "SELECT status FROM pipeline_runs WHERE stage='ingest_earnings_calendar' "
            "ORDER BY run_id DESC LIMIT 1"
        ).fetchone()
        assert run_row["status"] == "ok"
    finally:
        conn.close()


def test_run_logs_skip_when_bse_fetch_fails_and_nse_also_fails(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        def failing_bse():
            raise ConnectionError("simulated network failure")

        def failing_nse():
            raise PermissionError("simulated cookie-wall block")

        written = earnings_calendar.run(conn, "2026-10-01", bse_fetcher=failing_bse, nse_fetcher=failing_nse)
        assert written == 0

        row = conn.execute(
            "SELECT status, detail FROM pipeline_runs WHERE stage='ingest_earnings_calendar'"
        ).fetchone()
        assert row["status"] == "skip"
        assert "simulated network failure" in row["detail"]
    finally:
        conn.close()


def test_endpoint_empty_state_when_table_missing(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    # Drop the table init_db just created, to exercise the "never ingested" path.
    conn = db.connect(db_path)
    conn.execute("DROP TABLE IF EXISTS earnings_calendar")
    conn.commit()
    conn.close()

    client = _client(db_path, monkeypatch)
    resp = client.get("/api/earnings/upcoming", params={"days": 7})
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is False
    assert body["days"] == []
    assert "reason" in body and body["reason"]


def test_endpoint_empty_state_when_no_rows_in_window(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    client = _client(db_path, monkeypatch)
    resp = client.get("/api/earnings/upcoming", params={"days": 7, "date": "2026-01-01"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is False
    assert "reason" in body and body["reason"]


def test_endpoint_returns_grouped_days_with_chips(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        def bse_fetcher():
            return _BSE_PAYLOAD

        def nse_fetcher():
            raise PermissionError("blocked")

        earnings_calendar.run(conn, "2026-10-01", bse_fetcher=bse_fetcher, nse_fetcher=nse_fetcher)

        # Chip sources: universe (in_universe), scan_candidates (rs, delivery_pct),
        # features_daily (adr_pct) -- all cheaply joinable existing tables.
        conn.execute(
            "INSERT INTO universe (symbol, as_of_date, is_tradeable) VALUES ('ACC', '2026-10-01', 1)"
        )
        conn.execute(
            "INSERT INTO scan_candidates (scan_date, symbol, setup, rs, delivery_pct) "
            "VALUES ('2026-10-01', 'ACC', 'ep', 92.5, 61.0)"
        )
        conn.execute(
            "INSERT INTO features_daily (symbol, trade_date, feature_json) "
            "VALUES ('ACC', '2026-10-01', '{\"adr20_pct\": 3.4}')"
        )
        conn.commit()
    finally:
        conn.close()

    client = _client(db_path, monkeypatch)
    resp = client.get("/api/earnings/upcoming", params={"days": 30, "date": "2026-10-01"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is True
    assert body["as_of"] == "2026-10-01"
    assert [d["date"] for d in body["days"]] == ["2026-10-23", "2026-10-24"]

    acc_day = body["days"][0]
    assert acc_day["symbols"] == [{
        "symbol": "ACC", "meeting_date": "2026-10-23", "purpose": "Results",
        "source": "bse_board_meetings", "in_universe": True, "rs": 92.5,
        "adr_pct": 3.4, "delivery_pct": 61.0,
    }]

    threem_day = body["days"][1]
    assert threem_day["symbols"][0]["symbol"] == "3MINDIA"
    assert threem_day["symbols"][0]["in_universe"] is False
    assert threem_day["symbols"][0]["rs"] is None
