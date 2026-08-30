import type { ChipTone } from "../components/ui/Chip";
import type { Lifecycle } from "../data/fixtures";

// Single source of truth for tone -> color, so "warning is always amber"
// holds everywhere (V2 manual §9: "colour never carries meaning alone").
export const TONE_COLOR: Record<ChipTone, string> = {
  positive: "var(--positive)",
  warning: "var(--warning)",
  danger: "var(--danger)",
  neutral: "var(--neutral)",
  accent: "var(--accent)",
  info: "var(--score-mid)",
};

export function toneColor(tone: ChipTone): string {
  return TONE_COLOR[tone];
}

export const LIFECYCLE_META: Record<Lifecycle, { label: string; tone: ChipTone }> = {
  forming: { label: "Forming", tone: "neutral" },
  fresh_breakout: { label: "Fresh breakout", tone: "info" },
  climbing: { label: "Climbing", tone: "positive" },
  played_out: { label: "Played out", tone: "warning" },
};

// Score bands (Stock/Setup/Entry, 0-100). Amber is reserved for the warning
// SEMANTIC elsewhere (chips, alerts) — reusing it here would make a mid
// score read as "caution" instead of "average", so the middle band gets a
// distinct cool neutral instead of warning-amber.
export function scoreTone(score: number): "positive" | "score-mid" | "danger" {
  if (score >= 75) return "positive";
  if (score >= 45) return "score-mid";
  return "danger";
}

export function scoreColor(score: number): string {
  if (score >= 75) return "var(--positive)";
  if (score >= 45) return "var(--score-mid)";
  return "var(--danger)";
}
