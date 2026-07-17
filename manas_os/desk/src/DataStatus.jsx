import React from "react";

export function staleCoverageSources(coverage) {
  return (coverage?.sources || []).filter((source) => source.health === "red");
}

export default function DataStatus({ coverage }) {
  const sources = coverage?.sources || [];
  const red = staleCoverageSources(coverage).length;
  return (
    <details className="data-status">
      <summary className="mono">Data status · {red ? `${red} blocked` : "current"}</summary>
      <div className="data-status-panel">
        <h2>Source coverage</h2>
        <ul>
          {sources.map((source) => (
            <li key={source.key} className={`data-status-row health-${source.health}`}>
              <span className="data-health-dot" aria-label={source.health} />
              <div>
                <b>{source.label}</b>
                <span className="mono">as of {source.until || "none"} · {source.last_status}</span>
                {source.diagnostic && <code>{source.diagnostic}</code>}
                <p>{source.what_to_do}</p>
              </div>
            </li>
          ))}
        </ul>
        <h2>Debate models</h2>
        <ul>
          {(coverage?.models || []).map((model) => (
            <li key={model.model} className="data-model-row">
              <b>{model.model}</b> · {model.status} · Rs {Number(model.cost_inr || 0).toFixed(4)}
              {model.reason && <code>{model.reason}</code>}
            </li>
          ))}
        </ul>
      </div>
    </details>
  );
}

export function DataHealthStrip({ coverage }) {
  const stale = staleCoverageSources(coverage);
  if (!coverage) return null;
  return (
    <div className={`data-health-strip ${stale.length ? "has-stale" : "is-current"}`} role="status">
      <b>Data health</b> · {coverage.sources.length} sources · {stale.length
        ? `${stale.length} need attention: ${stale.map((source) => source.label).join(", ")}`
        : `all current through ${coverage.latest_price_date || "latest session"}`}
    </div>
  );
}
