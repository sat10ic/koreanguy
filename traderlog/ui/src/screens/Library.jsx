// LIBRARY — WIREFRAMES.md §6
import React from "react";
import { fetchLibrary } from "../api.js";
import { Bar, ErrorBox, Loading, Panel, fmtDate, useApi } from "../components/ui.jsx";

function Practice({ p }) {
  // Below the minimum, show no percentage at all. A preach score computed on two
  // trades is worse than no score, because it looks like a finding.
  if (!p.enough) {
    return (
      <div className="practice">
        <span className="practice-none">
          not enough linked trades yet — {p.n} of a {p.min_n}-trade minimum
        </span>
      </div>
    );
  }
  return (
    <div className="practice">
      <div className="practice-counts">
        <span>
          followed <strong className="mono">{p.followed}</strong>
        </span>
        <span>
          violated <strong className="mono">{p.violated}</strong>
        </span>
        <span>
          n/a <strong className="mono">{p.na}</strong>
        </span>
      </div>
      <div className="metric-row">
        <Bar pct={p.score_pct} tone={p.score_pct >= 70 ? "green" : "amber"} width={220} />
        <span className="mono">{p.score_pct}%</span>
      </div>
      {p.violations.length > 0 && (
        <div className="violations">
          violations: {p.violations.map((v) => v.position_id.slice(0, 8)).join(", ")}
          {" — "}
          {p.violations[0].evidence}
        </div>
      )}
    </div>
  );
}

export default function Library() {
  const { data, error } = useApi(fetchLibrary, []);
  const [topic, setTopic] = React.useState(null);

  if (error) return <ErrorBox error={error} />;
  if (!data) return <Loading />;

  const active = topic || data.topics[0] || null;
  const items = active ? data.items.filter((i) => i.topics.includes(active)) : data.items;

  return (
    <>
      <p className="page-lede">
        What they teach, quoted exactly, next to whether their own logged trades
        followed it.
      </p>

      <Panel title="By topic">
        {data.topics.length === 0 && <p className="empty">No educational posts captured yet.</p>}
        <div className="topic-tabs">
          {data.topics.map((t) => (
            <button
              key={t}
              className={`topic-tab${t === active ? " active" : ""}`}
              onClick={() => setTopic(t)}
            >
              {t}
            </button>
          ))}
        </div>
      </Panel>

      <Panel
        title={
          active
            ? `${active} · ${items.length} item${items.length === 1 ? "" : "s"}`
            : "All items"
        }
      >
        {items.length === 0 && <p className="empty">Nothing under this topic.</p>}
        {items.map((it) => (
          <article className="edu-item" key={it.id}>
            <div className="post-head">
              <span className="post-handle">@{it.handle}</span>
              <span className="post-time">{fmtDate(it.stated_at)}</span>
            </div>
            {/* Verbatim quote. Paraphrase drift would corrupt the very thing
                practice-vs-preach measures. */}
            <blockquote className="edu-quote">"{it.principle_text}"</blockquote>
            <div className="post-meta">
              {it.post_url && (
                <a href={it.post_url} target="_blank" rel="noreferrer">
                  ↗ post
                </a>
              )}
            </div>
            <div className="sub-label" style={{ marginTop: 10 }}>
              Practised?
            </div>
            <Practice p={it.practice} />
          </article>
        ))}
      </Panel>
    </>
  );
}
