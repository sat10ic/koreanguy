from fastapi.testclient import TestClient

from manas_os import db
from manas_os.api import app as api_app
from manas_os.scanner import candidates

from manas_os.tests.conftest import insert_price_ramp, seed_confluent_symbol, seed_regime


def _insert_prices(conn, symbol="ACME", n=210):
    # 210 real-dated bars: enough for the 200SMA trend-template gate.
    insert_price_ramp(conn, symbol=symbol, n=n)


def _insert_wide_stop_prices(conn, symbol="WIDE", n=210):
    # Deep daily lows (low = 80% of close): every candidate stop lands far
    # outside the 8% cap, so the risk gate must refuse with a named reason.
    insert_price_ramp(conn, symbol=symbol, n=n, low_frac=0.80)


def test_ep_gap_uses_pre_gap_box_height_projection():
    bars = []
    for i in range(20):
        bars.append({"open": 100, "high": 105, "low": 95, "close": 100, "prev_close": 100})
    bars.append({"open": 106, "high": 110, "low": 104, "close": 108, "prev_close": 100})
    target = candidates.ep_box_projection(bars, 107.0)
    assert target == {
        "target": 117.0,
        "method": "pre-gap 20-session box height (10.00)",
        "synthetic": False,
    }


def test_discovery_watch_is_not_added_to_candidate_pool(monkeypatch):
    monkeypatch.setattr(candidates.discovery, "build_bucket", lambda *_: [{
        "symbol": "COIL", "classification": "WATCH",
        "archetypes": ["anticipation_watch"], "metrics": {},
    }])
    assert candidates.discovery_bucket_map(None, "2026-07-16") == {}


def test_scanner_run_persists_candidates_and_logs_pipeline(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        _insert_prices(conn)
        seed_confluent_symbol(conn, scan_date="2026-06-30")
        result = candidates.run(conn, "2026-06-30")

        assert result["status"] == "ok"
        assert result["rows"] == 1
        row = conn.execute(
            "SELECT symbol, setup, readiness, grade, evidence_json "
            "FROM scan_candidates WHERE scan_date = '2026-06-30'"
        ).fetchone()
        assert row["symbol"] == "ACME"
        assert row["readiness"] > 0
        assert row["grade"] in {"A+", "A", "B", "C"}
        assert "delivery>=60" in row["evidence_json"]

        run = conn.execute(
            "SELECT status, rows_affected FROM pipeline_runs WHERE stage = 'scan_candidates'"
        ).fetchone()
        assert run["status"] == "ok"
        assert run["rows_affected"] == 1
    finally:
        conn.close()


def test_setups_endpoint_reads_persisted_scanner_rows(tmp_path, monkeypatch):
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    try:
        _insert_prices(conn)
        seed_confluent_symbol(conn, scan_date="2026-06-30")
        candidates.run(conn, "2026-06-30")
    finally:
        conn.close()

    orig_connect = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: orig_connect(db_path))
    client = TestClient(api_app.app)

    res = client.get("/api/setups", params={"date": "2026-06-30"})
    assert res.status_code == 200
    payload = res.json()
    assert payload["available"] is True
    assert payload["source"] == "scan_candidates"
    assert payload["as_of"] == "2026-06-30"
    assert payload["candidates"][0]["symbol"] == "ACME"


def test_growth_clamp_marks_untrusted_and_negative_sign_format(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        _insert_prices(conn)
        seed_confluent_symbol(conn, scan_date="2026-06-30")
        conn.execute(
            "UPDATE symbol_quality SET eps_yoy = 55250, eps_qoq = -5 WHERE symbol = 'ACME'"
        )
        result = candidates.scan_candidates(conn, "2026-06-30")
        card = result["candidates"][0]
        growth = card["score_breakdown"]["growth"]

        assert growth["eps_yoy"] == {"value": 55250.0, "untrusted": True}
        assert "EPS YoY" not in {e["filter"] for e in card["evidence"]}
        assert candidates.format_growth_value(-5) == "-5%"
        assert candidates.format_growth_value(55250) == "N/A (data error)"
    finally:
        conn.close()


def test_wide_stop_candidate_is_dropped_with_named_reason(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        _insert_wide_stop_prices(conn)
        seed_confluent_symbol(conn, symbol="WIDE", scan_date="2026-06-30")
        result = candidates.scan_candidates(conn, "2026-06-30")
        assert result["candidates"] == []
        refusal = result["dropped"][0]
        assert refusal["symbol"] == "WIDE"
        assert refusal["failed_gate"] == "risk"
        assert "stop" in refusal["reason"] and "cap" in refusal["reason"]
        # and it landed in the refusal ledger (T1.5)
        row = conn.execute("SELECT failed_gate, reason FROM refusals WHERE symbol='WIDE'").fetchone()
        assert row["failed_gate"] == "risk" and "cap" in row["reason"]
    finally:
        conn.close()


def test_persisted_candidates_have_rr_and_suggested_qty(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        _insert_prices(conn)
        seed_confluent_symbol(conn, scan_date="2026-06-30")
        result = candidates.run(conn, "2026-06-30")
        assert result["rows"] == 1
        row = conn.execute(
            "SELECT rr, suggested_qty FROM scan_candidates WHERE scan_date = '2026-06-30'"
        ).fetchone()
        durable = conn.execute(
            "SELECT rr, suggested_qty, source_payload_json FROM candidates WHERE candidate_date = '2026-06-30'"
        ).fetchone()
        assert row["rr"] is not None
        assert row["suggested_qty"] > 0
        assert durable["rr"] == row["rr"]
        assert durable["suggested_qty"] == row["suggested_qty"]
        assert '"suggested_qty"' in durable["source_payload_json"]
    finally:
        conn.close()


def test_load_persisted_candidates_attaches_circuit_state_from_bands(tmp_path):
    # W0.2 focus field: circuit_state is one writer (server-side, from
    # circuit_bands). The field is always present on the payload; null when no
    # band exists for the symbol, the latest band_pct as-of scan_date otherwise.
    conn = db.init_db(tmp_path / "manas.db")
    try:
        _insert_prices(conn)
        seed_confluent_symbol(conn, scan_date="2026-06-30")
        candidates.run(conn, "2026-06-30")
        # Seed a band on/before scan_date and a newer one after it.
        conn.executemany(
            "INSERT INTO circuit_bands (symbol, as_of, band_pct) VALUES (?, ?, ?)",
            [("ACME", "2026-06-29", 10.0), ("ACME", "2026-07-01", 5.0)],
        )
        conn.commit()
        result = candidates.load_persisted_candidates(conn, "2026-06-30")
        assert result["available"] is True
        card = result["candidates"][0]
        # Latest band as-of scan_date is the 06-29 row (10.0); the 07-01 row is
        # future-dated relative to scan_date and must be ignored.
        assert card["symbol"] == "ACME"
        assert card["circuit_state"] == 10.0
    finally:
        conn.close()


def test_load_persisted_candidates_circuit_state_null_without_band(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        _insert_prices(conn)
        seed_confluent_symbol(conn, scan_date="2026-06-30")
        candidates.run(conn, "2026-06-30")
        result = candidates.load_persisted_candidates(conn, "2026-06-30")
        card = result["candidates"][0]
        assert "circuit_state" in card
        assert card["circuit_state"] is None
    finally:
        conn.close()


# --------------------------------------------------------------------------
# WAVE_M M2+M3 (user order 2026-07-11, "the filter IS the defect"):
# discovery.build_bucket joins the live pool; RS floor, 52wH nearness, and
# regime family-kill become scored objections instead of hard drops.
# --------------------------------------------------------------------------

def test_no_trade_regime_still_hard_refuses_everything(tmp_path):
    """NO_TRADE is the one LOCKED hard regime refusal — 0 cards stays 0."""
    conn = db.init_db(tmp_path / "manas.db")
    try:
        _insert_prices(conn)
        seed_confluent_symbol(conn, scan_date="2026-06-30")
        seed_regime(conn, scan_date="2026-06-30", mode="NO_TRADE")
        result = candidates.scan_candidates(conn, "2026-06-30")
        assert result["candidates"] == []
        assert result["refused_count"] >= 1
        refusal = next(r for r in result["dropped"] if r["symbol"] == "ACME")
        assert refusal["failed_gate"] == "regime"
    finally:
        conn.close()


def test_regime_family_kill_is_scored_objection_not_a_refusal(tmp_path):
    """A DEFENSIVE tape only allows 'catalyst' — a plain momentum-family name
    used to be hard-refused there; M3 makes it a scored objection instead:
    the name survives, grade-capped at B, with a named 'regime_family'
    objection riding in its evidence."""
    conn = db.init_db(tmp_path / "manas.db")
    try:
        _insert_prices(conn)
        seed_confluent_symbol(conn, scan_date="2026-06-30")
        seed_regime(conn, scan_date="2026-06-30", mode="DEFENSIVE")
        result = candidates.scan_candidates(conn, "2026-06-30")
        assert not any(r["symbol"] == "ACME" for r in result["dropped"])
        card = next(c for c in result["candidates"] if c["symbol"] == "ACME")
        objections = card.get("objections") or []
        assert any(o["code"] == "regime_family" for o in objections)
        assert card.get("grade_cap") == "B"
    finally:
        conn.close()


def test_rs_floor_below_80_is_admitted_with_objection(tmp_path):
    """RS 40 (below the 80 floor) no longer hard-refuses at trend-template —
    the name is admitted with a named 'rs_floor' objection and a capped
    grade, never silently dropped."""
    conn = db.init_db(tmp_path / "manas.db")
    try:
        _insert_prices(conn, symbol="LOWRS")
        seed_confluent_symbol(conn, symbol="LOWRS", scan_date="2026-06-30")
        conn.execute(
            "UPDATE screener_hits SET rs_rating = 40 WHERE symbol = 'LOWRS' AND trade_date = '2026-06-30'"
        )
        conn.commit()
        result = candidates.scan_candidates(conn, "2026-06-30")
        assert not any(r["symbol"] == "LOWRS" for r in result["dropped"])
        card = next(c for c in result["candidates"] if c["symbol"] == "LOWRS")
        objections = card.get("objections") or []
        assert any(o["code"] == "rs_floor" for o in objections)
        assert card.get("grade_cap") == "B"
    finally:
        conn.close()


def test_discovery_bucket_joins_live_pool_with_archetype_evidence(tmp_path):
    """WAVE_M M2: a name only build_bucket tags (no ChartsMaze confluence, no
    detector_shortlist 252d-history hit) still enters the live pool and, if
    it survives the cascade, carries its archetype(s) as evidence."""
    conn = db.init_db(tmp_path / "manas.db")
    try:
        # 210-bar ramp (cascade-eligible) but with NO confluence/screener_hits
        # seed at all — under the pre-M2 pool this symbol is invisible.
        _insert_prices(conn, symbol="BUCKETONLY")
        seed_regime(conn, scan_date="2026-06-30", mode="RISK_ON")
        result = candidates.scan_candidates(conn, "2026-06-30")
        assert result.get("discovery_bucket_size", 0) > 0
        assert result.get("pool_size", 0) >= result.get("pool_size_pre_discovery", 0)
        seen = {c["symbol"] for c in result["candidates"]} | {r["symbol"] for r in result["dropped"]}
        assert "BUCKETONLY" in seen
    finally:
        conn.close()


def test_detector_shortlist_cap_drops_weakest_not_alphabetically_last(tmp_path):
    """Bug fix 2026-07-11 (SKYGOLD/RAIN discovery defect): when more names
    qualify (close within 15% of 252d high) than the cap, detector_shortlist
    must keep the STRONGEST-nearness names and drop the weakest ones -- never
    truncate by ticker letter. Seed many early-alphabet symbols at the bare
    0.85 nearness floor and one late-alphabet symbol (ZZZLATE) at 0.99
    nearness; with limit below the qualifying count, ZZZLATE must survive
    and the weakest early-alphabet name must not."""
    conn = db.init_db(tmp_path / "manas.db")
    try:
        scan_date = "2026-06-30"
        rows = []
        n_weak = 20
        for i in range(n_weak):
            sym = f"AAA{i:02d}"  # alphabetically first, weakest nearness
            rows.append((sym, scan_date, "EQ", 84.0, 100.0, 84.0, 85.5,
                         85.0, 500000, 100, 62.0, "test"))
        # strongest nearness, alphabetically LAST -- must survive a tight cap
        rows.append(("ZZZLATE", scan_date, "EQ", 98.0, 100.0, 98.0, 99.0,
                     99.0, 500000, 100, 62.0, "test"))
        conn.executemany(
            "INSERT OR REPLACE INTO daily_prices (symbol, trade_date, series, open, high, low, "
            "close, prev_close, volume, delivery_qty, delivery_pct, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()

        total_qualifying = n_weak + 1
        assert total_qualifying > 5  # sanity: cap below this actually bites
        shortlist = candidates.detector_shortlist(conn, scan_date, limit=5)

        assert "ZZZLATE" in shortlist
        assert len(shortlist) == 5
        # under the old `ORDER BY p.symbol` behavior a limit=5 cap would keep
        # only AAA00..AAA04 and drop ZZZLATE entirely -- assert that is NOT
        # what happened.
        assert shortlist != [f"AAA{i:02d}" for i in range(5)]
    finally:
        conn.close()
