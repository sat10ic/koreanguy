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

/*
  TONIGHT (manual V2 §3) — the primary screen, fixed reading order top to
  bottom: header, regime, setups grouped by detector, yesterday's calls,
  watchlist drift, honesty footer. "Report first-read test: a new reader
  finds the day's candidates and the market mood in under a minute."

  2026-08-30: wired to the real nightly scan (data/market/reports/
  tonight_2026-08-28.json, via src/data/tonight.ts) — header stats, the
  setups grouped by detector, and the honesty footer are now real. Regime
  and Yesterday's Calls/Watchlist Drift stay on the illustrative fixture:
  the real honesty_footer says regime_built: false, and there is no
  outcome-join or watchlist backend yet (see UI_BACKEND_INTEGRATION_PLAN.md
  cadence rows 3-4). Both are visibly tagged as illustrative below.
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
  const groups = groupBySetup(REAL_CANDIDATES);
  // Per-detector-group trust from the report's setups array: shows a
  // "Blocked" / "Review" badge next to non-rankable detector groups so the
  // reader knows these candidates are visible but not actionable. Absent
  // when the JSON predates the trust wiring.
  const groupTrust = new Map(
    TONIGHT_REPORT.setups.map((s) => [s.detector, s.trust])
  );

  return (
    <AppShell breadcrumb={["Tonight"]}>
      <div className="flex flex-col gap-4 p-4">
        {/* Header */}
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-card border border-border bg-surface-1 px-4 py-3">
          <div>
            <h1 className="text-h2 font-semibold text-ink-primary">Tonight's report</h1>
            <p className="text-caption text-ink-tertiary">
              Session {REAL_SESSION.date} · as of {new Date(REAL_SESSION.asOf).toLocaleString()}
            </p>
          </div>
          <div className="flex items-center gap-4 text-caption text-ink-tertiary">
            <span>
              <span className="font-mono-num font-semibold text-ink-primary">{REAL_SESSION.universeScanned}</span> scanned
            </span>
            <span>
              <span className="font-mono-num font-semibold text-ink-primary">{REAL_SESSION.universeSkipped}</span> skipped
            </span>
            <span>
              <span className="font-mono-num font-semibold text-ink-primary">
                {REAL_SESSION.aboveEma21}/{REAL_SESSION.aboveEma21Of}
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

        {/* B. Tonight's setups, grouped by detector — real scan candidates */}
        <div className="flex flex-col gap-4">
          <div className="flex items-baseline justify-between">
            <h2 className="text-h3 font-semibold text-ink-primary">Tonight's setups</h2>
            <span className="text-caption text-ink-muted">
              {REAL_CANDIDATES.length} candidates across {groups.size} setup types — real scan, {REAL_SESSION.date}
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
