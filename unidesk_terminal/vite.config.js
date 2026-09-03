import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // NOTE: hardcoded — a harness that assigns a different port is ignored
    // (the desk tooling expects 5183).
    port: 5183,
    // E-3: the dev server proxies /api to the localhost desk server so the
    // same fetch paths work in dev and in the static bundle.
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8181',
        changeOrigin: false,
      },
    },
  },
})
