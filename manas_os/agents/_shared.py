"""AU6: shared helpers for the agent modules.

Mechanical consolidation of duplicated code that was copy-pasted across
debate.py, chair.py, vision.py, sizer.py, lessons.py, and coach.py: .env
loading, API key resolution, the models() list, the agent_verdicts +
scan_agent_logs schema, and the client.chat(...) tuple-unwrap. No behavior
change — every call site is a straight substitution.
"""
from __future__ import annotations

import calendar
import os
import json
import re
import time
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any

from manas_os import config
from manas_os.advisor.client import OpenRouterClient

DEFAULT_MODEL = "deepseek/deepseek-chat"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
_PRICING_CACHE: tuple[float, dict[str, dict[str, float]]] | None = None

STALE_EVIDENCE_MAX_AGE_MONTHS = 6

_MONTH_YEAR_RE = re.compile(
    r"\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
    r"Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\.?\s+(20\d{2})\b",
    re.IGNORECASE,
)

_MONTH_NUM = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def load_env_file() -> None:
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


def api_key() -> str | None:
    load_env_file()
    return config.get("agents.api_key") or config.get("advisor.api_key") or os.environ.get("OPENROUTER_API_KEY")


def models() -> list[str]:
    configured = config.get("agents.models")
    if isinstance(configured, str) and configured.strip():
        return [configured.strip()]
    if isinstance(configured, list):
        out = [str(m).strip() for m in configured if str(m).strip()]
        if out:
            return out
    return [str(config.get("agents.model", DEFAULT_MODEL))]


def ensure_agent_tables(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS agent_verdicts ("
        "scan_date TEXT NOT NULL, symbol TEXT NOT NULL, agent TEXT NOT NULL, "
        "verdict TEXT NOT NULL, conviction INTEGER, rank INTEGER, "
        "lens_scores_json TEXT, bull_case TEXT, bear_case TEXT, reasoning TEXT, "
        "outcome_r REAL, tier TEXT, created_at TEXT DEFAULT (datetime('now')), "
        "PRIMARY KEY (scan_date, symbol, agent))"
    )
    have = {r[1] for r in conn.execute("PRAGMA table_info(agent_verdicts)")}
    if "tier" not in have:
        conn.execute("ALTER TABLE agent_verdicts ADD COLUMN tier TEXT")
    if "source" not in have:
        # Chartink-screener push-to-debate amendment (2026-07-11 ~09:30):
        # NULL = nightly scanner debate; 'user_pushed' = on-demand symbol the
        # user pushed from the screener/search box (POST /api/desk/debate/push).
        conn.execute("ALTER TABLE agent_verdicts ADD COLUMN source TEXT")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS scan_agent_logs ("
        "log_id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "run_date TEXT, agent TEXT, model TEXT, prompt_sha TEXT, "
        "latency_ms INTEGER, tokens_in INTEGER, tokens_out INTEGER, "
        "parsed_ok INTEGER, validation TEXT, error TEXT, "
        "created_at TEXT DEFAULT (datetime('now')))"
    )
    have_logs = {r[1] for r in conn.execute("PRAGMA table_info(scan_agent_logs)")}
    if "model_status" not in have_logs:
        conn.execute("ALTER TABLE scan_agent_logs ADD COLUMN model_status TEXT")
    if "cost_inr" not in have_logs:
        conn.execute("ALTER TABLE scan_agent_logs ADD COLUMN cost_inr REAL")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS agent_watchlist ("
        "scan_date TEXT NOT NULL, symbol TEXT NOT NULL, "
        "tier TEXT, status TEXT NOT NULL, prev_status TEXT, reason TEXT, "
        "miss_streak INTEGER DEFAULT 0, "
        "created_at TEXT DEFAULT (datetime('now')), "
        "PRIMARY KEY (scan_date, symbol))"
    )
    have_wl = {r[1] for r in conn.execute("PRAGMA table_info(agent_watchlist)")}
    if "miss_streak" not in have_wl:
        conn.execute("ALTER TABLE agent_watchlist ADD COLUMN miss_streak INTEGER DEFAULT 0")


def chat_tuple(llm: Any, system: str, user: Any) -> tuple[str, str]:
    """Unwrap a plain client.chat(...) call: (content, model) or (content, model, usage)."""
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


def chat_with_usage(llm: Any, system: str, user: str) -> Any:
    """Call client.chat(...), requesting include_usage from OpenRouterClient specifically."""
    if isinstance(llm, OpenRouterClient):
        return llm.chat(system=system, user=user, include_usage=True)
    return llm.chat(system=system, user=user)


def unpack_chat(result: Any, default_model: str) -> tuple[str, str, dict[str, Any] | None]:
    """Unwrap the result of chat_with_usage(...) into (raw, used_model, usage)."""
    if not isinstance(result, tuple):
        raise ValueError("client.chat must return a tuple")
    if len(result) == 2:
        raw, used_model = result
        return raw, used_model or default_model, None
    if len(result) == 3:
        raw, used_model, usage = result
        return raw, used_model or default_model, usage if isinstance(usage, dict) else None
    raise ValueError("client.chat must return (content, model) or (content, model, usage)")


def model_pricing(*, fetcher: Any | None = None, now: float | None = None) -> dict[str, dict[str, float]]:
    """Return OpenRouter per-token prompt/completion USD pricing, cached daily."""
    global _PRICING_CACHE
    current = time.time() if now is None else now
    if _PRICING_CACHE and current - _PRICING_CACHE[0] < 86400:
        return _PRICING_CACHE[1]
    if fetcher is None:
        def fetcher():
            with urllib.request.urlopen(OPENROUTER_MODELS_URL, timeout=15) as response:
                return json.loads(response.read().decode("utf-8"))
    payload = fetcher()
    out: dict[str, dict[str, float]] = {}
    for item in payload.get("data", []) if isinstance(payload, dict) else []:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        pricing = item.get("pricing") or {}
        try:
            out[str(item["id"])] = {
                "prompt": float(pricing.get("prompt") or 0.0),
                "completion": float(pricing.get("completion") or 0.0),
            }
        except (TypeError, ValueError):
            continue
    _PRICING_CACHE = (current, out)
    return out


def recency_rule(scan_date: str) -> str:
    """Shared RECENCY RULE text for vision/observer system prompts (I10 fix).

    Root cause: the vision/observer LLM was shown a daily PNG spanning ~120
    sessions and a weekly PNG spanning ~2 years with no explicit "today" —
    nothing stopped it from narrating an old region of the image (e.g. a
    Sep 2024 episode) as if it were current. This pins the model to the
    current scan_date and instructs it to say so rather than guess when the
    image itself is ambiguous about dates.
    """
    return (
        f"RECENCY RULE: Today is {scan_date}. Anchor your analysis on the LAST 60 "
        "trading sessions and the current date. Describe structure as of this date; "
        "do not narrate historical episodes older than ~3 months except as brief "
        "one-line context. If the image is ambiguous about dates, say so rather "
        "than guessing dates."
    )


def _months_before(as_of: date, months: int) -> date:
    year = as_of.year
    month = as_of.month - months
    while month <= 0:
        month += 12
        year -= 1
    day = min(as_of.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def stale_evidence_warning(
    text: str, scan_date: str, *, max_age_months: int = STALE_EVIDENCE_MAX_AGE_MONTHS
) -> str | None:
    """Post-check (I10): scan vision/observer free-text output for explicit
    month-year mentions (e.g. "Sep 2024") older than max_age_months before
    scan_date. Returns a human-readable warning string, or None if the text
    carries no stale-dated claims. This does not try to prove the claim is
    wrong — it flags it so the stored card carries a visible warning instead
    of silently accepting an old chart region narrated as current.
    """
    if not text or not scan_date:
        return None
    try:
        as_of = date.fromisoformat(scan_date)
    except (TypeError, ValueError):
        return None
    cutoff = _months_before(as_of, max_age_months)
    cutoff_month_start = date(cutoff.year, cutoff.month, 1)

    stale: list[str] = []
    seen: set[str] = set()
    for match in _MONTH_YEAR_RE.finditer(text):
        month_key = match.group(1)[:3].lower()
        month_num = _MONTH_NUM.get(month_key)
        if not month_num:
            continue
        year = int(match.group(2))
        mentioned_month_start = date(year, month_num, 1)
        if mentioned_month_start < cutoff_month_start:
            label = f"{match.group(1)} {year}"
            key = label.lower()
            if key not in seen:
                seen.add(key)
                stale.append(label)

    if not stale:
        return None
    joined = ", ".join(stale)
    return f"references {joined} — treat dated claims with suspicion"
