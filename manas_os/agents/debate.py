"""Agent debate overlay for persisted deterministic scan candidates.

This stage is additive: it reads scan_candidates and writes only agent tables.
It never writes candidates/refusals, and it never computes trade plan numbers.
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
from manas_os.agents import context_pack

STAGE = "agents_debate"
SOURCE = "agent_verdicts"
DEFAULT_SHORTLIST_SIZE = 15


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
    agent: str,
    model: str | None,
    prompt_sha: str | None,
    latency_ms: int | None,
    tokens_in: int | None = None,
    tokens_out: int | None = None,
    parsed_ok: bool = False,
    validation: str | None = None,
    error: str | None = None,
) -> None:
    conn.execute(
        "INSERT INTO scan_agent_logs "
        "(run_date, agent, model, prompt_sha, latency_ms, tokens_in, tokens_out, parsed_ok, validation, error) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            run_date,
            agent,
            model,
            prompt_sha,
            latency_ms,
            tokens_in,
            tokens_out,
            1 if parsed_ok else 0,
            validation,
            error,
        ),
    )


def _shortlist_size() -> int:
    try:
        return max(1, int(config.get("agents.shortlist_size", DEFAULT_SHORTLIST_SIZE) or DEFAULT_SHORTLIST_SIZE))
    except (TypeError, ValueError):
        return DEFAULT_SHORTLIST_SIZE


def _models() -> list[str]:
    models = config.get("agents.models")
    if isinstance(models, str) and models.strip():
        return [models.strip()]
    if isinstance(models, list):
        out = [str(m).strip() for m in models if str(m).strip()]
        if out:
            return out
    return [str(config.get("agents.model", "deepseek/deepseek-chat"))]


def _api_key() -> str | None:
    _load_env_file()
    return config.get("agents.api_key") or config.get("advisor.api_key") or os.environ.get("OPENROUTER_API_KEY")


def _load_shortlist(conn, run_date: str, limit: int) -> tuple[str | None, list[dict[str, Any]]]:
    # R1 (code-review, folded into B1a): scan_candidates already persists the full
    # cascade pass list (see scanner/candidates.py persist path) — verified complete,
    # no persistence change needed here; this just reads the top `limit` of it.
    row = conn.execute(
        "SELECT MAX(scan_date) AS d FROM scan_candidates WHERE scan_date <= ?",
        (run_date,),
    ).fetchone()
    if not row or not row["d"]:
        return None, []
    scan_date = row["d"]
    rows = conn.execute(
        "SELECT scan_date, symbol, setup, setup_family, readiness, grade, rank, rank_of, "
        "entry, stop, rr, suggested_qty, evidence_json, timing_json, score_breakdown_json, "
        "trade_plan_json, gates_json, sector, industry "
        "FROM scan_candidates WHERE scan_date = ? "
        "ORDER BY COALESCE(rank, 999999), readiness DESC, symbol LIMIT ?",
        (scan_date, limit),
    ).fetchall()
    out = []
    for row in rows:
        item = dict(row)
        for key, fallback in {
            "evidence_json": [],
            "timing_json": {},
            "score_breakdown_json": {},
            "trade_plan_json": {},
            "gates_json": [],
        }.items():
            try:
                item[key[:-5] if key.endswith("_json") else key] = json.loads(item.pop(key) or json.dumps(fallback))
            except json.JSONDecodeError:
                item[key[:-5] if key.endswith("_json") else key] = fallback
        out.append(item)
    return scan_date, out


def _system_prompt() -> str:
    return (
        "You are the Manas OS debate layer. The deterministic scanner already created "
        "the shortlist and risk/plan.py already computed entry, stop, target, R:R, and qty. "
        "Do not output or alter plan numbers. Judge the shortlist comparatively through "
        "Strong Start, EP theme, IPO base, high tight flag, and PEAD drift lenses.\n\n"
        "Return only JSON: an array of objects with symbol, verdict (TAKE or SKIP), "
        "conviction (integer 1-5), rank (integer, 1 is best), lens_scores (object), "
        "bull_case, bear_case, and reasoning. No markdown."
    )


def _user_prompt(conn, scan_date: str, shortlist: list[dict[str, Any]]) -> str:
    return context_pack.build_pack_json(conn, scan_date, shortlist)


def _extract_json(raw: str) -> Any:
    text = (raw or "").strip()
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0].strip()
    return json.loads(text)


def _skip_note(item: Any, reason: str) -> str:
    if isinstance(item, dict):
        symbol = str(item.get("symbol") or "?").upper().strip() or "?"
    else:
        symbol = "?"
    return f"{symbol}({reason})"


def _validate_payload(payload: Any, symbols: set[str]) -> tuple[list[dict[str, Any]], str]:
    if isinstance(payload, dict) and isinstance(payload.get("verdicts"), list):
        payload = payload["verdicts"]
    if not isinstance(payload, list):
        raise ValueError("model JSON must be an array")
    out = []
    skipped = []
    for item in payload:
        if not isinstance(item, dict):
            skipped.append(_skip_note(item, "not object"))
            continue
        symbol = str(item.get("symbol") or "").upper().strip()
        if symbol not in symbols:
            skipped.append(_skip_note(item, "unknown symbol"))
            continue
        # AD8 anti-anchoring: composite scores/ratings are computed deterministically
        # in Python; the LLM must not be allowed to invent its own composite number.
        # Allowed numeric fields beyond identity/verdict are: conviction, rank, lens_scores.
        allowed_keys = {"symbol", "verdict", "decision", "conviction", "rank",
                        "lens_scores", "lens_scores_json", "bull_case", "bear_case",
                        "reasoning", "read"}
        for key, value in item.items():
            if key in allowed_keys:
                continue
            key_lower = key.lower()
            if ("score" in key_lower or "rating" in key_lower) and isinstance(value, (int, float)) and not isinstance(value, bool):
                skipped.append(_skip_note(item, f"disallowed composite field {key!r}"))
                item = None
                break
        if item is None:
            continue
        verdict = str(item.get("verdict") or item.get("decision") or "").upper().strip()
        if verdict not in {"TAKE", "SKIP"}:
            skipped.append(_skip_note(item, "bad verdict"))
            continue
        try:
            conviction = int(item.get("conviction") or 0)
        except (TypeError, ValueError):
            conviction = 0
        if conviction < 1 or conviction > 5:
            skipped.append(_skip_note(item, "bad conviction"))
            continue
        rank = item.get("rank")
        try:
            rank = int(rank) if rank is not None else None
        except (TypeError, ValueError):
            rank = None
        out.append({
            "symbol": symbol,
            "verdict": verdict,
            "conviction": conviction,
            "rank": rank,
            "lens_scores": item.get("lens_scores") or item.get("lens_scores_json") or {},
            "bull_case": item.get("bull_case"),
            "bear_case": item.get("bear_case"),
            "reasoning": item.get("reasoning") or item.get("read"),
        })
    if not out:
        detail = f"; skipped={len(skipped)}: {','.join(skipped)}" if skipped else ""
        raise ValueError(f"model returned no valid shortlist verdicts{detail}")
    validation = "ok"
    if skipped:
        validation = f"skipped={len(skipped)}: {','.join(skipped)}"
    return out, validation


def _unpack_chat(result: Any, default_model: str) -> tuple[str, str, dict[str, Any] | None]:
    if not isinstance(result, tuple):
        raise ValueError("client.chat must return a tuple")
    if len(result) == 2:
        raw, used_model = result
        return raw, used_model or default_model, None
    if len(result) == 3:
        raw, used_model, usage = result
        return raw, used_model or default_model, usage if isinstance(usage, dict) else None
    raise ValueError("client.chat must return (content, model) or (content, model, usage)")


def _chat(llm: Any, system: str, user: str) -> Any:
    if isinstance(llm, OpenRouterClient):
        return llm.chat(system=system, user=user, include_usage=True)
    return llm.chat(system=system, user=user)


def _usage_tokens(usage: dict[str, Any] | None, user: str, raw: str) -> tuple[int, int, str | None]:
    if usage:
        prompt = usage.get("prompt_tokens")
        completion = usage.get("completion_tokens")
        try:
            if prompt is not None and completion is not None:
                return int(prompt), int(completion), None
        except (TypeError, ValueError):
            pass
    return len(user.split()), len(raw.split()), "tokens=approx"


def _validation_note(base: str, token_note: str | None) -> str:
    if token_note:
        return f"{base}; {token_note}"
    return base


def _persist_verdicts(conn, scan_date: str, agent: str, verdicts: list[dict[str, Any]]) -> int:
    for item in verdicts:
        conn.execute(
            "INSERT OR REPLACE INTO agent_verdicts "
            "(scan_date, symbol, agent, verdict, conviction, rank, lens_scores_json, bull_case, bear_case, reasoning) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                scan_date,
                item["symbol"],
                agent,
                item["verdict"],
                item["conviction"],
                item.get("rank"),
                json.dumps(item.get("lens_scores") or {}, sort_keys=True),
                item.get("bull_case"),
                item.get("bear_case"),
                item.get("reasoning"),
            ),
        )
    return len(verdicts)


def run(conn, run_date: str, client: Any | None = None) -> dict[str, Any]:
    """Run debate verdicts over the latest persisted deterministic shortlist."""
    started = time.monotonic()
    ensure_schema(conn)
    key = _api_key()
    enabled = bool(config.get("agents.enabled", bool(key)))
    if not enabled or (client is None and not key):
        _pipeline_log(conn, run_date, "skip", 0, started, "agents config/api key absent")
        conn.commit()
        return {"status": "skip", "rows": 0, "detail": "agents config/api key absent"}

    limit = _shortlist_size()
    scan_date, shortlist = _load_shortlist(conn, run_date, limit)
    if not scan_date or not shortlist:
        _pipeline_log(conn, run_date, "skip", 0, started, "no persisted scan_candidates shortlist")
        conn.commit()
        return {"status": "skip", "rows": 0, "detail": "no shortlist"}

    system = _system_prompt()
    user = _user_prompt(conn, scan_date, shortlist)
    symbols = {str(item["symbol"]).upper() for item in shortlist}
    rows = 0
    errors = []

    for model in _models():
        llm = client or OpenRouterClient(api_key=key, model=model, max_tokens=int(config.get("agents.max_tokens", 4000) or 4000))
        attempt_user = user
        last_error = None
        for attempt in range(2):
            call_started = time.monotonic()
            raw = ""
            used_model = model
            usage = None
            attempt_prompt_sha = hashlib.sha256((system + "\n" + attempt_user).encode("utf-8")).hexdigest()
            try:
                raw, used_model, usage = _unpack_chat(_chat(llm, system, attempt_user), model)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                tokens_in, tokens_out, token_note = _usage_tokens(usage, attempt_user, raw)
                _agent_log(
                    conn,
                    run_date=run_date,
                    agent=used_model,
                    model=used_model,
                    prompt_sha=attempt_prompt_sha,
                    latency_ms=round((time.monotonic() - call_started) * 1000),
                    tokens_in=tokens_in,
                    tokens_out=tokens_out if raw else None,
                    parsed_ok=False,
                    validation=_validation_note("fail", token_note),
                    error=str(exc),
                )
                break
            try:
                verdicts, validation = _validate_payload(_extract_json(raw), symbols)
                tokens_in, tokens_out, token_note = _usage_tokens(usage, attempt_user, raw)
                rows += _persist_verdicts(conn, scan_date, used_model, verdicts)
                _agent_log(
                    conn,
                    run_date=run_date,
                    agent=used_model,
                    model=used_model,
                    prompt_sha=attempt_prompt_sha,
                    latency_ms=round((time.monotonic() - call_started) * 1000),
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    parsed_ok=True,
                    validation=_validation_note(validation, token_note),
                )
                last_error = None
                break
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                tokens_in, tokens_out, token_note = _usage_tokens(usage, attempt_user, raw)
                _agent_log(
                    conn,
                    run_date=run_date,
                    agent=used_model,
                    model=used_model,
                    prompt_sha=attempt_prompt_sha,
                    latency_ms=round((time.monotonic() - call_started) * 1000),
                    tokens_in=tokens_in,
                    tokens_out=tokens_out if raw else None,
                    parsed_ok=False,
                    validation=_validation_note("fail", token_note),
                    error=str(exc),
                )
                if attempt == 0:
                    attempt_user = (
                        f"{user}\n\nYour previous response failed: {exc}. "
                        "Return ONLY the JSON array, no markdown."
                    )
                    continue
        if last_error is not None:
            errors.append(f"{model}: {last_error}")

    status = "ok" if rows else "fail"
    detail = f"scan_date={scan_date} shortlist={len(shortlist)} verdicts={rows}"
    if errors:
        detail = f"{detail}; errors={' | '.join(errors)}"
    _pipeline_log(conn, run_date, status, rows, started, detail)
    conn.commit()
    return {"status": status, "rows": rows, "as_of": scan_date, "shortlist_size": len(shortlist), "detail": detail}
