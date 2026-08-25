import React, { useEffect, useRef, useState } from "react";
import { createChart, ColorType } from "lightweight-charts";

/**
 * Institutional-grade TradingView Lightweight Chart
 * Refined for Quiet Editorial Light Terminal: Warm paper background, crisp candles,
 * trader action markers, and vision S/R price lines.
 */
export default function TradingViewChart({
  candles = [],
  markers = [],
  priceLines = [],
  height = 420,
  symbol = "",
}) {
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const candleSeriesRef = useRef(null);
  const volumeSeriesRef = useRef(null);
  const priceLineRefs = useRef([]);

  const [hoveredCandle, setHoveredCandle] = useState(null);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    // Create chart instance configured for Light Editorial Terminal
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: height,
      layout: {
        background: { type: ColorType.Solid, color: "#fdfdfc" }, // Warm white / paper
        textColor: "#4a4a46", // Soft dark ink
        fontSize: 11,
        fontFamily: "ui-monospace, 'SF Mono', Consolas, 'Roboto Mono', monospace",
      },
      grid: {
        vertLines: { color: "#efeee9" }, // Hairline light grid
        horzLines: { color: "#efeee9" },
      },
      crosshair: {
        mode: 1,
        vertLine: {
          color: "#1f4a8a", // Deep editorial blue
          width: 1,
          style: 3,
          labelBackgroundColor: "#1f4a8a",
        },
        horzLine: {
          color: "#1f4a8a",
          width: 1,
          style: 3,
          labelBackgroundColor: "#1f4a8a",
        },
      },
      rightPriceScale: {
        borderColor: "#cecbc0",
        scaleMargins: {
          top: 0.08,
          bottom: 0.22,
        },
      },
      timeScale: {
        borderColor: "#cecbc0",
        timeVisible: true,
        secondsVisible: false,
      },
    });

    // Candlestick Series using Quiet Editorial green/red tokens
    const candleSeries = chart.addCandlestickSeries({
      upColor: "#2f7d4f", // Editorial green
      downColor: "#b3402c", // Editorial red
      borderUpColor: "#20593a",
      borderDownColor: "#8a2f20",
      wickUpColor: "#20593a",
      wickDownColor: "#8a2f20",
    });

    // Volume Series
    const volumeSeries = chart.addHistogramSeries({
      color: "#1f4a8a",
      priceFormat: {
        type: "volume",
      },
      priceScaleId: "",
      scaleMargins: {
        top: 0.8,
        bottom: 0,
      },
    });

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
    volumeSeriesRef.current = volumeSeries;

    chart.subscribeCrosshairMove((param) => {
      if (!param || !param.time || !param.seriesData) {
        setHoveredCandle(null);
        return;
      }
      const data = param.seriesData.get(candleSeries);
      const vol = param.seriesData.get(volumeSeries);
      if (data) {
        setHoveredCandle({
          time: param.time,
          open: data.open,
          high: data.high,
          low: data.low,
          close: data.close,
          volume: vol ? vol.value : null,
        });
      }
    });

    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
      volumeSeriesRef.current = null;
    };
  }, [height]);

  useEffect(() => {
    if (!candleSeriesRef.current || !volumeSeriesRef.current || !candles.length) return;

    const sorted = [...candles].sort((a, b) => a.time.localeCompare(b.time));

    const candleData = sorted.map((c) => ({
      time: c.time,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
    }));

    const volumeData = sorted.map((c) => ({
      time: c.time,
      value: c.volume || 0,
      color: c.close >= c.open ? "rgba(47, 125, 79, 0.25)" : "rgba(179, 64, 44, 0.25)",
    }));

    candleSeriesRef.current.setData(candleData);
    volumeSeriesRef.current.setData(volumeData);

    // Apply Trader Markers
    if (markers && markers.length > 0) {
      const validMarkers = markers
        .filter((m) => m && m.time)
        .sort((a, b) => a.time.localeCompare(b.time))
        .map((m) => {
          let shape = "arrowUp";
          let color = "#20593a";
          let position = "belowBar";

          const k = (m.kind || "buy").toLowerCase();
          if (k.includes("exit") || k.includes("sold") || k.includes("sell")) {
            shape = "arrowDown";
            color = "#8a2f20";
            position = "aboveBar";
          } else if (k.includes("trim") || k.includes("partial")) {
            shape = "circle";
            color = "#8a6d00";
            position = "aboveBar";
          } else if (k.includes("add") || k.includes("pyramid")) {
            shape = "circle";
            color = "#1f4a8a";
            position = "belowBar";
          } else if (k.includes("stop") || k.includes("sl")) {
            shape = "square";
            color = "#b3402c";
            position = "belowBar";
          }

          return {
            time: m.time,
            position: position,
            color: color,
            shape: shape,
            text: `@${m.handle}: ${m.kind}${m.price ? ` @ ₹${m.price}` : ""}`,
          };
        });

      candleSeriesRef.current.setMarkers(validMarkers);
    } else {
      candleSeriesRef.current.setMarkers([]);
    }

    // Clear old price lines
    priceLineRefs.current.forEach((pl) => {
      try {
        candleSeriesRef.current.removePriceLine(pl);
      } catch (e) {}
    });
    priceLineRefs.current = [];

    // Add Vision Extracted Price Lines
    if (priceLines && priceLines.length > 0) {
      priceLines.forEach((lvl) => {
        if (!lvl || !lvl.price || isNaN(lvl.price)) return;
        const k = (lvl.kind || "other").toLowerCase();
        let color = "#6f6f68";
        let lineStyle = 2; // Dashed

        if (k === "support") {
          color = "#2f7d4f";
        } else if (k === "resistance") {
          color = "#b3402c";
        } else if (k === "entry") {
          color = "#1f4a8a";
          lineStyle = 0; // Solid
        } else if (k === "stop") {
          color = "#8a6d00";
        } else if (k === "target") {
          color = "#1f4a8a";
        }

        try {
          const pl = candleSeriesRef.current.createPriceLine({
            price: lvl.price,
            color: color,
            lineWidth: 1,
            lineStyle: lineStyle,
            axisLabelVisible: true,
            title: `${lvl.kind || "Level"}: ₹${lvl.price}${lvl.source ? ` (${lvl.source})` : ""}`,
          });
          priceLineRefs.current.push(pl);
        } catch (e) {}
      });
    }

    if (chartRef.current) {
      chartRef.current.timeScale().fitContent();
    }
  }, [candles, markers, priceLines]);

  const latest = candles.length ? candles[candles.length - 1] : null;
  const activeCandle = hoveredCandle || latest;

  return (
    <div className="tv-chart-wrapper" style={{ position: "relative", width: "100%", background: "#fdfdfc" }}>
      {activeCandle && (
        <div
          className="tv-chart-legend"
          style={{
            position: "absolute",
            top: "8px",
            left: "12px",
            zIndex: 10,
            display: "flex",
            flexWrap: "wrap",
            gap: "12px",
            fontSize: "12px",
            fontFamily: "var(--mono)",
            background: "var(--surface)",
            padding: "4px 8px",
            border: "1px solid var(--rule)",
            pointerEvents: "none",
          }}
        >
          <span style={{ fontWeight: 700, color: "var(--info-ink)" }}>
            {symbol}
          </span>
          <span>
            Date: <strong style={{ color: "var(--ink)" }}>{activeCandle.time}</strong>
          </span>
          <span>
            O: <strong style={{ color: "var(--ink-2)" }}>{activeCandle.open?.toFixed(2)}</strong>
          </span>
          <span>
            H: <strong style={{ color: "var(--ok-ink)" }}>{activeCandle.high?.toFixed(2)}</strong>
          </span>
          <span>
            L: <strong style={{ color: "var(--bad-ink)" }}>{activeCandle.low?.toFixed(2)}</strong>
          </span>
          <span>
            C:{" "}
            <strong
              style={{
                color: activeCandle.close >= activeCandle.open ? "var(--ok-ink)" : "var(--bad-ink)",
              }}
            >
              {activeCandle.close?.toFixed(2)}
            </strong>
          </span>
          {activeCandle.volume ? (
            <span>
              Vol:{" "}
              <strong style={{ color: "var(--info-ink)" }}>
                {(activeCandle.volume / 1000).toFixed(1)}k
              </strong>
            </span>
          ) : null}
        </div>
      )}

      <div
        ref={chartContainerRef}
        style={{ width: "100%", height: `${height}px`, background: "#fdfdfc" }}
      />
    </div>
  );
}
