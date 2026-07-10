import base64
import json
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
        scanner_candidates.ensure_schema(conn)
        conn.execute(
            "INSERT INTO regime_snapshots (snapshot_date, market_mode) VALUES (?, 'SELECTIVE')",
            (AS_OF,),
        )
        conn.execute(
            "INSERT OR REPLACE INTO scan_candidates "
            "(scan_date, symbol, setup, setup_family, readiness, grade, entry, stop, target, rr, "
            "suggested_qty, gates_json) "
            "VALUES (?, 'KPIL', 'Pullback', 'base/pattern', 80, 'A', 892.0, 861.5, 953.0, 2.0, 34, ?)",
            (AS_OF, json.dumps([{"gate": "regime", "pass": True, "reason": None, "evidence": {}}])),
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


def test_desk_positions_no_open_trades_is_honest(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/positions", params={"date": "2020-01-01"})
    assert resp.status_code == 200
    assert resp.json() == {"run_date": "2020-01-01", "positions": []}


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
        "NIFTY LargeMidcap 250",
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


def test_desk_watchlist_empty_date_is_honest(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/watchlist", params={"date": "2026-01-01"})
    assert resp.status_code == 200
    assert resp.json() == {"available": False, "scan_date": "2026-01-01", "rows": []}


def _seed_chartsmaze_rs_csv(tmp_path, run_date, rows):
    """Fabricate a minimal `sector-analytics-Relative Strength-stocks.csv`
    under a dated ChartsMaze folder so `chartsmaze.chartsmaze_dir()` (which
    the sector drill-down endpoints read) sees this run_date."""
    root = tmp_path / "chartsmaze" / run_date / "analytics"
    root.mkdir(parents=True)
    path = root / "sector-analytics-Relative Strength-stocks.csv"
    lines = ["Ticker,Industry,RS"]
    for ticker, industry, rs in rows:
        lines.append(f"{ticker},{industry},{rs}")
    path.write_text("\n".join(lines), encoding="utf-8")
    return tmp_path / "chartsmaze"


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

    root = _seed_chartsmaze_rs_csv(
        tmp_path, AS_OF,
        [("MARUTI", "Auto Manufacturers", 95), ("TVSMOTOR", "Auto Manufacturers", 40)],
    )
    monkeypatch.setattr(chartsmaze, "chartsmaze_dir", lambda: root)

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

    root = _seed_chartsmaze_rs_csv(tmp_path, AS_OF, [("MARUTI", "Auto Manufacturers", 95)])
    monkeypatch.setattr(chartsmaze, "chartsmaze_dir", lambda: root)
    client2 = _client(db_path, monkeypatch)
    resp2 = client2.get("/api/desk/market/sector-stocks", params={"sector": "NOT A REAL SECTOR", "date": AS_OF})
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert body2["available"] is False
    assert body2["stocks"] == []


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
