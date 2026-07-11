import React from "react";

// v5 primitive: 4-up mechanism lens cells (label, verdict value, micro
// progress bar, description). `lenses`: [{ label, value, pct, desc }].
// Only lanes the payload can back are rendered -- callers must omit lanes
// with no real data rather than fabricate a verdict.
export default function LensLane({ lenses }) {
  if (!lenses || lenses.length === 0) {
    return <div className="v5-lens-wrap"><div className="v5-lens"><div className="v5-ld">{"— N/A / not triggered"}</div></div></div>;
  }
  return (
    <div className="v5-lens-wrap">
      <div className="v5-lens-grid">
        {lenses.map((l) => (
          <div className="v5-lens" key={l.label}>
            <div className="v5-lh">{l.label}</div>
            <div className="v5-lv">{l.value ?? "—"}</div>
            {l.pct !== undefined && l.pct !== null && (
              <div className="v5-lbar">
                <div style={{ width: `${Math.max(0, Math.min(100, l.pct))}%` }} />
              </div>
            )}
            {l.desc && <div className="v5-ld">{l.desc}</div>}
          </div>
        ))}
      </div>
    </div>
  );
}
