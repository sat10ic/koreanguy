from __future__ import annotations

import json
import subprocess
import sys
from types import SimpleNamespace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from traderlog.checks.runner import check_ingest
from traderlog.db import init_db, now_iso
from traderlog.ingest import archive as archive_module
from traderlog.ingest.archive import archive_post
from traderlog.ingest.deletions import mark_missing_posts
from traderlog.ingest import xfetch
from traderlog.ingest.xfetch import (
    RawMedia,
    RawPost,
    fetch_timeline,
    parse_timeline_payload,
    poll_interval_seconds,
    run,
    store_posts,
)


def _tweet_result(
    post_id: str,
    *,
    handle: str = "chartist",
    text: str = "added here",
    conversation_id: str | None = None,
    in_reply_to: str | None = None,
    created_at: str = "Sat Aug 22 08:30:00 +0000 2026",
    media: list[dict] | None = None,
) -> dict:
    legacy = {
        "id_str": post_id,
        "full_text": text,
        "conversation_id_str": conversation_id or post_id,
        "in_reply_to_status_id_str": in_reply_to,
        "created_at": created_at,
        "extended_entities": {"media": media or []},
    }
    return {
        "rest_id": post_id,
        "legacy": legacy,
        "core": {
            "user_results": {
                "result": {"legacy": {"screen_name": handle}}
            }
        },
    }


def _raw_post(*, media: list[RawMedia] | None = None) -> RawPost:
    return RawPost(
        post_id="12345",
        handle="chartist",
        conversation_id="12000",
        in_reply_to="12000",
        ts_utc="2026-08-22T08:30:00+00:00",
        text="added here",
        url="https://x.com/chartist/status/12345",
        media=media or [],
        raw={"source": "fixture", "id": "12345"},
    )


def test_parse_timeline_payload_keeps_self_replies_and_exact_relationships():
    photo = {
        "type": "photo",
        "media_url_https": "https://pbs.twimg.com/media/chart.jpg",
    }
    payload = {
        "data": {
            "timeline": [
                _tweet_result("12000", text="starter"),
                _tweet_result(
                    "12345",
                    text="added here",
                    conversation_id="12000",
                    in_reply_to="12000",
                    media=[photo],
                ),
                _tweet_result("99999", handle="someone_else"),
            ]
        }
    }

    posts = parse_timeline_payload(payload, "@Chartist", since=None)

    assert [post.post_id for post in posts] == ["12000", "12345"]
    reply = posts[1]
    assert reply.handle == "chartist"
    assert reply.conversation_id == "12000"
    assert reply.in_reply_to == "12000"
    assert reply.media == [
        RawMedia("https://pbs.twimg.com/media/chart.jpg", "image")
    ]
    assert reply.ts_utc == "2026-08-22T08:30:00+00:00"


def test_parse_timeline_payload_deduplicates_and_applies_since_in_utc():
    recent = _tweet_result("12345")
    old = _tweet_result(
        "11111", created_at="Thu Aug 20 08:30:00 +0000 2026"
    )
    payload = {"items": [recent, recent, old]}

    posts = parse_timeline_payload(
        payload, "chartist", since="2026-08-21T00:00:00+00:00"
    )

    assert [post.post_id for post in posts] == ["12345"]


def test_parse_timeline_payload_prefers_complete_note_tweet_text():
    tweet = _tweet_result("12345", text="This post is truncated…")
    tweet["note_tweet"] = {
        "note_tweet_results": {
            "result": {"text": "This is the complete long-form post text."}
        }
    }

    posts = parse_timeline_payload({"result": tweet}, "chartist", since=None)

    assert posts[0].text == "This is the complete long-form post text."


def test_archive_post_writes_raw_and_media_once_with_sha256(tmp_path: Path):
    downloads = []

    def downloader(url: str) -> tuple[bytes, str]:
        downloads.append(url)
        return b"immutable-image-bytes", "image/jpeg"

    post = _raw_post(
        media=[RawMedia("https://pbs.twimg.com/media/chart", "image")]
    )
    raw_root = tmp_path / "raw"
    media_root = tmp_path / "media"

    first = archive_post(
        post,
        raw_root=raw_root,
        media_root=media_root,
        downloader=downloader,
    )
    raw_path = tmp_path / first.raw_path
    media_path = media_root / first.media[0].local_path

    assert json.loads(raw_path.read_text(encoding="utf-8")) == post.raw
    assert media_path.read_bytes() == b"immutable-image-bytes"
    assert first.media[0].sha256 == (
        "941e94c100343d71b0d41608c8bf1c469eddfc8e1097768348f9a5d7d7a054f3"
    )

    raw_path.write_text('{"source":"first-sight"}\n', encoding="utf-8")
    second = archive_post(
        post,
        raw_root=raw_root,
        media_root=media_root,
        downloader=lambda _url: pytest.fail("existing media must not be fetched"),
    )

    assert raw_path.read_text(encoding="utf-8") == '{"source":"first-sight"}\n'
    assert second.media[0].sha256 == first.media[0].sha256
    assert downloads == ["https://pbs.twimg.com/media/chart"]


def test_archive_paths_are_sanitized_from_untrusted_handle(tmp_path: Path):
    post = _raw_post()
    post = RawPost(**{**post.__dict__, "handle": "../escape"})

    with pytest.raises(ValueError, match="handle"):
        archive_post(
            post,
            raw_root=tmp_path / "raw",
            media_root=tmp_path / "media",
        )


def test_default_media_downloader_rejects_local_file_urls(tmp_path: Path):
    secret = tmp_path / "secret.txt"
    secret.write_text("must not be archived", encoding="utf-8")
    post = _raw_post(media=[RawMedia(secret.as_uri(), "image")])

    with pytest.raises(ValueError, match="media URL"):
        archive_post(
            post,
            raw_root=tmp_path / "raw",
            media_root=tmp_path / "media",
        )

    assert not list((tmp_path / "media").glob("*"))


def test_default_media_downloader_rejects_untrusted_https_hosts(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        archive_module.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: pytest.fail("untrusted URL must not be opened"),
    )

    with pytest.raises(ValueError, match="media URL"):
        archive_module._download("https://example.invalid/chart.png")


def test_default_media_downloader_allows_x_media_host_without_redirects(
    monkeypatch: pytest.MonkeyPatch,
):
    opened = []
    handlers = []

    class Headers:
        @staticmethod
        def get_content_type():
            return "image/jpeg"

    class Response:
        headers = Headers()

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        @staticmethod
        def read():
            return b"chart-bytes"

    class Opener:
        @staticmethod
        def open(request, timeout):
            opened.append((request.full_url, timeout))
            return Response()

    monkeypatch.setattr(
        archive_module.urllib.request,
        "build_opener",
        lambda *items: handlers.extend(items) or Opener(),
    )

    payload, content_type = archive_module._download(
        "https://pbs.twimg.com/media/chart.jpg?format=jpg"
    )

    assert payload == b"chart-bytes"
    assert content_type == "image/jpeg"
    assert opened == [("https://pbs.twimg.com/media/chart.jpg?format=jpg", 30)]
    assert len(handlers) == 1
    assert isinstance(handlers[0], archive_module._NoRedirect)


def _insert_trader(conn, handle: str, *, active: int = 1) -> None:
    conn.execute(
        "INSERT INTO traders "
        "(handle, display_name, active, is_mock, ingested_at) VALUES (?,?,?,0,?)",
        (handle, handle, active, now_iso()),
    )
    conn.commit()


def test_store_posts_archives_everything_before_any_database_insert(tmp_path: Path):
    conn = init_db(tmp_path / "traderlog.db")
    _insert_trader(conn, "chartist")
    first = _raw_post()
    second = RawPost(**{**first.__dict__, "post_id": "12346"})
    archived = []

    def failing_archiver(post, **_kwargs):
        archived.append(post.post_id)
        if post.post_id == "12346":
            raise OSError("media download failed")
        return type("Archive", (), {"raw_path": "raw/12345.json", "media": ()})()

    with pytest.raises(OSError, match="media download failed"):
        store_posts(conn, [first, second], archiver=failing_archiver)

    assert archived == ["12345", "12346"]
    assert conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0] == 0
    conn.close()


def test_store_posts_is_idempotent_and_persists_ist_and_media(tmp_path: Path):
    conn = init_db(tmp_path / "traderlog.db")
    _insert_trader(conn, "chartist")
    post = _raw_post(
        media=[RawMedia("https://pbs.twimg.com/media/chart", "image")]
    )

    assert store_posts(
        conn,
        [post],
        raw_root=tmp_path / "raw",
        media_root=tmp_path / "media",
        downloader=lambda _url: (b"image", "image/png"),
    ) == 1
    assert store_posts(
        conn,
        [post],
        raw_root=tmp_path / "raw",
        media_root=tmp_path / "media",
        downloader=lambda _url: pytest.fail("duplicate must not re-download"),
    ) == 0

    row = conn.execute("SELECT * FROM posts WHERE post_id='12345'").fetchone()
    assert row["conversation_id"] == "12000"
    assert row["in_reply_to"] == "12000"
    assert row["ts_ist"] == "2026-08-22T14:00:00+05:30"
    assert Path(row["raw_path"]).is_file()
    media = conn.execute(
        "SELECT * FROM post_media WHERE post_id='12345'"
    ).fetchone()
    assert not Path(media["local_path"]).is_absolute()
    assert (tmp_path / "media" / media["local_path"]).is_file()
    assert len(media["sha256"]) == 64
    conn.close()


def test_store_posts_advances_trader_watermark_without_regressing_on_old_replay(
    tmp_path: Path,
):
    conn = init_db(tmp_path / "traderlog.db")
    _insert_trader(conn, "chartist")
    newer = RawPost(
        **{
            **_raw_post().__dict__,
            "post_id": "newer",
            "ts_utc": "2026-08-22T08:30:00+00:00",
        }
    )
    older = RawPost(
        **{
            **_raw_post().__dict__,
            "post_id": "older",
            "ts_utc": "2026-08-20T08:30:00+00:00",
        }
    )

    store_posts(
        conn, [newer], raw_root=tmp_path / "raw", media_root=tmp_path / "media"
    )
    assert conn.execute(
        "SELECT last_seen_ts FROM traders WHERE handle='chartist'"
    ).fetchone()[0] == "2026-08-22T08:30:00+00:00"

    store_posts(
        conn, [older], raw_root=tmp_path / "raw", media_root=tmp_path / "media"
    )
    assert conn.execute(
        "SELECT last_seen_ts FROM traders WHERE handle='chartist'"
    ).fetchone()[0] == "2026-08-22T08:30:00+00:00"
    conn.close()


def test_mark_missing_posts_keeps_rows_and_archive_and_logs_run(tmp_path: Path):
    conn = init_db(tmp_path / "traderlog.db")
    _insert_trader(conn, "chartist")
    archive = tmp_path / "raw" / "chartist" / "12345.json"
    archive.parent.mkdir(parents=True)
    archive.write_text("{}\n", encoding="utf-8")
    for post_id, ts in (
        ("12345", "2026-08-22T08:30:00+00:00"),
        ("12346", "2026-08-22T09:30:00+00:00"),
        ("old", "2026-08-01T09:30:00+00:00"),
    ):
        conn.execute(
            "INSERT INTO posts "
            "(post_id,handle,ts_utc,ts_ist,raw_path,fetched_at,is_mock,ingested_at) "
            "VALUES (?,?,?,?,?,?,0,?)",
            (post_id, "chartist", ts, ts, str(archive), now_iso(), now_iso()),
        )
    conn.commit()

    changed = mark_missing_posts(
        conn,
        "chartist",
        seen_post_ids={"12346"},
        observed_since="2026-08-20T00:00:00+00:00",
        observed_until="2026-08-23T00:00:00+00:00",
        deleted_at="2026-08-23T01:00:00+00:00",
    )

    assert changed == 1
    rows = conn.execute(
        "SELECT post_id, deleted_at FROM posts ORDER BY post_id"
    ).fetchall()
    assert [(r["post_id"], r["deleted_at"]) for r in rows] == [
        ("12345", "2026-08-23T01:00:00+00:00"),
        ("12346", None),
        ("old", None),
    ]
    assert archive.is_file()
    logged = conn.execute(
        "SELECT status, rows FROM pipeline_runs WHERE stage='ingest.deletions'"
    ).fetchone()
    assert tuple(logged) == ("ok", 1)
    conn.close()


def test_run_continues_after_one_trader_fails_but_returns_zero(tmp_path: Path):
    conn = init_db(tmp_path / "traderlog.db")
    _insert_trader(conn, "broken")
    _insert_trader(conn, "chartist")

    def fetcher(handle: str, _since: str | None) -> list[RawPost]:
        if handle == "broken":
            raise RuntimeError("fixture failure")
        return [_raw_post()]

    result = run(
        conn,
        run_date="2026-08-23",
        fetcher=fetcher,
        raw_root=tmp_path / "raw",
        media_root=tmp_path / "media",
    )

    assert result == 0
    assert conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0] == 1
    logged = conn.execute(
        "SELECT status, detail FROM pipeline_runs WHERE stage='ingest.xfetch' "
        "ORDER BY id DESC LIMIT 1"
    ).fetchone()
    assert logged["status"] == "fail"
    assert "broken" in logged["detail"]
    conn.close()


def test_check_ingest_fails_when_a_real_posts_archive_is_missing(tmp_path: Path):
    conn = init_db(tmp_path / "traderlog.db")
    _insert_trader(conn, "chartist")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn.execute(
        "INSERT INTO posts "
        "(post_id,handle,ts_utc,ts_ist,raw_path,fetched_at,is_mock,ingested_at) "
        "VALUES ('12345','chartist',?,?,?,?,0,?)",
        (now, now, str(tmp_path / "missing.json"), now, now),
    )
    conn.commit()

    result = check_ingest(conn)

    assert result.status.startswith("fail")
    assert "archive" in result.status
    conn.close()


def test_check_ingest_fails_when_indexed_media_file_is_missing(tmp_path: Path):
    conn = init_db(tmp_path / "traderlog.db")
    _insert_trader(conn, "chartist")
    post = _raw_post(
        media=[RawMedia("https://example.invalid/chart.png", "image")]
    )
    store_posts(
        conn,
        [post],
        raw_root=tmp_path / "raw",
        media_root=tmp_path / "media",
        downloader=lambda _url: (b"original-chart", "image/png"),
    )
    media_path = tmp_path / "media" / conn.execute(
        "SELECT local_path FROM post_media"
    ).fetchone()[0]
    media_path.unlink()

    result = check_ingest(conn, media_root=tmp_path / "media")

    assert result.status.startswith("fail")
    assert "media" in result.status
    assert "missing" in result.status
    conn.close()


def test_check_ingest_fails_when_archived_media_hash_has_changed(tmp_path: Path):
    conn = init_db(tmp_path / "traderlog.db")
    _insert_trader(conn, "chartist")
    post = _raw_post(
        media=[RawMedia("https://example.invalid/chart.png", "image")]
    )
    store_posts(
        conn,
        [post],
        raw_root=tmp_path / "raw",
        media_root=tmp_path / "media",
        downloader=lambda _url: (b"original-chart", "image/png"),
    )
    media_path = tmp_path / "media" / conn.execute(
        "SELECT local_path FROM post_media"
    ).fetchone()[0]
    media_path.write_bytes(b"tampered-chart")

    result = check_ingest(conn, media_root=tmp_path / "media")

    assert result.status.startswith("fail")
    assert "media" in result.status
    assert "sha256" in result.status
    conn.close()


def _install_timeline_browser(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    initial_payload: dict,
    *,
    scroll_payloads: list[dict] | None = None,
    status: int = 200,
):
    class FakeResponse:
        url = "https://x.com/i/api/graphql/hash/UserTweetsAndReplies"

        def __init__(self, payload: dict):
            self.payload = payload
            self.status = status

        def json(self):
            return self.payload

    class FakePage:
        def __init__(self):
            self.callback = None
            self.scrolls = 0
            self.remaining = list(scroll_payloads or [])

        def on(self, _event, callback):
            self.callback = callback

        def goto(self, _url, **_kwargs):
            self.callback(FakeResponse(initial_payload))

        def evaluate(self, _script):
            self.scrolls += 1
            if self.remaining:
                self.callback(FakeResponse(self.remaining.pop(0)))

        def wait_for_timeout(self, _milliseconds):
            return None

    page = FakePage()

    class FakeContext:
        pages = [page]

        def close(self):
            return None

    fake_playwright = SimpleNamespace(
        chromium=SimpleNamespace(
            launch_persistent_context=lambda **_kwargs: FakeContext()
        )
    )

    class Manager:
        def __enter__(self):
            return fake_playwright

        def __exit__(self, *_args):
            return None

    monkeypatch.setitem(
        sys.modules,
        "playwright.sync_api",
        SimpleNamespace(sync_playwright=lambda: Manager()),
    )
    monkeypatch.setattr(
        xfetch.config,
        "get",
        lambda key, default=None: {
            "ingest.browser_profile_dir": str(tmp_path / "profile"),
            "ingest.headless": True,
        }.get(key, default),
    )
    return page


def test_fetch_timeline_does_not_treat_old_pinned_post_as_cutoff_completion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    initial = {
        "timeline": [
            _tweet_result("pinned", created_at="Mon Jul 20 08:30:00 +0000 2026"),
            _tweet_result("recent-1", created_at="Sat Aug 22 08:30:00 +0000 2026"),
        ]
    }
    later = {
        "timeline": [
            _tweet_result("recent-2", created_at="Fri Aug 21 08:30:00 +0000 2026")
        ]
    }
    page = _install_timeline_browser(
        monkeypatch, tmp_path, initial, scroll_payloads=[later]
    )

    posts = fetch_timeline("chartist", since="2026-07-24T12:00:00+00:00")

    assert [post.post_id for post in posts] == ["recent-2", "recent-1"]
    assert page.scrolls >= 1


def test_fetch_timeline_rejects_graphql_error_only_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _install_timeline_browser(
        monkeypatch,
        tmp_path,
        {"errors": [{"message": "Rate limit exceeded", "code": 88}]},
    )

    with pytest.raises(RuntimeError, match="GraphQL error"):
        fetch_timeline("chartist", since=None)


def test_fetch_timeline_rejects_http_error_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _install_timeline_browser(monkeypatch, tmp_path, {"data": {}}, status=429)

    with pytest.raises(RuntimeError, match="HTTP 429"):
        fetch_timeline("chartist", since=None)


def test_fetch_timeline_rejects_payload_without_requested_author(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _install_timeline_browser(
        monkeypatch,
        tmp_path,
        {"timeline": [_tweet_result("other", handle="someone_else")]},
    )

    with pytest.raises(RuntimeError, match="requested author"):
        fetch_timeline("chartist", since=None)


def test_fetch_timeline_uses_persistent_profile_and_with_replies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    payload = {"data": {"timeline": [_tweet_result("12345")]}}

    class FakeResponse:
        url = "https://x.com/i/api/graphql/hash/UserTweetsAndReplies"

        @staticmethod
        def json():
            return payload

    class FakePage:
        def __init__(self):
            self.callback = None
            self.visited = None

        def on(self, event, callback):
            assert event == "response"
            self.callback = callback

        def goto(self, url, **_kwargs):
            self.visited = url
            self.callback(FakeResponse())

        def evaluate(self, _script):
            return None

        def wait_for_timeout(self, _milliseconds):
            return None

    page = FakePage()

    class FakeContext:
        pages = [page]

        def close(self):
            self.closed = True

    context = FakeContext()
    launches = []
    chromium = SimpleNamespace(
        launch_persistent_context=lambda **kwargs: launches.append(kwargs) or context
    )
    fake_playwright = SimpleNamespace(chromium=chromium)

    class Manager:
        def __enter__(self):
            return fake_playwright

        def __exit__(self, *_args):
            return None

    module = SimpleNamespace(sync_playwright=lambda: Manager())
    monkeypatch.setitem(sys.modules, "playwright.sync_api", module)
    monkeypatch.setattr(
        xfetch.config,
        "get",
        lambda key, default=None: {
            "ingest.browser_profile_dir": str(tmp_path / "profile"),
            "ingest.headless": True,
        }.get(key, default),
    )

    posts = fetch_timeline("Chartist", since=None)

    assert [post.post_id for post in posts] == ["12345"]
    assert page.visited == "https://x.com/chartist/with_replies"
    assert launches == [
        {"user_data_dir": str(tmp_path / "profile"), "headless": True}
    ]
    assert context.closed is True


def test_open_login_profile_uses_home_page_and_waits_for_user(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    class FakePage:
        visited = None

        def goto(self, url, **_kwargs):
            self.visited = url

    page = FakePage()

    class FakeContext:
        pages = [page]
        closed = False

        def close(self):
            self.closed = True

    context = FakeContext()
    fake_playwright = SimpleNamespace(
        chromium=SimpleNamespace(
            launch_persistent_context=lambda **_kwargs: context
        )
    )

    class Manager:
        def __enter__(self):
            return fake_playwright

        def __exit__(self, *_args):
            return None

    monkeypatch.setitem(
        sys.modules,
        "playwright.sync_api",
        SimpleNamespace(sync_playwright=lambda: Manager()),
    )
    monkeypatch.setattr(
        xfetch.config,
        "get",
        lambda key, default=None: {
            "ingest.browser_profile_dir": str(tmp_path / "profile"),
            "ingest.headless": False,
        }.get(key, default),
    )
    prompts = []

    xfetch.open_login_profile(input_fn=lambda prompt: prompts.append(prompt))

    assert page.visited == "https://x.com/home"
    assert prompts and "log in" in prompts[0].lower()
    assert context.closed is True


def test_main_login_mode_does_not_run_ingest(monkeypatch: pytest.MonkeyPatch):
    calls = []
    monkeypatch.setattr(
        xfetch,
        "open_login_profile",
        lambda: calls.append("login"),
        raising=False,
    )
    monkeypatch.setattr(
        xfetch,
        "run",
        lambda: pytest.fail("login mode must not run ingest"),
    )

    assert xfetch.main(["--login"]) == 0
    assert calls == ["login"]


def test_main_help_does_not_run_ingest(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    monkeypatch.setattr(
        xfetch,
        "run",
        lambda: pytest.fail("help mode must not run ingest"),
    )

    assert xfetch.main(["--help"]) == 0
    output = capsys.readouterr().out
    assert "--login" in output
    assert "--forever" in output


def test_run_xfetch_shim_resolves_package_in_safe_path():
    launcher = Path(__file__).resolve().parents[1] / "run_xfetch.py"

    result = subprocess.run(
        [sys.executable, str(launcher), "--help"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "--login" in result.stdout


def test_poll_interval_uses_configured_jitter(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        xfetch.config,
        "get",
        lambda key, default=None: {
            "ingest.poll_interval_minutes": 15,
            "ingest.jitter_pct": 0.2,
        }.get(key, default),
    )

    low = poll_interval_seconds(uniform=lambda start, _end: start)
    high = poll_interval_seconds(uniform=lambda _start, end: end)

    assert low == 720
    assert high == 1080


def test_new_trader_uses_configured_thirty_day_initial_backfill(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    conn = init_db(tmp_path / "traderlog.db")
    _insert_trader(conn, "chartist")
    fixed_now = datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(
        xfetch.config,
        "get",
        lambda key, default=None: {
            "ingest.initial_backfill_days": 30,
        }.get(key, default),
    )

    since = xfetch._since_for_handle(conn, "chartist", now=fixed_now)

    assert since == "2026-07-24T12:00:00+00:00"
    conn.close()


def test_existing_trader_keeps_seven_day_audit_overlap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    conn = init_db(tmp_path / "traderlog.db")
    _insert_trader(conn, "chartist")
    archive = tmp_path / "existing.json"
    archive.write_text("{}\n", encoding="utf-8")
    conn.execute(
        "INSERT INTO posts "
        "(post_id,handle,ts_utc,ts_ist,raw_path,fetched_at,is_mock,ingested_at) "
        "VALUES ('latest','chartist','2026-08-20T12:00:00+00:00',"
        "'2026-08-20T17:30:00+05:30',?,?,0,?)",
        (str(archive), now_iso(), now_iso()),
    )
    conn.commit()
    monkeypatch.setattr(
        xfetch.config,
        "get",
        lambda key, default=None: {
            "ingest.initial_backfill_days": 30,
        }.get(key, default),
    )

    since = xfetch._since_for_handle(
        conn,
        "chartist",
        now=datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc),
    )

    assert since == "2026-08-13T12:00:00+00:00"
    conn.close()


def test_fetch_timeline_stops_after_three_stagnant_filtered_pages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    payload = {
        "data": {
            "timeline": [
                _tweet_result("recent", created_at="Sat Aug 22 08:30:00 +0000 2026"),
                _tweet_result("old", created_at="Mon Jul 20 08:30:00 +0000 2026"),
            ]
        }
    }

    class FakeResponse:
        url = "https://x.com/i/api/graphql/hash/UserTweetsAndReplies"

        @staticmethod
        def json():
            return payload

    class FakePage:
        def __init__(self):
            self.callback = None
            self.scrolls = 0

        def on(self, _event, callback):
            self.callback = callback

        def goto(self, _url, **_kwargs):
            self.callback(FakeResponse())

        def evaluate(self, _script):
            self.scrolls += 1

        def wait_for_timeout(self, _milliseconds):
            return None

    page = FakePage()

    class FakeContext:
        pages = [page]

        def close(self):
            return None

    fake_playwright = SimpleNamespace(
        chromium=SimpleNamespace(
            launch_persistent_context=lambda **_kwargs: FakeContext()
        )
    )

    class Manager:
        def __enter__(self):
            return fake_playwright

        def __exit__(self, *_args):
            return None

    monkeypatch.setitem(
        sys.modules,
        "playwright.sync_api",
        SimpleNamespace(sync_playwright=lambda: Manager()),
    )
    monkeypatch.setattr(
        xfetch.config,
        "get",
        lambda key, default=None: {
            "ingest.browser_profile_dir": str(tmp_path / "profile"),
            "ingest.headless": True,
        }.get(key, default),
    )

    posts = fetch_timeline("chartist", since="2026-07-24T12:00:00+00:00")

    assert [post.post_id for post in posts] == ["recent"]
    assert page.scrolls == 3


def test_run_never_raises_when_database_setup_fails(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        xfetch,
        "init_db",
        lambda: (_ for _ in ()).throw(OSError("database unavailable")),
    )

    assert run() == 0


def test_check_ingest_passes_at_exactly_eighty_percent_fresh(tmp_path: Path):
    conn = init_db(tmp_path / "traderlog.db")
    archive = tmp_path / "capture.json"
    archive.write_text("{}\n", encoding="utf-8")
    now = datetime.now(timezone.utc)
    for idx in range(5):
        handle = f"trader{idx}"
        _insert_trader(conn, handle)
        fetched = now if idx < 4 else now.replace(year=now.year - 1)
        stamp = fetched.isoformat(timespec="seconds")
        conn.execute(
            "INSERT INTO posts "
            "(post_id,handle,ts_utc,ts_ist,raw_path,fetched_at,is_mock,ingested_at) "
            "VALUES (?,?,?,?,?,?,0,?)",
            (str(idx), handle, stamp, stamp, str(archive), stamp, stamp),
        )
    conn.commit()

    result = check_ingest(conn)

    assert result.status == "pass"
    assert result.detail == "4/5 traders fresh"
    conn.close()


def test_check_ingest_without_roster_is_stale_not_not_built(tmp_path: Path):
    conn = init_db(tmp_path / "traderlog.db")

    result = check_ingest(conn)

    assert result.status == "stale_0d"
    conn.close()


def test_run_preserves_roster_handle_case_for_foreign_key(tmp_path: Path):
    conn = init_db(tmp_path / "traderlog.db")
    _insert_trader(conn, "Chartist")

    result = run(
        conn,
        run_date="2026-08-23",
        fetcher=lambda _handle, _since: [_raw_post()],
        raw_root=tmp_path / "raw",
        media_root=tmp_path / "media",
    )

    assert result == 1
    stored = conn.execute("SELECT handle FROM posts").fetchone()
    assert stored["handle"] == "Chartist"
    conn.close()


def test_run_does_not_mark_posts_outside_returned_timeline_slice(tmp_path: Path):
    conn = init_db(tmp_path / "traderlog.db")
    _insert_trader(conn, "chartist")
    archive = tmp_path / "existing.json"
    archive.write_text("{}\n", encoding="utf-8")
    conn.execute(
        "INSERT INTO posts "
        "(post_id,handle,ts_utc,ts_ist,raw_path,fetched_at,is_mock,ingested_at) "
        "VALUES ('older','chartist','2026-08-20T08:00:00+00:00',"
        "'2026-08-20T13:30:00+05:30',?,?,0,?)",
        (str(archive), now_iso(), now_iso()),
    )
    conn.commit()
    returned = RawPost(
        **{
            **_raw_post().__dict__,
            "post_id": "newer",
            "ts_utc": "2026-08-22T08:30:00+00:00",
        }
    )

    assert run(
        conn,
        run_date="2026-08-23",
        fetcher=lambda _handle, _since: [returned],
        raw_root=tmp_path / "raw",
        media_root=tmp_path / "media",
    ) == 1

    deleted = conn.execute(
        "SELECT deleted_at FROM posts WHERE post_id='older'"
    ).fetchone()[0]
    assert deleted is None
    conn.close()


def test_isolated_dummy_replay_proves_seven_day_three_trader_acceptance_shape(
    tmp_path: Path,
):
    """Synthetic evidence exercises W1 mechanics but never counts as live proof."""
    conn = init_db(tmp_path / "dummy-replay.db")
    handles = ("dummy_alpha", "dummy_beta", "dummy_gamma")
    for handle in handles:
        _insert_trader(conn, handle)

    base = datetime(2026, 8, 17, 8, 30, tzinfo=timezone.utc)
    corpus: dict[str, list[RawPost]] = {handle: [] for handle in handles}
    deleted_id = "dummy_beta_2"

    for day in range(7):
        for handle in handles:
            post_id = f"{handle}_{day}"
            root_id = f"{handle}_0"
            is_alpha_reply = handle == "dummy_alpha" and day == 1
            corpus[handle].append(
                RawPost(
                    post_id=post_id,
                    handle=handle,
                    conversation_id=root_id if is_alpha_reply else post_id,
                    in_reply_to=root_id if is_alpha_reply else None,
                    ts_utc=(base + timedelta(days=day)).isoformat(timespec="seconds"),
                    text=f"dummy day {day} for {handle}",
                    url=f"https://x.com/{handle}/status/{post_id}",
                    media=(
                        [RawMedia(f"https://example.invalid/{post_id}.png", "image")]
                        if handle == "dummy_alpha" and day in {0, 1}
                        else []
                    ),
                    raw={"source": "synthetic-w1-replay", "id": post_id},
                )
            )

        def fetcher(handle: str, _since: str | None) -> list[RawPost]:
            visible = corpus[handle]
            if day >= 4 and handle == "dummy_beta":
                visible = [post for post in visible if post.post_id != deleted_id]
            return list(visible)

        inserted = run(
            conn,
            run_date=(base + timedelta(days=day)).date().isoformat(),
            fetcher=fetcher,
            raw_root=tmp_path / "raw",
            media_root=tmp_path / "media",
            downloader=lambda url: (f"dummy-chart:{url}".encode(), "image/png"),
        )
        assert inserted == 3

    assert conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0] == 21
    assert len(list((tmp_path / "raw").rglob("*.json"))) == 21
    assert conn.execute("SELECT COUNT(*) FROM post_media").fetchone()[0] == 2
    assert all(
        len(row[0]) == 64
        for row in conn.execute("SELECT sha256 FROM post_media").fetchall()
    )

    reply = conn.execute(
        "SELECT conversation_id,in_reply_to FROM posts WHERE post_id='dummy_alpha_1'"
    ).fetchone()
    assert tuple(reply) == ("dummy_alpha_0", "dummy_alpha_0")
    assert conn.execute(
        "SELECT deleted_at FROM posts WHERE post_id=?", (deleted_id,)
    ).fetchone()[0] is not None
    assert conn.execute(
        "SELECT COUNT(*) FROM pipeline_runs WHERE stage='ingest.xfetch' AND status='ok'"
    ).fetchone()[0] == 7
    assert check_ingest(conn, media_root=tmp_path / "media").status == "pass"
    conn.close()
