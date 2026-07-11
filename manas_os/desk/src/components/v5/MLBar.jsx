import React from "react";

// v5 primitive: 44px teal micro-bar + pct for ML p(up). Renders "--" when null
// -- never fabricates a probability.
export default function MLBar({ pUp }) {
  if (pUp === null || pUp === undefined) {
    return <span className="v5-ml-bar-empty">{"—"}</span>;
  }
  const pct = Math.max(0, Math.min(1, pUp)) * 100;
  return (
    <span className="v5-ml-bar-wrap">
      <span className="v5-ml-bar-track">
        <span className="v5-ml-bar-fill" style={{ width: `${pct}%` }} />
      </span>
      <span className="v5-ml-bar-pct mono-num">{pct.toFixed(0)}%</span>
    </span>
  );
}
