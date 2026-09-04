"""Candidate screener: discover Indian trader accounts (breadth + journey) and
score their recent posts. Read-only; light traffic (one page at a time); the
extraction driver may run concurrently on the same capture Chrome.

Usage: python screen_candidates.py [--search "Nifty breadth trader"] [--candidate @handle]
"""
from __future__ import annotations

import argparse
import re
import time
from urllib.parse import quote

from playwright.sync_api import sync_playwright

CDP = "http://127.0.0.1:9222"

JOURNEY = re.compile(r"\b(entry|entered|added|exit|exited|stop|booked|sl\b|target|position|sized|qty|\+[0-9.]+R|initiated|took)\b", re.I)
BREADTH = re.compile(r"\b(breadth|advance|decline|adv/dec|internals|midsml|market breadth|mbi|xp\b|advance-decline|fii|dii)\b", re.I)
HANDLE_RE = re.compile(r"@([A-Za-z0-9_]+)")


def score_article(art, page) -> dict:
    text = ""
    te = art.locator('[data-testid="tweetText"]').first
    if te.count():
        text = (te.text_content() or "").strip()
    media = art.locator('img[src*="pbs.twimg.com/media"]').count()
    j = len(JOURNEY.findall(text))
    b = len(BREADTH.findall(text))
    return {"text": text[:160], "journey": j, "breadth": b, "media": media}


def screen_handle(page, handle: str, n: int = 10) -> dict:
    out = {"handle": handle, "ok": False, "posts": 0, "journey": 0, "breadth": 0, "media": 0, "samples": []}
    try:
        page.goto(f"https://x.com/{handle}", timeout=60000)
        page.wait_for_timeout(3500)
        arts = page.locator('article[data-testid="tweet"]')
        count = arts.count()
        out["ok"] = count > 0
        rows = 0
        for i in range(min(count, n)):
            s = score_article(arts.nth(i), page)
            out["posts"] += 1
            out["journey"] += s["journey"]
            out["breadth"] += s["breadth"]
            out["media"] += s["media"]
            rows += 1
            if len(out["samples"]) < 3 and (s["journey"] or s["breadth"]):
                out["samples"].append(s["text"])
        # keep scrolling a little to find journey/breadth posts
        for _ in range(3):
            page.mouse.wheel(0, 6000)
            page.wait_for_timeout(2500)
            arts = page.locator('article[data-testid="tweet"]')
            count2 = arts.count()
            for i in range(rows, min(count2, n)):
                s = score_article(arts.nth(i), page)
                out["posts"] += 1
                out["journey"] += s["journey"]
                out["breadth"] += s["breadth"]
                out["media"] += s["media"]
                if len(out["samples"]) < 4 and (s["journey"] or s["breadth"]):
                    out["samples"].append(s["text"])
            rows = count2
            if out["journey"] + out["breadth"] >= 4:
                break
    except Exception as exc:  # noqa: BLE001
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


def discover(page, query: str, limit: int = 6) -> list[str]:
    found: list[str] = []
    try:
        page.goto(f"https://x.com/search?q={quote(query)}&src=typed_query&f=user", timeout=60000)
        page.wait_for_timeout(4000)
        for _ in range(3):
            page.mouse.wheel(0, 7000)
            page.wait_for_timeout(2500)
        text = page.locator("body").inner_text(timeout=8000)
        for m in re.finditer(r"@([A-Za-z0-9_]{4,})", text):
            h = m.group(1)
            if h.lower() not in {x.lower() for x in found} and h.lower() not in ("x", "twitter", "signup", "login"):
                found.append(h)
            if len(found) >= limit:
                break
    except Exception as exc:  # noqa: BLE001
        print("discover err", exc)
    return found


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--search", default="market breadth Nifty trader")
    ap.add_argument("--candidate", default=None)
    a = ap.parse_args()
    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp(CDP)
        page = browser.contexts[0].new_page()
        try:
            if a.candidate:
                candidates = [a.candidate.lstrip("@")]
            else:
                candidates = discover(page, a.search)
                print("discovered:", candidates)
                time.sleep(8)
            results = []
            for h in candidates:
                r = screen_handle(page, h)
                r["score"] = r["journey"] * 2 + r["breadth"] * 3 + min(r["media"], 4)
                print(f"{h}: ok={r['ok']} posts={r['posts']} journey={r['journey']} breadth={r['breadth']} media={r['media']} score={r['score']}")
                results.append(r)
                time.sleep(6)
            print("--- top ---")
            for r in sorted(results, key=lambda x: -x["score"])[:5]:
                print(f"{r['handle']} score={r['score']} samples={r['samples'][:2]}")
        finally:
            page.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())