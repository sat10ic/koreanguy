import { AppShell } from "../components/shell/AppShell";
import { CandidateCard } from "../components/widgets/CandidateCard";
import { HonestyFooter } from "../components/widgets/HonestyFooter";
import { RegimeStrip } from "../components/widgets/RegimeStrip";
import { ScrollRail } from "../components/ui/ScrollRail";
import { Chip } from "../components/ui/Chip";
import { YesterdaysCalls } from "../components/widgets/YesterdaysCalls";
import { SETUP_LABEL, type Candidate, type SetupType } from "../data/fixtures";
import { REAL_CANDIDATES, REAL_HONESTY_FOOTER, REAL_SESSION, TONIGHT_REPORT } from "../data/tonight";
import { REAL_CALLS } from "../data/outcomes";
import { DEFAULT_REPORT, getAvailableSessions, getReport } from "../data/reportRegistry";
import { useState } from "react";
import { RefreshCw, AlertTriangle } from "lucide-react";
import { VintageBadge } from "../components/ui/VintageBadge";

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
  const [active, setActive] = useState(DEFAULT_REPORT.sessionDate);
  const sessions = getAvailableSessions();
  const rd = getReport(active)?.json as any;
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
  const sessionDate = REAL_SESSION.date;
  const isLatest = sessionDate >= today;
  const daysStale = sessionDate < today
    ? Math.floor((Date.now() - new Date(sessionDate).getTime()) / 86400000)
    : 0;
const si = { date: rd?.session_date ?? REAL_SESSION.date, asOf: rd?.as_of ?? REAL_SESSION.asOf };

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

  // Watchlist Drift: top 10 candidates by stock quality, with trigger proximity notes.
  const watchlistItems = TONIGHT_REPORT.candidates
    .map((c: any) => ({ c, score: c.stock_quality?.score ?? 0 }))
    .sort((a: any, b: any) => b.score - a.score)
    .slice(0, 10)
    .map(({ c }: any) => {
      const close = c.close;
      const trigger = c.trigger;
      const invalidation = c.invalidation;
      let note = "";
      if (trigger && close < trigger) {
        const pct = ((trigger - close) / close * 100).toFixed(1);
        note = pct + "% below trigger";
      } else if (trigger && close >= trigger) {
        note = "at or above trigger";
      } else {
        note = "score: " + (c.stock_quality?.score?.toFixed(0) ?? "?");
      }
      if (invalidation && close > invalidation) {
        const risk = ((close - invalidation) / close * 100).toFixed(1);
        note += " · " + risk + "% above invalidation";
      }
      return { symbol: c.symbol, note, scoreLabel: "Score: " + (c.stock_quality?.score?.toFixed(1) ?? "?") };
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
          {sessions.length > 1 && (
            <div className="mt-2 flex items-center gap-1 rounded-chip border border-border-subtle p-0.5">
              {sessions.map((s) => (
                <button key={s} onClick={() => setActive(s)}
                  className={"rounded-[4px] px-2.5 py-1 text-caption font-medium transition-colors " + (s === active ? "bg-accent-bg text-accent-strong" : "text-ink-tertiary hover:text-ink-secondary")}>
                  {s}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* A. Regime strip */}
        <RegimeStrip regimeBuilt={hf.regime_built} regimeNote={hf.regime_note} pctAboveEma50={hf.pct_above_ema50} nearHighsPct={hf.breadth?.near_highs_pct} nearLowsPct={hf.breadth?.near_lows_pct} />

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
            <div className="border-t border-border-subtle pt-2.5">
              <div className="text-caption text-ink-muted mb-2">
                Derived analytics -- reverse engineered from Market Breadth V2.0 (manas_os)
              </div>
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
              <div className="mt-1.5 text-caption text-ink-tertiary">
                BO/BD ratio: {breadthAnalytics.bo_bd_ratio?.toFixed(2) ?? "not available (needs breakout detector pass in loop)"}
              </div>
            </div>
          )}
          {(hf.stale_excluded ?? 0) > 0 && (
            <div className="mt-2 text-caption text-ink-muted">
              {hf.stale_excluded ?? 0} symbols excluded by liveness gate (no trade on session date)
            </div>
          )}
        </div>
        {/* B. Tonight's setups, grouped by detector — real scan candidates */}
        <div className="flex flex-col gap-4">
          <div className="flex items-baseline justify-between">
            <h2 className="text-h3 font-semibold text-ink-primary">Tonight's setups</h2>
            <span className="text-caption text-ink-muted">
              {REAL_CANDIDATES.length} candidates across {groups.size} setup types — real scan, {si.date}
              <VintageBadge label="Candidates" sessionDate={si.date} appDate={REAL_SESSION.date} />
            </span>
          </div>
          {[...groups.entries()].map(([setupType, list]) => {
            const t = groupTrust.get(setupType);
            return (
            <div key={setupType}>
              <div className="mb-2 flex items-baseline gap-2">
                <h3 className="text-h4 font-semibold text-ink-primary">{SETUP_LABEL[setupType]}</h3>
                <span className="text-caption text-ink-muted">{list.length} candidate{list.length === 1 ? "" : "s"}</span>
                {t && !t.rankable && (
                  <Chip tone="danger">{t.status === "REVIEW_REQUIRED" ? "Review" : "Blocked"}</Chip>
                )}
              </div>
              <ScrollRail>
                {list.map((c) => (
                  <CandidateCard key={`${c.symbol}-${c.setupType}-${c.dataSource}`} candidate={c} />
                ))}
              </ScrollRail>
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

        {/* D. Watchlist drift — top candidates by stock quality */}
        <div className="rounded-card border border-border bg-surface-1 p-3.5">
          <div className="mb-2.5 flex items-baseline justify-between">
            <h2 className="text-h4 font-semibold text-ink-primary">Watchlist drift</h2>
            <span className="text-caption text-ink-muted">top 10 by stock quality</span>
          </div>
          <div className="flex flex-col gap-2">
            {watchlistItems.map((w) => (
              <div key={w.symbol} className="flex items-center justify-between rounded-chip px-1.5 py-1.5">
                <div className="flex items-center gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-accent" />
                  <span className="text-caption font-semibold text-ink-primary">{w.symbol}</span>
                  <span className="text-caption text-ink-tertiary">{w.note}</span>
                </div>
                <span className="font-mono-num text-caption text-ink-muted">{w.scoreLabel}</span>
              </div>
            ))}
          </div>
        </div>

        {/* E. Honesty footer — real facts from honesty_footer */}
        <HonestyFooter items={REAL_HONESTY_FOOTER} />
      </div>
    </AppShell>
  );
}
