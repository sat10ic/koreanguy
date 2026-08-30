import type { Candidate } from "../../data/fixtures";
import { REGIME } from "../../data/fixtures";
import { useMode } from "../../lib/ModeContext";
import { LIFECYCLE_META } from "../../lib/status";
import { Chip } from "../ui/Chip";
import { ContributorBars } from "./ContributorBars";
import { QualityStack } from "./QualityStack";

/*
  Decision panel (manual V2 §5.3): "the 3-Layer Stack, entry-quality
  contributors (each bar decomposable), regime context, circuit/exit-risk
  chips." Policy is always a single static ADVISORY chip (R3/R7: rule
  outputs, not recommendations) — never a tradable/watch/avoid judgment.
*/
interface DecisionCardProps {
  candidate: Candidate;
}

export function DecisionCard({ candidate: c }: DecisionCardProps) {
  const { mode } = useMode();
  const lifecycle = LIFECYCLE_META[c.lifecycle];
  // Stock.tsx (out of scope for this slice) only ever looks candidates up
  // from the fully-scored ALL_CANDIDATES fixture, so these are always
  // defined in practice today. Defaults here are a type-safety fallback for
  // the Candidate type now being shared with the unscored real-scan rows
  // (src/data/tonight.ts) — not a claim that a real candidate has a score.
  const stockStrength = c.stockStrength ?? 0;
  const setupQuality = c.setupQuality ?? 0;
  const entryTiming = c.entryTiming ?? 0;
  const trigger = c.trigger ?? c.close;
  const invalidation = c.invalidation ?? c.close;
  const exitRisk = setupQuality < 55 ? { label: "Elevated exit risk", tone: "warning" as const } : { label: "Normal exit risk", tone: "neutral" as const };

  const contributors = [
    { label: "Room to trigger", value: Math.max(4, 100 - Math.abs(((trigger - c.close) / c.close) * 100) * 14), detail: `${(((trigger - c.close) / c.close) * 100).toFixed(1)}%` },
    { label: "Risk:reward", value: Math.min(100, ((trigger - invalidation) > 0 ? (trigger - c.close) / (trigger - invalidation) : 0) * 40), detail: `${(((trigger - c.close) / Math.max(0.01, trigger - invalidation))).toFixed(1)}R` },
    { label: "Extension", value: 100 - Math.min(100, Math.abs(((c.close - invalidation) / invalidation) * 100) * 6), detail: `${(((c.close - invalidation) / invalidation) * 100).toFixed(1)}%` },
    { label: "Trigger proximity", value: entryTiming, detail: `${entryTiming}` },
  ];

  return (
    <div className="rounded-card border border-border bg-surface-1 p-4">
      <div className="mb-3 flex items-start justify-between">
        <div>
          <div className="flex items-baseline gap-2">
            <span className="text-h3 font-semibold text-ink-primary">{c.symbol}</span>
            <span className="font-mono-num text-body text-ink-secondary">₹{c.close.toFixed(2)}</span>
          </div>
          <span className="text-caption text-ink-tertiary">{c.company}</span>
        </div>
        <div className="flex flex-col items-end gap-1">
          <Chip tone="accent">Advisory</Chip>
          <Chip tone={lifecycle.tone}>{lifecycle.label}</Chip>
        </div>
      </div>

      <QualityStack stock={stockStrength} setup={setupQuality} entry={entryTiming} size="full" mode={mode} />

      <div className="mt-4">
        <div className="mb-2 text-caption text-ink-muted">Entry timing, decomposed</div>
        <ContributorBars contributors={contributors} />
      </div>

      <div className="mt-4 flex items-center justify-between border-t border-border-subtle pt-3">
        <span className="text-caption text-ink-tertiary" title={REGIME.source}>
          Regime: <span className="font-medium text-ink-secondary">{REGIME.label}</span>
        </span>
        <Chip tone={exitRisk.tone}>{exitRisk.label}</Chip>
      </div>
    </div>
  );
}
