import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import { DensityProvider } from "./DensityContext.jsx";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <DensityProvider>
      <App />
    </DensityProvider>
  </React.StrictMode>
);
