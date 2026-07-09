import React, { useEffect, useState } from "react";
import { fetchFeed } from "./api.js";
import { Term, hasGlossaryTerm } from "./Glossary.jsx";

function round(n, digits = 2) {
  if (n === null || n === undefined) return "—";
  const f = Math.pow(10, digits);
  return Math.round(n * f) / f;
}

const DAY_COLOR_HEX = {
  green: "var(--positive)",
  red: "var(--danger)",
  yellow: "var(--warn)",
  amber: "var(--warn)",
};

function xpRead(xp) {
  if (xp === null || xp === undefined) return "XP unavailable";
  if (xp < 15) return `XP ${round(xp, 1)} - weak readiness, most setups should be refused tonight`;
  if (xp < 40) return `XP ${round(xp, 1)} - building readiness, stay selective`;
  if (xp < 100) return `XP ${round(xp, 1)} - strong readiness, breadth can support more risk`;
  return `XP ${round(xp, 1)} - extreme breadth, avoid confusing heat with a clean entry`;
}

function mbiRead(color) {
  const c = (color || "").toUpperCase();
  if (c === "GREEN") return "MBI green - broad strength is supporting the desk.";
  if (c === "RED") return "MBI red - broad weakness is pressing the desk toward defense.";
  if (c === "WHITE") return "MBI white - breadth is mixed, so the desk should be picky.";
  return "MBI unavailable - breadth color was not computed for this run.";
}

function lawRead(governor, openRisk, openCap, familiesLabel) {
  const mode = governor.market_mode || "UNKNOWN";
  if (mode === "NO_TRADE") return "NO_TRADE law - zero cards by design; cash is the trade.";
  const pushes = governor.push_allowed ? "pushes allowed" : "pushes blocked";
  return `${mode} law - up to ${governor.max_cards ?? "-"} cards, ${familiesLabel}, open risk ${openRisk}/${openCap}%, ${pushes}.`;
}

function stageTermKey(actor) {
  const key = `stage-${actor || ""}`;
  return hasGlossaryTerm(key) ? key : null;
}

// SHIP-1 #16 (I1): HAR-RV vol forecast caption, EXPERIMENTAL — only rendered
// when regime.vol_forecast is present (the nightly stage only writes it once
// its walk-forward QLIKE beats the naive-lag baseline; null otherwise, never
// a fabricated number). Never consumed by the governor.
function VolForecastCaption({ vol }) {
  if (!vol || vol.vol_forecast_pct === null || vol.vol_forecast_pct === undefined) return null;
  const bandWord = { rising: "rising", falling: "falling", flat: "flat" }[vol.band] || vol.band;
  return (
    <p className="caption-b vol-forecast-caption">
      [B] <Term k="vol-forecast-experimental">EXPERIMENTAL</Term> vol forecast: {bandWord},{" "}
      {vol.current_vol_pct}&rarr;{vol.vol_forecast_pct}.
    </p>
  );
}

function RegimeStrip({ regime }) {
  if (!regime) return null;
  const ratios = regime.ratios || {};
  const dotColor = DAY_COLOR_HEX[(regime.mbi_day_color || "").toLowerCase()] || "var(--ink-faint)";
  const tooltip = `[B] r4.5 ${round(ratios.r4p5, 2)} · r10 ${round(ratios.r10, 2)}`;
  return (
    <div className="panel">
      <p className="panel-title small-caps">Regime strip</p>
      <div className="metric-tiles">
        <div className="metric-tile" title={tooltip}>
          <span className="metric-tile-label overline">
            <Term k="mbi-day-color">MBI day-color</Term>
          </span>
          <div className="metric-tile-value-row">
            <span className="metric-tile-dot" style={{ background: dotColor }} />
            <span className="metric-tile-value">{regime.mbi_day_color || "—"}</span>
          </div>
        </div>
        <div className="metric-tile">
          <span className="metric-tile-label overline">
            <Term k="xp">XP</Term>
          </span>
          <div className="metric-tile-value-row">
            <span className="metric-tile-value mono">
              {regime.xp === null || regime.xp === undefined ? "—" : Math.round(regime.xp)}
            </span>
            <span className="metric-tile-trend up">▲</span>
          </div>
        </div>
        <div className="metric-tile">
          <span className="metric-tile-label overline">
            <Term k="r20">r20</Term>
          </span>
          <div className="metric-tile-value-row">
            <span className="metric-tile-value mono">{round(ratios.r20, 2)}</span>
          </div>
        </div>
        <div className="metric-tile">
          <span className="metric-tile-label overline">
            <Term k="r50">r50</Term>
          </span>
          <div className="metric-tile-value-row">
            <span className="metric-tile-value mono">{round(ratios.r50, 2)}</span>
          </div>
        </div>
      </div>
      <p className="caption-b">
        [B] {mbiRead(regime.mbi_day_color)} {xpRead(regime.xp)}. <Term k="r10">R10</Term> {round(ratios.r10, 2)}, <Term k="r20">R20</Term> {round(ratios.r20, 2)}, <Term k="r50">R50</Term> {round(ratios.r50, 2)}, <Term k="r4.5">R4.5</Term> {round(ratios.r4p5, 2)}.
      </p>
      <VolForecastCaption vol={regime.vol_forecast} />
    </div>
  );
}

function LawRow({ governor, heat }) {
  if (!governor) return null;
  const riskBand = governor.risk_band || {};
  const riskLabel =
    riskBand.base_pct !== null && riskBand.base_pct !== undefined
      ? `${round(riskBand.base_pct, 2)}-${round(riskBand.hard_max_pct, 2)}%`
      : "—";
  const familiesLabel = (governor.allowed_families || []).length
    ? governor.allowed_families.map((f) => f.toUpperCase()).join(" · ")
    : "NONE";
  const openRisk = heat && heat.open_risk_pct !== null && heat.open_risk_pct !== undefined
    ? round(heat.open_risk_pct, 1)
    : "—";
  const openCap = heat && heat.cap_pct !== null && heat.cap_pct !== undefined
    ? round(heat.cap_pct, 1)
    : round(governor.open_risk_cap_pct, 1);
  const pushOn = !!governor.push_allowed;
  const tooltip = governor.message || `[B] ${governor.market_mode} — the day's law, from the governor.`;

  return (
    <div className="panel law-panel" title={tooltip}>
      <p className="panel-title small-caps">Today's law</p>
      <div className="metric-tiles">
        <div className="metric-tile">
          <span className="metric-tile-label overline">
            <Term k="law-max-cards">Max cards</Term>
          </span>
          <div className="metric-tile-value-row">
            <span className="law-tile-value mono">{governor.max_cards ?? "—"}</span>
          </div>
        </div>
        <div className="metric-tile">
          <span className="metric-tile-label overline">
            <Term k="law-risk-trade">Risk/trade</Term>
          </span>
          <div className="metric-tile-value-row">
            <span className="law-tile-value mono">{riskLabel}</span>
          </div>
        </div>
        <div className="metric-tile">
          <span className="metric-tile-label overline">
            <Term k="law-allowed-families">Allowed</Term>
          </span>
          <div className="metric-tile-value-row">
            <span className="law-tile-value mono">{familiesLabel}</span>
          </div>
        </div>
        <div className="metric-tile">
          <span className="metric-tile-label overline">
            <Term k="law-open-risk">Open-risk</Term>
          </span>
          <div className="metric-tile-value-row">
            <span className="law-tile-value mono">
              {openRisk}/{openCap}%
            </span>
          </div>
        </div>
        <div className="metric-tile">
          <span className="metric-tile-label overline">
            <Term k="law-pushes">Pushes</Term>
          </span>
          <div className="metric-tile-value-row">
            <span className={"law-tile-value mono " + (pushOn ? "push-on" : "push-off")}>
              {pushOn ? "ON" : "OFF"}
            </span>
          </div>
        </div>
      </div>
      <p className="caption-b">[B] {lawRead(governor, openRisk, openCap, familiesLabel)}</p>
    </div>
  );
}

function agentKey(actor) {
  return (actor || "").toLowerCase();
}

function ExpandGrid({ data }) {
  if (!data || typeof data !== "object") {
    return <div className="expand-grid-value mono">{String(data ?? "—")}</div>;
  }
  const entries = Object.entries(data);
  if (entries.length === 0) {
    return <div className="expand-grid-value mono">—</div>;
  }
  return (
    <div className="expand-grid">
      {entries.map(([k, v]) => (
        <React.Fragment key={k}>
          <span className="expand-grid-key mono">{k}</span>
          <span className="expand-grid-value mono">
            {v !== null && typeof v === "object" ? JSON.stringify(v) : String(v ?? "—")}
          </span>
        </React.Fragment>
      ))}
    </div>
  );
}

function ActivityRow({ event }) {
  const [open, setOpen] = useState(false);
  const ts = (event.ts || "").slice(11, 16) || (event.ts || "").slice(0, 5);
  const actorTerm = stageTermKey(event.actor);
  return (
    <div className="activity-row" onClick={() => setOpen((o) => !o)}>
      <span className={"activity-row-rail-dot state-dot " + event.state} data-state={event.state} />
      <div className="activity-row-body">
        <div className="activity-row-top">
          <span className="ts mono">{ts}</span>
          <span
            className="actor agent-chip mono"
            data-agent={agentKey(event.actor)}
            title={event.actor}
          >
            {actorTerm ? <Term k={actorTerm}>{event.actor}</Term> : event.actor}
          </span>
          <span className="line">{event.line}</span>
          <span className="expand-caret">{open ? "▾" : "▸"}</span>
        </div>
        {open && (
          <div className="expand-detail">
            <ExpandGrid data={event.expand} />
          </div>
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
    return (
      <div className="empty-state">
        <div className="empty-state-icon">⚠</div>
        <p className="empty-state-line">Could not load the desk.</p>
        <p className="empty-state-sub">{error}</p>
      </div>
    );
  }
  if (!card || !card.available) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">◌</div>
        <p className="empty-state-line">No run for {date} yet.</p>
        <p className="empty-state-sub">The desk runs after market close (~18:30).</p>
      </div>
    );
  }

  return (
    <div>
      <div className="brief-card">
        <p className="overline accent" style={{ marginBottom: "8px" }}>
          <Term k="morning-brief">Morning brief</Term>
        </p>
        <p className="brief-body">{card.morning_brief || "—"}</p>
      </div>

      <div style={{ height: "var(--gap-m)" }} />

      <RegimeStrip regime={card.regime} />

      <div style={{ height: "var(--gap-m)" }} />

      <LawRow governor={card.governor} heat={card.heat} />

      <DegradedPanel card={card} />

      <div className="panel">
        <p className="panel-title small-caps">
          <Term k="activity-stream">Activity stream</Term>
        </p>
        {feedLoading && <p className="empty-state">Loading feed…</p>}
        {feedError && <p className="empty-state">{feedError}</p>}
        {!feedLoading && !feedError && feed.length === 0 && (
          <div className="empty-state">
            <div className="empty-state-icon">◌</div>
            <p className="empty-state-line">No activity recorded for {date}.</p>
          </div>
        )}
        {!feedLoading && !feedError && feed.length > 0 && (
          <div className="timeline">
            <span className="timeline-rail" />
            {feed.map((event, idx) => (
              <ActivityRow key={idx} event={event} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
