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
  const hasScores = c.stockStrength !== undefined && c.setupQuality !== undefined && c.entryTiming !== undefined;
  const hasTriggerLevels = c.trigger !== undefined && c.invalidation !== undefined;
  // 2026-08-30: a detector that failed its trust audit does not produce
  // actionable candidates. The backend's audit table (report_json.py →
  // detector_trust) marks blocked/review detectors as rankable=false —
  // the card surfaces this. When the versatile flag is absent (JSON
  // predates the audit wiring), the card is unchanged.
  const trust = c.detectorTrust;
  const trustBlocked = trust && !trust.rankable;
  const trustLabel = trustBlocked
    ? trust.status === "BLOCKED" ? "Not ranked — Blocked" : "Not ranked — Review"
    : undefined;

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

      {hasScores ? (
        <QualityStack stock={c.stockStrength!} setup={c.setupQuality!} entry={c.entryTiming!} size="compact" mode={mode} />
      ) : (
        <div className="rounded-chip border border-border-subtle bg-surface-2 px-2 py-1.5">
          <div className="mb-1 text-[10px] uppercase tracking-wide text-ink-muted">
            Raw scan signals — no quality score computed
          </div>
          <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 text-caption">
            {(c.rawStats ?? []).slice(0, 4).map((s) => (
              <div key={s.label} className="flex justify-between gap-2">
                <span className="text-ink-muted">{s.label}</span>
                <span className="font-mono-num text-ink-tertiary">{s.value}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {c.why && <p className="text-caption leading-snug text-ink-secondary">{c.why}</p>}

      {hasTriggerLevels ? (
        <div className="flex items-center justify-between border-t border-border-subtle pt-2 text-caption">
          <span className="text-ink-muted">
            Trigger <span className="font-mono-num text-ink-tertiary">₹{c.trigger!.toFixed(2)}</span>
          </span>
          <span className="text-ink-muted">
            Invalid. <span className="font-mono-num text-ink-tertiary">₹{c.invalidation!.toFixed(2)}</span>
          </span>
        </div>
      ) : (
        <div className="border-t border-border-subtle pt-2 text-caption text-ink-muted">
          Trigger / invalidation not computed — raw scan only.
        </div>
      )}

      {c.dataSource === "illustrative" && (
        <span className="text-[10px] uppercase tracking-wide text-ink-muted">Illustrative — not a real scan result</span>
      )}
      {c.dataSource === "real_scan_raw" && (
        <span className="text-[10px] uppercase tracking-wide text-accent-strong">
          Real scan — {c.sessions} sessions{c.adjusted ? ", CA-adjusted" : ""}
        </span>
      )}
      {c.dataSource === "real_scan" && (
        <span className="text-[10px] uppercase tracking-wide text-ink-muted">
          Real scan (2026-07-03 fixture, superseded)
        </span>
      )}
      {trustBlocked && (
        <span className="text-[10px] uppercase tracking-wide text-danger">
          {trustLabel}
          {trust?.reason ? ` — ${trust.reason.replace(/_/g, " ")}` : ""}
        </span>
      )}
    </Link>
  );
}
