"""Vision model pass over chair-ranked agent debate finalists."""
from __future__ import annotations

import base64
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any

from manas_os import config
from manas_os.advisor.client import OpenRouterClient
from manas_os.agents import charts
from manas_os.agents import _shared
from manas_os.agents.debate import ensure_schema

AGENT = "vision"
DEFAULT_TOP_N = 8
LENS_DIR = Path(__file__).resolve().parents[1] / "design" / "agents"
AD8_NOTE = (
    "AD8 anti-anchoring: deterministic composite scores are computed in Python. "
    "Do not invent, alter, or return numeric composite score/rating fields."
)


def _api_key() -> str | None:
    return _shared.api_key()


def _vision_model() -> str | None:
    model = config.get("agents.vision_model")
    if isinstance(model, str) and model.strip():
        return model.strip()
    return None


def _top_n() -> int:
    try:
        return max(1, int(config.get("agents.vision_top_n", DEFAULT_TOP_N) or DEFAULT_TOP_N))
    except (TypeError, ValueError):
        return DEFAULT_TOP_N


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


def _load_chair_rows(conn, scan_date: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT av.symbol, av.verdict, av.conviction, av.rank, av.lens_scores_json, "
        "av.bull_case, av.bear_case, av.reasoning, sc.setup_family, sc.setup "
        "FROM agent_verdicts av LEFT JOIN scan_candidates sc "
        "ON sc.scan_date = av.scan_date AND sc.symbol = av.symbol "
        "WHERE av.scan_date = ? AND av.agent = 'chair' "
        "ORDER BY COALESCE(av.rank, 999999), av.symbol",
        (scan_date,),
    ).fetchall()
    return [dict(row) for row in rows]


def _lens_path(setup_family: str | None, setup: str | None = None) -> Path:
    """Route by the SPECIFIC setup first, family second. Family alone is too
    coarse: 'catalyst' covers both EP and IPO-base, and the old family-only
    match fell through to Strong Start — night 3's vision pass vetoed a
    unanimous 3-TAKE IPO base for 'not matching the Strong Start lens'."""
    text = f"{(setup or '').lower()} {(setup_family or '').lower()}"
    if "pead" in text:
        return LENS_DIR / "LENS_PEAD.md"
    if "ipo" in text:
        return LENS_DIR / "LENS_IPO.md"
    if "htf" in text or "high_tight" in text or "high-tight" in text or "high tight" in text:
        return LENS_DIR / "LENS_HTF.md"
    if "ep" == (setup or "").lower() or "episodic" in text or "earnings" in text or "catalyst" in text:
        return LENS_DIR / "LENS_EP.md"
    return LENS_DIR / "LENS_STRONG_START.md"


def _lens_text(setup_family: str | None, setup: str | None = None) -> str:
    path = _lens_path(setup_family, setup)
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _system_prompt(scan_date: str) -> str:
    return (
        "You are the Manas OS chart vision reviewer. Compare the daily and weekly PNGs "
        "against the supplied setup lens only. "
        f"{_shared.recency_rule(scan_date)} "
        "Return only JSON with action "
        "promote, demote, veto, or hold; magnitude 1-2 only for promote/demote; "
        "what_i_see in at most 3 sentences; and reason."
    )


def _text_prompt(item: dict[str, Any], scan_date: str) -> str:
    return json.dumps(
        {
            "symbol": item["symbol"],
            "scan_date": scan_date,
            "setup": item.get("setup"),
            "setup_family": item.get("setup_family"),
            "chair_verdict": item.get("verdict"),
            "chair_rank": item.get("rank"),
            "chair_reasoning": item.get("reasoning"),
            "lens": _lens_text(item.get("setup_family"), item.get("setup")),
            "anti_anchoring": AD8_NOTE,
            "output_schema": {
                "action": "promote|demote|veto|hold",
                "magnitude": "1-2 for promote/demote",
                "what_i_see": "<=3 sentences",
                "reason": "string",
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


def _extract_json(raw: str) -> Any:
    text = (raw or "").strip()
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0].strip()
    return json.loads(text)


def _validate_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("vision JSON must be an object")
    action = str(payload.get("action") or "").lower().strip()
    if action not in {"promote", "demote", "veto", "hold"}:
        raise ValueError("vision action must be promote, demote, veto, or hold")
    magnitude = 0
    if action in {"promote", "demote"}:
        try:
            magnitude = int(payload.get("magnitude") or 1)
        except (TypeError, ValueError):
            magnitude = 1
        magnitude = max(1, min(2, magnitude))
    return {
        "action": action,
        "magnitude": magnitude,
        "what_i_see": str(payload.get("what_i_see") or "").strip(),
        "reason": str(payload.get("reason") or "").strip(),
    }


def _chat(llm: Any, system: str, user: list[dict[str, Any]]) -> tuple[str, str]:
    return _shared.chat_tuple(llm, system, user)


def _token_set(text: str) -> set[str]:
    return {tok for tok in re.findall(r"[a-z0-9]+", text.lower()) if tok}


def _jaccard(a: str, b: str) -> float:
    """Overlap coefficient (intersection / smaller set), not pure Jaccard:
    paraphrased duplicates commonly differ in length (one side adds
    qualifying words), which dilutes a union-based ratio below any sane
    threshold even when one side is almost entirely contained in the other."""
    sa, sb = _token_set(a), _token_set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / min(len(sa), len(sb))


def _reasoning(payload: dict[str, Any]) -> str:
    what_i_see = str(payload.get("what_i_see") or "").strip()
    reason = str(payload.get("reason") or "").strip()
    # Vision models frequently restate what_i_see inside reason (paraphrased,
    # not identical), which _dedup_paragraphs' exact-match check can't catch.
    # Drop reason at the source when it substantially overlaps what_i_see
    # instead of concatenating near-duplicate prose.
    if what_i_see and reason and _jaccard(what_i_see, reason) > 0.6:
        return what_i_see
    parts = [what_i_see, reason]
    return " ".join(part for part in parts if part)


def _persist_vision_row(
    conn,
    scan_date: str,
    symbol: str,
    payload: dict[str, Any],
    final_rank: int | None,
) -> None:
    action = payload["action"]
    verdict = {"promote": "PROMOTE", "demote": "DEMOTE", "veto": "SKIP", "hold": "HOLD"}[action]
    lens_scores: dict[str, Any] = {"action": action, "magnitude": payload["magnitude"]}
    if payload.get("stale_evidence_warning"):
        # I10 post-check: visible flag on the stored card when what_i_see/reason
        # narrate a month-year older than ~6 months before scan_date — the
        # frontend can surface this without us silently trusting the model.
        lens_scores["stale_evidence_warning"] = payload["stale_evidence_warning"]
    # AU1: upsert instead of INSERT OR REPLACE — a same-night rerun must not
    # null outcome_r/created_at on an existing row (REPLACE = delete+reinsert).
    conn.execute(
        "INSERT INTO agent_verdicts "
        "(scan_date, symbol, agent, verdict, conviction, rank, lens_scores_json, reasoning) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(scan_date, symbol, agent) DO UPDATE SET "
        "verdict=excluded.verdict, conviction=excluded.conviction, rank=excluded.rank, "
        "lens_scores_json=excluded.lens_scores_json, reasoning=excluded.reasoning, "
        "outcome_r=COALESCE(excluded.outcome_r, agent_verdicts.outcome_r), "
        "created_at=agent_verdicts.created_at",
        (
            scan_date,
            symbol,
            AGENT,
            verdict,
            None,
            final_rank,
            json.dumps(lens_scores, sort_keys=True),
            _reasoning(payload),
        ),
    )


def _apply_adjustments(
    conn,
    scan_date: str,
    chair_rows: list[dict[str, Any]],
    payloads: dict[str, dict[str, Any]],
) -> dict[str, int]:
    ranked = []
    for idx, row in enumerate(chair_rows, start=1):
        symbol = row["symbol"]
        original_rank = int(row["rank"] or idx)
        payload = payloads.get(symbol)
        action = payload["action"] if payload else "hold"
        magnitude = int(payload.get("magnitude") or 0) if payload else 0
        delta = -magnitude if action == "promote" else magnitude if action == "demote" else 0
        vetoed = action == "veto"
        verdict = "SKIP" if vetoed else row["verdict"]
        reasoning = row.get("reasoning")
        if vetoed:
            reason = payload.get("reason") or "vision veto"
            reasoning = f"{reasoning or ''}; vision veto: {reason}".strip("; ")
        ranked.append(
            {
                "symbol": symbol,
                "rank_key": original_rank + delta,
                "delta": delta,
                "original_rank": original_rank,
                "skip": 1 if verdict == "SKIP" else 0,
                "verdict": verdict,
                "reasoning": reasoning,
            }
        )
    # Tie on adjusted rank: the vision-moved name wins (delta more negative first) —
    # otherwise a boundary promote is silently a no-op against the incumbent.
    ranked.sort(key=lambda item: (item["skip"], item["rank_key"], item["delta"], item["original_rank"], item["symbol"]))
    final_ranks: dict[str, int] = {}
    for rank, item in enumerate(ranked, start=1):
        final_ranks[item["symbol"]] = rank
        conn.execute(
            "UPDATE agent_verdicts SET verdict = ?, rank = ?, reasoning = ? "
            "WHERE scan_date = ? AND symbol = ? AND agent = 'chair'",
            (item["verdict"], rank, item["reasoning"], scan_date, item["symbol"]),
        )
    return final_ranks


def run(conn, scan_date: str, *, run_date: str | None = None, client: Any | None = None) -> dict[str, Any]:
    run_date = run_date or scan_date
    ensure_schema(conn)
    model = _vision_model()
    if not model:
        return {"status": "skip", "rows": 0, "detail": "vision model unset"}
    key = _api_key()
    if client is None and not key:
        return {"status": "skip", "rows": 0, "detail": "vision api key absent"}

    chair_rows = _load_chair_rows(conn, scan_date)
    finalists = [row for row in chair_rows if row.get("verdict") == "TAKE"][:_top_n()]
    if not finalists:
        return {"status": "skip", "rows": 0, "detail": "vision no chair TAKE finalists"}

    chart_map = charts.render_charts(conn, scan_date, [row["symbol"] for row in finalists])
    llm = client or OpenRouterClient(api_key=key, model=model, max_tokens=int(config.get("agents.max_tokens", 4000) or 4000))
    system = _system_prompt(scan_date)
    payloads: dict[str, dict[str, Any]] = {}
    failures = []

    for item in finalists:
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
            warning = _shared.stale_evidence_warning(
                f"{payload.get('what_i_see', '')} {payload.get('reason', '')}", scan_date
            )
            if warning:
                payload["stale_evidence_warning"] = warning
            payloads[symbol] = payload
            _agent_log(
                conn,
                run_date=run_date,
                model=used_model or model,
                prompt_sha=prompt_sha,
                latency_ms=round((time.monotonic() - call_started) * 1000),
                parsed_ok=True,
                validation="ok",
            )
        except Exception as exc:  # noqa: BLE001
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

    final_ranks = _apply_adjustments(conn, scan_date, chair_rows, payloads)
    for symbol, payload in payloads.items():
        _persist_vision_row(conn, scan_date, symbol, payload, final_ranks.get(symbol))

    rows = len(payloads)
    status = "ok" if rows and not failures else "partial" if failures else "skip"
    detail = f"vision scan_date={scan_date} rows={rows}"
    if failures:
        detail = f"{detail}; failures={' | '.join(failures)}"
    return {"status": status, "rows": rows, "detail": detail, "failures": failures}
