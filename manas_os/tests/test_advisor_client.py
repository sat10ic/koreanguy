import json
from contextlib import contextmanager

from manas_os.advisor import client as client_mod
from manas_os.advisor.client import OpenRouterClient


class _FakeResp:
    def __init__(self, payload: dict):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _patch_urlopen(monkeypatch, payload, capture=None):
    def fake_urlopen(req, timeout=None):
        if capture is not None:
            capture["body"] = json.loads(req.data.decode("utf-8"))
        return _FakeResp(payload)

    monkeypatch.setattr(client_mod.urllib.request, "urlopen", fake_urlopen)


def test_chat_uses_content_when_present(monkeypatch):
    payload = {"choices": [{"message": {"content": "hello", "reasoning": "thinking..."}}], "usage": {}}
    _patch_urlopen(monkeypatch, payload)
    c = OpenRouterClient(api_key="k", model="qwen/qwen3.5-plus-02-15", max_tokens=4000)
    content, model = c.chat(system="s", user="u")
    assert content == "hello"
    assert model == "qwen/qwen3.5-plus-02-15"


def test_chat_falls_back_to_reasoning_content_when_content_empty(monkeypatch):
    payload = {
        "choices": [{"message": {"content": "", "reasoning_content": "Final Answer: BUY"}}],
        "usage": {},
    }
    _patch_urlopen(monkeypatch, payload)
    c = OpenRouterClient(api_key="k", model="deepseek/deepseek-v4-pro", max_tokens=4000)
    content, model = c.chat(system="s", user="u")
    assert content == "BUY"


def test_chat_falls_back_to_reasoning_when_content_and_reasoning_content_empty(monkeypatch):
    payload = {
        "choices": [{"message": {"content": "", "reasoning": "The user wants X. Final answer: {\"a\": 1}"}}],
        "usage": {},
    }
    _patch_urlopen(monkeypatch, payload)
    c = OpenRouterClient(api_key="k", model="z-ai/glm-5", max_tokens=4000)
    content, model = c.chat(system="s", user="u")
    assert content == '{"a": 1}'


def test_chat_raises_when_all_fields_empty(monkeypatch):
    payload = {"choices": [{"message": {"content": "", "reasoning_content": "", "reasoning": ""}}], "usage": {}}
    _patch_urlopen(monkeypatch, payload)
    c = OpenRouterClient(api_key="k", model="moonshotai/kimi-k2-thinking", max_tokens=4000)
    try:
        c.chat(system="s", user="u")
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "empty OpenRouter content" in str(exc)


def test_reasoning_model_bumps_max_tokens_and_sets_reasoning_effort(monkeypatch):
    payload = {"choices": [{"message": {"content": "OK"}}], "usage": {}}
    capture = {}
    _patch_urlopen(monkeypatch, payload, capture=capture)
    c = OpenRouterClient(api_key="k", model="deepseek/deepseek-v4-pro", max_tokens=4000)
    c.chat(system="s", user="u")
    assert capture["body"]["max_tokens"] == 8000
    assert capture["body"]["reasoning"] == {"effort": "low"}


def test_non_reasoning_model_keeps_configured_max_tokens_and_no_reasoning_field(monkeypatch):
    payload = {"choices": [{"message": {"content": "OK"}}], "usage": {}}
    capture = {}
    _patch_urlopen(monkeypatch, payload, capture=capture)
    c = OpenRouterClient(api_key="k", model="qwen/qwen3.5-plus-02-15", max_tokens=4000)
    c.chat(system="s", user="u")
    assert capture["body"]["max_tokens"] == 4000
    assert "reasoning" not in capture["body"]
