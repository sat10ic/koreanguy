// House chart vocabulary — VISUAL_LANGUAGE.md §2 and §6 (binding).
//
// Renderer ladder (owner amendment 2026-08-23): the seven exported components
// now render through the binding libraries — Apache ECharts (SVG renderer) for
// terminal/coordinated visuals (PositionBars 2.1, Ribbon 2.5, SmallMultiples
// 2.7) and Vega-Lite via vega-embed for custom analytical graphics (Dumbbell
// 2.2, StripPlot 2.3, BandLine 2.4, StackedStrip 2.6). Nothing here is inline
// SVG anymore.
//
// Contract rules kept from the previous implementation:
//   - Export names and props are identical to VISUAL_LANGUAGE §6.
//   - role="img" + aria-label stating the finding; the label sentences are
//     byte-identical to the inline-SVG version.
//   - Colour resolves ONLY through CSS custom properties (styles/tokens.css):
//     `useTokens()` reads them at the adapter boundary once per mount and the
//     resolved strings are passed into echarts options / Vega-Lite specs. No
//     raw hex literal exists in this file.
//   - Charts are responsive (no fixed pixel widths), never animate on load
//     (echarts option.animation=false; Vega renders statically), and every
//     rendered label is >= 11px (the wave's label floor).
//   - Empty state is ONE compact muted line (evidence-desk revision), never a
//     large framed SVG.
import React from "react";
import * as echarts from "echarts/core";
import { CustomChart } from "echarts/charts";
import { GridComponent, TooltipComponent } from "echarts/components";
import { SVGRenderer } from "echarts/renderers";
import embed from "vega-embed";

echarts.use([CustomChart, GridComponent, TooltipComponent, SVGRenderer]);

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

// ---------------------------------------------------------------------------
// Design-token adapter. The ONLY contact between this file and tokens.css:
// read the CSS custom properties once at mount and hand the resolved strings
// to each renderer's config. A token change propagates on reload; nothing
// here can introduce a colour literal.
// ---------------------------------------------------------------------------
function useTokens() {
  return React.useMemo(() => {
    const cs = getComputedStyle(document.documentElement);
    const get = (name) => cs.getPropertyValue(name).trim();
    return {
      ink: get("--ink"),
      ink2: get("--ink-2"),
      ink3: get("--ink-3"),
      ink4: get("--ink-4"),
      onInk: get("--on-ink"),
      ok: get("--ok"),
      okInk: get("--ok-ink"),
      bad: get("--bad"),
      badInk: get("--bad-ink"),
      warn: get("--warn"),
      warnInk: get("--warn-ink"),
      info: get("--info"),
      infoInk: get("--info-ink"),
      neutral: get("--neutral"),
      neutralFill: get("--neutral-fill"),
      surface: get("--surface"),
      surface2: get("--surface-2"),
      surface3: get("--surface-3"),
      rule: get("--rule"),
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

// Compact labelled empty state (evidence-desk revision): ONE muted line,
// ~12px (--fs-ui), --ink-3. Never a large framed SVG, never null.
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
// Rendered through ECharts: a hidden time/category scale, with a custom
// series painting the shared grid, date labels, and every row's glyphs. SVG
// renderer keeps the marks crisp.
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
                    style: { stroke: tokens.rule, lineWidth: 1 },
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
              const color =
                row.result > 0
                  ? tokens.ok
                  : row.result < 0
                    ? tokens.bad
                    : tokens.neutral;
              const children = [];

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
                    w: { fill: tokens.warnInk, fontSize: 11 },
                  },
                  x: l - 8,
                  y: cy,
                  align: "right",
                  verticalAlign: "middle",
                  fontFamily: tokens.sans,
                  fontSize: 11,
                },
              });

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
                  style: { fill: tokens.surface, stroke: color, lineWidth: 1.5 },
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
                      fill: tokens.surface,
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
    [list, fromT, toT, tokens, clickable, data] // eslint-disable-line react-hooks/exhaustive-deps
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
// chart keeps the old 160px label column and right-hand result column exactly.
// ---------------------------------------------------------------------------
// `n` added to the contract 2026-08-23: VISUAL_LANGUAGE §1 requires a
// denominator beside every percentage, and the original prop list had nowhere
// to put one. Optional -- renders "n=..." after the row label when supplied.
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
                condition: { test: "datum.warn", value: tokens.warn },
                value: tokens.neutral,
              },
            },
          },
          {
            mark: {
              type: "point",
              size: 50, // r 4
              fill: tokens.surface,
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
                condition: { test: "datum.warn", value: tokens.warnInk },
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
          mark: { type: "rule", stroke: tokens.rule, strokeWidth: 1 },
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
              fill: tokens.infoInk,
              stroke: tokens.infoInk,
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
              color: tokens.infoInk,
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
// rects. Generalises the XP chart. Bands are panel-2/panel-3 washes, never
// coloured fills. Rendered through Vega-Lite: band rects, right-side band
// labels, the info line, and the latest-point value are layered marks on a
// linear or log y scale.
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

  const width = useVega(
    elRef,
    () => {
      if (width <= 0 || pts.length === 0) return null;
      const PADL = 6;
      const PADR = 58;
      const plotTop = 12;
      const plotBottom = 134; // 150 - 16
      const n = pts.length;
      const bandMax = bandList.length ? bandList[bandList.length - 1].at : 0;
      const dataMax = Math.max(...pts.map((p) => p.y));
      const domainMax = Math.max(bandMax, dataMax) * 1.02 || 1;
      const safeMax = log ? Math.max(domainMax, 2) : domainMax;

      const yPx = (v) => {
        if (log) {
          const safe = Math.max(v, 1);
          return (
            plotBottom -
            (Math.log(safe) / Math.log(safeMax)) * (plotBottom - plotTop)
          );
        }
        return (
          plotBottom -
          (clamp(v, 0, domainMax) / domainMax) * (plotBottom - plotTop)
        );
      };
      const yDomainOf = (px) => {
        if (log) {
          return Math.pow(safeMax, (plotBottom - px) / (plotBottom - plotTop));
        }
        return ((plotBottom - px) / (plotBottom - plotTop)) * domainMax;
      };
      // band labels sit at the OLD pixel midpoint of each wash (+3), converted
      // back into domain units so the y scale places them identically
      const boundaries = [0].concat(bandList.map((b) => b.at));
      const bandData = bandList.map((b, i) => {
        let low = boundaries[i];
        let high = i + 1 < boundaries.length ? boundaries[i + 1] : domainMax;
        if (log) {
          low = Math.max(low, 1);
          high = Math.max(high, 1);
        }
        const midPx = (yPx(Math.max(low, high)) + yPx(low)) / 2 + 3;
        return {
          x0: 0,
          x1: n - 1,
          lb: low,
          hb: high,
          labY: yDomainOf(midPx),
          lab: b.label,
        };
      });

      const last = pts[n - 1];
      const seriesData = pts.map((p, i) => ({
        xi: i,
        yv: log ? Math.max(p.y, 1) : p.y,
      }));
      const lastData = [
        { xi: n - 1, yv: log ? Math.max(last.y, 1) : last.y },
      ];
      const numericLast =
        typeof last.y === "number"
          ? last.y
          : typeof last.y === "string" && last.y.trim() !== ""
            ? Number(last.y)
            : NaN;
      const latestValue = Number.isFinite(numericLast)
        ? numericLast.toFixed(1)
        : String(last.y);

      const xScale = {
        domain: [0, n - 1],
        range: [PADL, Math.max(width - PADR, PADL + 60)],
      };
      const yScale = log
        ? { type: "log", domain: [1, safeMax], range: [plotBottom, plotTop] }
        : { domain: [0, domainMax], range: [plotBottom, plotTop] };
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

      return {
        width,
        height: 150,
        config: { view: { stroke: "transparent" } },
        layer: [
          {
            data: { values: bandData },
            mark: { type: "rect", stroke: "transparent" },
            encoding: {
              x: X("x0"),
              x2: { field: "x1", type: "quantitative", scale: xScale },
              y: Y("hb"),
              y2: { field: "lb", type: "quantitative", scale: yScale },
              fill: {
                condition: {
                  test: "datum.fi % 2 === 1",
                  value: tokens.surface3,
                },
                value: tokens.surface2,
              },
            },
          },
          {
            data: { values: bandData },
            mark: {
              type: "text",
              fontSize: 11,
              font: tokens.sans,
              color: tokens.ink3,
              align: "left",
              dx: 5,
            },
            encoding: {
              x: X("x1"),
              y: Y("labY"),
              text: { field: "lab" },
            },
          },
          {
            data: { values: seriesData },
            mark: { type: "line", stroke: tokens.info, strokeWidth: 2 },
            encoding: { x: X("xi"), y: Y("yv") },
          },
          {
            data: { values: lastData },
            mark: { type: "point", size: 38, fill: tokens.infoInk },
            encoding: { x: X("xi"), y: Y("yv") },
          },
          {
            data: { values: lastData },
            mark: {
              type: "text",
              fontSize: 11,
              font: tokens.mono,
              color: tokens.infoInk,
              align: "left",
              dx: 6,
              dy: 3,
            },
            encoding: {
              x: X("xi"),
              y: Y("yv"),
              text: { value: latestValue },
            },
          },
        ],
      };
    },
    [pts, bandList, log, tokens, H]
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
      className="chart-vega"
      style={{ height: H }}
    >
      <div ref={elRef} className="chart-vega-inner" style={{ height: H }} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// 2.5 — Ribbon: one hard block per session, categorical state over time.
// Generalises the MBI ribbon. Rendered through ECharts: a custom series of
// solid blocks with the same proportional scaling the old viewBox used, plus
// the warning dot above each flagged session.
// ---------------------------------------------------------------------------
export function Ribbon({ cells }) {
  const list = React.useMemo(() => cells || [], [cells]);
  const elRef = React.useRef(null);
  const tokens = useTokens();

  useEChart(
    elRef,
    () => {
      const fillFor = {
        GREEN: tokens.ok,
        WHITE: tokens.neutralFill,
        RED: tokens.bad,
        NONE: tokens.surface2,
      };
      return {
        grid: { left: 0, right: 0, top: 0, bottom: 0 },
        xAxis: { type: "value", min: 0, max: 1, show: false },
        yAxis: { type: "value", min: 0, max: 1, show: false },
        tooltip: {
          trigger: "item",
          confine: true,
          formatter: (p) =>
            list[p.dataIndex]?.title || list[p.dataIndex]?.key || "",
        },
        series: [
          {
            type: "custom",
            clip: false,
            data: list.map((cell, i) => ({ value: [i, 0], cell })),
            renderItem(p, api) {
              const cell = list[p.dataIndex];
              const s = api.getWidth() / (list.length * 11); // CELL_W+GAP = 11
              const x = p.dataIndex * 11 * s;
              const fill = fillFor[cell.state] || fillFor.NONE;
              const noneState = cell.state === "NONE" || !cell.state;
              const children = [
                {
                  type: "rect",
                  shape: { x, y: 4, width: 9 * s, height: 22 },
                  style: {
                    fill,
                    stroke: noneState ? tokens.ink : "transparent",
                    lineWidth: 1.5,
                  },
                },
              ];
              if (cell.warn) {
                children.push({
                  type: "circle",
                  shape: { cx: x + (9 * s) / 2, cy: 3, r: 1.6 },
                  style: { fill: tokens.warn },
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

  return (
    <div
      ref={elRef}
      role="img"
      aria-label={ariaLabel}
      className="chart-echarts"
      style={{ height: 26 }}
    />
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
            mark: { type: "rect", stroke: tokens.surface, strokeWidth: 1 },
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
                condition: { test: "datum.fi < 2", value: tokens.surface },
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
                  style: { stroke: tokens.rule, lineWidth: 1 },
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