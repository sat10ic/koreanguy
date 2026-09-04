import React, { useMemo, useState } from "react";
import { Panel, Empty } from "../ui";
import { fmtNum, fmtPct, classNames } from "../utils";
import { InfoDot } from "./Tooltip";

const GRADE_ORDER = [
  "A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-",
  "D+", "D", "D-", "E+", "E", "F", "G",
];

function gradeBg(g) {
  if (!g) return "bg-surface";
  if (g.startsWith("A")) return "bg-bull/15 hover:bg-bull/25 border-bull/40";
  if (g.startsWith("B")) return "bg-emerald-300/10 hover:bg-emerald-300/20 border-emerald-300/30";
  if (g.startsWith("C")) return "bg-warn/10 hover:bg-warn/20 border-warn/30";
  if (g.startsWith("D") || g.startsWith("E"))
    return "bg-orange-400/10 hover:bg-orange-400/20 border-orange-400/30";
  return "bg-bear/10 hover:bg-bear/20 border-bear/30";
}

export default function RSGridPanel({ data, onSymbol }) {
  const [filter, setFilter] = useState("all");

  const grades = data?.grades || {};
  const counts = data?.counts || {};

  const filtered = useMemo(() => {
    const out = {};
    for (const g of GRADE_ORDER) {
      const items = grades[g] || [];
      out[g] = items.filter((i) => {
        if (filter === "watchlist") return i.watchlist_member === 1;
        if (filter === "purpledot") return i.purple_dot === 1;
        if (filter === "extended") return i.extended_yellow === 1 || i.extended_red === 1;
        if (filter === "bullish") return i.bucket === "Bullish";
        return true;
      });
    }
    return out;
  }, [grades, filter]);

  if (!data || !data.available) {
    return (
      <Panel title="RS Grid · Universe">
        <Empty>Run pipeline to compute RS grades for the universe.</Empty>
      </Panel>
    );
  }

  return (
    <Panel
      testId="rsgrid-panel"
      title={
        <span className="inline-flex items-center gap-2">
          Relative Strength Grid · Nifty 500
          <InfoDot k="Grade" />
        </span>
      }
      right={
        <div className="flex items-center gap-1">
          {[
            ["all", "All"],
            ["bullish", "Bullish"],
            ["watchlist", "Watchlist"],
            ["purpledot", "PD"],
            ["extended", "Ext"],
          ].map(([k, l]) => (
            <button
              key={k}
              onClick={() => setFilter(k)}
              data-testid={`rsgrid-filter-${k}`}
              className={classNames(
                "border px-2 py-0.5 font-mono text-[10px] uppercase tracking-overline transition-colors",
                filter === k
                  ? "border-bull text-bull"
                  : "border-borderDefault text-textSecondary hover:text-textPrimary"
              )}
            >
              {l}
            </button>
          ))}
        </div>
      }
    >
      <div className="overflow-x-auto">
        <div className="grid grid-flow-col auto-cols-[150px] gap-px bg-borderDefault">
          {GRADE_ORDER.map((g) => {
            const items = filtered[g] || [];
            return (
              <div
                key={g}
                className="flex flex-col bg-page"
                data-testid={`rsgrid-col-${g}`}
              >
                <div className="border-b border-borderDefault bg-surface px-2 py-1.5">
                  <div className="flex items-center justify-between">
                    <span className={classNames(
                      "font-mono text-[12px] font-semibold",
                      g.startsWith("A") ? "text-bull" :
                      g.startsWith("B") ? "text-emerald-300" :
                      g.startsWith("C") ? "text-warn" :
                      g.startsWith("D") || g.startsWith("E") ? "text-orange-400" :
                      "text-bear"
                    )}>
                      {g}
                    </span>
                    <span className="font-mono text-[10px] tnum text-textMuted">
                      {counts[g] || 0}
                    </span>
                  </div>
                </div>
                <div className="flex-1 overflow-y-auto" style={{ maxHeight: 540 }}>
                  {items.length === 0 ? (
                    <div className="px-2 py-3 text-[10px] text-textMuted">—</div>
                  ) : (
                    items.map((it) => (
                      <button
                        key={it.symbol}
                        onClick={() => onSymbol?.(it.symbol)}
                        data-testid={`rsgrid-cell-${it.symbol}`}
                        className={classNames(
                          "group block w-full border-b border-l-2 px-2 py-1 text-left transition-colors",
                          gradeBg(g),
                          "border-b-borderSubtle"
                        )}
                      >
                        <div className="flex items-center justify-between">
                          <span className="truncate font-mono text-[11px] font-medium text-textPrimary">
                            {it.symbol}
                          </span>
                          <div className="flex items-center gap-1">
                            {it.watchlist_member === 1 && (
                              <span className="font-mono text-[10px] text-saffron" title="watchlist">★</span>
                            )}
                            {it.purple_dot === 1 && (
                              <span className="block h-1.5 w-1.5 bg-purpledot" title="purple dot" />
                            )}
                            {it.extended_red === 1 && (
                              <span className="block h-1.5 w-1.5 bg-bear" title="extended red" />
                            )}
                            {it.extended_yellow === 1 && it.extended_red !== 1 && (
                              <span className="block h-1.5 w-1.5 bg-warn" title="extended yellow" />
                            )}
                          </div>
                        </div>
                        <div className="mt-0.5 flex items-center justify-between text-[10px]">
                          <span className="font-mono tnum text-textMuted">
                            {fmtNum(it.close, 0)}
                          </span>
                          <span className={classNames(
                            "font-mono tnum",
                            it.ret_5d > 0 ? "text-bull" : it.ret_5d < 0 ? "text-bear" : "text-textMuted"
                          )}>
                            {fmtPct(it.ret_5d, 1)}
                          </span>
                        </div>
                      </button>
                    ))
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-[10px] uppercase tracking-overline text-textMuted">
        <span><span className="text-saffron">★</span> watchlist</span>
        <span><span className="inline-block h-1.5 w-1.5 bg-purpledot align-middle" /> purple dot</span>
        <span><span className="inline-block h-1.5 w-1.5 bg-warn align-middle" /> extended yellow</span>
        <span><span className="inline-block h-1.5 w-1.5 bg-bear align-middle" /> extended red</span>
      </div>
    </Panel>
  );
}
