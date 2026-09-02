// Candidate enrichment shared by every screen (UI_BUILD_SPEC_V1 §0.55).
// One mapper, one ranking function, one section-metric table — all
// documented, all reading real report fields only.
import type { Candidate, SetupType } from "../data/fixtures";
import { episodesBySymbol, type RawBaseEpisode, type RawCandidate, type TonightReport } from "../data/tonight";
import { getRealHistory } from "../data/stockHistory";
import { deriveState, type ActionableState } from "./status";

const SETUP_ORDER: SetupType[] = [
  "base_breakout", "episodic_pivot", "inside_bar", "ipo_base",
  "power_play", "pullback", "reversal_reclaim",
];

/** H2-12 ranking key — single documented function.
 *  Order: actionable state (PRIME first, per STATE_THRESHOLDS in status.ts),
 *  then closest to trigger, then higher rs_rank, then symbol. Detectors with
 *  trust.rankable === false (P-04) are excluded from ranking entirely — the
 *  UI renders them unranked (no 01/02 numbers), alphabetically, visible with
 *  their trust reason. */
const STATE_RANK: Record<ActionableState, number> = {
  PRIME: 0, READY: 1, NEAR_PIVOT: 2, WATCH: 3, LOW_LIQ: 4, LOOSE: 5, EXTENDED: 6, REJECT: 7,
};

export function compareCandidates(a: Candidate, b: Candidate): number {
  const sa = STATE_RANK[deriveState(a)] ?? 9;
  const sb = STATE_RANK[deriveState(b)] ?? 9;
  if (sa !== sb) return sa - sb;
  const da = triggerDistPct(a), db = triggerDistPct(b);
  if (da != null && db != null && Math.abs(da - db) > 1e-9) return Math.abs(da) - Math.abs(db);
  const ra = a.rsRank ?? -1, rb = b.rsRank ?? -1;
  if (ra !== rb) return rb - ra;
  return a.symbol.localeCompare(b.symbol);
}

/** Percentage distance from close to trigger; negative = price above trigger. */
export function triggerDistPct(c: {
  close?: number | null; trigger?: number | null;
}): number | null {
  if (c.trigger == null || c.close == null || !c.close) return null;
  return (c.trigger - c.close) / c.close * 100;
}

/** Map one report's raw candidates into enriched rows. */
export function mapCandidates(report: TonightReport): Candidate[] {
  const episodes = episodesBySymbol(report);
  const session = report.session_date;
  return (report.candidates ?? []).map((c: RawCandidate) => toEnriched(c, episodes, session));
}

function toEnriched(c: RawCandidate, episodes: Map<string, RawBaseEpisode>, session: string): Candidate {
  const ep = episodes.get(c.symbol);
  return {
    symbol: c.symbol,
    close: c.close,
    setupType: c.detector as SetupType,
    lifecycle: "not_classified",
    dataSource: "real_scan_raw",
    adrPct: c.adr_pct ?? undefined,
    rsRank: c.rs_rank ?? undefined,
    rvol: c.rvol ?? undefined,
    contraction: c.contraction ?? undefined,
    deliveryRatio: c.delivery_ratio ?? undefined,
    trend: c.trend ?? undefined,
    sessions: c.sessions ?? undefined,
    adjusted: c.adjusted,
    stockStrength: c.stock_quality?.score ?? undefined,
    stockQuality: c.stock_quality ?? null,
    setupQuality: c.setup_quality?.score ?? undefined,
    setupQualitySnapshot: c.setup_quality ?? null,
    entryTiming: c.entry_quality?.score ?? undefined,
    entryQualitySnapshot: c.entry_quality ?? null,
    trigger: c.trigger ?? undefined,
    invalidation: c.invalidation ?? undefined,
    rr: c.rr ?? undefined,
    // Thrust / price-action quality (features/thrust.py, clean-room from the
    // author's published spec). adrMaxPct is undefined for names with under
    // 250 sessions — fail-closed, never a substituted ADR.
    adrMaxPct: c.adr_max_pct ?? undefined,
    chopScore: c.chop_score ?? undefined,
    chopBand: (c.chop_band ?? undefined) as Candidate["chopBand"],
    stopThrustDays: c.stop_thrust_days ?? undefined,
    geometryNotes: c.geometry_notes ?? undefined,
    detectorTrust: c.trust,
    activityScore: c.activity_score ?? null,
    prior: c.prior_close !== undefined || c.prior_trigger_distance !== undefined
      ? {
          close: c.prior_close ?? null,
          triggerDistance: c.prior_trigger_distance ?? null,
          rsRank: c.prior_rs_rank ?? null,
          gapPct: c.prior_gap_pct ?? null,
          source: c._prior_source ?? null,
        }
      : undefined,
    baseStage: ep ? ep.verdict : undefined,
    spark: sparkCloses(c.symbol, session),
  };
}

/** H2-03: sparkline closes from the real stock-history snapshot only.
 * Undefined → the cell renders nothing; a synthetic sparkline is never
 * drawn. The snapshot carries bars through its own session date (2026-08-28),
 * which is ≤ every bundled report session — no future leakage either way. */
function sparkCloses(symbol: string, session: string): number[] | undefined {
  const bars = getRealHistory(symbol, session);
  if (!bars || bars.length < 2) return undefined;
  return bars.slice(-30).map((b) => b.close);
}

/** H2-11: one setup-specific metric per section. Only rendered where the
 * backing field exists; the caller reports the rest BLOCKED (Pro mode). */
export const SECTION_METRIC: Record<SetupType, { label: string; blocked?: string; read: (c: Candidate) => string | null }> = {
  base_breakout: { label: "Pivot dist", read: (c) => pct(triggerDistPct(c)) },
  inside_bar: { label: "Compression", read: (c) => (c.contraction != null ? c.contraction.toFixed(2) : null) },
  episodic_pivot: { label: "Prior-day gap", read: (c) => pct(c.prior?.gapPct ?? null) },
  ipo_base: { label: "Wks listed", blocked: "weeks_since_listing not emitted", read: () => null },
  power_play: { label: "Gain+depth", blocked: "gain_pct / depth_pct not emitted", read: () => null },
  pullback: { label: "Dist from EMA", blocked: "ema21_distance_pct / avwap_extension not emitted", read: () => null },
  reversal_reclaim: { label: "Reclaimed level", blocked: "reclaimed_level not emitted", read: () => null },
  momentum_burst: { label: "Burst quality", blocked: "burst-specific fields not emitted", read: () => null },
};

function pct(v: number | null): string | null {
  return v == null ? null : `${v > 0 ? "+" : ""}${v.toFixed(1)}%`;
}

/** Group candidates into the seven setup sections in fixed display order. */
export function groupBySetup(candidates: Candidate[]): [SetupType, Candidate[]][] {
  const groups = new Map<SetupType, Candidate[]>();
  for (const t of SETUP_ORDER) groups.set(t, []);
  for (const c of candidates) {
    const key = c.setupType as SetupType;
    if (!groups.has(key)) continue;
    groups.get(key)!.push(c);
  }
  return [...groups.entries()];
}
