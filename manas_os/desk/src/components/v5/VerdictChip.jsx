import React from "react";
import ConvictionDots from "./ConvictionDots.jsx";

// v5 primitive: chair/model verdict chip (TAKE/SKIP), optional struck marker
// + embedded ConvictionDots. verdict must be the server's literal string --
// this component never invents a verdict.
export default function VerdictChip({
  verdict,
  struck = false,
  conviction,
  showDots = true,
  tone,
  label,
  children
}) {
  const displayLabel = children || label || verdict;
  if (!displayLabel) return <span className="v5-verdict-chip">{"—"}</span>;

  let toneClass = "";
  if (tone !== undefined) {
    toneClass = tone;
  } else if (verdict === "TAKE") {
    toneClass = "v5-take";
  } else if (verdict === "SKIP") {
    toneClass = "v5-skip";
  }

  return (
    <span className={"v5-verdict-chip " + toneClass}>
      {struck && <span className="v5-struck-mark" title="chair verdict struck by risk gate">*</span>}
      {displayLabel}
      {showDots && conviction !== undefined && <ConvictionDots conviction={conviction} />}
    </span>
  );
}
