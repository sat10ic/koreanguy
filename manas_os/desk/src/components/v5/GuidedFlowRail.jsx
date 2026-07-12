import React from "react";

// Status → display mapping for the guided flow rail.
// Source: /api/flow/today step.status field (done | action | blocked | skipped).
const STATUS_META = {
  done:    { icon: "✓", cls: "gfr-step--done",    label: "Done"    },
  action:  { icon: "●", cls: "gfr-step--action",  label: "Action"  },
  blocked: { icon: "○", cls: "gfr-step--blocked", label: "Blocked" },
  skipped: { icon: "—", cls: "gfr-step--skipped", label: "Skipped" },
};

function actionLabel(step) {
  // Generate a primary action label from the step id + detail payload.
  // Never show financial advice; only describe the tool action.
  const id = step.id || "";
  if (id === "data")        return "Run EOD update →";
  if (id === "regime")      return "Review regime →";
  if (id === "positions") {
    const exits = (step.actions || []).filter((a) => a && (a.banner || a.reason));
    return exits.length
      ? `Review ${exits.length} flagged position${exits.length > 1 ? "s" : ""} →`
      : "Review positions →";
  }
  if (id === "setups")      return step.count ? `Review ${step.count} setup${step.count !== 1 ? "s" : ""} →` : "Review setups →";
  if (id === "order_ticket") return step.ticket?.symbol ? `Open trade plan: ${step.ticket.symbol} →` : "Open trade plan →";
  if (id === "done")        return null; // terminal step — no action button
  return "Go →";
}

function tabForStep(id) {
  if (id === "data")         return null;         // triggers update, no tab
  if (id === "regime")       return "MARKET";
  if (id === "positions")    return "POSITIONS";
  if (id === "setups")       return "DEBATE";
  if (id === "order_ticket") return "DEBATE";     // opens trade plan from debate
  return null;
}

// GuidedFlowRail: left-side vertical stepper visible in beginner mode.
// Props:
//   steps      — array of step objects from /api/flow/today
//   currentStep — id of the current step (first non-done)
//   onNavigate  — (tab) => void
//   onStartUpdate — () => void  (for the "data" step)
//   onOpenTradePlan — (symbol) => void  (Handoff 13 task D: order_ticket step
//     routes straight to the TRADE PLAN route instead of the DEBATE tab)
export default function GuidedFlowRail({ steps, currentStep, onNavigate, onStartUpdate, onOpenTradePlan }) {
  if (!steps || steps.length === 0) return null;

  return (
    <aside className="gfr-rail" aria-label="Daily workflow guide">
      <div className="gfr-header">
        <span className="gfr-header-eyebrow">TODAY'S WORKFLOW</span>
      </div>
      <ol className="gfr-steps" role="list">
        {steps.map((step, idx) => {
          const meta   = STATUS_META[step.status] || STATUS_META.blocked;
          const isActive = step.id === currentStep;
          const btnLabel = actionLabel(step);
          const targetTab = tabForStep(step.id);

          return (
            <li
              key={step.id || idx}
              className={[
                "gfr-step",
                meta.cls,
                isActive ? "gfr-step--active" : "",
              ].filter(Boolean).join(" ")}
            >
              <div className="gfr-step-head">
                <span className="gfr-step-icon" aria-hidden="true">{meta.icon}</span>
                <span className="gfr-step-label">{step.label || step.id}</span>
                {step.count != null && step.count > 0 && (
                  <span className="gfr-step-count">{step.count}</span>
                )}
              </div>

              {isActive && step.detail && (
                <p className="gfr-step-detail">{step.detail}</p>
              )}

              {isActive && step.status === "action" && step.id === "positions" &&
                (step.actions || []).map((a, ai) => a && (
                  <div key={ai} className="gfr-step-flag">
                    <span className="gfr-flag-symbol">{a.symbol}</span>
                    {a.banner && <span className="gfr-flag-reason">{a.banner}</span>}
                  </div>
                ))
              }

              {isActive && btnLabel && (
                <button
                  className="gfr-step-action"
                  onClick={() => {
                    if (step.id === "data") { onStartUpdate && onStartUpdate(); return; }
                    if (step.id === "order_ticket" && step.ticket?.symbol && onOpenTradePlan) {
                      onOpenTradePlan(step.ticket.symbol);
                      return;
                    }
                    if (targetTab) onNavigate && onNavigate(targetTab);
                  }}
                >
                  {btnLabel}
                </button>
              )}
            </li>
          );
        })}
      </ol>
    </aside>
  );
}
