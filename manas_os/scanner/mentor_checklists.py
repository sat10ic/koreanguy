"""Configurable mentor checklist definitions and response storage schema."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from manas_os import config

_PKG_DIR = Path(__file__).resolve().parents[1]
_DEFAULT_PATH = _PKG_DIR / "design" / "mentor_checklists.yaml"


def _configured_path() -> Path:
    override = config.get("mentor_checklists.path")
    if not override:
        return _DEFAULT_PATH
    path = Path(str(override))
    return path if path.is_absolute() else _PKG_DIR / path


def _read_checklists() -> list[dict[str, Any]]:
    path = _configured_path()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    checklists = data.get("checklists", [])
    return checklists if isinstance(checklists, list) else []


_CHECKLISTS = _read_checklists()


def load_checklists() -> list[dict[str, Any]]:
    """Return configured mentor checklists from the module-import cache."""
    return deepcopy(_CHECKLISTS)


def ensure_schema(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS checklist_responses (
            response_date TEXT NOT NULL,
            checklist_id TEXT NOT NULL,
            item_id TEXT NOT NULL,
            checked INTEGER NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            PRIMARY KEY(response_date, checklist_id, item_id)
        )
        """
    )
