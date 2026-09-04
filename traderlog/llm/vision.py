"""Contract-validated, auditable chart transcription for W2 (CONTRACTS.md #2).

One call per image on a `trade_event` or `education` post, tier `vision`. This
module is the SOLE writer of `post_media.vision_json` / `vision_model` /
`vision_at` (CANONICAL.md #6). Style matches `llm/classify.py`: a strict
validator that rejects a payload violating the contract, a `chat_fn`-injectable
entrypoint for network-free testing, and an `apply_verified_*` path for a
human-audited transcription.

Vision output is evidence, not truth (CONTRACTS.md #3): the reconciler weighs
it against post text and may reject it. This module's job stops at faithful,
disciplined transcription.
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
from traderlog.ingest.archive import DEFAULT_MEDIA_ROOT
from traderlog.llm import provider


_TIMEFRAMES = frozenset({"daily", "weekly", "intraday", "unknown"})
_LEVEL_KINDS = frozenset({"entry", "stop", "target", "support", "resistance", "other"})
_IMAGE_KINDS = frozenset(
    {"chart", "order_confirmation", "holdings", "watchlist", "other", "unknown"}
)
_NON_CHART_EVIDENCE_KINDS = frozenset(
    {"entry_price", "average_price", "last_price", "quantity", "pnl", "return_pct"}
)
_PAYLOAD_KEYS = frozenset(
    {
        "chart_symbol", "timeframe", "image_kind", "text_in_image", "annotated_levels",
        "non_chart_evidence", "structure_note", "confidence", "unreadable",
    }
)
_LEGACY_OPTIONAL_PAYLOAD_KEYS = frozenset({"image_kind", "non_chart_evidence"})
_LEVEL_KEYS = frozenset({"kind", "price", "source"})
_NON_CHART_EVIDENCE_KEYS = frozenset({"kind", "value", "source"})
_TICKER_RE = re.compile(r"^[A-Z][A-Z0-9]{0,29}$")
_PROMPT = Path(__file__).with_name("prompts") / "vision.md"


class VisionValidationError(ValueError):
    """Vision output violates the stable W2 contract."""


@dataclass(frozen=True)
class AnnotatedLevel:
    kind: str
    price: float
    source: str


@dataclass(frozen=True)
class NonChartEvidence:
    """One number visibly transcribed from a readable non-chart image."""

    kind: str
    value: float
    source: str


@dataclass(frozen=True)
class VisionResult:
    chart_symbol: str | None
    timeframe: str
    image_kind: str
    text_in_image: tuple[str, ...]
    annotated_levels: tuple[AnnotatedLevel, ...]
    non_chart_evidence: tuple[NonChartEvidence, ...]
    structure_note: str
    confidence: float
    unreadable: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "chart_symbol": self.chart_symbol,
            "timeframe": self.timeframe,
            "image_kind": self.image_kind,
            "text_in_image": list(self.text_in_image),
            "annotated_levels": [
                {"kind": lvl.kind, "price": lvl.price, "source": lvl.source}
                for lvl in self.annotated_levels
            ],
            "non_chart_evidence": [
                {"kind": item.kind, "value": item.value, "source": item.source}
                for item in self.non_chart_evidence
            ],
            "structure_note": self.structure_note,
            "confidence": self.confidence,
            "unreadable": self.unreadable,
        }


def _system_prompt() -> str:
    return _PROMPT.read_text(encoding="utf-8")


def _is_finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def validate_vision(payload: object) -> VisionResult:
    """Normalize one vision payload and reject anything the contract forbids.

    Enforces the three disciplines vision.md states in prose:
    (1) an `unreadable` image carries empty arrays -- no smuggling a guess in
        alongside an honest "I can't read this";
    (2) every `annotated_levels[]` entry has both a price and the visual
        justification for it, never one without the other.
    (3) non-chart numeric evidence names the source field that visibly states it.

    `image_kind` and `non_chart_evidence` were added after initial archived
    vision rows existed. Missing both therefore normalizes to an explicit,
    canonical `unknown` / empty representation; every newly persisted row uses
    the complete current shape.
    """
    if not isinstance(payload, dict):
        raise VisionValidationError("vision output must be an object")
    actual = frozenset(payload)
    has_image_kind = "image_kind" in actual
    has_non_chart_evidence = "non_chart_evidence" in actual
    if has_image_kind != has_non_chart_evidence:
        raise VisionValidationError(
            "image_kind and non_chart_evidence must either both be present or both be absent"
        )
    missing = (_PAYLOAD_KEYS - _LEGACY_OPTIONAL_PAYLOAD_KEYS) - actual
    unknown = actual - _PAYLOAD_KEYS
    if missing:
        raise VisionValidationError(f"vision output missing keys: {sorted(missing)!r}")
    if unknown:
        raise VisionValidationError(f"vision output has unknown keys: {sorted(unknown)!r}")

    unreadable = payload["unreadable"]
    if not isinstance(unreadable, bool):
        raise VisionValidationError("unreadable must be a boolean")

    chart_symbol = payload["chart_symbol"]
    if chart_symbol is not None:
        if not isinstance(chart_symbol, str) or not chart_symbol:
            raise VisionValidationError("chart_symbol must be a non-empty string or null")
        chart_symbol = chart_symbol.upper()
        if not _TICKER_RE.fullmatch(chart_symbol):
            raise VisionValidationError("chart_symbol is not a conservative ticker token")

    timeframe = payload["timeframe"]
    if timeframe not in _TIMEFRAMES:
        raise VisionValidationError("timeframe is not in the vision enum")

    image_kind = payload.get("image_kind", "unknown")
    if not isinstance(image_kind, str) or image_kind not in _IMAGE_KINDS:
        raise VisionValidationError("image_kind is not in the vision enum")

    text_value = payload["text_in_image"]
    if not isinstance(text_value, list):
        raise VisionValidationError("text_in_image must be a list")
    text_in_image: list[str] = []
    for i, item in enumerate(text_value):
        if not isinstance(item, str) or not item:
            raise VisionValidationError(f"text_in_image[{i}] must be a non-empty string")
        text_in_image.append(item)

    levels_value = payload["annotated_levels"]
    if not isinstance(levels_value, list):
        raise VisionValidationError("annotated_levels must be a list")
    annotated_levels: list[AnnotatedLevel] = []
    for i, raw in enumerate(levels_value):
        if not isinstance(raw, dict):
            raise VisionValidationError(f"annotated_levels[{i}] must be an object")
        extra = set(raw) - _LEVEL_KEYS
        missing_lvl = _LEVEL_KEYS - set(raw)
        if extra:
            raise VisionValidationError(f"annotated_levels[{i}] has unknown keys: {sorted(extra)!r}")
        if missing_lvl:
            raise VisionValidationError(f"annotated_levels[{i}] missing keys: {sorted(missing_lvl)!r}")
        kind = raw["kind"]
        if kind not in _LEVEL_KINDS:
            raise VisionValidationError(f"annotated_levels[{i}].kind is not in the vision enum")
        price = raw["price"]
        if not _is_finite_number(price):
            raise VisionValidationError(f"annotated_levels[{i}].price must be a finite number")
        source = raw["source"]
        if not isinstance(source, str) or not source.strip():
            raise VisionValidationError(
                f"annotated_levels[{i}].source must name the visual evidence for this price"
            )
        annotated_levels.append(AnnotatedLevel(kind=kind, price=float(price), source=source.strip()))

    evidence_value = payload.get("non_chart_evidence", [])
    if not isinstance(evidence_value, list):
        raise VisionValidationError("non_chart_evidence must be a list")
    non_chart_evidence: list[NonChartEvidence] = []
    for i, raw in enumerate(evidence_value):
        if not isinstance(raw, dict):
            raise VisionValidationError(f"non_chart_evidence[{i}] must be an object")
        extra = set(raw) - _NON_CHART_EVIDENCE_KEYS
        missing_evidence = _NON_CHART_EVIDENCE_KEYS - set(raw)
        if extra:
            raise VisionValidationError(
                f"non_chart_evidence[{i}] has unknown keys: {sorted(extra)!r}"
            )
        if missing_evidence:
            raise VisionValidationError(
                f"non_chart_evidence[{i}] missing keys: {sorted(missing_evidence)!r}"
            )
        kind = raw["kind"]
        if not isinstance(kind, str) or kind not in _NON_CHART_EVIDENCE_KINDS:
            raise VisionValidationError(f"non_chart_evidence[{i}].kind is not in the vision enum")
        value = raw["value"]
        if not _is_finite_number(value):
            raise VisionValidationError(f"non_chart_evidence[{i}].value must be a finite number")
        source = raw["source"]
        if not isinstance(source, str) or not source.strip():
            raise VisionValidationError(
                f"non_chart_evidence[{i}].source must name the visual evidence for this value"
            )
        non_chart_evidence.append(
            NonChartEvidence(kind=kind, value=float(value), source=source.strip())
        )

    structure_note = payload["structure_note"]
    if not isinstance(structure_note, str) or not structure_note.strip():
        raise VisionValidationError("structure_note must be a non-empty string")

    confidence = payload["confidence"]
    if not _is_finite_number(confidence):
        raise VisionValidationError("confidence must be a finite number")
    confidence = float(confidence)
    if not 0.0 <= confidence <= 1.0:
        raise VisionValidationError("confidence must be between 0 and 1")

    if unreadable and (text_in_image or annotated_levels or non_chart_evidence):
        raise VisionValidationError(
            "unreadable=true must carry empty text_in_image, annotated_levels, and non_chart_evidence "
            "(vision.md rule 5: leave the arrays empty rather than guessing)"
        )
    if non_chart_evidence and image_kind not in {
        "order_confirmation", "holdings", "watchlist", "other"
    }:
        raise VisionValidationError("non_chart_evidence requires a non-chart image_kind")
    if image_kind in {"order_confirmation", "holdings", "watchlist", "other"} and annotated_levels:
        raise VisionValidationError("annotated_levels require image_kind=chart or unknown")

    return VisionResult(
        chart_symbol=chart_symbol,
        timeframe=timeframe,
        image_kind=image_kind,
        text_in_image=tuple(text_in_image),
        annotated_levels=tuple(annotated_levels),
        non_chart_evidence=tuple(non_chart_evidence),
        structure_note=structure_note.strip(),
        confidence=confidence,
        unreadable=unreadable,
    )


def _source_media(conn: sqlite3.Connection, post_id: str, idx: int) -> sqlite3.Row:
    row = conn.execute(
        "SELECT * FROM post_media WHERE post_id = ? AND idx = ?", (post_id, idx)
    ).fetchone()
    if row is None:
        raise ValueError(f"post_media ({post_id!r}, {idx!r}) does not exist")
    return row


def _upsert(
    conn: sqlite3.Connection,
    post_id: str,
    idx: int,
    result: VisionResult,
    *,
    model: str,
) -> None:
    with conn:
        conn.execute(
            "UPDATE post_media SET vision_json = ?, vision_model = ?, vision_at = ? "
            "WHERE post_id = ? AND idx = ?",
            (json.dumps(result.to_dict(), ensure_ascii=False), model, now_iso(), post_id, idx),
        )


def apply_verified_vision(
    conn: sqlite3.Connection,
    post_id: str,
    idx: int,
    payload: object,
    *,
    source: str = "user",
) -> VisionResult:
    """Persist a hand-audited chart transcription without an LLM call."""
    if not isinstance(source, str) or not source.strip():
        raise ValueError("source must be a non-empty audit label")
    _source_media(conn, post_id, idx)
    result = validate_vision(payload)
    _upsert(conn, post_id, idx, result, model=source.strip())
    return result


def vision_pass(
    conn: sqlite3.Connection,
    post_id: str,
    idx: int,
    *,
    chat_fn: Callable[..., provider.ProviderResult] = provider.chat,
    media_root: str | Path = DEFAULT_MEDIA_ROOT,
) -> VisionResult:
    """Transcribe one archived chart image through the vision tier.

    Reads the LOCAL archived file under `media_root` (CONTRACTS.md #6/#2) --
    never re-fetches from X.
    """
    media = _source_media(conn, post_id, idx)
    local_path = Path(media["local_path"])
    if not local_path.is_absolute():
        local_path = Path(media_root) / local_path
    if not local_path.is_file():
        raise FileNotFoundError(f"archived media not found at {local_path}")

    media_type = "image/png" if local_path.suffix.lower() == ".png" else "image/jpeg"
    image_part = provider.image_part(str(local_path), media_type=media_type)
    user: list[dict[str, Any]] = [
        {"type": "text", "text": f"post_id={post_id} idx={idx}"},
        image_part,
    ]

    result_raw = chat_fn(
        tier="vision",
        system=_system_prompt(),
        user=user,
        task="vision",
        conn=conn,
        ref_id=post_id,
        json_schema=True,
    )
    if not isinstance(result_raw, provider.ProviderResult):
        raise TypeError("chat_fn must return ProviderResult")

    result = validate_vision(result_raw.content)
    _upsert(conn, post_id, idx, result, model=result_raw.model)
    return result
