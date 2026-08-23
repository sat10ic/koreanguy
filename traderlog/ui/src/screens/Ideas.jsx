// IDEAS — WIREFRAMES.md §5
// Grouped by SYMBOL rather than by trader: three people naming the same stock in
// a week is the finding, and a per-trader list hides it.
// TickerBoard sits ABOVE the By-symbol panel: the same signal at one glance —
// how many tracked traders are actually in a ticker (entered / holding /
// exited) versus how many only mentioned it. Mentions never read as positions.
import React from "react";
import { fetchIdeas, fetchPositions } from "../api.js";
import { Bar, Chip, ErrorBox, Loading, Num, Panel, fmtDate, useApi } from "../components/ui.jsx";

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

// The leaderboard panel, rendered FIRST inside IDEAS. Positions are the one
// extra fetch nothing else on this screen needed; the ideas payload already
// comes from Ideas()'s own fetch and is passed down so /api/ideas is not
// fetched twice.
function TickerBoard({ ideasPayload, onNavigate }) {
  const { data, error } = useApi(() => fetchPositions({ limit: 200 }), []);
  if (error) return <ErrorBox error={error} />;
  // Still loading positions: show the compact loading line, never a false
  // "no positions yet" state.
  if (!data) return <Loading />;

  const rows = buildTickerRows(data.positions || [], ideasPayload);

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
    <Panel title="Ticker leaderboard" right={`${rows.length} ticker${rows.length === 1 ? "" : "s"}`}>
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

export default function Ideas({ onNavigate }) {
  const { data, error } = useApi(fetchIdeas, []);
  if (error) return <ErrorBox error={error} />;
  if (!data) return <Loading />;

  const maxMentions = Math.max(1, ...data.themes.map((t) => t.mention_count || 0));

  return (
    <>
      <p className="page-lede">
        What the tracked traders are watching, who else named the same thing, and
        whether anybody actually took it.
      </p>

      <TickerBoard ideasPayload={data} onNavigate={onNavigate} />

      <Panel title="By symbol" right={`${data.ideas.length} names`}>
        {data.ideas.length === 0 && (
          <p className="empty">
            No watch ideas captured yet — none of the tracked posts have been
            classified as one. Watch ideas are produced by W2 classification
            of the captured corpus.
          </p>
        )}
        {data.ideas.map((g) => (
          <div className="idea-group" key={g.symbol}>
            <div className="idea-head">
              <span className="idea-symbol">{g.symbol}</span>
              <span className="idea-meta">
                {g.trader_count} trader{g.trader_count === 1 ? "" : "s"} · first{" "}
                {fmtDate(g.first_seen)}
              </span>
            </div>

            {g.mentions.map((m) => (
              <div className="mention" key={m.id}>
                <span className="m-handle">@{m.handle}</span>
                <span className="m-date">{fmtDate(m.stated_at)}</span>
                <Chip kind="watch_idea">{m.kind.toLowerCase()}</Chip>
                {/* Quoted verbatim — the exact phrasing is the content. */}
                <span className="m-quote">"{m.trigger_text}"</span>
              </div>
            ))}

            {g.taken_by ? (
              <div className="followthrough taken">
                → @{g.taken_by.handle} took it {fmtDate(g.taken_by.opened_at)}
              </div>
            ) : (
              <div className="followthrough none">→ nobody has taken it</div>
            )}
          </div>
        ))}
        <div className="footnote">
          Whether the stock actually moved is deliberately not shown here. That
          needs price data, which isn't wired in yet, and it's a different claim —
          this screen reports what was said and who acted, not who was right.
        </div>
      </Panel>

      <Panel title="Themes">
        {data.themes.length === 0 && (
          <p className="empty">
            No themes captured yet — themes are produced by W2 classification
            of the captured corpus.
          </p>
        )}
        {data.themes.map((t) => (
          <div className="metric-row" key={t.name}>
            <span className="mk">{t.name}</span>
            <span className="mv mono">{t.mention_count}</span>
            <Bar pct={(t.mention_count / maxMentions) * 100} tone="amber" />
            <span className="unstated">
              {t.symbols.length} symbols · last {fmtDate(t.last_seen)}
            </span>
          </div>
        ))}
      </Panel>
    </>
  );
}