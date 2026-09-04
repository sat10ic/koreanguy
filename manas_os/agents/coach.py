"""Journal coach agent for open positions.

The deterministic exit engine is the one writer for position action. The LLM
only narrates that read; if it is unavailable, deterministic coach signals
still persist.
"""
from __future__ import annotations

import json
import time
from datetime import date as _date
from pathlib import Path
from typing import Any, Callable

from manas_os import config, market_calendar
from manas_os.advisor.client import OpenRouterClient
from manas_os.agents import _shared, lessons, run_card, signals
from manas_os.agents.context_pack import INDIA_STRUCTURE_PRIMER
from manas_os.alerts import outbox, telegram_engine
from manas_os.engine import eod_detectors

COACH_LINES_PATH = (
    Path(__file__).resolve().parent.parent / "design" / "agents" / "COACH_LINES.md"
)
_COACH_LINES_CACHE: dict[str, list[str]] | None = None
MAX_COACH_LINES = 2

STAGE = "agents_coach"
SOURCE = "journal_trades"
CHANNEL = "coach"
AGENT = "coach"
NET_COSTS_NOTE = (
    "Report thinking in NET terms: STT, GST, brokerage, and slippage drag small accounts; "
    "do not narrate gross R as if costs are zero."
)


def _api_key() -> str | None:
    return _shared.api_key()


def _models() -> list[str]:
    coach_model = config.get("agents.coach_model")
    if isinstance(coach_model, str) and coach_model.strip():
        return [coach_model.strip()]
    return _shared.models()


def _pipeline_log(conn, run_date: str, status: str, rows: int, started: float, detail: str) -> None:
    conn.execute(
        "INSERT INTO pipeline_runs (run_date, stage, source, status, rows_affected, "
        "duration_s, detail) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (run_date, STAGE, SOURCE, status, rows, round(time.monotonic() - started, 3), detail),
    )


def _agent_log(conn, run_date: str, parsed_ok: bool, validation: str, error: str | None = None, model: str | None = None) -> None:
    conn.execute(
        "INSERT INTO scan_agent_logs "
        "(run_date, agent, model, prompt_sha, latency_ms, parsed_ok, validation, error) "
        "VALUES (?, ?, ?, NULL, NULL, ?, ?, ?)",
        (run_date, AGENT, model, 1 if parsed_ok else 0, validation, error),
    )


def _load_symbol_bars(conn, symbol: str, on_or_before: str, limit: int = 80) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT trade_date AS date, open, high, low, close, prev_close, volume, "
        "delivery_qty, delivery_pct "
        "FROM daily_prices WHERE symbol = ? AND series = 'EQ' AND trade_date <= ? "
        "ORDER BY trade_date DESC LIMIT ?",
        (symbol.upper(), on_or_before, limit),
    ).fetchall()
    return [dict(r) for r in reversed(rows)]


def _setup_family_for_trade(trade_row) -> str:
    setup_name = str(trade_row["setup"] or "").lower()
    return "catalyst" if setup_name in {"ep", "ipo_base"} or "ep" in setup_name else "base/pattern"


def _plain_action_line(trade_row, trail: dict[str, Any], strikes: dict[str, Any]) -> str:
    phase = trail.get("phase")
    trail_stop = trail.get("trail_stop")
    fired = strikes.get("fired") or []
    if strikes.get("exit_now"):
        return (
            f"EXIT TODAY - {len(fired)} exit rules fired ({', '.join(fired)}). "
            "Sell the full position near the close."
        )
    if phase == "TREND":
        ema_name = "EMA10" if "EMA10" in str(trail.get("action", "")) else "EMA21"
        return f"HOLD - trailing {ema_name} (now {trail_stop}). You're +{trail.get('r')}R."
    if phase == "EXTENSION":
        return f"TRIM 25-33% into strength; tighten stop to the 2-bar low ({trail_stop})."
    return (
        f"HOLD - do nothing. Stop stays at {trade_row['stop']}. "
        "Wobble in the first few days is normal; the trade isn't wrong until the stop breaks."
    )


def _exit_timing_phrase(as_of: str | None) -> str:
    """Calendar-aware timing for the EXIT sentence (DEFECT 8, cold-start
    audit): 'EXIT today near the close (15:00-15:25)' rendered even when
    `as_of` (the card's run_date) is a Sunday/holiday -- there is no
    15:00-15:25 session to sell into "today" on a non-trading day. When
    `as_of` is given and is NOT a trading day, name the next actual trading
    day instead; otherwise (as_of omitted, or as_of is itself a trading
    day -- including intraday pre-open) keep the original 'today' wording."""
    if as_of:
        try:
            d = _date.fromisoformat(as_of)
        except ValueError:
            d = None
        if d is not None and not market_calendar.is_trading_day(d):
            nxt = market_calendar.next_trading_day(d)
            return f"on {nxt.strftime('%A %d %b')} near the close (15:00-15:25)"
    return "today near the close (15:00-15:25)"


def compose_action_sentence(
    verdict: str,
    trail: dict[str, Any],
    strikes: dict[str, Any],
    *,
    stop: float,
    r: float | None = None,
    account_label: str | None = None,
    as_of: str | None = None,
) -> str:
    """The single writer for a position's MANAGE-card action sentence --
    verdict, timing, and method in one string, so the badge word and the
    prose beside it can never disagree about WHEN or HOW to act.

    USABILITY_UX_AUDIT_2026-07-19.md defect #4: the MANAGE card badge read
    'EXIT NOW' while a separate coach line said 'near the close' -- two
    independent timing instructions for a beginner who is already the most
    likely to hesitate. Every reader of an exit/hold/trim/move-stop
    instruction for /api/desk/positions -- journaled positions
    (_deterministic_read below) and Zerodha-imported assigned-stop holdings
    (api/app.py _imported_holding_position_row) -- must go through this
    function for that text, and only this function.

    Deliberately NOT used for the Telegram coach message
    (_plain_action_line / _render_message below): that text is owned by the
    outbox lane and is left untouched by this change.

    `verdict` is the same word the caller renders in the badge; the
    sentence always leads with it (or, for an exit, opens on 'EXIT') so
    prose and badge cannot drift apart.
    """
    phase = trail.get("phase")
    trail_stop = trail.get("trail_stop")
    fired = strikes.get("fired") or []
    ema_name = "EMA10" if "EMA10" in str(trail.get("action", "")) else "EMA21"
    account_suffix = f" in your {account_label} account" if account_label else ""

    if strikes.get("exit_now"):
        n = len(fired)
        if fired:
            rule_word = "rule" if n == 1 else "rules"
            reason = f"{n} exit {rule_word} fired ({', '.join(fired)})"
        else:
            reason = "the two-strike rule fired"
        return (
            f"EXIT {_exit_timing_phrase(as_of)} - sell the full "
            f"position at market{account_suffix}. {reason}."
        )
    if verdict == "MOVE_STOP":
        return (
            f"MOVE STOP today to {trail_stop} (trailing {ema_name}){account_suffix} - "
            "this manages the tool-assigned stop; no exit action needed."
        )
    if verdict == "TRIM":
        return (
            f"TRIM today - sell 25-33% into strength{account_suffix}; tighten "
            f"the stop to the 2-bar low ({trail_stop})."
        )
    if phase == "TREND":
        r_text = f" You're +{r}R." if r is not None else ""
        return (
            f"HOLD today - trail stop moves to {trail_stop} (trailing {ema_name})"
            f"{account_suffix}; no action needed.{r_text}"
        )
    return (
        f"HOLD today - do nothing; stop stays at {stop}{account_suffix}. "
        "Wobble in the first few days is normal; the trade isn't wrong until the stop breaks."
    )


def _trading_sessions_since(flag_date: str | None, as_of: str) -> int:
    if not flag_date:
        return 0
    try:
        start = _date.fromisoformat(flag_date)
        end = _date.fromisoformat(as_of)
    except ValueError:
        return 0
    if end <= start:
        return 0
    return market_calendar.trading_days_between(start, end) + (1 if market_calendar.is_trading_day(end) else 0)


def _open_trades(conn) -> list[Any]:
    have = {r[1] for r in conn.execute("PRAGMA table_info(journal_trades)")}
    qty_select = "qty" if "qty" in have else "NULL AS qty"
    return conn.execute(
        f"SELECT trade_id, trade_date, symbol, setup, entry, stop, {qty_select}, first_exit_flag_date "
        "FROM journal_trades WHERE exit IS NULL ORDER BY trade_date DESC, trade_id DESC"
    ).fetchall()


def _latest_thesis_date(conn, symbol: str, trade_date: str) -> str | None:
    row = conn.execute(
        "SELECT MAX(scan_date) AS d FROM agent_verdicts WHERE symbol = ? AND scan_date <= ?",
        (symbol, trade_date),
    ).fetchone()
    return str(row["d"]) if row and row["d"] else None


def _original_thesis(conn, symbol: str, trade_date: str) -> dict[str, Any]:
    scan_date = _latest_thesis_date(conn, symbol, trade_date)
    if not scan_date:
        return {"note": "no agent thesis"}
    rows = conn.execute(
        "SELECT agent, verdict, conviction, bull_case, bear_case, reasoning "
        "FROM agent_verdicts WHERE scan_date = ? AND symbol = ? "
        "AND agent NOT IN ('sizer', 'vision') "
        "ORDER BY CASE WHEN agent = 'chair' THEN 0 ELSE 1 END, COALESCE(conviction, 0) DESC, agent",
        (scan_date, symbol),
    ).fetchall()
    if not rows:
        return {"note": "no agent thesis"}
    return {"scan_date": scan_date, "rows": [dict(r) for r in rows]}


def _deterministic_read(conn, trade_row, run_date: str) -> dict[str, Any] | None:
    if trade_row["entry"] is None or trade_row["stop"] is None:
        return None
    bars = _load_symbol_bars(conn, trade_row["symbol"], run_date, 80)
    if not bars:
        return None
    setup_family = _setup_family_for_trade(trade_row)
    trail = eod_detectors.trail_plan(
        bars,
        float(trade_row["entry"]),
        float(trade_row["stop"]),
        setup_family,
    )
    strikes = eod_detectors.two_strike(bars, float(trade_row["stop"]))
    verdict = {"INITIATION": "HOLD", "TREND": "HOLD", "EXTENSION": "TRIM"}.get(
        trail.get("phase"), "HOLD"
    )
    if strikes.get("exit_now"):
        verdict = "EXIT"
    first_flag = trade_row["first_exit_flag_date"] if "first_exit_flag_date" in trade_row.keys() else None
    banner = None
    if strikes.get("exit_now") and not first_flag:
        first_flag = run_date
        conn.execute(
            "UPDATE journal_trades SET first_exit_flag_date = ? WHERE trade_id = ?",
            (run_date, trade_row["trade_id"]),
        )
    elif not strikes.get("exit_now") and first_flag:
        first_flag = None
        conn.execute(
            "UPDATE journal_trades SET first_exit_flag_date = NULL WHERE trade_id = ?",
            (trade_row["trade_id"],),
        )
    if strikes.get("exit_now") and first_flag:
        sessions = _trading_sessions_since(first_flag, run_date)
        if sessions >= 2:
            banner = f"OVERDUE EXIT - flagged {sessions} sessions ago, still open"
    close = bars[-1].get("close")
    return {
        "trade_id": trade_row["trade_id"],
        "symbol": str(trade_row["symbol"]).upper(),
        "trade_date": trade_row["trade_date"],
        "setup": trade_row["setup"],
        "setup_family": setup_family,
        "close": close,
        "phase": trail.get("phase"),
        "verdict": verdict,
        "action": trail.get("action"),
        "trail_stop": trail.get("trail_stop"),
        "r": trail.get("r"),
        "why": trail.get("why", []),
        "fired": strikes.get("fired", []),
        "exit_now": bool(strikes.get("exit_now")),
        "banner": banner,
        "action_line": _plain_action_line(trade_row, trail, strikes),
        # Single-writer MANAGE-card sentence (verdict+timing+method) -- see
        # compose_action_sentence above. Distinct from action_line, which
        # still feeds the Telegram coach message and is left untouched.
        "action_sentence": compose_action_sentence(
            verdict, trail, strikes, stop=trade_row["stop"], r=trail.get("r"), as_of=run_date
        ),
        "original_thesis": _original_thesis(conn, str(trade_row["symbol"]).upper(), trade_row["trade_date"]),
    }


def _system_prompt() -> str:
    return (
        "You are the Manas OS journal coach. The deterministic exit engine owns the action. "
        "Never override, weaken, or contradict deterministic verdict/action/trail_stop/two-strike output. "
        "Only narrate it against the original thesis.\n\n"
        "Return only JSON: an array of objects with symbol, stance (agree, urgent, or note), "
        "and message (<=3 sentences quoting the original thesis). No markdown."
    )


def _user_prompt(positions: list[dict[str, Any]]) -> str:
    return json.dumps(
        {
            "run_date": positions[0].get("run_date") if positions else None,
            "india_structure_primer": INDIA_STRUCTURE_PRIMER,
            "net_costs_note": NET_COSTS_NOTE,
            "positions": positions,
        },
        indent=2,
        sort_keys=True,
        default=str,
    )


def _extract_json(raw: str) -> Any:
    text = (raw or "").strip()
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0].strip()
    return json.loads(text)


def _parse_narratives(raw: str, symbols: set[str]) -> dict[str, dict[str, str]]:
    payload = _extract_json(raw)
    if isinstance(payload, dict) and isinstance(payload.get("positions"), list):
        payload = payload["positions"]
    if not isinstance(payload, list):
        raise ValueError("coach JSON must be an array")
    out: dict[str, dict[str, str]] = {}
    for item in payload:
        if not isinstance(item, dict):
            continue
        symbol = str(item.get("symbol") or "").upper().strip()
        if symbol not in symbols:
            continue
        stance = str(item.get("stance") or "note").lower().strip()
        if stance not in {"agree", "urgent", "note"}:
            stance = "note"
        message = " ".join(str(item.get("message") or "").split())
        if message:
            out[symbol] = {"stance": stance, "message": message}
    return out


def _chat(llm: Any, system: str, user: str) -> Any:
    return _shared.chat_with_usage(llm, system, user)


def _unpack_chat(result: Any, default_model: str) -> tuple[str, str]:
    raw, used_model, _usage = _shared.unpack_chat(result, default_model)
    return raw, used_model


def _load_narratives(positions: list[dict[str, Any]], client: Any | None) -> tuple[dict[str, dict[str, str]], str | None, str | None]:
    key = _api_key()
    if client is None and not key:
        return {}, None, "coach llm config/api key absent"
    model = _models()[0]
    llm = client or OpenRouterClient(api_key=key, model=model, max_tokens=int(config.get("agents.max_tokens", 2000) or 2000))
    raw, used_model = _unpack_chat(_chat(llm, _system_prompt(), _user_prompt(positions)), model)
    symbols = {str(p["symbol"]).upper() for p in positions}
    return _parse_narratives(raw, symbols), used_model, None


def _parse_coach_lines_bank(text: str) -> dict[str, list[str]]:
    """Parse COACH_LINES.md into {situation-key: [line, ...]}. Deterministic, no LLM."""
    bank: dict[str, list[str]] = {}
    current_key: str | None = None
    current_bullet: list[str] = []

    def _flush() -> None:
        if current_key is not None and current_bullet:
            bank.setdefault(current_key, []).append(" ".join(current_bullet).strip())

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if line.startswith("## "):
            _flush()
            current_bullet = []
            current_key = line[3:].strip().lower()
            bank.setdefault(current_key, [])
        elif line.startswith("- "):
            _flush()
            current_bullet = [line[2:].strip()]
        elif not line.strip():
            _flush()
            current_bullet = []
        elif current_bullet:
            current_bullet.append(line.strip())
    _flush()
    return bank


def _coach_lines_bank() -> dict[str, list[str]]:
    global _COACH_LINES_CACHE
    if _COACH_LINES_CACHE is None:
        try:
            text = COACH_LINES_PATH.read_text(encoding="utf-8")
        except OSError:
            text = ""
        _COACH_LINES_CACHE = _parse_coach_lines_bank(text)
    return _COACH_LINES_CACHE


def _situation_keys_for_position(position: dict[str, Any]) -> list[str]:
    """Deterministic key match on position phase/verdict/R — no LLM involved.

    Order matters: earlier keys win the MAX_COACH_LINES slots.
    """
    keys: list[str] = []
    if position.get("exit_now") or position.get("verdict") == "EXIT":
        keys.append("exit_now")
    if position.get("banner"):
        keys.append("overdue_exit")
    phase = position.get("phase")
    if phase == "INITIATION":
        keys.append("new_position")
    r = position.get("r")
    if isinstance(r, (int, float)) and r < 0:
        keys.append("drawdown")
    if phase == "EXTENSION":
        keys.append("extension")
    if phase == "TREND" and not position.get("exit_now"):
        keys.append("trend_hold")
    return keys


def _coach_lines_for_position(position: dict[str, Any]) -> list[str]:
    bank = _coach_lines_bank()
    out: list[str] = []
    for key in _situation_keys_for_position(position):
        for line in bank.get(key, []):
            if line not in out:
                out.append(line)
            if len(out) >= MAX_COACH_LINES:
                return out
    return out


def _render_message(position: dict[str, Any], narrative: dict[str, str] | None) -> str:
    lines = [f"{position['symbol']} coach: {position['action_line']}"]
    if position.get("exit_now"):
        fired = ", ".join(position.get("fired") or []) or "two-strike rule"
        lines.append(f"URGENT: deterministic exit_now fired ({fired}).")
    if position.get("banner"):
        lines.append(str(position["banner"]))
    if narrative and narrative.get("message"):
        lines.append(narrative["message"])
    for coach_line in _coach_lines_for_position(position):
        lines.append(coach_line)
    lines.append(signals.MANUAL_SUFFIX)
    return "\n".join(lines)


def _persist_signal(conn, run_date: str, symbol: str, message: str, sent: bool) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO agent_signals (scan_date, symbol, channel, message, sent) "
        "VALUES (?, ?, ?, ?, ?)",
        (run_date, symbol, CHANNEL, message, 1 if sent else 0),
    )


_STANCE_MAP = {"agree": "agree", "urgent": "caution", "note": "agree"}


def _persist_advisor_note(
    conn, run_date: str, position: dict[str, Any], narrative: dict[str, str], model: str | None
) -> None:
    """SHIP-1 #4: persist the nightly LLM narrative into advisor_notes (scope=exit)
    so the POSITIONS card's LLM slot survives past the run that generated it —
    previously only agent_signals (the telegram mirror) carried it, so a night
    with no fresh bars/read showed a stale telegram line with no LLM narrative
    on the card itself. Only written when the LLM actually produced a
    narrative; an absent/failed LLM leaves advisor_notes empty for this
    symbol so the UI correctly falls back to the deterministic verdict."""
    from manas_os.advisor.advisor import ensure_schema

    ensure_schema(conn)
    stance = _STANCE_MAP.get(narrative.get("stance", "note"), "agree")
    watch_for = (
        f"verdict={position.get('verdict')} SL={position.get('trail_stop')} "
        f"phase={position.get('phase')}"
    )
    conn.execute(
        "INSERT INTO advisor_notes (note_date, scope, symbol, stance, note, watch_for, model) "
        "VALUES (?, 'exit', ?, ?, ?, ?, ?) "
        "ON CONFLICT(note_date, scope, symbol) DO UPDATE SET "
        "stance = excluded.stance, note = excluded.note, watch_for = excluded.watch_for, "
        "model = excluded.model, created_at = datetime('now')",
        (run_date, position["symbol"], stance, narrative["message"], watch_for, model),
    )


def run(
    conn,
    run_date: str,
    *,
    client: Any | None = None,
    sender: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    started = time.monotonic()
    signals.ensure_schema(conn)
    outbox.ensure_schema(conn)
    pending_alerts: list[tuple[str, str]] = []  # (alert_key, symbol) enqueued this run, awaiting post-commit delivery
    send = sender or telegram_engine.get_sender()
    rows = _open_trades(conn)
    if not rows:
        _agent_log(conn, run_date, True, "skip")
        _pipeline_log(conn, run_date, "skip", 0, started, "coach no open positions")
        result = {"status": "skip", "rows": 0, "sent": 0, "detail": "coach no open positions"}
    else:
        positions = []
        for row in rows:
            read = _deterministic_read(conn, row, run_date)
            if read is not None:
                read["run_date"] = run_date
                positions.append(read)
        if not positions:
            _agent_log(conn, run_date, True, "skip:no deterministic reads")
            _pipeline_log(conn, run_date, "skip", 0, started, "coach no deterministic reads")
            result = {"status": "skip", "rows": 0, "sent": 0, "detail": "coach no deterministic reads"}
        else:
            narratives: dict[str, dict[str, str]] = {}
            llm_error = None
            used_model = None
            try:
                narratives, used_model, llm_error = _load_narratives(positions, client)
            except Exception as exc:  # noqa: BLE001
                llm_error = str(exc)
            _agent_log(
                conn,
                run_date,
                parsed_ok=llm_error is None,
                validation="ok" if llm_error is None else "deterministic-only",
                error=llm_error,
                model=used_model,
            )

            # RELIABILITY_AUDIT_2026-07-19 #8: this used to call send()
            # inline, mid-loop, with the run's single conn.commit() only
            # happening much later (after lessons.run/run_card.write). A
            # crash after a send succeeded but before that commit lost every
            # write for the whole run -- including _persist_signal for
            # positions already sent -- so a retry would resend them all.
            # Fixed by enqueueing into the transactional outbox (no network
            # call, no commit) here, and only attempting delivery AFTER the
            # run's business writes have committed below.
            live = signals._live_enabled()
            for position in positions:
                narrative = narratives.get(position["symbol"])
                message = _render_message(position, narrative)
                if live:
                    alert_key = f"coach_signal:{run_date}:{position['symbol']}"
                    outbox.enqueue(conn, alert_key, "coach_signal",
                                    {"message": message, "symbol": position["symbol"], "run_date": run_date})
                    pending_alerts.append((alert_key, position["symbol"]))
                _persist_signal(conn, run_date, position["symbol"], message, sent=False)
                if narrative and narrative.get("message"):
                    _persist_advisor_note(conn, run_date, position, narrative, used_model)

            status = "ok" if not llm_error else "partial"
            detail = f"coach positions={len(positions)} live={live}"
            if llm_error:
                detail = f"{detail}; llm={llm_error}"
            _pipeline_log(conn, run_date, status, len(positions), started, detail)
            result = {"status": status, "rows": len(positions), "sent": 0, "detail": detail}
    lessons.run(conn, run_date)
    conn.commit()
    run_card.write(conn, run_date)

    if pending_alerts:
        def send_fn(payload: dict) -> None:
            send(payload["message"])
        deliver = outbox.deliver_pending(conn, send_fn)
        sent_count = 0
        send_failures: list[str] = []
        for alert_key, symbol in pending_alerts:
            if alert_key in deliver["delivered"]:
                sent_count += 1
                conn.execute(
                    "UPDATE agent_signals SET sent = 1 WHERE scan_date = ? AND symbol = ? AND channel = ?",
                    (run_date, symbol, CHANNEL),
                )
            else:
                # retried (still pending, backoff not yet elapsed), failed
                # (attempts exhausted), or ambiguous -- none of those are a
                # successful delivery this call, so the run is 'partial'.
                send_failures.append(symbol)
        if sent_count:
            conn.commit()
        result["sent"] = sent_count
        if send_failures:
            result["status"] = "partial"
            result["detail"] = f"{result['detail']}; send_failures={','.join(send_failures)}"
    return result
