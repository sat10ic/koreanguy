// Real outcome-labelled calls for the History screen —
// wired 2026-08-30 (UI_BACKEND_INTEGRATION_PLAN.md row 4, "History").
//
// Source of truth: unidesk/run_history_outcomes_export.py, which reads the
// research event store (data/market/research/events/date=*/events.parquet)
// using pyarrow with a symbol IN filter and emits outcome calls for every
// Tonight symbol that has any archived outcome labels. The safety gate
// refuses to run while the store is label-mixed.
//
// This is a committed build-time snapshot, same convention as all other
// data files in this terminal (static Vite bundle, no runtime fetch).
import outcomesJson from "./outcomes_2026-08-28.json";
import type { OutcomeCall } from "./fixtures";

interface RawOutcomeCall {
  symbol: string;
  setupType: string;
  date: string;
  entry: number;
  outcome: string;
  rMultiple: number | null;
  mfePct: number;
  maePct: number;
  stopHit: boolean;
  gapThrough: boolean | null;
  netBps: number | null;
  labelVersion: string;
  note: string;
}

interface RawOutcomesFile {
  report_session: string;
  outcome_labels_version: string;
  count: number;
  symbols_with_calls: number;
  symbols_sought: number;
  calls: RawOutcomeCall[];
}

const RAW = outcomesJson as unknown as RawOutcomesFile;

export const REAL_OUTCOMES = RAW.calls as unknown as OutcomeCall[];
export const HISTORY_SUMMARY = {
  session: RAW.report_session,
  totalCalls: RAW.count,
  symbolsWithCalls: RAW.symbols_with_calls,
  symbolsSought: RAW.symbols_sought,
  outcomeLabelsVersion: RAW.outcome_labels_version,
};

export function outcomesForSymbol(symbol: string): OutcomeCall[] {
  return REAL_OUTCOMES.filter((c) => c.symbol === symbol);
}