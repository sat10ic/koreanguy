"""09:20 IST heartbeat -- absence is the alert (LIVE_LOOP_FABLE §3.3).

One heartbeat row per (trade_date, slot); a second slot ("13:00") can be sent
the same way to catch a midday death. The standing instruction to the user
(documented, not enforced in code -- there is nothing code can do about a
message that never arrives): no 09:20 message means the loop is down, assume
no coverage today.
"""
from __future__ import annotations

from typing import Any

from manas_os.alerts import telegram_engine

DEFAULT_SLOT = "09:20"


def ensure_schema(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS live_heartbeats ("
        "trade_date TEXT NOT NULL, slot TEXT NOT NULL, status TEXT NOT NULL, "
        "detail TEXT, created_at TEXT DEFAULT (datetime('now')), "
        "PRIMARY KEY(trade_date, slot))"
    )


def send_heartbeat(conn, trade_date: str, *, slot: str = DEFAULT_SLOT, armed_count: int,
                    market_mode: str, ws_ok: bool, token_ok: bool, sender=None) -> dict[str, Any]:
    ensure_schema(conn)
    status = "alive" if (ws_ok and token_ok) else "degraded"
    message = (
        f"Loop alive | token {'OK' if token_ok else 'FAIL'} | WS {'OK' if ws_ok else 'FAIL'} | "
        f"{armed_count} armed | mode: {market_mode}"
    )
    cur = conn.execute(
        "INSERT OR IGNORE INTO live_heartbeats (trade_date, slot, status, detail) VALUES (?, ?, ?, ?)",
        (trade_date, slot, status, message),
    )
    is_new = bool(cur.rowcount)
    sent = False
    if is_new:
        cfg = telegram_engine._telegram_config()  # noqa: SLF001 - reuse the one dry_run/token resolver
        if not cfg["dry_run"]:
            try:
                (sender or telegram_engine.get_sender())(message)
                sent = True
            except Exception:  # noqa: BLE001 - heartbeat send failure must never crash the loop
                sent = False
    conn.commit()
    return {"status": status, "message": message, "sent": sent, "new": is_new}
