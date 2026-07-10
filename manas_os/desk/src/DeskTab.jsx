import React, { useEffect, useState } from "react";
import { fetchFeed, fetchFocus } from "./api.js";
import { Term, hasGlossaryTerm } from "./Glossary.jsx";
import ChartDrawer from "./ChartDrawer.jsx";

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
// SHIP-3 #3: forecast is only ever as fresh as the regime_snapshots row it
// was written on (vol_forecast_as_of, from the API). When that row predates
// the card's own scan_date -- HAR-RV didn't run tonight -- the caption must
// say so instead of silently showing yesterday's (or older) numbers as if
// they were tonight's.
function VolForecastCaption({ vol, asOf, scanDate }) {
  if (!vol || vol.vol_forecast_pct === null || vol.vol_forecast_pct === undefined) return null;
  const bandWord = { rising: "rising", falling: "falling", flat: "flat" }[vol.band] || vol.band;
  const stale = Boolean(asOf && scanDate && asOf < scanDate);
  return (
    <p className="caption-b vol-forecast-caption">
      [B] <Term k="vol-forecast-experimental">EXPERIMENTAL</Term> vol forecast (as of {asOf || "—"}): {bandWord},{" "}
      {vol.current_vol_pct}&rarr;{vol.vol_forecast_pct}.
      {stale && <span className="vol-forecast-stale"> (stale — from {asOf})</span>}
    </p>
  );
}

// SHIP-1 #17 (I5): HMM confirmation caption. RENDER RULE (locked) — the
// backend (regime_hmm.get_display_caption via run_card._regime) already
// enforces the 20-live-session display gate and only ever hands us the
// pre-built caption string; this component renders that string verbatim
// and NEVER the raw hmm_label itself. XP/MBI stays the sole authority.
function HmmCaption({ caption }) {
  if (!caption) return null;
  return <p className="caption-b hmm-caption">[B] {caption}</p>;
}

function RegimeStrip({ regime, scanDate }) {
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
        {regime.four_phase && (
          <>
            {" "}<Term k="four-phase">Four-phase</Term>: {regime.four_phase}.
          </>
        )}
      </p>
      <VolForecastCaption vol={regime.vol_forecast} asOf={regime.vol_forecast_as_of} scanDate={scanDate} />
      <HmmCaption caption={regime.hmm_caption} />
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

// SHIP-3 #4: pipeline_runs.detail is an internal telemetry string (e.g.
// "coach positions=1 sent=0 live=False; llm=..."), fine for the activity
// stream but not for a user-facing chip. Humanize the coach stage here;
// pipeline_runs itself is left untouched so telemetry/activity-stream
// consumers still see the raw detail.
function humanizeErrorDetail(stage, detail) {
  if (stage === "agents_coach" && detail) {
    const match = detail.match(/coach positions=(\d+) sent=(\d+) live=(\w+)/i);
    if (match) {
      const n = parseInt(match[1], 10);
      const rest = detail.slice(match[0].length).replace(/^;\s*/, "");
      const base = `Coach reviewed ${n} open position${n === 1 ? "" : "s"}`;
      return rest ? `${base} (${rest})` : base;
    }
  }
  return detail || "error";
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
            {e.stage} · {humanizeErrorDetail(e.stage, e.detail)}
          </span>
        ))}
      </div>
    </div>
  );
}

const STANCE_PILL_CLASS = {
  STAND_ASIDE: "stand-aside",
  SIT_OUT: "sit-out",
  CAUTION: "caution",
  ACT_PER_PLAN: "act-per-plan",
};

const STANCE_LABEL = {
  STAND_ASIDE: "STAND ASIDE",
  SIT_OUT: "SIT OUT",
  CAUTION: "CAUTION",
  ACT_PER_PLAN: "ACT PER PLAN",
};

export function TonightsCall({ call }) {
  if (!call || !call.stance) return null;
  const pillClass = STANCE_PILL_CLASS[call.stance] || "sit-out";
  const label = STANCE_LABEL[call.stance] || call.stance;
  return (
    <div className="call-card">
      <p className="overline accent" style={{ marginBottom: "8px" }}>
        <Term k="tonights-call">Tonight's call</Term>
      </p>
      <div className="call-stance-row">
        <span className={`call-stance-pill ${pillClass}`}>
          <Term k="stance">{label}</Term>
        </span>
      </div>
      <p className="call-headline">{call.headline}</p>
      {Array.isArray(call.what_to_do) && call.what_to_do.length > 0 && (
        <ul className="call-todo">
          {call.what_to_do.map((line, idx) => (
            <li key={idx}>{line}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

// SHIP-3 ML-visibility pass: one line per existing model/signal so the
// desk's AI is not buried behind a click into a debate card or chart
// drawer. Every value is read from data another stage already computed
// (_models_say in app.py just surfaces it) — this panel does not run any
// new computation, and every line is EXPERIMENTAL/fact-only (AD8).
function ModelsSayPanel({ modelsSay, volForecast }) {
  if (!modelsSay) return null;
  const mlRange = modelsSay.ml_p_up_range;
  const deliveryNames = modelsSay.delivery_accumulation?.names || [];
  const sectorRisk = modelsSay.sector_downside_top3 || [];
  const hasVol = volForecast && volForecast.vol_forecast_pct !== null && volForecast.vol_forecast_pct !== undefined;

  return (
    <div className="panel models-say-panel">
      <p className="panel-title small-caps">
        What the models say <span className="experimental-badge">EXPERIMENTAL</span>
      </p>
      <div className="models-say-lines mono">
        <p className="caption-b">
          [B] Tonight's ML P(up 10d):{" "}
          {mlRange && mlRange.available
            ? `${round(mlRange.min, 2)}-${round(mlRange.max, 2)} across ${mlRange.n} debated name${mlRange.n === 1 ? "" : "s"}`
            : "no scored names tonight"}
        </p>
        <p className="caption-b">
          [B] Delivery accumulation:{" "}
          {deliveryNames.length ? deliveryNames.join(", ") : "none flagged tonight"}
        </p>
        <p className="caption-b">
          [B] Market HMM: {modelsSay.market_hmm_status || "unavailable"}
        </p>
        <p className="caption-b">
          [B] Sector downside risk (top 3):{" "}
          {sectorRisk.length
            ? sectorRisk
                .map((s) => `${s.sector} ${round((s.p_drawdown_5d || 0) * 100, 1)}%`)
                .join(", ")
            : "no data yet"}
        </p>
        <p className="caption-b">
          [B] Vol forecast (HAR-RV, 5d):{" "}
          {hasVol
            ? `${volForecast.current_vol_pct}→${volForecast.vol_forecast_pct} (${volForecast.band})`
            : "not yet computed"}
        </p>
      </div>
    </div>
  );
}

// FOCUS NOW — theme-of-the-day aggregation over discovery_bucket, rolled up
// to ChartsMaze basic_industry (manas_os/scanner/focus.py). Deterministic
// rollup, not a recommendation: caption honesty over any ranking implication.
function FocusThemeChip({ theme, onSelectStock }) {
  const names = (theme.top_stocks || []).slice(0, 4).map((s) => s.symbol);
  return (
    <div className="focus-theme-chip">
      <p className="focus-theme-title mono">
        #{theme.rank} {theme.industry}
      </p>
      <p className="focus-theme-sub mono">
        {theme.member_count} fast mover{theme.member_count === 1 ? "" : "s"} · avg RS{" "}
        {theme.avg_rs === null || theme.avg_rs === undefined ? "—" : round(theme.avg_rs, 0)}
        {theme.industry_return_20d_pct !== null && theme.industry_return_20d_pct !== undefined
          ? ` · 20d ${theme.industry_return_20d_pct >= 0 ? "+" : ""}${round(theme.industry_return_20d_pct, 1)}%`
          : ""}
      </p>
      <div className="focus-theme-names">
        {names.map((sym) => (
          <button key={sym} className="focus-theme-name-btn mono" onClick={() => onSelectStock(sym)}>
            {sym}
          </button>
        ))}
      </div>
    </div>
  );
}

function FocusNowPanel({ date }) {
  const [focus, setFocus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [chartSymbol, setChartSymbol] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchFocus(date)
      .then((data) => {
        if (!cancelled) setFocus(data);
      })
      .catch((err) => {
        if (!cancelled) setError(String(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [date]);

  return (
    <div className="panel focus-now-panel">
      <p className="panel-title small-caps">Focus now</p>
      {loading && <p className="empty-state">Loading…</p>}
      {!loading && error && <p className="empty-state">{error}</p>}
      {!loading && !error && (!focus || !focus.available) && (
        <div className="empty-state">
          <div className="empty-state-icon">◌</div>
          <p className="empty-state-line">No theme signal for {date}.</p>
          <p className="empty-state-sub">{focus?.reason || "discovery_bucket has no data yet"}</p>
        </div>
      )}
      {!loading && !error && focus && focus.available && (
        <>
          <div className="focus-theme-row">
            {focus.themes.slice(0, 3).map((t) => (
              <FocusThemeChip key={t.industry} theme={t} onSelectStock={setChartSymbol} />
            ))}
          </div>
          <p className="caption-b">
            [B] Ranked by breadth of discovery-bucket strength (RS, % up from 65d low, purple-dot
            density) within a ChartsMaze industry — not a recommendation. As of {focus.as_of}.
          </p>
        </>
      )}
      <ChartDrawer symbol={chartSymbol} date={date} onClose={() => setChartSymbol(null)} />
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

      <TonightsCall call={card.tonights_call} />

      <div style={{ height: "var(--gap-m)" }} />

      <ModelsSayPanel modelsSay={card.models_say} volForecast={card.regime?.vol_forecast} />

      <div style={{ height: "var(--gap-m)" }} />

      <FocusNowPanel date={date} />

      <div style={{ height: "var(--gap-m)" }} />

      <RegimeStrip regime={card.regime} scanDate={card.scan_date} />

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
