import React from "react";
import { Panel, Empty } from "../ui";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

export default function HistoryChart({ rows, positionsStats, positionsSummary }) {
  const open = (positionsSummary?.PENDING_CONFIRM || 0) + (positionsSummary?.ACTIVE || 0);
  const totalExited = positionsStats?.total_exited || 0;

  const noData = !rows || rows.length === 0;

  return (
    <Panel
      testId="history-panel"
      title="30-Day Signal History"
      right={
        <div className="flex items-center gap-3 text-[10px] uppercase tracking-overline">
          <span className="text-textMuted">
            Open <span className="font-mono text-textPrimary">{open}</span>
          </span>
          <span className="text-textMuted">
            Exited <span className="font-mono text-textPrimary">{totalExited}</span>
          </span>
          <span className="text-textMuted">
            Hit Rate{" "}
            <span className="font-mono text-bull">
              {positionsStats?.hit_rate != null
                ? `${(positionsStats.hit_rate * 100).toFixed(1)}%`
                : "—"}
            </span>
          </span>
        </div>
      }
    >
      {noData ? (
        <div className="h-[180px]">
          <Empty>No historical signal data yet. Pipeline must run a few sessions to build history.</Empty>
        </div>
      ) : (
        <div className="h-[180px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={rows} margin={{ top: 10, right: 12, left: -10, bottom: 0 }}>
              <CartesianGrid stroke="#27272A" strokeDasharray="0" vertical={false} />
              <XAxis
                dataKey="date"
                stroke="#52525B"
                tick={{ fontSize: 10, fontFamily: "JetBrains Mono" }}
                tickLine={false}
                axisLine={{ stroke: "#27272A" }}
              />
              <YAxis
                stroke="#52525B"
                tick={{ fontSize: 10, fontFamily: "JetBrains Mono" }}
                tickLine={false}
                axisLine={{ stroke: "#27272A" }}
                width={28}
              />
              <Tooltip
                contentStyle={{
                  background: "#0a0a0a",
                  border: "1px solid #27272A",
                  fontFamily: "JetBrains Mono",
                  fontSize: 11,
                }}
                labelStyle={{ color: "#A1A1AA" }}
              />
              <Line
                type="monotone"
                dataKey="primary"
                stroke="#10B981"
                strokeWidth={1.5}
                dot={false}
                isAnimationActive={false}
              />
              <Line
                type="monotone"
                dataKey="secondary"
                stroke="#A1A1AA"
                strokeWidth={1.5}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="mt-2 flex items-center gap-4 text-[10px] uppercase tracking-overline text-textMuted">
        <span><span className="inline-block h-px w-5 bg-bull align-middle" /> Primary</span>
        <span><span className="inline-block h-px w-5 bg-textSecondary align-middle" /> Secondary</span>
      </div>
    </Panel>
  );
}
