/**
 * MiniSpark — shared sparkline math, extracted from BreadthSparkline (design
 * §1.3/§1.6 kill-list: "duplicated sparkline math in RegimeHistoryStrip.jsx
 * -> shared <MiniSpark>"). Pure presentational: takes numeric values, draws
 * a polyline scaled to its own min/max. No fetching, no captions — callers
 * own their own data + labels.
 */
export default function MiniSpark({ values, stroke = "#175cd3", width = 140, height = 28 }) {
  const pad = 2;
  const pts = (values || [])
    .map((v, i) => ({ i, v }))
    .filter((p) => p.v != null && !Number.isNaN(p.v));

  if (pts.length === 0) {
    return <span className="font-mono text-[14px] text-ink3">&mdash;</span>;
  }

  const n = values.length;
  const min = Math.min(...pts.map((p) => p.v));
  const max = Math.max(...pts.map((p) => p.v));
  const range = max - min || 1;

  const x = (i) => (n <= 1 ? width / 2 : pad + (i / (n - 1)) * (width - 2 * pad));
  const y = (v) => height - pad - ((v - min) / range) * (height - 2 * pad);

  const points = pts.map((p) => `${x(p.i).toFixed(1)},${y(p.v).toFixed(1)}`).join(" ");

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="h-full w-full" preserveAspectRatio="none">
      <polyline points={points} fill="none" stroke={stroke} strokeWidth="1.5" />
    </svg>
  );
}
