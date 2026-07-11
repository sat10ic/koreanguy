import React from "react";

// v5 primitive: small status chip used in the CommandStrip and elsewhere.
// tone: "green" | "amber" | "red" | "neutral" (default neutral -> no dot color override)
// qual: italic "qualitative" value styling for values that are not a hard number
export default function StatusChip({ label, value, tone = "neutral", qual = false, title, dot = true }) {
  const toneClass = tone && tone !== "neutral" ? ` v5-tone-${tone}` : "";
  return (
    <div className={"v5-status-chip" + toneClass} title={title}>
      {dot && <span className="v5-dot" aria-hidden="true" />}
      {label && <span className="v5-lbl">{label}</span>}
      <span className={"v5-val" + (qual ? " v5-qual" : "")}>{value ?? "—"}</span>
    </div>
  );
}
