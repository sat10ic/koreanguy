"""Config loader for manas_os.

Reads `manas_os/config.yaml` (git-ignored, user-filled) and falls back to the
committed `config.example.yaml` for any missing values. Callers use `get(path,
default)` with a dotted key, e.g. `config.get("regime.xp_seed", 15.0)`.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_PKG_DIR = Path(__file__).resolve().parent
_CONFIG = _PKG_DIR / "config.yaml"
_EXAMPLE = _PKG_DIR / "config.example.yaml"


def _read(path: Path) -> dict:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _deep_merge(base: dict, override: dict) -> dict:
    """override wins; nested dicts merge recursively."""
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


@lru_cache(maxsize=1)
def load_config() -> dict:
    """example.yaml as the base, config.yaml overrides. Cached."""
    return _deep_merge(_read(_EXAMPLE), _read(_CONFIG))


def get(dotted_key: str, default: Any = None) -> Any:
    """Fetch a nested config value by dotted path, e.g. 'sources.breadth_sheet_csv_url'."""
    node: Any = load_config()
    for part in dotted_key.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node
