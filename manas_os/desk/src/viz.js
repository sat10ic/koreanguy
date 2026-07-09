// Shared visualization helpers (VIZ-PASS V1-V7).
//
// colorScale: one red-green diverging scale used everywhere a %/return number
// is rendered — indices grid, movers, R values, sparkline endpoints, POSITIONS
// %/R cells. Intensity scales with magnitude; #141414 (App.css --bg-sunken-ish
// near-black) sits at zero so a flat/no-move cell reads as neutral, not colored.
//
// value: a plain percent or R number (e.g. 1.4 means +1.4%). `capAt` bounds
// the intensity ramp so one outlier doesn't wash out the rest of a column.
export function colorScale(value, capAt = 5) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return { background: "#141414", color: "var(--ink-dim)" };
  }
  const magnitude = Math.min(Math.abs(value), capAt) / capAt; // 0..1
  if (magnitude === 0) {
    return { background: "#141414", color: "var(--ink-dim)" };
  }
  const alpha = 0.12 + magnitude * 0.55; // visible even near zero, saturates near cap
  const rgb = value > 0 ? "0, 255, 102" : "255, 68, 68";
  return {
    background: `rgba(${rgb}, ${alpha.toFixed(3)})`,
    color: value > 0 ? "var(--positive)" : "var(--danger)",
  };
}

// Inline SVG sparkline for a 30d close array. Returns a small polyline path
// scaled to a fixed viewBox; caller controls width/height via CSS.
export function sparklinePoints(values, width = 100, height = 28) {
  const clean = (values || []).filter((v) => v !== null && v !== undefined);
  if (clean.length < 2) return null;
  const min = Math.min(...clean);
  const max = Math.max(...clean);
  const span = max - min || 1;
  const step = width / (clean.length - 1);
  return clean
    .map((v, i) => {
      const x = i * step;
      const y = height - ((v - min) / span) * height;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

// V1: DESK regime gauge zones, ordered least -> most permissive along the
// meter. Marker position = index of the current mode.
export const REGIME_GAUGE_ZONES = [
  { mode: "NO_TRADE", color: "var(--ink-dim)" },
  { mode: "DEFENSIVE", color: "var(--danger)" },
  { mode: "SELECTIVE", color: "var(--warn)" },
  { mode: "RISK_ON", color: "var(--positive)" },
];
