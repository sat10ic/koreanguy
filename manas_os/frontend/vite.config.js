import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server runs on :5173; the FastAPI API on :8000. The api.js helper talks
// to the API directly (CORS is allowed for this origin in api/app.py).
export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
});
