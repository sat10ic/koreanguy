import { ShieldCheck } from "lucide-react";

/* E — Honesty Footer (manual V2 §3.E). "data gaps, missing delivery, skew,
   unknowns — named, never hidden." Rendered plainly, no decoration — this
   panel's entire job is to be trusted, not to look interesting. */
export function HonestyFooter({ items }: { items: string[] }) {
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
      </ul>
    </div>
  );
}
