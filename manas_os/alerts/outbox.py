"""Transactional Telegram outbox (RELIABILITY_AUDIT_2026-07-19 defect #8:
"Telegram is not an end-to-end service").

The bug this fixes is a delivery-ordering bug, not a send-failure bug: three
call paths (heartbeat, the live FSM's ALERTED transition, the nightly
digest/coach send) each either committed durable state BEFORE attempting the
network send (a transient failure then becomes a PERMANENT missed alert,
because the durable dedupe/ALERTED row already exists and nothing retries
it) or sent BEFORE the final commit (a crash after network success but
before commit then DUPLICATES on the next run's retry).

The fix is the standard transactional-outbox pattern:

1. ``enqueue()`` writes one durable, idempotent row (``UNIQUE(alert_key)``)
   INSIDE the same database transaction as the business write it accompanies
   (the ALERTED transition, the heartbeat row, the armed-list rebuild, the
   coach signal persistence). It never sends and never commits -- the caller
   commits business state and the outbox row together, atomically.
2. ``deliver_pending()`` is the one place that ever calls the network sender.
   It runs strictly AFTER that commit, so a crash before commit means the
   outbox row (and the business row) never existed -- nothing to duplicate.
   A crash during/after the network call but before the local commit that
   would normally record the outcome leaves the row's pre-send marker
   in place; the NEXT call to ``deliver_pending`` (i.e. the next process,
   after a restart) recognizes that orphaned marker and flips the row to
   ``delivery_ambiguous`` -- surfaced, never silently resent.

Delivery semantics are declared, per the audit's own checklist: **at-least-
once with a stable alert_key**, never exactly-once. ``delivery_ambiguous``
is the explicit "we do not know if this went out" state the audit demands
instead of a silent guess in either direction.

dry_run behavior: dry_run and live share the exact same outbox state
machine. In dry_run, ``dry_run_or_live_sender`` short-circuits to the paper
log and reports success, so a dry_run row still walks pending -> sent like a
live one would -- that symmetry is the point (a paper-mode soak run and a
live run exercise identical code paths).
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

# Sentinel written into last_error immediately before the network call and
# cleared immediately after (success or clean failure). A row found holding
# this sentinel at the START of a deliver_pending() call was left mid-flight
# by a process that never got to record an outcome -- i.e. it crashed
# between "provider may have accepted this" and "we wrote that down".
_IN_FLIGHT_SENTINEL = "__IN_FLIGHT__"

DEFAULT_MAX_ATTEMPTS = 5
DEFAULT_BACKOFF_BASE_S = 30  # doubles per attempt, capped at 1 hour
DEFAULT_BACKOFF_CAP_S = 3600


def ensure_schema(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS telegram_outbox ("
        "outbox_id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "alert_key TEXT NOT NULL UNIQUE, "
        "kind TEXT NOT NULL, "
        "payload_json TEXT NOT NULL, "
        "state TEXT NOT NULL DEFAULT 'pending' "
        "CHECK(state IN ('pending','sent','failed','delivery_ambiguous')), "
        "attempts INTEGER NOT NULL DEFAULT 0, "
        "next_retry_at TEXT, "
        "provider_message_id TEXT, "
        "sent_at TEXT, "
        "last_error TEXT, "
        "created_at TEXT DEFAULT (datetime('now')))"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_telegram_outbox_state "
        "ON telegram_outbox(state, next_retry_at)"
    )


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")


def enqueue(conn, alert_key: str, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Idempotent create of one outbox row. Does NOT commit -- the caller is
    expected to enqueue inside the same transaction as the business write
    the alert accompanies (that atomicity is the entire fix). Calling this
    twice with the same alert_key is a safe no-op on the second call."""
    ensure_schema(conn)
    cur = conn.execute(
        "INSERT OR IGNORE INTO telegram_outbox (alert_key, kind, payload_json, state) "
        "VALUES (?, ?, ?, 'pending')",
        (alert_key, kind, json.dumps(payload, default=str, sort_keys=True)),
    )
    return {"created": bool(cur.rowcount), "alert_key": alert_key}


def dry_run_or_live_sender(
    *,
    dry_run: bool,
    live_sender: Callable[[str], Any],
    paper_fn: Callable[[dict[str, Any]], Any] | None = None,
) -> Callable[[dict[str, Any]], Any]:
    """Build a deliver_pending()-shaped sender_fn (payload dict -> result)
    that shares one state machine between paper and live: dry_run never
    calls the real network sender and never raises, so the row always walks
    pending -> sent exactly like a live send would ("state machine identical
    in paper and live -- that is the point")."""

    def _send(payload: dict[str, Any]) -> Any:
        if dry_run:
            if paper_fn is not None:
                paper_fn(payload)
            return {"paper": True}
        return live_sender(str(payload.get("message") or ""))

    return _send


def _backoff_seconds(attempts: int) -> int:
    return min(DEFAULT_BACKOFF_BASE_S * (2 ** max(0, attempts - 1)), DEFAULT_BACKOFF_CAP_S)


def _recover_in_flight(conn) -> list[str]:
    """Sweep rows a previous, now-dead process left mid-send (pre-send
    marker committed, outcome never recorded) into delivery_ambiguous.
    Runs first on every deliver_pending() call so an interrupted prior
    attempt is surfaced -- and excluded from the due-rows query below --
    before any new send is attempted this call."""
    rows = conn.execute(
        "SELECT alert_key FROM telegram_outbox WHERE state = 'pending' AND last_error = ?",
        (_IN_FLIGHT_SENTINEL,),
    ).fetchall()
    keys = [r["alert_key"] for r in rows]
    if keys:
        conn.execute(
            "UPDATE telegram_outbox SET state = 'delivery_ambiguous', "
            "last_error = 'interrupted after send attempt, before local acknowledgement' "
            "WHERE state = 'pending' AND last_error = ?",
            (_IN_FLIGHT_SENTINEL,),
        )
        conn.commit()
    return keys


def _due_rows(conn, now: str):
    return conn.execute(
        "SELECT * FROM telegram_outbox WHERE state = 'pending' "
        "AND (last_error IS NULL OR last_error != ?) "
        "AND (next_retry_at IS NULL OR next_retry_at <= ?) "
        "ORDER BY outbox_id",
        (_IN_FLIGHT_SENTINEL, now),
    ).fetchall()


def deliver_pending(
    conn,
    sender_fn: Callable[[dict[str, Any]], Any],
    now: str | None = None,
    *,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> dict[str, Any]:
    """The one place that ever calls a Telegram sender. Recovers any row
    orphaned by a crashed prior process first, then attempts every due
    'pending' row once, bounded retry/backoff on transient failure. Never
    raises on a send failure -- a bad send must never crash the caller
    (heartbeat/FSM/digest/coach all call this synchronously inline)."""
    ensure_schema(conn)
    now = now or _now_iso()
    ambiguous = _recover_in_flight(conn)
    delivered: list[str] = []
    retried: list[str] = []
    failed: list[str] = []

    for row in _due_rows(conn, now):
        alert_key = row["alert_key"]
        attempts = int(row["attempts"] or 0) + 1
        # Durable pre-send marker: committed BEFORE the network call so a
        # crash during/after send is recoverable (see _recover_in_flight)
        # instead of silently re-sent.
        conn.execute(
            "UPDATE telegram_outbox SET attempts = ?, last_error = ? WHERE alert_key = ?",
            (attempts, _IN_FLIGHT_SENTINEL, alert_key),
        )
        conn.commit()

        payload = json.loads(row["payload_json"])
        try:
            result = sender_fn(payload)
        except Exception as exc:  # noqa: BLE001 - a transient send failure must never crash the caller
            if attempts >= max_attempts:
                conn.execute(
                    "UPDATE telegram_outbox SET state = 'failed', last_error = ?, "
                    "next_retry_at = NULL WHERE alert_key = ?",
                    (str(exc), alert_key),
                )
                failed.append(alert_key)
            else:
                next_retry = (
                    datetime.fromisoformat(now) + timedelta(seconds=_backoff_seconds(attempts))
                ).isoformat(timespec="seconds")
                conn.execute(
                    "UPDATE telegram_outbox SET state = 'pending', last_error = ?, "
                    "next_retry_at = ? WHERE alert_key = ?",
                    (str(exc), next_retry, alert_key),
                )
                retried.append(alert_key)
            conn.commit()
            continue

        provider_message_id = None
        if isinstance(result, dict):
            provider_message_id = result.get("message_id") or result.get("provider_message_id")
        elif result is not None and not isinstance(result, bool):
            provider_message_id = str(result)
        conn.execute(
            "UPDATE telegram_outbox SET state = 'sent', provider_message_id = ?, "
            "sent_at = ?, last_error = NULL, next_retry_at = NULL WHERE alert_key = ?",
            (provider_message_id, now, alert_key),
        )
        conn.commit()
        delivered.append(alert_key)

    return {"delivered": delivered, "retried": retried, "failed": failed, "ambiguous": ambiguous}


def get(conn, alert_key: str) -> dict[str, Any] | None:
    ensure_schema(conn)
    row = conn.execute(
        "SELECT * FROM telegram_outbox WHERE alert_key = ?", (alert_key,)
    ).fetchone()
    return dict(row) if row else None
