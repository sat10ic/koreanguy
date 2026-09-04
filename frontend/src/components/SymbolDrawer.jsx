import React, { useEffect, useState } from "react";
import { endpoints } from "../api";
import { fmtNum, fmtPct, fmtInt, classNames, pnlClass } from "../utils";
import { Spinner, Button } from "../ui";
import { X } from "lucide-react";
import { InfoDot } from "./Tooltip";
import LightweightChart from "./LightweightChart";

export default function SymbolDrawer({ symbol, onClose }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    setLoading(true);
    endpoints
      .symbol(symbol, 240)
      .then(setData)
      .finally(() => setLoading(false));
  }, [symbol]);

  const last = data?.bars && data.bars.length ? data.bars[data.bars.length - 1] : null;
  const first = data?.bars && data.bars.length ? data.bars[0] : null;
  const chg = last && first ? (last.close - first.close) / first.close : null;
  const purpleDays = (data?.bars || []).filter((b) => b.purple_dot === 1).length;

  return (
    <div
      className="fixed inset-0 z-30 flex justify-end bg-page/70 backdrop-blur-sm"
      onClick={onClose}
      data-testid="symbol-drawer-overlay"
    >
      <aside
        onClick={(e) => e.stopPropagation()}
        className="flex h-full w-full max-w-[820px] flex-col border-l border-borderDefault bg-page fadein"
        data-testid="symbol-drawer"
      >
        <header className="flex items-center justify-between border-b border-borderDefault px-5 py-3">
          <div className="flex items-center gap-3">
            <span className="font-mono text-lg font-semibold tracking-tight">
              {symbol}
            </span>
            {data?.meta?.name && (
              <span className="hidden text-[12px] text-textSecondary md:inline">
                {data.meta.name}
              </span>
            )}
            {data?.meta?.sector && (
              <span className="border border-borderDefault px-2 py-0.5 text-[10px] uppercase tracking-overline text-textMuted">
                {data.meta.sector}
              </span>
            )}
          </div>
          <Button variant="ghost" onClick={onClose} testId="symbol-drawer-close">
            <X size={12} /> Close
          </Button>
        </header>

        {loading ? (
          <div className="flex flex-1 items-center justify-center">
            <Spinner label={`fetching ${symbol}`} />
          </div>
        ) : !data?.available ? (
          <div className="flex-1 px-5 py-12 text-center text-textMuted">
            <div className="font-mono text-[11px] uppercase tracking-overline">
              No data found for {symbol}.
            </div>
            <div className="mt-2 text-[12px]">
              Run the pipeline to populate OHLCV history.
            </div>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto">
            {/* Stat strip */}
            <div className="grid grid-cols-4 gap-px border-b border-borderDefault bg-borderDefault">
              <Stat label="Close" value={fmtNum(last?.close)} mono />
              <Stat
                label="240d Δ"
                value={fmtPct(chg)}
                accent={pnlClass(chg)}
                mono
              />
              <Stat
                label={<TermLabel k="ADR">ADR%(14)</TermLabel>}
                value={last?.adr14_pct != null ? `${fmtNum(last.adr14_pct, 2)}%` : "—"}
                mono
              />
              <Stat label="ATR(14)" value={fmtNum(last?.atr14)} mono />
              <Stat label="SMA50" value={fmtNum(last?.sma50)} mono />
              <Stat label="SMA200" value={fmtNum(last?.sma200)} mono />
              <Stat label="RSI(14)" value={fmtNum(last?.rsi14, 1)} mono />
              <Stat
                label={<TermLabel k="BF">BF·30d</TermLabel>}
                value={last?.bf_score_30d_max != null ? fmtNum(last.bf_score_30d_max, 1) : "—"}
                accent="text-purpledot"
                mono
                sub={`${purpleDays} purple days`}
              />
            </div>

            {/* TradingView lightweight-charts canvas */}
            <div className="border-b border-borderDefault px-3 py-3">
              <div className="mb-2 flex items-center justify-between">
                <div className="text-[10px] uppercase tracking-overline text-textMuted">
                  Candles · SMA20 / 50 / 200 · Purple Dots ·
                  <span className="ml-1 text-textSecondary">
                    {data.bars.length} sessions
                  </span>
                </div>
                <Legend />
              </div>
              <LightweightChart bars={data.bars} height={340} />
            </div>

            {/* Recent bars */}
            <div className="px-3 py-3">
              <div className="mb-2 text-[10px] uppercase tracking-overline text-textMuted">
                Recent 12 Sessions
              </div>
              <table className="w-full text-[11px]">
                <thead>
                  <tr>
                    <Th>Date</Th>
                    <Th align="right">Open</Th>
                    <Th align="right">High</Th>
                    <Th align="right">Low</Th>
                    <Th align="right">Close</Th>
                    <Th align="right">Δ%</Th>
                    <Th align="right">Vol·×</Th>
                    <Th align="right">PD</Th>
                  </tr>
                </thead>
                <tbody>
                  {data.bars.slice(-12).reverse().map((b) => (
                    <tr key={b.date}>
                      <Td><span className="font-mono text-textSecondary">{b.date}</span></Td>
                      <Td align="right" mono>{fmtNum(b.open)}</Td>
                      <Td align="right" mono>{fmtNum(b.high)}</Td>
                      <Td align="right" mono>{fmtNum(b.low)}</Td>
                      <Td align="right" mono>{fmtNum(b.close)}</Td>
                      <Td align="right" mono className={pnlClass(b.ret_1d)}>
                        {fmtPct(b.ret_1d, 2)}
                      </Td>
                      <Td align="right" mono className="text-textMuted">
                        {b.vol_ratio_20 != null ? `${fmtNum(b.vol_ratio_20, 1)}×` : "—"}
                      </Td>
                      <Td align="right">
                        {b.purple_dot === 1 ? (
                          <span
                            className="inline-block h-1.5 w-1.5 bg-purpledot"
                            title="Purple dot — ≥5% move on heavy volume"
                          />
                        ) : (
                          <span className="text-textMuted">—</span>
                        )}
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </aside>
    </div>
  );
}

function Legend() {
  return (
    <div className="flex items-center gap-3 text-[10px] uppercase tracking-overline text-textMuted">
      <span className="flex items-center gap-1">
        <span className="block h-0.5 w-3 bg-amber-500" /> SMA20
      </span>
      <span className="flex items-center gap-1">
        <span className="block h-0.5 w-3 bg-bull" /> SMA50
      </span>
      <span className="flex items-center gap-1">
        <span className="block h-0.5 w-3 bg-textMuted" /> SMA200
      </span>
      <span className="flex items-center gap-1">
        <span className="block h-1.5 w-1.5 rounded-full bg-purpledot" /> Purple Dot
      </span>
    </div>
  );
}

function TermLabel({ k, children }) {
  return (
    <span className="inline-flex items-center gap-1">
      {children}
      <InfoDot k={k} />
    </span>
  );
}

function Stat({ label, value, sub, mono, accent }) {
  return (
    <div className="bg-surface px-3 py-2">
      <div className="text-[9px] uppercase tracking-overline text-textMuted">{label}</div>
      <div className={classNames("mt-0.5", mono ? "font-mono tnum" : "", accent || "text-textPrimary")}>
        {value}
      </div>
      {sub && <div className="text-[9px] text-textMuted">{sub}</div>}
    </div>
  );
}

function Th({ children, align = "left" }) {
  return (
    <th
      className={classNames(
        "border-b border-borderDefault px-2 py-1.5 text-[9px] uppercase tracking-overline text-textMuted",
        align === "right" ? "text-right" : "text-left"
      )}
    >
      {children}
    </th>
  );
}

function Td({ children, align = "left", mono = false, className }) {
  return (
    <td
      className={classNames(
        "border-b border-borderSubtle px-2 py-1.5",
        align === "right" ? "text-right" : "text-left",
        mono ? "font-mono tnum" : "",
        className
      )}
    >
      {children}
    </td>
  );
}
