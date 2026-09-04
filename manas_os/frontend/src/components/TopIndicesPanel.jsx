import { useEffect, useMemo, useState } from "react";
import { getRegimeIndices } from "../api.js";
import Read from "./Read.jsx";

const TIMEFRAMES = ["1d", "1w", "1m", "3m", "6m"];

export default function TopIndicesPanel() {
  const [timeframe, setTimeframe] = useState("1m");
  const [state, setState] = useState({ loading: true, error: null, data: null });

  useEffect(() => {
    let cancelled = false;
    getRegimeIndices()
      .then((data) => !cancelled && setState({ loading: false, error: null, data }))
      .catch((error) => !cancelled && setState({ loading: false, error: error.message, data: null }));
    return () => {
      cancelled = true;
    };
  }, []);

  const rows = useMemo(() => {
    const indices = state.data?.indices || [];
    return [...indices]
      .filter((item) => item.returns?.[timeframe] != null)
      .sort((a, b) => b.returns[timeframe] - a.returns[timeframe])
      .slice(0, 12);
  }, [state.data, timeframe]);

  return (
    <section data-testid="top-indices-panel" className="mt-4 border border-hairline bg-card p-3">
      <header className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <div className="font-mono text-[12px] font-bold uppercase tracking-overline text-ink">
            Top indices
          </div>
          <div className="font-sans text-[11px] text-ink3">
            Cached sector-index returns from Fyers index history.
          </div>
        </div>
        <div className="flex flex-wrap gap-1">
          {TIMEFRAMES.map((tf) => (
            <button
              key={tf}
              onClick={() => setTimeframe(tf)}
              data-testid={`indices-timeframe-${tf}`}
              className={
                "border px-2 py-0.5 font-mono text-[10px] uppercase tracking-overline transition-colors " +
                (timeframe === tf ? "border-info text-info" : "border-hairline text-ink2 hover:text-ink")
              }
            >
              {tf}
            </button>
          ))}
        </div>
      </header>

      {state.loading ? (
        <div className="font-mono text-[11px] text-ink3">loading index returns...</div>
      ) : state.error ? (
        <div className="font-mono text-[11px] text-bear">{state.error}</div>
      ) : !state.data?.available ? (
        <Read band="muted" verdict="NO INDEX DATA">
          Connect Fyers and run update to latest so sector_index_prices can populate.
        </Read>
      ) : rows.length === 0 ? (
        <Read band="muted" verdict="NOT ENOUGH HISTORY">
          No {timeframe.toUpperCase()} return is available yet for cached index rows.
        </Read>
      ) : (
        <ul className="space-y-1.5">
          {rows.map((row) => {
            const value = row.returns[timeframe];
            const positive = value >= 0;
            const width = Math.min(100, Math.abs(value) / 20 * 100);
            return (
              <li key={row.symbol} className="grid grid-cols-12 items-center gap-2 px-1 py-1 text-[12px]">
                <span className="col-span-4 truncate font-mono text-ink" title={row.symbol}>
                  {row.name}
                </span>
                <div className="col-span-6 h-2 rounded-sm bg-hairline">
                  <div
                    className={"h-full rounded-sm " + (positive ? "bg-bull" : "bg-bear")}
                    style={{ width: `${width}%` }}
                  />
                </div>
                <span className={"col-span-2 text-right font-mono tabular-nums " + (positive ? "text-bull" : "text-bear")}>
                  {fmtPct(value)}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

function fmtPct(value) {
  if (value == null) return "-";
  return `${value > 0 ? "+" : ""}${Number(value).toFixed(1)}%`;
}
