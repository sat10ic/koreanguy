// IDEAS — WIREFRAMES.md §5
// Grouped by SYMBOL rather than by trader: three people naming the same stock in
// a week is the finding, and a per-trader list hides it.
import React from "react";
import { fetchIdeas } from "../api.js";
import { Bar, Chip, ErrorBox, Loading, Num, Panel, fmtDate, useApi } from "../components/ui.jsx";

export default function Ideas() {
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

      <Panel title="By symbol" right={`${data.ideas.length} names`}>
        {data.ideas.length === 0 && (
          <p className="empty">No watch ideas captured yet — classification is W2.</p>
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
                <Chip kind="watch_idea">{m.kind}</Chip>
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
          needs price data (W4), and it is a different claim — this screen reports
          what was said and who acted, not who was right.
        </div>
      </Panel>

      <Panel title="Themes">
        {data.themes.length === 0 && <p className="empty">no themes captured yet</p>}
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
