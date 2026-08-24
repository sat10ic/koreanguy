// MARKET (was BREADTH) — REDESIGN_SCOUTING_WIRE.md §4.6 + §5; HANDOFF
// "Screens — Market (was BREADTH) — S8".
//
// Deliberately quiet. No accent anywhere: the --risk accent means "money was
// risked" (Rule 3) and market internals never involve that, so this screen
// never uses it. Only --up/--down carry day-colour state; the ink ladder
// carries all hierarchy. No --caution this wave — XP is fixed in this wave,
// so no number is disclaimed here (the orchestrator re-adds the caution block
// only if the fix evidence later fails; not this screen's problem now).
//
// Consumes /api/breadth: today {trade_date, xp_value, xp_band, mbi_day_color,
// mbi_score, warning_day, r10, r20, r50, r4p5, band_*}, history[] (regime
// rows; S9 adds advances/declines in parallel — code defensively below),
// stances[], agreement[].
//
// Colours resolve ONLY through CSS custom properties at runtime (the same
// token-adapter pattern as components/charts.jsx and screens/Symbol.jsx).
// When a token has not been landed yet, the resolved value is dropped and the
// renderer keeps its default — no literal colour ever appears in this file.
import React from "react";
import * as echarts from "echarts/core";
import { LineChart } from "echarts/charts";
import {
  GridComponent, MarkLineComponent, TooltipComponent,
} from "echarts/components";
import { SVGRenderer } from "echarts/renderers";
import { fetchBreadth } from "../api.js";
import {
  ErrorBox, Loading, Panel, Stat, fmtDate, useApi,
} from "../components/ui.jsx";
import "../styles/market.css";

echarts.use([LineChart, GridComponent, MarkLineComponent, TooltipComponent, SVGRenderer]);

const DAY_MS = 86400000;
const RIBBON_SESSIONS = 60;
const STANCE_ROWS = 14;

// XP band glosses — copy appendix (binding, verbatim; LOW is taken from the
// microcopy table). Rule 1: the meaning is a sentence, never a bare label.
const BAND_GLOSS = {
  LOW: "Only a few stocks are pushing higher. Breakouts fail more often in a market like this.",
  BUILDING:
    "More stocks are starting to push higher, but the rope is still out — treat breakouts as unproven.",
  STRONG: "Most stocks are pushing higher — a breakout has a real chance of working.",
  EXTREME:
    "The whole tape is extended. Breakouts work until they stop working — assume reversion risk.",
};

// Reads the design tokens once per mount. `maybe()` drops an unresolved token
// ("") so the renderer falls back to its own default — never a literal here.
function useMarketTokens() {
  return React.useMemo(() => {
    const cs = getComputedStyle(document.documentElement);
    const get = (name) => cs.getPropertyValue(name).trim();
    const maybe = (v) => (v ? v : undefined);
    return Object.fromEntries(
      Object.entries({
        ink: get("--ink"),
        ink2: get("--ink-2"),
        ink3: get("--ink-3"),
        ink4: get("--ink-4"),
        up: get("--up"),
        down: get("--down"),
        edge: get("--edge"),
        hair: get("--hair"),
        raised: get("--raised"),
        sunken: get("--sunken"),
        mono: get("--mono"),
        sans: get("--sans"),
      }).map(([k, v]) => [k, maybe(v)])
    );
  }, []);
}

// Calendar days from a YYYY-MM-DD trade date to today (local midnight), or
// null when the date is absent/unparseable. Used for the reading's age.
function readingAgeDays(tradeDate) {
  if (!tradeDate) return null;
  const d = new Date(`${tradeDate}T00:00:00`);
  if (Number.isNaN(d.getTime())) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.round((today - d) / DAY_MS);
}

function shortDate(iso) {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso || "");
  if (!m) return iso;
  const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  return `${Number(m[3])} ${MONTHS[Number(m[2]) - 1]}`;
}

// ---------------------------------------------------------------------------
// Hero: the XP number with its plain-English meaning AND its age.
// ---------------------------------------------------------------------------
function HeroStat({ t }) {
  const band = (t && t.xp_band ? String(t.xp_band) : "").toUpperCase();
  const gloss = BAND_GLOSS[band] || null;
  const value = t && t.xp_value != null ? Number(t.xp_value).toFixed(1) : "—";
  const meaning =
    gloss ||
    (t
      ? "No market-strength reading for this session yet."
      : "No breadth data captured yet.");
  const age = readingAgeDays(t && t.trade_date);
  const stale = age !== null && age >= 6;

  return (
    <div className="mk-hero">
      <Stat value={value} meaning={meaning} />
      {t && t.trade_date && (
        <p className={`mk-hero-age${stale ? " mk-stale" : ""}`}>
          as of <span className="mono">{t.trade_date}</span>
          {stale
            ? `. This reading is ${age} days old — the market has moved since.`
            : "."}
        </p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Ratio row (WIREFRAMES §4 elements carry over): r10/r20/r50/r4.5 with their
// bands, one quiet line of mono numbers and band labels.
// ---------------------------------------------------------------------------
function RatioRow({ t }) {
  const ratios = [
    { k: "r10", v: t && t.r10, band: t && t.band_r10 },
    { k: "r20", v: t && t.r20, band: t && t.band_r20 },
    { k: "r50", v: t && t.r50, band: t && t.band_r50 },
    { k: "r4.5", v: t && t.r4p5, band: t && t.band_r4p5 },
  ];
  return (
    <div className="mk-ratios">
      {ratios.map(({ k, v, band }) => (
        <span className="mk-ratio" key={k}>
          <span className="k">{k}</span>
          <span className="v">{v == null ? "—" : Math.round(v)}</span>
          <span className={`b mk-band-${band || "none"}`}>{band || "no data"}</span>
        </span>
      ))}
      <p className="mk-note">
        r50 uses its own 85 / 60 cutoffs; r10 and r20 use 75 / 50.
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Day-colour ribbon: inline SVG (trivial, no library — REDESIGN §5), one hard
// block per session over the last 60 sessions. Cell colour maps the MBI day
// colour onto the day tokens (GREEN→--up, RED→--down, WHITE→--ink-3, none→
// --ink-4) with a warning mark on warning_day cells. The legend is in WORDS —
// binding copy, never hue-only.
// ---------------------------------------------------------------------------
function DayRibbon({ history }) {
  const cells = history.slice(-RIBBON_SESSIONS).map((r) => ({
    key: r.trade_date,
    state: r.mbi_day_color || "NONE",
    warn: !!r.warning_day,
    title: `${r.trade_date} · ${r.mbi_day_color || "no data"}${
      r.warning_day ? " · warning day" : ""
    }`,
  }));

  if (cells.length === 0) {
    return (
      <div
        className="chart-empty"
        role="img"
        aria-label="No market-internals sessions captured yet."
      >
        No market-internals sessions captured yet.
      </div>
    );
  }

  const W = 11;   // block width
  const GAP = 2;  // block gap
  const TOP = 4;  // block top; warning dot sits above it
  const H = 22;   // block height
  const UNIT = W + GAP;

  const counts = cells.reduce(
    (acc, c) => {
      acc[c.state] = (acc[c.state] || 0) + 1;
      if (c.warn) acc.warn += 1;
      return acc;
    },
    { GREEN: 0, WHITE: 0, RED: 0, NONE: 0, warn: 0 }
  );
  // The finding in words (group rule: role="img" + aria-label on every chart).
  const ariaLabel =
    `${cells.length} sessions: ${counts.GREEN} most stocks rose, ` +
    `${counts.WHITE} roughly even, ${counts.RED} most fell` +
    `${counts.NONE ? `, ${counts.NONE} no data` : ""}` +
    `${counts.warn ? `; ${counts.warn} warning day${counts.warn === 1 ? "" : "s"}` : ""}.`;

  return (
    <>
      <svg
        className="mk-ribbon"
        role="img"
        aria-label={ariaLabel}
        width={cells.length * UNIT - GAP}
        viewBox={`0 0 ${cells.length * UNIT - GAP} 30`}
      >
        {cells.map((c, i) => (
          <g key={c.key}>
            <rect
              x={i * UNIT}
              y={TOP}
              width={W}
              height={H}
              className={`mk-cell-${c.state}`}
            >
              <title>{c.title}</title>
            </rect>
            {c.warn && (
              <circle
                cx={i * UNIT + W / 2}
                cy={TOP - 3}
                r={1.8}
                className="mk-warn-dot"
              />
            )}
          </g>
        ))}
      </svg>
      <div className="mk-legend">
        <span><i className="mk-swatch mk-swatch-up" />most stocks rose</span>
        <span><i className="mk-swatch mk-swatch-even" />roughly even</span>
        <span><i className="mk-swatch mk-swatch-down" />most fell</span>
        <span className="mk-legend-note">· dot above = warning day (3 or more red bands)</span>
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// Cumulative advance–decline: ECharts line (REDESIGN §5) from
// history[].advances/declines — cumulative sum of (advances − declines) in
// chronological order. Labelled axis + a zero reference line are required (a
// chart with no scale is a defect). .chart-empty names the reason when the
// payload lacks the counts.
// ---------------------------------------------------------------------------
function AdLine({ rows, emptyReason, totalSessions }) {
  const elRef = React.useRef(null);
  const tk = useMarketTokens();

  const pts = React.useMemo(() => {
    let run = 0;
    return rows.map((r) => {
      const net = Number(r.advances) - Number(r.declines);
      run += net;
      return { date: r.trade_date, net, run, adv: r.advances, dec: r.declines };
    });
  }, [rows]);

  React.useEffect(() => {
    const el = elRef.current;
    if (!el || pts.length === 0) return undefined;
    const mono = tk.mono || "monospace";
    const chart = echarts.init(el, null, { renderer: "svg" });
    chart.setOption({
      animation: false,
      grid: { left: 52, right: 20, top: 12, bottom: 26 },
      xAxis: {
        type: "category",
        boundaryGap: false,
        data: pts.map((p) => p.date),
        axisLine: tk.ink4 ? { lineStyle: { color: tk.ink4 } } : undefined,
        axisTick: { show: false },
        axisLabel: {
          color: tk.ink3,
          fontFamily: mono,
          fontSize: 11,
          formatter: shortDate,
          interval: (idx) =>
            idx % Math.max(1, Math.ceil(pts.length / 8)) === 0 ||
            idx === pts.length - 1,
        },
        splitLine: { show: false },
      },
      yAxis: {
        type: "value",
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: tk.ink3, fontFamily: mono, fontSize: 11 },
        splitLine: tk.hair ? { lineStyle: { color: tk.hair, width: 1 } } : undefined,
      },
      tooltip: {
        trigger: "axis",
        confine: true,
        backgroundColor: tk.raised,
        borderColor: tk.edge,
        textStyle: { color: tk.ink, fontFamily: mono, fontSize: 12 },
        formatter: (params) => {
          const p = params && params[0];
          const row = p && pts[p.dataIndex];
          if (!row) return "";
          const sign = row.run >= 0 ? "+" : "";
          return (
            `${row.date} · net ${sign}${row.run}` +
            ` (${row.adv} up / ${row.dec} down)`
          );
        },
      },
      series: [
        {
          name: "net advances",
          type: "line",
          data: pts.map((p) => p.run),
          showSymbol: pts.length < 2, // with one session, show the point
          symbolSize: 5,
          lineStyle: { color: tk.ink, width: 2 },
          markLine: {
            silent: true,
            symbol: "none",
            label: {
              show: true,
              formatter: "0",
              position: "end",
              color: tk.ink4,
              fontFamily: mono,
              fontSize: 11,
            },
            lineStyle: { color: tk.ink4, type: "dashed", width: 1 },
            data: [{ yAxis: 0 }],
          },
        },
      ],
    });
    const ro = new ResizeObserver(() => chart.resize());
    ro.observe(el);
    return () => {
      ro.disconnect();
      chart.dispose();
    };
  }, [pts, tk]);

  if (pts.length === 0) {
    return (
      <div className="chart-empty" role="img" aria-label={emptyReason}>
        {emptyReason}
      </div>
    );
  }

  const first = pts[0];
  const last = pts[pts.length - 1];
  const partial = rows.length < totalSessions;
  const ariaLabel =
    `Cumulative advance–decline (advances minus declines) across ` +
    `${pts.length} session${pts.length === 1 ? "" : "s"}: ` +
    `starts at ${first.run}, ends at ${last.run}.`;

  return (
    <>
      <div
        ref={elRef}
        role="img"
        aria-label={ariaLabel}
        className="mk-chart"
        style={{ height: 190 }}
      />
      <p className="mk-caption">
        net advances · advances − declines
        {partial ? ` · counted ${rows.length} of ${totalSessions} sessions` : ""}
      </p>
    </>
  );
}

// ---------------------------------------------------------------------------
// Screen
// ---------------------------------------------------------------------------
export default function Market() {
  const { data, error } = useApi(() => fetchBreadth(90), []);
  if (error) return <ErrorBox error={error} />;
  if (!data) return <Loading />;

  const t = data.today;
  const history = data.history || [];
  const ribbonCells = history.slice(-RIBBON_SESSIONS);

  // S9 adds advances/declines in parallel; code defensively. Only rows that
  // carry both counts are usable for the cumulative line.
  const adRows = history.filter((r) => {
    const a = Number(r.advances);
    const d = Number(r.declines);
    return Number.isFinite(a) && Number.isFinite(d);
  });
  let adEmpty = null;
  if (history.length === 0) {
    adEmpty =
      "No market-internals sessions captured yet — nothing to draw.";
  } else if (adRows.length === 0) {
    adEmpty =
      "Advance–decline counts aren't in the breadth payload yet — the cumulative line appears once history carries them.";
  }

  return (
    <>
      <p className="mk-lede">
        What the market internals actually did, beside what each trader said
        about them.
      </p>

      <Panel title="Market strength" cite="XP: finallynitin's recursion · MBI: Stocksgeeks">
        {!t ? (
          <p className="empty">
            No breadth data yet — no market-internals sessions have been
            captured.
          </p>
        ) : (
          <>
            <HeroStat t={t} />
            <RatioRow t={t} />
          </>
        )}
      </Panel>

      <Panel
        title={
          ribbonCells.length
            ? `Day colour · last ${ribbonCells.length} sessions`
            : "Day colour"
        }
      >
        <DayRibbon history={history} />
      </Panel>

      <Panel title="Cumulative advance–decline">
        <AdLine
          rows={adRows}
          emptyReason={adEmpty}
          totalSessions={history.length}
        />
      </Panel>

      <Panel title="What traders said">
        {data.stances.length === 0 && (
          <p className="empty">No breadth commentary captured yet.</p>
        )}
        {data.stances.length > 0 && (
          <table className="mk-stances">
            <thead>
              <tr>
                <th>date</th>
                <th>trader</th>
                <th>stance</th>
                <th>XP / MBI that day</th>
                <th>agreed?</th>
              </tr>
            </thead>
            <tbody>
              {data.stances.slice(0, STANCE_ROWS).map((s) => (
                <tr key={`${s.trade_date}-${s.handle}`}>
                  <td className="mono">{fmtDate(s.trade_date)}</td>
                  <td className="mk-handle">@{s.handle}</td>
                  <td>{s.stance ? s.stance.replace("_", "-") : "—"}</td>
                  <td>
                    {s.xp_value != null ? (
                      <span className="mk-xp">
                        <span className="mono">{Number(s.xp_value).toFixed(1)}</span>{" "}
                        {s.xp_band} ·{" "}
                        {s.mbi_day_color ? (
                          <span className={`mk-band-${s.mbi_day_color}`}>
                            {s.mbi_day_color}
                          </span>
                        ) : (
                          <span className="unstated">no data</span>
                        )}
                      </span>
                    ) : (
                      <span className="unstated">no data</span>
                    )}
                  </td>
                  <td className="mk-agreed">
                    {s.agreed === null ? "—" : s.agreed ? "✓" : "✗"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {data.agreement.length > 0 && (
          <>
            <div className="mk-agree-head">Agreement</div>
            {data.agreement.map((a) => (
              <div className="mk-agree" key={a.handle}>
                <span className="handle">@{a.handle}</span>
                <span className="pct">
                  {a.agreed_pct == null ? "—" : `${a.agreed_pct}%`}
                </span>
                <span
                  className="mk-bar"
                  role="img"
                  aria-label={`@${a.handle} agreement rate ${
                    a.agreed_pct == null ? 0 : a.agreed_pct
                  }%`}
                >
                  <span
                    className="mk-bar-fill"
                    style={{
                      width: `${Math.max(0, Math.min(100, Number(a.agreed_pct) || 0))}%`,
                    }}
                  />
                </span>
                <span className="n">
                  {a.n == null ? "n=—" : `n=${a.n}`}
                </span>
              </div>
            ))}
          </>
        )}

        <p className="footnote">
          &ldquo;Agreed&rdquo; is a deliberately crude three-way match: risk-on
          vs GREEN, risk-off vs RED, neutral vs WHITE. It measures agreement
          with one particular breadth model — <strong>not</strong> whether the
          trader was right. A low score here is not evidence that someone reads
          the market badly.
        </p>
      </Panel>
    </>
  );
}