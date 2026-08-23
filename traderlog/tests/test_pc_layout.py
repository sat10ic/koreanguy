"""W3c 1920x1080 PC layout acceptance (HANDOFF_W3c_pc_ui_recovery.md).

Every test runs against a disposable database on a free localhost port, at a
real-browser 1920x1080 viewport. The production database is never opened; the
ONE read-only touch of production material is a ``post_media`` row pointing
at the real archived 1709px-wide holdings image, served through the real
``/api/media`` path -- the exact intrinsic-size hazard the handoff's
containment rules exist for. The file is read, never modified.

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
