import React, { useEffect, useMemo, useState } from "react";
import { fetchBreadth, fetchRegimeHistory, fetchMswing } from "../api.js";

/**
 * TODAY / Market Quadrant - the one panel that answers "can I trade today?"
 *
 * Four rows, each a question in plain English with a one-word verdict, a
 * 60-session sparkline and the number behind it. Replaces reading eleven
 * separate breadth panels and doing the synthesis yourself.
 *
 * Row inputs, all from /api/regime/breadth-analytics (universe_breadth is the
 * single writer; nothing is recomputed here):
 *   MOMENTUM  up_4pct - down_4pct      -- burst moves, up minus down
 *   SWING     pct_above_10dma          -- short-term participation
 *   TREND     pct_above_50dma + net_new_highs_pct
 *   BIAS      pct_above_200dma
 *   BREADTH   advances - declines      -- the rawest read
 *
 * A row whose input is missing says so. It never renders a proxy dressed as the
 * real thing, and never infers a zero -- the 2026-07-30 audit found the BIAS row
 * showing a 40-day stand-in labelled as long-term bias.
 */

const NEUTRAL = 50;

function verdictFor(value, { good, bad, invert = false }) {
  if (value == null) return { word: "NO DATA", tone: "muted" };
  const v = invert ? -value : value;
  const g = invert ? -good : good;
  const b = invert ? -bad : bad;
  if (v >= g) return { word: "UP", tone: "good" };
  if (v <= b) return { word: "DOWN", tone: "bad" };
  return { word: "MIXED", tone: "warn" };
}

/**
 * Bar histogram around a neutral line, one bar per session, coloured by side.
 *
 * The reference layout (finallynitin's Market Quadrant) uses bars, not a line:
 * you read the balance of green against red at a glance and see how long the
 * market has been on one side. A thin line loses exactly that.
 */
function Bars({ values, mid, height = 64 }) {
  if (!values || values.length < 2) {
    return <div className="v5-quad-bars v5-quad-bars--empty">not tracked</div>;
  }
  const w = 420;
  const h = height;
  const base = mid == null ? 0 : mid;
  const devs = values.map((v) => v - base);
  const span = Math.max(...devs.map(Math.abs)) || 1;
  const zeroY = h / 2;
  const bw = w / values.length;
  const gap = bw > 4 ? 1 : 0;
  return (
    <svg className="v5-quad-bars" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none"
         role="img"
         aria-label={`${values.length} sessions, latest ${values[values.length - 1].toFixed(1)}`}>
      <line x1="0" y1={zeroY} x2={w} y2={zeroY} className="v5-quad-zero" />
      {values.map((v, i) => {
        const d = v - base;
        const mag = (Math.abs(d) / span) * (h / 2 - 3);
        const y = d >= 0 ? zeroY - mag : zeroY;
        const cls = d >= 0 ? "up" : "down";
        const fresh = i >= values.length - 1 ? " v5-quad-bar--last" : "";
        return (
          <rect
            key={i}
            x={i * bw + gap / 2}
            y={y}
            width={Math.max(bw - gap, 0.8)}
            height={Math.max(mag, 0.8)}
            className={`v5-quad-bar v5-quad-bar--${cls}${fresh}`}
          />
        );
      })}
    </svg>
  );
}

/**
 * The numbers behind a row, last three sessions. This is the reference layout's
 * side table -- the same data the old app spread across eleven separate panels,
 * kept next to the verdict it supports instead of in its own card.
 */
function SideTable({ cols, rows }) {
  if (!rows || !rows.length) return null;
  // TRANSPOSED: metrics down the side, dates across. The original had dates as
  // rows and metrics as columns, so each extra metric widened the table until it
  // overflowed its 250px column. This way extra metrics add height, which the
  // row absorbs, and long plain-English labels get a full line instead of being
  // squeezed into a column header.
  return (
    <table className="v5-quad-tbl">
      <thead>
        <tr>
          <th className="v5-quad-tbl-metric" />
          {rows.map((r) => (
            <th key={r.date}>{r.date}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {cols.map((c) => (
          <tr key={c.key}>
            <td className="v5-quad-tbl-metric">{c.label}</td>
            {rows.map((r) => {
              const v = r[c.key];
              const tone =
                c.band && typeof v === "number"
                  ? v >= c.band[0]
                    ? "good"
                    : v <= c.band[1]
                    ? "bad"
                    : "warn"
                  : "flat";
              return (
                <td key={r.date} className={`v5-quad-tbl-num v5-quad-tbl-num--${tone}`}>
                  {typeof v === "number" ? (c.fmt ? c.fmt(v) : v.toFixed(0)) : "—"}
                </td>
              );
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/** Mswing per index — the reference layout's momentum table. */
function MswingTable({ rows }) {
  if (!rows || !rows.length) return null;
  const shortName = (s) => s.replace(/^NIFTY\s*/i, "") || s;
  return (
    <table className="v5-quad-tbl">
      <thead>
        <tr>
          <th style={{ textAlign: "left" }}>Index</th>
          <th>Speed</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.index}>
            <td className="v5-quad-tbl-date">
              {shortName(r.index)}
              {r.stale && <span className="v5-quad-stale" title={`Last updated ${r.as_of}`}>stale</span>}
            </td>
            <td className={`v5-quad-tbl-num v5-quad-tbl-num--${
              r.state === "up" ? "good" : r.state === "down" ? "bad" : "warn"}`}>
              {typeof r.mswing === "number" ? r.mswing.toFixed(2) : "—"}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/**
 * One quadrant row.
 *
 * Layout notes (2026-07-30 redesign): the first pass gave five identical rows
 * with 12px grey labels and an always-open monospace table each, so the panel
 * had no focal point and five tables of numbers competed with the verdicts. Now
 * the verdict is the largest thing in the row, the label is a pill carrying the
 * verdict's colour, `source` names the actual input so the number is never
 * anonymous, `action` says what the read means for today's trading, and the
 * numbers collapse behind a disclosure instead of shouting by default.
 */
function Row({ label, question, source, verdict, values, mid, latest, read, action, missing, table }) {
  return (
    <div className="v5-quad-row">
      <div className="v5-quad-key">
        <div className={`v5-quad-pill v5-quad-pill--${verdict.tone}`}>
          <i className="v5-quad-dot" />
          {label}
        </div>
        <div className={`v5-quad-verdict v5-quad-verdict--${verdict.tone}`}>{verdict.word}</div>
        <div className="v5-quad-source">{source}</div>
      </div>
      <div className="v5-quad-mid-col">
        <div className="v5-quad-question">{question}</div>
        <Bars values={values} mid={mid} />
        {missing ? (
          <div className="v5-quad-missing">{missing}</div>
        ) : (
          <div className="v5-quad-latest">
            <strong>{latest}</strong> — {read}
          </div>
        )}
        {action && !missing && <div className="v5-quad-action">{action}</div>}
        {table && (
          <details className="v5-quad-read">
            <summary>Numbers</summary>
            <div className="v5-quad-read-body">{table}</div>
          </details>
        )}
      </div>
    </div>
  );
}

export default function MarketQuadrant({ date, mode }) {
  const [state, setState] = useState({ loading: true, rows: [], error: null });
  const [regime, setRegime] = useState([]);
  const [ms, setMs] = useState({ rows: [], table: [] });

  useEffect(() => {
    let alive = true;
    setState((s) => ({ ...s, loading: true }));
    Promise.all([
      fetchBreadth(date, 60),
      fetchRegimeHistory(date, 60).catch(() => ({ rows: [] })),
      fetchMswing(date, 60).catch(() => ({ rows: [], table: [] })),
    ])
      .then(([b, r, m]) => {
        if (!alive) return;
        setRegime(r?.rows || []);
        setMs(m || { rows: [], table: [] });
        setState({ loading: false, rows: b?.rows || [], error: null });
      })
      .catch((e) => alive && setState({ loading: false, rows: [], error: String(e) }));
    return () => {
      alive = false;
    };
  }, [date]);

  const series = useMemo(() => {
    const rows = state.rows || [];
    const pick = (k) => rows.map((r) => r?.[k]).filter((v) => typeof v === "number");
    const burst = rows
      .map((r) =>
        typeof r?.up_4pct === "number" && typeof r?.down_4pct === "number"
          ? r.up_4pct - r.down_4pct
          : null)
      .filter((v) => v != null);
    const net = rows
      .map((r) =>
        typeof r?.advances === "number" && typeof r?.declines === "number"
          ? r.advances - r.declines
          : null)
      .filter((v) => v != null);
    return {
      burst,
      swing: pick("pct_above_10dma"),
      trend: pick("pct_above_50dma"),
      nhnl: pick("net_new_highs_pct"),
      bias: pick("pct_above_200dma"),
      net,
      last: rows.length ? rows[rows.length - 1] : null,
    };
  }, [state.rows]);

  if (state.loading) return <div className="v5-quad v5-quad--loading">Reading the market...</div>;
  if (state.error) return <div className="v5-quad v5-quad--error">Could not load breadth. {state.error}</div>;
  if (!series.last) return <div className="v5-quad v5-quad--error">No breadth for this date.</div>;

  const L = series.last;
  const lastOf = (a) => (a.length ? a[a.length - 1] : null);
  const one = (n, d = 0) => (typeof n === "number" ? n.toFixed(d) : "—");

  const burstNow = lastOf(series.burst);
  const swingNow = lastOf(series.swing);
  const trendNow = lastOf(series.trend);
  const nhnlNow = lastOf(series.nhnl);
  const biasNow = lastOf(series.bias);
  const netNow = lastOf(series.net);

  // Mswing: the reference index series drives the MOMENTUM bars
  const msSeries = (ms.rows || [])
    .map((r) => r.mswing)
    .filter((v) => typeof v === "number");
  const msNow = msSeries.length ? msSeries[msSeries.length - 1] : null;
  const msEma = (() => {
    const r = (ms.rows || []).filter((x) => typeof x.mswing_ema === "number");
    return r.length ? r[r.length - 1].mswing_ema : null;
  })();

  // last three sessions, newest first — the reference layout's side tables
  const recent = (state.rows || []).slice(-3).reverse();
  const recentRegime = (regime || []).slice(-3).reverse();
  const short = (d) => (d ? d.slice(5) : "");
  const pc = (v) => `${v.toFixed(0)}%`;
  const tbl = (src, cols) =>
    src.map((r) => ({ date: short(r.trade_date || r.snapshot_date), ...r }));

  const rows = [
    {
      label: "MOMENTUM",
      question: "How fast is the market moving, and which sizes are leading?",
      source: "Mswing, 20+50 day speed",
      action:
        msNow == null
          ? null
          : msNow <= 0
          ? "Do not start new longs on strength alone — wait for speed back above zero."
          : msEma != null && msNow < msEma
          ? "Trade what is already working; be slower to add new names while speed fades."
          : "Fresh breakouts have the wind behind them. Full regime size is justified.",
      verdict: verdictFor(msNow, { good: 0.2, bad: 0 }),
      values: msSeries.length ? msSeries : series.burst,
      mid: 0,
      latest:
        msNow == null
          ? `${one(L.up_4pct, 1)}% of stocks jumped 4%, ${one(L.down_4pct, 1)}% fell 4%`
          : `Mswing ${msNow.toFixed(2)}, its 9-day average ${one(msEma, 2)}`,
      read:
        msNow == null
          ? "Mswing unavailable — falling back to today's 4% burst counts."
          : msNow <= 0
          ? "Speed is negative — the market is losing ground, not gaining it."
          : msEma != null && msNow < msEma
          ? "Still positive, but slowing — above zero and below its own average."
          : "Positive and accelerating.",
      table: <MswingTable rows={ms.table || []} />,
    },
    {
      label: "SWING",
      question: "Is the short-term tide in?",
      source: "% of the 400 above their 10-day line",
      action:
        swingNow >= 55
          ? "Pullback entries have a decent hit rate — buying dips is supported."
          : swingNow <= 45
          ? "Dip-buying is fighting the tide. Wait for a reclaim of the 10-day."
          : "No short-term edge either way — take only your best-structured name.",
      verdict: verdictFor(swingNow, { good: 55, bad: 45 }),
      values: series.swing,
      mid: NEUTRAL,
      latest: `${one(swingNow, 0)}% above their 10-day line`,
      read:
        swingNow >= 55
          ? "Most stocks are holding short-term support."
          : swingNow <= 45
          ? "Under half — the short-term tide is out."
          : "Roughly half. No clear short-term edge.",
      table: (
        <SideTable
          rows={tbl(recent)}
          cols={[
            { key: "pct_above_10dma", label: "Above 10-day", band: [55, 45], fmt: pc },
            { key: "pct_10dma_gt_20dma", label: "Short over med", band: [55, 45], fmt: pc },
          ]}
        />
      ),
    },
    {
      label: "TREND",
      question: "Are stocks in real uptrends?",
      source: "% above the 50-day + 52-week new highs vs lows",
      action:
        nhnlNow == null
          ? null
          : nhnlNow > 0
          ? "There is a real leadership pool to pick from — breakout setups are worth taking."
          : "Leadership is thin. Expect breakouts to fail; demand tighter stops and smaller size.",
      verdict: verdictFor(trendNow, { good: 55, bad: 45 }),
      values: series.trend,
      mid: NEUTRAL,
      latest:
        nhnlNow == null
          ? `${one(trendNow, 0)}% above their 50-day line`
          : `${one(trendNow, 0)}% above the 50-day · ${L.new_highs_52w ?? "—"} new highs vs ${L.new_lows_52w ?? "—"} new lows`,
      read:
        nhnlNow == null
          ? "New-high data not yet computed for this date."
          : nhnlNow > 0
          ? "More stocks making 52-week highs than lows."
          : "More stocks making 52-week lows than highs.",
      table: (
        <SideTable
          rows={tbl(recent)}
          cols={[
            { key: "new_highs_52w", label: "New highs" },
            { key: "new_lows_52w", label: "New lows" },
            { key: "net_new_highs_pct", label: "Net new highs", band: [0.5, -0.5], fmt: (v) => v.toFixed(1) },
            { key: "pct_above_50dma", label: "Above 50-day", band: [55, 45], fmt: pc },
          ]}
        />
      ),
    },
    {
      label: "BIAS",
      question: "What is the long-term picture?",
      source: "% of the 400 above their 200-day line",
      action:
        biasNow == null
          ? null
          : biasNow >= 55
          ? "Weakness is a dip inside an uptrend. Hold winners through normal shakeouts."
          : biasNow <= 45
          ? "Rallies are counter-trend until this reclaims 50%. Book faster, trail tighter."
          : "Mixed floor — size at the regime's band, do not press.",
      verdict: verdictFor(biasNow, { good: 55, bad: 45 }),
      values: series.bias,
      mid: NEUTRAL,
      latest: biasNow == null ? null : `${one(biasNow, 0)}% above their 200-day line`,
      read:
        biasNow >= 55
          ? "The majority are in long-term uptrends."
          : biasNow <= 45
          ? "Fewer than half hold their 200-day line."
          : "Split down the middle.",
      missing: biasNow == null ? "200-day breadth not computed for this date." : null,
      table: (
        <SideTable
          rows={tbl(recent)}
          cols={[
            { key: "pct_above_200dma", label: "Above 200-day", band: [55, 45], fmt: pc },
            { key: "pct_20dma_gt_40dma", label: "Med over long", band: [55, 45], fmt: pc },
          ]}
        />
      ),
    },
    {
      label: "BREADTH",
      question: "Are more stocks up than down?",
      source: "today's advances minus declines",
      action:
        netNow > 0
          ? "Today's tape supports acting on a signal that fires."
          : "Today's tape is against you — let a signal prove itself before adding.",
      verdict: verdictFor(netNow, { good: 40, bad: -40 }),
      values: series.net,
      mid: 0,
      latest: `${L.advances ?? "—"} up against ${L.declines ?? "—"} down`,
      read: netNow > 0 ? "Advances are leading." : "Declines are leading.",
      table: (
        <SideTable
          rows={tbl(recent)}
          cols={[
            { key: "advances", label: "Up" },
            { key: "declines", label: "Down" },
            { key: "up_25pct_month", label: "Up 25% (mo)" },
            { key: "down_25pct_month", label: "Down 25% (mo)" },
          ]}
        />
      ),
    },
  ];

  const mbiNow = recentRegime.length ? recentRegime[0] : null;

  return (
    <section className="v5-quad" aria-label="Market quadrant">
      <header className="v5-quad-head">
        <div>
          <h2 className="v5-quad-title">Can I trade today?</h2>
          <p className="v5-quad-sub">
            Five reads on the market, in order of how long they look back.
          </p>
        </div>
        {mode && <div className={`v5-quad-mode v5-quad-mode--${String(mode).toLowerCase()}`}>{mode}</div>}
      </header>
      {rows.map((r) => (
        <Row key={r.label} {...r} />
      ))}
      {mbiNow && (
        <div className="v5-quad-mbi">
          <span className="v5-quad-mbi-label">MBI</span>
          <span className={`v5-quad-mbi-dot v5-quad-mbi-dot--${String(mbiNow.mbi_day_color || "").toLowerCase()}`} />
          <span className="v5-quad-mbi-val">{mbiNow.mbi_day_color || "—"}</span>
          <span className="v5-quad-mbi-sep">·</span>
          <span className="v5-quad-mbi-r">
            10R {one(mbiNow.r10, 0)} · 20R {one(mbiNow.r20, 0)} · 50R {one(mbiNow.r50, 0)} · 4.5R {one(mbiNow.r4p5, 0)}
          </span>
          {mbiNow.warning_day ? <span className="v5-quad-mbi-warn">WARNING DAY</span> : null}
        </div>
      )}
      <footer className="v5-quad-foot">
        Breadth over the NIFTY MidSmallCap 400. 52-week highs and lows count only
        names with a full year of history{L.nhnl_universe ? ` (${L.nhnl_universe} of 400 qualify today)` : ""}.
      </footer>
    </section>
  );
}

