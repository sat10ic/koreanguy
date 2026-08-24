// House chart vocabulary — VISUAL_LANGUAGE.md §2 and §6 (binding), as
// remapped by REDESIGN_SCOUTING_WIRE.md §5 (the Scouting × Wire ladder).
//
// Binding renderer mapping for this wave:
//   2.1  PositionBars  → ECharts custom series (the Ledger shared time axis)
//   2.2  Dumbbell      → Vega-Lite via vega-embed
//   2.3  StripPlot     → Vega-Lite via vega-embed
//   2.4  BandLine      → ECharts line (flat band rects + line + last value)
//   2.5  Ribbon        → inline SVG (trivial, no library — one block/session)
//   2.6  StackedStrip  → Vega-Lite via vega-embed
//   2.7  SmallMultiples→ ECharts custom series (grid of miniatures)
//   2.10 StackedArea   → ECharts stacked area (new export, Traders play-mix)
//   2.11 CalendarGrid  → ECharts calendar (new export, Traders cadence)
//
// Contract rules kept from the previous implementation:
//   - Export names and props are identical to VISUAL_LANGUAGE §6; the two new
//     exports (StackedArea, CalendarGrid) are fixed in the wave handoff.
//   - role="img" + aria-label stating the finding derived from the data —
//     never a static string.
//   - Colour resolves ONLY through CSS custom properties (the wave token
//     layer: --ground/--raised/--sunken/--edge/--hair/--ink/--ink-2/--ink-3/
//     --ink-4/--risk/--up/--down/--caution/--caution-bg). `useTokens()` reads
//     them at the adapter boundary once per mount and hands the resolved
//     strings into echarts options / Vega-Lite specs / inline SVG. No raw hex
//     literal exists in this file.
//   - Charts are responsive (no fixed pixel widths on containers; ECharts
//     ResizeObserver / Vega width-measure already present), never animate on
//     load (echarts option.animation=false; Vega renders statically; the
//     inline-SVG ribbon is static markup).
//   - Empty state is ONE compact muted line (.chart-empty), never a large
//     framed SVG, never null, never a zero-height container.
//   - House finish: no frame of its own, flat solid fills, 1px ink strokes
//     where definition is needed, hard-ended bars, radius 0, no gradients,
//     no glows, no blur shadows, no load animation.
import React from "react";
import * as echarts from "echarts/core";
import { CustomChart, HeatmapChart, LineChart } from "echarts/charts";
import {
  CalendarComponent,
  GridComponent,
  MarkPointComponent,
  TooltipComponent,
  VisualMapComponent,
} from "echarts/components";
import { SVGRenderer } from "echarts/renderers";
import embed from "vega-embed";

echarts.use([
  CustomChart,
  LineChart,
  HeatmapChart,
  CalendarComponent,
  GridComponent,
  MarkPointComponent,
  TooltipComponent,
  VisualMapComponent,
  SVGRenderer,
]);

function clamp(n, lo, hi) {
  return Math.max(lo, Math.min(hi, n));
}

function toTime(d) {
  if (d === null || d === undefined) return null;
  const t = new Date(d).getTime();
  return Number.isNaN(t) ? null : t;
}

// "YYYY-MM-DD" → UTC midnight timestamp (timezone-stable). Falls back to
// Date.parse for anything else.
function parseDay(s) {
  if (s === null || s === undefined) return null;
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(s));
  if (m) return Date.UTC(+m[1], +m[2] - 1, +m[3]);
  const t = new Date(s).getTime();
  return Number.isNaN(t) ? null : t;
}

function isoDay(t) {
  return new Date(t).toISOString().slice(0, 10);
}

function fmtSigned(v, dp = 1) {
  const n = Number(v);
  return `${n >= 0 ? "+" : ""}${n.toFixed(dp)}`;
}

// ---------------------------------------------------------------------------
// Design-token adapter. The ONLY contact between this file and tokens.css:
// read the CSS custom properties once at mount and hand the resolved strings
// to each renderer's config. A token change propagates on reload; nothing
// here can introduce a colour literal. Referenced names are fixed in the
// wave handoff §3 (the token layer) — never a raw hex, never an old name.
// ---------------------------------------------------------------------------
function useTokens() {
  return React.useMemo(() => {
    const cs = getComputedStyle(document.documentElement);
    const get = (name) => cs.getPropertyValue(name).trim();
    return {
      ground: get("--ground"),
      raised: get("--raised"),
      sunken: get("--sunken"),
      edge: get("--edge"),
      hair: get("--hair"),
      ink: get("--ink"),
      ink2: get("--ink-2"),
      ink3: get("--ink-3"),
      ink4: get("--ink-4"),
      risk: get("--risk"),
      up: get("--up"),
      down: get("--down"),
      caution: get("--caution"),
      cautionBg: get("--caution-bg"),
      sans: get("--sans"),
      mono: get("--mono"),
    };
  }, []);
}

// Shared ECharts mount lifecycle: SVG renderer, no animation, ResizeObserver
// -> chart.resize(), dispose on unmount. `build` is re-run whenever `deps`
// change so renderItem closures stay fresh. No-ops while the target element
// is absent (the component renders its compact empty state instead).
function useEChart(elRef, build, deps) {
  React.useEffect(() => {
    const el = elRef.current;
    if (!el) return undefined;
    const chart = echarts.init(el, null, { renderer: "svg" });
    chart.setOption({ animation: false, ...build() });
    const ro = new ResizeObserver(() => chart.resize());
    ro.observe(el);
    return () => {
      ro.disconnect();
      chart.dispose();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
}

// Measures the container width (0 until the element exists and lays out).
function useContainerWidth(elRef) {
  const [w, setW] = React.useState(0);
  React.useEffect(() => {
    const el = elRef.current;
    if (!el) return undefined;
    const measure = () => setW(el.clientWidth);
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  return w;
}

// Shared vega-embed lifecycle: actions off, static render, finalize() on
// cleanup. Embeds once the container has a width and `build()` returns a
// spec; re-embeds when props or the measured width change (`deps` includes
// the width). The wrapper is cleared before each embed so SVGs never stack.
function useVega(elRef, build, deps) {
  const width = useContainerWidth(elRef);
  React.useEffect(() => {
    const el = elRef.current;
    if (!el || width <= 0) return undefined;
    const spec = build();
    if (!spec) return undefined;
    let view = null;
    let cancelled = false;
    el.textContent = "";
    embed(el, spec, { actions: false })
      .then((res) => {
        if (cancelled) {
          res.view.finalize();
          return;
        }
        view = res.view;
      })
      .catch(() => {
        /* a failed embed must not take the screen down; the empty state
           contract covers genuinely empty payloads, this guards renderer
           failures only */
      });
    return () => {
      cancelled = true;
      if (view) view.finalize();
      view = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps.concat([width]));
  return width;
}

// Compact labelled empty state: ONE muted line, ~12px, --ink-3 (rendered by
// the shared .chart-empty class). Never a large framed SVG, never null.
function ChartEmpty({ reason }) {
  return (
    <div role="img" aria-label={reason} className="chart-empty">
      {reason}
    </div>
  );
}

// ---------------------------------------------------------------------------
// 2.1 — PositionBars: one row per position on a SHARED time axis. The point
// is that rows are comparable, so clustering in time is visible at a glance.
// The Ledger's signature element. Rendered through an ECharts custom series:
// one lane per row on a shared time domain, a --sunken lane track, a clip
// spanning entry→exit, and marker dots for adds / stop moves / exits. Clip
// colour: open → --risk · stated positive → --up · stated negative → --down ·
// unstated → --ink-4. SVG renderer keeps the marks crisp.
// ---------------------------------------------------------------------------
export function PositionBars({ from, to, rows, onRowClick }) {
  const list = React.useMemo(() => rows || [], [rows]);
  const elRef = React.useRef(null);
  const tokens = useTokens();
  const clickable = typeof onRowClick === "function";

  // window + row-band geometry shared by the option builder and the layout
  const { fromT, toT } = React.useMemo(() => {
    if (list.length === 0) {
      return { fromT: Date.now() - 30 * 86400000, toT: Date.now() };
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
    return { fromT, toT };
  }, [list, from, to]);

  // Clip colour: the contract's four states, in order of precedence.
  const clipTint = React.useCallback(
    (row) => {
      if (!row.end) return tokens.risk; // still open — money still risked
      if (row.result > 0) return tokens.up; // stated positive result
      if (row.result < 0) return tokens.down; // stated negative result
      return tokens.ink4; // closed with the result unstated
    },
    [tokens]
  );

  const H = 22 + list.length * 18 + 6;
  const fmtDate = (t) =>
    new Date(t).toLocaleDateString("en-IN", { day: "2-digit", month: "short" });

  // data item 0 paints the shared grid + date labels; items 1..N paint one
  // row each so the click dataIndex maps straight to the row
  const data = React.useMemo(
    () =>
      [{ value: [fromT, 0] }].concat(
        list.map((row, i) => ({ value: [fromT, i], row }))
      ),
    [list, fromT]
  );

  useEChart(
    elRef,
    () => {
      const ticks = [0, 1 / 3, 2 / 3, 1].map((f) => fromT + f * (toT - fromT));
      const bottom = 22 + list.length * 18;
      return {
        grid: { left: 150, right: 78, top: 22, bottom: 6, containLabel: false },
        xAxis: {
          type: "time",
          min: fromT,
          max: toT,
          axisLine: { show: false },
          axisTick: { show: false },
          axisLabel: { show: false },
          splitLine: { show: false },
        },
        yAxis: {
          type: "category",
          data: list.map((_, i) => i),
          axisLine: { show: false },
          axisTick: { show: false },
          axisLabel: { show: false },
          splitLine: { show: false },
        },
        tooltip: {
          trigger: "item",
          confine: true,
          formatter: (p) => {
            const row = list[p.dataIndex - 1];
            if (!row) return "";
            return row.warn
              ? `⚠ ${row.warn}`
              : `${row.label}${row.sublabel ? ` · ${row.sublabel}` : ""}`;
          },
        },
        series: [
          {
            type: "custom",
            clip: false,
            data,
            renderItem(p, api) {
              if (p.dataIndex === 0) {
                const l = api.coord([fromT, 0])[0];
                const r = api.coord([toT, 0])[0];
                const children = [];
                ticks.forEach((t) => {
                  const x = l + ((t - fromT) / (toT - fromT)) * (r - l);
                  children.push({
                    type: "line",
                    shape: { x1: x, x2: x, y1: 22, y2: bottom },
                    style: { stroke: tokens.hair, lineWidth: 1 },
                  });
                  children.push({
                    type: "text",
                    style: {
                      text: fmtDate(t),
                      x,
                      y: 12,
                      align: "center",
                      verticalAlign: "middle",
                      fontFamily: tokens.sans,
                      fontSize: 11,
                      fill: tokens.ink3,
                    },
                  });
                });
                return { type: "group", children };
              }

              const row = list[p.dataIndex - 1];
              const cy = api.coord([fromT, p.dataIndex - 1])[1];
              const l = api.coord([fromT, 0])[0];
              const r = api.coord([toT, 0])[0];
              const gx = (t) =>
                clamp(l + ((t - fromT) / (toT - fromT)) * (r - l), l, r);
              const startT = toTime(row.start);
              const endT = toTime(row.end);
              const x1 = startT !== null ? gx(startT) : l;
              const x2 = gx(endT ?? toT);
              const color = clipTint(row);
              const children = [];

              // the lane track: --sunken, one per row, spanning the plot
              children.push({
                type: "rect",
                shape: { x: l, y: cy - 9, width: r - l, height: 18 },
                style: { fill: tokens.sunken },
              });

              // full-width transparent hit band — the same click surface as
              // the old SVG row (Ledger opens the position detail through it)
              if (clickable) {
                children.push({
                  type: "rect",
                  shape: { x: 0, y: cy - 9, width: api.getWidth() + 228, height: 18 },
                  style: { fill: "transparent", cursor: "pointer" },
                });
              }

              // row label (label · sublabel · ⚠warn), right-aligned into the
              // label column — same composition as the old SVG
              const richText =
                `{b|${row.label}}` +
                (row.sublabel ? `{s| · ${row.sublabel}}` : "") +
                (row.warn ? `{w| ⚠}` : "");
              children.push({
                type: "text",
                style: {
                  text: richText,
                  rich: {
                    b: { fontWeight: 700, fill: tokens.ink, fontSize: 11 },
                    s: { fill: tokens.ink3, fontSize: 11 },
                    w: { fill: tokens.caution, fontSize: 11 },
                  },
                  x: l - 8,
                  y: cy,
                  align: "right",
                  verticalAlign: "middle",
                  fontFamily: tokens.sans,
                  fontSize: 11,
                },
              });

              // the clip: entry→exit on the lane
              children.push({
                type: "line",
                shape: { x1, y1: cy, x2, y2: cy },
                style: { stroke: color, lineWidth: 2 },
              });
              children.push({
                type: "circle",
                shape: { cx: x1, cy, r: 3 },
                style: { fill: color },
              });
              if (endT !== null) {
                children.push({
                  type: "circle",
                  shape: { cx: x2, cy, r: 3.5 },
                  style: { fill: tokens.sunken, stroke: color, lineWidth: 1.5 },
                });
              } else {
                children.push({
                  type: "polygon",
                  shape: {
                    points: [
                      [x2 - 1, cy - 4],
                      [x2 + 6, cy],
                      [x2 - 1, cy + 4],
                    ],
                  },
                  style: { fill: color },
                });
              }

              // marker dots for adds / stop moves / exits on the lane
              (row.events || []).forEach((ev) => {
                const et = toTime(ev.at);
                if (et === null) return;
                const ex = clamp(gx(et), Math.min(x1, x2), Math.max(x1, x2));
                if (ev.kind === "add") {
                  children.push({
                    type: "circle",
                    shape: { cx: ex, cy, r: 2.5 },
                    style: { fill: tokens.ink },
                  });
                } else if (ev.kind === "sl_up") {
                  children.push({
                    type: "polygon",
                    shape: {
                      points: [
                        [ex - 3, cy + 2],
                        [ex + 3, cy + 2],
                        [ex, cy - 4],
                      ],
                    },
                    style: { fill: tokens.ink2 },
                  });
                } else if (ev.kind === "sl_down") {
                  children.push({
                    type: "polygon",
                    shape: {
                      points: [
                        [ex - 3, cy - 2],
                        [ex + 3, cy - 2],
                        [ex, cy + 4],
                      ],
                    },
                    style: { fill: tokens.ink2 },
                  });
                } else if (ev.kind === "exit") {
                  children.push({
                    type: "circle",
                    shape: { cx: ex, cy, r: 3.5 },
                    style: {
                      fill: tokens.sunken,
                      stroke: tokens.ink2,
                      lineWidth: 1.5,
                    },
                  });
                }
              });

              children.push({
                type: "text",
                style: {
                  text:
                    row.result != null
                      ? `${fmtSigned(row.result)}%`
                      : endT !== null
                        ? "—"
                        : "open",
                  x: api.getWidth() + 220,
                  y: cy,
                  align: "right",
                  verticalAlign: "middle",
                  fontFamily: tokens.mono,
                  fontSize: 11,
                  fill: color,
                },
              });
              return { type: "group", children };
            },
          },
        ],
      };
    },
    [list, fromT, toT, tokens, clickable, data, clipTint] // eslint-disable-line react-hooks/exhaustive-deps
  );

  // map ECharts clicks to the row id — only series rows, only when wired
  React.useEffect(() => {
    const el = elRef.current;
    if (!el || !clickable) return undefined;
    const chart = echarts.getInstanceByDom(el);
    if (!chart) return undefined;
    const h = (p) => {
      if (
        p.componentType === "series" &&
        p.seriesType === "custom" &&
        p.dataIndex >= 1
      ) {
        const row = list[p.dataIndex - 1];
        if (row != null) onRowClick(row.id);
      }
    };
    chart.on("click", h);
    return () => chart.off("click", h);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [list, onRowClick, clickable]);

  if (list.length === 0) {
    return (
      <ChartEmpty reason="No positions reconstructed yet — nothing to place on the timeline." />
    );
  }

  let openCount = 0;
  let posCount = 0;
  let negCount = 0;
  list.forEach((r) => {
    if (!r.end) openCount += 1;
    else if (r.result > 0) posCount += 1;
    else if (r.result < 0) negCount += 1;
  });
  const ariaLabel =
    `${list.length} position${list.length === 1 ? "" : "s"} on the ledger timeline; ` +
    `${openCount} still open, ${posCount} positive, ${negCount} negative.`;

  return (
    <div
      ref={elRef}
      role="img"
      aria-label={ariaLabel}
      className="chart-echarts"
      style={{ height: H }}
    />
  );
}

// ---------------------------------------------------------------------------
// 2.2 — Dumbbell: two dots joined by a rule. The GAP is the finding.
// Rendered through Vega-Lite as ONE shared view (no facet): every row's marks
// are positioned by a per-row pixel y and one shared x scale, so the whole
// chart keeps the old label column and right-hand result column exactly.
// ---------------------------------------------------------------------------
// `n` added to the contract 2026-08-23: VISUAL_LANGUAGE §1 requires a
// denominator beside every percentage. Optional — renders "n=..." after the
// row label when supplied. Colour resolves through the wave tokens: the rule
// turns --caution when the gap exceeds gapWarn.
const DUMB_LABEL_W = 160;
const DUMB_RIGHT_W = 110;
const DUMB_PAD_R = 10;

export function Dumbbell({ rows, max, gapWarn = 10, suffix = "", n = null }) {
  const list = React.useMemo(() => rows || [], [rows]);
  const elRef = React.useRef(null);
  const tokens = useTokens();
  const H = 20 + list.length * 36;

  const width = useVega(
    elRef,
    () => {
      if (width <= 0) return null;
      const domainMax =
        max ||
        Math.max(
          10,
          ...list.flatMap((r) => [r.a?.value ?? 0, r.b?.value ?? 0])
        ) * 1.05;
      const xRange = [
        DUMB_LABEL_W,
        Math.max(width - DUMB_RIGHT_W - DUMB_PAD_R, DUMB_LABEL_W + 40),
      ];
      const yScale = { domain: [0, H], range: [H, 0] };
      const X = (field) => ({
        field,
        type: "quantitative",
        scale: { domain: [0, domainMax], range: xRange },
        axis: null,
      });
      const Y = (field) => ({
        field,
        type: "quantitative",
        scale: yScale,
        axis: null,
      });
      const values = list.map((r, i) => {
        const aV = r.a?.value ?? 0;
        const bV = r.b?.value ?? 0;
        const gap = Math.abs(aV - bV);
        const weaker = aV <= bV ? r.a : r.b;
        const stronger = aV <= bV ? r.b : r.a;
        const nShown = r.n != null || n != null ? ` n=${r.n ?? n}` : "";
        const rowTop = 10 + i * 36;
        return {
          wa: weaker?.value ?? 0,
          sa: stronger?.value ?? 0,
          wl: weaker?.label ?? "",
          sl: stronger?.label ?? "",
          yvRule: rowTop + 16,
          yvMid: rowTop + 19,
          yvLabels: rowTop + 32,
          xRow: 0,
          xRes: domainMax,
          rowLabel: `${r.label}${nShown}`,
          res: `${aV}${suffix} → ${bV}${suffix}`,
          warn: gap > gapWarn,
        };
      });
      return {
        width,
        height: H,
        config: { view: { stroke: "transparent" } },
        data: { values },
        layer: [
          {
            mark: { type: "rule", strokeWidth: 2 },
            encoding: {
              x: X("wa"),
              x2: { field: "sa", type: "quantitative" },
              y: Y("yvRule"),
              stroke: {
                condition: { test: "datum.warn", value: tokens.caution },
                value: tokens.ink3,
              },
            },
          },
          {
            mark: {
              type: "point",
              size: 50, // r 4
              fill: tokens.ground,
              stroke: tokens.ink2,
              strokeWidth: 1.5,
            },
            encoding: { x: X("wa"), y: Y("yvRule") },
          },
          {
            mark: { type: "point", size: 64, fill: tokens.ink2 }, // r 4.5
            encoding: { x: X("sa"), y: Y("yvRule") },
          },
          {
            mark: {
              type: "text",
              fontSize: 11,
              font: tokens.sans,
              fontWeight: 600,
              color: tokens.ink2,
              align: "right",
              dx: -8,
            },
            encoding: {
              x: X("xRow"),
              y: Y("yvMid"),
              text: { field: "rowLabel" },
            },
          },
          {
            mark: {
              type: "text",
              fontSize: 11,
              font: tokens.sans,
              color: tokens.ink3,
              align: "center",
            },
            encoding: { x: X("wa"), y: Y("yvLabels"), text: { field: "wl" } },
          },
          {
            mark: {
              type: "text",
              fontSize: 11,
              font: tokens.sans,
              color: tokens.ink3,
              align: "center",
            },
            encoding: { x: X("sa"), y: Y("yvLabels"), text: { field: "sl" } },
          },
          {
            mark: {
              type: "text",
              fontSize: 11,
              font: tokens.mono,
              align: "right",
              dx: DUMB_RIGHT_W - 10 + DUMB_PAD_R,
            },
            encoding: {
              x: X("xRes"),
              y: Y("yvMid"),
              text: { field: "res" },
              fill: {
                condition: { test: "datum.warn", value: tokens.caution },
                value: tokens.ink2,
              },
            },
          },
        ],
      };
    },
    [list, max, gapWarn, suffix, n, tokens, H]
  );

  if (list.length === 0) {
    return <ChartEmpty reason="No stated-vs-actual pair to compare yet." />;
  }

  const summary = list
    .map((r) => {
      const gap = Math.abs((r.a?.value ?? 0) - (r.b?.value ?? 0));
      return `${r.label}: ${r.a?.label} ${r.a?.value}${suffix} vs ${r.b?.label} ${r.b?.value}${suffix}, gap ${gap.toFixed(1)}${suffix}`;
    })
    .join("; ");

  return (
    <div
      role="img"
      aria-label={summary}
      className="chart-vega"
      style={{ height: H }}
    >
      {/* vega-embed promotes its target container itself and overwrites its
          role/aria-label, so it embeds into this inner div and the outer
          wrapper carries the contract's role="img" + finding aria-label. */}
      <div ref={elRef} className="chart-vega-inner" style={{ height: H }} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// 2.3 — StripPlot: one tick per observation on a shared axis, median ruled.
// Rendered through Vega-Lite on a fixed 72px-tall view: observation ticks,
// the 2px ink axis, tick marks + labels, and the median triangle + caption
// are all layered rule/text/point marks.
// ---------------------------------------------------------------------------
export function StripPlot({ values, median, suffix = "" }) {
  const vals = React.useMemo(
    () => (values || []).filter((v) => v !== null && v !== undefined),
    [values]
  );
  const elRef = React.useRef(null);
  const tokens = useTokens();
  const H = 72;

  const width = useVega(
    elRef,
    () => {
      if (width <= 0) return null;
      const rawMax = Math.max(...vals, median || 0);
      const dmax = Math.max(5, Math.ceil((rawMax * 1.1) / 5) * 5);
      const xScale = {
        domain: [0, dmax],
        range: [34, Math.max(width - 34, 74)],
      };
      const yScale = { domain: [0, 72], range: [72, 0] };
      const tickCount = 6;
      const ticks = Array.from(
        { length: tickCount + 1 },
        (_, i) => Math.round((dmax / tickCount) * i)
      );
      const observations = vals.map((v) => ({
        v,
        y2: 58, // pixel 14
        y1: 38, // pixel 34
      }));
      const tickData = ticks.map((t) => ({
        t,
        y2: 38, // pixel 34
        y1: 34, // pixel 38
        tlY: 23, // pixel 49
      }));
      const medData = [
        { m: median, mY: 38, tY: 10 }, // pixels 34 and 62
      ];
      const X = (field, extra = {}) => ({
        field,
        type: "quantitative",
        scale: xScale,
        axis: null,
        ...extra,
      });
      const Y = (field) => ({
        field,
        type: "quantitative",
        scale: yScale,
        axis: null,
      });

      const layers = [
        {
          data: { values: observations },
          mark: { type: "rule", stroke: tokens.ink, strokeWidth: 1.5 },
          encoding: {
            x: X("v"),
            y: Y("y2"),
            y2: { field: "y1", type: "quantitative", scale: yScale },
          },
        },
        {
          data: { values: [{ x1: 0, x2: dmax, yr: 38 }] },
          mark: { type: "rule", stroke: tokens.ink, strokeWidth: 2 },
          encoding: {
            x: { field: "x1", type: "quantitative", scale: xScale, axis: null },
            x2: { field: "x2", type: "quantitative", scale: xScale },
            y: { field: "yr", type: "quantitative", scale: yScale, axis: null },
            y2: { field: "yr", type: "quantitative", scale: yScale },
          },
        },
        {
          data: { values: tickData },
          mark: { type: "rule", stroke: tokens.hair, strokeWidth: 1 },
          encoding: {
            x: X("t"),
            y: Y("y2"),
            y2: { field: "y1", type: "quantitative", scale: yScale },
          },
        },
        {
          data: { values: tickData },
          mark: {
            type: "text",
            fontSize: 11,
            font: tokens.sans,
            color: tokens.ink3,
            align: "center",
          },
          encoding: {
            x: X("t"),
            y: Y("tlY"),
            text: { field: "t" },
          },
        },
      ];
      if (median != null) {
        layers.push(
          {
            data: { values: medData },
            mark: {
              type: "point",
              shape: "triangle",
              size: 26,
              fill: tokens.ink,
              stroke: tokens.ink,
            },
            encoding: {
              x: X("m"),
              y: Y("mY"),
            },
          },
          {
            data: { values: medData },
            mark: {
              type: "text",
              fontSize: 11,
              font: tokens.mono,
              color: tokens.ink2,
              align: "center",
            },
            encoding: {
              x: X("m"),
              y: Y("tY"),
              text: { value: `median ${median}${suffix} · n=${vals.length}` },
            },
          }
        );
      }
      return {
        width,
        height: 72,
        config: { view: { stroke: "transparent" } },
        layer: layers,
      };
    },
    [vals, median, suffix, tokens, H]
  );

  if (vals.length === 0) {
    return <ChartEmpty reason="No observations yet." />;
  }

  const label =
    `n=${vals.length} observations${median != null ? `, median ${median}${suffix}` : ""}.`;

  return (
    <div
      role="img"
      aria-label={label}
      className="chart-vega"
      style={{ height: H }}
    >
      <div ref={elRef} className="chart-vega-inner" style={{ height: H }} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// 2.4 — BandLine: a line with its threshold bands drawn as flat background
// rects. Generalises the XP chart (Market: cumulative advance–decline).
// Rendered through ECharts: a custom series paints the flat band rects and
// the fear/quiet band labels; a standard line series draws the trend; a
// markPoint marks the latest value. Linear or log y scale.
// ---------------------------------------------------------------------------
export function BandLine({ points, bands, log }) {
  const pts = React.useMemo(
    () => (points || []).filter((p) => p.y !== null && p.y !== undefined),
    [points]
  );
  const bandList = React.useMemo(() => bands || [], [bands]);
  const elRef = React.useRef(null);
  const tokens = useTokens();
  const H = 150;

  useEChart(
    elRef,
    () => {
      const PADL = 6;
      const PADR = 58;
      const n = pts.length;
      const bandMax = bandList.length ? bandList[bandList.length - 1].at : 0;
      const dataMax = Math.max(...pts.map((p) => p.y));
      const domainMax = Math.max(bandMax, dataMax) * 1.02 || 1;
      const safeMax = log ? Math.max(domainMax, 2) : domainMax;
      const boundaries = [0].concat(bandList.map((b) => b.at));
      const last = pts[n - 1];
      const lastYv = log ? Math.max(last.y, 1) : last.y;
      const numericLast =
        typeof last.y === "number"
          ? last.y
          : typeof last.y === "string" && last.y.trim() !== ""
            ? Number(last.y)
            : NaN;
      const latestValue = Number.isFinite(numericLast)
        ? numericLast.toFixed(1)
        : String(last.y);

      return {
        grid: { left: PADL, right: PADR, top: 12, bottom: 16 },
        xAxis: {
          type: "category",
          boundaryGap: false,
          data: pts.map((p, i) =>
            p.x != null && String(p.x) !== "" ? String(p.x) : String(i)
          ),
          axisLine: { show: false },
          axisTick: { show: false },
          axisLabel: { show: false },
          splitLine: { show: false },
        },
        yAxis: log
          ? {
              type: "log",
              min: 1,
              max: safeMax,
              axisLine: { show: false },
              axisTick: { show: false },
              axisLabel: { show: false },
              splitLine: { show: false },
            }
          : {
              type: "value",
              min: 0,
              max: domainMax,
              axisLine: { show: false },
              axisTick: { show: false },
              axisLabel: { show: false },
              splitLine: { show: false },
            },
        series: [
          {
            // flat threshold-band rects behind the line
            type: "custom",
            silent: true,
            z: 0,
            data: bandList.map((_, i) => ({ band: i })),
            renderItem(p, api) {
              const bi = p.dataIndex;
              const low = Math.max(boundaries[bi], log ? 1 : 0);
              const high = Math.max(
                bi + 1 < boundaries.length ? boundaries[bi + 1] : domainMax,
                log ? 1 : 0
              );
              const yLow = api.coord([0, low])[1];
              const yHigh = api.coord([0, high])[1];
              const children = [
                {
                  type: "rect",
                  shape: {
                    x: 0,
                    y: Math.min(yLow, yHigh),
                    width: api.getWidth(),
                    height: Math.max(1, Math.abs(yHigh - yLow)),
                  },
                  style: { fill: tokens.sunken },
                },
              ];
              // 1px hairline at the band's upper threshold
              if (bi + 1 < boundaries.length) {
                children.push({
                  type: "line",
                  shape: {
                    x1: 0,
                    x2: api.getWidth(),
                    y1: yHigh,
                    y2: yHigh,
                  },
                  style: { stroke: tokens.hair, lineWidth: 1 },
                });
              }
              // band label at the band's midpoint, in the right margin
              const midPx = (yLow + yHigh) / 2;
              children.push({
                type: "text",
                style: {
                  text: bandList[bi].label,
                  x: api.getWidth() + 6,
                  y: midPx,
                  align: "left",
                  verticalAlign: "middle",
                  fontFamily: tokens.sans,
                  fontSize: 11,
                  fill: tokens.ink3,
                },
              });
              return { type: "group", children };
            },
          },
          {
            // the trend line (quiet: no accent colour on Market)
            type: "line",
            z: 2,
            data: pts.map((p) => (log ? Math.max(p.y, 1) : p.y)),
            symbol: "none",
            smooth: false,
            lineStyle: { width: 2, color: tokens.ink2 },
            markPoint: {
              symbol: "circle",
              symbolSize: 5,
              itemStyle: { color: tokens.ink, borderColor: tokens.ink },
              label: {
                show: true,
                position: "right",
                color: tokens.ink2,
                fontFamily: tokens.mono,
                fontSize: 11,
                formatter: () => latestValue,
              },
              data: [{ coord: [n - 1, lastYv] }],
            },
          },
        ],
      };
    },
    [pts, bandList, log, tokens, H] // eslint-disable-line react-hooks/exhaustive-deps
  );

  if (pts.length === 0) {
    return <ChartEmpty reason="No series data yet." />;
  }

  const last = pts[pts.length - 1];
  const numericLast =
    typeof last.y === "number"
      ? last.y
      : typeof last.y === "string" && last.y.trim() !== "" ? Number(last.y) : NaN;
  const latestValue = Number.isFinite(numericLast)
    ? numericLast.toFixed(1)
    : String(last.y);
  const bandLabel = bandList.length
    ? bandList.find((b) => last.y <= b.at)?.label || bandList[bandList.length - 1].label
    : null;
  const ariaLabel =
    `Trend: ${pts.length} points, latest ${latestValue}${bandLabel ? ` (${bandLabel})` : ""}.`;

  return (
    <div
      role="img"
      aria-label={ariaLabel}
      className="chart-echarts"
      style={{ height: H }}
    >
      <div ref={elRef} style={{ width: "100%", height: H }} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// 2.5 — Ribbon: one hard block per session, categorical state over time.
// Generalises the MBI ribbon. Inline SVG (trivial, no library — the ladder's
// choice for the day-colour ribbon): one flat rect per session on a shared
// scale, stretched to the container width via viewBox. State colours resolve
// through the tokens: GREEN → --up · WHITE → --sunken (edge-stroked) · RED →
// --down · NONE → transparent with a hair outline. A warning dot sits above
// each flagged session.
// ---------------------------------------------------------------------------
const RIBBON_PITCH = 11; // 9px block + 2px gap
const RIBBON_H = 26;

export function Ribbon({ cells }) {
  const list = React.useMemo(() => cells || [], [cells]);
  const tokens = useTokens();

  if (list.length === 0) {
    return <ChartEmpty reason="No sessions recorded yet." />;
  }

  const counts = list.reduce(
    (acc, c) => {
      acc[c.state] = (acc[c.state] || 0) + 1;
      if (c.warn) acc.warn += 1;
      return acc;
    },
    { GREEN: 0, WHITE: 0, RED: 0, NONE: 0, warn: 0 }
  );
  const ariaLabel =
    `${list.length} sessions: ${counts.GREEN} green, ${counts.WHITE} white, ${counts.RED} red` +
    `${counts.warn ? `, ${counts.warn} warning day(s)` : ""}.`;

  const fillFor = {
    GREEN: tokens.up,
    WHITE: tokens.sunken,
    RED: tokens.down,
    NONE: tokens.ground,
  };
  const strokeFor = {
    GREEN: "none",
    WHITE: tokens.edge,
    RED: "none",
    NONE: tokens.hair,
  };

  return (
    <div
      role="img"
      aria-label={ariaLabel}
      style={{ width: "100%", height: RIBBON_H }}
    >
      <svg
        viewBox={`0 0 ${list.length * RIBBON_PITCH} ${RIBBON_H}`}
        preserveAspectRatio="none"
        aria-hidden="true"
        focusable="false"
        style={{ width: "100%", height: RIBBON_H, display: "block" }}
      >
        {list.map((cell, i) => (
          <g key={cell.key || i}>
            <rect
              x={i * RIBBON_PITCH}
              y={4}
              width={9}
              height={22}
              fill={fillFor[cell.state] || fillFor.NONE}
              stroke={strokeFor[cell.state] || strokeFor.NONE}
              strokeWidth={1}
              vectorEffect="non-scaling-stroke"
            />
            {cell.warn && (
              <circle
                cx={i * RIBBON_PITCH + 4.5}
                cy={3}
                r={1.6}
                fill={tokens.caution}
              />
            )}
          </g>
        ))}
      </svg>
    </div>
  );
}

// ---------------------------------------------------------------------------
// 2.6 — StackedStrip: one bar split proportionally, segments labelled in
// place. Never a pie. Categories carry no state, so segments differ by
// monochrome ink shade, never by hue. Rendered through Vega-Lite.
// ---------------------------------------------------------------------------
// `n` and `suffix` added to the contract 2026-08-23 for the same reason as
// Dumbbell: a composition shown as percentages without its denominator
// violates VISUAL_LANGUAGE §1.
// Caption carrying the denominator. Kept outside the chart so it wraps and
// scales with the surrounding type.
function StripCaption({ n, total }) {
  if (n == null) return null;
  return <div className="chart-caption">n={n} · total {total}</div>;
}

export function StackedStrip({ segments, n = null, suffix = "" }) {
  const list = React.useMemo(
    () => (segments || []).filter((s) => (s.value || 0) > 0),
    [segments]
  );
  const elRef = React.useRef(null);
  const tokens = useTokens();
  const total = list.reduce((sum, s) => sum + s.value, 0);
  const H = 30;

  const width = useVega(
    elRef,
    () => {
      if (width <= 0 || total <= 0) return null;
      const fills = [tokens.ink, tokens.ink2, tokens.ink3, tokens.ink4];
      let acc = 0;
      const parts = list.map((s, i) => {
        const seg = {
          cum: acc,
          cum2: acc + s.value,
          mid: acc + s.value / 2,
          fi: i % 4,
          y0: 0,
          y1: 1,
          ymid: 0.5,
          lab: `${s.label} ${s.value}${suffix}`,
        };
        acc += s.value;
        return seg;
      });
      const xScale = { domain: [0, total], range: [0, width] };
      const yScale = { domain: [0, 1], range: [30, 0] };
      const X = (field) => ({
        field,
        type: "quantitative",
        scale: xScale,
        axis: null,
      });
      const Y = (field) => ({
        field,
        type: "quantitative",
        scale: yScale,
        axis: null,
      });
      return {
        width,
        height: 30,
        config: { view: { stroke: "transparent" } },
        data: { values: parts },
        layer: [
          {
            // hard-ended segments separated by a 1px ground rule
            mark: { type: "rect", stroke: tokens.ground, strokeWidth: 1 },
            encoding: {
              x: X("cum"),
              x2: { field: "cum2", type: "quantitative", scale: xScale },
              y: Y("y0"),
              y2: { field: "y1", type: "quantitative", scale: yScale },
              fill: {
                condition: [
                  { test: "datum.fi === 1", value: fills[1] },
                  { test: "datum.fi === 2", value: fills[2] },
                  { test: "datum.fi === 3", value: fills[3] },
                ],
                value: fills[0],
              },
            },
          },
          {
            // labelled in place: dark text on light shades, ink text on dark
            mark: {
              type: "text",
              fontSize: 11,
              font: tokens.sans,
              align: "center",
              dy: 4,
            },
            encoding: {
              x: X("mid"),
              y: Y("ymid"),
              text: { field: "lab" },
              fill: {
                condition: { test: "datum.fi < 2", value: tokens.ground },
                value: tokens.ink,
              },
            },
          },
        ],
      };
    },
    [list, suffix, tokens, total, H]
  );

  if (list.length === 0 || total <= 0) {
    return <ChartEmpty reason="No composition data yet." />;
  }

  const ariaLabel =
    `Composition: ${list.map((s) => `${s.label} ${s.value}`).join(", ")}.`;

  return (
    <>
      <div
        role="img"
        aria-label={ariaLabel}
        className="chart-vega"
        style={{ height: H }}
      >
        <div ref={elRef} className="chart-vega-inner" style={{ height: H }} />
      </div>
      <StripCaption n={n} total={total} />
    </>
  );
}

// ---------------------------------------------------------------------------
// 2.7 — SmallMultiples: a grid of identical miniature charts on a SHARED
// scale. Do not merge into one big combined chart. Rendered through ECharts:
// a custom series where each panel is one data item, sharing one |v| domain.
// ---------------------------------------------------------------------------
export function SmallMultiples({ items }) {
  const list = React.useMemo(() => items || [], [items]);
  const elRef = React.useRef(null);
  const tokens = useTokens();

  useEChart(
    elRef,
    () => {
      const sharedMax = Math.max(
        1,
        ...list.flatMap((it) => it.values || []).map((v) => Math.abs(v))
      );
      return {
        grid: { left: 0, right: 0, top: 0, bottom: 0 },
        xAxis: { type: "value", min: 0, max: 1, show: false },
        yAxis: { type: "value", min: 0, max: 1, show: false },
        series: [
          {
            type: "custom",
            clip: false,
            data: list.map((it, i) => ({ value: [i, 0], it })),
            renderItem(p, api) {
              const it = list[p.dataIndex];
              const panelW = api.getWidth() / list.length;
              const baseX = p.dataIndex * panelW;
              const vals = it.values || [];
              const barW = vals.length ? (panelW - 16) / vals.length : 0;
              const children = [];
              if (p.dataIndex > 0) {
                children.push({
                  type: "line",
                  shape: { x1: baseX, x2: baseX, y1: 4, y2: 96 },
                  style: { stroke: tokens.hair, lineWidth: 1 },
                });
              }
              children.push({
                type: "text",
                style: {
                  text: it.label,
                  x: baseX + 8,
                  y: 12,
                  align: "left",
                  verticalAlign: "middle",
                  fontFamily: tokens.sans,
                  fontWeight: 700,
                  fontSize: 11,
                  fill: tokens.ink,
                },
              });
              children.push({
                type: "line",
                shape: {
                  x1: baseX + 8,
                  x2: baseX + panelW - 8,
                  y1: 78,
                  y2: 78,
                },
                style: { stroke: tokens.ink, lineWidth: 2 },
              });
              vals.forEach((v, j) => {
                const h = (Math.abs(v) / sharedMax) * 56;
                const x = baseX + 8 + j * barW;
                children.push({
                  type: "rect",
                  shape: {
                    x,
                    y: 78 - h,
                    width: Math.max(1, barW - 1),
                    height: h,
                  },
                  style: { fill: tokens.ink2 },
                });
              });
              if (it.caption) {
                children.push({
                  type: "text",
                  style: {
                    text: it.caption,
                    x: baseX + 8,
                    y: 95,
                    align: "left",
                    verticalAlign: "middle",
                    fontFamily: tokens.mono,
                    fontSize: 11,
                    fill: tokens.ink3,
                  },
                });
              }
              return { type: "group", children };
            },
          },
        ],
      };
    },
    [list, tokens]
  );

  if (list.length === 0) {
    return <ChartEmpty reason="No series to compare yet." />;
  }

  const ariaLabel =
    `${list.length} series on a shared scale: ` +
    list.map((it) => `${it.label} ${it.caption || ""}`.trim()).join("; ") +
    ".";

  return (
    <div
      ref={elRef}
      role="img"
      aria-label={ariaLabel}
      className="chart-echarts"
      style={{ height: 100 }}
    />
  );
}

// ---------------------------------------------------------------------------
// 2.10 — StackedArea: play-type mix over time (Traders). Rendered through
// ECharts as a stacked area over a category time axis. Play types are
// categories with no state, so the stacks differ by ink shade, never by hue.
// Never a pie. `.chart-empty` when rows is empty.
// ---------------------------------------------------------------------------
export function StackedArea({ rows, n = null, suffix = "" }) {
  const list = React.useMemo(() => rows || [], [rows]);
  const elRef = React.useRef(null);
  const tokens = useTokens();

  const { xCats, labels, seriesData, totals } = React.useMemo(() => {
    const cats = list.map((r) => r.x);
    const labs = [];
    list.forEach((r) =>
      (r.segments || []).forEach((s) => {
        if (!labs.includes(s.label)) labs.push(s.label);
      })
    );
    const per = labs.map((l) =>
      list.map((r) => {
        const seg = (r.segments || []).find((s) => s.label === l);
        const v = seg != null ? Number(seg.value) : 0;
        return Number.isFinite(v) ? v : 0;
      })
    );
    const tots = labs.map((l, i) => per[i].reduce((a, b) => a + b, 0));
    return { xCats: cats, labels: labs, seriesData: per, totals: tots };
  }, [list]);

  const H = 170;
  const fills = [tokens.ink, tokens.ink2, tokens.ink3, tokens.ink4];

  useEChart(
    elRef,
    () => ({
      grid: { left: 8, right: 12, top: 10, bottom: 32, containLabel: true },
      legend: {
        bottom: 0,
        left: "center",
        itemWidth: 8,
        itemHeight: 8,
        itemGap: 10,
        textStyle: { color: tokens.ink3, fontSize: 11 },
        data: labels,
      },
      tooltip: {
        trigger: "axis",
        confine: true,
        valueFormatter: (v) => `${v}${suffix}`,
      },
      xAxis: {
        type: "category",
        data: xCats,
        axisLine: { lineStyle: { color: tokens.edge } },
        axisTick: { show: false },
        axisLabel: { color: tokens.ink3, fontSize: 11 },
        splitLine: { show: false },
      },
      yAxis: {
        type: "value",
        min: 0,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: tokens.ink3, fontSize: 11 },
        splitLine: { lineStyle: { color: tokens.hair } },
      },
      series: labels.map((label, i) => ({
        name: label,
        type: "line",
        stack: "total",
        data: seriesData[i],
        symbol: "none",
        smooth: false,
        lineStyle: { width: 1, color: fills[i % fills.length] },
        areaStyle: { color: fills[i % fills.length], opacity: 0.72 },
        itemStyle: { color: fills[i % fills.length] },
      })),
    }),
    [list, labels, xCats, seriesData, suffix, tokens] // eslint-disable-line react-hooks/exhaustive-deps
  );

  if (list.length === 0) {
    return <ChartEmpty reason="No play-type history yet." />;
  }

  const grand = totals.reduce((a, b) => a + b, 0);
  const ariaLabel =
    `Play-type mix over ${list.length} session${list.length === 1 ? "" : "s"}, ` +
    `n=${n != null ? n : grand}, ` +
    labels.map((l, i) => `${l} ${totals[i]}${suffix}`).join("; ") +
    ".";

  return (
    <div
      ref={elRef}
      role="img"
      aria-label={ariaLabel}
      className="chart-echarts"
      style={{ height: H }}
    />
  );
}

// ---------------------------------------------------------------------------
// 2.11 — CalendarGrid: posting cadence (Traders). Rendered through ECharts as
// a calendar heatmap: one hard cell per posting day, weeks × weekdays, with a
// quiet grey ramp for the per-day count. `.chart-empty` when cells is empty.
// ---------------------------------------------------------------------------
export function CalendarGrid({ from, to, cells, caption = "" }) {
  const list = React.useMemo(() => cells || [], [cells]);
  const elRef = React.useRef(null);
  const tokens = useTokens();

  const { fromT, toT } = React.useMemo(() => {
    if (list.length === 0) return { fromT: 0, toT: 0 };
    let f = parseDay(from);
    let t = parseDay(to);
    const dates = list.map((c) => parseDay(c.date)).filter((v) => v !== null);
    if (f === null) f = dates.length ? Math.min(...dates) : Date.now();
    if (t === null) t = dates.length ? Math.max(...dates) : f;
    if (f >= t) t = f + 86400000;
    return { fromT: f, toT: t };
  }, [list, from, to]);

  const { max, maxWeeks } = React.useMemo(() => {
    let mx = 1;
    list.forEach((c) => {
      const v = Number(c.count);
      if (Number.isFinite(v) && v > mx) mx = v;
    });
    // horizontal layout stacks each month's weeks; height needs the tallest
    // month in the range
    let maxW = 1;
    const start = new Date(fromT);
    const end = new Date(toT);
    let y = start.getUTCFullYear();
    let m = start.getUTCMonth();
    while (
      y < end.getUTCFullYear() ||
      (y === end.getUTCFullYear() && m <= end.getUTCMonth())
    ) {
      const daysInMonth = new Date(Date.UTC(y, m + 1, 0)).getUTCDate();
      maxW = Math.max(maxW, Math.ceil(daysInMonth / 7));
      m += 1;
      if (m === 12) {
        m = 0;
        y += 1;
      }
    }
    return { max: mx, maxWeeks: maxW };
  }, [list, fromT, toT]);

  const H = 48 + maxWeeks * 15 + 34;

  useEChart(
    elRef,
    () => ({
      tooltip: {
        trigger: "item",
        confine: true,
        formatter: (p) =>
          p.data
            ? `${p.data[0]}: ${p.data[1]}${caption ? ` ${caption}` : ""}`
            : "",
      },
      visualMap: {
        show: true,
        min: 0,
        max,
        calculable: false,
        orient: "horizontal",
        left: "center",
        bottom: 0,
        itemWidth: 12,
        itemHeight: 9,
        text: [String(max), "0"],
        textStyle: { color: tokens.ink3, fontSize: 11 },
        inRange: {
          color: [
            tokens.sunken,
            tokens.ink4,
            tokens.ink3,
            tokens.ink2,
            tokens.ink,
          ],
        },
      },
      calendar: {
        top: 40,
        left: 40,
        right: 8,
        bottom: 30,
        cellSize: ["auto", 15],
        range: [isoDay(fromT), isoDay(toT)],
        itemStyle: {
          color: tokens.sunken,
          borderWidth: 1,
          borderColor: tokens.edge,
        },
        splitLine: {
          lineStyle: { color: tokens.edge, width: 1 },
        },
        dayLabel: {
          show: true,
          firstDay: 1,
          nameMap: "en",
          color: tokens.ink3,
          fontSize: 11,
        },
        monthLabel: {
          show: true,
          nameMap: "en",
          color: tokens.ink3,
          fontSize: 11,
        },
      },
      series: [
        {
          type: "heatmap",
          coordinateSystem: "calendar",
          data: list.map((c) => {
            const v = Number(c.count);
            return [String(c.date), Number.isFinite(v) ? v : 0];
          }),
        },
      ],
    }),
    [list, fromT, toT, max, caption, tokens] // eslint-disable-line react-hooks/exhaustive-deps
  );

  if (list.length === 0) {
    return <ChartEmpty reason="No posting days recorded yet." />;
  }

  const ariaLabel =
    `Posting cadence: ${list.length} posting day${list.length === 1 ? "" : "s"}` +
    `${from != null ? ` from ${from}` : ""}${to != null ? ` to ${to}` : ""}, ` +
    `busiest day ${max}${caption ? ` ${caption}` : ""}.`;

  return (
    <>
      <div
        ref={elRef}
        role="img"
        aria-label={ariaLabel}
        className="chart-echarts"
        style={{ height: H }}
      />
      {caption && <div className="chart-caption">{caption}</div>}
    </>
  );
}