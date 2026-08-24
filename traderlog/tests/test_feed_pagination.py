from __future__ import annotations

import json
import socket
import threading
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from traderlog.api import app as api_app
from traderlog.db import connect, init_db, now_iso


_DIST = Path(__file__).resolve().parents[1] / "ui" / "dist"


@pytest.fixture
def feed_db(tmp_path, monkeypatch):
    path = tmp_path / "traderlog.db"
    conn = init_db(path)
    conn.execute(
        "INSERT INTO traders (handle,active,is_mock,ingested_at) VALUES ('trader',1,0,?)",
        (now_iso(),),
    )

    def post(post_id, ts, *, conversation_id, in_reply_to, kind="trade_event"):
        conn.execute(
            "INSERT INTO posts (post_id,handle,conversation_id,in_reply_to,ts_utc,ts_ist,text,url,fetched_at,is_mock,ingested_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (post_id, "trader", conversation_id, in_reply_to, ts, ts, post_id, f"https://x.com/trader/status/{post_id}", now_iso(), 0, now_iso()),
        )
        conn.execute(
            "INSERT INTO post_class (post_id,kind,confidence,symbols,is_mock,ingested_at) VALUES (?,?,?,?,?,?)",
            (post_id, kind, 0.9, json.dumps(["TEST"]), 0, now_iso()),
        )

    post("root", "2026-08-01T09:00:00+00:00", conversation_id="root", in_reply_to=None)
    post("old", "2026-08-02T09:00:00+00:00", conversation_id="old", in_reply_to=None, kind="breadth")
    post("middle", "2026-08-03T09:00:00+00:00", conversation_id="middle", in_reply_to=None)
    # Deliberately unknown DOM ancestry: it must never be labelled a confirmed root.
    post("unknown", "2026-08-04T09:00:00+00:00", conversation_id=None, in_reply_to=None)
    post("reply", "2026-08-05T09:00:00+00:00", conversation_id="root", in_reply_to="root")
    conn.commit()
    monkeypatch.setattr(api_app, "connect", lambda: connect(path))
    yield conn
    conn.close()


def test_feed_pagination_reports_base_total_and_root_augmentation_without_advancing_offset(feed_db):
    page = api_app.feed(limit=2, offset=0)

    assert page["pagination"] == {
        "total": 5, "limit": 2, "offset": 0, "page": 1,
        "returned": 2, "next_offset": 2, "has_more": True,
    }
    assert {post["post_id"] for post in page["posts"]} == {"root", "reply", "unknown"}
    assert len({post["post_id"] for post in page["posts"]}) == len(page["posts"])
    assert next(post for post in page["posts"] if post["post_id"] == "unknown")["relationship_known"] is False
    assert next(post for post in page["posts"] if post["post_id"] == "root")["relationship_known"] is True


def test_feed_second_page_is_deterministic_and_filters_reset_the_base_total(feed_db):
    first = api_app.feed(limit=2, offset=0)
    second = api_app.feed(limit=2, offset=first["pagination"]["next_offset"])
    repeat_second = api_app.feed(limit=2, offset=2)
    filtered = api_app.feed(limit=2, offset=0, kind="breadth")

    assert [post["post_id"] for post in second["posts"]] == [post["post_id"] for post in repeat_second["posts"]]
    assert second["pagination"] == {
        "total": 5, "limit": 2, "offset": 2, "page": 2,
        "returned": 2, "next_offset": 4, "has_more": True,
    }
    assert {post["post_id"] for post in first["posts"] if post["post_id"] != "root"}.isdisjoint(
        {post["post_id"] for post in second["posts"]}
    )
    assert filtered["pagination"] == {
        "total": 1, "limit": 2, "offset": 0, "page": 1,
        "returned": 1, "next_offset": None, "has_more": False,
    }
    assert [post["post_id"] for post in filtered["posts"]] == ["old"]


def test_feed_clamps_limit_and_offset_safely(feed_db):
    page = api_app.feed(limit=999, offset=-20)

    assert page["pagination"]["limit"] == 100
    assert page["pagination"]["offset"] == 0
    assert page["pagination"]["total"] == 5


def test_feed_keeps_numeric_thread_ids_in_oldest_first_order(feed_db):
    root_id = "2092000000000000001"
    reply_id = "2092000000000000002"
    for post_id, ts, in_reply_to in (
        (root_id, "2026-09-01T09:00:00+00:00", None),
        (reply_id, "2026-09-01T10:00:00+00:00", root_id),
    ):
        feed_db.execute(
            "INSERT INTO posts (post_id,handle,conversation_id,in_reply_to,ts_utc,ts_ist,text,url,fetched_at,is_mock,ingested_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (post_id, "trader", root_id, in_reply_to, ts, ts, post_id, f"https://x.com/trader/status/{post_id}", now_iso(), 0, now_iso()),
        )
        feed_db.execute(
            "INSERT INTO post_class (post_id,kind,confidence,symbols,is_mock,ingested_at) VALUES (?,?,?,?,?,?)",
            (post_id, "trade_event", 0.9, json.dumps(["TEST"]), 0, now_iso()),
        )
    feed_db.commit()

    page = api_app.feed(limit=1, offset=0)

    assert [post["post_id"] for post in page["posts"]] == [root_id, reply_id]


def test_feed_browser_loads_older_without_duplicate_thread_context(tmp_path, monkeypatch):
    """The visible count tracks base posts, not root context added by the API.

    Rendered against the rebuilt TODAY screen (scouting×wire 2026-08-24): the
    post rows are article.td-row banded by rule, the pagination footer renders
    "<loaded> of <total> posts" with the same "Load older posts" button, and
    the unknown-ancestry signal is the row's "post ↗" relationship label (the
    old "thread unknown" chip is gone).
    """
    if not (_DIST / "index.html").exists():
        pytest.skip("ui/dist not built - run npm run build")

    from playwright.sync_api import sync_playwright
    import uvicorn

    path = tmp_path / "traderlog.db"
    conn = init_db(path)
    conn.execute(
        "INSERT INTO traders (handle,active,is_mock,ingested_at) VALUES ('trader',1,0,?)",
        (now_iso(),),
    )
    start = datetime(2026, 8, 1, 9, tzinfo=timezone.utc)

    def post(post_id, index, *, conversation_id, in_reply_to, kind="trade_event"):
        ts = (start + timedelta(hours=index)).isoformat()
        conn.execute(
            "INSERT INTO posts (post_id,handle,conversation_id,in_reply_to,ts_utc,ts_ist,text,url,fetched_at,is_mock,ingested_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (post_id, "trader", conversation_id, in_reply_to, ts, ts, post_id, f"https://x.com/trader/status/{post_id}", now_iso(), 0, now_iso()),
        )
        conn.execute(
            "INSERT INTO post_class (post_id,kind,confidence,symbols,is_mock,ingested_at) VALUES (?,?,?,?,?,?)",
            (post_id, kind, 0.9, json.dumps(["TEST"]), 0, now_iso()),
        )

    post("root", 0, conversation_id="root", in_reply_to=None)
    post("unknown", 33, conversation_id=None, in_reply_to=None)
    for index in range(2, 34):
        post(f"post-{index}", index, conversation_id=f"post-{index}", in_reply_to=None,
             kind="breadth" if index in {10, 11} else "trade_event")
    post("reply", 34, conversation_id="root", in_reply_to="root")
    conn.commit()
    monkeypatch.setattr(api_app, "connect", lambda: connect(path))

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = int(sock.getsockname()[1])
    server = uvicorn.Server(uvicorn.Config(api_app.app, host="127.0.0.1", port=port, log_level="warning"))
    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=1) as res:
                if res.status == 200:
                    break
        except Exception:  # noqa: BLE001 - transient while uvicorn starts
            time.sleep(0.1)
    else:
        pytest.fail("test API server did not start")

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1920, "height": 1080})
            try:
                page.goto(f"http://127.0.0.1:{port}/", wait_until="networkidle")
                page.get_by_text("30 of 35 posts", exact=True).wait_for()
                assert page.locator("article.td-row").count() == 31  # reply plus augmented root
                # Unknown ancestry reads "post ↗"; known threads read "thread ↗".
                assert page.locator(".td-row .td-meta a", has_text="post ↗").count() == 1

                page.get_by_role("button", name="Load older posts").click()
                page.get_by_text("35 of 35 posts", exact=True).wait_for()
                assert page.locator("article.td-row").count() == 35
                assert page.locator("article.td-row", has_text="root").count() == 1
                assert page.get_by_role("button", name="Load older posts").count() == 0

                page.get_by_label("kind").select_option("breadth")
                page.get_by_text("2 of 2 posts", exact=True).wait_for()
                assert page.locator("article.td-row").count() == 2
            finally:
                browser.close()
    finally:
        server.should_exit = True
        server_thread.join(timeout=5)
        conn.close()
        if server_thread.is_alive():
            pytest.fail("test API server did not stop")
