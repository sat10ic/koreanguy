import React from "react";
import { Panel, Tag, Empty } from "../ui";
import { fmtNum, classNames } from "../utils";
import { InfoDot } from "./Tooltip";

const PILLAR_META = [
  { key: "trend", label: "Trend", desc: "Equal-weight Nifty 500 above its 21-day average and rising — broad-market price uptrend" },
  { key: "momentum", label: "Momentum", desc: "Nifty 50 RSI not in overbought territory — buyers haven't exhausted themselves" },
  { key: "breadth", label: "Breadth", desc: "At least 45% of stocks trade above their 50-day average — wide participation" },
  { key: "volatility", label: "Volatility", desc: "Nifty within 3.2× ATR of its 21-day EMA — orderly tape, no panic moves" },
];

const REGIME_STYLE = {
  RISK_ON: {
    accent: "border-bull text-bull",
    chip: "bg-bull text-page",
    side: "Risk on the table",
  },
  CAUTION: {
    accent: "border-warn text-warn",
    chip: "bg-warn text-page",
    side: "Reduced size · 0.125% risk",
  },
  RISK_OFF: {
    accent: "border-bear text-bear",
    chip: "bg-bear text-page",
    side: "Signals suppressed",
  },
};

export default function RegimePanel({ regime }) {
  if (!regime || !regime.available) {
    return (
      <Panel title="Market Regime" testId="regime-panel">
        <Empty testId="regime-empty">
          No regime evaluated yet. Run the daily pipeline to compute today's
          state.
        </Empty>
      </Panel>
    );
  }

  const r = regime.regime || "—";
  const style = REGIME_STYLE[r] || REGIME_STYLE.CAUTION;
  const passed = regime.pillars_passed ?? 0;
  const riskPct = regime.risk_pct_override;

  return (
    <Panel
      title="Market Regime · Phase 1"
      testId="regime-panel"
      right={
        <div className="flex items-center gap-2">
          <InfoDot k="Regime" />
          <span className="font-mono text-[10px] uppercase tracking-overline text-textMuted">
            {regime.date}
          </span>
        </div>
      }
    >
      {/* Hero */}
      <div className={classNames("flex items-stretch border", style.accent)}>
        <div className="flex flex-col justify-between border-r border-borderDefault bg-page px-6 py-5">
          <div className="text-[10px] uppercase tracking-overline text-textMuted">
            Today's State
          </div>
          <div
            className={classNames(
              "mt-1 font-mono text-4xl font-semibold tracking-tighter",
              style.accent
            )}
            data-testid="regime-state"
          >
            {r}
          </div>
          <div className="mt-2 flex items-center gap-2 text-[11px] text-textSecondary">
            <span className={classNames("px-1.5 py-0.5 font-mono text-[10px]", style.chip)}>
              {passed}/4 pillars
            </span>
            <InfoDot k="Pillar" />
            <span>· {style.side}</span>
          </div>
        </div>

        {/* Pillars grid */}
        <div className="grid flex-1 grid-cols-2 md:grid-cols-4">
          {PILLAR_META.map(({ key, label, desc }) => {
            const p = regime.pillars?.[key];
            const ok = p?.pass;
            return (
              <div
                key={key}
                data-testid={`pillar-${key}`}
                className={classNames(
                  "flex flex-col justify-between border-l border-borderDefault px-4 py-4",
                  ok ? "bg-bull/5" : "bg-bear/5"
                )}
              >
                <div className="flex items-center justify-between">
                  <span className="text-[10px] uppercase tracking-overline text-textMuted">
                    {label}
                  </span>
                  <Tag color={ok ? "bull" : "bear"}>{ok ? "PASS" : "FAIL"}</Tag>
                </div>
                <div className="mt-3 truncate font-mono text-[11px] tnum text-textPrimary">
                  {p?.value || "—"}
                </div>
                <div className="mt-1 text-[10px] text-textMuted">{desc}</div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-1 text-[11px] text-textSecondary">
        <span>
          <span className="text-textMuted">risk_pct_override</span>{" "}
          <span className="font-mono text-textPrimary">
            {fmtNum((riskPct || 0) * 100, 4)}%
          </span>
        </span>
        <span>
          <span className="text-textMuted">methodology</span>{" "}
          <span className="font-mono text-textPrimary">Manas Arora · 4-Pillars</span>
        </span>
        <span>
          <span className="text-textMuted">universe</span>{" "}
          <span className="font-mono text-textPrimary">NSE Nifty 500</span>
        </span>
      </div>
    </Panel>
  );
}
