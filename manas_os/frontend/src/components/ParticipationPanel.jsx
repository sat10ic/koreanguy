import { useEffect, useState } from "react";
import { getBreadthHistory } from "../api.js";
import InfoDot from "./InfoDot.jsx";
import Read from "./Read.jsx";

/**
 * ParticipationPanel — GAP 2. One small chart, exactly two labelled lines:
 * pct_above_20dma (short-term participation) and pct_above_50dma (long-term
 * participation) over the last ~60 sessions, y-axis fixed 0-100%, legend,
 * plus a generated <Read> line comparing the two trends. Placed after the
 * MBI section on the Regime screen (design §1.6 verdict-layer pattern —
 * every data block gets exactly one <Read>).
 */
const DAYS = 60;

export default function ParticipationPanel() {
  const [state, setState] = useState({ loading: true, error: null, rows: [] });

  useEffect(() => {
    let cancelled = false;
    setState({ loading: true, error: null, rows: [] });
    getBreadthHistory(DAYS)
      .then((d) => !cancelled && setState({ loading: false, error: null, rows: d?.rows || [] }))
      .catch((e) => !cancelled && setState({ loading: false, error: e.message, rows: [] }));
    return () => {
      cancelled = true;
    };
  }, []);

  if (state.loading) return <PanelSkeleton />;
  if (state.error) {
    return (
      <EmptyBlock title="Couldn't reach the API">
        Make sure the backend is running: <code>python -m manas_os.api</code>
      </EmptyBlock>
    );
  }
  const rows = state.rows.filter((r) => r.pct_above_20dma != null || r.pct_above_50dma != null);
  if (rows.length === 0) {
    return (
      <EmptyBlock title="No participation data yet">
        Run the pipeline to populate:{" "}
        <code>python manas.py run-eod --date YYYY-MM-DD</code>
      </EmptyBlock>
    );
  }

  const readLine = buildReadLine(rows);

  return (
    <section data-testid="participation-panel" className="mt-4 border border-hairline bg-card p-3">
      <div className="mb-2">
        <span className="flex items-center font-mono text-[12px] font-bold uppercase tracking-overline text-ink">
          Participation — last {DAYS} sessions
          <InfoDot term="breadth" />
        </span>
        <p className="mt-0.5 font-sans text-[11px] leading-snug text-ink3">
          Share of stocks trading above their 20-day (short-term) and 50-day (long-term) averages.
        </p>
      </div>
      <ParticipationLines rows={rows} />
      <Legend />
      <Read band="info">{readLine}</Read>
    </section>
  );
}

function ParticipationLines({ rows }) {
  const width = 600;
  const height = 90;
  const pad = 4;
  const axisW = 24;
  const plotW = width - axisW;
  const n = rows.length;

  const x = (i) => (n <= 1 ? plotW / 2 : pad + (i / (n - 1)) * (plotW - 2 * pad));
  const y = (v) => height - pad - (v / 100) * (height - 2 * pad);

  const line20 = points(rows, "pct_above_20dma", x, y);
  const line50 = points(rows, "pct_above_50dma", x, y);

  return (
    <div className="border border-hairline bg-card p-2">
      <svg viewBox={`0 0 ${width} ${height}`} className="h-[90px] w-full" preserveAspectRatio="none">
        {/* y-axis: 0-100% fixed */}
        <text x="2" y={y(100) + 3} className="fill-ink3" fontSize="8">100</text>
        <text x="2" y={y(50) + 3} className="fill-ink3" fontSize="8">50</text>
        <text x="2" y={y(0) + 3} className="fill-ink3" fontSize="8">0</text>
        <line x1={axisW} y1={y(50)} x2={width} y2={y(50)} stroke="#eef0f3" strokeWidth="1" />
        <g transform={`translate(${axisW},0)`}>
          {line20 && <polyline points={line20} fill="none" stroke="#175cd3" strokeWidth="1.5" />}
          {line50 && <polyline points={line50} fill="none" stroke="#9a5b00" strokeWidth="1.5" strokeDasharray="3,2" />}
        </g>
      </svg>
    </div>
  );
}

function points(rows, field, x, y) {
  const pts = rows
    .map((r, i) => ({ i, v: r[field] }))
    .filter((p) => p.v != null);
  if (pts.length === 0) return null;
  return pts.map((p) => `${x(p.i).toFixed(1)},${y(p.v).toFixed(1)}`).join(" ");
}

function Legend() {
  return (
    <div className="mt-1.5 flex flex-wrap items-center gap-3 font-mono text-[9px] uppercase tracking-overline text-ink3">
      <span className="flex items-center gap-1">
        <span className="inline-block h-0.5 w-3 bg-info" />
        Short-term (20DMA)
      </span>
      <span className="flex items-center gap-1">
        <span className="inline-block h-0.5 w-3 bg-warn" style={{ borderTop: "2px dashed #9a5b00", height: 0 }} />
        Long-term (50DMA)
      </span>
    </div>
  );
}

// Compares the trend of the short-term line vs the long-term line over the
// window to produce a plain-English "early repair" / "broadening" / etc. read.
function buildReadLine(rows) {
  const v20 = rows.map((r) => r.pct_above_20dma).filter((v) => v != null);
  const v50 = rows.map((r) => r.pct_above_50dma).filter((v) => v != null);
  if (v20.length < 2 || v50.length < 2) {
    const latest = rows[rows.length - 1];
    return `Short-term participation is ${fmtPct(latest?.pct_above_20dma)}; long-term is ${fmtPct(
      latest?.pct_above_50dma
    )}. Not enough history yet for a trend read.`;
  }
  const d20 = v20[v20.length - 1] - v20[0];
  const d50 = v50[v50.length - 1] - v50[0];
  const dir20 = trendWord(d20);
  const dir50 = trendWord(d50);
  if (dir20 === "rising" && (dir50 === "flat" || dir50 === "falling")) {
    return `Short-term participation rising while long-term is ${dir50} — early repair.`;
  }
  if (dir20 === "falling" && (dir50 === "flat" || dir50 === "rising")) {
    return `Short-term participation falling while long-term is ${dir50} — early fatigue.`;
  }
  if (dir20 === dir50) {
    return `Both short-term and long-term participation are ${dir20} — a broad, consistent read.`;
  }
  return `Short-term participation is ${dir20}; long-term is ${dir50} — a mixed read.`;
}

function trendWord(delta) {
  if (delta > 3) return "rising";
  if (delta < -3) return "falling";
  return "flat";
}

function fmtPct(n) {
  return n == null ? "an unknown share" : `${n.toFixed(0)}%`;
}

function PanelSkeleton() {
  return (
    <div className="mt-4">
      <div className="mb-2 h-3 w-48 animate-pulse rounded bg-hairline2" />
      <div className="h-[90px] w-full animate-pulse rounded bg-hairline2" />
      <div className="mt-1 h-4 w-full animate-pulse rounded bg-hairline" />
    </div>
  );
}

function EmptyBlock({ title, children }) {
  return (
    <div className="mt-4 border border-dashed border-hairline px-4 py-6 text-center">
      <div className="font-mono text-[12px] font-semibold text-ink2">{title}</div>
      <div className="mt-1 font-sans text-[12px] leading-snug text-ink3">{children}</div>
    </div>
  );
}
