"""Immutable first-sight archives for X posts and their media."""
from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import re
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Callable
from urllib.parse import urlparse

if TYPE_CHECKING:
    from traderlog.ingest.xfetch import RawPost


_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW_ROOT = _ROOT / "data" / "raw"
DEFAULT_MEDIA_ROOT = _ROOT / "data" / "media"
_HANDLE_RE = re.compile(r"^[A-Za-z0-9_]{1,50}$")
_POST_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,100}$")
_MEDIA_HOSTS = {"pbs.twimg.com", "video.twimg.com"}


@dataclass(frozen=True)
class ArchivedMedia:
    idx: int
    local_path: str
    sha256: str
    media_type: str


@dataclass(frozen=True)
class ArchivedPost:
    raw_path: str
    media: tuple[ArchivedMedia, ...]


Downloader = Callable[[str], tuple[bytes, str]]


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _stored_path(path: Path, root: Path = _ROOT) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _validate_key(value: str, pattern: re.Pattern[str], name: str) -> None:
    if not pattern.fullmatch(value):
        raise ValueError(f"invalid {name}: {value!r}")


def _atomic_write_once(path: Path, payload: bytes) -> None:
    """Create ``path`` atomically and leave an existing first-sight file alone."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return

    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temp.open("xb") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        try:
            os.link(temp, path)
        except FileExistsError:
            pass
    finally:
        temp.unlink(missing_ok=True)


def _download(url: str) -> tuple[bytes, str]:
    parsed = urlparse(url)
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError(f"media URL has invalid port: {url!r}") from exc
    if (
        parsed.scheme.lower() != "https"
        or (parsed.hostname or "").lower() not in _MEDIA_HOSTS
        or parsed.username is not None
        or parsed.password is not None
        or port not in {None, 443}
    ):
        raise ValueError(f"media URL is not an allowed X media URL: {url!r}")
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "TraderLog/0.1 read-only archive"},
    )
    opener = urllib.request.build_opener(_NoRedirect())
    with opener.open(request, timeout=30) as response:
        return response.read(), response.headers.get_content_type()


def _extension(url: str, content_type: str, media_type: str) -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix and len(suffix) <= 6:
        return suffix
    guessed = mimetypes.guess_extension(content_type.split(";", 1)[0].strip())
    if guessed == ".jpe":
        return ".jpg"
    if guessed:
        return guessed
    return ".mp4" if media_type == "video" else ".bin"


def _existing_media(media_root: Path, post_id: str, idx: int) -> Path | None:
    matches = sorted(media_root.glob(f"{post_id}_{idx}.*"))
    return matches[0] if matches else None


def archive_post(
    post: RawPost,
    *,
    raw_root: str | Path = DEFAULT_RAW_ROOT,
    media_root: str | Path = DEFAULT_MEDIA_ROOT,
    downloader: Downloader = _download,
) -> ArchivedPost:
    """Archive raw JSON and all media without overwriting first-sight bytes."""
    _validate_key(post.handle, _HANDLE_RE, "handle")
    _validate_key(post.post_id, _POST_ID_RE, "post_id")
    raw_root = Path(raw_root)
    media_root = Path(media_root)

    raw_path = raw_root / post.handle / f"{post.post_id}.json"
    raw_bytes = (
        json.dumps(post.raw, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
        + b"\n"
    )
    _atomic_write_once(raw_path, raw_bytes)

    archived_media: list[ArchivedMedia] = []
    for idx, media in enumerate(post.media):
        existing = _existing_media(media_root, post.post_id, idx)
        if existing is None:
            payload, content_type = downloader(media.url)
            extension = _extension(media.url, content_type, media.media_type)
            existing = media_root / f"{post.post_id}_{idx}{extension}"
            _atomic_write_once(existing, payload)
        digest = hashlib.sha256(existing.read_bytes()).hexdigest()
        archived_media.append(
            ArchivedMedia(
                idx=idx,
                local_path=_stored_path(existing, media_root),
                sha256=digest,
                media_type=media.media_type,
            )
        )

    return ArchivedPost(
        raw_path=_stored_path(raw_path),
        media=tuple(archived_media),
    )
