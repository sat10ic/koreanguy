"""Telegram entry signals for chair-approved, sized agent picks."""
from __future__ import annotations

import json
from typing import Any, Callable

from manas_os import config
from manas_os.alerts import outbox, telegram_engine

AGENT = "signals"
CHANNEL = "telegram"
MANUAL_SUFFIX = "signal — manual execution only; not advice"


def ensure_schema(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS agent_signals ("
        "scan_date TEXT NOT NULL, symbol TEXT NOT NULL, channel TEXT NOT NULL, "
        "message TEXT NOT NULL, sent INTEGER NOT NULL DEFAULT 0, "
        "created_at TEXT DEFAULT (datetime('now')), "
        "PRIMARY KEY(scan_date, symbol, channel))"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS scan_agent_logs ("
        "log_id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "run_date TEXT, agent TEXT, model TEXT, prompt_sha TEXT, "
        "latency_ms INTEGER, tokens_in INTEGER, tokens_out INTEGER, "
        "parsed_ok INTEGER, validation TEXT, error TEXT, "
        "created_at TEXT DEFAULT (datetime('now')))"
    )


def _json(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def _live_enabled() -> bool:
    return bool(config.get("agents.telegram_live", False))


def _best_bear_case(conn, scan_date: str, symbol: str, chair_bear_case: str | None) -> str:
    row = conn.execute(
        "SELECT bear_case FROM agent_verdicts "
        "WHERE scan_date = ? AND symbol = ? "
        "AND agent NOT IN ('chair', 'sizer', 'vision') "
        "AND bear_case IS NOT NULL AND TRIM(bear_case) <> '' "
        "ORDER BY COALESCE(conviction, 0) DESC, COALESCE(rank, 999999), agent "
        "LIMIT 1",
        (scan_date, symbol),
    ).fetchone()
    if row and row["bear_case"]:
        return str(row["bear_case"]).strip()

    chair_cases = _json(chair_bear_case, [])
    if isinstance(chair_cases, list):
        for item in chair_cases:
            if isinstance(item, dict) and str(item.get("text") or "").strip():
                return str(item["text"]).strip()
    if isinstance(chair_cases, str) and chair_cases.strip():
        return chair_cases.strip()
    return "not stated"


def _one_line(text: str | None) -> str:
    return " ".join(str(text or "").split()) or "not stated"


def _format_number(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def _render_message(item: dict[str, Any]) -> str:
    lens = _json(item.get("sizer_lens_json"), {})
    chair_lens = _json(item.get("chair_lens_json"), {})
    setup_family = item.get("setup_family") or "setup"
    lens_tag = item.get("setup_type") or item.get("setup") or "lens"
    verdict_split = chair_lens.get("verdict_split") or "n/a"
    disagreement = "disagreement" if chair_lens.get("disagreement") else "aligned"
    multiplier = lens.get("multiplier", "n/a")
    final_qty = lens.get("final_qty", "n/a")
    return "\n".join(
        [
            f"{item['symbol']} | {setup_family} / {lens_tag}",
            f"chair: conviction {item.get('chair_conviction') or 'n/a'} | split {verdict_split} | {disagreement}",
            "plan: "
            f"entry {_format_number(item.get('entry'))} | "
            f"stop {_format_number(item.get('stop'))} | "
            f"RR {_format_number(item.get('rr'))} | "
            f"final_qty {final_qty}",
            f"sizer: multiplier {multiplier} | {_one_line(item.get('sizer_reasoning'))}",
            f"top risk: {_one_line(item.get('bear_case'))}",
            MANUAL_SUFFIX,
        ]
    )


def _load_picks(conn, scan_date: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT sz.symbol, sz.rank AS sizer_rank, sz.lens_scores_json AS sizer_lens_json, "
        "sz.reasoning AS sizer_reasoning, "
        "ch.conviction AS chair_conviction, ch.rank AS chair_rank, "
        "ch.lens_scores_json AS chair_lens_json, ch.bear_case AS chair_bear_case, "
        "sc.setup, sc.setup_type, sc.setup_family, sc.entry, sc.stop, sc.rr, sc.rank AS candidate_rank "
        "FROM agent_verdicts sz "
        "JOIN agent_verdicts ch ON ch.scan_date = sz.scan_date AND ch.symbol = sz.symbol AND ch.agent = 'chair' "
        "JOIN scan_candidates sc ON sc.scan_date = sz.scan_date AND sc.symbol = sz.symbol "
        "WHERE sz.scan_date = ? AND sz.agent = 'sizer' AND sz.verdict = 'TAKE' "
        "ORDER BY COALESCE(sz.rank, ch.rank, sc.rank, 999999), sz.symbol",
        (scan_date,),
    ).fetchall()
    picks = []
    for row in rows:
        item = dict(row)
        item["bear_case"] = _best_bear_case(conn, scan_date, item["symbol"], item.get("chair_bear_case"))
        picks.append(item)
    return picks


def _persist_signal(conn, scan_date: str, symbol: str, message: str, sent: bool) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO agent_signals (scan_date, symbol, channel, message, sent) "
        "VALUES (?, ?, ?, ?, ?)",
        (scan_date, symbol, CHANNEL, message, 1 if sent else 0),
    )


def _agent_log(conn, run_date: str, validation: str, error: str | None = None) -> None:
    conn.execute(
        "INSERT INTO scan_agent_logs "
        "(run_date, agent, model, prompt_sha, latency_ms, parsed_ok, validation, error) "
        "VALUES (?, ?, NULL, NULL, NULL, ?, ?, ?)",
        (run_date, AGENT, 0 if error else 1, validation, error),
    )


def run(
    conn,
    scan_date: str,
    run_date: str | None = None,
    *,
    sender: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    run_date = run_date or scan_date
    ensure_schema(conn)
    outbox.ensure_schema(conn)
    picks = _load_picks(conn, scan_date)
    if not picks:
        _agent_log(conn, run_date, "skip")
        return {"status": "skip", "rows": 0, "sent": 0, "detail": "signals no sizer TAKE picks"}

    live = _live_enabled()
    send = sender or telegram_engine.get_sender()

    # RELIABILITY_AUDIT_2026-07-19 #8, sibling of the coach.py fix (flagged in
    # that commit as "agents/signals.py same ordering"): this used to call
    # send() inline, mid-loop, with the agent_signals persistence committed
    # separately by the caller. A transient send failure was a permanently
    # missed alert (the row already said sent=0 with nothing retrying it), and
    # a crash after a successful send but before the caller's commit re-sent
    # every pick on the next run. Fixed identically to coach.run: enqueue into
    # the transactional outbox (no network call, no commit) inside the same
    # transaction as the agent_signals business writes, commit, and only THEN
    # attempt delivery via the outbox's single sender path.
    pending_alerts: list[tuple[str, str]] = []  # (alert_key, symbol) enqueued this run, awaiting post-commit delivery
    for item in picks:
        message = _render_message(item)
        if live:
            alert_key = f"entry_signal:{scan_date}:{item['symbol']}:{CHANNEL}"
            outbox.enqueue(conn, alert_key, "entry_signal",
                           {"message": message, "symbol": item["symbol"],
                            "scan_date": scan_date, "channel": CHANNEL})
            pending_alerts.append((alert_key, item["symbol"]))
        _persist_signal(conn, scan_date, item["symbol"], message, sent=False)

    sent_count = 0
    failures: list[str] = []
    if pending_alerts:
        # Business writes + outbox rows land atomically, BEFORE any send.
        conn.commit()

        def send_fn(payload: dict) -> None:
            send(payload["message"])

        deliver = outbox.deliver_pending(conn, send_fn)
        for alert_key, symbol in pending_alerts:
            if alert_key in deliver["delivered"]:
                sent_count += 1
                conn.execute(
                    "UPDATE agent_signals SET sent = 1 WHERE scan_date = ? AND symbol = ? AND channel = ?",
                    (scan_date, symbol, CHANNEL),
                )
            else:
                # retried (still pending, backoff not yet elapsed), failed
                # (attempts exhausted), or ambiguous -- none of those are a
                # successful delivery this call, so the run is 'partial'.
                row = outbox.get(conn, alert_key)
                reason = (row or {}).get("last_error") or f"not delivered (state={(row or {}).get('state')})"
                failures.append(f"{symbol}: {reason}")
        if sent_count:
            conn.commit()

    status = "partial" if failures else "ok"
    detail = f"signals scan_date={scan_date} rows={len(picks)} sent={sent_count} live={live}"
    if failures:
        detail = f"{detail}; send_failures={' | '.join(failures)}"
    _agent_log(conn, run_date, "ok" if not failures else "partial", "; ".join(failures) if failures else None)
    return {"status": status, "rows": len(picks), "sent": sent_count, "detail": detail}
