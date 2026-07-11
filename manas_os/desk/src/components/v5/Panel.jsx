import React from "react";

// v5 primitive: generic bordered panel + header (title + right-aligned italic
// mono "cite" slot for source provenance) + body.
export function PanelHeader({ title, cite }) {
  return (
    <div className="v5-panel-hd">
      <span className="v5-t">{title}</span>
      {cite && <span className="v5-cite">{cite}</span>}
    </div>
  );
}

export default function Panel({ title, cite, children, className = "" }) {
  return (
    <div className={"v5-panel" + (className ? " " + className : "")}>
      {(title || cite) && <PanelHeader title={title} cite={cite} />}
      <div className="v5-panel-bd">{children}</div>
    </div>
  );
}
