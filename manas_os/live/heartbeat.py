"""09:20 IST heartbeat -- absence is the alert (LIVE_LOOP_FABLE §3.3).

One heartbeat row per (trade_date, slot); a second slot ("13:00") can be sent
the same way to catch a midday death. The standing instruction to the user
(documented, not enforced in code -- there is nothing code can do about a
message that never arrives): no 09:20 message means the loop is down, assume
no coverage today.

RELIABILITY_AUDIT_2026-07-19 #8: this used to write the unique
(trade_date, slot) row BEFORE attempting the send and swallow a send
failure, so a transient failure permanently blocked retry -- the row
already existed, so `is_new` was False on every later call for that slot
and the send was never attempted again. Fixed via the transactional outbox
(manas_os.alerts.outbox): the heartbeat row and the outbox row are written
in the SAME transaction (either both commit or neither does), and delivery
is attempted through `outbox.deliver_pending` on every call -- not gated on
`is_new` -- so a still-pending outbox row from an earlier failed attempt is
retried (respecting backoff) even though the live_heartbeats row already
exists.
"""
from __future__ import annotations

from typing import Any

from manas_os.alerts import outbox, telegram_engine

DEFAULT_SLOT = "09:20"


def ensure_schema(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS live_heartbeats ("
        "trade_date TEXT NOT NULL, slot TEXT NOT NULL, status TEXT NOT NULL, "
        "detail TEXT, created_at TEXT DEFAULT (datetime('now')), "
        "PRIMARY KEY(trade_date, slot))"
    )
    outbox.ensure_schema(conn)


def _alert_key(trade_date: str, slot: str) -> str:
    return f"heartbeat:{trade_date}:{slot}"


def send_heartbeat(conn, trade_date: str, *, slot: str = DEFAULT_SLOT, armed_count: int,
                    market_mode: str, ws_ok: bool, token_ok: bool, sender=None,
                    now: str | None = None) -> dict[str, Any]:
    ensure_schema(conn)
    status = "alive" if (ws_ok and token_ok) else "degraded"
    message = (
        f"Loop alive | token {'OK' if token_ok else 'FAIL'} | WS {'OK' if ws_ok else 'FAIL'} | "
        f"{armed_count} armed | mode: {market_mode}"
    )
    alert_key = _alert_key(trade_date, slot)
    cur = conn.execute(
        "INSERT OR IGNORE INTO live_heartbeats (trade_date, slot, status, detail) VALUES (?, ?, ?, ?)",
        (trade_date, slot, status, message),
    )
    is_new = bool(cur.rowcount)
    if is_new:
        # Same transaction as the live_heartbeats row: both commit together
        # or (on a crash before commit) neither does -- there is never a
        # durable heartbeat row with no matching outbox row to retry.
        outbox.enqueue(conn, alert_key, "heartbeat",
                        {"message": message, "trade_date": trade_date, "slot": slot, "status": status})
    conn.commit()

    # Always attempt delivery, not only when is_new -- a prior call's outbox
    # row may still be 'pending' (transient failure, backoff not yet
    # elapsed) even though live_heartbeats already holds this slot's row.
    cfg = telegram_engine._telegram_config()  # noqa: SLF001 - reuse the one dry_run/token resolver
    live_sender = sender or telegram_engine.get_sender()
    send_fn = outbox.dry_run_or_live_sender(dry_run=cfg["dry_run"], live_sender=live_sender)
    result = outbox.deliver_pending(conn, send_fn, now=now)
    sent = alert_key in result["delivered"]
    return {"status": status, "message": message, "sent": sent, "new": is_new}
