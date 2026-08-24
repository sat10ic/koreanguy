"""1920x1080 PC layout acceptance — scouting×wire reboot (2026-08-24).

The FEED/BREADTH screens became TODAY/MARKET and the six product tabs are now
TODAY LEDGER TRADERS IDEAS LIBRARY MARKET (STYLE stays route-only). The
centered 1680px desktop grid at 1920x1080 STAYS (pageW 1680, pageX 120); the
body scale is now 12.5px (--fs-body).

Every test runs against a disposable database on a free localhost port, at a
real-browser 1920x1080 viewport. The production database is never opened; the
TWO read-only touches of production material are ``post_media`` rows pointing
at real archived images (the 1709px-wide holdings capture and its sibling),
served through the real ``/api/media`` path -- the exact intrinsic-size
hazard the W3c containment rules exist for. The files are read, never
modified.

Containment is asserted structurally (panel scrollWidth vs clientWidth,
image width vs its media box, document scrollWidth vs viewport) because the
original defect was masked by ``overflow: hidden``: the document measured
1920 while a child was 2675px wide.

In the new UI the media strip no longer renders on TODAY (thumbnails moved off
the newswire by design); the containment + source-backing assertions now live
where the images actually render -- the LEDGER expanded detail (.detail-grid /
.media-box). The thread-ancestry coverage moved to the new TODAY row furniture
(.td-thread-pos chip, .td-reply spine, "post ↗"/"thread ↗" relationship label).
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
# The sibling capture of the same real archive (read-only): the LEDGER detail
# renders both post_media rows inside .media-box figures -- the multi-image
# containment case the old feed-thumbs strip covered.
_THUMB_IMAGE = "2090713569793126757_1.jpg"

NAV_TABS = ["TODAY", "LEDGER", "TRADERS", "IDEAS", "LIBRARY", "MARKET"]


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
    # archive, read-only from data/media. The LEDGER detail then renders two
    # contained .media-box figures (the multi-image containment case).
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

# Screen-ready predicate: any fetch-backed screen has stopped showing the
# shared Loading placeholder (a p.empty whose text contains "loading"). TODAY
# has no .panel, so the presence side accepts the filters toolbar instead.
READY = """() => {
  const loading = [...document.querySelectorAll('main .empty')]
    .some(e => e.textContent.includes('loading'));
  const present = document.querySelectorAll('main .panel, main .td-filters').length > 0;
  return present && !loading;
}"""


def test_centered_grid_and_six_product_tabs_at_1920(harness):
    page = harness.page
    page.goto(f"{harness.base}/?tab=TODAY", wait_until="networkidle")
    page.wait_for_function(READY, timeout=10000)
    g = page.evaluate(GEOMETRY)
    assert g["pageW"] == 1680 and g["pageX"] == 120, g
    assert g["docScrollW"] == 1920, g
    assert g["overflowingPanels"] == 0, g
    assert g["tabs"] == NAV_TABS, g  # STYLE absent from visible navigation
    assert g["bodyFs"] == "12.5px", g  # --fs-body scale, not the old 14px
    # Today composition: the newscreen is bands in fixed order, the money band
    # headed by its own kicker and carrying the ONE accent use (Rule 3).
    assert page.locator(".td-band[data-band='money']").count() == 1
    assert page.locator(".td-band[data-band='money'] .td-kicker").inner_text() == "MONEY MOVED"
    assert page.locator(".td-risk-mark").count() == 1  # the money row, only it
    assert page.locator(".td-band[data-band='money'] .td-risk-mark").count() == 1


def test_style_route_renders_outside_navigation(harness):
    page = harness.page
    page.goto(f"{harness.base}/?tab=STYLE", wait_until="networkidle")
    assert page.evaluate(GEOMETRY)["tabs"] == NAV_TABS
    assert page.locator("main .panel, main .style-gallery").count() > 0


def test_ledger_expanded_media_containment_at_1920(harness):
    page = harness.page
    page.goto(f"{harness.base}/?tab=LEDGER", wait_until="networkidle")
    page.wait_for_function(READY, timeout=10000)
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
    page.goto(f"{harness.base}/?tab=TODAY", wait_until="networkidle")
    page.goto(f"{harness.base}/?tab=LEDGER", wait_until="networkidle")
    assert issues == [], issues


def test_ledger_media_strip_contained_and_source_backed(harness):
    """Both archived post_media rows render as contained /api/media figures in
    the LEDGER expanded detail -- no X hotlink, no overflow -- mirroring the
    W3 feed-thumbs source discipline (every image is ours, none external)."""
    page = harness.page
    page.goto(f"{harness.base}/?tab=LEDGER", wait_until="networkidle")
    page.wait_for_function(READY, timeout=10000)
    page.locator(".disclosure").first.click()
    page.wait_for_selector(".detail-grid", timeout=5000)
    page.wait_for_function(
        "() => document.querySelectorAll('.media-box img').length === 2",
        timeout=5000,
    )
    page.wait_for_function(
        "() => [...document.querySelectorAll('.media-box img')]"
        ".every(i => i.complete && i.naturalWidth > 0)",
        timeout=5000,
    )

    m = page.evaluate(
        """() => {
          const imgs = [...document.querySelectorAll('.media-box img')];
          const boxes = [...document.querySelectorAll('.media-box')];
          const widths = imgs.map(i => Math.round(i.getBoundingClientRect().width));
          return {
            srcs: imgs.map(i => i.getAttribute('src')),
            naturals: imgs.map(i => i.naturalWidth),
            widths,
            boxes: boxes.map(b => b.clientWidth),
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
    # Contained: intrinsic sizes never widen a box, a panel, or the document.
    assert all(w <= b + 1 for w, b in zip(m["widths"], m["boxes"])), m
    assert all(w < n for w, n in zip(m["widths"], m["naturals"])), m
    assert m["docScrollW"] == 1920, m
    assert m["panels"] == 0, m


def test_today_thread_ancestry_labels(harness):
    """A known root+reply pair keeps its identity on TODAY: the thread-position
    chip (.td-thread-pos '2/2') and, when both land in the same band, the 1px
    .td-reply spine under the root. A post with BOTH ancestry ids NULL renders
    no chip and its relationship label reads 'post ↗' -- never styled as a
    confirmed root ('thread ↗')."""
    conn = harness.conn
    now = now_iso()
    position_id = conn.execute(
        "SELECT position_id FROM positions WHERE root_post_id='root'"
    ).fetchone()[0]
    conn.execute(
        "INSERT INTO posts (post_id,handle,conversation_id,in_reply_to,ts_utc,ts_ist,"
        "text,url,fetched_at,is_mock,ingested_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        ("reply", "alice", "root", "root", "2026-08-02T10:00:00+00:00",
         "2026-08-02T15:30:00+05:30", "Booked ALPHA at 120",
         "https://x.com/alice/status/reply", now, 0, now),
    )
    # Give the reply a stated price in position_events, so it lands in the
    # MONEY MOVED band directly under its root -- the condition for the spine.
    # (Banding is computed from kind + event.price; the reply needs both.)
    conn.execute(
        "INSERT INTO post_class (post_id,kind,confidence,symbols,is_mock,ingested_at)"
        " VALUES (?,?,?,?,?,?)",
        ("reply", "trade_event", 1.0, "[]", 0, now),
    )
    conn.execute(
        "INSERT INTO position_events (position_id, post_id, kind, price, stated_at,"
        " seq, is_mock, ingested_at) VALUES (?,?,?,?,?,?,?,?)",
        (position_id, "reply", "entry", 150, "2026-08-02T15:30:00+05:30", 5, 0, now),
    )
    # Both ids NULL -> api/app.py derives relationship_known False: the post
    # must be labelled "post ↗" (relationship unknown), never a confirmed root.
    conn.execute(
        "INSERT INTO posts (post_id,handle,conversation_id,in_reply_to,ts_utc,ts_ist,"
        "text,url,fetched_at,is_mock,ingested_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        ("orphan", "alice", None, None, "2026-08-03T10:00:00+00:00",
         "2026-08-03T15:30:00+05:30", "Standalone claim with no captured ancestry",
         "https://x.com/alice/status/orphan", now, 0, now),
    )
    conn.commit()

    page = harness.page
    page.goto(f"{harness.base}/?tab=TODAY", wait_until="networkidle")
    page.wait_for_function(
        "() => [...document.querySelectorAll('article.td-row')].length === 3",
        timeout=5000,
    )

    root_art = page.locator("article.td-row", has_text="LONG ALPHA at 100")
    reply_art = page.locator("article.td-row", has_text="Booked ALPHA at 120")
    orphan_art = page.locator("article.td-row", has_text="Standalone claim")

    # Known pair in the same band: root + reply carry position chips and the
    # reply sits on the 1px spine (2/2, in the MONEY band under its root).
    assert root_art.locator(".td-thread-pos").inner_text().strip() == "1/2"
    assert reply_art.locator(".td-thread-pos").inner_text().strip() == "2/2"
    assert "td-reply" in reply_art.evaluate("el => [...el.classList]")
    assert reply_art.evaluate("el => el.getAttribute('data-band')") == "money"

    # Null pair: no chip (a singleton never gets a thread position), no root
    # styling -- the relationship label says the ancestry is unknown.
    assert orphan_art.locator(".td-thread-pos").count() == 0
    assert orphan_art.locator(".td-meta").count() == 1
    assert orphan_art.locator(".td-meta a", has_text="post ↗").count() == 1
    assert root_art.locator(".td-meta a", has_text="thread ↗").count() == 1
    assert reply_art.locator(".td-meta a", has_text="thread ↗").count() == 1


def test_screenshots_all_six_tabs_1920(harness):
    """Screenshot inventory: one full-viewport PNG per product tab at 1920x1080,
    kept with the scouting-wire completion report. Console and page errors stay
    clean across all six navigations."""
    page = harness.page
    out = Path(__file__).resolve().parents[1] / "output" / "playwright" / "scouting-wire"
    out.mkdir(parents=True, exist_ok=True)

    issues: list[str] = []
    page.on("console", lambda m: issues.append(f"{m.type}: {m.text}") if m.type in ("error", "warning") else None)
    page.on("pageerror", lambda e: issues.append(str(e)))

    targets = {}
    for tab in NAV_TABS:
        page.goto(f"{harness.base}/?tab={tab}", wait_until="networkidle")
        page.wait_for_function(READY, timeout=10000)
        target = out / f"final-1920-{tab.lower()}.png"
        page.screenshot(path=str(target), full_page=False)
        targets[tab] = target

    for tab, target in targets.items():
        assert target.exists(), f"missing screenshot for {tab}: {target}"
        size = target.stat().st_size
        assert size > 10_000, f"{target} too small to be real evidence: {size} bytes"
    assert issues == [], issues