import React, { createContext, useContext } from "react";

export const DENSITY_STORAGE_KEY = "mode";

export const DensityContext = createContext({
  mode: "beginner",
  isExpert: false,
  setMode: () => {},
  toggleMode: () => {},
});

export function useDensity() {
  return useContext(DensityContext);
}

export function normalizeDensityMode(value) {
  return value === "expert" ? "expert" : "beginner";
}
