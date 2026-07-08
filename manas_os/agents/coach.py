"""Journal coach agent for open positions.

The deterministic exit engine is the one writer for position action. The LLM
only narrates that read; if it is unavailable, deterministic coach signals
still persist.
"""
from __future__ import annotations

import json
import os
import time
from datetime import date as _date
from pathlib import Path
from typing import Any, Callable

from manas_os import config, market_calendar
from manas_os.advisor.client import OpenRouterClient
from manas_os.agents import lessons, run_card, signals
from manas_os.agents.context_pack import INDIA_STRUCTURE_PRIMER
from manas_os.alerts import telegram_engine
from manas_os.engine import eod_detectors

STAGE = "agents_coach"
SOURCE = "journal_trades"
CHANNEL = "coach"
AGENT = "coach"
NET_COSTS_NOTE = (
    "Report thinking in NET terms: STT, GST, brokerage, and slippage drag small accounts; "
    "do not narrate gross R as if costs are zero."
)


def _load_env_file() -> None:
    p = Path(os.getcwd())
    for parent in [p] + list(p.parents):
        env_path = parent / ".env"
        if not env_path.exists():
            continue
        try:
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
        except Exception:
            pass
        break


def _api_key() -> str | None:
    _load_env_file()
    return config.get("agents.api_key") or config.get("advisor.api_key") or os.environ.get("OPENROUTER_API_KEY")


def _models() -> list[str]:
    coach_model = config.get("agents.coach_model")
    if isinstance(coach_model, str) and coach_model.strip():
        return [coach_model.strip()]
    models = config.get("agents.models")
    if isinstance(models, str) and models.strip():
        return [models.strip()]
    if isinstance(models, list):
        out = [str(m).strip() for m in models if str(m).strip()]
        if out:
            return [out[0]]
    return [str(config.get("agents.model", "deepseek/deepseek-chat"))]


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
    return conn.execute(
        "SELECT trade_id, trade_date, symbol, setup, entry, stop, first_exit_flag_date "
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
    strikes = eod_detectors.two_strike(bars)
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
    if isinstance(llm, OpenRouterClient):
        return llm.chat(system=system, user=user, include_usage=True)
    return llm.chat(system=system, user=user)


def _unpack_chat(result: Any, default_model: str) -> tuple[str, str]:
    if not isinstance(result, tuple):
        raise ValueError("client.chat must return a tuple")
    if len(result) == 2:
        raw, used_model = result
        return raw, used_model or default_model
    if len(result) == 3:
        raw, used_model, _usage = result
        return raw, used_model or default_model
    raise ValueError("client.chat must return (content, model) or (content, model, usage)")


def _load_narratives(positions: list[dict[str, Any]], client: Any | None) -> tuple[dict[str, dict[str, str]], str | None, str | None]:
    key = _api_key()
    if client is None and not key:
        return {}, None, "coach llm config/api key absent"
    model = _models()[0]
    llm = client or OpenRouterClient(api_key=key, model=model, max_tokens=int(config.get("agents.max_tokens", 2000) or 2000))
    raw, used_model = _unpack_chat(_chat(llm, _system_prompt(), _user_prompt(positions)), model)
    symbols = {str(p["symbol"]).upper() for p in positions}
    return _parse_narratives(raw, symbols), used_model, None


def _render_message(position: dict[str, Any], narrative: dict[str, str] | None) -> str:
    lines = [f"{position['symbol']} coach: {position['action_line']}"]
    if position.get("exit_now"):
        fired = ", ".join(position.get("fired") or []) or "two-strike rule"
        lines.append(f"URGENT: deterministic exit_now fired ({fired}).")
    if position.get("banner"):
        lines.append(str(position["banner"]))
    if narrative and narrative.get("message"):
        lines.append(narrative["message"])
    lines.append(signals.MANUAL_SUFFIX)
    return "\n".join(lines)


def _persist_signal(conn, run_date: str, symbol: str, message: str, sent: bool) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO agent_signals (scan_date, symbol, channel, message, sent) "
        "VALUES (?, ?, ?, ?, ?)",
        (run_date, symbol, CHANNEL, message, 1 if sent else 0),
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

            live = signals._live_enabled()
            send = sender or telegram_engine._telegram_sender
            sent_count = 0
            send_failures: list[str] = []
            for position in positions:
                message = _render_message(position, narratives.get(position["symbol"]))
                sent = False
                if live:
                    try:
                        send(message)
                        sent = True
                        sent_count += 1
                    except Exception as exc:  # noqa: BLE001
                        send_failures.append(f"{position['symbol']}: {exc}")
                _persist_signal(conn, run_date, position["symbol"], message, sent)

            status = "ok"
            if llm_error or send_failures:
                status = "partial"
            detail = f"coach positions={len(positions)} sent={sent_count} live={live}"
            if llm_error:
                detail = f"{detail}; llm={llm_error}"
            if send_failures:
                detail = f"{detail}; send_failures={' | '.join(send_failures)}"
            _pipeline_log(conn, run_date, status, len(positions), started, detail)
            result = {"status": status, "rows": len(positions), "sent": sent_count, "detail": detail}
    lessons.run(conn, run_date)
    conn.commit()
    run_card.write(conn, run_date)
    return result
