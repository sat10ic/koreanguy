import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

const allTabs = ['MARKET', 'SCANNERS', 'SHORTLIST', 'DEBATE', 'ALPHA', 'POSITIONS', 'JOURNAL'];
const tabs = process.env.DESK_TABS ? process.env.DESK_TABS.split(',').map((tab) => tab.trim().toUpperCase()) : allTabs;
const baseUrl = process.env.DESK_URL || 'http://127.0.0.1:5173';
const date = process.env.DESK_DATE || '2026-07-10';
const viewportWidth = Number(process.env.DESK_WIDTH || 1440);
const viewportHeight = Number(process.env.DESK_HEIGHT || 1000);
const outputDir = path.resolve('screenshots');

fs.mkdirSync(outputDir, { recursive: true });

async function captureTabs() {
  const browser = await chromium.launch({ headless: true });
  const failures = [];

  for (const tab of tabs) {
    const page = await browser.newPage({
      viewport: { width: viewportWidth, height: viewportHeight },
      colorScheme: 'light',
      reducedMotion: 'reduce',
    });
    page.on('pageerror', (error) => failures.push(`${tab}: page error: ${error.message}`));
    page.on('console', (message) => {
      if (message.type() === 'error' && !message.text().includes('favicon.ico')) {
        failures.push(`${tab}: console error: ${message.text()}`);
      }
    });
    try {
      console.log(`Capturing ${tab}...`);
      const url = `${baseUrl}/?tab=${encodeURIComponent(tab)}&date=${encodeURIComponent(date)}`;
      // The desk intentionally polls live-work endpoints, so networkidle is
      // not a valid readiness signal. DOM + the visible shell + settled fonts
      // describe the user-visible contract without waiting on background work.
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
      await page.waitForSelector('.v5-shell .shell-body-inner', { state: 'visible' });
      await page.evaluate(() => document.fonts.ready);
      await page.addStyleTag({ content: '*,*::before,*::after{animation:none!important;transition:none!important;scroll-behavior:auto!important}' });
      await page.waitForTimeout(2500);

      const dimensions = await page.locator('.v5-shell').evaluate((shell) => ({
        width: shell.scrollWidth,
        viewport: document.documentElement.clientWidth,
      }));
      if (dimensions.width > dimensions.viewport + 1) {
        failures.push(`${tab}: horizontal overflow ${dimensions.width}px > ${dimensions.viewport}px`);
        const offenders = await page.locator('body *').evaluateAll((elements) => elements
          .filter((element) => element.scrollWidth > element.clientWidth + 1)
          .slice(0, 12)
          .map((element) => `${element.tagName.toLowerCase()}.${element.className}: ${element.scrollWidth}/${element.clientWidth}`));
        console.error(`  Overflow sources: ${offenders.join(' | ')}`);
      }

      const screenshotPath = path.join(outputDir, `${tab.toLowerCase()}-tab-${viewportWidth}.png`);
      await page.screenshot({ path: screenshotPath, fullPage: true, animations: 'disabled' });
      console.log(`  Saved: ${screenshotPath}`);
    } catch (error) {
      failures.push(`${tab}: ${error.message}`);
      console.error(`  Error capturing ${tab}:`, error.message);
    } finally {
      await page.close();
    }
  }

  await browser.close();
  if (failures.length) {
    console.error(failures.join('\n'));
    process.exitCode = 1;
  } else {
    console.log('All real-tab captures complete');
  }
}

captureTabs().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
