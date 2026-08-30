// Real point-in-time OHLCV history — wired 2026-08-30, unblocked by U-P0.3
// (InMemoryMarketStore.get_market_state, confirmed built and tested).
//
// Source of truth: unidesk/run_stock_history_export.py, which reads the real
// bhavcopy backlog (the same data unidesk/momentum/scan.py scans) and emits
// up to 130 real daily bars per symbol, strictly at-or-before the Tonight
// report's own session_date — no future leakage. This app is a static,
// build-time Vite bundle with no live fetch (nightly EOD desk, per
// unidesk/design/UI_BACKEND_INTEGRATION_PLAN.md), so the export is committed
// here as a build-time snapshot, same convention as tonight.ts.
//
// Only the 235 symbols that appear in the current Tonight report have real
// history. Every other symbol (illustrative fixtures, or a real candidate
// bhavcopy happened to have zero bars for) has none — getRealHistory returns
// undefined rather than a fabricated series, and the caller (StockChart) must
// fall back to the labelled-synthetic generateOhlc(), never silently blend.
import type { Bar } from "../lib/ohlc";
import stockHistoryJson from "./stock_history_2026-08-28.json";

interface RawSymbolHistory {
  sessions: string[];
  opens: number[];
  highs: number[];
  lows: number[];
  closes: number[];
  volumes: number[];
}

const RAW = stockHistoryJson as Record<string, RawSymbolHistory>;

export function getRealHistory(symbol: string): Bar[] | undefined {
  const h = RAW[symbol];
  if (!h || h.sessions.length === 0) return undefined;
  return h.sessions.map((time, i) => ({
    time,
    open: h.opens[i],
    high: h.highs[i],
    low: h.lows[i],
    close: h.closes[i],
    volume: h.volumes[i],
  }));
}
