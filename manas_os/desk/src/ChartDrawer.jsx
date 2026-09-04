import React, { useEffect, useMemo, useRef, useState } from "react";
import { createChart } from "lightweight-charts";
import { fetchAlphaActivitySymbol, fetchChartData } from "./api.js";
import { Term } from "./Glossary.jsx";
import { useDensity } from "./DensityContext.jsx";
import StatusBadge from "./components/v5/StatusBadge.jsx";

// ── #14 token migration: the gate forbids raw hex in .jsx, but lightweight-charts
// needs real color strings (not var()). Resolve each --v5-* chart token to its
// computed hex at runtime via getComputedStyle, so the token layer stays the
// single source of truth. Spec: V5_TOKEN_MIGRATION_DESIGN.md §1-§2.
const _tokenCache = {};
function tk(name) {
  if (_tokenCache[name]) return _tokenCache[name];
  const tokenRoot = document.querySelector(".v5") || document.documentElement;
  let v = getComputedStyle(tokenRoot).getPropertyValue(name).trim();
  // resolve var() chains (the chart tokens alias base tokens, e.g.
  // --v5-chart-bg → --v5-panel → #fffdf9). getComputedStyle already resolves
  // these on .v5 root, but be defensive: if it returns a var() ref, follow it.
  let guard = 0;
  while (v.startsWith("var(") && guard++ < 5) {
    const inner = v.match(/var\(\s*(--[\w-]+)/);
    if (!inner) break;
    v = getComputedStyle(tokenRoot).getPropertyValue(inner[1]).trim();
  }
  _tokenCache[name] = v;
  return v;
}

// Color constants now reference tokens, resolved lazily on first chart render.
// Previously these held raw hexes (#00c878, #b66cff, …) — a second dark palette
// inside the v5 light shell (the "dark island" release blocker).
const HMM_COLORS = {
  bull: () => tk("--v5-hmm-bull"),
  chop: () => tk("--v5-hmm-chop"),
  bear: () => tk("--v5-hmm-bear"),
};

const CONFIDENCE_LABEL = { LOW: "LOW", MED: "MED", HIGH: "HIGH" };

const VOLUME_COLORS = {
  bull_pp: () => tk("--v5-vol-bull-pp"),
  bear_pp: () => tk("--v5-vol-bear-pp"),
  dry: () => tk("--v5-vol-dry"),
  up: () => tk("--v5-vol-up"),
  down: () => tk("--v5-vol-down"),
  noise: () => tk("--v5-vol-noise"),
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
    const color = VOLUME_COLORS[volumeColors?.[idx] || "noise"]();
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
      color: tk("--v5-marker-purple"),
      shape: "circle",
      size: 0.6,
    });
  });
  if (layers.markers) {
    (data.markers.pocket_pivot || []).forEach((time) => {
      markers.push({
        time: bucket(time),
        position: "belowBar",
        color: tk("--v5-marker-pp"),
        shape: "arrowUp",
        text: "PP",
      });
    });
    (data.markers.persistency?.entry || []).forEach((row) => {
      markers.push({
        time: bucket(row.date),
        position: "belowBar",
        color: tk("--v5-marker-entry"),
        shape: "arrowUp",
        text: row.ema?.replace("ema", "E") || "E",
      });
    });
    (data.markers.persistency?.exit || []).forEach((row) => {
      markers.push({
        time: bucket(row.date),
        position: "aboveBar",
        color: tk("--v5-marker-exit"),
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
  { key: "compare", label: "vs theme / index" },
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
  { key: "ema10", label: "10 EMA", token: "--v5-ema-10", always: true },
  { key: "ema21", label: "21 EMA", token: "--v5-ema-21", always: true },
  { key: "ema50", label: "50 EMA", token: "--v5-ema-50", layer: "ema50" },
  { key: "ema200", label: "200 EMA", token: "--v5-ema-200", layer: "ema50" },
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
function ModelStateBox({ hmm, isExpert }) {
  if (!isExpert) return null;
  if (!hmm) return null;
  if (!hmm.available) {
    return (
      <div className="model-state-box model-state-unavailable mono">
        <span className="model-state-label">
          <Term k="stock-hmm-experimental">STOCK HMM</Term> <StatusBadge status="EXPERIMENTAL" />
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
        <Term k="stock-hmm-experimental">STOCK HMM</Term> <StatusBadge status="EXPERIMENTAL" />
      </span>
      <span className={"model-state-pill state-" + stateClass}>{current.state || "-"}</span>
      <span className={"model-state-conf conf-" + (current.confidence || "").toLowerCase()}>
        {CONFIDENCE_LABEL[current.confidence] || "-"} conf
      </span>
      <span className="model-state-probs">
        <i style={{ background: HMM_COLORS.bull() }} /> {fmt((current.p_bull || 0) * 100, 0)}%
        <i style={{ background: HMM_COLORS.chop() }} /> {fmt((current.p_chop || 0) * 100, 0)}%
        <i style={{ background: HMM_COLORS.bear() }} /> {fmt((current.p_bear || 0) * 100, 0)}%
      </span>
    </div>
  );
}

// F6: STOCK HMM / Mswing / RMV are expert-only header stats -- same
// DensityContext gate DebateTab/MarketTab already use for their [E] blocks.
// BP and RVOL stay visible in beginner mode (not named in the F6 ask).
function HeaderStrip({ data }) {
  const { isExpert } = useDensity();
  const meta = data?.meta || {};
  const burst = meta.burst_power || {};
  const mswing = meta.mswing || {};
  const ss = meta.ss_rvol || {};
  return (
    <div className="chart-drawer-strip">
      <span>
        <b>BP</b> {fmt(burst.power_value, 2)} ({burst.rounded ?? "-"})
      </span>
      {isExpert && (
        <span>
          <b>Mswing</b> {fmt(mswing.mswing, 2)} vs {fmt(mswing.index_mswing, 2)} {MSWING_LABEL[mswing.color] || ""}
        </span>
      )}
      <span>
        <b>RVOL</b> {fmt(ss.rvol, 2)}x {ss.star ? "SS*" : ""}
      </span>
      {isExpert && (
        <span>
          <b>RMV</b> {fmt(meta.rmv?.rmv, 1)}
        </span>
      )}
    </div>
  );
}

function ActivityEvidencePane({ activity }) {
  const trail = activity?.trail || [];
  if (activity?.state !== "ready" || !trail.length) {
    return <div className="chart-activity-empty">Unusual-activity history is warming. Twenty valid bhavcopy sessions are required.</div>;
  }
  const maxScore = Math.max(8, ...trail.map((row) => Number(row.score) || 0));
  const latest = activity.latest || trail[trail.length - 1];
  return (
    <section className="chart-activity" aria-label={`${activity.symbol} direction-neutral unusual activity`}>
      <div className="chart-activity-head">
        <div><b>EOD unusual activity</b><span>abnormal participation · direction unresolved</span></div>
        <div className="chart-activity-latest"><b>{fmt(latest?.score, 2)}</b><span>{String(latest?.state || "baseline").replaceAll("_", " ")}</span></div>
      </div>
      <div className="chart-activity-panel">
        <span className="chart-activity-axis mono">score</span>
        <div className="chart-activity-bars" role="img" aria-label={`Activity scores from ${trail[0]?.as_of_date} to ${trail[trail.length - 1]?.as_of_date}`}>
          <i className="chart-activity-line" style={{ bottom: `${(3.5 / maxScore) * 100}%` }}><span>3.5 abnormal</span></i>
          {trail.map((row) => <span key={row.as_of_date} className={`chart-activity-bar state-${row.state}`} style={{ height: `${Math.max(4, (Number(row.score) / maxScore) * 100)}%` }} title={`${row.as_of_date} · score ${fmt(row.score, 2)} · ${String(row.state).replaceAll("_", " ")}`} />)}
        </div>
      </div>
      <div className="chart-activity-panel chart-delivery-panel">
        <span className="chart-activity-axis mono">delivery</span>
        <div className="chart-activity-bars" role="img" aria-label={`Delivery percentage from ${trail[0]?.as_of_date} to ${trail[trail.length - 1]?.as_of_date}`}>
          <i className="chart-delivery-line" style={{ bottom: "50%" }}><span>50%</span></i>
          {trail.map((row) => <span key={row.as_of_date} className="chart-delivery-bar" style={{ height: `${Math.max(3, Math.min(100, Number(row.delivery_pct) || 0))}%` }} title={`${row.as_of_date} · delivery ${fmt(row.delivery_pct, 1)}%`} />)}
        </div>
      </div>
      <div className="chart-activity-dates mono"><span>{trail[0]?.as_of_date}</span><span>{trail[trail.length - 1]?.as_of_date}</span></div>
      <details className="chart-activity-explain"><summary>How to read this</summary><p>A single high bar can precede a sharp move or exhaustion. Repeated 3.5+ readings indicate persistent abnormal participation. Use price, volume, theme-relative behaviour and the setup—not this score alone—to infer direction.</p></details>
    </section>
  );
}

export default function ChartDrawer({ symbol, date, onClose, defaultInterval }) {
  const { isExpert } = useDensity();
  const hostRef = useRef(null);
  const rmvRef = useRef(null);
  const hmmRef = useRef(null);
  const chartRef = useRef(null);
  const rmvChartRef = useRef(null);
  const hmmChartRef = useRef(null);
  const compareRef = useRef(null);
  const compareChartRef = useRef(null);
  const [data, setData] = useState(null);
  const [activity, setActivity] = useState(null);
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
    compare: false,
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
    setActivity(null);
    setError(null);
    setLoading(true);
    Promise.all([
      fetchChartData(symbol, date),
      fetchAlphaActivitySymbol(symbol, date, 30).catch(() => null),
    ])
      .then(([body, activityBody]) => {
        if (!cancelled) {
          setData(body);
          setActivity(activityBody);
        }
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
      color: VOLUME_COLORS[data.panes?.volume_colors?.[idx] || "noise"](),
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
      { data: full, color: HMM_COLORS.bear(), key: "bear" },
      { data: bullChop, color: HMM_COLORS.chop(), key: "chop" },
      { data: bullOnly, color: HMM_COLORS.bull(), key: "bull" },
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
    if (compareChartRef.current) {
      compareChartRef.current.remove();
      compareChartRef.current = null;
    }
    const host = hostRef.current;
    const rmvHost = rmvRef.current;
    const hmmHost = hmmRef.current;
    const compareHost = compareRef.current;
    const chart = createChart(host, {
      width: host.clientWidth,
      height: host.clientHeight,
      layout: {
        background: { color: tk("--v5-chart-bg") },
        textColor: tk("--v5-chart-axis"),
      },
      grid: {
        vertLines: { color: tk("--v5-chart-grid") },
        horzLines: { color: tk("--v5-chart-grid") },
      },
      rightPriceScale: { borderColor: tk("--v5-chart-border") },
      timeScale: { borderColor: tk("--v5-chart-border") },
      crosshair: { mode: 1 },
    });
    chartRef.current = chart;

    const candles = chart.addCandlestickSeries({
      upColor: tk("--v5-up"),
      downColor: tk("--v5-down"),
      borderVisible: false,
      wickUpColor: tk("--v5-up"),
      wickDownColor: tk("--v5-down"),
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
    const EMA_COLORS = { ema10: tk("--v5-ema-10"), ema21: tk("--v5-ema-21"), ema50: tk("--v5-ema-50"), ema200: tk("--v5-ema-200") };
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
        layout: { background: { color: tk("--v5-chart-bg") }, textColor: tk("--v5-chart-axis") },
        grid: {
          vertLines: { color: tk("--v5-chart-grid") },
          horzLines: { color: tk("--v5-chart-grid") },
        },
        rightPriceScale: { borderColor: tk("--v5-chart-border") },
        timeScale: { borderColor: tk("--v5-chart-border") },
      });
      rmvChartRef.current = rmvChart;
      const rmv = rmvChart.addHistogramSeries({
        color: tk("--v5-rmv-base"),
        priceFormat: { type: "price", precision: 0, minMove: 1 },
        lastValueVisible: false,
        priceLineVisible: false,
      });
      rmv.setData(rmvData.map((p) => ({
        time: p.time,
        value: p.value || 0,
        color: p.value !== null && p.value <= 20 ? tk("--v5-rmv-alert") : tk("--v5-rmv-base"),
      })));
    }

    let hmmChart = null;
    if (layers.hmm && hmmHost && hmmSeries.length) {
      hmmChart = createChart(hmmHost, {
        width: hmmHost.clientWidth,
        height: hmmHost.clientHeight,
        layout: { background: { color: tk("--v5-chart-bg") }, textColor: tk("--v5-chart-axis") },
        grid: {
          vertLines: { color: tk("--v5-chart-grid") },
          horzLines: { color: tk("--v5-chart-grid") },
        },
        rightPriceScale: {
          borderColor: tk("--v5-chart-border"),
          scaleMargins: { top: 0.05, bottom: 0.05 },
        },
        timeScale: { borderColor: tk("--v5-chart-border") },
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

    let compareChart = null;
    if (layers.compare && compareHost && data?.comparison?.stock?.length) {
      compareChart = createChart(compareHost, {
        width: compareHost.clientWidth, height: compareHost.clientHeight,
        layout: { background: { color: tk("--v5-chart-bg") }, textColor: tk("--v5-chart-axis") },
        grid: { vertLines: { color: tk("--v5-chart-grid") }, horzLines: { color: tk("--v5-chart-grid") } },
        rightPriceScale: { borderColor: tk("--v5-chart-border") }, timeScale: { borderColor: tk("--v5-chart-border") },
      });
      compareChartRef.current = compareChart;
      [["stock", tk("--v5-ema-10")], ["theme", tk("--v5-ema-21")], ["broad", tk("--v5-chart-axis")]].forEach(([key, color]) => {
        if (!data.comparison[key]?.length) return;
        const series = compareChart.addLineSeries({ color, lineWidth: key === "stock" ? 2 : 1, priceLineVisible: false, lastValueVisible: false });
        series.setData(data.comparison[key]);
      });
      compareChart.timeScale().fitContent();
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
      if (compareChart && compareHost) compareChart.applyOptions({ width: compareHost.clientWidth, height: compareHost.clientHeight });
    }
    window.addEventListener("resize", resize);
    return () => {
      window.removeEventListener("resize", resize);
      chart.remove();
      if (rmvChart) rmvChart.remove();
      if (hmmChart) hmmChart.remove();
      if (compareChart) compareChart.remove();
      chartRef.current = null;
      rmvChartRef.current = null;
      hmmChartRef.current = null;
      compareChartRef.current = null;
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
            <div className="chart-drawer-market-line mono">
              <span className="chart-drawer-date">{data?.as_of || date}</span>
              {data?.market_data?.price !== null && data?.market_data?.price !== undefined && (
                <span className={`chart-market-state is-${String(data.market_data.state || "empty").toLowerCase()}`}>
                  ₹{Number(data.market_data.price).toLocaleString("en-IN", { maximumFractionDigits: 2 })}
                  {` · ${String(data.market_data.state || "").replace("_", " ")}`}
                </span>
              )}
            </div>
          </div>
          <button className="chart-drawer-close" onClick={onClose} aria-label="close chart">
            X
          </button>
        </header>
        <HeaderStrip data={data} />
        <ModelStateBox hmm={data?.hmm} isExpert={isExpert} />
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
                      <Term k="stock-hmm-experimental">HMM</Term> <StatusBadge status="EXPERIMENTAL" />
                    </div>
                    <div ref={hmmRef} className="chart-host-hmm" />
                  </>
                )}
                {layers.compare && (
                  <>
                    <div className="chart-host-compare-label mono">Relative behaviour · {symbol} vs {data?.comparison?.industry || "theme unavailable"} vs {data?.comparison?.broad_label || "broad index"} · rebased 100</div>
                    <div ref={compareRef} className="chart-host-compare" />
                  </>
                )}
              </div>
              <ActivityEvidencePane activity={activity} />
            </ChartErrorBoundary>
          )}
        </div>
        <footer className="chart-drawer-legend mono">
          {EMA_LEGEND.filter((item) => item.always || layers[item.layer]).map((item) => (
            <span key={item.key}><i style={{ background: tk(item.token) }} /> {item.label}</span>
          ))}
          <span><i style={{ background: VOLUME_COLORS.bull_pp() }} /> bull PP</span>
          <span><i style={{ background: VOLUME_COLORS.bear_pp() }} /> bear PP</span>
          <span><i style={{ background: VOLUME_COLORS.dry() }} /> dry</span>
          <span><i style={{ background: tk("--v5-marker-purple") }} /> purple dot</span>
        </footer>
      </aside>
    </div>
  );
}
