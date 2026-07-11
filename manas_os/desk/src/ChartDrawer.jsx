import React, { useEffect, useMemo, useRef, useState } from "react";
import { createChart } from "lightweight-charts";
import { fetchChartData } from "./api.js";
import { Term } from "./Glossary.jsx";

const HMM_COLORS = {
  bull: "#00c878",
  chop: "#b66cff",
  bear: "#ff4a5f",
};

const CONFIDENCE_LABEL = { LOW: "LOW", MED: "MED", HIGH: "HIGH" };

const VOLUME_COLORS = {
  bull_pp: "#1f8cff",
  bear_pp: "#8b5cf6",
  dry: "#7c8495",
  up: "#00c878",
  down: "#ff4a5f",
  noise: "#394150",
};

const MSWING_LABEL = {
  up: "beats index",
  neutral_positive: "positive, trails index",
  neutral_negative: "negative, beats index",
  down: "lags index",
};

function fmt(n, digits = 1) {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return "-";
  return Number(n).toFixed(digits);
}

function lineData(points) {
  return (points || []).filter((p) => p.value !== null && p.value !== undefined);
}

// V4-T12: weekly-first. /api/desk/chart-data only serves daily bars ("Only
// tf=1D is supported"), so weekly candles are resampled client-side from the
// daily series — deterministic, cheap, no backend change needed. ISO week
// (Monday start) is the bucket key so it lines up across bars/overlays/markers.
function isoWeekKey(dateStr) {
  const d = new Date(`${dateStr}T00:00:00Z`);
  const day = (d.getUTCDay() + 6) % 7; // Mon=0 .. Sun=6
  d.setUTCDate(d.getUTCDate() - day);
  return d.toISOString().slice(0, 10);
}

function resampleBarsWeekly(bars) {
  const order = [];
  const byKey = new Map();
  (bars || []).forEach((bar) => {
    const key = isoWeekKey(bar.time);
    let bucket = byKey.get(key);
    if (!bucket) {
      bucket = { time: key, open: bar.open, high: bar.high, low: bar.low, close: bar.close, volume: bar.volume || 0 };
      byKey.set(key, bucket);
      order.push(key);
    } else {
      bucket.high = Math.max(bucket.high, bar.high);
      bucket.low = Math.min(bucket.low, bar.low);
      bucket.close = bar.close;
      bucket.volume += bar.volume || 0;
    }
  });
  return order.map((key) => byKey.get(key));
}

function resampleLineWeekly(points) {
  const order = [];
  const byKey = new Map();
  lineData(points).forEach((p) => {
    const key = isoWeekKey(p.time);
    if (!byKey.has(key)) order.push(key);
    byKey.set(key, { time: key, value: p.value }); // last daily value in the week wins
  });
  return order.map((key) => byKey.get(key));
}

function resampleTimesWeekly(times) {
  const seen = new Set();
  const out = [];
  (times || []).forEach((t) => {
    const key = isoWeekKey(t);
    if (!seen.has(key)) {
      seen.add(key);
      out.push(key);
    }
  });
  return out;
}

function resampleVolumeWeekly(bars, volumeColors) {
  const order = [];
  const byKey = new Map();
  (bars || []).forEach((bar, idx) => {
    const key = isoWeekKey(bar.time);
    const color = VOLUME_COLORS[volumeColors?.[idx] || "noise"];
    let bucket = byKey.get(key);
    if (!bucket) {
      bucket = { time: key, value: bar.volume || 0, color };
      byKey.set(key, bucket);
      order.push(key);
    } else {
      bucket.value += bar.volume || 0;
      bucket.color = color; // most recent day in the week drives the color
    }
  });
  return order.map((key) => byKey.get(key));
}

function chartMarkers(data, layers, interval) {
  if (!data || !data.markers) return [];
  const bucket = interval === "W" ? isoWeekKey : (t) => t;
  const markers = [];
  (data.markers.purple_dot || []).forEach((time) => {
    markers.push({
      time: bucket(time),
      position: "belowBar",
      color: "#b66cff",
      shape: "circle",
      size: 0.6,
    });
  });
  if (layers.markers) {
    (data.markers.pocket_pivot || []).forEach((time) => {
      markers.push({
        time: bucket(time),
        position: "belowBar",
        color: "#1f8cff",
        shape: "arrowUp",
        text: "PP",
      });
    });
    (data.markers.persistency?.entry || []).forEach((row) => {
      markers.push({
        time: bucket(row.date),
        position: "belowBar",
        color: "#00c878",
        shape: "arrowUp",
        text: row.ema?.replace("ema", "E") || "E",
      });
    });
    (data.markers.persistency?.exit || []).forEach((row) => {
      markers.push({
        time: bucket(row.date),
        position: "aboveBar",
        color: "#ff4a5f",
        shape: "arrowDown",
        text: row.ema?.replace("ema", "X") || "X",
      });
    });
  }
  // lightweight-charts requires markers sorted ascending by time; the source
  // arrays above are concatenated per-category, so the combined list is not
  // in time order. Sort here or setMarkers() throws at runtime.
  markers.sort((a, b) => (a.time < b.time ? -1 : a.time > b.time ? 1 : 0));
  return markers;
}

const LAYER_DEFS = [
  { key: "ema50", label: "50/200 EMA" },
  { key: "markers", label: "Markers" },
  { key: "hmm", label: "HMM" },
  { key: "rmv", label: "RMV" },
];
// NOTE: a stage-of-market banner is spec'd in WIREFRAMES_V4.md's chart section
// but /api/desk/chart-data does not surface a stage field yet — no toggle for
// it here until the backend payload carries one (nothing to gate).

const LAYERS_STORAGE_KEY = "manas-chart-layers";

function loadLayerPrefs() {
  try {
    const raw = window.localStorage.getItem(LAYERS_STORAGE_KEY);
    if (!raw) return {};
    return JSON.parse(raw) || {};
  } catch (err) {
    return {};
  }
}

function saveLayerPrefs(layers) {
  try {
    window.localStorage.setItem(LAYERS_STORAGE_KEY, JSON.stringify(layers));
  } catch (err) {
    // localStorage unavailable (private mode etc.) — layer toggles just won't persist.
  }
}

const EMA_LEGEND = [
  { key: "ema10", label: "10 EMA", color: "#f8c14a", always: true },
  { key: "ema21", label: "21 EMA", color: "#4dd2ff", always: true },
  { key: "ema50", label: "50 EMA", color: "#c084fc", layer: "ema50" },
  { key: "ema200", label: "200 EMA", color: "#f97316", layer: "ema50" },
];

class ChartErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    // eslint-disable-next-line no-console
    console.error("ChartDrawer chart render failed:", error, info?.componentStack);
  }

  componentDidUpdate(prevProps) {
    if (prevProps.resetKey !== this.props.resetKey && this.state.error) {
      this.setState({ error: null });
    }
  }

  render() {
    if (this.state.error) {
      return (
        <div className="chart-drawer-state">
          Chart could not render: {String(this.state.error?.message || this.state.error)}
        </div>
      );
    }
    return this.props.children;
  }
}

// AlgoPoint-style per-stock HMM "MODEL STATE" box — EXPERIMENTAL, fact-only,
// never a verdict. Renders the honest unavailable reason when the symbol
// doesn't have enough clean history for the fit yet.
function ModelStateBox({ hmm }) {
  if (!hmm) return null;
  if (!hmm.available) {
    return (
      <div className="model-state-box model-state-unavailable mono">
        <span className="model-state-label">
          <Term k="stock-hmm-experimental">STOCK HMM</Term> <span className="experimental-badge">EXPERIMENTAL</span>
        </span>
        <span>{hmm.reason || "unavailable"}</span>
      </div>
    );
  }
  const current = hmm.current || {};
  const stateClass = (current.state || "").toLowerCase();
  return (
    <div className="model-state-box mono" data-state={stateClass}>
      <span className="model-state-label">
        <Term k="stock-hmm-experimental">STOCK HMM</Term> <span className="experimental-badge">EXPERIMENTAL</span>
      </span>
      <span className={"model-state-pill state-" + stateClass}>{current.state || "-"}</span>
      <span className={"model-state-conf conf-" + (current.confidence || "").toLowerCase()}>
        {CONFIDENCE_LABEL[current.confidence] || "-"} conf
      </span>
      <span className="model-state-probs">
        <i style={{ background: HMM_COLORS.bull }} /> {fmt((current.p_bull || 0) * 100, 0)}%
        <i style={{ background: HMM_COLORS.chop }} /> {fmt((current.p_chop || 0) * 100, 0)}%
        <i style={{ background: HMM_COLORS.bear }} /> {fmt((current.p_bear || 0) * 100, 0)}%
      </span>
    </div>
  );
}

function HeaderStrip({ data }) {
  const meta = data?.meta || {};
  const burst = meta.burst_power || {};
  const mswing = meta.mswing || {};
  const ss = meta.ss_rvol || {};
  return (
    <div className="chart-drawer-strip">
      <span>
        <b>BP</b> {fmt(burst.power_value, 2)} ({burst.rounded ?? "-"})
      </span>
      <span>
        <b>Mswing</b> {fmt(mswing.mswing, 2)} vs {fmt(mswing.index_mswing, 2)} {MSWING_LABEL[mswing.color] || ""}
      </span>
      <span>
        <b>RVOL</b> {fmt(ss.rvol, 2)}x {ss.star ? "SS*" : ""}
      </span>
      <span>
        <b>RMV</b> {fmt(meta.rmv?.rmv, 1)}
      </span>
    </div>
  );
}

export default function ChartDrawer({ symbol, date, onClose, defaultInterval }) {
  const hostRef = useRef(null);
  const rmvRef = useRef(null);
  const hmmRef = useRef(null);
  const chartRef = useRef(null);
  const rmvChartRef = useRef(null);
  const hmmChartRef = useRef(null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  // V4-T12: weekly-first when opened from SCANNERS/SHORTLIST (defaultInterval="W"),
  // daily-first from POSITIONS/DEBATE/MARKET (defaultInterval unset). The interval
  // itself is per-open state, not persisted — the caller's context decides the default.
  const [interval, setInterval] = useState(defaultInterval === "W" ? "W" : "D");
  const [layers, setLayers] = useState(() => ({
    ema50: false,
    markers: false,
    hmm: false,
    rmv: false,
    ...loadLayerPrefs(),
  }));

  useEffect(() => {
    setInterval(defaultInterval === "W" ? "W" : "D");
  }, [symbol, defaultInterval]);

  function toggleLayer(key) {
    setLayers((prev) => {
      const next = { ...prev, [key]: !prev[key] };
      saveLayerPrefs(next);
      return next;
    });
  }

  useEffect(() => {
    if (!symbol) return undefined;
    let cancelled = false;
    setData(null);
    setError(null);
    setLoading(true);
    fetchChartData(symbol, date)
      .then((body) => {
        if (!cancelled) setData(body);
      })
      .catch((err) => {
        if (!cancelled) setError(String(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [symbol, date]);

  useEffect(() => {
    if (!symbol) return undefined;
    function onKey(event) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [symbol, onClose]);

  const weeklyBars = useMemo(() => resampleBarsWeekly(data?.bars), [data]);
  const bars = interval === "W" ? weeklyBars : data?.bars || [];

  const volumeData = useMemo(() => {
    if (!data?.bars?.length) return [];
    if (interval === "W") return resampleVolumeWeekly(data.bars, data.panes?.volume_colors);
    return data.bars.map((bar, idx) => ({
      time: bar.time,
      value: bar.volume || 0,
      color: VOLUME_COLORS[data.panes?.volume_colors?.[idx] || "noise"],
    }));
  }, [data, interval]);

  const overlayData = useMemo(() => {
    const overlays = data?.overlays || {};
    const out = {};
    ["ema10", "ema21", "ema50", "ema200"].forEach((key) => {
      out[key] = interval === "W" ? resampleLineWeekly(overlays[key]) : lineData(overlays[key]);
    });
    return out;
  }, [data, interval]);

  const rmvData = useMemo(() => {
    const rmv = data?.panes?.rmv || [];
    if (interval !== "W") return rmv;
    // sample-hold: last daily RMV reading in the week represents the week
    const weekKeys = resampleTimesWeekly(rmv.map((p) => p.time));
    const byWeek = new Map();
    rmv.forEach((p) => byWeek.set(isoWeekKey(p.time), p));
    return weekKeys.map((key) => ({ time: key, value: byWeek.get(key)?.value ?? null }));
  }, [data, interval]);

  const hmmSeries = useMemo(() => {
    const hmm = data?.hmm;
    if (!hmm?.available || !hmm.series?.length) return [];
    // Cumulative bands for a visual stack: draw largest-cumulative area
    // first (back), progressively smaller on top (front) — bull ends up
    // as the bottom-most visible band, bear the top-most.
    const full = hmm.series.map((p) => ({ time: p.time, value: 1 }));
    const bullChop = hmm.series.map((p) => ({ time: p.time, value: (p.p_bull || 0) + (p.p_chop || 0) }));
    const bullOnly = hmm.series.map((p) => ({ time: p.time, value: p.p_bull || 0 }));
    return [
      { data: full, color: HMM_COLORS.bear, key: "bear" },
      { data: bullChop, color: HMM_COLORS.chop, key: "chop" },
      { data: bullOnly, color: HMM_COLORS.bull, key: "bull" },
    ];
  }, [data]);

  useEffect(() => {
    if (!hostRef.current || !data?.available || !bars.length) return undefined;
    if (layers.rmv && !rmvRef.current) return undefined;
    if (layers.hmm && hmmSeries.length && !hmmRef.current) return undefined;
    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
    }
    if (rmvChartRef.current) {
      rmvChartRef.current.remove();
      rmvChartRef.current = null;
    }
    if (hmmChartRef.current) {
      hmmChartRef.current.remove();
      hmmChartRef.current = null;
    }
    const host = hostRef.current;
    const rmvHost = rmvRef.current;
    const hmmHost = hmmRef.current;
    const chart = createChart(host, {
      width: host.clientWidth,
      height: host.clientHeight,
      layout: {
        background: { color: "#0b0f14" },
        textColor: "#c9d3df",
      },
      grid: {
        vertLines: { color: "#17202b" },
        horzLines: { color: "#17202b" },
      },
      rightPriceScale: { borderColor: "#27313d" },
      timeScale: { borderColor: "#27313d" },
      crosshair: { mode: 1 },
    });
    chartRef.current = chart;

    const candles = chart.addCandlestickSeries({
      upColor: "#00c878",
      downColor: "#ff4a5f",
      borderVisible: false,
      wickUpColor: "#00c878",
      wickDownColor: "#ff4a5f",
    });
    candles.setData(bars);
    if (candles.setMarkers) candles.setMarkers(chartMarkers(data, layers, interval));

    const volume = chart.addHistogramSeries({
      priceFormat: { type: "volume" },
      priceScaleId: "volume",
      lastValueVisible: false,
      priceLineVisible: false,
    });
    volume.priceScale().applyOptions({ scaleMargins: { top: 0.78, bottom: 0 } });
    volume.setData(volumeData);

    // V4-T12: EMA10/21 are always-on defaults; 50/200 sit behind the "50/200
    // EMA" layer chip. No on-chart title — the legend chip row under the
    // chart carries the color-to-name mapping instead of inline "e10"/"e50"
    // text on the series.
    const emaKeys = layers.ema50 ? ["ema10", "ema21", "ema50", "ema200"] : ["ema10", "ema21"];
    const EMA_COLORS = { ema10: "#f8c14a", ema21: "#4dd2ff", ema50: "#c084fc", ema200: "#f97316" };
    emaKeys.forEach((key) => {
      const series = chart.addLineSeries({
        color: EMA_COLORS[key],
        lineWidth: key === "ema200" ? 2 : 1,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      series.setData(overlayData[key] || []);
    });

    let rmvChart = null;
    if (layers.rmv && rmvHost) {
      rmvChart = createChart(rmvHost, {
        width: rmvHost.clientWidth,
        height: rmvHost.clientHeight,
        layout: { background: { color: "#0b0f14" }, textColor: "#c9d3df" },
        grid: {
          vertLines: { color: "#17202b" },
          horzLines: { color: "#17202b" },
        },
        rightPriceScale: { borderColor: "#27313d" },
        timeScale: { borderColor: "#27313d" },
      });
      rmvChartRef.current = rmvChart;
      const rmv = rmvChart.addHistogramSeries({
        color: "#7dd3fc",
        priceFormat: { type: "price", precision: 0, minMove: 1 },
        lastValueVisible: false,
        priceLineVisible: false,
      });
      rmv.setData(rmvData.map((p) => ({
        time: p.time,
        value: p.value || 0,
        color: p.value !== null && p.value <= 20 ? "#f8c14a" : "#7dd3fc",
      })));
    }

    let hmmChart = null;
    if (layers.hmm && hmmHost && hmmSeries.length) {
      hmmChart = createChart(hmmHost, {
        width: hmmHost.clientWidth,
        height: hmmHost.clientHeight,
        layout: { background: { color: "#0b0f14" }, textColor: "#c9d3df" },
        grid: {
          vertLines: { color: "#17202b" },
          horzLines: { color: "#17202b" },
        },
        rightPriceScale: {
          borderColor: "#27313d",
          scaleMargins: { top: 0.05, bottom: 0.05 },
        },
        timeScale: { borderColor: "#27313d" },
      });
      hmmChartRef.current = hmmChart;
      hmmSeries.forEach(({ data: seriesData, color }) => {
        const area = hmmChart.addAreaSeries({
          topColor: color,
          bottomColor: color,
          lineColor: color,
          lineWidth: 1,
          lastValueVisible: false,
          priceLineVisible: false,
          priceFormat: { type: "custom", minMove: 0.01, formatter: (v) => `${Math.round(v * 100)}%` },
        });
        area.setData(seriesData);
      });
      hmmChart.timeScale().fitContent();
    }

    chart.timeScale().fitContent();
    if (rmvChart) rmvChart.timeScale().fitContent();

    function resize() {
      chart.applyOptions({ width: host.clientWidth, height: host.clientHeight });
      if (rmvChart && rmvHost) {
        rmvChart.applyOptions({ width: rmvHost.clientWidth, height: rmvHost.clientHeight });
      }
      if (hmmChart && hmmHost) {
        hmmChart.applyOptions({ width: hmmHost.clientWidth, height: hmmHost.clientHeight });
      }
    }
    window.addEventListener("resize", resize);
    return () => {
      window.removeEventListener("resize", resize);
      chart.remove();
      if (rmvChart) rmvChart.remove();
      if (hmmChart) hmmChart.remove();
      chartRef.current = null;
      rmvChartRef.current = null;
      hmmChartRef.current = null;
    };
  }, [data, bars, volumeData, overlayData, rmvData, hmmSeries, layers, interval]);

  if (!symbol) return null;

  return (
    <div className="chart-drawer-root" role="dialog" aria-modal="true" aria-label={`${symbol} chart`}>
      <button className="chart-drawer-backdrop" onClick={onClose} aria-label="close chart overlay" />
      <aside className="chart-drawer">
        <header className="chart-drawer-head">
          <div>
            <p className="overline accent">Chart</p>
            <h2>{symbol}</h2>
            <span className="mono chart-drawer-date">{data?.as_of || date}</span>
          </div>
          <button className="chart-drawer-close" onClick={onClose} aria-label="close chart">
            X
          </button>
        </header>
        <HeaderStrip data={data} />
        <ModelStateBox hmm={data?.hmm} />
        <div className="chart-drawer-controls">
          <div className="chart-interval-toggle mono" role="group" aria-label="chart interval">
            <button
              type="button"
              className={interval === "D" ? "is-active" : ""}
              onClick={() => setInterval("D")}
            >
              D
            </button>
            <button
              type="button"
              className={interval === "W" ? "is-active" : ""}
              onClick={() => setInterval("W")}
            >
              W
            </button>
          </div>
          <div className="chart-layer-chips mono" role="group" aria-label="chart layers">
            {LAYER_DEFS.map((def) => (
              <button
                key={def.key}
                type="button"
                className={"chart-layer-chip" + (layers[def.key] ? " is-active" : "")}
                onClick={() => toggleLayer(def.key)}
                aria-pressed={!!layers[def.key]}
              >
                {def.label}
              </button>
            ))}
          </div>
        </div>
        <div className="chart-drawer-body">
          {loading && <div className="chart-drawer-state">Loading chart...</div>}
          {error && <div className="chart-drawer-state">Could not load chart: {error}</div>}
          {!loading && !error && data && !data.available && (
            <div className="chart-drawer-state">No daily price history for {symbol}.</div>
          )}
          {!loading && !error && data?.available && (
            <ChartErrorBoundary resetKey={`${symbol}:${date}:${interval}`}>
              <div className={"chart-host" + (layers.hmm && data?.hmm?.available ? " chart-host-with-hmm" : "")}>
                <div ref={hostRef} className="chart-host-main" />
                {layers.rmv && (
                  <>
                    <div className="chart-host-rmv-label mono">RMV</div>
                    <div ref={rmvRef} className="chart-host-rmv" />
                  </>
                )}
                {layers.hmm && data?.hmm?.available && (
                  <>
                    <div className="chart-host-hmm-label mono">
                      <Term k="stock-hmm-experimental">HMM</Term> <span className="experimental-badge">EXPERIMENTAL</span>
                    </div>
                    <div ref={hmmRef} className="chart-host-hmm" />
                  </>
                )}
              </div>
            </ChartErrorBoundary>
          )}
        </div>
        <footer className="chart-drawer-legend mono">
          {EMA_LEGEND.filter((item) => item.always || layers[item.layer]).map((item) => (
            <span key={item.key}><i style={{ background: item.color }} /> {item.label}</span>
          ))}
          <span><i style={{ background: VOLUME_COLORS.bull_pp }} /> bull PP</span>
          <span><i style={{ background: VOLUME_COLORS.bear_pp }} /> bear PP</span>
          <span><i style={{ background: VOLUME_COLORS.dry }} /> dry</span>
          <span><i style={{ background: "#b66cff" }} /> purple dot</span>
        </footer>
      </aside>
    </div>
  );
}
