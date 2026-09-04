"""Tests for the forward earnings calendar (EARNINGS_SEASON_HANDHOLD step 1)
and the widen-mapping wave (2026-07-18) on top of it.

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
        # constituents master -> surfaces as an unmapped row (match_method
        # 'unmapped'), never dropped, never guessed.
        "scrip_Code": "999999",
        "short_name": "UNKNOWNXYZ",
        "Long_Name": "Totally Unknown Company Pvt Ltd.",
        "meeting_date": "25 Oct 2026",
        "URL": "https://www.bseindia.com/y",
    },
    {
        # malformed date -> dropped silently (not an unresolved-name case,
        # there's no date to place it on the calendar).
        "scrip_Code": "500410",
        "short_name": "ACCLTD",
        "Long_Name": "ACC Ltd.",
        "meeting_date": "",
        "URL": "https://www.bseindia.com/z",
    },
]


def test_parse_bse_calendar_resolves_both_paths_and_surfaces_unmapped():
    rows, unresolved = earnings_calendar.parse_bse_calendar(_BSE_PAYLOAD)

    assert unresolved == 1
    # malformed-date row (4th) is the only one actually dropped -- 3 rows out
    # of 4 survive (2 mapped + 1 unmapped), not 2.
    assert len(rows) == 3

    by_symbol = {r["symbol"]: r for r in rows}
    assert by_symbol["ACC"]["meeting_date"] == "2026-10-23"
    assert by_symbol["ACC"]["match_method"] == earnings_calendar.MATCH_NAME_NORMALIZED
    assert by_symbol["3MINDIA"]["meeting_date"] == "2026-10-24"
    assert by_symbol["3MINDIA"]["match_method"] == earnings_calendar.MATCH_SYMBOL_DIRECT

    unmapped_symbol = f"{earnings_calendar.UNMAPPED_SYMBOL_PREFIX}999999"
    assert unmapped_symbol in by_symbol
    unmapped = by_symbol[unmapped_symbol]
    assert unmapped["match_method"] == earnings_calendar.MATCH_UNMAPPED
    assert unmapped["meeting_date"] == "2026-10-25"
    assert unmapped["scrip_code"] == "999999"
    assert unmapped["company_name"] == "Totally Unknown Company Pvt Ltd."


def test_resolve_symbol_name_normalized_then_symbol_direct_then_none():
    master = {"ACC": "ACC", "3M INDIA": "3MINDIA"}
    # name_normalized fallback: short_name doesn't match anything known.
    assert earnings_calendar.resolve_symbol("ACC Ltd.", "NOTASYMBOL", master) == (
        "ACC", earnings_calendar.MATCH_NAME_NORMALIZED,
    )
    # symbol_direct fast path (default known_symbols = set(master.values())
    # when the caller doesn't pass a widened set).
    assert earnings_calendar.resolve_symbol("garbled name", "3MINDIA", master) == (
        "3MINDIA", earnings_calendar.MATCH_SYMBOL_DIRECT,
    )
    # neither path matches -> never a guess.
    assert earnings_calendar.resolve_symbol("Nobody Ltd.", "NOBODY", master) == (None, None)


def test_resolve_symbol_known_symbols_widens_matching_beyond_the_400_master():
    """The core fix: BSE's short_name is frequently already the exact NSE
    symbol for large/mid-cap names entirely absent from the NIFTYMIDSML400
    (mid/small-cap only) master -- e.g. HDFCBANK. Without a widened
    known_symbols set, that row is unresolved; with one (as `run()` builds
    from load_known_symbols(conn) | set(master.values())), it resolves via
    symbol_direct."""
    master = {"ACC": "ACC"}  # HDFCBANK deliberately absent -- a Nifty50 name
    # would never appear in the mid/small-cap-only constituents CSV.
    assert earnings_calendar.resolve_symbol("HDFC Bank Ltd", "HDFCBANK", master) == (None, None)

    widened = earnings_calendar.resolve_symbol(
        "HDFC Bank Ltd", "HDFCBANK", master, known_symbols={"HDFCBANK", "ACC"},
    )
    assert widened == ("HDFCBANK", earnings_calendar.MATCH_SYMBOL_DIRECT)


def test_resolve_symbol_override_wins_over_symbol_direct():
    """overrides is checked before known_symbols, so a hand-verified
    correction always wins even if the (wrong) short_name would otherwise
    resolve via symbol_direct."""
    master: dict[str, str] = {}
    overrides = {earnings_calendar._normalize_company_name("Ambiguous Co Ltd"): "TRUESYM"}
    got = earnings_calendar.resolve_symbol(
        "Ambiguous Co Ltd", "WRONGSYM", master,
        known_symbols={"WRONGSYM"},  # would resolve to WRONGSYM if override didn't win
        overrides=overrides,
    )
    assert got == ("TRUESYM", earnings_calendar.MATCH_OVERRIDE)


def test_symbol_overrides_dict_is_wired_into_parse_bse_calendar():
    """End-to-end (still pure/no-DB): a row that resolves via neither
    symbol_direct nor name_normalized, but IS covered by a caller-supplied
    overrides dict, surfaces as match_method='override' -- proving the dict
    is actually wired into the parser, not just resolve_symbol in isolation."""
    payload = [{
        "scrip_Code": "111111",
        "short_name": "WEIRDCODE",
        "Long_Name": "Confusingly Renamed Co Ltd",
        "meeting_date": "01 Nov 2026",
    }]
    overrides = {
        earnings_calendar._normalize_company_name("Confusingly Renamed Co Ltd"): "REALNSESYM",
    }
    rows, unresolved = earnings_calendar.parse_bse_calendar(
        payload, master={}, known_symbols=set(), overrides=overrides,
    )
    assert unresolved == 0
    assert len(rows) == 1
    assert rows[0]["symbol"] == "REALNSESYM"
    assert rows[0]["match_method"] == earnings_calendar.MATCH_OVERRIDE


def test_load_symbol_master_reads_real_constituents_file():
    master = earnings_calendar.load_symbol_master()
    assert master  # the real niftymidsml400_constituents.csv ships in the repo
    assert master.get("ACC") == "ACC"


def test_load_known_symbols_unions_daily_prices_and_universe(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        conn.execute(
            "INSERT INTO daily_prices (symbol, trade_date, close) VALUES ('FOO', '2026-01-01', 100)"
        )
        conn.execute(
            "INSERT INTO universe (symbol, as_of_date, is_tradeable) VALUES ('BAR', '2026-01-01', 1)"
        )
        conn.commit()
        known = earnings_calendar.load_known_symbols(conn)
        assert known == {"FOO", "BAR"}
    finally:
        conn.close()


def test_load_known_symbols_empty_when_no_price_history(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        assert earnings_calendar.load_known_symbols(conn) == set()
    finally:
        conn.close()


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
        "match_method": earnings_calendar.MATCH_NSE_DIRECT, "scrip_code": None,
    }]


def test_run_ingests_bse_rows_including_unmapped_and_is_idempotent_on_rerun(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        def bse_fetcher():
            return _BSE_PAYLOAD

        def nse_fetcher():
            raise PermissionError("NSE event-calendar blocked (401) — cookie wall")

        written = earnings_calendar.run(conn, "2026-10-01", bse_fetcher=bse_fetcher, nse_fetcher=nse_fetcher)
        # 2 mapped (ACC, 3MINDIA) + 1 unmapped (UNKNOWNXYZ, now surfaced
        # instead of dropped) = 3. The malformed-date row stays dropped.
        assert written == 3

        rows = conn.execute(
            "SELECT symbol, meeting_date, source, match_method FROM earnings_calendar ORDER BY symbol"
        ).fetchall()
        got = {(r["symbol"], r["meeting_date"], r["source"], r["match_method"]) for r in rows}
        assert got == {
            ("ACC", "2026-10-23", "bse_board_meetings", earnings_calendar.MATCH_NAME_NORMALIZED),
            ("3MINDIA", "2026-10-24", "bse_board_meetings", earnings_calendar.MATCH_SYMBOL_DIRECT),
            (f"{earnings_calendar.UNMAPPED_SYMBOL_PREFIX}999999", "2026-10-25",
             "bse_board_meetings", earnings_calendar.MATCH_UNMAPPED),
        }

        # Re-run must upsert, not duplicate (idempotent on symbol/meeting_date/source,
        # including the synthetic unmapped symbol).
        written_again = earnings_calendar.run(conn, "2026-10-02", bse_fetcher=bse_fetcher, nse_fetcher=nse_fetcher)
        assert written_again == 3
        count = conn.execute("SELECT COUNT(*) FROM earnings_calendar").fetchone()[0]
        assert count == 3

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
    assert body["unmapped"] == []
    assert "reason" in body and body["reason"]


def test_endpoint_empty_state_when_no_rows_in_window(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    client = _client(db_path, monkeypatch)
    resp = client.get("/api/earnings/upcoming", params={"days": 7, "date": "2026-01-01"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is False
    assert body["unmapped"] == []
    assert "reason" in body and body["reason"]


def test_endpoint_returns_grouped_days_with_chips_and_surfaces_unmapped(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        def bse_fetcher():
            return _BSE_PAYLOAD

        def nse_fetcher():
            raise PermissionError("blocked")

        earnings_calendar.run(conn, "2026-10-01", bse_fetcher=bse_fetcher, nse_fetcher=nse_fetcher)

        # Chip sources: universe (in_universe, avg_turnover_cr), scan_candidates
        # (rs, delivery_pct), features_daily (adr_pct), daily_prices (52w-high
        # distance + 5d pre-earnings drift) -- all cheaply joinable existing
        # tables. ACC gets the full set (clears the A_WATCH bar); 3MINDIA gets
        # none of it (not in universe -> C_IGNORE, no price history -> honest
        # nulls on the two derived price-context fields).
        conn.execute(
            "INSERT INTO universe (symbol, as_of_date, is_tradeable, avg_turnover_cr) "
            "VALUES ('ACC', '2026-10-01', 1, 8.0)"
        )
        conn.execute(
            "INSERT INTO scan_candidates (scan_date, symbol, setup, rs, delivery_pct) "
            "VALUES ('2026-10-01', 'ACC', 'ep', 92.5, 61.0)"
        )
        conn.execute(
            "INSERT INTO features_daily (symbol, trade_date, feature_json) "
            "VALUES ('ACC', '2026-10-01', '{\"adr20_pct\": 3.4}')"
        )
        acc_bars = [
            ("2026-09-24", 90, 92), ("2026-09-25", 92, 93), ("2026-09-28", 95, 96),
            ("2026-09-29", 97, 98), ("2026-09-30", 99, 100), ("2026-10-01", 100, 101),
        ]
        for trade_date, close, high in acc_bars:
            conn.execute(
                "INSERT INTO daily_prices (symbol, trade_date, series, close, high) "
                "VALUES ('ACC', ?, 'EQ', ?, ?)",
                (trade_date, close, high),
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
    # Only the 2 mapped-symbol dates -- the unmapped row (10-25) is excluded
    # from `days` and surfaced in `unmapped` instead.
    assert [d["date"] for d in body["days"]] == ["2026-10-23", "2026-10-24"]

    acc_day = body["days"][0]
    # ACC: RS 92.5 >= EP_PREP_RS_FLOOR (70) and avg_turnover_cr 8.0 >=
    # EP_PREP_TURNOVER_FLOOR_CR (5.0) and in_universe -> A_WATCH. 52w-high
    # distance = (1 - 100/101)*100 = 0.99; 5d drift = (100-90)/90*100 = 11.11
    # (bars run 2026-09-24..2026-10-01 inclusive, 6 sessions).
    assert acc_day["symbols"] == [{
        "symbol": "ACC", "meeting_date": "2026-10-23", "purpose": "Results",
        "source": "bse_board_meetings", "match_method": earnings_calendar.MATCH_NAME_NORMALIZED,
        "in_universe": True, "rs": 92.5, "adr_pct": 3.4, "delivery_pct": 61.0,
        "avg_turnover_cr": 8.0, "pct_off_52w_high": 0.99,
        "pre_earnings_drift_5d_pct": 11.11, "prep_class": "A_WATCH",
    }]

    threem_day = body["days"][1]
    assert threem_day["symbols"][0]["symbol"] == "3MINDIA"
    assert threem_day["symbols"][0]["match_method"] == earnings_calendar.MATCH_SYMBOL_DIRECT
    assert threem_day["symbols"][0]["in_universe"] is False
    assert threem_day["symbols"][0]["rs"] is None
    assert threem_day["symbols"][0]["avg_turnover_cr"] is None
    assert threem_day["symbols"][0]["pct_off_52w_high"] is None
    assert threem_day["symbols"][0]["pre_earnings_drift_5d_pct"] is None
    # Not tradeable -> C_IGNORE regardless of any other field.
    assert threem_day["symbols"][0]["prep_class"] == "C_IGNORE"

    assert body["unmapped"] == [{
        "company_name": "Totally Unknown Company Pvt Ltd.",
        "scrip_code": "999999",
        "meeting_date": "2026-10-25",
        "purpose": "Results",
        "source": "bse_board_meetings",
    }]


def _seed_earnings_row(conn, symbol, meeting_date, source="bse_board_meetings"):
    conn.execute(
        "INSERT INTO earnings_calendar (symbol, meeting_date, purpose, source, match_method) "
        "VALUES (?, ?, 'Results', ?, ?)",
        (symbol, meeting_date, source, earnings_calendar.MATCH_SYMBOL_DIRECT),
    )


def test_earnings_prep_class_boundaries(tmp_path, monkeypatch):
    """EP-PREP prep_class (EARNINGS_SEASON_HANDHOLD step 3): A_WATCH needs
    in_universe AND rs>=EP_PREP_RS_FLOOR AND (avg_turnover_cr unknown OR
    >=EP_PREP_TURNOVER_FLOOR_CR); RS below floor (while liquid/tradeable)
    drops to B_CONTEXT; an EXPLICIT low avg_turnover_cr also drops to
    B_CONTEXT even with strong RS; not tradeable at all is always C_IGNORE
    regardless of how strong RS/turnover look.

    GGGNOTURN covers the real-world case (verified live 2026-07-19):
    avg_turnover_cr is None because sources/classify_universe.py never
    persists it, NOT because the symbol is illiquid -- a None must NOT be
    treated the same as a known-too-low number, or A_WATCH would never fire
    in production. See _ep_prep_class's own docstring for the full story.
    """
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        as_of = "2027-01-01"
        meeting_date = "2027-01-05"
        for sym in ("AAAWATCH", "BBBWEAKRS", "CCCILLIQ", "DDDNOTUNI", "GGGNOTURN"):
            _seed_earnings_row(conn, sym, meeting_date)

        rows = [
            # symbol,      in_universe, avg_turnover_cr, rs
            ("AAAWATCH", 1, 6.0, 75.0),      # clears both floors -> A_WATCH
            ("BBBWEAKRS", 1, 10.0, 50.0),    # liquid but RS below floor -> B_CONTEXT
            ("CCCILLIQ", 1, 2.0, 80.0),      # strong RS but EXPLICITLY illiquid -> B_CONTEXT
            ("DDDNOTUNI", 0, 20.0, 95.0),    # not tradeable at all -> C_IGNORE
            ("GGGNOTURN", 1, None, 90.0),    # tradeable, RS clears floor, turnover UNKNOWN -> A_WATCH
        ]
        for sym, is_tradeable, turnover, rs in rows:
            conn.execute(
                "INSERT INTO universe (symbol, as_of_date, is_tradeable, avg_turnover_cr) "
                "VALUES (?, ?, ?, ?)",
                (sym, as_of, is_tradeable, turnover),
            )
            conn.execute(
                "INSERT INTO scan_candidates (scan_date, symbol, setup, rs) VALUES (?, ?, 'ep', ?)",
                (as_of, sym, rs),
            )
        conn.commit()
    finally:
        conn.close()

    client = _client(db_path, monkeypatch)
    resp = client.get("/api/earnings/upcoming", params={"days": 10, "date": as_of})
    body = resp.json()
    assert body["available"] is True
    by_symbol = {s["symbol"]: s for s in body["days"][0]["symbols"]}

    assert by_symbol["AAAWATCH"]["prep_class"] == "A_WATCH"
    assert by_symbol["BBBWEAKRS"]["prep_class"] == "B_CONTEXT"
    assert by_symbol["CCCILLIQ"]["prep_class"] == "B_CONTEXT"
    assert by_symbol["DDDNOTUNI"]["prep_class"] == "C_IGNORE"
    assert by_symbol["GGGNOTURN"]["avg_turnover_cr"] is None
    assert by_symbol["GGGNOTURN"]["prep_class"] == "A_WATCH"


def test_earnings_rs_falls_back_to_stock_industry_rs_when_scan_candidates_empty(tmp_path, monkeypatch):
    """rs (EP-PREP): scan_candidates.rs is primary (a symbol the nightly EP
    scanner has actually touched); stock_industry_rs (the persisted ChartsMaze
    sector/industry RS export, broader coverage) fills the gap for reporters
    the scanner hasn't scored yet -- this is the 'stock_rs latest' half of the
    spec's 'rs (screener_hits/stock_rs latest)' join."""
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        as_of = "2027-01-01"
        _seed_earnings_row(conn, "FFFALLBACK", "2027-01-06")
        conn.execute(
            "INSERT INTO universe (symbol, as_of_date, is_tradeable, avg_turnover_cr) "
            "VALUES ('FFFALLBACK', ?, 1, 7.0)",
            (as_of,),
        )
        # No scan_candidates row at all for FFFALLBACK -- only the broader
        # stock_industry_rs snapshot carries its RS.
        conn.execute(
            "INSERT INTO stock_industry_rs (snapshot_date, ticker, industry, rs) "
            "VALUES (?, 'FFFALLBACK', 'Some Industry', 85.0)",
            (as_of,),
        )
        conn.commit()
    finally:
        conn.close()

    client = _client(db_path, monkeypatch)
    resp = client.get("/api/earnings/upcoming", params={"days": 10, "date": as_of})
    body = resp.json()
    row = body["days"][0]["symbols"][0]
    assert row["symbol"] == "FFFALLBACK"
    assert row["rs"] == 85.0
    # RS 85 >= floor and turnover 7.0 >= floor and in_universe -> A_WATCH,
    # proving the fallback RS actually feeds prep_class, not just display.
    assert row["prep_class"] == "A_WATCH"


def test_earnings_prep_null_honesty_when_no_supporting_data(tmp_path, monkeypatch):
    """A reporter that's in_universe but has NO scan_candidates/stock_industry_rs/
    features_daily/daily_prices/avg_turnover_cr row anywhere must come back
    with honest nulls on every derived field -- never a fabricated 0 or a
    crash -- and prep_class must degrade to B_CONTEXT (tradeable, but nothing
    is known well enough to call it A-list)."""
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        as_of = "2027-01-01"
        _seed_earnings_row(conn, "EEENODATA", "2027-01-07")
        # in_universe True but avg_turnover_cr left NULL (column omitted).
        conn.execute(
            "INSERT INTO universe (symbol, as_of_date, is_tradeable) VALUES ('EEENODATA', ?, 1)",
            (as_of,),
        )
        conn.commit()
    finally:
        conn.close()

    client = _client(db_path, monkeypatch)
    resp = client.get("/api/earnings/upcoming", params={"days": 10, "date": as_of})
    assert resp.status_code == 200
    body = resp.json()
    row = body["days"][0]["symbols"][0]
    assert row["symbol"] == "EEENODATA"
    assert row["in_universe"] is True
    assert row["rs"] is None
    assert row["adr_pct"] is None
    assert row["delivery_pct"] is None
    assert row["avg_turnover_cr"] is None
    assert row["pct_off_52w_high"] is None
    assert row["pre_earnings_drift_5d_pct"] is None
    assert row["prep_class"] == "B_CONTEXT"
