import { FileText, AlertTriangle } from "lucide-react";
import { Link } from "react-router-dom";
import { AppShell } from "../components/shell/AppShell";
import { Chip } from "../components/ui/Chip";
import { SESSION } from "../data/fixtures";
import { REAL_CALLS, OUTCOMES_META } from "../data/outcomes";

/*
  HISTORY (manual V2 §6): "past nightly reports, past candidate cards joined
  to measured outcomes. Contains the losses, visibly. This screen exists so
  the desk can never curate its own highlights." Losses get the identical
  card treatment as wins — only color differs (carried from YesterdaysCalls).

  Real-data wiring 2026-08-31: the rows below come from
  unidesk/run_history_outcomes_export.py (real research event store) and
  are emitted into outcomes_<date>.json as a build-time Vite snapshot. The
  synthetic YESTERDAYS_CALLS trio stays in fixtures.ts, tagged, for dev
  convenience; the screen renders REAL_CALLS as primary content.
*/
const OUTCOME_META: Record<string, { label: string; tone: "positive" | "danger" | "neutral" }> = {
  hit_target: { label: "Hit target", tone: "positive" },
  stopped_out: { label: "Stopped out", tone: "danger" },
  unresolved: { label: "Unresolved", tone: "neutral" },
};

const visibleCalls = REAL_CALLS.slice(0, 80);
const wins = REAL_CALLS.filter((c) => c.outcome === "hit_target").length;
const losses = REAL_CALLS.filter((c) => c.outcome === "stopped_out").length;
const unresolved = REAL_CALLS.filter((c) => c.outcome === "unresolved").length;

const showNetBpsWarning = OUTCOMES_META.netBpsCoverage === 0;

function formatNetBps(n: number | null | undefined): string {
  if (n === null || n === undefined) return "—";
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(1)} bps`;
}

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
            History rows below are joined to measured 10-bar outcomes for the
            {" "}{OUTCOMES_META.count.toLocaleString()} candidate calls across {OUTCOMES_META.symbolsCovered} symbols that
            fired a VALID detector in or before the {OUTCOMES_META.reportSession} session.
          </p>
        </div>

        {showNetBpsWarning && (
          <div className="rounded-card border border-border bg-surface-1 p-3.5">
            <div className="mb-1.5 flex items-center gap-1.5 text-caption text-ink-primary">
              <AlertTriangle size={13} aria-hidden />
              Net-of-cost numbers are not on disk yet
            </div>
            <p className="text-caption text-ink-muted">
              Outcomes carry the <span className="font-mono-num">{OUTCOMES_META.outcomeLabelsVersion}</span> label
              stamp, but the v4-net-cost writer never persisted a non-null net-of-cost field
              (0 / {OUTCOMES_META.count.toLocaleString()} calls have one). The values shown as gross
              bps / r-multiple below are real; the "net" line is intentionally blank until the
              attach_outcomes writer is rewired to read ADV from the per-session adv_series
              threaded in this wave. R-multiple and outcome class are unaffected.
            </p>
          </div>
        )}

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
            {visibleCalls.map((c) => {
              const meta = OUTCOME_META[c.outcome];
              return (
                <Link
                  key={`${c.symbol}-${c.date}-${c.setupType}`}
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
                  <span className="w-24 shrink-0 font-mono-num text-caption text-ink-tertiary">
                    {formatNetBps(c.netBps)}
                  </span>
                  <span className="flex-1 truncate text-caption text-ink-tertiary">{c.note}</span>
                  <Chip tone={meta.tone}>{meta.label}</Chip>
                </Link>
              );
            })}
          </div>
          {visibleCalls.length < REAL_CALLS.length && (
            <p className="mt-2 text-caption text-ink-muted">
              Showing the {visibleCalls.length} most recent of {REAL_CALLS.length} calls.
              A multi-date picker is the next wave (UI plan row 5) — until then the
              static Vite bundle ships one report at a time.
            </p>
          )}
        </div>
      </div>
    </AppShell>
  );
}
