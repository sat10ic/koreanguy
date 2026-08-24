// SYMBOL landing page — HANDOFF_scouting_wire_2026-08-24 §"Symbol landing page".
// Consumes GET /api/symbol/{symbol} (design/CONTRACTS.md §8).
//
// The price pane is the ONE place lightweight-charts is allowed (VISUAL_LANGUAGE
// §2 "Price candles / OHLC" row). It may only render bars that exist in
// daily_prices for a symbol `validated` against the bhavcopy NSE EQ universe —
// a candle chart of the wrong instrument, or of invented bars, is worse than no
// chart. When not validated the labelled empty state says which part is missing
// and no candle is ever drawn.
//
// Colours resolve ONLY through CSS custom properties at runtime (the same token
// adapter pattern as components/charts.jsx). When a token has not been landed by
// the tokens.css rewrite, the library default is left in place rather than a
// literal colour being introduced here. No hex literal exists in this file.
import React from "react";
import { createChart, ColorType } from "lightweight-charts";
import "../styles/symbol.css";
import { fetchSymbol } from "../api.js";
import {
  Conf, ErrorBox, Loading, MockBanner, Panel, Pct, fmtDate, useApi,
} from "../components/ui.jsx";

// Adaptive precision is a correctness rule (VISUAL_LANGUAGE §1): below ₹100 two
// decimals, above none. Mirrors ui.jsx autoDp for text strings (aria-labels).
function fmtPrice(v) {
  if (v === null || v === undefined) return "—";
  const n = Math.abs(Number(v));
  const places = n === 0 ? 0 : n < 100 ? 2 : 0;
  return Number(v).toLocaleString("en-IN", {
    minimumFractionDigits: places,
    maximumFractionDigits: places,
  });
}

// Reads the design tokens once per mount and hands the resolved strings to
// lightweight-charts. `maybe()` drops an unresolved token (""), letting the
// library fall back to its own default — never a literal colour here.
function useChartTokens() {
  return React.useMemo(() => {
    const cs = getComputedStyle(document.documentElement);
    const get = (name) => cs.getPropertyValue(name).trim();
    const tk = {
      ground: get("--ground"), edge: get("--edge"), hair: get("--hair"),
      ink3: get("--ink-3"), ink4: get("--ink-4"), up: get("--up"),
      down: get("--down"),
    };
    const maybe = (v) => (v ? v : undefined);
    return Object.fromEntries(Object.entries(tk).map(([k, v]) => [k, maybe(v)]));
  }, []);
}

// The only chart on this screen, and the only lightweight-charts instance in
// the app. Renders bars strictly from the validated prices array.
function CandlePane({ symbol, prices }) {
  const elRef = React.useRef(null);
  const tk = useChartTokens();
  const last = [...prices].reverse().find((p) => p.close != null) || prices[prices.length - 1];
  const fromDate = prices[0]?.trade_date;
  const toDate = last?.trade_date;

  // No load animation (group rule) — lightweight-charts draws statically with
  // no easing by default; nothing here enables one.
  React.useEffect(() => {
    const el = elRef.current;
    if (!el) return undefined;
    const chart = createChart(el, {
      width: Math.max(el.clientWidth || 600, 320),
      height: Math.max(el.clientHeight || 360, 240),
      layout: {
        background: { type: ColorType.Solid, color: tk.ground || "transparent" },
        textColor: tk.ink3,
        fontSize: 11,
      },
      grid: {
        vertLines: tk.hair ? { color: tk.hair } : undefined,
        horzLines: tk.hair ? { color: tk.hair } : undefined,
      },
      rightPriceScale: tk.edge ? { borderColor: tk.edge } : undefined,
      timeScale: { borderColor: tk.edge, timeVisible: false },
      crosshair: {
        vertLine: tk.ink4 ? { color: tk.ink4 } : undefined,
        horzLine: tk.ink4 ? { color: tk.ink4 } : undefined,
      },
    });
    const series = chart.addCandlestickSeries({
      upColor: tk.up,
      downColor: tk.down,
      borderUpColor: tk.up,
      borderDownColor: tk.down,
      wickUpColor: tk.up,
      wickDownColor: tk.down,
    });
    series.setData(
      prices.map((p) => ({
        time: p.trade_date, // YYYY-MM-DD business day, as stored
        open: p.open, high: p.high, low: p.low, close: p.close,
      }))
    );
    const ro = new ResizeObserver(() => {
      chart.applyOptions({ width: el.clientWidth, height: el.clientHeight });
    });
    ro.observe(el);
    return () => {
      ro.disconnect();
      chart.remove();
    };
  }, [prices, tk]);

  const closeText = last?.close != null ? fmtPrice(last.close) : "—";
  const summary =
    `${symbol} daily candles — ${prices.length} sessions, ` +
    `${fromDate || "—"} → ${toDate || "—"}` +
    `${last?.close != null ? `, last close ₹${closeText}` : ""}.`;
  return (
    <div
      ref={elRef}
      role="img"
      aria-label={summary}
      className="symbol-chart"
      style={{ height: 360 }}
    />
  );
}

export default function Symbol({ symbol, onNavigate }) {
  const { data, error } = useApi(() => fetchSymbol(symbol), [symbol]);
  if (error) return <ErrorBox error={error} />;
  if (!data) return <Loading />;

  const prices = data.prices || [];
  const positions = data.positions || [];
  const mentions = data.mentions || [];
  const showCandles = data.validated === true && prices.length > 0;
  // "Corpus" = positions + watch-idea mentions. When the symbol has neither,
  // the page must say the symbol itself is not in the corpus.
  const hasCorpus = positions.length + mentions.length > 0;

  const last = [...prices].reverse().find((p) => p.close != null) || prices[prices.length - 1];
  let gloss;
  if (showCandles) {
    gloss = (
      <>
        Last close{" "}
        <strong>
          ₹{fmtPrice(last?.close)}
        </strong>{" "}
        — {prices.length} sessions of NSE history
        {last?.trade_date ? `, newest ${fmtDate(last.trade_date)}` : ""}.
      </>
    );
  } else if (hasCorpus) {
    gloss = "This symbol has no price history on the NSE.";
  } else {
    gloss = "Nothing in the corpus for this symbol.";
  }

  const emptyLine = hasCorpus
    ? "This symbol has no price history on the NSE"
    : "Nothing in the corpus for this symbol";

  return (
    <div className="symbol-page">
      <MockBanner show={!!data.is_mock} />

      <header className="symbol-head">
        <p className="symbol-kicker">
          {data.validated ? "price history" : "symbol lookup"}
        </p>
        <h1 className="symbol-title">{data.symbol}</h1>
        <p className="symbol-gloss">{gloss}</p>
      </header>

      <Panel
        title={`${data.symbol} · candles`}
        right={data.validated ? <span className="mono">bhavcopy · NSE EQ</span> : null}
      >
        {showCandles ? (
          <>
            <CandlePane
              symbol={data.symbol}
              prices={prices}
            />
            <p className="chart-caption">
              n={prices.length} sessions · bhavcopy NSE EQ · last close{" "}
              <span className="mono">₹{fmtPrice(last?.close)}</span>
              {last?.trade_date ? ` · ${fmtDate(last.trade_date)}` : ""}
            </p>
          </>
        ) : (
          // Labelled one-line empty state — never a candle for an invalid
          // instrument, never a null chart.
          <p className="chart-empty" role="img" aria-label={emptyLine}>
            {emptyLine}.
          </p>
        )}
      </Panel>

      <Panel
        title={`Positions on ${data.symbol}`}
        right={positions.length ? `${positions.length} in the ledger` : null}
      >
        <button
          type="button"
          className="symbol-link"
          onClick={() => onNavigate?.("LEDGER", { symbol: data.symbol })}
        >
          ↗ open in LEDGER, filtered to {data.symbol}
        </button>
        {positions.length === 0 ? (
          <p className="empty">
            No positions reconstructed for this symbol yet.
          </p>
        ) : (
          <table className="data">
            <thead>
              <tr>
                <th>trader</th>
                <th>status</th>
                <th>opened</th>
                <th>closed</th>
                <th className="num">net</th>
                <th className="num">cf</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((p) => (
                <tr key={p.position_id}>
                  <td>
                    <button
                      type="button"
                      className="xlink"
                      onClick={() => onNavigate?.("TRADERS", { handle: p.handle })}
                    >
                      @{p.handle}
                    </button>
                  </td>
                  <td className="mono">{p.status}</td>
                  <td className="mono">{fmtDate(p.opened_at)}</td>
                  <td className="mono">{p.closed_at ? fmtDate(p.closed_at) : "—"}</td>
                  <td className="num">
                    <Pct value={p.net_result_pct} />
                  </td>
                  <td className="num">
                    <Conf value={p.confidence} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>

      <Panel title="Mentions" right={mentions.length ? `${mentions.length} watch ideas` : null}>
        {mentions.length === 0 ? (
          <p className="empty">
            No watch-idea mentions for this symbol yet.
          </p>
        ) : (
          <ul className="symbol-mentions">
            {mentions.map((m) => (
              <li key={m.id} className="symbol-mention">
                <span className="symbol-quote">"{m.trigger_text || m.kind}"</span>
                <span className="symbol-meta">
                  <button
                    type="button"
                    className="xlink"
                    onClick={() => onNavigate?.("TRADERS", { handle: m.handle })}
                  >
                    @{m.handle}
                  </button>
                  <span className="mono">· {fmtDate(m.stated_at)}</span>
                  <span className="symbol-kind">{m.kind}</span>
                </span>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}