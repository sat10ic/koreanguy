import { Check, X } from "lucide-react";
import type { Candidate } from "../../data/fixtures";

/* Setup evidence (manual V2 §5.4): "which detectors fired, which rules
   passed/failed, with the named numbers." Every score must decompose to
   this — no unexplained composite. */
export function SetupEvidencePanel({ candidate }: { candidate: Candidate }) {
  return (
    <div className="flex flex-col gap-1.5">
      {candidate.namedNumbers.map((n) => (
        <div
          key={n.label}
          className="flex items-center gap-2.5 rounded-chip border border-border-subtle bg-surface-2 px-2.5 py-2"
        >
          {n.pass ? (
            <Check size={13} className="shrink-0 text-positive" aria-hidden />
          ) : (
            <X size={13} className="shrink-0 text-danger" aria-hidden />
          )}
          <span className="text-caption font-medium text-ink-primary">{n.label}</span>
          <span className="font-mono-num text-caption text-ink-secondary">{n.value}</span>
          <span className="ml-auto text-caption text-ink-muted">{n.rule}</span>
        </div>
      ))}
    </div>
  );
}
