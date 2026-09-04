import React, { useEffect, useRef } from "react";
import {
  createChart,
  CandlestickSeries,
  LineSeries,
  CrosshairMode,
  createSeriesMarkers,
} from "lightweight-charts";

/**
 * TradingView lightweight-charts candle view with overlaid SMAs and
 * purple-dot markers (≥5% ROC + heavy volume — bread-and-butter "explosive
 * buying force" trigger encoded in Pine as
 *   abs(roc(close,1)) >= 5% AND volume >= threshold
 * which we already store as `purple_dot=1` in the features DB).
 *
 * Props:
 *   bars: [{date, open, high, low, close, sma20?, sma50?, sma200?, purple_dot?}]
 *   height: chart pixel height (default 320)
 */
export default function LightweightChart({ bars = [], height = 320 }) {
  const containerRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current || !bars.length) return;

    const chart = createChart(containerRef.current, {
      height,
      autoSize: true,
      localization: {
        locale: "en-US",
        dateFormat: "yyyy-MM-dd",
      },
      layout: {
        background: { color: "#050505" },
        textColor: "#A1A1AA",
        fontFamily: "JetBrains Mono, monospace",
        fontSize: 10,
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: "rgba(39,39,42,0.45)" },
        horzLines: { color: "rgba(39,39,42,0.45)" },
      },
      timeScale: {
        borderColor: "#27272A",
        timeVisible: true,
        secondsVisible: false,
        fixLeftEdge: true,
        fixRightEdge: true,
      },
      rightPriceScale: {
        borderColor: "#27272A",
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: "#52525B", width: 1, style: 2 },
        horzLine: { color: "#52525B", width: 1, style: 2 },
      },
      handleScale: {
        axisPressedMouseMove: { time: true, price: false },
        mouseWheel: true,
        pinch: true,
      },
    });
    chartRef.current = chart;

    // --- Candlestick series ---
    const candle = chart.addSeries(CandlestickSeries, {
      upColor: "#10B981",
      downColor: "#EF4444",
      borderUpColor: "#10B981",
      borderDownColor: "#EF4444",
      wickUpColor: "#10B981",
      wickDownColor: "#EF4444",
      priceFormat: { type: "price", precision: 2, minMove: 0.05 },
    });
    candle.setData(
      bars.map((b) => ({
        time: b.date,
        open: b.open,
        high: b.high,
        low: b.low,
        close: b.close,
      }))
    );

    // --- SMA lines ---
    const addSma = (key, color, label) => {
      const data = bars
        .filter((b) => b[key] != null && !isNaN(b[key]))
        .map((b) => ({ time: b.date, value: b[key] }));
      if (!data.length) return;
      const s = chart.addSeries(LineSeries, {
        color,
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
        title: label,
      });
      s.setData(data);
    };
    addSma("sma20", "#F59E0B", "SMA20");
    addSma("sma50", "#10B981", "SMA50");
    addSma("sma200", "#A1A1AA", "SMA200");

    // --- Purple dot markers (Manas Arora / Korean builder explosive buying) ---
    // Mark days where features.purple_dot === 1 with a purple circle below
    // bar — same visual semantics as the Pine `plotshape(... color=purple,
    // location=belowbar)`.
    const markers = bars
      .filter((b) => b.purple_dot === 1)
      .map((b) => ({
        time: b.date,
        position: "belowBar",
        color: "#A855F7",
        shape: "circle",
        size: 1,
      }));
    if (markers.length) {
      try {
        createSeriesMarkers(candle, markers);
      } catch (_e) {
        // marker primitive may differ across minor versions; non-fatal
      }
    }

    chart.timeScale().fitContent();

    const onResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", onResize);

    return () => {
      window.removeEventListener("resize", onResize);
      chart.remove();
      chartRef.current = null;
    };
  }, [bars, height]);

  if (!bars?.length) {
    return (
      <div
        className="flex items-center justify-center border border-dashed border-borderDefault text-[11px] text-textMuted"
        style={{ height }}
      >
        No bars to plot
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      data-testid="lightweight-chart"
      className="w-full border border-borderDefault"
      style={{ height }}
    />
  );
}
