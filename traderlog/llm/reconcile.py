"""Contract-validated, auditable thread reconciliation for W2.

This module is the sole writer of ``positions`` and ``position_events``
(CANONICAL.md #6, CONTRACTS.md #3). It re-derives the COMPLETE current state of
a position from the WHOLE thread every time it runs -- never a patch on the
previous answer. That is what makes it testable against frozen fixtures and
what keeps a multi-week thread from drifting.

Style and validation posture matches ``llm/classify.py``: a strict payload
validator that REJECTS anything that violates the contract (rather than
silently repairing it), a ``chat_fn``-injectable entrypoint for testing without
network access, and an ``apply_verified_*`` path for a human-audited state that
never touches the LLM.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from traderlog.db import now_iso
from traderlog.llm import provider


_STATUSES = frozenset({"open", "added", "partial", "closed", "scratched", "unclear"})
_TICKER_RE = re.compile(r"^[A-Z][A-Z0-9]{0,29}$")
_PROMPT = Path(__file__).with_name("prompts") / "reconcile.md"

_TOP_KEYS = frozenset(
    {
        "symbol", "status", "entries", "adds", "stop", "targets", "exits",
        "net_result_pct", "holding_days", "confidence", "unresolved", "evidence",
    }
)

# Event kinds this module writes to position_events (db/schema.sql #4).
_EVENT_ENTRY = "entry"
_EVENT_ADD = "add"
_EVENT_SL_SET = "sl_set"
_EVENT_SL_MOVE = "sl_move"
_EVENT_TARGET_SET = "target_set"
_EVENT_TARGET_HIT = "target_hit"
_EVENT_PARTIAL_EXIT = "partial_exit"
_EVENT_EXIT = "exit"
_EVENT_SCRATCH = "scratch"


class ReconcileValidationError(ValueError):
    """Reconciler output violates the stable W2 contract or the source thread."""


# ---------------------------------------------------------------------------
# normalized shapes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Entry:
    price: float
    date: str | None
    size_note: str | None
    post_id: str


@dataclass(frozen=True)
class Add:
    price: float
    date: str | None
    qty_pct: float | None
    post_id: str


@dataclass(frozen=True)
class Stop:
    price: float
    post_id: str
    moved_from: float | None


@dataclass(frozen=True)
class Target:
    price: float
    hit: bool
    post_id: str


@dataclass(frozen=True)
class Exit:
    price: float | None
    date: str | None
    qty_pct: float | None
    post_id: str


@dataclass(frozen=True)
class ReconciledPosition:
    symbol: str
    status: str
    entries: tuple[Entry, ...]
    adds: tuple[Add, ...]
    stop: Stop | None
    targets: tuple[Target, ...]
    exits: tuple[Exit, ...]
    net_result_pct: float | None
    holding_days: int | None
    confidence: float
    unresolved: tuple[str, ...]
    evidence: Mapping[str, str] = field(default_factory=dict)

    def to_state_dict(self) -> dict[str, Any]:
        """Canonical, key-ordered dict. Same input -> byte-identical JSON.

        Key order and array order are fixed (never re-sorted) so idempotence is
        testable with a plain string comparison, matching CONTRACTS.md #3.
        """
        return {
            "symbol": self.symbol,
            "status": self.status,
            "entries": [
                {
                    k: v
                    for k, v in (
                        ("price", e.price),
                        ("date", e.date),
                        ("size_note", e.size_note),
                        ("post_id", e.post_id),
                    )
                    if v is not None or k in ("price", "post_id")
                }
                for e in self.entries
            ],
            "adds": [
                {
                    k: v
                    for k, v in (
                        ("price", a.price),
                        ("date", a.date),
                        ("qty_pct", a.qty_pct),
                        ("post_id", a.post_id),
                    )
                    if v is not None or k in ("price", "post_id")
                }
                for a in self.adds
            ],
            "stop": (
                {
                    k: v
                    for k, v in (
                        ("price", self.stop.price),
                        ("post_id", self.stop.post_id),
                        ("moved_from", self.stop.moved_from),
                    )
                    if v is not None or k in ("price", "post_id")
                }
                if self.stop
                else None
            ),
            "targets": [
                {"price": t.price, "hit": t.hit, "post_id": t.post_id}
                for t in self.targets
            ],
            "exits": [
                {
                    k: v
                    for k, v in (
                        ("price", ex.price),
                        ("date", ex.date),
                        ("qty_pct", ex.qty_pct),
                        ("post_id", ex.post_id),
                    )
                    if v is not None or k == "post_id"
                }
                for ex in self.exits
            ],
            "net_result_pct": self.net_result_pct,
            "holding_days": self.holding_days,
            "confidence": self.confidence,
            "unresolved": list(self.unresolved),
            "evidence": dict(self.evidence),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_state_dict(), ensure_ascii=False, sort_keys=False)


# ---------------------------------------------------------------------------
# prompt + thread hashing
# ---------------------------------------------------------------------------


def _system_prompt() -> str:
    return _PROMPT.read_text(encoding="utf-8")


def _post_text(post: Any) -> str:
    """`post["text"]`, tolerating both a plain dict and a sqlite3.Row (no .get)."""
    try:
        return post["text"] or ""
    except (KeyError, IndexError):
        return ""


_HASH_SEP = "\x1f"  # ASCII unit separator -- avoids "ab"+"c" == "a"+"bc" collisions


def thread_hash(posts: Sequence[Mapping[str, Any]], vision_by_post: Mapping[str, Any]) -> str:
    """sha256 of the concatenated thread content, in the given (chronological) order.

    Sensitive to both new posts AND new vision annotations on existing posts, so
    a vision pass that lands after the first reconciliation still invalidates
    the cache. CONTRACTS.md #3: "cache on thread_hash ... an unchanged thread
    must cost zero LLM calls."
    """
    digest = hashlib.sha256()
    for post in posts:
        digest.update(str(post["post_id"]).encode("utf-8"))
        digest.update(_HASH_SEP.encode("utf-8"))
        digest.update(_post_text(post).encode("utf-8"))
        digest.update(_HASH_SEP.encode("utf-8"))
        vision = vision_by_post.get(post["post_id"]) or []
        digest.update(
            json.dumps(vision, ensure_ascii=False, sort_keys=True).encode("utf-8")
        )
        digest.update(_HASH_SEP.encode("utf-8"))
    return digest.hexdigest()


def position_id(handle: str, symbol: str, root_post_id: str) -> str:
    """sha1(handle|symbol|root_post_id) -- db/schema.sql #4."""
    return hashlib.sha1(f"{handle}|{symbol}|{root_post_id}".encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# validation
#
# Which fields require an evidence citation, and which are exempt, is the one
# place CONTRACTS.md #3 is genuinely ambiguous: its prose says "every populated
# field", but its own worked example does NOT cite `status` even though
# `status: "added"` is populated. Judgment call made here (see the wave's
# report): `status`, `confidence`, `unresolved` and `evidence` itself are
# meta/derived fields, not extracted facts, and are EXEMPT from citation. Every
# stated number/date/qty IS required to cite the post it came from. A `hit`
# flag only needs a citation when it asserts `true` -- `false` is the default,
# uncontested state and needs no evidence.
# ---------------------------------------------------------------------------


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise ReconcileValidationError(msg)


def _is_finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _check_post_id(post_id: Any, valid_post_ids: frozenset[str], where: str) -> str:
    _require(isinstance(post_id, str) and post_id, f"{where}: post_id must be a non-empty string")
    _require(post_id in valid_post_ids, f"{where}: post_id {post_id!r} is not in the input thread")
    return post_id


def _thread_text(posts: Sequence[Mapping[str, Any]]) -> str:
    return "\n".join(_post_text(p) for p in posts)


def validate_reconciliation(
    payload: object,
    posts: Sequence[Mapping[str, Any]],
) -> ReconciledPosition:
    """Normalize one reconciler payload and reject anything the thread can't support.

    `posts` is the exact chronological thread the model was given -- every cited
    post_id must belong to it, and the symbol must actually appear somewhere in
    it (same discipline as classify.validate_classification's symbol check).
    """
    if not isinstance(payload, dict):
        raise ReconcileValidationError("reconciliation must be an object")
    actual_keys = frozenset(payload)
    missing = _TOP_KEYS - actual_keys
    unknown = actual_keys - _TOP_KEYS
    _require(not missing, f"reconciliation missing keys: {sorted(missing)!r}")
    _require(not unknown, f"reconciliation has unknown keys: {sorted(unknown)!r}")

    valid_post_ids = frozenset(str(p["post_id"]) for p in posts)
    _require(bool(valid_post_ids), "reconciliation given an empty thread")
    thread_text = _thread_text(posts)

    evidence_raw = payload["evidence"]
    _require(isinstance(evidence_raw, dict), "evidence must be an object")
    for key, value in evidence_raw.items():
        _require(isinstance(key, str) and key, "evidence keys must be non-empty strings")
        _require(
            isinstance(value, str) and value in valid_post_ids,
            f"evidence[{key!r}] cites post_id {value!r}, not present in the input thread",
        )
    evidence: dict[str, str] = dict(evidence_raw)
    cited: set[str] = set()

    def cite(path: str) -> str:
        _require(path in evidence, f"field {path!r} is populated but has no evidence[{path!r}] citation")
        cited.add(path)
        return evidence[path]

    # --- symbol -------------------------------------------------------
    symbol_value = payload["symbol"]
    _require(isinstance(symbol_value, str) and symbol_value, "symbol must be a non-empty string")
    symbol = symbol_value.upper()
    _require(_TICKER_RE.fullmatch(symbol) is not None, "symbol is not a conservative ticker token")
    _require(
        re.search(rf"(?<![A-Za-z0-9_])#?{re.escape(symbol)}(?![A-Za-z0-9_])", thread_text, re.IGNORECASE)
        is not None,
        "symbol does not appear anywhere in the input thread",
    )
    cite("symbol")

    # --- status ---------------------------------------------------------
    status = payload["status"]
    _require(status in _STATUSES, "status is not in the reconciler enum")
    # status is exempt from citation -- see module-level note above.

    # --- entries ----------------------------------------------------------
    entries_raw = payload["entries"]
    _require(isinstance(entries_raw, list), "entries must be a list")
    entries: list[Entry] = []
    for i, raw in enumerate(entries_raw):
        _require(isinstance(raw, dict), f"entries[{i}] must be an object")
        price = raw.get("price")
        _require(_is_finite_number(price), f"entries[{i}].price must be a finite number")
        post_id = _check_post_id(raw.get("post_id"), valid_post_ids, f"entries[{i}]")
        cite(f"entries[{i}].price")
        date = raw.get("date")
        _require(date is None or isinstance(date, str), f"entries[{i}].date must be a string or null")
        if date is not None:
            cite(f"entries[{i}].date")
        size_note = raw.get("size_note")
        _require(
            size_note is None or isinstance(size_note, str), f"entries[{i}].size_note must be a string or null"
        )
        if size_note is not None:
            cite(f"entries[{i}].size_note")
        extra = set(raw) - {"price", "date", "size_note", "post_id"}
        _require(not extra, f"entries[{i}] has unknown keys: {sorted(extra)!r}")
        entries.append(Entry(price=float(price), date=date, size_note=size_note, post_id=post_id))

    # --- adds -------------------------------------------------------------
    adds_raw = payload["adds"]
    _require(isinstance(adds_raw, list), "adds must be a list")
    adds: list[Add] = []
    for i, raw in enumerate(adds_raw):
        _require(isinstance(raw, dict), f"adds[{i}] must be an object")
        price = raw.get("price")
        _require(_is_finite_number(price), f"adds[{i}].price must be a finite number")
        post_id = _check_post_id(raw.get("post_id"), valid_post_ids, f"adds[{i}]")
        cite(f"adds[{i}].price")
        date = raw.get("date")
        _require(date is None or isinstance(date, str), f"adds[{i}].date must be a string or null")
        if date is not None:
            cite(f"adds[{i}].date")
        qty_pct = raw.get("qty_pct")
        _require(
            qty_pct is None or (_is_finite_number(qty_pct) and 0 < qty_pct <= 100),
            f"adds[{i}].qty_pct must be null or a number in (0, 100]",
        )
        if qty_pct is not None:
            cite(f"adds[{i}].qty_pct")
        extra = set(raw) - {"price", "date", "qty_pct", "post_id"}
        _require(not extra, f"adds[{i}] has unknown keys: {sorted(extra)!r}")
        adds.append(Add(price=float(price), date=date, qty_pct=qty_pct, post_id=post_id))

    # --- stop ---------------------------------------------------------------
    stop_raw = payload["stop"]
    stop: Stop | None = None
    if stop_raw is not None:
        _require(isinstance(stop_raw, dict), "stop must be an object or null")
        price = stop_raw.get("price")
        _require(_is_finite_number(price), "stop.price must be a finite number")
        post_id = _check_post_id(stop_raw.get("post_id"), valid_post_ids, "stop")
        cite("stop.price")
        moved_from = stop_raw.get("moved_from")
        _require(
            moved_from is None or _is_finite_number(moved_from), "stop.moved_from must be a number or null"
        )
        if moved_from is not None:
            cite("stop.moved_from")
        extra = set(stop_raw) - {"price", "post_id", "moved_from"}
        _require(not extra, f"stop has unknown keys: {sorted(extra)!r}")
        stop = Stop(price=float(price), post_id=post_id, moved_from=moved_from)

    # --- targets --------------------------------------------------------
    targets_raw = payload["targets"]
    _require(isinstance(targets_raw, list), "targets must be a list")
    targets: list[Target] = []
    for i, raw in enumerate(targets_raw):
        _require(isinstance(raw, dict), f"targets[{i}] must be an object")
        price = raw.get("price")
        _require(_is_finite_number(price), f"targets[{i}].price must be a finite number")
        post_id = _check_post_id(raw.get("post_id"), valid_post_ids, f"targets[{i}]")
        cite(f"targets[{i}].price")
        hit = raw.get("hit")
        _require(isinstance(hit, bool), f"targets[{i}].hit must be a boolean")
        if hit:
            cite(f"targets[{i}].hit")
        extra = set(raw) - {"price", "hit", "post_id"}
        _require(not extra, f"targets[{i}] has unknown keys: {sorted(extra)!r}")
        targets.append(Target(price=float(price), hit=hit, post_id=post_id))

    # --- exits ------------------------------------------------------------
    exits_raw = payload["exits"]
    _require(isinstance(exits_raw, list), "exits must be a list")
    exits: list[Exit] = []
    for i, raw in enumerate(exits_raw):
        _require(isinstance(raw, dict), f"exits[{i}] must be an object")
        post_id = _check_post_id(raw.get("post_id"), valid_post_ids, f"exits[{i}]")
        price = raw.get("price")
        _require(price is None or _is_finite_number(price), f"exits[{i}].price must be a number or null")
        if price is not None:
            cite(f"exits[{i}].price")
        date = raw.get("date")
        _require(date is None or isinstance(date, str), f"exits[{i}].date must be a string or null")
        if date is not None:
            cite(f"exits[{i}].date")
        qty_pct = raw.get("qty_pct")
        _require(
            qty_pct is None or (_is_finite_number(qty_pct) and 0 < qty_pct <= 100),
            f"exits[{i}].qty_pct must be null or a number in (0, 100]",
        )
        if qty_pct is not None:
            cite(f"exits[{i}].qty_pct")
        extra = set(raw) - {"price", "date", "qty_pct", "post_id"}
        _require(not extra, f"exits[{i}] has unknown keys: {sorted(extra)!r}")
        exits.append(Exit(price=price, date=date, qty_pct=qty_pct, post_id=post_id))

    # --- net_result_pct / holding_days --------------------------------------
    net_result_pct = payload["net_result_pct"]
    _require(
        net_result_pct is None or _is_finite_number(net_result_pct),
        "net_result_pct must be a number or null",
    )
    if net_result_pct is not None:
        cite("net_result_pct")
    # reconcile.md: "fill this ONLY when the trader stated a result ... or when
    # both an entry and exit price were stated". That rule is SEMANTIC (did the
    # text actually say this?), not structural, so it cannot be mechanically
    # re-verified here the way a citation or an enum membership can -- the same
    # posture classify.py takes with its free-text `reason` field. The citation
    # requirement above is the structural half of the guarantee: any
    # net_result_pct that reaches the database still has to name the post that
    # justifies it.

    holding_days = payload["holding_days"]
    _require(
        holding_days is None or (isinstance(holding_days, int) and not isinstance(holding_days, bool) and holding_days >= 0),
        "holding_days must be a non-negative integer or null",
    )
    if holding_days is not None:
        cite("holding_days")

    # --- confidence / unresolved --------------------------------------------
    confidence = payload["confidence"]
    _require(_is_finite_number(confidence), "confidence must be a finite number")
    confidence = float(confidence)
    _require(0.0 <= confidence <= 1.0, "confidence must be between 0 and 1")

    unresolved_raw = payload["unresolved"]
    _require(isinstance(unresolved_raw, list), "unresolved must be a list")
    unresolved: list[str] = []
    for i, item in enumerate(unresolved_raw):
        _require(isinstance(item, str) and item.strip(), f"unresolved[{i}] must be a non-empty string")
        unresolved.append(item.strip())

    # --- no stray evidence entries -------------------------------------
    stray = set(evidence) - cited
    _require(
        not stray,
        f"evidence cites fields that are not populated or do not exist: {sorted(stray)!r}",
    )

    return ReconciledPosition(
        symbol=symbol,
        status=status,
        entries=tuple(entries),
        adds=tuple(adds),
        stop=stop,
        targets=tuple(targets),
        exits=tuple(exits),
        net_result_pct=float(net_result_pct) if net_result_pct is not None else None,
        holding_days=int(holding_days) if holding_days is not None else None,
        confidence=confidence,
        unresolved=tuple(unresolved),
        evidence=evidence,
    )


# ---------------------------------------------------------------------------
# thread loading
# ---------------------------------------------------------------------------


def _load_thread(conn: sqlite3.Connection, root_post_id: str) -> list[sqlite3.Row]:
    """The root post plus the SAME author's replies within its conversation.

    reconcile.md: "a root post and the author's own replies to it" -- replies
    from other people in the same conversation_id are not part of the trader's
    own record of the position and are deliberately excluded.

    A post with no ancestry has conversation_id = NULL, so the fallback query
    below binds root_post_id -- but the root's own row still has
    conversation_id = NULL and therefore does not match its own query. Such a
    post reconciles as a single-post thread of one: the root is appended
    explicitly if the query didn't already return it (it does for posts that
    have a real conversation_id, since the root's own conversation_id then
    matches itself -- a no-op for that case).
    """
    root = conn.execute(
        "SELECT * FROM posts WHERE post_id = ?", (root_post_id,)
    ).fetchone()
    if root is None:
        raise ValueError(f"root_post_id {root_post_id!r} does not exist")
    rows = conn.execute(
        "SELECT * FROM posts WHERE conversation_id = ? AND handle = ? "
        "ORDER BY ts_utc ASC, post_id ASC",
        (root["conversation_id"] or root_post_id, root["handle"]),
    ).fetchall()
    if root["post_id"] not in {row["post_id"] for row in rows}:
        rows = [*rows, root]
        rows.sort(key=lambda row: (row["ts_utc"], row["post_id"]))
    # Accepted cross-thread links are canonical evidence too.  They have no X
    # reply ancestry, so include their cited source posts explicitly; otherwise
    # a later unchanged reconciliation would hash only the original thread and
    # silently overwrite the accepted event.
    position = conn.execute(
        "SELECT position_id FROM positions WHERE root_post_id = ?", (root_post_id,)
    ).fetchone()
    if position is not None:
        linked = conn.execute(
            """SELECT p.* FROM review_queue q JOIN posts p ON p.post_id=q.post_id
                 WHERE q.kind='link_event' AND q.status='accepted' AND q.position_id=?
                 ORDER BY p.ts_utc ASC, p.post_id ASC""",
            (position["position_id"],),
        ).fetchall()
        known = {row["post_id"] for row in rows}
        rows = [*rows, *(row for row in linked if row["post_id"] not in known)]
        rows.sort(key=lambda row: (row["ts_utc"], row["post_id"]))
    return list(rows)


def _load_vision_by_post(
    conn: sqlite3.Connection, post_ids: Sequence[str]
) -> dict[str, list[dict]]:
    if not post_ids:
        return {}
    placeholders = ",".join("?" for _ in post_ids)
    rows = conn.execute(
        f"SELECT post_id, idx, vision_json FROM post_media "  # noqa: S608 - fixed column set
        f"WHERE post_id IN ({placeholders}) ORDER BY post_id, idx",
        tuple(post_ids),
    ).fetchall()
    out: dict[str, list[dict]] = {}
    for row in rows:
        if row["vision_json"]:
            out.setdefault(row["post_id"], []).append(json.loads(row["vision_json"]))
    return out


def _build_user_payload(posts: Sequence[sqlite3.Row], vision_by_post: Mapping[str, list[dict]]) -> str:
    thread = [
        {
            "post_id": p["post_id"],
            "ts_ist": p["ts_ist"],
            "text": p["text"] or "",
            "vision": vision_by_post.get(p["post_id"], []),
        }
        for p in posts
    ]
    return json.dumps({"thread": thread}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# writes -- positions + position_events, the two tables this module owns
# ---------------------------------------------------------------------------


def _existing_thread_hash(conn: sqlite3.Connection, root_post_id: str) -> tuple[str, str] | None:
    row = conn.execute(
        "SELECT position_id, thread_hash FROM positions WHERE root_post_id = ?",
        (root_post_id,),
    ).fetchone()
    if row is None:
        return None
    return row["position_id"], row["thread_hash"]


def _event_rows(
    result: ReconciledPosition, posts: Sequence[sqlite3.Row]
) -> list[dict[str, Any]]:
    """Flatten the re-derived state into position_events rows, in thread order.

    Re-derived from scratch every call -- the caller replaces ALL existing
    events for this position_id rather than patching, matching "never
    incremental" (CONTRACTS.md #3).
    """
    order = {p["post_id"]: i for i, p in enumerate(posts)}
    stated_at = {p["post_id"]: p["ts_ist"] for p in posts}
    rows: list[dict[str, Any]] = []

    def add_row(kind: str, post_id: str, *, price: float | None, qty_pct: float | None, note: str | None) -> None:
        rows.append(
            {
                "post_id": post_id,
                "kind": kind,
                "price": price,
                "qty_pct": qty_pct,
                "stated_at": stated_at.get(post_id),
                "seq_key": (order.get(post_id, 0), len(rows)),
                "confidence": result.confidence,
                "note": note,
            }
        )

    for e in result.entries:
        add_row(_EVENT_ENTRY, e.post_id, price=e.price, qty_pct=None, note=e.size_note)
    for a in result.adds:
        add_row(_EVENT_ADD, a.post_id, price=a.price, qty_pct=a.qty_pct, note=None)
    if result.stop is not None:
        kind = _EVENT_SL_MOVE if result.stop.moved_from is not None else _EVENT_SL_SET
        note = f"moved from {result.stop.moved_from}" if result.stop.moved_from is not None else None
        add_row(kind, result.stop.post_id, price=result.stop.price, qty_pct=None, note=note)
    for t in result.targets:
        add_row(
            _EVENT_TARGET_HIT if t.hit else _EVENT_TARGET_SET,
            t.post_id,
            price=t.price,
            qty_pct=None,
            note=None,
        )
    for ex in result.exits:
        kind = _EVENT_PARTIAL_EXIT if (ex.qty_pct is not None and ex.qty_pct < 100) else _EVENT_EXIT
        if result.status == "scratched":
            kind = _EVENT_SCRATCH
        add_row(kind, ex.post_id, price=ex.price, qty_pct=ex.qty_pct, note=None)

    rows.sort(key=lambda r: r["seq_key"])
    for seq, row in enumerate(rows):
        row["seq"] = seq
        del row["seq_key"]
    return rows


def _write_position(
    conn: sqlite3.Connection,
    *,
    handle: str,
    root_post_id: str,
    result: ReconciledPosition,
    posts: Sequence[sqlite3.Row],
    thread_hash_value: str,
    model: str,
    is_mock: int,
    transactional: bool = True,
) -> str:
    """Replace one complete position state and its derived events.

    ``transactional=False`` lets review resolution compose its queue decision and
    this sole-writer mutation into one SQLite transaction.
    """
    if transactional:
        with conn:
            return _write_position(
                conn, handle=handle, root_post_id=root_post_id, result=result, posts=posts,
                thread_hash_value=thread_hash_value, model=model, is_mock=is_mock, transactional=False,
            )
    pos_id = position_id(handle, result.symbol, root_post_id)
    root = next((post for post in posts if post["post_id"] == root_post_id), None)
    opened_at = root["ts_ist"] if root is not None else (posts[0]["ts_ist"] if posts else None)
    closed_at = None
    if result.status in ("closed", "scratched") and result.exits:
        last_exit = result.exits[-1]
        exit_post = next((post for post in posts if post["post_id"] == last_exit.post_id), None)
        closed_at = last_exit.date or (exit_post["ts_ist"] if exit_post is not None else None)

    conn.execute(
        """INSERT INTO positions
               (position_id, handle, symbol, root_post_id, status, opened_at, closed_at,
                net_result_pct, holding_days, confidence, state_json, evidence_json,
                unresolved_json, thread_hash, reconciled_at, reconcile_model, is_mock,
                ingested_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(position_id) DO UPDATE SET
                 status=excluded.status,
                 opened_at=excluded.opened_at,
                 closed_at=excluded.closed_at,
                 net_result_pct=excluded.net_result_pct,
                 holding_days=excluded.holding_days,
                 confidence=excluded.confidence,
                 state_json=excluded.state_json,
                 evidence_json=excluded.evidence_json,
                 unresolved_json=excluded.unresolved_json,
                 thread_hash=excluded.thread_hash,
                 reconciled_at=excluded.reconciled_at,
                 reconcile_model=excluded.reconcile_model,
                 is_mock=excluded.is_mock""",
        (
            pos_id,
            handle,
            result.symbol,
            root_post_id,
            result.status,
            opened_at,
            closed_at,
            result.net_result_pct,
            result.holding_days,
            result.confidence,
            result.to_json(),
            json.dumps(result.evidence, ensure_ascii=False, sort_keys=True),
            json.dumps(list(result.unresolved), ensure_ascii=False),
            thread_hash_value,
            now_iso(),
            model,
            is_mock,
            now_iso(),
        ),
    )
    # Re-derived from scratch: replace this position's events wholesale rather
    # than patching them (CONTRACTS.md #3, "never incremental").
    conn.execute("DELETE FROM position_events WHERE position_id = ?", (pos_id,))
    for row in _event_rows(result, posts):
        conn.execute(
            """INSERT INTO position_events
                   (position_id, post_id, kind, price, qty_pct, stated_at, seq,
                    confidence, note, is_mock, ingested_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                pos_id,
                row["post_id"],
                row["kind"],
                row["price"],
                row["qty_pct"],
                row["stated_at"],
                row["seq"],
                row["confidence"],
                row["note"],
                is_mock,
                now_iso(),
            ),
        )
    return pos_id


def _load_state(conn: sqlite3.Connection, position_id_value: str) -> ReconciledPosition:
    row = conn.execute(
        "SELECT state_json FROM positions WHERE position_id = ?", (position_id_value,)
    ).fetchone()
    state = json.loads(row["state_json"])
    return ReconciledPosition(
        symbol=state["symbol"],
        status=state["status"],
        entries=tuple(Entry(price=e["price"], date=e.get("date"), size_note=e.get("size_note"), post_id=e["post_id"]) for e in state["entries"]),
        adds=tuple(Add(price=a["price"], date=a.get("date"), qty_pct=a.get("qty_pct"), post_id=a["post_id"]) for a in state["adds"]),
        stop=(Stop(price=state["stop"]["price"], post_id=state["stop"]["post_id"], moved_from=state["stop"].get("moved_from")) if state["stop"] else None),
        targets=tuple(Target(price=t["price"], hit=t["hit"], post_id=t["post_id"]) for t in state["targets"]),
        exits=tuple(Exit(price=ex.get("price"), date=ex.get("date"), qty_pct=ex.get("qty_pct"), post_id=ex["post_id"]) for ex in state["exits"]),
        net_result_pct=state["net_result_pct"],
        holding_days=state["holding_days"],
        confidence=state["confidence"],
        unresolved=tuple(state["unresolved"]),
        evidence=state["evidence"],
    )


def _accepted_link_result(
    current: ReconciledPosition,
    proposal: Mapping[str, Any],
    source_post_id: str,
) -> ReconciledPosition:
    """Apply one source-cited event to a complete persisted position state."""
    raw_event = proposal.get("proposed_event")
    if not isinstance(raw_event, Mapping):
        raise ReconcileValidationError("accepted link proposed_event must be an object")
    kind = raw_event.get("kind")
    if kind not in {"exit", "partial_exit", "add", "stop", "target"}:
        raise ReconcileValidationError("accepted link event kind is not supported")
    extra = set(raw_event) - {"kind", "price", "qty_pct"}
    if extra:
        raise ReconcileValidationError(f"accepted link event has unknown keys: {sorted(extra)!r}")
    price = raw_event.get("price")
    if kind in {"add", "stop", "target"}:
        if not (_is_finite_number(price) and float(price) > 0):
            raise ReconcileValidationError("accepted link price must be a positive finite number")
    elif price is not None and not (_is_finite_number(price) and float(price) > 0):
        raise ReconcileValidationError("accepted link price must be null or a positive finite number")
    qty_pct = raw_event.get("qty_pct")
    if qty_pct is not None and not (_is_finite_number(qty_pct) and 0 < float(qty_pct) <= 100):
        raise ReconcileValidationError("accepted link qty_pct must be in (0, 100]")
    if kind == "partial_exit" and not (qty_pct is not None and float(qty_pct) < 100):
        raise ReconcileValidationError("accepted partial exit requires qty_pct below 100")
    if kind == "exit" and qty_pct is not None and float(qty_pct) != 100:
        raise ReconcileValidationError("accepted exit qty_pct must be 100 when present")
    confidence = proposal.get("confidence")
    if not (_is_finite_number(confidence) and 0 <= float(confidence) <= 1):
        raise ReconcileValidationError("accepted link confidence must be in [0, 1]")

    evidence = dict(current.evidence)
    entries, adds, targets, exits = list(current.entries), list(current.adds), list(current.targets), list(current.exits)
    stop = current.stop
    status = current.status
    price_value = float(price) if price is not None else None
    qty_value = float(qty_pct) if qty_pct is not None else None
    if kind == "add":
        adds.append(Add(price=price_value, date=None, qty_pct=qty_value, post_id=source_post_id))
        index = len(adds) - 1
        evidence[f"adds[{index}].price"] = source_post_id
        if qty_value is not None:
            evidence[f"adds[{index}].qty_pct"] = source_post_id
        status = "added"
    elif kind == "stop":
        moved_from = stop.price if stop is not None else None
        stop = Stop(price=price_value, post_id=source_post_id, moved_from=moved_from)
        evidence["stop.price"] = source_post_id
        if moved_from is not None:
            prior_citation = current.evidence.get("stop.price")
            if not prior_citation:
                raise ReconcileValidationError("existing stop has no evidence citation")
            evidence["stop.moved_from"] = prior_citation
    elif kind == "target":
        targets.append(Target(price=price_value, hit=False, post_id=source_post_id))
        evidence[f"targets[{len(targets) - 1}].price"] = source_post_id
    else:
        exits.append(Exit(price=price_value, date=None, qty_pct=qty_value, post_id=source_post_id))
        index = len(exits) - 1
        if price_value is not None:
            evidence[f"exits[{index}].price"] = source_post_id
        if qty_value is not None:
            evidence[f"exits[{index}].qty_pct"] = source_post_id
        status = "partial" if kind == "partial_exit" else "closed"
    return ReconciledPosition(
        symbol=current.symbol,
        status=status,
        entries=tuple(entries), adds=tuple(adds), stop=stop, targets=tuple(targets), exits=tuple(exits),
        net_result_pct=current.net_result_pct, holding_days=current.holding_days,
        confidence=min(current.confidence, float(confidence)), unresolved=current.unresolved, evidence=evidence,
    )


def apply_accepted_link(conn: sqlite3.Connection, proposal: Mapping[str, Any]) -> ReconciledPosition:
    """Sole-writer path for one already-validated accepted link proposal.

    The queue resolver owns the decision row; this helper owns all position and
    event mutation.  It rechecks the cited source and complete canonical state
    before replacing the position's derived event rows.
    """
    post_id = proposal.get("post_id")
    position_id_value = proposal.get("proposed_position_id")
    if not isinstance(post_id, str) or not post_id or not isinstance(position_id_value, str) or not position_id_value:
        raise ReconcileValidationError("accepted link requires post_id and proposed_position_id")
    position = conn.execute("SELECT * FROM positions WHERE position_id=?", (position_id_value,)).fetchone()
    source = conn.execute(
        "SELECT p.*, c.kind, c.symbols FROM posts p JOIN post_class c ON c.post_id=p.post_id WHERE p.post_id=?",
        (post_id,),
    ).fetchone()
    if position is None or source is None:
        raise ReconcileValidationError("accepted link source post or position is missing")
    if source["kind"] != "trade_event" or source["handle"] != position["handle"]:
        raise ReconcileValidationError("accepted link source is not a same-handle trade event")
    if source["in_reply_to"] is not None:
        raise ReconcileValidationError("accepted link source post must be standalone")
    try:
        source_symbols = {s.upper() for s in json.loads(source["symbols"] or "[]") if isinstance(s, str)}
    except (TypeError, ValueError):
        source_symbols = set()
    if position["symbol"] not in source_symbols:
        raise ReconcileValidationError("accepted link source and position symbol differ")
    if position["opened_at"] is None or source["ts_ist"] < position["opened_at"]:
        raise ReconcileValidationError("accepted link source post is before position opened")
    existing = conn.execute(
        "SELECT 1 FROM position_events WHERE position_id=? AND post_id=?", (position_id_value, post_id)
    ).fetchone()
    if existing is not None:
        return _load_state(conn, position_id_value)
    if position["status"] not in {"open", "added", "partial", "unclear"}:
        raise ReconcileValidationError("accepted link position is not open-like")
    current = _load_state(conn, position_id_value)
    if current.symbol != position["symbol"]:
        raise ReconcileValidationError("position state symbol does not match position row")
    result = _accepted_link_result(current, proposal, post_id)
    posts = _load_thread(conn, position["root_post_id"])
    if post_id not in {post["post_id"] for post in posts}:
        posts.append(source)
        posts.sort(key=lambda post: (post["ts_utc"], post["post_id"]))
    vision_by_post = _load_vision_by_post(conn, [post["post_id"] for post in posts])
    _write_position(
        conn,
        handle=position["handle"], root_post_id=position["root_post_id"], result=result,
        posts=posts, thread_hash_value=thread_hash(posts, vision_by_post),
        model="link", is_mock=int(position["is_mock"]),
        transactional=False,
    )
    return result


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------


def apply_verified_reconciliation(
    conn: sqlite3.Connection,
    root_post_id: str,
    payload: object,
    *,
    source: str = "user",
) -> ReconciledPosition:
    """Persist a hand-audited position state without an LLM call.

    Mirrors classify.apply_verified_classification: some threads are verified
    by a human reading the archived posts directly, and that verified state is
    real evidence, not a placeholder -- same posture as the golden fixtures.
    """
    if not isinstance(source, str) or not source.strip():
        raise ValueError("source must be a non-empty audit label")
    posts = _load_thread(conn, root_post_id)
    result = validate_reconciliation(payload, posts)
    vision_by_post = _load_vision_by_post(conn, [p["post_id"] for p in posts])
    hash_value = thread_hash(posts, vision_by_post)
    is_mock = int(posts[0]["is_mock"]) if posts else 0
    _write_position(
        conn,
        handle=posts[0]["handle"],
        root_post_id=root_post_id,
        result=result,
        posts=posts,
        thread_hash_value=hash_value,
        model=source.strip(),
        is_mock=is_mock,
    )
    return result


def reconcile_thread(
    conn: sqlite3.Connection,
    root_post_id: str,
    *,
    chat_fn: Callable[..., provider.ProviderResult] = provider.chat,
) -> ReconciledPosition:
    """Re-derive the position for `root_post_id`'s thread, from scratch.

    Skips the LLM call entirely when the thread's content (posts + vision
    output) is unchanged since the last reconciliation -- CONTRACTS.md #3's
    "an unchanged thread must cost zero LLM calls".
    """
    posts = _load_thread(conn, root_post_id)
    vision_by_post = _load_vision_by_post(conn, [p["post_id"] for p in posts])
    hash_value = thread_hash(posts, vision_by_post)

    cached = _existing_thread_hash(conn, root_post_id)
    if cached is not None and cached[1] == hash_value:
        return _load_state(conn, cached[0])

    result_raw = chat_fn(
        tier="smart",
        system=_system_prompt(),
        user=_build_user_payload(posts, vision_by_post),
        task="reconcile",
        conn=conn,
        ref_id=root_post_id,
        json_schema=True,
    )
    if not isinstance(result_raw, provider.ProviderResult):
        raise TypeError("chat_fn must return ProviderResult")

    result = validate_reconciliation(result_raw.content, posts)
    is_mock = int(posts[0]["is_mock"]) if posts else 0
    _write_position(
        conn,
        handle=posts[0]["handle"],
        root_post_id=root_post_id,
        result=result,
        posts=posts,
        thread_hash_value=hash_value,
        model=result_raw.model,
        is_mock=is_mock,
    )
    return result
