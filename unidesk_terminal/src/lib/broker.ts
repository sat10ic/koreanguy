// D-10 namespace: the owner's broker trade history. A DISTINCT source from
// PART 1 scan data — different grain (fills), different provenance (audited
// broker tradebook import), different trust. It is never merged into scan
// output, candidate lists, or research archives; it lives in its own module
// and every surface that shows it labels the source.
import tradesJson from "../data/broker/trades.json";
import deskSaidJson from "../data/broker/desk_said.json";

export interface BrokerTrade {
  trade_date: string;
  symbol: string;
  side: "BUY" | "SELL";
  quantity: string;
  price: string;
  gross_value: string;
  net_value: string;
  fees_allocated: string;
  product_type: string;
  exchange: string;
}

interface TradesFile {
  source: string;
  provenance: string;
  generator: string;
  count: number;
  trades: BrokerTrade[];
}

const TRADES = tradesJson as unknown as TradesFile;

export const BROKER_SOURCE_LABEL = `broker import (${TRADES.source}) — not scan data`;
export const BROKER_TRADES: BrokerTrade[] = TRADES.trades;

// D-06 audited baseline constants — from the owner's own audit, not
// computed here. Source: manas_os/design/reports/BROKER_AUDIT_2026-07-18.md
// and TRADE_AUTOPSY_2026-07-19.md (also UI_BUILD_SPEC_V1.md PART 11.0).
export const AUDITED_BASELINE = {
  source: "BROKER_AUDIT_2026-07-18.md / TRADE_AUTOPSY_2026-07-19.md",
  entriesPerWeek: 7,
  sameDayRoundTrips: 64,
  revengeReEntries: 27,
  lateExitCostInr: -4381,
  lateEntryCostPerTradeInr: -81,
  lateEntryZonePct: 80, // >80% off the 65d low = his worst entry zone
};

// D-09: what the desk said on each past session (per report on disk).
interface DeskSaidFile {
  source: string;
  generator: string;
  sessions: Record<string, {
    universe_known: boolean;
    universe_count: number | null;
    candidates: Record<string, string>;
    in_universe: string[];
  }>;
}

const DESK_SAID = deskSaidJson as unknown as DeskSaidFile;

export type DeskVerdict =
  | { kind: "candidate"; detector: string }
  | { kind: "in_universe" }
  | { kind: "unknown_universe" }   // report predates universe_symbols export
  | { kind: "not_in_universe" }
  | { kind: "no_report" };

export function deskSaidFor(date: string, symbol: string): DeskVerdict {
  const s = DESK_SAID.sessions[date];
  if (!s) return { kind: "no_report" };
  if (s.candidates[symbol]) return { kind: "candidate", detector: s.candidates[symbol] };
  if (s.in_universe.includes(symbol)) return { kind: "in_universe" };
  if (!s.universe_known) return { kind: "unknown_universe" };
  return { kind: "not_in_universe" };
}

export function deskSaidDates(): string[] {
  return Object.keys(DESK_SAID.sessions).sort();
}
