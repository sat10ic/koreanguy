// LIBRARY — REDESIGN_SCOUTING_WIRE.md §4.5 (wave 2026-08-24, S7-owned).
// The QUOTE IS THE HERO at full size: the principle verbatim, attributed,
// dated, linked to the original post. Beneath it, a --raised block sums up the
// record in WORDS built from practice (followed/violated/na) with every
// violation citing its position — evidence visible, never behind a toggle.
// Below the minimum sample (n < min_n, 10) the block dims to --ink-4 and no
// percentage is rendered at all.
import React from "react";
import { fetchLibrary } from "../api.js";
import { ErrorBox, Loading, Panel, fmtDate, useApi } from "../components/ui.jsx";
import "../styles/library.css";

function PracticeBlock({ p }) {
  // Below the minimum sample, show no percentage at all. A preach score
  // computed on a handful of trades is worse than no score, because it looks
  // like a finding when it is noise. The wording is protected copy.
  if (!p.enough) {
    const word = `${p.n} trade${p.n === 1 ? "" : "s"}`;
    const link = p.n === 1 ? "links" : "link";
    return (
      <div className="practice-block below-min">
        <p className="practice-words">
          Not enough to say yet — only {word} {link} to this. We won't score it
          until 10.
        </p>
      </div>
    );
  }
  // n >= min_n here, so "trades" is always plural in this branch.
  let words = `Followed in ${p.followed} of ${p.n} trades where he named a stop.`;
  if (p.violated > 0) {
    words += ` Of the ${p.violated} he didn't, each one is cited below.`;
  }
  return (
    <div className="practice-block">
      <p className="practice-words">{words}</p>
      {p.na > 0 && (
        <p className="practice-words na">
          In {p.na} more linked trade{p.na === 1 ? "" : "s"} no stop was named,
          so {p.na === 1 ? "it doesn't" : "they don't"} count either way.
        </p>
      )}
      <p className="practice-score">
        Score: <span className="mono">{p.score_pct}%</span> of {p.n}.
      </p>
      {p.violations.length > 0 && (
        <ul className="violations">
          {p.violations.map((v) => (
            <li key={v.position_id}>
              <span className="mono vpos">position {v.position_id}</span>
              <span className="v-evidence">{v.evidence}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function Library() {
  const { data, error } = useApi(fetchLibrary, []);
  const [topic, setTopic] = React.useState(null);

  if (error) return <ErrorBox error={error} />;
  if (!data) return <Loading />;

  // First topic is pre-selected when topics exist (the screen's existing
  // behavior); the chips switch the filter. edu_items is empty today, so the
  // honest compact line below carries the screen.
  const active = topic || data.topics[0] || null;
  const items = active
    ? data.items.filter((i) => (i.topics || []).includes(active))
    : data.items;

  return (
    <>
      <p className="page-lede">
        What they teach, quoted exactly, next to whether their own logged trades
        followed it.
      </p>

      <Panel title="Library" right={`${items.length} item${items.length === 1 ? "" : "s"}`}>
        {data.topics.length > 0 && (
          <div className="topic-chips" role="group" aria-label="topic">
            {data.topics.map((t) => (
              <button
                key={t}
                type="button"
                className={`topic-chip${t === active ? " active" : ""}`}
                aria-pressed={t === active}
                onClick={() => setTopic(t)}
              >
                {t}
              </button>
            ))}
          </div>
        )}

        {data.items.length === 0 && (
          <p className="lib-empty">
            No educational posts captured yet — educational items come from W2
            classification of the captured corpus.
          </p>
        )}
        {data.items.length > 0 && items.length === 0 && (
          <p className="lib-empty">Nothing under this topic.</p>
        )}

        {items.map((it) => (
          <article className="lib-item" key={it.id}>
            {/* Verbatim. Paraphrase drift would corrupt the very thing
                practice-vs-preach measures. */}
            <blockquote className="quote-hero">{it.principle_text}</blockquote>
            <p className="quote-by">
              <span className="q-handle">@{it.handle}</span>
              <span className="q-date">{fmtDate(it.stated_at)}</span>
              {it.post_url && (
                <a
                  className="q-link"
                  href={it.post_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  the post ↗
                </a>
              )}
            </p>
            <PracticeBlock p={it.practice} />
          </article>
        ))}
      </Panel>
    </>
  );
}