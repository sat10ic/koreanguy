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
  // Real scan candidates (tonight_<date>.json) carry no lifecycle stage —
  // the backend doesn't compute one. Honest "unknown" bucket, not a guess.
  not_classified: { label: "Not classified", tone: "neutral" },
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

// H2-04: Actionable states derived from trigger vs close + stock_quality score.
// Thresholds are documented constants per spec V1 H2-04.
export type ActionableState = "PRIME" | "READY" | "NEAR_PIVOT" | "WATCH" | "EXTENDED" | "LOOSE" | "LOW_LIQ" | "REJECT";

const STATE_THRESHOLDS = {
  primeEntryPct: -3.0,   // close within 3% below trigger
  readyEntryPct: -8.0,   // close within 8% below trigger
  extendedPct: 5.0,      // close more than 5% above trigger → extended
  minQuality: 60,        // stock_quality.score below this → watch-only
  minRvol: 0.3,          // rvol below this → LOW_LIQ
  minRsRank: 20,         // rs_rank below this → LOOSE (weak RS context)
};

export function deriveState(c: {
  close?: number | null; trigger?: number | null;
  stockStrength?: number | null; stock_quality?: { score?: number } | null;
  rvol?: number | null; rsRank?: number | null;
}): ActionableState {
  const sq = c.stockStrength ?? c.stock_quality?.score;
  const rv = c.rvol;
  const rs = c.rsRank;
  const cl = c.close;
  const tr = c.trigger;

  if (sq != null && sq < STATE_THRESHOLDS.minQuality) return "WATCH";
  if (rv != null && rv < STATE_THRESHOLDS.minRvol) return "LOW_LIQ";
  if (rs != null && rs < STATE_THRESHOLDS.minRsRank) return "LOOSE";

  if (tr != null && cl != null) {
    const distPct = (tr - cl) / cl * 100;
    if (distPct <= 0) {
      if (distPct >= -STATE_THRESHOLDS.extendedPct) return "PRIME";
      return "EXTENDED";
    }
    if (distPct <= -STATE_THRESHOLDS.primeEntryPct) return "PRIME";
    if (distPct <= -STATE_THRESHOLDS.readyEntryPct) return "READY";
    return "NEAR_PIVOT";
  }
  return "REJECT";
}

export const STATE_META: Record<ActionableState, { label: string; tone: "positive" | "info" | "warning" | "danger" | "neutral" }> = {
  PRIME: { label: "PRIME", tone: "positive" },
  READY: { label: "READY", tone: "info" },
  NEAR_PIVOT: { label: "NEAR PIVOT", tone: "warning" },
  WATCH: { label: "WATCH", tone: "neutral" },
  EXTENDED: { label: "EXTENDED", tone: "danger" },
  LOOSE: { label: "LOOSE", tone: "neutral" },
  LOW_LIQ: { label: "LOW LIQ", tone: "neutral" },
  REJECT: { label: "REJECT", tone: "danger" },
};
