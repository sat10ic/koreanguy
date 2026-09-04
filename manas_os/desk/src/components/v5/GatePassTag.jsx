import React from "react";

// v5 primitive: GATE-PASS - PAPER / NEAR-MISS status tag + 9px gate-note line.
// A refused/paper gate-pass must never render as a plain "GATE-PASS" (one-writer
// -for-risk guardrail) -- callers pass `paper` explicitly from the payload.
export default function GatePassTag({ status, paper = false, note }) {
  if (status === "gatepass") {
    return (
      <span className="v5-gatepass-wrap">
        <span className="v5-status-tag v5-gatepass">{paper ? "GATE-PASS · PAPER" : "GATE-PASS"}</span>
        {note && <span className="v5-gate-note">{note}</span>}
      </span>
    );
  }
  if (status === "nearmiss") {
    return (
      <span className="v5-gatepass-wrap">
        <span className="v5-status-tag v5-nearmiss">NEAR-MISS</span>
        {note && <span className="v5-gate-note">{note}</span>}
      </span>
    );
  }
  return <span className="v5-gate-note">{"—"}</span>;
}
