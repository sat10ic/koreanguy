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
from manas_os.agents import run_card as _run_card
from manas_os.alerts import outbox
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
    # HANDOFF live_stage2: persist zone at arm time (additive).
    have = {r[1] for r in conn.execute("PRAGMA table_info(armed_list)")}
    if "zone_low" not in have:
        conn.execute("ALTER TABLE armed_list ADD COLUMN zone_low REAL")
    if "zone_high" not in have:
        conn.execute("ALTER TABLE armed_list ADD COLUMN zone_high REAL")


def zone_from_plan(trigger: float | None, atr20: float | None) -> tuple[float | None, float | None]:
    """LIVE_LOOP_FABLE §2.1: pivot → pivot + 0.5*ATR20 when ATR available.

    Falls back to trigger→trigger*(1+0.6%) when ATR missing (documented
    approximation matching live_fsm DEFAULT_ZONE_PCT).
    """
    if trigger is None:
        return None, None
    t = float(trigger)
    if atr20 is not None and float(atr20) > 0:
        return t, t + 0.5 * float(atr20)
    # Same default as live_fsm.DEFAULT_ZONE_PCT (0.6%) — duplicated to avoid import cycle.
    return t, t * 1.006


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


def _watchlist_section(conn, run_date: str) -> dict[str, Any]:
    """SHIP-1 #10: read-only summary of tonight's agent_watchlist rows —
    PROMOTE/DEMOTE lines plus a count of hard-gate near-misses
    (tier LIKE 'NEAR_MISS(hard%'). Never writes; agents/watchlist.py
    (compute()) is the sole writer of agent_watchlist."""
    have_table = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='agent_watchlist'"
    ).fetchone()
    if not have_table:
        return {"promotions": [], "demotions": [], "near_miss_hard_count": 0}
    rows = [
        dict(r)
        for r in conn.execute(
            "SELECT symbol, tier, status, reason FROM agent_watchlist "
            "WHERE scan_date = ? ORDER BY symbol",
            (run_date,),
        ).fetchall()
    ]
    promotions = [r for r in rows if r["status"] == "PROMOTE"]
    demotions = [r for r in rows if r["status"] == "DEMOTE"]
    near_miss_hard_count = sum(1 for r in rows if str(r.get("tier") or "").startswith("NEAR_MISS(hard"))
    return {
        "promotions": promotions,
        "demotions": demotions,
        "near_miss_hard_count": near_miss_hard_count,
    }


def _tonights_call_headline(conn, as_of: str) -> str | None:
    """SHIP-2 finding 3: the same deterministic TONIGHT'S CALL stance the desk
    tab shows, computed via run_card.build (single writer for the decision
    table) so the digest headline can never disagree with the desk. Never
    raises -- a digest must still send on a night the card build hiccups."""
    try:
        card = _run_card.build(conn, as_of)
        call = card.get("tonights_call") or {}
        return call.get("headline")
    except Exception:  # noqa: BLE001
        return None


def build_digest(conn, run_date: str) -> dict[str, Any]:
    ensure_schema(conn)
    payload = scanner_candidates.load_persisted_candidates(conn, run_date)
    as_of = payload.get("as_of") or run_date
    market_mode, _ = scanner_candidates.market_mode_for(conn, as_of)
    cap = DIGEST_CAPS.get(market_mode, 0)
    digest = list(payload.get("candidates") or [])[:cap] if payload.get("available") else []
    refused = _refusal_count(conn, as_of)
    ttl_date = _next_trading_session(as_of)
    tonights_call_headline = _tonights_call_headline(conn, as_of)

    conn.execute("DELETE FROM armed_list WHERE armed_date = ?", (as_of,))
    armed_count = 0
    for card in digest:
        atr20 = None
        try:
            from manas_os.scanner import screener as scanner_screener
            m = scanner_screener.metrics_for_symbol(conn, card.get("symbol"), as_of)
            if m is not None:
                atr20 = m.get("atr20")
        except Exception:  # noqa: BLE001 -- zone falls back to pct approximation
            atr20 = None
        zlo, zhi = zone_from_plan(card.get("entry"), atr20)
        conn.execute(
            "INSERT OR REPLACE INTO armed_list "
            "(armed_date, symbol, trigger, stop, qty, setup_family, rank, ttl_date, zone_low, zone_high) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                as_of,
                card.get("symbol"),
                card.get("entry"),
                card.get("stop"),
                card.get("suggested_qty"),
                card.get("setup_family"),
                card.get("rank"),
                ttl_date,
                zlo,
                zhi,
            ),
        )
        armed_count += 1

    summary = (
        f"{market_mode} digest: {len(digest)} armed candidate"
        f"{'' if len(digest) == 1 else 's'} and {refused} names refused"
    )
    watchlist = _watchlist_section(conn, as_of)

    return {
        "as_of": as_of,
        "market_mode": market_mode,
        "summary": summary,
        "refusal_count": refused,
        "cap": cap,
        "digest": digest,
        "armed_count": armed_count,
        "watchlist": watchlist,
        "tonights_call_headline": tonights_call_headline,
    }


def render_digest_message(digest: dict[str, Any]) -> str:
    """Render the single nightly Telegram message. SHIP-2 finding 3: the
    message opens with the desk's TONIGHT'S CALL stance headline, so the
    first line answers "so what do I do" before any of the detail rows."""
    rows = []
    if digest.get("tonights_call_headline"):
        rows.append(digest["tonights_call_headline"])
    rows.extend([
        f"Manas armed list | {digest['as_of']} | {digest['market_mode']}",
        f"Armed: {digest['armed_count']}/{digest['cap']}",
        f"Refusals: {digest['refusal_count']}",
    ])
    if not digest["digest"]:
        rows.extend(["", "No armed candidates."])
    else:
        rows.append("")
        for idx, card in enumerate(digest["digest"], start=1):
            rows.append(
                f"{idx}. {card.get('symbol')} | {card.get('setup_family') or card.get('setup_type') or 'setup'} "
                f"| trigger {card.get('entry')} | stop {card.get('stop')} | qty {card.get('suggested_qty')}"
            )

    rows.extend(_render_watchlist_section(digest.get("watchlist")))
    return "\n".join(rows)


def _render_watchlist_section(watchlist: dict[str, Any] | None) -> list[str]:
    """SHIP-1 #10: append the watchlist section to the nightly digest —
    PROMOTE/DEMOTE lines plus a hard-near-miss count. Omitted entirely
    when there is nothing to report (no watchlist rows tonight)."""
    if not watchlist:
        return []
    promotions = watchlist.get("promotions") or []
    demotions = watchlist.get("demotions") or []
    near_miss_hard_count = watchlist.get("near_miss_hard_count") or 0
    if not promotions and not demotions and not near_miss_hard_count:
        return []
    out = ["", "Watchlist:"]
    for r in promotions:
        out.append(f"PROMOTE {r.get('symbol')} — {r.get('reason')}")
    for r in demotions:
        out.append(f"DEMOTE {r.get('symbol')} — {r.get('reason')}")
    out.append(f"Hard near-misses: {near_miss_hard_count}")
    return out


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
    now: str | None = None,
) -> dict[str, Any]:
    """Build, render, and pipeline-log one nightly digest; deliver it through
    the transactional outbox.

    RELIABILITY_AUDIT_2026-07-19 #8: this used to send over the network
    BEFORE the pipeline_runs commit below -- a crash after a successful send
    but before that commit meant the next retry would rebuild and re-send
    the same digest (armed_list rebuild is replay-safe; the Telegram send
    was not). Fixed by enqueueing the digest into the outbox in the SAME
    transaction as the armed_list rebuild and the pipeline_runs 'ok' row (a
    crash before that commit now means NONE of it happened -- nothing to
    duplicate), and only attempting delivery after that commit. A send
    failure at that point is therefore purely a retryable outbox concern: it
    does not roll back the (already-committed, already-idempotent) digest
    build, so the pipeline stage still reports 'ok'.
    """
    started = time.monotonic()
    try:
        ensure_schema(conn)
        outbox.ensure_schema(conn)
        result = build_digest(conn, run_date)
        message = render_digest_message(result)
        cfg = _telegram_config()
        is_dry_run = cfg["dry_run"] if dry_run is None else bool(dry_run)
        alert_key = f"telegram_digest:{result['as_of']}"
        outbox.enqueue(conn, alert_key, "telegram_digest", {"message": message, "as_of": result["as_of"]})
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
        # Everything above -- armed_list rebuild, outbox enqueue, pipeline_runs
        # 'ok' row -- commits together, atomically. Delivery is attempted only
        # after this point.
        conn.commit()

        live_sender = sender or _telegram_sender
        send_fn = outbox.dry_run_or_live_sender(dry_run=is_dry_run, live_sender=live_sender)
        deliver = outbox.deliver_pending(conn, send_fn, now=now)
        sent = alert_key in deliver["delivered"]
        return {
            "status": "ok",
            "armed_count": result["armed_count"],
            "sent": sent,
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
