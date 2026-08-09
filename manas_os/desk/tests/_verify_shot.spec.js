import { test, expect } from "@playwright/test";

const BASE_URL = process.env.DESK_URL || "http://localhost:8000";

test.use({ viewport: { width: 1280, height: 1000 } });

test("capture beginner PREPARE screenshot", async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem("mode", "beginner");
  });
  await page.goto(`${BASE_URL}/?tab=SCANNERS&date=2026-07-10`, { waitUntil: "networkidle" });
  await page.locator(".v5-panel").filter({ hasText: /Tonight/ }).first().waitFor({ state: "visible", timeout: 15000 });
  await page.screenshot({ path: "tests/_verify_prepare_beginner.png", fullPage: false });

  // Also capture with the research library expanded, to prove the toggle works.
  await page.locator("details.tnq-research summary").first().click();
  await expect(page.locator("details.tnq-research .scn-segmented").first()).toBeVisible();
  await page.screenshot({ path: "tests/_verify_prepare_research_open.png", fullPage: false });
});
