"""Replayable intraday alert FSM for the Telegram armed-list workflow (T4.1).

Originally the W4.1 harness-first slice ("no WebSocket, no Telegram network,
no credentials"). Extended here (Task #21 Stage 1) to the full binding
architecture in manas_os/design/LIVE_LOOP_FABLE.md §2.2-§2.3: the
TRIGGERED -> ALERTED step now gates on the live-confirmation bundle (price
clears trigger + first-15m holds OR-low/VWAP + gap-fill <=33% + projected
RVOL >=2), on the per-day regime push cap, and on the /halt kill-switch;
CONFIRM_PENDING -> CONFIRMED is now a genuine revalidation (outside the
pre-committed zone -> EXPIRED_MOVED, refuse); ALERTED emits a paper-gated
Telegram push. Still no WebSocket/network here -- manas_os.live.session owns
that and calls the same on_tick/on_confirm functions this module exposes.

Idempotency: a transition is only ever recorded once per
(trade_date, symbol, setup_id, to_state, event_ts, event_type) (UNIQUE index
on live_fsm_transitions), and `_transition()` additionally refuses to fire
out of a terminal state or into the state a row already holds. Replaying an
identical event list a second time therefore creates zero new transitions
and zero new Telegram pushes (record_push's own dedup is a second,
independent belt-and-suspenders layer on top).
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from manas_os import config
from manas_os.alerts import replies as telegram_replies
from manas_os.alerts import telegram_engine
from manas_os.live import confirmation, telegram_paper

DEFAULT_TTL_MINUTES = 25
DEFAULT_ZONE_PCT = 0.006  # 0.6% above trigger -- see docstring on `_zone_bounds`

TERMINAL_STATES = {"CONFIRMED", "EXPIRED", "EXPIRED_MOVED"}
ACTIVE_ALERT_STATES = {"ALERTED", "CONFIRMED_15M", "CONFIRM_PENDING"}


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
    # In-place migration for DBs created before Stage 1 (mirrors db.py's own
    # ALTER-guarded-by-pragma-check convention) -- zone bounds are new.
    have = {r[1] for r in conn.execute("PRAGMA table_info(live_fsm_state)")}
    if "zone_lo" not in have:
        conn.execute("ALTER TABLE live_fsm_state ADD COLUMN zone_lo REAL")
    if "zone_hi" not in have:
        conn.execute("ALTER TABLE live_fsm_state ADD COLUMN zone_hi REAL")


def _zone_bounds(trigger: float) -> tuple[float, float]:
    """Fallback when armed_list has no persisted zone_low/zone_high.

    Prefer persisted bounds at arm time (pivot → pivot+0.5*ATR20). When
    missing (legacy rows), use trigger → trigger*(1+zone_pct) with
    live.zone_pct default 0.6%.
    """
    zone_pct = float(config.get("live.zone_pct", DEFAULT_ZONE_PCT))
    return float(trigger), float(trigger) * (1 + zone_pct)


def arm_from_armed_list(conn, armed_date: str, ttl_minutes: int = DEFAULT_TTL_MINUTES) -> int:
    """Create ARMED FSM rows from the deterministic C14 armed_list.

    One-writer rule: trigger/stop/qty/zone are copied verbatim from armed_list
    (alerts.telegram_engine.build_digest -- the single writer); this never
    recomputes risk. Existing rows are left untouched, making arm/replay
    idempotent.
    """
    ensure_schema(conn)
    telegram_engine.ensure_schema(conn)  # armed_list lives in telegram_engine's schema
    rows = conn.execute(
        "SELECT symbol, trigger, stop, qty, setup_family, rank, zone_low, zone_high "
        "FROM armed_list WHERE armed_date = ? ORDER BY rank, symbol",
        (armed_date,),
    ).fetchall()
    created = 0
    for row in rows:
        setup_id = _setup_id(row)
        # Prefer persisted arm-time zone; fall back to pct approximation.
        if row["zone_low"] is not None and row["zone_high"] is not None:
            zone_lo, zone_hi = float(row["zone_low"]), float(row["zone_high"])
        elif row["trigger"] is not None:
            zone_lo, zone_hi = _zone_bounds(row["trigger"])
        else:
            zone_lo, zone_hi = None, None
        cur = conn.execute(
            "INSERT OR IGNORE INTO live_fsm_state "
            "(trade_date, symbol, setup_id, state, trigger, stop, qty, setup_family, rank, "
            "ttl_minutes, zone_lo, zone_hi) "
            "VALUES (?, ?, ?, 'ARMED', ?, ?, ?, ?, ?, ?, ?, ?)",
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
                zone_lo,
                zone_hi,
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


def alerted_count_today(conn, trade_date: str) -> int:
    """Count of distinct (symbol, setup_id) rows that have ever reached
    ALERTED today -- the regime push-cap denominator (DIGEST_CAPS)."""
    row = conn.execute(
        "SELECT COUNT(DISTINCT symbol || ':' || setup_id) AS n FROM live_fsm_transitions "
        "WHERE trade_date = ? AND to_state = 'ALERTED'",
        (trade_date,),
    ).fetchone()
    return int(row["n"] or 0)


def on_tick(conn, trade_date: str, event: dict[str, Any], *, regime_mode: str = "SELECTIVE",
            sender=None) -> dict[str, Any]:
    """Feed one tick/bar-close event through ARMED->TRIGGERED->ALERTED.

    `event` carries: symbol, ts, price, and (only needed once price has
    cleared the trigger) the live-confirmation bundle fields
    in_first_15m_complete / holds_or_low_vwap / gap_fill_pct / rvol_projected
    (see manas_os.live.confirmation). Missing bundle fields simply fail the
    gate (stay TRIGGERED) rather than defaulting to pass -- the safe
    direction for a beginner-safety system.
    """
    ensure_schema(conn)
    symbol = str(event["symbol"]).upper()
    price = float(event["price"])
    event_ts = event["ts"]
    row = _row(conn, trade_date, symbol)
    if not row:
        # Lazy-arm: on_tick/on_confirm are also called directly (not only via
        # replay_events), e.g. by manas_os.live.session against a live feed.
        # arm_from_armed_list is INSERT OR IGNORE + idempotent, so calling it
        # here on a cache-miss just materializes the ARMED row from the
        # locked armed_list (one-writer rule preserved -- nothing here
        # recomputes trigger/stop/qty) instead of forcing every caller to
        # remember to arm first.
        arm_from_armed_list(conn, trade_date)
        row = _row(conn, trade_date, symbol)
    if not row or row["state"] in TERMINAL_STATES:
        return {"applied": False, "reason": "terminal_or_not_armed", "symbol": symbol}
    if not _is_newer_bar(row, event_ts):
        return {"applied": False, "reason": "stale_bar_ts", "symbol": symbol}

    conn.execute(
        "UPDATE live_fsm_state SET last_bar_ts = ?, updated_at = datetime('now') "
        "WHERE trade_date = ? AND symbol = ? AND setup_id = ?",
        (event_ts, trade_date, symbol, row["setup_id"]),
    )
    conn.commit()

    if row["state"] == "ARMED":
        if row["trigger"] is None:
            return {"applied": False, "reason": "no_trigger", "symbol": symbol}

        is_busted = row["setup_family"] in ("busted", "busted_reversal")
        if is_busted:
            if price < float(row["trigger"]):
                applied = _transition(conn, row, "BUSTED", event_ts, "tick", price, "dropped below trigger (busted)")
                return {"applied": applied, "to_state": "BUSTED" if applied else None, "symbol": symbol}
            return {"applied": False, "reason": "above_trigger", "symbol": symbol}

        if price < float(row["trigger"]):
            return {"applied": False, "reason": "below_trigger", "symbol": symbol}

        applied = _transition(conn, row, "TRIGGERED", event_ts, "tick", price, "trigger crossed")
        if not applied:
            return {"applied": False, "to_state": None, "symbol": symbol}
        # Same-tick chaining: a bar can cross the trigger AND already carry a
        # passing live-confirmation bundle (the replay/backtest harness feeds
        # one enriched bar per event). Attempt the TRIGGERED->ALERTED gate
        # immediately; if it doesn't clear (bundle missing/failing, halted,
        # capped) that's not an error -- just report the trigger-cross that
        # did happen, per test_trigger_cross_alone_does_not_alert_without_confirmation_bundle.
        refreshed = _row(conn, trade_date, symbol, row["setup_id"])
        follow = _process_triggered(conn, trade_date, refreshed, event, event_ts, price, regime_mode, sender)
        if follow["applied"]:
            return follow
        return {"applied": True, "to_state": "TRIGGERED", "symbol": symbol}

    if row["state"] == "BUSTED":
        if row["trigger"] is not None and price >= float(row["trigger"]):
            busted_ts = conn.execute(
                "SELECT event_ts FROM live_fsm_transitions WHERE trade_date = ? AND symbol = ? AND setup_id = ? AND to_state = 'BUSTED' ORDER BY transition_id DESC LIMIT 1",
                (trade_date, symbol, row["setup_id"])
            ).fetchone()["event_ts"]

            if (_dt(event_ts) - _dt(busted_ts)).total_seconds() <= 45 * 60:
                applied = _transition(conn, row, "TRIGGERED", event_ts, "tick", price, "reclaimed trigger within 45m")
                if not applied:
                    return {"applied": False, "to_state": None, "symbol": symbol}
                refreshed = _row(conn, trade_date, symbol, row["setup_id"])
                follow = _process_triggered(conn, trade_date, refreshed, event, event_ts, price, regime_mode, sender)
                if follow["applied"]:
                    return follow
                return {"applied": True, "to_state": "TRIGGERED", "symbol": symbol}
            else:
                applied = _transition(conn, row, "EXPIRED", event_ts, "tick", price, "reclaim took longer than 45m")
                return {"applied": applied, "to_state": "EXPIRED" if applied else None, "symbol": symbol}
        return {"applied": False, "reason": "below_trigger", "symbol": symbol}

    if row["state"] == "TRIGGERED":
        return _process_triggered(conn, trade_date, row, event, event_ts, price, regime_mode, sender)

    if row["state"] in ("ALERTED", "CONFIRMED_15M"):
        zone_hi = row["zone_hi"]
        if zone_hi is not None and price > zone_hi:
            applied = _transition(conn, row, "EXPIRED", event_ts, "tick", price, "moved_out_of_zone")
            return {"applied": applied, "to_state": "EXPIRED" if applied else None, "symbol": symbol}

        if row["state"] == "ALERTED" and row["setup_family"] in ("strong_start", "strong_start_ready"):
            # Strong Start early-triggers at 2-3 minutes. This state upgrade happens when the first 15m completes.
            ok, _ = confirmation.live_confirmation_ok(event)  # default no setup_family = strict 15m requirement
            if ok:
                applied = _transition(conn, row, "CONFIRMED_15M", event_ts, "tick", price, "15m confirmation passed")
                return {"applied": applied, "to_state": "CONFIRMED_15M" if applied else None, "symbol": symbol}

        return {"applied": False, "reason": "awaiting_confirm", "symbol": symbol}

    return {"applied": False, "reason": f"unhandled_state_{row['state']}", "symbol": symbol}


def _process_triggered(conn, trade_date: str, row, event: dict[str, Any], event_ts: str, price: float,
                        regime_mode: str, sender) -> dict[str, Any]:
    """TRIGGERED -> ALERTED gate: zone check, live-confirmation bundle,
    /halt kill-switch, per-day regime push cap. Shared by the TRIGGERED
    branch of on_tick and the same-tick ARMED->TRIGGERED->ALERTED chain."""
    symbol = row["symbol"]
    zone_hi = row["zone_hi"]
    if zone_hi is not None and price > zone_hi:
        applied = _transition(conn, row, "EXPIRED", event_ts, "tick", price, "moved_out_of_zone")
        return {"applied": applied, "to_state": "EXPIRED" if applied else None, "symbol": symbol}

    ok, reason = confirmation.live_confirmation_ok(event, setup_family=row["setup_family"])
    if not ok:
        return {"applied": False, "reason": reason, "symbol": symbol}
    if telegram_replies.entries_halted(conn):
        return {"applied": False, "reason": "entries_halted", "symbol": symbol}
    cap = telegram_engine.DIGEST_CAPS.get(regime_mode, 0)
    if alerted_count_today(conn, trade_date) >= cap:
        return {"applied": False, "reason": "regime_cap_reached", "symbol": symbol}

    applied = _transition(conn, row, "ALERTED", event_ts, "tick", price, "live confirmation passed", alert=True)
    if not applied:
        return {"applied": False, "reason": "duplicate_alert", "symbol": symbol}
    refreshed = _row(conn, trade_date, symbol, row["setup_id"])
    push = telegram_paper.push_entry_alert(conn, trade_date, symbol, dict(refreshed), event, sender=sender)
    return {"applied": True, "to_state": "ALERTED", "symbol": symbol, "push": push}


def on_confirm(conn, trade_date: str, event: dict[str, Any]) -> dict[str, Any]:
    """Confirm = revalidation (LIVE_LOOP_FABLE §2.3, the core fix): re-check
    the LTP *at confirm time* against the pre-committed zone. Outside the
    zone -> refuse (EXPIRED_MOVED), never journal the plan."""
    ensure_schema(conn)
    symbol = str(event["symbol"]).upper()
    price = float(event.get("price") or 0)
    event_ts = event["ts"]
    row = _row(conn, trade_date, symbol)
    if not row:
        arm_from_armed_list(conn, trade_date)
        row = _row(conn, trade_date, symbol)
    if not row or row["state"] in TERMINAL_STATES:
        return {"ok": False, "reason": "terminal_or_not_found", "symbol": symbol}
    if row["state"] not in ("ALERTED", "CONFIRMED_15M"):
        return {"ok": False, "reason": f"cannot_confirm_from_{row['state']}", "symbol": symbol}

    entered = _transition(conn, row, "CONFIRM_PENDING", event_ts, "confirm", price, "user confirmation received")
    if not entered:
        return {"ok": False, "reason": "duplicate_confirm_request", "symbol": symbol}
    refreshed = _row(conn, trade_date, symbol, row["setup_id"])

    if confirmation.in_zone(price, refreshed["zone_lo"], refreshed["zone_hi"]):
        _transition(conn, refreshed, "CONFIRMED", event_ts, "confirm", price, "revalidation passed")
        return {"ok": True, "state": "CONFIRMED", "symbol": symbol, "price": price}

    _transition(conn, refreshed, "EXPIRED_MOVED", event_ts, "confirm", price, "outside_zone_at_confirm")
    return {
        "ok": False, "reason": "outside_zone", "state": "EXPIRED_MOVED", "symbol": symbol,
        "price": price, "zone_lo": refreshed["zone_lo"], "zone_hi": refreshed["zone_hi"],
    }


def expire_due(conn, trade_date: str, event_ts: str, force: bool = False) -> None:
    rows = conn.execute(
        "SELECT * FROM live_fsm_state WHERE trade_date = ? AND state IN ('ALERTED', 'CONFIRMED_15M', 'CONFIRM_PENDING')",
        (trade_date,),
    ).fetchall()
    now = _dt(event_ts)
    for row in rows:
        expires_at = row["expires_at"]
        if force or (expires_at and now >= _dt(expires_at)):
            _transition(conn, row, "EXPIRED", event_ts, "expire", None, "alert TTL expired")


def replay_events(conn, armed_date: str, events: list[dict[str, Any]], ttl_minutes: int = DEFAULT_TTL_MINUTES,
                   *, regime_mode: str = "SELECTIVE") -> dict[str, Any]:
    """Batch convenience wrapper over on_tick/on_confirm/expire_due -- drives
    mocked/replayed events through the FSM in ts order.

    Events are dicts:
    - tick: {"type": "tick", "symbol": "ABC", "ts": "...", "price": 101,
             "in_first_15m_complete": bool, "holds_or_low_vwap": bool,
             "gap_fill_pct": float, "rvol_projected": float}
    - confirm: {"type": "confirm", "symbol": "ABC", "ts": "...", "price": 101}
    - expire: {"type": "expire", "ts": "..."} to advance the virtual clock.
    """
    ensure_schema(conn)
    created = arm_from_armed_list(conn, armed_date, ttl_minutes=ttl_minutes)
    before = _transition_count(conn)
    for event in sorted(events, key=lambda e: e["ts"]):
        expire_due(conn, armed_date, event["ts"])
        kind = str(event.get("type") or "tick").lower()
        if kind == "tick":
            on_tick(conn, armed_date, event, regime_mode=regime_mode)
        elif kind == "confirm":
            on_confirm(conn, armed_date, event)
        elif kind == "expire":
            expire_due(conn, armed_date, event["ts"], force=True)
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


def _transition(conn, row, to_state: str, event_ts: str, event_type: str, price: float | None, detail: str,
                 alert: bool = False) -> bool:
    if row is None:
        return False
    if row["state"] == to_state or row["state"] in TERMINAL_STATES:
        return False
    from_state = row["state"]
    expires_at = row["expires_at"]
    alerted_at = row["alerted_at"]
    alert_count = int(row["alert_count"] or 0)
    paper_mode = 0 if telegram_paper.live_send_authorized() else 1
    if to_state == "ALERTED":
        alerted_at = event_ts
        expires_at = (_dt(event_ts) + timedelta(minutes=int(row["ttl_minutes"] or DEFAULT_TTL_MINUTES))).isoformat(timespec="minutes")
    if alert:
        alert_count += 1
    recorded = _record_transition(conn, row["trade_date"], row["symbol"], row["setup_id"], from_state, to_state,
                                   event_ts, event_type, price, detail)
    if not recorded:
        return False
    conn.execute(
        "UPDATE live_fsm_state SET state = ?, alerted_at = ?, expires_at = ?, "
        "alert_count = ?, paper_mode = ?, updated_at = datetime('now') "
        "WHERE trade_date = ? AND symbol = ? AND setup_id = ?",
        (to_state, alerted_at, expires_at, alert_count, paper_mode,
         row["trade_date"], row["symbol"], row["setup_id"]),
    )
    conn.commit()
    return True


def _record_transition(conn, trade_date: str, symbol: str, setup_id: str, from_state: str | None,
                        to_state: str, event_ts: str, event_type: str, price: float | None, detail: str) -> bool:
    cur = conn.execute(
        "INSERT OR IGNORE INTO live_fsm_transitions "
        "(trade_date, symbol, setup_id, from_state, to_state, event_ts, event_type, price, detail) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (trade_date, symbol, setup_id, from_state, to_state, event_ts, event_type, price, detail),
    )
    return bool(cur.rowcount)


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
