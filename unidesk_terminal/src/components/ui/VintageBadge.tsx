import { AlertTriangle, Clock } from "lucide-react";

/**
 * VintageBadge — AIRTIGHT RULE 2.
 *
 * Shows the session date of a data block, with a visual warning when
 * it doesn't match the app's authoritative session date. Every screen
 * section that displays computed data should include this badge.
 *
 * Props:
 *   label: short description of the data (e.g. "Regime", "Breadth")
 *   sessionDate: the date this data was computed for
 *   appDate: the authoritative session date from the report
 *   stale: if true, forces stale styling regardless of date match
 */
interface VintageBadgeProps {
  label: string;
  sessionDate: string;
  appDate: string;
  stale?: boolean;
}

export function VintageBadge({ label, sessionDate, appDate, stale }: VintageBadgeProps) {
  const isStale = stale || sessionDate !== appDate;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-[4px] px-1.5 py-0.5 text-[10px] font-medium ${
        isStale
          ? "bg-danger-bg text-danger"
          : "bg-accent-bg/50 text-accent-strong"
      }`}
      title={isStale ? `STALE: ${label} is from ${sessionDate}, report is ${appDate}` : `${label} from ${sessionDate}`}
    >
      <Clock size={10} />
      {sessionDate}
      {isStale && <AlertTriangle size={10} />}
    </span>
  );
}

/**
 * CoherenceBanner — AIRTIGHT RULE 1.
 *
 * Renders a full-width warning banner when a screen section's data
 * vintage doesn't match the report's session date. Use this for
 * major sections (regime, candidates list, history) that must be
 * coherent with the current report.
 */
export function CoherenceBanner({ message }: { message: string }) {
  return (
    <div className="flex items-center gap-2 rounded-card border border-dashed border-danger bg-danger-bg p-3 text-caption text-danger">
      <AlertTriangle size={14} />
      <span>{message}</span>
    </div>
  );
}