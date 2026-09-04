import React, { useEffect, useState } from "react";
import { Panel, GradePill, Tag } from "../ui";
import { fmtNum, fmtPct, classNames } from "../utils";
import { endpoints } from "../api";
import { InfoDot } from "./Tooltip";
import { Zap, ChevronRight, TrendingUp } from "lucide-react";

/**
 * Two-track horizontal ribbon shown above the Candidates panels.
 *
 * Track A — "Buying-Force Leaders": top-N stocks ranked by today's
 *   `buying_force_score` (positive ROC × volume_ratio_20). Surfaces
 *   stocks where institutional buying is hitting *today*, regardless
 *   of whether they pass the strict bread-and-butter setup.
 *
 * Track B — "Momentum Composite": ranks by a blended score
 *   sector_rs_pct × adr14_pct × bf_score_30d_max. Picks the running
 *   leaders that show sustained edge, not just one-day spikes.
 *
 * Click any tile → opens SymbolDrawer.
 */
export default function MomentumRibbon({ onSymbol }) {
  const [bf, setBf] = useState([]);
  const [mom, setMom] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([
      // BF leaders today (positive ROC * vol_ratio_20).
      endpoints
        .screen({
          sort_by: "buying_force_score",
          sort_desc: true,
          limit: 200,
        })
        .catch(() => ({ rows: [] })),
      // Momentum composite — pull the broader pool then rank locally.
      endpoints
        .screen({ sort_by: "rs_score", sort_desc: true, limit: 200 })
        .catch(() => ({ rows: [] })),
    ]).then(([bfData, momData]) => {
      if (cancelled) return;
      const bfTop = (bfData?.rows || [])
        .filter((r) => (r.buying_force_score ?? 0) > 0)
        .slice(0, 10);
      const momScored = (momData?.rows || [])
        .map((r) => ({
          ...r,
          composite:
            (r.sector_rs_pct ?? 0) *
            (r.adr14_pct ?? 0) *
            (r.bf_score_30d_max ?? 0),
        }))
        .filter((r) => r.composite > 0)
        .sort((a, b) => b.composite - a.composite)
        .slice(0, 10);
      setBf(bfTop);
      setMom(momScored);
      setLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) return null;
  if (!bf.length && !mom.length) return null;

  return (
    <div className="space-y-3">
      <Panel
        testId="bf-leaders-panel"
        title={
          <span className="inline-flex items-center gap-2">
            <Zap size={12} className="text-purpledot" />
            Buying-Force Leaders Today
            <InfoDot k="BF" />
          </span>
        }
        right={
          <span className="font-mono text-[10px] uppercase tracking-overline text-textMuted">
            ROC · Vol Ratio · live
          </span>
        }
      >
        {bf.length === 0 ? (
          <Empty>No positive buying-force prints today — quiet tape.</Empty>
        ) : (
          <RibbonRow rows={bf} kind="bf" onSymbol={onSymbol} />
        )}
      </Panel>

      <Panel
        testId="momentum-leaders-panel"
        title={
          <span className="inline-flex items-center gap-2">
            <TrendingUp size={12} className="text-bull" />
            Momentum Composite · Sect-RS × ADR × BF·30d
          </span>
        }
        right={
          <span className="font-mono text-[10px] uppercase tracking-overline text-textMuted">
            sustained leaders
          </span>
        }
      >
        {mom.length === 0 ? (
          <Empty>Need pipeline data to rank momentum.</Empty>
        ) : (
          <RibbonRow rows={mom} kind="mom" onSymbol={onSymbol} />
        )}
      </Panel>
    </div>
  );
}

function RibbonRow({ rows, kind, onSymbol }) {
  return (
    <div className="overflow-x-auto">
      <div className="flex gap-2">
        {rows.map((r, i) => (
          <Tile key={r.symbol} row={r} rank={i + 1} kind={kind} onSymbol={onSymbol} />
        ))}
      </div>
    </div>
  );
}

function Tile({ row, rank, kind, onSymbol }) {
  const r = row;
  const score = kind === "bf" ? r.buying_force_score : r.composite;
  const label = kind === "bf" ? "BF·today" : "Composite";
  return (
    <button
      type="button"
      onClick={() => onSymbol?.(r.symbol)}
      data-testid={`${kind}-tile-${r.symbol}`}
      className="group min-w-[180px] flex-shrink-0 border border-borderDefault bg-surface px-3 py-2 text-left transition-all hover:border-bull/60 hover:bg-surfaceHover"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="font-mono text-[10px] text-textMuted">#{rank}</span>
          <span className="font-mono text-[13px] font-semibold text-textPrimary">
            {r.symbol}
          </span>
        </div>
        <GradePill grade={r.grade} />
      </div>
      <div className="mt-1 truncate text-[10px] text-textMuted" title={r.sector}>
        {r.sector || "—"}
      </div>
      <div className="mt-2 flex items-baseline justify-between">
        <div>
          <div className="text-[9px] uppercase tracking-overline text-textMuted">
            {label}
          </div>
          <div
            className={classNames(
              "font-mono tnum text-[14px]",
              kind === "bf" ? "text-purpledot" : "text-bull"
            )}
          >
            {fmtNum(score, 1)}
          </div>
        </div>
        <div className="text-right">
          <div className="text-[9px] uppercase tracking-overline text-textMuted">
            Sect·RS
          </div>
          <div className="font-mono tnum text-[11px] text-textPrimary">
            {r.sector_rs_pct != null ? fmtPct(r.sector_rs_pct, 0) : "—"}
          </div>
        </div>
      </div>
      <div className="mt-1.5 flex items-center justify-between border-t border-borderSubtle pt-1.5 text-[10px]">
        <span className="font-mono text-textMuted">
          ADR{" "}
          <span className="text-textPrimary tnum">
            {r.adr14_pct != null ? `${fmtNum(r.adr14_pct, 1)}%` : "—"}
          </span>
        </span>
        <span className="font-mono text-textMuted">
          {r.purple_dot === 1 && <Tag color="purple" className="mr-1">PD</Tag>}
          {r.bucket === "Bullish" && <ChevronRight size={10} className="inline text-bull" />}
        </span>
      </div>
    </button>
  );
}

function Empty({ children }) {
  return (
    <div className="border border-dashed border-borderDefault px-3 py-3 text-center text-[11px] text-textMuted">
      {children}
    </div>
  );
}
