import { AppShell } from "../components/shell/AppShell";
import { CandidateCard } from "../components/widgets/CandidateCard";
import { HonestyFooter } from "../components/widgets/HonestyFooter";
import { RegimeStrip } from "../components/widgets/RegimeStrip";
import { ScrollRail } from "../components/ui/ScrollRail";
import { Sparkline } from "../components/ui/Sparkline";
import { YesterdaysCalls } from "../components/widgets/YesterdaysCalls";
import {
  ALL_CANDIDATES,
  HONESTY_FOOTER,
  REGIME,
  SESSION,
  SETUP_LABEL,
  WATCHLIST_DRIFT,
  YESTERDAYS_CALLS,
  type SetupType,
} from "../data/fixtures";

/*
  TONIGHT (manual V2 §3) — the primary screen, fixed reading order top to
  bottom: header, regime, setups grouped by detector, yesterday's calls,
  watchlist drift, honesty footer. "Report first-read test: a new reader
  finds the day's candidates and the market mood in under a minute."
*/
function groupBySetup(candidates: typeof ALL_CANDIDATES) {
  const groups = new Map<SetupType, typeof ALL_CANDIDATES>();
  for (const c of candidates) {
    const list = groups.get(c.setupType) ?? [];
    list.push(c);
    groups.set(c.setupType, list);
  }
  return groups;
}

export function Tonight() {
  const groups = groupBySetup(ALL_CANDIDATES);

  return (
    <AppShell breadcrumb={["Tonight"]}>
      <div className="flex flex-col gap-4 p-4">
        {/* Header */}
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-card border border-border bg-surface-1 px-4 py-3">
          <div>
            <h1 className="text-h2 font-semibold text-ink-primary">Tonight's report</h1>
            <p className="text-caption text-ink-tertiary">Session {SESSION.date}</p>
          </div>
          <div className="flex items-center gap-4 text-caption text-ink-tertiary">
            <span>
              <span className="font-mono-num font-semibold text-ink-primary">{SESSION.universeScanned}</span> gated
            </span>
            <span>
              <span className="font-mono-num font-semibold text-ink-primary">{SESSION.universeSkipped}</span> skipped
            </span>
            <span>
              <span className="font-mono-num font-semibold text-ink-primary">
                {SESSION.aboveEma21}/{SESSION.aboveEma21Of}
              </span>{" "}
              above EMA21
            </span>
          </div>
        </div>

        {/* A. Regime strip */}
        <RegimeStrip regime={REGIME} />

        {/* B. Tonight's setups, grouped by detector */}
        <div className="flex flex-col gap-4">
          <div className="flex items-baseline justify-between">
            <h2 className="text-h3 font-semibold text-ink-primary">Tonight's setups</h2>
            <span className="text-caption text-ink-muted">{ALL_CANDIDATES.length} candidates across {groups.size} setup types</span>
          </div>
          {[...groups.entries()].map(([setupType, list]) => (
            <div key={setupType}>
              <div className="mb-2 flex items-baseline gap-2">
                <h3 className="text-h4 font-semibold text-ink-primary">{SETUP_LABEL[setupType]}</h3>
                <span className="text-caption text-ink-muted">{list.length} candidate{list.length === 1 ? "" : "s"}</span>
              </div>
              <ScrollRail>
                {list.map((c) => (
                  <CandidateCard key={c.symbol} candidate={c} />
                ))}
              </ScrollRail>
            </div>
          ))}
        </div>

        {/* C. Yesterday's calls */}
        <YesterdaysCalls calls={YESTERDAYS_CALLS} />

        {/* D. Watchlist drift */}
        <div className="rounded-card border border-border bg-surface-1 p-3.5">
          <div className="mb-2.5 flex items-baseline justify-between">
            <h2 className="text-h4 font-semibold text-ink-primary">Watchlist drift</h2>
            <span className="text-caption text-ink-muted">quiet movement of tracked names</span>
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

        {/* E. Honesty footer */}
        <HonestyFooter items={HONESTY_FOOTER} />
      </div>
    </AppShell>
  );
}
