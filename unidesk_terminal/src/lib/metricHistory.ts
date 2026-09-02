// Per-symbol metric history from the archived nightly reports
// (unidesk/run_export_metric_history.py). Powers the audit's temporal
// features: RS Δ1D, RS trend sparkline, and the SMF-style accumulation
// view (NOW / PREV / 5D avg / 10D avg / streak / trend). Only real
// observations — a symbol absent from a session has no point that day.
import historyJson from "../data/metric_history.json";

type Series = [date: string, value: number][];

interface MetricHistoryFile {
  source: string;
  generator: string;
  sessions: string[];
  symbols: Record<string, {
    rs?: Series; act?: Series; dlv?: Series; rvol?: Series; close?: Series;
  }>;
}

const FILE = historyJson as unknown as MetricHistoryFile;

export function metricSeries(symbol: string, key: "rs" | "act" | "dlv" | "rvol" | "close"): Series {
  return FILE.symbols[symbol]?.[key] ?? [];
}

function latest(series: Series): number | null {
  return series.length ? series[series.length - 1][1] : null;
}

function avgLast(series: Series, n: number): number | null {
  if (!series.length) return null;
  const slice = series.slice(-n).map(([, v]) => v);
  return slice.reduce((a, b) => a + b, 0) / slice.length;
}

/** Consecutive most-recent sessions (excluding the first point) where the
 *  metric moved in one direction. Returns e.g. "3D ↑". */
function streakOf(series: Series): string {
  if (series.length < 3) return "—";
  let dir = 0;
  let count = 0;
  for (let i = series.length - 1; i > 0; i--) {
    const d = series[i][1] - series[i - 1][1];
    if (d === 0) break;
    const step = d > 0 ? 1 : -1;
    if (dir === 0) dir = step;
    else if (step !== dir) break;
    count += 1;
  }
  if (!dir || count === 0) return "—";
  return `${count}D ${dir > 0 ? "↑" : "↓"}`;
}

export interface AccTemporal {
  now: number | null;
  prev: number | null;
  avg5: number | null;
  avg10: number | null;
  streak: string;
  trend: number[];
}

/** SMF-style temporal view (spec §15.9) for a metric series. */
export function temporalFor(symbol: string, key: "act" | "dlv" | "rs"): AccTemporal {
  const series = metricSeries(symbol, key);
  const values = series.map(([, v]) => v);
  return {
    now: latest(series),
    prev: series.length >= 2 ? series[series.length - 2][1] : null,
    avg5: avgLast(series, 5),
    avg10: avgLast(series, 10),
    streak: streakOf(series),
    trend: values.slice(-10),
  };
}

/** RS change vs the prior archived session for this symbol (real only). */
export function rsDelta1D(symbol: string, rsNow: number | null | undefined): number | null {
  if (rsNow == null) return null;
  const series = metricSeries(symbol, "rs");
  if (series.length < 2) return null;
  const prev = series[series.length - 2][1];
  return rsNow - prev;
}

/** Last 10 RS observations for the trend sparkline. */
export function rsTrend(symbol: string): number[] {
  return metricSeries(symbol, "rs").map(([, v]) => v).slice(-10);
}
