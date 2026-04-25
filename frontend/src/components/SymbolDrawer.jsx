import React, { useEffect, useState } from "react";
import { endpoints } from "../api";
import { fmtNum, fmtPct, fmtInt, classNames, pnlClass } from "../utils";
import { Spinner, Button } from "../ui";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { X } from "lucide-react";

export default function SymbolDrawer({ symbol, onClose }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    setLoading(true);
    endpoints
      .symbol(symbol, 180)
      .then(setData)
      .finally(() => setLoading(false));
  }, [symbol]);

  const last = data?.bars && data.bars.length ? data.bars[data.bars.length - 1] : null;
  const first = data?.bars && data.bars.length ? data.bars[0] : null;
  const chg = last && first ? (last.close - first.close) / first.close : null;

  return (
    <div
      className="fixed inset-0 z-30 flex justify-end bg-page/70 backdrop-blur-sm"
      onClick={onClose}
      data-testid="symbol-drawer-overlay"
    >
      <aside
        onClick={(e) => e.stopPropagation()}
        className="flex h-full w-full max-w-[680px] flex-col border-l border-borderDefault bg-page fadein"
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
                label="180d Δ"
                value={fmtPct(chg)}
                accent={pnlClass(chg)}
                mono
              />
              <Stat label="ATR(14)" value={fmtNum(last?.atr14)} mono />
              <Stat label="ADV(20)" value={fmtInt(last?.adv20)} mono />
              <Stat label="SMA50" value={fmtNum(last?.sma50)} mono />
              <Stat label="SMA200" value={fmtNum(last?.sma200)} mono />
              <Stat label="RSI(14)" value={fmtNum(last?.rsi14, 1)} mono />
              <Stat
                label="PD 30d"
                value={fmtInt(last?.purple_dot_count_30d)}
                accent="text-purpledot"
                mono
              />
            </div>

            {/* Chart */}
            <div className="border-b border-borderDefault px-3 py-3">
              <div className="mb-2 text-[10px] uppercase tracking-overline text-textMuted">
                Close · SMA50 · SMA200 · 180 sessions
              </div>
              <div className="h-[260px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={data.bars} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                    <CartesianGrid stroke="#18181B" strokeDasharray="0" vertical={false} />
                    <XAxis dataKey="date" stroke="#52525B" tick={{ fontSize: 9, fontFamily: "JetBrains Mono" }} tickLine={false} axisLine={{ stroke: "#27272A" }} hide />
                    <YAxis stroke="#52525B" tick={{ fontSize: 9, fontFamily: "JetBrains Mono" }} tickLine={false} axisLine={{ stroke: "#27272A" }} width={45} domain={["auto", "auto"]} />
                    <Tooltip contentStyle={{ background: "#0a0a0a", border: "1px solid #27272A", fontFamily: "JetBrains Mono", fontSize: 10 }} labelStyle={{ color: "#A1A1AA" }} />
                    <Line type="monotone" dataKey="close" stroke="#F4F4F5" strokeWidth={1.5} dot={false} isAnimationActive={false} />
                    <Line type="monotone" dataKey="sma50" stroke="#10B981" strokeWidth={1} dot={false} strokeDasharray="2 2" isAnimationActive={false} />
                    <Line type="monotone" dataKey="sma200" stroke="#A1A1AA" strokeWidth={1} dot={false} strokeDasharray="3 3" isAnimationActive={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
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
                    <Th align="right">Volume</Th>
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
                      <Td align="right" mono className="text-textMuted">{fmtInt(b.volume)}</Td>
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
