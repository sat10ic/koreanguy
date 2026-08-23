"""W3c 1920x1080 PC layout acceptance (HANDOFF_W3c_pc_ui_recovery.md).

Every test runs against a disposable database on a free localhost port, at a
real-browser 1920x1080 viewport. The production database is never opened; the
TWO read-only touches of production material are ``post_media`` rows pointing
at real archived images (the 1709px-wide holdings capture and its sibling),
served through the real ``/api/media`` path -- the exact intrinsic-size
hazard the handoff's containment rules exist for. The files are read, never
modified.

Containment is asserted structurally (panel scrollWidth vs clientWidth,
image width vs its media box, document scrollWidth vs viewport) because the
original defect was masked by ``overflow: hidden``: the document measured
1920 while a child was 2675px wide.
"""
from __future__ import annotations

import hashlib
import socket
import threading
import time
import urllib.request
from pathlib import Path

import pytest

from traderlog.api import app as api_app
from traderlog.db import connect, init_db, now_iso
from traderlog.tests.test_link import _open_position

_DIST = Path(__file__).resolve().parents[1] / "ui" / "dist"
_MEDIA = Path(__file__).resolve().parents[1] / "data" / "media"
# The real archived holdings strip that measured 1709px intrinsic in the audit.
_WIDE_IMAGE = "2090713569793126757_0.jpg"
_WIDE_NATURAL = 1709
# The sibling capture of the same real archive (read-only): FEED's second
# thumbnail, driving the .feed-thumbs strip's multi-image containment.
_THUMB_IMAGE = "2090713569793126757_1.jpg"

NAV_TABS = ["FEED", "TRADERS", "LEDGER", "BREADTH", "IDEAS", "LIBRARY"]


def _require_built_ui() -> None:
    if not (_DIST / "index.html").exists():
        pytest.skip("ui/dist not built - run npm run build")


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_ready(port: int, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    last: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/api/health", timeout=1
            ) as res:
                if res.status == 200:
                    return
        except Exception as exc:  # noqa: BLE001 - poll until deadline, then report
            last = exc
            time.sleep(0.1)
    raise AssertionError(f"test API server not ready within {timeout}s: {last!r}")


class Harness:
    def __init__(self, conn, port, page):
        self.conn = conn
        self.port = port
        self.page = page

    @property
    def base(self) -> str:
        return f"http://127.0.0.1:{self.port}"


@pytest.fixture(scope="module")
def browser():
    _require_built_ui()
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        launched = pw.chromium.launch(headless=True)
        yield launched
        launched.close()


@pytest.fixture
def harness(tmp_path, monkeypatch, browser):
    import uvicorn

    path = tmp_path / "traderlog.db"
    conn = init_db(path)
    position_id = _open_position(conn)  # alice / ALPHA / root post / entry event
    # The root post's entry event carries the REAL wide archived image, served
    # read-only from data/media through /api/media -- intrinsic 1709px wide.
    wide = _MEDIA / _WIDE_IMAGE
    assert wide.exists(), "archived wide image missing from data/media"
    sha = hashlib.sha256(wide.read_bytes()).hexdigest()
    conn.execute(
        "INSERT INTO post_media (post_id, idx, local_path, sha256, media_type, is_mock, ingested_at)"
        " VALUES (?,?,?,?,?,?,?)",
        ("root", 0, _WIDE_IMAGE, sha, "image", 0, now_iso()),
    )
    # Second row for the same post: the sibling capture of the same real
    # archive, read-only from data/media. FEED's .feed-thumbs strip then
    # renders two contained thumbnails (Slice B evidence-desk behavior).
    thumb = _MEDIA / _THUMB_IMAGE
    assert thumb.exists(), "archived sibling thumb image missing from data/media"
    sha2 = hashlib.sha256(thumb.read_bytes()).hexdigest()
    conn.execute(
        "INSERT INTO post_media (post_id, idx, local_path, sha256, media_type, is_mock, ingested_at)"
        " VALUES (?,?,?,?,?,?,?)",
        ("root", 1, _THUMB_IMAGE, sha2, "image", 0, now_iso()),
    )
    conn.commit()

    monkeypatch.setattr(api_app, "connect", lambda: connect(path))

    port = _free_port()
    server = uvicorn.Server(
        uvicorn.Config(api_app.app, host="127.0.0.1", port=port, log_level="warning")
    )
    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()
    _wait_ready(port)

    context = browser.new_context(viewport={"width": 1920, "height": 1080})
    page = context.new_page()
    try:
        yield Harness(conn, port, page)
    finally:
        context.close()
        server.should_exit = True
        server_thread.join(timeout=5)
        if server_thread.is_alive():
            pytest.fail("uvicorn server thread still alive 5s after should_exit")
        conn.close()


GEOMETRY = """() => {
  const pg = document.querySelector('.page');
  const panels = [...document.querySelectorAll('.panel')]
    .filter(p => p.scrollWidth > p.clientWidth + 1).length;
  return {
    pageW: pg ? Math.round(pg.getBoundingClientRect().width) : null,
    pageX: pg ? Math.round(pg.getBoundingClientRect().x) : null,
    docScrollW: document.documentElement.scrollWidth,
    overflowingPanels: panels,
    tabs: [...document.querySelectorAll('.tab')].map(t => t.textContent.trim()),
    bodyFs: getComputedStyle(document.body).fontSize,
  };
}"""


def test_centered_grid_and_six_product_tabs_at_1920(harness):
    page = harness.page
    page.goto(f"{harness.base}/?tab=FEED", wait_until="networkidle")
    g = page.evaluate(GEOMETRY)
    assert g["pageW"] == 1680 and g["pageX"] == 120, g
    assert g["docScrollW"] == 1920, g
    assert g["overflowingPanels"] == 0, g
    assert g["tabs"] == NAV_TABS, g  # STYLE absent from visible navigation
    assert g["bodyFs"] == "14px", g  # reading copy, not the old 12px defect
    # Evidence-desk composition: primary workspace + secondary rail.
    assert page.locator(".feed-primary").count() == 1
    assert page.locator(".feed-rail").count() == 1


def test_style_route_renders_outside_navigation(harness):
    page = harness.page
    page.goto(f"{harness.base}/?tab=STYLE", wait_until="networkidle")
    assert page.evaluate(GEOMETRY)["tabs"] == NAV_TABS
    assert page.locator("main .panel, main .style-gallery").count() > 0


def test_ledger_expanded_media_containment_at_1920(harness):
    page = harness.page
    page.goto(f"{harness.base}/?tab=LEDGER", wait_until="networkidle")
    page.locator(".disclosure").first.click()
    page.wait_for_selector(".detail-grid", timeout=5000)
    page.wait_for_selector(".media-box img", timeout=5000)
    page.wait_for_function(
        "() => [...document.querySelectorAll('.media-box img')].every(i => i.complete && i.naturalWidth > 0)"
    )

    m = page.evaluate(
        """() => {
          const img = document.querySelector('.media-box img');
          const box = img.closest('.media-box');
          return {
            natural: img.naturalWidth,
            rendered: Math.round(img.getBoundingClientRect().width),
            boxClient: box.clientWidth,
            right: Math.round(img.getBoundingClientRect().right),
            docScrollW: document.documentElement.scrollWidth,
            panels: [...document.querySelectorAll('.panel')]
              .filter(p => p.scrollWidth > p.clientWidth + 1).length,
          };
        }"""
    )
    # The hazard is real: the intrinsic width exceeds the container by >3x...
    assert m["natural"] == _WIDE_NATURAL, m
    # ...and the image is contained: it renders at box width, not intrinsic
    # width, nothing exceeds the viewport, and no panel silently clips.
    assert m["rendered"] <= m["boxClient"] + 1, m
    assert m["rendered"] < m["natural"], m
    assert m["right"] <= 1920, m
    assert m["docScrollW"] == 1920, m
    assert m["panels"] == 0, m


def test_pc_console_clean(harness):
    page = harness.page
    issues = []
    page.on("console", lambda m: issues.append(f"{m.type}: {m.text}") if m.type in ("error", "warning") else None)
    page.on("pageerror", lambda e: issues.append(str(e)))
    page.goto(f"{harness.base}/?tab=FEED", wait_until="networkidle")
    page.goto(f"{harness.base}/?tab=LEDGER", wait_until="networkidle")
    assert issues == [], issues


def test_feed_thumbnails_render_and_contain(harness):
    """Slice B: both archived post_media rows render as contained /api/media
    thumbnails on the media post -- no X hotlink, no overflow -- and a
    text-only post must never render a strip (strips are backed by media)."""
    page = harness.page
    page.goto(f"{harness.base}/?tab=FEED", wait_until="networkidle")

    root = page.locator("article.post.post-root")
    root.wait_for(state="attached", timeout=5000)
    # Two post_media rows for the root post -> exactly one strip with two imgs.
    assert root.locator(".feed-thumbs").count() == 1
    assert root.locator(".feed-thumbs img").count() == 2
    page.wait_for_function(
        "() => document.querySelectorAll('.feed-thumbs img').length === 2",
        timeout=5000,
    )
    # Deterministic image-ready wait: both imgs decoded before any measurement.
    page.wait_for_function(
        "() => [...document.querySelectorAll('.feed-thumbs img')]"
        ".every(i => i.complete && i.naturalWidth > 0)",
        timeout=5000,
    )

    m = page.evaluate(
        """() => {
          const imgs = [...document.querySelectorAll('.feed-thumbs img')];
          const strip = document.querySelector('.feed-thumbs');
          const posts = [...document.querySelectorAll('article.post')];
          return {
            srcs: imgs.map(i => i.getAttribute('src')),
            widths: imgs.map(i => Math.round(i.getBoundingClientRect().width)),
            stripClient: strip ? strip.clientWidth : 0,
            postsWithMedia: posts.filter(a =>
              a.querySelector('.post-meta')?.textContent.includes('archived')).length,
            strips: document.querySelectorAll('.feed-thumbs').length,
            docScrollW: document.documentElement.scrollWidth,
            panels: [...document.querySelectorAll('.panel')]
              .filter(p => p.scrollWidth > p.clientWidth + 1).length,
          };
        }"""
    )
    assert len(m["srcs"]) == 2, m
    # Source-backed evidence: never a remote X host -- always our /api/media.
    assert all(s.startswith("/api/media/") for s in m["srcs"]), m
    assert not any("x.com" in s or "twimg" in s for s in m["srcs"]), m
    # Contained: intrinsic sizes never widen the strip, panel, or document.
    assert all(w <= m["stripClient"] + 1 for w in m["widths"]), m
    assert m["docScrollW"] == 1920, m
    assert m["panels"] == 0, m
    # Text-only posts render no strip: every strip is backed by post_media.
    assert m["strips"] <= m["postsWithMedia"], m
    assert m["postsWithMedia"] == 1 and m["strips"] == 1, m


def test_feed_thread_ancestry_labels(harness):
    """Slice B: a known root+reply pair keeps the spine and a thread_pos chip
    (reply renders .post-reply with '2/2'); a post with BOTH ancestry ids NULL
    renders the 'thread unknown' chip and never the root/reply spine classes."""
    conn = harness.conn
    now = now_iso()
    conn.execute(
        "INSERT INTO posts (post_id,handle,conversation_id,in_reply_to,ts_utc,ts_ist,"
        "text,url,fetched_at,is_mock,ingested_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        ("reply", "alice", "root", "root", "2026-08-02T10:00:00+00:00",
         "2026-08-02T15:30:00+05:30", "Booked ALPHA at 120",
         "https://x.com/alice/status/reply", now, 0, now),
    )
    # Both ids NULL -> api/app.py derives relationship_known False: the post
    # must be marked "thread unknown", never presented as a confirmed root.
    conn.execute(
        "INSERT INTO posts (post_id,handle,conversation_id,in_reply_to,ts_utc,ts_ist,"
        "text,url,fetched_at,is_mock,ingested_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        ("orphan", "alice", None, None, "2026-08-03T10:00:00+00:00",
         "2026-08-03T15:30:00+05:30", "Standalone claim with no captured ancestry",
         "https://x.com/alice/status/orphan", now, 0, now),
    )
    conn.commit()

    page = harness.page
    page.goto(f"{harness.base}/?tab=FEED", wait_until="networkidle")
    page.wait_for_function(
        "() => document.querySelectorAll('article.post').length === 3", timeout=5000
    )

    root_art = page.locator("article.post", has_text="LONG ALPHA at 100")
    reply_art = page.locator("article.post", has_text="Booked ALPHA at 120")
    orphan_art = page.locator("article.post", has_text="Standalone claim")

    # Known pair: the root carries the spine root class; the reply is a
    # .post-reply sitting at position 2 of 2 inside the shared conversation.
    assert "post-root" in root_art.evaluate("el => [...el.classList]")
    assert "post-reply" in reply_art.evaluate("el => [...el.classList]")
    assert reply_art.locator(".thread-pos").inner_text().strip() == "2/2"

    # Null pair: never styled as root or reply, and explicitly flagged.
    orphan_cls = orphan_art.evaluate("el => [...el.classList]")
    assert "post-unknown" in orphan_cls
    assert "post-root" not in orphan_cls, orphan_cls
    assert "post-reply" not in orphan_cls, orphan_cls
    assert orphan_art.get_by_text("thread unknown", exact=True).count() == 1


def test_screenshots_all_six_tabs_1920(harness):
    """Evidence-desk screenshot inventory: one full-viewport PNG per product
    tab at 1920x1080, kept with the completion report. Console and page
    errors stay clean across all six navigations."""
    page = harness.page
    out = Path(__file__).resolve().parents[1] / "output" / "playwright" / "evidence-desk"
    out.mkdir(parents=True, exist_ok=True)

    issues: list[str] = []
    page.on("console", lambda m: issues.append(f"{m.type}: {m.text}") if m.type in ("error", "warning") else None)
    page.on("pageerror", lambda e: issues.append(str(e)))

    targets = {}
    for tab in NAV_TABS:
        page.goto(f"{harness.base}/?tab={tab}", wait_until="networkidle")
        # Deterministic ready wait: the screen's own panels are in and no
        # fetch is still showing the Loading placeholder.
        page.wait_for_function(
            "() => document.querySelectorAll('main .panel').length > 0"
            " && ![...document.querySelectorAll('main .empty')]"
            ".some(e => e.textContent.includes('loading'))",
            timeout=10000,
        )
        target = out / f"final-1920-{tab.lower()}.png"
        page.screenshot(path=str(target), full_page=False)
        targets[tab] = target

    for tab, target in targets.items():
        assert target.exists(), f"missing screenshot for {tab}: {target}"
        size = target.stat().st_size
        assert size > 10_000, f"{target} too small to be real evidence: {size} bytes"
    assert issues == [], issues