import { useMemo, useState } from "react";
import { AppShell } from "../components/shell/AppShell";
import { FilterChip } from "../components/ui/FilterChip";
import { CandidateCard } from "../components/widgets/CandidateCard";
import { CandidateScatter } from "../components/widgets/CandidateScatter";
import { ALL_CANDIDATES, SETUP_LABEL, type Lifecycle, type SetupType } from "../data/fixtures";
import { LIFECYCLE_META } from "../lib/status";

type SortKey = "best_score" | "coverage" | "recency";

const SORTS: { key: SortKey; label: string }[] = [
  { key: "best_score", label: "Best score" },
  { key: "coverage", label: "Coverage" },
  { key: "recency", label: "Most recent" },
];

const SETUP_TYPES = Object.keys(SETUP_LABEL) as SetupType[];
const LIFECYCLES = Object.keys(LIFECYCLE_META) as Lifecycle[];

function sortCandidates(list: typeof ALL_CANDIDATES, key: SortKey) {
  const sorted = [...list];
  switch (key) {
    case "coverage":
      // Coverage stands in for "how many named-number rules had data" —
      // approximate with namedNumbers.length until the backend coverage
      // field is wired through.
      return sorted.sort((a, b) => b.namedNumbers.length - a.namedNumbers.length);
    case "recency":
      return sorted.sort((a, b) => (a.dataSource === b.dataSource ? 0 : a.dataSource === "real_scan" ? -1 : 1));
    case "best_score":
    default:
      return sorted.sort(
        (a, b) =>
          b.stockStrength + b.setupQuality + b.entryTiming - (a.stockStrength + a.setupQuality + a.entryTiming),
      );
  }
}

export function Candidates() {
  const [sort, setSort] = useState<SortKey>("best_score");
  const [activeSetupTypes, setActiveSetupTypes] = useState<Set<SetupType>>(new Set());
  const [activeLifecycles, setActiveLifecycles] = useState<Set<Lifecycle>>(new Set());

  const filtered = useMemo(() => {
    let base = ALL_CANDIDATES;
    if (activeSetupTypes.size > 0) base = base.filter((c) => activeSetupTypes.has(c.setupType));
    if (activeLifecycles.size > 0) base = base.filter((c) => activeLifecycles.has(c.lifecycle));
    return sortCandidates(base, sort);
  }, [sort, activeSetupTypes, activeLifecycles]);

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
          <CandidateScatter candidates={filtered} />
        </div>

        <div>
          <div className="mb-2 flex items-baseline justify-between">
            <h2 className="text-h4 font-semibold text-ink-primary">Candidates</h2>
            <span className="text-caption text-ink-muted">{filtered.length} shown</span>
          </div>
          {filtered.length === 0 ? (
            <div className="rounded-card border border-border-subtle bg-surface-1 p-8 text-center text-caption text-ink-tertiary">
              No candidates match the selected filters.
            </div>
          ) : (
            <div className="flex flex-wrap gap-3">
              {filtered.map((c) => (
                <CandidateCard key={c.symbol} candidate={c} dense />
              ))}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
