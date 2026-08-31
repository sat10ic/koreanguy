import { AppShell } from "../components/shell/AppShell";
import { CandidateCard } from "../components/widgets/CandidateCard";
import { HonestyFooter } from "../components/widgets/HonestyFooter";
import { RegimeStrip } from "../components/widgets/RegimeStrip";
import { ScrollRail } from "../components/ui/ScrollRail";
import { Sparkline } from "../components/ui/Sparkline";
import { Chip } from "../components/ui/Chip";
import { YesterdaysCalls } from "../components/widgets/YesterdaysCalls";
import { REGIME, SETUP_LABEL, WATCHLIST_DRIFT, YESTERDAYS_CALLS, type Candidate, type SetupType } from "../data/fixtures";
import { REAL_CANDIDATES, REAL_HONESTY_FOOTER, REAL_SESSION, TONIGHT_REPORT } from "../data/tonight";
import { DEFAULT_REPORT, getAvailableSessions, getReport } from "../data/reportRegistry";
import { useState } from "react";

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
  const hf = rd?.honesty_footer;
  const si = { date: rd?.session_date ?? REAL_SESSION.date, asOf: rd?.as_of ?? REAL_SESSION.asOf, uc: hf?.universe_scanned ?? REAL_SESSION.universeScanned, us: hf?.universe_skipped_insufficient_history ?? REAL_SESSION.universeSkipped, ae21: hf?.above_ema21 ?? REAL_SESSION.aboveEma21, ae21o: hf?.above_ema21_of ?? REAL_SESSION.aboveEma21Of, pe50: hf?.pct_above_ema50 ?? REAL_SESSION.pctAboveEma50 };

  return (
    <AppShell breadcrumb={["Tonight"]}>
      <div className="flex flex-col gap-4 p-4">
        {/* Header */}
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-card border border-border bg-surface-1 px-4 py-3">
          <div>
            <h1 className="text-h2 font-semibold text-ink-primary">Tonight's report</h1>
            <p className="text-caption text-ink-tertiary">
              Session {si.date} · as of {new Date(si.asOf).toLocaleString()}
            </p>
          </div>
          {sessions.length > 1 && (<div className="flex items-center gap-1 rounded-chip border border-border-subtle p-0.5">{sessions.map((s) => (<button key={s} onClick={() => setActive(s)} className={"rounded-[4px] px-2.5 py-1 text-caption font-medium transition-colors " + (s === active ? "bg-accent-bg text-accent-strong" : "text-ink-tertiary hover:text-ink-secondary")}>{s}</button>))}</div>)}
              <div className="flex items-center gap-4 text-caption text-ink-tertiary">
            <span>
              <span className="font-mono-num font-semibold text-ink-primary">{si.uc}</span> scanned
            </span>
            <span>
              <span className="font-mono-num font-semibold text-ink-primary">{si.us}</span> skipped
            </span>
            <span>
              <span className="font-mono-num font-semibold text-ink-primary">
                {si.ae21}/{si.ae21o}
              </span>{" "}
              above EMA21
            </span>
            <span>
              <span className="font-mono-num font-semibold text-ink-primary">{REAL_SESSION.pctAboveEma50.toFixed(1)}%</span>{" "}
              above EMA50
            </span>
          </div>
        </div>

        {/* A. Regime strip — real regime_built flag decides the state shown */}
        <RegimeStrip
          regime={REGIME}
          regimeBuilt={TONIGHT_REPORT.honesty_footer.regime_built}
          regimeNote={TONIGHT_REPORT.honesty_footer.regime_note}
        />

{/* A.5 Breadth analytics — live from nightly pipeline */}
        {REAL_SESSION.breadth && (() => {
          const b = REAL_SESSION.breadth;
          return (
            <div className="rounded-card border border-border bg-surface-1 p-3.5">
              <div className="flex items-baseline justify-between mb-2.5">
                <h2 className="text-h4 font-semibold text-ink-primary">Market breadth</h2>
                <span className="text-caption text-ink-muted">real scan {REAL_SESSION.date}</span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div>
                  <span className="text-caption text-ink-muted block">Near 52w high</span>
                  <span className="font-mono-num text-h4 text-green-500">{b.near_highs_pct ?? "---"}%</span>
                  <span className="text-caption text-ink-muted ml-1">({b.near_highs_5pct})</span>
                </div>
                <div>
                  <span className="text-caption text-ink-muted block">Near 52w low</span>
                  <span className="font-mono-num text-h4 text-red-500">{b.near_lows_pct ?? "---"}%</span>
                  <span className="text-caption text-ink-muted ml-1">({b.near_lows_5pct})</span>
                </div>
              </div>
            </div>
          );
        })()}
        {/* B. Tonight's setups, grouped by detector — real scan candidates */}
        <div className="flex flex-col gap-4">
          <div className="flex items-baseline justify-between">
            <h2 className="text-h3 font-semibold text-ink-primary">Tonight's setups</h2>
            <span className="text-caption text-ink-muted">
              {REAL_CANDIDATES.length} candidates across {groups.size} setup types — real scan, {si.date}
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

        {/* C. Yesterday's calls — illustrative: no outcome-join backend yet */}
        <div>
          <div className="mb-1.5 flex items-center gap-1.5">
            <span className="text-[10px] uppercase tracking-wide text-ink-muted">
              Illustrative — outcome-join backend not built (integration plan row 4)
            </span>
          </div>
          <div className="rounded-card border border-dashed border-border-subtle p-0.5">
            <YesterdaysCalls calls={YESTERDAYS_CALLS} />
          </div>
        </div>

        {/* D. Watchlist drift — illustrative: no watchlist backend yet */}
        <div className="rounded-card border border-dashed border-border-subtle bg-surface-1 p-3.5">
          <div className="mb-2.5 flex items-baseline justify-between">
            <h2 className="text-h4 font-semibold text-ink-primary">Watchlist drift</h2>
            <span className="text-caption text-ink-muted">illustrative — quiet movement of tracked names</span>
          </div>
          <div className="flex flex-col gap-2">
            {WATCHLIST_DRIFT.map((w) => (
              <div key={w.symbol} className="flex items-center justify-between rounded-chip px-1.5 py-1.5">
                <div className="flex items-center gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-accent" />
                  <span className="text-caption font-semibold text-ink-primary">{w.symbol}</span>
                  <span className="text-caption text-ink-tertiary">{w.note}</span>
                </div>
                <Sparkline values={w.spark} width={60} height={18} color="var(--text-secondary)" />
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
