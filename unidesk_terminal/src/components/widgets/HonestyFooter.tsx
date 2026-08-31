import { ShieldCheck, AlertTriangle, Clock } from "lucide-react";
import { TONIGHT_REPORT } from "../../data/tonight";

/* E — Honesty Footer (manual V2 §3.E). "data gaps, missing delivery, skew,
   unknowns — named, never hidden." Rendered plainly, no decoration — this
   panel's entire job is to be trusted, not to look interesting.

   2026-09-01: now includes liveness gate count, history depth, and grain
   disclosure. Every number in the footer is a real field from the pipeline
   JSON — never a fixture, never invented. */
export function HonestyFooter({ items }: { items: string[] }) {
  const hf = TONIGHT_REPORT.honesty_footer;
  const stale = hf?.stale_excluded ?? 0;
  const depth = hf?.history_depth ?? null;

  return (
    <div className="rounded-card border border-border-subtle bg-surface-1 p-3.5">
      <div className="mb-2 flex items-center gap-1.5 text-caption font-medium text-ink-secondary">
        <ShieldCheck size={13} className="text-ink-tertiary" aria-hidden />
        Honesty footer
      </div>
      <ul className="flex flex-col gap-1.5">
        {items.map((item, i) => (
          <li key={i} className="flex gap-2 text-caption text-ink-tertiary">
            <span className="text-ink-muted">–</span>
            <span>{item}</span>
          </li>
        ))}
        {stale > 0 && (
          <li className="flex gap-2 text-caption text-ink-tertiary">
            <span className="text-ink-muted">–</span>
            <span className="flex items-center gap-1">
              <AlertTriangle size={12} className="text-danger" />
              {stale} symbol{stale === 1 ? "" : "s"} excluded by liveness gate — no trade on session date
            </span>
          </li>
        )}
        {depth && (
          <li className="flex gap-2 text-caption text-ink-tertiary">
            <span className="text-ink-muted">–</span>
            <span className="flex items-center gap-1">
              <Clock size={12} className="text-ink-muted" />
              {depth}
            </span>
          </li>
        )}
      </ul>
    </div>
  );
}