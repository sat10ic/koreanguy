"""Scouting×wire acceptance tests (HANDOFF_scouting_wire_2026-08-24, S10).

These encode the wave's own design assertions on the rebuilt UI, on a
DISPOSABLE database only: banded TODAY news (fixed order, Removed lifecycle,
computed banding, Rule 3 accent scoping, Rule 1 glosses), the SYMBOL landing
page (chart only for a validated symbol), TRADERS honest "too few" states with
empty trader_style, the ⌘K command bar, and MARKET (hero Stat with its age,
ribbon legend in words, NO caution block this wave -- XP is fixed).

The production traderlog/data/traderlog.db is never opened: api_app.connect is
monkeypatched to the tmp_path database before the server starts (same pattern
as test_pc_layout.py / test_browser_review.py).
"""
from __future__ import annotations

import hashlib
import json
import re
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
# Real archived images, served read-only through /api/media (see test_pc_layout
# for the containment rationale -- copied so this file's fixture is identical).
_WIDE_IMAGE = "2090713569793126757_0.jpg"
_THUMB_IMAGE = "2090713569793126757_1.jpg"

# The ONE accent value (tokens.css --risk). Chromium computes it to this rgb.
_RISK_RGB = "rgb(198, 242, 78)"

# Rule-1 gloss sentence starters for money-moved rows (copy appendix).
_MONEY_GLOSS = (
    "Put money|Added|Booked|Took profit|Stated a stop|Moved the stop"
)


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


def _post(
    conn,
    post_id: str,
    handle: str,
    text: str,
    *,
    ts: str = "2026-08-06T10:00:00+00:00",
    ts_ist: str = "2026-08-06T15:30:00+05:30",
    conversation_id: str | None = None,
    in_reply_to: str | None = None,
    kind: str | None = None,
    symbols: list[str] | None = None,
    deleted_at: str | None = None,
) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO traders (handle, active, is_mock, ingested_at) VALUES (?,?,?,?)",
        (handle, 1, 0, now_iso()),
    )
    conn.execute(
        "INSERT INTO posts (post_id,handle,conversation_id,in_reply_to,ts_utc,ts_ist,"
        "text,url,fetched_at,deleted_at,is_mock,ingested_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            post_id, handle, conversation_id, in_reply_to, ts, ts_ist, text,
            f"https://x.com/{handle}/status/{post_id}", now_iso(), deleted_at, 0, now_iso(),
        ),
    )
    if kind is not None:
        conn.execute(
            "INSERT INTO post_class (post_id,kind,confidence,symbols,is_mock,ingested_at)"
            " VALUES (?,?,?,?,?,?)",
            (post_id, kind, 0.9, json.dumps(symbols or []), 0, now_iso()),
        )


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
    """Disposable DB + real uvicorn server + one fresh 1920x1080 page. Seeded
    exactly like test_pc_layout: alice/ALPHA open position (root entry at 100)
    plus the TWO real archived post_media rows (read-only from data/media)."""
    import uvicorn

    path = tmp_path / "traderlog.db"
    conn = init_db(path)
    position_id = _open_position(conn)

    for idx, image in ((0, _WIDE_IMAGE), (1, _THUMB_IMAGE)):
        media = _MEDIA / image
        assert media.exists(), f"archived image missing from data/media: {image}"
        sha = hashlib.sha256(media.read_bytes()).hexdigest()
        conn.execute(
            "INSERT INTO post_media (post_id, idx, local_path, sha256, media_type, is_mock, ingested_at)"
            " VALUES (?,?,?,?,?,?,?)",
            ("root", idx, image, sha, "image", 0, now_iso()),
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


# ---------------------------------------------------------------------------
# 1. Today bands: fixed order, data-band attributes, and the Removed band
#    lifecycle (absent until a real deletion is caught; then struck + kept
#    with the protected note).
# ---------------------------------------------------------------------------


def test_today_bands_fixed_order_and_removed_band_lifecycle(harness):
    conn = harness.conn
    # money: the fixture's root post (trade_event WITH event.price).
    _post(conn, "watch", "alice", "FCL is coiling under 1,240",
          kind="watch_idea", symbols=["FCL"])
    _post(conn, "noise", "alice", "coffee and charts tonight", kind="noise")
    conn.commit()

    page = harness.page
    page.goto(f"{harness.base}/?tab=TODAY", wait_until="networkidle")
    page.wait_for_function(
        "() => document.querySelectorAll('.td-band').length === 3", timeout=10000
    )
    bands = page.evaluate(
        "() => [...document.querySelectorAll('.td-band')].map(b => b.getAttribute('data-band'))"
    )
    assert bands == ["money", "watch", "background"], bands
    kickers = page.evaluate(
        "() => [...document.querySelectorAll('.td-band .td-kicker')].map(k => k.textContent.trim())"
    )
    assert kickers == ["MONEY MOVED", "NAMES TO WATCH", "BACKGROUND"], kickers
    # Every band carries its one-line WHY (a reason, not a description).
    assert page.locator(".td-band .td-band-why").count() == 3
    # No deletes -> no Removed band.
    assert page.locator(".td-band[data-band='removed']").count() == 0

    # A real deletion is caught later: the Removed band appears, struck and
    # kept, with the protected note, and the web link is dropped.
    _post(conn, "del", "alice", "I will not chase this",
          ts="2026-08-05T09:00:00+00:00", ts_ist="2026-08-05T14:30:00+05:30",
          deleted_at="2026-08-05T15:00:00+05:30")
    conn.commit()
    page.reload(wait_until="networkidle")
    removed = page.locator(".td-band[data-band='removed']")
    removed.wait_for(state="attached", timeout=10000)
    assert removed.count() == 1
    assert removed.locator(".td-row").count() == 1
    row = removed.locator(".td-row")
    assert row.locator(".td-bandlabel").inner_text().strip() == "REMOVED"
    assert row.evaluate("el => el.classList.contains('td-row-deleted')")
    # Struck + dimmed: line-through computed on the verbatim text.
    assert "line-through" in row.locator(".td-text").evaluate(
        "el => getComputedStyle(el).textDecorationLine"
    )
    # Protected copy survives verbatim (copy appendix #1).
    note = row.locator(".td-deleted-note").inner_text()
    assert "removed by its author. Kept on purpose" in note
    assert "traders delete losers" in note
    # The gloss says Up HH:MM, gone by HH:MM.
    gloss = row.locator(".td-gloss").inner_text()
    assert "gone by" in gloss
    # Deleted rows keep the web link out.
    assert row.locator(".td-meta").count() == 0
    # The main three bands still render in the same fixed order.
    bands = page.evaluate(
        "() => [...document.querySelectorAll('.td-band')].map(b => b.getAttribute('data-band'))"
    )
    assert bands == ["money", "watch", "background", "removed"], bands


# ---------------------------------------------------------------------------
# 2. Banding is computed, never editorial (Rule 2): trade_event WITH a stated
#    price -> Money moved; watch_idea -> Names to watch; everything the rule
#    cannot place (noise, theme, a trade_event with no stated price) ->
#    Background.
# ---------------------------------------------------------------------------


def test_today_banding_rules_assign_every_post(harness):
    conn = harness.conn
    _post(conn, "watch", "alice", "WATCH FCL above 1,240",
          kind="watch_idea", symbols=["FCL"])
    _post(conn, "noise", "alice", "buying milk", kind="noise")
    _post(conn, "theme", "alice", "semis are the new defensives", kind="theme")
    # A trade_event with NO stated price: money requires event.price, so it
    # must fall to Background rather than pretending to be a booking.
    _post(conn, "vague", "alice", "added some FCL", kind="trade_event", symbols=["FCL"])
    conn.commit()

    page = harness.page
    page.goto(f"{harness.base}/?tab=TODAY", wait_until="networkidle")
    page.wait_for_function(
        "() => document.querySelectorAll('article.td-row').length === 5", timeout=10000
    )
    counts = page.evaluate(
        """() => {
          const out = {};
          for (const b of document.querySelectorAll('.td-band')) {
            out[b.getAttribute('data-band')] = b.querySelectorAll('.td-row').length;
          }
          return out;
        }"""
    )
    # root (money) + watch + noise/theme/vague (background).
    assert counts == {"money": 1, "watch": 1, "background": 3}, counts
    # Every row's data-band attribute agrees with the computed rule.
    assigned = page.evaluate(
        """() => [...document.querySelectorAll('article.td-row')]
          .map(r => ({ text: r.querySelector('.td-text').textContent, band: r.getAttribute('data-band') }))"""
    )
    by_text = {row["text"]: row["band"] for row in assigned}
    assert by_text["LONG ALPHA at 100"] == "money"
    assert by_text["WATCH FCL above 1,240"] == "watch"
    assert by_text["buying milk"] == "background"
    assert by_text["semis are the new defensives"] == "background"
    assert by_text["added some FCL"] == "background"


# ---------------------------------------------------------------------------
# 3. Rule 3 accent scoping: --risk marks money that was risked and nothing
#    else. Present on every money row, absent from every other band, and the
#    MARKET screen (market internals never involve anyone risking money)
#    renders zero risk-usage anywhere.
# ---------------------------------------------------------------------------


def test_risk_accent_scoped_to_money_rows_and_absent_on_market(harness):
    conn = harness.conn
    _post(conn, "watch", "alice", "FCL coiling", kind="watch_idea", symbols=["FCL"])
    _post(conn, "noise", "alice", "rabbit hole thread", kind="noise")
    conn.commit()

    page = harness.page
    page.goto(f"{harness.base}/?tab=TODAY", wait_until="networkidle")
    page.wait_for_function(
        "() => document.querySelectorAll('.td-band').length === 3", timeout=10000
    )

    risk = page.evaluate(
        """() => {
          const marks = [...document.querySelectorAll('.td-risk-mark')];
          return {
            total: marks.length,
            outsideMoney: marks.filter(m => m.closest('.td-row').getAttribute('data-band') !== 'money').length,
            moneyRows: document.querySelectorAll('.td-band[data-band="money"] .td-row').length,
            moneyRowsWithoutMark: [...document.querySelectorAll('.td-band[data-band="money"] .td-row')]
              .filter(r => !r.querySelector('.td-risk-mark')).length,
            nonMoneyMarks: document.querySelectorAll('.td-row:not([data-band="money"]) .td-risk-mark').length,
            color: marks.length ? getComputedStyle(marks[0]).backgroundColor : null,
          };
        }"""
    )
    assert risk["total"] == 1, risk
    assert risk["color"] == _RISK_RGB, risk
    assert risk["outsideMoney"] == 0, risk
    assert risk["moneyRows"] == 1, risk
    assert risk["moneyRowsWithoutMark"] == 0, risk
    assert risk["nonMoneyMarks"] == 0, risk

    # MARKET: no risk class, no risk-computed color anywhere in the rendered
    # DOM (the accent means money was risked; internals never do that).
    page.goto(f"{harness.base}/?tab=MARKET", wait_until="networkidle")
    page.wait_for_function(
        "() => ![...document.querySelectorAll('main .empty')]"
        ".some(e => e.textContent.includes('loading'))",
        timeout=10000,
    )
    market = page.evaluate(
        f"""() => {{
          const riskEls = [...document.querySelectorAll('main *')].filter(el => {{
            const cs = getComputedStyle(el);
            return [cs.backgroundColor, cs.color, cs.borderColor, cs.outlineColor]
              .includes('{_RISK_RGB}');
          }});
          return {{
            riskClasses: document.querySelectorAll('main [class*="risk" i]').length,
            riskMarkers: document.querySelectorAll('.td-risk-mark, .risk-dot').length,
            riskColored: riskEls.length,
          }};
        }}"""
    )
    assert market == {"riskClasses": 0, "riskMarkers": 0, "riskColored": 0}, market


# ---------------------------------------------------------------------------
# 4. Rule 1 on TODAY: no bare numeral without a meaning. Money rows carry a
#    plain-English gloss sentence; digits never appear as bare text nodes
#    outside .mono (except the verbatim quote, which is the trader's own).
# ---------------------------------------------------------------------------


def test_today_no_numeral_without_meaning(harness):
    conn = harness.conn
    # A second money row with a different event kind: a partial exit with a
    # stated price exercises the "Took profit" gloss too.
    position_id = conn.execute(
        "SELECT position_id FROM positions WHERE root_post_id='root'"
    ).fetchone()[0]
    _post(conn, "took", "alice", "taking half off ALPHA",
          ts="2026-08-07T09:00:00+00:00", ts_ist="2026-08-07T14:30:00+05:30",
          kind="trade_event", symbols=["ALPHA"])
    conn.execute(
        "INSERT INTO position_events (position_id, post_id, kind, price, qty_pct, stated_at,"
        " seq, is_mock, ingested_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (position_id, "took", "partial_exit", 95, 0.5,
         "2026-08-07T14:30:00+05:30", 7, 0, now_iso()),
    )
    conn.commit()

    page = harness.page
    page.goto(f"{harness.base}/?tab=TODAY", wait_until="networkidle")
    page.wait_for_function(
        "() => document.querySelectorAll('article.td-row').length === 2", timeout=10000
    )

    # Every row renders a gloss sentence (Rule 1 lives in the gloss).
    assert page.locator(".td-row .td-gloss").count() == page.locator(".td-row").count()

    # Money rows state what happened in words -- never a bare number headline.
    glosses = page.evaluate(
        """() => [...document.querySelectorAll('.td-band[data-band="money"] .td-row .td-gloss')]
          .map(g => g.textContent)"""
    )
    assert len(glosses) == 2, glosses
    for g in glosses:
        assert re.search(_MONEY_GLOSS, g), (glosses, g)

    # No bare numeral: digits inside a row must sit inside a .mono construct
    # (times, prices, thread positions, counts) --- the one exception is the
    # verbatim post text, which quotes the trader and is never paraphrased.
    offenders = page.evaluate(
        """() => {
          const out = [];
          for (const row of document.querySelectorAll('.td-row')) {
            for (const el of row.querySelectorAll(
                '.td-bandlabel, .td-gloss, .td-time, .td-thread-pos, .td-meta')) {
              [...el.childNodes].forEach((n) => {
                if (n.nodeType === 3 && /\\d/.test(n.textContent || '')
                    && !n.parentElement.closest('.mono')) {
                  out.push(`${row.getAttribute('data-band')}: ${(n.textContent || '').trim()}`);
                }
              });
            }
          }
          return out;
        }"""
    )
    assert offenders == [], offenders


# ---------------------------------------------------------------------------
# 5. SYMBOL landing page: candles render only for a symbol validated against
#    daily_prices (bhavcopy NSE EQ); a nonsense symbol renders the honest
#    labelled empty state -- never a chart of an invalid instrument.
# ---------------------------------------------------------------------------


def test_symbol_page_validated_chart_and_nonsense_empty_state(harness):
    conn = harness.conn
    now = now_iso()
    for i, date in enumerate(("2026-08-12", "2026-08-13", "2026-08-14")):
        conn.execute(
            "INSERT INTO daily_prices (symbol, trade_date, open, high, low, close, volume, source, ingested_at)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            ("DIXON", date, 100 + i, 106 + i, 99 + i, 104 + i, 1000, "bhavcopy", now),
        )
    conn.commit()

    page = harness.page
    page.goto(f"{harness.base}/?tab=SYMBOL&symbol=DIXON", wait_until="networkidle")
    page.wait_for_selector(".symbol-chart", timeout=10000)
    assert page.locator(".symbol-chart").count() == 1
    assert page.locator(".symbol-title").inner_text().strip() == "DIXON"
    candles_panel = page.locator(".panel", has_text="candles").first
    assert candles_panel.locator(".chart-empty").count() == 0

    # Nonsense symbol: no candles, the honest labelled one-line empty state.
    page.goto(f"{harness.base}/?tab=SYMBOL&symbol=ZZZZZX", wait_until="networkidle")
    page.wait_for_selector(".chart-empty", timeout=10000)
    assert page.locator(".symbol-chart").count() == 0
    empty_text = page.locator(".chart-empty").first.inner_text()
    assert "Nothing in the corpus for this symbol" in empty_text, empty_text


# ---------------------------------------------------------------------------
# 6. TRADERS with empty trader_style: every metric row honestly shows the em
#    dash + "too few" (never a percentage), and the protected one-liner
#    renders verbatim beneath the ranking.
# ---------------------------------------------------------------------------


def test_traders_empty_style_shows_too_few_everywhere(harness):
    conn = harness.conn
    conn.execute(
        "INSERT OR IGNORE INTO traders (handle, active, is_mock, ingested_at) VALUES (?,?,?,?)",
        ("bob", 1, 0, now_iso()),
    )
    conn.commit()

    page = harness.page
    page.goto(f"{harness.base}/?tab=TRADERS", wait_until="networkidle")
    page.wait_for_selector(".traders-rank", timeout=10000)

    assert page.locator(".q-row").count() == 2  # alice + bob, roster size
    assert page.locator(".q-row .q-value", has_text="— too few").count() == 2
    # "too few" shows up on the ranked rows AND every roster rate cell (win,
    # preach) -- at least once per roster trader.
    body_text = page.locator("main").inner_text()
    assert body_text.count("— too few") >= 2, body_text
    # Verbatim one-liner under the ranking (copy appendix).
    assert (
        page.get_by_text(
            "A dim bar means too little history to lean on. A dash means we won't guess.",
            exact=True,
        ).count()
        == 1
    )
    # Roster rate cells: 2 traders x 2 rate columns (win, preach).
    assert page.locator(".traders-roster td", has_text="— too few").count() == 4
    # The empty-style profile states plainly that nothing is guessed.
    assert page.locator(".traders-future").count() == 1


# ---------------------------------------------------------------------------
# 7. ⌘K command bar: Ctrl+K opens the overlay, typing a handle filters it,
#    Enter navigates to TRADERS with that handle preselected, Escape closes.
# ---------------------------------------------------------------------------


def test_command_bar_ctrl_k_opens_filters_navigates_and_escape_closes(harness):
    page = harness.page
    page.goto(f"{harness.base}/?tab=TODAY", wait_until="networkidle")

    page.keyboard.press("Control+k")
    page.wait_for_selector(".command-bar", timeout=5000)
    assert page.locator(".command-bar").count() == 1

    # Type the trader handle; the palette filters to @alice (directory loads
    # lazily on first open).
    page.keyboard.type("alice")
    item = page.locator(".command-bar-item", has_text="alice")
    item.wait_for(state="attached", timeout=5000)
    page.keyboard.press("Enter")

    # The palette closed and navigation went to TRADERS with the handle
    # preselected (URL is the deep link; the profile renders).
    page.wait_for_selector(".traders-rank", timeout=10000)
    assert page.locator(".command-bar").count() == 0
    assert "tab=TRADERS" in page.url, page.url
    assert "handle=alice" in page.url, page.url
    assert page.locator(".traders-future").count() >= 1  # alice profile rendered

    # Escape closes the overlay on the next open.
    page.keyboard.press("Control+k")
    page.wait_for_selector(".command-bar", timeout=5000)
    page.keyboard.press("Escape")
    page.wait_for_selector(".command-bar", state="detached", timeout=5000)


# ---------------------------------------------------------------------------
# 8. MARKET: no §8 caution block this wave (XP is fixed), the hero Stat
#    renders with its plain-English meaning AND its age, and the day-colour
#    ribbon legend speaks in words.
# ---------------------------------------------------------------------------


def test_market_hero_age_ribbon_legend_and_no_caution(harness):
    conn = harness.conn
    now = now_iso()
    # Two sessions so the ribbon has cells and the A/D line has a run.
    conn.execute(
        "INSERT INTO breadth_daily (trade_date, advances, declines, up_4pct, down_4pct, ingested_at)"
        " VALUES (?,?,?,?,?,?)",
        ("2026-08-13", 90, 110, 8.2, 4.5, now),
    )
    conn.execute(
        "INSERT INTO breadth_daily (trade_date, advances, declines, up_4pct, down_4pct, ingested_at)"
        " VALUES (?,?,?,?,?,?)",
        ("2026-08-14", 120, 80, 7.5, 3.9, now),
    )
    for date, xp, color in (("2026-08-13", 8.2, "RED"), ("2026-08-14", 7.5, "GREEN")):
        conn.execute(
            "INSERT INTO regime_daily (trade_date, xp_value, xp_z_state, xp_band,"
            " mbi_day_color, warning_day, is_mock, ingested_at) VALUES (?,?,?,?,?,?,?,?)",
            (date, xp, 0.0, "LOW", color, 0, 0, now),
        )
    conn.commit()

    page = harness.page
    page.goto(f"{harness.base}/?tab=MARKET", wait_until="networkidle")
    page.wait_for_selector(".mk-hero", timeout=10000)

    # Hero Stat: the number AND its plain-English meaning (Rule 1) AND its age.
    assert page.locator(".mk-hero .stat-value").inner_text().strip() == "7.5"
    assert "Only a few stocks are pushing higher" in page.locator(".mk-hero .stat-gloss").inner_text()
    age = page.locator(".mk-hero-age").inner_text()
    assert "as of" in age and "2026-08-14" in age, age

    # Ribbon legend in words, never hue-only.
    assert page.locator(".mk-ribbon").count() == 1
    legend = page.locator(".mk-legend").inner_text()
    assert "most stocks rose" in legend
    assert "roughly even" in legend
    assert "most fell" in legend

    # XP is fixed in this wave -> no §8 caution block anywhere on MARKET.
    assert "Don't rely on this number" not in page.locator("main").inner_text()