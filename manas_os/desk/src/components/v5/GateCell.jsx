import React from "react";

// v5 primitive: one gate result cell (PASS/WAIVED state + optional amber
// objection note). `gates`: [{ name, state, objection }]
export function GateCell({ name, state, objection }) {
  const pass = (state || "").toUpperCase() === "PASS";
  return (
    <div className={"v5-gate-cell" + (pass ? " v5-pass" : "") + (objection ? " v5-objection" : "")}>
      <div className="v5-gname">{name}</div>
      <div className="v5-gstate">{state || "—"}</div>
      {objection && <div className="v5-gobj">{objection}</div>}
    </div>
  );
}

export default function GateCellGrid({ gates }) {
  if (!gates || gates.length === 0) {
    return <div className="v5-gate-note">no gate evaluation recorded</div>;
  }
  return (
    <div className="v5-gate-grid">
      {gates.map((g) => (
        <GateCell key={g.name} name={g.name} state={g.state} objection={g.objection} />
      ))}
    </div>
  );
}
