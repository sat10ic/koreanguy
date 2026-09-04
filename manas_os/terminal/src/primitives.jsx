// Terminal primitives — the shared visual language for sat10ic OS.
// Light theme, dense tables where data is tabular, cleaner cards for
// decision surfaces. Western color semantics: green = up/bull, red = down/bear.

import { useState } from "react";

// ── Tone helpers ─────────────────────────────────────────────────────────────
// Semantic tone → Tailwind class map. All surfaces share these.
const TONE_TEXT = {
  bull: "text-bull",
  bear: "text-bear",
  warn: "text-warn",
  info: "text-info",
  muted: "text-ink2",
};

const TONE_BG = {
  bull: "bg-bull-bg text-bull",
  bear: "bg-bear-bg text-bear",
  warn: "bg-warn-bg text-warn",
  info: "bg-info-bg text-info",
  muted: "bg-muted-bg text-ink2",
};

const TONE_BORDER = {
  bull: "border-bull-border bg-bull-bg text-bull",
  bear: "border-bear-border bg-bear-bg text-bear",
  warn: "border-warn-border bg-warn-bg text-warn",
  info: "border-info-border bg-info-bg text-info",
  muted: "border-hairline bg-card text-ink2",
};

const STATUS_DOT = {
  bull: "bg-bull-dot",
  bear: "bg-bear-dot",
  warn: "bg-warn-dot",
  info: "bg-info-dot",
  muted: "bg-ink3",
  off: "bg-ink3",
};

export function toneText(tone) {
  return TONE_TEXT[tone] || TONE_TEXT.muted;
}
export function toneBg(tone) {
  return TONE_BG[tone] || TONE_BG.muted;
}
export function toneBorder(tone) {
  return TONE_BORDER[tone] || TONE_BORDER.muted;
}
export function statusDot(tone) {
  return STATUS_DOT[tone] || STATUS_DOT.muted;
}

// ── Formatting ───────────────────────────────────────────────────────────────
export function fmtPct(value, digits = 1) {
  if (value == null || Number.isNaN(Number(value))) return "—";
  return `${Number(value).toFixed(digits)}%`;
}

export function signed(value, suffix = "", digits = 2) {
  if (value == null || Number.isNaN(Number(value))) return "—";
  const n = Number(value);
  return `${n > 0 ? "+" : ""}${n.toFixed(digits).replace(/\.?0+$/, "")}${suffix}`;
}

export function fmtNum(value) {
  if (value == null || Number.isNaN(Number(value))) return "—";
  return Number(value).toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

// ── StatusChip: the smallest state indicator (color dot + label) ──────────
export function StatusChip({ tone = "muted", label, title, dot = true, className = "" }) {
  return (
    <span
      title={title}
      className={`inline-flex items-center gap-1 whitespace-nowrap font-mono text-[10px] uppercase tracking-overline ${toneText(tone)} ${className}`}
    >
      {dot && <span className={`inline-block h-2 w-2 rounded-full ${statusDot(tone)}`} />}
      {label}
    </span>
  );
}

// ── BandChip: colored chip w/ border + bg (the "grade" / "phase" pill) ────
export function BandChip({ tone = "muted", children, className = "" }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-chip border px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-overline ${toneBorder(tone)} ${className}`}>
      {children}
    </span>
  );
}

// ── TermPanel: the base panel box ─────────────────────────────────────────
export function TermPanel({ title, sub, right, children, className = "", pad = "p-3" }) {
  return (
    <section className={`border border-hairline bg-card ${pad} ${className}`}>
      {(title || sub || right) && (
        <header className="mb-2 flex items-start justify-between gap-2">
          <div className="min-w-0">
            {title && (
              <h2 className="font-mono text-[11px] font-bold uppercase tracking-overline text-ink">
                {title}
              </h2>
            )}
            {sub && <p className="mt-0.5 font-sans text-[12px] leading-snug text-ink3">{sub}</p>}
          </div>
          {right && <div className="shrink-0">{right}</div>}
        </header>
      )}
      {children}
    </section>
  );
}

// ── plain-read: the jargon-reduction layer. Tech label + question, then a
//    one-line human answer. The `gloss` prop becomes a (?) tooltip.
export function PlainRead({ label, question, read, gloss, tone = "muted" }) {
  return (
    <div className="flex items-start gap-2 font-sans text-[12px] leading-snug text-ink2">
      <span className={`mt-px shrink-0 font-mono text-[9px] font-bold uppercase tracking-overline ${toneText(tone)}`}>
        {label}
      </span>
      {question && <span className="shrink-0 text-ink3">{question}</span>}
      <span className="min-w-0">{read}</span>
      {gloss && <Gloss text={gloss} />}
    </div>
  );
}

// ── Gloss: (?) tooltip that explains jargon in plain words ───────────────
export function Gloss({ text, className = "" }) {
  const [open, setOpen] = useState(false);
  return (
    <span className={`relative inline-flex shrink-0 ${className}`}>
      <button
        type="button"
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onClick={() => setOpen((v) => !v)}
        className="flex h-3.5 w-3.5 items-center justify-center rounded-full border border-hairline bg-raised font-mono text-[9px] text-ink3 hover:border-ink hover:text-ink"
        aria-label="explain term"
      >
        ?
      </button>
      {open && (
        <span className="absolute left-0 top-5 z-20 w-56 border border-hairline bg-card px-2 py-1.5 font-sans text-[11px] leading-snug text-ink2 shadow-sm">
          {text}
        </span>
      )}
    </span>
  );
}

// ── BarSpark: thin vertical bars for a history series. Green above mid/zero,
//    red below, latest bar highlighted (the quadrant-row history view).
export function BarSpark({ values = [], mid = 0, height = 34, className = "" }) {
  if (!values || values.length < 2) {
    return <div className={`flex items-center justify-center border border-dashed border-hairline bg-raised font-mono text-[9px] uppercase tracking-overline text-ink3 ${className}`} style={{ height }}>no history</div>;
  }
  const w = 100;
  const h = 34;
  const base = mid == null ? 0 : mid;
  const devs = values.map((v) => (v == null ? 0 : v - base));
  const span = Math.max(...devs.map(Math.abs)) || 1;
  const zeroY = h / 2;
  const bw = w / values.length;
  const gap = bw > 4 ? 1 : 0;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" className={`block w-full ${className}`} style={{ height }} aria-hidden="true">
      <line x1="0" y1={zeroY} x2={w} y2={zeroY} stroke="currentColor" strokeOpacity="0.3" strokeWidth="1" />
      {values.map((v, i) => {
        if (v == null) return null;
        const d = v - base;
        const mag = (Math.abs(d) / span) * (h / 2 - 2);
        const y = d >= 0 ? zeroY - mag : zeroY;
        const last = i === values.length - 1;
        return (
          <rect
            key={i}
            x={i * bw + gap / 2}
            y={y}
            width={Math.max(bw - gap, 0.8)}
            height={Math.max(mag, 0.8)}
            className={d >= 0 ? "fill-bull" : "fill-bear"}
            opacity={last ? 1 : 0.55}
          />
        );
      })}
    </svg>
  );
}

// ── LineSpark: thin line sparkline for smooth series (equity, closing price) ─
export function LineSpark({ values = [], height = 30, tone = "bull", className = "" }) {
  if (!values || values.length < 2) {
    return <div className={`flex items-center justify-center border border-dashed border-hairline bg-raised font-mono text-[9px] uppercase tracking-overline text-ink3 ${className}`} style={{ height }}>no history</div>;
  }
  const w = 100;
  const h = 30;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const pts = values.map((v, i) => `${(i / (values.length - 1)) * w},${h - ((v - min) / span) * (h - 4) - 2}`).join(" ");
  const color = tone === "bear" ? "var(--tw-bear, #b42318)" : tone === "warn" ? "#9a5b00" : "#0f7a3d";
  return (
    <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" className={`block w-full ${className}`} style={{ height }} aria-hidden="true">
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

// ── MeterBar: horizontal progress-style bar (money-at-risk, capacity) ────
export function MeterBar({ pct, tone = "info", className = "" }) {
  const p = Math.max(0, Math.min(100, Number(pct) || 0));
  const fill = {
    bull: "bg-bull",
    bear: "bg-bear",
    warn: "bg-warn",
    info: "bg-info",
  }[tone] || "bg-info";
  return (
    <div className={`h-1.5 w-full overflow-hidden bg-hairline2 ${className}`}>
      <div className={`h-full ${fill}`} style={{ width: `${p}%` }} />
    </div>
  );
}

// ── TermTable: the dense terminal grid. Columns = [{key, label, align}].
//    `renderCell` returns a node per (row, col) for custom cells; default
//    renders text. `toneFor` can color a cell's bg.
export function TermTable({
  columns = [],
  rows = [],
  renderCell,
  toneFor,
  className = "",
  dense = true,
}) {
  return (
    <div className={`term-scroll overflow-x-auto ${className}`}>
      <table className={`w-full border-collapse font-mono ${dense ? "text-[11px]" : "text-[12px]"}`}>
        <thead>
          <tr className="border border-hairline bg-raised text-left text-[9px] uppercase tracking-overline text-ink3">
            {columns.map((col) => (
              <th key={col.key} className="whitespace-nowrap border-r border-hairline px-2 py-1.5 last:border-r-0">
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-hairline2">
              {columns.map((col) => {
                const tone = toneFor?.(row, col);
                const content = renderCell ? renderCell(row, col) : row[col.key];
                return (
                  <td
                    key={col.key}
                    className={`whitespace-nowrap border-r border-hairline2 px-2 py-1.5 last:border-r-0 tabular-nums ${
                      tone ? toneBg(tone) : i % 2 ? "bg-card" : "bg-bg/30"
                    }`}
                  >
                    {content ?? "—"}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── TermGrid: uniform tile grid for chips/cards (candidate rows, sectors) ─
export function TermGrid({ children, className = "grid-cols-2 lg:grid-cols-3", gap = "gap-2" }) {
  return <div className={`grid ${gap} ${className}`}>{children}</div>;
}

// ── StatTile: compact number tile for metric tapes ───────────────────────
export function StatTile({ label, value, tone = "muted", sub, gloss }) {
  return (
    <div className="border border-hairline bg-raised px-3 py-2">
      <div className="flex items-center gap-1 font-mono text-[9px] uppercase tracking-overline text-ink3">
        {label}
        {gloss && <Gloss text={gloss} />}
      </div>
      <div className={`mt-1 font-mono text-[18px] font-bold leading-none tabular-nums ${toneText(tone)}`}>
        {value ?? "—"}
      </div>
      {sub && <div className="mt-1 font-sans text-[11px] leading-tight text-ink3">{sub}</div>}
    </div>
  );
}

// ── EmptyLine: honest empty/loading/error state (never a blank grid) ─────
export function EmptyLine({ children, tone = "muted" }) {
  return (
    <div className={`border border-dashed border-hairline bg-raised px-3 py-4 font-mono text-[11px] uppercase tracking-overline ${toneText(tone)}`}>
      {children}
    </div>
  );
}

// ── SectionLabel: small uppercase section kicker ─────────────────────────
export function SectionLabel({ children, className = "" }) {
  return (
    <div className={`font-mono text-[10px] font-bold uppercase tracking-overline text-ink3 ${className}`}>
      {children}
    </div>
  );
}

// ── Expandable: "details"-style disclosure for expert layers ─────────────
export function Expandable({ label, children, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="font-mono text-[10px] uppercase tracking-overline text-ink3 hover:text-ink"
      >
        {open ? "▾" : "▸"} {label}
      </button>
      {open && <div className="mt-1.5">{children}</div>}
    </div>
  );
}