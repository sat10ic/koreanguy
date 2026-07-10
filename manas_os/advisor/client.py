# config.yaml keys:
# advisor:
#   enabled: true
#   api_key: "sk-or-..."
#   model: "deepseek/deepseek-chat"
#   max_tokens: 1200
#   daily_budget_calls: 3
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

from manas_os import config

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Reasoning/hybrid models that emit their answer via message.reasoning_content
# or message.reasoning when the requested max_tokens is spent on chain-of-thought
# before any `content` is written. These need a capped reasoning effort and a
# higher max_tokens ceiling, plus a parse fallback onto the reasoning fields.
REASONING_MODELS = (
    "deepseek/deepseek-v4-pro",
    "z-ai/glm-5",
    "moonshotai/kimi-k2-thinking",
)

REASONING_MIN_MAX_TOKENS = 8000


def _is_reasoning_model(model: str) -> bool:
    return any(model.startswith(m) or m in model for m in REASONING_MODELS)


def _extract_final_answer(text: str) -> str:
    """Best-effort extraction of a final answer embedded in a reasoning trace.

    Reasoning fields are free-form chain-of-thought; when they contain an
    explicit final-answer marker, prefer the text after it. Otherwise return
    the reasoning text as-is (still better than raising on empty content).
    """
    if not text:
        return text
    markers = [
        "final answer:",
        "final answer",
        "answer:",
        "so the answer is",
    ]
    lowered = text.lower()
    for marker in markers:
        idx = lowered.rfind(marker)
        if idx != -1:
            candidate = text[idx + len(marker):].strip(" :\n\t")
            if candidate:
                return candidate
    return text.strip()


class OpenRouterClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
        timeout_s: int = 45,
    ) -> None:
        self.api_key = api_key if api_key is not None else config.get("advisor.api_key")
        self.model = model or config.get("advisor.model", "deepseek/deepseek-chat")
        self.max_tokens = int(max_tokens or config.get("advisor.max_tokens", 1200) or 1200)
        self.timeout_s = timeout_s

    def chat(
        self,
        *,
        system: str,
        user: str | list[dict[str, Any]],
        include_usage: bool = False,
    ) -> tuple[str, str] | tuple[str, str, dict[str, Any] | None]:
        if not self.api_key:
            raise RuntimeError("advisor api_key missing")
        is_reasoning = _is_reasoning_model(self.model)
        effective_max_tokens = self.max_tokens
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
        }
        if is_reasoning:
            effective_max_tokens = max(self.max_tokens, REASONING_MIN_MAX_TOKENS)
            payload["reasoning"] = {"effort": "low"}
        payload["max_tokens"] = effective_max_tokens
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            OPENROUTER_URL,
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/sat10ic/koreanguy",
                "X-Title": "Manas OS Advisor",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                data: Any = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"openrouter request failed: {exc}") from exc
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError(f"empty OpenRouter choices: {data}")
        message = choices[0].get("message") or {}
        content = (message.get("content") or "").strip()
        parse_source = "content"
        if not content:
            reasoning_content = (message.get("reasoning_content") or "").strip()
            if reasoning_content:
                content = _extract_final_answer(reasoning_content)
                parse_source = "reasoning_content"
            else:
                reasoning = (message.get("reasoning") or "").strip()
                if reasoning:
                    content = _extract_final_answer(reasoning)
                    parse_source = "reasoning"
        if not content:
            raise RuntimeError("empty OpenRouter content")
        if parse_source != "content":
            logger.warning(
                "OpenRouter model %s returned empty content; used %s as fallback",
                self.model, parse_source,
            )
        usage = data.get("usage")
        if include_usage:
            return content, self.model, usage if isinstance(usage, dict) else None
        return content, self.model
