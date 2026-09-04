from __future__ import annotations

import json
import re
from typing import Any

NUMBER_RE = re.compile(r"-?\d{1,3}(?:[,_]\d{3})*(?:\.\d+)?")
IMPERATIVE_RE = re.compile(
    r"\b("
    r"buy\s+now|sell\s+now|enter\s+(now|immediately)?|exit\s+(now|immediately)|"
    r"increase\s+size|reduce\s+size|add\s+(size|now)|cut\s+(now|immediately)|"
    r"place\s+(an?\s+)?order|take\s+the\s+trade|short\s+now"
    r")\b",
    re.IGNORECASE,
)
VALID_SCOPES = {"regime", "entry", "exit", "risk", "event"}
VALID_STANCES = {"agree", "caution", "disagree"}


def _extract_numbers(text: str) -> set[str]:
    out: set[str] = set()
    for match in NUMBER_RE.finditer(text or ""):
        token = match.group(0).replace(",", "").replace("_", "")
        try:
            value = float(token)
        except ValueError:
            continue
        out.add(str(int(value)) if value.is_integer() else f"{value:g}")
    return out


def context_numbers(context_pack: dict[str, Any]) -> set[str]:
    return _extract_numbers(json.dumps(context_pack, sort_keys=True, default=str))


def parse_notes(raw: str) -> list[dict[str, Any]]:
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError("model output must be a JSON array")
    return data


def validate_notes(raw: str, context_pack: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    parsed = parse_notes(raw)
    allowed_numbers = context_numbers(context_pack)
    accepted: list[dict[str, Any]] = []
    rejected: list[str] = []
    for idx, item in enumerate(parsed):
        if not isinstance(item, dict):
            rejected.append(f"{idx}: note is not an object")
            continue
        scope = str(item.get("scope") or "").strip().lower()
        stance = str(item.get("stance") or "").strip().lower()
        symbol = item.get("symbol")
        note = str(item.get("note") or "").strip()
        watch_for = str(item.get("watch_for") or "").strip()
        if scope not in VALID_SCOPES:
            rejected.append(f"{idx}: invalid scope {scope}")
            continue
        if stance not in VALID_STANCES:
            rejected.append(f"{idx}: invalid stance {stance}")
            continue
        if not note:
            rejected.append(f"{idx}: blank note")
            continue
        text = f"{note} {watch_for}".strip()
        invented = sorted(n for n in _extract_numbers(text) if n not in allowed_numbers)
        if invented:
            rejected.append(f"{idx}: novel numbers {','.join(invented)}")
            continue
        if IMPERATIVE_RE.search(text):
            rejected.append(f"{idx}: imperative phrase")
            continue
        accepted.append({
            "scope": scope,
            "symbol": None if symbol in (None, "") else str(symbol).strip().upper(),
            "stance": stance,
            "note": note[:700],
            "watch_for": watch_for[:300] or None,
        })
    return accepted, rejected

