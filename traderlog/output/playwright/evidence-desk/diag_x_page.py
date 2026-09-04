from playwright.sync_api import sync_playwright

CDP = "http://127.0.0.1:9222"
with sync_playwright() as pw:
    browser = pw.chromium.connect_over_cdp(CDP)
    ctx = browser.contexts[0]
    page = ctx.new_page()
    try:
        page.goto("https://x.com/iManasArora/with_replies", timeout=60000)
        page.wait_for_timeout(4000)
        print("URL:", page.url)
        print("TITLE:", page.title())
        body = page.locator("body").inner_text(timeout=8000)[:500]
        print("BODY:", body.replace("\n", " | ")[:500])
        print("articles:", page.locator('article[data-testid="tweet"]').count())
        print("login links:", page.locator('a[href="/i/flow/login"]').count())
        print("signin prompts:", page.locator("text=Sign in").count())
        # what about the copied profile's cookie count for x.com?
        cookie_info = page.evaluate("() => document.cookie.length")
        print("document.cookie length:", cookie_info)
    except Exception as exc:
        print("ERR:", type(exc).__name__, exc)
    finally:
        page.close()
    browser.close()