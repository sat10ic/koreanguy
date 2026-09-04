"""Telegram reply capture and alert controls.

This module has no Telegram network dependency. Bot/webhook layers can pass
plain reply text here; the durable write lands in the same setup_decisions and
journal_trades tables used by /api/setups/decision.
"""
from __future__ import annotations

import json
from typing import Any

from manas_os.scanner import candidates as scanner_candidates
from manas_os.scanner import outcomes as scanner_outcomes


def ensure_schema(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS telegram_controls ("
        "key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT DEFAULT (datetime('now')))"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS telegram_pushes ("
        "push_date TEXT NOT NULL, symbol TEXT NOT NULL, kind TEXT NOT NULL, "
        "created_at TEXT DEFAULT (datetime('now')), "
        "PRIMARY KEY(push_date, symbol, kind))"
    )


def _ensure_journal_table(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS journal_trades ("
        "trade_id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "trade_date TEXT NOT NULL, symbol TEXT NOT NULL, setup TEXT, "
        "entry REAL, exit REAL, stop REAL, r_result REAL, mistake_tags_json TEXT, "
        "notes TEXT, created_at TEXT DEFAULT (datetime('now')))"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_journal_trades_date ON journal_trades(trade_date)")
    have = {r[1] for r in conn.execute("PRAGMA table_info(journal_trades)")}
    if "exit_state_json" not in have:
        conn.execute("ALTER TABLE journal_trades ADD COLUMN exit_state_json TEXT")
    if "first_exit_flag_date" not in have:
        conn.execute("ALTER TABLE journal_trades ADD COLUMN first_exit_flag_date TEXT")
    if "exit_date" not in have:
        conn.execute("ALTER TABLE journal_trades ADD COLUMN exit_date TEXT")


def set_halt(conn, halted: bool, reason: str | None = None) -> dict[str, Any]:
    ensure_schema(conn)
    conn.execute(
        "INSERT INTO telegram_controls (key, value, updated_at) VALUES ('entries_halted', ?, datetime('now')) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=datetime('now')",
        ("1" if halted else "0",),
    )
    if reason:
        conn.execute(
            "INSERT INTO telegram_controls (key, value, updated_at) VALUES ('halt_reason', ?, datetime('now')) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=datetime('now')",
            (reason,),
        )
    conn.commit()
    return {"ok": True, "entries_halted": halted}


def entries_halted(conn) -> bool:
    ensure_schema(conn)
    row = conn.execute("SELECT value FROM telegram_controls WHERE key = 'entries_halted'").fetchone()
    return bool(row and row["value"] == "1")


def exit_alerts_allowed(conn) -> bool:
    ensure_schema(conn)
    return True


def record_push(conn, push_date: str, symbol: str, kind: str = "entry", *, commit: bool = True) -> dict[str, Any]:
    """`commit=False` lets a caller (alerts.live_fsm) fold this dedupe write
    into a larger transaction -- e.g. together with the FSM's ALERTED state
    write and the outbox enqueue, so all three commit atomically
    (RELIABILITY_AUDIT_2026-07-19 #8: this used to commit its own dedupe key
    before the network send even happened, so a transient send failure
    still left the dedupe row in place and the alert was never retried)."""
    ensure_schema(conn)
    sym = symbol.strip().upper()
    if kind == "entry" and entries_halted(conn):
        return {"ok": False, "reason": "entries_halted", "symbol": sym, "kind": kind}
    cur = conn.execute(
        "INSERT OR IGNORE INTO telegram_pushes (push_date, symbol, kind) VALUES (?, ?, ?)",
        (push_date, sym, kind),
    )
    if commit:
        conn.commit()
    return {
        "ok": cur.rowcount == 1,
        "reason": None if cur.rowcount == 1 else "duplicate_push",
        "symbol": sym,
        "kind": kind,
    }


def handle_reply(conn, text: str, trade_date: str) -> dict[str, Any]:
    ensure_schema(conn)
    raw = (text or "").strip()
    if raw.lower().startswith("/halt"):
        return set_halt(conn, True, reason=raw)

    parts = raw.split(maxsplit=2)
    if len(parts) < 2 or parts[0].upper() not in {"TAKE", "SKIP"}:
        return {"ok": False, "reason": "unsupported_reply"}

    action = parts[0].lower()
    symbol = parts[1].upper()
    skip_reason = parts[2] if action == "skip" and len(parts) > 2 else None
    return record_setup_decision(
        conn,
        trade_date,
        symbol,
        "taken" if action == "take" else "skipped",
        skip_reason=skip_reason,
    )


def record_setup_decision(
    conn,
    scan_date: str,
    symbol: str,
    decision: str,
    *,
    skip_reason: str | None = None,
    entry_price: float | None = None,
    qty: int | None = None,
) -> dict[str, Any]:
    if decision not in {"taken", "skipped"}:
        return {"ok": False, "reason": "decision must be taken or skipped"}
    sym = symbol.strip().upper()
    scanner_candidates.ensure_schema(conn)
    scanner_outcomes.ensure_setup_decisions_schema(conn)
    _ensure_journal_table(conn)
    row = conn.execute(
        "SELECT * FROM scan_candidates WHERE scan_date = ? AND symbol = ? "
        "ORDER BY rank IS NULL, rank, setup LIMIT 1",
        (scan_date, sym),
    ).fetchone()
    if not row:
        return {"ok": False, "reason": "setup candidate not found", "symbol": sym}

    previous = conn.execute(
        "SELECT decision FROM setup_decisions WHERE scan_date = ? AND symbol = ?",
        (scan_date, sym),
    ).fetchone()
    candidate = dict(row)
    conn.execute(
        "INSERT INTO setup_decisions "
        "(scan_date, symbol, decision, skip_reason, entry_price, qty, snapshot_json) "
        "VALUES (?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(scan_date, symbol) DO UPDATE SET "
        "decision=excluded.decision, skip_reason=excluded.skip_reason, "
        "entry_price=excluded.entry_price, qty=excluded.qty, "
        "snapshot_json=excluded.snapshot_json, created_at=datetime('now')",
        (
            scan_date,
            sym,
            decision,
            skip_reason,
            entry_price,
            qty,
            json.dumps(candidate, sort_keys=True),
        ),
    )
    trade_id = None
    if decision == "taken" and (not previous or previous["decision"] != "taken"):
        cur = conn.execute(
            "INSERT INTO journal_trades "
            "(trade_date, symbol, setup, entry, stop, exit, notes, mistake_tags_json) "
            "VALUES (?, ?, ?, ?, ?, NULL, 'auto-captured from telegram reply', '[]')",
            (
                scan_date,
                sym,
                candidate.get("setup"),
                entry_price if entry_price is not None else candidate.get("entry"),
                candidate.get("stop"),
            ),
        )
        trade_id = cur.lastrowid
    conn.commit()
    out: dict[str, Any] = {"ok": True, "decision": decision, "symbol": sym}
    if trade_id is not None:
        out["trade_id"] = trade_id
    return out
