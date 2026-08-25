"""B1 Disagreement-feed engine tests (derive/disagreement.py).

Pure-read derivation over watch_ideas + posts on disposable databases.
Locks: the verbatim keyword buckets and their crude substring-matching rule;
the never-guessed polarity outcomes (both-bucket hit -> mixed, zero-hit ->
neutral); the disagreement test (both directional polarities present for the
symbol, mixed/neutral excluded); the min_traders distinct-handle gate; the
rolling days_back window boundary; the handle normalisation rule; and full
citation integrity.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from traderlog.db import init_db, now_iso
from traderlog.derive.disagreement import (
    BEARISH_MARKERS,
    BULLISH_MARKERS,
    POLARITY_BEARISH,
    POLARITY_BULLISH,
    POLARITY_MIXED,
    POLARITY_NEUTRAL,
    classify_polarity,
    find_disagreements,
    summarize,
)

# Fixed injected clock for deterministic window tests. The 7-day cutoff is
# 2026-08-19T12:00:00+00:00 == 2026-08-19T17:30:00+05:30 IST.
NOW = datetime(2026, 8, 26, 12, 0, 0, tzinfo=timezone.utc)

# Valid IST timestamps around the boundary.
TS_INSIDE = "2026-08-20T09:30:00+05:30"
TS_AT_CUTOFF = "2026-08-19T17:30:00+05:30"     # == now - 7 days, inclusive
TS_OUTSIDE = "2026-08-19T17:29:59+05:30"       # one second before the cutoff
TS_OLD = "2026-06-01T09:00:00+05:30"


# ---------------------------------------------------------------------------
# Helpers -- disposable sqlite DB with known traders/posts/watch_ideas rows
# ---------------------------------------------------------------------------

def _add_trader(conn, handle: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO traders (handle, active, is_mock, ingested_at) "
        "VALUES (?,1,0,?)",
        (handle, now_iso()),
    )


def _add_post(conn, post_id: str, handle: str, text: str | None,
              ts_ist: str = TS_INSIDE) -> None:
    _add_trader(conn, handle)
    conn.execute(
        "INSERT INTO posts "
        "(post_id,handle,ts_utc,ts_ist,text,url,fetched_at,is_mock,ingested_at) "
        "VALUES (?,?,?,?,?,?,?,0,?)",
        (post_id, handle, ts_ist, ts_ist, text,
         f"https://x.com/{handle.lstrip('@')}/status/{post_id}",
         now_iso(), now_iso()),
    )


def _add_idea(conn, post_id: str, handle: str, symbol: str, *,
              text: str | None = None, trigger_text: str | None = None,
              stated_at: str = TS_INSIDE) -> None:
    """One trader + post + watch_ideas row naming ``symbol``."""
    _add_post(conn, post_id, handle, text, ts_ist=stated_at)
    conn.execute(
        "INSERT INTO watch_ideas "
        "(post_id,handle,symbol,kind,trigger_text,stated_at,is_mock,ingested_at) "
        "VALUES (?,?,?,?,?,?,0,?)",
        (post_id, handle, symbol, "watch", trigger_text, stated_at, now_iso()),
    )


@pytest.fixture
def db(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    yield conn
    conn.close()


def _rows_by_symbol(rows):
    return {r["symbol"]: r for r in rows}


# ---------------------------------------------------------------------------
# The vocabulary -- the contract. Verbatim from the brief, disjoint buckets.
# ---------------------------------------------------------------------------

def test_vocabulary_is_verbatim_from_the_brief_and_disjoint():
    assert BULLISH_MARKERS == frozenset({
        "buy", "bought", "long", "enter", "entered",
        "adding", "added", "accumulat", "breakout", "bullish",
    })
    assert BEARISH_MARKERS == frozenset({
        "sell", "sold", "exit", "exited", "avoid", "bearish",
        "short", "distribution", "stopped out",
    })
    # a marker may never live in both buckets, or the polarity test would be
    # unable to distinguish the directions
    assert BULLISH_MARKERS.isdisjoint(BEARISH_MARKERS)


# ---------------------------------------------------------------------------
# classify_polarity -- text-only unit tests, no DB
# ---------------------------------------------------------------------------

def test_classify_polarity_bullish_from_each_marker():
    bullish_texts = [
        "I buy the dip in this name",
        "bought 100 shares today",
        "Going long here",
        "Enter above 100",
        "Entered at 95 and holding",
        "Adding to the position",
        "Added 25% more",
        "Accumulating through the base",      # stem: "accumulat"
        "Accumulation phase looks good",
        "Breakout above 1,200 on volume",
        "Bullish thesis intact",
    ]
    for text in bullish_texts:
        assert classify_polarity(text) == POLARITY_BULLISH, text


def test_classify_polarity_bearish_from_each_marker():
    bearish_texts = [
        "Sell into the rally",
        "Sold my full position",
        "Exit the position now",
        "Exited at 90",
        "Avoid this name entirely",
        "Bearish on this sector",
        "Short at 500 with a stop above",
        "Distribution day across the index",
        "My trade stopped out at 95",
    ]
    for text in bearish_texts:
        assert classify_polarity(text) == POLARITY_BEARISH, text


def test_classify_polarity_mixed_when_both_buckets_hit():
    assert classify_polarity("Bought at 100, sold at 110") == POLARITY_MIXED
    assert classify_polarity("Adding to longs but short-term risk") == POLARITY_MIXED
    # contradictory evidence is never resolved in favour of one side
    assert classify_polarity("Entered the breakout, then avoided it") == POLARITY_MIXED


def test_classify_polarity_neutral_when_no_marker_hits():
    for text in ("Watching HDFC Bank today", "Strong watchlist for next week",
                 "No bias here", ""):
        assert classify_polarity(text) == POLARITY_NEUTRAL, text


def test_classify_polarity_is_crude_substring_matching_documented():
    # v1 crudeness (documented in the module docstring): "short" fires inside
    # "shortage", "long" inside "along", "buy" inside "buyback". Locks the
    # crude-but-auditable rule so a future refinement is a conscious change.
    assert classify_polarity("No shortage of sellers") == POLARITY_BEARISH
    assert classify_polarity("Coming along nicely") == POLARITY_BULLISH
    assert classify_polarity("Watch the buyback announcement") == POLARITY_BULLISH


# ---------------------------------------------------------------------------
# Disagreement semantics over disposable DBs
# ---------------------------------------------------------------------------

def test_bullish_vs_bearish_same_symbol_is_disagreement(db):
    _add_idea(db, "d1", "alpha", "D1", text="Buy D1 above 500")
    _add_idea(db, "d2", "beta", "D1", text="Sell D1 into strength")
    db.commit()

    rows = _rows_by_symbol(find_disagreements(db, now=NOW))
    row = rows["D1"]

    assert row["distinct_trader_count"] == 2
    assert row["mention_count"] == 2
    assert row["polarities"] == ["bearish", "bullish"]
    assert row["disagreement"] is True
    assert {m["handle"] for m in row["mentions"]} == {"alpha", "beta"}
    assert {m["polarity"] for m in row["mentions"]} == {POLARITY_BULLISH, POLARITY_BEARISH}


def test_same_polarity_only_is_not_disagreement(db):
    _add_idea(db, "s1", "alpha", "S1", text="Buy S1 above 400")
    _add_idea(db, "s2", "beta", "S1", text="Breakout confirms, bought S1")
    db.commit()

    row = _rows_by_symbol(find_disagreements(db, now=NOW))["S1"]

    assert row["distinct_trader_count"] == 2
    assert row["disagreement"] is False
    assert row["polarities"] == ["bullish"]


def test_mixed_polarity_mention_is_excluded_from_the_polarity_match(db):
    # alpha bullish, beta mixed: no disagreement -- "mixed" is a documented
    # outcome, not a polarity, and never counted as either direction.
    _add_idea(db, "m1", "alpha", "M1", text="Bought M1, adding more")
    _add_idea(db, "m2", "beta", "M1", text="Bought M1, but sold half already")
    db.commit()

    row = _rows_by_symbol(find_disagreements(db, now=NOW))["M1"]

    assert row["disagreement"] is False
    assert row["polarities"] == ["bullish"]
    assert row["polarity_counts"] == {
        "bullish": 1, "bearish": 0, "mixed": 1, "neutral": 0,
    }


def test_neutral_only_mentions_are_not_disagreement(db):
    _add_idea(db, "n1", "alpha", "N1", text="Watching N1 today")
    _add_idea(db, "n2", "beta", "N1", text="N1 on the watchlist")
    db.commit()

    row = _rows_by_symbol(find_disagreements(db, now=NOW))["N1"]

    assert row["disagreement"] is False
    assert row["polarities"] == []
    assert row["polarity_counts"] == {
        "bullish": 0, "bearish": 0, "mixed": 0, "neutral": 2,
    }


# ---------------------------------------------------------------------------
# min_traders gate
# ---------------------------------------------------------------------------

def test_min_traders_gate_excludes_underpopulated_symbols(db):
    # one trader, two mentions (bullish + bearish): polarity-wise a clash,
    # but the default 2-distinct-handle gate must keep it out entirely.
    _add_idea(db, "g1", "alpha", "G1", text="Buy G1 above 300")
    _add_idea(db, "g2", "alpha", "G1", text="Sell G1 at market")
    db.commit()

    stats: dict = {}
    rows = find_disagreements(db, now=NOW, _stats_out=stats)

    assert rows == []
    assert stats["symbols_qualifying"] == 0
    assert stats["skipped"]["below_min_traders_symbols"] == 1

    # same corpus at min_traders=1 surfaces the row (mechanical polarity rule)
    one = _rows_by_symbol(find_disagreements(db, now=NOW, min_traders=1))
    assert one["G1"]["distinct_trader_count"] == 1
    assert one["G1"]["disagreement"] is True


# ---------------------------------------------------------------------------
# days_back rolling window boundary
# ---------------------------------------------------------------------------

def test_days_back_window_boundary_is_inclusive_and_rolling(db):
    # IN: both mentions inside -- one at exactly now-7d (inclusive lower bound),
    # one well inside. OUT: both mentions one second before the cutoff.
    _add_idea(db, "in1", "alpha", "IN", text="Buy IN", stated_at=TS_INSIDE)
    _add_idea(db, "in2", "beta", "IN", text="Sell IN", stated_at=TS_AT_CUTOFF)
    _add_idea(db, "o1", "gamma", "OUT", text="Buy OUT", stated_at=TS_OUTSIDE)
    _add_idea(db, "o2", "delta", "OUT", text="Sell OUT", stated_at=TS_OUTSIDE)
    db.commit()

    stats: dict = {}
    rows = _rows_by_symbol(find_disagreements(db, now=NOW, _stats_out=stats))

    assert set(rows) == {"IN"}
    assert rows["IN"]["mention_count"] == 2
    assert rows["IN"]["window"]["days"] == 7
    assert stats["skipped"]["outside_window"] == 2


def test_window_is_relative_to_now_not_calendar_fixed(db):
    # A 30-day window from a later clock pulls the same corpus back in.
    _add_idea(db, "o1", "gamma", "OLD", text="Buy OLD", stated_at=TS_OLD)
    _add_idea(db, "o2", "delta", "OLD", text="Sell OLD", stated_at=TS_OLD)
    db.commit()

    assert _rows_by_symbol(find_disagreements(db, now=NOW)) == {}
    late = datetime(2026, 7, 2, 0, 0, 0, tzinfo=timezone.utc)
    rows = _rows_by_symbol(find_disagreements(db, now=late, days_back=60))
    assert "OLD" in rows


# ---------------------------------------------------------------------------
# Citations resolve; malformed source rows are counted, never guessed
# ---------------------------------------------------------------------------

def test_citations_resolve_to_real_posts(db):
    _add_idea(db, "d1", "alpha", "D1", text="Buy D1 above 500")
    _add_idea(db, "d2", "beta", "D1", text="Avoid D1 at these levels")
    _add_idea(db, "s1", "alpha", "S1", text="Buy S1")
    _add_idea(db, "s2", "gamma", "S1", text="Sell S1")
    db.commit()

    rows = find_disagreements(db, now=NOW)
    post_ids = {m["post_id"] for r in rows for m in r["mentions"]}
    existing = {r[0] for r in db.execute("SELECT post_id FROM posts")}
    watch_rows = {r[0] for r in db.execute("SELECT post_id FROM watch_ideas")}

    assert post_ids <= existing
    assert post_ids <= watch_rows
    assert post_ids == watch_rows  # no qualifying row lost its citation
    # the mention's handle is the post's actual author
    for r in rows:
        for m in r["mentions"]:
            author = db.execute(
                "SELECT handle FROM posts WHERE post_id=?", (m["post_id"],)
            ).fetchone()[0]
            assert m["handle"] == author


def test_invalid_stated_at_timestamp_is_skipped_and_counted(db):
    _add_idea(db, "t1", "alpha", "TS1", text="Buy TS1")
    _add_idea(db, "t2", "beta", "TS1", text="Sell TS1", stated_at="not-a-timestamp")
    db.commit()

    stats: dict = {}
    rows = find_disagreements(db, now=NOW, _stats_out=stats)

    # the malformed mention is dropped -> only one trader -> gate fails
    assert rows == []
    assert stats["skipped"]["invalid_timestamp"] == 1


def test_contaminated_reply_under_own_handle_is_skipped(db):
    _add_idea(db, "c1", "alpha", "CT1",
              text="@alpha what do you think of CT1?")
    _add_idea(db, "c2", "beta", "CT1",
              text="@beta is CT1 still worth buying?",
              stated_at=TS_AT_CUTOFF)
    db.commit()

    stats: dict = {}
    rows = find_disagreements(db, now=NOW, min_traders=1, _stats_out=stats)

    assert rows == []
    assert stats["skipped"]["contaminated"] == 2


def test_verbatim_trigger_text_used_when_post_text_is_null(db):
    # watchlists writes trigger_text only on single-symbol posts; when the
    # post text itself is NULL, the engine must fall back to the trigger_text
    # as the mention's own verbatim words and classify from it.
    _add_trader(db, "alpha")
    db.execute(
        "INSERT INTO posts (post_id,handle,ts_utc,ts_ist,text,url,fetched_at,is_mock,ingested_at) "
        "VALUES ('f1','alpha',?,?,NULL,'https://x.com/alpha/status/f1',?,0,?)",
        (TS_INSIDE, TS_INSIDE, now_iso(), now_iso()),
    )
    db.execute(
        "INSERT INTO watch_ideas (post_id,handle,symbol,kind,trigger_text,stated_at,is_mock,ingested_at) "
        "VALUES ('f1','alpha','F1','watch','buy above 1,240 on volume',?,0,?)",
        (TS_INSIDE, now_iso()),
    )
    _add_idea(db, "f2", "beta", "F1", text="Sell F1 into the pop")
    db.commit()

    row = _rows_by_symbol(find_disagreements(db, now=NOW))["F1"]

    alpha_mention = row["mentions"][0]
    assert alpha_mention["post_id"] == "f1"
    assert alpha_mention["trigger_text"] == "buy above 1,240 on volume"
    assert alpha_mention["text"] is None
    assert alpha_mention["verbatim"] == "buy above 1,240 on volume"
    assert alpha_mention["polarity"] == POLARITY_BULLISH
    assert row["disagreement"] is True


def test_invalid_handle_is_skipped_and_counted(db):
    # an empty-string handle passes the NOT NULL column but normalises to
    # None -> the mention is dropped and counted, never guessed-at a trader
    _add_post(db, "h1", "alpha", "Buy HAN", ts_ist=TS_INSIDE)
    db.execute(
        "INSERT INTO watch_ideas (post_id,handle,symbol,kind,trigger_text,stated_at,is_mock,ingested_at) "
        "VALUES ('h1','','HAN','watch',NULL,?,0,?)",
        (TS_INSIDE, now_iso()),
    )
    _add_idea(db, "h2", "beta", "HAN", text="Sell HAN")
    db.commit()

    stats: dict = {}
    rows = find_disagreements(db, now=NOW, _stats_out=stats)

    # only beta's mention survives -> HAN is below the 2-handle gate
    assert rows == []
    assert stats["skipped"]["invalid_handle"] == 1


# ---------------------------------------------------------------------------
# Handle normalisation, ordering, summaries, argument validation
# ---------------------------------------------------------------------------

def test_handle_normalisation_counts_distinct_traders_once(db):
    # "@Alpha" and "alpha" are the SAME trader: two mentions, one trader.
    _add_idea(db, "h1", "@Alpha", "HN1", text="Buy HN1")
    _add_idea(db, "h2", "alpha", "HN1", text="Sell HN1")
    db.commit()

    stats: dict = {}
    rows = find_disagreements(db, now=NOW, _stats_out=stats)
    assert rows == []
    assert stats["skipped"]["below_min_traders_symbols"] == 1

    one = _rows_by_symbol(find_disagreements(db, now=NOW, min_traders=1))
    assert one["HN1"]["distinct_trader_count"] == 1
    # stashed handles keep their exact stored evidence value
    assert {m["handle"] for m in one["HN1"]["mentions"]} == {"@Alpha", "alpha"}


def test_rows_sort_by_trader_count_desc_then_symbol(db):
    _add_idea(db, "a1", "alpha", "A1", text="Sell A1")
    _add_idea(db, "a2", "beta", "A1", text="Avoid A1")
    _add_idea(db, "a3", "gamma", "A1", text="Bearish on A1")
    _add_idea(db, "d1", "alpha", "D1", text="Buy D1")
    _add_idea(db, "d2", "beta", "D1", text="Sell D1")
    _add_idea(db, "s1", "alpha", "S1", text="Buy S1")
    _add_idea(db, "s2", "gamma", "S1", text="Sell S1")
    db.commit()

    rows = find_disagreements(db, now=NOW)

    assert [r["symbol"] for r in rows] == ["A1", "D1", "S1"]
    assert [r["distinct_trader_count"] for r in rows] == [3, 2, 2]
    # tie at 2 broken by symbol ascending
    assert rows[1]["symbol"] < rows[2]["symbol"]


def test_summarize_returns_api_display_counts(db):
    _add_idea(db, "a1", "alpha", "A1", text="Sell A1")
    _add_idea(db, "a2", "beta", "A1", text="Avoid A1")
    _add_idea(db, "a3", "gamma", "A1", text="Bearish on A1")
    _add_idea(db, "d1", "alpha", "D1", text="Buy D1")
    _add_idea(db, "d2", "delta", "D1", text="Sell D1")
    db.commit()

    summary = summarize(find_disagreements(db, now=NOW))

    assert summary["symbols_total"] == 2
    assert summary["symbols_with_disagreement"] == 1
    assert summary["mention_total"] == 5
    # alpha, beta, gamma, delta: 4 distinct traders, alpha counted once
    assert summary["trader_total"] == 4
    assert summary["polarity_counts"] == {
        "bullish": 1, "bearish": 4, "mixed": 0, "neutral": 0,
    }


def test_argument_validation(db):
    with pytest.raises(ValueError):
        find_disagreements(db, days_back=0)
    with pytest.raises(ValueError):
        find_disagreements(db, days_back=1.5)
    with pytest.raises(ValueError):
        find_disagreements(db, min_traders=0)
    with pytest.raises(ValueError):
        find_disagreements(db, now="2026-08-26T12:00:00+00:00")


def test_empty_corpus_is_an_empty_result_with_full_stats(db):
    db.commit()

    stats: dict = {}
    rows = find_disagreements(db, now=NOW, _stats_out=stats)

    assert rows == []
    assert stats["rows_considered"] == 0
    assert stats["symbols_qualifying"] == 0
    assert summarize(rows)["symbols_total"] == 0


def test_defaults_run_without_arguments(db):
    # the brief's default call shape (days_back=7, min_traders=2, real clock)
    # must be callable. stated_at is built relative to the REAL clock so the
    # test cannot drift stale (rolling window, not calendar-fixed).
    from datetime import timedelta

    recent = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(
        timespec="seconds"
    )
    _add_idea(db, "d1", "alpha", "D1", text="Buy D1 now", stated_at=recent)
    _add_idea(db, "d2", "beta", "D1", text="Sell D1 now", stated_at=recent)
    db.commit()

    rows = find_disagreements(db)
    assert _rows_by_symbol(rows)["D1"]["disagreement"] is True