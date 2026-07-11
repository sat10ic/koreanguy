import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import "./tokens.css";

// v5 fonts -- @fontsource, NOT CDN (offline desk, zero Google requests).
// Weights actually used by the round-4 light design: Fraunces variable
// (display/verdicts, incl. italic axis for SectionLabel), Public Sans
// 400/500/600/700/800 (UI+prose), IBM Plex Mono 400/500/600/700 (numbers).
import "@fontsource-variable/fraunces";
import "@fontsource-variable/fraunces/wght-italic.css";
import "@fontsource/public-sans/400.css";
import "@fontsource/public-sans/500.css";
import "@fontsource/public-sans/600.css";
import "@fontsource/public-sans/700.css";
import "@fontsource/public-sans/800.css";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
import "@fontsource/ibm-plex-mono/600.css";
import "@fontsource/ibm-plex-mono/700.css";
import "./styles/tokens.v5.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
