"""Read-only X timeline capture through a persistent Playwright profile."""
from __future__ import annotations

import json
import random
import sqlite3
import sys
import time
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from traderlog import config
from traderlog.db import init_db, now_iso
from traderlog.ingest.archive import (
    DEFAULT_MEDIA_ROOT,
    DEFAULT_RAW_ROOT,
    Downloader,
    archive_post,
)
from traderlog.ingest.deletions import mark_missing_posts


_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = _ROOT.parent
_IST = ZoneInfo("Asia/Kolkata")
_AUDIT_LOOKBACK = timedelta(days=7)


@dataclass(frozen=True)
class RawMedia:
    url: str
    media_type: str


@dataclass(frozen=True)
class RawPost:
    post_id: str
    handle: str
    conversation_id: str | None
    in_reply_to: str | None
    ts_utc: str
    text: str
    url: str
    media: list[RawMedia]
    raw: dict


def _walk(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _unwrap_tweet(candidate: dict) -> dict | None:
    current = candidate
    seen: set[int] = set()
    while isinstance(current, dict) and id(current) not in seen:
        seen.add(id(current))
        legacy = current.get("legacy")
        if isinstance(legacy, dict) and (
            legacy.get("id_str") or current.get("rest_id")
        ):
            return current
        nested = current.get("tweet")
        if isinstance(nested, dict):
            current = nested
            continue
        result = current.get("result")
        if isinstance(result, dict):
            current = result
            continue
        break
    return None


def _screen_name(tweet: dict) -> str | None:
    core = tweet.get("core") or {}
    user_results = core.get("user_results") or {}
    user = _unwrap_tweet(user_results) or user_results.get("result") or {}
    legacy = user.get("legacy") if isinstance(user, dict) else None
    return legacy.get("screen_name") if isinstance(legacy, dict) else None


def _media_from_legacy(legacy: dict) -> list[RawMedia]:
    entities = legacy.get("extended_entities") or legacy.get("entities") or {}
    items = entities.get("media") if isinstance(entities, dict) else []
    output: list[RawMedia] = []
    for item in items or []:
        kind = item.get("type")
        if kind == "video" or kind == "animated_gif":
            variants = (item.get("video_info") or {}).get("variants") or []
            mp4 = [v for v in variants if v.get("content_type") == "video/mp4"]
            chosen = max(mp4, key=lambda v: v.get("bitrate", 0), default={})
            url = chosen.get("url")
            media_type = "video"
        else:
            url = item.get("media_url_https") or item.get("media_url")
            media_type = "image" if kind == "photo" else "other"
        if url and RawMedia(url, media_type) not in output:
            output.append(RawMedia(url, media_type))
    return output


def _tweet_text(tweet: dict, legacy: dict) -> str:
    note = tweet.get("note_tweet") or {}
    result = (note.get("note_tweet_results") or {}).get("result") or {}
    return result.get("text") or legacy.get("full_text") or legacy.get("text") or ""


def _as_utc_iso(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        parsed = parsedate_to_datetime(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds")


def _iso_as_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_timeline_payload(
    payload: dict,
    handle: str,
    since: str | None,
) -> list[RawPost]:
    """Normalize tweet results from X's browser GraphQL response."""
    normalized_handle = handle.lstrip("@").lower()
    since_dt = _iso_as_utc(since) if since else None

    by_id: dict[str, RawPost] = {}
    for candidate in _walk(payload):
        tweet = _unwrap_tweet(candidate)
        if tweet is None:
            continue
        legacy = tweet.get("legacy") or {}
        post_id = str(legacy.get("id_str") or tweet.get("rest_id") or "")
        author = (_screen_name(tweet) or "").lower()
        created_at = legacy.get("created_at")
        if not post_id or author != normalized_handle or not created_at:
            continue
        ts_utc = _as_utc_iso(created_at)
        ts_dt = datetime.fromisoformat(ts_utc)
        if since_dt and ts_dt < since_dt:
            continue
        by_id.setdefault(
            post_id,
            RawPost(
                post_id=post_id,
                handle=normalized_handle,
                conversation_id=legacy.get("conversation_id_str"),
                in_reply_to=legacy.get("in_reply_to_status_id_str"),
                ts_utc=ts_utc,
                text=_tweet_text(tweet, legacy),
                url=f"https://x.com/{normalized_handle}/status/{post_id}",
                media=_media_from_legacy(legacy),
                raw=tweet,
            ),
        )
    return sorted(by_id.values(), key=lambda post: (post.ts_utc, post.post_id))


def _path_from_config(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (_REPO_ROOT / path).resolve()


def _launch_persistent_context(playwright):
    profile = _path_from_config(
        str(config.get("ingest.browser_profile_dir", "traderlog/data/browser_profile"))
    )
    profile.mkdir(parents=True, exist_ok=True)
    return playwright.chromium.launch_persistent_context(
        user_data_dir=str(profile),
        headless=bool(config.get("ingest.headless", False)),
    )


def open_login_profile(*, input_fn=input) -> None:
    """Open the dedicated X profile for a user-driven login; perform no ingest."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - environment-specific
        raise RuntimeError(
            "Playwright is required: install traderlog[ingest] and Chromium"
        ) from exc

    with sync_playwright() as playwright:
        context = _launch_persistent_context(playwright)
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(
                "https://x.com/home",
                wait_until="domcontentloaded",
                timeout=60_000,
            )
            input_fn(
                "Log in to the secondary X account in the browser, then press Enter "
                "here to save and close the profile: "
            )
        finally:
            context.close()


def fetch_timeline(handle: str, since: str | None) -> list[RawPost]:
    """Fetch one user's timeline-with-replies through their logged-in profile."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - environment-specific
        raise RuntimeError(
            "Playwright is required: install traderlog[ingest] and Chromium"
        ) from exc

    normalized_handle = handle.lstrip("@").lower()
    payloads: list[dict] = []
    response_errors: list[str] = []
    saw_target_post = False

    def capture(response) -> None:
        nonlocal saw_target_post
        if "/graphql/" not in response.url or "UserTweetsAndReplies" not in response.url:
            return
        try:
            status = int(getattr(response, "status", 200))
            if status >= 400:
                response_errors.append(f"HTTP {status}")
            payload = response.json()
            if isinstance(payload, dict):
                payloads.append(payload)
                errors = payload.get("errors")
                if isinstance(errors, list) and errors:
                    response_errors.append(f"GraphQL error ({len(errors)})")
                captured = parse_timeline_payload(payload, normalized_handle, None)
                if captured:
                    saw_target_post = True
        except Exception as exc:  # a non-JSON GraphQL error is still diagnostic
            response_errors.append(type(exc).__name__)

    with sync_playwright() as playwright:
        context = _launch_persistent_context(playwright)
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.on("response", capture)
            page.goto(
                f"https://x.com/{normalized_handle}/with_replies",
                wait_until="domcontentloaded",
                timeout=60_000,
            )
            stagnant = 0
            previous_count = -1
            for _ in range(50):
                posts = _merge_payloads(payloads, normalized_handle, since)
                count = len(posts)
                stagnant = stagnant + 1 if count == previous_count else 0
                previous_count = count
                if stagnant >= 3:
                    break
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(random.randint(800, 1600))
        finally:
            context.close()

    if not payloads:
        detail = f" ({','.join(response_errors)})" if response_errors else ""
        raise RuntimeError(f"X timeline returned no readable GraphQL payloads{detail}")
    if response_errors:
        raise RuntimeError(f"X timeline response failed: {','.join(response_errors)}")
    if not saw_target_post:
        raise RuntimeError("X timeline payload contained no posts for requested author")
    return _merge_payloads(payloads, normalized_handle, since)


def _merge_payloads(
    payloads: list[dict], handle: str, since: str | None
) -> list[RawPost]:
    by_id: dict[str, RawPost] = {}
    for payload in payloads:
        for post in parse_timeline_payload(payload, handle, since):
            by_id.setdefault(post.post_id, post)
    return sorted(by_id.values(), key=lambda post: (post.ts_utc, post.post_id))


def poll_interval_seconds(*, uniform=random.uniform) -> int:
    """Configured human polling cadence with symmetric bounded jitter."""
    minutes = max(1.0, float(config.get("ingest.poll_interval_minutes", 15)))
    jitter = min(0.9, max(0.0, float(config.get("ingest.jitter_pct", 0.35))))
    multiplier = uniform(1.0 - jitter, 1.0 + jitter)
    return max(60, round(minutes * 60 * multiplier))


def store_posts(
    conn: sqlite3.Connection,
    posts: list[RawPost],
    *,
    raw_root: str | Path = DEFAULT_RAW_ROOT,
    media_root: str | Path = DEFAULT_MEDIA_ROOT,
    downloader: Downloader | None = None,
    archiver=archive_post,
) -> int:
    """Archive all new posts first, then atomically insert their index rows."""
    unique = {post.post_id: post for post in posts}
    new_posts = [
        post
        for post in unique.values()
        if conn.execute(
            "SELECT 1 FROM posts WHERE post_id=?", (post.post_id,)
        ).fetchone()
        is None
    ]
    archived = []
    for post in new_posts:
        kwargs = {"raw_root": raw_root, "media_root": media_root}
        if downloader is not None:
            kwargs["downloader"] = downloader
        archived.append((post, archiver(post, **kwargs)))

    stamp = now_iso()
    with conn:
        for post, artifact in archived:
            ts_ist = datetime.fromisoformat(post.ts_utc).astimezone(_IST).isoformat(
                timespec="seconds"
            )
            legacy = post.raw.get("legacy") if isinstance(post.raw, dict) else {}
            lang = legacy.get("lang") if isinstance(legacy, dict) else None
            conn.execute(
                "INSERT INTO posts "
                "(post_id,handle,conversation_id,in_reply_to,ts_utc,ts_ist,text,url,"
                "lang,raw_path,fetched_at,is_mock,ingested_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,0,?)",
                (
                    post.post_id,
                    post.handle,
                    post.conversation_id,
                    post.in_reply_to,
                    post.ts_utc,
                    ts_ist,
                    post.text,
                    post.url,
                    lang,
                    artifact.raw_path,
                    stamp,
                    stamp,
                ),
            )
            conn.executemany(
                "INSERT INTO post_media "
                "(post_id,idx,local_path,sha256,media_type,is_mock,ingested_at) "
                "VALUES (?,?,?,?,?,0,?)",
                [
                    (
                        post.post_id,
                        media.idx,
                        media.local_path,
                        media.sha256,
                        media.media_type,
                        stamp,
                    )
                    for media in artifact.media
                ],
            )
        latest_by_handle: dict[str, str] = {}
        for post in unique.values():
            latest_by_handle[post.handle] = max(
                post.ts_utc,
                latest_by_handle.get(post.handle, post.ts_utc),
            )
        for handle, latest in latest_by_handle.items():
            conn.execute(
                "UPDATE traders SET last_seen_ts = CASE "
                "WHEN last_seen_ts IS NULL OR last_seen_ts < ? THEN ? "
                "ELSE last_seen_ts END WHERE handle=?",
                (latest, latest, handle),
            )
    return len(archived)


def _since_for_handle(
    conn: sqlite3.Connection,
    handle: str,
    *,
    now: datetime | None = None,
) -> str:
    row = conn.execute(
        "SELECT MAX(p.ts_utc), t.last_seen_ts FROM traders t "
        "LEFT JOIN posts p ON p.handle=t.handle AND p.is_mock=0 "
        "WHERE t.handle=? GROUP BY t.handle",
        (handle,),
    ).fetchone()
    latest = (row[0] or row[1]) if row else None
    if not latest:
        days = max(1, int(config.get("ingest.initial_backfill_days", 30)))
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        return (current.astimezone(timezone.utc) - timedelta(days=days)).isoformat(
            timespec="seconds"
        )
    value = _iso_as_utc(str(latest))
    return (value - _AUDIT_LOOKBACK).isoformat(
        timespec="seconds"
    )


def _log_run(
    conn: sqlite3.Connection,
    *,
    run_date: str,
    status: str,
    rows: int,
    duration_ms: int,
    detail: str,
) -> None:
    with conn:
        conn.execute(
            "INSERT INTO pipeline_runs "
            "(stage,run_date,status,rows,duration_ms,detail,ts) VALUES (?,?,?,?,?,?,?)",
            ("ingest.xfetch", run_date, status, rows, duration_ms, detail, now_iso()),
        )


def run(
    conn: sqlite3.Connection | None = None,
    run_date: str | None = None,
    *,
    fetcher=fetch_timeline,
    raw_root: str | Path = DEFAULT_RAW_ROOT,
    media_root: str | Path = DEFAULT_MEDIA_ROOT,
    downloader: Downloader | None = None,
) -> int:
    """Fetch every real active trader; log failures and never raise outward."""
    owned_connection = False
    if conn is None:
        try:
            conn = init_db()
            owned_connection = True
        except Exception:
            return 0
    run_date = run_date or date.today().isoformat()
    started = time.perf_counter()
    inserted = 0
    errors: list[str] = []
    try:
        traders = conn.execute(
            "SELECT handle FROM traders WHERE active=1 AND is_mock=0 ORDER BY handle"
        ).fetchall()
        for trader in traders:
            handle = trader["handle"]
            since = _since_for_handle(conn, handle)
            try:
                posts = fetcher(handle, since)
                if any(post.handle.casefold() != handle.casefold() for post in posts):
                    raise ValueError(f"fetcher returned a different author for {handle}")
                posts = [
                    post if post.handle == handle else replace(post, handle=handle)
                    for post in posts
                ]
                inserted += store_posts(
                    conn,
                    posts,
                    raw_root=raw_root,
                    media_root=media_root,
                    downloader=downloader,
                )
                mark_missing_posts(
                    conn,
                    handle,
                    seen_post_ids={post.post_id for post in posts},
                    observed_since=min((post.ts_utc for post in posts), default=None),
                    observed_until=max((post.ts_utc for post in posts), default=None),
                )
            except Exception as exc:
                errors.append(f"{handle}: {type(exc).__name__}: {exc}")
        elapsed = int((time.perf_counter() - started) * 1000)
        status = "fail" if errors else "ok"
        detail = json.dumps({"errors": errors}, ensure_ascii=True)
        _log_run(
            conn,
            run_date=run_date,
            status=status,
            rows=inserted,
            duration_ms=elapsed,
            detail=detail,
        )
        return 0 if errors else inserted
    except Exception as exc:
        elapsed = int((time.perf_counter() - started) * 1000)
        try:
            _log_run(
                conn,
                run_date=run_date,
                status="fail",
                rows=inserted,
                duration_ms=elapsed,
                detail=f"{type(exc).__name__}: {exc}",
            )
        except Exception:
            pass
        return 0
    finally:
        if owned_connection:
            conn.close()


def poll_forever(*, stop_event=None) -> None:
    """Run at the configured human cadence until interrupted or stopped."""
    while True:
        run()
        delay = poll_interval_seconds()
        if stop_event is not None:
            if stop_event.wait(delay):
                return
        else:
            time.sleep(delay)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--help" in argv or "-h" in argv:
        print(
            "Usage: python traderlog/run_xfetch.py "
            "[--login | --forever]\n"
            "  --login    open the dedicated profile for manual X login only\n"
            "  --forever  ingest approved active traders at the configured cadence"
        )
        return 0
    if "--login" in argv:
        open_login_profile()
        return 0
    if "--forever" in argv:
        poll_forever()
        return 0
    run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
