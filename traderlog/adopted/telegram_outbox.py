"""Transactional Telegram outbox -- sole writer of ``telegram_outbox`` (W7).

Adopted (copied, never imported) from ``manas_os/alerts/outbox.py`` and
``manas_os/alerts/telegram_engine.py`` on 2026-08-25 for TraderLog W7. See
CANONICAL.md -- but the CANONICAL §6 row this file replaces read
``alerts/outbox.py``; in TraderLog the table's sole writer is this module,
``traderlog/adopted/telegram_outbox.py``. Once copied this file is TraderLog's
own; drift from the manas_os original is expected and fine (CANONICAL.md §5).

The pattern this adopts (``manas_os/alerts/outbox.py`` docstring, quoting the
RELIABILITY_AUDIT defect it fixes): delivery must never be ordered such that a
transient network failure becomes a PERMANENT missed notification (durable
business state committed before the send, nothing retries it) or such that a
crash after a successful send but before the local commit DUPLICATES on the
next run's retry.

How that works here, minimal honest v1:

* ``enqueue()`` writes one durable, idempotent row (``dedupe_key`` UNIQUE)
  and NEVER sends and NEVER commits -- the caller enqueues inside the same
  database transaction as the business write it accompanies, and commits
  business state + outbox row together, atomically.
* ``send_pending()`` is the one place that ever calls the Telegram sender. It
  runs strictly after that commit, so a crash before commit means the outbox
  row (and business row) never existed -- nothing to duplicate. A crash
  during/after the network call but before the local outcome commit leaves
  the row holding the pre-send marker; the NEXT ``send_pending()`` call
  recognizes the orphaned marker and flips the row to ``delivery_ambiguous``
  -- surfaced, never silently resent (same state ``checks/runner.py``
  ``check_telegram`` reads).
* ``dry_run`` and live share the exact same outbox state machine: in dry_run
  the sender short-circuits to a paper marker and reports success, so a
  dry_run row still walks pending -> sent exactly like a live one.

Drift from manas_os, all because TraderLog's own ``telegram_outbox`` table
(db/schema.sql, W7) has a different column set:

* TraderLog's table has ONE text column ``body`` where manas_os has separate
  ``kind``/``payload_json`` columns. ``body`` stores a JSON envelope
  ``{"kind", "ref_id", "payload"}`` so kind + payload survive to send time
  and the message is rendered from the payload, not stored pre-rendered.
* No ``next_retry_at`` / no ``provider_message_id`` columns: v1 does not
  retry/backoff -- a failing row is marked ``failed`` with the error text and
  stays there (the error IS the surfaced state). Documented, not hidden;
  retry/backoff needs a schema change, out of scope for W7 v1.
* ``created_at`` is written as ``YYYY-MM-DD HH:MM:SS`` UTC (no ``T``, no
  offset) deliberately: ``checks/runner.py`` ``check_telegram`` compares it
  with SQLite's ``datetime('now', '-1 hour')`` output, which has that exact
  format. The column's only consumer is that check, so this keeps its
  stuck-in-``delivery_ambiguous`` detection functional when dry_run is off.

Secrets: the bot token is NEVER logged, NEVER stored in ``body``/payload/any
table column, and never printed. It is read from the environment via
``traderlog.config.env("TELEGRAM_BOT_TOKEN")`` only inside the live sender,
immediately before the request is built (``traderlog/config.py`` loads the
repo-root .env). ``chat_id`` comes from config (``telegram.chat_id``).
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Callable
from urllib import parse, request

from traderlog import config

TELEGRAM_API = "https://api.telegram.org"
DEFAULT_SEND_TIMEOUT_S = 10

# Producer floor for trade_event notifications (see enqueue_trade_event).
DEFAULT_TRADE_EVENT_CONFIDENCE_FLOOR = 0.8

# Sentinel written into last_error immediately before the send and replaced
# with the real outcome right after. A row found holding this at the START of
# a send_pending() call was left mid-flight by a process that never recorded
# an outcome -- i.e. it crashed between "provider may have accepted this" and
# "we wrote that down".
_IN_FLIGHT_SENTINEL = "__IN_FLIGHT__"

# Reconciler statuses -> notification event (CONTRACTS.md §3: status is one of
# open | added | partial | closed | scratched | unclear). A status with an
# entry event (still open-like) notifies "entry"; a status whose thread ended
# exited notifies "exit". "Status entry/exit events only" per the W7 brief.
_ENTRY_STATUSES = frozenset({"open", "added", "partial", "unclear"})
_EXIT_STATUSES = frozenset({"closed", "scratched"})


def _now_sqlite() -> str:
    """UTC timestamp in SQLite datetime('now') format (space, no offset).

    See the module header: checks/runner.py check_telegram compares
    telegram_outbox.created_at against datetime('now', '-1 hour'), so this
    format is load-bearing for that check.
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Create the table if it does not exist; no-op after db/__init__.py ran.

    Mirrors db/schema.sql exactly (same columns/index) so a bare connection
    still works and an init_db() database is untouched.
    """
    conn.execute(
        "CREATE TABLE IF NOT EXISTS telegram_outbox ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "dedupe_key TEXT NOT NULL UNIQUE, "
        "body TEXT NOT NULL, "
        "state TEXT NOT NULL DEFAULT 'pending', "
        "attempts INTEGER NOT NULL DEFAULT 0, "
        "last_error TEXT, "
        "created_at TEXT NOT NULL, "
        "sent_at TEXT)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_outbox_state ON telegram_outbox(state)")


def _envelope_json(kind: str, payload: dict[str, Any], ref_id: str | None) -> str:
    return json.dumps(
        {"kind": kind, "ref_id": ref_id, "payload": payload},
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )


def _payload_dedupe_suffix(kind: str, payload: dict[str, Any]) -> str:
    """Stable key for enqueues without an explicit ref_id: same kind+payload
    twice in a row is the same intended notification, so it must dedupe."""
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(f"{kind}:{canonical}".encode("utf-8")).hexdigest()


def dedupe_key_for(kind: str, payload: dict[str, Any], ref_id: str | None = None) -> str:
    """The natural key of an outbox row. With a ref_id the key is human
    readable (``<kind>:<ref_id>``) and stable across payload edits; without
    one it is a hash of kind + canonical payload."""
    if ref_id is not None and str(ref_id):
        return f"{kind}:{ref_id}"
    return f"{kind}:{_payload_dedupe_suffix(kind, payload)}"


def enqueue(
    conn: sqlite3.Connection,
    kind: str,
    payload: dict[str, Any],
    ref_id: str | None = None,
) -> dict[str, Any]:
    """Idempotent create of one outbox row. Does NOT commit and never sends --
    the caller enqueues inside the same transaction as the business write the
    notification accompanies (that atomicity is the entire fix; a second call
    with the same dedupe key is a safe no-op)."""
    ensure_schema(conn)
    if not isinstance(kind, str) or not kind:
        raise ValueError("kind must be a non-empty string")
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    key = dedupe_key_for(kind, payload, ref_id)
    cur = conn.execute(
        "INSERT OR IGNORE INTO telegram_outbox (dedupe_key, body, state, created_at) "
        "VALUES (?, ?, 'pending', ?)",
        (key, _envelope_json(kind, payload, ref_id), _now_sqlite()),
    )
    return {"created": bool(cur.rowcount), "dedupe_key": key}


# ---------------------------------------------------------------------------
# sending
# ---------------------------------------------------------------------------


def render_message(kind: str, payload: dict[str, Any]) -> str:
    """Render the Telegram message text from an outbox payload.

    Unknown kinds fall back to the stable payload JSON so no payload is ever
    lost to a rendering gap; the fallback is deliberately not a production
    message format, it is a never-silently-drop guarantee.
    """
    if kind == "trade_event":
        symbol = str(payload.get("symbol") or "?")
        event = str(payload.get("event") or "event").upper()
        handle = str(payload.get("handle") or "?")
        lines = [f"[TraderLog] {symbol} {event} -- @{handle}"]
        url = payload.get("post_url")
        if url:
            lines.append(str(url))
        return "\n".join(lines)
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)


def _send_telegram_message(message: str) -> dict[str, Any]:
    """Live Bot API send (plain urllib POST; the adopted sender pattern from
    manas_os/alerts/telegram_engine.py::_telegram_sender).

    Token is read HERE, from the environment only, and never logged or stored.
    chat_id comes from config. Telegram reports API errors (bad token, wrong
    chat) as HTTP 200 with {"ok": false}, so the body is parsed and its
    description becomes the recorded error text -- that is what makes the
    failure honest instead of a silent 200.
    """
    token = str(config.env("TELEGRAM_BOT_TOKEN") or "").strip()
    chat_id = str(config.get("telegram.chat_id", "") or "").strip()
    if not token or not chat_id:
        raise ValueError(
            "TELEGRAM_BOT_TOKEN env and telegram.chat_id are required when dry_run=false"
        )
    body = parse.urlencode({"chat_id": chat_id, "text": message}).encode("utf-8")
    req = request.Request(
        f"{TELEGRAM_API}/bot{token}/sendMessage",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with request.urlopen(req, timeout=DEFAULT_SEND_TIMEOUT_S) as resp:  # noqa: S310 - opt-in configured endpoint.
        if resp.status >= 400:
            raise RuntimeError(f"telegram send failed: HTTP {resp.status}")
        raw = resp.read().decode("utf-8", errors="replace")
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        raise RuntimeError("telegram send failed: non-JSON response") from None
    if not result.get("ok"):
        detail = result.get("description") or result.get("error_code") or "unknown API error"
        raise RuntimeError(f"telegram send failed: {detail}")
    return {"message_id": (result.get("result") or {}).get("message_id")}


def _recover_in_flight(conn: sqlite3.Connection) -> list[str]:
    """Sweep rows a previous, now-dead process left mid-send (pre-send marker
    committed, outcome never recorded) into delivery_ambiguous. Runs first on
    every send_pending() call so an interrupted prior attempt is surfaced --
    and excluded from the due-rows query below -- before anything new is sent."""
    rows = conn.execute(
        "SELECT dedupe_key FROM telegram_outbox WHERE state = 'pending' AND last_error = ?",
        (_IN_FLIGHT_SENTINEL,),
    ).fetchall()
    keys = [r["dedupe_key"] for r in rows]
    if keys:
        conn.execute(
            "UPDATE telegram_outbox SET state = 'delivery_ambiguous', "
            "last_error = 'interrupted after send attempt, before local acknowledgement' "
            "WHERE state = 'pending' AND last_error = ?",
            (_IN_FLIGHT_SENTINEL,),
        )
        conn.commit()
    return keys


def _due_rows(conn: sqlite3.Connection):
    return conn.execute(
        "SELECT * FROM telegram_outbox WHERE state = 'pending' "
        "AND (last_error IS NULL OR last_error != ?) ORDER BY id",
        (_IN_FLIGHT_SENTINEL,),
    ).fetchall()


def send_pending(
    conn: sqlite3.Connection,
    *,
    sender: Callable[[str], Any] | None = None,
    dry_run: bool | None = None,
    now: str | None = None,
) -> dict[str, Any]:
    """Deliver every pending outbox row through the Telegram sender.

    The one place that ever calls a Telegram sender. Recovers rows orphaned by
    a crashed prior process first, then attempts each pending row once, marks
    sent/failed with the error text, and NEVER raises on a send failure -- a
    bad send must not crash its caller. dry_run (default: the config value
    ``telegram.dry_run``) marks the row sent with last_error 'dry_run' and
    makes no network call at all.
    """
    ensure_schema(conn)
    now = now or _now_sqlite()
    is_dry_run = bool(config.get("telegram.dry_run", True)) if dry_run is None else bool(dry_run)
    ambiguous = _recover_in_flight(conn)
    delivered: list[str] = []
    failed: list[str] = []
    live_sender = sender or _send_telegram_message

    for row in _due_rows(conn):
        key = row["dedupe_key"]
        attempts = int(row["attempts"] or 0) + 1
        # Durable pre-send marker, committed BEFORE the send so a crash
        # during/after the network call is recoverable (see _recover_in_flight)
        # instead of silently re-sent. Written in dry_run too so paper and live
        # exercise the identical state machine.
        conn.execute(
            "UPDATE telegram_outbox SET attempts = ?, last_error = ? WHERE dedupe_key = ?",
            (attempts, _IN_FLIGHT_SENTINEL, key),
        )
        conn.commit()

        try:
            envelope = json.loads(row["body"])
            message = render_message(envelope.get("kind"), envelope.get("payload") or {})
            if not is_dry_run:
                live_sender(message)
        except Exception as exc:  # noqa: BLE001 - a send failure must never crash the caller
            conn.execute(
                "UPDATE telegram_outbox SET state = 'failed', last_error = ? WHERE dedupe_key = ?",
                (str(exc), key),
            )
            conn.commit()
            failed.append(key)
            continue

        if is_dry_run:
            # Paper marker: sent, last_error 'dry_run', zero network calls.
            conn.execute(
                "UPDATE telegram_outbox SET state = 'sent', sent_at = ?, last_error = 'dry_run' "
                "WHERE dedupe_key = ?",
                (now, key),
            )
        else:
            conn.execute(
                "UPDATE telegram_outbox SET state = 'sent', sent_at = ?, last_error = NULL "
                "WHERE dedupe_key = ?",
                (now, key),
            )
        conn.commit()
        delivered.append(key)

    return {"delivered": delivered, "failed": failed, "ambiguous": ambiguous}


# ---------------------------------------------------------------------------
# event producer (optional post-write hook, W7)
# ---------------------------------------------------------------------------


def event_for_status(status: str | None) -> str | None:
    """Map a reconciler position status (CONTRACTS.md §3) to the notification
    event: open-like statuses -> 'entry', exited statuses -> 'exit', anything
    else -> None (never notified). 'Status entry/exit events only' per W7."""
    if status in _ENTRY_STATUSES:
        return "entry"
    if status in _EXIT_STATUSES:
        return "exit"
    return None


def enqueue_trade_event(
    conn: sqlite3.Connection,
    *,
    handle: str,
    symbol: str,
    event: str,
    post_url: str | None = None,
    ref_id: str | None = None,
    confidence: float | None = None,
    confidence_floor: float = DEFAULT_TRADE_EVENT_CONFIDENCE_FLOOR,
) -> dict[str, Any]:
    """Optional post-write hook: enqueue one high-confidence trade_event
    notification. Same transaction discipline as enqueue() -- call it inside
    the same ``with conn:`` block as the positions/position_events write
    (llm/reconcile.py::_write_position with transactional=False, or the
    caller's own transaction) and commit once. The ''NEW position'' gate is
    the caller's: run this only when the write created a position row that did
    not exist before, and pass the new row's status through event_for_status().

    payload (per the W7 brief) = handle / symbol / event / kind / post_url.
    Belt-and-braces guard: a confidence below the floor is skipped rather than
    pushing a low-quality notification; position.confidence is 0..1
    (CONTRACTS.md §3). No network, no commit."""
    if not isinstance(handle, str) or not handle:
        raise ValueError("handle must be a non-empty string")
    if not isinstance(symbol, str) or not symbol:
        raise ValueError("symbol must be a non-empty string")
    if event not in {"entry", "exit"}:
        raise ValueError("event must be 'entry' or 'exit' (map a position status with event_for_status)")
    if confidence is not None and not (0 <= float(confidence) <= 1):
        raise ValueError("confidence must be in [0, 1] or None")
    if confidence is not None and float(confidence) < float(confidence_floor):
        return {"created": False, "dedupe_key": None, "skipped": "below_confidence_floor"}
    kind = "trade_event"
    payload = {
        "handle": handle,
        "symbol": symbol,
        "event": event,
        "kind": kind,
        "post_url": post_url,
    }
    return enqueue(conn, kind, payload, ref_id=ref_id)