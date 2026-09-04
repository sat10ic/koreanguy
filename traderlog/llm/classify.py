"""Contract-validated, auditable post classification for W2.

This module is the sole writer of ``post_class``.  It classifies a post only;
position and position-event reconstruction remain the reconciler's later work.
"""
from __future__ import annotations

import json
import math
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from traderlog.db import now_iso
from traderlog.llm import provider


_KINDS = frozenset(
    {"trade_event", "breadth", "watch_idea", "theme", "education", "noise"}
)
_PLAY_TYPES = frozenset(
    {
        "ep",
        "momentum_burst",
        "breakout",
        "pullback",
        "vcp",
        "ipo_base",
        "swing_range",
        "unclear",
    }
)
_PAYLOAD_KEYS = frozenset(
    {"kind", "confidence", "symbols", "play_type", "conviction_words", "reason"}
)
_TICKER_RE = re.compile(r"^[A-Z][A-Z0-9]{0,29}$")
_PROMPT = Path(__file__).with_name("prompts") / "classify.md"


class ClassificationValidationError(ValueError):
    """Classifier output violates the stable W2 contract or its source text."""


@dataclass(frozen=True)
class Classification:
    kind: str
    confidence: float
    symbols: tuple[str, ...]
    play_type: str
    conviction_words: tuple[str, ...]
    reason: str


def _system_prompt() -> str:
    """Load the binding W2 classifier contract without duplicating it in code."""
    return _PROMPT.read_text(encoding="utf-8")


def _exact_keys(payload: Mapping[str, Any]) -> None:
    actual = frozenset(payload)
    missing = _PAYLOAD_KEYS - actual
    unknown = actual - _PAYLOAD_KEYS
    if missing:
        raise ClassificationValidationError(f"classification missing keys: {sorted(missing)!r}")
    if unknown:
        raise ClassificationValidationError(f"classification has unknown keys: {sorted(unknown)!r}")


def _source_has_symbol(text: str, symbol: str) -> bool:
    return re.search(
        rf"(?<![A-Za-z0-9_])#?{re.escape(symbol)}(?![A-Za-z0-9_])",
        text,
        flags=re.IGNORECASE,
    ) is not None


def validate_classification(payload: object, source_text: object) -> Classification:
    """Normalize one classifier payload and reject unsupported assertions."""
    if not isinstance(payload, dict):
        raise ClassificationValidationError("classification must be an object")
    if not isinstance(source_text, str):
        raise ClassificationValidationError("source text must be a string")
    _exact_keys(payload)

    kind = payload["kind"]
    if kind not in _KINDS:
        raise ClassificationValidationError("kind is not in the classifier enum")

    confidence = payload["confidence"]
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise ClassificationValidationError("confidence must be a finite number between 0 and 1")
    confidence = float(confidence)
    if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
        raise ClassificationValidationError("confidence must be a finite number between 0 and 1")

    symbols_value = payload["symbols"]
    if not isinstance(symbols_value, list):
        raise ClassificationValidationError("symbols must be a list")
    symbols: list[str] = []
    for index, value in enumerate(symbols_value):
        if not isinstance(value, str):
            raise ClassificationValidationError(f"symbols[{index}] must be a string")
        normalized = value.upper()
        if not _TICKER_RE.fullmatch(normalized):
            raise ClassificationValidationError(f"symbols[{index}] is not a conservative ticker token")
        if not _source_has_symbol(source_text, normalized):
            raise ClassificationValidationError(f"symbols[{index}] is not present in source text")
        if normalized not in symbols:
            symbols.append(normalized)

    play_type = payload["play_type"]
    if play_type not in _PLAY_TYPES:
        raise ClassificationValidationError("play_type is not in the classifier enum")
    if kind not in {"trade_event", "watch_idea"} and play_type != "unclear":
        raise ClassificationValidationError("play_type must be unclear outside trade_event/watch_idea")

    conviction_value = payload["conviction_words"]
    if not isinstance(conviction_value, list):
        raise ClassificationValidationError("conviction_words must be a list")
    conviction_words: list[str] = []
    for index, phrase in enumerate(conviction_value):
        if not isinstance(phrase, str) or not phrase:
            raise ClassificationValidationError(
                f"conviction_words[{index}] must be a non-empty verbatim string"
            )
        if phrase not in source_text:
            raise ClassificationValidationError(
                f"conviction_words[{index}] is not verbatim in source text"
            )
        if phrase not in conviction_words:
            conviction_words.append(phrase)

    reason = payload["reason"]
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 500:
        raise ClassificationValidationError("reason must be a non-empty string up to 500 characters")

    return Classification(
        kind=kind,
        confidence=confidence,
        symbols=tuple(symbols),
        play_type=play_type,
        conviction_words=tuple(conviction_words),
        reason=reason.strip(),
    )


def _source_post(conn: sqlite3.Connection, post_id: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT post_id, text, is_mock FROM posts WHERE post_id=?", (post_id,)
    ).fetchone()
    if row is None:
        raise ValueError(f"post_id {post_id!r} does not exist")
    return row


def _upsert(
    conn: sqlite3.Connection,
    post_id: str,
    classification: Classification,
    *,
    model: str,
    run_id: int | None,
    is_mock: int,
) -> None:
    """Write the contract fields only; ``reason`` remains returned audit context.

    The existing schema has no reason/source column.  ``model`` records the
    provider model or the audited human source, and ``run_id`` links provider
    calls when one exists.
    """
    with conn:
        conn.execute(
            """INSERT INTO post_class
               (post_id,kind,confidence,symbols,play_type,conviction_words,model,run_id,is_mock,ingested_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(post_id) DO UPDATE SET
                 kind=excluded.kind,
                 confidence=excluded.confidence,
                 symbols=excluded.symbols,
                 play_type=excluded.play_type,
                 conviction_words=excluded.conviction_words,
                 model=excluded.model,
                 run_id=excluded.run_id,
                 is_mock=excluded.is_mock,
                 ingested_at=excluded.ingested_at""",
            (
                post_id,
                classification.kind,
                classification.confidence,
                json.dumps(list(classification.symbols), ensure_ascii=False),
                classification.play_type,
                json.dumps(list(classification.conviction_words), ensure_ascii=False),
                model,
                run_id,
                is_mock,
                now_iso(),
            ),
        )


def apply_verified_classification(
    conn: sqlite3.Connection,
    post_id: str,
    payload: object,
    *,
    source: str = "user",
) -> Classification:
    """Persist an audited human label without creating a trade event or position."""
    if not isinstance(source, str) or not source.strip():
        raise ValueError("source must be a non-empty audit label")
    post = _source_post(conn, post_id)
    classification = validate_classification(payload, post["text"])
    _upsert(
        conn,
        post_id,
        classification,
        model=source.strip(),
        run_id=None,
        is_mock=int(post["is_mock"]),
    )
    return classification


def classify_post(
    conn: sqlite3.Connection,
    post_id: str,
    *,
    chat_fn: Callable[..., provider.ProviderResult] = provider.chat,
) -> Classification:
    """Classify one persisted post through the cheap tier and audit its provider run."""
    post = _source_post(conn, post_id)
    if not isinstance(post["text"], str):
        raise ValueError(f"post_id {post_id!r} has no classifiable text")
    result = chat_fn(
        tier="cheap",
        system=_system_prompt(),
        user=json.dumps({"post_id": post_id, "text": post["text"]}, ensure_ascii=False),
        task="classify",
        conn=conn,
        ref_id=post_id,
        json_schema=True,
    )
    if not isinstance(result, provider.ProviderResult):
        raise TypeError("chat_fn must return ProviderResult")
    classification = validate_classification(result.content, post["text"])
    _upsert(
        conn,
        post_id,
        classification,
        model=result.model,
        run_id=result.run_id,
        is_mock=int(post["is_mock"]),
    )
    return classification
