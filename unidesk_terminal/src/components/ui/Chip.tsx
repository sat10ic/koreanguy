import type { ReactNode } from "react";

// "info" is a distinct cool blue (var(--score-mid)) — kept apart from
// "accent"/"warning" (both amber) so a chip never collides with the brand
// accent or the warning semantic just because they share a hue family.
export type ChipTone = "positive" | "warning" | "danger" | "neutral" | "accent" | "info";

const TONE_CLASSES: Record<ChipTone, string> = {
  positive: "text-positive bg-positive-bg border-positive-border",
  warning: "text-warning bg-warning-bg border-warning-border",
  danger: "text-danger bg-danger-bg border-danger-border",
  neutral: "text-ink-tertiary bg-neutral-bg border-neutral-border",
  accent: "text-accent-strong bg-accent-bg border-accent-border",
  info: "text-score-mid bg-score-mid-bg border-score-mid-border",
};

interface ChipProps {
  tone: ChipTone;
  children: ReactNode;
  dot?: boolean;
  pulse?: boolean;
}

export function Chip({ tone, children, dot, pulse }: ChipProps) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-chip border px-2 py-0.5 text-caption font-medium leading-none tracking-wide ${TONE_CLASSES[tone]}`}
    >
      {dot && (
        <span className="relative flex h-1.5 w-1.5">
          {pulse && (
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-current opacity-60" />
          )}
          <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-current" />
        </span>
      )}
      {children}
    </span>
  );
}
