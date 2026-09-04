import { useEffect, useState } from "react";
import DataStamp from "./DataStamp.jsx";
import { getEodAlerts, getPipelineStatus } from "../api.js";
import { Caption, SectionBadge, Verdict } from "./poster/Primitives.jsx";

/**
 * HealthPage — the Health tab. Data freshness + source-update controls +
 * the last pipeline run's per-stage result. The heavier "update to latest"
 * (fetch fresh source files, minutes-long) lives here, off the home page.
 */
export default function HealthPage({ onUpdateLatest, refresh }) {
  const [status, setStatus] = useState(null);
  const [alerts, setAlerts] = useState({ loading: true, error: null, data: null });

  useEffect(() => {
    let cancelled = false;
    const tick = () =>
      getPipelineStatus()
        .then((s) => !cancelled && setStatus(s))
        .catch(() => {});
    tick();
    // Poll while a run is in flight so the stage list updates live.
    const id = setInterval(tick, refresh?.running ? 1500 : 6000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [refresh?.running]);

  useEffect(() => {
    let cancelled = false;
    getEodAlerts({ limit: 20 })
      .then((data) => !cancelled && setAlerts({ loading: false, error: null, data }))
      .catch((error) => !cancelled && setAlerts({ loading: false, error: error.message, data: null }));
    return () => {
      cancelled = true;
    };
  }, [refresh?.running]);

  return (
    <section data-testid="health-page">
      <div className="mb-4 border border-hairline bg-card p-4 md:p-5">
        <SectionBadge label="HEALTH" state={refresh?.running ? "warn" : status?.running ? "warn" : "muted"} />
        <div className="mt-3">
          <Verdict>{refresh?.running || status?.running ? "PIPELINE IS RUNNING" : "SYSTEM STATUS READY"}</Verdict>
          <Caption>
            {status?.current_stage
              ? `Current stage is ${status.current_stage}; wait for the run to finish before trusting fresh reads.`
              : "Pipeline runs, data stamps, and EOD alerts are checked here before acting on the operating screens."}
          </Caption>
        </div>
      </div>
      <div className="mb-4 border border-hairline bg-card px-3 py-2">
        <DataStamp nonce={refresh?.running ? "running" : "idle"} />
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-3 border border-hairline bg-card px-3 py-3">
        <div className="flex-1">
          <div className="font-mono text-[12px] font-bold uppercase tracking-overline text-ink">
            Update to latest
          </div>
          <p className="mt-0.5 font-sans text-[11px] text-ink3">
            Fetches fresh source files — NSE bhavcopy + a ChartsMaze scrape — then re-ingests.
            Slower (can take a few minutes). Breadth is always pulled live during a normal refresh.
          </p>
        </div>
        <button
          onClick={onUpdateLatest}
          disabled={refresh?.running}
          data-testid="update-latest-btn"
          className="flex items-center gap-1 border border-info bg-info-bg px-3 py-1.5 font-mono text-[11px] uppercase tracking-overline text-info hover:bg-info hover:text-white disabled:opacity-60"
        >
          <span className={refresh?.running ? "inline-block animate-spin" : ""}>↧</span>
          {refresh?.running ? refresh.stage || "running" : "update to latest"}
        </button>
      </div>

      <div className="border border-hairline bg-card px-3 py-3">
        <div className="mb-2 font-mono text-[10px] uppercase tracking-overline text-ink3">
          Last pipeline run
        </div>
        {!status || (!status.stages?.length && !status.running) ? (
          <div className="font-sans text-[11px] text-ink3">No run recorded yet this session.</div>
        ) : (
          <ul className="space-y-1">
            {status.running && status.current_stage && (
              <li className="flex items-center gap-2 font-mono text-[11px] text-info">
                <span className="inline-block animate-spin">⟳</span>
                {status.current_stage}…
              </li>
            )}
            {(status.stages || []).map((s) => {
              const ok = s.status === "ok";
              return (
                <li key={s.name} className="flex items-center gap-2 font-mono text-[11px]">
                  <span
                    className={"inline-block h-1.5 w-1.5 rounded-full " + (ok ? "bg-bull-dot" : "bg-bear-dot")}
                  />
                  <span className="text-ink2">{s.name}</span>
                  <span className={ok ? "text-bull" : "text-bear"}>{s.status}</span>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      <div className="mt-4 border border-hairline bg-card px-3 py-3">
        <div className="mb-2 flex items-center justify-between">
          <div className="font-mono text-[10px] uppercase tracking-overline text-ink3">
            Latest EOD alerts
          </div>
          {alerts.data?.as_of && (
            <div className="font-mono text-[10px] uppercase tracking-overline text-ink3">
              as of {alerts.data.as_of}
            </div>
          )}
        </div>
        {alerts.loading ? (
          <div className="font-sans text-[11px] text-ink3">loading alerts...</div>
        ) : alerts.error ? (
          <div className="font-sans text-[11px] text-bear">{alerts.error}</div>
        ) : !alerts.data?.available || alerts.data.alerts.length === 0 ? (
          <div className="border border-dashed border-hairline px-3 py-5 text-center font-sans text-[11px] text-ink3">
            No EOD alerts generated yet. Run refresh after scan_candidates is available.
          </div>
        ) : (
          <ul className="space-y-1">
            {alerts.data.alerts.map((alert) => (
              <li key={alert.alert_id} className="border border-hairline2 bg-raised px-2 py-2">
                <div className="flex flex-wrap items-center gap-2">
                  <span className={"h-1.5 w-1.5 rounded-full " + severityDot(alert.severity)} />
                  <span className="font-mono text-[10px] font-bold uppercase tracking-overline text-ink">
                    {alert.title}
                  </span>
                  <span className="font-mono text-[9px] uppercase tracking-overline text-ink3">
                    {alert.alert_type}
                  </span>
                </div>
                <p className="mt-1 font-sans text-[11px] leading-snug text-ink3">{alert.detail}</p>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

function severityDot(severity) {
  if (severity === "critical" || severity === "blocked") return "bg-bear-dot";
  if (severity === "action") return "bg-bull-dot";
  if (severity === "warning") return "bg-warn-dot";
  return "bg-muted-dot";
}
