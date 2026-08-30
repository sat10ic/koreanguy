import { useState } from "react";
import { Cell, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from "recharts";
import { useNavigate } from "react-router-dom";
import type { Candidate } from "../../data/fixtures";
import { LIFECYCLE_META, toneColor } from "../../lib/status";

/*
  The candidate scatter (manual V2 §4) — "the map of opportunity, the
  product's signature visual after the Quality Stack." x = Entry Timing,
  y = Stock Strength, bubble = Setup Quality, color = lifecycle stage.
*/
interface CandidateScatterProps {
  candidates: Candidate[];
}

export function CandidateScatter({ candidates }: CandidateScatterProps) {
  const [hovered, setHovered] = useState<string | null>(null);
  const navigate = useNavigate();

  const data = candidates.map((c) => ({
    ...c,
    x: c.entryTiming,
    y: c.stockStrength,
    z: c.setupQuality,
  }));

  return (
    <div className="relative h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
          <XAxis
            type="number"
            dataKey="x"
            name="Entry Timing"
            domain={[0, 100]}
            tick={{ fill: "var(--text-tertiary)", fontSize: 11 }}
            stroke="var(--border)"
            label={{ value: "Entry Timing →", position: "insideBottom", offset: -4, fill: "var(--text-tertiary)", fontSize: 11 }}
          />
          <YAxis
            type="number"
            dataKey="y"
            name="Stock Strength"
            domain={[0, 100]}
            tick={{ fill: "var(--text-tertiary)", fontSize: 11 }}
            stroke="var(--border)"
            label={{ value: "↑ Stock Strength", angle: -90, position: "insideLeft", fill: "var(--text-tertiary)", fontSize: 11 }}
          />
          <ZAxis type="number" dataKey="z" range={[80, 420]} />
          <Tooltip
            cursor={{ stroke: "var(--border-strong)", strokeDasharray: "3 3" }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const d = payload[0].payload as Candidate & { x: number; y: number; z: number };
              return (
                <div className="rounded-chip border border-border-strong bg-surface-3 px-2.5 py-2 text-caption">
                  <div className="font-semibold text-ink-primary">{d.symbol}</div>
                  <div className="text-ink-tertiary">
                    Stock {d.stockStrength} · Setup {d.setupQuality} · Entry {d.entryTiming}
                  </div>
                </div>
              );
            }}
          />
          <Scatter
            data={data}
            onMouseEnter={(d) => setHovered((d as unknown as { symbol: string }).symbol)}
            onMouseLeave={() => setHovered(null)}
            onClick={(d) => navigate(`/stock/${(d as unknown as { symbol: string }).symbol}`)}
            cursor="pointer"
          >
            {data.map((d) => {
              const color = toneColor(LIFECYCLE_META[d.lifecycle].tone);
              return (
                <Cell
                  key={`${d.symbol}-${d.setupType}-${d.dataSource}`}
                  fill={color}
                  fillOpacity={hovered && hovered !== d.symbol ? 0.25 : 0.55}
                  stroke={color}
                  strokeWidth={hovered === d.symbol ? 1.5 : 1}
                />
              );
            })}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
      <div className="pointer-events-none absolute right-2 top-1 flex gap-3 text-caption text-ink-muted">
        {Object.entries(LIFECYCLE_META).map(([key, meta]) => (
          <span key={key} className="flex items-center gap-1">
            <span className="h-1.5 w-1.5 rounded-full" style={{ background: toneColor(meta.tone) }} />
            {meta.label}
          </span>
        ))}
      </div>
    </div>
  );
}
