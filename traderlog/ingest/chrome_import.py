"""Strict archive-first import of authenticated Chrome DOM capture manifests.

The manifest is deliberately small and closed:
``{"schema_version": 1, "posts": [RawPost-shaped records]}``.
Each record's ``raw`` field retains the Chrome DOM evidence needed to audit a
manual capture without trusting browser state, cookies, or page instructions.
"""
from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from traderlog.ingest.archive import DEFAULT_MEDIA_ROOT, DEFAULT_RAW_ROOT, Downloader
from traderlog.ingest.xfetch import RawMedia, RawPost, store_posts


_MANIFEST_KEYS = frozenset({"schema_version", "posts"})
_POST_KEYS = frozenset(
    {
        "post_id",
        "handle",
        "conversation_id",
        "in_reply_to",
        "ts_utc",
        "text",
        "url",
        "media",
        "raw",
    }
)
_MEDIA_KEYS = frozenset({"url", "media_type"})
_CONTEXT_KEYS = frozenset(
    {"surface", "ordered_status_ids", "relationship_basis", "quoted_status_id"}
)
_REQUIRED_CONTEXT_KEYS = _CONTEXT_KEYS - {"quoted_status_id"}
_ID_RE = re.compile(r"^[0-9]{1,30}$")
_HANDLE_RE = re.compile(r"^[A-Za-z0-9_]{1,50}$")
_MEDIA_HOSTS = frozenset({"pbs.twimg.com", "video.twimg.com"})
_MEDIA_TYPES = frozenset({"image", "video", "other"})


class ChromeManifestError(ValueError):
    """A manifest cannot be proven to represent the approved X capture."""


def _require_exact_keys(value: Mapping[str, Any], expected: frozenset[str], label: str) -> None:
    actual = frozenset(value)
    missing = expected - actual
    unknown = actual - expected
    if missing:
        raise ChromeManifestError(f"{label} missing required keys: {sorted(missing)!r}")
    if unknown:
        raise ChromeManifestError(f"{label} has unknown keys: {sorted(unknown)!r}")


def _require_x_id(value: object, label: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ChromeManifestError(f"{label} must be a digits-only X id")
    return value


def _normalize_utc(value: object) -> str:
    if not isinstance(value, str) or not (value.endswith("Z") or value.endswith("+00:00")):
        raise ChromeManifestError("ts_utc must be an ISO-8601 UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ChromeManifestError("ts_utc must be an ISO-8601 UTC timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ChromeManifestError("ts_utc must be an ISO-8601 UTC timestamp")
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds")


def _validate_media_url(value: object) -> str:
    if not isinstance(value, str):
        raise ChromeManifestError("media url must be a string")
    parsed = urlparse(value)
    try:
        port = parsed.port
    except ValueError as exc:
        raise ChromeManifestError("media url has an invalid port") from exc
    if (
        parsed.scheme != "https"
        or (parsed.hostname or "").lower() not in _MEDIA_HOSTS
        or parsed.username is not None
        or parsed.password is not None
        or port not in {None, 443}
        or not parsed.path
        or parsed.fragment
    ):
        raise ChromeManifestError("media url is not an approved X media URL")
    return value


def _approved_handles(conn: sqlite3.Connection) -> dict[str, str]:
    approved: dict[str, str] = {}
    for row in conn.execute(
        "SELECT handle FROM traders WHERE active=1 AND is_mock=0"
    ):
        handle = row[0]
        normalized = handle.lower()
        if normalized in approved:
            raise ChromeManifestError("approved roster has case-insensitive handle collision")
        approved[normalized] = handle
    return approved


def _validate_raw(value: object, *, url: str, post_id: str) -> dict:
    if not isinstance(value, dict):
        raise ChromeManifestError("raw must be a capture dict")
    if value.get("capture_method") != "chrome_dom":
        raise ChromeManifestError("raw.capture_method must be 'chrome_dom'")
    if value.get("source_url") != url:
        raise ChromeManifestError("raw.source_url must exactly equal url")
    context = value.get("captured_context")
    if not isinstance(context, dict):
        raise ChromeManifestError("raw.captured_context must be an object")
    context_keys = frozenset(context)
    missing_context_keys = _REQUIRED_CONTEXT_KEYS - context_keys
    unknown_context_keys = context_keys - _CONTEXT_KEYS
    if missing_context_keys:
        raise ChromeManifestError(
            "raw.captured_context missing required keys: "
            f"{sorted(missing_context_keys)!r}"
        )
    if unknown_context_keys:
        raise ChromeManifestError(
            "raw.captured_context has unknown keys: "
            f"{sorted(unknown_context_keys)!r}"
        )
    surface = context["surface"]
    relationship_basis = context["relationship_basis"]
    ordered_status_ids = context["ordered_status_ids"]
    if not isinstance(surface, str) or not surface.strip():
        raise ChromeManifestError("raw.captured_context.surface must be a non-empty string")
    if not isinstance(relationship_basis, str) or not relationship_basis.strip():
        raise ChromeManifestError(
            "raw.captured_context.relationship_basis must be a non-empty string"
        )
    if not isinstance(ordered_status_ids, list) or not ordered_status_ids:
        raise ChromeManifestError(
            "raw.captured_context.ordered_status_ids must be a non-empty list"
        )
    for context_index, status_id in enumerate(ordered_status_ids):
        _require_x_id(
            status_id,
            f"raw.captured_context.ordered_status_ids[{context_index}]",
        )
    if ordered_status_ids[-1] != post_id:
        raise ChromeManifestError(
            "raw.captured_context.ordered_status_ids must end with post_id"
        )
    if "quoted_status_id" in context:
        _require_x_id(context["quoted_status_id"], "raw.captured_context.quoted_status_id")
    try:
        json.dumps(value, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise ChromeManifestError("raw capture dict must be JSON-serializable") from exc
    return value


def _validate_record(
    value: object,
    *,
    approved_handles: Mapping[str, str],
    index: int,
) -> RawPost:
    if not isinstance(value, dict):
        raise ChromeManifestError(f"posts[{index}] must be an object")
    _require_exact_keys(value, _POST_KEYS, f"posts[{index}]")

    post_id = _require_x_id(value["post_id"], f"posts[{index}].post_id")
    handle = value["handle"]
    if not isinstance(handle, str) or not _HANDLE_RE.fullmatch(handle):
        raise ChromeManifestError(f"posts[{index}].handle is invalid")
    roster_handle = approved_handles.get(handle.lower())
    if roster_handle is None:
        raise ChromeManifestError(f"posts[{index}].handle is not an approved active real handle")

    url = value["url"]
    expected_url = f"https://x.com/{roster_handle}/status/{post_id}"
    if url != expected_url:
        raise ChromeManifestError(
            f"posts[{index}].url must exactly equal approved handle/status identity"
        )
    if not isinstance(value["text"], str):
        raise ChromeManifestError(f"posts[{index}].text must be a string")

    media_value = value["media"]
    if not isinstance(media_value, list):
        raise ChromeManifestError(f"posts[{index}].media must be a list")
    media: list[RawMedia] = []
    for media_index, item in enumerate(media_value):
        if not isinstance(item, dict):
            raise ChromeManifestError(f"posts[{index}].media[{media_index}] must be an object")
        _require_exact_keys(item, _MEDIA_KEYS, f"posts[{index}].media[{media_index}]")
        media_type = item["media_type"]
        if not isinstance(media_type, str) or media_type not in _MEDIA_TYPES:
            raise ChromeManifestError(f"posts[{index}].media[{media_index}].media_type is invalid")
        media.append(RawMedia(_validate_media_url(item["url"]), media_type))

    ts_utc = _normalize_utc(value["ts_utc"])
    conversation_id = _require_x_id(
        value["conversation_id"], f"posts[{index}].conversation_id"
    )
    in_reply_to = _require_x_id(
        value["in_reply_to"], f"posts[{index}].in_reply_to", nullable=True
    )
    raw = _validate_raw(value["raw"], url=url, post_id=post_id)
    ordered_status_ids = raw["captured_context"]["ordered_status_ids"]
    if in_reply_to is None:
        if conversation_id != post_id:
            raise ChromeManifestError(
                f"posts[{index}] root relationship requires conversation_id == post_id"
            )
    else:
        if len(ordered_status_ids) < 2:
            raise ChromeManifestError(
                f"posts[{index}] reply relationship requires at least two ordered_status_ids"
            )
        if conversation_id != ordered_status_ids[0]:
            raise ChromeManifestError(
                f"posts[{index}] reply relationship requires conversation_id to match ancestry"
            )
        if in_reply_to != ordered_status_ids[-2]:
            raise ChromeManifestError(
                f"posts[{index}] reply relationship requires in_reply_to to match ancestry"
            )
    raw = {
        **raw,
        "captured_post": {
            "post_id": post_id,
            "handle": roster_handle,
            "conversation_id": conversation_id,
            "in_reply_to": in_reply_to,
            "ts_utc": ts_utc,
            "text": value["text"],
            "url": url,
            "media": [
                {"url": item.url, "media_type": item.media_type} for item in media
            ],
        },
    }

    return RawPost(
        post_id=post_id,
        handle=roster_handle,
        conversation_id=conversation_id,
        in_reply_to=in_reply_to,
        ts_utc=ts_utc,
        text=value["text"],
        url=url,
        media=media,
        raw=raw,
    )


def validate_manifest(conn: sqlite3.Connection, manifest: object) -> list[RawPost]:
    """Validate every record before archive or database persistence begins."""
    if not isinstance(manifest, dict):
        raise ChromeManifestError("manifest must be an object")
    _require_exact_keys(manifest, _MANIFEST_KEYS, "manifest")
    if manifest["schema_version"] != 1:
        raise ChromeManifestError("manifest.schema_version must be 1")
    records = manifest["posts"]
    if not isinstance(records, list):
        raise ChromeManifestError("manifest.posts must be a list")

    approved_handles = _approved_handles(conn)
    posts = [
        _validate_record(record, approved_handles=approved_handles, index=index)
        for index, record in enumerate(records)
    ]
    post_ids = [post.post_id for post in posts]
    if len(post_ids) != len(set(post_ids)):
        raise ChromeManifestError("manifest contains duplicate post_id values")
    return posts


def import_manifest(
    conn: sqlite3.Connection,
    manifest: object,
    *,
    raw_root: str | Path = DEFAULT_RAW_ROOT,
    media_root: str | Path = DEFAULT_MEDIA_ROOT,
    downloader: Downloader | None = None,
) -> int:
    """Validate a Chrome DOM manifest, then use the existing archive-first store."""
    posts = validate_manifest(conn, manifest)
    return store_posts(
        conn,
        posts,
        raw_root=raw_root,
        media_root=media_root,
        downloader=downloader,
    )
