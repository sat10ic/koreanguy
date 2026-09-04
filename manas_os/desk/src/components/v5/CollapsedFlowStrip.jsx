import React from "react";

// CollapsedFlowStrip: expert-mode single-line status bar for the guided flow.
// Shows the current step label + status, plus a count of done/total steps.
// Clicking expands to show the active step's detail inline.
export default function CollapsedFlowStrip({ steps, currentStep }) {
  if (!steps || steps.length === 0) return null;

  const done   = steps.filter((s) => s.status === "done").length;
  const total  = steps.length;
  const active = steps.find((s) => s.id === currentStep) || steps.find((s) => s.status === "action");
  const isDone = done === total;

  return (
    <div className="gfr-strip" aria-label="Workflow status">
      <span className="gfr-strip-progress mono">
        {done}/{total}
      </span>
      <span className="gfr-strip-sep" aria-hidden="true">·</span>
      {isDone ? (
        <span className="gfr-strip-status gfr-strip-status--done">ALL DONE</span>
      ) : active ? (
        <>
          <span className="gfr-strip-step">{active.label || active.id}</span>
          {active.detail && (
            <>
              <span className="gfr-strip-sep" aria-hidden="true">—</span>
              <span className="gfr-strip-detail">{active.detail}</span>
            </>
          )}
        </>
      ) : (
        <span className="gfr-strip-status">No pending actions</span>
      )}
    </div>
  );
}
