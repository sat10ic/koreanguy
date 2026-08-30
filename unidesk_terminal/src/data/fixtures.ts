// Fixture data for the V2 "evening desk" prototype
// (plan/UNIFIED_DESK_UI_UX_MANUAL_V2.md). The manual's own header already
// discloses this app is a fixture prototype, not the shipped artifact (the
// shipped nightly artifact is markdown: unidesk/momentum/report.py ->
// data/market/reports/tonight_*.md). Within that constraint, REAL values
// below are transcribed verbatim from the one report that has actually run
// on real data: data/market/reports/tonight_2026-07-03.md (2,563 symbols,
// N1). Everything tagged `dataSource: "illustrative"` is invented to
// demonstrate layout for setup types / screens the backend hasn't produced
// output for yet — never present it as a real scan result.

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

export type Lifecycle = "forming" | "fresh_breakout" | "climbing" | "played_out";

export interface Candidate {
  symbol: string;
  company: string;
  sector: string;
  close: number;
  setupType: SetupType;
  lifecycle: Lifecycle;
  stockStrength: number; // 0-100
  setupQuality: number; // 0-100
  entryTiming: number; // 0-100
  trigger: number;
  invalidation: number;
  why: string; // one line, named numbers, per manual §3
  namedNumbers: { label: string; value: string; pass: boolean; rule: string }[];
  dataSource: "real_scan" | "illustrative";
  spark: number[];
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

// ILLUSTRATIVE — the other 7 detectors returned zero candidates in the real
// 2026-07-03 scan (only Momentum Burst is in the report). These exist only
// to show the grouped-by-setup layout and CANDIDATES filters; never treat
// as scan output.
export const CANDIDATES_ILLUSTRATIVE: Candidate[] = [
  {
    symbol: "TRENT",
    company: "Trent Ltd",
    sector: "Consumer Retail",
    close: 6120.0,
    setupType: "pullback",
    lifecycle: "climbing",
    stockStrength: 88,
    setupQuality: 76,
    entryTiming: 81,
    trigger: 6180.0,
    invalidation: 5960.0,
    why: "Illustrative — pullback to EMA21 on a prior breakout, volume drying up.",
    namedNumbers: [
      { label: "Pullback depth", value: "6.1%", pass: true, rule: "≤ 8%" },
      { label: "Volume dry-up", value: "0.61", pass: true, rule: "≤ 0.70" },
    ],
    dataSource: "illustrative",
    spark: spark(9),
  },
  {
    symbol: "ZOMATO",
    company: "Eternal (Zomato)",
    sector: "Technology",
    close: 289.4,
    setupType: "base_breakout",
    lifecycle: "played_out",
    stockStrength: 64,
    setupQuality: 41,
    entryTiming: 30,
    trigger: 302.0,
    invalidation: 278.0,
    why: "Illustrative — extended 8% past trigger, room mostly used up.",
    namedNumbers: [
      { label: "Base depth", value: "14.2%", pass: false, rule: "≤ 12%" },
      { label: "Distance past trigger", value: "8.1%", pass: false, rule: "≤ 3%" },
    ],
    dataSource: "illustrative",
    spark: spark(10),
  },
  {
    symbol: "RATEGAIN",
    company: "RateGain Travel Technologies",
    sector: "Technology",
    close: 512.0,
    setupType: "reversal_reclaim",
    lifecycle: "played_out",
    stockStrength: 45,
    setupQuality: 39,
    entryTiming: 28,
    trigger: 528.0,
    invalidation: 498.0,
    why: "Illustrative — reclaim failed to hold, back below EMA21 next session.",
    namedNumbers: [
      { label: "EMA21 reclaim", value: "failed", pass: false, rule: "hold ≥ 2 sessions" },
    ],
    dataSource: "illustrative",
    spark: spark(11),
  },
];

export const ALL_CANDIDATES = [...CANDIDATES, ...CANDIDATES_ILLUSTRATIVE];

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
