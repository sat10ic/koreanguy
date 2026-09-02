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
