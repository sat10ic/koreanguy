import React, { useEffect, useState } from "react";
import { fetchAlphaActivitySymbol, fetchAlphaSymbol } from "./api.js";

export default function DebateAlphaCard({ symbol, date, attached }) {
  const [state, setState] = useState({ loading: !attached, data: attached || null, error: null });
  const [activity, setActivity] = useState(null);
  useEffect(() => {
    if (!symbol) return undefined;
    let live = true;
    fetchAlphaActivitySymbol(symbol, date).then((data) => live && setActivity(data)).catch(() => live && setActivity(null));
    if (!attached) fetchAlphaSymbol(symbol, date).then((data) => live && setState({ loading: false, data, error: null })).catch((error) => live && setState({ loading: false, data: null, error: String(error) }));
    return () => { live = false; };
  }, [attached, symbol, date]);
  if (state.loading) return <section className="v5-alpha-card"><p className="v5-alpha-kicker">ALPHA READ · SHADOW</p><p>Reading the chart behaviour and comparable evidence…</p></section>;
  const data = state.data;
  if (state.error || !data || data.state !== "ready") return <section className="v5-alpha-card"><p className="v5-alpha-kicker">ALPHA READ · WARMING</p><p>No causal opportunity-rank snapshot exists for {symbol} yet. The debate continues from the real chart and teacher lenses.</p>{activity?.state === "ready" && activity.latest && <div className="v5-alpha-activity"><b>Unusual participation: {Number(activity.latest.score).toFixed(2)}</b><span>{String(activity.latest.state).replaceAll("_", " ")} · quantity/trade {Number(activity.latest.avg_trade_qty_ratio20).toFixed(2)}x · delivery {Number(activity.latest.delivery_ratio19).toFixed(2)}x</span><small>Direction unresolved. This aggregate bhavcopy analogue cannot identify institutions or change the trade gate.</small></div>}</section>;
  const chart = data.chart_behavior || {};
  const trend = chart.trend_structure || {};
  const base = chart.base_and_contraction || {};
  const volume = chart.volume_behavior || {};
  const analogues = data.analogues || [];
  return <section className="v5-alpha-card">
    <div className="v5-alpha-head"><div><p className="v5-alpha-kicker">ALPHA READ · SHADOW ONLY</p><h3>What the chart is doing</h3></div><b className="v5-alpha-rank">leadership {data.opportunity_rank == null ? "—" : `${Math.round(data.opportunity_rank)}th pct`}</b></div>
    <p className="v5-alpha-summary">{trend.stack === "close>10>21>50" ? "Price is stacked above rising decision averages" : "EMA structure is mixed"}; 20-day range is {base.range_20d_pct == null ? "unavailable" : `${base.range_20d_pct}%`} and recent volume is {volume.recent10_vs_50d == null ? "unavailable" : `${volume.recent10_vs_50d}× its 50-day norm`}.</p>
    <div className="v5-alpha-contract"><span><b>Confirm:</b> the selected lens must name a trigger from this structure.</span><span><b>Invalidate:</b> the debate must name the price behaviour that disproves its thesis.</span><span><b>Contradiction:</b> model probability cannot override damaged structure or risk law.</span></div>
    {activity?.state === "ready" && activity.latest && <div className="v5-alpha-activity">
      <b>Unusual participation: {Number(activity.latest.score).toFixed(2)}</b>
      <span>{String(activity.latest.state).replaceAll("_", " ")} · quantity/trade {Number(activity.latest.avg_trade_qty_ratio20).toFixed(2)}x · delivery {Number(activity.latest.delivery_ratio19).toFixed(2)}x</span>
      <small>Direction unresolved. This aggregate bhavcopy analogue cannot identify institutions and does not change the trade gate.</small>
    </div>}
    <div className="v5-alpha-analogues"><b>Comparable decisions</b>{analogues.length ? analogues.slice(0, 3).map((a) => <span key={a.memory_id}>{a.symbol} · {a.decision} · {a.outcome ? "resolved" : "outcome pending"}</span>) : <span>No mature analogues yet—no invented precedent.</span>}</div>
  </section>;
}
