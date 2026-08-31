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

function spark(seed: number, n = 20): number[] {
  let v = 50 + (seed % 20) - 10;
  const out: number[] = [];
  for (let i = 0; i < n; i++) {
    v += Math.sin(i * 0.7 + seed) * 4 + (((seed * 9301 + i * 49297) % 233280) / 233280 - 0.5) * 3;
    out.push(Math.round(v * 10) / 10);
  }
  return out;
}

// REAL — Momentum Burst, 2026-07-03, verbatim from tonight_2026-07-03.md.
export const CANDIDATES: Candidate[] = [
  {
    symbol: "BANKA",
    company: "Banka BioLoo",
    sector: "Industrials",
    close: 74.18,
    setupType: "momentum_burst",
    lifecycle: "fresh_breakout",
    stockStrength: 98,
    setupQuality: 82,
    entryTiming: 68,
    trigger: 75.66,
    invalidation: 71.59,
    why: "RS 98th percentile, RVOL 2.1x, contraction 0.73 into a strong uptrend.",
    namedNumbers: [
      { label: "Contraction", value: "0.73", pass: true, rule: "≤ 0.80" },
      { label: "RVOL", value: "2.12x", pass: true, rule: "≥ 1.5x" },
      { label: "RS rank", value: "98.0", pass: true, rule: "≥ 90" },
    ],
    dataSource: "real_scan",
    spark: spark(1),
  },
  {
    symbol: "VLEGOV",
    company: "V L Enterprises",
    sector: "Chemicals",
    close: 15.84,
    setupType: "momentum_burst",
    lifecycle: "forming",
    stockStrength: 92,
    setupQuality: 71,
    entryTiming: 55,
    trigger: 16.16,
    invalidation: 15.29,
    why: "RS 92nd percentile, RVOL 1.9x — trend still TRANSITION, not confirmed yet.",
    namedNumbers: [
      { label: "Contraction", value: "0.734", pass: true, rule: "≤ 0.80" },
      { label: "RVOL", value: "1.923x", pass: true, rule: "≥ 1.5x" },
      { label: "Trend", value: "TRANSITION", pass: false, rule: "STRONG_UPTREND preferred" },
    ],
    dataSource: "real_scan",
    spark: spark(2),
  },
  {
    symbol: "FILATEX",
    company: "Filatex India",
    sector: "Textiles",
    close: 55.95,
    setupType: "momentum_burst",
    lifecycle: "fresh_breakout",
    stockStrength: 84,
    setupQuality: 79,
    entryTiming: 74,
    trigger: 57.07,
    invalidation: 54.00,
    why: "RVOL 3.2x, delivery ratio 3.45x — heavy real participation on the burst.",
    namedNumbers: [
      { label: "Contraction", value: "0.778", pass: true, rule: "≤ 0.80" },
      { label: "RVOL", value: "3.194x", pass: true, rule: "≥ 1.5x" },
      { label: "Delivery ratio", value: "3.445", pass: true, rule: "≥ 1.2" },
    ],
    dataSource: "real_scan",
    spark: spark(3),
  },
];

export const ALL_CANDIDATES = [...CANDIDATES];

// REAL — universe + honesty footer, verbatim from tonight_2026-07-03.md.
export const SESSION = {
  date: "2026-07-03",
  universeScanned: 2563,
  universeSkipped: 197,
  pctAboveEma50: 65.86,
  aboveEma21: 1653,
  aboveEma21Of: 2563,
};

export const HONESTY_FOOTER: string[] = [
  "Symbols skipped for insufficient history: 197.",
  "Detection inputs missing for some symbols (RS needs 21 sessions, ADR/RVOL need 20 priors): such symbols are excluded from that detector, not zero-filled.",
  "Data source: NSE bhavcopy (EQ series). Unadjusted prices — long-window features are provisional until the corporate-action adjustment pass (N3).",
  "All outputs are rule results for research review. They are not recommendations, and nothing here places orders.",
];

// REAL (as of session state, not re-run into this report yet) — N2's R0
// breadth-only regime classifier computed Jun/Jul 2026 = BULL over 233
// sessions of real breadth history (unidesk/GOAL.md, N2 entry). report.py
// hasn't been re-run to fold the regime line in yet — shown here ahead of
// that wiring, flagged honestly rather than hidden.
export const REGIME = {
  label: "BULL" as const,
  sessions: 12,
  source: "R0 breadth-only classifier (N2) — not yet folded into report.py's regime line",
  aboveEma50Pct: 65.86,
  aboveEma21Pct: Math.round((1653 / 2563) * 1000) / 10,
  nearHighsPct: 22.4, // illustrative — 52w-high proximity bucket not in N2 output yet
  nearLowsPct: 6.1, // illustrative
  breadthSpark: spark(31, 30),
};

// ILLUSTRATIVE — HISTORY/outcome-join backend (labels -> candidate join)
// is not built yet; these demonstrate the "losses shown like wins" rule.
export interface OutcomeCall {
  symbol: string;
  setupType: SetupType;
  date: string;
  entry: number;
  outcome: "hit_target" | "stopped_out" | "unresolved";
  rMultiple: number | null;
  mfePct: number;
  maePct: number;
  // Optional fields populated by the real outcomes export. The
  // synthetic fixture data leaves them undefined on purpose; the
  // History screen handles undefined as "--" without crashing.
  netBps?: number | null;
  stopHit?: boolean | null;
  gapThrough?: boolean | null;
  note: string;
}

export const YESTERDAYS_CALLS: OutcomeCall[] = [
  {
    symbol: "PARKHOSPS",
    setupType: "momentum_burst",
    date: "2026-07-02",
    entry: 534.8,
    outcome: "hit_target",
    rMultiple: 2.4,
    mfePct: 9.1,
    maePct: -1.2,
    note: "Held above trigger, closed near the session high.",
  },
  {
    symbol: "NEOGEN",
    setupType: "base_breakout",
    date: "2026-07-02",
    entry: 1842.0,
    outcome: "stopped_out",
    rMultiple: -1.0,
    mfePct: 1.4,
    maePct: -3.8,
    note: "Failed to hold the breakout — stopped at invalidation the next session.",
  },
  {
    symbol: "OMNI",
    setupType: "pullback",
    date: "2026-07-01",
    entry: 42.6,
    outcome: "unresolved",
    rMultiple: null,
    mfePct: 4.2,
    maePct: -0.8,
    note: "Still inside the setup window — not yet resolved either way.",
  },
];

export interface WatchlistDrift {
  symbol: string;
  note: string;
  spark: number[];
}

export const WATCHLIST_DRIFT: WatchlistDrift[] = [
  { symbol: "TRENT", note: "Drifted 1.1% closer to the pullback trigger.", spark: spark(41) },
  { symbol: "IGPL", note: "Extended further from the last accepted entry zone.", spark: spark(42) },
  { symbol: "KIMS", note: "Setup quality improved as contraction tightened.", spark: spark(43) },
];
