import React, { useEffect, useMemo, useRef } from "react";
import StageRail from "../components/v5/StageRail.jsx";
import { useDensity } from "../DensityContext.jsx";
import { TERMINAL_JOB_STATUSES, useLiveWork } from "./useJobStream.js";
import "./livework.v5.css";

function statusLabel(status) {
  return status === "succeeded" ? "DONE" : String(status || "IDLE").toUpperCase();
}

function plainEvent(event) {
  const payload = event.payload || {};
  const name = String(payload.name || "").replaceAll("_", " ");
  if (event.event_type === "job_started") return `Started building the ${payload.run_date || "selected"} desk.`;
  if (event.event_type === "step_started") return `Started ${name || "the next stage"}.`;
  if (event.event_type === "step_finished") return `Stage finished${payload.duration_s != null ? ` in ${Number(payload.duration_s).toFixed(1)} seconds` : ""}.`;
  if (event.event_type === "step_failed") return "A stage failed. The update continued to preserve the rest of the night’s work.";
  if (event.event_type === "job_finished") return `Update ${payload.status || "finished"}.`;
  if (event.event_type === "cancel_requested") return "Cancellation requested. The current stage will finish safely first.";
  if (event.event_type === "retry_started") return `Retrying ${name || "the failed stage"} (attempt ${payload.attempt || 2}).`;
  if (event.event_type === "artifact") return payload.label ? `Ready: ${payload.label}.` : "A new result is ready.";
  return String(event.event_type || "Update").replaceAll("_", " ");
}

function formatElapsed(job) {
  if (!job?.started_at) return "not started";
  const start = new Date(`${job.started_at.replace(" ", "T")}Z`).getTime();
  const end = job.finished_at ? new Date(`${job.finished_at.replace(" ", "T")}Z`).getTime() : Date.now();
  const seconds = Math.max(0, Math.round((end - start) / 1000));
  return seconds < 60 ? `${seconds}s elapsed` : `${Math.floor(seconds / 60)}m ${seconds % 60}s elapsed`;
}

export function LiveWorkStrip() {
  const { job, steps, running, setOpen } = useLiveWork();
  if (!job) return null;
  const completed = steps.filter((step) => ["ok", "skip", "fail"].includes(step.status)).length;
  const current = steps.find((step) => step.status === "running");
  if (!running) return null;
  return (
    <button type="button" className="v5-live-strip" onClick={() => setOpen(true)}>
      <span className="v5-live-dot" aria-hidden="true" />
      <span>Building tonight’s desk</span>
      <span className="mono-num">{completed}/{steps.length || "—"}</span>
      <span className="v5-live-stage">{current ? String(current.name).replaceAll("_", " ") : "preparing stages"}</span>
      <span aria-hidden="true">→</span>
    </button>
  );
}

export function LastJobSummary({ compact = false }) {
  const { job, steps, events, setOpen } = useLiveWork();
  if (!job) return <p className="caption-b">No desk update has been recorded yet.</p>;
  const counts = steps.reduce((acc, step) => ({ ...acc, [step.status]: (acc[step.status] || 0) + 1 }), {});
  const finalEvent = [...events].reverse().find((event) => event.event_type === "job_finished");
  return (
    <div className={`v5-last-job${compact ? " v5-last-job-compact" : ""}`}>
      <p><b>{statusLabel(job.status)}</b> · {job.run_date || "date unavailable"}</p>
      <p className="mono-num">{counts.ok || 0} done · {counts.skip || 0} skipped · {counts.fail || 0} failed</p>
      {!compact && finalEvent && <p>{plainEvent(finalEvent)}</p>}
      <button type="button" className="v5-text-action" onClick={() => setOpen(true)}>view activity →</button>
    </div>
  );
}

export default function LiveWorkInspector() {
  const { isExpert } = useDensity();
  const { job, steps, artifacts, events, open, setOpen, loading, error, transport, running, cancel, retry } = useLiveWork();
  const drawerRef = useRef(null);
  const closeRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const previous = document.activeElement;
    closeRef.current?.focus();
    const onKey = (event) => {
      if (event.key === "Escape") setOpen(false);
      if (event.key !== "Tab" || !drawerRef.current) return;
      const focusable = [...drawerRef.current.querySelectorAll("button,[href],summary,[tabindex]:not([tabindex='-1'])")];
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      previous?.focus?.();
    };
  }, [open, setOpen]);

  const recentEvents = useMemo(() => [...events].reverse().slice(0, isExpert ? 80 : 18), [events, isExpert]);
  if (!open) return null;

  return (
    <div className="v5-live-overlay" onMouseDown={(event) => event.target === event.currentTarget && setOpen(false)}>
      <aside ref={drawerRef} className="v5-live-inspector" role="dialog" aria-modal="true" aria-labelledby="live-work-title">
        <header className="v5-live-header">
          <div>
            <p className="v5-live-kicker">LIVE WORK · {transport.toUpperCase()}</p>
            <h2 id="live-work-title">Tonight’s desk update</h2>
            <p>{job ? `${job.run_date || "Selected date"} · ${formatElapsed(job)}` : "Waiting for the first update"}</p>
          </div>
          <div className="v5-live-header-actions">
            {job && <span className={`v5-job-state v5-job-state-${job.status}`}>{statusLabel(job.status)}</span>}
            <button ref={closeRef} type="button" className="v5-live-close" onClick={() => setOpen(false)} aria-label="Close live work inspector">×</button>
          </div>
        </header>

        {loading && <div className="v5-live-skeleton" aria-label="Loading activity"><span /><span /><span /></div>}
        {error && <p className="v5-live-error" role="alert">Live activity is temporarily unavailable. {error}</p>}
        {!loading && !job && <div className="v5-live-idle"><h3>No update recorded yet</h3><p>Run an update to watch every stage complete here without leaving the desk.</p></div>}

        {job && (
          <>
            <section className="v5-live-section">
              <div className="v5-live-section-head"><h3>Stages</h3><span className="mono-num">{steps.filter((s) => s.status === "ok").length}/{steps.length}</span></div>
              <StageRail steps={steps} jobStatus={job.status} onRetry={retry} />
            </section>

            <section className="v5-live-section">
              <div className="v5-live-section-head"><h3>What’s happening</h3><span>{isExpert ? "full detail" : "plain language"}</span></div>
              <div className="v5-event-feed" role="log" aria-live="polite" aria-relevant="additions">
                {recentEvents.length ? recentEvents.map((event) => (
                  <div className={`v5-event-row v5-event-${event.event_type}`} key={event.event_id}>
                    <span className="v5-event-mark" aria-hidden="true" />
                    <div><p>{plainEvent(event)}</p>{isExpert && <span className="mono-num">#{event.event_id} · {event.created_at}</span>}</div>
                    {event.payload?.error && <details><summary>technical detail</summary><p>{event.payload.error}</p></details>}
                  </div>
                )) : <p className="v5-live-muted">The job is queued. Its first stage will appear here.</p>}
              </div>
            </section>

            {artifacts.length > 0 && (
              <section className="v5-live-section">
                <div className="v5-live-section-head"><h3>Results ready</h3><span className="mono-num">{artifacts.length}</span></div>
                <div className="v5-artifacts">{artifacts.map((artifact) => <span key={artifact.artifact_id}>{artifact.label || artifact.kind}</span>)}</div>
              </section>
            )}

            <footer className="v5-live-footer">
              {running && job.status === "running" && <button type="button" className="v5-cancel-action" onClick={cancel}>Cancel after this stage</button>}
              {TERMINAL_JOB_STATUSES.has(job.status) && <p>This update is recorded. You can close this panel; the desk stays in place.</p>}
            </footer>
          </>
        )}
      </aside>
    </div>
  );
}
