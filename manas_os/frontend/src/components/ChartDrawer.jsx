import { useEffect, useMemo, useState } from "react";
import { getJournal, getSymbolOhlc } from "../api.js";
import Read from "./Read.jsx";
import SymbolCard from "./SymbolCard.jsx";

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
      <aside className="absolute right-0 top-0 h-full w-full max-w-[560px] overflow-y-auto border-l border-hairline bg-card p-4 shadow-none">
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

        <div className="mt-3 flex gap-1 border border-hairline bg-raised p-1">
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
  const width = 500;
  const height = 360;
  const priceHeight = 210;
  const volumeTop = 238;
  const volumeHeight = 52;
  const histTop = 305;
  const histHeight = 40;
  const pad = 12;
  const shown = candles.slice(-180);
  const shownDates = new Set(shown.map((c) => c.date));
  const overlayKeys =
    preset === "exit" ? ["ema15", "ema21"] : preset === "trend" ? ["ema50"] : ["ema10", "ema21", "ema50"];
  const setupLevels = setupChartLevels(selection);
  const shownMars = (marsSeries || []).filter((point) => shownDates.has(point.date) && point.value != null);
  const shownAvwap = (avwap?.series || []).filter((point) => shownDates.has(point.date) && point.value != null);
  const shownTtm = (ttmSqueeze || []).filter((point) => shownDates.has(point.date) && point.value != null);
  const chartSignals = (signals || []).filter((signal) => shownDates.has(signal.date));
  const actionSignals = chartSignals.filter((signal) => isPriceActionMarker(signal.kind));
  const pocketPivots = chartSignals.filter((signal) => signal.kind === "POCKET_PIVOT");
  const journalMarkers = useMemo(() => tradeMarkers(journalTrades, shown), [journalTrades, shown]);
  const values = shown
    .flatMap((c) => [c.high, c.low, ...overlayKeys.map((key) => c[key])])
    .concat(setupLevels.flatMap((level) => [level.low, level.high, level.value]))
    .concat(journalMarkers.map((marker) => marker.price))
    .concat(shownAvwap.map((point) => point.value))
    .filter((v) => v != null && Number.isFinite(Number(v)))
    .map(Number);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const x = (i) => pad + (i / Math.max(1, shown.length - 1)) * (width - 2 * pad);
  const y = (v) => priceHeight - pad - ((Number(v) - min) / range) * (priceHeight - 2 * pad);
  const indexByDate = new Map(shown.map((c, i) => [c.date, i]));
  const line = (key) =>
    shown
      .map((c, i) => (c[key] == null ? null : `${x(i).toFixed(1)},${y(c[key]).toFixed(1)}`))
      .filter(Boolean)
      .join(" ");
  const maxVolume = Math.max(...shown.map((c) => Number(c.volume) || 0), 1);
  const marsValues = shownMars.map((point) => Number(point.value));
  const marsMin = Math.min(...marsValues, 0);
  const marsMax = Math.max(...marsValues, 0);
  const marsRange = marsMax - marsMin || 1;
  const marsY = (v) => priceHeight - pad - ((Number(v) - marsMin) / marsRange) * (priceHeight - 2 * pad);
  const marsLine = shownMars
    .map((point) => `${x(indexByDate.get(point.date)).toFixed(1)},${marsY(point.value).toFixed(1)}`)
    .join(" ");
  const avwapLine = shownAvwap
    .map((point) => `${x(indexByDate.get(point.date)).toFixed(1)},${y(point.value).toFixed(1)}`)
    .join(" ");
  const ttmMax = Math.max(...shownTtm.map((point) => Math.abs(Number(point.value))), 1);
  const ttmZero = histTop + histHeight / 2;
  const stroke = {
    ema10: TOKEN.info,
    ema15: TOKEN.purpledot,
    ema21: TOKEN.warn,
    ema50: TOKEN.muted,
  };

  return (
    <div className="mt-3 border border-hairline bg-card p-2">
      <div className="mb-1 flex items-center justify-between font-mono text-[9px] uppercase tracking-overline text-ink3">
        <span>Daily price - last {shown.length} bars</span>
        <span>{overlayKeys.map((k) => k.replace("ema", "")).join(" / ")} EMA preset</span>
      </div>
      <svg viewBox={`0 0 ${width} ${height}`} className="h-72 w-full" preserveAspectRatio="none">
        {setupLevels.map((level) =>
          level.type === "buy-zone" ? (
            <g key={level.type}>
              <rect
                x={pad}
                y={y(level.high)}
                width={width - 2 * pad}
                height={Math.max(1, y(level.low) - y(level.high))}
                fill={TOKEN.bullBg}
                opacity="0.7"
              >
                <title>Buy-zone band: about 1% around setup entry {level.value}.</title>
              </rect>
              <text x={width - pad} y={y(level.value) - 3} textAnchor="end" fontSize="8" fill={TOKEN.bull}>
                buy zone
              </text>
            </g>
          ) : (
            <g key={level.type}>
              <line
                x1={pad}
                x2={width - pad}
                y1={y(level.value)}
                y2={y(level.value)}
                stroke={level.stroke}
                strokeWidth={level.type === "stop" ? "1.3" : "1"}
                strokeDasharray={level.type === "measured-move" ? "4 3" : undefined}
              >
                <title>{level.detail}</title>
              </line>
              <text x={width - pad} y={y(level.value) - 3} textAnchor="end" fontSize="8" fill={level.stroke}>
                {level.label}
              </text>
            </g>
          )
        )}
        {shown.map((c, i) => {
          const up = c.close >= c.open;
          const cx = x(i);
          const bodyTop = y(Math.max(c.open, c.close));
          const bodyBot = y(Math.min(c.open, c.close));
          return (
            <g key={c.date}>
              <line x1={cx} x2={cx} y1={y(c.high)} y2={y(c.low)} stroke={up ? TOKEN.bull : TOKEN.bear} strokeWidth="1" />
              <rect
                x={cx - 1.2}
                y={bodyTop}
                width="2.4"
                height={Math.max(1, bodyBot - bodyTop)}
                fill={up ? TOKEN.bull : TOKEN.bear}
              />
            </g>
          );
        })}
        {overlayKeys.map((key) => (
          <polyline key={key} points={line(key)} fill="none" stroke={stroke[key]} strokeWidth="1.2">
            <title>{key.replace("ema", "")} day exponential moving average.</title>
          </polyline>
        ))}
        {marsLine && (
          <polyline points={marsLine} fill="none" stroke={TOKEN.info} strokeWidth="1" strokeDasharray="2 3">
            <title>RS line: symbol strength versus benchmark, scaled to fit this chart. Phase: {rsPhase || "unknown"}.</title>
          </polyline>
        )}
        {avwapLine && (
          <polyline points={avwapLine} fill="none" stroke={TOKEN.purpledot} strokeWidth="1.2" strokeDasharray="4 2">
            <title>AVWAP from {avwap?.anchor_date}: {avwap?.reason}</title>
          </polyline>
        )}
        {actionSignals.map((signal) => {
          const i = indexByDate.get(signal.date);
          const candle = shown[i];
          const reclaim = signal.kind.includes("RECLAIM") || signal.kind === "SHAKEOUT";
          const cy = reclaim ? y(candle.low) + 12 : y(candle.high) - 12;
          return (
            <g key={`${signal.date}-${signal.kind}`}>
              <path
                d={reclaim ? `M ${x(i)} ${cy - 6} l -4 7 h 8 z` : `M ${x(i)} ${cy + 6} l -4 -7 h 8 z`}
                fill={reclaim ? TOKEN.bull : TOKEN.bear}
              >
                <title>{signal.detail || signal.kind}</title>
              </path>
              <text
                x={x(i)}
                y={reclaim ? cy + 15 : cy - 9}
                textAnchor="middle"
                fontSize="7"
                fill={reclaim ? TOKEN.bull : TOKEN.bear}
              >
                {signalLabel(signal.kind)}
              </text>
            </g>
          );
        })}
        {journalMarkers.map((marker) => (
          <g key={`${marker.tradeId}-${marker.type}`}>
            <path
              d={
                marker.type === "entry"
                  ? `M ${x(marker.index)} ${y(marker.price) - 10} l -5 8 h 3 v 8 h 4 v -8 h 3 z`
                  : `M ${x(marker.index)} ${y(marker.price) + 10} l -5 -8 h 3 v -8 h 4 v 8 h 3 z`
              }
              fill={marker.type === "entry" ? TOKEN.bull : TOKEN.bear}
            >
              <title>{marker.title}</title>
            </path>
            <text
              x={x(marker.index)}
              y={marker.type === "entry" ? y(marker.price) - 14 : y(marker.price) + 22}
              textAnchor="middle"
              fontSize="8"
              fill={marker.type === "entry" ? TOKEN.bull : TOKEN.bear}
            >
              {marker.type === "entry" ? "entry" : "exit"}
            </text>
          </g>
        ))}
        <line x1={pad} x2={width - pad} y1={volumeTop - 6} y2={volumeTop - 6} stroke={TOKEN.hairline} strokeWidth="1" />
        {shown.map((c, i) => {
          const up = c.close >= c.open;
          const cx = x(i);
          const barHeight = ((Number(c.volume) || 0) / maxVolume) * volumeHeight;
          const pivot = pocketPivots.find((signal) => signal.date === c.date);
          return (
            <g key={`${c.date}-volume`}>
              <rect
                x={cx - 1.4}
                y={volumeTop + volumeHeight - barHeight}
                width="2.8"
                height={Math.max(1, barHeight)}
                fill={up ? TOKEN.bullBorder : TOKEN.bearBorder}
              >
                <title>Volume bar for {c.date}.</title>
              </rect>
              {pivot && (
                <circle cx={cx} cy={volumeTop - 10} r="2.7" fill={TOKEN.info}>
                  <title>{pivot.detail || "Pocket pivot: volume accumulation signal."}</title>
                </circle>
              )}
            </g>
          );
        })}
        <line x1={pad} x2={width - pad} y1={ttmZero} y2={ttmZero} stroke={TOKEN.hairline} strokeWidth="1" />
        {shownTtm.map((point) => {
          const i = indexByDate.get(point.date);
          const v = Number(point.value);
          const barHeight = Math.min(histHeight / 2, Math.abs(v) / ttmMax * (histHeight / 2));
          return (
            <rect
              key={`${point.date}-ttm`}
              x={x(i) - 1.4}
              y={v >= 0 ? ttmZero - barHeight : ttmZero}
              width="2.8"
              height={Math.max(1, barHeight)}
              fill={v >= 0 ? TOKEN.bullBorder : TOKEN.bearBorder}
            >
              <title>TTM momentum histogram {point.value} on {point.date}.</title>
            </rect>
          );
        })}
      </svg>
      <ChartLegend
        overlayKeys={overlayKeys}
        hasPocketPivot={pocketPivots.length > 0}
        markerKinds={[...new Set(actionSignals.map((signal) => signal.kind))]}
        hasMars={Boolean(marsLine)}
        hasAvwap={Boolean(avwapLine)}
        hasTtm={shownTtm.length > 0}
        hasSetupLevels={setupLevels.length > 0}
        hasJournal={journalMarkers.length > 0}
      />
    </div>
  );
}

function ChartLegend({ overlayKeys, hasPocketPivot, markerKinds, hasMars, hasAvwap, hasTtm, hasSetupLevels, hasJournal }) {
  const emaLabels = {
    ema10: "10 EMA: short-term support/resistance",
    ema15: "15 EMA: faster trailing line",
    ema21: "21 EMA: pullback/trend line",
    ema50: "50 EMA: intermediate trend line",
  };
  const stroke = {
    ema10: TOKEN.info,
    ema15: TOKEN.purpledot,
    ema21: TOKEN.warn,
    ema50: TOKEN.muted,
  };
  return (
    <div className="mt-2 flex flex-wrap gap-1.5 font-mono text-[9px] uppercase tracking-overline text-ink3">
      <LegendItem color={TOKEN.ink} label="Candles: each bar shows the daily open, high, low, and close" />
      {overlayKeys.map((key) => (
        <LegendItem key={key} color={stroke[key]} label={emaLabels[key]} />
      ))}
      <LegendItem color={TOKEN.mutedBorder} label="Volume row: daily shares traded" />
      {hasPocketPivot && <LegendItem color={TOKEN.info} label="Pocket pivot (volume accumulation signal)" dot />}
      {markerKinds.map((kind) => (
        <LegendItem key={kind} color={kind?.includes("LOSS") ? TOKEN.bear : TOKEN.bull} label={markerLegendLabel(kind)} />
      ))}
      {hasSetupLevels && <LegendItem color={TOKEN.bull} label="Setup levels" />}
      {hasMars && <LegendItem color={TOKEN.info} label="RS line" dashed />}
      {hasAvwap && <LegendItem color={TOKEN.purpledot} label="AVWAP" dashed />}
      {hasTtm && <LegendItem color={TOKEN.mutedBorder} label="TTM histogram" />}
      {hasJournal && <LegendItem color={TOKEN.ink} label="Journal arrows: recorded entry and exit prices" />}
    </div>
  );
}

function LegendItem({ color, label, dot = false, dashed = false }) {
  return (
    <span title={label} className="inline-flex items-center gap-1 border border-hairline bg-raised px-1.5 py-0.5">
      <span
        className={dot ? "inline-block h-1.5 w-1.5 rounded-full" : "inline-block h-px w-4"}
        style={{ backgroundColor: dot || !dashed ? color : undefined, borderTop: dashed ? `1px dashed ${color}` : undefined }}
      />
      {label}
    </span>
  );
}

function setupChartLevels(selection) {
  if (selection?.source !== "setups") return [];
  const entry = toNumber(selection.entry);
  const stop = toNumber(selection.stop);
  const measuredMove = toNumber(selection.measured_move);
  const levels = [];
  if (entry != null) {
    levels.push({
      type: "buy-zone",
      value: entry,
      low: entry * 0.99,
      high: entry * 1.01,
      label: "buy zone",
      stroke: TOKEN.bull,
    });
  }
  if (stop != null) {
    levels.push({
      type: "stop",
      value: stop,
      label: "stop",
      stroke: TOKEN.bear,
      detail: `Setup stop level ${stop}.`,
    });
  }
  if (measuredMove != null) {
    levels.push({
      type: "measured-move",
      value: measuredMove,
      label: "measured move (if it works)",
      stroke: TOKEN.warn,
      detail: `Measured move level ${measuredMove}; conditional target, not a promise.`,
    });
  }
  return levels;
}

function isPriceActionMarker(kind) {
  return kind === "SHAKEOUT" || /^EMA\d+_(RECLAIM|LOSS)$/.test(kind || "");
}

function signalLabel(kind) {
  if (kind === "SHAKEOUT") return "shakeout";
  const match = /^EMA(\d+)_(RECLAIM|LOSS)$/.exec(kind || "");
  if (!match) return kind || "signal";
  return `${match[1]} ${match[2].toLowerCase()}`;
}

function markerLegendLabel(kind) {
  if (kind === "SHAKEOUT") return "Shakeout: price undercut and recovered";
  const match = /^EMA(\d+)_(RECLAIM|LOSS)$/.exec(kind || "");
  if (!match) return `${kind || "Signal"} marker`;
  return `${match[1]} EMA ${match[2].toLowerCase()}: ${
    match[2] === "LOSS" ? "price lost that moving average" : "price got back above that moving average"
  }`;
}

function tradeMarkers(trades, shown) {
  if (!trades?.length || !shown.length) return [];
  return trades.flatMap((trade) => {
    const markers = [];
    const entry = toNumber(trade.entry);
    const exit = toNumber(trade.exit);
    const entryIndex = nearestIndex(shown, trade.trade_date);
    if (entry != null && entryIndex != null) {
      markers.push({
        tradeId: trade.trade_id,
        type: "entry",
        index: entryIndex,
        price: entry,
        title: `Journal entry: ${trade.symbol} at ${entry} on ${shown[entryIndex].date}.`,
      });
    }
    const exitDate = trade.exit_date || trade.closed_at || shown[shown.length - 1].date;
    const exitIndex = nearestIndex(shown, exitDate);
    if (exit != null && exitIndex != null) {
      markers.push({
        tradeId: trade.trade_id,
        type: "exit",
        index: exitIndex,
        price: exit,
        title: `Journal exit: ${trade.symbol} at ${exit} on ${shown[exitIndex].date}.`,
      });
    }
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
