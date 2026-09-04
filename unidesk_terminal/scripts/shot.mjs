import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

const outDir = process.argv[2];
const routes = process.argv.slice(3);
mkdirSync(outDir, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
const errors = [];
page.on("pageerror", (e) => errors.push(`[pageerror] ${e.message}`));
page.on("console", (msg) => {
  if (msg.type() === "error") errors.push(`[console.error] ${msg.text()}`);
});

for (const route of routes) {
  const url = `http://localhost:5183/#${route}`;
  await page.goto(url, { waitUntil: "networkidle" });
  await page.waitForTimeout(300);
  const name = route === "/" ? "home" : route.replace(/\W+/g, "_");
  await page.screenshot({ path: `${outDir}/${name}.png`, fullPage: true });
  console.log(`shot: ${route} -> ${name}.png`);
}

await browser.close();
if (errors.length) {
  console.log("\n--- console/page errors ---");
  console.log([...new Set(errors)].join("\n"));
} else {
  console.log("\nno console/page errors");
}
