"""Sizer agent for chair-approved picks.

The sizer is deliberately downstream of risk.plan: it may choose a multiplier,
but the accepted quantity must stay inside the envelope returned by
risk_plan.validate().
"""
from __future__ import annotations

import hashlib
import json
import math
import time
from typing import Any

from manas_os import config
from manas_os.advisor.client import OpenRouterClient
from manas_os.agents import context_pack
from manas_os.agents import _shared
from manas_os.agents.debate import ensure_schema
from manas_os.regime.governor import governor
from manas_os.risk import plan as risk_plan
from manas_os.scanner import expectancy, outcomes

AGENT = "sizer"
DEFAULT_RISK_APPETITE = "aggressive"
AD7_NOTE = "report thinking in NET terms - costs drag small accounts"
AD9_TIER_BANDS = {
    "india_vix": {"low": "<12", "normal": "12-20", "danger": ">20"},
}


def _api_key() -> str | None:
    return _shared.api_key()


def _sizer_model() -> str:
    model = config.get("agents.sizer_model")
    if isinstance(model, str) and model.strip():
        return model.strip()
    models = config.get("agents.models")
    if isinstance(models, str) and models.strip():
        return models.strip()
    if isinstance(models, list):
        for item in models:
            text = str(item).strip()
            if text:
                return text
    return str(config.get("agents.model", "deepseek/deepseek-chat"))


def _latest_mode(conn, scan_date: str) -> str:
    row = conn.execute(
        "SELECT market_mode FROM regime_snapshots WHERE snapshot_date <= ? "
        "ORDER BY snapshot_date DESC LIMIT 1",
        (scan_date,),
    ).fetchone()
    return str(row["market_mode"]).upper() if row and row["market_mode"] else "SELECTIVE"


def _json(text: str | None, fallback: Any) -> Any:
    if not text:
        return fallback
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return fallback


def _load_picks(conn, scan_date: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT av.symbol, av.rank AS final_rank, av.reasoning AS chair_reasoning, "
        "sc.setup, sc.setup_family, sc.entry, sc.stop, sc.target, sc.rr, "
        "sc.suggested_qty, sc.sector, sc.industry "
        "FROM agent_verdicts av JOIN scan_candidates sc "
        "ON sc.scan_date = av.scan_date AND sc.symbol = av.symbol "
        "WHERE av.scan_date = ? AND av.agent = 'chair' AND av.verdict = 'TAKE' "
        "ORDER BY COALESCE(av.rank, 999999), av.symbol",
        (scan_date,),
    ).fetchall()
    return [dict(row) for row in rows]


def _base_rate(conn, setup_family: str | None, regime: str) -> dict[str, Any] | None:
    if not setup_family:
        return None
    return expectancy.chip_for(conn, setup_family, regime)


def _open_positions(conn, capital: float, scan_date: str) -> list[dict[str, Any]]:
    outcomes.ensure_setup_decisions_schema(conn)
    try:
        rows = conn.execute(
            "SELECT trade_id, trade_date, symbol, setup, entry, stop FROM journal_trades "
            "WHERE exit IS NULL ORDER BY trade_date DESC, trade_id DESC"
        ).fetchall()
    except Exception:  # noqa: BLE001
        return []
    positions = []
    for row in rows:
        decision = conn.execute(
            "SELECT qty, snapshot_json FROM setup_decisions WHERE scan_date = ? AND symbol = ?",
            (row["trade_date"], row["symbol"]),
        ).fetchone()
        qty = int(decision["qty"]) if decision and decision["qty"] is not None else 0
        sector = None
        if decision and decision["snapshot_json"]:
            sector = _json(decision["snapshot_json"], {}).get("sector")
        entry = float(row["entry"]) if row["entry"] is not None else None
        stop = float(row["stop"]) if row["stop"] is not None else None
        risk_pct = 0.0
        if entry is not None and stop is not None and entry > stop and qty > 0 and capital > 0:
            risk_pct = (entry - stop) * qty / capital * 100.0
        positions.append(
            {
                "symbol": row["symbol"],
                "sector": sector,
                "risk_pct": round(risk_pct, 4),
                "opened_today": row["trade_date"] == scan_date,
            }
        )
    return positions


def _portfolio_heat(open_positions: list[dict[str, Any]], law: dict[str, Any]) -> dict[str, Any]:
    return {
        "open_risk_pct": round(sum(float(p.get("risk_pct") or 0.0) for p in open_positions), 4),
        "cap_pct": law.get("open_risk_cap_pct"),
        "open_positions": len(open_positions),
    }


def _system_prompt() -> str:
    return (
        "You are the Manas OS sizer. The deterministic risk/plan.py validator is "
        "the arithmetic authority. Choose only take and multiplier. Return only "
        "JSON: an array of {symbol, take, multiplier, reasoning}. Multiplier must "
        "be between 0.25 and 1.25; reasoning is at most 3 sentences."
    )


def _user_prompt(conn, scan_date: str, picks: list[dict[str, Any]], regime: str, law: dict[str, Any], heat: dict[str, Any]) -> str:
    pack = context_pack.build_pack(conn, scan_date, picks)
    appetite = str(config.get("agents.risk_appetite", DEFAULT_RISK_APPETITE) or DEFAULT_RISK_APPETITE)
    return json.dumps(
        {
            "scan_date": scan_date,
            "risk_appetite": appetite,
            "governor_law": law,
            "portfolio_heat": {"open_risk_pct": heat["open_risk_pct"], "cap_pct": heat["cap_pct"]},
            "india_vix": pack.get("india_vix"),
            "ad9_tier_bands": AD9_TIER_BANDS,
            "ad7_note": AD7_NOTE,
            "india_structure_primer": pack.get("india_structure_primer"),
            "lesson_digest": pack.get("lesson_digest", ""),
            "picks": [
                {
                    "symbol": item["symbol"],
                    "rank": item.get("final_rank"),
                    "setup_family": item.get("setup_family"),
                    "plan_from_risk_plan": {
                        "entry": item.get("entry"),
                        "stop": item.get("stop"),
                        "rr": item.get("rr"),
                        "suggested_qty": item.get("suggested_qty"),
                    },
                    "base_rates": _base_rate(conn, item.get("setup_family"), regime) or "no base rates available",
                    "chair_reasoning": item.get("chair_reasoning"),
                }
                for item in picks
            ],
            "output_schema": {"symbol": "string", "take": "bool", "multiplier": "0.25-1.25", "reasoning": "<=3 sentences"},
        },
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


def _payload_by_symbol(payload: Any, symbols: set[str]) -> dict[str, dict[str, Any]]:
    if isinstance(payload, dict) and isinstance(payload.get("sizes"), list):
        payload = payload["sizes"]
    if not isinstance(payload, list):
        raise ValueError("sizer JSON must be an array")
    out = {}
    for item in payload:
        if not isinstance(item, dict):
            continue
        symbol = str(item.get("symbol") or "").upper().strip()
        if symbol in symbols:
            out[symbol] = item
    if not out:
        raise ValueError("sizer returned no known symbols")
    return out


def _clamp_multiplier(value: Any) -> float:
    try:
        m = float(value)
    except (TypeError, ValueError):
        m = 1.0
    return max(0.25, min(1.25, m))


def _final_qty(suggested_qty: Any, multiplier: float) -> int:
    try:
        qty = int(math.floor(float(suggested_qty or 0) * multiplier))
    except (TypeError, ValueError):
        qty = 0
    return max(0, qty)


def _validate_choice(
    item: dict[str, Any],
    multiplier: float,
    *,
    regime: str,
    profile: str,
    open_positions: list[dict[str, Any]],
    account_capital: float,
) -> tuple[float, int, dict[str, Any], list[str]]:
    steps = []
    current = multiplier
    while current >= 0.25:
        final_qty = _final_qty(item.get("suggested_qty"), current)
        result = risk_plan.validate(
            entry=float(item.get("entry") or 0),
            stop=float(item.get("stop") or 0),
            measured_move=float(item["target"]) if item.get("target") is not None else None,
            regime=regime,
            setup_family=str(item.get("setup_family") or ""),
            open_positions=open_positions,
            sector=item.get("sector"),
            profile=profile,
            account_capital=account_capital,
        )
        allowed_qty = int(result.get("qty") or 0)
        if result.get("pass") and final_qty > 0 and final_qty <= allowed_qty:
            return current, final_qty, result, steps
        reasons = list(result.get("reasons") or [])
        if final_qty > allowed_qty:
            reasons.append(f"qty {final_qty} exceeds validated envelope {allowed_qty}")
        next_m = round(current - 0.25, 2)
        steps.append(f"{item['symbol']}: {current:.2f}->{max(next_m, 0.25):.2f} ({'; '.join(reasons) or 'validation failed'})")
        if current <= 0.25:
            break
        current = max(0.25, next_m)
    return 0.0, 0, result, steps


def _persist_row(conn, scan_date: str, symbol: str, verdict: str, rank: int, lens: dict[str, Any], reasoning: str | None) -> None:
    # AU1: upsert instead of INSERT OR REPLACE — a same-night rerun must not
    # null outcome_r/created_at on an existing row (REPLACE = delete+reinsert).
    conn.execute(
        "INSERT INTO agent_verdicts "
        "(scan_date, symbol, agent, verdict, conviction, rank, lens_scores_json, reasoning) "
        "VALUES (?, ?, ?, ?, NULL, ?, ?, ?) "
        "ON CONFLICT(scan_date, symbol, agent) DO UPDATE SET "
        "verdict=excluded.verdict, rank=excluded.rank, "
        "lens_scores_json=excluded.lens_scores_json, reasoning=excluded.reasoning, "
        "outcome_r=COALESCE(excluded.outcome_r, agent_verdicts.outcome_r), "
        "created_at=agent_verdicts.created_at",
        (scan_date, symbol, AGENT, verdict, rank, json.dumps(lens, sort_keys=True), reasoning),
    )


def _agent_log(conn, *, run_date: str, model: str | None, prompt_sha: str | None, latency_ms: int | None, parsed_ok: bool, validation: str, error: str | None = None) -> None:
    conn.execute(
        "INSERT INTO scan_agent_logs "
        "(run_date, agent, model, prompt_sha, latency_ms, parsed_ok, validation, error) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (run_date, AGENT, model, prompt_sha, latency_ms, 1 if parsed_ok else 0, validation, error),
    )


def _chat(llm: Any, system: str, user: str) -> tuple[str, str]:
    return _shared.chat_tuple(llm, system, user)


def run(conn, scan_date: str, *, run_date: str | None = None, client: Any | None = None) -> dict[str, Any]:
    run_date = run_date or scan_date
    ensure_schema(conn)
    picks = _load_picks(conn, scan_date)
    if not picks:
        return {"status": "skip", "rows": 0, "detail": "sizer no chair TAKE picks"}

    model = _sizer_model()
    key = _api_key()
    if client is None and not key:
        return {"status": "skip", "rows": 0, "detail": "sizer api key absent"}

    regime = _latest_mode(conn, scan_date)
    profile = str(config.get("agents.risk_appetite", DEFAULT_RISK_APPETITE) or DEFAULT_RISK_APPETITE).lower()
    if profile not in risk_plan.PROFILES:
        profile = DEFAULT_RISK_APPETITE
    account_capital = float(config.get("risk.capital", 1_000_000.0) or 1_000_000.0)
    open_positions = _open_positions(conn, account_capital, scan_date)
    law = governor(regime, profile=profile)
    heat = _portfolio_heat(open_positions, law)
    system = _system_prompt()
    user = _user_prompt(conn, scan_date, picks, regime, law, heat)
    prompt_sha = hashlib.sha256((system + "\n" + user).encode("utf-8")).hexdigest()
    started = time.monotonic()
    try:
        llm = client or OpenRouterClient(api_key=key, model=model, max_tokens=int(config.get("agents.max_tokens", 4000) or 4000))
        raw, used_model = _chat(llm, system, user)
        payloads = _payload_by_symbol(_extract_json(raw), {item["symbol"] for item in picks})
    except Exception as exc:  # noqa: BLE001
        _agent_log(
            conn,
            run_date=run_date,
            model=model,
            prompt_sha=prompt_sha,
            latency_ms=round((time.monotonic() - started) * 1000),
            parsed_ok=False,
            validation="fail",
            error=str(exc),
        )
        return {"status": "partial", "rows": 0, "detail": f"sizer LLM failure: {exc}"}

    rows = 0
    validation_notes = []
    for rank, item in enumerate(picks, start=1):
        payload = payloads.get(item["symbol"], {})
        take = bool(payload.get("take", True))
        reasoning = str(payload.get("reasoning") or "").strip() or None
        if not take:
            _persist_row(conn, scan_date, item["symbol"], "SKIP", rank, {"multiplier": 0, "final_qty": 0, "validated": True}, reasoning)
            rows += 1
            continue
        multiplier = _clamp_multiplier(payload.get("multiplier"))
        multiplier, final_qty, result, steps = _validate_choice(
            item,
            multiplier,
            regime=regime,
            profile=profile,
            open_positions=open_positions,
            account_capital=account_capital,
        )
        validation_notes.extend(steps)
        if multiplier <= 0 or final_qty <= 0:
            verdict = "SKIP"
            lens = {"multiplier": 0, "final_qty": 0, "validated": False}
            reason = "; ".join(result.get("reasons") or ["validation failed"])
            reasoning = f"{reasoning or ''}; {reason}".strip("; ")
        else:
            verdict = "TAKE"
            lens = {"multiplier": multiplier, "final_qty": final_qty, "validated": True}
            risk_pct = float(result.get("risk_pct_used") or 0.0) * multiplier
            open_positions.append({"symbol": item["symbol"], "sector": item.get("sector"), "risk_pct": risk_pct, "opened_today": True})
        _persist_row(conn, scan_date, item["symbol"], verdict, rank, lens, reasoning)
        rows += 1
    _agent_log(
        conn,
        run_date=run_date,
        model=used_model or model,
        prompt_sha=prompt_sha,
        latency_ms=round((time.monotonic() - started) * 1000),
        parsed_ok=True,
        validation="ok" if not validation_notes else "ok; stepped=" + " | ".join(validation_notes),
    )
    return {"status": "ok", "rows": rows, "detail": f"sizer scan_date={scan_date} rows={rows}"}
