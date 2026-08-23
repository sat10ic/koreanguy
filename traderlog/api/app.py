"""TraderLog read API.

Endpoints match design/CONTRACTS.md §8 exactly. Every payload carries `is_mock`
so a screen can say out loud that it is showing seeded data.

Shape stability matters more than content here: later waves replace mock rows
with real ones, and no response shape may change when they do. Removing the mock
data must only make arrays empty.

Run:  python traderlog/run_api.py       (http://127.0.0.1:8100)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from traderlog.db import connect, count, init_db, now_iso
from traderlog.llm.reconcile import apply_accepted_link

app = FastAPI(title="TraderLog", version="0.1.0")

# Vite dev server runs on 5180; the built app is served from this origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5180", "http://127.0.0.1:5180"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_DIST = Path(__file__).resolve().parents[1] / "ui" / "dist"


def _rows(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    conn = connect()
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def _jload(value: Any, fallback: Any = None) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return fallback


def _is_mock() -> bool:
    conn = connect()
    try:
        return count(conn, "posts", "is_mock = 1") > 0
    finally:
        conn.close()


@app.get("/api/health")
def health() -> dict:
    conn = connect()
    try:
        counts = {
            "traders": count(conn, "traders"),
            "posts": count(conn, "posts"),
            "positions": count(conn, "positions"),
            "review_open": count(conn, "review_queue", "status = 'open'"),
        }
        mock = count(conn, "posts", "is_mock = 1") > 0
    finally:
        conn.close()
    return {"ok": True, "ts": now_iso(), "counts": counts, "is_mock": mock}


# ---------------------------------------------------------------------------
# FEED
# ---------------------------------------------------------------------------

@app.get("/api/feed")
def feed(
    limit: int = 60,
    handle: str | None = None,
    kind: str | None = None,
    min_confidence: float | None = None,
    unresolved: bool = False,
) -> dict:
    where, params = ["1=1"], []
    if handle:
        where.append("p.handle = ?"); params.append(handle)
    if kind:
        if kind == "unclassified":
            where.append("c.kind IS NULL")
        else:
            where.append("c.kind = ?"); params.append(kind)
    if min_confidence is not None:
        where.append("c.confidence >= ?"); params.append(min_confidence)
    if unresolved:
        where.append(
            "EXISTS (SELECT 1 FROM position_events e "
            "JOIN positions pos ON pos.position_id = e.position_id "
            "WHERE e.post_id = p.post_id "
            "AND COALESCE(json_array_length(pos.unresolved_json), 0) > 0)"
        )
    params.append(limit)

    # Relationship columns are selected here on purpose. Adds, stop moves and
    # exits are almost always the author replying to their own entry post -- that
    # is why ingest polls /with_replies at all -- so a feed that drops
    # conversation_id and in_reply_to cannot render the thing the tool exists to
    # show. Fields are ADDITIVE: `posts` stays a flat list and the UI groups it,
    # so no existing consumer breaks.
    select = """SELECT p.post_id, p.handle, p.ts_ist, p.text, p.url, p.deleted_at,
                   p.conversation_id, p.in_reply_to,
                   c.kind, c.confidence, c.symbols,
                   (SELECT COUNT(*) FROM post_media m WHERE m.post_id = p.post_id) AS media_count,
                   b.stance,
                   r.xp_value, r.xp_band, r.mbi_day_color, r.warning_day
            FROM posts p
            LEFT JOIN post_class    c ON c.post_id = p.post_id
            LEFT JOIN breadth_notes b ON b.post_id = p.post_id
            LEFT JOIN regime_daily  r ON r.trade_date = substr(p.ts_ist, 1, 10)"""

    posts = _rows(
        f"{select} WHERE {' AND '.join(where)} ORDER BY p.ts_ist DESC LIMIT ?",
        tuple(params),
    )

    # LIMIT and the filters both cut mid-thread, which would leave replies whose
    # root is absent -- rendering an exit with no visible entry. Pull the missing
    # roots back in so every thread on screen is whole.
    have = {p["post_id"] for p in posts}
    missing = {
        p["conversation_id"] for p in posts
        if p.get("conversation_id") and p["conversation_id"] not in have
    }
    if missing:
        marks = ",".join("?" * len(missing))
        posts += _rows(f"{select} WHERE p.post_id IN ({marks})", tuple(missing))

    # Thread metadata, computed once over the assembled set.
    threads: dict[str, list] = {}
    for p in posts:
        threads.setdefault(p.get("conversation_id") or p["post_id"], []).append(p)
    for conv, members in threads.items():
        members.sort(key=lambda m: m["ts_ist"])
        last_ts = members[-1]["ts_ist"]
        for i, m in enumerate(members):
            m["thread_size"] = len(members)
            m["thread_pos"] = i
            m["thread_last_ts"] = last_ts
            m["is_root"] = m["in_reply_to"] is None or m["post_id"] == conv
    # Threads newest-activity first, but posts WITHIN a thread oldest first:
    # a position has to read entry -> add -> stop -> exit, top down. Two passes,
    # relying on sort stability, because the two keys run in opposite directions.
    posts.sort(key=lambda m: m["ts_ist"])
    posts.sort(key=lambda m: m["thread_last_ts"], reverse=True)

    for p in posts:
        p["symbols"] = _jload(p.get("symbols"), [])
        ev = _rows(
            """SELECT e.kind, e.price, e.qty_pct, e.position_id, pos.symbol,
                      pos.unresolved_json, pos.evidence_json,
                      (SELECT price FROM position_events x
                        WHERE x.position_id = e.position_id AND x.kind IN ('sl_set','sl_move')
                          AND x.seq < e.seq ORDER BY x.seq DESC LIMIT 1) AS prev_stop
                 FROM position_events e
                 JOIN positions pos ON pos.position_id = e.position_id
                WHERE e.post_id = ? ORDER BY e.seq LIMIT 1""",
            (p["post_id"],),
        )
        if ev:
            e = ev[0]
            e["unresolved"] = _jload(e.pop("unresolved_json"), [])
            e["evidence"] = _jload(e.pop("evidence_json"), {})
            p["event"] = e
        else:
            p["event"] = None
        regime = {
            "xp_value": p.pop("xp_value", None),
            "xp_band": p.pop("xp_band", None),
            "mbi_day_color": p.pop("mbi_day_color", None),
            "warning_day": p.pop("warning_day", None),
        }
        # Null when no regime row exists for that date, so the UI can tell
        # "market was red" apart from "we have no breadth data for that day".
        p["regime"] = regime if regime["xp_value"] is not None else None
    return {"posts": posts, "is_mock": _is_mock()}


@app.get("/api/review")
def review() -> dict:
    items = _rows(
        "SELECT id, kind, question, proposed_json, confidence, ingested_at "
        "FROM review_queue WHERE status = 'open' ORDER BY confidence DESC"
    )
    for it in items:
        proposed = _jload(it.pop("proposed_json"), {}) or {}
        it["reasoning"] = proposed.get("reasoning", "")
        it["alternatives"] = proposed.get("alternatives", [])
        it["proposed_event"] = proposed.get("proposed_event")
    return {"items": items, "is_mock": _is_mock()}


@app.post("/api/review/{item_id}")
def resolve_review(item_id: int, decision: str = "accepted") -> dict:
    if decision not in {"accepted", "rejected"}:
        raise HTTPException(400, "decision must be 'accepted' or 'rejected'")
    conn = connect()
    try:
        with conn:
            item = conn.execute("SELECT * FROM review_queue WHERE id = ?", (item_id,)).fetchone()
            if item is None:
                raise HTTPException(404, "no review item with that id")
            if item["status"] != "open":
                return {
                    "ok": True, "id": item_id, "status": item["status"],
                    "applied": item["status"] == "accepted", "already_resolved": True,
                }
            if decision == "accepted":
                try:
                    proposal = json.loads(item["proposed_json"] or "")
                except (TypeError, ValueError) as exc:
                    raise HTTPException(400, "review item has invalid proposed_json") from exc
                if item["kind"] != "link_event" or not isinstance(proposal, dict):
                    raise HTTPException(400, "review item cannot be applied as a link event")
                # Reconciliation is the sole writer of positions and events.
                apply_accepted_link(conn, proposal)
            conn.execute(
                "UPDATE review_queue SET status = ?, resolved_by = 'ui', resolved_at = ? WHERE id = ?",
                (decision, now_iso(), item_id),
            )
    finally:
        conn.close()
    return {"ok": True, "id": item_id, "status": decision, "applied": decision == "accepted", "already_resolved": False}


# ---------------------------------------------------------------------------
# TRADERS
# ---------------------------------------------------------------------------

@app.get("/api/traders")
def traders() -> dict:
    rows = _rows(
        """SELECT t.handle, t.display_name, t.tier, t.tags, t.active, t.last_seen_ts,
                  (SELECT COUNT(*) FROM posts p WHERE p.handle = t.handle) AS posts,
                  (SELECT COUNT(*) FROM positions x
                    WHERE x.handle = t.handle AND x.status != 'closed') AS open_positions,
                  (SELECT COUNT(*) FROM positions x
                    WHERE x.handle = t.handle AND x.status = 'closed') AS closed_positions,
                  s.median_hold_days, s.stated_win_rate, s.avg_r, s.preach_score
             FROM traders t
             LEFT JOIN trader_style s
                    ON s.handle = t.handle
                   AND s.as_of = (SELECT MAX(as_of) FROM trader_style z WHERE z.handle = t.handle)
            ORDER BY t.tier, t.handle"""
    )
    for r in rows:
        r["tags"] = _jload(r.get("tags"), [])
    return {"traders": rows, "is_mock": _is_mock()}


@app.get("/api/traders/{handle}")
def trader_detail(handle: str) -> dict:
    base = _rows("SELECT * FROM traders WHERE handle = ?", (handle,))
    if not base:
        raise HTTPException(404, f"no trader {handle!r}")
    t = base[0]
    t["tags"] = _jload(t.get("tags"), [])

    style_rows = _rows(
        "SELECT * FROM trader_style WHERE handle = ? ORDER BY as_of DESC LIMIT 1", (handle,)
    )
    style = style_rows[0] if style_rows else None
    if style:
        style["sector_tilt"] = _jload(style.pop("sector_tilt_json"), {})
        style["entry_type"] = _jload(style.pop("entry_type_json"), {})

    positions = _rows(
        "SELECT position_id, symbol, status, opened_at, closed_at, net_result_pct, "
        "holding_days, confidence, unresolved_json FROM positions "
        "WHERE handle = ? ORDER BY opened_at DESC", (handle,),
    )
    for p in positions:
        p["unresolved"] = _jload(p.pop("unresolved_json"), [])

    return {
        "trader": t, "style": style,
        "open": [p for p in positions if p["status"] != "closed"],
        "closed": [p for p in positions if p["status"] == "closed"],
        "is_mock": _is_mock(),
    }


# ---------------------------------------------------------------------------
# LEDGER
# ---------------------------------------------------------------------------

@app.get("/api/positions")
def positions(handle: str | None = None, symbol: str | None = None,
              status: str | None = None, min_confidence: float | None = None,
              limit: int = 200) -> dict:
    where, params = ["1=1"], []
    for col, val in (("handle", handle), ("symbol", symbol), ("status", status)):
        if val:
            where.append(f"{col} = ?"); params.append(val)
    if min_confidence is not None:
        where.append("confidence >= ?"); params.append(min_confidence)
    params.append(limit)
    rows = _rows(
        f"""SELECT position_id, handle, symbol, status, opened_at, closed_at,
                   net_result_pct, holding_days, confidence, state_json, unresolved_json
              FROM positions WHERE {' AND '.join(where)}
             ORDER BY opened_at DESC LIMIT ?""",
        tuple(params),
    )
    for r in rows:
        state = _jload(r.pop("state_json"), {}) or {}
        r["unresolved"] = _jload(r.pop("unresolved_json"), [])
        r["entry"] = (state.get("entries") or [{}])[0].get("price")
        r["adds"] = state.get("adds") or []
        r["stop"] = (state.get("stop") or {}).get("price")
        r["exit"] = (state.get("exits") or [{}])[0].get("price") if state.get("exits") else None

        # Dated interior events, so the LEDGER timeline can mark adds and stop
        # moves rather than only entry and exit. state_json's `adds` carry no
        # date, and the detail endpoint is one-position-at-a-time, so without
        # this the lead graphic is a plain bar with nothing happening inside it.
        # A stop move is classified up or down by comparing to the previous
        # stop -- a stop that moved UP is the trader taking risk off, which is
        # the single most informative mark on the chart.
        r["events"] = [
            {"at": e["stated_at"][:10], "kind": _event_mark(e["kind"], e["direction"])}
            for e in _rows(
                """SELECT e.kind, e.stated_at,
                          CASE WHEN e.price > (
                              SELECT x.price FROM position_events x
                               WHERE x.position_id = e.position_id
                                 AND x.kind IN ('sl_set','sl_move')
                                 AND x.seq < e.seq
                            ORDER BY x.seq DESC LIMIT 1
                          ) THEN 'up' ELSE 'down' END AS direction
                     FROM position_events e
                    WHERE e.position_id = ?
                      AND e.kind IN ('add','sl_move','exit','partial_exit')
                    ORDER BY e.seq""",
                (r["position_id"],),
            )
            if e.get("stated_at")
        ]
    return {"positions": rows, "is_mock": _is_mock()}


def _event_mark(kind: str, direction: str | None) -> str:
    """position_events.kind -> the PositionBars marker vocabulary."""
    if kind == "sl_move":
        return "sl_up" if direction == "up" else "sl_down"
    if kind in ("exit", "partial_exit"):
        return "exit"
    return "add"


@app.get("/api/positions/{position_id}")
def position_detail(position_id: str) -> dict:
    base = _rows("SELECT * FROM positions WHERE position_id = ?", (position_id,))
    if not base:
        raise HTTPException(404, "no such position")
    p = base[0]
    p["state"] = _jload(p.pop("state_json"), {})
    p["evidence"] = _jload(p.pop("evidence_json"), {})
    p["unresolved"] = _jload(p.pop("unresolved_json"), [])

    events = _rows(
        """SELECT e.id, e.kind, e.price, e.qty_pct, e.stated_at, e.seq, e.confidence,
                  e.post_id, po.text AS post_text, po.url AS post_url
             FROM position_events e
             LEFT JOIN posts po ON po.post_id = e.post_id
            WHERE e.position_id = ? ORDER BY e.seq""",
        (position_id,),
    )
    media = _rows(
        """SELECT m.post_id, m.idx, m.local_path, m.vision_json
             FROM post_media m
             JOIN position_events e ON e.post_id = m.post_id
            WHERE e.position_id = ? GROUP BY m.post_id, m.idx""",
        (position_id,),
    )
    for m in media:
        m["vision"] = _jload(m.pop("vision_json"), None)
    return {"position": p, "events": events, "media": media, "is_mock": _is_mock()}


# ---------------------------------------------------------------------------
# BREADTH
# ---------------------------------------------------------------------------

@app.get("/api/breadth")
def breadth(days: int = 90) -> dict:
    history = _rows(
        "SELECT * FROM regime_daily ORDER BY trade_date DESC LIMIT ?", (days,)
    )
    history.reverse()
    today = history[-1] if history else None

    stances = _rows(
        """SELECT b.trade_date, b.handle, b.stance, b.post_id,
                  r.xp_value, r.xp_band, r.mbi_day_color, r.warning_day
             FROM breadth_notes b
             LEFT JOIN regime_daily r ON r.trade_date = b.trade_date
            ORDER BY b.trade_date DESC, b.handle LIMIT 40"""
    )
    # A deliberately crude three-way match: RISK-ON vs GREEN, RISK-OFF vs RED,
    # NEUTRAL vs WHITE. It measures agreement with one particular breadth model,
    # NOT whether the trader was right. The UI must say so.
    agree_map = {"risk_on": "GREEN", "risk_off": "RED", "neutral": "WHITE"}
    for s in stances:
        expected = agree_map.get(s.get("stance") or "")
        s["agreed"] = (
            None if not s.get("mbi_day_color") or expected is None
            else s["mbi_day_color"] == expected
        )

    tally: dict[str, list[int]] = {}
    for s in stances:
        if s["agreed"] is None:
            continue
        t = tally.setdefault(s["handle"], [0, 0])
        t[0] += 1 if s["agreed"] else 0
        t[1] += 1
    agreement = [
        {"handle": h, "agreed_pct": round(100 * a / n, 1) if n else None, "n": n}
        for h, (a, n) in sorted(tally.items(), key=lambda kv: -kv[1][1])
    ]

    return {
        "today": today, "history": history, "stances": stances,
        "agreement": agreement, "is_mock": _is_mock(),
    }


# ---------------------------------------------------------------------------
# IDEAS
# ---------------------------------------------------------------------------

@app.get("/api/ideas")
def ideas() -> dict:
    raw = _rows(
        """SELECT w.id, w.symbol, w.handle, w.kind, w.trigger_text, w.level,
                  w.stated_at, w.status, w.post_id
             FROM watch_ideas w ORDER BY w.symbol, w.stated_at"""
    )
    grouped: dict[str, dict[str, Any]] = {}
    for r in raw:
        g = grouped.setdefault(
            r["symbol"], {"symbol": r["symbol"], "mentions": [], "traders": set(),
                          "first_seen": r["stated_at"], "taken_by": None}
        )
        g["mentions"].append(r)
        g["traders"].add(r["handle"])
        g["first_seen"] = min(g["first_seen"], r["stated_at"])

    for symbol, g in grouped.items():
        # Follow-through: did anyone actually take it after flagging it?
        taken = _rows(
            "SELECT handle, opened_at, symbol FROM positions "
            "WHERE symbol = ? AND opened_at >= ? ORDER BY opened_at LIMIT 1",
            (symbol, g["first_seen"]),
        )
        g["taken_by"] = taken[0] if taken else None
        g["trader_count"] = len(g.pop("traders"))

    out = sorted(grouped.values(), key=lambda g: (-g["trader_count"], g["symbol"]))

    themes = _rows("SELECT * FROM themes ORDER BY mention_count DESC")
    for t in themes:
        t["symbols"] = _jload(t.pop("symbols_json"), [])
    return {"ideas": out, "themes": themes, "is_mock": _is_mock()}


# ---------------------------------------------------------------------------
# LIBRARY
# ---------------------------------------------------------------------------

# Below this many linked trades a preach score is worse than no score: it looks
# like a finding when it is noise. WIREFRAMES.md §6 requires the UI to say so.
PREACH_MIN_N = 10


@app.get("/api/library")
def library() -> dict:
    items = _rows(
        """SELECT e.id, e.handle, e.title, e.principle_text, e.topic_tags,
                  e.stated_at, e.post_id, p.url AS post_url
             FROM edu_items e LEFT JOIN posts p ON p.post_id = e.post_id
            ORDER BY e.stated_at DESC"""
    )
    topics: set[str] = set()
    for it in items:
        tags = _jload(it.pop("topic_tags"), []) or []
        it["topics"] = tags
        topics.update(tags)

        links = _rows(
            "SELECT verdict, position_id, evidence FROM edu_links WHERE edu_id = ?", (it["id"],)
        )
        followed = sum(1 for x in links if x["verdict"] == "followed")
        violated = sum(1 for x in links if x["verdict"] == "violated")
        na = sum(1 for x in links if x["verdict"] == "na")
        scored = followed + violated
        it["practice"] = {
            "followed": followed, "violated": violated, "na": na, "n": scored,
            "min_n": PREACH_MIN_N,
            "enough": scored >= PREACH_MIN_N,
            "score_pct": round(100 * followed / scored, 1) if scored >= PREACH_MIN_N else None,
            "violations": [x for x in links if x["verdict"] == "violated"],
        }
    return {"items": items, "topics": sorted(topics), "is_mock": _is_mock()}


# ---------------------------------------------------------------------------
# media + static
# ---------------------------------------------------------------------------

@app.get("/api/media/{post_id}/{idx}")
def media(post_id: str, idx: int):
    rows = _rows(
        "SELECT local_path, is_mock FROM post_media WHERE post_id = ? AND idx = ?",
        (post_id, idx),
    )
    if not rows:
        raise HTTPException(404, "no such media")
    if rows[0]["is_mock"]:
        # Seeded rows point at a path that does not exist on purpose -- there is
        # no real chart image to serve, and inventing one would be a lie.
        raise HTTPException(404, "mock media has no file")
    path = Path(__file__).resolve().parents[1] / "data" / "media" / rows[0]["local_path"]
    if not path.exists():
        raise HTTPException(404, "archived media file missing")
    return FileResponse(path)


if _DIST.exists():
    app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="ui")


def main() -> None:
    import uvicorn
    init_db()
    uvicorn.run(app, host="127.0.0.1", port=8100)
