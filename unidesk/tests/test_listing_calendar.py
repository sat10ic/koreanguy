"""NSE listing-calendar ingest + listing-age feature (trust.py's ipo_base is
BLOCKED on ``listing_age_is_not_verified``; these tests cover the calendar
this repo never had, not a trust-status change -- that stays owner-gated).
"""
from __future__ import annotations

import json
from datetime import date

import pytest

from unidesk.momentum.data.calendar import from_sessions
from unidesk.momentum.data.listing_calendar import (
    content_hash,
    listing_age_sessions_for,
    load_listing_calendar,
    normalize_nse_equity_master,
    persist_listing_calendar,
    sessions_since_listing,
    write_normalized_csv,
)
from unidesk.momentum.data.events import parse_ipo_listings

BOM = "﻿"

# Shaped exactly like a real NSE EQUITY_L.csv slice: stray leading spaces on
# every header after the first (NSE's own formatting), DD-MON-YYYY dates.
FAKE_NSE_CSV = (
    BOM + "SYMBOL,NAME OF COMPANY, SERIES, DATE OF LISTING, PAID UP VALUE,"
    " MARKET LOT, ISIN NUMBER, FACE VALUE\n"
    "AGL,Alpha Logistics Limited,EQ,03-JUL-2026,10,1,INE000A01011,10\n"
    "M&M,Mahindra & Mahindra Limited,EQ,01-APR-1969,5,1,INE101A01026,5\n"
    ",No Symbol Row,EQ,01-JAN-2020,10,1,INE000B01011,10\n"
    "BADDATE,Bad Date Row,EQ,not-a-date,10,1,INE000C01011,10\n"
).encode("utf-8")


def _cal(sessions):
    return from_sessions(sessions)


# ---------------------------------------------------------------- parse round-trip


def test_normalize_and_parse_round_trip(tmp_path):
    rows, stats = normalize_nse_equity_master(FAKE_NSE_CSV)
    assert stats["kept"] == 2
    assert stats["skipped"] == 2
    by_symbol = {r["Stock Name"]: r["Listing Date"] for r in rows}
    assert by_symbol["AGL"] == "03-07-2026"
    assert by_symbol["M&M"] == "01-04-1969"

    normalized_path = write_normalized_csv(rows, tmp_path / "ipo_listings_normalized.csv")
    parsed_rows, parsed_stats = parse_ipo_listings(normalized_path)
    assert parsed_stats["kept"] == 2 and parsed_stats["skipped"] == 0
    by = {r["symbol"]: r["listing_date"] for r in parsed_rows}
    assert by["AGL"] == "2026-07-03"
    assert by["M&M"] == "1969-04-01"


def test_normalize_rejects_malformed_rows_without_guessing():
    rows, stats = normalize_nse_equity_master(FAKE_NSE_CSV)
    kept_symbols = {r["Stock Name"] for r in rows}
    assert "BADDATE" not in kept_symbols  # unparseable date -> skipped, not guessed
    assert "" not in kept_symbols          # missing symbol -> skipped


# ---------------------------------------------------------------- listing age feature


def test_unknown_symbol_returns_none():
    cal = _cal([date(2026, 7, 1), date(2026, 7, 2), date(2026, 7, 3)])
    assert sessions_since_listing(cal, None, date(2026, 7, 2)) is None
    assert listing_age_sessions_for(
        "GHOST", date(2026, 7, 2), listing_dates={}, trading_calendar=cal,
    ) is None


def test_future_listing_date_returns_none():
    cal = _cal([date(2026, 7, 1), date(2026, 7, 2), date(2026, 7, 3)])
    # Listed AFTER the as-of session -- not listed yet at that point in time.
    assert sessions_since_listing(cal, date(2026, 7, 3), date(2026, 7, 1)) is None


def test_listing_date_not_an_observed_session_returns_none():
    cal = _cal([date(2026, 7, 1), date(2026, 7, 2), date(2026, 7, 3)])
    # listing_date itself missing from the calendar (warm-up / gap) -- never
    # invent a distance from an unobserved session.
    assert sessions_since_listing(cal, date(2026, 6, 15), date(2026, 7, 3)) is None


def test_sessions_since_listing_counts_listing_day_as_session_one():
    sessions = [date(2026, 7, 1), date(2026, 7, 2), date(2026, 7, 3), date(2026, 7, 6)]
    cal = _cal(sessions)
    assert sessions_since_listing(cal, date(2026, 7, 1), date(2026, 7, 1)) == 1
    assert sessions_since_listing(cal, date(2026, 7, 1), date(2026, 7, 6)) == 4


def test_listing_age_sessions_for_normalizes_symbol():
    cal = _cal([date(2026, 7, 1), date(2026, 7, 2)])
    listing_dates = {"AGL": date(2026, 7, 1)}
    assert listing_age_sessions_for(
        " agl ", date(2026, 7, 2), listing_dates=listing_dates, trading_calendar=cal,
    ) == 2


# ---------------------------------------------------------------- hashing + persistence


def test_content_hash_is_stable_and_content_sensitive():
    h1 = content_hash(FAKE_NSE_CSV)
    h2 = content_hash(FAKE_NSE_CSV)
    assert h1 == h2
    assert h1 != content_hash(FAKE_NSE_CSV + b"\n")


def test_load_listing_calendar_missing_file_returns_empty(tmp_path):
    assert load_listing_calendar(tmp_path / "nope.parquet") == {}


def test_persist_and_load_round_trip(tmp_path):
    rows = [
        {
            "symbol": "AGL",
            "listing_date": "2026-07-03",
            "source_tier": "NSE_EQUITY_MASTER",
            "source_file": "EQUITY_L.csv",
            "content_hash": "deadbeefdeadbeef",
            "snapshot_date": "2026-07-04",
            "first_seen_at": "2026-07-04T00:00:00+00:00",
        },
    ]
    path = persist_listing_calendar(rows, tmp_path / "listing_calendar.parquet")
    loaded = load_listing_calendar(path)
    assert loaded == {"AGL": date(2026, 7, 3)}


def test_absent_symbol_does_not_crash_a_scan(tmp_path):
    """A snapshot covering only some symbols must not raise for the rest --
    the scan degrades to None per symbol, never crashes the loop."""
    rows = [{
        "symbol": "AGL", "listing_date": "2026-07-03", "source_tier": "NSE_EQUITY_MASTER",
        "source_file": "EQUITY_L.csv", "content_hash": "abc", "snapshot_date": "2026-07-04",
        "first_seen_at": "2026-07-04T00:00:00+00:00",
    }]
    path = persist_listing_calendar(rows, tmp_path / "listing_calendar.parquet")
    listing_dates = load_listing_calendar(path)
    cal = _cal([date(2026, 7, 3), date(2026, 7, 6)])

    results = {}
    for symbol in ("AGL", "NOTPRESENT", "ALSO_MISSING"):
        results[symbol] = listing_age_sessions_for(
            symbol, date(2026, 7, 6), listing_dates=listing_dates, trading_calendar=cal,
        )
    # TRADING-SESSION age, listing day = session 1 (documented convention on
    # sessions_since_listing — it replaces build_setup_inputs' bar-count
    # proxy, so ipo_base's 61-session floor keeps its meaning). The fixture
    # calendar holds 07-03 and 07-06: AGL is 2 sessions old at as_of. (The
    # original draft expected 4 — calendar days 03..06 — the wrong unit.)
    assert results["AGL"] == 2
    assert results["NOTPRESENT"] is None
    assert results["ALSO_MISSING"] is None


# ---------------------------------------------------------------- ingest idempotency


def test_ingest_idempotent_same_hash_and_first_seen_at(tmp_path, monkeypatch):
    import unidesk.run_ingest_listing_calendar as ingest

    monkeypatch.setattr(ingest, "DEFAULT_SNAPSHOT_ROOT", tmp_path / "listing_calendar")
    monkeypatch.setattr(ingest, "DEFAULT_LATEST_PARQUET", tmp_path / "listing_calendar.parquet")

    snap_date = date(2026, 7, 4)
    rc1 = ingest.run(snapshot_date=snap_date, raw_bytes=FAKE_NSE_CSV)
    assert rc1 == 0
    manifest_path = tmp_path / "listing_calendar" / "2026-07-04" / "manifest.json"
    manifest1 = json.loads(manifest_path.read_text(encoding="utf-8"))

    rc2 = ingest.run(snapshot_date=snap_date, raw_bytes=FAKE_NSE_CSV)
    assert rc2 == 0
    manifest2 = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest1["content_hash"] == manifest2["content_hash"]
    assert manifest1["first_seen_at"] == manifest2["first_seen_at"]

    loaded = load_listing_calendar(tmp_path / "listing_calendar.parquet")
    assert len(loaded) == 2  # AGL, M&M -- not duplicated by the second run
    assert loaded["AGL"] == date(2026, 7, 3)


def test_ingest_stops_on_schema_mismatch_without_writing(tmp_path, monkeypatch):
    import unidesk.run_ingest_listing_calendar as ingest

    monkeypatch.setattr(ingest, "DEFAULT_SNAPSHOT_ROOT", tmp_path / "listing_calendar")
    monkeypatch.setattr(ingest, "DEFAULT_LATEST_PARQUET", tmp_path / "listing_calendar.parquet")

    garbage = "NOT,THE,RIGHT,COLUMNS\n1,2,3,4\n".encode("utf-8")
    rc = ingest.run(snapshot_date=date(2026, 7, 4), raw_bytes=garbage)
    assert rc == 1
    assert not (tmp_path / "listing_calendar").exists()
    assert not (tmp_path / "listing_calendar.parquet").exists()
