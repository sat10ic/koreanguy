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
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from manas_os import config
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


def push_entry_alert(conn, trade_date: str, symbol: str, fsm_row: dict, tick: dict, *,
                      sender=None) -> dict[str, Any]:
    ensure_schema(conn)
    dedup = telegram_replies.record_push(conn, trade_date, symbol, kind="entry")
    if not dedup["ok"]:
        return {"ok": False, "reason": dedup["reason"], "paper": True}

    payload = render_entry_payload(trade_date, symbol, fsm_row, tick)
    message = render_entry_message(payload)
    sent = _maybe_send(message, sender)
    _write_log(conn, trade_date, symbol, "entry", payload, message, paper=not sent, sent=sent)
    return {"ok": True, "paper": not sent, "sent": sent, "message": message, "payload": payload}


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
