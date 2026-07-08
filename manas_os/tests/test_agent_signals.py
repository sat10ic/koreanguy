import json

from manas_os import db
from manas_os.agents import debate, signals
from manas_os.scanner import candidates as scanner_candidates


AS_OF = "2026-06-30"


def _patch_config(monkeypatch, *, live=False):
    def fake_get(key, default=None):
        values = {"agents.telegram_live": live}
        return values.get(key, default)

    monkeypatch.setattr(signals.config, "get", fake_get)


def _seed_pick(conn):
    scanner_candidates.ensure_schema(conn)
    debate.ensure_schema(conn)
    signals.ensure_schema(conn)
    conn.execute(
        "INSERT OR REPLACE INTO scan_candidates "
        "(scan_date, symbol, setup, setup_type, setup_family, readiness, grade, entry, stop, rr, suggested_qty, "
        "evidence_json, timing_json, score_breakdown_json, trade_plan_json, gates_json, rank, rank_of) "
        "VALUES (?, 'AAA', 'Pullback-to-EMA', 'pullback', 'momentum', 90, 'A', 101.5, 97.25, 2.6, 100, "
        "'[]', '{}', '{}', '{}', '[]', 1, 1)",
        (AS_OF,),
    )
    conn.execute(
        "INSERT OR REPLACE INTO agent_verdicts "
        "(scan_date, symbol, agent, verdict, conviction, rank, lens_scores_json, bear_case, reasoning) "
        "VALUES (?, 'AAA', 'model/high', 'TAKE', 5, 1, '{}', 'Gap fill below pivot.', 'Best setup.')",
        (AS_OF,),
    )
    conn.execute(
        "INSERT OR REPLACE INTO agent_verdicts "
        "(scan_date, symbol, agent, verdict, conviction, rank, lens_scores_json, bear_case, reasoning) "
        "VALUES (?, 'AAA', 'model/low', 'TAKE', 3, 2, '{}', 'Needs volume.', 'Second view.')",
        (AS_OF,),
    )
    conn.execute(
        "INSERT OR REPLACE INTO agent_verdicts "
        "(scan_date, symbol, agent, verdict, conviction, rank, lens_scores_json, bear_case, reasoning) "
        "VALUES (?, 'AAA', 'chair', 'TAKE', 4, 1, ?, ?, 'chair take')",
        (
            AS_OF,
            json.dumps({"verdict_split": "2T/0S", "disagreement": False}),
            json.dumps([{"agent": "model/high", "text": "Gap fill below pivot."}]),
        ),
    )
    conn.execute(
        "INSERT OR REPLACE INTO agent_verdicts "
        "(scan_date, symbol, agent, verdict, conviction, rank, lens_scores_json, reasoning) "
        "VALUES (?, 'AAA', 'sizer', 'TAKE', NULL, 1, ?, 'Size after validation.')",
        (AS_OF, json.dumps({"multiplier": 0.75, "final_qty": 75, "validated": True})),
    )
    conn.commit()


def _signal_row(conn):
    return conn.execute(
        "SELECT symbol, channel, message, sent FROM agent_signals WHERE scan_date = ?",
        (AS_OF,),
    ).fetchone()


def test_signals_dry_run_persists_rendered_message_without_sending(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    try:
        _patch_config(monkeypatch, live=False)
        _seed_pick(conn)
        sent = []

        result = signals.run(conn, AS_OF, sender=lambda message: sent.append(message))

        assert result["status"] == "ok"
        assert result["sent"] == 0
        assert sent == []
        row = _signal_row(conn)
        assert row["symbol"] == "AAA"
        assert row["channel"] == "telegram"
        assert row["sent"] == 0
        assert "entry 101.5" in row["message"]
        assert "stop 97.25" in row["message"]
        assert "RR 2.6" in row["message"]
        assert "final_qty 75" in row["message"]
        assert "multiplier 0.75" in row["message"]
        assert "top risk: Gap fill below pivot." in row["message"]
        assert signals.MANUAL_SUFFIX in row["message"]
    finally:
        conn.close()


def test_signals_live_send_marks_sent_with_mocked_transport(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    try:
        _patch_config(monkeypatch, live=True)
        _seed_pick(conn)
        sent = []

        result = signals.run(conn, AS_OF, sender=lambda message: sent.append(message))

        assert result["status"] == "ok"
        assert result["sent"] == 1
        assert len(sent) == 1
        assert signals.MANUAL_SUFFIX in sent[0]
        assert _signal_row(conn)["sent"] == 1
    finally:
        conn.close()


def test_signals_send_failure_keeps_unsent_and_does_not_raise(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    try:
        _patch_config(monkeypatch, live=True)
        _seed_pick(conn)

        def fail_sender(_message):
            raise RuntimeError("telegram down")

        result = signals.run(conn, AS_OF, sender=fail_sender)

        assert result["status"] == "partial"
        assert result["sent"] == 0
        assert "telegram down" in result["detail"]
        assert _signal_row(conn)["sent"] == 0
        log = conn.execute(
            "SELECT parsed_ok, validation, error FROM scan_agent_logs WHERE agent = 'signals' ORDER BY log_id DESC LIMIT 1"
        ).fetchone()
        assert log["parsed_ok"] == 0
        assert log["validation"] == "partial"
        assert "telegram down" in log["error"]
    finally:
        conn.close()
