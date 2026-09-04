"""Deep, human-paced capture of one handle's timeline, up to `--days` back.

Attaches read-ONLY to the capture Chrome (debug port 9222, separate profile
with the owner's X login). Human-speed pacing (randomized, with pauses) to
avoid automation detection. Extracts tweet articles, dedupes by status id, and
writes a provisional checkpoint JSON in the strict importer's schema.

Usage:
  python extract_manas_deep.py --handle iManasArora --tab posts --days 365 --out manas_year_posts.json [--limit 120]
  python extract_manas_deep.py --handle iManasArora --tab with_replies --days 365 --out manas_year_replies.json [--limit 120]
"""
from __future__ import annotations

import argparse
import json
import random
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlparse

from playwright.sync_api import sync_playwright

CDP = "http://127.0.0.1:9222"
STATUS_RE = re.compile(r"/status/(\d{15,25})")
MANAS = "iManasArora"


def norm_media(url: str) -> str:
    p = urlparse(url)
    if p.hostname == "pbs.twimg.com":
        q = dict(kv.split("=", 1) for kv in (p.query.split("&") if p.query else []))
        q["name"] = "orig"
        q.setdefault("format", "jpg")
        return f"https://pbs.twimg.com{p.path}?{urlencode(q)}"
    if p.hostname == "video.twimg.com":
        return f"https://video.twimg.com{p.path}"
    return url


def extract(art, handle: str, root_author: str) -> dict | None:
    ctx = art.locator('[data-testid="socialContext"]').first
    if ctx.count() and "repost" in (ctx.text_content() or "").lower():
        return None
    time_el = art.locator("time").first
    dt = time_el.get_attribute("datetime") or "" if time_el.count() else ""
    own = None
    tlink = time_el.evaluate("el => el.closest('a')?.getAttribute('href') || ''") if time_el.count() else ""
    m = STATUS_RE.search(tlink)
    if m:
        own = m.group(1)
    if not own:
        for lk in art.locator('a[href*="/status/"]').evaluate_all("els => els.map(e=>e.getAttribute('href'))"):
            sm = STATUS_RE.search(lk or "")
            if sm:
                own = sm.group(1)
                break
    if not own or not dt:
        return None
    text_el = art.locator('[data-testid="tweetText"]').first
    text = " ".join((text_el.text_content() or "").split()) if text_el.count() else ""
    media = []
    for j in range(art.locator('img[src*="pbs.twimg.com"]').count()):
        src = art.locator('img[src*="pbs.twimg.com"]').nth(j).get_attribute("src")
        if src and "/media/" in src and src not in media:
            media.append(norm_media(src))
    for j in range(art.locator('video source[src*="video.twimg.com"]').count()):
        src = art.locator('video source[src*="video.twimg.com"]').nth(j).get_attribute("src")
        if src and src not in media:
            media.append(norm_media(src))
    parent = None
    parent_author = None
    rep = art.locator('a[href*="/status/"][aria-label*="eply"]').first
    if rep.count():
        href = rep.get_attribute("href") or ""
        pm = STATUS_RE.search(href)
        if pm:
            parent = pm.group(1)
        label = (rep.get_attribute("aria-label") or "") + " " + (rep.inner_text() or "")
        m = re.search(r"@([A-Za-z0-9_]+)", label)
        if m:
            parent_author = m.group(1)
    rec = {
        "post_id": own, "handle": handle,
        "url": f"https://x.com/{handle}/status/{own}",
        "text": text, "posted_at": dt, "media_urls": media, "surfaces": ["profile_replies"],
    }
    if parent:
        rec["in_reply_to"] = parent
    if parent_author:
        rec["thread_root_author"] = parent_author
    return rec


def deep(handle: str, tab: str, days: int, out_path: Path, limit: int, self_only: bool) -> dict:
    cutoff = datetime.now(timezone.utc) - __import__("datetime").timedelta(days=days)
    source: dict[str, dict] = {}
    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp(CDP)
        page = browser.contexts[0].new_page()
        try:
            base = f"https://x.com/{handle}"
            url = base if tab in ("", "posts", "status") else f"{base}/{tab}"
            page.goto(url, timeout=90000)
            page.wait_for_timeout(6500)
            # Wait for the timeline to actually render before counting.
            for _ in range(15):
                if page.locator('article[data-testid="tweet"]').count() > 0:
                    break
                page.wait_for_timeout(1500)
            no_progress = 0
            loads = 0
            while loads < limit:
                loads += 1
                # EXTRA human-paced scroll: randomized 4.5-7.5s per wheel, tight
                # article pass only every other scroll burst.
                for _ in range(random.randint(2, 3)):
                    page.mouse.wheel(0, 5200)
                    page.wait_for_timeout(random.randint(4500, 7500))
                page.wait_for_timeout(1500)
                arts = page.locator('article[data-testid="tweet"]')
                total = arts.count()
                before = len(source)
                # capture thread-root author for each article's conversation
                for i in range(total):
                    art = arts.nth(i)
                    rc = extract(art, handle, None)
                    if rc and rc["post_id"] not in source:
                        if self_only:
                            if not rc.get("in_reply_to"):
                                continue  # top-level post -> covered by the posts pass
                            if rc.get("thread_root_author") and rc["thread_root_author"].lower() != handle.lower():
                                continue  # reply to someone else
                        source[rc["post_id"]] = rc
                new_this_load = len(source) - before
                # oldest post date
                oldest = None
                for r in source.values():
                    try:
                        d = datetime.fromisoformat(r["posted_at"].replace("Z", "+00:00"))
                        if oldest is None or d < oldest:
                            oldest = d
                    except Exception:
                        pass
                print(f"load {loads}: {total} articles, total {len(source)} posts, oldest {oldest and oldest.date()}", flush=True)
                if new_this_load == 0:
                    no_progress += 1
                    if no_progress >= 3:
                        print("reached end of timeline (3 empty loads)");
                        break
                else:
                    no_progress = 0
                if oldest is not None and oldest < cutoff:
                    print(f"reached {days}-day lookback (oldest {oldest.date()})");
                    break
                if loads % 4 == 0:
                    page.wait_for_timeout(random.randint(15000, 26000))
        finally:
            page.close()
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump({handle: source}, fh, ensure_ascii=False, indent=1)
    print(f"wrote {out_path}: {len(source)} posts")
    return source


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--handle", default=MANAS)
    ap.add_argument("--tab", choices=["", "posts", "with_replies"], default="posts")
    ap.add_argument("--days", type=int, default=365)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=120)
    ap.add_argument("--self", action="store_true", help="keep only replies whose parent author is the handle (self-thread replies)")
    a = ap.parse_args()
    deep(a.handle, a.tab, a.days, Path(a.out), a.limit, a.self)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())