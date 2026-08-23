// House chart vocabulary — VISUAL_LANGUAGE.md §2 and §6 (binding).
//
// Plain inline SVG only. No chart library, ever. Colour comes exclusively from
// CSS custom properties defined in styles/tokens.css -- never a raw hex in
// this file. Every component renders a labelled empty frame when it has no
// data (never null, never a zero-height SVG): the database is real-data-only
// and sparse today, so the empty state is what will actually be on screen
// most of the time.
import React from "react";

const W = 900; // shared viewBox width unit for the wide charts

function clamp(n, lo, hi) {
  return Math.max(lo, Math.min(hi, n));
}

function toTime(d) {
  if (d === null || d === undefined) return null;
  const t = new Date(d).getTime();
  return Number.isNaN(t) ? null : t;
}

function fmtSigned(v, dp = 1) {
  const n = Number(v);
  return `${n >= 0 ? "+" : ""}${n.toFixed(dp)}`;
}

// Shared empty-frame renderer -- a bordered, sized SVG with a centred one-line
// reason. Never null, never zero height, so an empty chart still reads as a
// deliberate part of the page rather than a rendering failure.
function EmptyFrame({ height, reason, label }) {
  return (
    <svg
      viewBox={`0 0 ${W} ${height}`}
      width="100%"
      height={height}
      role="img"
      aria-label={label || reason}
    >
      <rect
        x="1" y="1" width={W - 2} height={height - 2}
        fill="var(--surface-2)" stroke="var(--ink)" strokeWidth="2"
      />
      <text
        x={W / 2} y={height / 2} textAnchor="middle" dominantBaseline="middle"
        fontSize="11" fontStyle="italic" fill="var(--ink-3)"
      >
        {reason}
      </text>
    </svg>
  );
}

// ---------------------------------------------------------------------------
// 2.1 — PositionBars: one row per position on a SHARED time axis. The point
// is that rows are comparable, so clustering in time is visible at a glance.
// ---------------------------------------------------------------------------
export function PositionBars({ from, to, rows, onRowClick }) {
  const list = rows || [];
  const ROW_H = 18;
  const AXIS_H = 22;
  const LABEL_W = 150;
  const RESULT_W = 72;
  const PAD_R = 8;

  if (list.length === 0) {
    return (
      <EmptyFrame
        height={AXIS_H + ROW_H * 3}
        reason="No positions reconstructed yet — nothing to place on the timeline."
      />
    );
  }

  let fromT = toTime(from);
  let toT = toTime(to);
  if (fromT === null || toT === null || fromT >= toT) {
    const starts = list.map((r) => toTime(r.start)).filter((v) => v !== null);
    const ends = list.map((r) => toTime(r.end)).filter((v) => v !== null);
    fromT = starts.length ? Math.min(...starts) : Date.now() - 30 * 86400000;
    toT = Math.max(ends.length ? Math.max(...ends) : 0, Date.now());
    if (fromT >= toT) toT = fromT + 86400000;
  }

  const plotX0 = LABEL_W;
  const plotX1 = W - RESULT_W - PAD_R;
  const x = (t) => clamp(plotX0 + ((t - fromT) / (toT - fromT)) * (plotX1 - plotX0), plotX0, plotX1);

  const H = AXIS_H + list.length * ROW_H + 6;
  const ticks = [0, 1 / 3, 2 / 3, 1].map((f) => fromT + f * (toT - fromT));

  let openCount = 0, posCount = 0, negCount = 0;
  list.forEach((r) => {
    if (!r.end) openCount += 1;
    else if (r.result > 0) posCount += 1;
    else if (r.result < 0) negCount += 1;
  });
  const label = `${list.length} position${list.length === 1 ? "" : "s"} on the ledger timeline; ` +
    `${openCount} still open, ${posCount} positive, ${negCount} negative.`;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} role="img" aria-label={label}>
      {ticks.map((t, i) => (
        <g key={i}>
          <line x1={x(t)} x2={x(t)} y1={AXIS_H} y2={H} stroke="var(--rule)" />
          <text x={x(t)} y={12} textAnchor="middle" fontSize="9" fill="var(--ink-4)">
            {new Date(t).toLocaleDateString("en-IN", { day: "2-digit", month: "short" })}
          </text>
        </g>
      ))}

      {list.map((row, i) => {
        const y = AXIS_H + i * ROW_H + ROW_H / 2;
        const startT = toTime(row.start);
        const endT = toTime(row.end);
        const barEndT = endT ?? toT;
        const x1 = startT !== null ? x(startT) : plotX0;
        const x2 = x(barEndT);
        const color = row.result > 0 ? "var(--ok)" : row.result < 0 ? "var(--bad)" : "var(--neutral)";
        const clickable = typeof onRowClick === "function";

        return (
          <g key={row.id ?? i} style={{ cursor: clickable ? "pointer" : "default" }}
             onClick={() => clickable && onRowClick(row.id)}>
            {row.warn && <title>{row.warn}</title>}
            <rect x="0" y={y - ROW_H / 2} width={W} height={ROW_H} fill="transparent" />

            <text x={LABEL_W - 8} y={y + 3} textAnchor="end" fontSize="10" fontWeight="700" fill="var(--ink)">
              {row.label}
              {row.sublabel && <tspan fontWeight="400" fill="var(--ink-3)" fontSize="9"> · {row.sublabel}</tspan>}
              {row.warn && <tspan fill="var(--warn-ink)"> ⚠</tspan>}
            </text>

            <line x1={x1} x2={x2} y1={y} y2={y} stroke={color} strokeWidth="2" />

            {(row.events || []).map((ev, j) => {
              const et = toTime(ev.at);
              if (et === null) return null;
              const ex = clamp(x(et), Math.min(x1, x2), Math.max(x1, x2));
              if (ev.kind === "add") {
                return <circle key={j} cx={ex} cy={y} r="2.5" fill="var(--ink)" />;
              }
              if (ev.kind === "sl_up") {
                return <path key={j} d={`M${ex - 3},${y + 2} L${ex + 3},${y + 2} L${ex},${y - 4} Z`} fill="var(--ink-2)" />;
              }
              if (ev.kind === "sl_down") {
                return <path key={j} d={`M${ex - 3},${y - 2} L${ex + 3},${y - 2} L${ex},${y + 4} Z`} fill="var(--ink-2)" />;
              }
              if (ev.kind === "exit") {
                return <circle key={j} cx={ex} cy={y} r="3.5" fill="var(--surface)" stroke="var(--ink-2)" strokeWidth="1.5" />;
              }
              return null;
            })}

            <circle cx={x1} cy={y} r="3" fill={color} />
            {endT !== null ? (
              <circle cx={x2} cy={y} r="3.5" fill="var(--surface)" stroke={color} strokeWidth="1.5" />
            ) : (
              <path d={`M${x2 - 1},${y - 4} L${x2 + 6},${y} L${x2 - 1},${y + 4} Z`} fill={color} />
            )}

            <text x={W - PAD_R} y={y + 3} textAnchor="end" fontSize="10" className="mono"
                  fill={row.result > 0 ? "var(--ok)" : row.result < 0 ? "var(--bad)" : "var(--neutral)"}>
              {row.result != null ? `${fmtSigned(row.result)}%` : endT !== null ? "—" : "open"}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

// ---------------------------------------------------------------------------
// 2.2 — Dumbbell: two dots joined by a rule. The GAP is the finding.
// ---------------------------------------------------------------------------
// `n` added to the contract 2026-08-23: VISUAL_LANGUAGE §1 requires a
// denominator beside every percentage, and the original prop list had nowhere to
// put one. Optional -- renders "n=..." after the row label when supplied, and
// nothing when the underlying payload genuinely has no count to give.
export function Dumbbell({ rows, max, gapWarn = 10, suffix = "", n = null }) {
  const list = rows || [];
  if (list.length === 0) {
    return <EmptyFrame height={70} reason="No stated-vs-actual pair to compare yet." />;
  }

  const RH = 36;
  const PAD_T = 10;
  const LABEL_W = 160;
  const RIGHT_W = 110;
  const PAD_R = 10;
  const domainMax = max || Math.max(10, ...list.flatMap((r) => [r.a?.value ?? 0, r.b?.value ?? 0])) * 1.05;
  const plotX0 = LABEL_W;
  const plotX1 = W - RIGHT_W - PAD_R;
  const x = (v) => plotX0 + (clamp(v, 0, domainMax) / domainMax) * (plotX1 - plotX0);
  const H = PAD_T * 2 + list.length * RH;

  const summary = list
    .map((r) => {
      const gap = Math.abs((r.a?.value ?? 0) - (r.b?.value ?? 0));
      return `${r.label}: ${r.a?.label} ${r.a?.value}${suffix} vs ${r.b?.label} ${r.b?.value}${suffix}, gap ${gap.toFixed(1)}${suffix}`;
    })
    .join("; ");

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} role="img" aria-label={summary}>
      {list.map((row, i) => {
        const aV = row.a?.value ?? 0;
        const bV = row.b?.value ?? 0;
        const weaker = aV <= bV ? row.a : row.b;
        const stronger = aV <= bV ? row.b : row.a;
        const gap = Math.abs(aV - bV);
        const warn = gap > gapWarn;
        const cy = PAD_T + i * RH + 16;
        const wx = x(weaker?.value ?? 0);
        const sx = x(stronger?.value ?? 0);

        return (
          <g key={i}>
            <text x={PAD_R} y={cy + 3} fontSize="10" fontWeight="600" fill="var(--ink-2)">
              {row.label}
              {/* A percentage without its denominator is a defect on any screen
                  in this project (VISUAL_LANGUAGE §1). */}
              {row.n != null || n != null ? (
                <tspan fill="var(--ink-4)" fontWeight="400"> n={row.n ?? n}</tspan>
              ) : null}
            </text>
            <line x1={wx} x2={sx} y1={cy} y2={cy} stroke={warn ? "var(--warn)" : "var(--neutral)"} strokeWidth="2" />
            <circle cx={wx} cy={cy} r="4" fill="var(--surface)" stroke="var(--ink-2)" strokeWidth="1.5" />
            <circle cx={sx} cy={cy} r="4.5" fill="var(--ink-2)" />
            <text x={wx} y={cy + 16} textAnchor="middle" fontSize="9" fill="var(--ink-3)">
              {weaker?.label}
            </text>
            <text x={sx} y={cy + 16} textAnchor="middle" fontSize="9" fill="var(--ink-3)">
              {stronger?.label}
            </text>
            <text x={W - PAD_R} y={cy + 3} textAnchor="end" fontSize="10" className="mono"
                  fill={warn ? "var(--warn-ink)" : "var(--ink-2)"}>
              {row.a?.value}{suffix} → {row.b?.value}{suffix}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

// ---------------------------------------------------------------------------
// 2.3 — StripPlot: one tick per observation on a shared axis, median ruled.
// ---------------------------------------------------------------------------
export function StripPlot({ values, median, suffix = "" }) {
  const vals = (values || []).filter((v) => v !== null && v !== undefined);
  if (vals.length === 0) {
    return <EmptyFrame height={70} reason="No observations yet." />;
  }

  const H = 72;
  const PADL = 34;
  const PADR = 34;
  const TICK_TOP = 14;
  const TICK_BOT = 34;
  const rawMax = Math.max(...vals, median || 0);
  const domainMax = Math.max(5, Math.ceil((rawMax * 1.1) / 5) * 5);
  const x = (v) => PADL + (clamp(v, 0, domainMax) / domainMax) * (W - PADL - PADR);

  const tickCount = 6;
  const ticks = Array.from({ length: tickCount + 1 }, (_, i) => Math.round((domainMax / tickCount) * i));

  const label = `n=${vals.length} observations${median != null ? `, median ${median}${suffix}` : ""}.`;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} role="img" aria-label={label}>
      <line x1={PADL} x2={W - PADR} y1={TICK_BOT} y2={TICK_BOT} stroke="var(--ink)" strokeWidth="2" />
      {ticks.map((t, i) => (
        <g key={i}>
          <line x1={x(t)} x2={x(t)} y1={TICK_BOT} y2={TICK_BOT + 4} stroke="var(--rule)" />
          <text x={x(t)} y={TICK_BOT + 15} textAnchor="middle" fontSize="9" fill="var(--ink-4)">
            {t}
          </text>
        </g>
      ))}
      {vals.map((v, i) => (
        <line key={i} x1={x(v)} x2={x(v)} y1={TICK_TOP} y2={TICK_BOT} stroke="var(--ink)" strokeWidth="1.5" />
      ))}
      {median != null && (
        <g>
          <path
            d={`M${x(median) - 4},${TICK_BOT + 6} L${x(median) + 4},${TICK_BOT + 6} L${x(median)},${TICK_BOT} Z`}
            fill="var(--info-ink)"
          />
          <text x={x(median)} y={TICK_BOT + 28} textAnchor="middle" fontSize="9" className="mono" fill="var(--info-ink)">
            median {median}{suffix} · n={vals.length}
          </text>
        </g>
      )}
    </svg>
  );
}

// ---------------------------------------------------------------------------
// 2.4 — BandLine: a line with its threshold bands drawn as flat background
// rects. Generalises the XP chart. Bands are panel-2/panel-3 washes, never
// coloured fills.
// ---------------------------------------------------------------------------
export function BandLine({ points, bands, log }) {
  const pts = (points || []).filter((p) => p.y !== null && p.y !== undefined);
  if (pts.length === 0) {
    return <EmptyFrame height={150} reason="No series data yet." />;
  }

  const H = 150;
  const PADL = 6;
  const PADR = 58;
  const TOP = 12;
  const BOTTOM = 16;
  const plotTop = TOP;
  const plotBottom = H - BOTTOM;
  const bandList = bands || [];
  const bandMax = bandList.length ? bandList[bandList.length - 1].at : 0;
  const dataMax = Math.max(...pts.map((p) => p.y));
  const domainMax = Math.max(bandMax, dataMax) * 1.02 || 1;

  const yFor = (v) => {
    if (log) {
      const safe = Math.max(v, 1);
      const safeMax = Math.max(domainMax, 2);
      return plotBottom - (Math.log(safe) / Math.log(safeMax)) * (plotBottom - plotTop);
    }
    return plotBottom - (clamp(v, 0, domainMax) / domainMax) * (plotBottom - plotTop);
  };
  const xFor = (i) => (pts.length > 1 ? PADL + (i / (pts.length - 1)) * (W - PADL - PADR) : (W - PADL - PADR) / 2 + PADL);

  const boundaries = [0, ...bandList.map((b) => b.at)];
  const last = pts[pts.length - 1];
  const bandLabel = bandList.length
    ? bandList.find((b) => last.y <= b.at)?.label || bandList[bandList.length - 1].label
    : null;
  const label = `Trend: ${pts.length} points, latest ${last.y}${bandLabel ? ` (${bandLabel})` : ""}.`;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} role="img" aria-label={label}>
      {bandList.map((b, i) => {
        const lower = boundaries[i];
        const upper = i + 1 < boundaries.length ? boundaries[i + 1] : domainMax;
        const rectTop = yFor(Math.max(upper, lower));
        const rectBottom = yFor(lower);
        return (
          <g key={i}>
            <rect
              x={PADL} y={rectTop} width={W - PADL - PADR} height={Math.max(0, rectBottom - rectTop)}
              fill={i % 2 === 0 ? "var(--surface-2)" : "var(--surface-3)"}
            />
            <text x={W - PADR + 5} y={(rectTop + rectBottom) / 2 + 3} fontSize="9" fill="var(--ink-4)">
              {b.label}
            </text>
          </g>
        );
      })}

      {pts.length > 1 && (
        <path
          d={pts.map((p, i) => `${i ? "L" : "M"}${xFor(i).toFixed(1)},${yFor(p.y).toFixed(1)}`).join("")}
          fill="none" stroke="var(--info)" strokeWidth="2"
        />
      )}
      <circle cx={xFor(pts.length - 1)} cy={yFor(last.y)} r="3.5" fill="var(--info-ink)" />
      <text x={xFor(pts.length - 1) + 6} y={yFor(last.y) + 3} fontSize="10" className="mono" fill="var(--info-ink)">
        {last.y}
      </text>
    </svg>
  );
}

// ---------------------------------------------------------------------------
// 2.5 — Ribbon: one small rect per session. Generalises the MBI ribbon.
// ---------------------------------------------------------------------------
export function Ribbon({ cells }) {
  const list = cells || [];
  if (list.length === 0) {
    return <EmptyFrame height={30} reason="No sessions recorded yet." />;
  }

  const CELL_W = 9;
  const GAP = 2;
  const H = 26;
  const TOP = 4;
  const w = list.length * (CELL_W + GAP);
  const fillFor = { GREEN: "var(--ok)", WHITE: "var(--neutral-fill)", RED: "var(--bad)", NONE: "var(--surface-2)" };

  const counts = list.reduce(
    (acc, c) => {
      acc[c.state] = (acc[c.state] || 0) + 1;
      if (c.warn) acc.warn += 1;
      return acc;
    },
    { GREEN: 0, WHITE: 0, RED: 0, NONE: 0, warn: 0 }
  );
  const label = `${list.length} sessions: ${counts.GREEN} green, ${counts.WHITE} white, ${counts.RED} red` +
    `${counts.warn ? `, ${counts.warn} warning day(s)` : ""}.`;

  return (
    <svg viewBox={`0 0 ${w} ${H}`} width="100%" height={H} role="img" aria-label={label}>
      {list.map((cell, i) => {
        const x = i * (CELL_W + GAP);
        const fill = fillFor[cell.state] || fillFor.NONE;
        return (
          <g key={cell.key ?? i}>
            <rect
              x={x} y={TOP} width={CELL_W} height={H - TOP} fill={fill}
              stroke={cell.state === "NONE" || !cell.state ? "var(--ink)" : "none"}
              strokeWidth={cell.state === "NONE" || !cell.state ? "1.5" : "0"}
            />
            {cell.warn && <circle cx={x + CELL_W / 2} cy={TOP - 1} r="1.6" fill="var(--warn)" />}
            <title>{cell.title || cell.key}</title>
          </g>
        );
      })}
    </svg>
  );
}

// ---------------------------------------------------------------------------
// 2.6 — StackedStrip: one bar split proportionally, segments labelled in
// place. Never a pie. Categories carry no state, so segments differ by
// monochrome ink shade, never by hue.
// ---------------------------------------------------------------------------
const STRIP_FILLS = ["var(--ink)", "var(--ink-2)", "var(--ink-3)", "var(--ink-4)"];

// `n` and `suffix` added to the contract 2026-08-23 for the same reason as
// Dumbbell: a composition shown as percentages without its denominator violates
// VISUAL_LANGUAGE §1.
// Caption carrying the denominator. Kept outside the <svg> so it wraps and
// scales with the surrounding type rather than being baked into the viewBox.
function StripCaption({ n, total }) {
  if (n == null) return null;
  return <div className="chart-caption">n={n} · total {total}</div>;
}

export function StackedStrip({ segments, n = null, suffix = "" }) {
  const list = (segments || []).filter((s) => (s.value || 0) > 0);
  const total = list.reduce((sum, s) => sum + s.value, 0);
  if (list.length === 0 || total <= 0) {
    return <EmptyFrame height={32} reason="No composition data yet." />;
  }

  const H = 30;
  let acc = 0;
  const parts = list.map((s) => {
    const width = (s.value / total) * W;
    const seg = { ...s, x: acc, width };
    acc += width;
    return seg;
  });
  const label = `Composition: ${list.map((s) => `${s.label} ${s.value}`).join(", ")}.`;

  return (
    <>
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} role="img" aria-label={label}>
      {parts.map((s, i) => (
        <g key={i}>
          <rect x={s.x} y="0" width={s.width} height={H} fill={STRIP_FILLS[i % STRIP_FILLS.length]}
                stroke="var(--surface)" strokeWidth="1" />
          <text
            x={s.x + s.width / 2} y={H / 2 + 4} textAnchor="middle" fontSize="10"
            fill={i % 4 < 2 ? "var(--surface)" : "var(--ink)"}
          >
            {s.label} {s.value}{suffix}
          </text>
        </g>
      ))}
    </svg>
    <StripCaption n={n} total={total} />
    </>
  );
}


// ---------------------------------------------------------------------------
// 2.7 — SmallMultiples: a grid of identical miniature charts on a SHARED
// scale. Do not merge into one big combined chart.
// ---------------------------------------------------------------------------
export function SmallMultiples({ items }) {
  const list = items || [];
  if (list.length === 0) {
    return <EmptyFrame height={100} reason="No series to compare yet." />;
  }

  const ITEM_W = 200;
  const H = 100;
  const BAR_TOP = 22;
  const BAR_BOTTOM = 78;
  const sharedMax = Math.max(1, ...list.flatMap((it) => it.values || []).map((v) => Math.abs(v)));
  const w = list.length * ITEM_W;

  const label = `${list.length} series on a shared scale: ` +
    list.map((it) => `${it.label} ${it.caption || ""}`.trim()).join("; ") + ".";

  return (
    <svg viewBox={`0 0 ${w} ${H}`} width="100%" height={H} role="img" aria-label={label}>
      {list.map((it, i) => {
        const baseX = i * ITEM_W;
        const vals = it.values || [];
        const barW = vals.length ? (ITEM_W - 16) / vals.length : 0;
        return (
          <g key={it.label ?? i}>
            {i > 0 && <line x1={baseX} x2={baseX} y1="4" y2={H - 4} stroke="var(--rule)" />}
            <text x={baseX + 8} y="12" fontSize="10" fontWeight="700" fill="var(--ink)">
              {it.label}
            </text>
            <line x1={baseX + 8} x2={baseX + ITEM_W - 8} y1={BAR_BOTTOM} y2={BAR_BOTTOM} stroke="var(--ink)" strokeWidth="2" />
            {vals.map((v, j) => {
              const h = (Math.abs(v) / sharedMax) * (BAR_BOTTOM - BAR_TOP);
              const x = baseX + 8 + j * barW;
              return (
                <rect key={j} x={x} y={BAR_BOTTOM - h} width={Math.max(1, barW - 1)} height={h} fill="var(--ink-2)" />
              );
            })}
            {it.caption && (
              <text x={baseX + 8} y={H - 6} fontSize="9" className="mono" fill="var(--ink-3)">
                {it.caption}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
}
