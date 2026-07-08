# config.yaml keys:
# advisor:
#   enabled: true
#   api_key: "sk-or-..."
#   model: "deepseek/deepseek-chat"
#   max_tokens: 1200
#   daily_budget_calls: 3
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from manas_os import config

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


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

    def chat(self, *, system: str, user: str) -> tuple[str, str]:
        if not self.api_key:
            raise RuntimeError("advisor api_key missing")
        body = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": self.max_tokens,
            "temperature": 0.2,
        }).encode("utf-8")
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
        content = ((choices[0].get("message") or {}).get("content") or "").strip()
        if not content:
            raise RuntimeError("empty OpenRouter content")
        return content, self.model

