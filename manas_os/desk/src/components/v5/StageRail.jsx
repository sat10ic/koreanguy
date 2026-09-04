import React from "react";
import StepRow from "./StepRow.jsx";

export default function StageRail({ steps, jobStatus, onRetry }) {
  const latest = new Map();
  (steps || []).forEach((step) => {
    const prior = latest.get(step.seq);
    if (!prior || Number(step.attempt) >= Number(prior.attempt)) latest.set(step.seq, step);
  });
  const rows = [...latest.values()].sort((a, b) => Number(a.seq) - Number(b.seq));
  return (
    <ol className="v5-stage-rail" aria-label="Update stages">
      {rows.map((step) => (
        <StepRow
          key={step.step_id}
          step={step}
          canRetry={step.status === "fail" && ["partial", "failed", "interrupted"].includes(jobStatus)}
          onRetry={onRetry}
        />
      ))}
    </ol>
  );
}
