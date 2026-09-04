// sat10ic OS — light-terminal shell.
// Tape (index quotes) + F-key tab bar + status cluster (posture / date /
// fyers stage / density / refresh-with-progress). Panels mount below.

import { useEffect, useState } from "react";
import { getRegimeIndices, getPipelineStatus, getFyersStatus, runPipeline } from "./api.js";
import { StatusChip } from "./primitives.jsx";
import RegimePage from "./regime.jsx";
import SetupsPage from "./setups.jsx";
import WatchlistPage from "./watchlist.jsx";
import JournalPage from "./journal.jsx";
import HealthPage from "./health.jsx";

const TABS = [
  { id: "regime", label: "Regime", key: "R" },
  { id: "setups", label: "Setups", key: "S" },
  { id: "focus", label: "Focus", key: "F" },
  { id: "watchlist", label: "Watchlist", key: "W" },
  { id: "journal", label: "Journal", key: "J" },
  { id: "health", label: "Health", key: "H" },
];

const POSTURE_TONE = {
  RISK_ON: "bull",
  SELECTIVE: "warn",
  DEFENSIVE: "bear",
  NO_TRADE: "bear",
  STALE: "muted",
};

const FYERS_LABEL = {
  ready: { label: "fyers · live", tone: "bull" },
  missing_app_id: { label: "fyers · set app id", tone: "warn" },
  missing_token: { label: "fyers · log in today", tone: "warn" },
};

// Raw pipeline stage name -> plain words (the jargon layer, per contract).
const STAGE_PLAIN = {
  "fetching sources": "downloading today's files",
  starting: "starting…",
  refresh_live_quotes: "live quotes",
  ingest_breadth: "market breadth",
  scan_candidates: "scanning the universe",
  backtest_lockup: "quality checks",
};

function plainStage(name) {
  if (!name) return "working…";
  return STAGE_PLAIN[name] || String(name).replace(/_/g, " ");
}

export default function App() {
  const [tab, setTab] = useState("regime");
  const [posture, setPosture] = useState(null);
  const [tape, setTape] = useState({ loading: true, rows: [] });
  const [refresh, setRefresh] = useState(null); // null | {running, stageIndex, total, currentStage, eta}
  const [fyers, setFyers] = useState({ status: "unknown", loading: true });
  const [fyersOpen, setFyersOpen] = useState(false);
  const [density, setDensity] = useState("beginner"); // beginner | expert

  // Tape: index quotes, colored chips.
  useEffect(() => {
    let alive = true;
    getRegimeIndices()
      .then((d) => alive && setTape({ loading: false, rows: d?.indices || [] }))
      .catch(() => alive && setTape({ loading: false, rows: [] }));
    return () => {
      alive = false;
    };
  }, []);

  // Fyers stage: reflects what's actually blocking.
  useEffect(() => {
    let alive = true;
    const load = () =>
      getFyersStatus()
        .then((s) => alive && setFyers({ status: s?.status || "missing_app_id", loading: false }))
        .catch(() => alive && setFyers({ status: "unknown", loading: false }));
    load();
    const id = setInterval(load, 60000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  // Refresh: kick the pipeline, then poll progress until done, then reload.
  const doRefresh = async (fetchSources = false) => {
    if (refresh?.running) return;
    setRefresh({ running: true, stageIndex: 1, total: 1, currentStage: "starting", eta: null });
    try {
      await runPipeline({ fetchSources });
      for (let i = 0; i < 480; i++) {
        await new Promise((r) => setTimeout(r, 1500));
        const s = await getPipelineStatus();
        setRefresh({
          running: s.running,
          stageIndex: s.stage_index || 1,
          total: s.total_stages || 1,
          currentStage: s.current_stage,
          eta: s.eta_seconds,
          message: s.message,
        });
        if (!s.running) break;
      }
      // Let the UI show the final state before the hard reload.
      setTimeout(() => window.location.reload(), 1200);
    } catch (e) {
      setRefresh({ running: false, currentStage: `error: ${e.message}` });
    }
  };

  const fyersMeta = FYERS_LABEL[fyers.status] || { label: "fyers · checking…", tone: "muted" };
  const postureTone = POSTURE_TONE[posture] || "muted";
  const progressPct = refresh?.total
    ? Math.min(100, Math.round(((refresh.stageIndex - 1) / refresh.total) * 100))
    : 0;

  return (
    <div className="min-h-screen bg-bg">
      {/* ── Tape ─────────────────────────────────────────────────── */}
      <div className="border-b border-hairline bg-card">
        <div className="mx-auto flex max-w-content items-center gap-5 overflow-x-auto px-4 py-1.5 term-scroll">
          <span className="shrink-0 font-mono text-[9px] font-bold uppercase tracking-overline text-ink3">
            sat10ic os
          </span>
          {tape.loading ? (
            <span className="font-mono text-[10px] text-ink3">loading indices…</span>
          ) : tape.rows.length === 0 ? (
            <span className="font-mono text-[10px] uppercase tracking-overline text-ink3">
              no index data
            </span>
          ) : (
            tape.rows.map((row) => {
              const pct = row.returns?.["1d"];
              const tone = pct == null ? "muted" : Number(pct) >= 0 ? "bull" : "bear";
              return (
                <span key={row.symbol} className="flex shrink-0 items-center gap-1.5 font-mono text-[11px]">
                  <span className="text-ink2">{row.name}</span>
                  <span className="tabular-nums text-ink3">{row.close}</span>
                  <span className={`tabular-nums font-bold ${tone === "bull" ? "text-bull" : tone === "bear" ? "text-bear" : "text-ink3"}`}>
                    {pct == null ? "—" : pct >= 0 ? `▲ +${pct.toFixed(1)}%` : `▼ ${pct.toFixed(1)}%`}
                  </span>
                </span>
              );
            })
          )}
        </div>
      </div>

      {/* ── Tab bar + status cluster ─────────────────────────────── */}
      <div className="border-b border-hairline bg-card">
        <div className="mx-auto flex max-w-content flex-wrap items-center justify-between gap-2 px-4 py-1.5">
          <nav className="flex items-center gap-1">
            {TABS.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => setTab(t.id)}
                className={`border px-2 py-1 font-mono text-[10px] uppercase tracking-overline transition-colors ${
                  tab === t.id
                    ? "border-ink bg-ink text-white"
                    : "border-hairline text-ink2 hover:border-ink hover:text-ink"
                }`}
              >
                [{t.key}] {t.label}
              </button>
            ))}
          </nav>

          <div className="flex flex-wrap items-center gap-3">
            <StatusChip tone={postureTone} label={posture || "posture"} title="Market posture from the latest regime snapshot" />
            <StatusChip tone="muted" label="data · today" dot={false} title="Data freshness (stamp from backend when wired)" />
            <button
              type="button"
              onClick={() => setFyersOpen(true)}
              className="flex items-center gap-1"
              title="Fyers connector status — click to connect"
            >
              <StatusChip tone={fyersMeta.tone} label={fyersMeta.label} />
            </button>

            {/* Density toggle */}
            <button
              type="button"
              onClick={() => setDensity((d) => (d === "beginner" ? "expert" : "beginner"))}
              className="border border-hairline px-2 py-1 font-mono text-[10px] uppercase tracking-overline text-ink2 hover:border-ink hover:text-ink"
              title="Expert mode shows jargon columns / extra layers"
            >
              {density}
            </button>

            {/* Refresh with progress — never a black box */}
            {refresh?.running ? (
              <span className="flex items-center gap-2 border border-info-border bg-info-bg px-2 py-1">
                <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-info-dot" />
                <span className="font-mono text-[10px] uppercase tracking-overline text-info">
                  {plainStage(refresh.currentStage)}
                </span>
                <span className="font-mono text-[10px] text-info">
                  {refresh.stageIndex}/{refresh.total}
                  {refresh.eta != null ? ` · ~${Math.ceil(refresh.eta / 60)}m left` : ""}
                </span>
                <span className="h-1.5 w-16 overflow-hidden bg-info-bg">
                  <span className="block h-full bg-info" style={{ width: `${progressPct}%` }} />
                </span>
              </span>
            ) : (
              <button
                type="button"
                onClick={() => doRefresh(false)}
                className="border border-hairline px-2 py-1 font-mono text-[10px] uppercase tracking-overline text-ink2 hover:border-ink hover:text-ink"
                title="Re-run today's pipeline over current data"
              >
                ⟳ refresh
              </button>
            )}
          </div>
        </div>
      </div>

      {/* ── Panel ────────────────────────────────────────────────── */}
      <main className="mx-auto max-w-content px-4 py-4">
        {tab === "regime" && <RegimePage onPosture={setPosture} density={density} />}
        {tab === "setups" && <SetupsPage posture={posture} density={density} />}
        {tab === "focus" && <SetupsPage posture={posture} density={density} focus />}
        {tab === "watchlist" && <WatchlistPage posture={posture} density={density} />}
        {tab === "journal" && <JournalPage density={density} />}
        {tab === "health" && <HealthPage onRefresh={() => doRefresh(true)} />}
      </main>
    </div>
  );
}