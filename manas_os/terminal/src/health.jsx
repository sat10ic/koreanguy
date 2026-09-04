// Health — the operational readout in one glance.
// Trust verdict → status rows (data, pipeline, fyers, jobs) → refresh button.

import { useEffect, useState } from "react";
import { getDataCoverage, getFyersStatus } from "./api.js";
import { TermPanel, BandChip, StatusChip, EmptyLine, StatTile, fmtNum } from "./primitives.jsx";

export default function HealthPage({ onRefresh }) {
  const [coverage, setCoverage] = useState({ loading: true, error: null, data: null });
  const [fyers, setFyers] = useState({ loading: true, status: null });

  useEffect(() => {
    let alive = true;
    getDataCoverage()
      .then((d) => !alive || setCoverage({ loading: false, error: null, data: d }))
      .catch((e) => !alive || setCoverage({ loading: false, error: e.message, data: null }));
    getFyersStatus()
      .then((s) => !alive || setFyers({ loading: false, status: s }))
      .catch(() => !alive || setFyers({ loading: false, status: null }));
    return () => {
      alive = false;
    };
  }, []);

  const sources = coverage.data?.sources || coverage.data || {};

  return (
    <div className="space-y-3">
      <TermPanel
        title="System health"
        sub="The operational readout — what's fresh, what's behind."
        right={
          <button
            type="button"
            onClick={onRefresh}
            className="border border-hairline px-2 py-1 font-mono text-[10px] uppercase tracking-overline text-ink2 hover:border-ink hover:text-ink"
          >
            ⟳ update data (fetch new files)
          </button>
        }
      >
        {coverage.loading ? (
          <EmptyLine>checking data freshness…</EmptyLine>
        ) : coverage.error ? (
          <EmptyLine tone="bear">couldn't reach the API — {coverage.error}</EmptyLine>
        ) : (
          <div className="grid gap-2 md:grid-cols-2">
            {Object.entries(sources)
              .filter(([key]) => !["models", "universe_size"].includes(key))
              .map(([key, value]) => {
                const val = value && typeof value === "object" ? value : { as_of: value };
                const asOf = val.as_of || val.latest || val.latest_date;
                return (
                  <div key={key} className="flex items-center justify-between gap-2 border border-hairline bg-raised px-3 py-2">
                    <span className="font-mono text-[10px] uppercase tracking-overline text-ink3">{key.replace(/_/g, " ")}</span>
                    <span className="font-mono text-[11px] text-ink2">{asOf ? String(asOf) : "—"}</span>
                  </div>
                );
              })}
          </div>
        )}
      </TermPanel>

      {/* Fyers */}
      <TermPanel title="Connectors" sub="Live-data integrations.">
        <div className="flex flex-wrap items-center gap-3">
          <StatusChip
            tone={fyers.loading ? "muted" : fyers.status?.status === "ready" ? "bull" : "warn"}
            label={fyers.loading ? "fyers · checking…" : fyers.status?.status === "ready" ? "fyers · live" : "fyers · needs login"}
          />
          <span className="font-sans text-[12px] text-ink2">
            {fyers.status?.status === "ready"
              ? "Token active — live quotes will use Fyers on the next run."
              : fyers.status?.status === "missing_app_id"
                ? "Set your Fyers app credentials to connect."
                : "Fyers token expired — log in to refresh today's token."}
          </span>
        </div>
      </TermPanel>

      {/* Models */}
      {Array.isArray(coverage.data?.models) && coverage.data.models.length > 0 && (
        <TermPanel title="Models" sub="Agent model availability from the last scan.">
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {coverage.data.models.map((m) => (
              <div key={m.model} className="flex items-center justify-between gap-2 border border-hairline bg-raised px-3 py-2">
                <span className="font-mono text-[10px] uppercase tracking-overline text-ink2">{m.model}</span>
                <StatusChip tone={m.status === "ok" ? "bull" : m.status === "empty" ? "muted" : "warn"} label={m.status} />
              </div>
            ))}
          </div>
        </TermPanel>
      )}
    </div>
  );
}