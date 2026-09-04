"""derive/watchlists.py -- turns posts into dated watchlist SETS.

## Design premise (why this module exists)
IDEAS was originally built assuming "one idea per symbol, with a trigger and
a numeric level." The real corpus does not work that way: a sample of 29
``watch_idea`` rows carried 0 numeric levels and 31% had no symbol at all.
What traders actually post is a DATED SET of symbols in one post -- e.g.
mystocks_in's 2026-05-31 post "#GlandPharma #Sakar #BharatCoal #SilverTouch
#ANgelOne #Sandhar #ShadowFax #Sandhar #BalaAmines Names from Strong
watchlist for next week" names nine tickers in one shot. The unit of
meaning is the LIST, on a DATE, by a TRADER -- not the individual symbol.

The existing ``watch_ideas`` table already supports this natively: N rows
sharing one ``post_id`` and ``stated_at`` ARE the set. No schema change is
made or needed. Per CANONICAL.md §6 this module is the SOLE writer of
``watch_ideas``.

## Source selection (unioned)
  1. ``post_class.kind == 'watch_idea'``.
  2. ANY post with >= ``HASHTAG_DENSITY_MIN_SYMBOLS`` distinct #hashtag
     tokens in its text, regardless of the classifier's assigned kind --
     watchlist dumps are frequently misclassified as something else, and
     hashtag density is a stronger signal than the label.

A post is EXCLUDED from both sources when a known capture defect has filed
someone else's reply under the tracked trader's own handle: text that
begins with the filed handle's own @mention (X's reply convention means a
genuine self-post never starts with the poster's own handle).

## Symbol resolution -- the quality-critical part
Candidate symbols come from ``post_class.symbols`` (the classifier's JSON
list) UNIONED with #hashtags parsed from the raw text, uppercased and
deduplicated WITHIN a post (the corpus contains posts that hashtag the same
symbol twice, e.g. "#Sandhar ... #Sandhar"). Every candidate is validated
against the real NSE master (``SELECT DISTINCT symbol FROM daily_prices``)
before being written. A symbol that fails validation is DROPPED, counted
and reported -- never invented, never fuzzy-matched.

``SYMBOL_ALIASES`` below is a small, hand-confirmed exception list for real
companies posted under a hashtag that is not the exact NSE ticker (e.g.
``#GlandPharma`` -> ``GLAND``). Every entry was confirmed present in
``SELECT DISTINCT symbol FROM daily_prices`` by direct inspection -- this is
NOT a fuzzy matcher, it is a fixed, auditable, hand-written map. A symbol
not covered here that fails validation is simply dropped.

## level / trigger_text
Project invariant: ``level`` is NULL unless the post states a numeric level
FOR THAT SPECIFIC SYMBOL -- never inferred, never carried from one symbol to
another in the same post. Attributing a bare number to one symbol out of
several named in the same list post is exactly the kind of guess this
module refuses to make, so level/trigger_text extraction only runs on posts
with EXACTLY ONE candidate symbol (attribution is then unambiguous by
construction). On those posts, a narrow set of price-trigger words
(at/above/below/near/around) followed by a >= 2 digit number is treated as
a stated level; ``trigger_text`` is the verbatim matched span from the
post's own text, never a paraphrase. Every other row gets NULL/NULL --
per the spec this is expected and correct for most rows.

## confidence
Source-1 rows (``kind == 'watch_idea'``) inherit the classifier's own
``post_class.confidence``. Source-2-only rows (hashtag-density heuristic,
no model judgement made) get ``HASHTAG_DENSITY_CONFIDENCE`` -- a fixed,
named, lower constant so it reads as a stated convention, not a
measurement.

## status -- forward performance, closed vocabulary
For every resolved symbol, ``status`` reports what happened AFTER the call,
computed only from ``daily_prices`` (no LLM, nothing invented):

  NO_PRICE_DATA          symbol never appears in daily_prices at all.
  NO_DATA_SINCE_STATED   daily_prices has rows for the symbol, but none on
                          or after stated_at's date (delisted, data gap, or
                          bhavcopy coverage ends before this call). A
                          missing price is reported honestly here -- it is
                          never treated as a 0% return.
  UP_BIG / UP             final return (first close on/after stated_at ->
                          most recent close) >= UP_BIG_THRESHOLD / UP_THRESHOLD.
  FLAT                    final return strictly between the up/down
                          thresholds -- no meaningful move either way.
  DOWN / DOWN_BIG         final return <= -UP_THRESHOLD / -UP_BIG_THRESHOLD.
  FADED                   the call worked -- the max favourable excursion
                          (highest daily HIGH reached after entry) reached
                          FADE_MFE_THRESHOLD -- but the most recent close has
                          given back >= FADE_GAP of that peak. FADED takes
                          priority over the final-return buckets above,
                          because "it worked, then reversed" is a more
                          useful, truer story than whatever flat/down bucket
                          the current price alone would suggest.

## Idempotency
Full re-derivation every run, matching the reconciler's discipline: every
row this module owns is deleted and rebuilt inside one transaction (the
DELETE and the INSERTs commit together; a failure mid-rebuild rolls back to
the prior state -- watch_ideas is never left half-deleted). Re-running
``run()`` against an unchanged corpus produces the same rows (content-wise;
autoincrement ``id`` and ``ingested_at`` naturally advance, same as every
other adopted/derive stage's upsert), never duplicates.

Public contract (matches adopted/bhavcopy.py's ingestor shape):
    run(conn, run_date) -> int   # rows written; always logs pipeline_runs;
                                  # never partially commits
"""
from __future__ import annotations

import json
import re
import time
from datetime import date

from traderlog.db import now_iso

STAGE = "derive.watchlists"

# ---------------------------------------------------------------------------
# Tunables -- named + commented so every threshold is auditable, not magic.
# ---------------------------------------------------------------------------

# Source 2: a post counts as watchlist-shaped by hashtag density alone when
# it names at least this many DISTINCT hashtag tokens, regardless of the
# classifier's assigned kind. See module docstring "Source selection".
HASHTAG_DENSITY_MIN_SYMBOLS = 3

# Source-2-only confidence. NOT a measurement -- no model looked at these
# posts, the density heuristic alone put them here. Deliberately a fixed,
# named constant below the typical classifier-scored watch_idea confidence,
# so downstream consumers can tell "heuristic" apart from "classified".
HASHTAG_DENSITY_CONFIDENCE = 0.45

# level/trigger_text extraction only fires on single-candidate-symbol posts
# (see module docstring "level / trigger_text"). Trigger words are
# deliberately narrow to avoid matching unrelated numbers (dates, percents,
# times); the >=2-digit requirement plus the "not followed by % or :" guard
# rules out most non-price numbers (e.g. "at 9:30", "up 5%").
_LEVEL_TRIGGER_WORDS = r"at|above|below|near|around"
_LEVEL_RE = re.compile(
    rf"\b(?:{_LEVEL_TRIGGER_WORDS})\s+(?:rs\.?\s*|inr\s*|₹\s*)?"
    r"([0-9]{2,3}(?:,[0-9]{2,3})*(?:\.[0-9]+)?)(?![%:\d])",
    re.IGNORECASE,
)

# Same conservative ticker shape llm/classify.py validates symbols against.
_HASHTAG_RE = re.compile(r"#([A-Za-z][A-Za-z0-9]{0,29})")

# Forward-performance thresholds (see module docstring "status"). Return is
# computed from the first close on/after stated_at to the most recent close;
# MFE (max favourable excursion) from the highest daily HIGH in between.
FLAT_BAND = 0.05             # within +/-5% -> FLAT
UP_THRESHOLD = FLAT_BAND     # >= +5% -> UP
UP_BIG_THRESHOLD = 0.20      # >= +20% -> UP_BIG
DOWN_THRESHOLD = -FLAT_BAND  # <= -5% -> DOWN
DOWN_BIG_THRESHOLD = -0.20   # <= -20% -> DOWN_BIG
FADE_MFE_THRESHOLD = 0.15    # the peak itself must have been a real move
FADE_GAP = 0.10              # ...and given back at least this much by now

STATUS_NO_PRICE_DATA = "no_price_data"
STATUS_NO_DATA_SINCE_STATED = "no_data_since_stated"
STATUS_UP_BIG = "up_big"
STATUS_UP = "up"
STATUS_FLAT = "flat"
STATUS_DOWN = "down"
STATUS_DOWN_BIG = "down_big"
STATUS_FADED = "faded"

# Hand-confirmed alias map: real companies posted under a hashtag that is
# not the exact NSE ticker daily_prices carries. Every RHS was confirmed
# present in `SELECT DISTINCT symbol FROM daily_prices` by direct inspection
# on 2026-08-25. NOT fuzzy matching -- a fixed, auditable exception list.
# A candidate not covered here that fails validation is dropped, not guessed.
SYMBOL_ALIASES = {
    "GLANDPHARMA": "GLAND",       # Gland Pharma Ltd
    "BALAAMINES": "BALAMINES",    # Balaji Amines Ltd
    "WAAREENER": "WAAREEENER",    # Waaree Energies Ltd
    "GMDC": "GMDCLTD",            # Gujarat Mineral Development Corp Ltd
    "ASIANENERGY": "ASIANENE",    # Asian Energy Services Ltd
    "DECCANGOLD": "DECNGOLD",     # Deccan Gold Mines Ltd
    "SILVERTOUCH": "SILVERTUC",   # Silver Touch Technologies Ltd
}

# Every derived row is a generic dated watchlist entry -- the corpus does
# not reliably distinguish ep/ipo/theme sub-kinds at the list-dump layer
# this module targets (see module docstring "Design premise").
_KIND = "watch"

_INSERT_SQL = (
    "INSERT INTO watch_ideas "
    "(post_id, handle, symbol, kind, trigger_text, level, stated_at, "
    " status, confidence, is_mock, ingested_at) "
    "VALUES (:post_id, :handle, :symbol, :kind, :trigger_text, :level, "
    " :stated_at, :status, :confidence, :is_mock, :ingested_at)"
)


# ---------------------------------------------------------------------------
# Pure-ish helpers (unit-testable without a DB, except where a conn is the
# whole point -- symbol/price lookups).
# ---------------------------------------------------------------------------

def _hashtag_symbols(text: str) -> list[str]:
    """Distinct #hashtag tokens in ``text``, uppercased, first-seen order."""
    seen: list[str] = []
    for m in _HASHTAG_RE.finditer(text or ""):
        sym = m.group(1).upper()
        if sym not in seen:
            seen.append(sym)
    return seen


def _is_contaminated(handle: str, text: str) -> bool:
    """Reply-under-tracked-handle capture defect (see module docstring)."""
    return (text or "").startswith("@" + handle)


def resolve_symbol(raw: str, master: set[str]) -> str | None:
    """Raw candidate token -> validated NSE ticker, or None.

    Checks the hand-written alias map first, then the real master. Never
    fuzzy-matches: a token not in ``master`` (directly or via alias) simply
    fails to resolve.
    """
    candidate = SYMBOL_ALIASES.get(raw, raw)
    return candidate if candidate in master else None


def _extract_level(text: str) -> tuple[float | None, str | None]:
    """(level, trigger_text) from a SINGLE-symbol post's text, or (None, None).

    Caller is responsible for only invoking this on posts with exactly one
    candidate symbol -- that is what makes "this level belongs to this
    symbol" unambiguous. Returns the FIRST price-trigger match only.
    ``trigger_text`` is the verbatim matched span (never a paraphrase).
    """
    m = _LEVEL_RE.search(text or "")
    if not m:
        return None, None
    raw_num = m.group(1).replace(",", "")
    try:
        level = float(raw_num)
    except ValueError:
        return None, None
    return level, m.group(0)


def classify_forward_performance(conn, symbol: str, stated_date: str) -> str:
    """status string for ``symbol`` as of ``stated_date`` ('YYYY-MM-DD'),
    computed only from daily_prices. See module docstring "status".

    The NO_PRICE_DATA branch is unreachable via ``derive()``'s own pipeline
    (a symbol only reaches here after ``resolve_symbol`` confirmed it has at
    least one daily_prices row) but is kept for defensive completeness and
    because this function is directly unit-tested on its own.
    """
    has_any = conn.execute(
        "SELECT 1 FROM daily_prices WHERE symbol = ? LIMIT 1", (symbol,)
    ).fetchone()
    if has_any is None:
        return STATUS_NO_PRICE_DATA

    entry = conn.execute(
        "SELECT trade_date, close FROM daily_prices "
        "WHERE symbol = ? AND trade_date >= ? ORDER BY trade_date ASC LIMIT 1",
        (symbol, stated_date),
    ).fetchone()
    if entry is None or entry["close"] is None or entry["close"] <= 0:
        return STATUS_NO_DATA_SINCE_STATED

    latest = conn.execute(
        "SELECT trade_date, close FROM daily_prices "
        "WHERE symbol = ? ORDER BY trade_date DESC LIMIT 1",
        (symbol,),
    ).fetchone()
    entry_close = entry["close"]
    latest_close = latest["close"] if latest and latest["close"] is not None else entry_close
    latest_date = latest["trade_date"] if latest else entry["trade_date"]
    final_return = (latest_close / entry_close) - 1.0

    mfe_row = conn.execute(
        "SELECT MAX(high) AS max_high FROM daily_prices "
        "WHERE symbol = ? AND trade_date >= ? AND trade_date <= ?",
        (symbol, entry["trade_date"], latest_date),
    ).fetchone()
    max_high = mfe_row["max_high"] if mfe_row else None
    mfe_return = (max_high / entry_close - 1.0) if max_high is not None else final_return

    if mfe_return >= FADE_MFE_THRESHOLD and (mfe_return - final_return) >= FADE_GAP:
        return STATUS_FADED
    if final_return >= UP_BIG_THRESHOLD:
        return STATUS_UP_BIG
    if final_return >= UP_THRESHOLD:
        return STATUS_UP
    if final_return <= DOWN_BIG_THRESHOLD:
        return STATUS_DOWN_BIG
    if final_return <= DOWN_THRESHOLD:
        return STATUS_DOWN
    return STATUS_FLAT


# ---------------------------------------------------------------------------
# Derivation core -- read-only. Returns the rows to write plus a stats dict
# for logging/reporting. Never touches the DB (no writes; safe to call
# repeatedly, e.g. for a dry-run report).
# ---------------------------------------------------------------------------

def _candidate_posts(conn) -> list[dict]:
    return [
        dict(r)
        for r in conn.execute(
            "SELECT p.post_id, p.handle, p.text, p.ts_ist, p.is_mock, "
            "       pc.kind AS kind, pc.symbols AS class_symbols, "
            "       pc.confidence AS class_confidence "
            "FROM posts p LEFT JOIN post_class pc ON pc.post_id = p.post_id "
            "WHERE p.text IS NOT NULL"
        ).fetchall()
    ]


def derive(conn) -> tuple[list[dict], dict]:
    """Compute the full watch_ideas rebuild from posts/post_class/daily_prices.

    Pure read -- issues no writes, so it is safe to call on its own (e.g.
    for a stats-only preview) independent of ``run()``.
    """
    master = {r[0] for r in conn.execute("SELECT DISTINCT symbol FROM daily_prices")}

    rows: list[dict] = []
    contaminated_skipped = 0
    candidate_post_ids: set[str] = set()
    unresolved_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    levels_set = 0
    # (symbol, stated_date) forward-performance lookups repeat whenever more
    # than one trader/post names the same symbol on the same calendar date.
    perf_cache: dict[tuple[str, str], str] = {}

    for post in _candidate_posts(conn):
        handle = post["handle"]
        text = post["text"] or ""
        if _is_contaminated(handle, text):
            contaminated_skipped += 1
            continue

        tags = _hashtag_symbols(text)
        is_source1 = post["kind"] == "watch_idea"
        is_source2 = len(tags) >= HASHTAG_DENSITY_MIN_SYMBOLS
        if not (is_source1 or is_source2):
            continue

        candidates: list[str] = list(tags)
        if post["class_symbols"]:
            try:
                parsed = json.loads(post["class_symbols"])
            except (json.JSONDecodeError, TypeError):
                parsed = []
            for s in parsed:
                su = str(s).upper()
                if su not in candidates:
                    candidates.append(su)
        if not candidates:
            continue

        candidate_post_ids.add(post["post_id"])

        confidence = (
            post["class_confidence"]
            if is_source1 and post["class_confidence"] is not None
            else HASHTAG_DENSITY_CONFIDENCE
        )

        # Unambiguous attribution only: a stated level can be tied to THE
        # symbol solely when there is exactly one candidate in the post.
        level, trigger_text = (None, None)
        if len(candidates) == 1:
            level, trigger_text = _extract_level(text)

        stated_date = (post["ts_ist"] or "")[:10]
        for raw_symbol in candidates:
            symbol = resolve_symbol(raw_symbol, master)
            if symbol is None:
                unresolved_counts[raw_symbol] = unresolved_counts.get(raw_symbol, 0) + 1
                continue

            cache_key = (symbol, stated_date)
            status = perf_cache.get(cache_key)
            if status is None:
                status = classify_forward_performance(conn, symbol, stated_date)
                perf_cache[cache_key] = status
            status_counts[status] = status_counts.get(status, 0) + 1

            if level is not None:
                levels_set += 1

            rows.append({
                "post_id": post["post_id"],
                "handle": handle,
                "symbol": symbol,
                "kind": _KIND,
                "trigger_text": trigger_text,
                "level": level,
                "stated_at": post["ts_ist"],
                "status": status,
                "confidence": confidence,
                "is_mock": post["is_mock"],
                "ingested_at": now_iso(),
            })

    stats = {
        "candidate_posts": len(candidate_post_ids),
        "contaminated_skipped": contaminated_skipped,
        "rows": len(rows),
        "distinct_symbols": len({r["symbol"] for r in rows}),
        "unresolved_symbols": unresolved_counts,
        "unresolved_total": sum(unresolved_counts.values()),
        "levels_set": levels_set,
        "status_counts": status_counts,
    }
    return rows, stats


# ---------------------------------------------------------------------------
# Orchestration -- matches adopted/bhavcopy.py's run(conn, run_date) -> int
# contract: full transactional rebuild, pipeline_runs logging either way,
# never partially commits.
# ---------------------------------------------------------------------------

def _log_run(conn, run_date: str, status: str, rows: int, dur: float, detail: str) -> None:
    conn.execute(
        "INSERT INTO pipeline_runs (stage, run_date, status, rows, duration_ms, detail, ts) "
        "VALUES (?,?,?,?,?,?,?)",
        (STAGE, run_date, status, rows, int(dur * 1000), detail, now_iso()),
    )


def run(conn, run_date: str, _stats_out: dict | None = None) -> int:
    """Full re-derivation of watch_ideas. Never raises without first logging
    and rolling back to a clean state.

    Idempotent: re-running against an unchanged corpus writes the same
    content, never duplicates -- every row this module owns is deleted and
    rebuilt inside one transaction (see module docstring "Idempotency").

    ``run_date`` stamps the pipeline_runs row; this stage rebuilds from the
    WHOLE corpus every call, not a single date's slice, so it does not
    filter anything by ``run_date`` (matching the reconciler's full-rebuild
    discipline, not the single-date adopted/ ingestors).

    ``_stats_out``, if given, is populated in place with derive()'s full
    stats dict (unresolved symbol names, status distribution, etc.) for
    callers that want more than the row count -- see ``__main__`` below.

    Returns the number of watch_ideas rows written.
    """
    started = time.monotonic()
    try:
        rows, stats = derive(conn)
        if _stats_out is not None:
            _stats_out.update(stats)

        conn.execute("DELETE FROM watch_ideas")
        if rows:
            conn.executemany(_INSERT_SQL, rows)

        dur = time.monotonic() - started
        detail = (
            f"posts={stats['candidate_posts']} "
            f"contaminated_skipped={stats['contaminated_skipped']} "
            f"rows={len(rows)} distinct_symbols={stats['distinct_symbols']} "
            f"unresolved={stats['unresolved_total']} levels_set={stats['levels_set']} "
            f"status={stats['status_counts']}"
        )
        _log_run(conn, run_date, "ok", len(rows), dur, detail)
        conn.commit()
        return len(rows)
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        _log_run(conn, run_date, "fail", 0, time.monotonic() - started, f"{type(exc).__name__}: {exc}")
        conn.commit()
        raise


if __name__ == "__main__":
    from traderlog.db import connect

    _conn = connect()
    _stats: dict = {}
    _n = run(_conn, date.today().isoformat(), _stats_out=_stats)

    print(f"watch_ideas rows written: {_n}")
    print(f"candidate posts covered: {_stats['candidate_posts']}")
    print(f"contaminated posts skipped: {_stats['contaminated_skipped']}")
    print(f"distinct symbols resolved: {_stats['distinct_symbols']}")
    print(f"symbol instances that failed to resolve: {_stats['unresolved_total']}")
    if _stats["unresolved_symbols"]:
        print("unresolved symbols (symbol: post count):")
        for sym, cnt in sorted(_stats["unresolved_symbols"].items(), key=lambda kv: -kv[1]):
            print(f"  {sym}: {cnt}")
    print(f"rows with a non-NULL level: {_stats['levels_set']}")
    print(f"status distribution: {_stats['status_counts']}")
