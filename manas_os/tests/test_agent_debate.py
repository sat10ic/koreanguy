import json

from manas_os import db
from manas_os.agents import debate
from manas_os.scanner import candidates as scanner_candidates


AS_OF = "2026-06-30"


class FakeClient:
    model = "mock/model"

    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def chat(self, *, system, user):
        self.calls.append({"system": system, "user": user})
        return json.dumps(self.payload), self.model


def _patch_config(monkeypatch, *, enabled=True, api_key="test-key", shortlist_size=15):
    def fake_get(key, default=None):
        values = {
            "agents.enabled": enabled,
            "agents.api_key": api_key,
            "agents.models": ["mock/model"],
            "agents.max_tokens": 1200,
            "agents.shortlist_size": shortlist_size,
            "advisor.api_key": None,
        }
        return values.get(key, default)

    monkeypatch.setattr(debate.config, "get", fake_get)


def _seed_candidate(conn, symbol, rank):
    conn.execute(
        "INSERT OR REPLACE INTO scan_candidates "
        "(scan_date, symbol, setup, readiness, grade, entry, stop, rr, suggested_qty, "
        "evidence_json, timing_json, score_breakdown_json, trade_plan_json, gates_json, setup_family, rank, rank_of) "
        "VALUES (?, ?, 'Pullback', ?, 'A', 100, 95, 2.5, 10, ?, ?, ?, ?, ?, 'pullback', ?, 10)",
        (
            AS_OF,
            symbol,
            100 - rank,
            json.dumps([{"filter": "delivery>=60", "value": "62%"}]),
            json.dumps({"close": 100 + rank, "rvol": 1.5, "delivery_pct": 62}),
            json.dumps({"growth": {"eps_yoy": {"value": 40}}}),
            json.dumps({"entry_trigger": "deterministic"}),
            json.dumps([{"gate": "risk", "pass": True}]),
            rank,
        ),
    )


def _seed(conn, count=3):
    scanner_candidates.ensure_schema(conn)
    scanner_candidates.ensure_refusals_schema(conn)
    debate.ensure_schema(conn)
    for idx in range(1, count + 1):
        _seed_candidate(conn, f"SYM{idx}", idx)
    conn.execute(
        "INSERT OR REPLACE INTO refusals (scan_date, symbol, setup_family, failed_gate, reason, evidence_json) "
        "VALUES (?, 'MISS', 'pullback', 'risk', 'wide stop', '{}')",
        (AS_OF,),
    )
    conn.commit()


def test_agent_tables_created(tmp_path):
    conn = db.init_db(tmp_path / "m.db")
    try:
        debate.ensure_schema(conn)
        tables = {
            r["name"]
            for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert {"agent_verdicts", "scan_agent_logs"} <= tables
    finally:
        conn.close()


def test_debate_noops_without_config_or_key(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    try:
        _seed(conn)
        _patch_config(monkeypatch, enabled=False, api_key=None)
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        result = debate.run(conn, AS_OF)
        assert result["status"] == "skip"
        assert conn.execute("SELECT COUNT(*) FROM agent_verdicts").fetchone()[0] == 0
        run = conn.execute(
            "SELECT status, stage, rows_affected, detail FROM pipeline_runs ORDER BY run_id DESC LIMIT 1"
        ).fetchone()
        assert run["stage"] == "agents_debate"
        assert run["status"] == "skip"
        assert run["rows_affected"] == 0
        assert "config/api key absent" in run["detail"]
    finally:
        conn.close()


def test_mocked_debate_persists_verdicts_without_touching_candidates_or_refusals(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    try:
        _seed(conn, count=2)
        _patch_config(monkeypatch, shortlist_size=2)
        before_refusals = conn.execute("SELECT COUNT(*) FROM refusals").fetchone()[0]
        before_candidates = conn.execute("SELECT COUNT(*) FROM scan_candidates").fetchone()[0]
        fake = FakeClient([
            {
                "symbol": "SYM1",
                "verdict": "TAKE",
                "conviction": 5,
                "rank": 1,
                "lens_scores": {"strong_start": 4},
                "bull_case": "Clean pullback with demand.",
                "bear_case": "Needs follow-through.",
                "reasoning": "Best relative setup.",
            },
            {
                "symbol": "SYM2",
                "verdict": "SKIP",
                "conviction": 2,
                "rank": 2,
                "lens_scores": {"strong_start": 2},
                "bull_case": "Some RS.",
                "bear_case": "Less clean than SYM1.",
                "reasoning": "Lower priority.",
            },
        ])

        result = debate.run(conn, AS_OF, client=fake)

        assert result["status"] == "ok"
        assert conn.execute("SELECT COUNT(*) FROM refusals").fetchone()[0] == before_refusals
        assert conn.execute("SELECT COUNT(*) FROM scan_candidates").fetchone()[0] == before_candidates
        rows = conn.execute(
            "SELECT symbol, agent, verdict, conviction, bull_case, bear_case FROM agent_verdicts ORDER BY symbol"
        ).fetchall()
        assert [r["symbol"] for r in rows] == ["SYM1", "SYM2"]
        assert rows[0]["agent"] == "mock/model"
        assert rows[0]["verdict"] == "TAKE"
        assert rows[0]["conviction"] == 5
        assert rows[0]["bull_case"] == "Clean pullback with demand."
        log = conn.execute("SELECT parsed_ok, validation FROM scan_agent_logs").fetchone()
        assert log["parsed_ok"] == 1
        assert log["validation"] == "ok"
    finally:
        conn.close()


def test_shortlist_size_is_honored(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    try:
        _seed(conn, count=5)
        _patch_config(monkeypatch, shortlist_size=3)
        fake = FakeClient([
            {
                "symbol": "SYM1",
                "verdict": "TAKE",
                "conviction": 4,
                "rank": 1,
                "lens_scores": {},
                "bull_case": "Leader.",
                "bear_case": "None yet.",
                "reasoning": "Top rank.",
            }
        ])
        result = debate.run(conn, AS_OF, client=fake)
        sent = json.loads(fake.calls[0]["user"])
        assert result["shortlist_size"] == 3
        assert [item["symbol"] for item in sent["shortlist"]] == ["SYM1", "SYM2", "SYM3"]
    finally:
        conn.close()

