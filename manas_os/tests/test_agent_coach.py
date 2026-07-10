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
        monkeypatch.setattr(coach.eod_detectors, "two_strike", lambda _bars: {"fired": ["below-21EMA", "gap-down-open"], "exit_now": True})

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
