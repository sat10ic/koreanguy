"""Seed traderlog.db with plausible MOCK data so the UI renders end to end.

Why mock data in a real database rather than fixtures hardcoded in JSX: later
waves fill in real logic behind endpoints that already exist and already return
the right SHAPE. A model building W2 can see exactly what the UI expects.

Everything written here carries is_mock = 1. `/api/health` reports it, every
payload carries it, and the UI shows a banner. A tool that looks real while
showing invented data is the exact failure this project exists to avoid.

    python traderlog/seed_mock.py            # seed
    python traderlog/seed_mock.py --clear    # remove all mock rows, keep real ones

The trader handles below are INVENTED. They are not real accounts, and none of
the posts, prices or results are real. Replace them with the actual roster at W1.
"""
from __future__ import annotations

import hashlib
import json
import random
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from traderlog.db import connect, init_db, now_iso  # noqa: E402

RNG = random.Random(20260823)  # fixed seed: same fixture for every model, every run

MOCK_TABLES = [
    "edu_links", "position_events", "post_class", "post_media", "breadth_notes",
    "watch_ideas", "edu_items", "review_queue", "trader_style", "positions",
    "posts", "themes", "regime_daily", "symbol_attention", "traders",
]

# Child-before-parent purge plan.  The parent joins remove legacy rows whose
# is_mock flag was omitted but whose source post/position/trader is mock.
_MOCK_DELETE_WHERE = {
    "edu_links": (
        "is_mock = 1 OR edu_id IN (SELECT id FROM edu_items WHERE is_mock = 1 "
        "OR post_id IN (SELECT post_id FROM posts WHERE is_mock = 1)) "
        "OR position_id IN (SELECT position_id FROM positions WHERE is_mock = 1 "
        "OR handle IN (SELECT handle FROM traders WHERE is_mock = 1))"
    ),
    "position_events": (
        "is_mock = 1 OR position_id IN (SELECT position_id FROM positions WHERE is_mock = 1 "
        "OR handle IN (SELECT handle FROM traders WHERE is_mock = 1)) "
        "OR post_id IN (SELECT post_id FROM posts WHERE is_mock = 1 "
        "OR handle IN (SELECT handle FROM traders WHERE is_mock = 1))"
    ),
    "post_class": (
        "is_mock = 1 OR post_id IN (SELECT post_id FROM posts WHERE is_mock = 1 "
        "OR handle IN (SELECT handle FROM traders WHERE is_mock = 1))"
    ),
    "post_media": (
        "is_mock = 1 OR post_id IN (SELECT post_id FROM posts WHERE is_mock = 1 "
        "OR handle IN (SELECT handle FROM traders WHERE is_mock = 1))"
    ),
    "breadth_notes": (
        "is_mock = 1 OR post_id IN (SELECT post_id FROM posts WHERE is_mock = 1 "
        "OR handle IN (SELECT handle FROM traders WHERE is_mock = 1))"
    ),
    "watch_ideas": (
        "is_mock = 1 OR post_id IN (SELECT post_id FROM posts WHERE is_mock = 1 "
        "OR handle IN (SELECT handle FROM traders WHERE is_mock = 1))"
    ),
    "edu_items": (
        "is_mock = 1 OR post_id IN (SELECT post_id FROM posts WHERE is_mock = 1 "
        "OR handle IN (SELECT handle FROM traders WHERE is_mock = 1))"
    ),
    "review_queue": (
        "is_mock = 1 OR post_id IN (SELECT post_id FROM posts WHERE is_mock = 1 "
        "OR handle IN (SELECT handle FROM traders WHERE is_mock = 1)) "
        "OR position_id IN (SELECT position_id FROM positions WHERE is_mock = 1 "
        "OR handle IN (SELECT handle FROM traders WHERE is_mock = 1))"
    ),
    "trader_style": "is_mock = 1 OR handle IN (SELECT handle FROM traders WHERE is_mock = 1)",
    "positions": "is_mock = 1 OR handle IN (SELECT handle FROM traders WHERE is_mock = 1)",
    "posts": "is_mock = 1 OR handle IN (SELECT handle FROM traders WHERE is_mock = 1)",
    "themes": "is_mock = 1",
    "regime_daily": "is_mock = 1",
    "symbol_attention": "is_mock = 1",
    "traders": "is_mock = 1",
}

TRADERS = [
    ("mock_swingdesk",   "Swing Desk (MOCK)",     "CORE",   ["swing", "breakout"]),
    ("mock_baseandgo",   "Base & Go (MOCK)",      "CORE",   ["swing", "ep"]),
    ("mock_tapewatcher", "Tape Watcher (MOCK)",   "CORE",   ["breadth"]),
    ("mock_ipobase",     "IPO Base (MOCK)",       "WATCH",  ["ipo", "theme"]),
    ("mock_riskfirst",   "Risk First (MOCK)",     "WATCH",  ["education"]),
]

SYMBOLS = [
    ("APOLLOTYRE", 1792.0), ("DIXON", 14200.0), ("KPITTECH", 1610.0),
    ("ZAGGLE", 412.0), ("BEL", 318.0), ("CUMMINSIND", 3840.0),
    ("PERSISTENT", 5620.0), ("TATAELXSI", 6180.0),
]

THEMES = [
    ("DEFENCE", ["BEL", "HAL", "BDL", "SOLARINDS"]),
    ("POWER ANCILLARY", ["CUMMINSIND", "KIRLOSENG", "TRIVENI"]),
    ("QUICK COMMERCE", ["ZAGGLE", "SWIGGY"]),
]

EDU = [
    ("mock_riskfirst", "stops",
     "the stop goes where the idea is wrong, not where your loss feels big"),
    ("mock_riskfirst", "sizing",
     "size so that being wrong is boring; if a loss changes your mood you were too big"),
    ("mock_swingdesk", "entries",
     "no add unless the first tranche is already paying you"),
    ("mock_baseandgo", "exits",
     "sell into strength on the third or fourth thrust, not after the reversal"),
    ("mock_tapewatcher", "breadth",
     "when the 4% up count contracts three days running, stand down regardless of your setup"),
]


def _pid(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:16]


def clear_mock(conn) -> int:
    """Atomically purge rows proven mock by their flag or mock parentage."""
    total = 0
    with conn:
        for table in MOCK_TABLES:
            cur = conn.execute(  # noqa: S608 -- table names are the fixed list above.
                f"DELETE FROM {table} WHERE {_MOCK_DELETE_WHERE[table]}"
            )
            total += cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
    return total


def seed(conn) -> dict[str, int]:
    ts = now_iso()
    today = date(2026, 8, 22)          # fixed "today" so the fixture never drifts
    counts: dict[str, int] = {}

    # -- traders ------------------------------------------------------------
    for handle, name, tier, tags in TRADERS:
        conn.execute(
            "INSERT OR REPLACE INTO traders "
            "(handle, display_name, tier, tags, active, last_seen_ts, notes, is_mock, ingested_at) "
            "VALUES (?,?,?,?,1,?,?,1,?)",
            (handle, name, tier, json.dumps(tags), f"{today}T15:30:00+05:30",
             "seeded mock account - not a real X handle", ts),
        )
    counts["traders"] = len(TRADERS)

    # -- regime_daily: 90 sessions of XP + MBI -------------------------------
    # A random walk shaped to look like the real thing. NOT the real XP
    # recursion -- that arrives with the adopted module at W4, and implementing
    # it twice would break single-writer-per-table.
    xp, z = 22.0, 18.0
    regime_rows = 0
    for i in range(90, 0, -1):
        d = today - timedelta(days=i)
        if d.weekday() >= 5:
            continue
        xp = max(3.0, min(140.0, xp * RNG.uniform(0.86, 1.17)))
        z = z * 0.84 + RNG.uniform(4, 40) * 0.16
        band = "LOW" if xp < 15 else "BUILDING" if xp < 40 else "STRONG" if xp < 100 else "EXTREME"
        r10 = RNG.uniform(20, 160); r20 = RNG.uniform(20, 160)
        r50 = RNG.uniform(40, 180); r4p5 = RNG.uniform(10, 420)

        def _b(v: float, green: float = 75.0, white: float = 50.0) -> str:
            return "GREEN" if v >= green else "WHITE" if v >= white else "RED"

        bands = [_b(r10), _b(r20), _b(r50, 85.0, 60.0),
                 "RED" if r4p5 < 50 else "WHITE" if r4p5 < 200 else "GREEN"]
        score = sum(1 for b in bands if b == "GREEN") - sum(1 for b in bands if b == "RED")
        red_count = sum(1 for b in bands if b == "RED")
        color = "GREEN" if score >= 3 else "RED" if score <= -3 else "WHITE"
        conn.execute(
            "INSERT OR REPLACE INTO regime_daily (trade_date, xp_value, xp_z_state, xp_band,"
            " r10, r20, r50, r4p5, band_r10, band_r20, band_r50, band_r4p5,"
            " mbi_day_color, mbi_score, warning_day, source_date, is_mock, ingested_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?)",
            (d.isoformat(), round(xp, 2), round(z, 2), band,
             round(r10, 1), round(r20, 1), round(r50, 1), round(r4p5, 1),
             *bands, color, score, 1 if red_count >= 3 else 0, d.isoformat(), ts),
        )
        regime_rows += 1
    counts["regime_daily"] = regime_rows

    posts = events = media = 0

    def add_post(handle, pid, when, text, kind, conf, symbols=None,
                 conv=None, reply_to=None, deleted=None):
        nonlocal posts
        conn.execute(
            "INSERT OR REPLACE INTO posts (post_id, handle, conversation_id, in_reply_to,"
            " ts_utc, ts_ist, text, url, lang, raw_path, fetched_at, deleted_at, is_mock, ingested_at)"
            " VALUES (?,?,?,?,?,?,?,?,'en',NULL,?,?,1,?)",
            (pid, handle, conv or pid, reply_to,
             when.astimezone(timezone.utc).isoformat(timespec="seconds"),
             when.isoformat(timespec="seconds"), text,
             f"https://x.com/{handle}/status/{pid}", ts, deleted, ts),
        )
        conn.execute(
            "INSERT OR REPLACE INTO post_class (post_id, kind, confidence, symbols, model,"
            " run_id, is_mock, ingested_at) VALUES (?,?,?,?,'mock-seed',NULL,1,?)",
            (pid, kind, conf, json.dumps(symbols or []), ts),
        )
        posts += 1
        return pid

    def ist(d: date, h: int, m: int) -> datetime:
        return datetime(d.year, d.month, d.day, h, m,
                        tzinfo=timezone(timedelta(hours=5, minutes=30)))

    # -- positions with real thread structure --------------------------------
    plans = [
        # handle, symbol, entry_price, days_ago_entry, adds, stop, exit, result
        ("mock_swingdesk", "APOLLOTYRE", 1792.0, 18, [(1847.0, 11, 25)], 1790.0, None, None),
        ("mock_swingdesk", "DIXON", 14200.0, 21, [], 14450.0, (15610.0, 1), 9.9),
        ("mock_baseandgo", "KPITTECH", 1610.0, 10, [], None, None, None),
        ("mock_baseandgo", "BEL", 318.0, 30, [(331.0, 24, 50)], 322.0, (352.0, 4), 8.7),
        ("mock_swingdesk", "CUMMINSIND", 3840.0, 40, [], 3720.0, (3698.0, 33), -3.7),
        ("mock_baseandgo", "PERSISTENT", 5620.0, 52, [], 5480.0, (6210.0, 38), 10.5),
        ("mock_tapewatcher", "TATAELXSI", 6180.0, 26, [], None, (6050.0, 19), -2.1),
    ]

    for handle, symbol, entry, ago, adds, stop, exit_info, result in plans:
        entry_d = today - timedelta(days=ago)
        root = _pid(handle, symbol, str(entry_d))
        add_post(handle, root, ist(entry_d, 10, 15),
                 f"took a starter in {symbol.lower()} at {entry:,.0f}, base looks tight",
                 "trade_event", 0.93, [symbol])

        pos_id = _pid("pos", handle, symbol, root)
        seq = 0
        ev: list[tuple] = [("entry", entry, None, entry_d, root)]
        unresolved: list[str] = []
        evidence = {"symbol": root, "entries[0].price": root}

        if stop is not None:
            spid = add_post(handle, _pid(root, "sl"), ist(entry_d, 10, 16),
                            f"sl {stop:,.0f}", "trade_event", 0.9, [symbol],
                            conv=root, reply_to=root)
            ev.append(("sl_set", stop, None, entry_d, spid))
            evidence["stop.price"] = spid
        else:
            unresolved.append("stop never stated")

        for add_price, add_ago, qty in adds:
            ad = today - timedelta(days=add_ago)
            apid = add_post(handle, _pid(root, "add", str(add_ago)), ist(ad, 13, 40),
                            f"added {qty}% more at {add_price:,.0f}, sl trailed up",
                            "trade_event", 0.91, [symbol], conv=root, reply_to=root)
            ev.append(("add", add_price, qty, ad, apid))
            evidence["adds[0].price"] = apid

        status = "added" if adds and not exit_info else "open"
        if exit_info:
            xp_price, x_ago = exit_info
            xd = today - timedelta(days=x_ago)
            xpid = add_post(handle, _pid(root, "exit"), ist(xd, 14, 5),
                            f"booked {symbol.lower()} at {xp_price:,.0f}, {result:+.1f}%",
                            "trade_event", 0.94, [symbol], conv=root, reply_to=root)
            ev.append(("exit", xp_price, 100.0, xd, xpid))
            evidence["exits[0].price"] = xpid
            status = "closed"

        state = {
            "symbol": symbol, "status": status,
            "entries": [{"price": entry, "date": entry_d.isoformat(), "post_id": root}],
            "adds": [{"price": a, "qty_pct": q} for a, _, q in adds],
            "stop": {"price": stop} if stop else None,
            "exits": [{"price": exit_info[0]}] if exit_info else [],
            "net_result_pct": result, "confidence": 0.9,
        }
        conn.execute(
            "INSERT OR REPLACE INTO positions (position_id, handle, symbol, root_post_id, status,"
            " opened_at, closed_at, net_result_pct, holding_days, confidence, state_json,"
            " evidence_json, unresolved_json, thread_hash, reconciled_at, reconcile_model,"
            " is_mock, ingested_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'mock-seed',1,?)",
            (pos_id, handle, symbol, root, status, entry_d.isoformat(),
             (today - timedelta(days=exit_info[1])).isoformat() if exit_info else None,
             result, (ago - exit_info[1]) if exit_info else (today - entry_d).days,
             0.9 if stop else 0.58, json.dumps(state), json.dumps(evidence),
             json.dumps(unresolved), _pid(root, "hash"), ts, ts),
        )
        for kind, price, qty, when, src in ev:
            seq += 1
            conn.execute(
                "INSERT INTO position_events (position_id, post_id, kind, price, qty_pct,"
                " stated_at, seq, confidence, note, is_mock, ingested_at)"
                " VALUES (?,?,?,?,?,?,?,?,NULL,1,?)",
                (pos_id, src, kind, price, qty, when.isoformat(), seq, 0.9, ts),
            )
            events += 1

        if adds:
            conn.execute(
                "INSERT OR REPLACE INTO post_media (post_id, idx, local_path, sha256,"
                " media_type, vision_json, vision_model, vision_at, is_mock, ingested_at)"
                " VALUES (?,0,?,?, 'image', ?, 'mock-seed', ?, 1, ?)",
                (root, f"mock/{symbol}_daily.png", _pid(symbol, "sha"),
                 json.dumps({
                     "chart_symbol": symbol, "timeframe": "daily",
                     "text_in_image": [f"SL {stop:,.0f}" if stop else "no levels marked"],
                     "annotated_levels": (
                         [{"kind": "stop", "price": stop,
                           "source": "horizontal line labelled SL"}] if stop else []),
                     "structure_note": "multi-week range, breakout candle on expanded volume",
                     "confidence": 0.71, "unreadable": False,
                 }), ts, ts),
            )
            media += 1

    counts["positions"] = len(plans)
    counts["position_events"] = events
    counts["post_media"] = media

    # -- a deleted post ------------------------------------------------------
    dd = today - timedelta(days=3)
    add_post("mock_ipobase", _pid("deleted", "one"), ist(dd, 8, 40),
             "long ZAGGLE above 412", "trade_event", 0.88, ["ZAGGLE"],
             deleted=ist(dd, 11, 20).isoformat())

    # -- breadth commentary --------------------------------------------------
    stances = ["risk_on", "neutral", "risk_off"]
    bn = 0
    for i in range(28):
        d = today - timedelta(days=i)
        if d.weekday() >= 5:
            continue
        for handle in ("mock_tapewatcher", "mock_swingdesk", "mock_baseandgo"):
            if RNG.random() < 0.45:
                continue
            stance = RNG.choice(stances)
            pid = add_post(
                handle, _pid("breadth", handle, str(d)), ist(d, 9, 12),
                {"risk_on": "internals expanding, adding on strength today",
                 "neutral": "mixed tape, doing nothing new here",
                 "risk_off": "internals soft, staying light until the 4% up count expands",
                 }[stance], "breadth", 0.86)
            conn.execute(
                "INSERT OR REPLACE INTO breadth_notes (post_id, handle, trade_date, stance,"
                " claims_json, symbols, confidence, is_mock, ingested_at)"
                " VALUES (?,?,?,?,?,'[]',?,1,?)",
                (pid, handle, d.isoformat(), stance,
                 json.dumps(["4% up count is the trigger"]), 0.86, ts),
            )
            bn += 1
    counts["breadth_notes"] = bn

    # -- watch ideas + themes ------------------------------------------------
    wi = 0
    for symbol, level in [("KPITTECH", 1610.0), ("ZAGGLE", 412.0), ("BEL", 318.0)]:
        for handle in RNG.sample([t[0] for t in TRADERS], RNG.randint(1, 3)):
            d = today - timedelta(days=RNG.randint(2, 20))
            kind = RNG.choice(["watch", "watch", "ep", "ipo"])
            pid = add_post(handle, _pid("watch", handle, symbol), ist(d, 18, 5),
                           f"{symbol.lower()} above {level:,.0f} on volume, on the list",
                           "watch_idea", 0.83, [symbol])
            conn.execute(
                "INSERT INTO watch_ideas (post_id, handle, symbol, kind, trigger_text, level,"
                " stated_at, status, confidence, is_mock, ingested_at)"
                " VALUES (?,?,?,?,?,?,?,'open',?,1,?)",
                (pid, handle, symbol, kind, f"above {level:,.0f} on volume", level,
                 d.isoformat(), 0.83, ts),
            )
            wi += 1
    counts["watch_ideas"] = wi

    for name, syms in THEMES:
        conn.execute(
            "INSERT OR REPLACE INTO themes (name, symbols_json, first_seen, last_seen,"
            " mention_count, is_mock, ingested_at) VALUES (?,?,?,?,?,1,?)",
            (name, json.dumps(syms), (today - timedelta(days=40)).isoformat(),
             (today - timedelta(days=RNG.randint(1, 8))).isoformat(),
             RNG.randint(4, 14), ts),
        )
    counts["themes"] = len(THEMES)

    # -- education + practice-vs-preach links --------------------------------
    edu_ids = []
    for handle, topic, text in EDU:
        d = today - timedelta(days=RNG.randint(10, 60))
        pid = add_post(handle, _pid("edu", handle, topic), ist(d, 20, 30),
                       text, "education", 0.89)
        cur = conn.execute(
            "INSERT INTO edu_items (post_id, handle, title, principle_text, topic_tags,"
            " stated_at, confidence, is_mock, ingested_at) VALUES (?,?,?,?,?,?,?,1,?)",
            (pid, handle, topic.title(), text, json.dumps([topic]), d.isoformat(), 0.89, ts),
        )
        edu_ids.append((cur.lastrowid, handle))
    counts["edu_items"] = len(EDU)

    pos_rows = conn.execute("SELECT position_id, handle FROM positions WHERE is_mock = 1").fetchall()
    links = 0
    for edu_id, handle in edu_ids:
        for row in pos_rows:
            if row["handle"] != handle or RNG.random() < 0.4:
                continue
            verdict = RNG.choices(["followed", "violated", "na"], weights=[6, 2, 2])[0]
            conn.execute(
                "INSERT INTO edu_links (edu_id, position_id, verdict, evidence, confidence,"
                " is_mock, ingested_at) VALUES (?,?,?,?,?,1,?)",
                (edu_id, row["position_id"], verdict,
                 "stop widened rather than honoured" if verdict == "violated" else "consistent",
                 0.7, ts),
            )
            links += 1
    counts["edu_links"] = links

    # -- trader style --------------------------------------------------------
    for handle, *_ in TRADERS:
        n = conn.execute(
            "SELECT COUNT(*) FROM positions WHERE handle = ? AND is_mock = 1", (handle,)
        ).fetchone()[0]
        if n == 0:
            continue
        conn.execute(
            "INSERT OR REPLACE INTO trader_style (handle, as_of, n_positions, median_hold_days,"
            " stated_win_rate, avg_result_pct, avg_r, sector_tilt_json, entry_type_json,"
            " stop_stated_pct, stop_honored_pct, preach_score, is_mock, ingested_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,1,?)",
            (handle, today.isoformat(), n, RNG.uniform(6, 20),
             RNG.uniform(0.42, 0.63), RNG.uniform(1.5, 7.0), RNG.uniform(1.1, 2.3),
             json.dumps({"CAPITAL GOODS": 24, "AUTO": 18, "PHARMA": 12, "IT": 9}),
             json.dumps({"breakout": 61, "pullback": 24, "ep": 15}),
             RNG.uniform(0.55, 0.85), RNG.uniform(0.45, 0.78),
             RNG.uniform(0.55, 0.85), ts),
        )

    # -- review queue --------------------------------------------------------
    rq = [
        ("link_event", "booked apollo, +18%",
         "attach as EXIT Rs 2,104 to APOLLOTYRE opened 04 Aug?",
         {"reasoning": "same symbol, only open position for this handle, "
                       "'booked' implies a full exit",
          "alternatives": ["could be a separate same-day trade"],
          "proposed_event": {"kind": "exit", "price": 2104, "qty_pct": 100}}, 0.62),
        ("ambiguous_symbol", "long bel here, small",
         "BEL or BELRISE? both match 'bel' in this post",
         {"reasoning": "abbreviation is ambiguous",
          "alternatives": ["BEL (defence)", "BELRISE (auto parts)"]}, 0.44),
        ("low_conf_parse", "adding into strength",
         "add event with no symbol and no price - attach to the open KPITTECH thread?",
         {"reasoning": "posted 4 minutes after a KPITTECH post by the same handle",
          "alternatives": ["could refer to a position never posted about"]}, 0.51),
    ]
    for kind, _txt, question, proposed, conf in rq:
        conn.execute(
            "INSERT INTO review_queue (kind, post_id, position_id, question, proposed_json,"
            " confidence, status, is_mock, ingested_at) VALUES (?,NULL,NULL,?,?,?,'open',1,?)",
            (kind, question, json.dumps(proposed), conf, ts),
        )
    counts["review_queue"] = len(rq)
    counts["posts"] = posts

    conn.commit()
    return counts


def main() -> int:
    conn = init_db()
    try:
        if "--clear" in sys.argv:
            n = clear_mock(conn)
            print(f"removed {n} mock rows")
            return 0
        clear_mock(conn)          # idempotent: reseeding replaces, never duplicates
        counts = seed(conn)
        print("seeded MOCK data (is_mock = 1 on every row):")
        for k, v in sorted(counts.items()):
            print(f"  {k:<18} {v}")
        print("\nremove it later with: python traderlog/seed_mock.py --clear")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
