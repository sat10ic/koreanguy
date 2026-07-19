import React, { useCallback, useState } from "react";
import { fetchAdminHealth } from "./api.js";

export function staleCoverageSources(coverage) {
  return (coverage?.sources || []).filter((source) => source.health === "red");
}

// health.trust.verdict -> CSS tone. Server-computed (api/app.py
// _compute_trust_verdict); this only maps the word to a class name.
export function trustTone(verdict) {
  if (verdict === "TRUSTED") return "trusted";
  if (verdict === "DEGRADED") return "degraded";
  if (verdict === "STALE") return "stale";
  return "unknown";
}

export default function DataStatus({ coverage }) {
  const sources = coverage?.sources || [];
  const red = staleCoverageSources(coverage).length;
  const [health, setHealth] = useState(null);
  const [healthError, setHealthError] = useState(null);
  const [healthLoading, setHealthLoading] = useState(false);

  const loadHealth = useCallback(() => {
    setHealthLoading(true);
    setHealthError(null);
    fetchAdminHealth()
      .then(setHealth)
      .catch((error) => setHealthError(error.message || String(error)))
      .finally(() => setHealthLoading(false));
  }, []);

  const sectionText = (section, text) => {
    if (!section) return "unavailable";
    if (section.error) return `error: ${section.error}`;
    return text;
  };

  return (
    <details className="data-status" onToggle={(event) => event.currentTarget.open && loadHealth()}>
      <summary className="mono">Data status · {red ? `${red} blocked` : "current"}</summary>
      <div className="data-status-panel">
        <h2>System health</h2>
        <div className="admin-health-state" role="status" aria-live="polite">
          {healthLoading && !health && "Loading system health…"}
          {healthError && <code>Health endpoint error: {healthError}</code>}
          {health && health.trust && (
            <div className={`admin-health-trust admin-health-trust-${trustTone(health.trust.verdict)}`}>
              <span className="admin-health-trust-word">{health.trust.verdict || "UNKNOWN"}</span>
              {health.trust.reason && <span className="admin-health-trust-reason">{health.trust.reason}</span>}
            </div>
          )}
          {health && (
            <dl className="admin-health-grid">
              <div><dt>Build</dt><dd className="mono">{health.build_sha || "unknown"}</dd></div>
              <div><dt>API process</dt><dd className="mono">PID {health.port_owner_pid ?? "unknown"}</dd></div>
              <div>
                <dt>Data</dt>
                <dd>{sectionText(health.data_freshness,
                  `prices ${health.data_freshness?.latest_price_date || "none"} · scans ${health.data_freshness?.latest_scan_date || "none"} · expected ${health.data_freshness?.last_trading_day || "unknown"} · ${health.data_freshness?.is_stale ? "stale" : "current"}`)}</dd>
              </div>
              <div>
                <dt>Pipeline</dt>
                <dd>{sectionText(health.pipeline,
                  `${health.pipeline?.running ? "running" : "idle"} · ${health.pipeline?.current_stage || "no stage"}${health.pipeline?.started_at ? ` · started ${new Date(health.pipeline.started_at * 1000).toLocaleString()}` : ""}${health.pipeline?.stuck ? " · stuck" : ""}`)}</dd>
              </div>
              <div><dt>Fyers</dt><dd>{sectionText(health.fyers, health.fyers?.token_ready ? "token ready" : "token needed")}</dd></div>
              <div>
                <dt>Jobs</dt>
                <dd>{sectionText(health.jobs,
                  `${health.jobs?.running_count ?? "?"} running · ${health.jobs?.stale_count ?? "?"} stale`)}</dd>
              </div>
              <div>
                <dt>Database</dt>
                <dd>{sectionText(health.db,
                  `${health.db?.size_mb ?? "?"} MB · WAL ${health.db?.wal ? "on" : "off"}`)}</dd>
              </div>
            </dl>
          )}
        </div>
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
