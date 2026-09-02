// D-01: pre-trade veto — one function, four honest outcomes. Reads the
// SELECTED report only; never guesses. Also hosts D-08 (late-entry warning)
// which shares the same real-bar inputs.
import type { TonightReport, RawCandidate } from "../data/tonight";
import { getRealHistory } from "../data/stockHistory";
import { AUDITED_BASELINE } from "./broker";

export type VetoVerdict =
  | { kind: "candidate"; candidate: RawCandidate }
  | { kind: "in_universe_no_signal" }
  | { kind: "refused_liveness"; lastPrint: string }
  | { kind: "refused_universe"; reason: string }
  | { kind: "unknown_symbol" };

export function vetoLookup(report: TonightReport, rawInput: string): VetoVerdict {
  const symbol = rawInput.trim().toUpperCase();
  if (!symbol) return { kind: "unknown_symbol" };

  const candidate = (report.candidates ?? []).find((c) => c.symbol === symbol);
  if (candidate) return { kind: "candidate", candidate };

  const liveness = report.honesty_footer.liveness_excluded ?? {};
  if (symbol in liveness) {
    return { kind: "refused_liveness", lastPrint: liveness[symbol] };
  }

  const universe = report.honesty_footer.universe_symbols;
  if (Array.isArray(universe)) {
    if (universe.includes(symbol)) return { kind: "in_universe_no_signal" };
    return {
      kind: "refused_universe",
      reason: "not in tonight's scanned universe (filtered by universe gates: price floor, turnover floor, ETF or circuit-lock heuristics; per-symbol gate reason is not logged)",
    };
  }
  // Pre-universe_symbols snapshot: the honest gap, named.
  return { kind: "unknown_symbol" };
}

// ---- D-08: late-entry percentile off the 65-session low -----------------
// The owner's audited worst entry cohort is buying >80% off the 65-day low
// (−₹81/trade average; AUDITED_BASELINE). The percentile is computed from
// the real stock-history snapshot's lows; the report close is used when the
// snapshot's last bar is the same session, otherwise the snapshot's own last
// close (vintage disclosed by the caller).
export interface OffLowReading {
  pctOffLow: number;       // how far above the 65-session low, in %
  sessionsUsed: number;
  throughDate: string;     // last bar date used (vintage disclosure)
  late: boolean;           // above the audited 80% zone
}

export function offLowReading(symbol: string, closeOverride?: number | null, session?: string): OffLowReading | null {
  const bars = getRealHistory(symbol, session);
  if (!bars || bars.length < 10) return null;
  const window = bars.slice(-65);
  const low = Math.min(...window.map((b) => b.low));
  if (!low || low <= 0) return null;
  const close = closeOverride ?? window[window.length - 1].close;
  const pctOffLow = (close / low - 1) * 100;
  return {
    pctOffLow,
    sessionsUsed: window.length,
    throughDate: window[window.length - 1].time,
    late: pctOffLow > AUDITED_BASELINE.lateEntryZonePct,
  };
}

export function lateEntryWarning(r: OffLowReading): string {
  return `⚠ ${r.pctOffLow.toFixed(0)}% off ${r.sessionsUsed}d low — your worst historical entry zone (−₹${Math.abs(AUDITED_BASELINE.lateEntryCostPerTradeInr)}/trade avg)`;
}
