// Per-symbol outcome lookups for the Stock screen — shares the glob-based
// outcomes module so both History and Stock read the same newest snapshot.
import { REAL_CALLS, OUTCOMES_META } from "./outcomes";
import type { OutcomeCall } from "./fixtures";

export const REAL_OUTCOMES = REAL_CALLS;
export const HISTORY_SUMMARY = {
  session: OUTCOMES_META.reportSession,
  totalCalls: OUTCOMES_META.count,
  symbolsWithCalls: OUTCOMES_META.symbolsCovered,
  symbolsSought: OUTCOMES_META.symbolsCovered,
  outcomeLabelsVersion: OUTCOMES_META.outcomeLabelsVersion,
};

export function outcomesForSymbol(symbol: string): OutcomeCall[] {
  return REAL_CALLS.filter((c) => c.symbol === symbol);
}
