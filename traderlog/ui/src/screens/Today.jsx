// TODAY — was FEED. REDESIGN_SCOUTING_WIRE.md §4.1 + HANDOFF_scouting_wire (S3).
// A newswire, not a scroll: every post lands in one of four COMPUTED bands
// (Rule 2 — banding derives from payload fields, never an editorial judgement),
// in fixed order: Money moved, Names to watch, Background, Removed. Each band
// carries a kicker and ONE line explaining why these are grouped, not what the
// group contains. The review queue sits ABOVE the bands ("work the human owes
// the tool"), one decision at a time, W3 behaviour unchanged: same
// /api/review/{id} POST, disabled/aria-busy while pending, no second concurrent
// decision, inline error, in-session badge refresh through `refreshHealth`.
//
// Glosses (Rule 1): plain-English sentences derived from payload fields only.
// Never a bare number, never a trader-record claim (trader_style has too few
// closed positions today — record glosses are OMITTED, not invented, §11).
import React from "react";
import { fetchFeed, fetchReview, fetchTraders, resolveReview } from "../api.js";
import { Conf, ErrorBox, Loading, Num, fmtDate, fmtTime, useApi } from "../components/ui.jsx";
import "../styles/today.css";

const KINDS = ["trade_event", "breadth", "watch_idea", "theme", "education", "noise"];
// "unclassified" is the API sentinel for rows without a post_class record.
const UNCLASSIFIED = "unclassified";
const CONF_OPTIONS = [0, 0.5, 0.7, 0.9];
const PAGE_SIZE = 30;

// One line per band explaining WHY these are grouped (not a description).
// Sharp-colleague voice: direct, specific, unhedged. <=13 words each.
const BAND_WHY = {
  money: "Money on the table is the only thing that's verifiable.",
  watch: "A name to watch — with or without a trigger level.",
  background: "Everything else — commentary, themes, principles, banter.",
  removed: "People delete losers, and forgetting them would flatter everyone's record.",
};
const BAND_ORDER = [
  { key: "money", label: "MONEY MOVED" },
  { key: "watch", label: "NAMES TO WATCH" },
  { key: "background", label: "BACKGROUND" },
  { key: "removed", label: "REMOVED" },
];

// Rule 2: band assignment is computed, never editorial. Removed always wins
// (a deleted post is its own band, always kept); then money moved (a
// trade_event WITH a stated price/stop — the feed's event join carries it);
// then watch ideas; everything the rules cannot place goes to Background.
function bandOf(post) {
  if (post.deleted_at != null) return "removed";
  if (post.kind === "trade_event" && post.event && post.event.price != null) return "money";
  if (post.kind === "watch_idea") return "watch";
  return "background";
}

function threadKey(post) {
  return post.relationship_known === false ? post.post_id : post.conversation_id || post.post_id;
}

// Preserve thread identity while banding. `posts` arrives thread-ordered from
// mergeFeedPage (threads newest-activity first, members oldest first), so a
// partition preserves order; members of one thread that land in one band stay
// contiguous, and only a self-reply whose root is directly above it in the SAME
// band gets the 1px spine. A thread split across bands loses the spine but
// keeps its position chip — no fake root styling, ever.
function bucketByBand(posts) {
  const out = { money: [], watch: [], background: [], removed: [] };
  for (const post of posts) {
    const band = bandOf(post);
    const list = out[band];
    const prev = list[list.length - 1];
    const isReply = !!prev && post.thread_pos > 0 && threadKey(prev.post) === threadKey(post);
    list.push({ post, isReply });
  }
  return out;
}

// Re-group loaded posts by thread and order threads newest-activity-first with
// members oldest-first inside — ported unchanged from the W3 feed so a position
// reads entry -> add -> stop -> exit top down and thread members are never
// separated by a page boundary.
function orderLoadedPosts(posts) {
  const threads = new Map();
  for (const post of posts) {
    const threadId = threadKey(post);
    const members = threads.get(threadId) || [];
    members.push(post);
    threads.set(threadId, members);
  }

  return [...threads.entries()]
    .map(([threadId, members]) => {
      members.sort((a, b) =>
        a.ts_ist.localeCompare(b.ts_ist) || a.post_id.localeCompare(b.post_id)
      );
      const lastTs = members[members.length - 1].ts_ist;
      return {
        threadId,
        lastTs,
        members: members.map((post, index) => ({
          ...post,
          thread_size: members.length,
          thread_pos: index,
          thread_last_ts: lastTs,
        })),
      };
    })
    .sort((a, b) => b.lastTs.localeCompare(a.lastTs) || b.threadId.localeCompare(a.threadId))
    .flatMap((thread) => thread.members);
}

function mergeFeedPage(previous, page) {
  const byPostId = new Map(previous?.posts?.map((post) => [post.post_id, post]));
  page.posts.forEach((post) => byPostId.set(post.post_id, post));
  return {
    ...page,
    posts: orderLoadedPosts([...byPostId.values()]),
    loadedBaseCount: (previous?.loadedBaseCount || 0) + page.pagination.returned,
  };
}

// ---------------------------------------------------------------------------
// Review queue — the human's owed work, above the bands. NOT a band.
// Ported from the W3 feed with behaviour unchanged: `pendingId` is the item
// whose decision POST is in flight; while ANY decision is pending both buttons
// on EVERY item are disabled — one decision at a time, never a second
// concurrent POST. `onResolve` re-checks the guard as belt-and-braces.
// ---------------------------------------------------------------------------
function ReviewQueue({ items, onResolve, pendingId, resolveError }) {
  if (!items?.length) return null;
  return (
    <section className="td-queue" aria-label="Review queue">
      <header className="td-queue-head">
        <h2 className="kicker td-kicker">Review queue</h2>
        <span className="td-queue-count mono">{items.length} open</span>
        <span className="td-queue-owed">work you owe the tool</span>
      </header>
      <p className="td-queue-why">
        These could not be resolved automatically. One click each. There is no bulk
        accept — the confidence floor exists because these are genuinely ambiguous.
      </p>
      {resolveError && (
        <div className="error-box" role="alert">
          <strong>Could not submit this decision.</strong> {resolveError} The item is
          still open — try again.
        </div>
      )}
      {items.map((it) => (
        <div
          className="review-item"
          key={it.id}
          aria-busy={pendingId === it.id ? "true" : "false"}
        >
          <div className="td-review-top">
            <span className="td-review-kind">{it.kind.replace(/_/g, " ")}</span>
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
              type="button"
              className="btn-yes td-btn"
              disabled={pendingId !== null}
              onClick={() => onResolve(it.id, "accepted")}
            >
              ✓ attach
            </button>
            <button
              type="button"
              className="btn-no td-btn"
              disabled={pendingId !== null}
              onClick={() => onResolve(it.id, "rejected")}
            >
              ✗ no
            </button>
          </div>
        </div>
      ))}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Row furniture
// ---------------------------------------------------------------------------

// Every numeral is mono/tabular via .mono + Num(). Prices use Num()'s adaptive
// precision (2dp under ₹100, 0dp above, ₹ prefix). Symbols are live links to
// the SYMBOL landing page; handles link to TRADERS.
function SymLink({ symbol, onNavigate }) {
  if (!symbol) return null;
  return (
    <button
      type="button"
      className="td-symlink mono"
      onClick={() => onNavigate?.("SYMBOL", { symbol })}
    >
      {symbol}
    </button>
  );
}

// qty_pct is stated as a percent (25 = a quarter) or a fraction (0.25). Only
// the common fractions get words; anything else is omitted rather than
// rendered as a bare number (Rule 1).
function qtyInWords(raw) {
  if (raw == null) return null;
  const q = Number(raw);
  const pct = q > 1 ? q : q * 100;
  const close = (t) => Math.abs(pct - t) < 0.5;
  if (close(100)) return "the whole position";
  if (close(75)) return "three-quarters of the position";
  if (close(66.67)) return "two-thirds of the position";
  if (close(50)) return "half the position";
  if (close(33.33)) return "a third of the position";
  if (close(25)) return "a quarter of the position";
  return null;
}

// The per-row band label, derived from payload fields only.
function rowLabel(post, band) {
  if (band === "money") {
    return (post.event?.kind || post.kind || "trade_event").replace(/_/g, " ").toUpperCase();
  }
  if (band === "removed") return "REMOVED";
  return (post.kind || "unclassified").replace(/_/g, " ").toUpperCase();
}

// The plain-English gloss (Rule 1). Sentences, never bare numbers; record
// glosses omitted entirely (trader_style is below the 10-closed threshold).
function renderGloss(post, band, onNavigate) {
  if (band === "removed") {
    return (
      <>
        Up {fmtTime(post.ts_ist)}, gone by {fmtTime(post.deleted_at)}.
      </>
    );
  }

  const e = post.event;
  const sym = e?.symbol || post.symbols?.[0] || null;
  const symNode = <SymLink symbol={sym} onNavigate={onNavigate} />;
  const priceNode = (v) => (v != null ? <Num value={v} prefix="₹" /> : null);
  // A money-moved row whose linked position never stated a stop.
  const unstatedStop = e?.unresolved?.some((u) => /stop/i.test(String(u)))
    ? " ⚠ He never said where he'd get out."
    : "";

  let base;
  switch (post.kind) {
    case "trade_event":
      switch (e?.kind) {
        case "entry":
          base =
            e.price != null
              ? <>Put money on {symNode} at {priceNode(e.price)}.</>
              : <>Put money on {symNode}.</>;
          break;
        case "add":
          base = e.price != null ? <>Added at {priceNode(e.price)}.</> : <>Added.</>;
          break;
        case "partial_exit":
          base =
            e.price != null
              ? <>Took profit at {priceNode(e.price)} — holds the rest.</>
              : <>Took profit — holds the rest.</>;
          break;
        case "exit": {
          const qty = qtyInWords(e.qty_pct);
          base =
            e.price != null ? (
              qty ? (
                <>
                  Booked {symNode} at {priceNode(e.price)} — {qty}.
                </>
              ) : (
                <>
                  Booked {symNode} at {priceNode(e.price)}.
                </>
              )
            ) : (
              <>Booked {symNode}{qty ? ` — ${qty}.` : "."}</>
            );
          break;
        }
        case "sl_set":
          base = <>Stated a stop at {priceNode(e.price)}.</>;
          break;
        case "sl_move":
          base =
            e.prev_stop != null ? (
              <>
                Moved the stop to {priceNode(e.price)} — was at {priceNode(e.prev_stop)}.
              </>
            ) : (
              <>Moved the stop to {priceNode(e.price)}.</>
            );
          break;
        default:
          base =
            e?.price != null ? (
              <>
                Put money on {symNode} at {priceNode(e.price)}.
              </>
            ) : sym ? (
              <>Put money on {symNode}.</>
            ) : (
              "A trade — no price stated."
            );
      }
      break;
    case "watch_idea":
      base = sym ? <>A name to watch — {symNode}.</> : "A name to watch.";
      break;
    case "breadth":
      base = "His read on the market that day.";
      break;
    case "theme":
      base = "A theme, not a trade.";
      break;
    case "education":
      base = "A principle, not a trade.";
      break;
    case "noise":
      base = "Not about the market.";
      break;
    default:
      base = "Not yet classified.";
  }
  return (
    <>
      {base}
      {unstatedStop}
    </>
  );
}

function PostRow({ post, band, isReply, onNavigate }) {
  const deleted = band === "removed";
  return (
    <article
      className={[
        "td-row",
        band === "money" ? "td-money" : "",
        deleted ? "td-row-deleted" : "",
        isReply ? "td-reply" : "",
      ].filter(Boolean).join(" ")}
      data-band={band}
      key={post.post_id}
    >
      <div className="td-row-head">
        {/* Rule 3: --risk marks money that was risked. Only here. */}
        {band === "money" && <span className="td-risk-mark" aria-hidden="true" />}
        <span className="td-bandlabel">{rowLabel(post, band)}</span>
        <button
          type="button"
          className="td-handle"
          onClick={() => onNavigate?.("TRADERS", { handle: post.handle })}
        >
          @{post.handle}
        </button>
        <span className="td-time mono">
          {fmtDate(post.ts_ist)} {fmtTime(post.ts_ist)}
        </span>
        {post.thread_size > 1 && (
          <span className="td-thread-pos mono" title="position within this thread">
            {post.thread_pos + 1}/{post.thread_size}
          </span>
        )}
      </div>

      {/* Verbatim, never paraphrased, never truncated. */}
      <p className="td-text">{post.text}</p>

      {deleted && (
        <p className="td-deleted-note">
          ⚠ this post was removed by its author. Kept on purpose — traders delete
          losers, and dropping them would bias every derived metric.
        </p>
      )}

      <p className="td-gloss">{renderGloss(post, band, onNavigate)}</p>

      {!deleted && (
        <div className="td-meta">
          {post.media_count > 0 && <span className="mono">{post.media_count} archived</span>}
          <a href={post.url} target="_blank" rel="noreferrer">
            {post.relationship_known === false ? "post ↗" : "thread ↗"}
          </a>
        </div>
      )}
    </article>
  );
}

// ---------------------------------------------------------------------------
// Screen
// ---------------------------------------------------------------------------

export default function Today({ refreshHealth, onNavigate }) {
  const [handle, setHandle] = React.useState("");
  const [kind, setKind] = React.useState("");
  const [confMin, setConfMin] = React.useState("");
  const [unresolvedOnly, setUnresolvedOnly] = React.useState(false);
  const [reviewNonce, setReviewNonce] = React.useState(0);
  const [pendingId, setPendingId] = React.useState(null);
  const [resolveError, setResolveError] = React.useState(null);
  const [feed, setFeed] = React.useState(null);
  const [feedError, setFeedError] = React.useState(null);
  const [loadingOlder, setLoadingOlder] = React.useState(false);
  const loadedDepthRef = React.useRef(PAGE_SIZE);
  const previousFilterRef = React.useRef(null);
  const requestRef = React.useRef(0);
  const filterKey = JSON.stringify({ handle, kind, confMin, unresolvedOnly });
  const feedFilters = {
    handle,
    kind,
    min_confidence: confMin,
    unresolved: unresolvedOnly || undefined,
  };

  // A review decision can change a post's joined event, so the feed refetches
  // on reviewNonce — same contract as the W3 feed.
  React.useEffect(() => {
    const filterChanged = previousFilterRef.current !== filterKey;
    previousFilterRef.current = filterKey;
    const targetDepth = filterChanged ? PAGE_SIZE : loadedDepthRef.current;
    const requestId = ++requestRef.current;
    let cancelled = false;

    if (filterChanged) setFeed(null);
    setLoadingOlder(false);
    setFeedError(null);

    async function loadPages() {
      let offset = 0;
      let assembled = null;
      try {
        do {
          const page = await fetchFeed({ ...feedFilters, limit: PAGE_SIZE, offset });
          if (cancelled || requestId !== requestRef.current) return;
          assembled = mergeFeedPage(assembled, page);
          offset = page.pagination.next_offset;
        } while (offset !== null && assembled.loadedBaseCount < targetDepth);
        if (!cancelled && requestId === requestRef.current) {
          loadedDepthRef.current = assembled?.loadedBaseCount || 0;
          setFeed(assembled);
        }
      } catch (e) {
        if (!cancelled && requestId === requestRef.current) {
          setFeedError(String(e?.message || e));
        }
      }
    }

    loadPages();
    return () => {
      cancelled = true;
    };
  }, [filterKey, reviewNonce]);

  const { data: review } = useApi(fetchReview, [reviewNonce]);
  const { data: roster } = useApi(fetchTraders, []);

  async function loadOlder() {
    if (!feed?.pagination?.has_more || loadingOlder) return;
    const requestId = ++requestRef.current;
    const offset = feed.pagination.next_offset;
    setLoadingOlder(true);
    setFeedError(null);
    try {
      const page = await fetchFeed({ ...feedFilters, limit: PAGE_SIZE, offset });
      if (requestId !== requestRef.current) return;
      setFeed((current) => {
        if (!current || current.pagination.next_offset !== offset) return current;
        const merged = mergeFeedPage(current, page);
        loadedDepthRef.current = merged.loadedBaseCount;
        return merged;
      });
    } catch (e) {
      if (requestId === requestRef.current) setFeedError(String(e?.message || e));
    } finally {
      if (requestId === requestRef.current) setLoadingOlder(false);
    }
  }

  async function onResolve(id, decision) {
    if (pendingId !== null) return; // disabled buttons are the lock; this is the bolt
    setResolveError(null);
    setPendingId(id);
    try {
      await resolveReview(id, decision);
      setReviewNonce((n) => n + 1);
      refreshHealth?.();
    } catch (e) {
      setResolveError(String(e?.message || e));
    } finally {
      setPendingId(null);
    }
  }

  const posts = feed?.posts || [];
  const buckets = React.useMemo(() => bucketByBand(posts), [posts]);
  const hasFilters = Boolean(handle || kind || confMin !== "" || unresolvedOnly);
  const bands = BAND_ORDER.filter((b) => buckets[b.key].length > 0);

  return (
    <>
      <p className="page-lede">
        A newswire from the tracked traders — ranked by what it cost them to say:
        money first, names second, everything else last.
      </p>
      <ErrorBox error={feedError} />

      <ReviewQueue
        items={review?.items}
        onResolve={onResolve}
        pendingId={pendingId}
        resolveError={resolveError}
      />

      <div className="td-filters" role="toolbar" aria-label="Post filters">
        <label className="td-filter">
          <span className="td-filter-label">trader</span>
          <select value={handle} onChange={(e) => setHandle(e.target.value)}>
            <option value="">all</option>
            {roster?.traders?.map((t) => (
              <option key={t.handle} value={t.handle}>
                {t.handle}
              </option>
            ))}
          </select>
        </label>
        <label className="td-filter">
          <span className="td-filter-label">kind</span>
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
        <label className="td-filter">
          <span className="td-filter-label">confidence</span>
          <select
            value={confMin}
            onChange={(e) => setConfMin(e.target.value === "" ? "" : Number(e.target.value))}
          >
            <option value="">all</option>
            {CONF_OPTIONS.map((c) => (
              <option key={c} value={c}>
                {`≥${c.toFixed(1)}`}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          className={`td-toggle${unresolvedOnly ? " active" : ""}`}
          aria-pressed={unresolvedOnly}
          onClick={() => setUnresolvedOnly((v) => !v)}
        >
          unresolved{unresolvedOnly ? " ✕" : ""}
        </button>
      </div>

      {!feed && !feedError && <Loading />}
      {feed && posts.length === 0 && !hasFilters && (
        <p className="empty td-empty">
          No posts yet. Nothing has been pulled in from the tracked traders yet.
        </p>
      )}
      {feed && posts.length === 0 && hasFilters && (
        <p className="empty td-empty">No posts match these filters.</p>
      )}

      {bands.map((band) => (
        <section className="td-band" key={band.key} data-band={band.key}>
          <header className="td-band-head">
            <h2 className="kicker td-kicker">{band.label}</h2>
            <p className="td-band-why">{BAND_WHY[band.key]}</p>
          </header>
          <div className="td-rows">
            {buckets[band.key].map(({ post, isReply }) => (
              <PostRow
                key={post.post_id}
                post={post}
                band={band.key}
                isReply={isReply}
                onNavigate={onNavigate}
              />
            ))}
          </div>
        </section>
      ))}

      {feed && (
        <div className="td-footer">
          <span className="td-count">
            <span className="mono">{feed.loadedBaseCount}</span> of{" "}
            <span className="mono">{feed.pagination.total}</span> posts
          </span>
          {feed.pagination?.has_more && (
            <button
              type="button"
              className="td-btn"
              disabled={loadingOlder}
              aria-busy={loadingOlder}
              onClick={loadOlder}
            >
              {loadingOlder ? "loading older posts…" : "Load older posts"}
            </button>
          )}
        </div>
      )}
    </>
  );
}