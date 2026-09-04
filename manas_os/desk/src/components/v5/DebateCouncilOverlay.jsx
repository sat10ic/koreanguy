import React from "react";
import DebateLivePanel from "./DebateLivePanel.jsx";
import "./DebateCouncilOverlay.v5.css";

// DebateCouncilOverlay: the slide-over that makes every "push to debate"
// action observable regardless of which tab it was fired from (DEBATE push
// form, ALPHA rows, SHORTLIST rows). One push = one queue entry; the panel
// streams whichever entry is currently focused (liveWork tracks a single
// job at a time), and other queued pushes wait as clickable rows in the
// header until focused. Wave2 spec I. DEBATE LIVE THEATER.
export default function DebateCouncilOverlay({ open, queue, focusedId, onFocus, onClose, onRetry, onViewCard, onDismiss }) {
  if (!open || !queue || queue.length === 0) return null;
  const focused = queue.find((entry) => entry.id === focusedId) || queue[queue.length - 1];

  return (
    <div className="v5-council-overlay" role="dialog" aria-label="Council push queue">
      <div className="v5-council-overlay-backdrop" onClick={onClose} />
      <div className="v5-council-overlay-panel">
        <header className="v5-council-overlay-header">
          <div>
            <span className="v5-live-kicker">COUNCIL PUSH QUEUE</span>
            <h3>{queue.length} push{queue.length === 1 ? "" : "es"} this session</h3>
          </div>
          <button type="button" className="v5-council-overlay-close" onClick={onClose} aria-label="Close council panel">
            &times;
          </button>
        </header>

        {queue.length > 1 && (
          <div className="v5-council-queue-list" role="list">
            {queue.map((entry) => (
              <button
                type="button"
                key={entry.id}
                role="listitem"
                className={
                  "v5-council-queue-chip" +
                  (entry.id === focused.id ? " v5-council-queue-chip--active" : "") +
                  (entry.status === "failed" ? " v5-council-queue-chip--failed" : "") +
                  (entry.status === "done" ? " v5-council-queue-chip--done" : "")
                }
                onClick={() => onFocus(entry.id)}
                title={`${entry.symbol} — ${entry.status}`}
              >
                <span className="v5-council-queue-dot" aria-hidden="true" />
                {entry.symbol}
                <span className="v5-council-queue-status">{entry.status}</span>
              </button>
            ))}
          </div>
        )}

        <div className="v5-council-overlay-body">
          {focused.jobId ? (
            <DebateLivePanel
              symbol={focused.symbol}
              jobId={focused.jobId}
              onRetry={() => onRetry(focused.symbol)}
              onViewCard={() => onViewCard(focused)}
            />
          ) : focused.status === "failed" ? (
            <div className="v5-council-fallback alpha-error alpha-state">
              <b>{focused.symbol} could not be pushed.</b>
              <span>{focused.error || "The push request failed before a council run could start."}</span>
              <button type="button" className="v5-debate-retry-btn" onClick={() => onRetry(focused.symbol)}>
                Retry
              </button>
            </div>
          ) : focused.status === "done" ? (
            <div className="v5-council-fallback alpha-state">
              <b>{focused.symbol} already has a debate card for this date.</b>
              <span>No new council run was needed — the existing verdicts are on DECIDE.</span>
              <button type="button" className="v5-debate-view-btn" onClick={() => onViewCard(focused)}>
                View card on DECIDE
              </button>
            </div>
          ) : (
            <div className="v5-debate-empty">
              <p>Sending {focused.symbol} to the council...</p>
              <span className="v5-live-dot" />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
