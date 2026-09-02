import type { ReactNode } from "react";

/*
  MetricRow (spec §7.3): label — value — delta/interpretation, with an
  optional inline microbar. The delta column is rendered by the caller
  from real prior data; when no prior exists it renders "—", never a
  fabricated change.
*/
export function MetricRow({
  label, value, delta, delta5, barPct, barTone, tooltip,
}: {
  label: string;
  value: ReactNode;
  delta?: ReactNode;
  delta5?: ReactNode;
  barPct?: number | null;
  barTone?: string;
  tooltip?: string;
}) {
  return (
    <div className="grid grid-cols-[130px_1fr_64px_64px_64px] items-center gap-x-3 border-b border-subtle py-2 last:border-b-0">
      <span className="truncate text-t3 text-ink-secondary" title={tooltip}>{label}</span>
      <div className="flex items-center gap-3">
        {barPct != null && (
          <div className="h-2 w-full max-w-56 overflow-hidden rounded-sm bg-surface-2">
            <div
              className="h-full rounded-sm"
              style={{ width: Math.min(100, Math.max(1.5, barPct)) + "%", background: barTone ?? "var(--accent)", opacity: 0.75 }}
            />
          </div>
        )}
        <span className="ml-auto font-mono-num text-t3 font-semibold text-ink-primary">{value}</span>
      </div>
      <span className="text-right font-mono-num text-caption text-ink-secondary">{delta ?? "—"}</span>
      <span className="text-right font-mono-num text-caption text-ink-tertiary">{delta5 ?? "—"}</span>
      <span />
    </div>
  );
}
