import React from "react";

// v5 primitive: mechanism lane summary card (momentum/basepattern/ipobase),
// 3px left accent border per family + count + symbol summary line.
// `family`: "momentum" | "basepattern" | "ipobase" (drives the accent color).
export default function LaneCard({ family, name, count, sub, summary }) {
  const famClass = family ? ` v5-lane-${family}` : "";
  return (
    <div className={"v5-lane-card" + famClass}>
      <div className="v5-lane-hd">
        <span className="v5-name">{name}</span>
        <span className="v5-n mono-num">{count ?? "—"}</span>
      </div>
      {sub && <div className="v5-lane-sub">{sub}</div>}
      {summary && <div className="v5-lane-syms">{summary}</div>}
    </div>
  );
}
