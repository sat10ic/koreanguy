import React, { useEffect, useMemo, useRef, useState } from "react";
import { fetchIndexCandles } from "../api.js";

/**
 * The quadrant's anchor: the reference index drawn as candles, with the day's
 * market_mode shaded behind it.
 *
 * Why this panel exists: every other row on TODAY is a derived breadth number.
 * Without price on the page you cannot tell whether "breadth is thinning" showed
 * up as a real drawdown or as three flat weeks, and the regime label has nothing
 * to sit against. The bands answer the question the breadth rows cannot: was the
 * tool's own posture right the last time it said this?
 *
 * OHLC comes from NSE's ind_close_all archive via sources/nse_indices.py — the
 * same file that has always supplied the close. Bars written before 2026-07-30
 * have no open/high/low and the API omits them rather than faking a doji, so a
 * short history here means "not backfilled yet", not "the market stood still".
 *
 * WHY HAND-DRAWN SVG AND NOT lightweight-charts: it was tried first (the library
 * is already a dependency of manas_os/desk). It renders nothing in this app's
 * browser — a minimal three-candle page leaves every one of its canvases at the
 * 300x150 HTML default with zero painted pixels, because its device-pixel-
 * content-box capability probe never resolves here, so the bitmap binding is
 * never created. 160 daily bars do not need a charting engine, and drawing them
 * directly means the regime bands are rects in the same coordinate space as the
 * candles instead of an overlay kept in sync through a coordinate API.
 */

const MODE_TONE = {
  RISK_ON: "risk_on",
  SELECTIVE: "selective",
  DEFENSIVE: "defensive",
  NO_TRADE: "no_trade",
};

const PAD = { top: 14, right: 56, bottom: 22, left: 8 };
const VB_W = 1000;
const VB_H = 300;

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function niceTicks(lo, hi, count = 4) {
  const span = hi - lo;
  if (!(span > 0)) return [lo];
  const raw = span / count;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) || mag * 10;
  const out = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi; v += step) out.push(v);
  return out;
}

export default function IndexCandles({ date, symbol = "NIFTYMIDSML400", label = "NIFTY MidSmallCap 400" }) {
  const [data, setData] = useState({ loading: true, candles: [], bands: [], error: null, covered: null });
  const [hoverIdx, setHoverIdx] = useState(null);
  const svgRef = useRef(null);

  useEffect(() => {
    let alive = true;
    setData((s) => ({ ...s, loading: true }));
    fetchIndexCandles(date, symbol, 160)
      .then((d) => {
        if (!alive) return;
        setData({
          loading: false,
          candles: d?.candles || [],
          bands: d?.bands || [],
          covered: d?.covered || null,
          error: null,
        });
      })
      .catch((e) => alive && setData({ loading: false, candles: [], bands: [], error: String(e) }));
    return () => { alive = false; };
  }, [date, symbol]);

  const geom = useMemo(() => {
    const c = data.candles;
    if (!c.length) return null;
    const plotW = VB_W - PAD.left - PAD.right;
    const plotH = VB_H - PAD.top - PAD.bottom;
    const lo = Math.min(...c.map((b) => b.low));
    const hi = Math.max(...c.map((b) => b.high));
    const padY = (hi - lo) * 0.06 || 1;
    const yLo = lo - padY;
    const yHi = hi + padY;
    const step = plotW / c.length;
    const y = (v) => PAD.top + ((yHi - v) / (yHi - yLo)) * plotH;
    const xMid = (i) => PAD.left + step * (i + 0.5);
    const idx = new Map(c.map((b, i) => [b.time, i]));
    return { plotW, plotH, yLo, yHi, step, y, xMid, idx, body: Math.max(step * 0.62, 1) };
  }, [data.candles]);

  if (data.loading) return <section className="v5-price v5-price--flat">Loading price…</section>;
  if (data.error) return <section className="v5-price v5-price--flat">Could not load price. {data.error}</section>;
  if (!data.candles.length) {
    return (
      <section className="v5-price v5-price--flat">
        No open/high/low stored for {label} yet — only closes. Run the index backfill to draw candles.
      </section>
    );
  }

  const c = data.candles;
  const last = c[c.length - 1];
  const shown = hoverIdx != null ? c[hoverIdx] : last;
  const before = hoverIdx != null ? c[hoverIdx - 1] : c[c.length - 2];
  const chg = before ? ((shown.close - before.close) / before.close) * 100 : null;
  const partial = data.covered && data.covered.with_ohlc < data.covered.bars;

  const ticks = niceTicks(geom.yLo, geom.yHi, 5);

  // month boundaries -> x-axis labels, so the axis reads as time and not as 160
  // anonymous bars
  const monthMarks = [];
  for (let i = 1; i < c.length; i++) {
    if (c[i].time.slice(0, 7) !== c[i - 1].time.slice(0, 7)) {
      monthMarks.push({ i, label: MONTHS[Number(c[i].time.slice(5, 7)) - 1] });
    }
  }

  const onMove = (e) => {
    const svg = svgRef.current;
    if (!svg) return;
    const r = svg.getBoundingClientRect();
    const vx = ((e.clientX - r.left) / r.width) * VB_W;
    const i = Math.floor((vx - PAD.left) / geom.step);
    setHoverIdx(i >= 0 && i < c.length ? i : null);
  };

  return (
    <section className="v5-price" aria-label={`${label} price`}>
      <header className="v5-price-head">
        <div className="v5-price-id">
          <span className="v5-price-name">{label}</span>
          <span className="v5-price-last">
            {shown.close?.toLocaleString("en-IN", { maximumFractionDigits: 0 })}
          </span>
          {chg != null && (
            <span className={`v5-price-chg v5-price-chg--${chg >= 0 ? "up" : "down"}`}>
              {chg >= 0 ? "+" : ""}{chg.toFixed(2)}%
            </span>
          )}
          <span className="v5-price-ohlc">
            {shown.time} · O {shown.open?.toFixed(0)} · H {shown.high?.toFixed(0)} · L {shown.low?.toFixed(0)}
            {shown.mode ? ` · ${shown.mode.replace("_", " ").toLowerCase()}` : ""}
          </span>
        </div>
        <div className="v5-price-legend">
          {["RISK_ON", "SELECTIVE", "DEFENSIVE", "NO_TRADE"].map((m) => (
            <span key={m} className="v5-price-legend-item">
              <i className={`v5-price-swatch v5-price-swatch--${MODE_TONE[m]}`} />
              {m.replace("_", " ").toLowerCase()}
            </span>
          ))}
        </div>
      </header>

      <svg
        ref={svgRef}
        className="v5-price-svg"
        viewBox={`0 0 ${VB_W} ${VB_H}`}
        preserveAspectRatio="none"
        onMouseMove={onMove}
        onMouseLeave={() => setHoverIdx(null)}
        role="img"
        aria-label={`${label} daily candles with market posture shading, ${c.length} sessions`}
      >
        {/* regime bands, behind everything. A band runs from the left edge of its
            first bar to the right edge of its last, so adjacent postures meet
            with no gap — a gap reads as missing data, not as a flip. */}
        {data.bands.map((b) => {
          if (!b.mode) return null;
          const i0 = geom.idx.get(b.from);
          const i1 = geom.idx.get(b.to);
          if (i0 == null && i1 == null) return null;
          const x0 = PAD.left + geom.step * (i0 ?? 0);
          const x1 = PAD.left + geom.step * ((i1 ?? c.length - 1) + 1);
          return (
            <rect
              key={`${b.mode}-${b.from}`}
              x={x0}
              y={PAD.top}
              width={Math.max(x1 - x0, 0.5)}
              height={geom.plotH}
              className={`v5-price-band v5-price-band--${MODE_TONE[b.mode]}`}
            />
          );
        })}

        {ticks.map((t) => (
          <g key={t}>
            <line x1={PAD.left} x2={VB_W - PAD.right} y1={geom.y(t)} y2={geom.y(t)} className="v5-price-grid" />
            <text x={VB_W - PAD.right + 6} y={geom.y(t) + 3.5} className="v5-price-axis">
              {Math.round(t).toLocaleString("en-IN")}
            </text>
          </g>
        ))}

        {monthMarks.map((m) => (
          <text key={m.i} x={geom.xMid(m.i)} y={VB_H - 6} className="v5-price-axis v5-price-axis--x">
            {m.label}
          </text>
        ))}

        {c.map((b, i) => {
          const up = b.close >= b.open;
          const x = geom.xMid(i);
          const yO = geom.y(b.open);
          const yC = geom.y(b.close);
          const top = Math.min(yO, yC);
          const h = Math.max(Math.abs(yC - yO), 0.8);
          return (
            <g key={b.time} className={`v5-price-candle v5-price-candle--${up ? "up" : "down"}`}>
              <line x1={x} x2={x} y1={geom.y(b.high)} y2={geom.y(b.low)} className="v5-price-wick" />
              <rect x={x - geom.body / 2} y={top} width={geom.body} height={h} className="v5-price-body" />
            </g>
          );
        })}

        {hoverIdx != null && (
          <line
            x1={geom.xMid(hoverIdx)}
            x2={geom.xMid(hoverIdx)}
            y1={PAD.top}
            y2={PAD.top + geom.plotH}
            className="v5-price-cross"
          />
        )}
      </svg>

      <p className="v5-price-foot">
        Shading is the posture the tool called that day — read the candles against it.
        {partial ? ` Showing ${data.covered.with_ohlc} of ${data.covered.bars} sessions; the rest have closes only.` : ""}
      </p>
    </section>
  );
}
