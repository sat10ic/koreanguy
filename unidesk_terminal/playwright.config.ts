import { defineConfig } from "playwright/test";

// F-3: frontend smoke suite. Serves the BUILT bundle (npm run preview) so the
// specs exercise exactly what ships; CI runs this right after `npm run build`.
export default defineConfig({
  testDir: "./tests",
  timeout: 30_000,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: "http://127.0.0.1:4173",
    trace: "off",
  },
  webServer: {
    command: "npm run preview -- --port 4173 --strictPort --host 127.0.0.1",
    url: "http://127.0.0.1:4173",
    reuseExistingServer: false,
    timeout: 60_000,
  },
});
