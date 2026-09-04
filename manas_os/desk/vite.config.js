import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: { port: 5174 },
  test: {
    // Playwright journeys live under tests/ and use a different runner.
    // Keeping them out of Vitest prevents two incompatible test runtimes
    // from loading the same *.spec.js file.
    exclude: ["tests/**", "**/node_modules/**", "**/dist/**"],
  },
});
