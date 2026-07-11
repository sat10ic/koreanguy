import React, { useEffect, useState } from "react";
import { fetchAlphaExperiments, fetchAlphaLeaders, fetchAlphaModels, fetchAlphaOverview } from "./api.js";
import { useDensity } from "./DensityContext.jsx";
import "./AlphaLab.css";

function pct(value, digits = 0) {
  return value === null || value === undefined ? "—" : `${Number(value).toFixed(digits)}%`;
}

function Panel({ eyebrow, title, explain, children }) {
  return <section className="alpha-panel"><p className="alpha-eyebrow">{eyebrow}</p><h2>{title}</h2><p className="alpha-explain">{explain}</p>{children}</section>;
}

export default function AlphaLab({ date }) {
  const { isExpert } = useDensity();
  const [state, setState] = useState({ loading: true, error: null, overview: null, leaders: null, models: null, experiments: null });
  useEffect(() => {
    let live = true;
    setState((s) => ({ ...s, loading: true, error: null }));
    Promise.all([fetchAlphaOverview(), fetchAlphaLeaders(date), fetchAlphaModels(), fetchAlphaExperiments()])
      .then(([overview, leaders, models, experiments]) => live && setState({ loading: false, error: null, overview, leaders, models, experiments }))
      .catch((error) => live && setState({ loading: false, error: String(error), overview: null, leaders: null, models: null, experiments: null }));
    return () => { live = false; };
  }, [date]);

  if (state.loading) return <div className="alpha-state"><span className="v5-live-dot" /> Building the causal opportunity map…</div>;
  if (state.error) return <div className="alpha-state alpha-error"><b>Alpha Lab could not load.</b><span>{state.error}</span></div>;
  const overview = state.overview || {};
  const rows = state.leaders?.rows || [];
  const setupRows = overview.setup_expectancy || [];
  const risk = overview.competing_risks || {};
  const modelRows = state.models?.rows || [];
  const experimentRows = state.experiments?.rows || [];

  return <div className="alpha-lab">
    <header className="alpha-hero">
      <div><p className="alpha-eyebrow">ALPHA LAB · SHADOW EVIDENCE</p><h1>Regime, ranking and setup evidence</h1><p>Review causal leadership and chart behaviour. Forecasts remain supporting evidence and never size a trade.</p></div>
      <div className="alpha-health"><b>{overview.state === "ready" ? "OBSERVING" : "WARMING"}</b><span>{overview.as_of || "no feature build yet"}</span><span>{overview.source_denominator ? `${overview.source_denominator} eligible stocks` : "waiting for universe"}</span></div>
    </header>
    {overview.state !== "ready" ? <div className="alpha-state"><b>Nothing is fabricated while the lab warms.</b><span>Run the nightly update to build point-in-time ranks from local NSE history.</span></div> : <>
      <Panel eyebrow="WHAT MAY LEAD NEXT" title="Opportunity ranking" explain="Stocks leading the eligible Indian universe after market movement is removed. This is a research rank, not a buy list.">
        <div className="alpha-leader-table" role="table">
          <div className="alpha-table-head" role="row"><span>Rank</span><span>Symbol</span><span>Sector</span><span>Leadership</span><span>20d residual</span></div>
          {rows.slice(0, 12).map((row, index) => <div className="alpha-table-row" role="row" key={row.symbol}><span>{index + 1}</span><b>{row.symbol}</b><span>{row.sector || "unmapped"}</span><span>{pct(row.momentum_percentile)}</span><span>{pct(row.market_residual_20 * 100, 1)}</span></div>)}
        </div>
      </Panel>
      <div className="alpha-split">
        <Panel eyebrow="WHY" title="What the rank is noticing" explain="Residual momentum, participation and chart behaviour provide the observation. Debate agents must still identify the actual setup and contradiction.">
          <ul className="alpha-plain-list"><li>Strength after removing the broad market move</li><li>Sector-relative leadership where point-in-time membership exists</li><li>EMA, volume, ADR and contraction context inside each stock debate</li></ul>
        </Panel>
        <Panel eyebrow="WHAT HAS WORKED" title="Shrunk setup evidence" explain="Small samples are pulled toward the parent rate so one lucky trade cannot masquerade as edge.">
          {setupRows.length ? <div className="alpha-evidence-list">{setupRows.slice(0, 6).map((row) => <div key={row.setup}><b>{row.setup}</b><span>n={row.n}</span><span>posterior hit {pct(row.posterior_hit_rate * 100)}</span><span>{Number(row.posterior_expectancy_r).toFixed(2)}R</span></div>)}</div> : <p className="alpha-muted">No mature setup outcomes yet.</p>}
          {risk.state === "ready" && <p className="alpha-risk-line">Across {risk.n} resolved 10-session paths: +1R first {pct(risk.probabilities?.plus_1r_first * 100)} · stop first {pct(risk.probabilities?.stop_first * 100)}.</p>}
        </Panel>
      </div>
      <Panel eyebrow="RESEARCH BENCH" title="Models must earn visibility" explain="Every model remains shadow-only until causal walk-forward and genuine live observation gates pass.">
        <div className="alpha-bench"><div><b>{modelRows.length}</b><span>registered models</span></div><div><b>{overview.live_shadow_sessions || 0}</b><span>live shadow sessions</span></div><div><b>{experimentRows.length}</b><span>recorded experiments</span></div><div><b>0</b><span>models allowed to size</span></div></div>
        {isExpert && <pre className="alpha-expert">{JSON.stringify({ models: modelRows, experiments: experimentRows }, null, 2)}</pre>}
      </Panel>
    </>}
  </div>;
}
