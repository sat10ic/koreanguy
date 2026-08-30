import { CandlestickSeries, ColorType, createChart, LineSeries, type IChartApi } from "lightweight-charts";
import { useEffect, useRef } from "react";
import { anchoredVwap, ema, generateOhlc } from "../../lib/ohlc";

/*
  Main chart (manual §11.4). Must-include: candles, EMA21, EMA50, an AVWAP,
  trigger line, invalidation line. Kept deliberately uncluttered — one AVWAP,
  two EMAs, two horizontal levels. No volume pane yet (honest scope cut, not
  in this pass).
*/
interface StockChartProps {
  symbol: string;
  price: number;
  triggerPrice: number;
  invalidationPrice: number;
}

export function StockChart({ symbol, price, triggerPrice, invalidationPrice }: StockChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const chart = createChart(el, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#9aa2ad",
        fontSize: 11,
        fontFamily: "Inter, system-ui, sans-serif",
      },
      grid: {
        vertLines: { color: "rgba(255,255,255,0.04)" },
        horzLines: { color: "rgba(255,255,255,0.04)" },
      },
      rightPriceScale: { borderColor: "rgba(255,255,255,0.08)" },
      timeScale: { borderColor: "rgba(255,255,255,0.08)" },
      crosshair: {
        vertLine: { color: "rgba(216,155,74,0.4)", labelBackgroundColor: "#1c212a" },
        horzLine: { color: "rgba(216,155,74,0.4)", labelBackgroundColor: "#1c212a" },
      },
      autoSize: true,
    });
    chartRef.current = chart;

    const bars = generateOhlc(symbol, price);
    const candles = chart.addSeries(CandlestickSeries, {
      upColor: "#3ecf8e",
      downColor: "#ef5350",
      borderVisible: false,
      wickUpColor: "#3ecf8e",
      wickDownColor: "#ef5350",
    });
    candles.setData(bars as never);

    const ema21 = chart.addSeries(LineSeries, { color: "#7fb0e0", lineWidth: 1, title: "EMA21" });
    ema21.setData(ema(bars, 21) as never);

    const ema50 = chart.addSeries(LineSeries, { color: "#8f8fe0", lineWidth: 1, title: "EMA50" });
    ema50.setData(ema(bars, 50) as never);

    const anchorIdx = Math.max(0, bars.length - 25);
    const avwap = chart.addSeries(LineSeries, { color: "#d89b4a", lineWidth: 2, lineStyle: 2, title: "AVWAP" });
    avwap.setData(anchoredVwap(bars, anchorIdx) as never);

    candles.createPriceLine({
      price: triggerPrice,
      color: "#d89b4a",
      lineWidth: 1,
      lineStyle: 0,
      axisLabelVisible: true,
      title: "Trigger",
    });
    candles.createPriceLine({
      price: invalidationPrice,
      color: "#ef5350",
      lineWidth: 1,
      lineStyle: 2,
      axisLabelVisible: true,
      title: "Invalidation",
    });

    chart.timeScale().fitContent();

    return () => {
      chart.remove();
      chartRef.current = null;
    };
  }, [symbol, price, triggerPrice, invalidationPrice]);

  return <div ref={containerRef} className="h-full w-full" />;
}
