import { Link } from "react-router-dom";
import type { Candidate } from "../../data/fixtures";
import { SETUP_LABEL } from "../../data/fixtures";
import { useMode } from "../../lib/ModeContext";
import { LIFECYCLE_META } from "../../lib/status";
import { Chip } from "../ui/Chip";
import { QualityStack } from "./QualityStack";

/*
  The candidate card (manual V2 §3): symbol, close, setup name, the 3-Layer
  Quality Stack, lifecycle chip, one-line "why", trigger/invalidation pair.
  This is what "Tonight's Setups" and CANDIDATES are both built from.
*/
interface CandidateCardProps {
  candidate: Candidate;
  dense?: boolean;
}

export function CandidateCard({ candidate: c, dense = false }: CandidateCardProps) {
  const { mode } = useMode();
  const lifecycle = LIFECYCLE_META[c.lifecycle];

  return (
    <Link
      to={`/stock/${c.symbol}`}
      className={`group flex ${dense ? "w-60" : "w-72"} shrink-0 flex-col gap-2.5 rounded-card border p-3.5 transition-colors duration-150 ease-out hover:bg-surface-2 ${
        c.dataSource === "illustrative" ? "border-dashed border-border-subtle" : "border-border bg-surface-1 hover:border-border-strong"
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-baseline gap-2">
            <span className="text-h4 font-semibold text-ink-primary">{c.symbol}</span>
            <span className="font-mono-num text-caption text-ink-tertiary">₹{c.close.toFixed(2)}</span>
          </div>
          <span className="text-caption text-ink-tertiary">{SETUP_LABEL[c.setupType]}</span>
        </div>
        <Chip tone={lifecycle.tone}>{lifecycle.label}</Chip>
      </div>

      <QualityStack stock={c.stockStrength} setup={c.setupQuality} entry={c.entryTiming} size="compact" mode={mode} />

      <p className="text-caption leading-snug text-ink-secondary">{c.why}</p>

      <div className="flex items-center justify-between border-t border-border-subtle pt-2 text-caption">
        <span className="text-ink-muted">
          Trigger <span className="font-mono-num text-ink-tertiary">₹{c.trigger.toFixed(2)}</span>
        </span>
        <span className="text-ink-muted">
          Invalid. <span className="font-mono-num text-ink-tertiary">₹{c.invalidation.toFixed(2)}</span>
        </span>
      </div>

      {c.dataSource === "illustrative" && (
        <span className="text-[10px] uppercase tracking-wide text-ink-muted">Illustrative — not a real scan result</span>
      )}
    </Link>
  );
}
