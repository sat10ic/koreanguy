"""Strict import of the approved, already-captured provisional X corpus.

This module deliberately accepts a narrower source than :mod:`chrome_import`.
The saved capture is a profile/replies DOM export, not a collection of complete
thread manifests, so it preserves a relationship only when a capture contains
the same permalink ancestry proof required by ``chrome_import``.  All other
posts are archived and indexed as relationship-unresolved evidence.

``traders`` rows for newly captured handles are created here atomically: the
apply path inserts an inactive WATCH roster row on the first real capture of a
handle and ``store_posts`` activation flips it to active in the same write.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

from traderlog.db import now_iso
from traderlog.ingest.archive import DEFAULT_MEDIA_ROOT, DEFAULT_RAW_ROOT, Downloader, archive_post
from traderlog.ingest.xfetch import RawMedia, RawPost, store_posts


# Owner direction, amended AND expanded 2026-08-23, then expanded again
# 2026-08-24 (HANDOFF.md): capture/ingest of posts AND replies for all
# seventeen roster handles -- the four active (iManasArora, Fastzonetrader,
# tradinghustlr, VCPSwing), the four pending (StocksNerd, ChartistEdge,
# iArpanK, mystocks_in, incl. first capture + atomic activation), the six
# added 2026-08-23 for roster + first capture (rpmrpm4, thechartist26,
# SakatasHomma, Trading4Bucks, wealthexpress21, Setups_Swing), and the three
# added 2026-08-24 for roster + first capture (investor_sr33, multibaggerwala,
# AdeptMarket; exact casing above is the required roster spelling).
APPROVED_HANDLES = (
    "iManasArora",
    "Fastzonetrader",
    "tradinghustlr",
    "VCPSwing",
    "StocksNerd",
    "ChartistEdge",
    "iArpanK",
    "mystocks_in",
    "rpmrpm4",
    "thechartist26",
    "SakatasHomma",
    "Trading4Bucks",
    "wealthexpress21",
    "Setups_Swing",
    "investor_sr33",
    "multibaggerwala",
    "AdeptMarket",
)
_APPROVED_HANDLE_SET = frozenset(APPROVED_HANDLES)
_MEDIA_HOSTS = frozenset({"pbs.twimg.com", "video.twimg.com"})


class ProvisionalImportError(ValueError):
    """The provisional capture cannot prove the identity it claims."""


@dataclass(frozen=True)
class ProvisionalImportReport:
    selected: int
    eligible: int
    excluded: int
    excluded_pinned: int
    excluded_empty: int
    existing: int
    new: int
    media_items: int
    new_media_items: int
    failed: dict[str, str] = field(default_factory=dict)
    # Handles whose WATCH roster row was created (inactive -> active) by this
    # apply run's first-capture path; empty on dry-run and when nothing is new.
    activated_handles: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _decimal_id(value: object, label: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not value.isdecimal() or len(value) > 30:
        raise ProvisionalImportError(f"{label} must be a decimal X status id")
    return value


def _utc_timestamp(value: object) -> str:
    if not isinstance(value, str) or not (value.endswith("Z") or value.endswith("+00:00")):
        raise ProvisionalImportError("posted_at must be an ISO-8601 UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ProvisionalImportError("posted_at must be an ISO-8601 UTC timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ProvisionalImportError("posted_at must be an ISO-8601 UTC timestamp")
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds")


def _media_url(value: object) -> tuple[str, str]:
    if not isinstance(value, str):
        raise ProvisionalImportError("media_urls items must be strings")
    parsed = urlparse(value)
    try:
        port = parsed.port
    except ValueError as exc:
        raise ProvisionalImportError("media URL has an invalid port") from exc
    if (
        parsed.scheme != "https"
        or (parsed.hostname or "").lower() not in _MEDIA_HOSTS
        or parsed.username is not None
        or parsed.password is not None
        or port not in {None, 443}
        or not parsed.path
        or parsed.fragment
    ):
        raise ProvisionalImportError("media URL is not an approved X media URL")
    return value, "video" if (parsed.hostname or "").lower() == "video.twimg.com" else "image"


def _relationship(record: Mapping[str, Any], post_id: str) -> tuple[str | None, str | None, str]:
    """Return only relationships proven by explicit permalink ancestry evidence."""
    conversation_id = record.get("conversation_id")
    in_reply_to = record.get("in_reply_to")
    ordered_status_ids = record.get("ordered_status_ids")
    basis = record.get("relationship_basis")
    try:
        conversation_id = _decimal_id(conversation_id, "conversation_id")
        in_reply_to = _decimal_id(in_reply_to, "in_reply_to", nullable=True)
    except ProvisionalImportError:
        return None, None, "captured relationship ids are invalid"
    if not isinstance(basis, str) or not basis.strip():
        return None, None, "no non-empty relationship_basis was captured"
    if not isinstance(ordered_status_ids, list) or not ordered_status_ids:
        return None, None, "no ordered_status_ids ancestry was captured"
    try:
        ordered = [
            _decimal_id(value, f"ordered_status_ids[{index}]")
            for index, value in enumerate(ordered_status_ids)
        ]
    except ProvisionalImportError:
        return None, None, "ordered_status_ids contains an invalid id"
    if ordered[-1] != post_id:
        return None, None, "ordered_status_ids does not end with post_id"
    if in_reply_to is None:
        if conversation_id == post_id and ordered == [post_id]:
            return conversation_id, None, "proven root permalink ancestry"
        return None, None, "root relationship is not proven by permalink ancestry"
    if (
        len(ordered) >= 2
        and conversation_id == ordered[0]
        and in_reply_to == ordered[-2]
    ):
        return conversation_id, in_reply_to, "proven reply permalink ancestry"
    return None, None, "reply relationship is not proven by permalink ancestry"


def _record_to_post(record: object, *, handle: str, key: object) -> tuple[RawPost, bool]:
    if not isinstance(record, Mapping):
        raise ProvisionalImportError(f"{handle} capture {key!r} must be an object")
    post_id = _decimal_id(key, f"{handle} capture key")
    if record.get("post_id") != post_id:
        raise ProvisionalImportError(f"{handle} capture key must exactly equal record.post_id")
    if record.get("handle") != handle:
        raise ProvisionalImportError(f"{post_id} record.handle must exactly equal {handle}")
    expected_url = f"https://x.com/{handle}/status/{post_id}"
    if record.get("url") != expected_url:
        raise ProvisionalImportError(f"{post_id} url must exactly equal approved handle/status identity")
    text = record.get("text")
    if not isinstance(text, str):
        raise ProvisionalImportError(f"{post_id} text must be a string")
    ts_utc = _utc_timestamp(record.get("posted_at"))
    media_values = record.get("media_urls")
    if not isinstance(media_values, list):
        raise ProvisionalImportError(f"{post_id} media_urls must be a list")
    media = [RawMedia(*_media_url(value)) for value in media_values]
    if "is_pinned" in record and not isinstance(record["is_pinned"], bool):
        raise ProvisionalImportError(f"{post_id} is_pinned must be a boolean when captured")
    try:
        source_record = json.loads(json.dumps(record, ensure_ascii=False, sort_keys=True))
    except (TypeError, ValueError) as exc:
        raise ProvisionalImportError(f"{post_id} record must be JSON-serializable") from exc

    conversation_id, in_reply_to, relationship_reason = _relationship(record, post_id)
    relationship_status = "proven" if conversation_id is not None else "unresolved"
    raw = {
        "capture_method": "chrome_dom_provisional",
        "source_url": expected_url,
        "provisional_record": source_record,
        "provenance": {
            "source": "2026-08-23_30d_provisional",
            "relationship_status": relationship_status,
            "relationship_reason": relationship_reason,
        },
    }
    post = RawPost(
        post_id=post_id,
        handle=handle,
        conversation_id=conversation_id,
        in_reply_to=in_reply_to,
        ts_utc=ts_utc,
        text=text,
        url=expected_url,
        media=media,
        raw=raw,
    )
    return post, bool(record.get("is_pinned", False))


def load_provisional_posts(source: Mapping[str, Any], handles: list[str] | tuple[str, ...]) -> list[tuple[RawPost, bool]]:
    """Validate and normalize explicit approved-handle selections from a capture."""
    if not isinstance(source, Mapping):
        raise ProvisionalImportError("provisional source root must map handles to records")
    if not handles:
        raise ProvisionalImportError("at least one explicit handle is required")
    if len(handles) != len(set(handles)):
        raise ProvisionalImportError("handles must not contain duplicates")
    unknown = [handle for handle in handles if handle not in _APPROVED_HANDLE_SET]
    if unknown:
        raise ProvisionalImportError(f"unapproved provisional handles: {unknown!r}")

    output: list[tuple[RawPost, bool]] = []
    seen: set[str] = set()
    for handle in handles:
        records = source.get(handle)
        if not isinstance(records, Mapping):
            raise ProvisionalImportError(f"source[{handle!r}] must map post ids to records")
        for key, record in records.items():
            post, pinned = _record_to_post(record, handle=handle, key=key)
            if post.post_id in seen:
                raise ProvisionalImportError(f"duplicate post_id across selected handles: {post.post_id}")
            seen.add(post.post_id)
            output.append((post, pinned))
    return sorted(output, key=lambda item: (item[0].ts_utc, item[0].post_id))


def read_provisional_source(path: str | Path) -> Mapping[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProvisionalImportError(f"cannot read provisional source: {exc}") from exc
    if not isinstance(value, Mapping):
        raise ProvisionalImportError("provisional source root must map handles to records")
    return value


def import_provisional(
    conn: sqlite3.Connection,
    source: Mapping[str, Any],
    *,
    handles: list[str] | tuple[str, ...],
    dry_run: bool = False,
    raw_root: str | Path = DEFAULT_RAW_ROOT,
    media_root: str | Path = DEFAULT_MEDIA_ROOT,
    downloader: Downloader | None = None,
    archiver=archive_post,
) -> ProvisionalImportReport:
    """Archive and index eligible posts, isolating each media/archive failure.

    All identity validation occurs before the first archive or DB mutation.  A
    later per-post archive failure is recorded and does not prevent independent
    posts from being archived and indexed.
    """
    selected = load_provisional_posts(source, handles)
    eligible = [(post, pinned) for post, pinned in selected if not pinned and (post.text.strip() or post.media)]
    excluded_pinned = sum(1 for post, pinned in selected if pinned)
    excluded_empty = sum(1 for post, pinned in selected if not pinned and not (post.text.strip() or post.media))
    eligible_posts = [post for post, _ in eligible]
    existing_ids = {
        row[0]
        for row in conn.execute(
            "SELECT post_id FROM posts WHERE post_id IN ("
            + ",".join("?" for _ in eligible_posts)
            + ")",
            [post.post_id for post in eligible_posts],
        )
    } if eligible_posts else set()
    new_posts = [post for post in eligible_posts if post.post_id not in existing_ids]
    media_items = sum(len(post.media) for post in eligible_posts)
    new_media_items = sum(len(post.media) for post in new_posts)
    report = ProvisionalImportReport(
        selected=len(selected),
        eligible=len(eligible_posts),
        excluded=excluded_pinned + excluded_empty,
        excluded_pinned=excluded_pinned,
        excluded_empty=excluded_empty,
        existing=len(existing_ids),
        new=0,
        media_items=media_items,
        new_media_items=new_media_items,
    )
    if dry_run:
        return ProvisionalImportReport(
            selected=report.selected,
            eligible=report.eligible,
            excluded=report.excluded,
            excluded_pinned=report.excluded_pinned,
            excluded_empty=report.excluded_empty,
            existing=report.existing,
            new=len(new_posts),
            media_items=report.media_items,
            new_media_items=report.new_media_items,
        )

    # First-capture roster creation (apply path only -- dry-run returned above):
    # insert an inactive WATCH row for every handle about to receive its first
    # real post, so store_posts' activation UPDATE (is_mock=0 only) flips that
    # same row to active atomically with the capture. INSERT OR IGNORE never
    # touches an existing row (mock or real) and never inserts mock rows.
    roster_handles = sorted({post.handle for post in new_posts})
    created_handles: list[str] = []
    if roster_handles:
        roster_placeholders = ",".join("?" * len(roster_handles))
        existing_roster = {
            row[0]
            for row in conn.execute(
                f"SELECT handle FROM traders WHERE handle IN ({roster_placeholders})",
                roster_handles,
            )
        }
        created_handles = [
            handle for handle in roster_handles if handle not in existing_roster
        ]
        if created_handles:
            stamp = now_iso()
            with conn:
                conn.executemany(
                    "INSERT OR IGNORE INTO traders "
                    "(handle, tier, tags, active, notes, is_mock, ingested_at) "
                    "VALUES (?,?,?,?,?,0,?)",
                    [
                        (
                            handle,
                            "WATCH",
                            '["india","nse"]',
                            0,
                            "Owner-authorized 2026-08-23; activated on first capture.",
                            stamp,
                        )
                        for handle in created_handles
                    ],
                )

    failures: dict[str, str] = {}
    written = 0
    for post in new_posts:
        try:
            written += store_posts(
                conn,
                [post],
                raw_root=raw_root,
                media_root=media_root,
                downloader=downloader,
                archiver=archiver,
                activate_handles=(post.handle,),
            )
        except Exception as exc:  # one media/archive failure must not block the corpus
            failures[post.post_id] = f"{type(exc).__name__}: {exc}"
    return ProvisionalImportReport(
        selected=report.selected,
        eligible=report.eligible,
        excluded=report.excluded,
        excluded_pinned=report.excluded_pinned,
        excluded_empty=report.excluded_empty,
        existing=report.existing,
        new=written,
        media_items=report.media_items,
        new_media_items=report.new_media_items,
        failed=failures,
        activated_handles=tuple(sorted(created_handles)),
    )
