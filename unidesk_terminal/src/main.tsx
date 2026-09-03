import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { MotionConfig } from 'framer-motion'
import './index.css'
import App from './App.tsx'
import { ThemeProvider } from './lib/ThemeContext'
import { ToastProvider } from './components/ui/Toast'
import { Skeleton } from './components/ui/Skeleton'
import { initDeskData } from './data/deskData'

// set theme before first paint to avoid a dark flash on the light default
// (private-mode safe: localStorage can throw — F-2)
document.documentElement.dataset.theme = (() => {
  try { return localStorage.getItem("unidesk.theme") === "dark" ? "dark" : "light"; }
  catch { return "light"; }
})();

// E-3: hydrate desk data from the localhost server BEFORE first render
// (falls back to the bundled snapshots, loudly disclosed, when unreachable).
// The boot skeleton names what is loading (F-2/F-3: a hang must be
// diagnosable, not a blank screen).
async function boot() {
  const root = createRoot(document.getElementById('root')!);
  root.render(
    <StrictMode>
      <Skeleton label="loading desk data…" />
    </StrictMode>,
  );
  await initDeskData();
  root.render(
    <StrictMode>
      <ThemeProvider>
        {/* E-4: MotionConfig reducedMotion="user" — every framer-motion
            animation (route fades, toasts, list motion, count-up) suppresses
            under the OS reduced-motion setting, on top of the CSS
            prefers-reduced-motion block in index.css. */}
        <MotionConfig reducedMotion="user">
          <ToastProvider>
            <App />
          </ToastProvider>
        </MotionConfig>
      </ThemeProvider>
    </StrictMode>,
  );
}

void boot();
