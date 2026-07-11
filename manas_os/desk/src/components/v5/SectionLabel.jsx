import React from "react";

// v5 primitive: italic Fraunces section header + gradient rule + optional count pill.
export default function SectionLabel({ children, count }) {
  return (
    <div className="v5-sec-label">
      <span className="v5-txt">{children}</span>
      <span className="v5-rule" aria-hidden="true" />
      {count !== undefined && count !== null && <span className="v5-count">{count}</span>}
    </div>
  );
}
