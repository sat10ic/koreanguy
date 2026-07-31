import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The API stays where it is -- this is a new FRONT END over the same backend and
// the same manas.db. Proxying /api keeps the app origin-clean in dev.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5175,
    proxy: {
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: true },
    },
  },
});
