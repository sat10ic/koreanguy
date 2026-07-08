import json

from fastapi.testclient import TestClient

from manas_os import db
from manas_os.advisor import advisor
from manas_os.advisor.context import build_context_pack
from manas_os.advisor.guard import validate_notes
from manas_os.api import app as api_app
from manas_os.scanner import candidates as scanner_candidates


AS_OF = "2026-06-30"


class FakeClient:
    model = "mock/model"

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def chat(self, *, system, user):
        self.calls += 1
        return self.responses.pop(0), self.model


def _patch_config(monkeypatch, enabled=True, api_key="test-key"):
    def fake_get(key, default=None):
        values = {
            "advisor.enabled": enabled,
            "advisor.api_key": api_key,
            "advisor.model": "mock/model",
            "advisor.max_tokens": 1200,
        }
        return values.get(key, default)

    monkeypatch.setattr(advisor.config, "get", fake_get)


def _seed(conn):
    scanner_candidates.ensure_schema(conn)
    scanner_candidates.ensure_refusals_schema(conn)
    conn.execute(
        "INSERT OR REPLACE INTO regime_snapshots "
        "(snapshot_date, market_mode, xp_value, pillars_passed, preferred_setups_json, avoid_setups_json, quadrant_json) "
        "VALUES (?, 'SELECTIVE', 15, 3, ?, ?, ?)",
        (AS_OF, json.dumps(["pullback"]), json.dumps(["extended"]), json.dumps({"bias": "selective"})),
    )
    conn.execute(
        "INSERT OR REPLACE INTO breadth_daily "
        "(trade_date, advances, declines, up_4pct, down_4pct, pct_above_20dma, nifty_chg_pct) "
        "VALUES (?, 900, 700, 40, 25, 55, -0.5)",
        (AS_OF,),
    )
    conn.execute(
        "INSERT OR REPLACE INTO scan_candidates "
        "(scan_date, symbol, setup, readiness, grade, entry, stop, rr, suggested_qty, "
        "evidence_json, timing_json, setup_family, rank, rank_of, gates_json) "
        "VALUES (?, 'ACME', 'Pullback', 90, 'A', 100, 95, 2.5, 10, ?, ?, 'pullback', 1, 1, ?)",
        (
            AS_OF,
            json.dumps([{"filter": "rvol>=1.5", "value": "1.6x"}]),
            json.dumps({"gap_pct": 1.2}),
            json.dumps({"regime": {"passed": True}}),
        ),
    )
    conn.execute(
        "INSERT OR REPLACE INTO refusals (scan_date, symbol, setup_family, failed_gate, reason, evidence_json) "
        "VALUES (?, 'MISS', 'breakout', 'risk', 'wide stop', '{}')",
        (AS_OF,),
    )
    conn.execute(
        "INSERT INTO journal_trades (trade_date, symbol, setup, entry, stop) VALUES (?, 'HELD', 'EP', 200, 180)",
        (AS_OF,),
    )
    conn.execute(
        "INSERT OR REPLACE INTO daily_prices "
        "(symbol, trade_date, series, open, high, low, close, prev_close, volume) "
        "VALUES ('ACME', ?, 'EQ', 104, 106, 99, 105, 100, 1000)",
        (AS_OF,),
    )
    conn.execute(
        "INSERT OR REPLACE INTO disclosures (trade_date, symbol, kind, detail_json) "
        "VALUES (?, 'ACME', 'corporate-announcement', ?)",
        (AS_OF, json.dumps({"headline": "board meeting"})),
    )
    conn.commit()


def test_context_pack_uses_existing_payload_shapes_and_tables(tmp_path):
    conn = db.init_db(tmp_path / "m.db")
    try:
        _seed(conn)
        pack = build_context_pack(conn, AS_OF)
        assert pack["cards"][0]["symbol"] == "ACME"
        assert set(pack["cards"][0]) == {"symbol", "family", "rank", "rank_of", "gates", "evidence", "plan", "expectancy"}
        assert pack["refusals"][0] == {"symbol": "MISS", "failed_gate": "risk", "reason": "wide stop"}
        assert pack["breadth_trend"][0]["pct_above_20dma"] == 55
        assert "advisor_notes" not in json.dumps(pack)
    finally:
        conn.close()


def test_guard_rejects_note_with_number_absent_from_context():
    ctx = {"entry": 100, "stop": 95}
    raw = json.dumps([{"scope": "entry", "symbol": "ACME", "stance": "caution", "note": "Risk is at 123.", "watch_for": ""}])
    accepted, rejected = validate_notes(raw, ctx)
    assert accepted == []
    assert "novel numbers" in rejected[0]


def test_guard_rejects_imperative_trade_phrases():
    ctx = {"entry": 100, "stop": 95}
    raw = json.dumps([{"scope": "entry", "symbol": "ACME", "stance": "agree", "note": "Buy now near 100.", "watch_for": ""}])
    accepted, rejected = validate_notes(raw, ctx)
    assert accepted == []
    assert "imperative phrase" in rejected[0]


def test_run_persists_notes_and_noops_without_api_key(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    try:
        _seed(conn)
        _patch_config(monkeypatch)
        fake = FakeClient([json.dumps([
            {"scope": "entry", "symbol": "ACME", "stance": "agree", "note": "Entry 100 and stop 95 match the plan.", "watch_for": "Hold 95."}
        ])])
        result = advisor.run(conn, AS_OF, client=fake)
        assert result["status"] == "ok"
        row = conn.execute("SELECT scope, symbol, stance, note FROM advisor_notes").fetchone()
        assert dict(row) == {
            "scope": "entry",
            "symbol": "ACME",
            "stance": "agree",
            "note": "Entry 100 and stop 95 match the plan.",
        }

        _patch_config(monkeypatch, enabled=True, api_key=None)
        before = conn.execute("SELECT COUNT(*) FROM advisor_notes").fetchone()[0]
        skipped = advisor.run(conn, AS_OF)
        after = conn.execute("SELECT COUNT(*) FROM advisor_notes").fetchone()[0]
        assert skipped["status"] == "skip"
        assert after == before
    finally:
        conn.close()


def test_note_action_endpoint_upserts_user_action(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    conn.execute(
        "INSERT INTO advisor_notes (note_date, scope, symbol, stance, note) VALUES (?, 'entry', 'ACME', 'agree', 'ok')",
        (AS_OF,),
    )
    conn.commit()
    conn.close()
    orig_connect = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: orig_connect(db_path))
    client = TestClient(api_app.app)

    res = client.post("/api/advisor/note-action", json={
        "note_date": AS_OF, "scope": "entry", "symbol": "ACME", "action": "dismissed"
    })
    assert res.status_code == 200
    assert res.json()["action"] == "dismissed"
    conn = db.connect(db_path)
    try:
        row = conn.execute("SELECT user_action FROM advisor_notes WHERE symbol = 'ACME'").fetchone()
        assert row["user_action"] == "dismissed"
    finally:
        conn.close()


def test_malformed_model_json_logs_fail_after_one_retry_no_crash(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    try:
        _seed(conn)
        _patch_config(monkeypatch)
        fake = FakeClient(["not json", "{still bad"])
        result = advisor.run(conn, AS_OF, client=fake)
        assert result["status"] == "fail"
        assert fake.calls == 2
        row = conn.execute(
            "SELECT status, rows_affected, detail FROM pipeline_runs WHERE stage = 'advisor' ORDER BY run_id DESC LIMIT 1"
        ).fetchone()
        assert row["status"] == "fail"
        assert row["rows_affected"] == 0
        assert "malformed model JSON" in row["detail"]
    finally:
        conn.close()
