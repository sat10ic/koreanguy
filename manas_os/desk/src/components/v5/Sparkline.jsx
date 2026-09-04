import React from "react";

// v5 primitive: pure-SVG sparkline from a real closes array (props only --
// no synthetic series ever). green/red by first-vs-last. Renders an honest
// "--" when the series is absent or too short to draw.
export default function Sparkline({ series, width = 72, height = 22 }) {
  if (!series || series.length < 2) {
    return <span className="v5-spark-empty">{"—"}</span>;
  }
  const min = Math.min(...series);
  const max = Math.max(...series);
  const range = max - min || 1;
  const stepX = width / (series.length - 1);
  const points = series
    .map((v, i) => {
      const x = i * stepX;
      const y = height - ((v - min) / range) * height;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  const up = series[series.length - 1] >= series[0];
  const stroke = up ? "var(--v5-green)" : "var(--v5-red)";
  return (
    <svg className="v5-spark" width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={up ? "rising" : "falling"}>
      <polyline points={points} fill="none" stroke={stroke} strokeWidth="1.4" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}
