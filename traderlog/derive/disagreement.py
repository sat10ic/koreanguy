"""derive/disagreement.py -- B1 "Disagreement feed" engine (owner-approved
brainstorm item B1): symbols where public traders DISAGREED within one rolling
window.

## Design premise (why this module exists)
The Radar (INS-1) surfaces co-attention: which symbols several traders named in
a tight window. Co-attention is not consensus -- a name can be simultaneously
being bought by one trader and sold or avoided by another, and that tension is
itself information. This module turns the `watch_ideas` surface into that
signal: group mentions by symbol inside a rolling window and decide, from each
mention's OWN verbatim text and NOTHING else, whether the traders' stated
directions contradict.

This module is PURE READ. It issues no database writes of any kind (not even
pipeline_runs), so it claims no sole-writer ownership anywhere; it only reads
`watch_ideas` (the sole-writer table of derive/watchlists.py) and joins `posts`
for the mention's own text. Safe to call repeatedly against the production
database; it cannot mutate it.

## The polarity vocabulary -- deliberately crude-but-auditable v1
Polarity of each mention is decided ONLY by the two explicit keyword buckets
below. This is v1 and it is deliberately crude: matching is exact-match
substrings on the lowercased text -- `"buy"` matches inside "buyback" and
"buying", `"long"` matches inside "along" and "belong", `"short"` matches
inside "shorts" and "shortage", `"accumulat"` matches inside "accumulating"
and "accumulation", `"stopped out"` is a literal two-word phrase. No stemming,
no synonyms, no word boundaries, no sentiment, no LLM: what the corpus says is
already the whole verdict.

THE VOCABULARY IS THE CONTRACT. Anyone refining this later MUST extend the
BULLISH_MARKERS / BEARISH_MARKERS tables (and this docstring) -- never add
ad-hoc matching logic at the call site. Crudeness is deliberate and auditable;
silent per-callsite "fixes" are not.

Verbatim buckets (as given in the B1 brief, transcribed exactly):
    bullish:  "buy", "bought", "long", "enter", "entered", "adding", "added",
              "accumulat", "breakout", "bullish"
    bearish:  "sell", "sold", "exit", "exited", "avoid", "bearish", "short",
              "distribution", "stopped out"

## Polarity rule -- never guessed
For each mention exactly one of:
    * both buckets hit   -> "mixed"    (the mention states both directions)
    * zero buckets hit   -> "neutral"  (no direction stated at all)
    * only bullish hits  -> "bullish"
    * only bearish hits  -> "bearish"
"mixed" and "neutral" are documented outcomes, NOT polarity values: they are
excluded from the disagreement test. A text that says "bought then sold" is
contradictory evidence; a text that says "watching" is no evidence. Neither is
ever resolved in favour of one side.

## Disagreement rule
A symbol row is emitted when it meets the min_traders gate (>= ``min_traders``
DISTINCT normalized handles in the window). ``disagreement`` is true ONLY when
the symbol's mentions contain BOTH a bullish and a bearish polarity (i.e. >= 2
distinct polarities among the directional ones). Two bearish traders are NOT a
disagreement; one bullish + one mixed is NOT a disagreement; one bullish + one
bearish IS.

## Rolling window
``stated_at`` values are Asia/Kolkata (IST) timestamps as stored by
derive/watchlists.py (``posts.ts_ist``). The window is genuinely rolling: it
ends at ``now`` (the caller's injected clock, defaulting to the current UTC
time) and includes every mention whose stated_at >= ``now - days_back days``
(inclusive lower bound). Window semantics are UTC-instant comparisons on the
parsed timestamps -- not calendar days. ``now`` is an injectable keyword
argument so the window boundary is deterministic and testable; naive ``now``
values are treated as UTC.

## Handle normalisation
Distinct-handle counting strips one leading '@' and case-folds (the same rule
radar.py uses), so "@Alpha" and "alpha" count as ONE trader. A mention's row
keeps the exact stored handle as evidence, with a normalised ``handle_key``
alongside.

## Output and ordering
Each returned row: symbol, window (days/start/end), distinct_trader_count,
mention_count, polarity_counts, disagreement, and ``mentions`` -- one dict per
watch_ideas row: handle, handle_key, post_id, polarity, stated_at, the matched
marker strings (``matches``), trigger_text, the verbatim post text, and
``verbatim`` (trigger_text when present, else the post text -- the "verbatim
trigger_text / post excerpt" the API shows). Rows sort by distinct trader count
descending, then symbol ascending (deterministic). The full computation's
coverage debt (invalid timestamps, no text, contaminated, outside window,
below-min-trader symbols) is reported through the optional ``_stats_out`` dict
-- always counted, never silently dropped.

Public contract:
    find_disagreements(conn, days_back=7, min_traders=2, *, now=None,
                       _stats_out=None) -> list[dict]
    summarize(rows) -> dict
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

_KOLKATA = ZoneInfo("Asia/Kolkata")

# ---------------------------------------------------------------------------
# The polarity vocabulary -- THE CONTRACT (see module docstring). v1, crude
# but auditable: exact-match substrings on the lowercased text. Refinements
# extend THESE tables, never ad-hoc logic at call sites.
# ---------------------------------------------------------------------------

BULLISH_MARKERS = frozenset({
    "buy", "bought", "long", "enter", "entered",
    "adding", "added", "accumulat", "breakout", "bullish",
})
BEARISH_MARKERS = frozenset({
    "sell", "sold", "exit", "exited", "avoid", "bearish",
    "short", "distribution", "stopped out",
})

POLARITY_BULLISH = "bullish"
POLARITY_BEARISH = "bearish"
POLARITY_MIXED = "mixed"
POLARITY_NEUTRAL = "neutral"

# The two directional polarities -- the only values that count as a
# "polarity" for the disagreement test; mixed/neutral never do.
_DIRECTIONAL = frozenset({POLARITY_BULLISH, POLARITY_BEARISH})
# Fixed display order for polarity_counts dicts (deterministic JSON).
_POLARITY_ORDER = (
    POLARITY_BULLISH, POLARITY_BEARISH, POLARITY_MIXED, POLARITY_NEUTRAL,
)

_SELECT_SQL = (
    "SELECT w.post_id, w.handle, w.symbol, w.trigger_text, w.stated_at, "
    "       p.text AS post_text "
    "FROM watch_ideas w LEFT JOIN posts p ON p.post_id = w.post_id"
)


# ---------------------------------------------------------------------------
# Pure helpers (unit-testable without a DB)
# ---------------------------------------------------------------------------

def _parse_stated_at(value: Any) -> datetime | None:
    """Parse a watch_ideas.stated_at (IST) value into an aware datetime.

    Aware values are kept (possibly converted from ''Z''/+00:00 to
    Asia/Kolkata); naive values are treated as already IST, matching the
    schema convention that every timestamp is IST (same rule as tape.py).
    Absent or malformed values return None so the caller can count them.
    """
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=_KOLKATA)
    return parsed.astimezone(_KOLKATA)


def _normalize_handle(value: Any) -> str | None:
    """Normalised trader identity: one leading '@' stripped, case-folded."""
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if normalized.startswith("@"):
        normalized = normalized[1:].strip()
    return normalized.casefold() or None


def _is_contaminated(handle: str, text: str) -> bool:
    """Reply-under-tracked-handle capture defect (same rule as watchlists.py
    and insight_tables.py): text that begins with the filed handle's own
    @mention is someone else's reply, not the trader's own words."""
    return (text or "").startswith("@" + handle)


def classify_polarity(text: str) -> str:
    """Polarity of a mention from its OWN text, keyword buckets ONLY.

    Both buckets hit -> "mixed"; zero hits -> "neutral"; exactly one bucket
    -> that polarity. See the module docstring "The polarity vocabulary" for
    the crude-but-auditable v1 matching rule (exact-match substrings on the
    lowercased text).
    """
    lower = (text or "").lower()
    bullish = any(marker in lower for marker in BULLISH_MARKERS)
    bearish = any(marker in lower for marker in BEARISH_MARKERS)
    if bullish and bearish:
        return POLARITY_MIXED
    if bullish:
        return POLARITY_BULLISH
    if bearish:
        return POLARITY_BEARISH
    return POLARITY_NEUTRAL


def _matched_markers(text: str) -> list[str]:
    """The exact marker strings that fired for ``text``, bucket-table order
    (bullish table order, then bearish table order) -- auditable evidence of
    why a polarity was assigned."""
    lower = (text or "").lower()
    out: list[str] = []
    for marker in BULLISH_MARKERS:
        if marker in lower:
            out.append(marker)
    for marker in BEARISH_MARKERS:
        if marker in lower:
            out.append(marker)
    return out


def summarize(rows: list[dict]) -> dict:
    """Counts over a ``find_disagreements`` result, for API display.

    Returns: symbols_total, symbols_with_disagreement, mention_total,
    trader_total (distinct normalised handles across the returned rows) and
    polarity_counts across every returned mention.
    """
    mentions = [m for row in rows for m in row["mentions"]]
    polarity_counts: dict[str, int] = {p: 0 for p in _POLARITY_ORDER}
    traders: set[str] = set()
    for m in mentions:
        polarity_counts[m["polarity"]] = polarity_counts.get(m["polarity"], 0) + 1
        if m["handle_key"]:
            traders.add(m["handle_key"])
    return {
        "symbols_total": len(rows),
        "symbols_with_disagreement": sum(1 for r in rows if r["disagreement"]),
        "mention_total": len(mentions),
        "trader_total": len(traders),
        "polarity_counts": polarity_counts,
    }


# ---------------------------------------------------------------------------
# Derivation core -- pure read. Issues no writes of any kind.
# ---------------------------------------------------------------------------

def find_disagreements(
    conn,
    days_back: int = 7,
    min_traders: int = 2,
    *,
    now: datetime | None = None,
    _stats_out: dict | None = None,
) -> list[dict]:
    """Symbols where traders publicly disagreed inside the rolling window.

    ``days_back`` is the inclusive rolling window length in days
    (stated_at >= now - days_back). ``min_traders`` is the distinct-normalised-
    handle gate a symbol must pass to be reported at all. ``now`` injects the
    clock for deterministic window boundaries (defaults to the current UTC
    time; a naive value is treated as UTC). ``_stats_out``, if given, is
    populated in place with the full computation's counts and coverage debt
    (see module docstring "Rolling window" / "Output and ordering").

    Returns the per-symbol rows described in the module docstring, sorted by
    distinct trader count descending then symbol ascending.
    """
    if not isinstance(days_back, int) or isinstance(days_back, bool) or days_back < 1:
        raise ValueError("days_back must be a positive integer")
    if not isinstance(min_traders, int) or isinstance(min_traders, bool) or min_traders < 1:
        raise ValueError("min_traders must be a positive integer")

    if now is None:
        window_end = datetime.now(timezone.utc)
    elif isinstance(now, datetime):
        window_end = now
        if window_end.tzinfo is None:
            window_end = window_end.replace(tzinfo=timezone.utc)
    else:
        raise ValueError("now must be a datetime or None")
    window_start = window_end - timedelta(days=days_back)

    stats: dict[str, Any] = {
        "requested": {"days_back": days_back, "min_traders": min_traders},
        "window": {"start": window_start.isoformat(), "end": window_end.isoformat()},
        "rows_considered": 0,
        "symbols_qualifying": 0,
        "skipped": {
            "invalid_timestamp": 0,
            "invalid_handle": 0,
            "no_text": 0,
            "contaminated": 0,
            "outside_window": 0,
            "below_min_traders_symbols": 0,
        },
    }

    by_symbol: dict[str, list[dict]] = {}
    for row in conn.execute(_SELECT_SQL).fetchall():
        stats["rows_considered"] += 1

        stated = _parse_stated_at(row["stated_at"])
        if stated is None:
            stats["skipped"]["invalid_timestamp"] += 1
            continue
        if stated < window_start:
            stats["skipped"]["outside_window"] += 1
            continue

        handle_key = _normalize_handle(row["handle"])
        if handle_key is None:
            stats["skipped"]["invalid_handle"] += 1
            continue

        post_text = (row["post_text"] or "").strip()
        trigger_text = (row["trigger_text"] or "").strip()
        text = post_text or trigger_text
        if not text:
            stats["skipped"]["no_text"] += 1
            continue
        if _is_contaminated(row["handle"] or "", text):
            stats["skipped"]["contaminated"] += 1
            continue

        by_symbol.setdefault(str(row["symbol"]), []).append({
            "handle": row["handle"],
            "handle_key": handle_key,
            "post_id": str(row["post_id"]),
            "stated_at": row["stated_at"],
            "polarity": classify_polarity(text),
            "matches": _matched_markers(text),
            "trigger_text": trigger_text or None,
            "text": post_text or None,
            # The verbatim span the API quotes: the trigger_text when the
            # row has one, else the post text (the "post excerpt").
            "verbatim": trigger_text or post_text,
        })

    rows: list[dict] = []
    for symbol in sorted(by_symbol):
        mentions = sorted(
            by_symbol[symbol],
            key=lambda m: (m["stated_at"] or "", m["post_id"]),
        )
        trader_count = len({m["handle_key"] for m in mentions})
        if trader_count < min_traders:
            stats["skipped"]["below_min_traders_symbols"] += 1
            continue

        directional = {m["polarity"] for m in mentions} & _DIRECTIONAL
        polarity_counts: dict[str, int] = {p: 0 for p in _POLARITY_ORDER}
        for m in mentions:
            polarity_counts[m["polarity"]] += 1
        rows.append({
            "symbol": symbol,
            "window": {
                "days": days_back,
                "start": window_start.isoformat(),
                "end": window_end.isoformat(),
            },
            "distinct_trader_count": trader_count,
            "mention_count": len(mentions),
            "polarity_counts": polarity_counts,
            "polarities": sorted(directional),
            "disagreement": len(directional) >= 2,
            "mentions": mentions,
        })

    rows.sort(key=lambda r: (-r["distinct_trader_count"], r["symbol"]))
    stats["symbols_qualifying"] = len(rows)
    if _stats_out is not None:
        _stats_out.update(stats)
    return rows