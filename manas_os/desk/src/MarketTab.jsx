import React, { useEffect, useMemo, useRef, useState } from "react";
import { fetchMarket } from "./api.js";
import { colorScale, sparklinePoints, squarifyTreemap } from "./viz.js";

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
// the treemap/movers), but the user's ask names it as one of the four
// top-strip "indicator" indices regardless of that classification.
function normName(s) {
  return (s || "").toUpperCase().replace(/[^A-Z0-9]/g, "");
}
const BROAD_STRIP_NAMES = ["NIFTY50", "NIFTYBANK", "NIFTYMIDSMALLCAP400"];

function BroadIndicesStrip({ indices, vix }) {
  const byNorm = new Map((indices || []).map((r) => [normName(r.name || r.symbol), r]));
  const ordered = BROAD_STRIP_NAMES.map((n) => byNorm.get(n)).filter(Boolean);

  return (
    <div className="panel mkt-broad-strip">
      <p className="panel-title small-caps">Broad indices</p>
      <div className="mkt-broad-row">
        {ordered.map((row) => {
          const style = colorScale(row.returns?.["1d"]);
          return (
            <div key={row.symbol} className="mkt-broad-tile">
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
        [B] Broad indices are the weather report, not the trade — sectors and themes below
        drive the actual calls.
      </p>
    </div>
  );
}

const VIX_BAND_COLOR = {
  low: "var(--positive, #2e7d32)",
  normal: "var(--ink-dim)",
  elevated: "var(--warn, #b8860b)",
  danger: "var(--negative, #c0392b)",
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
        {vix.band}
      </span>
    </div>
  );
}

// ── G3: sortable D/W/M/3M table for SECTORAL (+ optional THEMATIC_STRATEGY)
// indices only — this replaces the old full indices grid, which duplicated
// the sector treemap ("point of heatmap and indice values of the same
// thing"). Rows click-filter the movers panel via onSelect.
const SORT_KEYS = {
  name: (r) => r.name || r.symbol || "",
  last: (r) => r.close ?? -Infinity,
  r1d: (r) => r.returns?.["1d"] ?? -Infinity,
  r1w: (r) => r.returns?.["1w"] ?? -Infinity,
  r1m: (r) => r.returns?.["1m"] ?? -Infinity,
  r3m: (r) => r.returns?.["3m"] ?? -Infinity,
};

function SectorTable({ indices, selected, onSelect, includeThematic, onToggleThematic }) {
  const [sortKey, setSortKey] = useState("r1d");
  const [sortDir, setSortDir] = useState(-1);

  const filtered = (indices || []).filter((r) => r.class === "SECTORAL" || r.class === "THEMATIC_STRATEGY");

  const rows = useMemo(() => {
    if (!sortKey) return filtered;
    const fn = SORT_KEYS[sortKey];
    return [...filtered].sort((a, b) => (fn(a) > fn(b) ? 1 : fn(a) < fn(b) ? -1 : 0) * sortDir);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [indices, sortKey, sortDir]);

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
      <p className="panel-title small-caps">Sectors &amp; themes — D/W/M/3M</p>
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
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={row.symbol}
                className={"mkt-row-clickable" + (selected === row.symbol ? " active" : "")}
                onClick={() => onSelect(selected === row.symbol ? null : row.symbol)}
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
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={7} className="mono thin-row">
                  no sector/theme index history
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <p className="caption-b">
        [B] Click a row to filter the movers panel to that sector. Colors: green = up, red =
        down; intensity = size of the move.{" "}
        <button className="mkt-treemap-clear" onClick={onToggleThematic}>
          {includeThematic ? "hide thematic/strategy indices" : "show thematic/strategy indices"}
        </button>
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

  const rects = useMemo(() => {
    if (!sectors || sectors.length === 0 || width === 0) return [];
    const items = sectors.map((s) => ({
      name: s.name || s.symbol,
      symbol: s.symbol,
      size: s.num_stocks && s.num_stocks > 0 ? s.num_stocks : 1,
      value: s.move_pct,
    }));
    return squarifyTreemap(items, width, height);
  }, [sectors, width]);

  return (
    <div className="panel">
      <p className="panel-title small-caps">Sectors &amp; themes — treemap</p>
      <div ref={containerRef} className="mkt-treemap" style={{ height: `${height}px` }}>
        {rects.length === 0 && <p className="mono thin-note">no sector data</p>}
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
    { key: "big_delivery", label: "Big delivery" },
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

function FiiDiiStrip({ fiiDii }) {
  if (!fiiDii) {
    return (
      <div className="fii-dii-strip mono">
        [BACKEND-GAP-FII] FII/DII cash flows not ingested yet for this date.
      </div>
    );
  }
  const { latest, last_10: last10, net_trend: netTrend } = fiiDii;
  const fiiStyle = colorScale(latest?.fii_net, FII_DII_CAP_CR);
  const diiStyle = colorScale(latest?.dii_net, FII_DII_CAP_CR);
  const oldestFirst = [...(last10 || [])].reverse();
  return (
    <div className="fii-dii-strip">
      <p className="overline">FII / DII cash (₹ cr, {latest?.trade_date})</p>
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
      <p className="caption-b">[B] {fiiDiiCaption(fiiDii)}</p>
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
        {price ? ` @ ${price}` : ""} · {truncateName(who)}
      </span>
      <span className="mkt-deal-date">
        {deal.trade_date}
        {pctOfMcap != null && <span className="mkt-deal-pct-mcap"> · {pct(pctOfMcap)} of mcap</span>}
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

function DealsPanel({ deals, fiiDii }) {
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

      <FiiDiiStrip fiiDii={fiiDii} />
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

  return (
    <div>
      <BroadIndicesStrip indices={view.indices} vix={data.vix} />
      <SectorTreemap sectors={data.sectors} selected={sectorFilter} onSelect={setSectorFilter} />
      <SectorTable
        indices={view.indices}
        selected={sectorFilter}
        onSelect={setSectorFilter}
        includeThematic={includeThematic}
        onToggleThematic={() => setIncludeThematic((v) => !v)}
      />
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
      <DealsPanel deals={data.deals} fiiDii={data.fii_dii} />
    </div>
  );
}
