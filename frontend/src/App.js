import React, { useEffect, useState, useCallback } from "react";
import { endpoints } from "./api";
import { Spinner } from "./ui";
import RegimePanel from "./components/RegimePanel";
import UniverseSummary from "./components/UniverseSummary";
import CandidatesPanel from "./components/CandidatesPanel";
import PositionsPanel from "./components/PositionsPanel";
import RSGridPanel from "./components/RSGridPanel";
import WatchlistPanel from "./components/WatchlistPanel";
import PipelineControl from "./components/PipelineControl";
import HistoryChart from "./components/HistoryChart";
import SymbolDrawer from "./components/SymbolDrawer";
import { Activity, Cpu, Database } from "lucide-react";

function formatTime(d) {
  if (!d) return "";
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

const TABS = [
  { id: "candidates", label: "Candidates" },
  { id: "positions", label: "Positions" },
  { id: "rsgrid", label: "RS Grid" },
  { id: "watchlist", label: "Watchlist" },
];

export default function App() {
  const [tab, setTab] = useState("candidates");
  const [health, setHealth] = useState(null);
  const [regime, setRegime] = useState(null);
  const [uni, setUni] = useState(null);
  const [candidates, setCandidates] = useState({ primary: [], secondary: [] });
  const [positions, setPositions] = useState({ rows: [], summary: {}, stats: {} });
  const [rsGrid, setRsGrid] = useState(null);
  const [watchlist, setWatchlist] = useState({ rows: [] });
  const [history, setHistory] = useState({ rows: [] });
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [activeSymbol, setActiveSymbol] = useState(null);
  const [loading, setLoading] = useState(true);
  const [universeMeta, setUniverseMeta] = useState({ total: 0 });
  const [lastUpdated, setLastUpdated] = useState(null);

  const refreshAll = useCallback(async () => {
    try {
      const [h, r, u, c, p, g, w, hi, um] = await Promise.all([
        endpoints.health().catch(() => null),
        endpoints.regime().catch(() => null),
        endpoints.universeSummary().catch(() => null),
        endpoints.candidates().catch(() => ({ primary: [], secondary: [] })),
        endpoints.positions().catch(() => ({ rows: [], summary: {}, stats: {} })),
        endpoints.rsGrid().catch(() => null),
        endpoints.watchlist().catch(() => ({ rows: [] })),
        endpoints.candidatesHistory(30).catch(() => ({ rows: [] })),
        endpoints.universe().catch(() => ({ total: 0 })),
      ]);
      setHealth(h);
      setRegime(r);
      setUni(u);
      setCandidates(c);
      setPositions(p);
      setRsGrid(g);
      setWatchlist(w);
      setHistory(hi);
      setUniverseMeta(um);
      setLastUpdated(new Date());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshAll();
  }, [refreshAll]);

  // Auto-refresh every 5 minutes so the board stays "live" without
  // requiring the user to reload. Also pauses while the pipeline is
  // running (the pipeline poll already triggers a refresh on completion).
  useEffect(() => {
    const id = setInterval(() => {
      if (!pipelineRunning) refreshAll();
    }, 5 * 60 * 1000);
    return () => clearInterval(id);
  }, [refreshAll, pipelineRunning]);

  useEffect(() => {
    let timer;
    const poll = async () => {
      try {
        const s = await endpoints.pipelineStatus();
        setPipelineRunning(!!s.running);
        if (!s.running && pipelineRunning) {
          // Just finished — refresh
          await refreshAll();
        }
      } catch (e) {}
      timer = setTimeout(poll, 2000);
    };
    poll();
    return () => clearTimeout(timer);
  }, [pipelineRunning, refreshAll]);

  const todayDate = regime?.date || new Date().toISOString().slice(0, 10);

  return (
    <div className="min-h-screen bg-page text-textPrimary">
      <div className="grid-bg pointer-events-none fixed inset-0" />

      {/* Top Header Bar */}
      <header className="sticky top-0 z-20 border-b border-borderDefault bg-page/90 backdrop-blur">
        <div className="mx-auto flex max-w-[1640px] items-center justify-between px-6 py-3">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <div className="font-mono text-[11px] uppercase tracking-overline text-saffron">
                ◢◤
              </div>
              <h1
                className="text-base font-medium tracking-tighter text-textPrimary"
                data-testid="app-title"
              >
                SwingEdge<span className="text-textMuted">·Lite</span>
              </h1>
            </div>
            <div className="hidden items-center gap-4 text-[10px] uppercase tracking-overline text-textMuted md:flex">
              <span>NSE · NIFTY {universeMeta?.total || 500}</span>
              <span className="border-l border-borderDefault pl-4">
                Phase 1 · Daily EOD
              </span>
              <span className="border-l border-borderDefault pl-4 text-textSecondary">
                Session: <span className="font-mono text-textPrimary">{todayDate}</span>
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden items-center gap-1.5 text-[10px] uppercase tracking-overline text-textMuted md:flex">
              <span
                className={`inline-block h-1.5 w-1.5 ${
                  health?.status === "ok" ? "bg-bull animate-pulse" : "bg-bear"
                }`}
              />
              <span>{health?.status === "ok" ? "API Live" : "API Down"}</span>
            </div>
            <button
              data-testid="manual-refresh-btn"
              onClick={refreshAll}
              title={
                lastUpdated
                  ? `Last refreshed ${lastUpdated.toLocaleTimeString()} · auto-refresh every 5 min`
                  : "Refresh now"
              }
              className="hidden items-center gap-1.5 border border-borderDefault px-2 py-1 font-mono text-[10px] uppercase tracking-overline text-textSecondary transition-colors hover:border-bull hover:text-bull md:flex"
            >
              <span className="inline-block h-1 w-1 bg-bull" />
              {lastUpdated
                ? `Live · ${formatTime(lastUpdated)}`
                : "Refresh"}
            </button>
            <PipelineControl
              running={pipelineRunning}
              onStarted={() => setPipelineRunning(true)}
            />
          </div>
        </div>
      </header>

      <main className="relative mx-auto max-w-[1640px] px-6 py-6">
        {loading && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-page/50">
            <Spinner label="loading dashboard" />
          </div>
        )}

        {/* Regime + Universe Summary block */}
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
          <div className="xl:col-span-8">
            <RegimePanel regime={regime} />
          </div>
          <div className="xl:col-span-4">
            <UniverseSummary uni={uni} onSymbol={setActiveSymbol} />
          </div>
        </div>

        {/* History chart row */}
        <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-12">
          <div className="xl:col-span-12">
            <HistoryChart
              rows={history?.rows || []}
              positionsStats={positions?.stats || {}}
              positionsSummary={positions?.summary || {}}
            />
          </div>
        </div>

        {/* Tab bar */}
        <nav className="mt-6 flex flex-wrap items-end gap-0 border-b border-borderDefault">
          {TABS.map((t) => {
            const active = t.id === tab;
            const counts = {
              candidates:
                (candidates?.primary?.length || 0) +
                (candidates?.secondary?.length || 0),
              positions: positions?.rows?.length || 0,
              rsgrid: uni?.total || 0,
              watchlist: watchlist?.rows?.length || 0,
            };
            return (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                data-testid={`tab-${t.id}`}
                className={`relative -mb-px border-b-2 px-4 py-2 font-mono text-[11px] uppercase tracking-overline transition-colors ${
                  active
                    ? "border-bull text-textPrimary"
                    : "border-transparent text-textSecondary hover:text-textPrimary"
                }`}
              >
                {t.label}
                <span className="ml-2 text-textMuted">[{counts[t.id]}]</span>
              </button>
            );
          })}
        </nav>

        <div className="mt-4">
          {tab === "candidates" && (
            <CandidatesPanel
              data={candidates}
              onSymbol={setActiveSymbol}
            />
          )}
          {tab === "positions" && (
            <PositionsPanel data={positions} onSymbol={setActiveSymbol} />
          )}
          {tab === "rsgrid" && (
            <RSGridPanel data={rsGrid} onSymbol={setActiveSymbol} />
          )}
          {tab === "watchlist" && (
            <WatchlistPanel
              data={watchlist}
              onSymbol={setActiveSymbol}
              onChange={refreshAll}
            />
          )}
        </div>

        <footer className="mt-12 flex items-center justify-between border-t border-borderDefault py-4 text-[10px] uppercase tracking-overline text-textMuted">
          <div className="flex items-center gap-3">
            <Activity size={11} />
            <span>Read-only paper trading · No orders executed</span>
          </div>
          <div className="flex items-center gap-3">
            <Database size={11} />
            <span>Data: yfinance EOD · Fyers compatible</span>
            <span className="border-l border-borderDefault pl-3">
              <Cpu size={11} className="-mt-0.5 inline" /> v0.3
            </span>
          </div>
        </footer>
      </main>

      {activeSymbol && (
        <SymbolDrawer symbol={activeSymbol} onClose={() => setActiveSymbol(null)} />
      )}
    </div>
  );
}
