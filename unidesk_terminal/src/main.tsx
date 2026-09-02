import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { ThemeProvider } from './lib/ThemeContext'

// set theme before first paint to avoid a dark flash on the light default
document.documentElement.dataset.theme =
  localStorage.getItem("unidesk.theme") === "dark" ? "dark" : "light";

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider>
      <App />
    </ThemeProvider>
  </StrictMode>,
)
