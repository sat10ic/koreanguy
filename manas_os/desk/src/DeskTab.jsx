import React, { useEffect, useState } from "react";
import { fetchFeed } from "./api.js";

function round(n, digits = 2) {
  if (n === null || n === undefined) return "—";
  const f = Math.pow(10, digits);
  return Math.round(n * f) / f;
}

function RegimeStrip({ regime }) {
  if (!regime) return null;
  const ratios = regime.ratios || {};
  return (
    <div className="panel">
      <p className="panel-title small-caps">Regime strip</p>
      <div className="regime-strip mono">
        <span>● MBI day-color {regime.mbi_day_color || "—"}</span>
        <span>
          r4.5 {round(ratios.r4p5, 2)} · r10 {round(ratios.r10, 2)} · r20 {round(ratios.r20, 2)} · r50{" "}
          {round(ratios.r50, 2)}
        </span>
        <span>XP {regime.xp === null || regime.xp === undefined ? "—" : Math.round(regime.xp)} ▲</span>
      </div>
      <p className="caption-b">
        [B] MBI = how broad the market's strength is today. XP = the desk's readiness score.
      </p>
    </div>
  );
}

function agentKey(actor) {
  return (actor || "").toLowerCase();
}

function ActivityRow({ event }) {
  const [open, setOpen] = useState(false);
  const ts = (event.ts || "").slice(11, 16) || (event.ts || "").slice(0, 5);
  return (
    <div className="activity-row" onClick={() => setOpen((o) => !o)}>
      <div style={{ width: "100%" }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: "8px" }}>
          <span className="ts mono">{ts}</span>
          <span className={"state-dot " + event.state} data-state={event.state} />
          <span className="actor agent-chip mono" data-agent={agentKey(event.actor)}>
            {event.actor}
          </span>
          <span className="line">{event.line}</span>
          <span className="expand-caret">{open ? "▾" : "▸"}</span>
        </div>
        {open && (
          <pre className="expand-detail mono">{JSON.stringify(event.expand, null, 2)}</pre>
        )}
      </div>
    </div>
  );
}

function DegradedPanel({ card }) {
  const errors = card.errors || [];
  if (!errors.length) return null;
  const chairStruck = (card.chair || []).filter((c) => c.struck).length;
  const chairTotal = (card.chair || []).length;
  return (
    <div className="panel degraded-panel">
      <p className="panel-title small-caps">Degraded night</p>
      <p>
        Thin night. Shortlist of {(card.shortlist || []).length}.{" "}
        {chairTotal ? `Chair struck ${chairStruck}/${chairTotal}.` : ""} This is a normal quiet
        night.
      </p>
      <div className="chip-row">
        {(card.debate || []).map((d) => (
          <span key={d.model} className="agent-chip" data-agent={agentKey(d.model)}>
            {d.model} {d.parsed_ok === d.verdicts ? "done" : `failed ${d.verdicts - (d.parsed_ok || 0)}`}
          </span>
        ))}
        {errors.map((e, idx) => (
          <span key={idx} className="agent-chip">
            {e.stage} · {e.detail || "error"}
          </span>
        ))}
      </div>
    </div>
  );
}

export default function DeskTab({ date, card, loading, error }) {
  const [feed, setFeed] = useState([]);
  const [feedLoading, setFeedLoading] = useState(true);
  const [feedError, setFeedError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setFeedLoading(true);
    fetchFeed(date)
      .then((data) => {
        if (!cancelled) setFeed(data.events || []);
      })
      .catch((err) => {
        if (!cancelled) setFeedError(String(err));
      })
      .finally(() => {
        if (!cancelled) setFeedLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [date]);

  if (loading) {
    return <div className="empty-state">Loading…</div>;
  }
  if (error) {
    return <div className="empty-state">{error}</div>;
  }
  if (!card || !card.available) {
    return (
      <div className="empty-state">
        No run for {date} yet. The desk runs after market close (~18:30).
      </div>
    );
  }

  return (
    <div>
      <div className="panel">
        <p className="panel-title small-caps">Morning brief</p>
        <p>{card.morning_brief || "—"}</p>
      </div>

      <RegimeStrip regime={card.regime} />

      <DegradedPanel card={card} />

      <div className="panel">
        <p className="panel-title small-caps">Activity stream</p>
        {feedLoading && <p className="empty-state">Loading feed…</p>}
        {feedError && <p className="empty-state">{feedError}</p>}
        {!feedLoading && !feedError && feed.length === 0 && (
          <p className="empty-state">No activity recorded for {date}.</p>
        )}
        {!feedLoading &&
          !feedError &&
          feed.map((event, idx) => <ActivityRow key={idx} event={event} />)}
      </div>
    </div>
  );
}
