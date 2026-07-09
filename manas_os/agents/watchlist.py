"""G1: the living agent watchlist.

Deterministic, no extra LLM call — reads the chair's already-persisted verdicts
for tonight and the most recent prior night that had chair verdicts, diffs
them, and writes one agent_watchlist row per symbol with a plain-English
reason. A symbol that drops out of actual debate gets a two-night grace
period (miss_streak) before being marked DROP, so a single quiet night is not
mistaken for "forgotten."
"""
from __future__ import annotations

from typing import Any

from manas_os.agents import _shared

AGENT = "watchlist"


def ensure_schema(conn) -> None:
    _shared.ensure_agent_tables(conn)


def _chair_rows(conn, scan_date: str) -> dict[str, dict[str, Any]]:
    rows = conn.execute(
        "SELECT symbol, verdict, conviction, rank, tier FROM agent_verdicts "
        "WHERE scan_date = ? AND agent = 'chair'",
        (scan_date,),
    ).fetchall()
    return {row["symbol"]: dict(row) for row in rows}


def _previous_chair_scan_date(conn, scan_date: str) -> str | None:
    row = conn.execute(
        "SELECT MAX(scan_date) AS d FROM agent_verdicts WHERE agent = 'chair' AND scan_date < ?",
        (scan_date,),
    ).fetchone()
    return row["d"] if row and row["d"] else None


def _previous_watchlist_scan_date(conn, scan_date: str) -> str | None:
    row = conn.execute(
        "SELECT MAX(scan_date) AS d FROM agent_watchlist WHERE scan_date < ?",
        (scan_date,),
    ).fetchone()
    return row["d"] if row and row["d"] else None


def _watchlist_rows(conn, scan_date: str) -> dict[str, dict[str, Any]]:
    rows = conn.execute(
        "SELECT symbol, tier, status, prev_status, reason, miss_streak "
        "FROM agent_watchlist WHERE scan_date = ?",
        (scan_date,),
    ).fetchall()
    return {row["symbol"]: dict(row) for row in rows}


def _verdict_value(verdict: str | None, conviction: int | None) -> int:
    conviction = int(conviction or 0)
    return conviction if str(verdict or "").upper() == "TAKE" else -conviction


def _fmt_verdict(verdict: str | None, conviction: int | None) -> str:
    return f"{str(verdict or 'SKIP').upper()} (conviction {int(conviction or 0)})"


def _status_for_present(tonight: dict[str, Any], prior: dict[str, Any] | None) -> tuple[str, str]:
    if prior is None:
        status = "PROMOTE" if str(tonight.get("verdict") or "").upper() == "TAKE" else "HOLD"
        reason = f"new to the debate; chair verdict {_fmt_verdict(tonight.get('verdict'), tonight.get('conviction'))}"
        return status, reason

    tv = _verdict_value(tonight.get("verdict"), tonight.get("conviction"))
    pv = _verdict_value(prior.get("verdict"), prior.get("conviction"))
    if tv > pv:
        status = "PROMOTE"
    elif tv < pv:
        status = "DEMOTE"
    else:
        status = "HOLD"
    reason = (
        f"chair verdict {_fmt_verdict(prior.get('verdict'), prior.get('conviction'))} -> "
        f"{_fmt_verdict(tonight.get('verdict'), tonight.get('conviction'))}"
    )
    return status, reason


def _status_for_hard_near_miss(tier: str, gate: str, reason: str, prior: dict[str, Any] | None) -> tuple[str, str]:
    reason_suffix = f" — {reason}" if reason else ""
    if prior is None:
        return "HOLD", f"hard gate failure: {gate}{reason_suffix}"
    if (prior.get("tier") or "") == tier:
        return "HOLD", f"still hard-failing {gate}{reason_suffix}"
    was = prior.get("tier") or prior.get("status") or "unknown"
    return "DEMOTE", f"now hard-failing {gate} (was {was}){reason_suffix}"


def compute(conn, scan_date: str, hard_near_misses: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Compute + persist tonight's watchlist rows. Idempotent (safe to rerun).

    WO6: hard-gate near-misses (structurally untradeable — regime/tradability/
    risk) never enter the debate, so they never get a chair verdict; they are
    passed in separately and still land here with tier NEAR_MISS(hard:<gate>)
    so a human can see them, without spending any tokens or rendering charts.
    """
    ensure_schema(conn)
    hard_near_misses = hard_near_misses or []
    tonight = _chair_rows(conn, scan_date)

    prev_chair_date = _previous_chair_scan_date(conn, scan_date)
    prev_chair = _chair_rows(conn, prev_chair_date) if prev_chair_date else {}

    prev_wl_date = _previous_watchlist_scan_date(conn, scan_date)
    prev_watchlist = _watchlist_rows(conn, prev_wl_date) if prev_wl_date else {}

    if not tonight and not prev_watchlist and not hard_near_misses:
        return {"status": "skip", "rows": 0, "detail": "watchlist: nothing debated, nothing carried over"}

    rows_written = 0
    handled: set[str] = set()
    for symbol, row in tonight.items():
        status, reason = _status_for_present(row, prev_chair.get(symbol))
        prev_status = (prev_watchlist.get(symbol) or {}).get("status")
        conn.execute(
            "INSERT INTO agent_watchlist (scan_date, symbol, tier, status, prev_status, reason, miss_streak) "
            "VALUES (?, ?, ?, ?, ?, ?, 0) "
            "ON CONFLICT(scan_date, symbol) DO UPDATE SET "
            "tier=excluded.tier, status=excluded.status, prev_status=excluded.prev_status, "
            "reason=excluded.reason, miss_streak=excluded.miss_streak",
            (scan_date, symbol, row.get("tier") or "PASSED", status, prev_status, reason),
        )
        rows_written += 1
        handled.add(symbol)

    for item in hard_near_misses:
        symbol = str(item.get("symbol") or "").upper().strip()
        if not symbol or symbol in handled:
            continue
        gate = str(item.get("failed_gate") or "unknown")
        reason_text = str(item.get("reason") or "")
        tier = f"NEAR_MISS(hard:{gate})"
        prior = prev_watchlist.get(symbol)
        status, reason = _status_for_hard_near_miss(tier, gate, reason_text, prior)
        prev_status = (prior or {}).get("status")
        conn.execute(
            "INSERT INTO agent_watchlist (scan_date, symbol, tier, status, prev_status, reason, miss_streak) "
            "VALUES (?, ?, ?, ?, ?, ?, 0) "
            "ON CONFLICT(scan_date, symbol) DO UPDATE SET "
            "tier=excluded.tier, status=excluded.status, prev_status=excluded.prev_status, "
            "reason=excluded.reason, miss_streak=excluded.miss_streak",
            (scan_date, symbol, tier, status, prev_status, reason),
        )
        rows_written += 1
        handled.add(symbol)

    for symbol, prior in prev_watchlist.items():
        if symbol in handled:
            continue
        if prior.get("status") == "DROP":
            continue  # already dropped; do not resurrect or re-emit noise
        miss_streak = int(prior.get("miss_streak") or 0) + 1
        if miss_streak >= 2:
            status = "DROP"
            reason = f"missing from debate {miss_streak} nights running"
        else:
            status = prior.get("status") or "HOLD"
            reason = f"not re-debated tonight (miss {miss_streak}/2); holding prior status"
        conn.execute(
            "INSERT INTO agent_watchlist (scan_date, symbol, tier, status, prev_status, reason, miss_streak) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(scan_date, symbol) DO UPDATE SET "
            "tier=excluded.tier, status=excluded.status, prev_status=excluded.prev_status, "
            "reason=excluded.reason, miss_streak=excluded.miss_streak",
            (scan_date, symbol, prior.get("tier"), status, prior.get("status"), reason, miss_streak),
        )
        rows_written += 1

    return {"status": "ok" if rows_written else "skip", "rows": rows_written, "detail": f"watchlist scan_date={scan_date} rows={rows_written}"}
