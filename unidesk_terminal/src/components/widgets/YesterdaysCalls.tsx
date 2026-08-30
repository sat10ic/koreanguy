import { Link } from "react-router-dom";
import type { OutcomeCall } from "../../data/fixtures";
import { Chip } from "../ui/Chip";

/* C — Yesterday's Calls (manual V2 §3.C). "measured outcomes; losses shown
   like wins" — the loss row gets the exact same visual treatment as the
   win row (same card shape, same font weight), only the color differs. */
const OUTCOME_META: Record<OutcomeCall["outcome"], { label: string; tone: "positive" | "danger" | "neutral" }> = {
  hit_target: { label: "Hit target", tone: "positive" },
  stopped_out: { label: "Stopped out", tone: "danger" },
  unresolved: { label: "Unresolved", tone: "neutral" },
};

export function YesterdaysCalls({ calls }: { calls: OutcomeCall[] }) {
  return (
    <div className="rounded-card border border-border bg-surface-1 p-3.5">
      <div className="mb-2.5 flex items-baseline justify-between">
        <h2 className="text-h4 font-semibold text-ink-primary">Yesterday's calls</h2>
        <span className="text-caption text-ink-muted">what happened next</span>
      </div>
      <div className="flex flex-col gap-2">
        {calls.map((c) => {
          const meta = OUTCOME_META[c.outcome];
          return (
            <Link
              key={`${c.symbol}-${c.date}`}
              to={`/stock/${c.symbol}`}
              className="flex items-center gap-3 rounded-chip border border-border-subtle bg-surface-2 px-2.5 py-2 transition-colors duration-150 ease-out hover:border-border"
            >
              <span className="w-20 shrink-0 text-caption font-semibold text-ink-primary">{c.symbol}</span>
              <span className="w-16 shrink-0 font-mono-num text-caption text-ink-tertiary">
                {c.rMultiple === null ? "—" : `${c.rMultiple > 0 ? "+" : ""}${c.rMultiple.toFixed(1)}R`}
              </span>
              <span className="flex-1 truncate text-caption text-ink-tertiary">{c.note}</span>
              <Chip tone={meta.tone}>{meta.label}</Chip>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
