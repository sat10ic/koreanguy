import { useEffect, useState } from "react";
import { getRegimeHistory } from "../api.js";
import Read from "./Read.jsx";

/**
 * RegimeTrend — reworked RegimeHistoryStrip (design §1.5). Default window
 * 60D (was 90 — too wide to read). Title + sans subtitle, a labelled y-axis
 * on the XP line (min/mid/max ticks + faint 50 gridline + hover tooltip
 * showing date+XP), a posture-ribbon LEGEND row, and a generated READ line.
 */
const DAYS = 60;

const MODE_BAND = {
  RISK_ON: "bull",
  SELECTIVE: "warn",
  DEFENSIVE: "bear",
  NO_TRADE: "ink",
};
const BAND_BG = {
  bull: "bg-bull",
  warn: "bg-warn",
  bear: "bg-bear",
  ink: "bg-ink",
};
const BAND_DOT = {
  bull: "bg-bull-dot",
  warn: "bg-warn-dot",
  bear: "bg-bear-dot",
  ink: "bg-ink",
};
const MODE_LABEL = {
  RISK_ON: "Risk-On",
  SELECTIVE: "Selective",
  DEFENSIVE: "Defensive",
  NO_TRADE: "No-Trade",
};

export default function RegimeTrend() {
  const [state, setState] = useState({ loading: true, error: null, data: null });
  const [hover, setHover] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setState({ loading: true, error: null, data: null });
    getRegimeHistory(DAYS)
      .then((d) => !cancelled && setState({ loading: false, error: null, data: d }))
      .catch((e) => !cancelled && setState({ loading: false, error: e.message, data: null }));
    return () => {
      cancelled = true;
    };
  }, []);

  if (state.loading) return <StripSkeleton />;
  if (state.error) {
    return (
      <EmptyBlock title="Couldn't reach the API">
        Make sure the backend is running: <code>python -m manas_os.api</code>
      </EmptyBlock>
    );
  }
  if (!state.data?.available || state.data.rows.length === 0) {
    return (
      <EmptyBlock title="No regime history yet">
        Run backfill to populate: <code>python manas.py backfill-snapshots</code>
      </EmptyBlock>
    );
  }

  const rows = state.data.rows;
  const readLine = buildReadLine(rows);

  return (
    <section data-testid="regime-trend" className="mt-4 border border-hairline bg-card p-3">
      <div className="mb-2">
        <span className="font-mono text-[12px] font-bold uppercase tracking-overline text-ink">
          XP &amp; Posture — last {DAYS} sessions
        </span>
        <p className="mt-0.5 font-sans text-[11px] leading-snug text-ink3">
          Blue line = XP dial (0–100). Colored ribbon below = market posture that day.
        </p>
      </div>
      <XpLine rows={rows} hover={hover} onHover={setHover} />
      <Ribbon rows={rows} />
      <Legend />
      <Read band="info">{readLine}</Read>
    </section>
  );
}

function XpLine({ rows, hover, onHover }) {
  const width = 600;
  const height = 80;
  const pad = 4;
  const axisW = 24;

  const values = rows
    .map((r, i) => ({ i, v: r.xp_value, date: r.snapshot_date }))
    .filter((p) => p.v != null);

  if (values.length === 0) {
    return (
      <div className="border border-hairline bg-raised px-3 py-2">
        <span className="font-mono text-[10px] text-ink3">No XP values in this window.</span>
      </div>
    );
  }

  const n = rows.length;
  const min = Math.min(0, ...values.map((p) => p.v));
  const max = Math.max(100, ...values.map((p) => p.v));
  const range = max - min || 1;
  const plotW = width - axisW;

  const x = (i) => (n <= 1 ? plotW / 2 : pad + (i / (n - 1)) * (plotW - 2 * pad));
  const y = (v) => height - pad - ((v - min) / range) * (height - 2 * pad);
  const mid = (min + max) / 2;

  const points = values.map((p) => `${x(p.i).toFixed(1)},${y(p.v).toFixed(1)}`).join(" ");

  return (
    <div className="relative border border-hairline bg-card p-2">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="h-[80px] w-full"
        preserveAspectRatio="none"
        onMouseLeave={() => onHover(null)}
      >
        {/* y-axis labels */}
        <text x="2" y={y(max) + 3} className="fill-ink3" fontSize="8">{Math.round(max)}</text>
        <text x="2" y={y(mid) + 3} className="fill-ink3" fontSize="8">{Math.round(mid)}</text>
        <text x="2" y={y(min) + 3} className="fill-ink3" fontSize="8">{Math.round(min)}</text>
        {/* faint 50 gridline (only meaningful when 50 is in-range) */}
        {min <= 50 && max >= 50 && (
          <line x1={axisW} y1={y(50)} x2={width} y2={y(50)} stroke="#eef0f3" strokeWidth="1" />
        )}
        <g transform={`translate(${axisW},0)`}>
          <polyline points={points} fill="none" stroke="#175cd3" strokeWidth="1.5" />
          {values.map((p) => (
            <circle
              key={p.i}
              cx={x(p.i)}
              cy={y(p.v)}
              r={hover?.i === p.i ? 3 : 6}
              fill={hover?.i === p.i ? "#175cd3" : "transparent"}
              onMouseEnter={() => onHover(p)}
              style={{ cursor: "pointer" }}
            />
          ))}
        </g>
      </svg>
      {hover && (
        <div
          className="pointer-events-none absolute top-1 rounded-chip border border-hairline bg-card px-1.5 py-0.5 font-mono text-[9px] text-ink"
          style={{ left: `${((axisW + x(hover.i)) / width) * 100}%` }}
        >
          {hover.date} · XP {hover.v.toFixed(1)}
        </div>
      )}
    </div>
  );
}

function Ribbon({ rows }) {
  return (
    <div className="mt-1 flex h-4 w-full border border-hairline bg-card">
      {rows.map((r) => {
        const band = MODE_BAND[r.market_mode] || "muted";
        const bg = BAND_BG[band] || "bg-muted";
        return (
          <div key={r.snapshot_date} title={r.snapshot_date} className={"relative flex-1 " + bg}>
            {Boolean(r.warning_day) && (
              <span className="absolute left-1/2 top-1/2 h-1 w-1 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white ring-1 ring-ink" />
            )}
          </div>
        );
      })}
    </div>
  );
}

function Legend() {
  return (
    <div className="mt-1.5 flex flex-wrap items-center gap-3 font-mono text-[9px] uppercase tracking-overline text-ink3">
      {Object.entries(MODE_LABEL).map(([mode, label]) => (
        <span key={mode} className="flex items-center gap-1">
          <span className={"inline-block h-2 w-2 rounded-sm " + BAND_DOT[MODE_BAND[mode]]} />
          {label}
        </span>
      ))}
      <span className="flex items-center gap-1">
        <span className="inline-block h-1.5 w-1.5 rounded-full bg-white ring-1 ring-ink" />
        warning day
      </span>
    </div>
  );
}

function buildReadLine(rows) {
  const values = rows.map((r) => r.xp_value).filter((v) => v != null);
  const lastMode = rows[rows.length - 1]?.market_mode;
  const modeLabel = MODE_LABEL[lastMode] || "unknown";
  if (values.length < 2) {
    return `Posture is ${modeLabel}.`;
  }
  const first = values[0];
  const last = values[values.length - 1];
  const verb = last > first ? "rose" : last < first ? "fell" : "held";
  return `XP ${verb} ${first.toFixed(0)}→${last.toFixed(0)} over ${rows.length} sessions; posture is ${modeLabel}.`;
}

function StripSkeleton() {
  return (
    <div className="mt-4">
      <div className="mb-2 h-3 w-40 animate-pulse rounded bg-hairline2" />
      <div className="h-[80px] w-full animate-pulse rounded bg-hairline2" />
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
