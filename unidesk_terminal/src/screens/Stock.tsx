import { History, Play } from "lucide-react";
import { useParams } from "react-router-dom";
import { AppShell } from "../components/shell/AppShell";
import { Chip } from "../components/ui/Chip";
import { DecisionCard } from "../components/widgets/DecisionCard";
import { SetupEvidencePanel } from "../components/widgets/SetupEvidencePanel";
import { StockChart } from "../components/widgets/StockChart";
import { ALL_CANDIDATES, SETUP_LABEL, YESTERDAYS_CALLS } from "../data/fixtures";
import { LIFECYCLE_META } from "../lib/status";

/*
  STOCK (manual V2 §5) — reading order: header, chart, decision panel, setup
  evidence, history strip. No live/social panels — those are deferred (§10).
*/
export function Stock() {
  const { symbol } = useParams<{ symbol: string }>();
  const candidate = ALL_CANDIDATES.find((c) => c.symbol === symbol);
  const priorCalls = YESTERDAYS_CALLS.filter((c) => c.symbol === symbol);

  if (!candidate) {
    return (
      <AppShell breadcrumb={["Stock"]}>
        <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
          <h1 className="text-h3 font-semibold text-ink-primary">No symbol selected</h1>
          <p className="max-w-sm text-caption text-ink-tertiary">
            Open a candidate from Tonight or Candidates to see its deep-dive workspace.
          </p>
        </div>
      </AppShell>
    );
  }

  const lifecycle = LIFECYCLE_META[candidate.lifecycle];

  return (
    <AppShell breadcrumb={["Candidates", candidate.symbol]}>
      <div className="flex flex-col gap-4 p-4">
        {/* Header */}
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-card border border-border bg-surface-1 px-4 py-3">
          <div className="flex items-baseline gap-3">
            <h1 className="text-h2 font-semibold text-ink-primary">{candidate.symbol}</h1>
            <span className="text-caption text-ink-tertiary">
              {candidate.company} · {candidate.sector}
            </span>
            <span className="font-mono-num text-h4 text-ink-primary">₹{candidate.close.toFixed(2)}</span>
          </div>
          <div className="flex items-center gap-2">
            <Chip tone="accent">{SETUP_LABEL[candidate.setupType]}</Chip>
            <Chip tone={lifecycle.tone}>{lifecycle.label}</Chip>
            <Chip tone="accent">Advisory</Chip>
          </div>
        </div>
        {candidate.dataSource === "illustrative" && (
          <div className="rounded-chip border border-dashed border-border-subtle px-3 py-2 text-caption text-ink-muted">
            Illustrative candidate — not a real 2026-07-03 scan result. Shown to demonstrate the layout for setup
            types the real scan didn't fire that session.
          </div>
        )}

        {/* Chart | Decision panel */}
        <div className="grid grid-cols-[1fr_340px] gap-4">
          <div className="h-[420px] rounded-card border border-border bg-surface-1 p-3">
            <StockChart
              symbol={candidate.symbol}
              price={candidate.close}
              triggerPrice={candidate.trigger}
              invalidationPrice={candidate.invalidation}
            />
          </div>
          <DecisionCard candidate={candidate} />
        </div>

        {/* Setup evidence */}
        <div className="rounded-card border border-border bg-surface-1 p-3.5">
          <div className="mb-2.5 flex items-baseline justify-between">
            <h2 className="text-h4 font-semibold text-ink-primary">Setup evidence</h2>
            <span className="text-caption text-ink-muted">why it did (or didn't) qualify</span>
          </div>
          <SetupEvidencePanel candidate={candidate} />
          <p className="mt-2.5 text-caption text-ink-muted">{candidate.why}</p>
        </div>

        {/* History strip */}
        <div className="rounded-card border border-border bg-surface-1 px-4 py-3">
          <div className="mb-2 flex items-center gap-2 text-caption text-ink-tertiary">
            <History size={14} aria-hidden />
            <span>This symbol's past candidates and measured outcomes</span>
          </div>
          {priorCalls.length === 0 ? (
            <p className="text-caption text-ink-muted">No prior candidates on record for {candidate.symbol} yet.</p>
          ) : (
            <div className="flex flex-col gap-1.5">
              {priorCalls.map((c) => (
                <div key={c.date} className="flex items-center gap-3 text-caption">
                  <span className="font-mono-num text-ink-muted">{c.date}</span>
                  <span className="text-ink-secondary">{c.note}</span>
                </div>
              ))}
            </div>
          )}
          <button
            disabled
            className="mt-3 flex items-center gap-1.5 rounded-chip border border-border-subtle px-2.5 py-1.5 text-caption text-ink-muted opacity-60"
            title="Replay needs the U-P0.5 recorder's owner-run live session — not available yet"
          >
            <Play size={12} aria-hidden /> Replay
          </button>
        </div>
      </div>
    </AppShell>
  );
}
