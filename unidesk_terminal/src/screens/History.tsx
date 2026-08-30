import { FileText } from "lucide-react";
import { Link } from "react-router-dom";
import { AppShell } from "../components/shell/AppShell";
import { Chip } from "../components/ui/Chip";
import { SESSION, YESTERDAYS_CALLS } from "../data/fixtures";

/*
  HISTORY (manual V2 §6): "past nightly reports, past candidate cards joined
  to measured outcomes. Contains the losses, visibly. This screen exists so
  the desk can never curate its own highlights." Losses get the identical
  card treatment as wins — only color differs (carried from YesterdaysCalls).
*/
const OUTCOME_META: Record<string, { label: string; tone: "positive" | "danger" | "neutral" }> = {
  hit_target: { label: "Hit target", tone: "positive" },
  stopped_out: { label: "Stopped out", tone: "danger" },
  unresolved: { label: "Unresolved", tone: "neutral" },
};

const wins = YESTERDAYS_CALLS.filter((c) => c.outcome === "hit_target").length;
const losses = YESTERDAYS_CALLS.filter((c) => c.outcome === "stopped_out").length;
const unresolved = YESTERDAYS_CALLS.filter((c) => c.outcome === "unresolved").length;

export function History() {
  return (
    <AppShell breadcrumb={["History"]}>
      <div className="flex flex-col gap-4 p-4">
        <div className="rounded-card border border-border bg-surface-1 p-3.5">
          <div className="mb-2.5 flex items-center gap-1.5 text-caption text-ink-muted">
            <FileText size={13} aria-hidden />
            Past reports
          </div>
          <Link
            to="/"
            className="flex items-center justify-between rounded-chip border border-border-subtle bg-surface-2 px-3 py-2 transition-colors duration-150 ease-out hover:border-border"
          >
            <span className="text-caption font-medium text-ink-primary">Tonight's report — {SESSION.date}</span>
            <span className="text-caption text-ink-muted">{SESSION.universeScanned} scanned</span>
          </Link>
          <p className="mt-2 text-caption text-ink-muted">
            Only one report has run on real data so far (N1). Reports accumulate here nightly going forward.
          </p>
        </div>

        <div className="rounded-card border border-border bg-surface-1 p-3.5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-h4 font-semibold text-ink-primary">Every past call, outcomes joined</h2>
            <div className="flex items-center gap-3 text-caption">
              <span className="text-positive">{wins} hit target</span>
              <span className="text-danger">{losses} stopped out</span>
              <span className="text-ink-tertiary">{unresolved} unresolved</span>
            </div>
          </div>
          <div className="flex flex-col gap-2">
            {YESTERDAYS_CALLS.map((c) => {
              const meta = OUTCOME_META[c.outcome];
              return (
                <Link
                  key={`${c.symbol}-${c.date}`}
                  to={`/stock/${c.symbol}`}
                  className="flex items-center gap-3 rounded-chip border border-border-subtle bg-surface-2 px-2.5 py-2 transition-colors duration-150 ease-out hover:border-border"
                >
                  <span className="w-20 shrink-0 font-mono-num text-caption text-ink-muted">{c.date}</span>
                  <span className="w-20 shrink-0 text-caption font-semibold text-ink-primary">{c.symbol}</span>
                  <span className="w-16 shrink-0 font-mono-num text-caption text-ink-tertiary">
                    {c.rMultiple === null ? "—" : `${c.rMultiple > 0 ? "+" : ""}${c.rMultiple.toFixed(1)}R`}
                  </span>
                  <span className="w-16 shrink-0 font-mono-num text-caption text-ink-tertiary">
                    MFE {c.mfePct.toFixed(1)}%
                  </span>
                  <span className="w-16 shrink-0 font-mono-num text-caption text-ink-tertiary">
                    MAE {c.maePct.toFixed(1)}%
                  </span>
                  <span className="flex-1 truncate text-caption text-ink-tertiary">{c.note}</span>
                  <Chip tone={meta.tone}>{meta.label}</Chip>
                </Link>
              );
            })}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
