"""INS-1 RADAR UI acceptance against a disposable database at 1920x1080 only."""
from __future__ import annotations

import socket
import threading
import time
import urllib.request
from pathlib import Path

import pytest

from traderlog.api import app as api_app
from traderlog.db import connect, init_db, now_iso


_DIST = Path(__file__).resolve().parents[1] / "ui" / "dist"


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
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=1) as res:
                if res.status == 200:
                    return
        except Exception as exc:  # noqa: BLE001 - poll until the server is ready
            last = exc
            time.sleep(0.1)
    raise AssertionError(f"test API server not ready within {timeout}s: {last!r}")


class Harness:
    def __init__(self, conn, port: int, page):
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


def _insert_post(conn, post_id: str, handle: str, text: str, symbols: str) -> None:
    now = now_iso()
    conn.execute(
        "INSERT INTO posts (post_id, handle, ts_utc, ts_ist, text, url, fetched_at, is_mock, ingested_at) "
        "VALUES (?, ?, '2026-08-23T09:00:00+00:00', '2026-08-23T14:30:00+05:30', ?, ?, ?, 0, ?)",
        (post_id, handle, text, f"https://x.com/{handle.lstrip('@')}/status/{post_id}", now, now),
    )
    conn.execute(
        "INSERT INTO post_class (post_id, kind, confidence, symbols, is_mock, ingested_at) "
        "VALUES (?, 'watch_idea', 0.91, ?, 0, ?)",
        (post_id, symbols, now),
    )


@pytest.fixture
def harness(tmp_path, monkeypatch, browser):
    import uvicorn

    path = tmp_path / "traderlog.db"
    conn = init_db(path)
    now = now_iso()
    for handle in ("@alpha", "@bravo", "@charlie"):
        conn.execute(
            "INSERT INTO traders (handle, active, is_mock, ingested_at) VALUES (?, 1, 0, ?)",
            (handle, now),
        )
    _insert_post(conn, "fcl-alpha", "@alpha", "FCL exact evidence one", '["FCL"]')
    _insert_post(conn, "fcl-bravo", "@bravo", "FCL exact evidence two", '["FCL"]')
    _insert_post(conn, "beta-charlie", "@charlie", "BETA one-trader evidence", '["BETA"]')
    _insert_post(conn, "ghost-alpha", "@alpha", "GHOST missing NSE coverage", '["GHOST"]')
    _insert_post(conn, "ghost-bravo", "@bravo", "GHOST second missing coverage", '["GHOST"]')
    _insert_post(conn, "broken-symbols", "@charlie", "Malformed symbols are coverage debt", "{broken")
    conn.execute(
        "INSERT INTO daily_prices (symbol, trade_date, close, source, ingested_at) "
        "VALUES ('FCL', '2026-08-23', 100, 'bhavcopy', ?)",
        (now,),
    )
    conn.execute(
        "INSERT INTO daily_prices (symbol, trade_date, close, source, ingested_at) "
        "VALUES ('BETA', '2026-08-23', 100, 'bhavcopy', ?)",
        (now,),
    )
    conn.commit()

    monkeypatch.setattr(api_app, "connect", lambda: connect(path))
    monkeypatch.setattr(api_app, "_radar_now", lambda: "2026-08-25T12:00:00+00:00")

    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(api_app.app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    _wait_ready(port)

    context = browser.new_context(viewport={"width": 1920, "height": 1080})
    page = context.new_page()
    try:
        yield Harness(conn, port, page)
    finally:
        context.close()
        server.should_exit = True
        thread.join(timeout=5)
        conn.close()
        if thread.is_alive():
            pytest.fail("uvicorn server thread still alive 5s after should_exit")


def _open_radar(harness: Harness, query: str = "?tab=RADAR") -> None:
    harness.page.goto(f"{harness.base}/{query}", wait_until="networkidle")
    harness.page.locator(".radar-workspace").wait_for(state="attached", timeout=5000)


def test_radar_component_behaviors(harness):
    page = harness.page
    radar_requests: list[str] = []
    page.on("request", lambda req: radar_requests.append(req.url) if "/api/radar" in req.url else None)

    _open_radar(harness)

    rows = page.locator("button.radar-row")
    assert rows.count() == 1
    assert rows.first.get_attribute("aria-pressed") == "true"
    assert page.locator(".radar-evidence", has_text="FCL exact evidence one").count() == 1
    assert page.locator(".radar-evidence", has_text="@alpha").count() == 1
    assert page.locator(".radar-evidence a[href='https://x.com/alpha/status/fcl-alpha']").count() == 1

    coverage = page.locator(".radar-coverage").inner_text()
    for label in (
        "Eligible classified posts",
        "Included mentions",
        "Invalid symbol JSON",
        "Invalid symbol values",
        "Invalid timestamps",
        "Invalid handles",
        "Unvalidated mentions",
        "GHOST",
    ):
        assert label in coverage

    page.get_by_role("button", name="7 days").click()
    page.get_by_role("button", name="3 traders").click()
    page.wait_for_function("() => document.querySelector('.radar-zero') !== null")
    assert any("days=7" in url for url in radar_requests), radar_requests
    assert any("min_traders=3" in url for url in radar_requests), radar_requests
    assert page.locator(".radar-zero").count() == 1

    page.get_by_role("button", name="4 traders").click()
    page.wait_for_function("() => document.querySelector('.radar-zero') !== null")
    assert any("min_traders=4" in url for url in radar_requests), radar_requests

    page.goto(f"{harness.base}/?tab=IDEAS", wait_until="networkidle")
    page.locator(".radar-workspace").wait_for(state="attached", timeout=5000)
    assert page.url.endswith("?tab=RADAR")
    assert page.get_by_role("button", name="RADAR").count() == 1
    assert page.get_by_role("button", name="IDEAS").count() == 0


def test_radar_1920_acceptance(harness):
    page = harness.page
    issues: list[str] = []
    bad_responses: list[str] = []
    page.on("console", lambda msg: issues.append(f"{msg.type}: {msg.text}") if msg.type in ("error", "warning") else None)
    page.on("pageerror", lambda exc: issues.append(str(exc)))
    page.on("response", lambda res: bad_responses.append(f"{res.status} {res.url}") if res.status >= 400 else None)

    _open_radar(harness)
    # Add a second ranked row after the first fetch without changing the client payload.
    harness.conn.execute(
        "INSERT INTO posts (post_id, handle, ts_utc, ts_ist, text, url, fetched_at, is_mock, ingested_at) "
        "VALUES ('beta-alpha', '@alpha', '2026-08-23T10:00:00+00:00', '2026-08-23T15:30:00+05:30', "
        "'BETA exact evidence', 'https://x.com/alpha/status/beta-alpha', ?, 0, ?)",
        (now_iso(), now_iso()),
    )
    harness.conn.execute(
        "INSERT INTO post_class (post_id, kind, confidence, symbols, is_mock, ingested_at) "
        "VALUES ('beta-alpha', 'theme', 0.88, '[\"BETA\"]', 0, ?)",
        (now_iso(),),
    )
    harness.conn.commit()
    page.get_by_role("button", name="90 days").click()
    page.wait_for_function("() => document.querySelectorAll('button.radar-row').length === 2")

    rows = page.locator("button.radar-row")
    rows.first.focus()
    rows.first.press("ArrowDown")
    assert rows.nth(1).get_attribute("aria-pressed") == "true"
    assert rows.nth(1).evaluate("element => document.activeElement === element") is True
    # Equal clusters sort symbol-ascending, so ArrowDown moves BETA -> FCL.
    assert page.locator(".radar-rail", has_text="FCL exact evidence one").count() == 1
    rows.nth(1).press("ArrowUp")
    assert rows.first.get_attribute("aria-pressed") == "true"
    assert rows.first.evaluate("element => document.activeElement === element") is True

    geometry = page.evaluate(
        """() => ({
          pageWidth: Math.round(document.querySelector('.page').getBoundingClientRect().width),
          pageX: Math.round(document.querySelector('.page').getBoundingClientRect().x),
          documentWidth: document.documentElement.scrollWidth,
          overflowingRegions: [...document.querySelectorAll('.radar-region')]
            .filter(region => region.scrollWidth > region.clientWidth + 1).length,
        })"""
    )
    assert geometry == {
        "pageWidth": 1680,
        "pageX": 120,
        "documentWidth": 1920,
        "overflowingRegions": 0,
    }, geometry
    assert issues == [], issues
    assert bad_responses == [], bad_responses
