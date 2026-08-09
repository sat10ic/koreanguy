import { test, expect } from '@playwright/test';

test.describe('Beginner Workflow Baseline Harness', () => {
  const tabs = [
    ['MARKET', 'TODAY'],
    ['SCANNERS', 'PREPARE'],
    ['SHORTLIST', 'WATCH'],
    ['DEBATE', 'DECIDE'],
    ['POSITIONS', 'MANAGE'],
    ['JOURNAL', 'REVIEW'],
  ];
  const BASE_URL = process.env.DESK_URL || 'http://127.0.0.1:5173';
  const DATE = '2026-07-10';

  // Make sure it runs in 1440x1000 viewport as requested in Wave 0 baseline, 
  // though Playwright config usually handles this, we'll set it here to be safe.
  test.use({ viewport: { width: 1440, height: 1000 } });

  test('Read-only journey across all beginner tabs', async ({ page }) => {
    const errors = [];
    // Keep this read-only without letting an unconfirmed live profile obscure
    // every screen. PUT/other methods still continue to the real API.
    await page.route('**/api/trader-profile', async (route) => {
      if (route.request().method() !== 'GET') return route.continue();
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          account_capital: 1000000,
          experience_mode: 'LEARNING',
          profile_confirmed_at: '2026-01-01T00:00:00Z',
        }),
      });
    });
    
    // Listen for page errors and console errors
    page.on('pageerror', (err) => errors.push(`PageError: ${err.message}`));
    page.on('console', (msg) => {
      if (msg.type() === 'error' && !msg.text().includes('favicon.ico')) {
        errors.push(`ConsoleError: ${msg.text()}`);
      }
    });

    for (const [tabName, beginnerLabel] of tabs) {
      await test.step(`Navigate to ${tabName}`, async () => {
        const url = `${BASE_URL}/?tab=${encodeURIComponent(tabName)}&date=${DATE}`;
        console.log(`Loading ${url}...`);
        
        // Measure endpoint timings (very rough approximation)
        const start = Date.now();
        await page.goto(url, { waitUntil: 'domcontentloaded' });
        
        // Wait up to 8s for any loading indicators to disappear
        const loadingIndicator = page.locator('.loading, .spinner, [aria-busy="true"]');
        try {
          await loadingIndicator.waitFor({ state: 'hidden', timeout: 8000 });
        } catch (e) {
          errors.push(`[${tabName}] Visible loading exceeded 8s`);
        }
        
        const loadTime = Date.now() - start;
        console.log(`[${tabName}] Loaded in ${loadTime}ms`);

        // Check for missing primary content (basic check - main body exists)
        const mainContent = page.locator('.v5-shell .shell-body-inner');
        await expect(mainContent).toBeVisible({ timeout: 2000 }).catch(() => {
           errors.push(`[${tabName}] Missing primary content shell-body-inner`);
        });

        const activeTab = page.locator('.shell-tabs .tab-btn.active');
        await expect(activeTab).toHaveText(beginnerLabel, { timeout: 4000 }).catch(() => {
          errors.push(`[${tabName}] URL did not activate the ${beginnerLabel} tab`);
        });

        // Check for horizontal overflow
        const overflowCheck = await page.evaluate(() => {
          const shell = document.querySelector('.v5-shell');
          if (!shell) return false;
          return shell.scrollWidth > document.documentElement.clientWidth;
        });
        
        if (overflowCheck) {
          errors.push(`[${tabName}] Page/local horizontal overflow detected`);
        }

        // We specifically avoid mutating clicks (no TAKE, save, etc.)
        // Just verify basic layout and readability.
      });
    }

    // Output all collected errors to fail the test and document the baseline defects
    if (errors.length > 0) {
      console.error("Baseline journey failures detected:", errors);
      // The handoff explicitly expects this to FAIL on the known defects
      // so throwing here is correct for baseline validation.
      throw new Error(`Journey harness failed with ${errors.length} baseline defects:\n${errors.join('\n')}`);
    }
  });

  test('Expert Alpha Lab is reachable and renders its research controls', async ({ page }) => {
    await page.addInitScript(() => window.localStorage.setItem('mode', 'expert'));
    await page.route('**/api/trader-profile', (route) => route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ account_capital: 1000000, experience_mode: 'LEARNING', profile_confirmed_at: '2026-01-01T00:00:00Z' }),
    }));
    await page.goto(`${BASE_URL}/?tab=ALPHA&date=2026-07-13`, { waitUntil: 'domcontentloaded' });
    await expect(page.locator('.shell-tabs .tab-btn.active')).toHaveText('ALPHA');
    await expect(page.getByText('ALPHA LAB · SHADOW EVIDENCE')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('How the lab avoids fooling itself')).toBeVisible();
  });
});
