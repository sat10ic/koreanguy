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
