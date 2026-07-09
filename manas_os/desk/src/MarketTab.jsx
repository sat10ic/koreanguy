import React, { useEffect, useMemo, useState } from "react";
import { fetchMarket } from "./api.js";
import { colorScale, sparklinePoints } from "./viz.js";

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
  const last = (values || []).filter((v) => v !== null && v !== undefined).slice(-1)[0];
  const endColor = last !== null && last !== undefined ? colorScale(0).color : "var(--ink-dim)";
  return (
    <svg className="mkt-spark" viewBox="0 0 100 26" preserveAspectRatio="none">
      <polyline points={points} fill="none" stroke="var(--accent)" strokeWidth="1.5" />
    </svg>
  );
}

const SORT_KEYS = {
  name: (r) => r.name || r.symbol || "",
  last: (r) => r.close ?? -Infinity,
  r1d: (r) => r.returns?.["1d"] ?? -Infinity,
  r1w: (r) => r.returns?.["1w"] ?? -Infinity,
  r1m: (r) => r.returns?.["1m"] ?? -Infinity,
  r3m: (r) => r.returns?.["3m"] ?? -Infinity,
};

function IndicesTable({ indices }) {
  const [sortKey, setSortKey] = useState(null);
  const [sortDir, setSortDir] = useState(1);

  const rows = useMemo(() => {
    if (!sortKey) return indices;
    const fn = SORT_KEYS[sortKey];
    return [...indices].sort((a, b) => (fn(a) > fn(b) ? 1 : fn(a) < fn(b) ? -1 : 0) * sortDir);
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
      <p className="panel-title small-caps">Indices</p>
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
              <tr key={row.symbol}>
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
                  no index history
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <p className="caption-b">[B] colors: green = up, red = down; intensity = size of the move.</p>
    </div>
  );
}

const MOVER_TABS = [
  { key: "d1", label: "1D" },
  { key: "w1", label: "1W" },
  { key: "m1", label: "1M" },
];

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

function MoversPanel({ movers }) {
  const [tab, setTab] = useState("d1");
  const data = movers && movers[tab];
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
      {!data && <p className="mono thin-note">no data</p>}
      {data && (
        <div className="mkt-movers-grid">
          <MoversList title="Sectors up" rows={data.sectors_up} />
          <MoversList title="Sectors down" rows={data.sectors_down} />
          <MoversList title="Themes up" rows={data.themes_up} />
        </div>
      )}
    </div>
  );
}

const DEAL_CHIP_COLOR = { bulk_deal: "var(--accent)", insider: "var(--warn)" };

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

function DealChip({ deal }) {
  const detail = deal.detail || {};
  const rawQty = firstOf(detail, QTY_KEYS);
  const qty = rawQty ? Number(String(rawQty).replace(/[^0-9.]/g, "")) : null;
  const size = qty ? Math.min(20 + Math.log10(qty + 1) * 8, 64) : 28;
  return (
    <span
      className="mkt-deal-chip mono"
      title={`${deal.symbol} · ${deal.kind} · ${deal.trade_date}`}
      style={{
        background: DEAL_CHIP_COLOR[deal.kind] || "var(--accent)",
        width: `${size}px`,
        height: `${size}px`,
      }}
    >
      {deal.symbol.slice(0, 3)}
    </span>
  );
}

function DealsPanel({ deals }) {
  const blockBulk = (deals && deals.block_bulk) || [];
  const insider = (deals && deals.insider) || [];
  const timeline = [...blockBulk, ...insider].sort((a, b) => (a.trade_date < b.trade_date ? 1 : -1));

  return (
    <div className="panel">
      <p className="panel-title small-caps">Deals &amp; flows</p>
      <div className="mkt-deal-timeline">
        {timeline.length === 0 && <span className="mono thin-note">no disclosures</span>}
        {timeline.map((d, idx) => (
          <DealChip key={`${d.symbol}-${d.kind}-${idx}`} deal={d} />
        ))}
      </div>

      <p className="overline" style={{ marginTop: "var(--gap-s)" }}>
        Block / bulk
      </p>
      <div className="mkt-deal-list">
        {blockBulk.length === 0 && <p className="mono thin-note">none</p>}
        {blockBulk.map((d, idx) => (
          <div key={`bb-${idx}`} className="mkt-deal-row mono">
            <span className="symbol-chip">{d.symbol}</span>
            <span className="mkt-deal-detail">
              {firstOf(d.detail || {}, QTY_KEYS) || "—"} @ {firstOf(d.detail || {}, PRICE_KEYS) || "—"} ·{" "}
              {firstOf(d.detail || {}, SIDE_KEYS) || "—"} · {firstOf(d.detail || {}, COUNTERPARTY_KEYS) || "—"}
            </span>
            <span className="mkt-deal-date">{d.trade_date}</span>
          </div>
        ))}
      </div>

      <p className="overline" style={{ marginTop: "var(--gap-s)" }}>
        Insider
      </p>
      <div className="mkt-deal-list">
        {insider.length === 0 && <p className="mono thin-note">none</p>}
        {insider.map((d, idx) => (
          <div key={`ins-${idx}`} className="mkt-deal-row mono">
            <span className="symbol-chip">{d.symbol}</span>
            <span className="mkt-deal-detail">
              {firstOf(d.detail || {}, COUNTERPARTY_KEYS) || "—"} · {firstOf(d.detail || {}, SIDE_KEYS) || "—"} ·{" "}
              {firstOf(d.detail || {}, QTY_KEYS) || "—"}
            </span>
            <span className="mkt-deal-date">{d.trade_date}</span>
          </div>
        ))}
      </div>

      <div className="fii-dii-strip mono">[BACKEND-GAP-FII] FII/DII cash flows not ingested yet — parked for F7.</div>
    </div>
  );
}

const PRESETS = [
  { key: "top_movers", label: "Top movers" },
  { key: "big_delivery", label: "Big delivery" },
];

function PresetChips({ active, onToggle }) {
  return (
    <div className="chip-row mkt-preset-row">
      {PRESETS.map((p) => (
        <button
          key={p.key}
          className={"agent-chip mkt-preset-chip" + (active === p.key ? " active" : "")}
          onClick={() => onToggle(active === p.key ? null : p.key)}
        >
          {p.label}
        </button>
      ))}
    </div>
  );
}

function applyPreset(preset, data) {
  if (!preset || !data) return data;
  if (preset === "top_movers") {
    // Top movers: sort indices by |1D| descending, keep the top 8.
    const sorted = [...(data.indices || [])].sort(
      (a, b) => Math.abs(b.returns?.["1d"] ?? 0) - Math.abs(a.returns?.["1d"] ?? 0)
    );
    return { ...data, indices: sorted.slice(0, 8) };
  }
  if (preset === "big_delivery") {
    // Big delivery is a stock-level concept we don't carry at the index/sector
    // level yet; the honest behavior here is to fall through unfiltered,
    // signalled via a caption rather than silently dropping rows.
    return data;
  }
  return data;
}

export default function MarketTab({ date }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [preset, setPreset] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchMarket(date)
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
  }, [date]);

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

  const view = applyPreset(preset, data);

  return (
    <div>
      <PresetChips active={preset} onToggle={setPreset} />
      {preset === "big_delivery" && (
        <p className="caption-b">
          [B] Big-delivery filtering needs per-stock delivery% on this payload — not available yet, showing
          everything.
        </p>
      )}
      <IndicesTable indices={view.indices} />
      <div style={{ height: "var(--gap-m)" }} />
      <div className="mkt-two-col">
        <MoversPanel movers={data.movers} />
        <DealsPanel deals={data.deals} />
      </div>
    </div>
  );
}
