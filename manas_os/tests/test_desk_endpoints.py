import base64
import json
import os
import re
import time
from datetime import datetime

from fastapi.testclient import TestClient

from manas_os import db
from manas_os.agents import lessons
from manas_os.api import app as api_app
from manas_os.scanner import candidates as scanner_candidates
from manas_os.tests.conftest import insert_price_ramp, trading_dates


AS_OF = "2026-06-30"
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


def _client(db_path, monkeypatch):
    orig_connect = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: orig_connect(db_path))
    return TestClient(api_app.app)


def test_trader_profile_onboarding_accepts_the_desk_payload(tmp_path, monkeypatch):
    """The first-run modal historically omits ``paper_mode``.

    Profile creation is a compatibility boundary: adding a new server-side
    setting must not turn the existing onboarding submission into HTTP 422.
    """
    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    client = _client(db_path, monkeypatch)

    response = client.put(
        "/api/trader-profile",
        json={
            "account_capital": 1_000_000,
            "experience_mode": "LEARNING",
            "profile_confirmed_at": "2026-07-14T09:30:00+05:30",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["account_capital"] == 1_000_000
    assert body["experience_mode"] == "LEARNING"
    assert body["paper_mode"] == 1
    assert body["profile_confirmed_at"]


def test_desk_chart_serves_png_and_404s_when_absent(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    chart_dir = tmp_path / "data" / "agent_charts" / AS_OF
    chart_dir.mkdir(parents=True)
    (chart_dir / "AAA_daily.png").write_bytes(PNG_1X1)

    client = _client(db_path, monkeypatch)
    ok = client.get("/api/desk/chart", params={"date": AS_OF, "symbol": "AAA", "tf": "daily"})
    assert ok.status_code == 200
    assert ok.headers["content-type"] == "image/png"
    assert ok.content == PNG_1X1

    missing = client.get("/api/desk/chart", params={"date": AS_OF, "symbol": "AAA", "tf": "weekly"})
    assert missing.status_code == 404
    assert missing.json() == {"available": False, "date": AS_OF, "symbol": "AAA", "tf": "weekly"}


def test_desk_chart_rejects_bad_symbol_and_date(tmp_path, monkeypatch):
    """AUDIT-2: path-traversal / injection-shaped symbol or date must 4xx
    before touching the filesystem, not fall through to a 404 file lookup."""
    monkeypatch.chdir(tmp_path)
    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    client = _client(db_path, monkeypatch)

    for bad_symbol in ("../evil", "a b", "AAA/../../etc"):
        resp = client.get("/api/desk/chart", params={"date": AS_OF, "symbol": bad_symbol, "tf": "daily"})
        assert resp.status_code == 400, bad_symbol

    for bad_date in ("2026-13-99", "..", "2026/06/30", "not-a-date"):
        resp = client.get("/api/desk/chart", params={"date": bad_date, "symbol": "AAA", "tf": "daily"})
        assert resp.status_code == 400, bad_date


def test_desk_chart_data_shapes_indicator_payload(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        insert_price_ramp(conn, symbol="ACME", n=260, end=AS_OF)
        dates = trading_dates(260, AS_OF)
        conn.executemany(
            "INSERT OR REPLACE INTO sector_index_prices (symbol, trade_date, close) VALUES (?, ?, ?)",
            [("NIFTYMIDSML400", d, 100.0 + i * 0.2) for i, d in enumerate(dates, start=1)],
        )
        conn.commit()
    finally:
        conn.close()

    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/chart-data", params={"date": AS_OF, "symbol": "acme"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is True
    assert body["symbol"] == "ACME"
    assert body["as_of"] == AS_OF
    assert len(body["bars"]) == 250
    assert body["bars"][-1]["time"] == AS_OF
    assert {"time", "open", "high", "low", "close", "volume"} <= set(body["bars"][-1])
    assert set(body["overlays"]) == {"ema10", "ema21", "ema50", "ema200"}
    assert all(len(points) == 250 for points in body["overlays"].values())
    assert len(body["panes"]["volume_colors"]) == 250
    assert set(body["panes"]["volume_colors"]) <= {"bull_pp", "bear_pp", "dry", "up", "down", "noise"}
    assert len(body["panes"]["rmv"]) == 250
    assert len(body["panes"]["mswing"]) == 250
    assert set(body["markers"]) == {"purple_dot", "pocket_pivot", "persistency"}
    assert set(body["markers"]["persistency"]) == {"entry", "exit"}
    assert "burst_power" in body["meta"]
    assert "ss_rvol" in body["meta"]
    # Per-stock HMM regime pane (EXPERIMENTAL) — always present as a key,
    # honest {"available": False, ...} when the fit can't run/fails rather
    # than a 500 or a silently-missing field.
    assert "hmm" in body
    assert "available" in body["hmm"]
    if body["hmm"]["available"]:
        assert {"series", "current"} <= set(body["hmm"])
        current = body["hmm"]["current"]
        assert current["state"] in ("BULLISH", "BEARISH", "CHOP")
        assert current["confidence"] in ("LOW", "MED", "HIGH")


def test_desk_chart_data_mswing_rejects_corrupted_index_bars(tmp_path, monkeypatch):
    """AUDIT: sector_index_prices can carry stray placeholder rows (e.g. a
    rebased series pegged near 100) interleaved with the real NIFTYMIDSML400
    level under otherwise-valid trade_dates. A plain date join happily aligns
    those onto real stock bars and leaks raw off-scale levels into the
    mswing% pane. Both the alignment step and the pane's sanity clamp must
    keep the corrupted points out of the response."""
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        insert_price_ramp(conn, symbol="ACME", n=260, end=AS_OF)
        dates = trading_dates(260, AS_OF)
        rows = []
        for i, d in enumerate(dates, start=1):
            # Corrupt a contiguous run in the middle of the window with
            # placeholder levels (~100) instead of the real index level
            # (~20000) -- same shape as the real-world MAHLOG incident.
            if 100 <= i < 132:
                rows.append(("NIFTYMIDSML400", d, 100.0 + (i - 100) * 0.05))
            else:
                rows.append(("NIFTYMIDSML400", d, 20000.0 + i * 0.2))
        conn.executemany(
            "INSERT OR REPLACE INTO sector_index_prices (symbol, trade_date, close) VALUES (?, ?, ?)",
            rows,
        )
        conn.commit()
    finally:
        conn.close()

    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/chart-data", params={"date": AS_OF, "symbol": "acme"})
    assert resp.status_code == 200
    body = resp.json()
    mswing = body["panes"]["mswing"]
    assert len(mswing) == 250
    for point in mswing:
        if point["index"] is not None:
            assert abs(point["index"]) <= 50, point
        if point["stock"] is not None:
            assert abs(point["stock"]) <= 50, point


def test_desk_chart_data_empty_and_validation(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    client = _client(db_path, monkeypatch)

    empty = client.get("/api/desk/chart-data", params={"date": AS_OF, "symbol": "AAA"})
    assert empty.status_code == 200
    assert empty.json() == {"available": False, "symbol": "AAA", "as_of": None, "bars": []}

    for bad_symbol in ("../evil", "a b"):
        resp = client.get("/api/desk/chart-data", params={"date": AS_OF, "symbol": bad_symbol})
        assert resp.status_code == 400, bad_symbol

    bad_date = client.get("/api/desk/chart-data", params={"date": "2026-13-99", "symbol": "AAA"})
    assert bad_date.status_code == 400


def test_desk_track_record_aggregates_agent_family_outcomes(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        scanner_candidates.ensure_schema(conn)
        for idx, outcome in enumerate([1.2, -0.5, 2.0], start=1):
            symbol = f"A{idx}"
            conn.execute(
                "INSERT OR REPLACE INTO scan_candidates "
                "(scan_date, symbol, setup, setup_family, readiness, grade, entry, stop, rr, suggested_qty) "
                "VALUES (?, ?, 'Pullback', 'base/pattern', 80, 'A', 100, 95, 2.0, 10)",
                (AS_OF, symbol),
            )
            conn.execute(
                "INSERT OR REPLACE INTO agent_verdicts "
                "(scan_date, symbol, agent, verdict, outcome_r) VALUES (?, ?, 'mock/model-a', 'TAKE', ?)",
                (AS_OF, symbol, outcome),
            )
        conn.execute(
            "INSERT OR REPLACE INTO scan_candidates "
            "(scan_date, symbol, setup, setup_family, readiness, grade, entry, stop, rr, suggested_qty) "
            "VALUES (?, 'B1', 'Breakout', 'catalyst', 80, 'A', 100, 95, 2.0, 10)",
            (AS_OF,),
        )
        conn.execute(
            "INSERT OR REPLACE INTO agent_verdicts "
            "(scan_date, symbol, agent, verdict, outcome_r) VALUES (?, 'B1', 'chair', 'SKIP', -1.0)",
            (AS_OF,),
        )
        conn.commit()
    finally:
        conn.close()

    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/track-record")
    assert resp.status_code == 200
    records = resp.json()["records"]
    model = next(r for r in records if r["agent"] == "mock/model-a" and r["family"] == "base/pattern")
    assert model["n"] == 3
    assert model["hit_rate"] == 2 / 3
    assert abs(model["avg_r"] - 0.9) < 1e-9
    assert model["thin"] is True
    chair = next(r for r in records if r["agent"] == "chair" and r["family"] == "catalyst")
    assert chair["n"] == 1
    assert chair["hit_rate"] == 0
    assert chair["avg_r"] == -1.0


def test_desk_lessons_lists_markdown_and_digest(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    lesson_dir = tmp_path / "lessons"
    lesson_dir.mkdir()
    (lesson_dir / "2026-06-30_AAA.md").write_text(
        "[clean-hit] AAA followed through.\nSecond line.", encoding="utf-8"
    )
    (lesson_dir / "2026-06-29_BBB.md").write_text(
        "BBB was a right-process-loss after tape rolled over.", encoding="utf-8"
    )
    (lesson_dir / "_digest.md").write_text("Carry forward the clean base lesson.", encoding="utf-8")
    monkeypatch.setattr(lessons, "LESSON_DIR", lesson_dir)

    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/lessons", params={"limit": 1})
    assert resp.status_code == 200
    body = resp.json()
    assert body["digest"] == "Carry forward the clean base lesson."
    assert body["lessons"] == [
        {
            "filename": "2026-06-30_AAA.md",
            "tag": "clean-hit",
            "first_line": "[clean-hit] AAA followed through.",
        }
    ]


def test_desk_feed_orders_events_and_composes_lines(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        conn.execute(
            "INSERT INTO scan_agent_logs (run_date, agent, model, latency_ms, parsed_ok, "
            "validation, error, created_at) VALUES (?, 'mock/model-a', 'mock/model-a', 500, "
            "1, 'ok', NULL, '2026-06-30 18:33:00')",
            (AS_OF,),
        )
        conn.execute(
            "INSERT INTO scan_agent_logs (run_date, agent, model, latency_ms, parsed_ok, "
            "validation, error, created_at) VALUES (?, 'gemma', 'gemma', NULL, 0, NULL, NULL, "
            "'2026-06-30 18:41:00')",
            (AS_OF,),
        )
        conn.execute(
            "INSERT INTO scan_agent_logs (run_date, agent, model, latency_ms, parsed_ok, "
            "validation, error, created_at) VALUES (?, 'qwen', 'qwen', 900, 0, 'bad json', "
            "'429', '2026-06-30 18:35:00')",
            (AS_OF,),
        )
        conn.execute(
            "INSERT INTO pipeline_runs (run_date, stage, source, status, rows_affected, "
            "duration_s, detail, ran_at) VALUES (?, 'scan_candidates', 'candidates', 'ok', "
            "14, 1.2, '1,029 -> 259 -> 34 -> 14 shortlist', '2026-06-30 18:31:00')",
            (AS_OF,),
        )
        conn.commit()
    finally:
        conn.close()

    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/feed", params={"date": AS_OF})
    assert resp.status_code == 200
    body = resp.json()
    assert body["run_date"] == AS_OF
    events = body["events"]
    assert [e["actor"] for e in events] == ["gemma", "qwen", "mock/model-a", "scan_candidates"]
    assert events[0]["state"] == "running"
    assert "in flight" in events[0]["line"]
    assert events[1]["state"] == "failed"
    assert "failed" in events[1]["line"]
    assert events[2]["state"] == "done"
    assert "parsed ok" in events[2]["line"]
    assert events[3]["state"] == "done"
    assert "shortlist" in events[3]["line"]
    assert events[3]["expand"]["stage"] == "scan_candidates"


def test_desk_debate_returns_shaped_payload_for_seeded_night(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        insert_price_ramp(conn, symbol="KPIL", end=AS_OF)
        scanner_candidates.ensure_schema(conn)
        conn.execute(
            "INSERT INTO regime_snapshots (snapshot_date, market_mode) VALUES (?, 'SELECTIVE')",
            (AS_OF,),
        )
        conn.execute(
            "INSERT OR REPLACE INTO scan_candidates "
            "(scan_date, symbol, setup, setup_family, readiness, grade, entry, stop, target, rr, "
            "suggested_qty, gates_json, evidence_json) "
            "VALUES (?, 'KPIL', 'Pullback', 'base/pattern', 80, 'A', 892.0, 861.5, 953.0, 2.0, 34, ?, ?)",
            (
                AS_OF,
                json.dumps([{"gate": "regime", "pass": True, "reason": None, "evidence": {}}]),
                json.dumps([{"filter": "objection:rs_floor", "value": "RS 78 below 80 floor"}]),
            ),
        )
        conn.execute(
            "INSERT INTO agent_watchlist (scan_date, symbol, tier, status, prev_status, reason) "
            "VALUES (?, 'KPIL', 1, 'PROMOTE', 'HOLD', 'chair TAKE tonight')",
            (AS_OF,),
        )
        conn.execute(
            "INSERT INTO agent_watchlist (scan_date, symbol, tier, status, prev_status, reason) "
            "VALUES (?, 'DROPPED', 1, 'DROP', 'HOLD', 'no longer clean')",
            (AS_OF,),
        )
        scanner_candidates.ensure_refusals_schema(conn)
        conn.execute(
            "INSERT INTO refusals (scan_date, symbol, setup_family, failed_gate, reason) "
            "VALUES (?, 'ZZZ', 'base/pattern', 'tradability', 'illiquid')",
            (AS_OF,),
        )
        conn.execute(
            "INSERT OR REPLACE INTO agent_verdicts "
            "(scan_date, symbol, agent, verdict, conviction, rank, bull_case, bear_case, reasoning) "
            "VALUES (?, 'KPIL', 'nemotron', 'TAKE', 4, 1, 'quiet base + delivery surge', 'gap-fill overhead', 'take it')",
            (AS_OF,),
        )
        conn.execute(
            "INSERT OR REPLACE INTO agent_verdicts "
            "(scan_date, symbol, agent, verdict, conviction, rank, bull_case, bear_case, reasoning) "
            "VALUES (?, 'KPIL', 'gemma', 'TAKE', 3, 2, 'tight VCP', 'third pullback, RR only 1.8', 'ok')",
            (AS_OF,),
        )
        conn.execute(
            "INSERT OR REPLACE INTO agent_verdicts "
            "(scan_date, symbol, agent, verdict, conviction, rank, reasoning, lens_scores_json) "
            "VALUES (?, 'KPIL', 'chair', 'TAKE', 4, 1, 'models 2T/0S, spread 1', ?)",
            (AS_OF, json.dumps({"disagreement": True, "conviction_spread": 1})),
        )
        conn.execute(
            "INSERT OR REPLACE INTO agent_verdicts "
            "(scan_date, symbol, agent, verdict, reasoning) "
            "VALUES (?, 'KPIL', 'vision', 'PROMOTE', 'pivot clean, volume dry-up')",
            (AS_OF,),
        )
        conn.execute(
            "INSERT OR REPLACE INTO agent_verdicts "
            "(scan_date, symbol, agent, verdict, reasoning, lens_scores_json) "
            "VALUES (?, 'KPIL', 'sizer', 'TAKE', 'split debate, fresh regime', ?)",
            (AS_OF, json.dumps({"multiplier": 0.75, "final_qty": 25, "validated": True})),
        )
        conn.commit()
    finally:
        conn.close()

    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/debate", params={"date": AS_OF})
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is True
    assert body["scan_date"] == AS_OF
    assert body["regime_mode"] == "SELECTIVE"
    assert len(body["symbols"]) == 1
    sym = body["symbols"][0]
    assert sym["symbol"] == "KPIL"
    assert sym["family"] == "base/pattern"
    assert sym["chair"]["verdict"] == "TAKE"
    assert sym["chair"]["conviction_spread"] == 1
    assert {m["agent"] for m in sym["models"]} == {"nemotron", "gemma"}
    assert sym["vision"]["verdict"] == "PROMOTE"
    assert sym["sizer"]["multiplier"] == 0.75
    assert sym["sizer"]["final_qty"] == 25
    assert sym["plan"]["entry"] == 892.0
    assert sym["plan"]["rr"] == 2.0
    assert sym["gates"] == [{"gate": "regime", "pass": True, "reason": None, "evidence": {}}]

    # V4-T3: scan_metrics/scout_note/objections per card.
    assert sym["scan_metrics"] is not None
    assert "pct_up_from_65d_low" in sym["scan_metrics"]
    assert "adr20" in sym["scan_metrics"]
    assert "purple_dot_count_60d" in sym["scan_metrics"]
    assert "rs" in sym["scan_metrics"]
    assert sym["scout_note"]
    assert sym["objections"] == [{"code": "rs_floor", "reason": "RS 78 below 80 floor"}]

    # V4-T3: pool_summary — actionable (gate-passed + sizer qty>0), watchlist
    # (active agent_watchlist rows, DROP excluded), pool_total (all candidates
    # incl. objection-carrying).
    pool_summary = body["pool_summary"]
    assert pool_summary["actionable"] == 1
    assert pool_summary["watchlist"] == 1
    assert pool_summary["pool_total"] == 1

    funnel = body["funnel"]
    assert funnel["shortlist"] == 1
    assert funnel["debated"] == 1
    # SHIP-1 #12: tradability is a Screeners->Gates drop, not a Gates->
    # Shortlist drop, so it is excluded from by_gate (which is gates-stage-
    # only) and surfaced separately as screener_drop.
    assert funnel["screener_drop"] == 1
    assert funnel["by_gate"] == {}
    assert funnel["screeners"] == 2
    assert funnel["gates"] == 1
    # Exclusive first-failed-gate attribution: by_gate must always sum to
    # exactly the Gates->Shortlist delta.
    assert sum(funnel["by_gate"].values()) == funnel["gates"] - funnel["shortlist"]


def test_desk_signal_guide_ep_symbol_returns_numbered_steps(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        scanner_candidates.ensure_schema(conn)
        conn.execute(
            "INSERT INTO regime_snapshots (snapshot_date, market_mode) VALUES (?, 'SELECTIVE')",
            (AS_OF,),
        )
        conn.execute(
            "INSERT OR REPLACE INTO scan_candidates "
            "(scan_date, symbol, setup, setup_type, setup_family, readiness, grade, entry, stop, "
            "target, rr, suggested_qty) "
            "VALUES (?, 'KPIL', 'Earnings Power gap', 'ep', 'catalyst', 80, 'A', 892.0, 861.5, 953.0, 2.0, 34)",
            (AS_OF,),
        )
        conn.commit()
    finally:
        conn.close()

    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/signal-guide", params={"symbol": "KPIL", "date": AS_OF})
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is True
    assert body["family"] == "ep"
    assert len(body["steps"]) >= 6
    first = body["steps"][0]
    assert first["n"] == 1
    assert "LENS_EP.md" in first["source_cite"]
    assert any("892" in s["instruction"] for s in body["steps"])
    # BLOCKER 2: unheld symbol carries a null already_held, not an omitted
    # field -- the frontend needs to tell "checked, not held" apart from
    # "field missing".
    assert body["already_held"] is None


def test_desk_signal_guide_flags_symbol_already_held_elsewhere(tmp_path, monkeypatch):
    """BLOCKER 2 (cold-start audit): GRANULES was simultaneously tonight's
    fresh TAKE ticket (entry/stop from scan_candidates) and an open CDSL
    holding on POSITIONS (broker_open_lots) -- the ticket had no idea the
    user already holds the symbol. The signal-guide payload must join
    broker_open_lots by symbol and surface already_held: {qty, account,
    current_stop, source} so the plan can never be blind to an existing
    holding it would ADD to."""
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        insert_price_ramp(conn, symbol="GRANULES", n=210, end=AS_OF)
        first_buy = trading_dates(20, AS_OF)[0]
        scanner_candidates.ensure_schema(conn)
        conn.execute(
            "INSERT INTO regime_snapshots (snapshot_date, market_mode) VALUES (?, 'SELECTIVE')",
            (AS_OF,),
        )
        conn.execute(
            "INSERT OR REPLACE INTO scan_candidates "
            "(scan_date, symbol, setup, setup_type, setup_family, readiness, grade, entry, stop, "
            "target, rr, suggested_qty) "
            "VALUES (?, 'GRANULES', 'Pullback', 'base', 'base/pattern', 80, 'A', 910.0, 881.36, 960.0, 1.8, 12)",
            (AS_OF,),
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS broker_open_lots ("
            "symbol TEXT NOT NULL, qty REAL NOT NULL, avg_cost REAL NOT NULL, "
            "first_buy_date TEXT NOT NULL, import_key TEXT NOT NULL UNIQUE)"
        )
        conn.execute(
            "INSERT INTO broker_open_lots (symbol, qty, avg_cost, first_buy_date, import_key) "
            "VALUES ('GRANULES', 8, 850.0, ?, 'cdsl_stmt:test-granules')",
            (first_buy,),
        )
        conn.commit()
    finally:
        conn.close()

    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/signal-guide", params={"symbol": "GRANULES", "date": AS_OF})
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is True
    assert body["plan"]["entry"] == 910.0
    assert body["plan"]["stop"] == 881.36

    held = body["already_held"]
    assert held is not None
    assert held["qty"] == 8
    assert held["account"] == "CDSL demat"
    assert held["source"] == "broker_open_lots"
    # Position stop (tool-assigned management stop) is reported honestly and
    # is NOT reconciled against the plan's own stop (881.36) -- one-writer;
    # the two numbers are independent and both surfaced for the user to
    # reconcile themselves.
    assert isinstance(held["current_stop"], (int, float))


def test_desk_signal_guide_near_miss_symbol_is_honest_placeholder(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        scanner_candidates.ensure_schema(conn)
        scanner_candidates.ensure_refusals_schema(conn)
        conn.execute(
            "INSERT INTO refusals (scan_date, symbol, setup_family, failed_gate, reason) "
            "VALUES (?, 'ZZZ', 'catalyst', 'fresh-leg', 'extended 9%')",
            (AS_OF,),
        )
        conn.commit()
    finally:
        conn.close()

    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/signal-guide", params={"symbol": "ZZZ", "date": AS_OF})
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is True
    assert len(body["steps"]) == 1
    assert "debate-only" in body["steps"][0]["instruction"]
    assert "extended 9%" in body["steps"][0]["instruction"]


def test_desk_signal_guide_morning_setups_symbol_returns_d2_template(tmp_path, monkeypatch):
    """T3: a symbol with no scan_candidates plan but a morning_setups row
    (EOD D2/strong-start-ready checklist, M7) must route to the D2/
    strong-start guide template with real day1_high/day1_low numbers, not
    the generic 'no sized plan' fallback."""
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        conn.execute(
            "INSERT INTO morning_setups (scan_date, symbol, setup_type, branch, evidence_json, "
            "resolve_json, entry_rule, stop_rule) VALUES (?, 'PPAP', 'd2_ready', 'strong_close_gap_up', ?, ?, ?, ?)",
            (
                AS_OF,
                json.dumps({"day1_high": 331.95, "day1_low": 272.25, "day1_change_pct": 18.4, "day_rvol": 3.2}),
                json.dumps(["Did the open gap up?"]),
                "Intraday breakout of the first 5-min opening-range high / day-high breakout.",
                "Day's / morning low = maximum-pressure anchor.",
            ),
        )
        conn.commit()
    finally:
        conn.close()

    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/signal-guide", params={"symbol": "PPAP", "date": AS_OF})
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is True
    assert body["source"] == "morning_setups"
    assert body["day1_high"] == 331.95
    assert body["day1_low"] == 272.25
    assert body["family"] == "d2"
    assert len(body["steps"]) >= 4
    assert any(
        "331.95" in s["instruction"] or "272.25" in s["instruction"] for s in body["steps"]
    )


def test_desk_signal_guide_unknown_symbol_is_unavailable(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/signal-guide", params={"symbol": "NOPE", "date": AS_OF})
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is False
    assert body["steps"] == []


def test_desk_debate_near_miss_symbol_shows_failed_gate_not_blank_shell(tmp_path, monkeypatch):
    """SHIP-2 #4: a debated symbol with no scan_candidates row (never cleared
    every gate) must not render as a blank shell next to a populated
    gate-passed card — it should carry the setup_family + failed_gate +
    reason from refusals, with no fabricated plan/base-rate."""
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        scanner_candidates.ensure_schema(conn)
        conn.execute(
            "INSERT INTO regime_snapshots (snapshot_date, market_mode) VALUES (?, 'SELECTIVE')",
            (AS_OF,),
        )
        scanner_candidates.ensure_refusals_schema(conn)
        conn.execute(
            "INSERT INTO refusals (scan_date, symbol, setup_family, failed_gate, reason) "
            "VALUES (?, 'NEARM', 'base/pattern', 'fresh-leg', 'extended 9.1% above pivot')",
            (AS_OF,),
        )
        conn.execute(
            "INSERT OR REPLACE INTO agent_verdicts "
            "(scan_date, symbol, agent, verdict, conviction, rank, reasoning) "
            "VALUES (?, 'NEARM', 'chair', 'SKIP', 2, 5, 'struck: failed fresh-leg')",
            (AS_OF,),
        )
        conn.commit()
    finally:
        conn.close()

    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/debate", params={"date": AS_OF})
    assert resp.status_code == 200
    body = resp.json()
    sym = body["symbols"][0]
    assert sym["symbol"] == "NEARM"
    assert sym["family"] == "base/pattern"
    assert sym["plan"] is None
    assert sym["base_rate"] is None
    assert sym["gates"] == []
    assert sym["near_miss"] == {"failed_gate": "fresh-leg", "reason": "extended 9.1% above pivot"}


def test_desk_funnel_exclusive_gate_attribution_reconciles(tmp_path):
    """SHIP-1 #12: with a mix of tradability + named-gate refusals, by_gate
    (gates-stage-only) must sum to exactly gates - shortlist, and
    screener_drop (tradability) must be excluded from that sum."""
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        scanner_candidates.ensure_refusals_schema(conn)
        for i, gate in enumerate(["tradability", "tradability", "regime", "fresh-leg", "fresh-leg"]):
            conn.execute(
                "INSERT INTO refusals (scan_date, symbol, setup_family, failed_gate, reason) "
                "VALUES (?, ?, 'base/pattern', ?, 'x')",
                (AS_OF, f"SYM{i}", gate),
            )
        conn.commit()
        funnel = api_app._desk_funnel(conn, AS_OF, shortlist_count=3, debated_count=2)
    finally:
        conn.close()

    assert funnel["screener_drop"] == 2
    assert funnel["by_gate"] == {"fresh-leg": 2, "regime": 1}
    assert sum(funnel["by_gate"].values()) == funnel["gates"] - funnel["shortlist"]
    assert funnel["screeners"] == funnel["shortlist"] + funnel["screener_drop"] + sum(funnel["by_gate"].values())


def test_desk_debate_empty_date_is_honest(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/debate", params={"date": "2020-01-01"})
    assert resp.status_code == 200
    assert resp.json() == {"available": False, "scan_date": "2020-01-01", "symbols": []}


def test_desk_debate_resolves_latest_completed_session_on_or_before_requested_date(
    tmp_path, monkeypatch
):
    """Selecting today must not blank a valid prior-session debate."""
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        scanner_candidates.ensure_schema(conn)
        conn.execute(
            "INSERT OR REPLACE INTO agent_verdicts "
            "(scan_date, symbol, agent, verdict, conviction, rank, reasoning) "
            "VALUES (?, 'KPIL', 'chair', 'TAKE', 4, 1, 'prior completed session')",
            (AS_OF,),
        )
        conn.commit()
    finally:
        conn.close()

    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/debate", params={"date": "2026-07-01"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is True
    assert body["requested_date"] == "2026-07-01"
    assert body["scan_date"] == AS_OF
    assert [row["symbol"] for row in body["symbols"]] == ["KPIL"]


def test_desk_feed_empty_date_is_honest(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/feed", params={"date": "2020-01-01"})
    assert resp.status_code == 200
    assert resp.json() == {"run_date": "2020-01-01", "events": []}


def test_desk_positions_seeded_open_trade_shapes_lifecycle_card(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        scanner_candidates.ensure_schema(conn)
        insert_price_ramp(conn, symbol="HUDCO", n=210, end=AS_OF)
        dates = trading_dates(20, AS_OF)
        trade_date = dates[0]
        row = conn.execute(
            "SELECT close FROM daily_prices WHERE symbol = 'HUDCO' AND trade_date = ?",
            (trade_date,),
        ).fetchone()
        entry = float(row["close"])
        stop = entry - 5.0
        conn.execute(
            "INSERT INTO journal_trades (trade_date, symbol, setup, entry, stop) "
            "VALUES (?, 'HUDCO', 'Pullback', ?, ?)",
            (trade_date, entry, stop),
        )
        conn.execute(
            "INSERT OR REPLACE INTO agent_verdicts "
            "(scan_date, symbol, agent, verdict, conviction, bull_case, reasoning) "
            "VALUES (?, 'HUDCO', 'nemotron', 'TAKE', 4, 'quiet base + delivery surge', 'take it')",
            (trade_date,),
        )
        from manas_os.agents import signals as agents_signals

        agents_signals.ensure_schema(conn)
        conn.execute(
            "INSERT OR REPLACE INTO agent_signals (scan_date, symbol, channel, message, sent) "
            "VALUES (?, 'HUDCO', 'coach', 'HUDCO coach: HOLD.', 1)",
            (AS_OF,),
        )
        conn.commit()
    finally:
        conn.close()

    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/positions", params={"date": AS_OF})
    assert resp.status_code == 200
    body = resp.json()
    assert body["run_date"] == AS_OF
    assert len(body["positions"]) == 1
    pos = body["positions"][0]
    assert pos["symbol"] == "HUDCO"
    assert pos["trade_date"] == trade_date
    assert pos["phase"] in {"INITIATION", "TREND", "EXTENSION"}
    assert isinstance(pos["r_path"], list) and len(pos["r_path"]) > 0
    for point in pos["r_path"]:
        assert trade_date <= point["date"] <= AS_OF
    assert pos["original_thesis"]["agent"] == "nemotron"
    assert pos["original_thesis"]["bull_case"] == "quiet base + delivery surge"
    assert pos["coach"]["message"] == "HUDCO coach: HOLD."
    assert pos["coach"]["sent"] is True
    assert pos["urgent"] is False
    assert pos["coach_verdict"] in {"HOLD", "TRIM", "EXIT"}
    assert pos["todays_stop"] is not None
    assert pos["plain_why"] == pos["action_line"]
    assert pos["days_held"] is not None and pos["days_held"] >= 0
    assert pos["open_r"] == pos["r"]


def test_desk_positions_below_stop_forces_exit_and_reports_rupee_pnl(tmp_path, monkeypatch):
    # T1 regression: a position trading BELOW its live stop must always come
    # back as coach_verdict EXIT with a stop-breach rule fired -- previously
    # the deterministic engine only checked soft weakness signals (EMA,
    # reversal bar, distribution days, fresh-low, gap-down) and never
    # compared price to the stop itself, so a stock could sit deeply
    # underwater and still be told "HOLD".
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        scanner_candidates.ensure_schema(conn)
        insert_price_ramp(conn, symbol="HUDCO", n=210, end=AS_OF)
        dates = trading_dates(20, AS_OF)
        trade_date = dates[0]
        row = conn.execute(
            "SELECT close FROM daily_prices WHERE symbol = 'HUDCO' AND trade_date = ?",
            (trade_date,),
        ).fetchone()
        entry = float(row["close"])
        stop = entry - 5.0
        qty = 100
        # Force the latest (AS_OF) bar deep below the stop.
        breach_close = stop - 3.0
        conn.execute(
            "UPDATE daily_prices SET close = ?, high = ?, low = ?, open = ? "
            "WHERE symbol = 'HUDCO' AND trade_date = ?",
            (breach_close, breach_close + 1, breach_close - 1, breach_close + 0.5, AS_OF),
        )
        conn.execute(
            "INSERT INTO journal_trades (trade_date, symbol, setup, entry, stop, qty) "
            "VALUES (?, 'HUDCO', 'Pullback', ?, ?, ?)",
            (trade_date, entry, stop, qty),
        )
        conn.commit()
    finally:
        conn.close()

    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/positions", params={"date": AS_OF})
    assert resp.status_code == 200
    pos = resp.json()["positions"][0]
    assert pos["symbol"] == "HUDCO"
    assert pos["coach_verdict"] == "EXIT"
    assert pos["urgent"] is True
    assert "stop-breached" in pos["fired"]
    assert pos["close"] == breach_close
    assert pos["pnl_rupees"] == round((breach_close - entry) * qty, 2)
    assert pos["pnl_pct"] == round((breach_close - entry) / entry * 100.0, 2)
    assert pos["pnl_rupees"] < 0


def test_desk_positions_includes_assigned_stop_for_imported_holding(tmp_path, monkeypatch):
    """Zerodha-imported open holdings (broker_open_lots, qty > 0) carry no
    journaled stop, so before this change the coach path (which hard-requires
    entry+stop) never produced a verdict for them and they were invisible to
    /api/desk/positions. The tool now assigns each one a MANAGEMENT stop
    (eod_detectors.assigned_management_stop) so the same trail_plan/
    two_strike machinery journaled positions use can read them too. A
    negative-qty (closed-out) lot must never surface as a position."""
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        insert_price_ramp(conn, symbol="HUDCO", n=210, end=AS_OF)
        first_buy = trading_dates(20, AS_OF)[0]
        conn.execute(
            "CREATE TABLE IF NOT EXISTS broker_open_lots ("
            "symbol TEXT NOT NULL, qty REAL NOT NULL, avg_cost REAL NOT NULL, "
            "first_buy_date TEXT NOT NULL, import_key TEXT NOT NULL UNIQUE)"
        )
        conn.execute(
            "INSERT INTO broker_open_lots (symbol, qty, avg_cost, first_buy_date, import_key) "
            "VALUES ('HUDCO', 10, 100.0, ?, 'zerodha-open:test-open')",
            (first_buy,),
        )
        # Fully exited lot (qty <= 0) -- must be excluded from the surface.
        conn.execute(
            "INSERT INTO broker_open_lots (symbol, qty, avg_cost, first_buy_date, import_key) "
            "VALUES ('HUDCO', -5, 100.0, ?, 'zerodha-open:test-closed')",
            (first_buy,),
        )
        conn.commit()
    finally:
        conn.close()

    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/positions", params={"date": AS_OF})
    assert resp.status_code == 200
    positions = resp.json()["positions"]
    assert len(positions) == 1  # the qty<=0 lot never appears

    pos = positions[0]
    assert pos["symbol"] == "HUDCO"
    assert pos["source"] == "zerodha_import"
    assert pos["assigned_stop"] is True
    assert pos["assigned_stop_source"] in {"21ema", "swing_low_10"}
    assert pos["trade_id"] is None
    assert pos["stop"] is not None
    assert pos["stop"] < pos["close"]  # gently-rising ramp: assigned stop sits below close
    assert pos["coach_verdict"] in {"HOLD", "TRIM", "EXIT", "MOVE_STOP"}
    assert pos["exit_state"]["state"] in {"Intact", "Weakening", "Broken"}

    # R stats stay excluded for assigned-stop (management-only) positions --
    # this stop is never a journaled risk plan, so no R-based coaching leaks.
    assert pos["r"] is None
    assert pos["open_r"] is None
    assert pos["r_path"] == []
    assert "R." not in (pos["action_line"] or "")
    assert "+" not in (pos["action_line"] or "") or "R" not in (pos["action_line"] or "")


def test_desk_positions_assigned_stop_breach_forces_exit(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        insert_price_ramp(conn, symbol="RAIN", n=210, end=AS_OF)
        first_buy = trading_dates(20, AS_OF)[0]
        # Crash the last two sessions well under any plausible assigned stop
        # so two_strike's hard stop-breach rule fires.
        dates = trading_dates(210, AS_OF)
        conn.execute(
            "UPDATE daily_prices SET open=60, high=61, low=40, close=42, volume=900000 "
            "WHERE symbol='RAIN' AND trade_date=?",
            (dates[-2],),
        )
        conn.execute(
            "UPDATE daily_prices SET open=41, high=43, low=30, close=32, volume=1200000 "
            "WHERE symbol='RAIN' AND trade_date=?",
            (dates[-1],),
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS broker_open_lots ("
            "symbol TEXT NOT NULL, qty REAL NOT NULL, avg_cost REAL NOT NULL, "
            "first_buy_date TEXT NOT NULL, import_key TEXT NOT NULL UNIQUE)"
        )
        conn.execute(
            "INSERT INTO broker_open_lots (symbol, qty, avg_cost, first_buy_date, import_key) "
            "VALUES ('RAIN', 3, 100.0, ?, 'zerodha-open:test-crash')",
            (first_buy,),
        )
        conn.commit()
    finally:
        conn.close()

    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/positions", params={"date": AS_OF})
    assert resp.status_code == 200
    pos = resp.json()["positions"][0]
    assert pos["symbol"] == "RAIN"
    assert pos["assigned_stop"] is True
    assert pos["coach_verdict"] == "EXIT"
    assert pos["urgent"] is True
    assert "stop-breached" in pos["fired"]

    # USABILITY_UX_AUDIT_2026-07-19.md defect #4, imported-holding half: the
    # banner used to read "EXIT NOW - two-strike fired..." -- a second,
    # independent timing word next to action_sentence's own "EXIT today near
    # the close". The banner must state the mechanical fact only; timing
    # comes from action_sentence alone.
    assert pos["banner"] == "Two-strike rule fired on an assigned-stop holding"
    assert "EXIT NOW" not in pos["banner"]
    assert pos["action_sentence"].startswith("EXIT today near the close (15:00-15:25)")
    assert "sell the full position at market" in pos["action_sentence"]


def test_desk_positions_no_open_trades_is_honest(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/positions", params={"date": "2020-01-01"})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["run_date"] == "2020-01-01"
    assert payload["positions"] == []
    assert "fyers_connected" in payload
    assert "market_open" in payload



def test_desk_position_add_and_update_write_journal(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    client = _client(db_path, monkeypatch)

    add = client.post(
        "/api/desk/positions",
        json={"symbol": "hudco", "entry": 100.0, "stop": 92.0, "qty": 25, "date": AS_OF},
    )
    assert add.status_code == 200
    trade_id = add.json()["trade_id"]

    update = client.post(f"/api/desk/positions/{trade_id}/update", json={"stop": 94.0, "qty": 10})
    assert update.status_code == 200
    assert update.json() == {"ok": True, "trade_id": trade_id, "stop": 94.0, "qty": 10.0}

    conn = db.connect(db_path)
    try:
        row = conn.execute(
            "SELECT symbol, trade_date, entry, stop, qty, exit FROM journal_trades WHERE trade_id = ?",
            (trade_id,),
        ).fetchone()
        assert dict(row) == {
            "symbol": "HUDCO",
            "trade_date": AS_OF,
            "entry": 100.0,
            "stop": 94.0,
            "qty": 10.0,
            "exit": None,
        }
    finally:
        conn.close()


def test_desk_position_update_and_close_bad_id_404(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    client = _client(db_path, monkeypatch)

    update = client.post("/api/desk/positions/999/update", json={"stop": 94.0})
    assert update.status_code == 404
    close = client.post("/api/desk/positions/999/close", json={"exit_price": 120.0, "reason_tag": "target"})
    assert close.status_code == 404


def test_desk_position_close_computes_realized_r(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        conn.execute(
            "INSERT INTO journal_trades (trade_date, symbol, setup, entry, stop, qty) "
            "VALUES (?, 'HUDCO', 'manual', 100.0, 90.0, 5)",
            (AS_OF,),
        )
        trade_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
        conn.commit()
    finally:
        conn.close()

    client = _client(db_path, monkeypatch)
    resp = client.post(
        f"/api/desk/positions/{trade_id}/close",
        json={"exit_price": 120.0, "reason_tag": "target", "date": "2026-07-01"},
    )
    assert resp.status_code == 200
    assert resp.json()["r_result"] == 2.0

    conn = db.connect(db_path)
    try:
        row = conn.execute(
            "SELECT exit, exit_date, r_result, mistake_tags_json FROM journal_trades WHERE trade_id = ?",
            (trade_id,),
        ).fetchone()
        assert row["exit"] == 120.0
        assert row["exit_date"] == "2026-07-01"
        assert row["r_result"] == 2.0
        assert json.loads(row["mistake_tags_json"]) == ["target"]
    finally:
        conn.close()


def test_desk_market_seeded_index_history_hand_checked_returns(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        dates = trading_dates(25, AS_OF)  # ascending, dates[-1] == AS_OF
        for i, d in enumerate(dates, start=1):
            conn.execute(
                "INSERT INTO sector_index_prices (symbol, trade_date, close) VALUES (?, ?, ?)",
                ("NIFTY 50", d, 100.0 + i),
            )
            conn.execute(
                "INSERT INTO sector_index_prices (symbol, trade_date, close) VALUES (?, ?, ?)",
                ("NIFTY BANK", d, 200.0 + i * 2),
            )
        conn.execute(
            "INSERT INTO industry_metrics (snapshot_date, name, perf_1d, perf_1w, perf_1m, num_stocks) "
            "VALUES (?, 'Pharmaceuticals', 3.5, 5.0, 8.0, 12)",
            (AS_OF,),
        )
        conn.execute(
            "INSERT INTO industry_metrics (snapshot_date, name, perf_1d, perf_1w, perf_1m, num_stocks) "
            "VALUES (?, 'Auto Ancillaries', -1.2, -2.0, -3.0, 9)",
            (AS_OF,),
        )
        conn.execute(
            "INSERT INTO sector_metrics (snapshot_date, sector_key, setup_count_a, setup_count_b, setup_count_c) "
            "VALUES (?, 'BANK', 3, 2, 1)",
            (AS_OF,),
        )
        conn.execute(
            "INSERT INTO disclosures (trade_date, symbol, kind, detail_json) "
            "VALUES (?, 'ACME', 'bulk_deal', ?)",
            (AS_OF, json.dumps({"qty": "10000", "price": "123.4", "buyer": "Foo Fund"})),
        )
        conn.execute(
            "INSERT INTO disclosures (trade_date, symbol, kind, detail_json) "
            "VALUES (?, 'ACME', 'insider', ?)",
            (AS_OF, json.dumps({"person": "Jane Doe", "type": "Buy", "qty": "500"})),
        )
        conn.execute(
            "INSERT INTO fii_dii_daily "
            "(trade_date, fii_buy, fii_sell, fii_net, dii_buy, dii_sell, dii_net, source) "
            "VALUES (?, 17463.95, 15501.15, 1962.8, 19165.13, 18374.97, 790.16, 'groww_fii_dii')",
            (AS_OF,),
        )
        conn.execute(
            "INSERT INTO fii_dii_daily "
            "(trade_date, fii_buy, fii_sell, fii_net, dii_buy, dii_sell, dii_net, source) "
            "VALUES ('2026-06-29', 18414.01, 18020.82, 393.19, 18897.44, 19280.87, -383.43, 'groww_fii_dii')",
        )
        conn.commit()
    finally:
        conn.close()

    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/market", params={"date": AS_OF})
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is True
    assert body["as_of"] == AS_OF
    fii_dii = body["fii_dii"]
    assert fii_dii["latest"]["trade_date"] == AS_OF
    assert fii_dii["latest"]["fii_net"] == 1962.8
    assert fii_dii["latest"]["dii_net"] == 790.16
    assert len(fii_dii["last_10"]) == 2
    assert fii_dii["last_10"][0]["trade_date"] == AS_OF
    assert fii_dii["net_trend"]["fii_net_sum"] == 1962.8 + 393.19
    assert fii_dii["net_trend"]["dii_net_sum"] == 790.16 + (-383.43)

    by_symbol = {row["symbol"]: row for row in body["indices"]}
    n50 = by_symbol["NIFTY 50"]
    # last close 125 (i=25), 1d prior close 124 (i=24): (125-124)/124*100
    assert n50["returns"]["1d"] == round((125.0 - 124.0) / 124.0 * 100.0, 2)
    # 1w = 5 sessions back, i=20 close=120
    assert n50["returns"]["1w"] == round((125.0 - 120.0) / 120.0 * 100.0, 2)
    assert len(n50["spark"]) == 25
    assert n50["spark"][-1] == 125.0
    # NIFTY 50 is first in indices (broad-first ordering).
    assert body["indices"][0]["symbol"] == "NIFTY 50"

    bank = by_symbol["NIFTY BANK"]
    assert bank["returns"]["1d"] == round((250.0 - 248.0) / 248.0 * 100.0, 2)

    movers = body["movers"]
    assert set(movers.keys()) == {"d1", "w1", "m1"}
    d1 = movers["d1"]
    assert any(s["symbol"] == "NIFTY BANK" for s in d1["sectors_up"])
    bank_up = next(s for s in d1["sectors_up"] if s["symbol"] == "NIFTY BANK")
    assert bank_up["num_stocks"] == 6  # setup_count_a+b+c = 3+2+1
    assert d1["themes_up"][0]["name"] == "Pharmaceuticals"

    sectors = body["sectors"]
    assert any(s["symbol"] == "NIFTY BANK" and s["num_stocks"] == 6 for s in sectors)
    assert all(s["symbol"] != "NIFTY 50" for s in sectors)  # broad index excluded

    deals = body["deals"]
    assert deals["block_bulk"][0]["symbol"] == "ACME"
    assert deals["block_bulk"][0]["detail"]["buyer"] == "Foo Fund"
    assert deals["insider"][0]["detail"]["person"] == "Jane Doe"


def test_market_deals_pct_of_mcap_rank_and_null_last(tmp_path):
    """SHIP-1 #14: deals join symbol_quality.market_cap_cr to compute
    pct_of_mcap, and _market_deals ranks by it desc within each kind list,
    with no-mcap/no-qty deals sorting last (by trade_date desc)."""
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        conn.execute(
            "INSERT INTO symbol_quality (trade_date, symbol, market_cap_cr) VALUES (?, 'BIG', 100000)",
            (AS_OF,),
        )
        conn.execute(
            "INSERT INTO symbol_quality (trade_date, symbol, market_cap_cr) VALUES (?, 'SMALL', 500)",
            (AS_OF,),
        )
        conn.commit()
        # BIG: qty 10000 @ 100 = 10,00,000 INR value vs mcap 100000cr*1e7 -> tiny pct.
        conn.execute(
            "INSERT INTO disclosures (trade_date, symbol, kind, detail_json) VALUES (?, 'BIG', 'bulk_deal', ?)",
            (AS_OF, json.dumps({"qty": "10000", "price": "100"})),
        )
        # SMALL: qty 100000 @ 200 = 2,00,00,000 INR value vs mcap 500cr*1e7 -> much bigger pct.
        conn.execute(
            "INSERT INTO disclosures (trade_date, symbol, kind, detail_json) VALUES (?, 'SMALL', 'bulk_deal', ?)",
            (AS_OF, json.dumps({"qty": "100000", "price": "200"})),
        )
        # NOMCAP: no symbol_quality row -> pct_of_mcap must be None, sorts last.
        conn.execute(
            "INSERT INTO disclosures (trade_date, symbol, kind, detail_json) VALUES (?, 'NOMCAP', 'bulk_deal', ?)",
            (AS_OF, json.dumps({"qty": "500", "price": "50"})),
        )
        conn.commit()

        deals = api_app._market_deals(conn, AS_OF)
    finally:
        conn.close()

    block_bulk = deals["block_bulk"]
    assert [d["symbol"] for d in block_bulk] == ["SMALL", "BIG", "NOMCAP"]
    assert block_bulk[0]["pct_of_mcap"] > block_bulk[1]["pct_of_mcap"] > 0
    assert block_bulk[2]["pct_of_mcap"] is None


def test_desk_market_empty_date_is_honest(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/market", params={"date": "2020-01-01"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is False
    assert body["indices"] == []
    assert body["deals"] == {"block_bulk": [], "insider": []}
    assert body["fii_dii"] is None
    assert body["vix"] is None


def test_classify_index_spot_checks():
    """Name-pattern classifier — see comment above BROAD_INDEX_LADDER in
    manas_os/api/app.py for the precedence rules."""
    classify = api_app.classify_index
    broad = [
        "NIFTY 50", "Nifty 100", "NIFTY 200", "Nifty 500", "Nifty Next 50",
        "NIFTY MIDCAP 150", "Nifty Smallcap 250", "NIFTY MICROCAP 250",
        "NIFTY LargeMidcap 250", "NIFTYMIDSML400",
    ]
    for name in broad:
        assert classify(name) == "BROAD", name

    sectoral = [
        "Nifty Bank", "NIFTY IT", "Nifty Auto", "Nifty Metal", "Nifty FMCG",
        "Nifty Energy", "Nifty Realty", "Nifty PSU Bank", "Nifty Private Bank",
        "Nifty Financial Services", "Nifty Healthcare Index", "Nifty Media",
        "Nifty Infrastructure", "Nifty Consumer Durables", "Nifty Oil & Gas",
        "Nifty Commodities", "Nifty CPSE", "Nifty India Defence",
        "Nifty500 Healthcare",  # "500" prefix has no strategy marker word
    ]
    for name in sectoral:
        assert classify(name) == "SECTORAL", name

    thematic = [
        "NIFTY Alpha Low-Volatility 30", "NIFTY100 Quality 30", "Nifty500 Value 50",
        "Nifty50 Equal Weight", "Nifty50 Shariah", "Nifty Dividend Opportunities 50",
        "Nifty 10 yr Benchmark G-Sec", "Nifty BHARAT Bond Index - April 2030",
        "Nifty 50 Arbitrage", "Nifty50 PR 2x Leverage", "Nifty50 USD",
        "Nifty MidSmall Healthcare",  # blend, not plain sector
        "Nifty IPO", "Nifty SME EMERGE", "Nifty Total Market",
        "Nifty MidSmallcap400 Momentum Quality 100",  # MIDSML400 broad-name
        # regex only matches the bare alias symbol, not blend variants
        "Nifty MidSmallcap400 50:50",
    ]
    for name in thematic:
        assert classify(name) == "THEMATIC_STRATEGY", name


def test_desk_market_taxonomy_and_vix(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        dates = trading_dates(25, AS_OF)
        for i, d in enumerate(dates, start=1):
            conn.execute(
                "INSERT INTO sector_index_prices (symbol, trade_date, close) VALUES (?, ?, ?)",
                ("NIFTY 50", d, 100.0 + i),
            )
            conn.execute(
                "INSERT INTO sector_index_prices (symbol, trade_date, close) VALUES (?, ?, ?)",
                ("Nifty Bank", d, 200.0 + i),
            )
            conn.execute(
                "INSERT INTO sector_index_prices (symbol, trade_date, close) VALUES (?, ?, ?)",
                ("NIFTY100 Quality 30", d, 300.0 + i),
            )
            conn.execute(
                "INSERT INTO sector_index_prices (symbol, trade_date, close) VALUES (?, ?, ?)",
                ("India VIX", d, 14.5),
            )
        conn.commit()
    finally:
        conn.close()

    client = _client(db_path, monkeypatch)

    resp = client.get("/api/desk/market", params={"date": AS_OF})
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is True

    # VIX is extracted, not listed as an index.
    assert body["vix"] == {"value": 14.5, "band": "normal"}
    symbols = {row["symbol"] for row in body["indices"]}
    assert "India VIX" not in symbols
    assert all(s["symbol"] != "India VIX" for s in body["sectors"])

    # Default payload: BROAD + SECTORAL only, no thematic index.
    assert "NIFTY 50" in symbols
    assert "Nifty Bank" in symbols
    assert "NIFTY100 Quality 30" not in symbols

    # Treemap/sectors set is SECTORAL only.
    sector_symbols = {s["symbol"] for s in body["sectors"]}
    assert sector_symbols == {"Nifty Bank"}

    resp2 = client.get("/api/desk/market", params={"date": AS_OF, "include_thematic": "true"})
    body2 = resp2.json()
    symbols2 = {row["symbol"] for row in body2["indices"]}
    assert "NIFTY100 Quality 30" in symbols2


def test_vix_band_tiers():
    band = api_app._vix_band
    assert band(11.9) == "low"
    assert band(12.0) == "normal"
    assert band(19.9) == "normal"
    assert band(20.0) == "elevated"
    assert band(24.9) == "elevated"
    assert band(25.0) == "danger"
    assert band(30.0) == "danger"


def test_desk_latest_reports_run_card_and_scan_dates(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    for scan_date in ("2026-06-25", "2026-06-30"):
        conn.execute(
            "INSERT OR REPLACE INTO scan_candidates "
            "(scan_date, symbol, setup, readiness, grade) VALUES (?, 'AAA', 'ep', 80, 'A')",
            (scan_date,),
        )
    conn.commit()
    conn.close()
    run_card_dir = tmp_path / "data" / "run_cards"
    run_card_dir.mkdir(parents=True)
    (run_card_dir / "2026-06-28.json").write_text("{}")
    (run_card_dir / "2026-06-29.json").write_text("{}")

    from manas_os.agents import run_card as run_card_module

    monkeypatch.setattr(run_card_module, "RUN_CARD_ROOT", run_card_dir)
    monkeypatch.setattr(api_app, "_BUILD_SHA", "abc1234")
    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/latest")
    assert resp.status_code == 200
    body = resp.json()
    assert body["latest_run_card_date"] == "2026-06-29"
    assert body["latest_scan_date"] == "2026-06-30"
    assert body["data_as_of"] == "2026-06-29"
    assert body["build_sha"] == "abc1234"
    assert isinstance(body["next_update_hint"], str) and body["next_update_hint"]
    assert body["run_card_dates"] == ["2026-06-28", "2026-06-29"]



def test_desk_latest_empty_db_returns_nulls(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    from manas_os.agents import run_card as run_card_module

    monkeypatch.setattr(run_card_module, "RUN_CARD_ROOT", tmp_path / "data" / "run_cards")
    monkeypatch.setattr(api_app, "_BUILD_SHA", None)
    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/latest")
    assert resp.status_code == 200
    body = resp.json()
    assert body["latest_run_card_date"] is None
    assert body["latest_scan_date"] is None
    assert body["data_as_of"] is None
    assert body["build_sha"] is None
    assert body["run_card_dates"] == []



def test_next_update_hint_live_market_hours_weekday_shows_yesterday_close():
    now = datetime(2026, 7, 9, 11, 0, tzinfo=api_app._IST)  # Thursday, 11:00 IST
    hint = api_app._next_update_hint(now, "2026-07-08")
    assert "live market hours" in hint
    assert "yesterday's close" in hint
    assert "19:00 IST" in hint


def test_next_update_hint_after_1900_weekday_data_still_yesterday_shows_pending():
    now = datetime(2026, 7, 9, 20, 0, tzinfo=api_app._IST)  # Thursday, 20:00 IST
    hint = api_app._next_update_hint(now, "2026-07-08")
    assert "update pending" in hint
    assert "run_daily_update.bat" in hint


def test_next_update_hint_weekend_shows_market_closed_through_date():
    now = datetime(2026, 7, 11, 12, 0, tzinfo=api_app._IST)  # Saturday
    hint = api_app._next_update_hint(now, "2026-07-10")
    assert hint == "market closed — data through 2026-07-10"


def test_next_update_hint_after_1900_weekday_data_already_today():
    now = datetime(2026, 7, 9, 20, 0, tzinfo=api_app._IST)  # Thursday, 20:00 IST
    hint = api_app._next_update_hint(now, "2026-07-09")
    assert "update pending" not in hint
    assert "tonight's update is in" in hint
    assert "2026-07-09" in hint
    assert "next trading day ~19:00 IST" in hint


def test_desk_watchlist_returns_rows_joined_with_chair_verdict(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        from manas_os.agents import _shared

        _shared.ensure_agent_tables(conn)
        conn.execute(
            "INSERT INTO agent_verdicts (scan_date, symbol, agent, verdict, conviction, rank, tier) "
            "VALUES (?, 'AAA', 'chair', 'TAKE', 5, 1, 'PASSED')",
            (AS_OF,),
        )
        conn.execute(
            "INSERT INTO agent_watchlist (scan_date, symbol, tier, status, prev_status, reason, miss_streak) "
            "VALUES (?, 'AAA', 'PASSED', 'PROMOTE', 'HOLD', 'chair verdict SKIP -> TAKE', 0)",
            (AS_OF,),
        )
        conn.commit()
    finally:
        conn.close()
    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/watchlist", params={"date": AS_OF})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["available"] is True
    assert len(payload["rows"]) == 1
    row = payload["rows"][0]
    assert row["symbol"] == "AAA"
    assert row["status"] == "PROMOTE"
    assert row["prev_status"] == "HOLD"
    assert row["chair_verdict"] == "TAKE"
    assert row["conviction"] == 5
    assert "SKIP -> TAKE" in row["reason"]
    assert row["events"] == [
        {"date": AS_OF, "action": "PROMOTE", "reason": row["reason"]},
    ]
    assert payload["curator_delta"] == {
        "added": [],
        "promoted": ["AAA"],
        "demoted": [],
        "dropped": [],
    }


def test_desk_watchlist_events_and_curator_delta_multi_date(tmp_path, monkeypatch):
    """V4-T7: events[] is the full dated status-change history for a symbol
    (a row is an event when status != prev_status, or on first appearance);
    curator_delta summarizes the latest night's moves vs. the prior night."""
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    d1, d2, d3 = "2026-07-06", "2026-07-08", "2026-07-09"
    try:
        from manas_os.agents import _shared

        _shared.ensure_agent_tables(conn)
        conn.execute(
            "INSERT INTO agent_watchlist (scan_date, symbol, tier, status, prev_status, reason, miss_streak) "
            "VALUES (?, 'NCC', 'PASSED', 'PROMOTE', NULL, 'IPO base tightening, RS 84', 0)",
            (d1,),
        )
        # holds at d2 -- status == prev_status, should NOT appear as an event
        conn.execute(
            "INSERT INTO agent_watchlist (scan_date, symbol, tier, status, prev_status, reason, miss_streak) "
            "VALUES (?, 'NCC', 'PASSED', 'HOLD', 'HOLD', 'still coiling', 0)",
            (d2,),
        )
        # real transition at d2 too, seeded separately below via d3 PROMOTE
        conn.execute(
            "INSERT INTO agent_watchlist (scan_date, symbol, tier, status, prev_status, reason, miss_streak) "
            "VALUES (?, 'NCC', 'PASSED', 'PROMOTE', 'HOLD', 'double inside bar', 0)",
            (d3,),
        )
        # a second symbol dropped at d3 -- should show in curator_delta.dropped
        conn.execute(
            "INSERT INTO agent_watchlist (scan_date, symbol, tier, status, prev_status, reason, miss_streak) "
            "VALUES (?, 'BSOFT', 'PASSED', 'DROP', 'HOLD', 'broke 21EMA on volume', 0)",
            (d3,),
        )
        conn.commit()
    finally:
        conn.close()

    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/watchlist", params={"date": d3})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["available"] is True
    rows_by_symbol = {r["symbol"]: r for r in payload["rows"]}
    ncc = rows_by_symbol["NCC"]
    assert [e["action"] for e in ncc["events"]] == ["ADDED", "PROMOTE"]
    assert ncc["events"][0]["date"] == d1
    assert ncc["events"][1]["date"] == d3
    assert "double inside bar" in ncc["events"][1]["reason"]

    # DROP rows still render (DROPPED section of the wireframe)
    assert "BSOFT" in rows_by_symbol
    assert rows_by_symbol["BSOFT"]["status"] == "DROP"

    assert payload["curator_delta"] == {
        "added": [],
        "promoted": ["NCC"],
        "demoted": [],
        "dropped": ["BSOFT"],
    }


def test_desk_watchlist_active_count_excludes_hard_near_miss_noise(tmp_path, monkeypatch):
    """V4-T7: pool_summary.watchlist and the ACTIVE definition must exclude
    NEAR_MISS(hard:*) tier rows -- gate-failure logging that never reached
    the debate/Curator -- so the count reflects the living watchlist, not
    the whole nightly scan pool."""
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        from manas_os.agents import _shared

        _shared.ensure_agent_tables(conn)
        conn.execute(
            "INSERT INTO agent_watchlist (scan_date, symbol, tier, status, prev_status, reason, miss_streak) "
            "VALUES (?, 'REAL1', 'PASSED', 'PROMOTE', NULL, 'chair verdict TAKE', 0)",
            (AS_OF,),
        )
        conn.execute(
            "INSERT INTO agent_watchlist (scan_date, symbol, tier, status, prev_status, reason, miss_streak) "
            "VALUES (?, 'REAL2', 'NEAR_MISS', 'HOLD', NULL, 'chair verdict SKIP', 0)",
            (AS_OF,),
        )
        for i in range(50):
            conn.execute(
                "INSERT INTO agent_watchlist (scan_date, symbol, tier, status, prev_status, reason, miss_streak) "
                "VALUES (?, ?, 'NEAR_MISS(hard:tradability)', 'HOLD', NULL, 'hard gate failure', 0)",
                (AS_OF, f"NOISE{i}"),
            )
        conn.commit()
    finally:
        conn.close()

    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/watchlist", params={"date": AS_OF})
    payload = resp.json()
    assert payload["available"] is True
    assert {r["symbol"] for r in payload["rows"]} == {"REAL1", "REAL2"}


def test_desk_watchlist_add_and_remove_endpoints(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    conn.execute(
        "INSERT INTO daily_prices (symbol, trade_date, close) VALUES ('MANUAL1', ?, 100)",
        (AS_OF,),
    )
    conn.commit()
    conn.close()
    client = _client(db_path, monkeypatch)

    resp = client.post("/api/desk/watchlist/add", json={"symbol": "manual1", "reason": "liked the base", "scan_date": AS_OF})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["symbol"] == "MANUAL1"
    assert body["status"] == "ADDED"
    assert body["reason"] == "user: liked the base"

    resp = client.get("/api/desk/watchlist", params={"date": AS_OF})
    payload = resp.json()
    row = next(r for r in payload["rows"] if r["symbol"] == "MANUAL1")
    assert row["tier"] == "USER"
    assert row["status"] == "ADDED"
    assert row["events"][-1]["action"] == "ADDED"
    assert row["events"][-1]["reason"] == "user: liked the base"

    resp = client.post("/api/desk/watchlist/remove", json={"symbol": "MANUAL1", "reason": "thesis void", "scan_date": AS_OF})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "DROP"
    assert body["reason"] == "user: thesis void"

    resp = client.get("/api/desk/watchlist", params={"date": AS_OF})
    payload = resp.json()
    row = next(r for r in payload["rows"] if r["symbol"] == "MANUAL1")
    assert row["status"] == "DROP"
    assert row["events"][-1]["action"] == "DROP"
    assert row["events"][-1]["reason"] == "user: thesis void"

    resp = client.post("/api/desk/watchlist/add", json={"symbol": ""})
    assert resp.status_code == 400


def test_desk_watchlist_add_rejects_injection_shaped_symbol(tmp_path, monkeypatch):
    """B2: junk/injection-shaped input (e.g. from a prior bug/fuzzing) must be
    rejected with 400, not persisted as a literal agent_watchlist row."""
    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    client = _client(db_path, monkeypatch)

    resp = client.post(
        "/api/desk/watchlist/add",
        json={"symbol": "BAD;DROP TABLE X;--", "scan_date": AS_OF},
    )
    assert resp.status_code == 400

    resp = client.post(
        "/api/desk/watchlist/remove",
        json={"symbol": "BAD;DROP TABLE X;--", "scan_date": AS_OF},
    )
    assert resp.status_code == 400


def test_desk_watchlist_add_rejects_symbol_not_in_universe(tmp_path, monkeypatch):
    """B2: a well-formed but nonexistent symbol (not in daily_prices) must
    also be rejected with 400."""
    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    client = _client(db_path, monkeypatch)

    resp = client.post(
        "/api/desk/watchlist/add",
        json={"symbol": "NOTAREALSYMBOL", "scan_date": AS_OF},
    )
    assert resp.status_code == 400


def test_desk_watchlist_empty_date_is_honest(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/watchlist", params={"date": "2026-01-01"})
    assert resp.status_code == 200
    # C4 (2026-07-18): empty Curator list now carries gate_passed_candidates so the
    # guided flow never points WATCH at an empty room; empty DB => empty list.
    assert resp.json() == {
        "available": False,
        "scan_date": "2026-01-01",
        "rows": [],
        "curator_delta": None,
        "gate_passed_candidates": [],
    }


# --- STRONG START / ARORA FOCUS LIST (design/STRONG_START_FOCUS_SPEC.md) ---

def _insert_bars(conn, symbol, bars):
    rows = [
        (symbol, b["date"], "EQ", b.get("open"), b.get("high"), b.get("low"), b.get("close"),
         b.get("prev_close"), b.get("volume"))
        for b in bars
    ]
    conn.executemany(
        "INSERT OR REPLACE INTO daily_prices (symbol, trade_date, series, open, high, low, "
        "close, prev_close, volume) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()


def _qualifying_bars(as_of_dates):
    """66 real trading dates: 45-day climb 100->130 with one purple-dot day,
    20 flat days at 130 (tight 20DMA), then a final SS gap-up-hold day.
    Matches the fixture verified against arora_strong_start_qualifies
    directly (SS=True, RVOL20=2.5, pct_up_65d_low~33%, 1 purple dot,
    dist_20dma~2.2% vs an ADR-scaled ceiling ~4.8%)."""
    assert len(as_of_dates) == 66
    bars = []
    for i in range(1, 46):
        close = 100 + (i - 1) * (30 / 44)
        prev = bars[-1]["close"] if bars else close - 0.5
        bars.append({"date": as_of_dates[i - 1], "open": close - 0.5, "high": close + 1,
                     "low": close - 1, "close": close, "prev_close": prev, "volume": 100000})
    bars[19] = {**bars[19], "close": bars[18]["close"] * 1.06, "prev_close": bars[18]["close"], "volume": 600000}
    bars[19]["high"] = bars[19]["close"] + 1
    bars[19]["low"] = bars[19]["close"] - 1
    for i in range(20, 45):
        bars[i]["prev_close"] = bars[i - 1]["close"]
    for j in range(1, 21):
        close = 130.0
        bars.append({"date": as_of_dates[44 + j], "open": close, "high": close + 1,
                     "low": close - 1, "close": close, "prev_close": bars[-1]["close"], "volume": 100000})
    prev_close = bars[-1]["close"]
    bars.append({"date": as_of_dates[65], "open": prev_close + 2, "high": prev_close + 4,
                 "low": prev_close + 0.5, "close": prev_close + 3, "prev_close": prev_close, "volume": 250000})
    return bars


def _flat_bars(as_of_dates):
    """66 flat days -- no SS, RVOL~1.0, ~0% up-from-low, zero purple dots.
    Fails every ARORA condition; also a valid non-qualifying symbol for the
    llm-must-qualify 422 test."""
    return [
        {"date": d, "open": 100.0, "high": 100.5, "low": 99.5, "close": 100.0,
         "prev_close": 100.0, "volume": 100000}
        for d in as_of_dates
    ]


def test_focus_list_add_remove_and_get_roundtrip(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    dates = trading_dates(66)
    _insert_bars(conn, "GOODQ", _qualifying_bars(dates))
    conn.close()
    client = _client(db_path, monkeypatch)

    empty = client.get("/api/desk/focus-list", params={"date": dates[-1]})
    assert empty.status_code == 200
    assert empty.json()["rows"] == []

    added = client.post("/api/desk/focus-list/add", json={"symbol": "goodq", "source": "user", "reason": "liked it"})
    assert added.status_code == 200
    body = added.json()
    assert body == {"ok": True, "symbol": "GOODQ", "source": "user", "reason": "liked it"}

    got = client.get("/api/desk/focus-list", params={"date": dates[-1]})
    assert got.status_code == 200
    rows = got.json()["rows"]
    assert len(rows) == 1
    row = rows[0]
    assert row["symbol"] == "GOODQ"
    assert row["ss_flag"] is True
    assert row["rvol20"] == 2.5
    assert row["purple_dot_count"] == 1
    assert row["arora_qualifies"] is True
    assert row["source"] == "user"
    assert row["reason"] == "liked it"

    removed = client.post("/api/desk/focus-list/remove", json={"symbol": "GOODQ"})
    assert removed.status_code == 200
    assert removed.json() == {"ok": True, "symbol": "GOODQ", "active": False}

    after_remove = client.get("/api/desk/focus-list", params={"date": dates[-1]})
    assert after_remove.json()["rows"] == []


def test_focus_list_llm_push_requires_arora_qualify(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    dates = trading_dates(66)
    _insert_bars(conn, "GOODQ", _qualifying_bars(dates))
    _insert_bars(conn, "FLATQ", _flat_bars(dates))
    conn.close()
    client = _client(db_path, monkeypatch)

    ok = client.post("/api/desk/focus-list/add", json={"symbol": "GOODQ", "source": "llm"})
    assert ok.status_code == 200
    assert ok.json()["source"] == "llm"

    blocked = client.post("/api/desk/focus-list/add", json={"symbol": "FLATQ", "source": "llm"})
    assert blocked.status_code == 422
    detail = blocked.json()["detail"]
    assert detail["fails"]  # the failing-condition reasons ride along

    # a blocked llm push must not have been persisted
    rows = client.get("/api/desk/focus-list", params={"date": dates[-1]}).json()["rows"]
    assert {r["symbol"] for r in rows} == {"GOODQ"}


def test_focus_list_add_rejects_bad_symbol_and_unknown_symbol(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    client = _client(db_path, monkeypatch)

    bad_shape = client.post("/api/desk/focus-list/add", json={"symbol": "BAD;DROP TABLE X;--", "source": "user"})
    assert bad_shape.status_code == 400

    unknown = client.post("/api/desk/focus-list/add", json={"symbol": "NOTAREALSYMBOL", "source": "user"})
    assert unknown.status_code == 400

    bad_source = client.post("/api/desk/focus-list/add", json={"symbol": "ACME", "source": "robot"})
    assert bad_source.status_code == 400


def _seed_stock_industry_rs(db_path, run_date, rows):
    """Seed the persisted stock_industry_rs table (the drill-down endpoints
    migrated from live-CSV reads to this table; chartsmaze.run() is its one
    writer in production)."""
    conn = db.init_db(db_path)
    try:
        conn.executemany(
            "INSERT OR REPLACE INTO stock_industry_rs (snapshot_date, ticker, industry, rs) "
            "VALUES (?, ?, ?, ?)",
            [(run_date, ticker, industry, rs) for ticker, industry, rs in rows],
        )
        conn.commit()
    finally:
        conn.close()


def test_desk_market_sector_stocks_returns_enriched_rs_rows(tmp_path, monkeypatch):
    """SECTOR/THEME DRILL-DOWN: /api/desk/market/sector-stocks reuses the
    ChartsMaze RS membership machinery and joins daily_prices + features_daily
    for close, 1D%, EMA-stack state, and a delivery flag, sorted RS desc."""
    from manas_os.sources import chartsmaze

    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        insert_price_ramp(conn, symbol="MARUTI", n=60, start=100.0, step=1.0, delivery=70.0, end=AS_OF)
        insert_price_ramp(conn, symbol="TVSMOTOR", n=60, start=50.0, step=-0.5, delivery=20.0, end=AS_OF)
        # MARUTI: bullish Lead stack (close above a rising EMA10>EMA21>EMA50).
        conn.execute(
            "INSERT OR REPLACE INTO features_daily (symbol, trade_date, feature_json) VALUES (?, ?, ?)",
            ("MARUTI", AS_OF, json.dumps({"ema10": 150.0, "ema21": 140.0, "ema50": 120.0})),
        )
        # TVSMOTOR: bearish Lag stack (close below a falling EMA10<EMA21<EMA50).
        conn.execute(
            "INSERT OR REPLACE INTO features_daily (symbol, trade_date, feature_json) VALUES (?, ?, ?)",
            ("TVSMOTOR", AS_OF, json.dumps({"ema10": 25.0, "ema21": 30.0, "ema50": 35.0})),
        )
        conn.commit()
    finally:
        conn.close()

    _seed_stock_industry_rs(
        db_path, AS_OF,
        [("MARUTI", "Auto Manufacturers", 95), ("TVSMOTOR", "Auto Manufacturers", 40)],
    )

    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/market/sector-stocks", params={"sector": "NIFTY AUTO", "date": AS_OF})
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is True
    assert body["sector_key"] == "AUTO"
    assert [r["symbol"] for r in body["stocks"]] == ["MARUTI", "TVSMOTOR"]  # RS desc

    maruti = body["stocks"][0]
    assert maruti["rs"] == 95.0
    assert maruti["close"] is not None
    assert maruti["pct_1d"] is not None
    assert maruti["ema_state"] == "lead"
    assert maruti["delivery_flag"] is True

    tvsmotor = body["stocks"][1]
    assert tvsmotor["ema_state"] == "lag"
    assert tvsmotor["delivery_flag"] is False


def test_desk_market_sector_stocks_honest_empty_states(tmp_path, monkeypatch):
    """No ChartsMaze RS history at all, and a sector with no membership
    mapping, must both come back available=False with an empty stocks list —
    never a 500 or a silently-wrong row."""
    from manas_os.sources import chartsmaze

    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    monkeypatch.setattr(chartsmaze, "chartsmaze_dir", lambda: tmp_path / "no-such-dir")
    client = _client(db_path, monkeypatch)

    resp = client.get("/api/desk/market/sector-stocks", params={"sector": "NIFTY AUTO", "date": AS_OF})
    assert resp.status_code == 200
    assert resp.json() == {
        "available": False, "sector": "NIFTY AUTO", "sector_key": "AUTO", "stocks": [], "count": 0,
    }

    _seed_stock_industry_rs(db_path, AS_OF, [("MARUTI", "Auto Manufacturers", 95)])
    client2 = _client(db_path, monkeypatch)
    resp2 = client2.get("/api/desk/market/sector-stocks", params={"sector": "NOT A REAL SECTOR", "date": AS_OF})
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert body2["available"] is False
    assert body2["stocks"] == []


def test_desk_market_sector_stocks_resolves_all_label_vocabularies(tmp_path, monkeypatch):
    """The `sector` query param must resolve identically to the same
    canonical key (and the same stock rows) whichever vocabulary the caller
    uses: raw/aliased NSE index name, canonical sector key, ChartsMaze
    sector label, or a raw ChartsMaze Basic Industry name — the bridge
    _resolve_sector_key() in app.py tries in that order."""
    from manas_os.sources import chartsmaze

    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        insert_price_ramp(conn, symbol="MARUTI", n=60, start=100.0, step=1.0, delivery=70.0, end=AS_OF)
        conn.commit()
    finally:
        conn.close()

    _seed_stock_industry_rs(db_path, AS_OF, [("MARUTI", "Auto Manufacturers", 95)])

    for label in ("NIFTY AUTO", "Nifty Auto", "AUTO", "Auto", "Auto Manufacturers"):
        client = _client(db_path, monkeypatch)
        resp = client.get("/api/desk/market/sector-stocks", params={"sector": label, "date": AS_OF})
        assert resp.status_code == 200
        body = resp.json()
        assert body["sector_key"] == "AUTO", label
        assert body["available"] is True, label
        assert [r["symbol"] for r in body["stocks"]] == ["MARUTI"], label


def test_desk_focus_returns_themes_and_watches(tmp_path, monkeypatch):
    """FOCUS layer endpoint: rolls up discovery_bucket + screener_hits +
    industry_metrics into ranked theme rows plus IPO/EP watch shortlists."""
    import json as _json

    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS discovery_bucket ("
            "scan_date TEXT NOT NULL, symbol TEXT NOT NULL, "
            "archetypes_json TEXT NOT NULL, metrics_json TEXT NOT NULL, "
            "created_at TEXT DEFAULT (datetime('now')), "
            "PRIMARY KEY (scan_date, symbol))"
        )
        metrics = {"adr20": 5.0, "purple_dot_count_60d": 3, "pct_up_from_65d_low": 70.0, "momentum_63d": 40.0}
        for sym in ("CHEMA", "CHEMB", "CHEMC"):
            conn.execute(
                "INSERT INTO discovery_bucket (scan_date, symbol, archetypes_json, metrics_json) VALUES (?, ?, ?, ?)",
                (AS_OF, sym, _json.dumps(["persistent_momentum"]), _json.dumps(metrics)),
            )
            conn.execute(
                "INSERT INTO screener_hits (trade_date, symbol, screener, basic_industry, rs_rating) VALUES (?, ?, ?, ?, ?)",
                (AS_OF, sym, "vcp", "Chemicals Specialty", 85.0),
            )
        conn.execute(
            "INSERT INTO industry_metrics (snapshot_date, name, perf_1m, perf_1w, num_stocks) VALUES (?, ?, ?, ?, ?)",
            (AS_OF, "Chemicals Specialty", 6.5, 1.2, 110),
        )
        conn.commit()
        from manas_os.scanner import focus as scanner_focus
        scanner_focus.run(conn, AS_OF)
    finally:
        conn.close()

    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/focus", params={"date": AS_OF})
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is True
    assert body["as_of"] == AS_OF
    assert body["themes"][0]["industry"] == "Chemicals Specialty"
    assert body["themes"][0]["member_count"] == 3
    assert "top_stocks" in body["themes"][0]
    assert isinstance(body["ipo_watch"], list)
    assert isinstance(body["ep_watch"], list)


def test_desk_focus_honest_empty_state(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/focus", params={"date": AS_OF})
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is False
    assert body["themes"] == []
    assert body["reason"]


def test_desk_focus_returns_persisted_top5_not_all_recomputed_themes(tmp_path, monkeypatch):
    """T4: the nightly pipeline persists only the top-5 focus_themes rows
    (scanner_focus.persist_focus, TOP_THEMES=5) but a naive endpoint that
    always recomputes can surface more than 5 (up to 13 in the real DB).
    When rows are persisted for the date, the endpoint must return exactly
    those persisted rows, not a fresh recompute."""
    import json as _json

    from manas_os.scanner import focus as scanner_focus

    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        scanner_focus.ensure_schema(conn)
        # 8 persisted-looking rows written directly, but only 5 are actually
        # in focus_themes (as persist_focus would truncate to TOP_THEMES).
        for i in range(1, 6):
            industry = f"Industry{i}"
            conn.execute(
                "INSERT INTO focus_themes (scan_date, industry, rank, score_json) VALUES (?, ?, ?, ?)",
                (AS_OF, industry, i, _json.dumps({"industry": industry, "rank": i, "score": 100 - i})),
            )
        conn.commit()
    finally:
        conn.close()

    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/focus", params={"date": AS_OF})
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is True
    assert len(body["themes"]) == 5
    assert [t["industry"] for t in body["themes"]] == [f"Industry{i}" for i in range(1, 6)]


def test_desk_focus_no_date_resolves_to_latest_persisted_top5(tmp_path, monkeypatch):
    """T4: the no-date path must resolve to the latest persisted date's
    top-5 (same as the explicit-date path), not silently fall through to a
    live recompute that can return more than 5 qualifying themes."""
    from manas_os.scanner import focus as scanner_focus

    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        scanner_focus.ensure_schema(conn)
        for i in range(1, 6):
            industry = f"Industry{i}"
            conn.execute(
                "INSERT INTO focus_themes (scan_date, industry, rank, score_json) VALUES (?, ?, ?, ?)",
                (AS_OF, industry, i, json.dumps({"industry": industry, "rank": i, "score": 100 - i})),
            )
        conn.commit()
    finally:
        conn.close()

    client = _client(db_path, monkeypatch)
    explicit = client.get("/api/desk/focus", params={"date": AS_OF})
    no_date = client.get("/api/desk/focus")
    assert explicit.status_code == 200 and no_date.status_code == 200
    explicit_body, no_date_body = explicit.json(), no_date.json()
    assert explicit_body["available"] is True and len(explicit_body["themes"]) == 5
    assert no_date_body["available"] is True
    assert no_date_body["as_of"] == AS_OF
    assert len(no_date_body["themes"]) == 5


# --------------------------------------------------------------------------
# Chartink-style screener + push-to-debate (user order 2026-07-11 ~09:30)
# --------------------------------------------------------------------------

def _seed_screener_prices(conn):
    days = trading_dates(40, end="2026-02-09")
    for d in days:
        conn.execute(
            "INSERT OR REPLACE INTO daily_prices (symbol, trade_date, series, open, high, low, "
            "close, prev_close, volume, delivery_qty, delivery_pct) VALUES "
            "('MOVER', ?, 'EQ', 100, 104, 96, 100, 100, 500000, 100, 50.0)",
            (d,),
        )
        conn.execute(
            "INSERT OR REPLACE INTO daily_prices (symbol, trade_date, series, open, high, low, "
            "close, prev_close, volume, delivery_qty, delivery_pct) VALUES "
            "('FLAT', ?, 'EQ', 50, 51, 49, 50, 50, 200000, 100, 30.0)",
            (d,),
        )
    # last day: MOVER bursts +8% on high volume (a TODAYS_MOVERS hit); FLAT stays flat
    conn.execute(
        "INSERT OR REPLACE INTO daily_prices (symbol, trade_date, series, open, high, low, "
        "close, prev_close, volume, delivery_qty, delivery_pct) VALUES "
        "('MOVER', '2026-02-10', 'EQ', 105, 112, 104, 108, 100, 3000000, 100, 60.0)"
    )
    conn.execute(
        "INSERT OR REPLACE INTO daily_prices (symbol, trade_date, series, open, high, low, "
        "close, prev_close, volume, delivery_qty, delivery_pct) VALUES "
        "('FLAT', '2026-02-10', 'EQ', 50, 51, 49, 50, 50, 200000, 100, 30.0)"
    )
    conn.commit()


def test_desk_screener_presets_lists_todays_movers(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/screener/presets")
    assert resp.status_code == 200
    names = [p["name"] for p in resp.json()["presets"]]
    assert "TODAYS_MOVERS" in names


def test_desk_screener_preset_and_conditions_filter_correctly(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        _seed_screener_prices(conn)
    finally:
        conn.close()
    client = _client(db_path, monkeypatch)

    preset_resp = client.get("/api/desk/screener", params={"date": "2026-02-10", "preset": "TODAYS_MOVERS"})
    assert preset_resp.status_code == 200
    preset_body = preset_resp.json()
    assert preset_body["available"] is True
    assert [r["symbol"] for r in preset_body["rows"]] == ["MOVER"]

    manual = client.get("/api/desk/screener", params={
        "date": "2026-02-10",
        "conditions": json.dumps([{"field": "pct_change_1d", "op": "gte", "value": 5.0}]),
    })
    assert manual.status_code == 200
    manual_body = manual.json()
    assert [r["symbol"] for r in manual_body["rows"]] == ["MOVER"]
    assert manual_body["universe_size"] == 2

    bad_preset = client.get("/api/desk/screener", params={"date": "2026-02-10", "preset": "NOPE"})
    assert bad_preset.status_code == 400


def test_desk_user_screens_save_list_delete(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    client = _client(db_path, monkeypatch)

    save = client.post("/api/desk/user_screens", json={
        "name": "my-vcp",
        "conditions": [{"field": "adr20", "op": "gte", "value": 3.0}],
    })
    assert save.status_code == 200

    listed = client.get("/api/desk/user_screens")
    assert listed.status_code == 200
    names = [s["name"] for s in listed.json()["screens"]]
    assert "my-vcp" in names

    deleted = client.delete("/api/desk/user_screens/my-vcp")
    assert deleted.status_code == 200
    listed2 = client.get("/api/desk/user_screens")
    assert "my-vcp" not in [s["name"] for s in listed2.json()["screens"]]


def test_desk_debate_push_requires_symbol_and_404s_without_prices(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    client = _client(db_path, monkeypatch)

    missing = client.post("/api/desk/debate/push", json={"date": AS_OF})
    assert missing.status_code == 400

    no_prices = client.post("/api/desk/debate/push", json={"symbol": "NOPE", "date": AS_OF})
    assert no_prices.status_code == 404


def test_desk_debate_push_creates_a_debate_card(tmp_path, monkeypatch):
    """Push-to-debate: on-demand debate of a symbol lands on GET
    /api/desk/debate flagged source:"user_pushed"."""
    from manas_os.agents import debate as agent_debate

    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        insert_price_ramp(conn, symbol="PUSHED", n=210, end=AS_OF)
    finally:
        conn.close()

    def fake_get(key, default=None):
        values = {
            "agents.enabled": True,
            "agents.api_key": "test-key",
            "agents.models": ["mock/model"],
            "agents.max_tokens": 1200,
        }
        return values.get(key, default)

    monkeypatch.setattr(agent_debate.config, "get", fake_get)

    class FakeClient:
        model = "mock/model"

        def chat(self, *, system, user, **kw):
            return json.dumps([{
                "symbol": "PUSHED", "verdict": "TAKE", "conviction": 4, "rank": 1,
                "lens_scores": {}, "bull_case": "strong", "bear_case": "extended",
                "reasoning": "pushed by user",
            }]), self.model

    monkeypatch.setattr(agent_debate, "OpenRouterClient", lambda **kw: FakeClient())

    class ChairFakeClient(FakeClient):
        def chat(self, *, system, user, **kw):
            return json.dumps([{"symbol": "PUSHED", "verdict": "TAKE", "strike": None}]), self.model

    monkeypatch.setattr("manas_os.agents.chair.OpenRouterClient", lambda **kw: ChairFakeClient())
    monkeypatch.setattr("manas_os.agents.sizer.OpenRouterClient", lambda **kw: ChairFakeClient())

    client = _client(db_path, monkeypatch)
    resp = client.post("/api/desk/debate/push", json={"symbol": "pushed", "date": AS_OF})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in ("ok", "partial")
    assert body["symbol"] == "PUSHED"
    assert body["verdicts"] >= 1

    debate_resp = client.get("/api/desk/debate", params={"date": body["as_of"]})
    assert debate_resp.status_code == 200
    cards = {c["symbol"]: c for c in debate_resp.json()["symbols"]}
    assert "PUSHED" in cards
    assert cards["PUSHED"]["source"] == "user_pushed"


def test_pipeline_status_idle_shape_before_any_run(tmp_path, monkeypatch):
    """V4-T2: idle state (no run yet) — running False, no crash on the new
    progress fields, honest null/0 defaults."""
    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    client = _client(db_path, monkeypatch)

    resp = client.get("/api/pipeline/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["running"] is False
    assert body["total_stages"] > 0
    assert body["stage_index"] == 0
    assert body["eta_seconds"] is None
    assert body["data_live_hint"] is None
    assert body["last_run"] is None


def test_pipeline_status_mid_run_reports_stage_progress(tmp_path, monkeypatch):
    """V4-T2: while a run is in flight, stage_index/total_stages/eta_seconds/
    data_live_hint are derived from the live pipeline module state (fixture
    fakes a run in progress by writing straight to app's _PIPELINE_STATUS,
    the same dict _run_pipeline_thread mutates)."""
    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    client = _client(db_path, monkeypatch)

    from manas_os.cli import _load_stages

    stage_names = [name for name, _fn in _load_stages()]
    assert len(stage_names) >= 3
    halfway = len(stage_names) // 2

    with api_app._PIPELINE_LOCK:
        api_app._PIPELINE_STATUS.update({
            "running": True,
            "run_date": AS_OF,
            "current_stage": stage_names[halfway],
            "stages": [{"name": n, "status": "ok"} for n in stage_names[:halfway]],
            "started_at": datetime.now().timestamp() - 60.0,
            "finished_at": None,
            "error": None,
        })
    try:
        resp = client.get("/api/pipeline/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["running"] is True
        assert body["total_stages"] == len(stage_names)
        assert body["stage_index"] == halfway + 1
        assert body["current_stage"] == stage_names[halfway]
        assert body["eta_seconds"] is not None and body["eta_seconds"] >= 0
        assert body["data_live_hint"] is not None and "data live ~" in body["data_live_hint"]
    finally:
        with api_app._PIPELINE_LOCK:
            api_app._PIPELINE_STATUS.update({
                "running": False, "run_date": None, "current_stage": None,
                "stages": [], "started_at": None, "last_progress_at": None,
                "finished_at": None, "error": None,
            })


def test_dist_build_sha_reads_the_served_vite_entry_hash(tmp_path):
    index = tmp_path / "index.html"
    index.write_text(
        '<script type="module" src="/assets/index-AbC_123-x.js"></script>',
        encoding="utf-8",
    )

    assert api_app._get_dist_build_sha(index) == "AbC_123-x"


def test_static_index_is_no_store_while_hashed_assets_are_immutable():
    client = TestClient(api_app.app)
    index = client.get("/")

    assert index.status_code == 200
    assert index.headers["cache-control"] == "no-store"
    asset_path = re.search(r'src="([^"]*/assets/[^"]+\.js)"', index.text).group(1)

    asset = client.get(asset_path)
    assert asset.status_code == 200
    assert asset.headers["cache-control"] == "public, max-age=31536000, immutable"


def test_admin_health_returns_defensive_operational_shape(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    conn.execute(
        "INSERT INTO daily_prices(symbol, trade_date, series, close) VALUES('AAA', '2026-06-30', 'EQ', 100)"
    )
    conn.execute(
        "INSERT INTO scan_candidates(scan_date, symbol, setup, readiness, grade) "
        "VALUES('2026-06-30', 'AAA', 'ep', 80, 'A')"
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(api_app, "_BUILD_SHA", "AbC_123-x")
    from manas_os.providers import fyers_auth

    monkeypatch.setattr(fyers_auth, "get_access_token", lambda: "test-token")
    client = _client(db_path, monkeypatch)

    response = client.get("/api/admin/health")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "build_sha", "port_owner_pid", "trust", "build_stale", "data_freshness",
        "ops_freshness", "pipeline", "fyers", "jobs", "db",
    }
    assert body["build_sha"] == "AbC_123-x"
    assert body["port_owner_pid"] == os.getpid()
    assert set(body["data_freshness"]) >= {
        "latest_price_date", "latest_scan_date", "last_trading_day", "is_stale"
    }
    assert set(body["ops_freshness"]) >= {"latest_price_date", "expected_last_session", "stale"}
    assert set(body["pipeline"]) >= {"running", "current_stage", "started_at", "stuck"}
    assert set(body["fyers"]) == {"token_ready"}
    assert set(body["jobs"]) == {"running_count", "stale_count"}
    assert set(body["db"]) == {"size_mb", "wal"}
    assert isinstance(body["build_stale"], bool)
    assert set(body["trust"]) == {"verdict", "reason"}
    assert body["trust"]["verdict"] in {"TRUSTED", "DEGRADED", "STALE"}

    def fail_fyers_probe():
        raise RuntimeError("fyers probe unavailable")

    monkeypatch.setattr(api_app, "_health_fyers", fail_fyers_probe)
    degraded = client.get("/api/admin/health").json()
    assert degraded["fyers"] == {"error": "fyers probe unavailable"}
    assert "error" not in degraded["data_freshness"]


def test_admin_health_trust_verdict_is_trusted_when_data_current_and_nothing_stuck(tmp_path, monkeypatch):
    """USABILITY_UX_AUDIT_2026-07-19.md defect #9: operational/data/model/
    build statuses competed for attention with no single verdict. TRUSTED
    requires data fresh per ops_freshness.check_freshness, no stuck
    pipeline/jobs, and a build matching the current repo HEAD."""
    from datetime import date as _date, datetime as _datetime

    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    conn.execute(
        "INSERT INTO daily_prices(symbol, trade_date, series, close) VALUES('AAA', ?, 'EQ', 100)",
        (AS_OF,),
    )
    conn.commit()
    conn.close()

    from manas_os import ops_freshness
    from manas_os.providers import fyers_auth

    monkeypatch.setattr(ops_freshness, "_now_ist", lambda: _datetime(2026, 6, 30, 20, 0, tzinfo=ops_freshness._IST))
    monkeypatch.setattr(fyers_auth, "get_access_token", lambda: None)
    monkeypatch.setattr(api_app, "_is_build_stale", lambda: False)
    client = _client(db_path, monkeypatch)

    body = client.get("/api/admin/health").json()

    assert body["ops_freshness"]["stale"] is False
    assert body["build_stale"] is False
    assert body["trust"] == {"verdict": "TRUSTED", "reason": f"Data current through {AS_OF}."}


def test_admin_health_trust_verdict_is_stale_when_ops_freshness_reports_stale(tmp_path, monkeypatch):
    from datetime import date as _date, datetime as _datetime

    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    conn.execute(
        "INSERT INTO daily_prices(symbol, trade_date, series, close) VALUES('AAA', ?, 'EQ', 100)",
        (AS_OF,),
    )
    conn.commit()
    conn.close()

    from manas_os import ops_freshness
    from manas_os.providers import fyers_auth

    # "today" is well past AS_OF -- the price row is stale by ops_freshness's
    # own check, regardless of pipeline/jobs/build state.
    monkeypatch.setattr(ops_freshness, "_now_ist", lambda: _datetime(2026, 7, 6, 20, 0, tzinfo=ops_freshness._IST))
    monkeypatch.setattr(fyers_auth, "get_access_token", lambda: None)
    monkeypatch.setattr(api_app, "_is_build_stale", lambda: False)
    client = _client(db_path, monkeypatch)

    body = client.get("/api/admin/health").json()

    assert body["ops_freshness"]["stale"] is True
    assert body["trust"]["verdict"] == "STALE"
    assert AS_OF in body["trust"]["reason"]


def test_admin_health_trust_verdict_is_degraded_when_data_fresh_but_a_job_is_stuck(tmp_path, monkeypatch):
    from datetime import date as _date, datetime as _datetime

    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    conn.execute(
        "INSERT INTO daily_prices(symbol, trade_date, series, close) VALUES('AAA', ?, 'EQ', 100)",
        (AS_OF,),
    )
    conn.commit()
    conn.close()

    from manas_os import ops_freshness
    from manas_os.providers import fyers_auth

    monkeypatch.setattr(ops_freshness, "_now_ist", lambda: _datetime(2026, 6, 30, 20, 0, tzinfo=ops_freshness._IST))
    monkeypatch.setattr(fyers_auth, "get_access_token", lambda: None)
    monkeypatch.setattr(api_app, "_is_build_stale", lambda: False)
    monkeypatch.setattr(api_app, "_health_jobs", lambda: {"running_count": 1, "stale_count": 1})
    client = _client(db_path, monkeypatch)

    body = client.get("/api/admin/health").json()

    assert body["ops_freshness"]["stale"] is False
    assert body["trust"]["verdict"] == "DEGRADED"
    assert "stuck" in body["trust"]["reason"].lower()


def test_admin_health_trust_verdict_is_degraded_when_build_is_stale(tmp_path, monkeypatch):
    from datetime import date as _date, datetime as _datetime

    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    conn.execute(
        "INSERT INTO daily_prices(symbol, trade_date, series, close) VALUES('AAA', ?, 'EQ', 100)",
        (AS_OF,),
    )
    conn.commit()
    conn.close()

    from manas_os import ops_freshness
    from manas_os.providers import fyers_auth

    monkeypatch.setattr(ops_freshness, "_now_ist", lambda: _datetime(2026, 6, 30, 20, 0, tzinfo=ops_freshness._IST))
    monkeypatch.setattr(fyers_auth, "get_access_token", lambda: None)
    monkeypatch.setattr(api_app, "_is_build_stale", lambda: True)
    client = _client(db_path, monkeypatch)

    body = client.get("/api/admin/health").json()

    assert body["build_stale"] is True
    assert body["trust"]["verdict"] == "DEGRADED"
    assert "build" in body["trust"]["reason"].lower()


def test_compute_trust_verdict_data_probe_error_counts_as_stale():
    result = api_app._compute_trust_verdict(
        {"error": "db locked"}, {"stuck": False}, {"stale_count": 0}, False,
    )
    assert result["verdict"] == "STALE"


def test_compute_trust_verdict_a_failed_probe_is_degraded_not_silently_dropped():
    result = api_app._compute_trust_verdict(
        {"stale": False, "latest_price_date": AS_OF}, {"error": "boom"}, {"stale_count": 0}, False,
    )
    assert result["verdict"] == "DEGRADED"
    assert "pipeline" in result["reason"].lower()


def test_current_build_sha_recomputes_when_dist_index_html_mtime_moves(tmp_path, monkeypatch):
    """Orchestrator-found defect: _BUILD_SHA used to be computed once at
    process import, so a frontend-only `npm run build` (new asset hash,
    same backend process) never cleared the desk's "new version" bar until
    a manual backend restart. _current_build_sha must pick up a new hash
    once dist/index.html's mtime moves, without a restart."""
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    index_path = dist_dir / "index.html"
    index_path.write_text('<script type="module" src="/assets/index-aaa111.js"></script>', encoding="utf-8")
    os.utime(index_path, (1_700_000_000, 1_700_000_000))

    monkeypatch.setattr(api_app, "_DIST_DIR", dist_dir)
    monkeypatch.setattr(api_app, "_BUILD_SHA", None)
    monkeypatch.setattr(api_app, "_BUILD_SHA_MTIME", None)

    assert api_app._current_build_sha() == "aaa111"
    # Unchanged mtime: cache holds, no error re-reading the same file.
    assert api_app._current_build_sha() == "aaa111"

    # Simulate a frontend-only rebuild: new asset hash, later mtime, same process.
    index_path.write_text('<script type="module" src="/assets/index-bbb222.js"></script>', encoding="utf-8")
    os.utime(index_path, (1_700_000_100, 1_700_000_100))

    assert api_app._current_build_sha() == "bbb222"


def test_current_build_sha_falls_back_to_cache_when_dist_is_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(api_app, "_DIST_DIR", tmp_path / "no-such-dist")
    monkeypatch.setattr(api_app, "_BUILD_SHA", "frozen-sha")
    monkeypatch.setattr(api_app, "_BUILD_SHA_MTIME", None)

    assert api_app._current_build_sha() == "frozen-sha"


def test_account_label_for_import_key_recognizes_known_prefixes_and_reports_unknown_honestly():
    """USABILITY_UX_AUDIT_2026-07-19.md: imported positions told the user to
    act 'in Zerodha' without saying which account. The only importer wired
    today (tools/import_broker.py) prefixes keys 'zerodha-open:'/'zerodha:';
    'zerodha_stmt:'/'cdsl_stmt:' are recognized for forward compatibility.
    Anything else must report honestly, not guess."""
    assert api_app._account_label_for_import_key("zerodha-open:abc123") == "Zerodha (FOU446)"
    assert api_app._account_label_for_import_key("zerodha:abc123") == "Zerodha (FOU446)"
    assert api_app._account_label_for_import_key("zerodha_stmt:abc123") == "Zerodha (FOU446)"
    assert api_app._account_label_for_import_key("cdsl_stmt:abc123") == "CDSL demat"
    assert api_app._account_label_for_import_key("some-other-broker:abc123") == "account unknown"
    assert api_app._account_label_for_import_key(None) == "account unknown"
    assert api_app._account_label_for_import_key("") == "account unknown"


def test_desk_positions_exit_action_sentence_is_the_single_timing_source(tmp_path, monkeypatch):
    """USABILITY_UX_AUDIT_2026-07-19.md defect #4: the MANAGE card badge
    ('EXIT') and the coach line must never carry independent timing
    instructions. action_sentence is the one server-composed string
    carrying verdict+timing+method; the legacy action_line/plain_why
    fields (which also still feed the Telegram coach message untouched)
    stay present alongside it, but the desk card no longer reads them for
    display."""
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        scanner_candidates.ensure_schema(conn)
        insert_price_ramp(conn, symbol="HUDCO", n=210, end=AS_OF)
        dates = trading_dates(20, AS_OF)
        trade_date = dates[0]
        row = conn.execute(
            "SELECT close FROM daily_prices WHERE symbol = 'HUDCO' AND trade_date = ?",
            (trade_date,),
        ).fetchone()
        entry = float(row["close"])
        stop = entry - 5.0
        breach_close = stop - 3.0
        conn.execute(
            "UPDATE daily_prices SET close = ?, high = ?, low = ?, open = ? "
            "WHERE symbol = 'HUDCO' AND trade_date = ?",
            (breach_close, breach_close + 1, breach_close - 1, breach_close + 0.5, AS_OF),
        )
        conn.execute(
            "INSERT INTO journal_trades (trade_date, symbol, setup, entry, stop, qty) "
            "VALUES (?, 'HUDCO', 'Pullback', ?, ?, 100)",
            (trade_date, entry, stop),
        )
        conn.commit()
    finally:
        conn.close()

    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/positions", params={"date": AS_OF})
    assert resp.status_code == 200
    pos = resp.json()["positions"][0]
    assert pos["coach_verdict"] == "EXIT"
    assert pos["urgent"] is True
    assert pos["action_sentence"].startswith("EXIT today near the close (15:00-15:25)")
    assert "sell the full position at market" in pos["action_sentence"]
    assert "stop-breached" in pos["action_sentence"]
    # The legacy Telegram-facing field is untouched and independent.
    assert pos["action_line"].startswith("EXIT TODAY -")
    assert pos["action_sentence"] != pos["action_line"]


def test_desk_positions_imported_holding_reports_account_and_action_sentence(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        insert_price_ramp(conn, symbol="HUDCO", n=210, end=AS_OF)
        first_buy = trading_dates(20, AS_OF)[0]
        conn.execute(
            "CREATE TABLE IF NOT EXISTS broker_open_lots ("
            "symbol TEXT NOT NULL, qty REAL NOT NULL, avg_cost REAL NOT NULL, "
            "first_buy_date TEXT NOT NULL, import_key TEXT NOT NULL UNIQUE)"
        )
        conn.execute(
            "INSERT INTO broker_open_lots (symbol, qty, avg_cost, first_buy_date, import_key) "
            "VALUES ('HUDCO', 10, 100.0, ?, 'zerodha-open:test-account')",
            (first_buy,),
        )
        conn.commit()
    finally:
        conn.close()

    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/positions", params={"date": AS_OF})
    assert resp.status_code == 200
    pos = resp.json()["positions"][0]
    assert pos["account"] == "Zerodha (FOU446)"
    assert pos["action_sentence"]
    if pos["urgent"]:
        assert "in your Zerodha (FOU446) account" in pos["action_sentence"]


def test_desk_positions_imported_holding_unknown_import_key_reports_honestly(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        insert_price_ramp(conn, symbol="HUDCO", n=210, end=AS_OF)
        first_buy = trading_dates(20, AS_OF)[0]
        conn.execute(
            "CREATE TABLE IF NOT EXISTS broker_open_lots ("
            "symbol TEXT NOT NULL, qty REAL NOT NULL, avg_cost REAL NOT NULL, "
            "first_buy_date TEXT NOT NULL, import_key TEXT NOT NULL UNIQUE)"
        )
        conn.execute(
            "INSERT INTO broker_open_lots (symbol, qty, avg_cost, first_buy_date, import_key) "
            "VALUES ('HUDCO', 10, 100.0, ?, 'unknown-broker:xyz')",
            (first_buy,),
        )
        conn.commit()
    finally:
        conn.close()

    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/positions", params={"date": AS_OF})
    assert resp.status_code == 200
    pos = resp.json()["positions"][0]
    assert pos["account"] == "account unknown"


def test_pipeline_run_clears_a_45_minute_silent_guard_and_starts_fresh(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    original_init = db.init_db
    monkeypatch.setattr(db, "init_db", lambda db_path_arg=None: original_init(db_path))

    started_threads = []

    class NoopThread:
        def __init__(self, *, target, args, daemon):
            self.target = target
            self.args = args
            self.daemon = daemon

        def start(self):
            started_threads.append(self)

    monkeypatch.setattr(api_app.threading, "Thread", NoopThread)
    now = time.time()
    with api_app._PIPELINE_LOCK:
        api_app._PIPELINE_STATUS.update({
            "running": True,
            "run_date": "2026-06-29",
            "current_stage": "ingest_bhavcopy",
            "stages": [],
            "started_at": now - (46 * 60),
            "last_progress_at": now - (46 * 60),
            "finished_at": None,
            "error": None,
        })

    try:
        assert api_app._pipeline_is_stuck(dict(api_app._PIPELINE_STATUS), now=now) is True
        recently_progressed = {**api_app._PIPELINE_STATUS, "last_progress_at": now - 60}
        assert api_app._pipeline_is_stuck(recently_progressed, now=now) is False

        response = TestClient(api_app.app).post(
            "/api/pipeline/run", json={"date": AS_OF, "fetch_sources": False}
        )

        assert response.status_code == 200
        body = response.json()
        assert body["started"] is True
        assert body["stale_guard_cleared"] is True
        assert "stale pipeline guard" in body["note"].lower()
        assert len(started_threads) == 1
        with api_app._PIPELINE_LOCK:
            assert api_app._PIPELINE_STATUS["run_date"] == AS_OF
            assert api_app._PIPELINE_STATUS["started_at"] > now
            assert api_app._PIPELINE_STATUS["last_progress_at"] == api_app._PIPELINE_STATUS["started_at"]
            assert started_threads[0].args[3] == api_app._PIPELINE_STATUS["started_at"]
    finally:
        with api_app._PIPELINE_LOCK:
            api_app._PIPELINE_STATUS.update({
                "running": False, "run_date": None, "current_stage": None,
                "stages": [], "started_at": None, "last_progress_at": None,
                "finished_at": None, "error": None,
            })


def test_pipeline_thread_crash_sets_error_and_crashed_stage(tmp_path, monkeypatch):
    """Audit #9: the background update thread used to have no top-level
    except, so an uncaught exception killed the run silently while
    /api/pipeline/status kept showing error=None. Now any exception sets
    _PIPELINE_STATUS["error"] = "<ExcType>: <msg>" and suffixes the current
    stage with ' (crashed)'. Verified end-to-end by running the thread
    inline with _load_stages patched to raise, then reading the status
    endpoint."""
    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    client = _client(db_path, monkeypatch)

    # Force the thread body to blow up the way audit #9 describes: a stage
    # loader that fails. _run_pipeline_thread imports _load_stages lazily, so
    # patching the source module is enough.
    from manas_os import cli as cli_mod

    def _boom():
        raise RuntimeError("stage loader exploded")

    monkeypatch.setattr(cli_mod, "_load_stages", _boom)

    started_at = time.time()
    with api_app._PIPELINE_LOCK:
        api_app._PIPELINE_STATUS.update({
            "running": True, "run_date": AS_OF,
            "current_stage": "starting", "stages": [],
            "started_at": started_at, "last_progress_at": started_at,
            "finished_at": None, "error": None,
        })
    try:
        # Run the thread body inline (it is just a function). The audit fix
        # captures the exception instead of re-raising, so this returns
        # normally and writes the error/crashed stage.
        api_app._run_pipeline_thread(
            AS_OF, fetch_sources=False, job_id=None,
            catch_up=[AS_OF], guard_started_at=started_at,
        )

        with api_app._PIPELINE_LOCK:
            assert api_app._PIPELINE_STATUS["running"] is False
            assert api_app._PIPELINE_STATUS["finished_at"] is not None
            assert api_app._PIPELINE_STATUS["error"] == "RuntimeError: stage loader exploded"
            assert api_app._PIPELINE_STATUS["current_stage"].endswith(" (crashed)")

        # The status endpoint already returns the error field verbatim.
        resp = client.get("/api/pipeline/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["running"] is False
        assert body["error"] == "RuntimeError: stage loader exploded"
        assert body["current_stage"].endswith(" (crashed)")
        assert body["last_run"]["error"] == "RuntimeError: stage loader exploded"
    finally:
        with api_app._PIPELINE_LOCK:
            api_app._PIPELINE_STATUS.update({
                "running": False, "run_date": None, "current_stage": None,
                "stages": [], "started_at": None, "last_progress_at": None,
                "finished_at": None, "error": None,
            })


def test_write_endpoints_return_structured_err_detail_shape(tmp_path, monkeypatch):
    """Audit #4: write endpoints used to raise HTTPException(status, 'plain
    string'); the frontend had no machine-readable cause/action. Now the
    audit-called-out write paths raise detail = _err(...) -> {code, cause,
    action, retryable}. Cover several shapes in one test."""
    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    client = _client(db_path, monkeypatch)

    # Journal add: missing required fields -> 400 with structured detail.
    resp = client.post("/api/journal", json={"symbol": "AAA"})
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert set(detail) == {"code", "cause", "action", "retryable"}
    assert detail["code"] == "validation"
    assert "trade_date" in detail["cause"]
    assert detail["retryable"] is False

    # Positions add: stop >= entry -> 400 invalid_stop.
    resp = client.post(
        "/api/desk/positions",
        json={"symbol": "AAA", "entry": 100.0, "stop": 105.0, "qty": 10, "date": AS_OF},
    )
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert detail["code"] == "invalid_stop"
    assert set(detail) == {"code", "cause", "action", "retryable"}

    # Positions update: missing stop and qty -> 400 validation.
    resp = client.post("/api/desk/positions/1/update", json={})
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert detail["code"] == "validation"
    assert set(detail) == {"code", "cause", "action", "retryable"}

    # Positions close: bad reason_tag -> 400 validation.
    resp = client.post("/api/desk/positions/1/close", json={"exit_price": 100.0, "reason_tag": "nope"})
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert detail["code"] == "validation"
    assert "reason_tag" in detail["cause"]

    # Fyers exchange: exchange_auth_code raises -> 400 token_exchange_failed,
    # retryable=True (paste a fresh code is a meaningful retry).
    from manas_os.providers import fyers_auth

    def _fail(_value):
        raise RuntimeError("expired auth code")

    monkeypatch.setattr(fyers_auth, "exchange_auth_code", _fail)
    resp = client.post("/api/fyers/exchange", json={"value": "deadbeef"})
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert detail["code"] == "token_exchange_failed"
    assert "expired auth code" in detail["cause"]
    assert detail["retryable"] is True
