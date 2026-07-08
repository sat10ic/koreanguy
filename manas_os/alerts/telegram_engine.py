"""Telegram digest generation for the armed-list workflow.

The default path is deterministic and dry-run: it renders the nightly digest,
stores the ARMED list for the next-session trigger workflow, and logs the
pipeline stage. Live Bot API delivery is opt-in via config.yaml.
"""
from __future__ import annotations

from datetime import date, timedelta
import time
from urllib import parse, request
from typing import Any

from manas_os import config
from manas_os import market_calendar
from manas_os.scanner import candidates as scanner_candidates

STAGE = "telegram_digest"
SOURCE = "scan_candidates+refusals"
TELEGRAM_API = "https://api.telegram.org"

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
        "refusal_count": refused,
        "cap": cap,
        "digest": digest,
        "armed_count": armed_count,
    }


def render_digest_message(digest: dict[str, Any]) -> str:
    """Render the single nightly Telegram message."""
    rows = [
        f"Manas armed list | {digest['as_of']} | {digest['market_mode']}",
        f"Armed: {digest['armed_count']}/{digest['cap']}",
        f"Refusals: {digest['refusal_count']}",
    ]
    if not digest["digest"]:
        return "\n".join([*rows, "", "No armed candidates."])

    rows.append("")
    for idx, card in enumerate(digest["digest"], start=1):
        rows.append(
            f"{idx}. {card.get('symbol')} | {card.get('setup_family') or card.get('setup_type') or 'setup'} "
            f"| trigger {card.get('entry')} | stop {card.get('stop')} | qty {card.get('suggested_qty')}"
        )
    return "\n".join(rows)


def _telegram_config() -> dict[str, Any]:
    """Read Telegram config; legacy alerts.* keys are fallback-only."""
    return {
        "bot_token": config.get("telegram.bot_token", config.get("alerts.telegram_token", "")),
        "chat_id": config.get("telegram.chat_id", config.get("alerts.telegram_chat_id", "")),
        "dry_run": bool(config.get("telegram.dry_run", config.get("alerts.dry_run", True))),
    }


def _telegram_sender(message: str) -> None:
    cfg = _telegram_config()
    token = str(cfg.get("bot_token") or "").strip()
    chat_id = str(cfg.get("chat_id") or "").strip()
    if not token or not chat_id:
        raise ValueError("telegram.bot_token and telegram.chat_id are required when dry_run=false")
    body = parse.urlencode({"chat_id": chat_id, "text": message}).encode("utf-8")
    req = request.Request(
        f"{TELEGRAM_API}/bot{token}/sendMessage",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with request.urlopen(req, timeout=10) as resp:  # noqa: S310 - opt-in operator-configured endpoint.
        if resp.status >= 400:
            raise RuntimeError(f"telegram send failed: HTTP {resp.status}")


def get_sender():
    """AU7: public accessor for the Telegram sender — callers outside this
    module (signals.py, coach.py) should not reach into the private
    _telegram_sender name directly."""
    return _telegram_sender


def send_digest(
    conn,
    run_date: str,
    *,
    sender=None,
    dry_run: bool | None = None,
) -> dict[str, Any]:
    """Build, render, optionally send, and pipeline-log one nightly digest."""
    started = time.monotonic()
    try:
        ensure_schema(conn)
        result = build_digest(conn, run_date)
        message = render_digest_message(result)
        cfg = _telegram_config()
        is_dry_run = cfg["dry_run"] if dry_run is None else bool(dry_run)
        if not is_dry_run:
            (sender or _telegram_sender)(message)
        conn.execute(
            "INSERT INTO pipeline_runs (run_date, stage, source, status, rows_affected, "
            "duration_s, detail) VALUES (?, ?, ?, 'ok', ?, ?, ?)",
            (
                run_date,
                STAGE,
                SOURCE,
                result["armed_count"],
                round(time.monotonic() - started, 3),
                f"as_of={result['as_of']} armed={result['armed_count']} dry_run={is_dry_run}",
            ),
        )
        conn.commit()
        return {
            "status": "ok",
            "armed_count": result["armed_count"],
            "sent": not is_dry_run,
            "dry_run": is_dry_run,
            "message": message,
        }
    except Exception as exc:  # noqa: BLE001
        conn.execute(
            "INSERT INTO pipeline_runs (run_date, stage, source, status, rows_affected, "
            "duration_s, detail) VALUES (?, ?, ?, 'fail', 0, ?, ?)",
            (run_date, STAGE, SOURCE, round(time.monotonic() - started, 3), str(exc)),
        )
        conn.commit()
        return {"status": "fail", "armed_count": 0, "detail": str(exc)}


def run(conn, run_date: str) -> dict[str, Any]:
    """Generate the Telegram digest armed list and log the pipeline stage."""
    result = send_digest(conn, run_date)
    return {
        "status": result["status"],
        "armed_count": result["armed_count"],
        **({"detail": result["detail"]} if result["status"] == "fail" else {}),
    }
