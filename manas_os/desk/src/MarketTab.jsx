import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  fetchFocus,
  fetchIndustryStocks,
  fetchMarket,
  fetchMarketSectorStocks,
  fetchSectorStocks,
} from "./api.js";
import { colorScale, sparklinePoints, squarifyTreemap } from "./viz.js";
import { Term } from "./Glossary.jsx";
import ChartDrawer from "./ChartDrawer.jsx";
import "./MarketTab.v5.css";

function round(n, digits = 2) {
  if (n === null || n === undefined) return "—";
  const f = Math.pow(10, digits);
  return Math.round(n * f) / f;
}

function pct(n) {
  if (n === null || n === undefined) return "—";
  return `${n >= 0 ? "+" : ""}${round(n, 2)}%`;
}

function ReturnCell({ value }) {
  const style = colorScale(value);
  return (
    <td className="mkt-ret-cell mono" style={style}>
      {pct(value)}
    </td>
  );
}

function Sparkline({ values }) {
  const points = sparklinePoints(values, 100, 26);
  if (!points) return <span className="mkt-spark-empty mono">—</span>;
  return (
    <svg className="mkt-spark" viewBox="0 0 100 26" preserveAspectRatio="none">
      <polyline points={points} fill="none" stroke="var(--accent)" strokeWidth="1.5" />
    </svg>
  );
}

// ── G3: broad indices shrink to one compact strip — value + 1D% + sparkline,
// nothing more. The old full indices grid (which duplicated the sector
// treemap below it) is gone.
//
// Picked by name, not by the backend's BROAD/SECTORAL/THEMATIC_STRATEGY
// taxonomy class: that taxonomy files Nifty Bank under SECTORAL (it drives
// the treemap/movers), but the user's ask names it as one of the top-strip
// "indicator" indices regardless of that classification.
//
// F6 re-emphasis: this is a SWING tool — midcaps/smallcaps are the traded
// universe, not Nifty 50. NIFTY MIDSMALLCAP 400 leads (and renders larger),
// then the canonical Midcap 150 / Smallcap 250 ladder rungs if the backfill
// has them for this date, then Bank (pre-existing indicator), then Nifty 50
// + India VIX purely as broad-market context.
function normName(s) {
  return (s || "").toUpperCase().replace(/[^A-Z0-9]/g, "");
}
// Matched against each row's canonical `symbol` (e.g. "NIFTY BANK",
// "NIFTYMIDSML400") — NOT `name` (a display label like "Bank" / "Midcap
// 150" for SECTORAL/BROAD-ladder rows respectively) which normName() would
// reduce to something that never matches these keys, silently dropping the
// tile instead of rendering it.
const BROAD_STRIP_NAMES = [
  "NIFTYMIDSML400",
  "NIFTYMIDCAP150",
  "NIFTYSMALLCAP250",
  "NIFTYBANK",
  "NIFTY50",
];
const BROAD_STRIP_LEAD = "NIFTYMIDSML400";

function BroadIndicesStrip({ indices, vix }) {
  const byNorm = new Map((indices || []).map((r) => [normName(r.symbol), r]));
  const ordered = BROAD_STRIP_NAMES.map((n) => byNorm.get(n)).filter(Boolean);

  return (
    <div className="panel mkt-broad-strip">
      <p className="panel-title small-caps">Broad indices</p>
      <div className="mkt-broad-row">
        {ordered.map((row) => {
          const style = colorScale(row.returns?.["1d"]);
          const isLead = normName(row.symbol) === BROAD_STRIP_LEAD;
          return (
            <div
              key={row.symbol}
              className={"mkt-broad-tile" + (isLead ? " mkt-broad-tile-lead" : "")}
            >
              <span className="mkt-broad-name mono">{row.name || row.symbol}</span>
              <span className="mkt-broad-last mono">{row.close ?? "—"}</span>
              <span className="mkt-broad-chg mono" style={{ color: style.color }}>
                {pct(row.returns?.["1d"])}
              </span>
              <Sparkline values={row.spark} />
            </div>
          );
        })}
        {vix && <VixTile vix={vix} />}
        {ordered.length === 0 && <p className="mono thin-note">no broad index history</p>}
      </div>
      <p className="caption-b">
        [B] This is a swing tool — midcap/smallcap names (led by Nifty MidSmallcap 400) are the
        traded universe, so they lead the strip. Nifty 50 and India VIX are broad-market context,
        not the trade; sectors and themes below drive the actual calls.
      </p>
    </div>
  );
}

const VIX_BAND_COLOR = {
  low: "var(--positive)",
  normal: "var(--ink-dim)",
  elevated: "var(--warn)",
  danger: "var(--danger)",
};

function VixTile({ vix }) {
  if (!vix) return null;
  const color = VIX_BAND_COLOR[vix.band] || "var(--ink-dim)";
  return (
    <div className="mkt-broad-tile mkt-broad-vix" style={{ borderColor: color }}>
      <span className="mkt-broad-name mono">India VIX</span>
      <span className="mkt-broad-last mono" style={{ color }}>
        {vix.value}
      </span>
      <span className="mkt-broad-chg small-caps" style={{ color }}>
        <Term k="vix-band">{vix.band}</Term>
      </span>
    </div>
  );
}

// ── G3/F6: sortable D/W/M/3M table for one NSE index class at a time
// (SECTORAL or THEMATIC_STRATEGY) — this replaces the old full indices grid,
// which duplicated the sector treemap ("point of heatmap and indice values
// of the same thing"), AND replaces the single mixed SECTORAL+THEMATIC
// table (F6 taxonomy cleanup: NSE sectoral and thematic indices no longer
// share one un-labeled table). Rows click-filter the movers panel and open
// the stock drill-down via onSelect.
const NSE_SORT_KEYS = {
  name: (r) => r.name || r.symbol || "",
  last: (r) => r.close ?? -Infinity,
  r1d: (r) => r.returns?.["1d"] ?? -Infinity,
  r1w: (r) => r.returns?.["1w"] ?? -Infinity,
  r1m: (r) => r.returns?.["1m"] ?? -Infinity,
  r3m: (r) => r.returns?.["3m"] ?? -Infinity,
  risk: (r) => r.p_drawdown_5d ?? -Infinity,
};

// SHIP-1 #15 (I14): EXPERIMENTAL hierarchical sector-downside risk chip —
// P(sector drawdown >= 2% over the next 5 sessions). Walk-forward validated
// to beat the base-rate baseline (Brier 0.206 vs 0.213 on the pooled OOS
// months) before this column was enabled; null when the row has no score
// yet (table not backfilled / gate not met for that sector that night).
function RiskCell({ pDrawdown }) {
  if (pDrawdown === null || pDrawdown === undefined) {
    return <td className="mono thin-row">—</td>;
  }
  const pct5 = Math.round(pDrawdown * 100);
  return (
    <td className="mono" title="EXPERIMENTAL — P(sector drawdown >= 2% within 5 sessions)">
      {pct5}%
    </td>
  );
}

// T9: default density -- top-5 by 1D% (strongest) + bottom-5 (weakest),
// deduped, with a "show all N" toggle for the full list. Not a re-sort of
// the underlying data, just which rows are shown by default.
function topBottomFive(sourceRows) {
  const withR1d = (sourceRows || []).filter((r) => r.returns?.["1d"] !== null && r.returns?.["1d"] !== undefined);
  const withoutR1d = (sourceRows || []).filter((r) => r.returns?.["1d"] === null || r.returns?.["1d"] === undefined);
  const bySortDesc = [...withR1d].sort((a, b) => (b.returns["1d"] ?? 0) - (a.returns["1d"] ?? 0));
  const top = bySortDesc.slice(0, 5);
  const bottom = bySortDesc.slice(-5);
  const seen = new Set();
  const picked = [];
  [...top, ...bottom].forEach((r) => {
    if (!seen.has(r.symbol)) {
      seen.add(r.symbol);
      picked.push(r);
    }
  });
  // Backfill with no-1D-data rows only if there weren't enough scored rows
  // to fill a top+bottom set at all (keeps the default view non-empty).
  if (picked.length === 0 && withoutR1d.length) return withoutR1d.slice(0, 10);
  return picked;
}

function NseIndexTable({ title, emptyLabel, rows: sourceRows, selected, onSelect, caption, defaultSortKey = "r1d" }) {
  const [sortKey, setSortKey] = useState(defaultSortKey);
  const [sortDir, setSortDir] = useState(-1);
  const [showAll, setShowAll] = useState(false);

  const totalCount = (sourceRows || []).length;
  const baseRows = showAll ? sourceRows : topBottomFive(sourceRows);
  // T9: hide RISK* in the default (top/bottom-5) view when it's "—" for
  // more than half of the rows actually shown; always show it once expanded.
  const riskFilled = (baseRows || []).filter(
    (r) => r.p_drawdown_5d !== null && r.p_drawdown_5d !== undefined
  ).length;
  const showRiskColumn = showAll || (baseRows.length > 0 && riskFilled > baseRows.length / 2);

  const rows = useMemo(() => {
    if (!sortKey) return baseRows;
    const fn = NSE_SORT_KEYS[sortKey];
    return [...(baseRows || [])].sort((a, b) => (fn(a) > fn(b) ? 1 : fn(a) < fn(b) ? -1 : 0) * sortDir);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [baseRows, sortKey, sortDir]);

  function onSort(key) {
    if (sortKey === key) {
      setSortDir((d) => -d);
    } else {
      setSortKey(key);
      setSortDir(1);
    }
  }

  function Th({ label, sortableKey }) {
    const active = sortKey === sortableKey;
    return (
      <th className={"mkt-th" + (active ? " active" : "")} onClick={() => onSort(sortableKey)}>
        {label} {active ? (sortDir === 1 ? "▲" : "▼") : ""}
      </th>
    );
  }

  return (
    <div className="panel">
      <p className="panel-title small-caps">{title}</p>
      <div className="ledger-table-wrap">
        <table className="ledger-table mkt-indices-table">
          <thead>
            <tr>
              <Th label="Name" sortableKey="name" />
              <Th label="Last" sortableKey="last" />
              <Th label="1D" sortableKey="r1d" />
              <Th label="1W" sortableKey="r1w" />
              <Th label="1M" sortableKey="r1m" />
              <Th label="3M" sortableKey="r3m" />
              <th className="mkt-th">30d</th>
              {showRiskColumn && <Th label="RISK*" sortableKey="risk" />}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={row.symbol}
                className={"mkt-row-clickable" + (selected === row.symbol ? " active" : "")}
                onClick={() => onSelect(selected === row.symbol ? null : row.symbol, row)}
              >
                <td className="mono">{row.name || row.symbol}</td>
                <td className="mono">{row.close ?? "—"}</td>
                <ReturnCell value={row.returns?.["1d"]} />
                <ReturnCell value={row.returns?.["1w"]} />
                <ReturnCell value={row.returns?.["1m"]} />
                <ReturnCell value={row.returns?.["3m"]} />
                <td>
                  <Sparkline values={row.spark} />
                </td>
                {showRiskColumn && <RiskCell pDrawdown={row.p_drawdown_5d} />}
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={showRiskColumn ? 8 : 7} className="mono thin-row">
                  {emptyLabel}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {totalCount > rows.length && !showAll && (
        <button type="button" className="show-all-toggle" onClick={() => setShowAll(true)}>
          show all {totalCount}
        </button>
      )}
      {showAll && totalCount > 10 && (
        <button type="button" className="show-all-toggle" onClick={() => setShowAll(false)}>
          show top/bottom 5 only
        </button>
      )}
      <p className="caption-b">{caption}</p>
    </div>
  );
}

// F6 taxonomy cleanup: the ChartsMaze 21-bucket sector leaderboard
// (sector_metrics: RS% + MA-participation breadth + MARS) gets its own
// table instead of being mixed into the NSE index rows above — a different
// vocabulary (ChartsMaze "Auto"/"Pharma & Healthcare" buckets, not NSE index
// names) and a different sort/refresh cadence.
const CHARTSMAZE_SORT_KEYS = {
  name: (r) => r.name || r.sector_key || "",
  rs: (r) => r.rs_pct ?? -Infinity,
  breadth: (r) => r.breadth ?? -Infinity,
  mars: (r) => r.mars_score ?? -Infinity,
  delta: (r) => r.rs_delta_1w ?? -Infinity,
};

function StockRsInline({ kind, identity, date, onSelectStock }) {
  const [state, setState] = useState({ loading: true, error: null, data: null });

  useEffect(() => {
    let cancelled = false;
    setState({ loading: true, error: null, data: null });
    const request = kind === "sector"
      ? fetchSectorStocks(identity, date)
      : fetchIndustryStocks(identity, date);
    request
      .then((data) => {
        if (!cancelled) setState({ loading: false, error: null, data });
      })
      .catch((error) => {
        if (!cancelled) setState({ loading: false, error: String(error), data: null });
      });
    return () => {
      cancelled = true;
    };
  }, [date, identity, kind]);

  if (state.loading) {
    return <p className="v5-stock-rs-state mono" role="status">Loading stocks…</p>;
  }
  if (state.error) {
    return <p className="v5-stock-rs-state mono" role="status">Could not load stocks.</p>;
  }
  if (!state.data?.available || state.data.stocks.length === 0) {
    return <p className="v5-stock-rs-state mono" role="status">No stock RS data for this row yet.</p>;
  }

  const stocks = [...state.data.stocks].sort(
    (a, b) => (b.rs ?? -Infinity) - (a.rs ?? -Infinity) || a.ticker.localeCompare(b.ticker),
  );
  return (
    <ul className="v5-stock-rs-list" aria-label={`${identity} stocks by relative strength`}>
      {stocks.map((stock) => (
        <li key={stock.ticker}>
          <button type="button" className="v5-stock-rs-stock mono" onClick={() => onSelectStock(stock.ticker)}>
            <span>{stock.ticker}</span>
            <span>RS {stock.rs ?? "—"}</span>
          </button>
        </li>
      ))}
    </ul>
  );
}

function ChartsMazeSectorsTable({ rows: sourceRows, date, onSelectStock }) {
  const [sortKey, setSortKey] = useState("rs");
  const [sortDir, setSortDir] = useState(-1);
  const [expandedKey, setExpandedKey] = useState(null);

  const rows = useMemo(() => {
    if (!sortKey) return sourceRows;
    const fn = CHARTSMAZE_SORT_KEYS[sortKey];
    return [...(sourceRows || [])].sort((a, b) => (fn(a) > fn(b) ? 1 : fn(a) < fn(b) ? -1 : 0) * sortDir);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sourceRows, sortKey, sortDir]);

  function onSort(key) {
    if (sortKey === key) {
      setSortDir((d) => -d);
    } else {
      setSortKey(key);
      setSortDir(1);
    }
  }

  function Th({ label, sortableKey }) {
    const active = sortKey === sortableKey;
    return (
      <th className={"mkt-th" + (active ? " active" : "")} onClick={() => onSort(sortableKey)}>
        {label} {active ? (sortDir === 1 ? "▲" : "▼") : ""}
      </th>
    );
  }

  return (
    <div className="panel">
      <p className="panel-title small-caps">ChartsMaze sectors</p>
      <div className="ledger-table-wrap">
        <table className="ledger-table mkt-indices-table">
          <thead>
            <tr>
              <Th label="Sector" sortableKey="name" />
              <Th label="RS %" sortableKey="rs" />
              <Th label="Breadth" sortableKey="breadth" />
              <Th label="MARS" sortableKey="mars" />
              <Th label="1W RS chg" sortableKey="delta" />
              <th className="mkt-th">Action</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const expanded = expandedKey === row.sector_key;
              return (
                <React.Fragment key={row.sector_key}>
                  <tr className={expanded ? "mkt-row-clickable active" : "mkt-row-clickable"}>
                    <td className="mono">
                      <button
                        type="button"
                        className="v5-row-drill-toggle mono"
                        aria-expanded={expanded}
                        onClick={() => setExpandedKey(expanded ? null : row.sector_key)}
                      >
                        <span aria-hidden="true">{expanded ? "⌄" : "›"}</span>
                        {row.name || row.sector_key}
                      </button>
                    </td>
                    <ReturnCell value={row.rs_pct} />
                    <td className="mono">{row.breadth ?? "—"}</td>
                    <td className="mono">
                      {row.mars_score ?? "—"}
                      {row.mars_state ? ` · ${row.mars_state}` : ""}
                    </td>
                    <ReturnCell value={row.rs_delta_1w} />
                    <td className="mono">{row.action ?? "—"}</td>
                  </tr>
                  {expanded && (
                    <tr className="v5-stock-rs-detail-row">
                      <td colSpan={6}>
                        <StockRsInline
                          kind="sector"
                          identity={row.sector_key}
                          date={date}
                          onSelectStock={onSelectStock}
                        />
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
            {rows.length === 0 && (
              <tr>
                <td colSpan={6} className="mono thin-row">
                  no ChartsMaze sector snapshot
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <p className="caption-b">
        [B] These are ChartsMaze's own 21 sector buckets (RS % rank and 50-day breadth over that
        sector's stocks), not NSE indices — a different vocabulary from the two tables above, so
        it gets its own row and its own sort instead of being blended in.
      </p>
    </div>
  );
}

// F6 SECTOR/THEME DRILL-DOWN: inline expandable card of member stocks for
// whichever sector/theme was last clicked (treemap cell or any of the three
// tables above). Ticker, RS, price, 1D%, EMA-stack state, delivery flag —
// each row opens the ChartDrawer via onSelectStock.
const EMA_STATE_LABEL = { lead: "Lead", mixed: "Mixed", lag: "Lag" };

function EmaStateChip({ state }) {
  if (!state) return <span className="mono thin-note">—</span>;
  const label = EMA_STATE_LABEL[state] || state;
  return (
    <span className={`mkt-ema-chip mkt-ema-${state}`}>
      <Term k="ema-stack">{label}</Term>
    </span>
  );
}

function SectorStockDrilldown({ sector, label, date, onSelectStock, onClose }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!sector) return undefined;
    let cancelled = false;
    setData(null);
    setError(null);
    setLoading(true);
    fetchMarketSectorStocks(sector, date)
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
  }, [sector, date]);

  if (!sector) return null;

  return (
    <div className="panel mkt-drilldown">
      <div className="mkt-drilldown-head">
        <p className="panel-title small-caps">
          {label || sector} — stocks
        </p>
        <button className="mkt-treemap-clear" onClick={onClose}>
          close
        </button>
      </div>
      {loading && <p className="mono thin-note">Loading stocks…</p>}
      {error && <p className="mono thin-note">Could not load stocks: {error}</p>}
      {!loading && !error && data && !data.available && (
        <p className="mono thin-note">
          No ChartsMaze stock membership for {label || sector} yet.
        </p>
      )}
      {!loading && !error && data && data.available && (
        <div className="ledger-table-wrap">
          <table className="ledger-table mkt-indices-table">
            <thead>
              <tr>
                <th className="mkt-th">Ticker</th>
                <th className="mkt-th">
                  <Term k="rs">RS</Term>
                </th>
                <th className="mkt-th">Price</th>
                <th className="mkt-th">1D</th>
                <th className="mkt-th">EMA-stack</th>
                <th className="mkt-th">Delivery</th>
              </tr>
            </thead>
            <tbody>
              {data.stocks.map((s) => (
                <tr key={s.symbol} className="mkt-row-clickable" onClick={() => onSelectStock(s.symbol)}>
                  <td className="mono">
                    <span className="symbol-chip">{s.symbol}</span>
                  </td>
                  <td className="mono">{s.rs ?? "—"}</td>
                  <td className="mono">{s.close ?? "—"}</td>
                  <ReturnCell value={s.pct_1d} />
                  <td>
                    <EmaStateChip state={s.ema_state} />
                  </td>
                  <td className="mono">
                    {s.delivery_pct != null ? `${round(s.delivery_pct, 1)}%` : "—"}
                    {s.delivery_flag ? " ●" : ""}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="caption-b">
        [B] Click a ticker to open its chart. <Term k="rs">RS</Term> is ChartsMaze's 1-99
        percentile rank; <Term k="ema-stack">EMA-stack</Term> reads Lead/Mixed/Lag off the
        EMA10/21/50 order; the delivery dot flags &gt;=50% delivery (real accumulation/
        distribution, not intraday churn).
      </p>
    </div>
  );
}

// V2: squarified sector treemap. size = num_stocks proxy (falls back to a
// uniform 1 when absent, so the map still renders — just as equal tiles).
// color = 1D % change via the shared colorScale. Click -> onSelect(symbol).
function SectorTreemap({ sectors, selected, onSelect }) {
  const containerRef = useRef(null);
  const [width, setWidth] = useState(0);
  const height = 260;

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return undefined;
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) setWidth(entry.contentRect.width);
    });
    ro.observe(el);
    setWidth(el.clientWidth);
    return () => ro.disconnect();
  }, []);

  const hasSectors = Boolean(sectors && sectors.length > 0);
  // First mount: `sectors` (fetched by the parent) is already there by the
  // time this renders, but the container's real width isn't known until the
  // ResizeObserver's first callback fires a tick later. Before that, `width`
  // is still its initial 0 -- which used to read exactly like "the fetch
  // came back empty" and flash "no sector data" for one frame on first load
  // (never on a later re-render, because `width` is already measured by
  // then). Treat width-not-yet-measured as a distinct loading state so the
  // empty state only ever means settled-empty.
  const notYetMeasured = hasSectors && width === 0;

  const rects = useMemo(() => {
    if (!hasSectors || width === 0) return [];
    const items = sectors.map((s) => ({
      name: s.name || s.symbol,
      symbol: s.symbol,
      size: s.num_stocks && s.num_stocks > 0 ? s.num_stocks : 1,
      value: s.move_pct,
    }));
    return squarifyTreemap(items, width, height);
  }, [sectors, hasSectors, width]);

  return (
    <div className="panel">
      <p className="panel-title small-caps">Sectors &amp; themes — treemap</p>
      <div ref={containerRef} className="mkt-treemap" style={{ height: `${height}px` }}>
        {notYetMeasured && <p className="mono thin-note">loading sector map…</p>}
        {!notYetMeasured && rects.length === 0 && <p className="mono thin-note">no sector data</p>}
        {rects.map((r) => {
          const style = colorScale(r.value, 5);
          const isSelected = selected === r.symbol;
          const tooSmall = r.w < 46 || r.h < 28;
          return (
            <button
              key={r.symbol}
              className={"mkt-treemap-cell" + (isSelected ? " active" : "")}
              style={{
                left: `${r.x}px`,
                top: `${r.y}px`,
                width: `${r.w}px`,
                height: `${r.h}px`,
                background: style.background,
                color: style.color,
              }}
              title={`${r.name} · ${pct(r.value)} · ${sectors.find((s) => s.symbol === r.symbol)?.num_stocks ?? "—"} weight`}
              onClick={() => onSelect(isSelected ? null : r.symbol)}
            >
              {!tooSmall && (
                <span className="mkt-treemap-cell-inner mono">
                  <span className="mkt-treemap-cell-name">{r.name}</span>
                  <span className="mkt-treemap-cell-pct">{pct(r.value)}</span>
                </span>
              )}
            </button>
          );
        })}
      </div>
      <p className="caption-b">
        [B] Size = number of stocks in the sector, color = today's move. This is the hero —
        sectors and themes, not broad indices, are where the setups live.
        {selected && (
          <>
            {" "}
            Filtering to <strong>{selected}</strong>.{" "}
            <button className="mkt-treemap-clear" onClick={() => onSelect(null)}>
              clear
            </button>
          </>
        )}
      </p>
    </div>
  );
}

const MOVER_TABS = [
  { key: "d1", label: "1D" },
  { key: "w1", label: "1W" },
  { key: "m1", label: "1M" },
];

// Industry (ChartsMaze theme) rotation — RS / Returns by horizon. The
// sector half of this table used to duplicate ChartsMazeSectorsTable above
// (same "ChartsMaze sectors" title, same rank, just fewer columns) -- that
// duplicate panel is gone; this table now only covers the ~90-bucket theme
// set, which ChartsMazeSectorsTable does NOT cover (it's sectors-only).
function RotationRsTable({ themes, date, onSelectStock }) {
  const [lens, setLens] = useState("1m");
  const [measure, setMeasure] = useState("rs");
  const [expandedIndustry, setExpandedIndustry] = useState(null);
  const themeRows = [...(themes || [])].filter((row) => row[measure]?.[lens] !== null && row[measure]?.[lens] !== undefined)
    .sort((a, b) => Number(b[measure][lens]) - Number(a[measure][lens]));
  return (
    <div className="panel v5-rotation-rs-workspace">
      <p className="panel-title small-caps">Industry rotation — ChartsMaze themes</p>
      <div className="v5-rotation-tabs" role="group" aria-label="relative strength timeframe">
        {["3d", "1w", "1m", "3m", "6m"].map((key) => (
          <button type="button" key={key} className={lens === key ? "active" : ""} onClick={() => setLens(key)}>
            {key.toUpperCase()}
          </button>
        ))}
        <span className="v5-rotation-switch">
          <button type="button" className={measure === "rs" ? "active" : ""} onClick={() => setMeasure("rs")}>RS</button>
          <button type="button" className={measure === "returns" ? "active" : ""} onClick={() => setMeasure("returns")}>Returns</button>
        </span>
      </div>
      <p className="caption-b">
        The full ChartsMaze industry/theme set (a finer grain than the 21 sector buckets above).
        RS is the cross-sectional percentile of the selected horizon's return; returns come from
        the preserved daily ChartsMaze history.
      </p>
      <div className="v5-rotation-rs" role="table" aria-label="ChartsMaze themes">
        <div className="v5-rotation-theme-head" role="row">
          <span>Rank</span>
          <span>Group</span>
          <span>{lens.toUpperCase()} {measure === "rs" ? "RS" : "return"}</span>
        </div>
        {themeRows.slice(0, 20).map((row, index) => {
          const expanded = expandedIndustry === row.name;
          return (
            <React.Fragment key={row.name}>
              <div className={expanded ? "v5-rotation-theme-row active" : "v5-rotation-theme-row"} role="row">
                <span>{index + 1}</span>
                <button
                  type="button"
                  className="v5-row-drill-toggle"
                  aria-expanded={expanded}
                  onClick={() => setExpandedIndustry(expanded ? null : row.name)}
                >
                  <span aria-hidden="true">{expanded ? "⌄" : "›"}</span>
                  <b>{row.name}</b>
                </button>
                <span className="mono-num">{measure === "rs" ? `${row.rs[lens].toFixed(1)}` : pct(row.returns[lens])}</span>
              </div>
              {expanded && (
                <div className="v5-stock-rs-industry-detail">
                  <StockRsInline
                    kind="industry"
                    identity={row.name}
                    date={date}
                    onSelectStock={onSelectStock}
                  />
                </div>
              )}
            </React.Fragment>
          );
        })}
        {themeRows.length === 0 && <p className="mono thin-note">no theme rotation data for this horizon yet</p>}
      </div>
    </div>
  );
}

// SHIP-1 #11: "sectors_up" is always the top-5 sectors by return, even when
// every sector is red (all-red day) — so a plain "Sectors up" label lies on
// those days. Pure helper: on an all-negative (or empty) list, relabel to
// "Least down" / "no sectors up today" instead.
export function sectorsUpTitle(rows, valueKey = "move_pct") {
  if (!rows || rows.length === 0) return "no sectors up today";
  const allNegative = rows.every((r) => typeof r[valueKey] === "number" && r[valueKey] < 0);
  return allNegative ? "Least down" : "Sectors up";
}

function MoversList({ title, rows, valueKey = "move_pct" }) {
  return (
    <div className="mkt-movers-col">
      <p className="overline">{title}</p>
      {(!rows || rows.length === 0) && <p className="mono thin-note">none</p>}
      {(rows || []).map((r) => {
        const style = colorScale(r[valueKey]);
        return (
          <div key={r.symbol || r.name} className="mkt-mover-row mono" style={style}>
            <span className="mkt-mover-name">{r.name}</span>
            <span className="mkt-mover-value">{pct(r[valueKey])}</span>
            {r.num_stocks !== undefined && r.num_stocks !== null && (
              <span className="mkt-mover-count">({r.num_stocks})</span>
            )}
          </div>
        );
      })}
    </div>
  );
}

function SectorThemeMoversPanel({ movers, sectorFilter, onClearFilter }) {
  const [tab, setTab] = useState("d1");
  const data = movers && movers[tab];
  const filterRows = (rows) =>
    sectorFilter ? (rows || []).filter((r) => r.symbol === sectorFilter) : rows;
  return (
    <div className="panel">
      <p className="panel-title small-caps">Sector &amp; theme movers</p>
      <div className="mkt-sub-tabs">
        {MOVER_TABS.map((t) => (
          <button
            key={t.key}
            className={"mkt-sub-tab-btn" + (t.key === tab ? " active" : "")}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>
      {sectorFilter && (
        <p className="caption-b">
          Filtered to <strong>{sectorFilter}</strong>.{" "}
          <button className="mkt-treemap-clear" onClick={onClearFilter}>
            clear
          </button>
        </p>
      )}
      {!data && <p className="mono thin-note">no data</p>}
      {data && (
        <div className="mkt-movers-grid">
          <MoversList title={sectorsUpTitle(data.sectors_up)} rows={filterRows(data.sectors_up)} />
          <MoversList title="Sectors down" rows={filterRows(data.sectors_down)} />
          <MoversList title="Themes up" rows={sectorFilter ? [] : data.themes_up} />
        </div>
      )}
      <p className="caption-b">
        [B] These rank sector/theme indices themselves (e.g. Nifty Bank, Pharmaceuticals) —
        for individual stocks, see "Stock movers" below.
      </p>
    </div>
  );
}

// ── G3 bug fix: "movers and big delivery show indices instead of stocks".
// The panel below reads `stock_movers` (added server-side from daily_prices,
// EQ series, is_tradeable stocks only) — real tickers with %chg and
// delivery%, never index rows.
function StockRow({ r, valueLabel }) {
  const style = colorScale(r.chg_pct);
  return (
    <div key={r.symbol} className="mkt-stock-row mono">
      <span className="symbol-chip">{r.symbol}</span>
      <span className="mkt-stock-name">{r.name}</span>
      <span className="mkt-stock-chg" style={{ color: style.color }}>
        {pct(r.chg_pct)}
      </span>
      {valueLabel === "delivery" ? (
        <span className="mkt-stock-extra">{r.delivery_pct != null ? `${round(r.delivery_pct, 1)}% del` : "—"}</span>
      ) : (
        <span className="mkt-stock-extra">{r.close ?? "—"}</span>
      )}
    </div>
  );
}

function StockMoversPanel({ stockMovers }) {
  const [tab, setTab] = useState("gainers");
  if (!stockMovers || (!stockMovers.gainers?.length && !stockMovers.losers?.length && !stockMovers.big_delivery?.length)) {
    return (
      <div className="panel">
        <p className="panel-title small-caps">Stock movers &amp; big delivery</p>
        <p className="mono thin-note">no priced stock data for this date yet</p>
      </div>
    );
  }
  const tabs = [
    { key: "gainers", label: "Top gainers" },
    { key: "losers", label: "Top losers" },
    { key: "big_delivery", label: <Term k="delivery-pct" as="span">Big delivery</Term> },
  ];
  const rows = stockMovers[tab] || [];
  return (
    <div className="panel">
      <p className="panel-title small-caps">Stock movers &amp; big delivery</p>
      <div className="mkt-sub-tabs">
        {tabs.map((t) => (
          <button
            key={t.key}
            className={"mkt-sub-tab-btn" + (t.key === tab ? " active" : "")}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="mkt-movers-col">
        {rows.length === 0 && <p className="mono thin-note">none</p>}
        {rows.map((r) => (
          <StockRow key={r.symbol} r={r} valueLabel={tab === "big_delivery" ? "delivery" : "chg"} />
        ))}
      </div>
      <p className="caption-b">
        [B] These are individual stocks (ticker, %chg{tab === "big_delivery" ? ", delivery%" : ""}) — not index
        rows. Big delivery = high delivery% names, a sign of real (non-intraday) buying/selling interest.
      </p>
    </div>
  );
}

// F7: FII/DII cash-provisional strip. Values are Rs. crore, so colorScale's
// default %-range cap doesn't apply — cap the intensity ramp at 2000cr
// (typical single-day range) instead.
const FII_DII_CAP_CR = 2000;

function crore(n) {
  if (n === null || n === undefined) return "—";
  const sign = n >= 0 ? "+" : "";
  return `${sign}${round(n, 0)}`;
}

function FiiDiiMiniBars({ rows, valueKey }) {
  const values = (rows || []).map((r) => r[valueKey]).filter((v) => v !== null && v !== undefined);
  const maxAbs = Math.max(1, ...values.map((v) => Math.abs(v)));
  return (
    <div className="fii-dii-bars">
      {(rows || []).map((r, idx) => {
        const v = r[valueKey];
        const style = colorScale(v, FII_DII_CAP_CR);
        const h = v === null || v === undefined ? 2 : Math.max(2, (Math.abs(v) / maxAbs) * 22);
        return (
          <span
            key={r.trade_date || idx}
            className="fii-dii-bar"
            title={`${r.trade_date}: ${crore(v)} cr`}
            style={{ height: `${h}px`, background: style.color }}
          />
        );
      })}
    </div>
  );
}

function fiiDiiCaption(fiiDii) {
  const net = fiiDii?.latest?.fii_net;
  const diiNet = fiiDii?.latest?.dii_net;
  if (net === null || net === undefined) return null;
  const fiiVerb = net >= 0 ? "bought" : "sold";
  const fiiWho = net >= 0 ? "foreign money entering" : "foreign money leaving";
  const diiVerb = diiNet === null || diiNet === undefined ? null : diiNet >= 0 ? "bought" : "sold";
  let line = `FII ${fiiVerb} ₹${round(Math.abs(net), 0)} cr today — ${fiiWho}.`;
  if (diiVerb) {
    line += ` DII ${diiVerb} ₹${round(Math.abs(diiNet), 0)} cr — domestic funds ${diiVerb === "bought" ? "buying the dip" : "taking profit"}.`;
  }
  return line;
}

// F7/UI-3: standalone FII/DII panel (was buried inside the Deals & flows
// card under a dashed mini-strip — promoted to its own titled panel per
// user ask, so it's not missed while scrolling). Honest empty-state when
// fii_dii_daily has no rows on/before this date, never a fake zero.
function FiiDiiPanel({ fiiDii }) {
  if (!fiiDii) {
    return (
      <div className="panel">
        <p className="panel-title small-caps">FII / DII cash</p>
        <p className="mono thin-note">FII/DII data not available (as of this date) — fii_dii_daily not yet ingested.</p>
      </div>
    );
  }
  const { latest, last_10: last10, net_trend: netTrend } = fiiDii;
  const fiiStyle = colorScale(latest?.fii_net, FII_DII_CAP_CR);
  const diiStyle = colorScale(latest?.dii_net, FII_DII_CAP_CR);
  const oldestFirst = [...(last10 || [])].reverse();
  return (
    <div className="panel fii-dii-strip">
      <div className="mkt-drilldown-head">
        <p className="panel-title small-caps">
          <Term k="fii-dii">FII / DII cash</Term> (₹ cr)
        </p>
        <span className="mono thin-note">EOD as of {latest?.trade_date || "—"}</span>
      </div>
      <div className="fii-dii-row">
        <div className="fii-dii-cell mono" style={fiiStyle}>
          <span className="fii-dii-label">FII net</span>
          <span className="fii-dii-value">{crore(latest?.fii_net)}</span>
        </div>
        <div className="fii-dii-cell mono" style={diiStyle}>
          <span className="fii-dii-label">DII net</span>
          <span className="fii-dii-value">{crore(latest?.dii_net)}</span>
        </div>
      </div>
      <div className="fii-dii-row">
        <div className="fii-dii-col">
          <span className="mono thin-note">FII 10d trend ({crore(netTrend?.fii_net_sum)})</span>
          <FiiDiiMiniBars rows={oldestFirst} valueKey="fii_net" />
        </div>
        <div className="fii-dii-col">
          <span className="mono thin-note">DII 10d trend ({crore(netTrend?.dii_net_sum)})</span>
          <FiiDiiMiniBars rows={oldestFirst} valueKey="dii_net" />
        </div>
      </div>
      <p className="caption-b">[B] {fiiDiiCaption(fiiDii) || "No FII/DII net figure for this date yet."}</p>
    </div>
  );
}

// ── G3: "point of the blue circles in deals" — replace anonymous dot chips
// with labeled cards: symbol, deal type, qty/value, buyer/seller (truncated), date.
function truncateName(name, max = 22) {
  if (!name) return "—";
  return name.length > max ? `${name.slice(0, max - 1)}…` : name;
}

function firstOf(detail, keys) {
  for (const k of keys) {
    if (detail[k] !== undefined && detail[k] !== null && detail[k] !== "") return detail[k];
  }
  return null;
}

const QTY_KEYS = ["Quantity Traded", "Quantity", "Qty", "qty"];
const PRICE_KEYS = ["Trade Price", "Price", "price"];
const SIDE_KEYS = ["Buy / Sell", "Buy/Sell", "Deal Type", "type"];
const COUNTERPARTY_KEYS = ["Client Name", "Acquirer/Disposer", "Person", "person", "buyer"];

const DEAL_KIND_LABEL = { bulk_deal: "Bulk/block", insider: "Insider" };

// SHIP-1 #14: known prop-desk/HFT counterparties get a muted card style —
// these are not directional conviction signals the way a promoter or a
// concentrated fund buy is, so they should not visually compete with those.
const PROP_DESK_NAMES = [
  "GRAVITON", "ALPHAGREP", "IRAGE", "JUMP", "JUNOMONETA", "QE SECURITIES", "TOWER RESEARCH",
];

export function isPropDeskCounterparty(name) {
  if (!name) return false;
  const upper = String(name).toUpperCase();
  return PROP_DESK_NAMES.some((n) => upper.includes(n));
}

function DealCard({ deal }) {
  const detail = deal.detail || {};
  const qty = firstOf(detail, QTY_KEYS);
  const price = firstOf(detail, PRICE_KEYS);
  const side = firstOf(detail, SIDE_KEYS);
  const who = firstOf(detail, COUNTERPARTY_KEYS);
  const muted = isPropDeskCounterparty(who);
  const pctOfMcap = deal.pct_of_mcap;
  return (
    <div className={"mkt-deal-card mono" + (muted ? " mkt-deal-card-muted" : "")}>
      <span className="symbol-chip">{deal.symbol}</span>
      <span className="mkt-deal-kind small-caps">{DEAL_KIND_LABEL[deal.kind] || deal.kind}</span>
      <span className="mkt-deal-detail">
        {side ? `${side} · ` : ""}
        {qty ? `${qty} sh` : "qty n/a"}
        {price ? ` @ ${price}` : ""} ·{" "}
        {muted ? <Term k="prop-desk">{truncateName(who)}</Term> : truncateName(who)}
      </span>
      <span className="mkt-deal-date">
        {deal.trade_date}
        {pctOfMcap != null && (
          <span className="mkt-deal-pct-mcap">
            {" "}
            · <Term k="pct-of-mcap">{pct(pctOfMcap)} of mcap</Term>
          </span>
        )}
      </span>
    </div>
  );
}

// SHIP-1 #14: rank the combined deals timeline by pct_of_mcap desc; deals
// with no computable pct_of_mcap (missing market cap or missing qty/price)
// sort last, ordered by trade_date desc among themselves.
export function rankDealsByMcap(deals) {
  const withPct = [];
  const withoutPct = [];
  for (const d of deals || []) {
    if (d.pct_of_mcap != null) withPct.push(d);
    else withoutPct.push(d);
  }
  withPct.sort((a, b) => b.pct_of_mcap - a.pct_of_mcap);
  withoutPct.sort((a, b) => (a.trade_date < b.trade_date ? 1 : -1));
  return [...withPct, ...withoutPct];
}

function DealsPanel({ deals }) {
  const blockBulk = (deals && deals.block_bulk) || [];
  const insider = (deals && deals.insider) || [];
  const timeline = rankDealsByMcap([...blockBulk, ...insider]);

  return (
    <div className="panel">
      <p className="panel-title small-caps">Deals &amp; flows</p>
      <div className="mkt-deal-timeline">
        {timeline.length === 0 && <span className="mono thin-note">no disclosures</span>}
        {timeline.map((d, idx) => (
          <DealCard key={`${d.symbol}-${d.kind}-${idx}`} deal={d} />
        ))}
      </div>
      <p className="caption-b">
        [B] Bulk/block = large single trades disclosed to the exchange; insider = promoter/insider buying or
        selling their own company's stock. Both can hint at conviction, but check size relative to the
        company before reading much into one deal.
      </p>
    </div>
  );
}

// EP / IPO WATCH — two side-by-side ranked shortlists over
// manas_os/scanner/focus.py's ipo_watch/ep_watch (discovery_bucket +
// screener_hits, ranked by velocity + strength). Deterministic aggregation,
// not a recommendation.
function WatchRow({ row, onSelect }) {
  const w = row.why || {};
  const bits = [];
  if (w.pct_up_from_65d_low !== null && w.pct_up_from_65d_low !== undefined) {
    bits.push(`+${round(w.pct_up_from_65d_low, 0)}% off 65d low`);
  }
  if (w.adr20 !== null && w.adr20 !== undefined) {
    bits.push(`ADR20 ${round(w.adr20, 1)}%`);
  }
  if (w.purple_dot_count_60d !== null && w.purple_dot_count_60d !== undefined) {
    bits.push(`${w.purple_dot_count_60d} dots`);
  }
  if (w.days_since_listing !== null && w.days_since_listing !== undefined) {
    bits.push(`${w.days_since_listing}d listed`);
  }
  return (
    <button className="watch-row mono" onClick={() => onSelect(row.symbol)}>
      <span className="watch-row-symbol">
        #{row.rank} {row.symbol}
      </span>
      <span className="watch-row-metrics">{bits.join(" · ") || "—"}</span>
    </button>
  );
}

// TOMORROW MORNING (9:07-9:30) — EOD strong-start-ready / D2-ready setups from
// manas_os/scanner/focus.py tomorrow_morning (engine/eod_detectors.py). These
// are NOT fired signals: each is a checklist the human verifies at the open.
function MorningRow({ row, onSelect }) {
  const [open, setOpen] = useState(false);
  const ev = row.evidence || {};
  // d2_ready evidence has day1_high/day1_low (today's completed burst-day
  // candle); strong_start_ready evidence only has prev_day_high (today's
  // high == tomorrow's entry reference) and no pre-open low.
  const buyTrigger = ev.day1_high !== null && ev.day1_high !== undefined ? ev.day1_high : ev.prev_day_high;
  const stopAnchor = ev.day1_low;
  const bits = [];
  if (ev.day1_change_pct !== null && ev.day1_change_pct !== undefined) {
    bits.push(`Day-1 +${round(ev.day1_change_pct, 1)}%${ev.is_20pct_circuit ? " (circuit)" : ""}`);
  }
  if (ev.prev_day_tightness_pctile !== null && ev.prev_day_tightness_pctile !== undefined) {
    bits.push(`tight p${round(ev.prev_day_tightness_pctile, 0)}`);
  }
  if (ev.day_rvol !== null && ev.day_rvol !== undefined) {
    bits.push(`RVOL ${round(ev.day_rvol, 1)}x`);
  }
  return (
    <div className="watch-row-block">
      <button className="watch-row mono" onClick={() => setOpen((o) => !o)}>
        <span className="watch-row-symbol">
          {open ? "▾" : "▸"} {row.symbol}
          <span className="thin-note" style={{ marginLeft: "6px" }}>
            {row.label}
            {row.branch ? ` · ${row.branch}` : ""}
          </span>
        </span>
        <span className="watch-row-metrics">{bits.join(" · ") || "—"}</span>
      </button>
      {open && (
        <div className="mono" style={{ padding: "4px 8px 8px", fontSize: "10px" }}>
          <p className="thin-note" style={{ margin: "2px 0" }}>Verify at the open (9:07-9:30):</p>
          <ul style={{ margin: "2px 0 6px", paddingLeft: "16px" }}>
            {(row.resolve_at_open || []).map((c, i) => (
              <li key={i} style={{ marginBottom: "2px" }}>☐ {c}</li>
            ))}
          </ul>
          {buyTrigger !== null && buyTrigger !== undefined && (
            <p className="thin-note" style={{ margin: "2px 0" }}>
              Buy above {round(buyTrigger, 2)} only if the 5-min ORB (opening range breakout: first
              5-minute high/low) confirms — not the gap price itself.
            </p>
          )}
          {stopAnchor !== null && stopAnchor !== undefined && (
            <p className="thin-note" style={{ margin: "2px 0" }}>
              Stop: day's low, last known {round(stopAnchor, 2)}.
            </p>
          )}
          <p className="thin-note" style={{ margin: "2px 0" }}>Entry: {row.entry_rule}</p>
          <p className="thin-note" style={{ margin: "2px 0" }}>Stop: {row.stop_rule}</p>
          <button
            className="focus-theme-name-btn"
            onClick={() => onSelect(row.symbol)}
            style={{ marginTop: "4px" }}
          >
            open chart
          </button>
        </div>
      )}
    </div>
  );
}

function EpIpoWatchPanel({ date, onSelectStock }) {
  const [focus, setFocus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchFocus(date)
      .then((data) => {
        if (!cancelled) setFocus(data);
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
  }, [date]);

  const ipoRows = focus?.ipo_watch || [];
  const epRows = focus?.ep_watch || [];
  const morningRows = focus?.tomorrow_morning?.rows || [];
  const morningAsOf = focus?.tomorrow_morning?.as_of;

  return (
    <div className="panel">
      <p className="panel-title small-caps">EP / IPO watch</p>
      {loading && <p className="empty-state">Loading…</p>}
      {!loading && error && <p className="empty-state">{error}</p>}
      {!loading && !error && (
        <div className="watch-two-col">
          <div>
            <p className="panel-title small-caps" style={{ fontSize: "10px" }}>
              IPO watch ({ipoRows.length})
            </p>
            {ipoRows.length === 0 && <span className="mono thin-note">no recent listings surfaced</span>}
            <div className="watch-list">
              {ipoRows.map((r) => (
                <WatchRow key={r.symbol} row={r} onSelect={onSelectStock} />
              ))}
            </div>
          </div>
          <div>
            <p className="panel-title small-caps" style={{ fontSize: "10px" }}>
              EP watch ({epRows.length})
            </p>
            {epRows.length === 0 && <span className="mono thin-note">no episodic-pivot names surfaced</span>}
            <div className="watch-list">
              {epRows.map((r) => (
                <WatchRow key={r.symbol} row={r} onSelect={onSelectStock} />
              ))}
            </div>
          </div>
        </div>
      )}
      {!loading && !error && (
        <div style={{ marginTop: "var(--gap-m)" }}>
          <p className="panel-title small-caps" style={{ fontSize: "10px" }}>
            Tomorrow morning · 9:07-9:30 ({morningRows.length})
          </p>
          {morningRows.length === 0 && (
            <span className="mono thin-note">no strong-start / D2 setups ready for the open</span>
          )}
          <div className="watch-list">
            {morningRows.map((r) => (
              <MorningRow key={`${r.symbol}-${r.setup_type}`} row={r} onSelect={onSelectStock} />
            ))}
          </div>
          <p className="caption-b">
            [B] EOD strong-start-ready / D2-ready setups (engine/eod_detectors.py). NOT fired
            signals — each is a checklist to verify at the 9:15 open; the trigger only exists
            intraday. As of {morningAsOf || "—"}.
          </p>
        </div>
      )}
      <p className="caption-b">
        [B] IPO watch = listings &lt;=12 trading months old; EP watch = earnings-gap/episodic-pivot
        screener hits, both ranked by velocity + strength (% up from 65d low, ADR20, purple-dot
        count) — not a recommendation. As of {focus?.as_of || "—"}.
      </p>
    </div>
  );
}

function applyPreset(preset, data) {
  if (!preset || !data) return data;
  return data;
}

export default function MarketTab({ date }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [sectorFilter, setSectorFilter] = useState(null);
  const [includeThematic, setIncludeThematic] = useState(false);
  // F6 drill-down state: which sector/theme's stock list is expanded (shared
  // by the treemap and all three taxonomy tables below) and which chart the
  // ChartDrawer is showing (lifted here, same pattern as DebateTab).
  const [drillSector, setDrillSector] = useState(null);
  const [drillLabel, setDrillLabel] = useState(null);
  const [chartSymbol, setChartSymbol] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchMarket(date, includeThematic)
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
  }, [date, includeThematic]);

  if (loading) {
    return <div className="empty-state">Loading…</div>;
  }
  if (error) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">⚠</div>
        <p className="empty-state-line">Could not load the market.</p>
        <p className="empty-state-sub">{error}</p>
      </div>
    );
  }
  if (!data || !data.available) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">◌</div>
        <p className="empty-state-line">No index history for {date} yet.</p>
        <p className="empty-state-sub">sector_index_prices has nothing on or before this date.</p>
      </div>
    );
  }

  const view = applyPreset(null, data);
  const sectoralRows = (view.indices || []).filter((r) => r.class === "SECTORAL");
  const thematicRows = (view.indices || []).filter((r) => r.class === "THEMATIC_STRATEGY");

  // Treemap + the two NSE tables share one selection: it both filters the
  // movers panel below and opens the enriched stock drill-down. ChartsMaze
  // sector/industry tables own their smaller per-row RS expansions locally.
  function selectNseSector(symbol, row) {
    setSectorFilter(symbol);
    setDrillSector(symbol);
    setDrillLabel(symbol ? row?.name || symbol : null);
  }
  function clearDrilldown() {
    setDrillSector(null);
    setDrillLabel(null);
  }

  return (
    <div>
      <BroadIndicesStrip indices={view.indices} vix={data.vix} />
      <div style={{ height: "var(--gap-m)" }} />
      <FiiDiiPanel fiiDii={data.fii_dii} />
      <div style={{ height: "var(--gap-m)" }} />
      <SectorTreemap
        sectors={data.sectors}
        selected={sectorFilter}
        onSelect={(symbol) => {
          const row = symbol ? (data.sectors || []).find((s) => s.symbol === symbol) : null;
          selectNseSector(symbol, row);
        }}
      />
      {drillSector && (
        <SectorStockDrilldown
          sector={drillSector}
          label={drillLabel}
          date={date}
          onSelectStock={setChartSymbol}
          onClose={clearDrilldown}
        />
      )}
      <NseIndexTable
        title="NSE sectoral indices"
        emptyLabel="no sectoral index history"
        rows={sectoralRows}
        selected={sectorFilter}
        onSelect={selectNseSector}
        caption={
          <>
            [B] Official NSE single-industry indices (e.g. Nifty Bank, Nifty IT) — click a row to
            filter the movers panel and open its stock list. Colors: green = up, red = down;
            intensity = size of the move. RISK* is{" "}
            <Term k="risk-experimental">EXPERIMENTAL</Term>: a hierarchical model's estimated
            chance the sector falls 2%+ over the next 5 sessions — a fact for context, never a
            gate or a size input.
          </>
        }
      />
      <div style={{ height: "var(--gap-m)" }} />
      <NseIndexTable
        title="NSE thematic / strategy indices"
        emptyLabel={includeThematic ? "no thematic/strategy index history" : "hidden — click show below"}
        rows={includeThematic ? thematicRows : []}
        selected={sectorFilter}
        onSelect={selectNseSector}
        defaultSortKey="r1d"
        caption={
          <>
            [B] Multi-sector strategy/factor/fixed-income indices (Quality, Momentum, MidSmall
            blends, G-Sec, etc.) — a different NSE vocabulary from the plain sectoral indices
            above, so they get their own table.{" "}
            <button className="mkt-treemap-clear" onClick={() => setIncludeThematic((v) => !v)}>
              {includeThematic ? "hide thematic/strategy indices" : "show thematic/strategy indices"}
            </button>
          </>
        }
      />
      <div style={{ height: "var(--gap-m)" }} />
      <ChartsMazeSectorsTable
        rows={data.chartsmaze_sectors}
        date={date}
        onSelectStock={setChartSymbol}
      />
      <div style={{ height: "var(--gap-m)" }} />
      <RotationRsTable themes={data.chartsmaze_themes} date={date} onSelectStock={setChartSymbol} />
      <div style={{ height: "var(--gap-m)" }} />
      <div className="mkt-two-col">
        <SectorThemeMoversPanel
          movers={data.movers}
          sectorFilter={sectorFilter}
          onClearFilter={() => setSectorFilter(null)}
        />
        <StockMoversPanel stockMovers={data.stock_movers} />
      </div>
      <div style={{ height: "var(--gap-m)" }} />
      <DealsPanel deals={data.deals} />
      <div style={{ height: "var(--gap-m)" }} />
      <EpIpoWatchPanel date={date} onSelectStock={setChartSymbol} />
      <ChartDrawer symbol={chartSymbol} date={date} onClose={() => setChartSymbol(null)} />
    </div>
  );
}
