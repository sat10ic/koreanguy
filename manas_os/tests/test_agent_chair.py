import json

from manas_os import db
from manas_os.agents import chair, debate
from manas_os.scanner import candidates as scanner_candidates


AS_OF = "2026-06-30"


class ChairClient:
    model = "mock/chair"

    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def chat(self, *, system, user):
        self.calls.append({"system": system, "user": user})
        return json.dumps(self.payload), self.model


class FailingClient:
    def chat(self, *, system, user):
        raise RuntimeError("chair unavailable")


def _patch_config(monkeypatch):
    def fake_get(key, default=None):
        values = {
            "agents.models": ["mock/analyst-a"],
            "agents.chair_model": "mock/chair",
            "agents.max_tokens": 1200,
            "risk.capital": 1_000_000,
        }
        return values.get(key, default)

    monkeypatch.setattr(chair.config, "get", fake_get)


def _seed_candidate(conn, symbol, rank, sector="TECH"):
    scanner_candidates.ensure_schema(conn)
    conn.execute(
        "INSERT OR REPLACE INTO scan_candidates "
        "(scan_date, symbol, setup, readiness, grade, entry, stop, target, rr, suggested_qty, "
        "trade_plan_json, evidence_json, timing_json, score_breakdown_json, gates_json, setup_family, rank, rank_of, sector) "
        "VALUES (?, ?, 'Pullback', 90, 'A', 100, 95, 112, 2.4, 10, ?, '[]', '{}', '{}', '[]', 'base/pattern', ?, 2, ?)",
        (AS_OF, symbol, json.dumps({"entry_trigger": "pivot"}), rank, sector),
    )


def _seed_verdict(conn, symbol, agent, verdict, conviction, rank, bull="bull", bear="bear"):
    debate.ensure_schema(conn)
    conn.execute(
        "INSERT OR REPLACE INTO agent_verdicts "
        "(scan_date, symbol, agent, verdict, conviction, rank, bull_case, bear_case, reasoning, lens_scores_json) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'reason', '{}')",
        (AS_OF, symbol, agent, verdict, conviction, rank, bull, bear),
    )


def _seed_base(conn):
    _seed_candidate(conn, "AAA", 1, "TECH")
    _seed_candidate(conn, "BBB", 2, "BANK")
    conn.execute(
        "INSERT INTO regime_snapshots (snapshot_date, market_mode) VALUES (?, 'SELECTIVE')",
        (AS_OF,),
    )


def test_chair_aggregation_math_and_preserves_cases(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    try:
        _patch_config(monkeypatch)
        _seed_base(conn)
        _seed_verdict(conn, "AAA", "m1", "TAKE", 5, 1, bull="m1 bull", bear="m1 bear")
        _seed_verdict(conn, "AAA", "m2", "TAKE", 3, 2, bull="m2 bull", bear="m2 bear")
        _seed_verdict(conn, "BBB", "m1", "SKIP", 2, 2)
        _seed_verdict(conn, "BBB", "m2", "TAKE", 4, None)
        conn.commit()

        result = chair.run(conn, AS_OF, client=ChairClient([
            {"symbol": "AAA", "strike": False, "strike_reason": ""},
            {"symbol": "BBB", "strike": False, "strike_reason": ""},
        ]))

        assert result["status"] == "ok"
        rows = conn.execute(
            "SELECT symbol, verdict, conviction, rank, bull_case, bear_case, reasoning, lens_scores_json "
            "FROM agent_verdicts WHERE agent = 'chair' ORDER BY rank"
        ).fetchall()
        assert [(r["symbol"], r["verdict"], r["conviction"], r["rank"]) for r in rows] == [
            ("AAA", "TAKE", 4, 1),
            ("BBB", "SKIP", 3, 2),
        ]
        assert json.loads(rows[0]["bull_case"]) == [
            {"agent": "m1", "text": "m1 bull"},
            {"agent": "m2", "text": "m2 bull"},
        ]
        assert json.loads(rows[0]["bear_case"])[1]["text"] == "m2 bear"
        lens = json.loads(rows[1]["lens_scores_json"])
        assert lens["verdict_split"] == "1T/1S"
        assert lens["conviction_spread"] == 2
        assert lens["disagreement"] is True
        assert "models 1T/1S, spread 2; struck: no" in rows[1]["reasoning"]
    finally:
        conn.close()


def test_chair_aggregate_breaks_tied_mean_rank_by_conviction_then_symbol(tmp_path, monkeypatch):
    """AU8: two symbols tied on mean_rank across two models must resolve
    deterministically (higher mean_conviction first, then symbol) rather than
    depending on dict/row iteration order."""
    conn = db.init_db(tmp_path / "m.db")
    try:
        _patch_config(monkeypatch)
        _seed_base(conn)
        # Both AAA and BBB get rank 1 from one model and rank 2 from the
        # other -> identical mean_rank (1.5) for both symbols.
        _seed_verdict(conn, "AAA", "m1", "TAKE", 5, 1)
        _seed_verdict(conn, "AAA", "m2", "TAKE", 3, 2)
        _seed_verdict(conn, "BBB", "m1", "TAKE", 2, 2)
        _seed_verdict(conn, "BBB", "m2", "TAKE", 4, 1)
        conn.commit()

        aggregates = chair.aggregate(conn, AS_OF)

        assert [a["mean_rank"] for a in aggregates] == [1.5, 1.5]
        # AAA mean_conviction=4.0 beats BBB mean_conviction=3.0 at equal mean_rank.
        assert [a["symbol"] for a in aggregates] == ["AAA", "BBB"]

        result = chair.run(conn, AS_OF, client=ChairClient([
            {"symbol": "AAA", "strike": False, "strike_reason": ""},
            {"symbol": "BBB", "strike": False, "strike_reason": ""},
        ]))
        assert result["status"] == "ok"
        rows = conn.execute(
            "SELECT symbol, rank FROM agent_verdicts WHERE agent = 'chair' ORDER BY rank"
        ).fetchall()
        assert [(r["symbol"], r["rank"]) for r in rows] == [("AAA", 1), ("BBB", 2)]
    finally:
        conn.close()


def test_chair_disagreement_flag_on_wide_conviction_spread(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    try:
        _patch_config(monkeypatch)
        _seed_candidate(conn, "AAA", 1)
        _seed_verdict(conn, "AAA", "m1", "TAKE", 5, 1)
        _seed_verdict(conn, "AAA", "m2", "TAKE", 2, 2)
        conn.commit()

        chair.run(conn, AS_OF, client=ChairClient([{"symbol": "AAA", "strike": False}]))

        lens = json.loads(conn.execute(
            "SELECT lens_scores_json FROM agent_verdicts WHERE agent = 'chair' AND symbol = 'AAA'"
        ).fetchone()["lens_scores_json"])
        assert lens["conviction_spread"] == 3
        assert lens["disagreement"] is True
    finally:
        conn.close()


def test_chair_strike_becomes_skip_and_ranks_last(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    try:
        _patch_config(monkeypatch)
        _seed_base(conn)
        _seed_verdict(conn, "AAA", "m1", "TAKE", 5, 1)
        _seed_verdict(conn, "BBB", "m1", "TAKE", 4, 2)
        conn.commit()

        result = chair.run(conn, AS_OF, client=ChairClient([
            {"symbol": "AAA", "strike": True, "strike_reason": "TECH concentration in open book"},
            {"symbol": "BBB", "strike": False, "strike_reason": ""},
        ]))

        assert result["strikes"] == {"AAA": "TECH concentration in open book"}
        rows = conn.execute(
            "SELECT symbol, verdict, rank, reasoning FROM agent_verdicts WHERE agent = 'chair' ORDER BY rank"
        ).fetchall()
        assert [(r["symbol"], r["verdict"], r["rank"]) for r in rows] == [
            ("BBB", "TAKE", 1),
            ("AAA", "SKIP", 2),
        ]
        assert "struck: TECH concentration in open book" in rows[1]["reasoning"]
    finally:
        conn.close()


def test_chair_stage2_prompt_carries_gate_evidence_and_anti_double_count_instruction(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    try:
        _patch_config(monkeypatch)
        scanner_candidates.ensure_schema(conn)
        conn.execute(
            "INSERT OR REPLACE INTO scan_candidates "
            "(scan_date, symbol, setup, readiness, grade, entry, stop, target, rr, suggested_qty, "
            "trade_plan_json, evidence_json, timing_json, score_breakdown_json, gates_json, "
            "setup_family, rank, rank_of, sector) "
            "VALUES (?, 'AAA', 'Pullback', 90, 'B', 100, 95, 112, 2.4, 10, '{}', ?, '{}', '{}', ?, "
            "'base/pattern', 1, 1, 'TECH')",
            (
                AS_OF,
                json.dumps([{"filter": "exit-conflict", "value": "entry conflicts with weakness — grade capped at B"}]),
                json.dumps([{"gate": "regime", "pass": True}, {"gate": "risk", "pass": True}]),
            ),
        )
        _seed_verdict(conn, "AAA", "m1", "TAKE", 5, 1)
        conn.commit()

        client = ChairClient([{"symbol": "AAA", "strike": False, "strike_reason": ""}])
        chair.run(conn, AS_OF, client=client)

        assert len(client.calls) == 1
        system = client.calls[0]["system"]
        user = client.calls[0]["user"]
        assert "gate_evidence" in system
        assert (
            "The deterministic gate already priced these risks (grade caps, evidence "
            "chips). Strike ONLY on risks NOT already reflected there: portfolio "
            "concentration, correlated exposure across picks, or event risk named in "
            "bear cases. Do not strike for a risk the gate already graded." in system
        )
        payload = json.loads(user)
        aaa = next(a for a in payload["aggregates"] if a["symbol"] == "AAA")
        assert aaa["gate_evidence"]["grade"] == "B"
        assert aaa["gate_evidence"]["gates_passed"] == ["regime", "risk"]
        assert "grade capped at B" in aaa["gate_evidence"]["notes"][0]
    finally:
        conn.close()


def test_chair_mocked_strike_citing_already_graded_risk_still_persists(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    try:
        _patch_config(monkeypatch)
        _seed_candidate(conn, "AAA", 1)
        _seed_verdict(conn, "AAA", "m1", "TAKE", 5, 1)
        conn.commit()

        result = chair.run(conn, AS_OF, client=ChairClient([
            {"symbol": "AAA", "strike": True, "strike_reason": "grade B already capped by gate"},
        ]))

        assert result["strikes"] == {"AAA": "grade B already capped by gate"}
        row = conn.execute(
            "SELECT verdict FROM agent_verdicts WHERE agent = 'chair' AND symbol = 'AAA'"
        ).fetchone()
        assert row["verdict"] == "SKIP"
    finally:
        conn.close()


def test_chair_strike_pass_skips_malformed_item_and_keeps_valid_ones(tmp_path, monkeypatch):
    """AU4: R2 skip-and-log semantics — one malformed strike item (unknown
    symbol) must not raise and nuke the whole strike pass; valid items still
    apply, only zero-valid-among-present should raise."""
    conn = db.init_db(tmp_path / "m.db")
    try:
        _patch_config(monkeypatch)
        _seed_base(conn)
        _seed_verdict(conn, "AAA", "m1", "TAKE", 5, 1)
        _seed_verdict(conn, "BBB", "m1", "TAKE", 4, 2)
        conn.commit()

        result = chair.run(conn, AS_OF, client=ChairClient([
            {"symbol": "ZZZ", "strike": True, "strike_reason": "unknown symbol from model"},
            {"symbol": "AAA", "strike": True, "strike_reason": "concentration"},
            {"symbol": "BBB", "strike": False, "strike_reason": ""},
        ]))

        assert result["status"] == "ok"
        assert result["strikes"] == {"AAA": "concentration"}
        rows = conn.execute(
            "SELECT symbol, verdict, rank FROM agent_verdicts WHERE agent = 'chair' ORDER BY rank"
        ).fetchall()
        assert [(r["symbol"], r["verdict"], r["rank"]) for r in rows] == [
            ("BBB", "TAKE", 1),
            ("AAA", "SKIP", 2),
        ]
    finally:
        conn.close()


def test_chair_strike_pass_all_bad_items_raises_and_persists_partial(tmp_path, monkeypatch):
    """AU4: raise only when zero valid items AND items were present."""
    conn = db.init_db(tmp_path / "m.db")
    try:
        _patch_config(monkeypatch)
        _seed_candidate(conn, "AAA", 1)
        _seed_verdict(conn, "AAA", "m1", "TAKE", 5, 1)
        conn.commit()

        result = chair.run(conn, AS_OF, client=ChairClient([
            {"symbol": "ZZZ", "strike": True, "strike_reason": "unknown"},
        ]))

        assert result["status"] == "partial"
        row = conn.execute(
            "SELECT symbol, verdict FROM agent_verdicts WHERE agent = 'chair'"
        ).fetchone()
        assert (row["symbol"], row["verdict"]) == ("AAA", "TAKE")
    finally:
        conn.close()


def test_chair_llm_failure_persists_partial_aggregate_rows(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    try:
        _patch_config(monkeypatch)
        _seed_candidate(conn, "AAA", 1)
        _seed_verdict(conn, "AAA", "m1", "TAKE", 5, 1)
        conn.commit()

        result = chair.run(conn, AS_OF, client=FailingClient())

        assert result["status"] == "partial"
        row = conn.execute(
            "SELECT symbol, verdict, conviction, reasoning FROM agent_verdicts WHERE agent = 'chair'"
        ).fetchone()
        assert (row["symbol"], row["verdict"], row["conviction"]) == ("AAA", "TAKE", 5)
        assert "struck: no" in row["reasoning"]
        run = conn.execute(
            "SELECT status, stage, rows_affected, detail FROM pipeline_runs ORDER BY run_id DESC LIMIT 1"
        ).fetchone()
        assert run["stage"] == "agents_debate"
        assert run["status"] == "partial"
        assert run["rows_affected"] == 1
        assert "risk_gate_error=chair unavailable" in run["detail"]
    finally:
        conn.close()
