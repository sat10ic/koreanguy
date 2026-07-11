import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { fetchRunCard, fetchLatest, runPipeline, getPipelineStatus } from "./api.js";
import MarketHomeTab from "./MarketHomeTab.jsx";
import ScannersTab from "./ScannersTab.jsx";
import DebateTab from "./DebateTab.jsx";
import PositionsTab from "./PositionsTab.jsx";
import LedgerTab from "./LedgerTab.jsx";
import { DensityContext, DENSITY_STORAGE_KEY, normalizeDensityMode } from "./DensityContext.jsx";
import { REGIME_GAUGE_ZONES } from "./viz.js";
import { Term } from "./Glossary.jsx";
import "./App.css";

const TABS = ["MARKET", "SCANNERS", "SHORTLIST", "DEBATE", "POSITIONS", "JOURNAL"];

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

function shiftDate(iso, days) {
  const d = new Date((iso || todayIso()) + "T00:00:00");
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
          <polygon points={`${markerX - 3},0 ${markerX + 3},0 ${markerX},5`} fill="var(--ink)" />
        )}
      </svg>
      <div className="regime-gauge-label mono">
        {mode && modeTerm(mode) ? <Term k={modeTerm(mode)}>{mode}</Term> : <span>{mode || "â€”"}</span>}
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

function lastExpectedTradingDay(iso) {
  let d = new Date(iso + "T00:00:00");
  do {
    d.setDate(d.getDate() - 1);
  } while (d.getDay() === 0 || d.getDay() === 6);
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${m}-${day}`;
}

export function relativeDayLabel(dataAsOf, todayIso) {
  if (!dataAsOf) return "unknown";
  const a = new Date(dataAsOf + "T00:00:00");
  const b = new Date(todayIso + "T00:00:00");
  const days = Math.round((b - a) / 86400000);
  if (days === 0) return "today";
  if (days === 1) return "yesterday";
  if (days > 1) return `${days} days ago`;
  return dataAsOf;
}

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
  const lastBad = stages.find((s) => ["error", "partial", "fail"].includes(s.status));
  if (!lastBad) return null;
  return `Data fresh only through ${card.scan_date || card.run_date} — last night's run did not complete.`;
}

export default function App() {
  const [date, setDate] = useState(null);
  const [tab, setTab] = useState("MARKET");
  const [mode, setModeState] = useState(() => {
    if (typeof window === "undefined") return "beginner";
    return normalizeDensityMode(window.localStorage.getItem(DENSITY_STORAGE_KEY));
  });
  const [symbolSearch, setSymbolSearch] = useState("");
  const [card, setCard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [updateStage, setUpdateStage] = useState(null);
  const [latestMeta, setLatestMeta] = useState(null);
  const [debateJump, setDebateJump] = useState(null);
  const pollRef = useRef(null);

  const goToDebate = useCallback((symbol) => {
    setDebateJump({ symbol: symbol || null, ts: Date.now() });
    setTab("DEBATE");
  }, []);

  const navigateTab = useCallback((nextTab) => {
    if (TABS.includes(nextTab)) setTab(nextTab);
  }, []);

  const setMode = useCallback((nextMode) => {
    const normalized = normalizeDensityMode(nextMode);
    setModeState(normalized);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(DENSITY_STORAGE_KEY, normalized);
    }
  }, []);

  const densityValue = useMemo(
    () => ({
      mode,
      isExpert: mode === "expert",
      setMode,
      toggleMode: () => setMode(mode === "expert" ? "beginner" : "expert"),
    }),
    [mode, setMode]
  );

  const submitSymbolSearch = useCallback(
    (event) => {
      event.preventDefault();
      const symbol = symbolSearch.trim().toUpperCase();
      if (!symbol) return;
      goToDebate(symbol);
      setSymbolSearch("");
    },
    [goToDebate, symbolSearch]
  );

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

  useEffect(() => {
    jumpToLatest();
  }, [jumpToLatest]);

  useEffect(() => {
    const id = setInterval(() => {
      fetchLatest()
        .then((latest) => setLatestMeta(latest))
        .catch(() => {});
    }, 5 * 60 * 1000);
    return () => clearInterval(id);
  }, []);

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
    if (updateStage) return;
    setUpdateStage("starting...");
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
                setUpdateStage(status.current_stage || "running...");
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

  const staleBanner = useMemo(() => computeStaleBanner(card), [card]);
  const freshnessStamp = useMemo(() => computeFreshnessStamp(latestMeta, todayIso()), [latestMeta]);

  return (
    <DensityContext.Provider value={densityValue}>
      <div className={`shell density-${mode}`}>
        <header className="shell-header">
          <div className="shell-brand">
            <span className="shell-brand-tick" aria-hidden="true" />
            <span className="shell-title mono">MANAS</span>
          </div>
          <div className="date-scrubber" role="group" aria-label="date scrubber">
            <button onClick={() => setDate((d) => shiftDate(d, -1))} aria-label="previous date">
              ◀
            </button>
            <span className="mono date-scrubber-value">{date || "..."}</span>
            <button onClick={() => setDate((d) => shiftDate(d, 1))} aria-label="next date">
              ▶
            </button>
          </div>
          <div className="shell-header-right">
            <RegimeGauge regime={card && card.regime} />
            <XpBadge regime={card && card.regime} />
            <form className="symbol-search" onSubmit={submitSymbolSearch} role="search">
              <span aria-hidden="true">⌕</span>
              <input
                value={symbolSearch}
                onChange={(e) => setSymbolSearch(e.target.value)}
                placeholder="symbol search"
                aria-label="symbol search"
              />
            </form>
            <div className="mode-toggle mono" role="group" aria-label="beginner expert mode">
              <button type="button" className={mode === "beginner" ? "active" : ""} onClick={() => setMode("beginner")}>
                beginner
              </button>
              <button type="button" className={mode === "expert" ? "active" : ""} onClick={() => setMode("expert")}>
                expert
              </button>
            </div>
            <button className="update-btn mono" onClick={startUpdate} disabled={!!updateStage}>
              {updateStage ? `⟳ ${updateStage}` : "⟳ UPDATE"}
            </button>
          </div>
        </header>

        <nav className="shell-tabs">
          <div className="shell-tabs-inner">
            {TABS.map((t) => (
              <button key={t} className={"tab-btn" + (t === tab ? " active" : "")} onClick={() => setTab(t)}>
                {t}
              </button>
            ))}
            <span className="pipeline-status mono">
              {(pipelineRunning || updateStage) && (
                <>
                  <span className="pipeline-dot" /> pipeline running{updateStage ? ` - ${updateStage}` : ""}
                </>
              )}
            </span>
          </div>
        </nav>

        {freshnessStamp && (
          <div className={"freshness-stamp mono" + (freshnessStamp.isAmber ? " freshness-stamp-amber" : "")}>
            {freshnessStamp.text}
          </div>
        )}
        {latestMeta && latestMeta.stale_build && (
          <div className="stale-banner">
            <span>⚠ desk running an older build - restart to pick up updates</span>
          </div>
        )}
        {staleBanner && (
          <div className="stale-banner">
            <span>⚠ {staleBanner}</span>
          </div>
        )}
        {!staleBanner && staleLatestNudge && (
          <div className="stale-banner">
            <span>
              ⚠ Data fresh only through {date} - the last expected trading day has more recent data available.
              <button className="stale-banner-link" onClick={startUpdate}>
                Run update now
              </button>
            </span>
          </div>
        )}

        <main className="shell-body">
          <div className="shell-body-inner">
            {tab === "MARKET" && (
              <MarketHomeTab date={date} card={card} loading={loading} error={error} onNavigate={navigateTab} />
            )}
            {tab === "SCANNERS" && (
              <ScannersTab date={date} />
            )}
            {tab === "SHORTLIST" && (
              <PlaceholderPane label="SHORTLIST" note="building - curator watchlist and weekly charts wire in later slices" />
            )}
            {tab === "DEBATE" && <DebateTab date={date} card={card} jumpSignal={debateJump} />}
            {tab === "POSITIONS" && <PositionsTab date={date} />}
            {tab === "JOURNAL" && <LedgerTab />}
          </div>
        </main>
      </div>
    </DensityContext.Provider>
  );
}

function PlaceholderPane({ label, note }) {
  return (
    <div className="empty-state placeholder-tab">
      <div className="empty-state-icon">○</div>
      <p className="empty-state-line">{label}</p>
      <p className="empty-state-sub">{note}</p>
    </div>
  );
}
