import React, { useEffect, useState } from "react";
import { fetchFeed } from "./api.js";

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
          <span className="metric-tile-label overline">MBI day-color</span>
          <div className="metric-tile-value-row">
            <span className="metric-tile-dot" style={{ background: dotColor }} />
            <span className="metric-tile-value">{regime.mbi_day_color || "—"}</span>
          </div>
        </div>
        <div className="metric-tile">
          <span className="metric-tile-label overline">XP</span>
          <div className="metric-tile-value-row">
            <span className="metric-tile-value mono">
              {regime.xp === null || regime.xp === undefined ? "—" : Math.round(regime.xp)}
            </span>
            <span className="metric-tile-trend up">▲</span>
          </div>
        </div>
        <div className="metric-tile">
          <span className="metric-tile-label overline">r20</span>
          <div className="metric-tile-value-row">
            <span className="metric-tile-value mono">{round(ratios.r20, 2)}</span>
          </div>
        </div>
        <div className="metric-tile">
          <span className="metric-tile-label overline">r50</span>
          <div className="metric-tile-value-row">
            <span className="metric-tile-value mono">{round(ratios.r50, 2)}</span>
          </div>
        </div>
      </div>
      <p className="caption-b">
        [B] MBI = how broad the market's strength is today. XP = the desk's readiness score.
      </p>
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
          <span className="metric-tile-label overline">Max cards</span>
          <div className="metric-tile-value-row">
            <span className="law-tile-value mono">{governor.max_cards ?? "—"}</span>
          </div>
        </div>
        <div className="metric-tile">
          <span className="metric-tile-label overline">Risk/trade</span>
          <div className="metric-tile-value-row">
            <span className="law-tile-value mono">{riskLabel}</span>
          </div>
        </div>
        <div className="metric-tile">
          <span className="metric-tile-label overline">Allowed</span>
          <div className="metric-tile-value-row">
            <span className="law-tile-value mono">{familiesLabel}</span>
          </div>
        </div>
        <div className="metric-tile">
          <span className="metric-tile-label overline">Open-risk</span>
          <div className="metric-tile-value-row">
            <span className="law-tile-value mono">
              {openRisk}/{openCap}%
            </span>
          </div>
        </div>
        <div className="metric-tile">
          <span className="metric-tile-label overline">Pushes</span>
          <div className="metric-tile-value-row">
            <span className={"law-tile-value mono " + (pushOn ? "push-on" : "push-off")}>
              {pushOn ? "ON" : "OFF"}
            </span>
          </div>
        </div>
      </div>
      <p className="caption-b">[B] {governor.market_mode || "—"} regime law — what the desk is allowed to show tonight.</p>
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
            {event.actor}
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
          Morning brief
        </p>
        <p className="brief-body">{card.morning_brief || "—"}</p>
      </div>

      <div style={{ height: "var(--gap-m)" }} />

      <RegimeStrip regime={card.regime} />

      <div style={{ height: "var(--gap-m)" }} />

      <LawRow governor={card.governor} heat={card.heat} />

      <DegradedPanel card={card} />

      <div className="panel">
        <p className="panel-title small-caps">Activity stream</p>
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
