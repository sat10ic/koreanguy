import json

from fastapi.testclient import TestClient

from manas_os import db
from manas_os.agents import lessons, run_card, signals
from manas_os.api import app as api_app
from manas_os.scanner import candidates as scanner_candidates


AS_OF = "2026-06-30"


def _seed_night(conn):
    scanner_candidates.ensure_schema(conn)
    lessons.ensure_schema(conn)
    signals.ensure_schema(conn)
    conn.execute(
        "INSERT INTO regime_snapshots (snapshot_date, market_mode) VALUES (?, 'SELECTIVE')",
        (AS_OF,),
    )
    conn.execute(
        "INSERT OR REPLACE INTO scan_candidates "
        "(scan_date, symbol, setup, setup_family, readiness, grade, entry, stop, target, rr, "
        "suggested_qty, evidence_json, timing_json, score_breakdown_json, trade_plan_json, "
        "gates_json, rank, rank_of) "
        "VALUES (?, 'AAA', 'Pullback', 'base/pattern', 90, 'A', 100, 95, 112, 2.4, 10, "
        "'[]', '{}', '{}', '{}', '[]', 1, 1)",
        (AS_OF,),
    )
    conn.execute(
        "INSERT OR REPLACE INTO agent_verdicts "
        "(scan_date, symbol, agent, verdict, conviction, rank, reasoning) "
        "VALUES (?, 'AAA', 'mock/model-a', 'TAKE', 5, 1, 'raw model take')",
        (AS_OF,),
    )
    conn.execute(
        "INSERT OR REPLACE INTO agent_verdicts "
        "(scan_date, symbol, agent, verdict, conviction, rank, reasoning) "
        "VALUES (?, 'AAA', 'chair', 'TAKE', 4, 1, 'models 1T/0S, spread 1; struck: no')",
        (AS_OF,),
    )
    conn.execute(
        "INSERT OR REPLACE INTO agent_verdicts "
        "(scan_date, symbol, agent, verdict, conviction, rank, reasoning) "
        "VALUES (?, 'AAA', 'vision', 'HOLD', NULL, 1, 'chart confirms base')",
        (AS_OF,),
    )
    conn.execute(
        "INSERT OR REPLACE INTO agent_verdicts "
        "(scan_date, symbol, agent, verdict, conviction, rank, reasoning) "
        "VALUES (?, 'AAA', 'sizer', 'TAKE', NULL, 1, 'sized to risk cap')",
        (AS_OF,),
    )
    conn.execute(
        "INSERT INTO scan_agent_logs (run_date, agent, model, parsed_ok, validation, tokens_in, tokens_out) "
        "VALUES (?, 'mock/model-a', 'mock/model-a', 1, 'ok', 500, 200)",
        (AS_OF,),
    )
    conn.execute(
        "INSERT INTO scan_agent_logs (run_date, agent, model, parsed_ok, validation) "
        "VALUES (?, 'chair', 'mock/chair', 1, 'ok')",
        (AS_OF,),
    )
    conn.execute(
        "INSERT INTO agent_signals (scan_date, symbol, channel, message, sent) "
        "VALUES (?, 'AAA', 'telegram', 'AAA entry signal', 1)",
        (AS_OF,),
    )
    conn.execute(
        "INSERT INTO pipeline_runs (run_date, stage, source, status, rows_affected, duration_s, detail) "
        "VALUES (?, 'agents_debate', 'agent_verdicts', 'ok', 1, 0.5, 'debate ok')",
        (AS_OF,),
    )
    conn.execute(
        "INSERT INTO pipeline_runs (run_date, stage, source, status, rows_affected, duration_s, detail) "
        "VALUES (?, 'agents_coach', 'journal_trades', 'partial', 0, 0.1, 'coach no open positions')",
        (AS_OF,),
    )
    run_card.LESSON_DIR.mkdir(parents=True, exist_ok=True)
    (run_card.LESSON_DIR / f"{AS_OF}_AAA.md").write_text("lesson body", encoding="utf-8")
    conn.commit()


def test_run_card_written_with_expected_top_level_keys(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    lesson_dir = tmp_path / "lessons"
    monkeypatch.setattr(run_card, "LESSON_DIR", lesson_dir)
    monkeypatch.setattr(run_card, "RUN_CARD_ROOT", tmp_path / "run_cards")
    try:
        _seed_night(conn)

        path = run_card.write(conn, AS_OF)

        assert path.exists()
        card = json.loads(path.read_text(encoding="utf-8"))
        for key in [
            "run_date", "scan_date", "regime", "pipeline", "shortlist", "debate",
            "chair", "vision", "sizer", "signals", "coach", "lessons_written", "errors",
        ]:
            assert key in card

        assert card["run_date"] == AS_OF
        assert card["scan_date"] == AS_OF
        assert card["regime"]["mode"] == "SELECTIVE"
        assert card["regime"]["age_days"] == 0
        assert card["shortlist"] == [
            {
                "symbol": "AAA", "rank": 1, "setup_family": "base/pattern",
                "entry": 100, "stop": 95, "target": 112, "rr": 2.4, "suggested_qty": 10,
            }
        ]
        assert card["debate"] == [
            {"model": "mock/model-a", "verdicts": 1, "parsed_ok": 1, "tokens_in": 500, "tokens_out": 200}
        ]
        assert card["chair"][0]["symbol"] == "AAA"
        assert card["chair"][0]["struck"] is False
        assert card["vision"][0]["verdict"] == "HOLD"
        assert card["sizer"][0]["verdict"] == "TAKE"
        assert card["signals"] == [{"channel": "telegram", "symbol": "AAA", "sent": True}]
        assert card["coach"] == [{"detail": "coach no open positions"}]
        assert card["lessons_written"] == [f"{AS_OF}_AAA.md"]
        assert card["errors"] == [{"stage": "agents_coach", "detail": "coach no open positions"}]

        pipeline_stages = {p["stage"] for p in card["pipeline"]}
        assert pipeline_stages == {"agents_debate", "agents_coach"}
    finally:
        conn.close()


def test_run_card_idempotent_overwrite(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    monkeypatch.setattr(run_card, "LESSON_DIR", tmp_path / "lessons")
    monkeypatch.setattr(run_card, "RUN_CARD_ROOT", tmp_path / "run_cards")
    try:
        _seed_night(conn)
        path1 = run_card.write(conn, AS_OF)
        path2 = run_card.write(conn, AS_OF)
        assert path1 == path2
        assert len(list((tmp_path / "run_cards").glob("*.json"))) == 1
    finally:
        conn.close()


def test_run_card_no_data_still_writes_shell(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    monkeypatch.setattr(run_card, "LESSON_DIR", tmp_path / "lessons")
    monkeypatch.setattr(run_card, "RUN_CARD_ROOT", tmp_path / "run_cards")
    try:
        conn.commit()
        path = run_card.write(conn, "2026-07-01")
        card = json.loads(path.read_text(encoding="utf-8"))
        assert card["scan_date"] is None
        assert card["shortlist"] == []
        assert card["pipeline"] == []
    finally:
        conn.close()


def _api_client(db_path, monkeypatch):
    orig_connect = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: orig_connect(db_path))
    monkeypatch.setattr(api_app, "_today", lambda: AS_OF)
    return TestClient(api_app.app)


def test_run_card_endpoint_returns_written_card(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    monkeypatch.setattr(run_card, "LESSON_DIR", tmp_path / "lessons")
    monkeypatch.setattr(run_card, "RUN_CARD_ROOT", tmp_path / "run_cards")
    try:
        _seed_night(conn)
        run_card.write(conn, AS_OF)
    finally:
        conn.close()

    client = _api_client(db_path, monkeypatch)
    resp = client.get("/api/desk/run-card", params={"date": AS_OF})
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is True
    assert body["run_date"] == AS_OF
    assert body["scan_date"] == AS_OF


def test_run_card_endpoint_available_false_when_missing(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    monkeypatch.setattr(run_card, "RUN_CARD_ROOT", tmp_path / "run_cards")

    client = _api_client(db_path, monkeypatch)
    resp = client.get("/api/desk/run-card", params={"date": "2026-01-01"})
    assert resp.status_code == 200
    assert resp.json() == {"available": False, "run_date": "2026-01-01"}
