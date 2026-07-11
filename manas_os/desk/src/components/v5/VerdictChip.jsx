import React from "react";
import ConvictionDots from "./ConvictionDots.jsx";

// v5 primitive: chair/model verdict chip (TAKE/SKIP), optional struck marker
// + embedded ConvictionDots. verdict must be the server's literal string --
// this component never invents a verdict.
export default function VerdictChip({ verdict, struck = false, conviction, showDots = true }) {
  if (!verdict) return <span className="v5-verdict-chip">{"—"}</span>;
  const tone = verdict === "TAKE" ? "v5-take" : "v5-skip";
  return (
    <span className={"v5-verdict-chip " + tone}>
      {struck && <span className="v5-struck-mark" title="chair verdict struck by risk gate">*</span>}
      {verdict}
      {showDots && conviction !== undefined && <ConvictionDots conviction={conviction} />}
    </span>
  );
}
