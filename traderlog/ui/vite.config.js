import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Port 5180 keeps out of the way of manas_os (5173/5174/5175).
// The API runs on 8100 and serves ui/dist in production; in dev we proxy so the
// same relative /api paths work in both, and api.js needs no environment switch.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5180,
    strictPort: true,
    proxy: { "/api": { target: "http://127.0.0.1:8100", changeOrigin: true } },
  },
  build: { outDir: "dist", emptyOutDir: true },
});
