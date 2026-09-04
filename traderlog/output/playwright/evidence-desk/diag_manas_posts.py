from playwright.sync_api import sync_playwright

CDP = "http://127.0.0.1:9222"
with sync_playwright() as pw:
    b = pw.chromium.connect_over_cdp(CDP)
    page = b.contexts[0].new_page()
    errs = []
    page.on("console", lambda m: errs.append(f"{m.type}: {m.text[:80]}") if m.type in ("error", "warning") else None)
    try:
        page.goto("https://x.com/iManasArora", timeout=60000)
        page.wait_for_timeout(8000)
        arts = page.locator('article[data-testid="tweet"]').count()
        print("articles after 8s:", arts)
        # tab rail buttons
        tabs = page.locator('a[role="tab"]').evaluate_all("els => els.map(e=>e.textContent.trim())")
        print("tabs:", tabs)
        # 'see new posts' / login interstitial
        print("see-new-posts:", page.locator("text=See new posts").count())
        print("sign-in:", page.locator("text=Sign in").count())
        # try clicking the Posts tab if present
        pg = page.locator('a[role="tab"]:has-text("Posts")')
        if pg.count():
            pg.first.click()
            page.wait_for_timeout(6000)
            print("articles after clicking Posts tab:", page.locator('article[data-testid="tweet"]').count())
        body = page.locator("body").inner_text(timeout=8000)[:260]
        print("BODY:", body.replace("\n", " | ")[:260])
        print("console:", errs[:5])
    except Exception as exc:
        print("ERR", type(exc).__name__, exc)
    finally:
        page.close()
    b.close()