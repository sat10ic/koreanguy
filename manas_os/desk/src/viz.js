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
    return { background: "var(--v5-chart-bg)", color: "var(--ink-dim)" };
  }
  const magnitude = Math.min(Math.abs(value), capAt) / capAt; // 0..1
  if (magnitude === 0) {
    return { background: "var(--v5-chart-bg)", color: "var(--ink-dim)" };
  }
  const alpha = 0.12 + magnitude * 0.55; // visible even near zero, saturates near cap
  const rgb = value > 0 ? "20, 113, 63" : "173, 44, 52"; // v5 green / red (was neon 0,255,102 / 255,68,68)
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

// V2: hand-rolled squarified treemap (Bruls/Huizing/van Wijk algorithm),
// no library. Input: [{name, size, value}, ...] (size drives area, value is
// carried through untouched for coloring by the caller). Output: same items
// with {x, y, w, h} rect positions (in the same units as width/height)
// added. Items with size <= 0 are dropped. Zero/невалид width or height or
// an empty/all-zero input returns [].
export function squarifyTreemap(items, width, height) {
  const clean = (items || []).filter((it) => it && it.size > 0);
  if (clean.length === 0 || width <= 0 || height <= 0) return [];

  const total = clean.reduce((sum, it) => sum + it.size, 0);
  const area = width * height;
  // Normalize sizes to area units, largest first (squarify wants descending order).
  const scaled = clean
    .map((it) => ({ ...it, _area: (it.size / total) * area }))
    .sort((a, b) => b._area - a._area);

  const rects = [];
  let x = 0, y = 0, w = width, h = height;
  let row = [];
  let rowSum = 0;

  function worstAspect(rowItems, sum, shortSide) {
    if (rowItems.length === 0) return Infinity;
    const rowAreaSum = sum;
    let maxA = -Infinity, minA = Infinity;
    for (const it of rowItems) {
      if (it._area > maxA) maxA = it._area;
      if (it._area < minA) minA = it._area;
    }
    const s2 = shortSide * shortSide;
    const ratio1 = (s2 * maxA) / (rowAreaSum * rowAreaSum);
    const ratio2 = (rowAreaSum * rowAreaSum) / (s2 * minA);
    return Math.max(ratio1, ratio2);
  }

  function layoutRow(rowItems, sum) {
    const vertical = w >= h;
    const shortSide = vertical ? h : w;
    const rowLength = sum / shortSide; // thickness of this row along the long axis
    let offset = 0;
    for (const it of rowItems) {
      const extent = shortSide > 0 ? it._area / rowLength / shortSide * shortSide : 0;
      const len = shortSide > 0 ? it._area / rowLength : 0;
      if (vertical) {
        rects.push({ ...it, x, y: y + offset, w: rowLength, h: len });
      } else {
        rects.push({ ...it, x: x + offset, y, w: len, h: rowLength });
      }
      offset += len;
    }
    if (vertical) {
      x += rowLength;
      w -= rowLength;
    } else {
      y += rowLength;
      h -= rowLength;
    }
  }

  let i = 0;
  while (i < scaled.length) {
    const item = scaled[i];
    const shortSide = Math.min(w, h);
    const newRow = [...row, item];
    const newSum = rowSum + item._area;
    if (
      row.length === 0 ||
      worstAspect(newRow, newSum, shortSide) <= worstAspect(row, rowSum, shortSide)
    ) {
      row = newRow;
      rowSum = newSum;
      i += 1;
    } else {
      layoutRow(row, rowSum);
      row = [];
      rowSum = 0;
    }
  }
  if (row.length > 0) layoutRow(row, rowSum);

  return rects.map((r) => ({
    ...r,
    x: Math.round(r.x * 100) / 100,
    y: Math.round(r.y * 100) / 100,
    w: Math.round(r.w * 100) / 100,
    h: Math.round(r.h * 100) / 100,
  }));
}

// V1: DESK regime gauge zones, ordered least -> most permissive along the
// meter. Marker position = index of the current mode.
export const REGIME_GAUGE_ZONES = [
  { mode: "NO_TRADE", color: "var(--ink-dim)" },
  { mode: "DEFENSIVE", color: "var(--danger)" },
  { mode: "SELECTIVE", color: "var(--warn)" },
  { mode: "RISK_ON", color: "var(--positive)" },
];
