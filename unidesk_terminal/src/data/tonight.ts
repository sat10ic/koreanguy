// Real nightly scan data — wired 2026-08-30.
//
// Source of truth: data/market/reports/tonight_<date>.json, emitted by
// unidesk/momentum/report_json.py (see
// unidesk/design/handoffs/HANDOFF_UI_JSON_EMITTER_COMPLETED.md). This app is
// a static, build-time Vite bundle with no server and no live fetch (an EOD
// nightly desk, per unidesk/design/UI_BACKEND_INTEGRATION_PLAN.md) — the
// report JSON is committed here as a build-time snapshot (Vite bundles JSON
// imports natively) rather than fetched at runtime. The snapshot below is a
// verbatim copy of data/market/reports/tonight_2026-08-28.json, the one real
// report that exists as of this wiring. When a newer report lands, copy the
// new file in and update TONIGHT_JSON_FILENAME/the import below — there is
// no multi-report picker yet (out of scope for this slice; see the
// integration-plan cadence table for why History/Research/Stock stay on
// fixtures).
//
// Every field below is read straight off the JSON with no invention. Fields
// the real scan does not compute (quality scores, trigger/invalidation
// prices, lifecycle stage, company/sector names, a narrative "why") are left
// undefined on the mapped Candidate — CandidateCard renders those rows from
// the illustrative fixture path instead, tagged, never silently filled in.
import tonightJson from "./tonight_2026-08-31.json";
import type { Candidate, SetupType } from "./fixtures";

export const TONIGHT_JSON_FILENAME = "tonight_2026-08-28.json";

interface RawCandidate {
  symbol: string;
  close: number;
  adr_pct: number;
  rs_rank: number;
  rvol: number;
  contraction: number;
  delivery_ratio: number;
  trend: string;
  sessions: number;
  adjusted: boolean;
  detector: string;
  setup_title: string;
  activity_score?: { activity_score: number; q_ratio: number; d_ratio: number; avg_trade_qty: number } | null;
  stock_quality?: { score: number; coverage: number; unknowns: string[]; hard_gates: string[] } | null;
  setup_quality?: { score: number | null; coverage: number; unknowns: string[]; feature_version: string; config_hash: string } | null;
  entry_quality?: { score: number | null; coverage: number; unknowns: string[]; feature_version: string; config_hash: string } | null;
  trigger?: number | null;
  invalidation?: number | null;
  rr?: number | null;
  geometry_notes?: string[] | null;
}

interface RawBaseEpisode {
  episode_id: string;
  symbol: string;
  base_start: string;
  base_end: string;
  base_sessions: number;
  depth_pct: number;
  coil_ratio: number | null;
  dry_ratio: number | null;
  verdict: string;
  vcp_match?: { preset: string; included: boolean; failed_rules: string[] } | null;
}

interface RawSetupGroup {
  detector: string;
  title: string;
  candidate_count: number;
  trust?: { status: string; reason: string; version: string; rankable: boolean };
  candidates: RawCandidate[];
}

export interface HonestyFooterFacts {
  regime_note: string;
  regime_built: boolean;
  universe_scanned: number;
  universe_skipped_insufficient_history: number;
  pct_above_ema50: number;
  above_ema21: number;
  above_ema21_of: number;
  detection_inputs_policy: string;
  adjustment_status: string;
  actions_applied: number;
  adjusted_symbols: number;
  adjustment_note: string;
  disclaimer: string;
  history_depth?: string;
  stale_excluded?: number;
  candidate_grain?: string;
  candidate_distinct_symbols?: number;
  universe_gate_skips?: Record<string, number>;
  universe_gate_skips_total?: number;
  breadth?: { near_highs_5pct: number; near_lows_5pct: number; near_highs_pct: number | null; near_lows_pct: number | null };
}

export interface TonightReport {
  schema_version: number;
  session_date: string;
  as_of: string;
  honesty_footer: HonestyFooterFacts;
  detector_trust?: Record<string, { status: string; reason: string; version: string; rankable: boolean }>;
  base_episodes?: RawBaseEpisode[];
  setups: RawSetupGroup[];
  candidates: RawCandidate[];
}

export const TONIGHT_REPORT = tonightJson as unknown as TonightReport;

function formatWhy(c: RawCandidate): string {
  // Plain restatement of the real fields — the same numbers report.py's own
  // Markdown table prints per candidate (per the emitter handoff), just
  // formatted as one line. Not a synthesized judgment: no pass/fail claim,
  // no invented threshold.
  const trendLabel = c.trend.replace(/_/g, " ").toLowerCase();
  return `${trendLabel} · RVOL ${c.rvol.toFixed(2)}x · contraction ${c.contraction.toFixed(2)} · RS rank ${c.rs_rank.toFixed(1)}`;
}

function rawStats(c: RawCandidate): { label: string; value: string }[] {
  return [
    { label: "RS rank", value: c.rs_rank.toFixed(1) },
    { label: "RVOL", value: `${c.rvol.toFixed(2)}x` },
    { label: "Contraction", value: c.contraction.toFixed(3) },
    { label: "Delivery ratio", value: c.delivery_ratio.toFixed(2) },
    { label: "ADR%", value: `${c.adr_pct.toFixed(2)}%` },
    { label: "Sessions", value: String(c.sessions) },
  ];
}

function toCandidate(c: RawCandidate): Candidate {
  const trust = TONIGHT_REPORT.detector_trust?.[c.detector];
  return {
    symbol: c.symbol,
    close: c.close,
    setupType: c.detector as SetupType,
    lifecycle: "not_classified",
    dataSource: "real_scan_raw",
    why: formatWhy(c),
    rawStats: rawStats(c),
    adrPct: c.adr_pct,
    rsRank: c.rs_rank,
    rvol: c.rvol,
    contraction: c.contraction,
    deliveryRatio: c.delivery_ratio,
    trend: c.trend,
    sessions: c.sessions,
    adjusted: c.adjusted,
    detectorTrust: trust
      ? { status: trust.status, reason: trust.reason, version: trust.version, rankable: trust.rankable }
      : undefined,
    activityScore: c.activity_score ?? undefined,
    stockStrength: c.stock_quality?.score,
    setupQuality: c.setup_quality?.score ?? undefined,
    entryTiming: c.entry_quality?.score ?? undefined,
    trigger: c.trigger ?? undefined,
    invalidation: c.invalidation ?? undefined,
    rr: c.rr ?? undefined,
    geometryNotes: c.geometry_notes ?? undefined,
  };
}

// The real, live scan result — 268 candidates across 8 detectors, from the
// 2026-08-28 session. This is what Tonight/Candidates now treat as primary
// content; the old fixture "real_scan" trio (July 3) and the illustrative
// demo trio stay in fixtures.ts, tagged, for the reasons in their own
// header comments.
export const REAL_CANDIDATES: Candidate[] = TONIGHT_REPORT.candidates.map(toCandidate);

export const REAL_SESSION = {
  date: TONIGHT_REPORT.session_date,
  asOf: TONIGHT_REPORT.as_of,
  universeScanned: TONIGHT_REPORT.honesty_footer.universe_scanned,
  universeSkipped: TONIGHT_REPORT.honesty_footer.universe_skipped_insufficient_history,
  aboveEma21: TONIGHT_REPORT.honesty_footer.above_ema21,
  aboveEma21Of: TONIGHT_REPORT.honesty_footer.above_ema21_of,
  pctAboveEma50: TONIGHT_REPORT.honesty_footer.pct_above_ema50,
  staleExcluded: TONIGHT_REPORT.honesty_footer.stale_excluded ?? 0,
  candidateGrain: TONIGHT_REPORT.honesty_footer.candidate_grain ?? "symbol",
  candidateDistinctSymbols: TONIGHT_REPORT.honesty_footer.candidate_distinct_symbols ?? REAL_CANDIDATES.length,
  breadth: TONIGHT_REPORT.honesty_footer.breadth as
    { near_highs_5pct: number; near_lows_5pct: number; near_highs_pct: number | null; near_lows_pct: number | null } | undefined,
};

// Real honesty-footer facts, rendered as structured strings (not parsed from
// prose) — the plan's non-negotiable requirement.
export const REAL_HONESTY_FOOTER: string[] = [
  `Universe scanned: ${TONIGHT_REPORT.honesty_footer.universe_scanned.toLocaleString()}. Skipped for insufficient history: ${TONIGHT_REPORT.honesty_footer.universe_skipped_insufficient_history.toLocaleString()}.`,
  TONIGHT_REPORT.honesty_footer.detection_inputs_policy,
  TONIGHT_REPORT.honesty_footer.adjustment_note,
  `Regime classifier: ${TONIGHT_REPORT.honesty_footer.regime_built ? "built" : "not built"} — ${TONIGHT_REPORT.honesty_footer.regime_note}.`,
  `Candidates: ${REAL_CANDIDATES.length} distinct symbols (grain: ${TONIGHT_REPORT.honesty_footer.candidate_grain ?? "symbol"}).`,
  TONIGHT_REPORT.honesty_footer.disclaimer,
];
