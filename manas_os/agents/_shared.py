"""AU6: shared helpers for the agent modules.

Mechanical consolidation of duplicated code that was copy-pasted across
debate.py, chair.py, vision.py, sizer.py, lessons.py, and coach.py: .env
loading, API key resolution, the models() list, the agent_verdicts +
scan_agent_logs schema, and the client.chat(...) tuple-unwrap. No behavior
change — every call site is a straight substitution.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from manas_os import config
from manas_os.advisor.client import OpenRouterClient

DEFAULT_MODEL = "deepseek/deepseek-chat"


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
