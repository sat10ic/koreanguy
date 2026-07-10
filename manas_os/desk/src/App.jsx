import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { fetchRunCard, fetchLatest, runPipeline, getPipelineStatus } from "./api.js";
import DeskTab from "./DeskTab.jsx";
import DebateTab from "./DebateTab.jsx";
import MarketTab from "./MarketTab.jsx";
import PositionsTab from "./PositionsTab.jsx";
import LedgerTab from "./LedgerTab.jsx";
import { REGIME_GAUGE_ZONES } from "./viz.js";
import { Term } from "./Glossary.jsx";
import "./App.css";

const TABS = ["DESK", "DEBATE", "MARKET", "POSITIONS", "LEDGER"];

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

function shiftDate(iso, days) {
  // Format from LOCAL date parts — toISOString() converts to UTC, which on
  // IST (+5:30) lands on the previous calendar day: "prev" jumped 2 days and
  // "next" was a no-op.
  const d = new Date(iso + "T00:00:00");
  d.setDate(d.getDate() + days);
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${m}-${day}`;
}

function modeTerm(mode) {
  const m = (mode || "").toUpperCase();
  if (m === "RISK_ON") return "mode-risk-on";
  if (m === "SELECTIVE") return "mode-selective";
  if (m === "DEFENSIVE") return "mode-defensive";
  if (m === "NO_TRADE") return "mode-no-trade";
  return null;
}

// V1: DESK regime -> a color-state gauge (horizontal SVG meter), replacing
// the text-only mode pill. Zones are colored by regime semantics
// (NO_TRADE ink / DEFENSIVE red / SELECTIVE amber / RISK_ON green), a marker
// sits over the current mode's zone, day-count renders underneath.
function RegimeGauge({ regime }) {
  const mode = regime && regime.mode;
  const age = regime && regime.age_days;
  const zoneW = 100 / REGIME_GAUGE_ZONES.length;
  const activeIdx = REGIME_GAUGE_ZONES.findIndex((z) => z.mode === mode);
  const markerX = activeIdx >= 0 ? zoneW * activeIdx + zoneW / 2 : null;

  return (
    <div className="regime-gauge" title={mode ? `[B] regime mode: ${mode}` : "no regime snapshot"}>
      <svg className="regime-gauge-svg" viewBox="0 0 100 14" preserveAspectRatio="none">
        {REGIME_GAUGE_ZONES.map((z, i) => (
          <rect
            key={z.mode}
            x={zoneW * i}
            y="2"
            width={zoneW}
            height="8"
            fill={z.color}
            opacity={mode === z.mode ? 1 : 0.28}
          />
        ))}
        {markerX !== null && (
          <polygon
            points={`${markerX - 3},0 ${markerX + 3},0 ${markerX},5`}
            fill="var(--ink)"
          />
        )}
      </svg>
      <div className="regime-gauge-label mono">
        {mode && modeTerm(mode) ? <Term k={modeTerm(mode)}>{mode}</Term> : <span>{mode || "—"}</span>}
        {age !== null && age !== undefined && (
          <span className="regime-gauge-day">
            <Term k="regime-age">day {age}</Term>
          </span>
        )}
      </div>
    </div>
  );
}

function XpBadge({ regime }) {
  const xp = regime && regime.xp;
  if (xp === null || xp === undefined) return null;
  return (
    <div className="xp-badge mono" title="[B] Desk readiness score">
      <span className="xp-badge-value">{Math.round(xp)}</span>
      <span className="xp-badge-label">
        <Term k="xp-badge">XP</Term>
      </span>
    </div>
  );
}

// Weekday-only check for the stale-nudge — good enough to flag "the last
// run_card is older than the last expected trading day" without pulling in
// the server-side market_calendar (holidays aren't worth a round-trip here;
// worst case the nudge shows one extra day around a holiday).
function lastExpectedTradingDay(iso) {
  let d = new Date(iso + "T00:00:00");
  do {
    d.setDate(d.getDate() - 1);
  } while (d.getDay() === 0 || d.getDay() === 6);
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${m}-${day}`;
}

// SHIP-1 item 3: exported (not inlined in the useMemo) so it's independently
// vitest-covered — a no_op card (phantom run_card fix) must bank a plain
// "STALE — showing last completed night <scan_date>" banner instead of the
// desk silently opening on carried-forward data that looks like tonight's.
// Relative-day label for the freshness stamp — deliberately calendar-day
// (not trading-day) math: "today/yesterday/N days ago" reads naturally to a
// human glancing at the header, unlike a trading-day count.
export function relativeDayLabel(dataAsOf, todayIso) {
  if (!dataAsOf) return "unknown";
  const a = new Date(dataAsOf + "T00:00:00");
  const b = new Date(todayIso + "T00:00:00");
  const days = Math.round((b - a) / 86400000);
  if (days === 0) return "today";
  if (days === 1) return "yesterday";
  if (days > 1) return `${days} days ago`;
  return dataAsOf; // future-dated data_as_of shouldn't happen; show raw date
}

// SHIP: the permanent freshness stamp bar — always visible, distinct from
// the harder stale-nudge banner above. Exported (not inlined) so it's
// independently vitest-covered.
export function computeFreshnessStamp(latest, todayIso) {
  if (!latest) return null;
  const dataAsOf = latest.data_as_of;
  const rel = relativeDayLabel(dataAsOf, todayIso);
  const hint = latest.next_update_hint || "";
  const sha = latest.build_sha || "unknown";
  const text = `DATA AS OF ${dataAsOf || "unknown"} (${rel}) · ${hint} · build ${sha}`;
  const isAmber = dataAsOf !== todayIso;
  return { text, isAmber };
}

export function computeStaleBanner(card) {
  if (!card || !card.available) return null;
  if (card.no_op) {
    return `STALE — showing last completed night ${card.scan_date || card.run_date}`;
  }
  const stages = card.pipeline || [];
  // 'skip' is a normal graceful stage (e.g. mars without a Fyers token) —
  // only genuine failures mean the night didn't complete.
  const lastBad = stages.find((s) => ["error", "partial", "fail"].includes(s.status));
  if (!lastBad) return null;
  return `Data fresh only through ${card.scan_date || card.run_date} — last night's run did not complete.`;
}

export default function App() {
  const [date, setDate] = useState(null);
  const [tab, setTab] = useState("DESK");
  const [card, setCard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [updateStage, setUpdateStage] = useState(null);
  const [latestMeta, setLatestMeta] = useState(null);
  const pollRef = useRef(null);

  const jumpToLatest = useCallback(() => {
    return fetchLatest()
      .then((latest) => {
        const next = latest.latest_run_card_date || latest.latest_scan_date || todayIso();
        setDate(next);
        setLatestMeta(latest);
        // eslint-disable-next-line no-console
        console.log(`[MANAS DESK] build ${latest.build_sha || "unknown"} · data as of ${latest.data_as_of || "unknown"}`);
        return latest;
      })
      .catch(() => {
        setDate((d) => d || todayIso());
      });
  }, []);

  // Desk opens ON the most recent completed night — every tab would
  // otherwise show empty because verdicts live under the latest SCAN date,
  // not today.
  useEffect(() => {
    jumpToLatest();
  }, [jumpToLatest]);

  useEffect(() => {
    if (!date) return undefined;
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchRunCard(date)
      .then((data) => {
        if (cancelled) return;
        setCard(data);
        const running = (data.pipeline || []).some((p) => p.status === null || p.status === undefined);
        setPipelineRunning(running);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(String(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [date]);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const startUpdate = useCallback(() => {
    if (updateStage) return; // already running
    setUpdateStage("starting…");
    runPipeline({ fetch_sources: true })
      .catch((err) => {
        setUpdateStage(null);
        setError(String(err));
      })
      .then(() => {
        pollRef.current = setInterval(() => {
          getPipelineStatus()
            .then((status) => {
              if (status.running) {
                setUpdateStage(status.current_stage || "running…");
              } else {
                stopPolling();
                setUpdateStage(null);
                jumpToLatest();
              }
            })
            .catch(() => {
              stopPolling();
              setUpdateStage(null);
            });
        }, 3000);
      });
  }, [updateStage, stopPolling, jumpToLatest]);

  useEffect(() => stopPolling, [stopPolling]);

  const staleLatestNudge = useMemo(() => {
    if (!date || updateStage) return false;
    return date < lastExpectedTradingDay(todayIso());
  }, [date, updateStage]);

  const live = useMemo(() => {
    if (!card || !card.signals) return false;
    return card.signals.some((s) => s.sent);
  }, [card]);

  const staleBanner = useMemo(() => computeStaleBanner(card), [card]);
  const freshnessStamp = useMemo(() => computeFreshnessStamp(latestMeta, todayIso()), [latestMeta]);

  return (
    <div className="shell">
      <header className="shell-header">
        <div className="shell-brand">
          <span className="shell-brand-tick" aria-hidden="true" />
          <span className="shell-title mono">MANAS DESK</span>
        </div>
        <div className="date-scrubber" role="group" aria-label="date scrubber">
          <button onClick={() => setDate((d) => shiftDate(d, -1))} aria-label="previous date">
            ◀
          </button>
          <span className="mono date-scrubber-value">{date || "…"}</span>
          <button onClick={() => setDate((d) => shiftDate(d, 1))} aria-label="next date">
            ▶
          </button>
        </div>
        <div className="shell-header-right">
          <RegimeGauge regime={card && card.regime} />
          <XpBadge regime={card && card.regime} />
          <span className={"live-badge mono " + (live ? "live" : "dry")}>
            {live ? <Term k="live">● LIVE</Term> : <Term k="dry-run">⦿ DRY-RUN</Term>}
          </span>
          <button className="update-btn mono" onClick={startUpdate} disabled={!!updateStage}>
            {updateStage ? `⟳ ${updateStage}…` : "⟳ UPDATE"}
          </button>
        </div>
      </header>
      {freshnessStamp && (
        <div className={"freshness-stamp mono" + (freshnessStamp.isAmber ? " freshness-stamp-amber" : "")}>
          {freshnessStamp.text}
        </div>
      )}
      <nav className="shell-tabs">
        <div className="shell-tabs-inner">
          {TABS.map((t) => (
            <button
              key={t}
              className={"tab-btn" + (t === tab ? " active" : "")}
              onClick={() => setTab(t)}
            >
              {t}
            </button>
          ))}
          <span className="pipeline-status mono">
            {(pipelineRunning || updateStage) && (
              <>
                <span className="pipeline-dot" /> pipeline running{updateStage ? ` — ${updateStage}` : ""}
              </>
            )}
          </span>
        </div>
      </nav>
      {staleBanner && (
        <div className="stale-banner">
          <span>⚠ {staleBanner}</span>
        </div>
      )}
      {!staleBanner && staleLatestNudge && (
        <div className="stale-banner">
          <span>
            ⚠ Data fresh only through {date} — the last expected trading day has more recent data available.
            <button className="stale-banner-link" onClick={startUpdate}>
              Run update now
            </button>
          </span>
        </div>
      )}
      <main className="shell-body">
        <div className="shell-body-inner">
          {tab === "DESK" && (
            <DeskTab date={date} card={card} loading={loading} error={error} />
          )}
          {tab === "DEBATE" && <DebateTab date={date} card={card} />}
          {tab === "MARKET" && <MarketTab date={date} />}
          {tab === "POSITIONS" && <PositionsTab date={date} />}
          {tab === "LEDGER" && <LedgerTab />}
        </div>
      </main>
    </div>
  );
}

function PlaceholderPane({ label, note }) {
  return (
    <div className="empty-state">
      <div className="empty-state-icon">◌</div>
      <p className="empty-state-line">{label} tab not built yet.</p>
      <p className="empty-state-sub">{note}</p>
    </div>
  );
}
