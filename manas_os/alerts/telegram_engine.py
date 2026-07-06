"""Telegram digest generation for the armed-list workflow.

This slice is deliberately deterministic: no Bot API calls, no credentials,
and no network I/O. It turns persisted scanner cards into the nightly digest
payload and stores the ARMED list for the next-session trigger workflow.
"""
from __future__ import annotations

from datetime import date, timedelta
import time
from typing import Any

from manas_os import market_calendar
from manas_os.scanner import candidates as scanner_candidates

STAGE = "telegram_digest"
SOURCE = "scan_candidates+refusals"

DIGEST_CAPS = {
    "RISK_ON": 5,
    "SELECTIVE": 3,
    "DEFENSIVE": 1,
    "NO_TRADE": 0,
}


def ensure_schema(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS armed_list ("
        "armed_date TEXT NOT NULL, symbol TEXT NOT NULL, trigger REAL, stop REAL, "
        "qty INTEGER, setup_family TEXT, rank INTEGER, ttl_date TEXT, "
        "created_at TEXT DEFAULT (datetime('now')), "
        "PRIMARY KEY(armed_date, symbol))"
    )


def _next_trading_session(run_date: str) -> str:
    cur = date.fromisoformat(run_date) + timedelta(days=1)
    while not market_calendar.is_trading_day(cur):
        cur += timedelta(days=1)
    return cur.isoformat()


def _refusal_count(conn, run_date: str) -> int:
    have_refusals = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='refusals'"
    ).fetchone()
    if not have_refusals:
        return 0
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM refusals WHERE scan_date = ?",
        (run_date,),
    ).fetchone()
    return int(row["n"] or 0) if row else 0


def build_digest(conn, run_date: str) -> dict[str, Any]:
    ensure_schema(conn)
    payload = scanner_candidates.load_persisted_candidates(conn, run_date)
    as_of = payload.get("as_of") or run_date
    market_mode, _ = scanner_candidates.market_mode_for(conn, as_of)
    cap = DIGEST_CAPS.get(market_mode, 0)
    digest = list(payload.get("candidates") or [])[:cap] if payload.get("available") else []
    refused = _refusal_count(conn, as_of)
    ttl_date = _next_trading_session(as_of)

    conn.execute("DELETE FROM armed_list WHERE armed_date = ?", (as_of,))
    armed_count = 0
    for card in digest:
        conn.execute(
            "INSERT OR REPLACE INTO armed_list "
            "(armed_date, symbol, trigger, stop, qty, setup_family, rank, ttl_date) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                as_of,
                card.get("symbol"),
                card.get("entry"),
                card.get("stop"),
                card.get("suggested_qty"),
                card.get("setup_family"),
                card.get("rank"),
                ttl_date,
            ),
        )
        armed_count += 1

    summary = (
        f"{market_mode} digest: {len(digest)} armed candidate"
        f"{'' if len(digest) == 1 else 's'} and {refused} names refused"
    )
    return {
        "as_of": as_of,
        "market_mode": market_mode,
        "summary": summary,
        "digest": digest,
        "armed_count": armed_count,
    }


def run(conn, run_date: str) -> dict[str, Any]:
    """Generate the Telegram digest armed list and log the pipeline stage."""
    started = time.monotonic()
    try:
        ensure_schema(conn)
        result = build_digest(conn, run_date)
        conn.execute(
            "INSERT INTO pipeline_runs (run_date, stage, source, status, rows_affected, "
            "duration_s, detail) VALUES (?, ?, ?, 'ok', ?, ?, ?)",
            (
                run_date,
                STAGE,
                SOURCE,
                result["armed_count"],
                round(time.monotonic() - started, 3),
                f"as_of={result['as_of']} armed={result['armed_count']}",
            ),
        )
        conn.commit()
        return {"status": "ok", "armed_count": result["armed_count"]}
    except Exception as exc:  # noqa: BLE001
        conn.execute(
            "INSERT INTO pipeline_runs (run_date, stage, source, status, rows_affected, "
            "duration_s, detail) VALUES (?, ?, ?, 'fail', 0, ?, ?)",
            (run_date, STAGE, SOURCE, round(time.monotonic() - started, 3), str(exc)),
        )
        conn.commit()
        return {"status": "fail", "armed_count": 0, "detail": str(exc)}
