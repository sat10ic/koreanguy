from __future__ import annotations

import json

import pytest

from traderlog.db import init_db, now_iso
from traderlog.derive.insight_tables import (
    STANCE_NEUTRAL_WORDS,
    STANCE_RISK_OFF,
    STANCE_RISK_OFF_WORDS,
    STANCE_RISK_ON,
    STANCE_RISK_ON_WORDS,
    THEME_LABELS,
    _match_themes,
    _stance_of,
    _topic_tags_of,
    derive,
    run,
)


# ---------------------------------------------------------------------------
# Helpers -- disposable sqlite DB with known posts/post_class rows
# ---------------------------------------------------------------------------

def _add_trader(conn, handle: str, *, is_mock: int = 0) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO traders (handle, active, is_mock, ingested_at) "
        "VALUES (?,1,?,?)",
        (handle, is_mock, now_iso()),
    )


def _add_post(
    conn,
    post_id: str,
    handle: str,
    kind: str,
    text: str,
    *,
    ts_ist: str = "2026-08-20T09:30:00+05:30",
    symbols: str | None = None,
    confidence: float = 0.9,
    is_mock: int = 0,
) -> None:
    _add_trader(conn, handle, is_mock=is_mock)
    conn.execute(
        "INSERT INTO posts "
        "(post_id,handle,ts_utc,ts_ist,text,url,fetched_at,is_mock,ingested_at) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (post_id, handle, ts_ist, ts_ist, text,
         f"https://x.com/{handle}/status/{post_id}", now_iso(), is_mock, now_iso()),
    )
    conn.execute(
        "INSERT INTO post_class (post_id,kind,confidence,symbols,model,is_mock,ingested_at) "
        "VALUES (?,?,?,?,?,?,?)",
        (post_id, kind, confidence, symbols if symbols is not None else "[]",
         "test-model", is_mock, now_iso()),
    )


def _add_price(conn, symbol: str, trade_date: str = "2026-08-20") -> None:
    conn.execute(
        "INSERT INTO daily_prices (symbol, trade_date, close, source, ingested_at) "
        "VALUES (?,?,?,?,?)",
        (symbol, trade_date, 100.0, "bhavcopy", now_iso()),
    )


@pytest.fixture
def db(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    yield conn
    conn.close()


def _count(conn, table: str) -> int:
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


# ---------------------------------------------------------------------------
# themes
# ---------------------------------------------------------------------------

def test_theme_happy_path_counts_distinct_traders_and_dates(db):
    _add_post(db, "t1", "alpha", "theme",
              "Everywhere Gold and Silver, that is all the noise.",
              ts_ist="2026-08-20T09:00:00+05:30")
    _add_post(db, "t2", "beta", "theme",
              "Gold and Silver both finding support at 50-DMA.",
              ts_ist="2026-08-22T10:00:00+05:30")
    _add_post(db, "t3", "alpha", "theme",
              "All wire and cable firms ran fast in May-June.",
              ts_ist="2026-08-21T11:00:00+05:30")
    db.commit()

    rows, stats = derive(db)
    names = {r["name"]: r for r in rows["themes"]}

    assert stats["themes"]["written"] == 2
    assert names["Gold and Silver"]["mention_count"] == 2  # two distinct traders
    assert names["Gold and Silver"]["first_seen"] == "2026-08-20"
    assert names["Gold and Silver"]["last_seen"] == "2026-08-22"
    assert names["Wire and Cable"]["mention_count"] == 1
    assert stats["themes"]["per_theme"]["Gold and Silver"]["posts"] == 2


def test_theme_alias_merges_only_listed_variants(db):
    # "wire & cable" is a deliberate alias of "wire and cable" -> same theme.
    _add_post(db, "t1", "alpha", "theme", "Wire & cable stocks have lost steam.")
    _add_post(db, "t2", "beta", "theme", "Wire and cable firms leading.")
    # A DIFFERENT literal phrase stays conservatively separate:
    _add_post(db, "t3", "gamma", "theme", "Cables and wires are the leaders.")
    db.commit()

    rows, _ = derive(db)
    assert {r["name"] for r in rows["themes"]} == {"Wire and Cable"}
    row = [r for r in rows["themes"] if r["name"] == "Wire and Cable"][0]
    assert row["mention_count"] == 3


def test_theme_no_invention_guard(db):
    _add_post(db, "t1", "alpha", "theme", "Markets are strong this week.")
    _add_post(db, "t2", "beta", "theme", "Gold and Silver look constructive.")
    db.commit()

    rows, stats = derive(db)
    assert len(rows["themes"]) == 1
    assert stats["themes"]["skipped"]["no_extractable_theme"] == 1


def test_theme_symbols_only_nse_validated(db):
    _add_price(db, "HINDCOPPER")
    _add_post(db, "t1", "alpha", "theme",
              "One of the best days #SILVER #GOLD #HINDCOPPER #NOTREAL.")
    db.commit()

    rows, stats = derive(db)
    assert len(rows["themes"]) == 1
    theme = rows["themes"][0]
    assert json.loads(theme["symbols_json"]) == ["HINDCOPPER"]
    # NOTREAL never invented; counted as unresolved in the stats detail.
    assert theme["mention_count"] == 1


def test_theme_accepts_breadth_posts_naming_a_sector(db):
    _add_post(db, "t1", "alpha", "breadth",
              "Gold and Silver recovered today, crude down. Volatile tape.")
    db.commit()

    rows, stats = derive(db)
    assert [r["name"] for r in rows["themes"]] == ["Gold and Silver"]
    assert stats["themes"]["breadth_contrib_posts"] == 1


def test_theme_stale_row_removed_on_reclassification(db):
    _add_post(db, "t1", "alpha", "theme", "Gold and Silver today.")
    db.commit()
    run(db, "2026-08-20")
    assert _count(db, "themes") == 1

    # Reclassify the only citing post away; the theme must disappear.
    db.execute("UPDATE post_class SET kind='noise' WHERE post_id='t1'")
    db.commit()
    run(db, "2026-08-21")
    assert _count(db, "themes") == 0


# ---------------------------------------------------------------------------
# breadth_notes
# ---------------------------------------------------------------------------

def test_breadth_happy_path_stance_claims_and_symbols(db):
    _add_price(db, "KIMS")
    _add_post(db, "b1", "alpha", "breadth",
              "Market is very bullish today. Adding on strength. #KIMS strong.",
              symbols='["KIMS"]', confidence=0.85)
    db.commit()

    rows, stats = derive(db)
    assert len(rows["breadth_notes"]) == 1
    row = rows["breadth_notes"][0]
    assert row["post_id"] == "b1"
    assert row["handle"] == "alpha"
    assert row["trade_date"] == "2026-08-20"
    assert row["stance"] == STANCE_RISK_ON
    claims = json.loads(row["claims_json"])
    # sentence-final punctuation is retained (verbatim spans)
    assert claims == ["Market is very bullish today.", "Adding on strength.",
                      "#KIMS strong."]
    assert json.loads(row["symbols"]) == ["KIMS"]
    assert row["confidence"] == 0.85
    assert stats["breadth_notes"]["stances"]["risk_on"] == 1


def test_breadth_stance_null_when_not_stated(db):
    _add_post(db, "b1", "alpha", "breadth", "Volatile tape today, watching.")
    db.commit()

    rows, stats = derive(db)
    row = rows["breadth_notes"][0]
    assert row["stance"] is None
    assert stats["breadth_notes"]["stances"]["null"] == 1


def test_breadth_conflicting_stance_is_null_not_guessed(db):
    _add_post(db, "b1", "alpha", "breadth",
              "Bullish at the open but staying light into the close.")
    db.commit()

    rows, stats = derive(db)
    assert rows["breadth_notes"][0]["stance"] is None
    assert stats["breadth_notes"]["ambiguous_stance"] == 1


def test_breadth_risk_off_word(db):
    _add_post(db, "b1", "alpha", "breadth", "Brutal day, staying light.")
    db.commit()
    rows, _ = derive(db)
    assert rows["breadth_notes"][0]["stance"] == STANCE_RISK_OFF


# ---------------------------------------------------------------------------
# edu_items
# ---------------------------------------------------------------------------

def test_edu_happy_path_principle_verbatim_and_literal_tags(db):
    text = "Always use a stop loss and size positions small."
    _add_post(db, "e1", "alpha", "education", text)
    db.commit()

    rows, stats = derive(db)
    assert len(rows["edu_items"]) == 1
    row = rows["edu_items"][0]
    assert row["post_id"] == "e1"
    assert row["handle"] == "alpha"
    assert row["principle_text"] == text
    assert row["title"] == text  # first sentence == whole text when no period
    tags = json.loads(row["topic_tags"])
    assert "stops" in tags and "sizing" in tags
    assert row["stated_at"] == "2026-08-20T09:30:00+05:30"
    assert stats["edu_items"]["tags"].get("stops") == 1


def test_edu_no_literal_tag_produces_empty_tags(db):
    _add_post(db, "e1", "alpha", "education", "Weekly close basis works.")
    db.commit()

    rows, _ = derive(db)
    assert json.loads(rows["edu_items"][0]["topic_tags"]) == []


def test_edu_title_is_first_sentence_only(db):
    _add_post(db, "e1", "alpha", "education",
              "Note down the prior uptrend percentage. Then the consolidation length.")
    db.commit()

    rows, _ = derive(db)
    assert rows["edu_items"][0]["title"] == "Note down the prior uptrend percentage."


# ---------------------------------------------------------------------------
# idempotency / citation integrity / guards
# ---------------------------------------------------------------------------

def test_rerun_is_idempotent_counts_stable(db):
    _add_post(db, "t1", "alpha", "theme",
              "Gold and Silver are the leading groups.")
    _add_post(db, "b1", "beta", "breadth", "Market is very bullish today.")
    _add_post(db, "e1", "gamma", "education",
              "Never blame the market for your losses.")
    db.commit()

    first = run(db, "2026-08-20")
    counts1 = (_count(db, "themes"), _count(db, "breadth_notes"),
               _count(db, "edu_items"))
    second = run(db, "2026-08-21")
    counts2 = (_count(db, "themes"), _count(db, "breadth_notes"),
               _count(db, "edu_items"))

    assert first == second
    assert counts1 == counts2
    assert counts2 == (1, 1, 1)
    # content identical (mention_count untouched by the re-run)
    assert db.execute("SELECT mention_count FROM themes").fetchone()[0] == 1


def test_edu_row_is_updated_in_place_not_duplicated(db):
    _add_post(db, "e1", "alpha", "education", "First version of the lesson.")
    db.commit()
    run(db, "2026-08-20")
    assert _count(db, "edu_items") == 1

    db.execute("UPDATE posts SET text = 'Revised and better lesson.' WHERE post_id='e1'")
    db.commit()
    run(db, "2026-08-21")
    assert _count(db, "edu_items") == 1
    assert db.execute(
        "SELECT principle_text FROM edu_items WHERE post_id='e1'"
    ).fetchone()[0] == "Revised and better lesson."


def test_citation_integrity_every_row_traces_to_a_real_post(db):
    _add_post(db, "t1", "alpha", "theme", "Gold and Silver leading.")
    _add_post(db, "b1", "beta", "breadth", "Very strong selloff today.")
    _add_post(db, "e1", "gamma", "education", "Patience matters more than urge.")
    db.commit()
    run(db, "2026-08-20")

    assert db.execute("SELECT post_id FROM breadth_notes").fetchone()[0] == "b1"
    assert db.execute("SELECT post_id FROM edu_items").fetchone()[0] == "e1"
    # every cited post_id exists in posts
    cited = {r[0] for r in db.execute("SELECT post_id FROM breadth_notes")}
    cited |= {r[0] for r in db.execute("SELECT post_id FROM edu_items")}
    existing = {r[0] for r in db.execute("SELECT post_id FROM posts")}
    assert cited <= existing
    # theme mention_count == distinct traders among the citing (real) posts
    assert db.execute("SELECT mention_count FROM themes").fetchone()[0] == 1
    # breadth/edu rows keep is_mock provenance of their source post
    assert db.execute("SELECT is_mock FROM breadth_notes").fetchone()[0] == 0
    assert db.execute("SELECT is_mock FROM edu_items").fetchone()[0] == 0


def test_contamination_guard_skips_reply_under_own_handle(db):
    _add_post(db, "b1", "alpha", "breadth",
              "@alpha what do you think of today's tape?")
    _add_post(db, "e1", "beta", "education",
              "Stop losses get triggered even in good markets.")
    db.commit()

    rows, stats = derive(db)
    assert len(rows["breadth_notes"]) == 0
    assert len(rows["edu_items"]) == 1
    assert stats["breadth_notes"]["skipped"]["contaminated"] == 1


# ---------------------------------------------------------------------------
# pure-helper unit tests (no DB)
# ---------------------------------------------------------------------------

def test_match_themes_longest_phrase_wins_and_boundaries():
    assert _match_themes("Gold and Silver both finding support") == (
        "Gold and Silver", "gold and silver")
    # bare "gold" boundary: never fires on "golden"
    assert _match_themes("A golden opportunity") == (None, None)
    assert _match_themes("Silver is back") == ("Silver", "silver")
    # "#SILVER" matches the single-word phrase through the '#' boundary
    assert _match_themes("#SILVER at a record high") == ("Silver", "silver")
    # longest matched literal phrase wins: "crude" (5) beats "gold" (4)
    assert _match_themes("Crude at 112 and gold is fine") == ("Crude and Oil", "crude")


def test_match_themes_is_conservative_on_unknown_phrases():
    assert _match_themes("The market is simply chopping around") == (None, None)
    assert _match_themes("") == (None, None)


def test_stance_bucket_disjointness():
    # a single stance value must never live in two buckets, or a text stating
    # it could not resolve unambiguously
    all_words = set(STANCE_RISK_ON_WORDS) | set(STANCE_RISK_OFF_WORDS) | set(STANCE_NEUTRAL_WORDS)
    assert len(all_words) == (
        len(STANCE_RISK_ON_WORDS) + len(STANCE_RISK_OFF_WORDS) + len(STANCE_NEUTRAL_WORDS)
    )


def test_stance_of_explicit_words_only():
    assert _stance_of("Market is very bullish today") == ("risk_on", 1)
    assert _stance_of("Staying light and protecting capital") == ("risk_off", 1)
    assert _stance_of("Sideways tape at the moment") == ("neutral", 1)
    assert _stance_of("Volatile tape, watching.") == (None, 0)
    assert _stance_of("Bullish but staying light") == (None, 2)


def test_topic_tags_literal_only():
    assert _topic_tags_of("Always use a stop loss and size small") == [
        "stops", "sizing"]
    assert _topic_tags_of("Patience matters more than urge") == ["discipline"]
    assert _topic_tags_of("No trigger words here") == []


def test_theme_labels_unique_canonical_keys():
    names = list(THEME_LABELS)
    assert len(names) == len(set(names))