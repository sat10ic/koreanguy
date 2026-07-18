import React, { useEffect, useMemo, useRef, useState } from "react";
import { useLiveWork, TERMINAL_JOB_STATUSES } from "../../livework/useJobStream.js";
import StatusBadge from "./StatusBadge.jsx";
import StageRail from "./StageRail.jsx";
import "./DebateLivePanel.v5.css";

const STALL_MS = 60000;

// DebateLivePanel: displays real-time progress of an on-demand council debate.
// Subscribes to the liveWork context to display stages, model verdicts, and adjudication.
// onRetry / onViewCard are optional -- callers that can't retry or navigate
// (e.g. a read-only replay) simply omit them and the affordances don't render.
export default function DebateLivePanel({ symbol, jobId, onComplete, onRetry, onViewCard }) {
  const liveWork = useLiveWork();
  const job = liveWork.job;
  const steps = liveWork.steps;
  const events = liveWork.events;

  const isCurrentJob = job && job.job_id === jobId;
  const isTerminal = job && TERMINAL_JOB_STATUSES.has(job.status);

  // Trigger onComplete once job succeeds
  useEffect(() => {
    if (isCurrentJob && isTerminal && job.status === "succeeded") {
      if (onComplete) onComplete();
    }
  }, [isCurrentJob, isTerminal, job?.status, onComplete]);

  // Stall honesty (Wave2 spec I-2/I-3): the event stream can go quiet without
  // the job ever failing (a slow model, a stuck queue). Rather than spin
  // forever, count real wall-clock seconds since the last event WE received
  // and say so once it crosses 60s. Never invented progress -- just honesty
  // about silence.
  const lastEventAtRef = useRef(Date.now());
  const eventCount = events.length;
  useEffect(() => {
    lastEventAtRef.current = Date.now();
  }, [eventCount]);
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    if (!isCurrentJob || isTerminal) return undefined;
    const id = setInterval(() => setNow(Date.now()), 2000);
    return () => clearInterval(id);
  }, [isCurrentJob, isTerminal]);
  const stalledMs = isCurrentJob && !isTerminal ? now - lastEventAtRef.current : 0;
  const isStalled = stalledMs >= STALL_MS;

  const chairDetail = useMemo(
    () => (steps || []).find((s) => s.name === "chair_adjudication")?.detail || null,
    [steps]
  );

  // Extract verdicts from events
  const seatVerdicts = useMemo(() => {
    if (!isCurrentJob) return {};
    const verdicts = {};
    events.forEach((ev) => {
      if (ev.event_type === "seat_verdict") {
        const p = ev.payload || {};
        if (p.model) {
          verdicts[p.model] = { status: "done", verdict: p.verdict, conviction: p.conviction };
        }
      } else if (ev.event_type === "seat_failed") {
        const p = ev.payload || {};
        if (p.model) {
          verdicts[p.model] = { status: "failed", error: p.error };
        }
      }
    });
    return verdicts;
  }, [events, isCurrentJob]);

  if (!isCurrentJob) {
    return (
      <div className="v5-debate-empty">
        <p>Connecting to debate stream for {symbol}...</p>
        <span className="v5-live-dot" />
      </div>
    );
  }

  // Visual seats configuration based on registered models or returned verdicts
  const modelKeys = Object.keys(seatVerdicts);
  // Default fallbacks if no events returned yet
  const displayModels = modelKeys.length > 0 ? modelKeys : ["deepseek-r1", "gpt-4o", "gemini-1.5-pro"];

  return (
    <div className="v5-debate-live-panel">
      <header className="v5-debate-live-header">
        <div>
          <span className="v5-live-kicker">LIVE DEBATE ON-DEMAND</span>
          <h2>Analyzing {symbol}</h2>
          <p className="alpha-explain">
            Watch the AI seats construct the visual-behavioural thesis. Planned stop/target/risk numbers are verbatim.
          </p>
        </div>
        <div className="v5-debate-live-status">
          <StatusBadge status={job.status === "running" ? "LIVE" : "SHADOW"} />
        </div>
      </header>

      {isStalled && (
        <p className="v5-debate-stall" role="status">
          still waiting on the council ({Math.floor(stalledMs / 1000)}s)…
        </p>
      )}

      <div className="v5-debate-live-layout">
        {/* Left column: Stepper */}
        <section className="v5-debate-live-stages">
          <h3>DEBATE PROGRESS</h3>
          <StageRail steps={steps} jobStatus={job.status} />
        </section>

        {/* Right column: Council Seats */}
        <section className="v5-debate-live-seats">
          <h3>COUNCIL MEMBERS</h3>
          <div className="v5-debate-seats-grid">
            {displayModels.map((model) => {
              const res = seatVerdicts[model];
              const isDone = res?.status === "done";
              const isFailed = res?.status === "failed";
              const isPending = !res;

              let cardClass = "v5-seat-card";
              if (isDone) cardClass += " v5-seat-card--done";
              if (isFailed) cardClass += " v5-seat-card--failed";
              if (isPending) cardClass += " v5-seat-card--pending";

              return (
                <div key={model} className={cardClass}>
                  <div className="v5-seat-header">
                    <span className="v5-seat-name">{model.split("/").pop()}</span>
                    {isDone && (
                      <span className={`v5-seat-badge v5-seat-badge--${res.verdict.toLowerCase()}`}>
                        {res.verdict} c{res.conviction}
                      </span>
                    )}
                    {isFailed && <span className="v5-seat-badge v5-seat-badge--fail">FAIL</span>}
                    {isPending && <span className="v5-seat-badge v5-seat-badge--wait">REASONING...</span>}
                  </div>
                  <div className="v5-seat-body">
                    {isDone && <p className="v5-seat-verdict-note">Verdict returned successfully.</p>}
                    {isFailed && <p className="v5-seat-error-note">{res.error || "LLM request failed."}</p>}
                    {isPending && (
                      <div className="v5-seat-loading">
                        <div className="v5-live-dot" />
                        <span>Analysing chart behaviours...</span>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      </div>

      {job.status === "failed" && (
        <div className="alpha-error alpha-state">
          <b>Debate job failed.</b>
          <span>{job.error || "An unknown error occurred during debate execution."}</span>
          {onRetry && (
            <button type="button" className="v5-debate-retry-btn" onClick={onRetry}>
              Retry
            </button>
          )}
        </div>
      )}

      {isTerminal && job.status === "succeeded" && (
        <div className="v5-debate-done-banner">
          <b>Chair verdict logged for {symbol}.</b>
          <span>{chairDetail || "Council finished — verdicts and chair adjudication are recorded."}</span>
          {onViewCard && (
            <button type="button" className="v5-debate-view-btn" onClick={onViewCard}>
              View card on DECIDE
            </button>
          )}
        </div>
      )}
    </div>
  );
}
