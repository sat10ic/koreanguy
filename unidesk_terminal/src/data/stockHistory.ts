// Real point-in-time OHLCV history — auto-discovers every bundled
// stock_history_<date>.json (one per report session; bars strictly
// at-or-before that session — no future leakage between sessions).
// getRealHistory(symbol, session) prefers the session's own snapshot and
// falls back to another bundled snapshot when the symbol is absent; the
// caller discloses the last bar date wherever staleness matters. A symbol
// in no snapshot returns undefined; never a fabricated series.
import type { Bar } from "../lib/ohlc";

interface RawSymbolHistory {
  sessions: string[];
  opens: number[];
  highs: number[];
  lows: number[];
  closes: number[];
  volumes: number[];
}

const modules = import.meta.glob("./stock_history_*.json", { eager: true }) as Record<string, unknown>;

const SNAPSHOTS = Object.entries(modules)
  .map(([path, json]) => ({
    session: path.replace("./stock_history_", "").replace(".json", ""),
    symbols: json as Record<string, RawSymbolHistory>,
  }))
  .sort((a, b) => b.session.localeCompare(a.session));

function toBars(h: RawSymbolHistory): Bar[] {
  return h.sessions.map((time, i) => ({
    time,
    open: h.opens[i],
    high: h.highs[i],
    low: h.lows[i],
    close: h.closes[i],
    volume: h.volumes[i],
  }));
}

export function getRealHistory(symbol: string, session?: string): Bar[] | undefined {
  const ordered = session
    ? [...SNAPSHOTS].sort((a, b) => (a.session === session ? -1 : b.session === session ? 1 : 0))
    : SNAPSHOTS;
  for (const snap of ordered) {
    const h = snap.symbols[symbol];
    if (h && h.sessions.length > 0) return toBars(h);
  }
  return undefined;
}

/* ---- Trading calendar (A-2/A-3): union of session dates across every
   symbol in the NEWEST bundled snapshot. A single symbol can suspend or
   list late; the union is the exchange's actual trading calendar through
   that snapshot's session. Static build-time data, so computed once. ---- */
let _calendar: string[] | null = null;

export function tradingCalendar(): string[] {
  if (_calendar) return _calendar;
  const set = new Set<string>();
  if (SNAPSHOTS.length > 0) {
    for (const h of Object.values(SNAPSHOTS[0].symbols)) {
      for (const d of h.sessions) set.add(d);
    }
  }
  _calendar = [...set].sort();
  return _calendar;
}

/** Number of trading sessions strictly after `date` (up to the calendar's
 *  end, i.e. the newest bundled session). A call dated `date` has had its
 *  full 10-bar outcome horizon once this reaches 10. */
export function sessionsElapsedAfter(date: string): number {
  const cal = tradingCalendar();
  let n = 0;
  for (let i = cal.length - 1; i >= 0 && cal[i] > date; i--) n++;
  return n;
}

/** The newest session whose 10-bar outcome horizon has fully elapsed —
 *  calls dated on or before this are win/loss/flat-decided. */
export function settledCutoff(horizon = 10): string | null {
  const cal = tradingCalendar();
  return cal.length > horizon ? cal[cal.length - 1 - horizon] : null;
}
