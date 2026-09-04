import { test, expect } from "@playwright/test";

// UX audit 2026-07-19 §1 verification: beginner PREPARE shows the 4-part
// TonightQueue contract, the Research library disclosure is collapsed, and
// there is no horizontal overflow at 1280w. Expert mode is unchanged.

const BASE_URL = process.env.DESK_URL || "http://localhost:8000";
const DATE = "2026-07-10";

test.use({ viewport: { width: 1280, height: 1000 } });

test("beginner PREPARE: 4-part contract + collapsed research library + no 1280w overflow", async ({ page }) => {
  const errors = [];
  page.on("pageerror", (err) => errors.push(`PageError: ${err.message}`));
  page.on("console", (msg) => {
    if (msg.type() === "error" && !msg.text().includes("favicon.ico")) {
      errors.push(`ConsoleError: ${msg.text()}`);
    }
  });

  // Force beginner density (localStorage "mode" = "beginner") before the app
  // bootstraps, then open PREPARE.
  await page.addInitScript(() => {
    window.localStorage.setItem("mode", "beginner");
  });
  await page.goto(`${BASE_URL}/?tab=SCANNERS&date=${DATE}`, { waitUntil: "networkidle" });

  // The Tonight panel is the beginner primary surface. Its title is
  // "Tonight: N names to prepare" or the honest empty state.
  const tonightPanel = page.locator(".v5-panel").filter({ hasText: /Tonight/ }).first();
  await expect(tonightPanel).toBeVisible({ timeout: 15000 });

  // Research library disclosure must exist and be collapsed by default.
  const research = page.locator("details.tnq-research").first();
  await expect(research).toBeVisible();
  await expect(research).not.toHaveAttribute("open", "");
  // Collapsed means the segmented control inside is hidden (display:none on
  // the body via <details>), so it has no visible box.
  const segmented = research.locator(".scn-segmented").first();
  await expect(segmented).not.toBeVisible();

  // Either the per-name 4-part contract renders (if A_WATCH has hits) or the
  // honest empty state does. Capture which one for the report.
  const nameCount = await page.locator(".tnq-name").count();
  const emptyStateVisible = await page.getByText(/Nothing to prepare tonight/).count();
  console.log(`[verify] tnq-name count=${nameCount}, empty-state-visible=${emptyStateVisible}`);

  if (nameCount > 0) {
    // 4-part contract: every name exposes Trigger / Invalidation / Final size
    // / Why it survived / What would disqualify it labels.
    const first = page.locator(".tnq-name").first();
    for (const label of ["Trigger", "Invalidation", "Final size", "Why it survived", "What would disqualify it"]) {
      await expect(first.locator("dt", { hasText: label })).toBeVisible();
    }
    // No more than 3 names rendered (cap), with a "+K more" line if exceeded.
    expect(nameCount, "cap at 3").toBeLessThanOrEqual(3);
  }

  // No horizontal overflow at 1280w: the document width must not exceed the
  // viewport width (allow 1px for sub-pixel rounding).
  const overflow = await page.evaluate(() => ({
    docWidth: document.documentElement.scrollWidth,
    viewportWidth: window.innerWidth,
  }));
  console.log(`[verify] docWidth=${overflow.docWidth} viewportWidth=${overflow.viewportWidth}`);
  expect(overflow.docWidth, "no horizontal overflow at 1280w").toBeLessThanOrEqual(overflow.viewportWidth + 1);

  // Surface any page/console errors so the report is honest.
  expect(errors, `no page/console errors; got: ${JSON.stringify(errors)}`).toEqual([]);

  // Snapshot the Tonight panel text for the report.
  const tonightText = (await tonightPanel.innerText()).replace(/\s+\n/g, "\n").slice(0, 800);
  console.log(`[verify] Tonight panel text:\n${tonightText}`);
});

test("expert PREPARE: no Tonight queue, no disclosure wrapper (unchanged)", async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem("mode", "expert");
  });
  await page.goto(`${BASE_URL}/?tab=SCANNERS&date=${DATE}`, { waitUntil: "networkidle" });

  // Expert mode must not show the beginner Tonight panel.
  await expect(page.locator(".tnq-list")).toHaveCount(0);
  // And no disclosure wrapper around the segmented control.
  await expect(page.locator("details.tnq-research")).toHaveCount(0);
  // The segmented control is rendered directly (visible).
  await expect(page.locator(".scn-segmented").first()).toBeVisible({ timeout: 15000 });
});
