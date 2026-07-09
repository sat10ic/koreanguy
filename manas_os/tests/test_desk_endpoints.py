import base64
import json

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
            "(scan_date, symbol, setup, setup_family, readiness, grade, entry, stop, target, rr, suggested_qty) "
            "VALUES (?, 'KPIL', 'Pullback', 'base/pattern', 80, 'A', 892.0, 861.5, 953.0, 2.0, 34)",
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


def test_desk_positions_no_open_trades_is_honest(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/positions", params={"date": "2020-01-01"})
    assert resp.status_code == 200
    assert resp.json() == {"run_date": "2020-01-01", "positions": []}
