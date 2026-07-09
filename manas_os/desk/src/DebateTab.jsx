import React, { useEffect, useState } from "react";
import { fetchDebate, chartUrl } from "./api.js";

function agentKey(actor) {
  return (actor || "").toLowerCase();
}

function round(n, digits = 1) {
  if (n === null || n === undefined) return "—";
  const f = Math.pow(10, digits);
  return Math.round(n * f) / f;
}

function ConvictionDots({ conviction }) {
  const c = conviction || 0;
  const dots = [];
  for (let i = 0; i < 5; i += 1) {
    dots.push(<span key={i} className={"conv-dot" + (i < c ? " filled" : "")} />);
  }
  return (
    <span className="conv-dots">
      {dots}
      <span className="conv-count">({c || "—"})</span>
    </span>
  );
}

function ChartImg({ date, symbol, tf }) {
  const [failed, setFailed] = useState(false);
  if (failed) {
    return <div className="chart-thumb chart-thumb-missing mono">[ {symbol}_{tf}.png unavailable ]</div>;
  }
  return (
    <img
      className="chart-thumb"
      src={chartUrl(date, symbol, tf)}
      alt={`${symbol} ${tf}`}
      onError={() => setFailed(true)}
    />
  );
}

function SymbolCard({ date, sym }) {
  const chair = sym.chair;
  const spread = chair && chair.conviction_spread;
  const disagreement = chair && chair.disagreement;
  const lensTag = (sym.family || "unknown").replace(/[/_]/g, " ").toUpperCase();

  return (
    <div className="panel debate-card">
      <div className="debate-card-header">
        <span className="debate-symbol">{sym.symbol}</span>
        <span className="debate-lens mono">· lens {lensTag} ·</span>
        <span className={"debate-chair-verdict mono " + (chair && chair.verdict === "TAKE" ? "take" : "skip")}>
          CHAIR: {chair ? chair.verdict : "—"}
        </span>
      </div>

      <div className="conviction-row">
        <span className="small-caps">Conviction</span>
        {sym.models.map((m) => (
          <span key={m.agent} className="conviction-item">
            <span className="agent-chip mono" data-agent={agentKey(m.agent)}>
              {m.agent}
            </span>
            <ConvictionDots conviction={m.conviction} />
          </span>
        ))}
        {spread !== null && spread !== undefined && (
          <span className={"spread-badge mono" + (disagreement ? " disagree" : "")}>spread {spread}</span>
        )}
      </div>

      <div className="bull-bear-columns">
        <div className="bull-column">
          <p className="panel-title small-caps">Bull</p>
          {sym.models.map((m) => (
            <p key={m.agent} className="case-line">
              <span className="agent-chip mono" data-agent={agentKey(m.agent)}>
                {m.agent}
              </span>
              : {m.bull_case || "—"}
            </p>
          ))}
        </div>
        <div className="bear-column">
          <p className="panel-title small-caps">Bear</p>
          {sym.models.map((m) => (
            <p key={m.agent} className="case-line">
              <span className="agent-chip mono" data-agent={agentKey(m.agent)}>
                {m.agent}
              </span>
              : {m.bear_case || "—"}
            </p>
          ))}
        </div>
      </div>

      <div className="vision-strip">
        <p className="panel-title small-caps">Vision strip</p>
        <div className="vision-images">
          <ChartImg date={date} symbol={sym.symbol} tf="daily" />
          <ChartImg date={date} symbol={sym.symbol} tf="weekly" />
        </div>
        <p className="vision-stamp mono">
          {sym.vision
            ? `stamp: "${sym.vision.reasoning || "—"}" ${sym.vision.verdict || ""}`
            : "stamp: — (no vision pass)"}
        </p>
      </div>

      <div className="plan-block">
        <p className="panel-title small-caps">
          Plan <span className="math-engine-label mono">[math: engine]</span>
        </p>
        {sym.plan ? (
          <p className="plan-line mono">
            entry {round(sym.plan.entry)}&nbsp;&nbsp;stop {round(sym.plan.stop)}&nbsp;&nbsp;target{" "}
            {round(sym.plan.target)}&nbsp;&nbsp;RR {round(sym.plan.rr)}&nbsp;&nbsp;base qty{" "}
            {sym.plan.suggested_qty ?? "—"}
          </p>
        ) : (
          <p className="plan-line mono">plan unavailable</p>
        )}
        {sym.sizer && (
          <p className="sizer-line mono">
            SIZER: {sym.sizer.multiplier ?? "—"}x → final qty {sym.sizer.final_qty ?? "—"} ·{" "}
            {sym.sizer.reasoning || "—"}
          </p>
        )}
      </div>

      <div className="debate-footer">
        {sym.base_rate ? (
          <span className="mono">
            base rate {lensTag}: sys n=
            {sym.base_rate.system ? sym.base_rate.system.n : "—"}
            {sym.base_rate.system
              ? ` hit ${round((sym.base_rate.system.hit_rate || 0) * 100, 0)}%`
              : ""}
          </span>
        ) : (
          <span className="mono">base rate — n/a</span>
        )}
        {sym.track_record.map((t) => (
          <span key={t.agent} className="mono track-chip">
            {t.agent} on {sym.family}: {t.n ? `${round((t.hit_rate || 0) * t.n, 0)}/${t.n}` : "n/a"}
            {t.thin ? " (thin)" : ""}
          </span>
        ))}
      </div>
    </div>
  );
}

function ZeroTakeState({ symbols }) {
  const struck = symbols.filter((s) => s.chair && s.chair.verdict !== "TAKE");
  return (
    <div className="panel zero-take-panel">
      <p className="panel-title small-caps">The desk sat out</p>
      <p>
        The desk took nothing on this date. {symbols.length} name{symbols.length === 1 ? "" : "s"} debated, all
        struck.
      </p>
      {struck.map((s) => (
        <p key={s.symbol} className="mono struck-line">
          {s.symbol} — chair struck: "{s.chair ? s.chair.reasoning : "—"}"
        </p>
      ))}
    </div>
  );
}

export default function DebateTab({ date }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchDebate(date)
      .then((body) => {
        if (!cancelled) setData(body);
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

  if (loading) {
    return <div className="empty-state">Loading…</div>;
  }
  if (error) {
    return <div className="empty-state">{error}</div>;
  }
  if (!data || !data.available || !data.symbols || data.symbols.length === 0) {
    return (
      <div className="empty-state">
        No debate for this date — shortlist was empty or the debate stage didn't run.
      </div>
    );
  }

  const anyTake = data.symbols.some((s) => s.chair && s.chair.verdict === "TAKE");

  return (
    <div>
      {!anyTake && <ZeroTakeState symbols={data.symbols} />}
      {data.symbols.map((sym) => (
        <SymbolCard key={sym.symbol} date={date} sym={sym} />
      ))}
    </div>
  );
}
