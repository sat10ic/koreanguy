import json

from fastapi.testclient import TestClient

from manas_os import db
from manas_os.agents import lessons, run_card, signals
from manas_os.api import app as api_app
from manas_os.scanner import candidates as scanner_candidates
from manas_os.scanner import expectancy as scanner_expectancy


AS_OF = "2026-06-30"


def _seed_night(conn):
    scanner_candidates.ensure_schema(conn)
    lessons.ensure_schema(conn)
    signals.ensure_schema(conn)
    conn.execute(
        "INSERT INTO regime_snapshots "
        "(snapshot_date, market_mode, xp_value, mbi_day_color, r4p5, r10, r20, r50) "
        "VALUES (?, 'SELECTIVE', 62, 'GREEN', 180, 1.4, 1.2, 1.1)",
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
            "run_date", "scan_date", "no_op", "regime", "governor", "heat", "pipeline", "shortlist",
            "debate", "chair", "vision", "sizer", "signals", "coach", "lessons_written", "errors",
            "morning_brief",
        ]:
            assert key in card

        assert card["run_date"] == AS_OF
        assert card["scan_date"] == AS_OF
        assert card["no_op"] is False
        assert card["regime"]["mode"] == "SELECTIVE"
        assert card["regime"]["age_days"] == 0
        assert card["regime"]["xp"] == 62
        assert card["regime"]["mbi_day_color"] == "GREEN"
        assert card["regime"]["ratios"] == {"r4p5": 180, "r10": 1.4, "r20": 1.2, "r50": 1.1}
        assert card["governor"]["market_mode"] == "SELECTIVE"
        assert card["governor"]["max_cards"] == 4
        assert card["governor"]["allowed_families"] == ["catalyst", "base/pattern"]
        assert card["heat"]["open_risk_pct"] == 0.0
        assert card["heat"]["cap_pct"] == card["governor"]["open_risk_cap_pct"]
        assert card["morning_brief"] == (
            "Regime SELECTIVE, day-color GREEN, XP 62.0. "
            "R10 1.4, R20 1.2, R50 1.1, burst-ratio 1.8:1 up:down. "
            "Reviewed 1 name across 1 model (1 verdict); chair took 1, sizer took 1. "
            "1 pipeline issue recorded. "
            "selective conditions call for staying picky."
        )
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


class _UnusedClient:
    """AD5: the brief is a deterministic template now — zero LLM tokens. A
    client passed to write() must be accepted (call-site compatibility) but
    never invoked; this stub raises if that contract is ever violated."""

    def chat(self, system, user):
        raise AssertionError("morning_brief must not call an LLM client")


def test_run_card_morning_brief_is_deterministic_and_ignores_client(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    monkeypatch.setattr(run_card, "LESSON_DIR", tmp_path / "lessons")
    monkeypatch.setattr(run_card, "RUN_CARD_ROOT", tmp_path / "run_cards")
    try:
        _seed_night(conn)
        path = run_card.write(conn, AS_OF, client=_UnusedClient())
        card = json.loads(path.read_text(encoding="utf-8"))
        assert card["morning_brief"] == (
            "Regime SELECTIVE, day-color GREEN, XP 62.0. "
            "R10 1.4, R20 1.2, R50 1.1, burst-ratio 1.8:1 up:down. "
            "Reviewed 1 name across 1 model (1 verdict); chair took 1, sizer took 1. "
            "1 pipeline issue recorded. "
            "selective conditions call for staying picky."
        )
    finally:
        conn.close()


def test_run_card_morning_brief_on_no_data_shell(tmp_path, monkeypatch):
    """No regime/debate/shortlist at all (test_run_card_no_data_still_writes_shell's
    scenario) — governor() degrades an unknown mode to NO_TRADE (never
    permissive), so the template still renders sensibly instead of crashing
    or reading as a fabricated real session."""
    conn = db.init_db(tmp_path / "m.db")
    monkeypatch.setattr(run_card, "LESSON_DIR", tmp_path / "lessons")
    monkeypatch.setattr(run_card, "RUN_CARD_ROOT", tmp_path / "run_cards")
    try:
        conn.commit()
        path = run_card.write(conn, "2026-07-01")
        card = json.loads(path.read_text(encoding="utf-8"))
        assert card["morning_brief"] == (
            "Regime NO_TRADE, day-color unavailable, XP unavailable. "
            "R10 —, R20 —, R50 —, burst-ratio unavailable. "
            "Reviewed 0 names across 0 models (0 verdicts); chair took 0, sizer took 0. "
            "0 pipeline issues recorded. "
            "no-trade conditions mean cash is the trade tonight."
        )
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


def test_run_card_records_total_outage_debate_fail_honestly(tmp_path, monkeypatch):
    """AU3: a total-outage night logs agents_debate with status='fail' (rows==0,
    all models failed) — the card's errors list must record it, not silently
    omit it because _errors() only checked ('error', 'partial')."""
    conn = db.init_db(tmp_path / "m.db")
    monkeypatch.setattr(run_card, "LESSON_DIR", tmp_path / "lessons")
    monkeypatch.setattr(run_card, "RUN_CARD_ROOT", tmp_path / "run_cards")
    try:
        conn.execute(
            "INSERT INTO pipeline_runs (run_date, stage, source, status, rows_affected, duration_s, detail) "
            "VALUES (?, 'agents_debate', 'agent_verdicts', 'fail', 0, 0.2, 'errors=deepseek/deepseek-chat: 500')",
            (AS_OF,),
        )
        conn.execute(
            "INSERT INTO pipeline_runs (run_date, stage, source, status, rows_affected, duration_s, detail) "
            "VALUES (?, 'agents_coach', 'journal_trades', 'skip', 0, 0.1, 'coach no open positions')",
            (AS_OF,),
        )
        conn.commit()

        path = run_card.write(conn, AS_OF)
        card = json.loads(path.read_text(encoding="utf-8"))

        assert card["errors"] == [
            {"stage": "agents_debate", "detail": "errors=deepseek/deepseek-chat: 500"}
        ]
    finally:
        conn.close()


def test_run_card_total_debate_outage_has_one_council_failure_message(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    monkeypatch.setattr(run_card, "LESSON_DIR", tmp_path / "lessons")
    monkeypatch.setattr(run_card, "RUN_CARD_ROOT", tmp_path / "run_cards")
    try:
        _seed_night(conn)
        conn.execute("DELETE FROM agent_verdicts WHERE scan_date = ?", (AS_OF,))
        conn.execute(
            "INSERT INTO pipeline_runs (run_date, stage, source, status, rows_affected, duration_s, detail) "
            "VALUES (?, 'agents_debate', 'agent_verdicts', 'fail', 0, 0.2, 'HTTP 429 rate limit')",
            (AS_OF,),
        )
        conn.commit()

        card = run_card.build(conn, AS_OF)

        assert card["council_status"] == {
            "state": "run_failed",
            "reason": "model errors",
            "ungraded_count": 1,
            "message": (
                "Council didn't run last night (model errors) — 1 gate-passed setup is ungraded. "
                "Review it manually on DECIDE or retry the council."
            ),
            "pipeline_message": (
                "Council models were rate-limited last night. 1 gate-passed candidate went ungraded."
            ),
        }
        assert card["tonights_call"]["stance"] == "SIT_OUT"
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
        assert card["no_op"] is True
    finally:
        conn.close()


def test_run_card_post_midnight_rerun_lands_on_same_scan_date_card(tmp_path, monkeypatch):
    """SHIP-2: one night's scan -> one card, keyed by scan_date. A
    post-midnight rerun (agents_coach fires after midnight, run_date rolls to
    the next calendar day but nothing new was scanned) resolves the SAME
    scan_date as the original run and must overwrite the SAME file — not
    mint a second run_date-stamped card that the desk then has to choose
    between (the SHIP-2 bug: 2026-07-10.json, no_op:true, next to the real
    populated 2026-07-09.json)."""
    conn = db.init_db(tmp_path / "m.db")
    monkeypatch.setattr(run_card, "LESSON_DIR", tmp_path / "lessons")
    run_cards_dir = tmp_path / "run_cards"
    monkeypatch.setattr(run_card, "RUN_CARD_ROOT", run_cards_dir)
    try:
        _seed_night(conn)  # writes real data for AS_OF (2026-06-30) only
        next_day = "2026-07-01"

        path = run_card.write(conn, next_day)
        card = json.loads(path.read_text(encoding="utf-8"))

        # The card lands under the scan_date it actually carries, not the
        # triggering run_date.
        assert path == run_cards_dir / f"{AS_OF}.json"
        assert not (run_cards_dir / f"{next_day}.json").exists()
        assert card["run_date"] == next_day
        assert card["scan_date"] == AS_OF
        # A real, describable night (SELECTIVE regime + a debated shortlist)
        # is not a no-op just because it was written by a post-midnight rerun.
        assert card["no_op"] is False
    finally:
        conn.close()


def test_run_card_no_op_only_when_no_scan_or_regime_data_at_all(tmp_path, monkeypatch):
    """no_op is reserved for genuinely empty nights — no scan_date and no
    regime snapshot resolvable at all — not for "not this exact run_date"."""
    conn = db.init_db(tmp_path / "m.db")
    monkeypatch.setattr(run_card, "LESSON_DIR", tmp_path / "lessons")
    run_cards_dir = tmp_path / "run_cards"
    monkeypatch.setattr(run_card, "RUN_CARD_ROOT", run_cards_dir)
    try:
        conn.commit()
        run_date = "2026-07-01"
        path = run_card.write(conn, run_date)
        card = json.loads(path.read_text(encoding="utf-8"))

        assert path == run_cards_dir / f"{run_date}.json"  # falls back to run_date
        assert card["scan_date"] is None
        assert card["no_op"] is True
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


def test_run_card_endpoint_falls_back_to_latest_completed_card_on_or_before_date(
    tmp_path, monkeypatch
):
    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    root = tmp_path / "run_cards"
    root.mkdir()
    (root / f"{AS_OF}.json").write_text(
        json.dumps({"run_date": AS_OF, "scan_date": AS_OF, "no_op": False}),
        encoding="utf-8",
    )
    monkeypatch.setattr(run_card, "RUN_CARD_ROOT", root)

    client = _api_client(db_path, monkeypatch)
    resp = client.get("/api/desk/run-card", params={"date": "2026-07-01"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is True
    assert body["requested_date"] == "2026-07-01"
    assert body["run_date"] == AS_OF
    assert body["scan_date"] == AS_OF


# ---------------------------------------------------------------------------
# SHIP-2 finding 3: TONIGHT'S CALL — deterministic stance decision table.
# ---------------------------------------------------------------------------


def test_tonights_call_stand_aside_on_no_trade_regime(tmp_path, monkeypatch):
    """NO_TRADE regime wins regardless of anything else on the card."""
    conn = db.init_db(tmp_path / "m.db")
    monkeypatch.setattr(run_card, "LESSON_DIR", tmp_path / "lessons")
    monkeypatch.setattr(run_card, "RUN_CARD_ROOT", tmp_path / "run_cards")
    try:
        run_date = "2026-07-01"
        conn.execute(
            "INSERT INTO regime_snapshots "
            "(snapshot_date, market_mode, xp_value, mbi_day_color, r4p5, r10, r20, r50) "
            "VALUES (?, 'NO_TRADE', 10, 'RED', 50, 0.5, 0.5, 0.5)",
            (run_date,),
        )
        conn.commit()

        path = run_card.write(conn, run_date)
        card = json.loads(path.read_text(encoding="utf-8"))

        assert card["tonights_call"]["stance"] == "STAND_ASIDE"
        assert card["tonights_call"]["headline"] == "No trades by design — cash is the position."
        assert len(card["tonights_call"]["what_to_do"]) >= 2
    finally:
        conn.close()


def test_tonights_call_sit_out_when_chair_takes_nothing(tmp_path, monkeypatch):
    """Chair reviewed names but struck/skipped all of them -> SIT_OUT."""
    conn = db.init_db(tmp_path / "m.db")
    monkeypatch.setattr(run_card, "LESSON_DIR", tmp_path / "lessons")
    monkeypatch.setattr(run_card, "RUN_CARD_ROOT", tmp_path / "run_cards")
    try:
        _seed_night(conn)
        conn.execute(
            "UPDATE agent_verdicts SET verdict = 'SKIP', reasoning = 'struck: spread too wide' "
            "WHERE scan_date = ? AND agent = 'chair'",
            (AS_OF,),
        )
        conn.commit()

        path = run_card.write(conn, AS_OF)
        card = json.loads(path.read_text(encoding="utf-8"))

        assert card["tonights_call"]["stance"] == "SIT_OUT"
        assert "1 name reviewed, none worth capital" in card["tonights_call"]["headline"]
        # base SIT_OUT lines are always present; a choppy-market line may be
        # appended on top when the four-phase read is a "Lack of" phase.
        what_to_do = card["tonights_call"]["what_to_do"]
        base_len = len(run_card._STANCE_WHAT_TO_DO["SIT_OUT"])
        assert what_to_do[:base_len] == run_card._STANCE_WHAT_TO_DO["SIT_OUT"]
    finally:
        conn.close()


def test_tonights_call_caution_when_family_base_rate_negative(tmp_path, monkeypatch):
    """Chair took the name, but the system loop shows a negative base rate at
    n>=20 for that (family, regime) cell -> CAUTION, not a plain green light."""
    conn = db.init_db(tmp_path / "m.db")
    monkeypatch.setattr(run_card, "LESSON_DIR", tmp_path / "lessons")
    monkeypatch.setattr(run_card, "RUN_CARD_ROOT", tmp_path / "run_cards")
    try:
        _seed_night(conn)
        scanner_expectancy.ensure_schema(conn)
        conn.execute(
            "INSERT INTO setup_expectancy (as_of, loop, setup_family, regime, cohort, n, "
            "hit_rate, mean_r, median_r, posterior_r, trust) "
            "VALUES (?, 'system', 'base/pattern', 'SELECTIVE', 'passed', 21, 0.0, -1.19, -1.0, -0.9, 'directional')",
            (AS_OF,),
        )
        conn.commit()

        path = run_card.write(conn, AS_OF)
        card = json.loads(path.read_text(encoding="utf-8"))

        assert card["tonights_call"]["stance"] == "CAUTION"
        assert "n=21" in card["tonights_call"]["headline"]
        assert "negative" in card["tonights_call"]["headline"]
    finally:
        conn.close()


def test_tonights_call_act_per_plan_when_takes_and_no_negative_base_rate(tmp_path, monkeypatch):
    """Chair took a name and the family has no proven-negative track record
    (unproven/positive) -> ACT_PER_PLAN, the constructive green light."""
    conn = db.init_db(tmp_path / "m.db")
    monkeypatch.setattr(run_card, "LESSON_DIR", tmp_path / "lessons")
    monkeypatch.setattr(run_card, "RUN_CARD_ROOT", tmp_path / "run_cards")
    try:
        _seed_night(conn)
        path = run_card.write(conn, AS_OF)
        card = json.loads(path.read_text(encoding="utf-8"))

        assert card["tonights_call"]["stance"] == "ACT_PER_PLAN"
        assert "1 setup cleared the gate" in card["tonights_call"]["headline"]
        assert card["tonights_call"]["what_to_do"] == run_card._STANCE_WHAT_TO_DO["ACT_PER_PLAN"]
    finally:
        conn.close()


def test_regime_block_exposes_four_phase(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    monkeypatch.setattr(run_card, "LESSON_DIR", tmp_path / "lessons")
    monkeypatch.setattr(run_card, "RUN_CARD_ROOT", tmp_path / "run_cards")
    try:
        _seed_night(conn)  # SELECTIVE + GREEN, no pillars_passed row
        path = run_card.write(conn, AS_OF)
        card = json.loads(path.read_text(encoding="utf-8"))

        assert card["regime"]["four_phase"] == "Lack of Supply"
        assert "four_phase_cite" in card["regime"]
    finally:
        conn.close()


def test_tonights_call_adds_choppy_line_in_lack_of_demand_phase(tmp_path, monkeypatch):
    """Deterministic template extension: a 'Lack of' four-phase read appends
    the cited TradeTM choppy-market line to SIT_OUT/CAUTION what_to_do."""
    conn = db.init_db(tmp_path / "m.db")
    monkeypatch.setattr(run_card, "LESSON_DIR", tmp_path / "lessons")
    monkeypatch.setattr(run_card, "RUN_CARD_ROOT", tmp_path / "run_cards")
    try:
        _seed_night(conn)
        # Force a WHITE/weak-pillar SELECTIVE tape -> Lack of Demand (chop).
        conn.execute(
            "UPDATE regime_snapshots SET mbi_day_color = 'WHITE', pillars_passed = 0 "
            "WHERE snapshot_date = ?",
            (AS_OF,),
        )
        conn.execute(
            "UPDATE agent_verdicts SET verdict = 'SKIP', reasoning = 'struck: spread too wide' "
            "WHERE scan_date = ? AND agent = 'chair'",
            (AS_OF,),
        )
        conn.commit()

        path = run_card.write(conn, AS_OF)
        card = json.loads(path.read_text(encoding="utf-8"))

        assert card["regime"]["four_phase"] == "Lack of Demand"
        assert card["tonights_call"]["stance"] == "SIT_OUT"
        what_to_do = card["tonights_call"]["what_to_do"]
        assert any("Choppy-tape read" in line for line in what_to_do)
        assert any("TTM-C3" in line for line in what_to_do)
    finally:
        conn.close()


def test_tonights_call_no_choppy_line_in_demand_domination(tmp_path, monkeypatch):
    """RISK_ON -> Demand Domination is not a chop phase; no line appended."""
    conn = db.init_db(tmp_path / "m.db")
    monkeypatch.setattr(run_card, "LESSON_DIR", tmp_path / "lessons")
    monkeypatch.setattr(run_card, "RUN_CARD_ROOT", tmp_path / "run_cards")
    try:
        _seed_night(conn)
        conn.execute(
            "UPDATE regime_snapshots SET market_mode = 'RISK_ON', mbi_day_color = 'GREEN', "
            "pillars_passed = 4 WHERE snapshot_date = ?",
            (AS_OF,),
        )
        conn.execute(
            "UPDATE agent_verdicts SET verdict = 'SKIP', reasoning = 'struck: spread too wide' "
            "WHERE scan_date = ? AND agent = 'chair'",
            (AS_OF,),
        )
        conn.commit()

        path = run_card.write(conn, AS_OF)
        card = json.loads(path.read_text(encoding="utf-8"))

        assert card["regime"]["four_phase"] == "Demand Domination"
        assert card["tonights_call"]["what_to_do"] == run_card._STANCE_WHAT_TO_DO["SIT_OUT"]
    finally:
        conn.close()


def test_tonights_call_adds_choppy_line_in_supply_domination_phase(tmp_path, monkeypatch):
    """Round-5 doctrine fix: Supply Domination (not Lack of Supply) is the
    choppy/failure-prone read alongside Lack of Demand."""
    conn = db.init_db(tmp_path / "m.db")
    monkeypatch.setattr(run_card, "LESSON_DIR", tmp_path / "lessons")
    monkeypatch.setattr(run_card, "RUN_CARD_ROOT", tmp_path / "run_cards")
    try:
        _seed_night(conn)
        conn.execute(
            "UPDATE regime_snapshots SET market_mode = 'DEFENSIVE' WHERE snapshot_date = ?",
            (AS_OF,),
        )
        conn.execute(
            "UPDATE agent_verdicts SET verdict = 'SKIP', reasoning = 'struck: spread too wide' "
            "WHERE scan_date = ? AND agent = 'chair'",
            (AS_OF,),
        )
        conn.commit()

        path = run_card.write(conn, AS_OF)
        card = json.loads(path.read_text(encoding="utf-8"))

        assert card["regime"]["four_phase"] == "Supply Domination"
        assert card["tonights_call"]["stance"] == "SIT_OUT"
        what_to_do = card["tonights_call"]["what_to_do"]
        assert any("Choppy-tape read" in line for line in what_to_do)
        assert any("TTM-C3" in line for line in what_to_do)
    finally:
        conn.close()


def test_tonights_call_adds_constructive_line_in_lack_of_supply_phase(tmp_path, monkeypatch):
    """Round-5 doctrine fix: Lack of Supply is the OPPOSITE of choppy per
    TradeTM C1 -- supply exhausted, long setups tend to follow through -- so
    it gets a constructive note, never the choppy-tape caution line."""
    conn = db.init_db(tmp_path / "m.db")
    monkeypatch.setattr(run_card, "LESSON_DIR", tmp_path / "lessons")
    monkeypatch.setattr(run_card, "RUN_CARD_ROOT", tmp_path / "run_cards")
    try:
        _seed_night(conn)  # SELECTIVE + GREEN, no pillars_passed row -> Lack of Supply
        conn.execute(
            "UPDATE agent_verdicts SET verdict = 'SKIP', reasoning = 'struck: spread too wide' "
            "WHERE scan_date = ? AND agent = 'chair'",
            (AS_OF,),
        )
        conn.commit()

        path = run_card.write(conn, AS_OF)
        card = json.loads(path.read_text(encoding="utf-8"))

        assert card["regime"]["four_phase"] == "Lack of Supply"
        assert card["tonights_call"]["stance"] == "SIT_OUT"
        what_to_do = card["tonights_call"]["what_to_do"]
        assert any("Lack of Supply" in line and "TradeTM C1" in line for line in what_to_do)
        assert not any("Choppy-tape read" in line for line in what_to_do)
    finally:
        conn.close()
