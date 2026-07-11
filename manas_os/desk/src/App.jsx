import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { fetchRunCard, fetchLatest, fetchMarket, fetchDebate } from "./api.js";
import MarketHomeTab from "./MarketHomeTab.jsx";
import ScannersTab from "./ScannersTab.jsx";
import ShortlistTab from "./ShortlistTab.jsx";
import DebateTab from "./DebateTab.jsx";
import TradePlanTab from "./TradePlanTab.jsx";
import PositionsTab from "./PositionsTab.jsx";
import LedgerTab from "./LedgerTab.jsx";
import { DensityContext, DENSITY_STORAGE_KEY, normalizeDensityMode } from "./DensityContext.jsx";
import { REGIME_GAUGE_ZONES } from "./viz.js";
import { Term } from "./Glossary.jsx";
import { CommandStrip, TickerTape } from "./components/v5/index.js";
import LiveWorkInspector from "./livework/LiveWorkInspector.jsx";
import { LiveWorkProvider, useLiveWork } from "./livework/useJobStream.js";
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
  // R2: offline_fallback payloads mean the API is unreachable and this is a
  // cached local snapshot -- the freshness stamp must say OFFLINE, not a
  // build sha, so it can't be mistaken for a live build.
  const sha = latest.offline_fallback ? "OFFLINE" : latest.build_sha || "unknown";
  const text = `DATA AS OF ${dataAsOf || "unknown"} (${rel}) · ${hint} · build ${sha}`;
  const isAmber = dataAsOf !== todayIso || !!latest.offline_fallback;
  return { text, isAmber };
}

// R2: true when any payload the shell has consumed came back tagged
// offline_fallback:true (api.js returns cached local JSON when the API is
// unreachable) -- used to render an honest "API offline" banner instead of
// silently presenting stale local data as if it were live.
export function computeOfflineBanner(latestMeta, card) {
  const offline = !!(latestMeta && latestMeta.offline_fallback) || !!(card && card.offline_fallback);
  if (!offline) return null;
  return "API offline — showing cached snapshot from 2026-07-10, numbers may be stale";
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

// Wave 1 CommandStrip VIX: honest passthrough only. Never present the
// offline-fallback hardcoded vix:13.4 as live -- an offline_fallback payload
// renders "--" with a title, the same as a genuinely missing vix.
export function computeVixDisplay(market) {
  if (!market || market.offline_fallback) {
    return { value: null, title: "India VIX not available for this date (API offline -- cached snapshot)" };
  }
  const vix = market.vix;
  if (!vix || vix.value === null || vix.value === undefined) {
    return { value: null, title: "India VIX not available for this date" };
  }
  return { value: vix.value, title: vix.band ? `VIX band: ${vix.band}` : undefined };
}

// TickerTape items from /api/desk/debate symbols: chair verdict tag,
// %65dL, ADR20, conviction -- real fields only, no synthetic fill.
export function debateToTapeItems(debate) {
  if (!debate || !debate.available || !Array.isArray(debate.symbols)) return [];
  return debate.symbols.map((s) => {
    const chair = s.chair || {};
    const metrics = s.scan_metrics || {};
    const tag = chair.verdict === "TAKE" ? "take" : chair.verdict === "SKIP" ? "skip" : null;
    const pctLow = metrics.pct_up_from_65d_low;
    return {
      symbol: s.symbol,
      tag,
      tagLabel: chair.struck && tag === "skip" ? "SKIP*" : undefined,
      metricLabel: pctLow !== null && pctLow !== undefined ? "65dL" : undefined,
      metricValue: pctLow !== null && pctLow !== undefined ? `${pctLow.toFixed(0)}%` : undefined,
    };
  });
}

function DeskApp() {
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
  const [latestMeta, setLatestMeta] = useState(null);
  const [debateJump, setDebateJump] = useState(null);
  const [tradePlan, setTradePlan] = useState(null);
  const [market, setMarket] = useState(null);
  const [tapeDebate, setTapeDebate] = useState(null);
  const liveWork = useLiveWork();
  const wasRunningRef = useRef(false);

  const goToDebate = useCallback((symbol) => {
    setDebateJump({ symbol: symbol || null, ts: Date.now() });
    setTradePlan(null);
    setTab("DEBATE");
  }, []);

  // V4-T13: per-symbol TRADE PLAN route (like the debateJump pattern) --
  // opened from a DEBATE card's [TRADE PLAN->] link or a SHORTLIST row's
  // "open trade plan" action. No router lib: tradePlan!=null simply
  // replaces the tab body with the full-screen route until dismissed.
  const openTradePlan = useCallback(
    (symbol) => {
      if (!symbol) return;
      setTradePlan({ symbol, date });
    },
    [date]
  );

  const closeTradePlan = useCallback(
    (symbol) => {
      goToDebate(symbol);
    },
    [goToDebate]
  );

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

  // Wave 1: CommandStrip needs VIX (from /api/desk/market) and the tape needs
  // debate symbols (from /api/desk/debate) -- fetched once per date,
  // independent of the tab-body fetches above so the shell renders real data
  // even when the user is sitting on a tab that doesn't itself call these.
  useEffect(() => {
    if (!date) return undefined;
    let cancelled = false;
    fetchMarket(date)
      .then((data) => {
        if (!cancelled) setMarket(data);
      })
      .catch(() => {
        if (!cancelled) setMarket(null);
      });
    fetchDebate(date)
      .then((data) => {
        if (!cancelled) setTapeDebate(data);
      })
      .catch(() => {
        if (!cancelled) setTapeDebate(null);
      });
    return () => {
      cancelled = true;
    };
  }, [date]);

  const startUpdate = useCallback(() => {
    if (liveWork.running) return;
    liveWork.start({ date, fetchSources: true }).catch((err) => setError(String(err)));
  }, [date, liveWork]);

  useEffect(() => {
    if (wasRunningRef.current && !liveWork.running) jumpToLatest();
    wasRunningRef.current = liveWork.running;
  }, [liveWork.running, jumpToLatest]);

  const staleLatestNudge = useMemo(() => {
    if (!date || liveWork.running) return false;
    return date < lastExpectedTradingDay(todayIso());
  }, [date, liveWork.running]);

  const staleBanner = useMemo(() => computeStaleBanner(card), [card]);
  const freshnessStamp = useMemo(() => computeFreshnessStamp(latestMeta, todayIso()), [latestMeta]);
  const offlineBanner = useMemo(() => computeOfflineBanner(latestMeta, card), [latestMeta, card]);

  const vixDisplay = useMemo(() => computeVixDisplay(market), [market]);
  const tapeItems = useMemo(() => debateToTapeItems(tapeDebate), [tapeDebate]);
  const regime = card && card.regime;
  const funnel = tapeDebate && tapeDebate.funnel;

  return (
    <DensityContext.Provider value={densityValue}>
      <div className={`v5 v5-shell shell density-${mode}`}>
        <CommandStrip
          date={date}
          dayColor={regime && regime.mbi_day_color}
          regimeMode={regime && regime.mode}
          hmmCaption={regime && regime.hmm_caption}
          vix={vixDisplay.value}
          vixTitle={vixDisplay.title}
          xp={regime && regime.xp !== null && regime.xp !== undefined ? regime.xp.toFixed(2) : null}
          universe={funnel && funnel.universe}
          debated={funnel && funnel.debated}
        />
        <TickerTape items={tapeItems} emptyLabel={`no debate for ${date || "this date"}`} />

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
            <button className="update-btn mono" onClick={startUpdate} disabled={liveWork.running}>
              {liveWork.running ? "⟳ UPDATING" : "⟳ UPDATE"}
            </button>
          </div>
        </header>

        <nav className="shell-tabs">
          <div className="shell-tabs-inner">
            {TABS.map((t) => (
              <button
                key={t}
                className={"tab-btn" + (t === tab && !tradePlan ? " active" : "")}
                onClick={() => {
                  // F7(a): top-nav clicks must exit the TRADE PLAN full-screen
                  // route -- tradePlan!=null short-circuits the tab body
                  // (see shell-body-inner below), so a bare setTab() here was
                  // a no-op while a plan was open. Clear the route first.
                  setTradePlan(null);
                  setTab(t);
                }}
              >
                {t}
              </button>
            ))}
            <button type="button" className="v5-live-trigger" onClick={() => liveWork.setOpen(true)}>
              {liveWork.running && <span className="v5-live-dot" aria-hidden="true" />}
              {liveWork.running ? `${liveWork.steps.filter((s) => s.status === "ok").length}/${liveWork.steps.length || "—"} live work` : "activity"}
            </button>
          </div>
        </nav>

        {offlineBanner && (
          <div className="stale-banner offline-fallback-banner">
            <span>⚠ {offlineBanner}</span>
          </div>
        )}
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
            {tradePlan ? (
              <TradePlanTab
                date={tradePlan.date}
                symbol={tradePlan.symbol}
                card={card}
                onBackToDebate={() => closeTradePlan(tradePlan.symbol)}
              />
            ) : (
              <>
                {tab === "MARKET" && (
                  <MarketHomeTab date={date} card={card} loading={loading} error={error} onNavigate={navigateTab} />
                )}
                {tab === "SCANNERS" && (
                  <ScannersTab date={date} />
                )}
                {tab === "SHORTLIST" && <ShortlistTab date={date} onOpenTradePlan={openTradePlan} />}
                {tab === "DEBATE" && (
                  <DebateTab date={date} card={card} jumpSignal={debateJump} onOpenTradePlan={openTradePlan} />
                )}
                {tab === "POSITIONS" && <PositionsTab date={date} />}
                {tab === "JOURNAL" && <LedgerTab />}
              </>
            )}
          </div>
        </main>
        <LiveWorkInspector />
      </div>
    </DensityContext.Provider>
  );
}

export default function App() {
  return (
    <LiveWorkProvider>
      <DeskApp />
    </LiveWorkProvider>
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
