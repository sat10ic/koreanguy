"""Validated, auditable cross-thread link proposals for W3.

This module owns proposal validation and review-queue insertion.  It never
writes ``positions`` or ``position_events``: accepted application is delegated
to :mod:`traderlog.llm.reconcile`, their sole writer.
``run_link_pass`` batches that single-post flow into an idempotent runtime
producer pass over every eligible post.
"""
from __future__ import annotations

import json
import math
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from traderlog.config import get as config_get
from traderlog.db import now_iso
from traderlog.llm import provider
from traderlog.llm.reconcile import apply_accepted_link


_PROMPT = Path(__file__).with_name("prompts") / "link.md"
_TOP_KEYS = frozenset({"post_id", "proposed_position_id", "proposed_event", "confidence", "reasoning", "alternatives"})
_EVENT_KINDS = frozenset({"exit", "partial_exit", "add", "stop", "target"})
_OPEN_LIKE = frozenset({"open", "added", "partial", "unclear"})


class LinkValidationError(ValueError):
    """A proposed cross-thread event is outside the auditable contract."""


@dataclass(frozen=True)
class LinkProposal:
    post_id: str
    proposed_position_id: str
    proposed_event: Mapping[str, Any]
    confidence: float
    reasoning: str
    alternatives: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "post_id": self.post_id,
            "proposed_position_id": self.proposed_position_id,
            "proposed_event": dict(self.proposed_event),
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "alternatives": list(self.alternatives),
        }


@dataclass(frozen=True)
class LinkRoute:
    id: int
    status: str
    applied: bool
    proposal: LinkProposal


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise LinkValidationError(message)


def _finite(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _symbols(row: sqlite3.Row) -> set[str]:
    try:
        raw = json.loads(row["symbols"] or "[]")
    except (TypeError, ValueError):
        return set()
    return {item.upper() for item in raw if isinstance(item, str) and item}


def _canonical_json(proposal: LinkProposal) -> str:
    return json.dumps(proposal.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _validate_event(raw: object) -> dict[str, Any]:
    _require(isinstance(raw, dict), "proposed_event must be an object")
    _require("kind" in raw, "proposed_event.kind is required")
    kind = raw["kind"]
    _require(kind in _EVENT_KINDS, "proposed_event.kind is not supported")
    allowed = {"kind", "price", "qty_pct"}
    _require(not (set(raw) - allowed), f"proposed_event has unknown keys: {sorted(set(raw) - allowed)!r}")
    price = raw.get("price")
    if kind in {"add", "stop", "target"}:
        _require(_finite(price) and float(price) > 0, "proposed_event.price must be a positive finite number")
    else:
        _require(price is None or (_finite(price) and float(price) > 0), "proposed_event.price must be null or a positive finite number")
    qty_pct = raw.get("qty_pct")
    _require(qty_pct is None or (_finite(qty_pct) and 0 < float(qty_pct) <= 100), "proposed_event.qty_pct must be in (0, 100]")
    if kind == "partial_exit":
        _require(qty_pct is not None and float(qty_pct) < 100, "partial_exit requires qty_pct below 100")
    if kind == "exit":
        _require(qty_pct is None or float(qty_pct) == 100, "exit qty_pct must be 100 when present")
    return {
        "kind": kind,
        **({"price": float(price)} if price is not None else {}),
        **({"qty_pct": float(qty_pct)} if qty_pct is not None else {}),
    }


def validate_link_proposal(conn: sqlite3.Connection, payload: object) -> LinkProposal:
    """Validate the proposal shape and every source/candidate boundary."""
    _require(isinstance(payload, dict), "link proposal must be an object")
    _require(set(payload) == _TOP_KEYS, f"link proposal has missing or unknown keys: missing={sorted(_TOP_KEYS - set(payload))!r}, unknown={sorted(set(payload) - _TOP_KEYS)!r}")
    post_id = payload["post_id"]
    position_id = payload["proposed_position_id"]
    _require(isinstance(post_id, str) and post_id, "post_id must be a non-empty string")
    _require(isinstance(position_id, str) and position_id, "proposed_position_id must be a non-empty string")
    event = _validate_event(payload["proposed_event"])
    confidence = payload["confidence"]
    _require(_finite(confidence) and 0.0 <= float(confidence) <= 1.0, "confidence must be a finite number in [0, 1]")
    reasoning = payload["reasoning"]
    _require(isinstance(reasoning, str) and reasoning.strip(), "reasoning must be a non-empty string")
    alternatives = payload["alternatives"]
    _require(isinstance(alternatives, list) and all(isinstance(x, str) and x.strip() for x in alternatives), "alternatives must be a list of non-empty strings")

    source = conn.execute("SELECT p.*, c.kind, c.symbols FROM posts p JOIN post_class c ON c.post_id=p.post_id WHERE p.post_id=?", (post_id,)).fetchone()
    _require(source is not None, "source post does not exist or is not classified")
    _require(source["kind"] == "trade_event", "source post must be classified trade_event")
    _require(source["in_reply_to"] is None, "source post must be standalone")
    source_symbols = _symbols(source)
    _require(bool(source_symbols), "source post must name a symbol")
    position = conn.execute("SELECT * FROM positions WHERE position_id=?", (position_id,)).fetchone()
    _require(position is not None, "proposed position does not exist")
    _require(position["handle"] == source["handle"], "source post and position handle differ")
    _require(position["symbol"] in source_symbols, "source post and position symbol differ")
    _require(position["status"] in _OPEN_LIKE, "proposed position is not open-like")
    _require(position["opened_at"] is not None and source["ts_ist"] >= position["opened_at"], "source post is before position opened")
    _require(
        conn.execute("SELECT 1 FROM position_events WHERE post_id=? LIMIT 1", (post_id,)).fetchone() is None,
        "source post already backs a position event",
    )
    return LinkProposal(post_id, position_id, event, float(confidence), reasoning.strip(), tuple(x.strip() for x in alternatives))


def _candidate_positions(conn: sqlite3.Connection, post_id: str) -> list[dict[str, Any]]:
    source = conn.execute("SELECT p.handle, p.in_reply_to, c.kind, c.symbols FROM posts p JOIN post_class c ON c.post_id=p.post_id WHERE p.post_id=?", (post_id,)).fetchone()
    if source is None or source["kind"] != "trade_event":
        raise LinkValidationError("source post does not exist or is not classified trade_event")
    if source["in_reply_to"] is not None:
        raise LinkValidationError("source post must be standalone")
    if conn.execute("SELECT 1 FROM position_events WHERE post_id=? LIMIT 1", (post_id,)).fetchone() is not None:
        raise LinkValidationError("source post already backs a position event")
    symbols = _symbols(source)
    if not symbols:
        raise LinkValidationError("source post must name a symbol")
    marks = ",".join("?" for _ in symbols)
    rows = conn.execute(
        f"SELECT position_id, handle, symbol, status, root_post_id FROM positions WHERE handle=? AND symbol IN ({marks}) AND status IN ({','.join('?' for _ in _OPEN_LIKE)})",
        (source["handle"], *sorted(symbols), *sorted(_OPEN_LIKE)),
    ).fetchall()
    return [dict(row) for row in rows]


def propose_link(
    conn: sqlite3.Connection,
    post_id: str,
    *,
    chat_fn: Callable[..., provider.ProviderResult] = provider.chat,
) -> LinkProposal:
    """Ask the smart tier for one proposal against source-grounded candidates."""
    candidates = _candidate_positions(conn, post_id)
    if not candidates:
        raise LinkValidationError("source post has no same-handle/symbol open-like candidate")
    post = conn.execute("SELECT post_id, handle, ts_ist, text FROM posts WHERE post_id=?", (post_id,)).fetchone()
    result = chat_fn(
        tier="smart",
        system=_PROMPT.read_text(encoding="utf-8"),
        user=json.dumps({"source_post": dict(post), "candidate_positions": candidates}, ensure_ascii=False),
        task="link",
        conn=conn,
        ref_id=post_id,
        json_schema=True,
    )
    if not isinstance(result, provider.ProviderResult):
        raise TypeError("chat_fn must return ProviderResult")
    return validate_link_proposal(conn, result.content)


def _floor() -> float:
    value = config_get("reconcile.link_confidence_floor", 0.8)
    if not _finite(value) or not 0 <= float(value) <= 1:
        raise LinkValidationError("reconcile.link_confidence_floor must be a finite number in [0, 1]")
    return float(value)


def route_link_proposal(conn: sqlite3.Connection, payload: object) -> LinkRoute:
    """Queue below-floor proposals; audit and apply higher-confidence ones atomically."""
    # A byte-identical retry after application must be a no-op even though its
    # source post now legitimately backs an event.
    if isinstance(payload, dict) and set(payload) == _TOP_KEYS:
        try:
            tentative = LinkProposal(
                payload["post_id"], payload["proposed_position_id"], _validate_event(payload["proposed_event"]),
                float(payload["confidence"]), payload["reasoning"].strip(), tuple(item.strip() for item in payload["alternatives"]),
            )
            existing = conn.execute(
                "SELECT id, status FROM review_queue WHERE kind='link_event' AND post_id=? AND position_id=? AND proposed_json=?",
                (tentative.post_id, tentative.proposed_position_id, _canonical_json(tentative)),
            ).fetchone()
            if existing is not None:
                return LinkRoute(existing["id"], existing["status"], existing["status"] == "accepted", tentative)
        except (KeyError, AttributeError, TypeError, ValueError, LinkValidationError):
            pass

    proposal = validate_link_proposal(conn, payload)
    proposed_json = _canonical_json(proposal)
    status = "accepted" if proposal.confidence >= _floor() else "open"
    question = f"Attach {proposal.proposed_event['kind']} from post {proposal.post_id} to position {proposal.proposed_position_id}?"
    source = conn.execute("SELECT is_mock FROM posts WHERE post_id=?", (proposal.post_id,)).fetchone()
    source_is_mock = int(source["is_mock"]) if source is not None else 0
    resolved_at = now_iso() if status == "accepted" else None
    with conn:
        cur = conn.execute(
            "INSERT INTO review_queue (kind,post_id,position_id,question,proposed_json,confidence,status,resolved_by,resolved_at,is_mock,ingested_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            ("link_event", proposal.post_id, proposal.proposed_position_id, question, proposed_json, proposal.confidence, status, "auto" if status == "accepted" else None, resolved_at, source_is_mock, now_iso()),
        )
        item_id = int(cur.lastrowid)
        if status == "accepted":
            apply_accepted_link(conn, proposal.to_dict())
    return LinkRoute(item_id, status, status == "accepted", proposal)


# ---------------------------------------------------------------------------
# W3 runtime producer: one idempotent pass over every eligible post
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LinkPassResult:
    """Outcome of one ``run_link_pass``; per-post errors are never fatal."""

    eligible: int          # posts that passed the full eligibility filter
    queued: int            # routed below-floor -> open review items
    applied: int           # routed at/above floor -> auto-applied
    failures: tuple[tuple[str, str], ...]  # (post_id, error); never raised outward


def run_link_pass(
    conn: sqlite3.Connection,
    *,
    chat_fn: Callable[..., provider.ProviderResult] = provider.chat,
    limit: int | None = None,
) -> LinkPassResult:
    """Propose and route links for every eligible standalone trade event.

    Idempotency is structural, not tracked: the coarse filter excludes any
    post that already backs a ``position_events`` row or has ANY
    ``review_queue`` row of kind ``link_event`` (open, accepted, or
    rejected), so a rejected post is never re-queued, an open one is never
    re-proposed, and a second pass over processed data makes zero provider
    calls and zero writes.  A per-post error (provider raises, or the
    returned proposal fails ``validate_link_proposal``) is recorded in
    ``failures`` and the pass continues; the pass never raises outward.
    """
    sql = (
        "SELECT p.post_id, c.symbols FROM posts p "
        "JOIN post_class c ON c.post_id = p.post_id "
        "WHERE c.kind = 'trade_event' AND p.in_reply_to IS NULL "
        "AND NOT EXISTS (SELECT 1 FROM position_events e WHERE e.post_id = p.post_id) "
        "AND NOT EXISTS (SELECT 1 FROM review_queue r WHERE r.kind = 'link_event' AND r.post_id = p.post_id) "
        "ORDER BY p.ts_ist, p.post_id"
    )
    if limit is not None:
        rows = conn.execute(sql + " LIMIT ?", (limit,)).fetchall()
    else:
        rows = conn.execute(sql).fetchall()

    eligible = 0
    queued = 0
    applied = 0
    failures: list[tuple[str, str]] = []
    for row in rows:
        post_id = row["post_id"]
        # Fine filter on top of the coarse SQL, reusing the module's own
        # gates: non-empty parsed symbols and at least one same-handle/
        # symbol open-like candidate.  Failing it is a silent skip -- not a
        # failure, not eligible.
        if not _symbols(row):
            continue
        try:
            if not _candidate_positions(conn, post_id):
                continue
        except LinkValidationError:
            continue
        eligible += 1
        try:
            proposal = propose_link(conn, post_id, chat_fn=chat_fn)
            routed = route_link_proposal(conn, proposal.to_dict())
        except Exception as exc:  # noqa: BLE001 - per-post isolation is the contract
            failures.append((post_id, str(exc)))
            continue
        if routed.status == "open":
            queued += 1
        elif routed.status == "accepted":
            applied += 1
    return LinkPassResult(eligible, queued, applied, tuple(failures))
