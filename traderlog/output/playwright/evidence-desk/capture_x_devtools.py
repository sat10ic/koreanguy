"""One-shot DevTools capture of the 8 roster handles' posts + replies.

Attaches READ-ONLY to the user's Chrome (debug port 9222, separate
user-data-dir copy launched by the orchestrator). Navigates ONLY
https://x.com/<handle>/with_replies for the approved handles, scrolls the
timeline, extracts tweet articles from the DOM, and writes a provisional
checkpoint JSON in the exact schema the strict importer validates
(ingest/provisional_import.py). No cookies/credentials/localStorage are read
programmatically; page navigation uses the browser's own session. No writes
back to X (no likes/replies/posts). Scratch tooling - deleted at wave close.

Usage: python capture_x_devtools.py <out.json>
"""
from __future__ import annotations

import json
import re
import sys
import time
from typing import Any
from urllib.parse import urlparse, parse_qs

from playwright.sync_api import sync_playwright

CDP = "http://127.0.0.1:9222"
ROSTER = [
    "iManasArora",
    "Fastzonetrader",
    "tradinghustlr",
    "VCPSwing",
    "StocksNerd",
    "ChartistEdge",
    "iArpanK",
    "mystocks_in",
    "rpmrpm4",
    "thechartist26",
    "SakatasHomma",
    "Trading4Bucks",
    "wealthexpress21",
    "Setups_Swing",
]
SCROLLS = 6
WAIT = 2.4
STATUS_RE = re.compile(r"/status/(\d{15,25})")


def norm_media(url: str) -> str:
    """Approved media host only; images upgraded to orig size, query kept."""
    p = urlparse(url)
    if p.hostname == "pbs.twimg.com":
        q = parse_qs(p.query)
        q["name"] = ["orig"]
        if "format" not in q:
            q["format"] = ["jpg"]
        from urllib.parse import urlencode

        return f"https://pbs.twimg.com{p.path}?{urlencode(q, doseq=True)}"
    if p.hostname == "video.twimg.com":
        return f"https://video.twimg.com{p.path}"
    return url


def extract_article(art: dict, roster_handle: str) -> dict[str, Any] | None:
    """One article -> checkable record fields. Conservative: relationship only
    when the parent anchor AND parent's own article permalink prove ancestry."""
    text_el = art.get("tweetText")
    text = " ".join((text_el or "").split()) if text_el else ""
    own = art.get("ownStatusId")
    if not own:
        return None
    record: dict[str, Any] = {
        "post_id": own,
        "handle": roster_handle,
        "url": f"https://x.com/{roster_handle}/status/{own}",
        "text": text,
        "posted_at": art.get("datetime") or "",
        "media_urls": [norm_media(u) for u in art.get("media", [])],
        "surfaces": ["profile_replies"],
    }
    if art.get("isPinned"):
        record["is_pinned"] = True
    # Relationship: ONLY when the reply-parent anchor is present and the same
    # timeline also rendered the parent article whose OWN id equals the anchor
    # (that proves parent == thread root; nothing deeper is provable here).
    parent = art.get("replyParentId")
    root_ids = art.get("onPageRootIds", set())
    if parent and own != parent and parent in root_ids:
        record["conversation_id"] = parent
        record["in_reply_to"] = parent
        record["ordered_status_ids"] = [parent, own]
        record["relationship_basis"] = "dom:reply-anchor-to-on-page-root"
    return record


def handle_lower(roster_handle: str, seen: dict[str, str]) -> str:
    return roster_handle


# Posts tab (top-level posts) + Replies tab. Reposts are excluded: the tab may
# show re-posted tweets whose text belongs to OTHER authors — attributing them
# to the roster handle would corrupt the record.
TABS = ["", "/with_replies"]


def is_repost(art) -> bool:
    ctx = art.locator('[data-testid="socialContext"]').first
    if ctx.count():
        txt = (ctx.text_content() or "").lower()
        if "reposted" in txt or "reposted by" in txt:
            return True
    label = art.locator("span").first.text_content() if art.locator("span").first.count() else None
    return bool(label and "reposted" in (label or "").lower())


def main() -> int:
    out_path = sys.argv[1] if len(sys.argv) > 1 else "x_capture.json"
    source: dict[str, dict[str, Any]] = {h: {} for h in ROSTER}
    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp(CDP)
        ctx = browser.contexts[0]
        for roster_handle in ROSTER:
            for tab in TABS:
                page = ctx.new_page()
                try:
                    page.goto(f"https://x.com/{roster_handle}{tab}", timeout=60000)
                    page.wait_for_timeout(3500)
                    # Login wall check: no tweets after a beat means not authenticated.
                    n = page.locator('article[data-testid="tweet"]').count()
                    if n == 0 and page.locator('a[href="/i/flow/login"]').count() > 0:
                        print(f"!! {roster_handle}{tab}: login wall - session missing")
                        page.close()
                        continue
                    for _ in range(SCROLLS):
                        page.mouse.wheel(0, 9000)
                        page.wait_for_timeout(int(WAIT * 1000))
                    page.wait_for_timeout(2000)
                    articles = page.locator('article[data-testid="tweet"]')
                    total = articles.count()
                    # X throttles rapid loads; one gentle retry for empty tabs.
                    if total == 0:
                        print(f"{roster_handle}{tab}: 0 articles, retrying once")
                        page.wait_for_timeout(5000)
                        for _ in range(SCROLLS):
                            page.mouse.wheel(0, 9000)
                            page.wait_for_timeout(int(WAIT * 1000))
                        page.wait_for_timeout(2000)
                        total = articles.count()
                    print(f"{roster_handle}{tab or '/<posts>'}: {total} articles on page")
                    # First pass: on-page root ids = articles without a reply
                    # parent anchor (candidate thread roots).
                    raw: list[dict[str, Any]] = []
                    for i in range(total):
                        art = articles.nth(i)
                        if is_repost(art):
                            continue
                        time_el = art.locator("time").first
                        dt = time_el.get_attribute("datetime") or ""
                        anch = art.locator(
                            'a[href*="/status/"]:not([aria-label*="repl"])'
                        )
                        own = None
                        tlink = time_el.evaluate(
                            "el => el.closest('a')?.getAttribute('href') || ''"
                        ) if time_el.count() else ""
                        if tlink:
                            m = STATUS_RE.search(tlink)
                            if m:
                                own = m.group(1)
                        if not own:
                            links = anch.evaluate_all(
                                "els => els.map(e => e.getAttribute('href'))"
                            )
                            for lk in links:
                                m = STATUS_RE.search(lk or "")
                                if m:
                                    own = m.group(1)
                                    break
                        parent = None
                        rep = art.locator('a[href*="/status/"][aria-label*="eply"], a[href*="/status/"][aria-label*="eplying"]').first
                        if rep.count():
                            href = rep.get_attribute("href") or ""
                            m = STATUS_RE.search(href)
                            if m:
                                parent = m.group(1)
                        media = []
                        imgs = art.locator('img[src*="pbs.twimg.com"]')
                        for j in range(imgs.count()):
                            src = imgs.nth(j).get_attribute("src")
                            if src and src not in media:
                                media.append(src)
                        vids = art.locator('video source[src*="video.twimg.com"]')
                        for j in range(vids.count()):
                            src = vids.nth(j).get_attribute("src")
                            if src and src not in media:
                                media.append(src)
                        text_el = art.locator('[data-testid="tweetText"]').first
                        txt = text_el.text_content() if text_el.count() else ""
                        pinned = "Pinned" in (art.inner_text()[:400] if art.count() else "")
                        raw.append({
                            "own": own,
                            "parent": parent,
                            "datetime": dt,
                            "text": txt or "",
                            "media": media,
                            "isPinned": bool(pinned),
                        })
                    root_ids = {
                        r["own"] for r in raw
                        if r["own"] and not r["parent"]
                    }
                    for r in raw:
                        rec = extract_article(
                            {
                                "ownStatusId": r["own"],
                                "replyParentId": r["parent"],
                                "datetime": r["datetime"],
                                "tweetText": r["text"],
                                "media": r["media"],
                                "isPinned": r["isPinned"],
                                "onPageRootIds": root_ids,
                            },
                            roster_handle,
                        )
                        if rec and rec["post_id"] not in source[roster_handle]:
                            source[roster_handle][rec["post_id"]] = rec
                except Exception as exc:  # noqa: BLE001 - one handle/tab must not kill the run
                    print(f"!! {roster_handle}{tab}: {type(exc).__name__}: {exc}")
                finally:
                    page.close()
                    time.sleep(0.4)
    # Prune empty handles so the importer only sees captured ones.
    source = {h: v for h, v in source.items() if v}
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(source, fh, ensure_ascii=False, indent=1)
    total_posts = sum(len(v) for v in source.values())
    print(f"wrote {out_path}: {len(source)} handles, {total_posts} posts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())