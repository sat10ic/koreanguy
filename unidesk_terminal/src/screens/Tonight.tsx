import { AppShell } from "../components/shell/AppShell";
import { CandidateCard } from "../components/widgets/CandidateCard";
import { HonestyFooter } from "../components/widgets/HonestyFooter";
import { RegimeStrip } from "../components/widgets/RegimeStrip";
import { Chip } from "../components/ui/Chip";
import { YesterdaysCalls } from "../components/widgets/YesterdaysCalls";
import { SETUP_LABEL, type Candidate, type SetupType } from "../data/fixtures";
import { REAL_CANDIDATES, REAL_HONESTY_FOOTER, TONIGHT_REPORT } from "../data/tonight";
import { REAL_CALLS } from "../data/outcomes";
import { getReport } from "../data/reportRegistry";
import { RefreshCw, AlertTriangle } from "lucide-react";
import { VintageBadge } from "../components/ui/VintageBadge";
import { useMode } from "../lib/ModeContext";
import { deriveState, STATE_META } from "../lib/status";
import React from "react";

/*
  TONIGHT (manual V2 §3) — the primary screen, fixed reading order top to
  bottom: header, regime, breadth, setups grouped by detector, yesterday's
  calls, honesty footer. "Report first-read test: a new reader finds the
  day's candidates and the market mood in under a minute."

  2026-08-31: All fabricated candidates removed per owner directive. Regime
  and breadth analytics are now live from the real nightly pipeline
  (CA=4, gated universe). Breadth counters and analytics rendered from
  honesty_footer.breadth. Yesterday's Calls and Watchlist Drift remain
  illustrative (no outcome-join or watchlist backend yet — integration plan
  rows 3-4).
*/
function groupBySetup(candidates: Candidate[]) {
  const groups = new Map<SetupType, Candidate[]>();
  for (const c of candidates) {
    const list = groups.get(c.setupType) ?? [];
    list.push(c);
    groups.set(c.setupType, list);
  }
  return groups;
}

export function Tonight() {
  const { activeReport, setActiveReport, availableSessions } = useMode();
  const rd = getReport(activeReport)?.json as any;
  const candidates: Candidate[] = rd?.candidates?.map((c: any) => ({
    symbol: c.symbol, close: c.close, setupType: c.detector as SetupType,
    lifecycle: "not_classified" as const, dataSource: "real_scan_raw" as const,
    adrPct: c.adr_pct, rsRank: c.rs_rank, rvol: c.rvol, contraction: c.contraction,
    deliveryRatio: c.delivery_ratio, trend: c.trend, sessions: c.sessions, adjusted: c.adjusted,
    why: (c.trend??"").replace(/_/g," ") + " · " + (c.rvol??0).toFixed(2) + "x",
    rawStats: [
      {label:"RS rank",value:(c.rs_rank??0).toFixed(1)},
      {label:"RVOL",value:(c.rvol??0).toFixed(2)+"x"},
    ],
  })) ?? REAL_CANDIDATES;
  const groups = groupBySetup(candidates);
  // Per-detector-group trust from the report's setups array: shows a
  // "Blocked" / "Review" badge next to non-rankable detector groups so the
  // reader knows these candidates are visible but not actionable. Absent
  // when the JSON predates the trust wiring.
  const groupTrust = new Map(
    TONIGHT_REPORT.setups.map((s) => [s.detector, s.trust])
  );
  const hf = TONIGHT_REPORT.honesty_footer;
  const breadthAnalytics = (hf.breadth as any)?.analytics ?? null;
  const today = new Date().toISOString().slice(0, 10);
  const sessionDate = TONIGHT_REPORT.session_date;
  const isLatest = sessionDate >= today;
  const daysStale = sessionDate < today
    ? Math.floor((Date.now() - new Date(sessionDate).getTime()) / 86400000)
    : 0;

  // Yesterday's Calls: real outcome-labelled calls from the event store.
  // Find the most recent session with resolved outcomes (mfe > 0 or stopped out).
  // This reads from outcomes_2026-08-28.json which has 11,591 real calls.
  const allDates = [...new Set(REAL_CALLS.map((c) => c.date))].sort().reverse();
  let resolvedDate = allDates[0];
  for (const dt of allDates) {
    const resolved = REAL_CALLS.filter((c) => c.date === dt && (c.outcome === "hit_target" || c.outcome === "stopped_out"));
    if (resolved.length > 0) { resolvedDate = dt; break; }
  }
  const yesterdayCalls = REAL_CALLS.filter((c) => c.date === resolvedDate).slice(0, 50);
  const yesterdayWins = yesterdayCalls.filter((c) => c.outcome === "hit_target").length;
  const yesterdayLosses = yesterdayCalls.filter((c) => c.outcome === "stopped_out").length;
  const yesterdayUnresolved = yesterdayCalls.filter((c) => c.outcome === "unresolved").length;

  // Watchlist: top 10 by stock quality, with trigger proximity ladder data
  const watchlistItems = TONIGHT_REPORT.candidates
    .map((c: any) => ({ c, score: c.stock_quality?.score ?? 0 }))
    .sort((a: any, b: any) => b.score - a.score)
    .slice(0, 10)
    .map(({ c }: any) => {
      const close = c.close;
      const trigger = c.trigger;
      let pctFromTrigger: number | null = null;
      if (trigger && close) { pctFromTrigger = (trigger - close) / close * 100; }
      const state = deriveState({ close, trigger, stockStrength: c.stock_quality?.score, rvol: c.rvol, rsRank: c.rs_rank });
      const sm = STATE_META[state];
      return { symbol: c.symbol, pctFromTrigger, state: sm.label, stateTone: sm.tone };
    });

  return (
    <AppShell breadcrumb={["Tonight"]}>
      <div className="flex flex-col gap-4 p-4">
        {/* HEADER — Data freshness + pipeline-run prompt */}
        <div className="rounded-card border border-border bg-surface-1 p-3.5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h1 className="text-h2 font-semibold text-ink-primary">Tonight's report</h1>
              <p className="text-caption text-ink-tertiary">
                Session {sessionDate} &middot; scan of {hf.universe_scanned.toLocaleString()} symbols
              </p>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <VintageBadge label="Data" sessionDate={sessionDate} appDate={today} stale={!isLatest} />
              <span className="text-caption text-ink-muted px-2 py-1 rounded-chip border border-border-subtle cursor-default"
                title="Run: start /B .venv-orderflow\Scripts\python.exe unidesk\run_nightly_background.py">
                <RefreshCw size={12} className="inline mr-1" />
                Run pipeline
              </span>
            </div>
          </div>
          {daysStale > 0 && (
            <div className="mt-2 flex items-center gap-1.5 text-caption text-danger">
              <AlertTriangle size={12} />
              Data is {daysStale} day{daysStale === 1 ? "" : "s"} stale. Run after market close (~19:30 IST) to refresh.
            </div>
          )}
          {availableSessions.length > 1 && (
            <div className="mt-2 flex items-center gap-1 rounded-chip border border-border-subtle p-0.5">
              {availableSessions.map((s) => (
                <button key={s} onClick={() => setActiveReport(s)}
                  className={"rounded-[4px] px-2.5 py-1 text-caption font-medium transition-colors " + (s === activeReport ? "bg-accent-bg text-accent-strong" : "text-ink-tertiary hover:text-ink-secondary")}>
                  {s}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* A. Regime strip */}
        <RegimeStrip regimeBuilt={hf.regime_built} regimeNote={hf.regime_note} pctAboveEma50={hf.pct_above_ema50} nearHighsPct={hf.breadth?.near_highs_pct} nearLowsPct={hf.breadth?.near_lows_pct} />

        {/* H1-02: Regime position strip */}
        <div className="rounded-card border border-border bg-surface-1 p-3.5">
          <div className="flex justify-between text-caption text-ink-muted mb-1 text-xs">
            <span>Risk-Off</span><span>Weak</span><span>CHOP</span><span>Healthy</span><span>Strong</span>
          </div>
          <div className="relative h-2 rounded-full bg-surface-2">
            <div className="absolute top-0 h-2 w-2 rounded-full bg-accent transition-all duration-300"
              style={{ left: "calc(" + (hf.pct_above_ema50 != null ? Math.min(100, Math.max(0, hf.pct_above_ema50)) : 50) + "% - 4px)" }} />
          </div>
          <div className="text-right text-caption text-ink-muted mt-1">{(hf.pct_above_ema50 ?? 50).toFixed(0)}% above EMA50</div>
        </div>

        {/* H1-04: Market participation ruled table */}
        <div className="rounded-card border border-border bg-surface-1 p-3.5">
          <div className="flex items-baseline justify-between mb-2.5">
            <h2 className="text-h4 font-semibold text-ink-primary">Market participation</h2>
            <span className="text-caption text-ink-muted text-xs">TODAY 1D 5D</span>
          </div>
          <div className="space-y-2 text-caption">
            {[{ l: "Above EMA21", v: (hf.above_ema21 / (hf.above_ema21_of || 1) * 100), pct: hf.above_ema21 + "/" + hf.above_ema21_of, c: "bg-accent" },
              { l: "Above EMA50", v: hf.pct_above_ema50 ?? 0, pct: (hf.pct_above_ema50?.toFixed(1) ?? "---") + "%", c: "bg-accent" },
              { l: "Near 52W High", v: hf.breadth?.near_highs_pct ?? 0, pct: (hf.breadth?.near_highs_pct?.toFixed(1) ?? "---") + "%", c: "bg-green-500/60" },
              { l: "Near 52W Low", v: hf.breadth?.near_lows_pct ?? 0, pct: (hf.breadth?.near_lows_pct?.toFixed(1) ?? "---") + "%", c: "bg-red-500/60" }
            ].map((r) => {
              const bw = r.v != null ? Math.min(100, Math.max(2, r.v)) : 0;
              return (
                <div key={r.l} className="flex items-center gap-3">
                  <span className="w-24 shrink-0 text-ink-muted">{r.l}</span>
                  <div className="flex-1 h-3 rounded-sm bg-surface-2 overflow-hidden">
                    <div className={"h-full rounded-sm " + r.c} style={{ width: bw + "%" }} />
                  </div>
                  <span className="w-16 text-right font-mono-num text-ink-primary">{r.pct}</span>
                  <span className="w-8 text-right text-ink-tertiary">-</span>
                  <span className="w-8 text-right text-ink-tertiary">-</span>
                </div>
              );
            })}
          </div>
          <div className="mt-2 text-caption text-ink-tertiary text-right">1D/5D: not available (B-07)</div>
        </div>

{/* A.5 Breadth analytics — live from pipeline, with reverse-engineered analytics from manas_os */}
        <div className="rounded-card border border-border bg-surface-1 p-3.5">
          <div className="flex items-baseline justify-between mb-2.5">
            <h2 className="text-h4 font-semibold text-ink-primary">Market breadth</h2>
            <div className="flex items-center gap-2">
              <span className="text-caption text-ink-muted">live from pipeline</span>
              <VintageBadge label="Breadth" sessionDate={sessionDate} appDate={sessionDate} />
            </div>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-3">
            <div>
              <span className="text-caption text-ink-muted block">Near 52w high</span>
              <span className="font-mono-num text-h4 text-green-500">{hf.breadth?.near_highs_pct ?? "---"}%</span>
              <span className="text-caption text-ink-muted ml-1">({hf.breadth?.near_highs_5pct})</span>
            </div>
            <div>
              <span className="text-caption text-ink-muted block">Near 52w low</span>
              <span className="font-mono-num text-h4 text-red-500">{hf.breadth?.near_lows_pct ?? "---"}%</span>
              <span className="text-caption text-ink-muted ml-1">({hf.breadth?.near_lows_5pct})</span>
            </div>
            <div>
              <span className="text-caption text-ink-muted block">Above EMA50</span>
              <span className="font-mono-num text-h4">{hf.pct_above_ema50?.toFixed(1) ?? "---"}%</span>
            </div>
            <div>
              <span className="text-caption text-ink-muted block">Above EMA21</span>
              <span className="font-mono-num text-h4">{hf.above_ema21} / {hf.above_ema21_of}</span>
            </div>
          </div>
          {breadthAnalytics && (
            <>
            <div className="border-t border-border-subtle pt-2.5">
              <div className="text-caption text-ink-muted mb-2">Derived analytics</div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                <div className="rounded-chip bg-surface-2 px-2 py-1.5">
                  <span className="text-caption text-ink-muted block">Net NH-NL</span>
                  <span className={"font-mono-num text-body font-semibold " + ((breadthAnalytics.net_nh_nl ?? 0) > 0 ? "text-green-500" : "text-red-500")}>
                    {breadthAnalytics.net_nh_nl?.toFixed(2) ?? "---"}
                  </span>
                </div>
                <div className="rounded-chip bg-surface-2 px-2 py-1.5">
                  <span className="text-caption text-ink-muted block">Volatility ratio</span>
                  <span className="font-mono-num text-body font-semibold text-ink-primary">{breadthAnalytics.volatility_ratio?.toFixed(2) ?? "---"}</span>
                </div>
                <div className="rounded-chip bg-surface-2 px-2 py-1.5">
                  <span className="text-caption text-ink-muted block">Volume ratio</span>
                  <span className="font-mono-num text-body font-semibold text-ink-primary">{breadthAnalytics.volume_ratio?.toFixed(2) ?? "---"}</span>
                </div>
                <div className="rounded-chip bg-surface-2 px-2 py-1.5">
                  <span className="text-caption text-ink-muted block">Up/Down close</span>
                  <span className="font-mono-num text-body font-semibold text-ink-primary">{breadthAnalytics.up_down_close_pct?.toFixed(1) ?? "---"}%</span>
                </div>
              </div>

              {/* H1-06: NH/NL balance bar */}
              <div className="mt-1.5 text-caption text-ink-tertiary">
                BO/BD ratio: {breadthAnalytics.bo_bd_ratio?.toFixed(2) ?? "not available (needs breakout detector pass in loop)"}
              </div>
            </div>
            </>          )}
          {(hf.stale_excluded ?? 0) > 0 && (
            <div className="mt-2 text-caption text-ink-muted">
              {hf.stale_excluded ?? 0} symbols excluded by liveness gate (no trade on session date)
            </div>
          )}
        </div>

        {/* H1-06: NH/NL balance bar */}
        {breadthAnalytics?.net_nh_nl != null && (
          <div className="rounded-card border border-border bg-surface-1 p-3.5">
            <div className="text-caption text-ink-muted mb-1">NH/NL balance</div>
            <div className="relative h-2 rounded-full bg-surface-2">
              <div className="absolute top-0 h-2 w-2 rounded-full bg-accent transition-all duration-300"
                style={{ left: "calc(" + Math.min(100, Math.max(0, (breadthAnalytics.net_nh_nl + 5) / 10 * 100)) + "% - 4px)" }} />
            </div>
            <div className="flex justify-between text-caption text-ink-muted mt-1">
              <span>Low dominance</span>
              <span className={"font-mono-num " + (breadthAnalytics.net_nh_nl > 0 ? "text-green-500" : "text-red-500")}>
                {breadthAnalytics.net_nh_nl > 0 ? "+" : ""}{breadthAnalytics.net_nh_nl.toFixed(3)}
              </span>
              <span>High dominance</span>
            </div>
          </div>
        )}

        {/* H1-07: Tonight's Playbook */}
        {(() => {
          const rl2 = hf.regime_note?.split(/[ (]/)[0] ?? "CHOP";
          const pbr = ({ CHOP: { e: "Neutral", f: "Mean reversion, inside bar", a: "Trend-following breakouts", s: "High" },
            BULL: { e: "Long", f: "Breakouts, momentum burst", a: "Short strategies", s: "Moderate" },
            BEAR: { e: "Defensive", f: "Reversal, quality names", a: "High-beta momentum", s: "High" } } as any)[rl2] ?? { e: "Neutral", f: "Setup quality", a: "N/A", s: "Standard" };
          return (
            <div className="rounded-card border border-border bg-surface-1 p-3.5">
              <div className="flex items-baseline justify-between mb-2.5">
                <h2 className="text-h4 font-semibold text-ink-primary">Tonight's playbook</h2>
                <span className="text-caption text-ink-muted text-xs">heuristic, not validated</span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-caption">
                <div className="rounded-chip bg-surface-2 px-2 py-1.5">
                  <span className="text-ink-muted block">Exposure</span>
                  <span className="font-semibold text-ink-primary">{pbr.e}</span>
                </div>
                <div className="rounded-chip bg-surface-2 px-2 py-1.5">
                  <span className="text-ink-muted block">Selectivity</span>
                  <span className="font-semibold text-ink-primary">{pbr.s}</span>
                </div>
                <div className="rounded-chip bg-surface-2 px-2 py-1.5">
                  <span className="text-ink-muted block">Favour</span>
                  <span className="text-ink-primary">{pbr.f}</span>
                </div>
                <div className="rounded-chip bg-surface-2 px-2 py-1.5">
                  <span className="text-ink-muted block">Avoid</span>
                  <span className="text-ink-primary">{pbr.a}</span>
                </div>
              </div>
              <div className="mt-1.5 text-caption text-ink-tertiary">Regime history: not available (B-07)</div>
            </div>
          );
        })()}

        {/* B. Tonight's setups — compact rows per H2-02/H2-09/H2-10 */}
        <div className="flex flex-col gap-4">
          {[...groups.entries()].map(([setupType, list]) => {
            const t = groupTrust.get(setupType);
            // H2-09: Section header with per-state counts
            const stateCounts: Record<string, number> = {};
            for (const c of list) {
              const st = deriveState(c);
              stateCounts[st] = (stateCounts[st] ?? 0) + 1;
            }
            const stateSummary = Object.entries(stateCounts).map(([st, n]) => n + " " + st.toLowerCase()).join(" · ");
            // H2-10: Collapse if >10
            const [collapsed, setCollapsed] = React.useState(list.length > 10);
            return (
              <div key={setupType}>
                <div className="flex items-baseline gap-2 mb-1.5 cursor-pointer select-none"
                  onClick={() => setCollapsed(!collapsed)}>
                  <h3 className="text-h4 font-semibold text-ink-primary">{SETUP_LABEL[setupType]}</h3>
                  <span className="text-caption text-ink-muted">{list.length} found</span>
                  <span className="text-caption text-ink-tertiary">{stateSummary}</span>
                  {t && !t.rankable && <Chip tone="danger">{t.status === "REVIEW_REQUIRED" ? "Review" : "Blocked"}</Chip>}
                  <span className="ml-auto text-caption text-ink-tertiary">{collapsed ? "▸" : "▾"}</span>
                </div>
                {!collapsed && (
                  <div className="rounded-card border border-border bg-surface-1 overflow-hidden">
                    {list.map((c, i) => <CandidateCard key={c.symbol + "-" + c.setupType} candidate={c} rank={i + 1} />)}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* C. Yesterday's calls — real outcomes from event store */}
        <div>
          <div className="mb-1.5 flex items-center gap-1.5">
            <span className="text-[10px] uppercase tracking-wide text-accent-strong">
              Real — {yesterdayCalls.length} prior outcomes ({yesterdayWins} hit target, {yesterdayLosses} stopped out, {yesterdayUnresolved} unresolved)
            </span>
          </div>
          <div className="rounded-card border border-border bg-surface-1 p-3.5">
            <YesterdaysCalls calls={yesterdayCalls} />
          </div>
        </div>

        {/* D. Trigger Proximity — H4-02 proximity ladder format */}
        {watchlistItems.length > 0 && (
          <div className="rounded-card border border-border bg-surface-1 p-3.5">
            <div className="mb-2.5 flex items-baseline justify-between">
              <h2 className="text-h4 font-semibold text-ink-primary">Trigger proximity</h2>
              <span className="text-caption text-ink-muted">top 10 by quality</span>
            </div>
            <div className="flex flex-col gap-2">
              {watchlistItems.map((w: any) => (
                <div key={w.symbol} className="flex items-center gap-2 text-caption">
                  <span className="w-20 font-semibold text-ink-primary shrink-0">{w.symbol}</span>
                  {/* Ladder bar */}
                  <div className="flex-1 relative h-4 rounded-sm bg-surface-2 overflow-hidden">
                    <div className="absolute inset-y-0 w-px bg-accent left-1/2" title="trigger" />
                    {w.pctFromTrigger != null && (
                      <div className="absolute top-0.5 h-3 w-3 rounded-full transition-all duration-300"
                        style={{
                          left: Math.min(95, Math.max(5, 50 + ((w.pctFromTrigger ?? 0) * 5))) + "%",
                          backgroundColor: (w.pctFromTrigger ?? 0) < -5 ? "var(--positive)" :
                                          (w.pctFromTrigger ?? 0) < 0 ? "var(--score-mid)" :
                                          (w.pctFromTrigger ?? 0) < 3 ? "var(--warning)" : "var(--danger)"
                        }} />
                    )}
                  </div>
                  <span className="w-14 text-right font-mono-num text-ink-muted shrink-0">
                    {w.pctFromTrigger != null ? (w.pctFromTrigger > 0 ? "+" : "") + w.pctFromTrigger.toFixed(1) + "%" : "—"}
                  </span>
                  <Chip tone={w.stateTone || "neutral"}>{w.state}</Chip>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* E. Honesty footer — real facts from honesty_footer */}
        <HonestyFooter items={REAL_HONESTY_FOOTER} />
      </div>
    </AppShell>
  );
}
