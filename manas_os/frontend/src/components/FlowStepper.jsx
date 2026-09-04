import { useEffect, useState } from "react";
import { getFlowToday } from "../api.js";
import { useDensity } from "../DensityContext.jsx";

/**
 * FlowStepper (plan T3.8) — the Guided Daily Flow.
 *
 * A five-step state-driven walk through the operator's evening, so a beginner
 * never has to ask "what do I do now?". Each step has a status (done / action /
 * blocked / skipped) and the FIRST non-done step expands with its detail + one
 * primary action. The rest collapse to a one-line strip.
 *
 *   ① Data ✓   ② Regime ✓   ③ Positions (1 action!)   ④ Setups (2 to review)   ⑤ Done
 *
 * Beginner: full stepper, always visible above the active screen. Expert:
 * collapses to a single one-line strip (the state is still there, just compact).
 *
 * Backend: /api/flow/today. This component only renders what the backend says —
 * no client-side state inference.
 */
const STATUS_STYLE = {
  done:    { dot: "bg-bull-dot",   text: "text-bull",   label: "✓" },
  action:  { dot: "bg-warn-dot",   text: "text-warn",   label: "!" },
  blocked: { dot: "bg-bear-dot",   text: "text-bear",   label: "✗" },
  skipped: { dot: "bg-hairline2",  text: "text-ink3",   label: "–" },
};

export default function FlowStepper() {
  const [state, setState] = useState({ loading: true, error: null, data: null });
  const { density } = useDensity();
  const expert = density === "expert";

  useEffect(() => {
    let cancelled = false;
    setState({ loading: true, error: null, data: null });
    getFlowToday()
      .then((d) => !cancelled && setState({ loading: false, error: null, data: d }))
      .catch((e) => !cancelled && setState({ loading: false, error: e.message, data: null }));
    return () => { cancelled = true; };
  }, []);

  if (state.loading) {
    return (
      <div data-testid="flow-stepper" className="border border-hairline bg-card px-4 py-2">
        <div className="h-3 w-48 animate-pulse rounded bg-hairline2" />
      </div>
    );
  }
  if (state.error || !state.data) {
    return (
      <div data-testid="flow-stepper" className="border border-hairline bg-card px-4 py-2 font-mono text-[10px] text-ink3">
        flow unavailable
      </div>
    );
  }

  const { steps, current_step: currentId } = state.data;

  // EXPERT: collapse to a single one-line strip (wireframe [E] behavior).
  if (expert) {
    const current = steps.find((s) => s.id === currentId) || steps[steps.length - 1];
    const style = STATUS_STYLE[current.status] || STATUS_STYLE.done;
    return (
      <div data-testid="flow-stepper" className="flex items-center gap-2 border border-hairline bg-card px-4 py-1.5 font-mono text-[10px] uppercase tracking-overline">
        <span className="text-ink3">Today's flow:</span>
        {steps.map((s) => {
          const st = STATUS_STYLE[s.status] || STATUS_STYLE.done;
          return (
            <span key={s.id} className={`flex items-center gap-0.5 ${st.text}`}>
              <span className={`inline-block h-1.5 w-1.5 rounded-full ${st.dot}`} />
              {s.label}
              {s.count != null && s.count > 0 && <span className="tabular-nums">({s.count})</span>}
            </span>
          );
        })}
        <span className={`ml-1 ${style.text}`}>→ {current.label}: {current.detail}</span>
      </div>
    );
  }

  // BEGINNER: full stepper with the current step expanded.
  const current = steps.find((s) => s.id === currentId) || steps[steps.length - 1];

  return (
    <section data-testid="flow-stepper" className="border border-hairline bg-card">
      <div className="border-b border-hairline px-4 py-2">
        <div className="font-mono text-[10px] font-bold uppercase tracking-overline text-ink">
          Today's flow
        </div>
      </div>

      {/* the 5-dot strip */}
      <div className="flex items-center gap-1 px-4 py-2">
        {steps.map((s, i) => {
          const st = STATUS_STYLE[s.status] || STATUS_STYLE.done;
          const isCurrent = s.id === current.id;
          return (
            <div key={s.id} className="flex items-center gap-1">
              <span
                data-testid={`flow-step-${s.id}`}
                className={`flex items-center gap-1 ${isCurrent ? "text-ink" : st.text}`}
              >
                <span className={`inline-flex h-4 w-4 items-center justify-center rounded-full text-[9px] font-bold ${st.dot} ${isCurrent ? "ring-2 ring-ink" : ""} ${s.status === "done" || s.status === "skipped" ? "text-white" : "text-ink"}`}>
                  {i + 1}
                </span>
                <span className="font-mono text-[10px] uppercase tracking-overline">
                  {s.label}
                  {s.count != null && s.count > 0 && (
                    <span className="tabular-nums"> ({s.count})</span>
                  )}
                </span>
              </span>
              {i < steps.length - 1 && <span className="text-hairline2">→</span>}
            </div>
          );
        })}
      </div>

      {/* the current step's expanded detail + primary action */}
      <div className="border-t border-hairline px-4 py-3">
        <div className={`font-sans text-[13px] ${STATUS_STYLE[current.status]?.text || "text-ink2"}`}>
          {current.detail}
        </div>
        {current.status === "action" && current.id === "positions" && (current.actions || []).length > 0 && (
          <div className="mt-2 space-y-1">
            {current.actions.map((a) => (
              <div key={a.symbol} className="border border-bear-border bg-bear-bg px-2 py-1">
                {a.banner && (
                  <div className="mb-1 font-mono text-[10px] font-bold uppercase tracking-overline text-bear">{a.banner}</div>
                )}
                <div className="flex items-center justify-between">
                <span className="font-mono text-[11px] font-bold text-bear">{a.symbol}</span>
                <span className="font-sans text-[11px] text-ink2">EXIT TODAY — {a.reason}</span>
                </div>
              </div>
            ))}
          </div>
        )}
        {current.status === "action" && current.id === "setups" && (
          <div className="mt-2 font-sans text-[12px] text-ink3">
            Open the Setups tab to review tonight's candidates and log TAKEN / SKIPPED.
          </div>
        )}
        {current.status === "action" && current.id === "order_ticket" && current.ticket && (
          <OrderTicket ticket={current.ticket} />
        )}
        {current.status === "blocked" && (
          <div className="mt-2 font-sans text-[12px] text-ink3">
            {current.id === "order_ticket" ? (
              "Log TAKEN on a setup card first; the ticket unlocks after that."
            ) : (
              <>
                Run the pipeline: <code className="font-mono text-[11px]">python manas.py run-eod</code>
              </>
            )}
          </div>
        )}
        {current.status === "done" && current.id === "done" && (
          <div className="mt-1 font-sans text-[12px] text-bull">
            You're done for tonight. Trades logged and snapshots captured.
          </div>
        )}
      </div>
    </section>
  );
}

function OrderTicket({ ticket }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(ticket.copy_text || "");
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  };
  return (
    <div className="mt-2 border border-hairline bg-raised p-2" data-testid="flow-order-ticket">
      <div className="mb-1 font-mono text-[10px] font-bold uppercase tracking-overline text-ink">
        {ticket.symbol} order ticket
      </div>
      <code className="block whitespace-normal break-words border border-hairline bg-card px-2 py-1 font-mono text-[11px] text-ink2">
        {ticket.copy_text}
      </code>
      <button
        type="button"
        onClick={copy}
        className="mt-2 border border-ink bg-ink px-2 py-1 font-mono text-[10px] uppercase tracking-overline text-white"
      >
        {copied ? "copied" : "copy ticket"}
      </button>
    </div>
  );
}
