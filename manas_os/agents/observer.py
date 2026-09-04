"""Chart-behaviour observer that runs before the independent debate seats."""
from __future__ import annotations

import base64
import hashlib
import json
import time
from pathlib import Path
from typing import Any

from manas_os import config
from manas_os.advisor.client import OpenRouterClient
from manas_os.agents import charts
from manas_os.agents import _shared
from manas_os.agents.debate import ensure_schema

AGENT = "observer"
LENS_DIR = Path(__file__).resolve().parents[1] / "design" / "agents"

def _api_key() -> str | None:
    return _shared.api_key()

def _vision_model() -> str | None:
    model = config.get("agents.observer_model")
    if isinstance(model, str) and model.strip():
        return model.strip()
    return None

def _agent_log(
    conn,
    *,
    run_date: str,
    model: str | None,
    prompt_sha: str | None,
    latency_ms: int | None,
    parsed_ok: bool,
    validation: str,
    error: str | None = None,
) -> None:
    conn.execute(
        "INSERT INTO scan_agent_logs "
        "(run_date, agent, model, prompt_sha, latency_ms, parsed_ok, validation, error) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (run_date, AGENT, model, prompt_sha, latency_ms, 1 if parsed_ok else 0, validation, error),
    )

def _system_prompt(scan_date: str) -> str:
    return (
        "You are the Manas OS chart observer. Compare the daily and weekly PNGs. "
        "Do not predict targets, stops, sizes, or output a final trade verdict. "
        f"{_shared.recency_rule(scan_date)} "
        "Return only JSON with the following string fields: phase_and_sequence, "
        "supply_demand_behavior, base_age_and_quality, volume_behavior, "
        "stock_vs_group, confirming_evidence, strongest_contradiction, "
        "what_must_happen_next, invalidation_criteria, and a list of strings for plausible_hypotheses."
    )

def _text_prompt(item: dict[str, Any], scan_date: str) -> str:
    return json.dumps(
        {
            "symbol": item["symbol"],
            "scan_date": scan_date,
            "setup": item.get("setup"),
            "setup_family": item.get("setup_family"),
            "output_schema": {
                "phase_and_sequence": "string",
                "supply_demand_behavior": "string",
                "base_age_and_quality": "string",
                "volume_behavior": "string",
                "stock_vs_group": "string",
                "plausible_hypotheses": ["string"],
                "confirming_evidence": "string",
                "strongest_contradiction": "string",
                "what_must_happen_next": "string",
                "invalidation_criteria": "string",
            },
        },
        sort_keys=True,
    )

def _image_part(path: str) -> dict[str, Any]:
    data = base64.b64encode(Path(path).read_bytes()).decode("ascii")
    return {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{data}"}}

def _message_parts(item: dict[str, Any], chart_paths: dict[str, str], scan_date: str) -> list[dict[str, Any]]:
    return [
        {"type": "text", "text": _text_prompt(item, scan_date)},
        _image_part(chart_paths["daily"]),
        _image_part(chart_paths["weekly"]),
    ]


def _persist_observer_row(
    conn,
    scan_date: str,
    symbol: str,
    payload: dict[str, Any],
) -> None:
    # We store the observer's output in the lens_scores_json or reasoning field.
    # Since it's not a verdict, we just put verdict="OBSERVED".
    import json
    conn.execute(
        "INSERT INTO agent_verdicts "
        "(scan_date, symbol, agent, verdict, conviction, rank, lens_scores_json, reasoning) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(scan_date, symbol, agent) DO UPDATE SET "
        "verdict=excluded.verdict, "
        "lens_scores_json=excluded.lens_scores_json, reasoning=excluded.reasoning, "
        "outcome_r=COALESCE(excluded.outcome_r, agent_verdicts.outcome_r), "
        "created_at=agent_verdicts.created_at",
        (
            scan_date,
            symbol,
            "observer",
            "OBSERVED",
            None,
            None,
            json.dumps(payload, sort_keys=True),
            payload.get("phase_and_sequence", ""),
        ),
    )

def _extract_json(raw: str) -> Any:
    text = (raw or "").strip()
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0].strip()
    return json.loads(text)

def _validate_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("observer JSON must be an object")
    return {
        "phase_and_sequence": str(payload.get("phase_and_sequence") or ""),
        "supply_demand_behavior": str(payload.get("supply_demand_behavior") or ""),
        "base_age_and_quality": str(payload.get("base_age_and_quality") or ""),
        "volume_behavior": str(payload.get("volume_behavior") or ""),
        "stock_vs_group": str(payload.get("stock_vs_group") or ""),
        "plausible_hypotheses": payload.get("plausible_hypotheses") or [],
        "confirming_evidence": str(payload.get("confirming_evidence") or ""),
        "strongest_contradiction": str(payload.get("strongest_contradiction") or ""),
        "what_must_happen_next": str(payload.get("what_must_happen_next") or ""),
        "invalidation_criteria": str(payload.get("invalidation_criteria") or ""),
    }

def _chat(llm: Any, system: str, user: list[dict[str, Any]]) -> tuple[str, str]:
    return _shared.chat_tuple(llm, system, user)

def run(conn, scan_date: str, shortlist: list[dict[str, Any]], *, run_date: str | None = None, client: Any | None = None) -> dict[str, Any]:
    run_date = run_date or scan_date
    ensure_schema(conn)
    model = _vision_model()
    if not model:
        return {"status": "skip", "rows": 0, "detail": "vision model unset"}
    key = _api_key()
    if client is None and not key:
        return {"status": "skip", "rows": 0, "detail": "vision api key absent"}

    if not shortlist:
        return {"status": "skip", "rows": 0, "detail": "observer no shortlist given"}

    chart_map = charts.render_charts(conn, scan_date, [row["symbol"] for row in shortlist])
    llm = client or OpenRouterClient(api_key=key, model=model, max_tokens=int(config.get("agents.max_tokens", 4000) or 4000))
    system = _system_prompt(scan_date)
    payloads: dict[str, dict[str, Any]] = {}
    failures = []

    for item in shortlist:
        symbol = item["symbol"]
        paths = chart_map.get(symbol) or {}
        if not paths.get("daily") or not paths.get("weekly"):
            error = paths.get("note") or "missing daily/weekly chart"
            failures.append(f"{symbol}: {error}")
            _agent_log(conn, run_date=run_date, model=model, prompt_sha=None, latency_ms=None, parsed_ok=False, validation="fail", error=error)
            continue
        call_started = time.monotonic()
        prompt_sha = None
        try:
            user = _message_parts(item, paths, scan_date)
            prompt_sha = hashlib.sha256(json.dumps(user, sort_keys=True).encode("utf-8")).hexdigest()
            raw, used_model = _chat(llm, system, user)
            payload = _validate_payload(_extract_json(raw))
            combined_text = " ".join(
                [
                    payload.get("phase_and_sequence", ""),
                    payload.get("supply_demand_behavior", ""),
                    payload.get("base_age_and_quality", ""),
                    payload.get("volume_behavior", ""),
                    payload.get("stock_vs_group", ""),
                    payload.get("confirming_evidence", ""),
                    payload.get("strongest_contradiction", ""),
                    payload.get("what_must_happen_next", ""),
                    payload.get("invalidation_criteria", ""),
                    " ".join(payload.get("plausible_hypotheses") or []),
                ]
            )
            warning = _shared.stale_evidence_warning(combined_text, scan_date)
            if warning:
                # I10 post-check: visible flag on the stored card, not a silent
                # accept, when the observer narrates a month-year older than
                # ~6 months before scan_date (e.g. a stale chart region).
                payload["stale_evidence_warning"] = warning
            payloads[symbol] = payload
            _persist_observer_row(conn, scan_date, symbol, payload)
            _agent_log(
                conn,
                run_date=run_date,
                model=used_model or model,
                prompt_sha=prompt_sha,
                latency_ms=round((time.monotonic() - call_started) * 1000),
                parsed_ok=True,
                validation="ok",
            )
        except Exception as exc:
            failures.append(f"{symbol}: {exc}")
            _agent_log(
                conn,
                run_date=run_date,
                model=model,
                prompt_sha=prompt_sha,
                latency_ms=round((time.monotonic() - call_started) * 1000),
                parsed_ok=False,
                validation="fail",
                error=str(exc),
            )

    rows = len(payloads)
    status = "ok" if rows and not failures else "partial" if failures else "skip"
    detail = f"observer scan_date={scan_date} rows={rows}"
    if failures:
        detail = f"{detail}; failures={' | '.join(failures)}"
    return {"status": status, "rows": rows, "detail": detail, "failures": failures, "payloads": payloads}

