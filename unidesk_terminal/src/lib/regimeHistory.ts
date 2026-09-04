// H1-10: regime history strip data. Generated from the real archived
// reports by unidesk/run_export_regime_history.py — one row per session.
//
// Two regimes per row:
//  - `regime`: what the classifier actually said at the time (null when the
//    session predates the classifier and carries no classification).
//  - `regimeReplayed`: the same R0 classifier deterministically replayed
//    over the stored breadth series (labelled as a replay wherever shown).
export interface RegimeHistoryRow {
  date: string;
  regime: string | null;
  regime_note: string;
  regime_built: boolean;
  pct_above_ema50: number | null;
  pct_above_ema21?: number | null;
  near_highs_pct?: number | null;
  near_lows_pct?: number | null;
  regime_replayed: string | null;
}

import regimeHistoryJson from "../data/regime_history.json";

interface RegimeHistoryFile {
  source: string;
  generator: string;
  sessions: RegimeHistoryRow[];
}

const FILE = regimeHistoryJson as unknown as RegimeHistoryFile;

/** Up to `count` sessions ending at (and including) `sessionDate`. */
export function regimeHistoryBefore(sessionDate: string, count = 20): RegimeHistoryRow[] {
  const idx = FILE.sessions.findIndex((s) => s.date >= sessionDate);
  const end = idx === -1 ? FILE.sessions.length : idx + 1;
  return FILE.sessions.slice(Math.max(0, end - count), end);
}

// E-3: rehydrate in place from the desk server's export.
export function hydrateRegimeHistory(file: RegimeHistoryFile): void {
  Object.assign(FILE, file);
}
