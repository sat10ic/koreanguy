"""Agent lesson loop for closed-out debate outcomes.

The LLM writes prose only. Trigger checks, R-path values, tags, and digest
inputs are computed here before any model call.
"""
from __future__ import annotations

import json
from datetime import date as _date
from pathlib import Path
from typing import Any

from manas_os import config, market_calendar
from manas_os.advisor.client import OpenRouterClient
from manas_os.agents import _shared
from manas_os.agents.context_pack import LESSON_DIGEST_PATH

LESSON_DIR = LESSON_DIGEST_PATH.parent
TAGS = {"clean-hit", "clean-miss", "right-process-loss", "wrong-process-win"}


def ensure_schema(conn) -> None:
    # lessons.py only needs agent_verdicts (not scan_agent_logs); reuse the
    # shared agent_verdicts DDL to avoid drift, ignore the extra table.
    _shared.ensure_agent_tables(conn)


def _api_key() -> str | None:
    return _shared.api_key()


def _model() -> str:
    model = config.get("agents.lessons_model") or config.get("agents.coach_model")
    if isinstance(model, str) and model.strip():
        return model.strip()
    models = config.get("agents.models")
    if isinstance(models, str) and models.strip():
        return models.strip()
    if isinstance(models, list):
        out = [str(m).strip() for m in models if str(m).strip()]
        if out:
            return out[0]
    return str(config.get("agents.model", "deepseek/deepseek-chat"))


def _chat(llm: Any, system: str, user: str) -> str:
    result = llm.chat(system=system, user=user, include_usage=True) if isinstance(llm, OpenRouterClient) else llm.chat(system=system, user=user)
    if not isinstance(result, tuple):
        raise ValueError("client.chat must return a tuple")
    if len(result) not in {2, 3}:
        raise ValueError("client.chat must return (content, model) or (content, model, usage)")
    return str(result[0] or "")


def _sessions_old(scan_date: str, run_date: str) -> int:
    try:
        start = _date.fromisoformat(scan_date)
        end = _date.fromisoformat(run_date)
    except ValueError:
        return 0
    if end <= start:
        return 0
    return market_calendar.trading_days_between(start, end) + (1 if market_calendar.is_trading_day(end) else 0)


def _eligible_chairs(conn, run_date: str) -> list[Any]:
    rows = conn.execute(
        "SELECT av.scan_date, av.symbol, av.verdict, av.conviction, av.rank, "
        "av.bull_case, av.bear_case, av.reasoning, sc.entry, sc.stop "
        "FROM agent_verdicts av "
        "JOIN scan_candidates sc ON sc.scan_date = av.scan_date AND sc.symbol = av.symbol "
        "WHERE av.agent = 'chair' AND av.outcome_r IS NULL "
        "ORDER BY av.scan_date, av.symbol"
    ).fetchall()
    return [r for r in rows if _sessions_old(str(r["scan_date"]), run_date) >= 10]


def _outcome_path(conn, symbol: str, scan_date: str, entry: Any, stop: Any, horizon: int = 10) -> dict[str, Any]:
    try:
        entry_f = float(entry)
        stop_f = float(stop)
    except (TypeError, ValueError):
        return {"status": "invalid_plan", "outcome_r": None, "path": []}
    risk = entry_f - stop_f
    if risk <= 0:
        return {"status": "invalid_plan", "outcome_r": None, "path": []}

    fwd = conn.execute(
        "SELECT trade_date, high, close FROM daily_prices WHERE symbol = ? AND series = 'EQ' "
        "AND trade_date > ? AND close IS NOT NULL ORDER BY trade_date ASC LIMIT ?",
        (symbol.upper(), scan_date, horizon),
    ).fetchall()
    if len(fwd) < horizon:
        return {"status": "insufficient_data", "outcome_r": None, "path": []}

    touched = [r for r in fwd if r["high"] is not None and float(r["high"]) >= entry_f]
    path = [
        {
            "date": r["trade_date"],
            "high": r["high"],
            "close": r["close"],
            "r": round((float(r["close"]) - entry_f) / risk, 4),
        }
        for r in fwd
    ]
    if not touched:
        return {"status": "never_triggered", "outcome_r": None, "path": path}
    return {
        "status": "filled",
        "outcome_r": (float(fwd[-1]["close"]) - entry_f) / risk,
        "trigger_date": touched[0]["trade_date"],
        "path": path,
    }


def _append_never_triggered(conn, scan_date: str, symbol: str) -> None:
    rows = conn.execute(
        "SELECT agent, reasoning FROM agent_verdicts WHERE scan_date = ? AND symbol = ?",
        (scan_date, symbol),
    ).fetchall()
    for row in rows:
        reasoning = str(row["reasoning"] or "")
        if "[never triggered]" in reasoning:
            continue
        suffix = " [never triggered]" if reasoning else "[never triggered]"
        conn.execute(
            "UPDATE agent_verdicts SET reasoning = ? WHERE scan_date = ? AND symbol = ? AND agent = ?",
            (f"{reasoning}{suffix}", scan_date, symbol, row["agent"]),
        )


def _propagate_outcome(conn, scan_date: str, symbol: str, outcome_r: float) -> None:
    conn.execute(
        "UPDATE agent_verdicts SET outcome_r = ? WHERE scan_date = ? AND symbol = ?",
        (outcome_r, scan_date, symbol),
    )


def _tag(outcome_r: float) -> str:
    if outcome_r >= 1.0:
        return "clean-hit"
    if outcome_r < 0:
        return "clean-miss"
    return "right-process-loss"


def _lesson_payload(row: Any, outcome: dict[str, Any], tag: str) -> dict[str, Any]:
    return {
        "scan_date": row["scan_date"],
        "symbol": row["symbol"],
        "verdict": row["verdict"],
        "conviction": row["conviction"],
        "rank": row["rank"],
        "bull_case": row["bull_case"],
        "bear_case": row["bear_case"],
        "reasoning": row["reasoning"],
        "entry": row["entry"],
        "stop": row["stop"],
        "outcome_r": round(float(outcome["outcome_r"]), 4),
        "trigger_date": outcome.get("trigger_date"),
        "r_path": outcome["path"],
        "required_tag": tag,
        "allowed_tags": sorted(TAGS),
    }


def _system_prompt() -> str:
    return (
        "Write one compact markdown paragraph for a ticker-scoped trading lesson. "
        "Use only the supplied numbers; do not calculate or invent R values. "
        "Quote the model conviction or split if present, explain why the thesis was right or wrong, "
        "and include exactly one supplied tag."
    )


def _one_paragraph(text: str, tag: str) -> str:
    paragraph = " ".join((text or "").strip().split())
    if not paragraph:
        return ""
    if not any(t in paragraph for t in TAGS):
        paragraph = f"{paragraph} [{tag}]"
    return paragraph


def _stub_lesson(payload: dict[str, Any], tag: str, error: str | None = None) -> str:
    err = f"; llm_error={error}" if error else ""
    return (
        f"{payload['symbol']} {payload['scan_date']} lesson stub: "
        f"entry={payload['entry']} stop={payload['stop']} outcome_r={payload['outcome_r']:.4f}R "
        f"trigger_date={payload.get('trigger_date')} tag={tag}{err}"
    )


def _write_lesson(row: Any, outcome: dict[str, Any], client: Any | None) -> Path:
    LESSON_DIR.mkdir(parents=True, exist_ok=True)
    tag = _tag(float(outcome["outcome_r"]))
    payload = _lesson_payload(row, outcome, tag)
    text = ""
    error = None
    try:
        key = _api_key()
        if client is None and not key:
            raise RuntimeError("lessons api key absent")
        llm = client or OpenRouterClient(api_key=key, model=_model(), max_tokens=int(config.get("agents.max_tokens", 2000) or 2000))
        text = _one_paragraph(_chat(llm, _system_prompt(), json.dumps(payload, indent=2, sort_keys=True, default=str)), tag)
        if not text:
            raise ValueError("empty lesson response")
    except Exception as exc:  # noqa: BLE001
        error = str(exc)
        text = _stub_lesson(payload, tag, error)
    path = LESSON_DIR / f"{row['scan_date']}_{str(row['symbol']).upper()}.md"
    # AU2: tmp+rename atomic write (match the digest's existing pattern) so a
    # mid-write crash can't feed a truncated lesson file to the digest LLM.
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


def _digest_prompt(files: list[Path]) -> str:
    lessons = [{"file": p.name, "text": p.read_text(encoding="utf-8").strip()} for p in files]
    return json.dumps(
        {
            "instruction": "Compress these lessons into <=15 total lines. Preserve ticker tags and recurring mistakes.",
            "lessons": lessons,
        },
        indent=2,
        sort_keys=True,
    )


def _regenerate_digest(client: Any | None) -> bool:
    try:
        files = sorted(p for p in LESSON_DIR.glob("*.md") if p.name != "_digest.md")[-20:]
        if not files:
            return False
        key = _api_key()
        if client is None and not key:
            raise RuntimeError("lessons api key absent")
        llm = client or OpenRouterClient(api_key=key, model=_model(), max_tokens=int(config.get("agents.max_tokens", 2000) or 2000))
        raw = _chat(
            llm,
            "Return only markdown, <=15 non-empty lines total.",
            _digest_prompt(files),
        )
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        if not lines:
            raise ValueError("empty digest response")
        text = "\n".join(lines[:15]) + "\n"
        LESSON_DIR.mkdir(parents=True, exist_ok=True)
        tmp = LESSON_DIGEST_PATH.with_name("_digest.md.tmp")
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(LESSON_DIGEST_PATH)
        return True
    except Exception:  # noqa: BLE001
        return False


def run(conn, run_date: str, *, client: Any | None = None) -> dict[str, Any]:
    ensure_schema(conn)
    backfilled = 0
    never_triggered = 0
    lessons_written = 0
    for row in _eligible_chairs(conn, run_date):
        symbol = str(row["symbol"]).upper()
        outcome = _outcome_path(conn, symbol, str(row["scan_date"]), row["entry"], row["stop"])
        if outcome["status"] == "never_triggered":
            _append_never_triggered(conn, str(row["scan_date"]), symbol)
            never_triggered += 1
            continue
        if outcome["status"] != "filled":
            continue
        _propagate_outcome(conn, str(row["scan_date"]), symbol, float(outcome["outcome_r"]))
        backfilled += 1
        if str(row["verdict"]).upper() == "TAKE":
            _write_lesson(row, outcome, client)
            lessons_written += 1
    digest_written = _regenerate_digest(client) if lessons_written else False
    return {
        "status": "ok",
        "backfilled": backfilled,
        "never_triggered": never_triggered,
        "lessons": lessons_written,
        "digest": digest_written,
    }
