import React, { useEffect, useMemo, useState } from "react";
import { fetchRunCard } from "./api.js";
import DeskTab from "./DeskTab.jsx";
import DebateTab from "./DebateTab.jsx";
import PositionsTab from "./PositionsTab.jsx";
import "./App.css";

const TABS = ["DESK", "DEBATE", "POSITIONS", "LEDGER"];

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

function shiftDate(iso, days) {
  // Format from LOCAL date parts — toISOString() converts to UTC, which on
  // IST (+5:30) lands on the previous calendar day: "prev" jumped 2 days and
  // "next" was a no-op.
  const d = new Date(iso + "T00:00:00");
  d.setDate(d.getDate() + days);
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${m}-${day}`;
}

const DAY_COLOR_HEX = {
  green: "var(--positive)",
  red: "var(--danger)",
  yellow: "var(--warn)",
  amber: "var(--warn)",
};

function RegimeChip({ regime }) {
  if (!regime || !regime.mode) {
    return (
      <div className="regime-pill mono">
        <span className="regime-pill-dot" style={{ background: "var(--ink-faint)" }} />
        REGIME —
      </div>
    );
  }
  const age = regime.age_days;
  const dotColor = DAY_COLOR_HEX[(regime.mbi_day_color || "").toLowerCase()] || "var(--accent)";
  return (
    <div className="regime-pill">
      <span className="regime-pill-dot" style={{ background: dotColor }} />
      <span className="regime-pill-mode mono">{regime.mode}</span>
      {age !== null && age !== undefined && <span className="regime-pill-sub">day {age}</span>}
    </div>
  );
}

function XpBadge({ regime }) {
  const xp = regime && regime.xp;
  if (xp === null || xp === undefined) return null;
  return (
    <div className="xp-badge mono" title="[B] Desk readiness score">
      <span className="xp-badge-value">{Math.round(xp)}</span>
      <span className="xp-badge-label">XP</span>
    </div>
  );
}

export default function App() {
  const [date, setDate] = useState(todayIso());
  const [tab, setTab] = useState("DESK");
  const [card, setCard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pipelineRunning, setPipelineRunning] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchRunCard(date)
      .then((data) => {
        if (cancelled) return;
        setCard(data);
        const running = (data.pipeline || []).some((p) => p.status === null || p.status === undefined);
        setPipelineRunning(running);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(String(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [date]);

  const live = useMemo(() => {
    if (!card || !card.signals) return false;
    return card.signals.some((s) => s.sent);
  }, [card]);

  const staleBanner = useMemo(() => {
    if (!card || !card.available) return null;
    const stages = card.pipeline || [];
    const lastBad = stages.find((s) => s.status && s.status !== "ok");
    if (!lastBad) return null;
    return `Data fresh only through ${card.scan_date || card.run_date} — last night's run did not complete.`;
  }, [card]);

  return (
    <div className="shell">
      <header className="shell-header">
        <div className="shell-brand">
          <span className="shell-brand-tick" aria-hidden="true" />
          <span className="shell-title mono">MANAS DESK</span>
        </div>
        <div className="date-scrubber" role="group" aria-label="date scrubber">
          <button onClick={() => setDate((d) => shiftDate(d, -1))} aria-label="previous date">
            ◀
          </button>
          <span className="mono date-scrubber-value">{date}</span>
          <button onClick={() => setDate((d) => shiftDate(d, 1))} aria-label="next date">
            ▶
          </button>
        </div>
        <div className="shell-header-right">
          <RegimeChip regime={card && card.regime} />
          <XpBadge regime={card && card.regime} />
          <span className={"live-badge mono " + (live ? "live" : "dry")}>
            {live ? "● LIVE" : "⦿ DRY-RUN"}
          </span>
        </div>
      </header>
      <nav className="shell-tabs">
        <div className="shell-tabs-inner">
          {TABS.map((t) => (
            <button
              key={t}
              className={"tab-btn" + (t === tab ? " active" : "")}
              onClick={() => setTab(t)}
            >
              {t}
            </button>
          ))}
          <span className="pipeline-status mono">
            {pipelineRunning && (
              <>
                <span className="pipeline-dot" /> pipeline running
              </>
            )}
          </span>
        </div>
      </nav>
      {staleBanner && (
        <div className="stale-banner">
          <span>⚠ {staleBanner}</span>
        </div>
      )}
      <main className="shell-body">
        <div className="shell-body-inner">
          {tab === "DESK" && (
            <DeskTab date={date} card={card} loading={loading} error={error} />
          )}
          {tab === "DEBATE" && <DebateTab date={date} />}
          {tab === "POSITIONS" && <PositionsTab date={date} />}
          {tab === "LEDGER" && <PlaceholderPane label="LEDGER" note="wave F4" />}
        </div>
      </main>
    </div>
  );
}

function PlaceholderPane({ label, note }) {
  return (
    <div className="empty-state">
      <div className="empty-state-icon">◌</div>
      <p className="empty-state-line">{label} tab not built yet.</p>
      <p className="empty-state-sub">{note}</p>
    </div>
  );
}
