"""Agent debate overlay for persisted deterministic scan candidates.

This stage is additive: it reads scan_candidates and writes only agent tables.
It never writes candidates/refusals, and it never computes trade plan numbers.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from typing import Any

from manas_os import config
from manas_os.advisor.client import OpenRouterClient
from manas_os.agents import context_pack
from manas_os.agents import _shared
from manas_os.scanner.candidates import ensure_refusals_schema

STAGE = "agents_debate"
SOURCE = "agent_verdicts"
DEFAULT_SHORTLIST_SIZE = 15
# G1: debate must cover at least this many names when the deterministic gate
# has enough refusals to fill from — the gate keeps refusing (real trades
# stay gated on scan_candidates membership); this only widens what the LLMs
# get to argue about, so a 1-stock night stays honest instead of silent.
SHORTLIST_FLOOR = 10
# WO6: only these gates are "almost there" — a name that failed one of these
# is worth a real debate turn. Hard-fails (regime/tradability/risk) are
# structurally untradeable (delisted-risk, pump signature, no valid stop) and
# get zero LLM tokens; they still land on the watchlist tagged NEAR_MISS(hard:
# <gate>) so a human can see them, but the debate pool never pads with them.
SOFT_GATES = {"trend-template", "fresh-leg", "participation"}


def ensure_schema(conn) -> None:
    _shared.ensure_agent_tables(conn)


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
    return _shared.models()


def _config_seconds(key: str, default: float) -> float:
    try:
        configured = config.get(key, default)
        value = float(default if configured is None else configured)
    except (TypeError, ValueError):
        return default
    return max(0.0, value)


def _status_code(exc: Exception) -> int | None:
    for attr in ("status_code", "code"):
        value = getattr(exc, attr, None)
        try:
            if value is not None:
                return int(value)
        except (TypeError, ValueError):
            pass
    response = getattr(exc, "response", None)
    value = getattr(response, "status_code", None)
    try:
        if value is not None:
            return int(value)
    except (TypeError, ValueError):
        pass
    return None


def _is_http_429(exc: Exception) -> bool:
    if _status_code(exc) == 429:
        return True
    text = str(exc).lower()
    return "429" in text and ("http" in text or "rate" in text)


def _api_key() -> str | None:
    return _shared.api_key()


def _load_survivors(conn, scan_date: str, limit: int) -> list[dict[str, Any]]:
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
        item["tier"] = "PASSED"
        out.append(item)
    return out


def _near_miss_sort_key(row: dict[str, Any]) -> tuple[int, float, str]:
    """Closest-to-passing first. Tradability refusals are structural (hard-no)
    and sort last — they are not "almost there" the way a fresh-leg/risk/
    participation near-miss is. `refusals` stores one failed_gate per symbol
    (the last cascade gate that tripped), so this is the closest proxy to
    "fewest failed gates" the schema supports without widening `refusals`."""
    gate = str(row.get("failed_gate") or "").lower()
    hard = 1 if "trad" in gate else 0
    reason = str(row.get("reason") or "")
    numbers = [float(x) for x in re.findall(r"[-+]?\d+(?:\.\d+)?", reason)]
    distance = abs(numbers[0] - numbers[1]) if len(numbers) >= 2 else float("inf")
    return (hard, distance, str(row.get("symbol") or ""))


def _near_miss_item(scan_date: str, row: dict[str, Any]) -> dict[str, Any]:
    return {
        "scan_date": scan_date,
        "symbol": row["symbol"],
        "setup": None,
        "setup_family": row.get("setup_family"),
        "readiness": None,
        "grade": None,
        "rank": None,
        "rank_of": None,
        "entry": None,
        "stop": None,
        "rr": None,
        "suggested_qty": None,
        "evidence": [],
        "timing": {},
        "score_breakdown": {},
        "trade_plan": {},
        "gates": [],
        "sector": None,
        "industry": None,
        "tier": "NEAR_MISS",
        "failed_gate": row.get("failed_gate"),
        "near_miss_reason": row.get("reason"),
    }


def _load_all_refusals(conn, scan_date: str, exclude: set[str]) -> list[dict[str, Any]]:
    ensure_refusals_schema(conn)
    rows = conn.execute(
        "SELECT scan_date, symbol, setup_family, failed_gate, reason, evidence_json "
        "FROM refusals WHERE scan_date = ?",
        (scan_date,),
    ).fetchall()
    return [dict(r) for r in rows if str(r["symbol"]).upper() not in exclude]


def _load_shortlist(
    conn, run_date: str, limit: int
) -> tuple[str | None, list[dict[str, Any]], list[dict[str, Any]]]:
    # R1 (code-review, folded into B1a): scan_candidates already persists the full
    # cascade pass list (see scanner/candidates.py persist path) — verified complete,
    # no persistence change needed here; this just reads the top `limit` of it.
    row = conn.execute(
        "SELECT MAX(scan_date) AS d FROM scan_candidates WHERE scan_date <= ?",
        (run_date,),
    ).fetchone()
    if not row or not row["d"]:
        return None, [], []
    scan_date = row["d"]
    survivors = _load_survivors(conn, scan_date, limit)

    # WO6 selector: gate survivors fill the pool first; remaining slots (up to
    # the floor) come ONLY from SOFT-gate near-misses (trend-template,
    # fresh-leg, participation), ranked closest-to-passing. Hard-gate
    # near-misses (regime/tradability/risk) are structurally untradeable and
    # are EXCLUDED from the debate pool entirely — no padding to reach the
    # floor with theater. If fewer soft near-misses qualify than needed, the
    # pool is simply smaller than the floor; it is never padded with hard
    # fails. This never changes what the deterministic gate refuses —
    # sizer/signals still INNER JOIN scan_candidates, so a NEAR_MISS symbol
    # (refusals-only, no scan_candidates row) can never produce a live trade
    # signal no matter what the debate concludes.
    floor = min(SHORTLIST_FLOOR, limit)
    needed = max(0, floor - len(survivors))
    exclude = {str(item["symbol"]).upper() for item in survivors}
    all_misses = _load_all_refusals(conn, scan_date, exclude)
    soft = sorted(
        (r for r in all_misses if str(r.get("failed_gate") or "").lower() in SOFT_GATES),
        key=_near_miss_sort_key,
    )
    hard = [r for r in all_misses if str(r.get("failed_gate") or "").lower() not in SOFT_GATES]
    soft_selected = soft[:needed]
    near_misses = [_near_miss_item(scan_date, r) for r in soft_selected]
    hard_near_misses = [
        {
            "symbol": r["symbol"],
            "setup_family": r.get("setup_family"),
            "failed_gate": r.get("failed_gate"),
            "reason": r.get("reason"),
        }
        for r in hard
    ]
    return scan_date, survivors + near_misses, hard_near_misses


def _system_prompt() -> str:
    return (
        "You are the Manas OS debate layer. The deterministic scanner already created "
        "the shortlist and risk/plan.py already computed entry, stop, target, R:R, and qty. "
        "Do not output or alter plan numbers. Judge the shortlist comparatively through "
        "Strong Start, EP theme, IPO base, high tight flag, and PEAD drift lenses.\n\n"
        "Some shortlist items carry tier: NEAR_MISS with a near_miss block "
        "(failed_gate + reason) — the deterministic gate already refused these; "
        "argue with full honesty about the stated failure (e.g. 'failed gate: "
        "fresh-leg — extended 9%'), do not pretend the failure did not happen, "
        "and default to SKIP for a NEAR_MISS unless the case for TAKE explicitly "
        "argues the failure is minor and about to resolve.\n\n"
        "Return only JSON: an array of objects with symbol, verdict (TAKE or SKIP), "
        "conviction (integer 1-5), rank (integer, 1 is best), lens_scores (object), "
        "bull_case, bear_case, and reasoning. No markdown."
    )


def _user_prompt(conn, scan_date: str, shortlist: list[dict[str, Any]]) -> str:
    families = sorted({str(item.get("setup_family") or "").strip() for item in shortlist if item.get("setup_family")})
    return context_pack.build_pack_json(conn, scan_date, shortlist, families=families)


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
    return _shared.unpack_chat(result, default_model)


def _chat(llm: Any, system: str, user: str) -> Any:
    return _shared.chat_with_usage(llm, system, user)


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


def _persist_verdicts(
    conn,
    scan_date: str,
    agent: str,
    verdicts: list[dict[str, Any]],
    tier_by_symbol: dict[str, str] | None = None,
) -> int:
    # AU1: upsert instead of INSERT OR REPLACE — a same-night rerun must not
    # null outcome_r/created_at on an existing row (REPLACE = delete+reinsert).
    tier_by_symbol = tier_by_symbol or {}
    for item in verdicts:
        conn.execute(
            "INSERT INTO agent_verdicts "
            "(scan_date, symbol, agent, verdict, conviction, rank, lens_scores_json, bull_case, bear_case, reasoning, tier) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(scan_date, symbol, agent) DO UPDATE SET "
            "verdict=excluded.verdict, conviction=excluded.conviction, rank=excluded.rank, "
            "lens_scores_json=excluded.lens_scores_json, bull_case=excluded.bull_case, "
            "bear_case=excluded.bear_case, reasoning=excluded.reasoning, "
            "outcome_r=COALESCE(excluded.outcome_r, agent_verdicts.outcome_r), "
            "tier=COALESCE(excluded.tier, agent_verdicts.tier), "
            "created_at=agent_verdicts.created_at",
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
                tier_by_symbol.get(item["symbol"]),
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
    scan_date, shortlist, hard_near_misses = _load_shortlist(conn, run_date, limit)
    if not scan_date or (not shortlist and not hard_near_misses):
        _pipeline_log(conn, run_date, "skip", 0, started, "no persisted scan_candidates shortlist")
        conn.commit()
        return {"status": "skip", "rows": 0, "detail": "no shortlist"}
    if not shortlist:
        # Every refusal tonight was a hard fail — nothing worth debating, but
        # the hard near-misses still need to land on the watchlist.
        from manas_os.agents import watchlist as watchlist_module

        watchlist_result = watchlist_module.compute(conn, scan_date, hard_near_misses=hard_near_misses)
        detail = f"scan_date={scan_date} shortlist=0 verdicts=0; {watchlist_result.get('detail')}"
        _pipeline_log(conn, run_date, "skip", 0, started, detail)
        conn.commit()
        return {"status": "skip", "rows": 0, "as_of": scan_date, "shortlist_size": 0, "detail": detail}

    system = _system_prompt()
    user = _user_prompt(conn, scan_date, shortlist)
    symbols = {str(item["symbol"]).upper() for item in shortlist}
    tier_by_symbol = {str(item["symbol"]).upper(): item.get("tier") or "PASSED" for item in shortlist}
    rows = 0
    errors = []

    for model_index, model in enumerate(_models()):
        if client is None and model_index > 0:
            time.sleep(_config_seconds("agents.call_gap_s", 15.0))
        llm = client or OpenRouterClient(api_key=key, model=model, max_tokens=int(config.get("agents.max_tokens", 4000) or 4000))
        attempt_user = user
        last_error = None
        json_attempt = 0
        retried_429 = False
        while json_attempt < 2:
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
                if _is_http_429(exc) and not retried_429:
                    retried_429 = True
                    if client is None:
                        time.sleep(_config_seconds("agents.rate_limit_backoff_s", 60.0))
                    continue
                break
            try:
                verdicts, validation = _validate_payload(_extract_json(raw), symbols)
                tokens_in, tokens_out, token_note = _usage_tokens(usage, attempt_user, raw)
                rows += _persist_verdicts(conn, scan_date, used_model, verdicts, tier_by_symbol)
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
                if json_attempt == 0:
                    attempt_user = (
                        f"{user}\n\nYour previous response failed: {exc}. "
                        "Return ONLY the JSON array, no markdown."
                    )
                    json_attempt += 1
                    continue
                break
        if last_error is not None:
            errors.append(f"{model}: {last_error}")
        # Durability: commit after EVERY model's verdicts+logs land. Slow free
        # models can stretch a night to many minutes; a kill mid-stage must not
        # roll back the calls that already succeeded (first live run lost all
        # its work to a single end-of-stage commit).
        conn.commit()

    # G1: charts for EVERY debated name (not just chair TAKE finalists), so the
    # UI never shows "png unavailable" for a card that made it into the debate.
    # Independent of chair/vision — a thin-history symbol just skips (charts.py
    # is already failure-safe per symbol).
    from manas_os.agents import charts as charts_module

    charts_module.render_charts(conn, scan_date, [item["symbol"] for item in shortlist])

    chair_result = None
    if rows:
        from manas_os.agents import chair

        chair_result = chair.run(conn, scan_date, run_date=run_date, client=client, log_pipeline=False)
        rows += int(chair_result.get("rows") or 0)

    # Watchlist runs regardless of whether the debate itself produced rows —
    # hard-fail near-misses (no verdicts, no tokens spent) still need to land
    # so a human can see them.
    from manas_os.agents import watchlist as watchlist_module

    watchlist_result = watchlist_module.compute(conn, scan_date, hard_near_misses=hard_near_misses)
    detail_watchlist = watchlist_result.get("detail")

    status = "ok" if rows else "fail"
    if chair_result and chair_result.get("status") == "partial":
        status = "partial"
    detail = f"scan_date={scan_date} shortlist={len(shortlist)} verdicts={rows}"
    if chair_result:
        detail = f"{detail}; chair={chair_result['status']}"
        if detail_watchlist:
            detail = f"{detail}; {detail_watchlist}"
        from manas_os.agents import vision

        vision_result = vision.run(conn, scan_date, run_date=run_date, client=client)
        rows += int(vision_result.get("rows") or 0)
        detail = f"{detail}; vision={vision_result['status']}"
        if vision_result.get("detail"):
            detail = f"{detail} ({vision_result['detail']})"
        if vision_result.get("status") == "partial" and status == "ok":
            status = "partial"
        # Sizer runs regardless of the vision pass — vision is an optional rank
        # adjuster (skips when no vision model is configured); sizing is core.
        from manas_os.agents import sizer

        sizer_result = sizer.run(conn, scan_date, run_date=run_date, client=client)
        rows += int(sizer_result.get("rows") or 0)
        detail = f"{detail}; sizer={sizer_result['status']}"
        if sizer_result.get("detail"):
            detail = f"{detail} ({sizer_result['detail']})"
        if sizer_result.get("status") == "partial" and status == "ok":
            status = "partial"
        from manas_os.agents import signals

        signals_result = signals.run(conn, scan_date, run_date=run_date)
        rows += int(signals_result.get("rows") or 0)
        detail = f"{detail}; signals={signals_result['status']}"
        if signals_result.get("detail"):
            detail = f"{detail} ({signals_result['detail']})"
        if signals_result.get("status") == "partial" and status == "ok":
            status = "partial"
    if errors:
        detail = f"{detail}; errors={' | '.join(errors)}"
    _pipeline_log(conn, run_date, status, rows, started, detail)
    conn.commit()
    return {"status": status, "rows": rows, "as_of": scan_date, "shortlist_size": len(shortlist), "detail": detail}
