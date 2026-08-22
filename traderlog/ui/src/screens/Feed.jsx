// FEED — WIREFRAMES.md §1
import React from "react";
import { fetchFeed, fetchReview, fetchTraders, resolveReview } from "../api.js";
import {
  Chip, Conf, ErrorBox, Loading, Num, Panel, fmtDate, fmtTime, useApi,
} from "../components/ui.jsx";

const KINDS = ["trade_event", "breadth", "watch_idea", "theme", "education", "noise"];

function ReviewQueue({ items, onResolve }) {
  if (!items?.length) return null;
  return (
    <Panel
      title={`Review queue — ${items.length} open`}
      tone="alert"
      right="work you owe the tool"
    >
      <p className="review-why" style={{ marginTop: 0 }}>
        These could not be resolved automatically. One click each. There is no
        bulk accept — the confidence floor exists because these are genuinely
        ambiguous.
      </p>
      {items.map((it) => (
        <div className="review-item" key={it.id}>
          <div className="post-head">
            <Chip kind="deleted">{it.kind.replace(/_/g, " ")}</Chip>
            <Conf value={it.confidence} />
          </div>
          <p className="review-q">{it.question}</p>
          {it.reasoning && <div className="review-why">why: {it.reasoning}</div>}
          {it.alternatives?.map((a, i) => (
            <div className="review-but" key={i}>
              but: {a}
            </div>
          ))}
          <div className="review-actions">
            <button className="btn btn-yes" onClick={() => onResolve(it.id, "accepted")}>
              ✓ attach
            </button>
            <button className="btn btn-no" onClick={() => onResolve(it.id, "rejected")}>
              ✗ no
            </button>
          </div>
        </div>
      ))}
    </Panel>
  );
}

function EventStrip({ event }) {
  if (!event) return null;
  const stopMoved = event.kind === "sl_move" || (event.prev_stop && event.kind === "sl_set");
  return (
    <div className="event-strip">
      <span className="event-symbol">{event.symbol}</span>
      <span className="event-kind">{event.kind.replace(/_/g, " ")}</span>
      {event.price !== null && <Num value={event.price} prefix="₹" />}
      {event.qty_pct != null && <span className="mono">{event.qty_pct}%</span>}
      {stopMoved && event.prev_stop != null && (
        <span>
          SL <Num value={event.prev_stop} /> → <Num value={event.price} />
        </span>
      )}
      {event.unresolved?.length > 0 && (
        <span className="unstated">{event.unresolved.join(" · ")}</span>
      )}
    </div>
  );
}

function StanceStrip({ post }) {
  if (!post.stance) return null;
  const r = post.regime;
  return (
    <div className="event-strip stance-strip">
      <span className="event-kind">stance {post.stance.replace("_", "-")}</span>
      {r ? (
        <span>
          that day: XP <span className="mono">{r.xp_value?.toFixed(1)}</span> {r.xp_band} · MBI{" "}
          <span className={`color-${r.mbi_day_color}`}>{r.mbi_day_color}</span>
          {r.warning_day ? " · warning ⚠" : ""}
        </span>
      ) : (
        <span className="unstated">no breadth data for that day</span>
      )}
    </div>
  );
}

export default function Feed() {
  const [handle, setHandle] = React.useState("");
  const [kind, setKind] = React.useState("");
  const [openEvidence, setOpenEvidence] = React.useState(null);
  const [reviewNonce, setReviewNonce] = React.useState(0);

  const { data: feed, error } = useApi(() => fetchFeed({ handle, kind, limit: 60 }), [handle, kind]);
  const { data: review } = useApi(fetchReview, [reviewNonce]);
  const { data: roster } = useApi(fetchTraders, []);

  async function onResolve(id, decision) {
    await resolveReview(id, decision);
    setReviewNonce((n) => n + 1);
  }

  return (
    <>
      <p className="page-lede">
        Everything the tracked traders posted, newest first, with what each post
        was understood to mean.
      </p>
      <ErrorBox error={error} />

      <Panel title="Filters">
        <div className="filters">
          <label>
            trader
            <select value={handle} onChange={(e) => setHandle(e.target.value)}>
              <option value="">all</option>
              {roster?.traders?.map((t) => (
                <option key={t.handle} value={t.handle}>
                  {t.handle}
                </option>
              ))}
            </select>
          </label>
          <label>
            kind
            <select value={kind} onChange={(e) => setKind(e.target.value)}>
              <option value="">all</option>
              {KINDS.map((k) => (
                <option key={k} value={k}>
                  {k.replace(/_/g, " ")}
                </option>
              ))}
            </select>
          </label>
        </div>
      </Panel>

      <ReviewQueue items={review?.items} onResolve={onResolve} />

      <Panel title="Posts" right={feed ? `${feed.posts.length} shown` : ""}>
        {!feed && !error && <Loading />}
        {feed?.posts?.length === 0 && (
          <p className="empty">
            No posts yet. Ingest has not run — that is W1. See{" "}
            <code>traderlog/HANDOFF.md</code>.
          </p>
        )}
        {feed?.posts?.map((p) => (
          <article className={`post${p.deleted_at ? " post-deleted" : ""}`} key={p.post_id}>
            <div className="post-head">
              <span className="post-handle">@{p.handle}</span>
              <span className="post-time">
                {fmtDate(p.ts_ist)} {fmtTime(p.ts_ist)} IST
              </span>
              {p.deleted_at ? (
                <Chip kind="deleted">deleted {fmtTime(p.deleted_at)}</Chip>
              ) : (
                <Chip kind={p.kind}>{(p.kind || "unclassified").replace(/_/g, " ")}</Chip>
              )}
              <Conf value={p.confidence} />
            </div>

            <p className="post-text">{p.text}</p>

            {p.deleted_at && (
              <div className="deleted-note">
                ⚠ this post was removed by its author. Kept on purpose — traders
                delete losers, and dropping them would bias every derived metric.
              </div>
            )}

            <EventStrip event={p.event} />
            <StanceStrip post={p} />

            <div className="post-meta">
              {p.media_count > 0 && <span>🖼 {p.media_count} image attached · </span>}
              <a href={p.url} target="_blank" rel="noreferrer">
                thread ↗
              </a>
              {p.event?.evidence && Object.keys(p.event.evidence).length > 0 && (
                <>
                  {" · "}
                  <button
                    className="linkish"
                    onClick={() =>
                      setOpenEvidence(openEvidence === p.post_id ? null : p.post_id)
                    }
                  >
                    why?
                  </button>
                </>
              )}
            </div>

            {openEvidence === p.post_id && (
              <dl className="evidence">
                {Object.entries(p.event.evidence).map(([field, pid]) => (
                  <React.Fragment key={field}>
                    <dt>{field}</dt>
                    <dd>← post {pid}</dd>
                  </React.Fragment>
                ))}
              </dl>
            )}
          </article>
        ))}
      </Panel>
    </>
  );
}
