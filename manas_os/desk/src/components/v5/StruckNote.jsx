import React from "react";

// v5 primitive: teal-edged chair-strike quote block -- renders the true
// pre-strike -> strike-reason -> post-strike story from the payload.
export default function StruckNote({ children }) {
  if (!children) return null;
  return <div className="v5-struck-note">{children}</div>;
}
