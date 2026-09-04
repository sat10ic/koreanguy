import React, { useMemo, useState } from "react";
import { Panel, Empty } from "../ui";
import { fmtInt, fmtNum, classNames } from "../utils";
import { InfoDot } from "./Tooltip";
import StockListModal from "./StockListModal";
import { ChevronRight } from "lucide-react";

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

export default function UniverseSummary({ uni, onSymbol }) {
  const [view, setView] = useState("sectors");
  const [modal, setModal] = useState(null); // { title, subtitle, filter }
  const items = useMemo(() => uni?.[view] || [], [uni, view]);
  const [showAll, setShowAll] = useState(false);

  if (!uni || !uni.available) {
    return (
      <Panel title="Universe · Breadth" testId="universe-panel">
        <Empty>Run pipeline to compute breadth + sector stats.</Empty>
      </Panel>
    );
  }

  const total = uni.total || 0;
  const bullPct = total ? (uni.bullish / total) * 100 : 0;
  const limit = showAll
    ? items.length
    : view === "sectors"
      ? 8
      : view === "industries"
        ? 10
        : 12;

  const openModal = (cfg) => setModal(cfg);

  return (
    <Panel
      title="Universe · Breadth & Sectors"
      testId="universe-panel"
      right={
        <div className="flex items-center gap-1">
          {VIEWS.map((v) => (
            <button
              key={v.key}
              onClick={() => {
                setView(v.key);
                setShowAll(false);
              }}
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
      {/* Stat strip — every card is now clickable */}
      <div className="grid grid-cols-2 gap-2">
        <ClickableCard
          testId="card-bullish-bearish"
          onClick={() =>
            openModal({
              title: "Bullish stocks today",
              subtitle: "Closing above the 50-day moving average",
              filter: { bucket: "Bullish" },
            })
          }
        >
          <div className="flex items-center gap-1 text-[10px] uppercase tracking-overline text-textMuted">
            <span>Bullish / Bearish</span>
            <InfoDot k="Bucket" />
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
            {fmtNum(bullPct, 1)}% above 50-DMA
          </div>
        </ClickableCard>

        <ClickableCard
          testId="card-purple-dots"
          onClick={() =>
            openModal({
              title: "Purple Dot stocks today",
              subtitle: "Closed up ≥5% on heavy volume — institutional buying signal",
              filter: { purple_dot_only: true },
            })
          }
        >
          <div className="flex items-center gap-1 text-[10px] uppercase tracking-overline text-textMuted">
            <span>Purple Dots Today</span>
            <InfoDot k="PD" />
          </div>
          <div className="mt-1 font-mono text-2xl text-purpledot tnum">
            {fmtInt(uni.purple_dots_today)}
          </div>
          <div className="mt-1 flex items-center justify-between text-[10px] text-textMuted">
            <span>≥5% move + heavy volume</span>
            <ChevronRight size={11} className="text-purpledot" />
          </div>
        </ClickableCard>

        <ClickableCard
          testId="card-setup-pass"
          onClick={() =>
            openModal({
              title: "Bread-and-Butter setups today",
              subtitle: "Strong-RS stocks pulling back to 50-DMA with volume contraction + green confirmation",
              filter: { setup_only: true },
            })
          }
        >
          <div className="flex items-center gap-1 text-[10px] uppercase tracking-overline text-textMuted">
            <span>Setup Pass</span>
            <InfoDot k="Setup" />
          </div>
          <div className="mt-1 font-mono text-2xl text-textPrimary tnum">
            {fmtInt(uni.setup_pass_count)}
          </div>
          <div className="mt-1 flex items-center justify-between text-[10px] text-textMuted">
            <span>Bread-and-butter trigger</span>
            <ChevronRight size={11} className="text-bull" />
          </div>
        </ClickableCard>

        <ClickableCard
          testId="card-extended"
          onClick={() =>
            openModal({
              title: "Extended stocks (avoid fresh longs)",
              subtitle: "Trading 5–7× ATR above the 50-day average — high mean-reversion risk",
              filter: { bucket: "Bullish", sort_by: "rs_score", sort_desc: true, limit: 100 },
            })
          }
        >
          <div className="flex items-center gap-1 text-[10px] uppercase tracking-overline text-textMuted">
            <span>Extended (Y / R)</span>
            <InfoDot k="Extended" />
          </div>
          <div className="mt-1 flex items-baseline gap-2 font-mono">
            <span className="text-warn tnum">{fmtInt(uni.extended_yellow)}</span>
            <span className="text-textMuted">/</span>
            <span className="text-bear tnum">{fmtInt(uni.extended_red)}</span>
          </div>
          <div className="mt-1 text-[10px] text-textMuted">
            5×/7× ATR from 50-DMA
          </div>
        </ClickableCard>
      </div>

      {/* Breakdown */}
      <div className="mt-4">
        <div className="mb-2 flex items-center justify-between text-[10px] uppercase tracking-overline text-textMuted">
          <span>
            {view === "sectors" && "Sector Breadth"}
            {view === "industries" && "Industry Breadth"}
            {view === "basic_industries" && "Basic Industry Breadth"}
            {" · "}
            {showAll
              ? `All ${items.length}`
              : `Top ${Math.min(limit, items.length)}`}
          </span>
          <div className="flex items-center gap-3">
            <span className="font-mono text-textMuted">{items.length} groups</span>
            {items.length > limit && !showAll && (
              <button
                data-testid="uni-show-all"
                onClick={() => setShowAll(true)}
                className="font-mono text-bull hover:text-textPrimary"
              >
                Show all
              </button>
            )}
            {showAll && (
              <button
                data-testid="uni-show-less"
                onClick={() => setShowAll(false)}
                className="font-mono text-textMuted hover:text-textPrimary"
              >
                Collapse
              </button>
            )}
          </div>
        </div>
        <div className="space-y-1.5">
          {items.slice(0, limit).map((s) => {
            const name = s[FIELD[view]] || "—";
            const pct = s.count ? (s.bullish / s.count) * 100 : 0;
            const filterKey = FIELD[view];
            return (
              <button
                key={name}
                data-testid={`${view}-row-${name}`}
                onClick={() =>
                  openModal({
                    title: `${name}`,
                    subtitle: `${s.count} stocks · ${s.bullish} bullish · ${s.purple_dots || 0} purple dots`,
                    filter: { [filterKey]: name },
                  })
                }
                className="grid w-full grid-cols-12 items-center gap-2 border border-transparent px-1 py-1 text-left text-[11px] transition-colors hover:border-borderDefault hover:bg-surfaceHover"
              >
                <div
                  className="col-span-5 flex items-center gap-1.5 truncate text-textPrimary"
                  title={name}
                >
                  <ChevronRight
                    size={10}
                    className="shrink-0 text-textMuted"
                  />
                  <span className="truncate">{name}</span>
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
              </button>
            );
          })}
          {items.length === 0 && (
            <div className="py-4 text-center text-[11px] text-textMuted">
              No data for this view.
            </div>
          )}
        </div>
      </div>

      <StockListModal
        open={!!modal}
        title={modal?.title}
        subtitle={modal?.subtitle}
        filter={modal?.filter}
        onClose={() => setModal(null)}
        onSymbol={onSymbol}
      />
    </Panel>
  );
}

function ClickableCard({ children, onClick, testId }) {
  return (
    <button
      type="button"
      data-testid={testId}
      onClick={onClick}
      className="group border border-borderDefault px-3 py-2 text-left transition-all hover:border-bull/60 hover:bg-surfaceHover"
    >
      {children}
    </button>
  );
}
