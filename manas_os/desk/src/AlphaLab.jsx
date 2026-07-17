import React, { useEffect, useState } from "react";
import { addWatchlistSymbol, fetchAlphaActivity, fetchAlphaExperiments, fetchAlphaLeaders, fetchAlphaModels, fetchAlphaOverview, fetchAlphaResearchQuality, pushSymbolToDebate } from "./api.js";
import { useDensity } from "./DensityContext.jsx";
import StatusBadge from "./components/v5/StatusBadge.jsx";
import ListRelationshipLegend, { CrossBadges, useListMembership } from "./components/v5/ListRelationshipLegend.jsx";
import { formatDisplayFloat } from "./presentation.js";
import "./AlphaLab.css";

function pct(value, digits = 0) {
  return formatDisplayFloat(value, { digits: digits === 2 ? 2 : 1, unit: "%" });
}

function InfoDot({ label }) {
  return <span className="alpha-info-dot" tabIndex={0} role="note" aria-label={label} title={label}>ⓘ</span>;
}

function Panel({ eyebrow, title, explain, children }) {
  return <section className="alpha-panel"><p className="alpha-eyebrow">{eyebrow}</p><h2>{title}</h2><p className="alpha-explain">{explain}</p>{children}</section>;
}

// (#13b) The old collapsed static legend was replaced by the shared
// ListRelationshipLegend — live funnel numbers, cross-tab links, one writer.

// v5 Research Bench — replaces the raw JSON dump.
// Shows registered models and experiments in structured v5 tables.
function ResearchBenchPanel({ modelRows, experimentRows, liveShadowSessions }) {
  function modelStatus(m) {
    if (m.status === "live") return "LIVE";
    if (m.status === "shadow" || !m.status) return "SHADOW";
    if (m.status === "warming") return "WARMING";
    return "EXPERIMENTAL";
  }
  function expStatus(e) {
    if (e.status === "passed") return "LIVE";
    if (e.status === "running") return "SHADOW";
    if (e.status === "draft")   return "EXPERIMENTAL";
    return "NEEDS-DATA";
  }

  return (
    <div className="alpha-bench-v5">
      <div className="alpha-bench-summary">
        <div><b>{modelRows.length}</b><span>registered models</span></div>
        <div><b>{liveShadowSessions || 0}</b><span>shadow sessions</span></div>
        <div><b>{experimentRows.length}</b><span>experiments</span></div>
        <div><b>0</b><span>models allowed to size</span></div>
      </div>

      {modelRows.length > 0 && (
        <div className="alpha-bench-table-wrap">
          <p className="alpha-eyebrow">REGISTERED MODELS</p>
          <div className="alpha-bench-table" role="table">
            <div className="alpha-bench-thead" role="row">
              <span>Model</span><span>Type</span><span>Status</span><span>Sessions</span>
            </div>
            {modelRows.map((m) => (
              <div className="alpha-bench-row" role="row" key={m.model_id || m.id || m.name}>
                <b>{m.model_id || m.id || m.name || "—"}</b>
                <span>{m.model_type || m.type || "—"}</span>
                <StatusBadge status={modelStatus(m)} />
                <span className="mono-num">{m.live_shadow_sessions ?? "—"}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {experimentRows.length > 0 && (
        <div className="alpha-bench-table-wrap">
          <p className="alpha-eyebrow">RECORDED EXPERIMENTS</p>
          <div className="alpha-bench-table" role="table">
            <div className="alpha-bench-thead" role="row">
              <span>ID</span><span>Hypothesis</span><span>Status</span><span>Created</span>
            </div>
            {experimentRows.map((e) => (
              <div className="alpha-bench-row" role="row" key={e.experiment_id || e.id}>
                <b>{e.experiment_id || e.id || "—"}</b>
                <span>{e.hypothesis || e.description || "—"}</span>
                <StatusBadge status={expStatus(e)} />
                <span className="mono-num">{e.created_at ? String(e.created_at).slice(0, 10) : "—"}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {modelRows.length === 0 && experimentRows.length === 0 && (
        <p className="alpha-muted">
          No models or experiments registered yet.{" "}
          <StatusBadge status="NEEDS-DATA" why="Run the nightly update to seed the registry." />
        </p>
      )}
    </div>
  );
}

export default function AlphaLab({ date, onNavigate }) {
  const { isExpert } = useDensity();
  const [state, setState] = useState({ loading: true, error: null, overview: null, leaders: null, activity: null, quality: null, models: null, experiments: null });
  const membership = useListMembership(date);
  const [rowBusy, setRowBusy] = useState(null); // symbol currently pushing/adding
  useEffect(() => {
    let live = true;
    setState((s) => ({ ...s, loading: true, error: null }));
    Promise.all([fetchAlphaOverview(), fetchAlphaLeaders(date), fetchAlphaActivity(date), fetchAlphaResearchQuality(), fetchAlphaModels(), fetchAlphaExperiments()])
      .then(([overview, leaders, activity, quality, models, experiments]) => live && setState({ loading: false, error: null, overview, leaders, activity, quality, models, experiments }))
      .catch((error) => live && setState({ loading: false, error: String(error), overview: null, leaders: null, activity: null, quality: null, models: null, experiments: null }));
    return () => { live = false; };
  }, [date]);

  if (state.loading) return <div className="alpha-state"><span className="v5-live-dot" /> Building the causal opportunity map…</div>;
  if (state.error) return <div className="alpha-state alpha-error"><b>Alpha Lab could not load.</b><span>{state.error}</span></div>;
  const overview = state.overview || {};
  const rows = state.leaders?.rows || [];
  const activityRows = state.activity?.rows || [];
  const setupRows = overview.setup_expectancy || [];
  const risk = overview.competing_risks || {};
  const modelRows = state.models?.rows || [];
  const experimentRows = state.experiments?.rows || [];

  // Determine HMM status from overview
  const hmmStatus = overview.hmm_status || (overview.state === "ready" ? "LIVE" : "WARMING");
  const hmmWhy = overview.hmm_reason || (overview.state !== "ready" ? "Accumulating history — will activate automatically once enough sessions are recorded." : null);

  return <div className="alpha-lab">
    <header className="alpha-hero">
      <div>
        <p className="alpha-eyebrow">RESEARCH RANKING — evidence only, never sizes a trade</p>
        <h1>Regime, ranking and setup evidence</h1>
        <p>Review causal leadership and chart behaviour. Forecasts remain supporting evidence and never size a trade.</p>
      </div>
      <div className="alpha-health">
        <b>{overview.state === "ready" ? "OBSERVING" : "WARMING"}</b>
        <span>{overview.as_of || "no feature build yet"}</span>
        <span>{overview.source_denominator ? `${overview.source_denominator} eligible stocks` : "waiting for universe"}</span>
        {hmmWhy && <StatusBadge status={hmmStatus} why={hmmWhy} />}
      </div>
    </header>

    {/* #13b shared relationship legend — live funnel, cross-tab links */}
    <ListRelationshipLegend active="ALPHA" membership={membership} onNavigate={onNavigate} />

    {overview.state !== "ready" ? <div className="alpha-state"><b>Nothing is fabricated while the lab warms.</b><span>Run the nightly update to build point-in-time ranks from local NSE history.</span></div> : <>
      <Panel eyebrow="WHAT MAY LEAD NEXT" title="Opportunity ranking" explain="Stocks leading the eligible Indian universe after market movement is removed. This is a research rank, not a buy list. DEBATE sends a symbol to the council on demand; WATCH adds it to your shortlist.">
        <div className="alpha-leader-table alpha-leader-table--actions" role="table">
          <div className="alpha-table-head" role="row"><span>Rank</span><span>Symbol</span><span>Sector</span><span>Leadership <InfoDot label="Leadership is the stock's percentile rank within the eligible research universe." /></span><span>vs market (20d) <InfoDot label="Twenty-session performance after removing the broad market move; research evidence, not a trade signal." /></span><span>Actions</span></div>
          {rows.slice(0, 12).map((row, index) => (
            <div className="alpha-table-row" role="row" key={row.symbol}>
              <span>{index + 1}</span>
              <b>{row.symbol}<CrossBadges symbol={row.symbol} membership={membership} active="ALPHA" onNavigate={onNavigate} /></b>
              <span>{row.sector || "—"}</span>
              <span>{pct(row.momentum_percentile)}</span>
              <span>{pct(row.market_residual_20 * 100, 1)}</span>
              <span className="alpha-row-actions">
                <button
                  type="button"
                  className="alpha-row-btn"
                  disabled={rowBusy === row.symbol}
                  title="Push this symbol to the debate council (on-demand run, watch it live on DEBATE)"
                  onClick={async () => {
                    setRowBusy(row.symbol);
                    try { await pushSymbolToDebate(row.symbol, date, true); onNavigate?.("DEBATE"); }
                    catch (e) { /* 409 already running is fine — still navigate */ onNavigate?.("DEBATE"); }
                    finally { setRowBusy(null); }
                  }}
                >Debate</button>
                {membership.watch.has(row.symbol)
                  ? <span className="alpha-row-onwatch" title="Already on your shortlist">On watch</span>
                  : <button
                      type="button"
                      className="alpha-row-btn"
                      disabled={rowBusy === row.symbol}
                      title="Add to your shortlist"
                      onClick={async () => {
                        setRowBusy(row.symbol);
                        try { await addWatchlistSymbol(row.symbol, `alpha shadow rank #${index + 1} (${overview.as_of || date})`); membership.watch.add(row.symbol); }
                        finally { setRowBusy(null); }
                      }}
                    >Watch</button>}
              </span>
            </div>
          ))}
        </div>
      </Panel>
      <Panel
        eyebrow="UNUSUAL PARTICIPATION · SHADOW"
        title="EOD abnormal-activity analogue"
        explain="A direction-neutral clue from NSE average quantity per trade and delivery participation. It cannot identify institutions and is never a buy signal, eligibility gate or sizing input."
      >
        {activityRows.length ? <div className="alpha-activity-table" role="table">
          <div className="alpha-activity-head" role="row"><span>Symbol</span><span>Activity</span><span>State</span><span>Qty/trade vs norm</span><span>Delivery vs norm</span><span>Coverage</span></div>
          {activityRows.slice(0, 12).map((row) => <div className="alpha-activity-row" role="row" key={row.symbol}>
            <b>{row.symbol}</b>
            <span className="mono-num">{Number(row.score).toFixed(2)}</span>
            <span>{String(row.state || "baseline").replaceAll("_", " ")}</span>
            <span className="mono-num">{Number(row.avg_trade_qty_ratio20).toFixed(2)}x</span>
            <span className="mono-num">{Number(row.delivery_ratio19).toFixed(2)}x</span>
            <span className="mono-num">{Number(row.percentile).toFixed(0)}th pct</span>
          </div>)}
        </div> : <div className="alpha-inline-state"><b>Waiting for 20 valid bhavcopy sessions per stock.</b><span>No proxy values are invented from price-only history.</span></div>}
        <p className="alpha-risk-line">{state.activity?.note || "Abnormal activity; direction unresolved."}</p>
      </Panel>
      <div className="alpha-split">
        <Panel eyebrow="WHY" title="What the rank is noticing" explain="Residual momentum, participation and chart behaviour provide the observation. Debate agents must still identify the actual setup and contradiction.">
          <ul className="alpha-plain-list"><li>Strength after removing the broad market move</li><li>Sector-relative leadership where point-in-time membership exists</li><li>EMA, volume, ADR and contraction context inside each stock debate</li></ul>
        </Panel>
        <Panel eyebrow="WHAT HAS WORKED" title="Shrunk setup evidence" explain="Small samples are pulled toward the parent rate so one lucky trade cannot masquerade as edge.">
          {setupRows.length ? <div className="alpha-evidence-list">{setupRows.slice(0, 6).map((row) => {
            const needsData = row.n < 20;
            return <div key={row.setup}>
              <b>{row.setup}</b>
              <span>n={row.n}</span>
              {needsData
                ? <StatusBadge status="NEEDS-DATA" why={`Only ${row.n} resolved trades — posterior estimate unreliable below 20.`} />
                : <><span>posterior hit {pct(row.posterior_hit_rate * 100)}</span><span>{Number(row.posterior_expectancy_r).toFixed(2)}R</span></>
              }
            </div>;
          })}</div> : <p className="alpha-muted">No mature setup outcomes yet.</p>}
          {risk.state === "ready" && <p className="alpha-risk-line">Across {risk.n} resolved 10-session paths: +1R first {pct(risk.probabilities?.plus_1r_first * 100)} · stop first {pct(risk.probabilities?.stop_first * 100)}.</p>}
        </Panel>
      </div>
      <Panel eyebrow="RESEARCH BENCH" title="Models must earn visibility" explain="Every model remains shadow-only until causal walk-forward and genuine live observation gates pass.">
        <ResearchBenchPanel
          modelRows={modelRows}
          experimentRows={experimentRows}
          liveShadowSessions={overview.live_shadow_sessions}
        />
      </Panel>
      <Panel eyebrow="RESEARCH QUALITY · HORIZON-ADAPTED" title="How the lab avoids fooling itself" explain="These are research-control mechanisms, not stock signals. Ready means evidence exists; warming means the required trials or outcomes do not exist yet.">
        <div className="alpha-quality-grid">
          {(state.quality?.cards || []).map((card) => <article className="alpha-quality-card" key={card.key}>
            <div><b>{card.label}</b><span className={`alpha-quality-state alpha-quality-state--${card.state}`}>{String(card.state).replaceAll("_", " ")}</span></div>
            <p>{card.plain}</p>
            {card.value !== null && card.value !== undefined && <span className="mono-num">Recorded: {typeof card.value === "number" ? Number(card.value).toFixed(card.key === "regime_transition" ? 2 : 0) : card.value}</span>}
          </article>)}
        </div>
        <p className="alpha-risk-line">{state.quality?.hard_boundary}</p>
      </Panel>
    </>}
  </div>;
}
