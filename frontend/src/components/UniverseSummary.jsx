import React, { useMemo, useState } from "react";
import { Panel, Empty } from "../ui";
import { fmtInt, fmtNum, classNames } from "../utils";

const VIEWS = [
  { key: "sectors", label: "Sector" },
  { key: "industries", label: "Industry" },
  { key: "basic_industries", label: "Basic" },
];

const FIELD = {
  sectors: "sector",
  industries: "industry",
  basic_industries: "basic_industry",
};

export default function UniverseSummary({ uni }) {
  const [view, setView] = useState("sectors");
  const items = useMemo(() => uni?.[view] || [], [uni, view]);

  if (!uni || !uni.available) {
    return (
      <Panel title="Universe · Breadth" testId="universe-panel">
        <Empty>Run pipeline to compute breadth + sector stats.</Empty>
      </Panel>
    );
  }

  const total = uni.total || 0;
  const bullPct = total ? (uni.bullish / total) * 100 : 0;
  const limit = view === "sectors" ? 8 : view === "industries" ? 10 : 12;

  return (
    <Panel
      title="Universe · Breadth & Sectors"
      testId="universe-panel"
      right={
        <div className="flex items-center gap-1">
          {VIEWS.map((v) => (
            <button
              key={v.key}
              onClick={() => setView(v.key)}
              data-testid={`uni-view-${v.key}`}
              className={classNames(
                "border px-2 py-0.5 font-mono text-[10px] uppercase tracking-overline transition-colors",
                view === v.key
                  ? "border-bull text-bull"
                  : "border-borderDefault text-textSecondary hover:text-textPrimary"
              )}
            >
              {v.label}
            </button>
          ))}
        </div>
      }
    >
      {/* Stat strip */}
      <div className="grid grid-cols-2 gap-2">
        <div className="border border-borderDefault px-3 py-2">
          <div className="text-[10px] uppercase tracking-overline text-textMuted">
            Bullish / Bearish
          </div>
          <div className="mt-1 flex items-baseline gap-2 font-mono">
            <span className="text-bull tnum">{fmtInt(uni.bullish)}</span>
            <span className="text-textMuted">/</span>
            <span className="text-bear tnum">{fmtInt(uni.bearish)}</span>
          </div>
          <div className="mt-2 h-1 w-full bg-borderDefault">
            <div
              className="h-full bg-bull"
              style={{ width: `${bullPct.toFixed(1)}%` }}
            />
          </div>
          <div className="mt-1 text-[10px] tnum text-textMuted">
            {fmtNum(bullPct, 1)}% above SMA50
          </div>
        </div>
        <div className="border border-borderDefault px-3 py-2">
          <div className="text-[10px] uppercase tracking-overline text-textMuted">
            Purple Dots Today
          </div>
          <div className="mt-1 font-mono text-2xl text-purpledot tnum">
            {fmtInt(uni.purple_dots_today)}
          </div>
          <div className="mt-1 text-[10px] text-textMuted">
            ≥5% move + heavy volume
          </div>
        </div>
        <div className="border border-borderDefault px-3 py-2">
          <div className="text-[10px] uppercase tracking-overline text-textMuted">
            Setup Pass
          </div>
          <div className="mt-1 font-mono text-2xl text-textPrimary tnum">
            {fmtInt(uni.setup_pass_count)}
          </div>
          <div className="mt-1 text-[10px] text-textMuted">
            Bread-and-butter trigger
          </div>
        </div>
        <div className="border border-borderDefault px-3 py-2">
          <div className="text-[10px] uppercase tracking-overline text-textMuted">
            Extended (Y / R)
          </div>
          <div className="mt-1 flex items-baseline gap-2 font-mono">
            <span className="text-warn tnum">{fmtInt(uni.extended_yellow)}</span>
            <span className="text-textMuted">/</span>
            <span className="text-bear tnum">{fmtInt(uni.extended_red)}</span>
          </div>
          <div className="mt-1 text-[10px] text-textMuted">
            5×/7× ATR from SMA50
          </div>
        </div>
      </div>

      {/* Breakdown */}
      <div className="mt-4">
        <div className="mb-2 flex items-center justify-between text-[10px] uppercase tracking-overline text-textMuted">
          <span>
            {view === "sectors" && "Sector Breadth"}
            {view === "industries" && "Industry Breadth"}
            {view === "basic_industries" && "Basic Industry Breadth"}
            {" · Top "}{Math.min(limit, items.length)}
          </span>
          <span className="font-mono text-textMuted">{items.length} groups</span>
        </div>
        <div className="space-y-1.5">
          {items.slice(0, limit).map((s) => {
            const name = s[FIELD[view]] || "—";
            const pct = s.count ? (s.bullish / s.count) * 100 : 0;
            return (
              <div
                key={name}
                data-testid={`${view}-row-${name}`}
                className="grid grid-cols-12 items-center gap-2 text-[11px]"
              >
                <div className="col-span-5 truncate text-textPrimary" title={name}>
                  {name}
                </div>
                <div className="col-span-5 h-1.5 bg-borderDefault">
                  <div
                    className={classNames(
                      "h-full",
                      pct >= 50 ? "bg-bull" : "bg-bear"
                    )}
                    style={{ width: `${pct.toFixed(1)}%` }}
                  />
                </div>
                <div className="col-span-2 text-right font-mono tnum text-textMuted">
                  {s.bullish}/{s.count}
                </div>
              </div>
            );
          })}
          {items.length === 0 && (
            <div className="py-4 text-center text-[11px] text-textMuted">No data for this view.</div>
          )}
        </div>
      </div>
    </Panel>
  );
}
