import { createContext, useContext, useMemo, useState } from "react";

/**
 * DensityContext — global Beginner⇄Expert toggle (design §0.3).
 * Beginner (default): plain-English leads, ≤3 raw numbers per card, hides
 * raw columns (20R, 50R, ADR, raw RS rank). Expert: reveals raw columns
 * app-wide; READ lines shrink to one line. Same data, denser — never a
 * different data set, just a different amount of it shown at once.
 */
const DensityContext = createContext({ density: "beginner", setDensity: () => {} });

export function DensityProvider({ children }) {
  const [density, setDensity] = useState("beginner");
  const value = useMemo(() => ({ density, setDensity }), [density]);
  return <DensityContext.Provider value={value}>{children}</DensityContext.Provider>;
}

export function useDensity() {
  return useContext(DensityContext);
}

/** Segmented ink control for the header. */
export function DensityToggle() {
  const { density, setDensity } = useDensity();
  return (
    <div
      data-testid="density-toggle"
      className="flex items-center border border-hairline font-mono text-[9px] uppercase tracking-overline"
    >
      {["beginner", "expert"].map((d) => (
        <button
          key={d}
          onClick={() => setDensity(d)}
          data-testid={`density-${d}`}
          className={
            "px-2 py-0.5 transition-colors " +
            (density === d ? "bg-ink text-white" : "text-ink3 hover:text-ink")
          }
        >
          {d}
        </button>
      ))}
    </div>
  );
}
