// S-01: ONE documented verdict function for the Stock screen. Inputs are
// real report fields only (stock_quality.score, setup_quality.score,
// entry_quality.score, rr, distance to trigger). Output is a qualitative
// reading — never an instruction to trade (P-06), never a number.
//
// Rules (evaluated top to bottom, first match wins):
//   1. close > 5% past trigger                 → EXTENDED
//   2. trigger more than 8% above close        → WAIT-FAR
//   3. rr present and below 1.0                → POOR-RISK
//   4. stock ≥65 and setup ≥65 and dist ≤2%    → ACTIONABLE
//   5. stock ≥65 and setup ≥65                 → WAIT-ENTRY
//   6. otherwise                               → WATCH
export type VerdictKey =
  | "EXTENDED" | "WAIT_FAR" | "POOR_RISK" | "ACTIONABLE" | "WAIT_ENTRY" | "WATCH";

export interface Verdict {
  key: VerdictKey;
  headline: string;   // Beginner sentence
  tone: "positive" | "warning" | "danger" | "neutral";
}

export function verdictFor(c: {
  stockStrength?: number | null;
  setupQuality?: number | null;
  entryTiming?: number | null;
  rr?: number | null;
  close?: number | null;
  trigger?: number | null;
}): Verdict {
  const dist = c.trigger != null && c.close ? (c.trigger - c.close) / c.close * 100 : null;
  const strong = (c.stockStrength ?? -1) >= 65 && (c.setupQuality ?? -1) >= 65;

  if (dist != null && dist < -5) {
    return { key: "EXTENDED", headline: "Price has run past the trigger — entry is chased, not staged.", tone: "danger" };
  }
  if (dist != null && dist > 8) {
    return { key: "WAIT_FAR", headline: "The trigger is far above — let the setup come to you.", tone: "neutral" };
  }
  if (c.rr != null && c.rr < 1.0) {
    return { key: "POOR_RISK", headline: "Reward does not cover risk at these levels.", tone: "danger" };
  }
  if (strong && dist != null && dist <= 2) {
    return { key: "ACTIONABLE", headline: "Strong stock, strong setup, price near the trigger.", tone: "positive" };
  }
  if (strong) {
    return { key: "WAIT_ENTRY", headline: "Strong stock, strong setup — but the entry is unattractive right now.", tone: "warning" };
  }
  return { key: "WATCH", headline: "Qualifies on some legs only — not a full yes.", tone: "neutral" };
}
