"""Browser acceptance tests for the TODAY review flow (scouting×wire 2026-08-24).

The FEED review flow moved to the TODAY screen unchanged in behaviour: the
queue sits ABOVE the bands ("work the human owes the tool"), one decision at a
time, same /api/review/{id} POST, in-session badge refresh. The selectors
updated to the new furniture (.review-item/.review-q/.btn-yes/.btn-no on the
queue; the accepted exit event surfaces as a MONEY MOVED band row with the
plain-English gloss instead of the old .event-strip card).

Every test runs against a disposable database seeded exactly like
test_api_review.py / test_link.py and served by the real FastAPI app on a free
localhost port. The production traderlog/data/traderlog.db is never opened:
``api_app.connect`` is monkeypatched to the tmp_path database before the server
starts, and the readiness poll therefore can never fall through to the real
DB_PATH (db.connect also refuses that from inside pytest).

No page reload is part of any assertion: window.__marker survives the whole
decision flow, proving the refresh happens in-session.
"""
from __future__ import annotations

import json
import socket
import threading
import time
import urllib.request
from pathlib import Path

import pytest

from traderlog.api import app as api_app
from traderlog.db import connect, init_db, now_iso
from traderlog.llm.link import route_link_proposal
from traderlog.tests.test_link import _candidate, _open_position, _proposal

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
    """One disposable DB + one uvicorn server + one fresh browser page."""

    def __init__(self, conn, position_id: str, port: int, page):
        self.conn = conn
        self.position_id = position_id
        self.port = port
        self.page = page

    @property
    def base(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def one(self, sql: str, params: tuple = ()):
        return self.conn.execute(sql, params).fetchone()

    def scalar(self, sql: str, params: tuple = ()):
        return self.one(sql, params)[0]


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
    position_id = _open_position(conn)
    _candidate(conn)
    # Below the 0.8 floor: exactly one open review-queue row, no event written.
    queued = route_link_proposal(conn, _proposal(position_id, 0.79))
    assert queued.status == "open"
    assert conn.execute("SELECT COUNT(*) FROM review_queue WHERE status='open'").fetchone()[0] == 1

    # The whole API now serves the disposable DB. Never the production one.
    monkeypatch.setattr(api_app, "connect", lambda: connect(path))

    port = _free_port()
    server = uvicorn.Server(
        uvicorn.Config(api_app.app, host="127.0.0.1", port=port, log_level="warning")
    )
    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()
    _wait_ready(port)

    context = browser.new_context()
    page = context.new_page()
    try:
        yield Harness(conn, position_id, port, page)
    finally:
        context.close()
        server.should_exit = True
        # A daemon uvicorn thread that ignores should_exit is the leading
        # suspect for a one-off flaky teardown; join it and fail loudly
        # instead of leaving it racing the next test's tmp_path cleanup.
        server_thread.join(timeout=5)
        conn.close()
        if server_thread.is_alive():
            pytest.fail("uvicorn server thread still alive 5s after should_exit")


@pytest.fixture
def zero_harness(tmp_path, monkeypatch, browser):
    """Disposable DB with NO positions and NO review items: not a byte of
    _open_position/_candidate seeding, no media, no trader_style rows. The ONE
    seed -- a single trader row -- exists because TRADERS only renders its
    ranked question (and the empty-style profile state) when a roster row
    exists; with zero traders the screen would have no question at all. The
    is_mock flag stays false: real-shaped, disposable data."""
    import uvicorn

    path = tmp_path / "traderlog.db"
    conn = init_db(path)
    conn.execute(
        "INSERT INTO traders (handle, active, is_mock, ingested_at) VALUES (?,?,?,?)",
        ("alice", 1, 0, now_iso()),
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
        yield Harness(conn, None, port, page)
    finally:
        context.close()
        server.should_exit = True
        server_thread.join(timeout=5)
        conn.close()
        if server_thread.is_alive():
            pytest.fail("uvicorn server thread still alive 5s after should_exit")


def _open_feed(harness: Harness):
    # The default route IS TODAY now (App.jsx initialTab); the W3 default-route
    # behaviour is preserved.
    harness.page.goto(f"{harness.base}/", wait_until="networkidle")


# Screen-ready predicate (shared with test_pc_layout): the fetch-backed screen
# has stopped showing the shared Loading placeholder and some content root is
# in the DOM. TODAY has no .panel, so the filters toolbar counts as present.
READY = """() => {
  const loading = [...document.querySelectorAll('main .empty')]
    .some(e => e.textContent.includes('loading'));
  const present = document.querySelectorAll('main .panel, main .td-filters').length > 0;
  return present && !loading;
}"""


# ---------------------------------------------------------------------------
# a. cold load: no console errors, no page errors, no failed requests.
#    This is also the favicon regression test -- a missing favicon logs a 404.
# ---------------------------------------------------------------------------


def test_cold_load_is_clean(harness):
    page = harness.page
    console_errors: list[str] = []
    page_errors: list[str] = []
    bad_responses: list[str] = []
    failed_requests: list[str] = []
    page.on(
        "console",
        lambda msg: console_errors.append(msg.text) if msg.type == "error" else None,
    )
    page.on("pageerror", lambda exc: page_errors.append(str(exc)))
    page.on(
        "response",
        lambda res: bad_responses.append(f"{res.status} {res.url}")
        if res.status >= 400
        else None,
    )
    page.on(
        "requestfailed",
        lambda req: failed_requests.append(f"{req.failure} {req.url}"),
    )

    _open_feed(harness)

    assert console_errors == [], console_errors
    assert page_errors == [], page_errors
    assert bad_responses == [], bad_responses
    assert failed_requests == [], failed_requests


# ---------------------------------------------------------------------------
# b. accept flow: queue shows the item, decision applies, and everything
#    refreshes in the same session (no navigation) -- the accepted standalone
#    event surfaces as a MONEY MOVED band row with the gloss sentence, the
#    queue and badge clear.
# ---------------------------------------------------------------------------


def test_accept_flow_refreshes_in_session(harness):
    page = harness.page
    _open_feed(harness)
    page.wait_for_function(READY, timeout=10000)

    question = harness.one("SELECT question FROM review_queue")["question"]
    assert page.locator(".review-q").count() == 1
    assert page.locator(".review-q").inner_text().strip() == question.strip()
    assert page.locator(".tab-count").inner_text().strip() == "1"

    # Prove no navigation happens across the decision.
    page.evaluate("window.__marker = 1")
    page.locator(".btn-yes").click()

    page.wait_for_selector(".review-item", state="detached", timeout=5000)
    page.wait_for_selector(".tab-count", state="detached", timeout=5000)
    assert page.evaluate("window.__marker") == 1

    # The accepted exit event lands in MONEY MOVED: the row carries the ONE
    # accent use (Rule 3) and the plain-English gloss, not a bare number.
    row = page.locator("article.td-row", has_text="Booked ALPHA at 120")
    row.wait_for(state="attached", timeout=5000)
    assert row.evaluate("el => el.getAttribute('data-band')") == "money"
    assert row.locator(".td-risk-mark").count() == 1
    gloss = row.locator(".td-gloss").inner_text()
    assert "Booked" in gloss and "ALPHA" in gloss and "120" in gloss

    # API response contract, asserted through the DB it wrote.
    assert harness.scalar("SELECT status FROM review_queue") == "accepted"
    assert harness.scalar("SELECT COUNT(*) FROM position_events WHERE post_id='link-post'") == 1
    state = json.loads(harness.one("SELECT state_json FROM positions WHERE position_id=?", (harness.position_id,))[0])
    assert [e["price"] for e in state["exits"]] == [120.0]


# ---------------------------------------------------------------------------
# c. reject flow: item disappears, no money-band row, position untouched.
# ---------------------------------------------------------------------------


def test_reject_flow_leaves_position_unchanged(harness):
    page = harness.page
    _open_feed(harness)
    page.wait_for_function(READY, timeout=10000)

    page.evaluate("window.__marker = 1")
    page.locator(".btn-no").click()

    page.wait_for_selector(".review-item", state="detached", timeout=5000)
    page.wait_for_selector(".tab-count", state="detached", timeout=5000)
    assert page.evaluate("window.__marker") == 1

    # Rejected: the row stays in BACKGROUND (no risk mark -- no money was
    # booked) and its gloss is not a booking sentence.
    row = page.locator("article.td-row", has_text="Booked ALPHA at 120")
    assert row.count() == 1
    assert row.evaluate("el => el.getAttribute('data-band')") == "background"
    assert row.locator(".td-risk-mark").count() == 0
    assert "Booked" not in row.locator(".td-gloss").inner_text()

    assert harness.scalar("SELECT status FROM review_queue") == "rejected"
    assert harness.scalar("SELECT status FROM positions WHERE position_id=?", (harness.position_id,)) == "open"
    assert harness.scalar("SELECT COUNT(*) FROM position_events WHERE post_id='link-post'") == 0
    state = json.loads(harness.one("SELECT state_json FROM positions WHERE position_id=?", (harness.position_id,))[0])
    assert state["exits"] == []


# ---------------------------------------------------------------------------
# d. double-click guard: the decision POST is held in flight inside the page
#    (a fetch wrapper delays the response ~600ms), then a second click is
#    dispatched raw so it reaches the handler even against a disabled button.
#    Whichever layer absorbs it -- the disabled attribute or the handler's
#    pending guard -- exactly ONE POST may leave the page. (A Playwright route
#    handler cannot hold the response here: a blocking sync handler freezes
#    the whole connection, so the second click could not be dispatched.)
# ---------------------------------------------------------------------------


def test_double_click_submits_exactly_one_decision(harness):
    page = harness.page
    page.add_init_script(
        """
        window.__reviewPosts = [];
        const origFetch = window.fetch;
        window.fetch = (...args) => {
          const url = String(args[0]);
          const method = (args[1] && args[1].method) || 'GET';
          if (url.includes('/api/review/') && method === 'POST') {
            window.__reviewPosts.push(url);
            return origFetch(...args).then(
              (resp) => new Promise((resolve) => setTimeout(() => resolve(resp), 600))
            );
          }
          return origFetch(...args);
        };
        """
    )
    _open_feed(harness)
    page.wait_for_function(READY, timeout=10000)

    page.locator(".btn-yes").click()
    page.wait_for_timeout(100)  # pending state is committed; response still held
    # Second click in quick succession, while the first decision is in flight.
    page.evaluate(
        """() => {
          const btn = document.querySelector('.btn-yes');
          btn.dispatchEvent(new MouseEvent('click', { bubbles: true }));
        }"""
    )

    page.wait_for_selector(".review-item", state="detached", timeout=8000)
    assert page.evaluate("window.__reviewPosts.length") == 1
    # And the single decision still applied end to end.
    assert harness.scalar("SELECT status FROM review_queue") == "accepted"
    assert harness.scalar("SELECT COUNT(*) FROM position_events WHERE post_id='link-post'") == 1


# ---------------------------------------------------------------------------
# e. mobile 375x812: no horizontal overflow on TODAY.
# ---------------------------------------------------------------------------


def test_mobile_375_no_horizontal_overflow(harness):
    page = harness.page
    page.set_viewport_size({"width": 375, "height": 812})
    _open_feed(harness)
    overflow = page.evaluate(
        "document.documentElement.scrollWidth - window.innerWidth"
    )
    assert overflow <= 0, f"horizontal overflow of {overflow}px at 375px"


# ---------------------------------------------------------------------------
# f. zero-row desktop (1920x1080): compact states instead of framed
#    empty charts. The disposable DB has no positions, no review items, no
#    media, no style rows -- TRADERS gets exactly one trader seed so its
#    ranked question (and empty-style profile) can exist at all.
# ---------------------------------------------------------------------------


def test_zero_row_screens_show_compact_states_not_framed_charts(zero_harness):
    page = zero_harness.page

    for tab in ["TODAY", "TRADERS", "LEDGER", "IDEAS", "LIBRARY", "MARKET"]:
        page.goto(f"{zero_harness.base}/?tab={tab}", wait_until="networkidle")
        page.wait_for_function(READY, timeout=10000)
        geom = page.evaluate(
            """() => ({
              overflow: document.documentElement.scrollWidth - window.innerWidth,
              svgHeights: [...document.querySelectorAll('main svg')]
                .map(s => Math.round(s.getBoundingClientRect().height)),
              chartWraps: document.querySelectorAll('.chart-wrap').length,
            })"""
        )
        assert geom["overflow"] == 0, (tab, geom)
        # No giant framed empty chart anywhere: every svg that exists is small.
        assert all(h <= 80 for h in geom["svgHeights"]), (tab, geom)
        # LEDGER skips the PositionBars axis entirely when barRows is empty.
        assert geom["chartWraps"] == 0, (tab, geom)

        if tab == "TRADERS":
            # Honest zero-data state (§4.3/§6): every ranked row reads the em
            # dash + "too few" -- never a percentage -- and the verbatim
            # one-liner renders beneath the ranking; the empty-style profile
            # block states plainly that nothing is guessed.
            assert page.locator(".q-row").count() == 1
            assert page.locator(".q-row .q-value", has_text="— too few").count() == 1
            assert (
                page.get_by_text(
                    "A dim bar means too little history to lean on. A dash means we won't guess.",
                    exact=True,
                ).count()
                == 1
            )
            assert page.locator(".traders-future").count() == 1
            assert page.locator(".panel svg").count() == 0
        if tab == "LEDGER":
            assert (
                page.locator(".chart-empty", has_text="No positions reconstructed yet").count() == 1
            )
        if tab == "MARKET":
            # Market is built with XP fixed: the §8 caution block ("Don't rely
            # on this number yet") is gone this wave and must not leak back.
            assert page.locator("main", has_text="Don't rely on this number").count() == 0
            assert page.locator(".mk-hero").count() == 0


def test_desktop_real_shaped_data_note(zero_harness):
    """The disposable DB is real-SHAPED, not mock: /api/health reports
    is_mock false even though every content table is empty -- documents the
    real-versus-disposable data source for the completion report."""
    with urllib.request.urlopen(f"{zero_harness.base}/api/health", timeout=5) as res:
        body = json.loads(res.read())
    assert body["is_mock"] is False, body
    assert body["counts"] == {
        "traders": 1, "posts": 0, "positions": 0, "review_open": 0,
    }, body