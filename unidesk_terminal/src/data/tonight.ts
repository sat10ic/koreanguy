// Real nightly scan data — wired 2026-08-30, extended 2026-09-01 (UI_BUILD_SPEC_V1).
//
// Source of truth: data/market/reports/tonight_<date>.json, emitted by
// unidesk/momentum/report_json.py. This app is a static, build-time Vite
// bundle with no server and no live fetch (an EOD nightly desk, per
// unidesk/design/UI_BACKEND_INTEGRATION_PLAN.md) — report JSONs are committed
// here as build-time snapshots. reportRegistry.ts lists every bundled
// session; the selected report is shared app state (lib/ModeContext.tsx).
//
// Every field below is read straight off the JSON with no invention. Fields
// the scan does not compute are left undefined — screens render "—" or omit
// the row per UI_BUILD_SPEC_V1 PART 1.3 (the null-rendering ladder), never a
// zero-filled guess.
// C-1: the old hardcoded `TONIGHT_JSON_FILENAME = "tonight_2026-08-31.json"`
// (commented as "the newest") is gone — 2026-09-01 is newer and everything
// reads through reportRegistry.ts, which auto-discovers every bundled
// tonight_*.json and sorts newest-first. No session literal remains here.

export interface RawQualitySnapshot {
  score: number | null;
  coverage: number;
  unknowns: string[];
  feature_version?: string;
  config_hash?: string;
  hard_gates?: string[];
}

export interface RawCandidate {
  symbol: string;
  close: number;
  adr_pct?: number | null;
  rs_rank?: number | null;
  rvol?: number | null;
  contraction?: number | null;
  delivery_ratio?: number | null;
  trend?: string | null;
  sessions?: number | null;
  adjusted?: boolean;
  detector: string;
  setup_title?: string;
  trigger?: number | null;
  invalidation?: number | null;
  rr?: number | null;
  activity_score?: { activity_score: number; q_ratio: number; d_ratio: number; avg_trade_qty: number } | null;
  stock_quality?: (RawQualitySnapshot & { hard_gates: string[] }) | null;
  setup_quality?: RawQualitySnapshot | null;
  entry_quality?: RawQualitySnapshot | null;
  geometry_notes?: string[] | null;
  // Thrust / price-action quality (momentum/features/thrust.py, clean-room
  // from the authors' published descriptions). adr_max_pct is null below
  // 250 sessions — fail-closed, never a substituted ADR.
  adr_max_pct?: number | null;
  chop_score?: number | null;
  chop_band?: string | null;
  stop_thrust_days?: number | null;
  trust?: TrustInfo;
  // B-07 prior-session comparison fields (null when no prior report)
  prior_close?: number | null;
  prior_trigger_distance?: number | null;
  prior_rs_rank?: number | null;
  prior_gap_pct?: number | null;
  _prior_source?: string | null;
}

export interface TrustInfo {
  status: string;
  reason: string;
  version: string;
  rankable: boolean;
}

// B2-8: per-symbol refusal record (honesty_footer.symbol_refusals). Primary
// reason + detail; `also` carries every ADDITIONAL applicable reason — gate
// refusals as short codes, the history floor as an object with depth.
export interface SymbolRefusal {
  reason: string;
  also?: (string | { reason: string; sessions?: number; required?: number })[];
  price?: number;
  floor?: number;
  avg_turnover_cr?: number;
  sessions?: number;
  required?: number;
}

export interface BaseEpisodeAnnotation {
  kind: string;
  occurred_at: string;
  known_at: string;
}

export interface RawBaseEpisode {
  episode_id: string;
  symbol: string;
  as_of: string;
  known_at: string;
  method_version: string;
  adjustment_basis_hash: string;
  base_start: string;
  base_end: string;
  base_sessions: number;
  base_weeks: number | null;
  pivot: number | null;
  floor: number | null;
  depth_pct: number | null;
  coil_ratio: number | null;
  dry_ratio: number | null;
  dry_depth_ratio: number | null;
  rs_rank: number | null;
  verdict: string;
  notes: string[];
  annotations: BaseEpisodeAnnotation[];
  pullback_depths: number[] | null;
  atrp_percentile: number | null;
  delivery_bottom_quintile: boolean | null;
  rs_made_20d_low: boolean | null;
  vcp_match?: { preset: string; included: boolean; failed_rules: string[] } | null;
}

export interface RawSetupGroup {
  detector: string;
  title: string;
  candidate_count: number;
  trust?: TrustInfo;
  candidates: RawCandidate[];
}

export interface BreadthAnalytics {
  net_nh_nl: number | null;
  volatility_ratio: number | null;
  volume_ratio: number | null;
  up_down_close_pct: number | null;
  bo_bd_ratio: number | null;
}

export interface HonestyFooterFacts {
  regime_note: string;
  regime_built: boolean;
  universe_scanned: number;
  universe_skipped_insufficient_history: number;
  universe_gate_skips?: Record<string, number>;
  universe_gate_skips_total?: number;
  pct_above_ema50: number | null;
  above_ema21: number;
  above_ema21_of: number;
  detection_inputs_policy: string;
  adjustment_status: string;
  actions_applied: number;
  adjusted_symbols: number;
  adjustment_note: string;
  disclaimer: string;
  history_depth?: string;
  history_sessions_max?: number;
  stale_excluded?: number;
  liveness_gate?: string | null;
  liveness_excluded?: Record<string, string>;
  universe_symbols?: string[];
  /** B2-8: why each refused symbol is not in tonight's universe. */
  symbol_refusals?: Record<string, SymbolRefusal>;
  candidate_grain?: string;
  candidate_distinct_symbols?: number;
  prior_session_date?: string | null;
  prior_regime_note?: string | null;
  prior_pct_above_ema50?: number | null;
  breadth?: {
    near_highs_5pct: number;
    near_lows_5pct: number;
    near_highs_pct: number | null;
    near_lows_pct: number | null;
    analytics?: BreadthAnalytics | null;
  };
}

export interface TonightReport {
  schema_version: number;
  session_date: string;
  as_of: string;
  honesty_footer: HonestyFooterFacts;
  detector_trust?: Record<string, TrustInfo>;
  base_episodes?: RawBaseEpisode[];
  setups: RawSetupGroup[];
  candidates: RawCandidate[];
}

/** The typed report for a registry session. */
export function asReport(json: unknown): TonightReport {
  return json as TonightReport;
}

/** A symbol → episode index for one report (D-07/P-01 join by symbol). */
export function episodesBySymbol(report: TonightReport): Map<string, RawBaseEpisode> {
  const map = new Map<string, RawBaseEpisode>();
  for (const ep of report.base_episodes ?? []) {
    if (!map.has(ep.symbol)) map.set(ep.symbol, ep);
  }
  return map;
}
