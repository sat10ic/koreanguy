// Fixture data for the V2 "evening desk" prototype
// (plan/UNIFIED_DESK_UI_UX_MANUAL_V2.md). AS OF 2026-08-31 all illustrative
// candidates have been deleted per the owner's product-turn directive (see
// HANDOFF_2026-08-31_PRODUCT_TURN_FOR_DEEPSEEK.md). The only remaining
// fixture rows are the 3 real_scan records (BANKA/VLEGOV/FILATEX) from the
// 2026-07-03 report — superseded by the live 2026-08-28 scan's 73 real
// candidates but kept for reference. No fabricated data remains.

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

// "not_classified" added 2026-08-30 for the real JSON emitter wiring: the
// real nightly scan (data/market/reports/tonight_<date>.json) does not
// compute a lifecycle stage, unlike the illustrative fixture rows below
// which invent one for layout purposes. Real candidates get this honest
// "we don't know yet" bucket rather than a borrowed/fabricated stage.
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
  // 2026-08-30: real_scan_raw distinguishes the new real JSON records (raw
  // detector fields only, no quality scoring) from the older `real_scan`
  // fixture rows (BANKA/VLEGOV/FILATEX, fully scored, from the 2026-07-03
  // report, now superseded by the real 2026-08-28 scan but kept in fixtures
  // per the no-delete rule). Never blend the two silently — CandidateCard
  // tags them with different badges.
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
  outcome: "hit_target" | "stopped_out" | "unresolved";
  rMultiple: number | null;
  mfePct: number;
  maePct: number;
  netBps?: number | null;
  stopHit?: boolean | null;
  gapThrough?: boolean | null;
  note: string;
}
