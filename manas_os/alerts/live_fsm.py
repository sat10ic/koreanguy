"""Replayable intraday alert FSM for the Telegram workflow.

This is the W4.1 harness-first slice: no WebSocket, no Telegram network, no
credentials. Mocked/replayed events drive the same persisted state machine the
live loop will later call.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

DEFAULT_TTL_MINUTES = 25

TERMINAL_STATES = {"CONFIRMED", "EXPIRED"}
ACTIVE_ALERT_STATES = {"ALERTED", "CONFIRM_PENDING"}


def ensure_schema(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS live_fsm_state ("
        "trade_date TEXT NOT NULL, symbol TEXT NOT NULL, setup_id TEXT NOT NULL, "
        "state TEXT NOT NULL, trigger REAL, stop REAL, qty INTEGER, setup_family TEXT, "
        "rank INTEGER, ttl_minutes INTEGER NOT NULL DEFAULT 25, alerted_at TEXT, "
        "expires_at TEXT, last_bar_ts TEXT, alert_count INTEGER NOT NULL DEFAULT 0, "
        "paper_mode INTEGER NOT NULL DEFAULT 1, updated_at TEXT DEFAULT (datetime('now')), "
        "PRIMARY KEY(trade_date, symbol, setup_id))"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS live_fsm_transitions ("
        "transition_id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "trade_date TEXT NOT NULL, symbol TEXT NOT NULL, setup_id TEXT NOT NULL, "
        "from_state TEXT, to_state TEXT NOT NULL, event_ts TEXT NOT NULL, "
        "event_type TEXT NOT NULL, price REAL, detail TEXT, "
        "created_at TEXT DEFAULT (datetime('now')), "
        "UNIQUE(trade_date, symbol, setup_id, to_state, event_ts, event_type))"
    )


def arm_from_armed_list(conn, armed_date: str, ttl_minutes: int = DEFAULT_TTL_MINUTES) -> int:
    """Create ARMED FSM rows from the deterministic C14 armed_list.

    Existing rows are left untouched, making arm/replay idempotent.
    """
    ensure_schema(conn)
    rows = conn.execute(
        "SELECT symbol, trigger, stop, qty, setup_family, rank FROM armed_list "
        "WHERE armed_date = ? ORDER BY rank, symbol",
        (armed_date,),
    ).fetchall()
    created = 0
    for row in rows:
        setup_id = _setup_id(row)
        cur = conn.execute(
            "INSERT OR IGNORE INTO live_fsm_state "
            "(trade_date, symbol, setup_id, state, trigger, stop, qty, setup_family, rank, ttl_minutes) "
            "VALUES (?, ?, ?, 'ARMED', ?, ?, ?, ?, ?, ?)",
            (
                armed_date,
                row["symbol"],
                setup_id,
                row["trigger"],
                row["stop"],
                row["qty"],
                row["setup_family"],
                row["rank"],
                ttl_minutes,
            ),
        )
        if cur.rowcount:
            created += 1
            _record_transition(
                conn,
                armed_date,
                row["symbol"],
                setup_id,
                None,
                "ARMED",
                f"{armed_date}T00:00:00",
                "arm",
                row["trigger"],
                "armed from nightly digest",
            )
    conn.commit()
    return created


def replay_events(conn, armed_date: str, events: list[dict[str, Any]], ttl_minutes: int = DEFAULT_TTL_MINUTES) -> dict[str, Any]:
    """Drive mocked/replayed events through the FSM.

    Events are dicts:
    - tick: {"type": "tick", "symbol": "ABC", "ts": "...", "price": 101}
    - confirm: {"type": "confirm", "symbol": "ABC", "ts": "...", "price": 101}
    - expire: {"type": "expire", "ts": "..."} to advance the virtual clock.
    """
    ensure_schema(conn)
    created = arm_from_armed_list(conn, armed_date, ttl_minutes=ttl_minutes)
    before = _transition_count(conn)
    for event in sorted(events, key=lambda e: e["ts"]):
        _expire_due(conn, armed_date, event["ts"])
        kind = str(event.get("type") or "tick").lower()
        if kind == "tick":
            _on_tick(conn, armed_date, event)
        elif kind == "confirm":
            _on_confirm(conn, armed_date, event)
        elif kind == "expire":
            _expire_due(conn, armed_date, event["ts"], force=True)
        else:
            raise ValueError(f"unknown replay event type: {kind}")
    conn.commit()
    after = _transition_count(conn)
    return {
        "armed_created": created,
        "transitions_created": after - before,
        "alert_count": _alert_count(conn, armed_date),
        "states": states(conn, armed_date),
    }


def states(conn, armed_date: str) -> list[dict[str, Any]]:
    ensure_schema(conn)
    rows = conn.execute(
        "SELECT * FROM live_fsm_state WHERE trade_date = ? ORDER BY rank, symbol",
        (armed_date,),
    ).fetchall()
    return [dict(row) for row in rows]


def transitions(conn, armed_date: str) -> list[dict[str, Any]]:
    ensure_schema(conn)
    rows = conn.execute(
        "SELECT * FROM live_fsm_transitions WHERE trade_date = ? ORDER BY transition_id",
        (armed_date,),
    ).fetchall()
    return [dict(row) for row in rows]


def _on_tick(conn, armed_date: str, event: dict[str, Any]) -> None:
    symbol = str(event["symbol"]).upper()
    price = float(event["price"])
    event_ts = event["ts"]
    row = _row(conn, armed_date, symbol)
    if not row or row["state"] != "ARMED":
        return
    if not _is_newer_bar(row, event_ts):
        return
    conn.execute(
        "UPDATE live_fsm_state SET last_bar_ts = ?, updated_at = datetime('now') "
        "WHERE trade_date = ? AND symbol = ? AND setup_id = ?",
        (event_ts, armed_date, symbol, row["setup_id"]),
    )
    if price < float(row["trigger"]):
        return
    _transition(conn, row, "TRIGGERED", event_ts, "tick", price, "trigger crossed")
    refreshed = _row(conn, armed_date, symbol, row["setup_id"])
    _transition(conn, refreshed, "ALERTED", event_ts, "tick", price, "alert emitted", alert=True)


def _on_confirm(conn, armed_date: str, event: dict[str, Any]) -> None:
    symbol = str(event["symbol"]).upper()
    price = float(event.get("price") or 0)
    event_ts = event["ts"]
    row = _row(conn, armed_date, symbol)
    if not row or row["state"] in TERMINAL_STATES:
        return
    if row["state"] == "ALERTED":
        _transition(conn, row, "CONFIRM_PENDING", event_ts, "confirm", price, "user confirmation received")
        row = _row(conn, armed_date, symbol, row["setup_id"])
    if row["state"] == "CONFIRM_PENDING":
        _transition(conn, row, "CONFIRMED", event_ts, "confirm", price, "paper confirmation accepted")


def _expire_due(conn, armed_date: str, event_ts: str, force: bool = False) -> None:
    rows = conn.execute(
        "SELECT * FROM live_fsm_state WHERE trade_date = ? AND state IN ('ALERTED', 'CONFIRM_PENDING')",
        (armed_date,),
    ).fetchall()
    now = _dt(event_ts)
    for row in rows:
        expires_at = row["expires_at"]
        if force or (expires_at and now >= _dt(expires_at)):
            _transition(conn, row, "EXPIRED", event_ts, "expire", None, "alert TTL expired")


def _transition(conn, row, to_state: str, event_ts: str, event_type: str, price: float | None, detail: str, alert: bool = False) -> bool:
    if row is None:
        return False
    if row["state"] == to_state or row["state"] in TERMINAL_STATES:
        return False
    from_state = row["state"]
    expires_at = row["expires_at"]
    alerted_at = row["alerted_at"]
    alert_count = int(row["alert_count"] or 0)
    if to_state == "ALERTED":
        alerted_at = event_ts
        expires_at = (_dt(event_ts) + timedelta(minutes=int(row["ttl_minutes"] or DEFAULT_TTL_MINUTES))).isoformat(timespec="minutes")
    if alert:
        alert_count += 1
    _record_transition(conn, row["trade_date"], row["symbol"], row["setup_id"], from_state, to_state, event_ts, event_type, price, detail)
    conn.execute(
        "UPDATE live_fsm_state SET state = ?, alerted_at = ?, expires_at = ?, "
        "alert_count = ?, updated_at = datetime('now') "
        "WHERE trade_date = ? AND symbol = ? AND setup_id = ?",
        (to_state, alerted_at, expires_at, alert_count, row["trade_date"], row["symbol"], row["setup_id"]),
    )
    return True


def _record_transition(conn, trade_date: str, symbol: str, setup_id: str, from_state: str | None,
                       to_state: str, event_ts: str, event_type: str, price: float | None, detail: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO live_fsm_transitions "
        "(trade_date, symbol, setup_id, from_state, to_state, event_ts, event_type, price, detail) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (trade_date, symbol, setup_id, from_state, to_state, event_ts, event_type, price, detail),
    )


def _row(conn, armed_date: str, symbol: str, setup_id: str | None = None):
    if setup_id:
        return conn.execute(
            "SELECT * FROM live_fsm_state WHERE trade_date = ? AND symbol = ? AND setup_id = ?",
            (armed_date, symbol, setup_id),
        ).fetchone()
    return conn.execute(
        "SELECT * FROM live_fsm_state WHERE trade_date = ? AND symbol = ? ORDER BY rank, setup_id LIMIT 1",
        (armed_date, symbol),
    ).fetchone()


def _is_newer_bar(row, event_ts: str) -> bool:
    last = row["last_bar_ts"]
    return not last or _dt(event_ts) > _dt(last)


def _setup_id(row) -> str:
    family = row["setup_family"] or "setup"
    rank = row["rank"] if row["rank"] is not None else "na"
    return f"{family}:{rank}"


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _transition_count(conn) -> int:
    return int(conn.execute("SELECT COUNT(*) FROM live_fsm_transitions").fetchone()[0])


def _alert_count(conn, armed_date: str) -> int:
    row = conn.execute(
        "SELECT COALESCE(SUM(alert_count), 0) AS n FROM live_fsm_state WHERE trade_date = ?",
        (armed_date,),
    ).fetchone()
    return int(row["n"] or 0)

