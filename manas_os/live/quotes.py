"""Latest-LTP cache for the live loop -- Stage 1's contribution to the
LIVE-FIRST decision (manas_os/design/LIVE_FIRST_DECISION.md): a small,
persisted "what is the last price we saw" table that a later desk-facing
endpoint (and, later still, the SSE tick stream) can read without going back
to Fyers or waiting on the FSM.

One-writer rule holds here too: this module only ever records what a tick
said, never computes P&L, risk, or anything display-derived from it -- that
stays the API layer's job, reading whatever this table already states.

Persisted (not purely in-memory) so a process restart doesn't erase "what
did we last see" -- consistent with the rest of the live/ package's
restart-safe design.
"""
from __future__ import annotations

from typing import Any, Iterable


def ensure_schema(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS live_quotes ("
        "symbol TEXT PRIMARY KEY, ltp REAL NOT NULL, bar_ts TEXT, "
        "updated_at TEXT DEFAULT (datetime('now')))"
    )


def update_quote(conn, symbol: str, ltp: float, bar_ts: str | None = None) -> None:
    ensure_schema(conn)
    conn.execute(
        "INSERT INTO live_quotes (symbol, ltp, bar_ts, updated_at) VALUES (?, ?, ?, datetime('now')) "
        "ON CONFLICT(symbol) DO UPDATE SET ltp=excluded.ltp, bar_ts=excluded.bar_ts, "
        "updated_at=datetime('now')",
        (symbol.strip().upper(), ltp, bar_ts),
    )
    conn.commit()


def get_quotes(conn, symbols: Iterable[str] | None = None) -> dict[str, dict[str, Any]]:
    """Returns {SYMBOL: {ltp, bar_ts, updated_at}}. Never raises on a missing
    table (a fresh DB with no live session run yet is a legitimate state, not
    an error)."""
    ensure_schema(conn)
    if symbols is not None:
        symbols = [s.strip().upper() for s in symbols]
        if not symbols:
            return {}
        placeholders = ",".join("?" for _ in symbols)
        rows = conn.execute(
            f"SELECT symbol, ltp, bar_ts, updated_at FROM live_quotes WHERE symbol IN ({placeholders})",
            symbols,
        ).fetchall()
    else:
        rows = conn.execute("SELECT symbol, ltp, bar_ts, updated_at FROM live_quotes").fetchall()
    return {r["symbol"]: {"ltp": r["ltp"], "bar_ts": r["bar_ts"], "updated_at": r["updated_at"]} for r in rows}


def latest_as_of(conn) -> str | None:
    ensure_schema(conn)
    row = conn.execute("SELECT MAX(updated_at) AS m FROM live_quotes").fetchone()
    return row["m"] if row else None
