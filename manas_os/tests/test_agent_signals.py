import json

from manas_os import db
from manas_os.agents import debate, signals
from manas_os.alerts import outbox
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


def test_signals_live_send_enqueues_and_delivers_after_commit(tmp_path, monkeypatch):
    """RELIABILITY_AUDIT_2026-07-19 #8, sibling of the coach.py fix: signals
    used to call send() inline mid-loop with persistence committed separately
    by the caller. The live sender must now only ever be invoked AFTER the
    agent_signals business write (and its outbox row) has durably committed,
    with sent-status flipped to 1 only once delivery actually succeeded."""
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        _patch_config(monkeypatch, live=True)
        _seed_pick(conn)
        durable_at_send: list = []

        def sender(message):
            # Proof of ordering: a SECOND connection (its own transaction)
            # must already see the committed business row -- still sent=0 --
            # at the moment the network send happens.
            other = db.connect(db_path)
            try:
                row = other.execute(
                    "SELECT sent FROM agent_signals "
                    "WHERE scan_date = ? AND symbol = 'AAA' AND channel = 'telegram'",
                    (AS_OF,),
                ).fetchone()
                durable_at_send.append(dict(row) if row else None)
            finally:
                other.close()

        result = signals.run(conn, AS_OF, sender=sender)

        assert result["status"] == "ok"
        assert result["sent"] == 1
        assert durable_at_send == [{"sent": 0}]  # committed before send; marked sent only after
        assert _signal_row(conn)["sent"] == 1
        outbox_row = conn.execute(
            "SELECT alert_key, state FROM telegram_outbox WHERE kind = 'entry_signal'"
        ).fetchone()
        assert outbox_row["alert_key"] == f"entry_signal:{AS_OF}:AAA:telegram"
        assert outbox_row["state"] == "sent"
    finally:
        conn.close()


def test_signals_transient_failure_stays_pending_and_never_duplicates(tmp_path, monkeypatch):
    """A transient send failure must leave the outbox row pending/retryable
    (not lost), keep the business write durably committed, and a later
    retry/redelivery must send the SAME alert_key exactly once -- rerunning
    signals.run can neither enqueue a duplicate row nor resend."""
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        _patch_config(monkeypatch, live=True)
        _seed_pick(conn)
        calls: list[str] = []

        def fail_sender(message):
            calls.append(message)
            raise RuntimeError("telegram down")

        result = signals.run(conn, AS_OF, sender=fail_sender)

        assert result["status"] == "partial"
        assert result["sent"] == 0
        assert "telegram down" in result["detail"]
        assert len(calls) == 1

        key = f"entry_signal:{AS_OF}:AAA:telegram"
        row = outbox.get(conn, key)
        assert row["state"] == "pending"  # retryable, NOT permanently lost
        assert row["attempts"] == 1
        assert "telegram down" in row["last_error"]

        # Business write survived the failed send, durably (fresh connection).
        other = db.connect(db_path)
        try:
            persisted = other.execute(
                "SELECT sent FROM agent_signals "
                "WHERE scan_date = ? AND symbol = 'AAA' AND channel = 'telegram'",
                (AS_OF,),
            ).fetchone()
            assert persisted is not None and persisted["sent"] == 0
        finally:
            other.close()

        # Backoff not yet elapsed: redelivery right now must not call the sender.
        early = outbox.deliver_pending(conn, lambda p: calls.append(p["message"]))
        assert early["delivered"] == [] and early["retried"] == []
        assert len(calls) == 1

        # Once due, the SAME row (same alert_key) delivers exactly once.
        later = outbox.deliver_pending(
            conn,
            lambda p: calls.append(p["message"]) or {"message_id": "m-1"},
            now="2100-01-01T00:00:00",
        )
        assert later["delivered"] == [key]
        assert len(calls) == 2
        assert outbox.get(conn, key)["state"] == "sent"

        # A rerun of signals.run cannot enqueue a duplicate or resend.
        rerun = signals.run(conn, AS_OF, sender=fail_sender)
        assert rerun["sent"] == 0
        assert len(calls) == 2  # sender never invoked again for the sent row
        n = conn.execute(
            "SELECT COUNT(*) AS n FROM telegram_outbox WHERE alert_key = ?", (key,)
        ).fetchone()["n"]
        assert n == 1
    finally:
        conn.close()
