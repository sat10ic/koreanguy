"""Two-stage chair merge for model debate verdicts.

Stage 1 is deterministic aggregation over per-model verdict rows. Stage 2 is a
single risk-gate LLM pass that may only strike names on stated risk grounds.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

from manas_os import config
from manas_os.advisor.client import OpenRouterClient
from manas_os.regime.governor import governor

STAGE = "agents_debate"
SOURCE = "agent_verdicts"


def ensure_schema(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS agent_verdicts ("
        "scan_date TEXT NOT NULL, symbol TEXT NOT NULL, agent TEXT NOT NULL, "
        "verdict TEXT NOT NULL, conviction INTEGER, rank INTEGER, "
        "lens_scores_json TEXT, bull_case TEXT, bear_case TEXT, reasoning TEXT, "
        "outcome_r REAL, created_at TEXT DEFAULT (datetime('now')), "
        "PRIMARY KEY (scan_date, symbol, agent))"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS scan_agent_logs ("
        "log_id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "run_date TEXT, agent TEXT, model TEXT, prompt_sha TEXT, "
        "latency_ms INTEGER, tokens_in INTEGER, tokens_out INTEGER, "
        "parsed_ok INTEGER, validation TEXT, error TEXT, "
        "created_at TEXT DEFAULT (datetime('now')))"
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
    models = config.get("agents.models")
    if isinstance(models, str) and models.strip():
        return [models.strip()]
    if isinstance(models, list):
        out = [str(m).strip() for m in models if str(m).strip()]
        if out:
            return out
    return [str(config.get("agents.model", "deepseek/deepseek-chat"))]


def _chair_model() -> str:
    configured = config.get("agents.chair_model")
    if isinstance(configured, str) and configured.strip():
        return configured.strip()
    return _models()[0]


def _pipeline_log(conn, run_date: str, status: str, rows: int, started: float, detail: str) -> None:
    conn.execute(
        "INSERT INTO pipeline_runs (run_date, stage, source, status, rows_affected, "
        "duration_s, detail) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (run_date, STAGE, SOURCE, status, rows, round(time.monotonic() - started, 3), detail),
    )


def _agent_log(
    conn,
    *,
    run_date: str,
    model: str,
    prompt_sha: str | None,
    latency_ms: int | None,
    parsed_ok: bool,
    validation: str,
    error: str | None = None,
) -> None:
    conn.execute(
        "INSERT INTO scan_agent_logs "
        "(run_date, agent, model, prompt_sha, latency_ms, parsed_ok, validation, error) "
        "VALUES (?, 'chair', ?, ?, ?, ?, ?, ?)",
        (run_date, model, prompt_sha, latency_ms, 1 if parsed_ok else 0, validation, error),
    )


def _json(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def _extract_json(raw: str) -> Any:
    text = (raw or "").strip()
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0].strip()
    return json.loads(text)


def _chat(llm: Any, system: str, user: str) -> tuple[str, str]:
    result = llm.chat(system=system, user=user)
    if not isinstance(result, tuple):
        raise ValueError("client.chat must return a tuple")
    if len(result) == 2:
        raw, used_model = result
    elif len(result) == 3:
        raw, used_model, _usage = result
    else:
        raise ValueError("client.chat must return (content, model) or (content, model, usage)")
    return raw, used_model


def _verdict_split(counts: dict[str, int]) -> str:
    return f"{counts.get('TAKE', 0)}T/{counts.get('SKIP', 0)}S"


def aggregate(conn, scan_date: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT symbol, agent, verdict, conviction, rank, bull_case, bear_case "
        "FROM agent_verdicts WHERE scan_date = ? AND agent <> 'chair' "
        "ORDER BY symbol, agent",
        (scan_date,),
    ).fetchall()
    if not rows:
        return []
    worst_rank = max([int(r["rank"]) for r in rows if r["rank"] is not None] or [0]) + 1
    by_symbol: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_symbol.setdefault(row["symbol"], []).append(dict(row))

    out = []
    for symbol, items in by_symbol.items():
        convictions = [int(i["conviction"]) for i in items if i.get("conviction") is not None]
        ranks = [int(i["rank"]) if i.get("rank") is not None else worst_rank for i in items]
        counts = {"TAKE": 0, "SKIP": 0}
        for item in items:
            verdict = str(item.get("verdict") or "").upper()
            if verdict in counts:
                counts[verdict] += 1
        spread = (max(convictions) - min(convictions)) if convictions else 0
        verdicts_present = sum(1 for v in counts.values() if v > 0)
        out.append({
            "symbol": symbol,
            "mean_conviction": (sum(convictions) / len(convictions)) if convictions else 0.0,
            "conviction_spread": spread,
            "verdict_split": _verdict_split(counts),
            "disagreement": spread >= 3 or verdicts_present > 1,
            "mean_rank": (sum(ranks) / len(ranks)) if ranks else float(worst_rank),
            "base_verdict": "TAKE" if counts["TAKE"] > counts["SKIP"] else "SKIP",
            "bull_cases": [{"agent": i["agent"], "text": i.get("bull_case")} for i in items],
            "bear_cases": [{"agent": i["agent"], "text": i.get("bear_case")} for i in items],
        })
    return sorted(out, key=lambda i: (i["mean_rank"], -i["mean_conviction"], i["symbol"]))


def _candidate_context(conn, scan_date: str, symbols: list[str]) -> dict[str, Any]:
    if not symbols:
        return {}
    placeholders = ",".join("?" for _ in symbols)
    rows = conn.execute(
        f"SELECT symbol, entry, stop, target, rr, suggested_qty, trade_plan_json, sector, industry "
        f"FROM scan_candidates WHERE scan_date = ? AND symbol IN ({placeholders})",
        (scan_date, *symbols),
    ).fetchall()
    out = {}
    for row in rows:
        plan = _json(row["trade_plan_json"], {})
        out[row["symbol"]] = {
            "entry": row["entry"],
            "stop": row["stop"],
            "target": row["target"],
            "rr": row["rr"],
            "suggested_qty": row["suggested_qty"],
            "trade_plan": plan,
            "sector": row["sector"],
            "industry": row["industry"],
        }
    return out


def _latest_mode(conn, scan_date: str) -> str:
    row = conn.execute(
        "SELECT market_mode FROM regime_snapshots WHERE snapshot_date <= ? "
        "ORDER BY snapshot_date DESC LIMIT 1",
        (scan_date,),
    ).fetchone()
    return str(row["market_mode"]).upper() if row and row["market_mode"] else "SELECTIVE"


def _portfolio_heat(conn, mode: str) -> dict[str, Any]:
    rows = conn.execute(
        "SELECT symbol, setup, entry, stop FROM journal_trades WHERE exit IS NULL ORDER BY trade_date DESC"
    ).fetchall()
    positions = [dict(r) for r in rows]
    return {
        "open_positions": len(positions),
        "positions": positions,
        "open_risk_cap_pct": governor(mode).get("open_risk_cap_pct"),
    }


def _risk_input(conn, scan_date: str, aggregates: list[dict[str, Any]]) -> dict[str, Any]:
    symbols = [item["symbol"] for item in aggregates]
    mode = _latest_mode(conn, scan_date)
    plans = _candidate_context(conn, scan_date, symbols)
    return {
        "scan_date": scan_date,
        "aggregates": [
            {
                "symbol": item["symbol"],
                "mean_conviction": round(item["mean_conviction"], 2),
                "verdict_split": item["verdict_split"],
                "mean_rank": round(item["mean_rank"], 2),
                "disagreement": item["disagreement"],
                "bear_cases": item["bear_cases"],
                "plan": plans.get(item["symbol"], {}),
            }
            for item in aggregates
        ],
        "portfolio_heat": _portfolio_heat(conn, mode),
        "governor_law": governor(mode),
    }


def _system_prompt() -> str:
    return (
        "You are the Manas OS chair risk gate. You may only strike shortlisted "
        "symbols on stated risk grounds: concentration, correlated exposure, or "
        "event risk named in bear cases. You cannot reorder, change convictions, "
        "or add names. Return only JSON: an array of {symbol, strike, strike_reason}."
    )


def _validate_strikes(payload: Any, symbols: set[str]) -> dict[str, str]:
    if isinstance(payload, dict) and isinstance(payload.get("strikes"), list):
        payload = payload["strikes"]
    if not isinstance(payload, list):
        raise ValueError("chair JSON must be an array")
    strikes: dict[str, str] = {}
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("chair item must be an object")
        symbol = str(item.get("symbol") or "").upper().strip()
        if symbol not in symbols:
            raise ValueError(f"chair returned unknown symbol {symbol or '?'}")
        if bool(item.get("strike")):
            strikes[symbol] = str(item.get("strike_reason") or "risk strike").strip() or "risk strike"
    return strikes


def _persist(conn, scan_date: str, aggregates: list[dict[str, Any]], strikes: dict[str, str]) -> int:
    ranked = []
    for item in aggregates:
        struck = item["symbol"] in strikes
        ranked.append((struck, item))
    ranked.sort(key=lambda pair: (1 if pair[0] else 0, pair[1]["mean_rank"], -pair[1]["mean_conviction"], pair[1]["symbol"]))
    for rank, (struck, item) in enumerate(ranked, start=1):
        reason = strikes.get(item["symbol"])
        lens = {
            "verdict_split": item["verdict_split"],
            "conviction_spread": item["conviction_spread"],
            "disagreement": item["disagreement"],
        }
        reasoning = (
            f"models {item['verdict_split']}, spread {item['conviction_spread']}; "
            f"struck: {reason if struck else 'no'}"
        )
        conn.execute(
            "INSERT OR REPLACE INTO agent_verdicts "
            "(scan_date, symbol, agent, verdict, conviction, rank, lens_scores_json, bull_case, bear_case, reasoning) "
            "VALUES (?, ?, 'chair', ?, ?, ?, ?, ?, ?, ?)",
            (
                scan_date,
                item["symbol"],
                "SKIP" if struck else item["base_verdict"],
                int(item["mean_conviction"] + 0.5),
                rank,
                json.dumps(lens, sort_keys=True),
                json.dumps(item["bull_cases"], sort_keys=True),
                json.dumps(item["bear_cases"], sort_keys=True),
                reasoning,
            ),
        )
    return len(ranked)


def run(
    conn,
    scan_date: str,
    *,
    run_date: str | None = None,
    client: Any | None = None,
    log_pipeline: bool = True,
) -> dict[str, Any]:
    started = time.monotonic()
    run_date = run_date or scan_date
    ensure_schema(conn)
    aggregates = aggregate(conn, scan_date)
    if not aggregates:
        if log_pipeline:
            _pipeline_log(conn, run_date, "skip", 0, started, "chair: no model verdicts")
            conn.commit()
        return {"status": "skip", "rows": 0, "detail": "chair: no model verdicts"}

    model = _chair_model()
    strikes: dict[str, str] = {}
    status = "ok"
    error = None
    system = _system_prompt()
    user = json.dumps(_risk_input(conn, scan_date, aggregates), sort_keys=True)
    prompt_sha = hashlib.sha256((system + "\n" + user).encode("utf-8")).hexdigest()
    call_started = time.monotonic()
    try:
        llm = client or OpenRouterClient(api_key=_api_key(), model=model, max_tokens=int(config.get("agents.max_tokens", 4000) or 4000))
        raw, used_model = _chat(llm, system, user)
        model = used_model or model
        strikes = _validate_strikes(_extract_json(raw), {item["symbol"] for item in aggregates})
        _agent_log(
            conn,
            run_date=run_date,
            model=model,
            prompt_sha=prompt_sha,
            latency_ms=round((time.monotonic() - call_started) * 1000),
            parsed_ok=True,
            validation="ok",
        )
    except Exception as exc:  # noqa: BLE001
        status = "partial"
        error = str(exc)
        _agent_log(
            conn,
            run_date=run_date,
            model=model,
            prompt_sha=prompt_sha,
            latency_ms=round((time.monotonic() - call_started) * 1000),
            parsed_ok=False,
            validation="partial",
            error=error,
        )

    rows = _persist(conn, scan_date, aggregates, strikes)
    detail = f"chair scan_date={scan_date} rows={rows}"
    if status == "partial":
        detail = f"{detail}; risk_gate_error={error}"
    if log_pipeline:
        _pipeline_log(conn, run_date, status, rows, started, detail)
        conn.commit()
    return {"status": status, "rows": rows, "detail": detail, "strikes": strikes}
