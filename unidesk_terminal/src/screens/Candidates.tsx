import { useMemo, useState } from "react";
import { AppShell } from "../components/shell/AppShell";
import { FilterChip } from "../components/ui/FilterChip";
import { CandidateCard } from "../components/widgets/CandidateCard";
import { CandidateScatter } from "../components/widgets/CandidateScatter";
import { ALL_CANDIDATES, SETUP_LABEL, type Candidate, type Lifecycle, type SetupType } from "../data/fixtures";
import { REAL_CANDIDATES, REAL_SESSION } from "../data/tonight";
import { LIFECYCLE_META } from "../lib/status";

// 2026-08-30: real scan candidates (real_scan_raw, no quality scores) lead
// the list; the fixture rows (real_scan + illustrative, both tagged) stay
// appended so the screen still demonstrates the fully-scored card layout.
// Never blended without a badge — CandidateCard tags every dataSource
// differently.
const COMBINED_CANDIDATES: Candidate[] = [...REAL_CANDIDATES, ...ALL_CANDIDATES];

type SortKey = "best_score" | "coverage" | "recency";

const SORTS: { key: SortKey; label: string }[] = [
  { key: "best_score", label: "Best score" },
  { key: "coverage", label: "Coverage" },
  { key: "recency", label: "Most recent" },
];

const SETUP_TYPES = Object.keys(SETUP_LABEL) as SetupType[];
const LIFECYCLES = Object.keys(LIFECYCLE_META) as Lifecycle[];

function sortCandidates(list: Candidate[], key: SortKey) {
  const sorted = [...list];
  switch (key) {
    case "coverage":
      // Coverage stands in for "how many named-number/raw-stat facts had
      // data" — namedNumbers for scored fixture rows, rawStats for real
      // scan rows (approximation, until a backend coverage field exists).
      return sorted.sort(
        (a, b) => (b.namedNumbers?.length ?? b.rawStats?.length ?? 0) - (a.namedNumbers?.length ?? a.rawStats?.length ?? 0),
      );
    case "recency":
      // real_scan_raw (today's real scan) first, then the old real_scan
      // fixture trio, then illustrative — real and most-recent wins.
      return sorted.sort((a, b) => recencyRank(a) - recencyRank(b));
    case "best_score":
    default:
      // Undefined scores (real scan rows) sort after scored rows — no score
      // is not the same as a low score, so it isn't coerced to 0.
      return sorted.sort((a, b) => scoreSum(b) - scoreSum(a));
  }
}

function recencyRank(c: Candidate): number {
  if (c.dataSource === "real_scan_raw") return 0;
  if (c.dataSource === "real_scan") return 1;
  return 2;
}

function scoreSum(c: Candidate): number {
  if (c.stockStrength === undefined || c.setupQuality === undefined || c.entryTiming === undefined) {
    return -Infinity;
  }
  return c.stockStrength + c.setupQuality + c.entryTiming;
}

export function Candidates() {
  const [sort, setSort] = useState<SortKey>("best_score");
  const [activeSetupTypes, setActiveSetupTypes] = useState<Set<SetupType>>(new Set());
  const [activeLifecycles, setActiveLifecycles] = useState<Set<Lifecycle>>(new Set());

  const filtered = useMemo(() => {
    let base: Candidate[] = COMBINED_CANDIDATES;
    if (activeSetupTypes.size > 0) base = base.filter((c) => activeSetupTypes.has(c.setupType));
    if (activeLifecycles.size > 0) base = base.filter((c) => activeLifecycles.has(c.lifecycle));
    return sortCandidates(base, sort);
  }, [sort, activeSetupTypes, activeLifecycles]);

  // The scatter needs Stock Strength / Setup Quality / Entry Timing — only
  // the fixture rows have those. Real scan rows (no scoring model yet) are
  // excluded from the plot rather than forced onto axes with an invented 0,
  // and the count is disclosed under the chart.
  const scatterEligible = useMemo(
    () => filtered.filter((c) => c.stockStrength !== undefined && c.setupQuality !== undefined && c.entryTiming !== undefined),
    [filtered],
  );
  const scatterExcluded = filtered.length - scatterEligible.length;

  function toggle<T>(set: Set<T>, setSet: (s: Set<T>) => void, value: T) {
    const next = new Set(set);
    if (next.has(value)) next.delete(value);
    else next.add(value);
    setSet(next);
  }

  return (
    <AppShell breadcrumb={["Candidates"]}>
      <div className="flex flex-col gap-4 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-1.5">
            {SETUP_TYPES.map((t) => (
              <FilterChip
                key={t}
                label={SETUP_LABEL[t]}
                active={activeSetupTypes.has(t)}
                onClick={() => toggle(activeSetupTypes, setActiveSetupTypes, t)}
              />
            ))}
            <span className="mx-1 h-4 w-px bg-border-subtle" aria-hidden />
            {LIFECYCLES.map((l) => (
              <FilterChip
                key={l}
                label={LIFECYCLE_META[l].label}
                active={activeLifecycles.has(l)}
                onClick={() => toggle(activeLifecycles, setActiveLifecycles, l)}
              />
            ))}
          </div>
          <div role="group" aria-label="Sort" className="flex items-center gap-1.5 rounded-chip border border-border-subtle p-0.5">
            {SORTS.map((s) => (
              <button
                key={s.key}
                onClick={() => setSort(s.key)}
                aria-pressed={sort === s.key}
                className={`whitespace-nowrap rounded-[4px] px-2 py-1 text-caption font-medium transition-colors duration-150 ease-out ${
                  sort === s.key ? "bg-accent-bg text-accent-strong" : "text-ink-tertiary hover:text-ink-secondary"
                }`}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>

        <div className="rounded-card border border-border bg-surface-1 p-3.5">
          <div className="mb-2 flex items-baseline justify-between">
            <h2 className="text-h4 font-semibold text-ink-primary">Opportunity landscape</h2>
            <span className="text-caption text-ink-muted">bubble size = Setup Quality · color = lifecycle stage</span>
          </div>
          <CandidateScatter candidates={scatterEligible} />
          {scatterExcluded > 0 && (
            <p className="mt-1.5 text-caption text-ink-muted">
              {scatterExcluded} real-scan candidate{scatterExcluded === 1 ? "" : "s"} not plotted — no Stock/Setup/Entry
              score computed by the scan yet (see cards below).
            </p>
          )}
        </div>

        <div>
          <div className="mb-2 flex items-baseline justify-between">
            <h2 className="text-h4 font-semibold text-ink-primary">Candidates</h2>
            <span className="text-caption text-ink-muted">
              {filtered.length} shown — real scan {REAL_SESSION.date}, {ALL_CANDIDATES.length} fixture rows appended
            </span>
          </div>
          {filtered.length === 0 ? (
            <div className="rounded-card border border-border-subtle bg-surface-1 p-8 text-center text-caption text-ink-tertiary">
              No candidates match the selected filters.
            </div>
          ) : (
            <div className="flex flex-wrap gap-3">
              {filtered.map((c) => (
                <CandidateCard key={`${c.symbol}-${c.setupType}-${c.dataSource}`} candidate={c} dense />
              ))}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
