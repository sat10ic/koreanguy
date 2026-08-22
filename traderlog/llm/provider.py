"""Provider-agnostic LLM access.

Call sites ask for a TIER (`cheap`, `smart`, `vision`), never a model. Model ids
live only in config. That indirection is the entire reason this project can move
from free models to paid models to a local model without touching parsing code.

Each tier is an ORDERED FALLBACK CHAIN, not a single model. Free and stealth
endpoints get renamed or withdrawn without notice, and a pipeline that names one
model dies the day that happens. The provider walks the chain and records which
model actually answered in `llm_runs.model`.

Every call — success or failure — writes an `llm_runs` row. That ledger is what
makes "should we pay for the smart tier?" a measurement instead of an argument.

HTTP is plain urllib, adopted from manas_os/advisor/client.py (2026-08-23). No
vendor SDK, so swapping providers never means swapping a dependency.
"""
from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from traderlog import config
from traderlog.db import now_iso

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Reasoning/hybrid models emit their answer via message.reasoning_content or
# message.reasoning when max_tokens is spent on chain-of-thought before any
# `content` is written. Adopted from manas_os/advisor/client.py, which learned
# this the hard way. Match is substring-based so version suffixes still hit.
REASONING_HINTS = ("thinking", "reasoning", "-r1", "deepseek-v4", "glm-5", "o1", "o3")
REASONING_MIN_MAX_TOKENS = 8000

TIERS = ("cheap", "smart", "vision")


class ProviderError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ProviderExhausted(RuntimeError):
    """Every model in the tier's chain failed. Includes each failure."""

    def __init__(self, tier: str, failures: list[tuple[str, str]]) -> None:
        detail = "; ".join(f"{m}: {e}" for m, e in failures)
        super().__init__(f"tier '{tier}' exhausted after {len(failures)} attempts — {detail}")
        self.tier = tier
        self.failures = failures


class BudgetExceeded(RuntimeError):
    pass


@dataclass
class ProviderResult:
    content: Any                       # str, or parsed dict when json_schema=True
    model: str
    provider: str
    usage: dict[str, Any] = field(default_factory=dict)
    cost_usd: float = 0.0
    latency_ms: int = 0
    attempts: int = 1
    run_id: int | None = None


# ---------------------------------------------------------------------------
# tier resolution
# ---------------------------------------------------------------------------

def chain_for(tier: str) -> list[str]:
    """Ordered model ids for a tier. Accepts a string or a list in config."""
    if tier not in TIERS:
        raise ValueError(f"unknown tier {tier!r}; expected one of {TIERS}")
    raw = config.get(f"llm.tiers.{tier}")
    if raw is None:
        raise ProviderError(f"no models configured for tier '{tier}' (llm.tiers.{tier})")
    models = [raw] if isinstance(raw, str) else list(raw)
    models = [m for m in models if m and str(m).strip()]
    if not models:
        raise ProviderError(f"tier '{tier}' has an empty model chain")
    return models


def _is_reasoning(model: str) -> bool:
    lowered = model.lower()
    return any(hint in lowered for hint in REASONING_HINTS)


def _is_free(model: str) -> bool:
    return model.endswith(":free")


# ---------------------------------------------------------------------------
# response parsing
# ---------------------------------------------------------------------------

def _extract_final_answer(text: str) -> str:
    """Pull a final answer out of a reasoning trace when `content` came back empty."""
    if not text:
        return text
    lowered = text.lower()
    for marker in ("final answer:", "final answer", "answer:", "so the answer is"):
        idx = lowered.rfind(marker)
        if idx != -1:
            candidate = text[idx + len(marker):].strip(" :\n\t")
            if candidate:
                return candidate
    return text.strip()


def _parse_json(text: str) -> Any:
    """Parse model output as JSON, tolerating fenced blocks and leading prose.

    Models wrap JSON in ```json fences or preface it with a sentence often enough
    that failing on it would mean failing on working output. This does NOT repair
    malformed JSON — a genuinely broken response must raise so the chain falls
    through to the next model rather than silently storing garbage.
    """
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1] if "\n" in text else text
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
        text = text.strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = min((i for i in (text.find("{"), text.find("[")) if i != -1), default=-1)
        if start != -1:
            end = max(text.rfind("}"), text.rfind("]"))
            if end > start:
                return json.loads(text[start:end + 1])
        raise


# ---------------------------------------------------------------------------
# backends
# ---------------------------------------------------------------------------

def _post_json(url: str, payload: dict, headers: dict, timeout_s: int) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # Never include the response body: upstream errors can echo request
        # metadata back. The status is enough to decide retry vs fall through.
        raise ProviderError(f"HTTP {exc.code}", status_code=exc.code) from exc
    except urllib.error.URLError as exc:
        raise ProviderError(f"request failed: {exc.reason}") from exc


def _call_openrouter(
    model: str, system: str, user: Any, max_tokens: int, timeout_s: int, json_mode: bool
) -> tuple[str, dict]:
    api_key = config.env("OPENROUTER_API_KEY")
    if not api_key:
        raise ProviderError("OPENROUTER_API_KEY missing from environment/.env")

    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.0,  # extraction, not writing — determinism is the point
    }
    if _is_reasoning(model):
        max_tokens = max(max_tokens, REASONING_MIN_MAX_TOKENS)
        payload["reasoning"] = {"effort": "low"}
    payload["max_tokens"] = max_tokens
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    data = _post_json(
        OPENROUTER_URL,
        payload,
        {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/sat10ic/koreanguy",
            "X-Title": "TraderLog",
        },
        timeout_s,
    )

    choices = data.get("choices") or []
    if not choices:
        raise ProviderError(f"empty choices from {model}")
    message = choices[0].get("message") or {}
    content = (message.get("content") or "").strip()
    if not content:
        for key in ("reasoning_content", "reasoning"):
            trace = (message.get(key) or "").strip()
            if trace:
                content = _extract_final_answer(trace)
                logger.warning("%s returned empty content; recovered from %s", model, key)
                break
    if not content:
        raise ProviderError(f"empty content from {model}")
    return content, (data.get("usage") or {})


def _call_ollama(
    model: str, system: str, user: Any, max_tokens: int, timeout_s: int, json_mode: bool
) -> tuple[str, dict]:
    """Local backend. Same message shape, so prompts need no changes (W8)."""
    base = config.get("ollama.base_url", "http://127.0.0.1:11434").rstrip("/")
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "options": {"temperature": 0.0, "num_predict": max_tokens},
    }
    if json_mode:
        payload["format"] = "json"
    data = _post_json(f"{base}/api/chat", payload, {"Content-Type": "application/json"}, timeout_s)
    content = ((data.get("message") or {}).get("content") or "").strip()
    if not content:
        raise ProviderError(f"empty content from local model {model}")
    usage = {
        "prompt_tokens": data.get("prompt_eval_count"),
        "completion_tokens": data.get("eval_count"),
    }
    return content, usage


_BACKENDS = {"openrouter": _call_openrouter, "ollama": _call_ollama}


# ---------------------------------------------------------------------------
# ledger + budget
# ---------------------------------------------------------------------------

def _spent_today(conn) -> float:
    row = conn.execute(
        "SELECT COALESCE(SUM(cost_usd), 0) FROM llm_runs WHERE ts >= date('now')"
    ).fetchone()
    return float(row[0] or 0.0)


def _log_run(conn, **kw: Any) -> int | None:
    if conn is None:
        return None
    cur = conn.execute(
        """INSERT INTO llm_runs
           (task, tier, provider, model, attempt, ref_id, prompt_tokens,
            completion_tokens, cost_usd, latency_ms, ok, error, ts)
           VALUES (:task, :tier, :provider, :model, :attempt, :ref_id, :prompt_tokens,
                   :completion_tokens, :cost_usd, :latency_ms, :ok, :error, :ts)""",
        {"ts": now_iso(), **kw},
    )
    conn.commit()
    return cur.lastrowid


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------

def chat(
    *,
    tier: str,
    system: str,
    user: str | list[dict[str, Any]],
    task: str,
    conn=None,
    ref_id: str | None = None,
    json_schema: bool = False,
    max_tokens: int | None = None,
) -> ProviderResult:
    """Run one LLM call against `tier`, walking its fallback chain on failure.

    `user` may be a string or a list of multimodal content parts (CONTRACTS.md §6).
    With `json_schema=True` the response is parsed; a model returning unparseable
    output is treated as a failure and the chain continues — better a slower
    correct answer than a fast malformed one stored as fact.

    Raises ProviderExhausted if every model in the chain fails.
    """
    models = chain_for(tier)
    backend_name = config.get("llm.backend", "openrouter")
    backend = _BACKENDS.get(backend_name)
    if backend is None:
        raise ProviderError(f"unknown llm.backend {backend_name!r}; expected {sorted(_BACKENDS)}")

    max_tokens = int(max_tokens or config.get("llm.max_tokens", 4000))
    timeout_s = int(config.get("llm.timeout_s", 90))
    budget = float(config.get("llm.daily_budget_usd", 0.0) or 0.0)

    failures: list[tuple[str, str]] = []
    for attempt, model in enumerate(models, start=1):
        # Budget gate: refuse rather than silently spend. budget 0.0 means the
        # free tier only, which is the configured default.
        if conn is not None and backend_name != "ollama" and not _is_free(model):
            spent = _spent_today(conn)
            if spent >= budget:
                failures.append((model, f"daily budget reached (${spent:.4f} >= ${budget:.2f})"))
                continue

        started = time.monotonic()
        try:
            content, usage = backend(model, system, user, max_tokens, timeout_s, json_schema)
            parsed = _parse_json(content) if json_schema else content
        except (ProviderError, json.JSONDecodeError, ValueError) as exc:
            latency = int((time.monotonic() - started) * 1000)
            _log_run(
                conn, task=task, tier=tier, provider=backend_name, model=model,
                attempt=attempt, ref_id=ref_id, prompt_tokens=None, completion_tokens=None,
                cost_usd=0.0, latency_ms=latency, ok=0, error=str(exc)[:500],
            )
            logger.warning("tier=%s model=%s failed (%s); trying next", tier, model, exc)
            failures.append((model, str(exc)))
            continue

        latency = int((time.monotonic() - started) * 1000)
        cost = float(usage.get("cost") or 0.0)
        run_id = _log_run(
            conn, task=task, tier=tier, provider=backend_name, model=model,
            attempt=attempt, ref_id=ref_id,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            cost_usd=cost, latency_ms=latency, ok=1, error=None,
        )
        return ProviderResult(
            content=parsed, model=model, provider=backend_name, usage=usage,
            cost_usd=cost, latency_ms=latency, attempts=attempt, run_id=run_id,
        )

    raise ProviderExhausted(tier, failures)


def image_part(path: str, media_type: str = "image/png") -> dict[str, Any]:
    """Build a multimodal image content part from a LOCAL archived file.

    Images always come from data/media/. Never re-fetch from X: the post may be
    deleted by the time we look, and the archive is the record.
    """
    import base64
    from pathlib import Path

    data = base64.b64encode(Path(path).read_bytes()).decode("ascii")
    return {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{data}"}}
