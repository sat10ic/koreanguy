import json

from manas_os import db
from manas_os.agents import coach, debate, signals

AS_OF = "2026-06-30"


class MockClient:
    def __init__(self, raw=None, exc=None):
        self.raw = raw
        self.exc = exc
        self.calls = 0

    def chat(self, *, system, user):
        self.calls += 1
        if self.exc:
            raise self.exc
        return self.raw, "mock/coach"


def _patch_config(monkeypatch, *, live=False):
    def fake_get(key, default=None):
        values = {
            "agents.telegram_live": live,
            "agents.coach_model": "mock/coach",
            "agents.models": ["mock/default"],
            "agents.api_key": "test-key",
        }
        return values.get(key, default)

    monkeypatch.setattr(coach.config, "get", fake_get)
    monkeypatch.setattr(signals.config, "get", fake_get)


def _seed_open_position(conn, *, symbol="AAA", trade_date="2026-06-20", entry=100.0, stop=95.0):
    debate.ensure_schema(conn)
    signals.ensure_schema(conn)
    conn.execute(
        "INSERT INTO journal_trades (trade_date, symbol, setup, entry, stop, exit, mistake_tags_json) "
        "VALUES (?, ?, 'Pullback', ?, ?, NULL, '[]')",
        (trade_date, symbol, entry, stop),
    )
    conn.execute(
        "INSERT OR REPLACE INTO agent_verdicts "
        "(scan_date, symbol, agent, verdict, conviction, rank, lens_scores_json, bull_case, bear_case, reasoning) "
        "VALUES (?, ?, 'chair', 'TAKE', 5, 1, '{}', 'your thesis was clean pocket pivot demand', "
        "'Break below 21EMA invalidates.', 'chair take')",
        (trade_date, symbol),
    )
    conn.executemany(
        "INSERT OR REPLACE INTO daily_prices "
        "(symbol, trade_date, series, open, high, low, close, prev_close, volume, source) "
        "VALUES (?, ?, 'EQ', ?, ?, ?, ?, ?, ?, 'test')",
        [
            (symbol, "2026-06-20", 100, 102, 99, 100, 99, 1000),
            (symbol, "2026-06-21", 104, 106, 103, 105, 100, 1000),
            (symbol, "2026-06-22", 108, 111, 107, 110, 105, 1000),
            (symbol, AS_OF, 111, 114, 110, 112, 110, 1000),
        ],
    )
    conn.commit()


def _coach_row(conn, symbol="AAA"):
    return conn.execute(
        "SELECT symbol, channel, message, sent FROM agent_signals WHERE scan_date = ? AND symbol = ? AND channel = 'coach'",
        (AS_OF, symbol),
    ).fetchone()


def test_coach_persists_llm_narrative_with_thesis_and_suffix(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    try:
        _patch_config(monkeypatch, live=False)
        _seed_open_position(conn)
        raw = json.dumps([
            {
                "symbol": "AAA",
                "stance": "agree",
                "message": "Your thesis was clean pocket pivot demand - it held because price advanced in open R.",
            }
        ])

        result = coach.run(conn, AS_OF, client=MockClient(raw=raw), sender=lambda _message: None)

        assert result["status"] == "ok"
        row = _coach_row(conn)
        assert row["channel"] == "coach"
        assert row["sent"] == 0
        assert "TRIM 25-33% into strength" in row["message"]
        assert "Your thesis was clean pocket pivot demand" in row["message"]
        assert signals.MANUAL_SUFFIX in row["message"]
    finally:
        conn.close()


def test_coach_llm_failure_still_persists_deterministic_action(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    try:
        _patch_config(monkeypatch, live=False)
        _seed_open_position(conn)

        result = coach.run(conn, AS_OF, client=MockClient(exc=RuntimeError("llm down")))

        assert result["status"] == "partial"
        row = _coach_row(conn)
        assert row is not None
        assert "TRIM 25-33% into strength" in row["message"]
        assert "llm down" not in row["message"]
        assert signals.MANUAL_SUFFIX in row["message"]
        log = conn.execute(
            "SELECT parsed_ok, validation, error FROM scan_agent_logs WHERE agent = 'coach' ORDER BY log_id DESC LIMIT 1"
        ).fetchone()
        assert log["parsed_ok"] == 0
        assert log["validation"] == "deterministic-only"
        assert "llm down" in log["error"]
    finally:
        conn.close()


def test_coach_exit_now_message_is_flagged_urgent(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    try:
        _patch_config(monkeypatch, live=False)
        _seed_open_position(conn)
        monkeypatch.setattr(coach.eod_detectors, "two_strike", lambda _bars, _stop=None: {"fired": ["below-21EMA", "gap-down-open"], "exit_now": True})

        result = coach.run(conn, AS_OF, client=MockClient(raw="[]"))

        assert result["status"] == "ok"
        row = _coach_row(conn)
        assert "EXIT TODAY" in row["message"]
        assert "URGENT: deterministic exit_now fired" in row["message"]
        assert row["channel"] == "coach"
        trade = conn.execute("SELECT first_exit_flag_date FROM journal_trades WHERE symbol = 'AAA'").fetchone()
        assert trade["first_exit_flag_date"] == AS_OF
    finally:
        conn.close()


def test_coach_narrates_two_open_positions_in_one_call(tmp_path, monkeypatch):
    """AU8: coach must handle >1 open position in a single call, matching each
    narrative back to its own symbol and persisting a signal row per symbol."""
    conn = db.init_db(tmp_path / "m.db")
    try:
        _patch_config(monkeypatch, live=False)
        _seed_open_position(conn, symbol="AAA", trade_date="2026-06-20", entry=100.0, stop=95.0)
        _seed_open_position(conn, symbol="BBB", trade_date="2026-06-21", entry=200.0, stop=190.0)
        raw = json.dumps([
            {"symbol": "AAA", "stance": "agree", "message": "AAA thesis holding, demand intact."},
            {"symbol": "BBB", "stance": "note", "message": "BBB thesis holding, watch the base."},
        ])

        result = coach.run(conn, AS_OF, client=MockClient(raw=raw), sender=lambda _message: None)

        assert result["status"] == "ok"
        assert result["rows"] == 2
        row_aaa = _coach_row(conn, "AAA")
        row_bbb = _coach_row(conn, "BBB")
        assert row_aaa is not None and row_bbb is not None
        assert "AAA thesis holding" in row_aaa["message"]
        assert "BBB thesis holding" in row_bbb["message"]
        assert "AAA thesis holding" not in row_bbb["message"]
        assert "BBB thesis holding" not in row_aaa["message"]
    finally:
        conn.close()


def test_coach_line_bank_loads_from_repo_file():
    bank = coach._parse_coach_lines_bank(coach.COACH_LINES_PATH.read_text(encoding="utf-8"))
    assert "exit_now" in bank and bank["exit_now"]
    assert "new_position" in bank and bank["new_position"]
    assert "drawdown" in bank and bank["drawdown"]
    assert "No mental stop" not in bank["exit_now"][0]  # sanity: not accidentally mixed up
    assert "mental stop" in bank["new_position"][0].lower()


def test_coach_lines_selection_is_deterministic_key_match():
    exit_position = {"exit_now": True, "verdict": "EXIT", "phase": "TREND"}
    lines = coach._coach_lines_for_position(exit_position)
    assert lines  # exit_now bank has entries
    assert len(lines) <= coach.MAX_COACH_LINES
    bank = coach._coach_lines_bank()
    assert lines[0] == bank["exit_now"][0]

    new_position = {"exit_now": False, "phase": "INITIATION", "r": 0}
    lines2 = coach._coach_lines_for_position(new_position)
    assert lines2
    assert lines2[0] == coach._coach_lines_bank()["new_position"][0]

    drawdown_position = {"exit_now": False, "phase": "TREND", "r": -0.4}
    lines3 = coach._coach_lines_for_position(drawdown_position)
    assert lines3
    assert lines3[0] == coach._coach_lines_bank()["drawdown"][0]

    # a plain healthy TREND hold matches only the trend_hold reassurance line
    plain_position = {"exit_now": False, "phase": "TREND", "r": 0.5}
    plain_lines = coach._coach_lines_for_position(plain_position)
    assert plain_lines == [coach._coach_lines_bank()["trend_hold"][0]]

    # no situation matches at all -> no coach lines forced
    neutral_position = {"exit_now": False, "phase": "OTHER", "r": 0.5}
    assert coach._coach_lines_for_position(neutral_position) == []


def test_render_message_includes_matched_coach_line(tmp_path):
    position = {
        "symbol": "AAA",
        "action_line": "HOLD - do nothing.",
        "exit_now": False,
        "phase": "INITIATION",
        "r": 0,
        "banner": None,
    }
    message = coach._render_message(position, None)
    assert "mental stop" in message.lower()


# ---------------------------------------------------------------------------
# compose_action_sentence -- the single writer for the MANAGE-card action
# sentence (USABILITY_UX_AUDIT_2026-07-19.md defect #4: badge said
# "EXIT NOW", coach line separately said "near the close"). Distinct from
# _plain_action_line, which still feeds the Telegram coach message
# unchanged (outbox lane is out of scope for this fix).
# ---------------------------------------------------------------------------


def test_compose_action_sentence_exit_leads_with_verdict_timing_method():
    trail = {"phase": "INITIATION", "trail_stop": None, "action": None}
    strikes = {"exit_now": True, "fired": ["below-21EMA", "gap-down-open"]}

    sentence = coach.compose_action_sentence("EXIT", trail, strikes, stop=95.0)

    assert sentence.startswith("EXIT today near the close (15:00-15:25)")
    assert "sell the full position at market" in sentence
    assert "2 exit rules fired (below-21EMA, gap-down-open)" in sentence


def test_compose_action_sentence_exit_singular_rule_count_is_grammatical():
    trail = {"phase": "INITIATION", "trail_stop": None, "action": None}
    strikes = {"exit_now": True, "fired": ["stop-breached"]}

    sentence = coach.compose_action_sentence("EXIT", trail, strikes, stop=95.0)

    assert "1 exit rule fired (stop-breached)" in sentence


def test_compose_action_sentence_exit_puts_account_before_the_fired_reason():
    trail = {"phase": "INITIATION", "trail_stop": None, "action": None}
    strikes = {"exit_now": True, "fired": ["stop-breached"]}

    sentence = coach.compose_action_sentence(
        "EXIT", trail, strikes, stop=95.0, account_label="Zerodha (FOU446)"
    )

    assert "in your Zerodha (FOU446) account" in sentence
    assert sentence.index("in your Zerodha (FOU446) account") < sentence.index("1 exit rule fired")


def test_compose_action_sentence_no_account_label_omits_the_suffix():
    trail = {"phase": "INITIATION", "trail_stop": None, "action": None}
    strikes = {"exit_now": True, "fired": ["stop-breached"]}

    sentence = coach.compose_action_sentence("EXIT", trail, strikes, stop=95.0, account_label=None)

    assert "in your" not in sentence
    assert "account" not in sentence


def test_compose_action_sentence_move_stop_trim_and_hold_branches():
    strikes = {"exit_now": False, "fired": []}

    move_stop = coach.compose_action_sentence(
        "MOVE_STOP", {"phase": "TREND", "trail_stop": 110.0, "action": "trail EMA10"}, strikes, stop=100.0
    )
    assert move_stop.startswith("MOVE STOP today to 110.0 (trailing EMA10)")
    assert "no exit action needed" in move_stop

    trim = coach.compose_action_sentence(
        "TRIM", {"phase": "EXTENSION", "trail_stop": 108.0, "action": None}, strikes, stop=100.0
    )
    assert trim.startswith("TRIM today")
    assert "108.0" in trim

    hold_trend = coach.compose_action_sentence(
        "HOLD", {"phase": "TREND", "trail_stop": 105.0, "action": "trail EMA21"}, strikes, stop=100.0, r=1.2
    )
    assert hold_trend.startswith("HOLD today - trail stop moves to 105.0")
    assert "You're +1.2R." in hold_trend

    hold_no_r = coach.compose_action_sentence(
        "HOLD", {"phase": "TREND", "trail_stop": 105.0, "action": "trail EMA21"}, strikes, stop=100.0, r=None
    )
    assert "You're +" not in hold_no_r

    hold_default = coach.compose_action_sentence(
        "HOLD", {"phase": "INITIATION", "trail_stop": None, "action": None}, strikes, stop=95.0
    )
    assert hold_default.startswith("HOLD today - do nothing; stop stays at 95.0")


def test_compose_action_sentence_leading_verdict_word_matches_badge_input():
    """The sentence must lead with (or open on, for EXIT) the same verdict
    word the caller renders in the badge -- this is what makes badge and
    sentence structurally unable to disagree."""
    strikes = {"exit_now": False, "fired": []}
    for verdict, expect_prefix in (("MOVE_STOP", "MOVE STOP"), ("TRIM", "TRIM"), ("HOLD", "HOLD")):
        sentence = coach.compose_action_sentence(
            verdict, {"phase": "EXTENSION" if verdict == "TRIM" else "INITIATION", "trail_stop": 100.0, "action": None},
            strikes, stop=95.0,
        )
        assert sentence.startswith(expect_prefix)


def test_plain_action_line_telegram_text_is_unaffected_by_the_new_composer():
    """Regression guard: compose_action_sentence is additive. The Telegram-
    facing _plain_action_line text (which _render_message embeds in the
    outbound coach message) must keep its exact original wording -- alerts/
    live/heartbeat (the outbox lane) is explicitly out of scope here."""
    trade_row = {"stop": 95.0}
    trail = {"phase": "INITIATION", "trail_stop": None, "action": None}
    strikes = {"exit_now": True, "fired": ["below-21EMA"]}

    line = coach._plain_action_line(trade_row, trail, strikes)

    assert line == "EXIT TODAY - 1 exit rules fired (below-21EMA). Sell the full position near the close."


def test_coach_live_send_enqueues_and_delivers_after_commit(tmp_path, monkeypatch):
    """RELIABILITY_AUDIT_2026-07-19 #8: coach used to call send() mid-loop,
    with the run's single conn.commit() only happening much later. The live
    sender must now only ever be invoked AFTER every business write for the
    run (agent_signals, pipeline_runs, lessons, run_card) has committed."""
    conn = db.init_db(tmp_path / "m.db")
    try:
        _patch_config(monkeypatch, live=True)
        _seed_open_position(conn)
        raw = json.dumps([
            {"symbol": "AAA", "stance": "agree", "message": "AAA thesis holding, demand intact."},
        ])
        sent: list[str] = []

        result = coach.run(conn, AS_OF, client=MockClient(raw=raw), sender=lambda m: sent.append(m))

        assert result["status"] == "ok"
        assert result["sent"] == 1
        assert sent  # the live sender was actually invoked
        row = _coach_row(conn)
        assert row["sent"] == 1
        outbox_row = conn.execute(
            "SELECT state FROM telegram_outbox WHERE kind = 'coach_signal'"
        ).fetchone()
        assert outbox_row["state"] == "sent"
    finally:
        conn.close()


def test_coach_live_send_failure_marks_partial_but_business_writes_still_committed(tmp_path, monkeypatch):
    """A Telegram send failure must not lose or roll back the run's business
    writes (that was the bug: everything committed in one place, after the
    send). It only leaves the outbox row pending/retryable and the returned
    result reflects the failed delivery."""
    conn = db.init_db(tmp_path / "m.db")
    try:
        _patch_config(monkeypatch, live=True)
        _seed_open_position(conn)
        raw = json.dumps([
            {"symbol": "AAA", "stance": "agree", "message": "AAA thesis holding, demand intact."},
        ])

        def fail_sender(_message):
            raise RuntimeError("telegram down")

        result = coach.run(conn, AS_OF, client=MockClient(raw=raw), sender=fail_sender)

        assert result["status"] == "partial"
        assert result["sent"] == 0
        row = _coach_row(conn)
        assert row is not None
        assert row["sent"] == 0  # message text/persistence unaffected by the send outcome

        outbox_row = conn.execute(
            "SELECT state, attempts FROM telegram_outbox WHERE kind = 'coach_signal'"
        ).fetchone()
        assert outbox_row["state"] == "pending"
        assert outbox_row["attempts"] == 1

        pipeline_row = conn.execute(
            "SELECT status FROM pipeline_runs WHERE stage = 'agents_coach' ORDER BY run_id DESC LIMIT 1"
        ).fetchone()
        assert pipeline_row["status"] == "ok"  # business stage succeeded regardless of delivery
    finally:
        conn.close()


def test_coach_no_open_positions_writes_skip_row(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    try:
        _patch_config(monkeypatch, live=False)

        result = coach.run(conn, AS_OF)

        assert result["status"] == "skip"
        row = conn.execute(
            "SELECT status, rows_affected, detail FROM pipeline_runs WHERE stage = 'agents_coach' ORDER BY run_id DESC LIMIT 1"
        ).fetchone()
        assert row["status"] == "skip"
        assert row["rows_affected"] == 0
        assert "no open positions" in row["detail"]
    finally:
        conn.close()
