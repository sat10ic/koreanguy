// FEED — WIREFRAMES.md §1, the W3c evidence desk.
// Two-column composition: the thread workspace is primary; filters and
// compact operating context form the secondary rail. Every filter, the
// review queue, and all evidence behavior are unchanged -- this is
// composition, not a data change.
import React from "react";
import { fetchFeed, fetchReview, fetchTraders, resolveReview } from "../api.js";
import {
  Chip, Conf, ErrorBox, Loading, Num, Panel, fmtDate, fmtTime, useApi,
} from "../components/ui.jsx";
import "../styles/thread.css";

const KINDS = ["trade_event", "breadth", "watch_idea", "theme", "education", "noise"];
// F18: 9 of 12 real posts classify as kind:null and render as "UNCLASSIFIED"
// -- the majority state -- but the enum dropdown had no way to select it.
// "unclassified" is the API sentinel for rows without a post_class record.
const UNCLASSIFIED = "unclassified";
const CONF_OPTIONS = [0, 0.5, 0.7, 0.9];

// `pendingId` is the review item whose decision POST is in flight. Policy:
// while ANY decision is pending, both buttons on EVERY review item are
// disabled -- one decision at a time, never a second concurrent POST (a
// double click must not submit twice). `onResolve` re-checks the guard as
// belt-and-braces.
function ReviewQueue({ items, onResolve, pendingId, resolveError }) {
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
      {resolveError && (
        <div className="error-box" role="alert">
          <strong>Could not submit this decision.</strong> {resolveError} The
          item is still open — try again.
        </div>
      )}
      {items.map((it) => (
        <div
          className="review-item"
          key={it.id}
          aria-busy={pendingId === it.id ? "true" : "false"}
        >
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
            <button
              className="btn btn-yes"
              disabled={pendingId !== null}
              onClick={() => onResolve(it.id, "accepted")}
            >
              ✓ attach
            </button>
            <button
              className="btn btn-no"
              disabled={pendingId !== null}
              onClick={() => onResolve(it.id, "rejected")}
            >
              ✗ no
            </button>
          </div>
        </div>
      ))}
    </Panel>
  );
}

function EventStrip({ event, unresolvedOpen, onToggleUnresolved, onNavigate }) {
  if (!event) return null;
  const stopMoved = event.kind === "sl_move" || (event.prev_stop && event.kind === "sl_set");
  return (
    <div className="event-strip">
      {/* C2.2: this event became a position in the ledger -- jump straight
          to it, open, rather than making the user go find it by symbol. */}
      {event.position_id ? (
        <button
          type="button"
          className="xlink event-symbol"
          onClick={() => onNavigate?.("LEDGER", { position: event.position_id })}
        >
          {event.symbol}
        </button>
      ) : (
        <span className="event-symbol">{event.symbol}</span>
      )}
      <span className="event-kind">{event.kind.replace(/_/g, " ")}</span>
      {event.price !== null && <Num value={event.price} prefix="₹" />}
      {event.qty_pct != null && <span className="mono">{event.qty_pct}%</span>}
      {stopMoved && event.prev_stop != null && (
        <span>
          SL <Num value={event.prev_stop} /> → <Num value={event.price} />
        </span>
      )}
      {/* W3c: long unresolved copy must not dominate the row. The count is
          the summary; the complete strings expand below on disclosure --
          never paraphrased, never dropped. */}
      {event.unresolved?.length > 0 && (
        <button
          type="button"
          className="unres-toggle"
          aria-expanded={unresolvedOpen}
          onClick={onToggleUnresolved}
        >
          {event.unresolved.length} unresolved {unresolvedOpen ? "▴" : "▾"}
        </button>
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

// Secondary rail: filters plus compact operating context. The context rows
// read existing /api/traders fields; the Desk counts are computed client-side
// over the loaded /api/feed page. No invented metrics, no new payload.
function Rail({ handle, setHandle, kind, setKind, confMin, setConfMin,
                unresolvedOnly, setUnresolvedOnly, roster, posts }) {
  const threads = new Set(posts.map((p) => p.conversation_id || p.post_id)).size;
  const events = posts.filter((p) => p.event).length;
  return (
    <aside className="feed-rail">
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
              <option value={UNCLASSIFIED}>unclassified</option>
            </select>
          </label>
          <label>
            confidence
            <select
              value={confMin}
              onChange={(e) => setConfMin(e.target.value === "" ? "" : Number(e.target.value))}
            >
              <option value="">all</option>
              {CONF_OPTIONS.map((c) => (
                <option key={c} value={c}>{`≥${c.toFixed(1)}`}</option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className={`filter-toggle${unresolvedOnly ? " active" : ""}`}
            aria-pressed={unresolvedOnly}
            onClick={() => setUnresolvedOnly((v) => !v)}
          >
            unresolved{unresolvedOnly ? " ✕" : ""}
          </button>
        </div>
      </Panel>

      {roster?.traders?.length > 0 && (
        <Panel title="Traders on desk" right={`${roster.traders.length} tracked`}>
          <div className="desk-rows">
            {roster.traders.map((t) => (
              // I4: this used to be a static div beside a working trader
              // <select> with the same four handles -- looked clickable,
              // wasn't. Now a real button wired to the same filter state.
              <button
                type="button"
                className={`desk-row${handle === t.handle ? " active" : ""}`}
                aria-pressed={handle === t.handle}
                key={t.handle}
                onClick={() => setHandle(handle === t.handle ? "" : t.handle)}
              >
                <span className="d-handle">@{t.handle}</span>
                <Chip kind={t.tier}>{t.tier}</Chip>
                <span className="d-posts">{t.posts} posts</span>
              </button>
            ))}
          </div>
        </Panel>
      )}

      {posts.length > 0 && (
        <Panel title="Desk">
          <div className="desk-counts">
            <div className="desk-count">
              <span className="v">{posts.length}</span>
              <span className="k">posts shown</span>
            </div>
            <div className="desk-count">
              <span className="v">{threads}</span>
              <span className="k">threads</span>
            </div>
            <div className="desk-count">
              <span className="v">{events}</span>
              <span className="k">events joined</span>
            </div>
          </div>
        </Panel>
      )}
    </aside>
  );
}

export default function Feed({ refreshHealth, onNavigate }) {
  const [handle, setHandle] = React.useState("");
  const [kind, setKind] = React.useState("");
  const [confMin, setConfMin] = React.useState("");
  const [unresolvedOnly, setUnresolvedOnly] = React.useState(false);
  const [openEvidence, setOpenEvidence] = React.useState(null);
  const [openUnresolved, setOpenUnresolved] = React.useState(null);
  const [reviewNonce, setReviewNonce] = React.useState(0);
  const [pendingId, setPendingId] = React.useState(null);
  const [resolveError, setResolveError] = React.useState(null);

  // reviewNonce is a dependency of BOTH fetches on purpose. Bumping it after a
  // decision must refresh the review list AND the posts: an accepted standalone
  // event only becomes visible here through the /api/feed event join, so a
  // posts refetch that skips the nonce leaves the card without its event strip.
  const { data: feed, error } = useApi(
    () => fetchFeed({
      handle, kind, min_confidence: confMin, unresolved: unresolvedOnly || undefined, limit: 60,
    }),
    [handle, kind, confMin, unresolvedOnly, reviewNonce]
  );
  const { data: review } = useApi(fetchReview, [reviewNonce]);
  const { data: roster } = useApi(fetchTraders, []);

  async function onResolve(id, decision) {
    if (pendingId !== null) return; // disabled buttons are the lock; this is the bolt
    setResolveError(null);
    setPendingId(id);
    try {
      await resolveReview(id, decision);
      // Same-session refresh, no page reload: review list + posts via the
      // nonce, and the health-derived FEED badge via the App prop.
      setReviewNonce((n) => n + 1);
      refreshHealth?.();
    } catch (e) {
      setResolveError(String(e?.message || e));
    } finally {
      setPendingId(null);
    }
  }

  const posts = feed?.posts || [];
  const hasFilters = Boolean(handle || kind || confMin !== "" || unresolvedOnly);

  return (
    <>
      <p className="page-lede">
        Everything the tracked traders posted, newest first, with what each post
        was understood to mean.
      </p>
      <ErrorBox error={error} />

      <div className="feed-layout">
        <div className="feed-primary">
          <ReviewQueue
            items={review?.items}
            onResolve={onResolve}
            pendingId={pendingId}
            resolveError={resolveError}
          />

          <Panel title="Posts" right={feed ? `${posts.length} shown` : ""}>
            {!feed && !error && <Loading />}
            {feed?.posts?.length === 0 && !hasFilters && (
              <p className="empty">
                No posts yet. Nothing has been pulled in from the tracked traders yet.
              </p>
            )}
            {feed && posts.length === 0 && hasFilters && (
              <p className="empty">No posts match these filters.</p>
            )}
            {posts.map((p) => (
              <article
                className={[
                  "post",
                  p.deleted_at ? "post-deleted" : "",
                  // Threads are the unit of meaning here: adds, stop moves and exits
                  // are the author replying to their own entry. Replies are indented
                  // under their root and share a spine so a position reads as one
                  // object rather than four unrelated posts.
                  p.is_root ? "post-root" : "post-reply",
                  p.thread_size > 1 && p.thread_pos === p.thread_size - 1 ? "thread-last" : "",
                ].filter(Boolean).join(" ")}
                key={p.post_id}
              >
                <div className="post-head">
                  {/* C2.1: jump to this trader's TRADERS profile. */}
                  <button
                    type="button"
                    className="xlink post-handle"
                    onClick={() => onNavigate?.("TRADERS", { handle: p.handle })}
                  >
                    @{p.handle}
                  </button>
                  <span className="post-time">
                    {fmtDate(p.ts_ist)} {fmtTime(p.ts_ist)} IST
                  </span>
                  {p.thread_size > 1 && (
                    <span className="thread-pos mono" title="position within this thread">
                      {p.thread_pos + 1}/{p.thread_size}
                    </span>
                  )}
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

                <EventStrip
                  event={p.event}
                  unresolvedOpen={openUnresolved === p.post_id}
                  onToggleUnresolved={() =>
                    setOpenUnresolved(openUnresolved === p.post_id ? null : p.post_id)
                  }
                  onNavigate={onNavigate}
                />
                {openUnresolved === p.post_id && p.event?.unresolved?.length > 0 && (
                  <ul className="unres-full">
                    {p.event.unresolved.map((u, i) => (
                      <li key={i}>{u}</li>
                    ))}
                  </ul>
                )}
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
        </div>

        <Rail
          handle={handle}
          setHandle={setHandle}
          kind={kind}
          setKind={setKind}
          confMin={confMin}
          setConfMin={setConfMin}
          unresolvedOnly={unresolvedOnly}
          setUnresolvedOnly={setUnresolvedOnly}
          roster={roster}
          posts={posts}
        />
      </div>
    </>
  );
}
