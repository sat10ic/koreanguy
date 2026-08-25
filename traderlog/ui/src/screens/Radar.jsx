import React, { useEffect, useState } from "react";
import { fetchRadar, fetchStockCandles, fetchStockAnalytics } from "../api.js";
import { Chip, ErrorBox, Loading, Num, Panel, Segmented, fmtDate, useApi } from "../components/ui.jsx";
import TradingViewChart from "../components/TradingViewChart.jsx";
import "../styles/radar.css";

const DAY_OPTIONS = ["7 days", "30 days", "90 days", "180 days"];
const TRADER_OPTIONS = ["1 trader", "2 traders", "3 traders", "4 traders"];

function fmtReturn(value) {
  if (value === null || value === undefined) return "—";
  const pct = value * 100;
  return `${value > 0 ? "+" : ""}${pct.toFixed(1)}%`;
}

function fmtPrice(value) {
  if (value === null || value === undefined) return "—";
  const num = Number(value);
  if (num > 0 && num < 100) return num.toFixed(2);
  return num.toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

export default function Radar({ onNavigate }) {
  const [dayLabel, setDayLabel] = useState("30 days");
  const [traderLabel, setTraderLabel] = useState("2 traders");
  const [selectedSymbol, setSelectedSymbol] = useState(null);
  const [candles, setCandles] = useState([]);
  const [analytics, setAnalytics] = useState(null);

  const days = parseInt(dayLabel.split(" ")[0], 10) || 30;
  const minTraders = parseInt(traderLabel.split(" ")[0], 10) || 2;

  const { data, error } = useApi(
    () => fetchRadar({ days, min_traders: minTraders }),
    [days, minTraders]
  );

  const coAttention = data?.co_attention || [];
  const activeCluster = coAttention.find((c) => c.symbol === selectedSymbol) || coAttention[0] || null;

  // Auto-select first cluster if none selected
  useEffect(() => {
    if (coAttention.length > 0 && (!selectedSymbol || !coAttention.some((c) => c.symbol === selectedSymbol))) {
      setSelectedSymbol(coAttention[0].symbol);
    } else if (coAttention.length === 0) {
      setSelectedSymbol(null);
    }
  }, [coAttention, selectedSymbol]);

  // Fetch candles & analytics for active selected symbol
  useEffect(() => {
    const sym = activeCluster?.symbol;
    if (!sym) {
      setCandles([]);
      setAnalytics(null);
      return;
    }
    Promise.all([
      fetchStockCandles(sym, 365),
      fetchStockAnalytics(sym),
    ])
      .then(([candleRes, analyticsRes]) => {
        setCandles(candleRes.candles || []);
        setAnalytics(analyticsRes || null);
      })
      .catch((e) => console.error("Error loading stock data:", e));
  }, [activeCluster?.symbol]);

  // Keyboard navigation for radar-row
  const handleKeyDown = (e, index) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      const next = coAttention[index + 1];
      if (next) {
        setSelectedSymbol(next.symbol);
        const nextEl = document.querySelectorAll("button.radar-row")[index + 1];
        if (nextEl) nextEl.focus();
      }
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      const prev = coAttention[index - 1];
      if (prev) {
        setSelectedSymbol(prev.symbol);
        const prevEl = document.querySelectorAll("button.radar-row")[index - 1];
        if (prevEl) prevEl.focus();
      }
    }
  };

  const chartMarkers = [];
  analytics?.mentions?.forEach((m) => {
    chartMarkers.push({
      time: m.ts_ist.slice(0, 10),
      handle: m.handle,
      kind: m.play_type || (m.kind === "trade_event" ? "Trade" : "Mention"),
    });
  });

  return (
    <div className="radar-workspace">
      <p className="page-lede">
        Multi-trader symbol co-attention, forward tape alpha, and technical verification.
      </p>
      <ErrorBox error={error} />

      {/* Top Filter Bar */}
      <Panel
        title="Co-Attention Radar"
        cite="Convergent symbols across independent traders"
        right={
          <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
            <Segmented options={DAY_OPTIONS} value={dayLabel} onChange={setDayLabel} />
            <Segmented options={TRADER_OPTIONS} value={traderLabel} onChange={setTraderLabel} />
          </div>
        }
      >
        <div style={{ fontSize: "var(--fs-ui)", color: "var(--ink-2)" }}>
          Co-attention clusters formed by {minTraders}+ distinct traders mentioning a symbol within {days} days.
        </div>
      </Panel>

      {!data && !error && <Loading />}

      {/* Zero cluster state */}
      {data && coAttention.length === 0 && (
        <div className="radar-zero radar-region" style={{ padding: "24px 0", textAlign: "center", color: "var(--ink-3)", fontStyle: "italic" }}>
          No co-attention clusters meet the {minTraders}+ trader threshold within {days} days.
        </div>
      )}

      {/* Main Grid: Left Table + Right Technical Detail */}
      {data && coAttention.length > 0 && (
        <div className="radar-grid" style={{ display: "grid", gridTemplateColumns: "420px 1fr", gap: "16px" }}>
          
          {/* Left: Clusters Table */}
          <Panel title={`Ranked Clusters (${coAttention.length})`} cite="Ordered by trader count">
            <div className="radar-region" style={{ display: "flex", flexDirection: "column", gap: "4px", maxHeight: "780px", overflowY: "auto" }}>
              {coAttention.map((cluster, index) => {
                const isSelected = cluster.symbol === activeCluster?.symbol;
                return (
                  <button
                    key={cluster.symbol}
                    type="button"
                    className={`radar-row${isSelected ? " active" : ""}`}
                    aria-pressed={isSelected ? "true" : "false"}
                    onClick={() => setSelectedSymbol(cluster.symbol)}
                    onKeyDown={(e) => handleKeyDown(e, index)}
                    style={{
                      width: "100%",
                      textAlign: "left",
                      padding: "10px 12px",
                      background: isSelected ? "var(--info-fill)" : "var(--surface)",
                      border: isSelected ? "1px solid var(--info)" : "1px solid var(--rule)",
                      borderLeft: isSelected ? "3px solid var(--info)" : "1px solid var(--rule)",
                      cursor: "pointer",
                      display: "flex",
                      flexDirection: "column",
                      gap: "4px",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                      <span style={{ fontSize: "var(--fs-val)", fontWeight: 800, fontFamily: "var(--mono)", color: "var(--ink)" }}>
                        {cluster.symbol}
                      </span>
                      <Chip kind="info">{cluster.distinct_trader_count} traders ({cluster.mention_count} posts)</Chip>
                    </div>

                    <div style={{ display: "flex", flexWrap: "wrap", gap: "4px", fontSize: "var(--fs-micro)" }}>
                      {cluster.traders?.map((h) => (
                        <span key={h} style={{ background: "var(--surface-2)", border: "1px solid var(--rule)", padding: "1px 5px", color: "var(--ink-2)" }}>
                          @{h}
                        </span>
                      ))}
                    </div>

                    {cluster.tape_state === "computed" && (
                      <div
                        className="radar-tape"
                        style={{
                          display: "grid",
                          gridTemplateColumns: "repeat(4, 1fr)",
                          gap: "4px",
                          fontSize: "var(--fs-micro)",
                          fontFamily: "var(--mono)",
                          marginTop: "4px",
                          paddingTop: "4px",
                          borderTop: "1px solid var(--rule)",
                        }}
                      >
                        <div>1d: <strong className={cluster.ret_1d >= 0 ? "pos" : "neg"}>{fmtReturn(cluster.ret_1d)}</strong></div>
                        <div>5d: <strong className={cluster.ret_5d >= 0 ? "pos" : "neg"}>{fmtReturn(cluster.ret_5d)}</strong></div>
                        <div>10d: <strong className={cluster.ret_10d >= 0 ? "pos" : "neg"}>{fmtReturn(cluster.ret_10d)}</strong></div>
                        <div>20d: <strong className={cluster.ret_20d >= 0 ? "pos" : "neg"}>{fmtReturn(cluster.ret_20d)}</strong></div>
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          </Panel>

          {/* Right: Technical Dossier & TV Chart */}
          {activeCluster && (
            <div className="radar-rail radar-region" style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              
              {/* Selected Cluster Header */}
              <Panel
                title={`${activeCluster.symbol} Intelligence Dossier`}
                cite={`First seen ${fmtDate(activeCluster.first_seen)} · Last seen ${fmtDate(activeCluster.last_seen)}`}
                right={
                  <button
                    type="button"
                    className="btn"
                    onClick={() => onNavigate?.("LEDGER", { symbol: activeCluster.symbol })}
                  >
                    Open in Ledger ↗
                  </button>
                }
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", flexWrap: "wrap", gap: "12px" }}>
                  <div style={{ display: "flex", alignItems: "baseline", gap: "10px" }}>
                    {analytics?.stats?.last_price && (
                      <span style={{ fontSize: "var(--fs-big)", fontWeight: 800, fontFamily: "var(--mono)", color: "var(--ink)" }}>
                        ₹{fmtPrice(analytics.stats.last_price)}
                      </span>
                    )}
                    {analytics?.stats?.chg_pct !== undefined && (
                      <Chip kind={analytics.stats.chg_pct >= 0 ? "green" : "bad"}>
                        {analytics.stats.chg_pct >= 0 ? "+" : ""}{analytics.stats.chg_pct}%
                      </Chip>
                    )}
                  </div>

                  {analytics?.stats && (
                    <div style={{ display: "flex", gap: "16px", fontSize: "var(--fs-ui)" }}>
                      <div>
                        <span style={{ color: "var(--ink-3)" }}>52W Range: </span>
                        <strong className="mono">₹{fmtPrice(analytics.stats.low_52w)} – ₹{fmtPrice(analytics.stats.high_52w)}</strong>
                      </div>
                      {analytics.stats.volume_ratio && (
                        <div>
                          <span style={{ color: "var(--ink-3)" }}>Vol vs 20d: </span>
                          <strong className="mono">{analytics.stats.volume_ratio}x</strong>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </Panel>

              {/* TradingView Chart */}
              {candles.length > 0 && (
                <Panel title="Daily Candlestick & Volume Chart" cite="With trader action markers & vision S/R levels">
                  <TradingViewChart
                    candles={candles}
                    markers={chartMarkers}
                    priceLines={analytics?.extracted_levels || []}
                    height={380}
                    symbol={activeCluster.symbol}
                  />
                </Panel>
              )}

              {/* Mentions & Evidence */}
              <Panel title={`Evidence Posts (${activeCluster.posts?.length || activeCluster.mentions?.length || 0})`} cite="Verbatim trader quotes">
                <div style={{ display: "flex", flexDirection: "column", gap: "8px", maxHeight: "320px", overflowY: "auto" }}>
                  {(activeCluster.posts || activeCluster.mentions || []).map((p, i) => (
                    <div
                      key={p.post_id || i}
                      className="radar-evidence"
                      style={{
                        padding: "10px 12px",
                        border: "1px solid var(--rule)",
                        background: "var(--surface)",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                        <div>
                          <strong style={{ color: "var(--info-ink)" }}>@{p.handle}</strong>
                          <span style={{ fontSize: "var(--fs-micro)", color: "var(--ink-3)", marginLeft: "8px" }}>
                            {p.ts_ist || fmtDate(p.stated_at)}
                          </span>
                        </div>
                        {p.url && (
                          <a href={p.url} target="_blank" rel="noreferrer" style={{ fontSize: "var(--fs-micro)", color: "var(--info-ink)", textDecoration: "underline" }}>
                            ↗ post
                          </a>
                        )}
                      </div>
                      <p style={{ margin: 0, fontSize: "var(--fs-body)", color: "var(--ink)", lineHeight: "1.5" }}>
                        {p.text || p.trigger_text || ""}
                      </p>
                    </div>
                  ))}
                </div>
              </Panel>
            </div>
          )}
        </div>
      )}

      {/* Coverage Diagnostics Panel */}
      {data?.coverage && (
        <Panel title="Radar Coverage Diagnostics" cite="Ingest health & parse validity">
          <div className="radar-coverage" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: "8px", fontSize: "var(--fs-ui)" }}>
            <div>Eligible classified posts: <strong className="mono">{data.coverage.eligible_classified_posts ?? "—"}</strong></div>
            <div>Included mentions: <strong className="mono">{data.coverage.included_mentions ?? "—"}</strong></div>
            <div>Invalid symbol JSON: <strong className="mono">{data.coverage.invalid_symbol_json ?? 0}</strong></div>
            <div>Invalid symbol values: <strong className="mono">{data.coverage.invalid_symbol_values ?? 0}</strong></div>
            <div>Invalid timestamps: <strong className="mono">{data.coverage.invalid_timestamps ?? 0}</strong></div>
            <div>Invalid handles: <strong className="mono">{data.coverage.invalid_handles ?? 0}</strong></div>
            <div>Unvalidated mentions: <strong className="mono">{data.coverage.unvalidated_mentions ?? 0}</strong></div>
            {data.coverage.missing_symbols && (
              <div>Missing NSE coverage: <strong className="mono">{data.coverage.missing_symbols.join(", ") || "None"}</strong></div>
            )}
          </div>
        </Panel>
      )}
    </div>
  );
}
