import React, { useEffect, useMemo, useRef, useState } from "react";
import { createChart } from "lightweight-charts";
import { fetchChartData } from "./api.js";

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

function chartMarkers(data) {
  if (!data || !data.markers) return [];
  const markers = [];
  (data.markers.purple_dot || []).forEach((time) => {
    markers.push({
      time,
      position: "aboveBar",
      color: "#b66cff",
      shape: "circle",
      text: "PD",
    });
  });
  (data.markers.pocket_pivot || []).forEach((time) => {
    markers.push({
      time,
      position: "belowBar",
      color: "#1f8cff",
      shape: "arrowUp",
      text: "PP",
    });
  });
  (data.markers.persistency?.entry || []).forEach((row) => {
    markers.push({
      time: row.date,
      position: "belowBar",
      color: "#00c878",
      shape: "arrowUp",
      text: row.ema?.replace("ema", "E") || "E",
    });
  });
  (data.markers.persistency?.exit || []).forEach((row) => {
    markers.push({
      time: row.date,
      position: "aboveBar",
      color: "#ff4a5f",
      shape: "arrowDown",
      text: row.ema?.replace("ema", "X") || "X",
    });
  });
  // lightweight-charts requires markers sorted ascending by time; the source
  // arrays above are concatenated per-category (purple dots, pocket pivots,
  // then persistency entries grouped per-EMA), so the combined list is not
  // in time order. Sort here or setMarkers() throws at runtime.
  markers.sort((a, b) => (a.time < b.time ? -1 : a.time > b.time ? 1 : 0));
  return markers;
}

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

export default function ChartDrawer({ symbol, date, onClose }) {
  const hostRef = useRef(null);
  const rmvRef = useRef(null);
  const chartRef = useRef(null);
  const rmvChartRef = useRef(null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

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

  const volumeData = useMemo(() => {
    if (!data?.bars?.length) return [];
    return data.bars.map((bar, idx) => ({
      time: bar.time,
      value: bar.volume || 0,
      color: VOLUME_COLORS[data.panes?.volume_colors?.[idx] || "noise"],
    }));
  }, [data]);

  useEffect(() => {
    if (!hostRef.current || !rmvRef.current || !data?.available || !data.bars?.length) return undefined;
    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
    }
    if (rmvChartRef.current) {
      rmvChartRef.current.remove();
      rmvChartRef.current = null;
    }
    const host = hostRef.current;
    const rmvHost = rmvRef.current;
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
    candles.setData(data.bars);
    if (candles.setMarkers) candles.setMarkers(chartMarkers(data));

    const volume = chart.addHistogramSeries({
      priceFormat: { type: "volume" },
      priceScaleId: "volume",
      lastValueVisible: false,
      priceLineVisible: false,
    });
    volume.priceScale().applyOptions({ scaleMargins: { top: 0.78, bottom: 0 } });
    volume.setData(volumeData);

    [
      ["ema10", "#f8c14a"],
      ["ema21", "#4dd2ff"],
      ["ema50", "#c084fc"],
      ["ema200", "#f97316"],
    ].forEach(([key, color]) => {
      const series = chart.addLineSeries({
        color,
        lineWidth: key === "ema200" ? 2 : 1,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      series.setData(lineData(data.overlays?.[key]));
    });

    const rmvChart = createChart(rmvHost, {
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
    rmv.setData((data.panes?.rmv || []).map((p) => ({
      time: p.time,
      value: p.value || 0,
      color: p.value !== null && p.value <= 20 ? "#f8c14a" : "#7dd3fc",
    })));

    chart.timeScale().fitContent();
    rmvChart.timeScale().fitContent();

    function resize() {
      chart.applyOptions({ width: host.clientWidth, height: host.clientHeight });
      rmvChart.applyOptions({ width: rmvHost.clientWidth, height: rmvHost.clientHeight });
    }
    window.addEventListener("resize", resize);
    return () => {
      window.removeEventListener("resize", resize);
      chart.remove();
      rmvChart.remove();
      chartRef.current = null;
      rmvChartRef.current = null;
    };
  }, [data, volumeData]);

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
        <div className="chart-drawer-body">
          {loading && <div className="chart-drawer-state">Loading chart...</div>}
          {error && <div className="chart-drawer-state">Could not load chart: {error}</div>}
          {!loading && !error && data && !data.available && (
            <div className="chart-drawer-state">No daily price history for {symbol}.</div>
          )}
          {!loading && !error && data?.available && (
            <ChartErrorBoundary resetKey={`${symbol}:${date}`}>
              <div className="chart-host">
                <div ref={hostRef} className="chart-host-main" />
                <div className="chart-host-rmv-label mono">RMV</div>
                <div ref={rmvRef} className="chart-host-rmv" />
              </div>
            </ChartErrorBoundary>
          )}
        </div>
        <footer className="chart-drawer-legend mono">
          <span><i style={{ background: VOLUME_COLORS.bull_pp }} /> bull PP</span>
          <span><i style={{ background: VOLUME_COLORS.bear_pp }} /> bear PP</span>
          <span><i style={{ background: VOLUME_COLORS.dry }} /> dry</span>
          <span><i style={{ background: "#b66cff" }} /> purple dot</span>
        </footer>
      </aside>
    </div>
  );
}
