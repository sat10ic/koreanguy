import json

from manas_os import db
from manas_os.agents import debate, sizer
from manas_os.scanner import candidates as scanner_candidates


AS_OF = "2026-06-30"


class SizerClient:
    model = "mock/sizer"

    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def chat(self, *, system, user):
        self.calls.append({"system": system, "user": user})
        if isinstance(self.payload, Exception):
            raise self.payload
        return json.dumps(self.payload), self.model


def _patch_config(monkeypatch):
    def fake_get(key, default=None):
        values = {
            "agents.sizer_model": "mock/sizer",
            "agents.models": ["mock/fallback"],
            "agents.api_key": "test-key",
            "agents.max_tokens": 1200,
            "agents.risk_appetite": "aggressive",
            "advisor.api_key": None,
            "risk.capital": 1_000_000,
        }
        return values.get(key, default)

    monkeypatch.setattr(sizer.config, "get", fake_get)


def _seed_chair_pick(conn, symbol="AAA", rank=1, suggested_qty=100, sector="TECH"):
    scanner_candidates.ensure_schema(conn)
    debate.ensure_schema(conn)
    conn.execute(
        "INSERT OR REPLACE INTO regime_snapshots (snapshot_date, market_mode) VALUES (?, 'RISK_ON')",
        (AS_OF,),
    )
    conn.execute(
        "INSERT OR REPLACE INTO scan_candidates "
        "(scan_date, symbol, setup, readiness, grade, entry, stop, target, rr, suggested_qty, "
        "trade_plan_json, evidence_json, timing_json, score_breakdown_json, gates_json, setup_family, rank, rank_of, sector) "
        "VALUES (?, ?, 'Pullback', 90, 'A', 100, 95, 112, 2.4, ?, '{}', '[]', '{}', '{}', '[]', 'strong_start', ?, 3, ?)",
        (AS_OF, symbol, suggested_qty, rank, sector),
    )
    conn.execute(
        "INSERT OR REPLACE INTO agent_verdicts "
        "(scan_date, symbol, agent, verdict, conviction, rank, lens_scores_json, reasoning) "
        "VALUES (?, ?, 'chair', 'TAKE', 4, ?, '{}', 'chair take')",
        (AS_OF, symbol, rank),
    )


def _lens(conn, symbol="AAA"):
    row = conn.execute(
        "SELECT verdict, lens_scores_json FROM agent_verdicts WHERE agent = 'sizer' AND symbol = ?",
        (symbol,),
    ).fetchone()
    return row["verdict"], json.loads(row["lens_scores_json"])


def test_sizer_clamps_multiplier_to_validated_envelope(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    try:
        _patch_config(monkeypatch)
        _seed_chair_pick(conn, suggested_qty=100)
        conn.commit()

        result = sizer.run(conn, AS_OF, client=SizerClient([{"symbol": "AAA", "take": True, "multiplier": 9, "reasoning": "Push."}]))

        assert result["status"] == "ok"
        verdict, lens = _lens(conn)
        assert verdict == "TAKE"
        assert lens == {"final_qty": 125, "multiplier": 1.25, "validated": True}
    finally:
        conn.close()


def test_sizer_steps_down_until_validate_envelope_passes(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    try:
        _patch_config(monkeypatch)
        _seed_chair_pick(conn, suggested_qty=2000)
        conn.commit()

        result = sizer.run(conn, AS_OF, client=SizerClient([{"symbol": "AAA", "take": True, "multiplier": 1.25}]))

        assert result["status"] == "ok"
        verdict, lens = _lens(conn)
        assert verdict == "TAKE"
        assert lens == {"final_qty": 1500, "multiplier": 0.75, "validated": True}
        log = conn.execute("SELECT validation FROM scan_agent_logs WHERE agent = 'sizer'").fetchone()
        assert "AAA: 1.25->1.00" in log["validation"]
        assert "AAA: 1.00->0.75" in log["validation"]
    finally:
        conn.close()


def test_sizer_take_false_persists_skip(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    try:
        _patch_config(monkeypatch)
        _seed_chair_pick(conn)
        conn.commit()

        result = sizer.run(conn, AS_OF, client=SizerClient([{"symbol": "AAA", "take": False, "multiplier": 1.0, "reasoning": "Too crowded."}]))

        assert result["status"] == "ok"
        verdict, lens = _lens(conn)
        assert verdict == "SKIP"
        assert lens == {"final_qty": 0, "multiplier": 0, "validated": True}
    finally:
        conn.close()


def test_sizer_llm_failure_returns_partial_and_no_rows(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    try:
        _patch_config(monkeypatch)
        _seed_chair_pick(conn)
        conn.commit()

        result = sizer.run(conn, AS_OF, client=SizerClient(RuntimeError("sizer down")))

        assert result["status"] == "partial"
        assert conn.execute("SELECT COUNT(*) FROM agent_verdicts WHERE agent = 'sizer'").fetchone()[0] == 0
        log = conn.execute("SELECT parsed_ok, error FROM scan_agent_logs WHERE agent = 'sizer'").fetchone()
        assert log["parsed_ok"] == 0
        assert "sizer down" in log["error"]
    finally:
        conn.close()
