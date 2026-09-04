import React from "react";

// v5 primitive: 4-dot conviction meter, currentColor on/off (ported from the
// legacy DebateTab ConvictionDots -- shared so Wave 2 doesn't duplicate it).
// conviction: 0-4 (falls back to 0 when null/undefined).
export default function ConvictionDots({ conviction, max = 4 }) {
  const c = Math.max(0, Math.min(max, conviction || 0));
  const dots = [];
  for (let i = 0; i < max; i += 1) {
    dots.push(<span key={i} className={"v5-conv-dot" + (i < c ? " v5-on" : "")} />);
  }
  return (
    <span className="v5-conv-dots" title={`conviction ${conviction ?? "—"}`}>
      {dots}
    </span>
  );
}
