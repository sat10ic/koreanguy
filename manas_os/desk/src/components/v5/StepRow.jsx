import React from "react";

const STATUS = {
  pending: ["○", "waiting"], running: ["●", "running"], ok: ["✓", "done"],
  fail: ["×", "failed"], skip: ["–", "skipped"], cancelled: ["■", "cancelled"],
};

export default function StepRow({ step, canRetry, onRetry }) {
  const [glyph, label] = STATUS[step.status] || ["○", step.status || "waiting"];
  return (
    <li className={`v5-step-row v5-step-${step.status || "pending"}`}>
      <span className="v5-step-mark" aria-hidden="true">{glyph}</span>
      <span className="v5-step-copy">
        <span className="v5-step-name">{String(step.name || "step").replaceAll("_", " ")}</span>
        <span className="v5-step-state">{label}{step.attempt > 1 ? ` · attempt ${step.attempt}` : ""}</span>
      </span>
      <span className="v5-step-metrics mono-num">
        {step.duration_s != null ? `${Number(step.duration_s).toFixed(1)}s` : ""}
        {step.rows_affected != null ? ` · ${step.rows_affected} rows` : ""}
      </span>
      {canRetry && <button type="button" className="v5-text-action" onClick={() => onRetry(step.step_id)}>retry</button>}
      {step.error && <details className="v5-step-error"><summary>why it failed</summary><p>{step.error}</p></details>}
    </li>
  );
}
