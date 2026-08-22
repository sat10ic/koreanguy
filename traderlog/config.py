"""Config loader: config.example.yaml as base, config.yaml deep-merged over it.

Same shape as manas_os/config.py so a model moving between the two projects does
not have to learn a second convention. Secrets are NOT here — they come from the
repo-root .env via env().
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

_DIR = Path(__file__).resolve().parent
_EXAMPLE = _DIR / "config.example.yaml"
_LOCAL = _DIR / "config.yaml"


def _deep_merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


@lru_cache(maxsize=1)
def load_config() -> dict:
    try:
        import yaml  # noqa: PLC0415
    except ImportError:  # pragma: no cover - yaml is in requirements
        return {}
    base: dict = {}
    if _EXAMPLE.exists():
        base = yaml.safe_load(_EXAMPLE.read_text(encoding="utf-8")) or {}
    if _LOCAL.exists():
        local = yaml.safe_load(_LOCAL.read_text(encoding="utf-8")) or {}
        base = _deep_merge(base, local)
    return base


def get(dotted: str, default: Any = None) -> Any:
    """config.get("llm.tiers.smart") -> the model id, or `default`."""
    node: Any = load_config()
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node


@lru_cache(maxsize=1)
def _load_env_file() -> None:
    """Walk up from this file looking for a .env and setdefault its keys.

    setdefault, not overwrite: a real environment variable always wins over the
    file, so CI and one-off overrides behave predictably.
    """
    here = _DIR
    for candidate in [here, *here.parents]:
        env_path = candidate / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip().strip("'\""))
            return


def env(name: str, default: str | None = None) -> str | None:
    """Read a secret from the environment, loading the repo-root .env first."""
    _load_env_file()
    return os.environ.get(name, default)
