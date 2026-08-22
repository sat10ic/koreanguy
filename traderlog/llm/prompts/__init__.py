"""Prompt loader.

Prompts live as .md files beside this module, not as Python string literals, for
two reasons: a non-Claude model editing one does not have to touch code, and a
prompt change shows up as a readable diff rather than buried inside an f-string.

A prompt is versioned by its file content hash, which is recorded alongside
golden-fixture results. If the fixtures pass and the hash changed, the edit was
safe; if they fail, the hash tells you exactly which prompt to revert.
"""
from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

_DIR = Path(__file__).resolve().parent

NAMES = ("classify", "vision", "reconcile", "link")


@lru_cache(maxsize=None)
def load(name: str) -> str:
    if name not in NAMES:
        raise ValueError(f"unknown prompt {name!r}; expected one of {NAMES}")
    path = _DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"prompt file missing: {path}")
    return path.read_text(encoding="utf-8").strip()


@lru_cache(maxsize=None)
def version(name: str) -> str:
    """Short content hash. Record this with any fixture result."""
    return hashlib.sha256(load(name).encode("utf-8")).hexdigest()[:12]


def all_versions() -> dict[str, str]:
    return {n: version(n) for n in NAMES}
