import { useEffect, useMemo, useRef, useState } from "react";
import { createChart } from "lightweight-charts";
import { getJournal, getSymbolOhlc } from "../api.js";
import Read from "./Read.jsx";
import SymbolCard from "./SymbolCard.jsx";
import { Callout, PosterBand, Verdict } from "./poster/Primitives.jsx";

const PRESETS = [
  { key: "setup", label: "Setup", read: "10/21/50 EMA plus volume markers for setup validation." },
  { key: "trend", label: "Trend", read: "50EMA and stage context only, for trend structure." },
  { key: "exit", label: "Exit", read: "15/21 EMA trailing overlay for trade management." },
];

const TOKEN = {
  bull: "#0f7a3d",
  bullBg: "#e6f6ec",
  bullBorder: "#c2e6cf",
  warn: "#9a5b00",
  warnBg: "#fdf0dd",
  bear: "#b42318",
  bearBg: "#fdecea",
  bearBorder: "#f4c9c4",
  muted: "#5b6472",
  mutedBg: "#f0f1f4",
  mutedBorder: "#e2e5ea",
  ink: "#14161a",
  ink2: "#5b6472",
  ink3: "#8a93a0",
  hairline: "#e7e9ee",
  info: "#175cd3",
  infoBg: "#e9f1fd",
  infoBorder: "#c7dbf7",
  purpledot: "#7c3aed",
};

export default function ChartDrawer({ selection, onClose }) {
  const data = typeof selection === "string" ? { symbol: selection } : selection;
  const symbol = data?.symbol;
  const [state, setState] = useState({ loading: true, error: null, data: null, journal: [] });
  const [preset, setPreset] = useState("setup");

  useEffect(() => {
    const onKey = (event) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  useEffect(() => {
    if (!symbol) return;
    let cancelled = false;
    setState({ loading: true, error: null, data: null, journal: [] });
    Promise.all([
      getSymbolOhlc(symbol, { n: 300 }),
      getJournal().catch(() => ({ trades: [] })),
    ])
      .then(([ohlc, journal]) => {
        if (cancelled) return;
        const trades = (journal?.trades || []).filter((trade) => trade.symbol === symbol);
        setState({ loading: false, error: null, data: ohlc, journal: trades });
      })
      .catch((e) => !cancelled && setState({ loading: false, error: e.message, data: null, journal: [] }));
    return () => {
      cancelled = true;
    };
  }, [symbol]);

  const latest = state.data?.candles?.[state.data.candles.length - 1];
  const presetRead = PRESETS.find((p) => p.key === preset)?.read;

  return (
    <div data-testid="chart-drawer" className="fixed inset-0 z-40">
      <button
        type="button"
        aria-label="Close chart drawer"
        className="absolute inset-0 bg-ink/20"
        onClick={onClose}
      />
      <aside className="absolute right-0 top-0 h-full w-full max-w-[1200px] w-[90vw] overflow-y-auto border-l border-hairline bg-card p-6 shadow-2xl">
        <div className="mb-3 flex items-center justify-between">
          <div className="font-mono text-[12px] font-bold uppercase tracking-overline text-ink">
            Chart drawer
          </div>
          <button
            type="button"
            onClick={onClose}
            className="border border-hairline px-2 py-0.5 font-mono text-[10px] uppercase tracking-overline text-ink3 hover:border-ink hover:text-ink"
          >
            close
          </button>
        </div>

        <SymbolCard
          symbol={symbol}
          rs={data?.rs}
          rsAsOf={data?.rsAsOf}
          deliveryPct={data?.deliveryPct}
          deliveryAsOf={data?.deliveryAsOf}
          changePct={data?.changePct}
          fyersConnected={data?.fyersConnected}
          verdictBand="muted"
        />

        <PosterBand state="muted" kicker="INSPECTION" title="Chart" className="mt-3">
          <div className="flex gap-1">
            {PRESETS.map((p) => (
              <button
                key={p.key}
                type="button"
                onClick={() => setPreset(p.key)}
                className={
                  "flex-1 px-2 py-1 font-mono text-[10px] uppercase tracking-overline " +
                  (preset === p.key ? "bg-ink text-white" : "text-ink3 hover:text-ink")
                }
              >
                {p.label}
              </button>
            ))}
          </div>
          <Callout className="mt-2">{presetRead}</Callout>
        </PosterBand>

        {state.loading ? (
          <div className="mt-3 h-48 animate-pulse border border-hairline bg-raised" />
        ) : state.error ? (
          <div className="mt-3 border border-bear-border bg-bear-bg px-4 py-6 font-mono text-[11px] text-bear">
            {state.error}
          </div>
        ) : !state.data?.available ? (
          <div className="mt-3 border border-dashed border-hairline bg-raised px-4 py-10 text-center">
            <div className="font-mono text-[12px] font-bold uppercase tracking-overline text-ink">
              No candles found
            </div>
            <p className="mt-1 font-sans text-[12px] text-ink3">No EQ daily_prices rows exist for {symbol}.</p>
          </div>
        ) : (
          <>
            <PriceChart
              candles={state.data.candles}
              signals={state.data.signals || []}
              preset={preset}
              selection={data}
              marsSeries={state.data.pine_ports?.moving_average_rs?.series || []}
              rsPhase={state.data.rs_phase}
              avwap={state.data.avwap}
              ttmSqueeze={state.data.ttm_squeeze || []}
              journalTrades={state.journal}
            />
            {state.data.candles.length < 150 && (
              <Read band="warn" verdict="INSUFFICIENT HISTORY">
                Weinstein stage needs about 150 daily candles. This symbol only has {state.data.candles.length}.
              </Read>
            )}
            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              <StateBox label="Stage" value={state.data.stage?.stage || "-"} detail={state.data.stage?.detail} />
              <StateBox label="Trail" value={state.data.trail?.status || "-"} detail={state.data.trail?.detail} />
              <StateBox
                label="RS Phase"
                value={state.data.rs_phase || state.data.pine_ports?.moving_average_rs?.state || "-"}
                detail={state.data.pine_ports?.moving_average_rs?.detail}
              />
              <StateBox
                label="AVWAP anchor"
                value={state.data.avwap?.anchor_date || "-"}
                detail={state.data.avwap?.reason || "Default is to keep the existing anchor."}
              />
            </div>
            <Signals signals={state.data.signals || []} />
            <Read band="muted" verdict="PRICE ACTION">
              {latest ? `${symbol} closed at ${latest.close}; ${presetRead}` : "No latest candle available."}
            </Read>
          </>
        )}
      </aside>
    </div>
  );
}

function PriceChart({ candles, signals, preset, selection, marsSeries, rsPhase, avwap, ttmSqueeze, journalTrades }) {
  const chartRef = useRef(null);
  const shown = useMemo(() => candles.slice(-180), [candles]);
  const shownDates = useMemo(() => new Set(shown.map((c) => c.date)), [shown]);
  const overlayKeys =
    preset === "exit" ? ["ema15", "ema21"] : preset === "trend" ? ["ema50"] : ["ema10", "ema21", "ema50"];
  const setupLevels = useMemo(() => setupChartLevels(selection), [selection]);
  const chartSignals = useMemo(() => (signals || []).filter((signal) => shownDates.has(signal.date)), [signals, shownDates]);
  const lowerPaneData = useMemo(
    () => ({
      ttm: (ttmSqueeze || []).filter((point) => shownDates.has(point.date) && point.value != null),
      rs: (marsSeries || []).filter((point) => shownDates.has(point.date) && point.value != null),
    }),
    [marsSeries, shownDates, ttmSqueeze],
  );
  const journalMarkers = useMemo(() => tradeMarkers(journalTrades, shown), [journalTrades, shown]);

  useEffect(() => {
    if (!chartRef.current || !shown.length) return undefined;
    chartRef.current.replaceChildren();
    const chart = createChart(chartRef.current, {
      height: 520,
      layout: { background: { color: TOKEN.mutedBg }, textColor: TOKEN.ink2 },
      grid: { vertLines: { color: TOKEN.hairline }, horzLines: { color: TOKEN.hairline } },
      rightPriceScale: { borderColor: TOKEN.hairline, scaleMargins: { top: 0.08, bottom: 0.28 } },
      timeScale: { borderColor: TOKEN.hairline, timeVisible: false },
      crosshair: { mode: 1 },
    });
    const candleSeries = chart.addCandlestickSeries({
      upColor: TOKEN.bull,
      downColor: TOKEN.bear,
      borderUpColor: TOKEN.bull,
      borderDownColor: TOKEN.bear,
      wickUpColor: TOKEN.bull,
      wickDownColor: TOKEN.bear,
    });
    candleSeries.setData(
      shown.map((c) => ({
        time: c.date,
        open: Number(c.open),
        high: Number(c.high),
        low: Number(c.low),
        close: Number(c.close),
      })),
    );

    const volumeSeries = chart.addHistogramSeries({
      priceFormat: { type: "volume" },
      priceScaleId: "volume",
      color: TOKEN.mutedBorder,
    });
    volumeSeries.priceScale().applyOptions({ scaleMargins: { top: 0.78, bottom: 0 } });
    volumeSeries.setData(
      shown.map((c) => ({
        time: c.date,
        value: Number(c.volume) || 0,
        color: c.close >= c.open ? TOKEN.bullBorder : TOKEN.bearBorder,
      })),
    );

    const emaColors = { ema10: TOKEN.info, ema15: TOKEN.purpledot, ema21: TOKEN.warn, ema50: TOKEN.muted };
    overlayKeys.forEach((key) => {
      const line = chart.addLineSeries({ color: emaColors[key], lineWidth: 1, priceLineVisible: false });
      line.setData(shown.filter((c) => c[key] != null).map((c) => ({ time: c.date, value: Number(c[key]) })));
    });
    const avwapSeries = (avwap?.series || []).filter((point) => shownDates.has(point.date) && point.value != null);
    if (avwapSeries.length) {
      const line = chart.addLineSeries({ color: TOKEN.purpledot, lineWidth: 2, lineStyle: 2, priceLineVisible: false });
      line.setData(avwapSeries.map((point) => ({ time: point.date, value: Number(point.value) })));
    }
    setupLevels.forEach((level) => {
      if (level.type === "buy-zone") {
        candleSeries.createPriceLine({ price: level.low, color: TOKEN.bull, lineWidth: 1, lineStyle: 2, axisLabelVisible: false, title: "buy zone -1%" });
        candleSeries.createPriceLine({ price: level.high, color: TOKEN.bull, lineWidth: 1, lineStyle: 2, axisLabelVisible: false, title: "buy zone +1%" });
      } else {
        candleSeries.createPriceLine({
          price: level.value,
          color: level.stroke,
          lineWidth: level.type === "stop" ? 2 : 1,
          lineStyle: level.type === "measured-move" ? 2 : 0,
          title: level.label,
        });
      }
    });
    candleSeries.setMarkers(chartMarkers(chartSignals, journalMarkers));
    chart.timeScale().fitContent();
    const resize = () => chart.applyOptions({ width: chartRef.current?.clientWidth || 500 });
    resize();
    window.addEventListener("resize", resize);
    return () => {
      window.removeEventListener("resize", resize);
      chart.remove();
    };
  }, [avwap, chartSignals, journalMarkers, overlayKeys, setupLevels, shown, shownDates]);

  return (
    <div className="mt-3 border border-hairline bg-card p-2">
      <div className="mb-1 flex items-center justify-between font-mono text-[9px] uppercase tracking-overline text-ink3">
        <span>Daily price - last {shown.length} bars</span>
        <span>{overlayKeys.map((k) => k.replace("ema", "")).join(" / ")} EMA preset</span>
      </div>
      <div ref={chartRef} className="h-80 w-full" />
      <ChartLegend overlayKeys={overlayKeys} hasAvwap={Boolean(avwap?.series?.length)} hasSetupLevels={setupLevels.length > 0} hasJournal={journalMarkers.length > 0} />
      <LowerPane data={lowerPaneData} rsPhase={rsPhase} />
    </div>
  );
}

function ChartLegend({ overlayKeys, hasAvwap, hasSetupLevels, hasJournal }) {
  const labels = overlayKeys.map((key) => key.replace("ema", "EMA")).join(" ");
  return (
    <div className="mt-2 font-mono text-[9px] uppercase tracking-overline text-ink3">
      <span style={{ color: TOKEN.bull }}>green candles</span> / <span style={{ color: TOKEN.bear }}>red candles</span> · volume ·{" "}
      <span style={{ color: TOKEN.info }}>{labels}</span>
      {hasAvwap && <> · <span style={{ color: TOKEN.purpledot }}>AVWAP</span></>}
      {hasSetupLevels && <> · <span style={{ color: TOKEN.warn }}>stop / buy-zone / measured move</span></>}
      {hasJournal && <> · <span style={{ color: TOKEN.ink }}>entry/exit arrows</span></>}
      {" · "}
      <span style={{ color: TOKEN.info }}>PP dots</span>
    </div>
  );
}

function LowerPane({ data, rsPhase }) {
  const ttm = data.ttm.slice(-40);
  const rs = data.rs.slice(-40);
  const maxAbs = Math.max(...ttm.map((point) => Math.abs(Number(point.value))), 1);
  const latestRs = rs[rs.length - 1]?.value;
  return (
    <div className="mt-2 border border-hairline bg-raised p-2">
      <div className="mb-1 flex items-center justify-between font-mono text-[9px] uppercase tracking-overline text-ink3">
        <span>TTM momentum</span>
        <span>RS {latestRs == null ? "-" : Number(latestRs).toFixed(1)} {rsPhase ? `· ${rsPhase}` : ""}</span>
      </div>
      <div className="flex h-12 items-center gap-px">
        {ttm.map((point) => {
          const value = Number(point.value);
          const height = Math.max(2, Math.abs(value) / maxAbs * 42);
          return (
            <span
              key={point.date}
              title={`${point.date}: ${point.value}`}
              className={value >= 0 ? "self-end bg-bull-border" : "self-start bg-bear-border"}
              style={{ height, width: `${100 / Math.max(1, ttm.length)}%` }}
            />
          );
        })}
      </div>
    </div>
  );
}

function setupChartLevels(selection) {
  if (selection?.source !== "setups") return [];
  const entry = toNumber(selection.entry);
  const stop = toNumber(selection.stop);
  const measuredMove = toNumber(selection.measured_move);
  const levels = [];
  if (entry != null) levels.push({ type: "buy-zone", value: entry, low: entry * 0.99, high: entry * 1.01, label: "buy zone", stroke: TOKEN.bull });
  if (stop != null) levels.push({ type: "stop", value: stop, label: "stop", stroke: TOKEN.bear });
  if (measuredMove != null) levels.push({ type: "measured-move", value: measuredMove, label: "measured move (if it works)", stroke: TOKEN.warn });
  return levels;
}

function chartMarkers(signals, journalMarkers) {
  const signalMarkers = signals.flatMap((signal) => {
    if (signal.kind === "POCKET_PIVOT") {
      return [{ time: signal.date, position: "belowBar", color: TOKEN.info, shape: "circle", text: "PP" }];
    }
    if (signal.kind === "SHAKEOUT" || /^EMA\d+_RECLAIM$/.test(signal.kind || "")) {
      return [{ time: signal.date, position: "belowBar", color: TOKEN.bull, shape: "arrowUp", text: signalLabel(signal.kind) }];
    }
    if (/^EMA\d+_LOSS$/.test(signal.kind || "")) {
      return [{ time: signal.date, position: "aboveBar", color: TOKEN.bear, shape: "arrowDown", text: signalLabel(signal.kind) }];
    }
    return [];
  });
  const trade = journalMarkers.map((marker) => ({
    time: marker.date,
    position: marker.type === "entry" ? "belowBar" : "aboveBar",
    color: marker.type === "entry" ? TOKEN.bull : TOKEN.bear,
    shape: marker.type === "entry" ? "arrowUp" : "arrowDown",
    text: marker.type,
  }));
  return [...signalMarkers, ...trade].sort((a, b) => String(a.time).localeCompare(String(b.time)));
}

function signalLabel(kind) {
  if (kind === "SHAKEOUT") return "shakeout";
  const match = /^EMA(\d+)_(RECLAIM|LOSS)$/.exec(kind || "");
  if (!match) return kind || "signal";
  return `${match[1]} ${match[2].toLowerCase()}`;
}

function tradeMarkers(trades, shown) {
  if (!trades?.length || !shown.length) return [];
  return trades.flatMap((trade) => {
    const markers = [];
    const entryIndex = nearestIndex(shown, trade.trade_date);
    if (toNumber(trade.entry) != null && entryIndex != null) markers.push({ tradeId: trade.trade_id, type: "entry", date: shown[entryIndex].date });
    const exitDate = trade.exit_date || trade.closed_at || shown[shown.length - 1].date;
    const exitIndex = nearestIndex(shown, exitDate);
    if (toNumber(trade.exit) != null && exitIndex != null) markers.push({ tradeId: trade.trade_id, type: "exit", date: shown[exitIndex].date });
    return markers;
  });
}

function nearestIndex(candles, date) {
  if (!date) return null;
  const exact = candles.findIndex((c) => c.date === date);
  if (exact >= 0) return exact;
  const after = candles.findIndex((c) => c.date > date);
  if (after >= 0) return after;
  return candles.length - 1;
}

function toNumber(value) {
  if (value == null || value === "") return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function StateBox({ label, value, detail }) {
  return (
    <div className="border border-hairline bg-raised p-2">
      <div className="font-mono text-[9px] uppercase tracking-overline text-ink3">{label}</div>
      <div className="font-mono text-[13px] font-bold uppercase text-ink">{value}</div>
      <p className="mt-1 font-sans text-[11px] leading-snug text-ink3">{detail || "No detail yet."}</p>
    </div>
  );
}

function Signals({ signals }) {
  if (!signals.length) {
    return <div className="mt-3 font-mono text-[10px] text-ink3">No recent detector signals.</div>;
  }
  return (
    <ul className="mt-3 space-y-1">
      {signals.slice(0, 6).map((s) => (
        <li key={`${s.date}-${s.kind}`} className="border border-hairline2 bg-raised px-2 py-1">
          <div className="font-mono text-[10px] font-bold uppercase tracking-overline text-info">
            {s.date} - {s.kind}
          </div>
          <div className="font-sans text-[11px] text-ink2">{s.detail}</div>
        </li>
      ))}
    </ul>
  );
}
