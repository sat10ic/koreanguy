// Shared UI types (plan/UNIFIED_DESK_UI_UX_MANUAL_V2.md). AS OF 2026-09-01
// this module contributes TYPES ONLY: every candidate rendered anywhere is
// mapped from a real tonight_<date>.json report (reportRegistry.ts +
// src/lib/candidates.ts). The illustrative rows and the old real_scan
// fixture trio were removed per G-01; no fabricated data remains.

export type SetupType =
  | "momentum_burst"
  | "episodic_pivot"
  | "ipo_base"
  | "inside_bar"
  | "base_breakout"
  | "pullback"
  | "reversal_reclaim"
  | "power_play";

export const SETUP_LABEL: Record<SetupType, string> = {
  momentum_burst: "Momentum Burst",
  episodic_pivot: "Episodic Pivot",
  ipo_base: "IPO Base",
  inside_bar: "Inside Bar",
  base_breakout: "Base Breakout",
  pullback: "Pullback",
  reversal_reclaim: "Reversal / Reclaim",
  power_play: "Power Play",
};

// H2-04: the actionable state (PRIME/READY/NEAR PIVOT/...) replaced this
// module's old lifecycle vocabulary. The Lifecycle type remains only
// because the Candidate contract carries an honest lifecycle field; the
// mapper in src/lib/candidates.ts sets it to "not_classified" and no
// screen renders that label — states come from lib/status.ts deriveState.
export type Lifecycle = "forming" | "fresh_breakout" | "climbing" | "played_out" | "not_classified";

export interface Candidate {
  symbol: string;
  company?: string;
  sector?: string;
  close: number;
  setupType: SetupType;
  lifecycle: Lifecycle;
  // Quality Stack scores (0-100) — only ever present for illustrative fixture
  // rows. The real scan (unidesk/momentum/report_json.py) has no scoring
  // model; report_json.py's own docstring documents this gap. Left
  // undefined (not zero-filled) for real candidates — CandidateCard renders
  // a raw-stats row instead of the Quality Stack when these are absent.
  stockStrength?: number;
  setupQuality?: number;
  entryTiming?: number;
  // Stage 3: Trade geometry — trigger, invalidation, initial R:R, and named
  // reasons when geometry cannot be derived (e.g. no_geometry_rule_for_detector).
  // Never fabricated; absent on fixture/illustrative rows.
  trigger?: number | null;
  invalidation?: number | null;
  rr?: number | null;
  geometryNotes?: string[] | null;
  why?: string; // one line, named numbers, per manual §3 — fixture-only prose
  namedNumbers?: { label: string; value: string; pass: boolean; rule: string }[];
  // 2026-09-01: every live row is dataSource "real_scan_raw" — mapped
  // verbatim from tonight_<date>.json. The legacy "real_scan"/"illustrative"
  // variants remain in the union only so old serialized state can't be
  // misread; nothing emits them any more.
  dataSource: "real_scan" | "real_scan_raw" | "illustrative";
  // 2026-08-30: detector trust, carried from the backend's audit table
  // (unidesk/momentum/detectors/trust.py, emitted by report_json.py as
  // detector_trust / per-candidate trust). Present only on rows that read it
  // from the report JSON. A non-rankable detector's verdicts are surfaced on
  // the card as "not ranked" (Blocked/Review), never silently shown as a
  // validated signal.
  detectorTrust?: { status: string; reason: string; version: string; rankable: boolean };
  // 2026-08-31: Reactor Scale activity score (adopted from traderlog).
  activityScore?: { activity_score: number; q_ratio: number; d_ratio: number; avg_trade_qty: number } | null;
  spark?: number[];
  // Raw scan fields, present only on dataSource === "real_scan_raw" rows —
  // verbatim from tonight_<date>.json, nothing derived or invented.
  rawStats?: { label: string; value: string }[];
  adrPct?: number;
  rsRank?: number;
  rvol?: number;
  contraction?: number;
  deliveryRatio?: number;
  trend?: string;
  sessions?: number;
  adjusted?: boolean;
  // H2-05: stock_quality decomposed — score alone must not read as
  // confident when coverage is partial or unknowns are named.
  stockQuality?: { score: number | null; coverage: number; unknowns: string[]; hard_gates: string[] } | null;
  setupQualitySnapshot?: { score: number | null; coverage: number; unknowns: string[] } | null;
  entryQualitySnapshot?: { score: number | null; coverage: number; unknowns: string[] } | null;
  // B-07 prior-session comparison (all null when no prior report exists).
  prior?: {
    close: number | null;
    triggerDistance: number | null;
    rsRank: number | null;
    gapPct: number | null;
    source: string | null;
  };
  // Thrust / price-action quality (clean-room ADRMAX + ChopScore; see
  // unidesk/momentum/features/thrust.py). Display-only mapping from the
  // report fields — no recomputation in the UI.
  // adrMaxPct is undefined below 250 sessions of history — never substitute ADR.
  adrMaxPct?: number | null;
  chopScore?: number | null;
  chopBand?: "CLEAN" | "MODERATE" | "MESSY" | "VERY_CHOPPY" | null;
  // stop distance in the stock's own thrust-days; <1.0 means the stop sits
  // inside one ordinary strong day's expansion.
  stopThrustDays?: number | null;
  // D-07 / P-01: the clean-room base episode's own lifecycle verdict
  // (watch | breakout | running | exited | insufficient_data), joined by
  // symbol. The spec's EARLY/MID/FINAL stage names are NOT emitted by the
  // backend — the real verdict enum is surfaced instead, never mapped to a
  // guessed stage word.
  baseStage?: string | null;
}

export const CANDIDATES: Candidate[] = [];
export const ALL_CANDIDATES: Candidate[] = [];

// ILLUSTRATIVE - HISTORY/outcome-join backend (labels -> candidate join)
// is not built yet. This interface is imported by outcomes.ts and outcomeHistory.ts.
export interface OutcomeCall {
  symbol: string;
  setupType: SetupType;
  date: string;
  entry: number;
  // "open"          = horizon has not elapsed; still running, NOT a win.
  // "resolved_flat"  = ran the full horizon, never stopped, never reached +1R.
  // Both were previously mislabelled "hit_target" by the exporter.
  outcome: "hit_target" | "stopped_out" | "open" | "resolved_flat" | "unresolved";
  rMultiple: number | null;
  // mfePct/maePct are null on unresolved rows in the real outcomes export
  // (H3-05: this file previously crashed the screen via .toFixed() on null).
  mfePct: number | null;
  maePct: number | null;
  netBps?: number | null;
  stopHit?: boolean | null;
  gapThrough?: boolean | null;
  note: string;
}
