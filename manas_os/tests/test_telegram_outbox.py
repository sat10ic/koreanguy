"""Tests for manas_os.alerts.outbox -- the transactional Telegram outbox
fixing RELIABILITY_AUDIT_2026-07-19 defect #8 ("Telegram is not an
end-to-end service"): three call paths either committed durable state
before attempting the network send (transient failure -> permanently
missed alert) or sent before the final commit (crash after send ->
duplicate on retry).

These tests exercise the outbox primitives directly (enqueue idempotency,
bounded retry/backoff, the crash-after-accept -> delivery_ambiguous
recovery path, and the dry_run/live sender adapter). The per-caller
ordering fixes (heartbeat, live_fsm/replies, telegram_engine digest, coach)
are covered in their own test files.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta

import pytest

from manas_os import db
from manas_os.alerts import outbox


def test_enqueue_is_idempotent_on_alert_key(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        r1 = outbox.enqueue(conn, "k1", "test", {"message": "first"})
        conn.commit()
        r2 = outbox.enqueue(conn, "k1", "test", {"message": "second"})  # same key, different payload
        conn.commit()

        assert r1["created"] is True
        assert r2["created"] is False

        count = conn.execute(
            "SELECT COUNT(*) AS n FROM telegram_outbox WHERE alert_key = 'k1'"
        ).fetchone()["n"]
        assert count == 1

        row = outbox.get(conn, "k1")
        assert row["state"] == "pending"
        assert json.loads(row["payload_json"])["message"] == "first"  # first write wins
    finally:
        conn.close()


def test_enqueue_does_not_commit_caller_owns_the_transaction(tmp_path):
    """The entire fix depends on enqueue() NOT committing -- callers fold it
    into their own business transaction. A rollback after enqueue() must
    leave zero durable trace."""
    conn = db.init_db(tmp_path / "manas.db")
    try:
        outbox.enqueue(conn, "k-rollback", "test", {"message": "should vanish"})
        conn.rollback()
        row = outbox.get(conn, "k-rollback")
        assert row is None
    finally:
        conn.close()


def test_transient_failure_stays_pending_then_retries_then_sent(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        outbox.enqueue(conn, "k2", "test", {"message": "hi"})
        conn.commit()

        attempts: list[int] = []

        def flaky_sender(payload):
            attempts.append(1)
            if len(attempts) == 1:
                raise RuntimeError("transient network error")
            return {"message_id": "provider-msg-1"}

        base_now = "2026-07-19T09:00:00"
        first = outbox.deliver_pending(conn, flaky_sender, now=base_now)
        assert first["retried"] == ["k2"]
        assert first["delivered"] == []
        row = outbox.get(conn, "k2")
        assert row["state"] == "pending"
        assert row["attempts"] == 1
        assert "transient network error" in row["last_error"]
        assert row["next_retry_at"] > base_now

        # Not yet due (backoff hasn't elapsed) -- must not call the sender again.
        still_early = outbox.deliver_pending(conn, flaky_sender, now=base_now)
        assert still_early["delivered"] == [] and still_early["retried"] == []
        assert len(attempts) == 1

        later = "2026-07-19T09:05:00"
        second = outbox.deliver_pending(conn, flaky_sender, now=later)
        assert second["delivered"] == ["k2"]
        row2 = outbox.get(conn, "k2")
        assert row2["state"] == "sent"
        assert row2["provider_message_id"] == "provider-msg-1"
        assert row2["sent_at"] == later
        assert row2["last_error"] is None
        assert len(attempts) == 2
    finally:
        conn.close()


def test_exhausted_retries_marks_failed_terminal_and_is_never_retried_again(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        outbox.enqueue(conn, "k3", "test", {"message": "hi"})
        conn.commit()

        def always_fail(_payload):
            raise RuntimeError("permanently down")

        start = datetime(2026, 7, 19, 9, 0, 0)
        for i in range(3):
            now = (start + timedelta(hours=i)).isoformat(timespec="seconds")
            outbox.deliver_pending(conn, always_fail, now=now, max_attempts=3)

        row = outbox.get(conn, "k3")
        assert row["state"] == "failed"
        assert row["attempts"] == 3

        calls: list[int] = []
        result = outbox.deliver_pending(
            conn, lambda p: calls.append(1),
            now=(start + timedelta(hours=10)).isoformat(timespec="seconds"),
        )
        assert calls == []
        assert result["delivered"] == [] and result["retried"] == [] and result["failed"] == []
    finally:
        conn.close()


def test_crash_after_send_attempt_marks_delivery_ambiguous_and_is_never_resent(tmp_path):
    """Simulates a process dying between "we told the provider to send" and
    "we recorded the outcome" -- e.g. the machine loses power right after
    Telegram accepts the message but before the local UPDATE/commit runs.
    A sender raising something deliver_pending's `except Exception` does NOT
    catch (a real crash escapes every handler) leaves the pre-send marker in
    place. The NEXT deliver_pending call (simulating the next process, same
    durable DB) must recognize that orphaned marker, flip the row to
    delivery_ambiguous, and -- critically -- must NOT call the sender again
    for it (never silently resend an alert whose delivery outcome is
    unknown)."""
    conn = db.init_db(tmp_path / "manas.db")
    try:
        outbox.enqueue(conn, "k4", "test", {"message": "hi"})
        conn.commit()

        def crash_mid_send(_payload):
            raise SystemExit("simulated process death mid-send")

        with pytest.raises(SystemExit):
            outbox.deliver_pending(conn, crash_mid_send)

        # The pre-send marker was committed before the crash; the row is
        # still nominally 'pending' but not retryable via the normal path.
        row = outbox.get(conn, "k4")
        assert row["state"] == "pending"
        assert row["attempts"] == 1

        calls: list[dict] = []

        def should_never_be_called(payload):
            calls.append(payload)
            return "ok"

        result = outbox.deliver_pending(conn, should_never_be_called)
        assert calls == []  # never resent
        assert result["ambiguous"] == ["k4"]
        row2 = outbox.get(conn, "k4")
        assert row2["state"] == "delivery_ambiguous"
        assert row2["last_error"]
    finally:
        conn.close()


def test_dry_run_or_live_sender_paper_path_never_calls_live_sender():
    calls: list[str] = []
    send_fn = outbox.dry_run_or_live_sender(dry_run=True, live_sender=lambda m: calls.append(m))
    result = send_fn({"message": "hello"})
    assert calls == []
    assert result == {"paper": True}


def test_dry_run_or_live_sender_paper_path_invokes_paper_fn():
    logged: list[dict] = []

    def paper_fn(payload):
        logged.append(payload)

    send_fn = outbox.dry_run_or_live_sender(dry_run=True, live_sender=lambda m: None, paper_fn=paper_fn)
    send_fn({"message": "hello", "extra": 1})
    assert logged == [{"message": "hello", "extra": 1}]


def test_dry_run_or_live_sender_live_path_calls_through():
    calls: list[str] = []
    send_fn = outbox.dry_run_or_live_sender(dry_run=False, live_sender=lambda m: calls.append(m))
    send_fn({"message": "hello live"})
    assert calls == ["hello live"]


def test_dry_run_and_live_share_identical_outbox_state_machine(tmp_path):
    """"state machine identical in paper and live -- that is the point": a
    dry_run delivery and a live delivery both walk pending -> sent through
    the exact same deliver_pending() code path. deliver_pending() drains the
    whole due batch with one sender_fn, so each row is enqueued and
    delivered in its own call to keep the two paths isolated."""
    conn = db.init_db(tmp_path / "manas.db")
    try:
        never_called = lambda m: (_ for _ in ()).throw(AssertionError("paper mode must not call the live sender"))  # noqa: E731
        paper_send = outbox.dry_run_or_live_sender(dry_run=True, live_sender=never_called)
        live_send = outbox.dry_run_or_live_sender(dry_run=False, live_sender=lambda m: {"message_id": "abc"})

        outbox.enqueue(conn, "k-paper", "test", {"message": "paper"})
        conn.commit()
        r_paper = outbox.deliver_pending(conn, paper_send)
        assert "k-paper" in r_paper["delivered"]

        outbox.enqueue(conn, "k-live", "test", {"message": "live"})
        conn.commit()
        r_live = outbox.deliver_pending(conn, live_send)
        assert "k-live" in r_live["delivered"]

        row_paper = outbox.get(conn, "k-paper")
        row_live = outbox.get(conn, "k-live")
        assert row_paper["state"] == row_live["state"] == "sent"
    finally:
        conn.close()
