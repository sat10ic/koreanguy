// IDEAS — REDESIGN_SCOUTING_WIRE.md §4.4 (wave 2026-08-24, S7-owned).
// Grouped BY SYMBOL, never by trader: three people on one name is the finding,
// and a per-trader list hides it. Per symbol: a mention-density heat strip
// (inline SVG, trivial, no library), every mention quoted VERBATIM with handle
// and date, and a follow-through line naming who actually bought it — or the
// protected fallback when nobody did. The themes list and the ticker
// leaderboard (WIREFRAMES §5, computed client-side from /api/positions +
// /api/ideas) are kept beneath.
import React from "react";
import { fetchIdeas, fetchPositions } from "../api.js";
import { ErrorBox, Loading, Panel, fmtDate, useApi } from "../components/ui.jsx";
import "../styles/ideas.css";

const MS_DAY = 86400000;
const MAX_CELLS = 52;

// One row per distinct symbol, counts are distinct TRADERS derived entirely
// client-side from /api/positions + /api/ideas (WIREFRAMES.md §5 leaderboard):
//   entered   — traders with ANY position for the symbol
//   holding   — traders whose position is open or partial  (⊂ entered)
//   exited    — traders whose position is closed            (⊂ entered)
//   mentioned — ideas mentioners MINUS anyone already counted as entered
// Only symbols with ≥1 position or ≥1 mention render. Every cell is a count of
// real positions/mentions — nothing here is ever invented.
function buildTickerRows(positions, ideasPayload) {
  const bySymbol = new Map();
  const bucket = (symbol) => {
    let b = bySymbol.get(symbol);
    if (!b) {
      b = { entered: new Set(), holding: new Set(), exited: new Set(), mentioned: new Set() };
      bySymbol.set(symbol, b);
    }
    return b;
  };
  // Handle equality must not depend on a leading "@" if one source ever emits
  // it and another does not — both spell the same roster trader.
  const norm = (handle) => (handle || "").replace(/^@/, "");

  for (const p of positions || []) {
    if (!p || !p.symbol) continue;
    const b = bucket(p.symbol);
    const h = norm(p.handle);
    if (!h) continue;
    b.entered.add(h);
    if (p.status === "open" || p.status === "partial") b.holding.add(h);
    if (p.status === "closed") b.exited.add(h);
  }

  for (const g of ideasPayload?.ideas || []) {
    if (!g || !g.symbol) continue;
    const b = bucket(g.symbol);
    for (const m of g.mentions || []) {
      const h = norm(m.handle);
      if (h) b.mentioned.add(h);
    }
    // A confirmed position is not a mention: anyone already counted as entered
    // (holding and exited are subsets) drops out of the muted column.
    for (const h of b.entered) b.mentioned.delete(h);
  }

  return [...bySymbol.entries()]
    .filter(([, b]) => b.entered.size + b.holding.size + b.exited.size > 0 || b.mentioned.size > 0)
    .map(([symbol, b]) => ({
      symbol,
      entered: b.entered.size,
      holding: b.holding.size,
      exited: b.exited.size,
      mentioned: b.mentioned.size,
    }))
    .sort(
      (a, b) =>
        b.entered - a.entered ||
        b.holding - a.holding ||
        a.symbol.localeCompare(b.symbol)
    );
}

// The leaderboard panel, rendered FIRST inside IDEAS. Positions come from the
// Ideas() screen's own fetch (shared with the follow-through lookups below),
// so /api/positions is not fetched twice.
function TickerBoard({ ideasPayload, positionsData, positionsError, onNavigate }) {
  if (positionsError) return <ErrorBox error={positionsError} />;
  if (!positionsData) return <Loading />;

  const rows = buildTickerRows(positionsData.positions || [], ideasPayload);

  if (rows.length === 0) {
    return (
      <Panel title="Ticker leaderboard">
        <p className="ticker-board-empty">
          Ticker leaderboard — populated as W2 reconciliation links trader
          positions. No confirmed positions or mentions yet.
        </p>
      </Panel>
    );
  }

  return (
    <Panel
      title="Ticker leaderboard"
      right={`${rows.length} ticker${rows.length === 1 ? "" : "s"}`}
    >
      <table className="data ticker-board">
        <thead>
          <tr>
            <th>Ticker</th>
            <th className="num">Entered</th>
            <th className="num">Holding</th>
            <th className="num">Exited</th>
            <th className="num board-mentioned">Mentioned</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr
              key={r.symbol}
              className="ticker-row"
              onClick={() => onNavigate?.("LEDGER", { symbol: r.symbol })}
            >
              <td>
                {/* Keyboard path to the same navigation as the row click. */}
                <button
                  type="button"
                  className="xlink ticker-symbol"
                  onClick={(e) => {
                    e.stopPropagation();
                    onNavigate?.("LEDGER", { symbol: r.symbol });
                  }}
                >
                  {r.symbol}
                </button>
              </td>
              <td className="num">{r.entered}</td>
              <td className="num">{r.holding}</td>
              <td className="num">{r.exited}</td>
              <td className="num board-mentioned">{r.mentioned}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Panel>
  );
}

// WATCH/EP/IPO/THEME chips: same ink family, differentiated by FILL WEIGHT only
// — never hue. WATCH is the filled, heaviest one; THEME the flattest.
const KIND_LABEL = { watch: "WATCH", ep: "EP", ipo: "IPO", theme: "THEME" };
function KindChip({ kind }) {
  const k = String(kind || "").toLowerCase();
  const label = KIND_LABEL[k] || String(kind || "watch").toUpperCase();
  return <span className={`kind-chip kind-${KIND_LABEL[k] ? k : "default"}`}>{label}</span>;
}

// Bucket the mentions into one row of cells across the observed span
// (min..max stated_at), days when the span is short, weeks when it is long,
// capped at 52 cells. Every cell carries its real mention count.
function heatCells(mentions) {
  const times = [];
  for (const m of mentions || []) {
    if (!m || !m.stated_at) continue;
    const t = new Date(m.stated_at).getTime();
    if (!Number.isNaN(t)) times.push(t);
  }
  if (times.length === 0) return null;
  const first = Math.min(...times);
  const last = Math.max(...times);
  const spanDays = Math.max(1, Math.round((last - first) / MS_DAY));
  let bucketDays = spanDays <= 14 ? 1 : 7;
  let n = Math.max(1, Math.ceil(spanDays / bucketDays));
  if (n > MAX_CELLS) {
    bucketDays = Math.ceil(spanDays / MAX_CELLS);
    n = Math.max(1, Math.ceil(spanDays / bucketDays));
  }
  const cells = new Array(n).fill(0);
  for (const t of times) {
    const idx = Math.min(n - 1, Math.floor((t - first) / (bucketDays * MS_DAY)));
    cells[idx] += 1;
  }
  return { cells, first, last, spanDays, bucketDays, total: times.length };
}

// The heat strip: one row of cells, intensity ∝ mentions in that bucket.
// role="img" + an aria-label stating the finding in words (e.g. "FCL: 3
// mentions across 4 days"); no animation; a labelled .chart-empty when there
// is nothing to plot.
function HeatStrip({ symbol, mentions }) {
  const h = heatCells(mentions);
  if (!h) {
    return (
      <div className="chart-empty">
        No mention dates recorded for {symbol} — nothing to plot.
      </div>
    );
  }
  const maxCell = Math.max(1, ...h.cells);
  const cellW = 8;
  const gap = 2;
  const height = 18;
  const width = h.cells.length * cellW + (h.cells.length - 1) * gap;
  const dayIso = (offsetDays) => new Date(h.first + offsetDays * MS_DAY).toISOString();
  const countWord = (c) => `${c} mention${c === 1 ? "" : "s"}`;

  return (
    <div className="heat-strip-wrap">
      <svg
        className="heat-strip"
        width={width}
        height={height}
        role="img"
        aria-label={`${symbol}: ${h.total} mention${h.total === 1 ? "" : "s"} across ${h.spanDays} day${h.spanDays === 1 ? "" : "s"}`}
      >
        {h.cells.map((c, i) => {
          const x = i * (cellW + gap);
          const startIso = dayIso(i * h.bucketDays);
          const endIso = dayIso((i + 1) * h.bucketDays);
          const span = h.bucketDays > 1 ? `${fmtDate(startIso)} – ${fmtDate(endIso)}` : fmtDate(startIso);
          return (
            <rect
              key={i}
              x={x}
              width={cellW}
              height={height}
              className={`heat-cell${c > 0 ? " on" : ""}`}
              opacity={c > 0 ? 0.2 + 0.8 * (c / maxCell) : 1}
            >
              <title>{`${span} — ${countWord(c)}`}</title>
            </rect>
          );
        })}
      </svg>
      <div className="strip-axes">
        <span className="strip-date">{fmtDate(dayIso(0))}</span>
        <span className="strip-gloss">
          {h.total} mention{h.total === 1 ? "" : "s"} across {h.spanDays} day{h.spanDays === 1 ? "" : "s"} · darker is denser
        </span>
        <span className="strip-date">{fmtDate(dayIso(h.spanDays))}</span>
      </div>
    </div>
  );
}

// Adaptive price precision, same rule as the shared Num: 2dp under ₹100, 0dp
// above. Never rounds a stated price into silence, never invents one.
function fmtPrice(value) {
  if (value === null || value === undefined) return null;
  const n = Number(value);
  const dp = Math.abs(n) < 100 ? 2 : 0;
  return n.toLocaleString("en-IN", {
    minimumFractionDigits: dp,
    maximumFractionDigits: dp,
  });
}

// Who actually bought it, from taken_by (the earliest position opened after
// the symbol's first mention). The price comes from the positions payload and
// is omitted — never invented — when it is not there. Money was risked here:
// this line is the screen's one --risk.
function FollowThrough({ g, positions }) {
  if (!g.taken_by) {
    return <p className="follow-through none">nobody has bought it</p>;
  }
  const t = g.taken_by;
  const pos = (positions || []).find(
    (p) => p.symbol === g.symbol && p.handle === t.handle && p.opened_at === t.opened_at
  );
  const price = fmtPrice(pos && pos.entry);
  return (
    <p className="follow-through">
      Who actually bought it:{" "}
      <span className="took">
        @{t.handle}
        {price ? ` at ₹${price}` : ""}
      </span>{" "}
      on {fmtDate(t.opened_at)}
    </p>
  );
}

export default function Ideas({ onNavigate }) {
  const { data, error } = useApi(fetchIdeas, []);
  // Positions serve the ticker leaderboard and the follow-through prices —
  // fetched once, shared down. If the positions fetch fails, the ideas list
  // still stands on its own; only the board and the prices degrade.
  const pos = useApi(() => fetchPositions({ limit: 200 }), []);

  if (error) return <ErrorBox error={error} />;
  if (!data) return <Loading />;

  // Order: trader count desc, then symbol (the API already sorts this way;
  // re-sorting client-side keeps the screen honest if the payload order ever
  // changes).
  const groups = [...data.ideas].sort(
    (a, b) =>
      (b.trader_count || 0) - (a.trader_count || 0) || a.symbol.localeCompare(b.symbol)
  );
  const maxMentions = Math.max(1, ...data.themes.map((t) => t.mention_count || 0));

  return (
    <>
      <p className="page-lede">
        What the tracked traders are watching, who else named the same thing, and
        whether anybody actually took it.
      </p>

      <TickerBoard
        ideasPayload={data}
        positionsData={pos.data}
        positionsError={pos.error}
        onNavigate={onNavigate}
      />

      <Panel title="By symbol" right={`${groups.length} symbol${groups.length === 1 ? "" : "s"}`}>
        {groups.length === 0 && (
          <p className="empty">
            No watch ideas captured yet — none of the tracked posts have been
            classified as one. Watch ideas come from W2 classification of the
            captured corpus.
          </p>
        )}
        {groups.map((g) => (
          <div className="idea-group" key={g.symbol}>
            <div className="idea-head">
              <span className="idea-symbol">{g.symbol}</span>
              <span className="idea-meta mono">
                {g.trader_count} trader{g.trader_count === 1 ? "" : "s"} · first{" "}
                {fmtDate(g.first_seen)}
              </span>
            </div>

            <HeatStrip symbol={g.symbol} mentions={g.mentions} />

            {g.mentions.map((m) => (
              <div className="mention" key={m.id}>
                <KindChip kind={m.kind} />
                <span className="m-handle">@{m.handle}</span>
                <span className="m-date">{fmtDate(m.stated_at)}</span>
                {m.trigger_text ? (
                  // Quoted verbatim — the exact phrasing is the content.
                  <span className="m-quote">"{m.trigger_text}"</span>
                ) : (
                  <span className="m-quote-none">no trigger quote recorded</span>
                )}
              </div>
            ))}

            <FollowThrough g={g} positions={pos.data?.positions} />
          </div>
        ))}
        <div className="footnote">
          This screen reports what was said and who acted, not who was right.
          Whether the stock moved is deliberately not shown — a different
          question.
        </div>
      </Panel>

      <Panel title="Themes">
        {data.themes.length === 0 && (
          <p className="ideas-empty">
            No themes captured yet — themes come from W2 classification of the
            captured corpus.
          </p>
        )}
        {data.themes.map((t) => (
          <div className="theme-row" key={t.name}>
            <span className="theme-name">{t.name}</span>
            <span className="theme-count mono">{t.mention_count}</span>
            <span
              className="theme-meter"
              role="img"
              aria-label={`${t.name}: ${t.mention_count} mention${t.mention_count === 1 ? "" : "s"}`}
            >
              <span
                className="theme-meter-fill"
                style={{ width: `${(t.mention_count / maxMentions) * 100}%` }}
              />
            </span>
            <span className="theme-meta mono">
              {t.symbols.length} symbol{t.symbols.length === 1 ? "" : "s"} · last{" "}
              {fmtDate(t.last_seen)}
            </span>
          </div>
        ))}
      </Panel>
    </>
  );
}