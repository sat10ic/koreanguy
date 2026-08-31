import { FileText, AlertTriangle, CalendarRange } from "lucide-react";
import { Link } from "react-router-dom";
import { useState } from "react";
import { AppShell } from "../components/shell/AppShell";
import { Chip } from "../components/ui/Chip";
import { REAL_CALLS, OUTCOMES_META } from "../data/outcomes";
import { REAL_SESSION } from "../data/tonight";

const OUTCOME_META: Record<string, { label: string; tone: "positive" | "danger" | "neutral" }> = {
  hit_target: { label: "Hit target", tone: "positive" },
  stopped_out: { label: "Stopped out", tone: "danger" },
  unresolved: { label: "Unresolved", tone: "neutral" },
};

type RangeKey = "latest" | "this_week" | "last_week" | "this_month" | "all";

const RANGES: { key: RangeKey; label: string }[] = [
  { key: "latest", label: "Latest" },
  { key: "this_week", label: "This week" },
  { key: "last_week", label: "Last week" },
  { key: "this_month", label: "This month" },
  { key: "all", label: "All" },
];

function inRange(callDate: string, key: RangeKey, latest: string): boolean {
  if (key === "all") return true;
  const anchor = new Date(latest + "T00:00:00");
  const d = new Date(callDate + "T00:00:00");
  if (isNaN(anchor.getTime()) || isNaN(d.getTime())) return true;
  if (key === "latest") return d >= new Date(anchor.getTime() - 6 * 86400000);
  if (key === "this_week") {
    const start = anchor.getTime() - ((anchor.getDay() + 6) % 7) * 86400000;
    return d.getTime() >= start && d.getTime() <= anchor.getTime() + 86400000;
  }
  if (key === "last_week") {
    const thisMonday = anchor.getTime() - ((anchor.getDay() + 6) % 7) * 86400000;
    return d.getTime() >= thisMonday - 7 * 86400000 && d.getTime() < thisMonday;
  }
  const monthStart = new Date(anchor.getFullYear(), anchor.getMonth(), 1).getTime();
  return d.getTime() >= monthStart && d.getTime() <= anchor.getTime() + 86400000;
}

function formatNetBps(n: number | null | undefined): string {
  if (n === null || n === undefined) return "-";
  const sign = n > 0 ? "+" : "";
  return sign + n.toFixed(1) + " bps";
}
export function History() {
  const [range, setRange] = useState<RangeKey>("latest");
  const latest = REAL_SESSION.date || OUTCOMES_META.reportSession;
  const calls = REAL_CALLS.filter((c) => inRange(c.date, range, latest));
  const visibleCalls = calls.slice(0, 80);
  const wins = calls.filter((c) => c.outcome === "hit_target").length;
  const losses = calls.filter((c) => c.outcome === "stopped_out").length;
  const unresolved = calls.filter((c) => c.outcome === "unresolved").length;
  const showNetBpsWarning = OUTCOMES_META.netBpsCoverage === 0;

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
            <span className="text-caption font-medium text-ink-primary">Tonight's report - {REAL_SESSION.date}</span>
            <span className="text-caption text-ink-muted">{REAL_SESSION.universeScanned} scanned</span>
          </Link>
          <p className="mt-2 text-caption text-ink-muted">
            History rows below are joined to measured 10-bar outcomes for the
            {" "}{OUTCOMES_META.count.toLocaleString()} candidate calls across {OUTCOMES_META.symbolsCovered} symbols that
            fired a VALID detector in or before the {OUTCOMES_META.reportSession} session.
          </p>
        </div>

        <div className="flex items-center gap-1.5 rounded-chip border border-border-subtle p-0.5 w-fit">
          <CalendarRange size={13} className="ml-1 text-ink-tertiary" aria-hidden />
          {RANGES.map((r) => (
            <button
              key={r.key}
              onClick={() => setRange(r.key)}
              aria-pressed={range === r.key}
              className={"whitespace-nowrap rounded-[4px] px-2.5 py-1 text-caption font-medium transition-colors " +
                (range === r.key ? "bg-accent-bg text-accent-strong" : "text-ink-tertiary hover:text-ink-secondary")}
            >
              {r.label}
            </button>
          ))}
        </div>

        {showNetBpsWarning && (
          <div className="rounded-card border border-border bg-surface-1 p-3.5">
            <div className="mb-1.5 flex items-center gap-1.5 text-caption text-ink-primary">
              <AlertTriangle size={13} aria-hidden />
              Net-of-cost numbers are not on disk yet
            </div>
            <p className="text-caption text-ink-muted">
              Outcomes carry the <span className="font-mono-num">{OUTCOMES_META.outcomeLabelsVersion}</span> label
              stamp, but 0 / {OUTCOMES_META.count.toLocaleString()} calls have a real net-of-cost number.
              R-multiple and outcome class are unaffected.
            </p>
          </div>
        )}

        <div className="rounded-card border border-border bg-surface-1 p-3.5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-h4 font-semibold text-ink-primary">
              Past calls, outcomes joined - {range.replace(/_/g, " ")}
            </h2>
            <div className="flex items-center gap-3 text-caption">
              <span className="text-positive">{wins} hit target</span>
              <span className="text-danger">{losses} stopped out</span>
              <span className="text-ink-tertiary">{unresolved} unresolved</span>
              <span className="text-ink-muted">({calls.length} in range)</span>
            </div>
          </div>
          <div className="flex flex-col gap-2">
            {visibleCalls.map((c) => {
              const meta = OUTCOME_META[c.outcome];
              return (
                <Link
                  key={c.symbol + "-" + c.date + "-" + c.setupType}
                  to={"/stock/" + c.symbol}
                  className="flex items-center gap-3 rounded-chip border border-border-subtle bg-surface-2 px-2.5 py-2 transition-colors duration-150 ease-out hover:border-border"
                >
                  <span className="w-20 shrink-0 font-mono-num text-caption text-ink-muted">{c.date}</span>
                  <span className="w-20 shrink-0 text-caption font-semibold text-ink-primary">{c.symbol}</span>
                  <span className="w-16 shrink-0 font-mono-num text-caption text-ink-tertiary">
                    {c.rMultiple === null ? "-" : (c.rMultiple > 0 ? "+" : "") + c.rMultiple.toFixed(1) + "R"}
                  </span>
                  <span className="w-16 shrink-0 font-mono-num text-caption text-ink-tertiary">
                    MFE {c.mfePct?.toFixed(1) ?? "-"}%
                  </span>
                  <span className="w-16 shrink-0 font-mono-num text-caption text-ink-tertiary">
                    MAE {c.maePct?.toFixed(1) ?? "-"}%
                  </span>
                  <span className="w-24 shrink-0 font-mono-num text-caption text-ink-tertiary">
                    {formatNetBps(c.netBps)}
                  </span>
                  <span className="flex-1 truncate text-caption text-ink-tertiary">{c.note}</span>
                  <Chip tone={meta.tone}>{meta.label}</Chip>
                </Link>
              );
            })}
          </div>
          {visibleCalls.length < calls.length && (
            <p className="mt-2 text-caption text-ink-muted">
              Showing the {visibleCalls.length} most recent of {calls.length} calls in this range.
            </p>
          )}
        </div>
      </div>
    </AppShell>
  );
}