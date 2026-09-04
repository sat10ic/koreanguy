import { toneColor } from "../../lib/status";

/*
  ScaleMeter (handoff PART B) — a four-segment good→bad meter for the thrust
  display bands. Colour comes from the app's tone vocabulary (lib/status.ts
  TONE_COLOR via ChipTone) so it matches chips everywhere else; "info" resolves
  to the cool score-mid tone, never warning-amber.

  Two rules it exists to enforce:
  · A null value renders "—" plus a NAMED reason ("needs 250 sessions of
    history") — never 0, never a blank that reads as a rendering failure.
  · The tooltip always carries the RAW number and the threshold rule that
    produced the word — the simplified word is a display layer, not the data.

  density "row" fits the candidate card's fixed-width flex cell; "panel" adds
  a label line for the Stock page's stacked panel.
*/

export type ScaleTone = "positive" | "info" | "warning" | "danger" | "neutral";

interface ScaleMeterProps {
  segments: 1 | 2 | 3 | 4;
  word: string;
  tone: ScaleTone;
  /** Raw value + the threshold rule, for the tooltip. */
  tooltip: string;
  /** Panel density label ("Cleanliness", "Stop room"). Omitted at row density. */
  label?: string;
  /** Pro-only raw figure rendered beside the word (e.g. "0.67d", "48"). */
  proValue?: string;
  isPro?: boolean;
  /** When the value is absent: render "—" + this reason instead of a meter. */
  nullReason?: string;
  density?: "row" | "panel";
}

export function ScaleMeter({
  segments, word, tone, tooltip, label, proValue, isPro, nullReason, density = "row",
}: ScaleMeterProps) {
  const missing = (
    <span className="inline-flex items-baseline gap-1.5" title={tooltip}>
      {label && <span className="text-caption text-ink-muted">{label}</span>}
      <span className="font-mono-num text-t3 text-ink-muted">—</span>
      <span className="truncate text-[10px] leading-none text-ink-tertiary">{nullReason ?? "not computed"}</span>
    </span>
  );

  if (nullReason != null) return density === "panel" ? <div>{missing}</div> : missing;

  const meter = (
    <span className="inline-flex items-baseline gap-1.5" title={tooltip}>
      {label && <span className="text-caption text-ink-muted">{label}</span>}
      <span className="flex items-center gap-[2px]" aria-hidden>
        {[1, 2, 3, 4].map((i) => (
          <span
            key={i}
            className="inline-block h-2.5 w-1.5 rounded-[1px]"
            style={{
              background: i <= segments ? toneColor(tone) : "var(--surface-3)",
              border: `1px solid ${i <= segments ? toneColor(tone) : "var(--border-subtle)"}`,
            }}
          />
        ))}
      </span>
      <span className="whitespace-nowrap text-[10px] font-medium leading-none text-ink-secondary">{word}</span>
      {isPro && proValue != null && (
        <span className="whitespace-nowrap font-mono-num text-[10px] leading-none text-ink-tertiary">{proValue}</span>
      )}
    </span>
  );

  return density === "panel" ? <div className="flex flex-col gap-1">{meter}</div> : meter;
}
