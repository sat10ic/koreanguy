import { test, expect } from '@playwright/test';

const tabs = [
  'MARKET',
  'SCANNERS',
  'SHORTLIST / SS',
  'DEBATE',
  'ALPHA',
  'POSITIONS',
  'JOURNAL',
];

test('every top tab renders without boundary or console errors', async ({ page }) => {
  const consoleErrors = [];
  const pageErrors = [];
  let currentTab = 'startup';

  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(`${currentTab}: ${message.text()}`);
  });
  page.on('pageerror', (error) => pageErrors.push(`${currentTab}: ${error.message}`));
  await page.addInitScript(() => window.localStorage.setItem('mode', 'expert'));
  await page.goto('http://localhost:8000', { waitUntil: 'domcontentloaded' });
  await expect(page.locator('.shell-tabs')).toBeVisible();

  for (const label of tabs) {
    await test.step(label, async () => {
      currentTab = label;
      const tab = page.locator('.shell-tabs').getByRole('button', { name: label, exact: true });
      await tab.click();
      await expect(tab).toHaveClass(/active/);
      await page.waitForTimeout(250);
      await expect(page.getByText(/hit an error/i)).toHaveCount(0);
    });
  }

  expect(consoleErrors, `console errors:\n${consoleErrors.join('\n')}`).toEqual([]);
  expect(pageErrors, `page errors:\n${pageErrors.join('\n')}`).toEqual([]);
});
