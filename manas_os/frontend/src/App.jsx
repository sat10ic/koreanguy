import { useEffect, useState } from "react";
import RegimeSummary from "./components/RegimeSummary.jsx";
import FyersSetupPanel from "./components/FyersSetupPanel.jsx";
import HealthPage from "./components/HealthPage.jsx";
import SetupsPage from "./components/SetupsPage.jsx";
import WatchlistPage from "./components/WatchlistPage.jsx";
import JournalPage from "./components/JournalPage.jsx";
import FlowStepper from "./components/FlowStepper.jsx";
import ChartDrawer from "./components/ChartDrawer.jsx";
import DataStamp from "./components/DataStamp.jsx";
import { DensityToggle } from "./DensityContext.jsx";
import { runPipeline, getPipelineStatus } from "./api.js";

const HEADER_POSTURE = {
  RISK_ON: { cls: "bg-bull-dot", label: "risk-on" },
  SELECTIVE: { cls: "bg-warn-dot", label: "selective" },
  DEFENSIVE: { cls: "bg-bear-dot", label: "defensive" },
  NO_TRADE: { cls: "bg-ink", label: "no trade" },
  STALE: { cls: "bg-muted-dot", label: "stale" },
};

const TABS = [
  { id: "regime", label: "Regime", enabled: true },
  { id: "setups", label: "Setups", enabled: true },
  { id: "watchlist", label: "Watchlist", enabled: true },
  { id: "journal", label: "Journal", enabled: true },
  { id: "health", label: "Health", enabled: true },
];

export default function App() {
  const [tab, setTab] = useState("regime");
  const [posture, setPosture] = useState(null);
  const [health, setHealth] = useState({ loading: true, ok: null, fyersConnected: null });
  const [fyersOpen, setFyersOpen] = useState(false);
  const [selectedSymbol, setSelectedSymbol] = useState(null);
  const [refresh, setRefresh] = useState({ running: false, stage: null });

  const loadHealth = () =>
    fetch("http://127.0.0.1:8000/api/health")
      .then((r) => r.json())
      .then((d) => setHealth({ loading: false, ok: d.ok, fyersConnected: d.fyers_connected }))
      .catch(() => setHealth({ loading: false, ok: false, fyersConnected: false }));

  useEffect(() => {
    loadHealth();
  }, []);

  // Run the pipeline, poll until done, then hard-reload so every panel
  // refetches fresh data. `fetchSources` also refreshes the on-disk source
  // files first (slower) — that path lives on the Health tab.
  const doRefresh = async (fetchSources = false) => {
    if (refresh.running) return;
    setRefresh({ running: true, stage: fetchSources ? "fetching sources" : "starting" });
    try {
      await runPipeline({ fetchSources });
      const maxTicks = fetchSources ? 480 : 120;
      for (let i = 0; i < maxTicks; i++) {
        await new Promise((r) => setTimeout(r, 1500));
        const s = await getPipelineStatus();
        setRefresh({ running: s.running, stage: s.current_stage });
        if (!s.running) break;
      }
      window.location.reload();
    } catch (e) {
      setRefresh({ running: false, stage: `error: ${e.message}` });
    }
  };

  const badge = posture ? HEADER_POSTURE[posture] || HEADER_POSTURE.STALE : null;
  const activeTab = TABS.find((t) => t.id === tab)?.label || tab;
  const isStale = posture === "STALE";

  return (
    <div className="min-h-screen bg-bg">
      <header className="border-b border-hairline bg-card">
        <div className="mx-auto flex min-h-[56px] max-w-content items-center justify-between gap-4 px-6 py-2">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[14px] font-bold tracking-tight">
              MANAS<span className="text-bull"> OS</span>
            </span>
            <span className="font-mono text-[10px] uppercase tracking-overline text-ink3">
              · {activeTab}
            </span>
          </div>
          <div className="flex flex-wrap items-center justify-end gap-3 font-mono text-[10px] uppercase tracking-overline text-ink3">
            <span className="flex items-center gap-1" data-testid="header-posture">
              <span className={"inline-block h-1.5 w-1.5 rounded-full " + (badge?.cls || "bg-muted-dot")} />
              {badge?.label || "posture"}
            </span>
            <DataStamp mini nonce={refresh.running ? "running" : "idle"} />
            <DensityToggle />
            <button
              onClick={() => doRefresh(false)}
              disabled={refresh.running}
              data-testid="refresh-btn"
              title="Re-run the pipeline over current source files, then reload"
              className="flex items-center gap-1 border border-hairline px-2 py-0.5 uppercase tracking-overline hover:border-ink hover:text-ink disabled:opacity-60"
            >
              <span className={refresh.running ? "inline-block animate-spin" : ""}>⟳</span>
              {refresh.running ? (refresh.stage || "running") : "refresh"}
            </button>
            {!health.loading && (
              <button
                onClick={() => setFyersOpen(true)}
                className="flex items-center gap-1 uppercase tracking-overline hover:text-ink"
                data-testid="fyers-status"
                title="Connect / manage Fyers login"
              >
                <span
                  className={
                    "inline-block h-1.5 w-1.5 rounded-full " +
                    (health.fyersConnected ? "bg-bull-dot" : "bg-warn-dot")
                  }
                />
                fyers {health.fyersConnected ? "connected" : "connect"}
              </button>
            )}
          </div>
        </div>
        <nav className="mx-auto flex max-w-content gap-1 px-6 pb-2">
          {TABS.map((t) => (
            <button
              key={t.id}
              disabled={!t.enabled}
              onClick={() => t.enabled && setTab(t.id)}
              title={t.enabled ? undefined : "Coming soon"}
              data-testid={`nav-${t.id}`}
              className={
                "border px-2.5 py-1 font-mono text-[10px] uppercase tracking-overline transition-colors " +
                (!t.enabled
                  ? "cursor-not-allowed border-hairline text-inkDisabled"
                  : tab === t.id
                    ? "border-ink bg-ink text-white"
                    : "border-hairline text-ink2 hover:border-ink hover:text-ink")
              }
            >
              {t.label}
            </button>
          ))}
        </nav>
      </header>

      {isStale && (
        <div data-testid="stale-data-banner" className="border-b border-bear-border bg-bear-bg px-6 py-2">
          <div className="mx-auto flex max-w-content items-center gap-2">
            <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-bear-dot" />
            <span className="font-mono text-[11px] font-bold uppercase tracking-overline text-bear">
              Stale market data
            </span>
            <span className="font-sans text-[12px] text-ink2">
              Primary regime inputs are old; refresh before sizing fresh risk.
            </span>
          </div>
        </div>
      )}

      {!health.loading && !health.fyersConnected && (
        <div
          data-testid="fyers-auth-banner"
          className="border-b border-warn-border bg-warn-bg px-6 py-2"
        >
          <div className="mx-auto flex max-w-content items-center gap-2">
            <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-warn-dot" />
            <span className="font-mono text-[11px] font-bold uppercase tracking-overline text-warn">
              Fyers not connected
            </span>
            <span className="font-sans text-[12px] text-ink2">
              Live quotes + MARS run on fallback until Fyers is connected.
            </span>
            <button
              onClick={() => setFyersOpen(true)}
              data-testid="fyers-banner-connect"
              className="ml-auto border border-warn px-2 py-0.5 font-mono text-[10px] uppercase tracking-overline text-warn hover:bg-warn hover:text-white"
            >
              Connect Fyers
            </button>
          </div>
        </div>
      )}

      <main className="mx-auto max-w-content px-6 py-6">
        <div className="mb-4">
          <FlowStepper />
        </div>
        {tab === "regime" ? (
          <RegimeSummary onPosture={setPosture} />
        ) : tab === "setups" ? (
          <SetupsPage posture={posture} onSymbolSelect={setSelectedSymbol} />
        ) : tab === "watchlist" ? (
          <WatchlistPage posture={posture} onSymbolSelect={setSelectedSymbol} />
        ) : tab === "journal" ? (
          <JournalPage onSymbolSelect={setSelectedSymbol} />
        ) : (
          <HealthPage onUpdateLatest={() => doRefresh(true)} refresh={refresh} />
        )}
      </main>

      {fyersOpen && (
        <FyersSetupPanel onClose={() => setFyersOpen(false)} onConnected={loadHealth} />
      )}
      {selectedSymbol && (
        <ChartDrawer selection={selectedSymbol} onClose={() => setSelectedSymbol(null)} />
      )}
    </div>
  );
}
