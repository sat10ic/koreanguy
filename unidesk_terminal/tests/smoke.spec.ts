/*
  F-3: one smoke spec per route. Every spec asserts:
    1. the page renders a known landmark, and
    2. the browser console has NO APP errors. The expected `/api/` 502 when
       the optional desk server is not running is part of the OFFLINE design
       (the UI must show a loud banner, not break) — those resource errors
       are filtered; every other console error and ALL page errors fail.
  Plus the class-level invariants from the 2026-09-02 audit (F-7): a finding
  is not closed until something fails when it regresses.
*/
import { expect, test, type Page } from "@playwright/test";

const ROUTES: { path: string; landmark: string }[] = [
  { path: "#/", landmark: "Setup feed" },
  { path: "#/market", landmark: "Market" },
  { path: "#/candidates", landmark: "Ranked research table" },
  { path: "#/stock", landmark: "No symbol selected" },
  { path: "#/desk", landmark: "Positions register" },
  { path: "#/history", landmark: "What the scanner called" },
  { path: "#/research", landmark: "Archive coverage" },
  { path: "#/settings", landmark: "Display mode" },
];

async function watchConsole(page: Page): Promise<string[]> {
  const errors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() !== "error") return;
    // the desk-server probe failing in an offline preview is the designed,
    // loudly-disclosed OFFLINE path — not an app error (a banner asserts it)
    const url = msg.location()?.url ?? "";
    if (url.includes("/api/")) return;
    errors.push(msg.text());
  });
  page.on("pageerror", (err) => errors.push(String(err)));
  return errors;
}

for (const { path, landmark } of ROUTES) {
  test(`route ${path} renders "${landmark}" with a clean console`, async ({ page }) => {
    const errors = await watchConsole(page);
    await page.goto("/" + path);
    await expect(page.getByText(landmark).first()).toBeVisible({ timeout: 15_000 });
    expect(errors, `console errors on ${path}:\n${errors.join("\n")}`).toEqual([]);
  });
}

test.describe("audit invariants (F-7: a finding is not closed until something fails)", () => {
  test("A-1: Tonight's rendered section counts sum to the header count", async ({ page }) => {
    await page.goto("/#/");
    const header = await page.getByText(/\d+ candidates/).first().textContent();
    const headerCount = Number((header ?? "").match(/(\d+)/)?.[1] ?? NaN);
    expect(headerCount).not.toBeNaN();
    // every rendered section header carries its count in a mono span
    const counts = await page.locator("button:has(h3) > span.font-mono-num").allTextContents();
    const sum = counts.map((c) => Number(c)).filter((n) => !Number.isNaN(n)).reduce((a, b) => a + b, 0);
    expect(sum, `rendered section counts [${counts}] must sum to header ${headerCount}`).toBe(headerCount);
    // F-7 sharpening: the Other-section fallback keeps the sum honest, so the
    // real regression signal is a detector losing its OWN section mapping.
    const unmapped = await page.getByText("Other / unmapped detector").count();
    expect(unmapped, "every report detector must render in its own named section").toBe(0);
  });

  test("A-4: no PRIME row carries a null or sub-1.0 R:R", async ({ page }) => {
    await page.goto("/#/candidates");
    await expect(page.getByText("Ranked research table").first()).toBeVisible();
    // rows are grid <label>s; direct-child spans only (cells nest spans)
    const rows = page.locator("label:has(span:text-is('PRIME'))");
    const primeCount = await rows.count();
    expect(primeCount, "the desk should render at least one PRIME row").toBeGreaterThan(0);
    for (let i = 0; i < primeCount; i++) {
      const row = rows.nth(i);
      // cells: 0 rank · 1 stock · 2 setup · 3 sector · 4 quality · 5 entry ·
      // 6 rs · 7 rsΔ · 8 rvol · 9 tight · 10 trend · 11 R:R · 12 chop · 13 stop · 14 state
      const rrText = ((await row.locator("xpath=./span").nth(11).textContent()) ?? "").trim();
      expect(rrText, "PRIME row R:R cell must be present").not.toContain("—");
      const rr = Number(rrText.replace("R", "").trim());
      expect(rr, `PRIME row R:R value "${rrText}"`).toBeGreaterThanOrEqual(1.0);
    }
  });

  test("A-8: the top bar reports a truthful session age", async ({ page }) => {
    await page.goto("/#/");
    const age = page.locator("header span", { hasText: /current|sessions? behind/ });
    await expect(age.first()).toBeVisible({ timeout: 10_000 });
    const text = (await age.first().textContent()) ?? "";
    expect(text).toMatch(/(current|\d+ sessions? behind)/);
  });
});
