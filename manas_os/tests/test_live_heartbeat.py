"""Tests for manas_os.live.heartbeat -- RELIABILITY_AUDIT_2026-07-19 #8:
the heartbeat used to write its unique (trade_date, slot) row BEFORE
attempting the send and swallow a send failure, so once that row existed a
transient failure could never be retried (`is_new` gated the send attempt
and only true on the very first call for that slot). Delivery now goes
through the transactional outbox and is attempted on every call, not only
when the row is new.
"""
from __future__ import annotations

from manas_os import db
from manas_os.live import heartbeat
from manas_os.tests.conftest import AS_OF


def _patch_dry_run(monkeypatch, *, dry_run: bool):
    def fake_get(key, default=None):
        values = {"telegram.dry_run": dry_run, "telegram.bot_token": "x", "telegram.chat_id": "y"}
        return values.get(key, default)

    monkeypatch.setattr(heartbeat.telegram_engine.config, "get", fake_get)


def test_dry_run_heartbeat_marks_sent_via_paper_state_machine(tmp_path, monkeypatch):
    """dry_run delivers to the paper log and marks sent -- the state machine
    is identical in paper and live, so a dry_run heartbeat still walks the
    outbox row from pending to sent."""
    conn = db.init_db(tmp_path / "manas.db")
    try:
        _patch_dry_run(monkeypatch, dry_run=True)
        result = heartbeat.send_heartbeat(
            conn, AS_OF, armed_count=3, market_mode="SELECTIVE", ws_ok=True, token_ok=True,
        )
        assert result["new"] is True
        assert result["sent"] is True
        row = conn.execute(
            "SELECT state FROM telegram_outbox WHERE alert_key = ?",
            (f"heartbeat:{AS_OF}:09:20",),
        ).fetchone()
        assert row["state"] == "sent"
    finally:
        conn.close()


def test_repeat_call_same_slot_is_not_new_and_does_not_duplicate_outbox_row(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        _patch_dry_run(monkeypatch, dry_run=True)
        heartbeat.send_heartbeat(conn, AS_OF, armed_count=3, market_mode="SELECTIVE", ws_ok=True, token_ok=True)
        result2 = heartbeat.send_heartbeat(conn, AS_OF, armed_count=3, market_mode="SELECTIVE", ws_ok=True, token_ok=True)
        assert result2["new"] is False
        count = conn.execute("SELECT COUNT(*) AS n FROM telegram_outbox").fetchone()["n"]
        assert count == 1
    finally:
        conn.close()


def test_transient_send_failure_no_longer_permanently_blocks_retry(tmp_path, monkeypatch):
    """The exact bug: heartbeat.py wrote its unique row before sending and
    swallowed the send failure, so the row itself blocked any future retry.
    Now delivery is attempted on every call (gated by outbox backoff, not by
    `is_new`), so a transient failure on call 1 is retried and delivered on
    call 2 even though the live_heartbeats row for that slot already
    exists."""
    conn = db.init_db(tmp_path / "manas.db")
    try:
        _patch_dry_run(monkeypatch, dry_run=False)
        attempts: list[int] = []

        def flaky(_message):
            attempts.append(1)
            if len(attempts) == 1:
                raise RuntimeError("telegram down")

        first_call = "2026-07-19T09:20:00"
        result1 = heartbeat.send_heartbeat(
            conn, AS_OF, armed_count=1, market_mode="SELECTIVE", ws_ok=True, token_ok=True,
            sender=flaky, now=first_call,
        )
        assert result1["new"] is True
        assert result1["sent"] is False

        heartbeat_row = conn.execute(
            "SELECT COUNT(*) AS n FROM live_heartbeats WHERE trade_date = ? AND slot = '09:20'",
            (AS_OF,),
        ).fetchone()
        assert heartbeat_row["n"] == 1  # the durable row exists...

        later_call = "2026-07-19T09:25:00"
        result2 = heartbeat.send_heartbeat(
            conn, AS_OF, armed_count=1, market_mode="SELECTIVE", ws_ok=True, token_ok=True,
            sender=flaky, now=later_call,
        )
        assert result2["new"] is False  # ...so this call is NOT "new"...
        assert result2["sent"] is True  # ...but delivery still retried and succeeded.
        assert len(attempts) == 2
    finally:
        conn.close()


def test_two_heartbeat_slots_get_independent_outbox_rows(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        _patch_dry_run(monkeypatch, dry_run=True)
        heartbeat.send_heartbeat(conn, AS_OF, slot="09:20", armed_count=1, market_mode="SELECTIVE",
                                  ws_ok=True, token_ok=True)
        heartbeat.send_heartbeat(conn, AS_OF, slot="13:00", armed_count=1, market_mode="SELECTIVE",
                                  ws_ok=True, token_ok=True)
        count = conn.execute("SELECT COUNT(*) AS n FROM telegram_outbox").fetchone()["n"]
        assert count == 2
    finally:
        conn.close()
