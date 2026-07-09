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


class RawSequenceClient:
    model = "mock/model"

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def chat(self, *, system, user):
        self.calls.append({"system": system, "user": user})
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        if isinstance(response, tuple):
            return response
        return response, self.model


class UsageClient(FakeClient):
    def __init__(self, payload, usage):
        super().__init__(payload)
        self.usage = usage

    def chat(self, *, system, user):
        self.calls.append({"system": system, "user": user})
        return json.dumps(self.payload), self.model, self.usage


class Http429Error(Exception):
    status_code = 429


def _patch_config(monkeypatch, *, enabled=True, api_key="test-key", shortlist_size=15, models=None):
    def fake_get(key, default=None):
        values = {
            "agents.enabled": enabled,
            "agents.api_key": api_key,
            "agents.models": models or ["mock/model"],
            "agents.max_tokens": 1200,
            "agents.shortlist_size": shortlist_size,
            "agents.call_gap_s": 0.01,
            "agents.rate_limit_backoff_s": 0.01,
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
            "SELECT symbol, agent, verdict, conviction, bull_case, bear_case "
            "FROM agent_verdicts WHERE agent = 'mock/model' ORDER BY symbol"
        ).fetchall()
        assert [r["symbol"] for r in rows] == ["SYM1", "SYM2"]
        assert rows[0]["agent"] == "mock/model"
        assert rows[0]["verdict"] == "TAKE"
        assert rows[0]["conviction"] == 5
        assert rows[0]["bull_case"] == "Clean pullback with demand."
        log = conn.execute(
            "SELECT parsed_ok, validation FROM scan_agent_logs WHERE agent = 'mock/model'"
        ).fetchone()
        assert log["parsed_ok"] == 1
        assert log["validation"] == "ok; tokens=approx"
    finally:
        conn.close()


def test_debate_skips_bad_item_and_persists_good_ones(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    try:
        _seed(conn, count=3)
        _patch_config(monkeypatch, shortlist_size=3)
        fake = FakeClient([
            {"symbol": "SYM1", "verdict": "TAKE", "conviction": 5, "rank": 1},
            {"symbol": "SYM2", "verdict": "MAYBE", "conviction": 3, "rank": 2},
            {"symbol": "SYM3", "verdict": "SKIP", "conviction": 2, "rank": 3},
        ])

        result = debate.run(conn, AS_OF, client=fake)

        # Chair's stage-2 strike call gets debate-shaped JSON from this mock and
        # correctly degrades to 'partial' (failure-safe aggregate persists) — the
        # model verdicts themselves must still land.
        assert result["status"] in {"ok", "partial"}
        rows = conn.execute(
            "SELECT symbol, verdict FROM agent_verdicts WHERE agent = 'mock/model' ORDER BY symbol"
        ).fetchall()
        assert [(r["symbol"], r["verdict"]) for r in rows] == [("SYM1", "TAKE"), ("SYM3", "SKIP")]
        log = conn.execute(
            "SELECT parsed_ok, validation FROM scan_agent_logs WHERE agent = 'mock/model'"
        ).fetchone()
        assert log["parsed_ok"] == 1
        assert "skipped=1: SYM2(bad verdict)" in log["validation"]
    finally:
        conn.close()


def test_debate_retries_garbage_then_persists_valid_json(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    try:
        _seed(conn, count=1)
        _patch_config(monkeypatch, shortlist_size=1)
        valid = json.dumps([{"symbol": "SYM1", "verdict": "TAKE", "conviction": 4, "rank": 1}])
        chair_valid = json.dumps([{"symbol": "SYM1", "strike": False, "strike_reason": ""}])
        sizer_valid = json.dumps([{"symbol": "SYM1", "take": True, "multiplier": 1.0, "reasoning": "full size"}])
        fake = RawSequenceClient(["not json", valid, chair_valid, sizer_valid])

        result = debate.run(conn, AS_OF, client=fake)

        assert result["status"] == "ok"
        assert conn.execute("SELECT COUNT(*) FROM agent_verdicts WHERE agent = 'mock/model'").fetchone()[0] == 1
        logs = conn.execute(
            "SELECT parsed_ok, validation, error FROM scan_agent_logs "
            "WHERE agent = 'mock/model' ORDER BY log_id"
        ).fetchall()
        assert [r["parsed_ok"] for r in logs] == [0, 1]
        assert len(fake.calls) == 4
        assert "Your previous response failed:" in fake.calls[1]["user"]
        assert "Return ONLY the JSON array, no markdown." in fake.calls[1]["user"]
    finally:
        conn.close()


def test_debate_retries_http_429_without_consuming_json_retry_or_sleeping_for_injected_client(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    try:
        _seed(conn, count=1)
        _patch_config(monkeypatch, shortlist_size=1)
        monkeypatch.setattr(debate.time, "sleep", lambda seconds: (_ for _ in ()).throw(AssertionError("unexpected sleep")))
        valid = json.dumps([{"symbol": "SYM1", "verdict": "TAKE", "conviction": 4, "rank": 1}])
        chair_valid = json.dumps([{"symbol": "SYM1", "strike": False, "strike_reason": ""}])
        sizer_valid = json.dumps([{"symbol": "SYM1", "take": True, "multiplier": 1.0, "reasoning": "full size"}])
        fake = RawSequenceClient([Http429Error("HTTP 429 rate limit"), valid, chair_valid, sizer_valid])

        result = debate.run(conn, AS_OF, client=fake)

        assert result["status"] == "ok"
        assert conn.execute("SELECT COUNT(*) FROM agent_verdicts WHERE agent = 'mock/model'").fetchone()[0] == 1
        logs = conn.execute(
            "SELECT parsed_ok, error FROM scan_agent_logs WHERE agent = 'mock/model' ORDER BY log_id"
        ).fetchall()
        assert [r["parsed_ok"] for r in logs] == [0, 1]
        assert "HTTP 429 rate limit" in logs[0]["error"]
        assert len(fake.calls) == 4
    finally:
        conn.close()


def test_injected_client_skips_inter_model_call_gap(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    try:
        _seed(conn, count=1)
        _patch_config(monkeypatch, shortlist_size=1, models=["mock/a", "mock/b"])
        monkeypatch.setattr(debate.time, "sleep", lambda seconds: (_ for _ in ()).throw(AssertionError("unexpected sleep")))
        first_valid = json.dumps([{"symbol": "SYM1", "verdict": "TAKE", "conviction": 4, "rank": 1}])
        second_valid = json.dumps([{"symbol": "SYM1", "verdict": "TAKE", "conviction": 3, "rank": 1}])
        chair_valid = json.dumps([{"symbol": "SYM1", "strike": False, "strike_reason": ""}])
        sizer_valid = json.dumps([{"symbol": "SYM1", "take": True, "multiplier": 1.0, "reasoning": "full size"}])
        fake = RawSequenceClient([
            (first_valid, "mock/a"),
            (second_valid, "mock/b"),
            chair_valid,
            sizer_valid,
        ])

        result = debate.run(conn, AS_OF, client=fake)

        assert result["status"] == "ok"
        logs = conn.execute(
            "SELECT agent, parsed_ok FROM scan_agent_logs WHERE agent IN ('mock/a', 'mock/b') ORDER BY log_id"
        ).fetchall()
        assert [r["parsed_ok"] for r in logs] == [1, 1]
        assert [r["agent"] for r in logs] == ["mock/a", "mock/b"]
    finally:
        conn.close()


def test_debate_garbage_twice_logs_failure_and_no_verdicts(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    try:
        _seed(conn, count=1)
        _patch_config(monkeypatch, shortlist_size=1)
        fake = RawSequenceClient(["not json", "still not json"])

        result = debate.run(conn, AS_OF, client=fake)

        assert result["status"] == "fail"
        assert conn.execute("SELECT COUNT(*) FROM agent_verdicts").fetchone()[0] == 0
        logs = conn.execute(
            "SELECT parsed_ok, validation, error FROM scan_agent_logs ORDER BY log_id"
        ).fetchall()
        assert [r["parsed_ok"] for r in logs] == [0, 0]
        assert all(r["validation"] == "fail; tokens=approx" for r in logs)
    finally:
        conn.close()


def test_debate_logs_real_usage_tokens_when_present(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    try:
        _seed(conn, count=1)
        _patch_config(monkeypatch, shortlist_size=1)
        fake = UsageClient(
            [{"symbol": "SYM1", "verdict": "TAKE", "conviction": 4, "rank": 1}],
            {"prompt_tokens": 123, "completion_tokens": 45},
        )

        result = debate.run(conn, AS_OF, client=fake)

        assert result["status"] == "ok"
        log = conn.execute(
            "SELECT tokens_in, tokens_out, validation FROM scan_agent_logs WHERE agent = 'mock/model'"
        ).fetchone()
        assert log["tokens_in"] == 123
        assert log["tokens_out"] == 45
        assert log["validation"] == "ok"
    finally:
        conn.close()


def test_same_date_rerun_preserves_backfilled_outcome_r_across_all_agents(tmp_path, monkeypatch):
    """AU1: INSERT OR REPLACE nulled outcome_r/created_at on a same-night rerun
    because REPLACE = delete+reinsert. All four writers (debate, chair, vision,
    sizer) must upsert instead, preserving a backfilled outcome_r and the
    original created_at across a rerun for the same scan_date."""
    from manas_os.agents import vision as vision_module

    conn = db.init_db(tmp_path / "m.db")
    try:
        _seed(conn, count=1)
        conn.commit()

        def fake_get(key, default=None):
            values = {
                "agents.enabled": True,
                "agents.api_key": "test-key",
                "agents.models": ["mock/model"],
                "agents.max_tokens": 1200,
                "agents.shortlist_size": 1,
                "agents.call_gap_s": 0.01,
                "agents.rate_limit_backoff_s": 0.01,
                "agents.vision_model": "mock/vision",
                "agents.vision_top_n": 8,
                "agents.risk_appetite": "aggressive",
                "risk.capital": 1_000_000,
                "advisor.api_key": None,
            }
            return values.get(key, default)

        monkeypatch.setattr(debate.config, "get", fake_get)

        def fake_render(_conn, scan_date, symbols):
            chart_dir = tmp_path / "charts" / scan_date
            chart_dir.mkdir(parents=True, exist_ok=True)
            out = {}
            for symbol in symbols:
                daily = chart_dir / f"{symbol}_daily.png"
                weekly = chart_dir / f"{symbol}_weekly.png"
                daily.write_bytes(b"\x89PNG\r\n\x1a\nDaily")
                weekly.write_bytes(b"\x89PNG\r\n\x1a\nWeekly")
                out[symbol] = {"daily": str(daily), "weekly": str(weekly)}
            return out

        monkeypatch.setattr(vision_module.charts, "render_charts", fake_render)

        debate_verdict = json.dumps([{"symbol": "SYM1", "verdict": "TAKE", "conviction": 4, "rank": 1}])
        chair_verdict = json.dumps([{"symbol": "SYM1", "strike": False, "strike_reason": ""}])
        vision_verdict = json.dumps({"action": "hold", "what_i_see": "clean base.", "reason": "no change."})
        sizer_verdict = json.dumps([{"symbol": "SYM1", "take": True, "multiplier": 1.0, "reasoning": "full size"}])
        fake = RawSequenceClient([
            debate_verdict, chair_verdict, vision_verdict, sizer_verdict,
            debate_verdict, chair_verdict, vision_verdict, sizer_verdict,
        ])

        first = debate.run(conn, AS_OF, client=fake)
        assert first["status"] == "ok"

        agents_present = {
            r["agent"]
            for r in conn.execute(
                "SELECT DISTINCT agent FROM agent_verdicts WHERE scan_date = ? AND symbol = 'SYM1'",
                (AS_OF,),
            ).fetchall()
        }
        assert {"mock/model", "chair", "vision", "sizer"} <= agents_present

        # Simulate lessons.py backfilling outcome_r after the trade closed out,
        # with an old created_at that a rerun must not overwrite.
        conn.execute(
            "UPDATE agent_verdicts SET outcome_r = 1.5, created_at = '2020-01-01T00:00:00' "
            "WHERE scan_date = ? AND symbol = 'SYM1'",
            (AS_OF,),
        )
        conn.commit()

        second = debate.run(conn, AS_OF, client=fake)
        assert second["status"] == "ok"

        rows = conn.execute(
            "SELECT agent, outcome_r, created_at FROM agent_verdicts WHERE scan_date = ? AND symbol = 'SYM1'",
            (AS_OF,),
        ).fetchall()
        by_agent = {r["agent"]: (r["outcome_r"], r["created_at"]) for r in rows}
        for agent in ("mock/model", "chair", "vision", "sizer"):
            outcome_r, created_at = by_agent[agent]
            assert outcome_r == 1.5, f"{agent} lost its backfilled outcome_r on rerun"
            assert created_at == "2020-01-01T00:00:00", f"{agent} lost its original created_at on rerun"
    finally:
        conn.close()


def test_shortlist_floor_fills_from_soft_near_misses_only(tmp_path, monkeypatch):
    """WO6: only 2 gate survivors and 3 refusals for the same scan_date -> the
    pool fills with the SOFT-gate near-misses (fresh-leg), ranked closest-to-
    passing first (smallest numeric gap in the refusal reason). The hard
    "tradability" miss is excluded from the debate pool entirely — it does
    not even sort in, it is simply absent."""
    conn = db.init_db(tmp_path / "m.db")
    try:
        scanner_candidates.ensure_schema(conn)
        scanner_candidates.ensure_refusals_schema(conn)
        debate.ensure_schema(conn)
        _seed_candidate(conn, "SYM1", 1)
        _seed_candidate(conn, "SYM2", 2)
        conn.execute(
            "INSERT INTO refusals (scan_date, symbol, setup_family, failed_gate, reason, evidence_json) "
            "VALUES (?, 'MISS_CLOSE', 'pullback', 'fresh-leg', 'extension 8.1% exceeds 8.0% cap', '{}')",
            (AS_OF,),
        )
        conn.execute(
            "INSERT INTO refusals (scan_date, symbol, setup_family, failed_gate, reason, evidence_json) "
            "VALUES (?, 'MISS_MID', 'pullback', 'fresh-leg', 'extension 9.5% exceeds 8.0% cap', '{}')",
            (AS_OF,),
        )
        conn.execute(
            "INSERT INTO refusals (scan_date, symbol, setup_family, failed_gate, reason, evidence_json) "
            "VALUES (?, 'MISS_TRAD', 'pullback', 'tradability', 'illiquid: 0.05 below 0.1 floor', '{}')",
            (AS_OF,),
        )
        conn.commit()

        _patch_config(monkeypatch, shortlist_size=15)
        scan_date, shortlist, hard_near_misses = debate._load_shortlist(conn, AS_OF, debate._shortlist_size())

        assert scan_date == AS_OF
        assert len(shortlist) == 4  # 2 survivors + 2 SOFT near-misses; hard miss excluded
        tiers = {item["symbol"]: item["tier"] for item in shortlist}
        assert tiers["SYM1"] == "PASSED"
        assert tiers["SYM2"] == "PASSED"
        assert tiers["MISS_CLOSE"] == "NEAR_MISS"
        assert tiers["MISS_MID"] == "NEAR_MISS"
        assert "MISS_TRAD" not in tiers
        near_miss_symbols = [item["symbol"] for item in shortlist if item["tier"] == "NEAR_MISS"]
        # closest-to-passing (0.1pp gap) before mid (1.5pp gap).
        assert near_miss_symbols == ["MISS_CLOSE", "MISS_MID"]
        assert shortlist[2]["failed_gate"] == "fresh-leg"
        assert "8.1%" in shortlist[2]["near_miss_reason"]
        # the hard tradability miss is excluded from the pool but returned
        # separately for watchlist-only landing.
        assert [h["symbol"] for h in hard_near_misses] == ["MISS_TRAD"]
        assert hard_near_misses[0]["failed_gate"] == "tradability"
    finally:
        conn.close()


def test_shortlist_floor_caps_soft_near_miss_fill_at_ten(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    try:
        scanner_candidates.ensure_schema(conn)
        scanner_candidates.ensure_refusals_schema(conn)
        debate.ensure_schema(conn)
        _seed_candidate(conn, "SYM1", 1)
        for i in range(20):
            conn.execute(
                "INSERT INTO refusals (scan_date, symbol, setup_family, failed_gate, reason, evidence_json) "
                "VALUES (?, ?, 'pullback', 'fresh-leg', 'extension 9% exceeds 8% cap', '{}')",
                (AS_OF, f"MISS{i}"),
            )
        conn.commit()

        _patch_config(monkeypatch, shortlist_size=15)
        scan_date, shortlist, hard_near_misses = debate._load_shortlist(conn, AS_OF, debate._shortlist_size())

        assert len(shortlist) == 10  # floor: 1 survivor + 9 near-misses, not all 20
        assert hard_near_misses == []
    finally:
        conn.close()


def test_shortlist_pool_shrinks_below_floor_when_too_few_soft_near_misses_qualify(tmp_path, monkeypatch):
    """WO6: no padding — if only hard-fail refusals exist, the debate pool is
    just the survivors; it is never padded to the floor with hard fails."""
    conn = db.init_db(tmp_path / "m.db")
    try:
        scanner_candidates.ensure_schema(conn)
        scanner_candidates.ensure_refusals_schema(conn)
        debate.ensure_schema(conn)
        _seed_candidate(conn, "SYM1", 1)
        _seed_candidate(conn, "SYM2", 2)
        for i, gate in enumerate(["risk", "tradability", "regime", "risk"]):
            conn.execute(
                "INSERT INTO refusals (scan_date, symbol, setup_family, failed_gate, reason, evidence_json) "
                "VALUES (?, ?, 'pullback', ?, 'hard no', '{}')",
                (AS_OF, f"HARD{i}", gate),
            )
        conn.commit()

        _patch_config(monkeypatch, shortlist_size=15)
        scan_date, shortlist, hard_near_misses = debate._load_shortlist(conn, AS_OF, debate._shortlist_size())

        assert len(shortlist) == 2  # only the 2 survivors; no padding from hard fails
        assert all(item["tier"] == "PASSED" for item in shortlist)
        assert len(hard_near_misses) == 4
        assert {h["symbol"] for h in hard_near_misses} == {"HARD0", "HARD1", "HARD2", "HARD3"}
    finally:
        conn.close()


def test_shortlist_floor_not_needed_when_survivors_already_meet_it(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    try:
        scanner_candidates.ensure_schema(conn)
        scanner_candidates.ensure_refusals_schema(conn)
        debate.ensure_schema(conn)
        for idx in range(1, 12):
            _seed_candidate(conn, f"SYM{idx}", idx)
        conn.execute(
            "INSERT INTO refusals (scan_date, symbol, setup_family, failed_gate, reason, evidence_json) "
            "VALUES (?, 'MISS', 'pullback', 'risk', 'wide stop', '{}')",
            (AS_OF,),
        )
        conn.commit()

        _patch_config(monkeypatch, shortlist_size=15)
        scan_date, shortlist, hard_near_misses = debate._load_shortlist(conn, AS_OF, debate._shortlist_size())

        assert len(shortlist) == 11  # all 11 survivors returned (LIMIT 15), no near-miss needed
        assert all(item["tier"] == "PASSED" for item in shortlist)
        assert [h["symbol"] for h in hard_near_misses] == ["MISS"]  # risk is a hard gate
    finally:
        conn.close()


def test_near_miss_items_are_tagged_in_context_pack(tmp_path, monkeypatch):
    """The debate prompt must carry the near-miss failure honestly (G1)."""
    conn = db.init_db(tmp_path / "m.db")
    try:
        scanner_candidates.ensure_schema(conn)
        scanner_candidates.ensure_refusals_schema(conn)
        debate.ensure_schema(conn)
        _seed_candidate(conn, "SYM1", 1)
        conn.execute(
            "INSERT INTO refusals (scan_date, symbol, setup_family, failed_gate, reason, evidence_json) "
            "VALUES (?, 'MISS1', 'pullback', 'fresh-leg', 'extension 9% exceeds 8% cap', '{}')",
            (AS_OF,),
        )
        conn.commit()

        _patch_config(monkeypatch, shortlist_size=15)
        scan_date, shortlist, hard_near_misses = debate._load_shortlist(conn, AS_OF, debate._shortlist_size())
        packed = json.loads(debate._user_prompt(conn, scan_date, shortlist))
        by_symbol = {block["symbol"]: block for block in packed["shortlist"]}
        assert by_symbol["SYM1"]["tier"] == "PASSED"
        assert by_symbol["MISS1"]["tier"] == "NEAR_MISS"
        assert by_symbol["MISS1"]["near_miss"]["failed_gate"] == "fresh-leg"
        assert "9%" in by_symbol["MISS1"]["near_miss"]["reason"]
        assert hard_near_misses == []
    finally:
        conn.close()


def test_hard_near_miss_lands_on_watchlist_without_verdict_or_chart(tmp_path, monkeypatch):
    """WO6 acceptance: a hard-fail near-miss gets zero debate/chart/token spend
    but still lands on agent_watchlist tagged NEAR_MISS(hard:<gate>)."""
    conn = db.init_db(tmp_path / "m.db")
    try:
        _seed(conn, count=1)
        conn.execute(
            "INSERT INTO refusals (scan_date, symbol, setup_family, failed_gate, reason, evidence_json) "
            "VALUES (?, 'HARDMISS', 'pullback', 'tradability', 'ASM-flagged surveillance', '{}')",
            (AS_OF,),
        )
        conn.commit()
        _patch_config(monkeypatch, shortlist_size=1)
        rendered = {}

        def fake_render(_conn, scan_date, symbols):
            rendered["symbols"] = list(symbols)
            return {}

        from manas_os.agents import charts as charts_module

        monkeypatch.setattr(charts_module, "render_charts", fake_render)
        fake = FakeClient([{"symbol": "SYM1", "verdict": "TAKE", "conviction": 5, "rank": 1}])

        result = debate.run(conn, AS_OF, client=fake)

        assert result["status"] in {"ok", "partial"}
        # no verdict, no token spend for the hard near-miss
        assert conn.execute(
            "SELECT COUNT(*) FROM agent_verdicts WHERE symbol = 'HARDMISS'"
        ).fetchone()[0] == 0
        assert conn.execute(
            "SELECT COUNT(*) FROM scan_agent_logs WHERE agent = 'HARDMISS'"
        ).fetchone()[0] == 0
        # no chart render call for the hard near-miss
        assert "HARDMISS" not in rendered.get("symbols", [])
        # but it lands on the watchlist
        row = conn.execute(
            "SELECT tier, status FROM agent_watchlist WHERE scan_date = ? AND symbol = 'HARDMISS'",
            (AS_OF,),
        ).fetchone()
        assert row is not None
        assert row["tier"] == "NEAR_MISS(hard:tradability)"
    finally:
        conn.close()


def test_persisted_verdicts_carry_tier_column(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    try:
        scanner_candidates.ensure_schema(conn)
        scanner_candidates.ensure_refusals_schema(conn)
        debate.ensure_schema(conn)
        _seed_candidate(conn, "SYM1", 1)
        conn.execute(
            "INSERT INTO refusals (scan_date, symbol, setup_family, failed_gate, reason, evidence_json) "
            "VALUES (?, 'MISS1', 'pullback', 'fresh-leg', 'extension 9% exceeds 8% cap', '{}')",
            (AS_OF,),
        )
        conn.commit()
        _patch_config(monkeypatch, shortlist_size=15)
        fake = FakeClient([
            {"symbol": "SYM1", "verdict": "TAKE", "conviction": 5, "rank": 1},
            {"symbol": "MISS1", "verdict": "SKIP", "conviction": 2, "rank": 2,
             "reasoning": "failed gate: fresh-leg — extended 9%"},
        ])

        result = debate.run(conn, AS_OF, client=fake)

        assert result["status"] in {"ok", "partial"}
        rows = {
            r["symbol"]: r["tier"]
            for r in conn.execute(
                "SELECT symbol, tier FROM agent_verdicts WHERE agent = 'mock/model'"
            ).fetchall()
        }
        assert rows["SYM1"] == "PASSED"
        assert rows["MISS1"] == "NEAR_MISS"
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
