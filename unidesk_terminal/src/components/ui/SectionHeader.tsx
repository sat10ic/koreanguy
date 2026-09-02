import type { ReactNode } from "react";

/*
  SectionHeader (spec §7.1 + audit "typography does the work"):
  optional uppercase eyebrow -> 16px title -> quiet subtitle/count on one
  ruled line. Hairline rule instead of a box; no decorative icons.
*/
export function SectionHeader({
  title, subtitle, count, right, id, eyebrow,
}: {
  title: string;
  subtitle?: ReactNode;
  count?: ReactNode;
  right?: ReactNode;
  id?: string;
  eyebrow?: string;
}) {
  return (
    <div id={id} className="mb-4 border-b border-border pb-2.5">
      {eyebrow && (
        <div className="mb-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-ink-tertiary">
          {eyebrow}
        </div>
      )}
      <div className="flex items-baseline justify-between gap-4">
        <div className="flex min-w-0 items-baseline gap-3">
          <h2 className="text-h4 font-semibold tracking-tight text-ink-primary">{title}</h2>
          {count != null && (
            <span className="font-mono-num text-caption text-ink-muted">{count}</span>
          )}
          {subtitle && <span className="truncate text-t3 text-ink-tertiary">{subtitle}</span>}
        </div>
        {right && <div className="flex shrink-0 items-center gap-2">{right}</div>}
      </div>
    </div>
  );
}
