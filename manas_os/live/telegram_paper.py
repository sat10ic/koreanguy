"""Paper-mode Telegram push gate for the intraday live loop.

Every push (entry alert or exit alert) is rendered into the real payload
shape and *always* logged to live_pushes_log. A live Bot API send only
happens when BOTH `agents.telegram_live` is true in config AND a written
graduation-criterion document exists on disk (manas_os/design/
LIVE_LOOP_GRADUATION.md) -- neither is true in this repo today, so this
module is paper-only by construction. This is the "paper gate": logs instead
of sending whenever the gate is closed, per the task's binding instruction.

Dedup reuses alerts.replies.record_push (already tested, already ships
/halt + 1-push-per-symbol-per-day semantics) rather than re-deriving it --
entries are blocked while halted, exits never are.

RELIABILITY_AUDIT_2026-07-19 #8: `push_entry_alert` used to send-then-log
inline, and the caller (alerts.live_fsm) committed the ALERTED transition
BEFORE ever calling this function -- a transient send failure was therefore
converted into a permanently missed alert (the durable ALERTED/dedupe state
already existed with nothing left to retry it). Entry delivery now goes
through the transactional outbox (manas_os.alerts.outbox): live_fsm enqueues
the outbox row in the SAME transaction as the ALERTED write (via
`_transition`'s pre_commit hook) and passes the resulting `alert_key` in
here; this function's job becomes purely "deliver whatever is due and log
the outcome". Exit alerts (`push_exit_alert`) are unchanged -- exit push
ordering was not one of the three paths named in the audit's smallest-fix
list, and there is currently no production caller of it (only the replay
harness / tests), so it is left on the direct-send path.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from manas_os import config
from manas_os.alerts import outbox
from manas_os.alerts import replies as telegram_replies
from manas_os.alerts import telegram_engine

GRADUATION_DOC = Path(__file__).resolve().parents[1] / "design" / "LIVE_LOOP_GRADUATION.md"


def ensure_schema(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS live_pushes_log ("
        "push_id INTEGER PRIMARY KEY AUTOINCREMENT, trade_date TEXT NOT NULL, symbol TEXT NOT NULL, "
        "kind TEXT NOT NULL, payload_json TEXT NOT NULL, message TEXT NOT NULL, "
        "paper INTEGER NOT NULL DEFAULT 1, sent INTEGER NOT NULL DEFAULT 0, "
        "created_at TEXT DEFAULT (datetime('now')))"
    )
    outbox.ensure_schema(conn)


def entry_alert_key(trade_date: str, symbol: str, setup_id: str) -> str:
    """Single source of truth for the entry-alert outbox key, shared by
    alerts.live_fsm (enqueues inside the ALERTED transaction) and this
    module (delivers it)."""
    return f"live_entry:{trade_date}:{symbol}:{setup_id}"


def live_send_authorized() -> bool:
    """Both the config flag AND a written graduation doc must be true. The
    doc does not exist yet in this repo, so this is currently always False --
    that is the point: paper-first is locked until a human writes the
    criterion and flips the flag, not until code merely allows it."""
    return bool(config.get("agents.telegram_live", False)) and GRADUATION_DOC.exists()


def render_entry_payload(trade_date: str, symbol: str, fsm_row: dict, tick: dict) -> dict[str, Any]:
    return {
        "trade_date": trade_date,
        "symbol": symbol,
        "state": "ALERTED",
        "trigger": fsm_row.get("trigger"),
        "stop": fsm_row.get("stop"),
        "qty": fsm_row.get("qty"),
        "zone_lo": fsm_row.get("zone_lo"),
        "zone_hi": fsm_row.get("zone_hi"),
        "ltp": tick.get("ltp"),
        "rvol_projected": tick.get("rvol_projected"),
        "gap_fill_pct": tick.get("gap_fill_pct"),
        "ttl_minutes": 25,
    }


def render_entry_message(payload: dict[str, Any]) -> str:
    return (
        f"ARMED->ALERTED {payload['symbol']} | trigger {payload['trigger']} | "
        f"stop {payload['stop']} | qty {payload['qty']} | "
        f"zone {payload['zone_lo']}-{payload['zone_hi']} | ltp {payload['ltp']} | "
        f"RVOL {payload['rvol_projected']} | TTL {payload['ttl_minutes']}m"
    )


def _write_log(conn, trade_date, symbol, kind, payload, message, *, paper: bool, sent: bool) -> None:
    conn.execute(
        "INSERT INTO live_pushes_log (trade_date, symbol, kind, payload_json, message, paper, sent) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (trade_date, symbol, kind, json.dumps(payload, default=str), message, int(paper), int(sent)),
    )
    conn.commit()


def _maybe_send(message: str, sender) -> bool:
    if not live_send_authorized():
        return False
    try:
        (sender or telegram_engine.get_sender())(message)
        return True
    except Exception:  # noqa: BLE001 - a push failure must never crash the loop
        return False


def _deliver_and_log(conn, alert_key: str, trade_date: str, symbol: str, kind: str,
                      payload: dict[str, Any], message: str, *, sender=None) -> dict[str, Any]:
    """Attempt delivery of an already-enqueued outbox row and log exactly
    once, on the call that resolves it to a terminal outcome (sent/failed/
    ambiguous). A row still 'pending' after this call (transient failure,
    backoff not yet elapsed) is NOT logged here -- it will be logged by
    whichever future deliver_pending() call finally resolves it, so
    live_pushes_log never gets more than one row per alert_key."""
    dry_run = not live_send_authorized()
    live_sender = sender or telegram_engine.get_sender()
    send_fn = outbox.dry_run_or_live_sender(dry_run=dry_run, live_sender=live_sender)
    result = outbox.deliver_pending(conn, send_fn)

    if alert_key in result["delivered"]:
        sent, paper = (not dry_run), dry_run
        _write_log(conn, trade_date, symbol, kind, payload, message, paper=paper, sent=sent)
        return {"ok": True, "paper": paper, "sent": sent, "message": message, "payload": payload, "state": "sent"}
    if alert_key in result["failed"]:
        _write_log(conn, trade_date, symbol, kind, payload, message, paper=True, sent=False)
        return {"ok": True, "paper": True, "sent": False, "message": message, "payload": payload, "state": "failed"}
    if alert_key in result["ambiguous"]:
        _write_log(conn, trade_date, symbol, kind, payload, message, paper=True, sent=False)
        return {"ok": True, "paper": True, "sent": False, "message": message, "payload": payload,
                "state": "delivery_ambiguous", "alert_key": alert_key}
    # Still pending (retried this call, backoff not yet elapsed) -- not a
    # terminal outcome, so not logged yet.
    return {"ok": True, "paper": True, "sent": False, "message": message, "payload": payload, "state": "pending"}


def push_entry_alert(conn, trade_date: str, symbol: str, fsm_row: dict, tick: dict, *,
                      sender=None, alert_key: str | None = None) -> dict[str, Any]:
    """Deliver one entry alert through the transactional outbox.

    Normal production call shape (from alerts.live_fsm): the caller has
    ALREADY written the dedupe row (alerts.replies.record_push) and the
    outbox row (alerts.outbox.enqueue) inside the SAME transaction as the
    FSM's ALERTED state write and passes the resulting `alert_key` here --
    this function then only attempts delivery and logs the outcome
    (RELIABILITY_AUDIT_2026-07-19 #8: delivery must never be what a crash
    between ALERTED-commit and send turns into a permanently missed alert).

    `alert_key=None` (direct/standalone callers, e.g. tests) falls back to
    doing the dedupe + enqueue + commit itself, atomically, before
    delivering -- so this function remains safe to call on its own.
    """
    ensure_schema(conn)
    payload = render_entry_payload(trade_date, symbol, fsm_row, tick)
    message = render_entry_message(payload)
    payload["message"] = message
    setup_id = fsm_row.get("setup_id") or "setup"
    key = alert_key or entry_alert_key(trade_date, symbol, setup_id)

    if alert_key is None:
        dedup = telegram_replies.record_push(conn, trade_date, symbol, kind="entry", commit=False)
        if not dedup["ok"]:
            return {"ok": False, "reason": dedup["reason"], "paper": True}
        outbox.enqueue(conn, key, "live_entry", payload)
        conn.commit()

    return _deliver_and_log(conn, key, trade_date, symbol, "entry", payload, message, sender=sender)


def push_exit_alert(conn, trade_date: str, symbol: str, message: str,
                     payload: dict[str, Any] | None = None, *, sender=None) -> dict[str, Any]:
    """Exit alerts are never gated by /halt -- record_push only checks the
    halt flag for kind='entry' (alerts/replies.py); stops stay sacred."""
    ensure_schema(conn)
    dedup = telegram_replies.record_push(conn, trade_date, symbol, kind="exit")
    if not dedup["ok"]:
        return {"ok": False, "reason": dedup["reason"], "paper": True}
    sent = _maybe_send(message, sender)
    _write_log(conn, trade_date, symbol, "exit", payload or {}, message, paper=not sent, sent=sent)
    return {"ok": True, "paper": not sent, "sent": sent, "message": message}
