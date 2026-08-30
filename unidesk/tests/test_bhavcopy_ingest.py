"""Bhavcopy ingestion tests: header variants, EQ filter, numeric skips,
point-in-time publication policy — against a tiny synthetic fixture in the
real wire format."""
from datetime import datetime, timezone

import pytest

from unidesk.contracts.base import ContractError
from unidesk.momentum.data.bhavcopy import (
    BhavcopyIngestError, load_into_store, parse_bhavcopy_file,
)
from unidesk.momentum.data.market_store import InMemoryMarketStore

UTC = timezone.utc

FIXTURE = (
    "SYMBOL, SERIES, DATE1, PREV_CLOSE, OPEN_PRICE, HIGH_PRICE, LOW_PRICE, "
    "LAST_PRICE, CLOSE_PRICE, AVG_PRICE, TTL_TRD_QNTY, TURNOVER_LACS, "
    "NO_OF_TRADES, DELIV_QTY, DELIV_PER\n"
    "TRENT, EQ, 01-Apr-2025, 100.00, 101.00, 105.00, 100.50, 104.00, 104.00, 103.00, 50000, 520.00, 4000, 20000, 40.00\n"
    "trent, EQ, 02-Apr-2025, 104.00, 104.50, 106.00, 103.00, 105.50, 105.50, 104.80, 60000, 630.00, 4500, 30000, 50.00\n"
    "TRENT, BE, 02-Apr-2025, 104.00, 104.50, 106.00, 103.00, 105.50, 105.50, 104.80, 10, 0.10, 2, 5, 50.00\n"
    "OTHERSYM, EQ, 02-Apr-2025, 50.00, , 52.00, 49.00, 51.00, 51.00, 51.00, 100, 1.00, 5, 50, 50.00\n"
)


@pytest.fixture()
def fixture_file(tmp_path):
    p = tmp_path / "cm01Apr2025bhav.csv"
    p.write_text(FIXTURE, encoding="utf-8")
    return p


def test_parse_normalizes_symbols_and_filters_series(fixture_file):
    rows, stats = parse_bhavcopy_file(fixture_file)
    symbols = [r["symbol"] for r in rows]
    assert symbols.count("TRENT") == 2          # both cases normalize, BE filtered out
    unpriced = [r for r in rows if r["symbol"] == "OTHERSYM"]
    assert unpriced and unpriced[0]["open"] is None   # parse keeps it; load skips it
    assert stats["skipped_symbols"] == 0


def test_parse_dates_and_delivery(fixture_file):
    rows, _stats = parse_bhavcopy_file(fixture_file)
    r0 = rows[0]
    assert r0["session"] == datetime(2025, 4, 1).date()
    assert r0["close"] == 104.0
    assert r0["delivery_pct"] == 40.0


def test_nonnormalizable_symbol_skipped_and_counted(tmp_path):
    # `&` IS part of the amended charset (M&M is a real NSE stock), so M&M
    # ingests; a genuinely malformed identifier (embedded space) is skipped+counted.
    bad = tmp_path / "cm01Apr2025bhav.csv"
    bad.write_text(
        "SYMBOL, SERIES, DATE1, PREV_CLOSE, OPEN_PRICE, HIGH_PRICE, LOW_PRICE, "
        "LAST_PRICE, CLOSE_PRICE, AVG_PRICE, TTL_TRD_QNTY, TURNOVER_LACS, "
        "NO_OF_TRADES, DELIV_QTY, DELIV_PER\n"
        "M&M, EQ, 01-Apr-2025, 100.00, 101.00, 105.00, 100.50, 104.00, 104.00, 103.00, 50000, 520.00, 4000, 20000, 40.00\n"
        "TRENT LTD, EQ, 01-Apr-2025, 100.00, 101.00, 105.00, 100.50, 104.00, 104.00, 103.00, 50000, 520.00, 4000, 20000, 40.00\n"
        "TRENT, EQ, 01-Apr-2025, 100.00, 101.00, 105.00, 100.50, 104.00, 104.00, 103.00, 50000, 520.00, 4000, 20000, 40.00\n",
        encoding="utf-8",
    )
    rows, stats = parse_bhavcopy_file(bad)
    assert [r["symbol"] for r in rows] == ["M&M", "TRENT"]
    assert stats["skipped_symbols"] == 1


def test_unparseable_number_fails_loudly(tmp_path):
    bad = tmp_path / "cm01Apr2025bhav.csv"
    bad.write_text(
        "SYMBOL, SERIES, DATE1, PREV_CLOSE, OPEN_PRICE, HIGH_PRICE, LOW_PRICE, "
        "LAST_PRICE, CLOSE_PRICE, AVG_PRICE, TTL_TRD_QNTY, TURNOVER_LACS, "
        "NO_OF_TRADES, DELIV_QTY, DELIV_PER\n"
        "TRENT, EQ, 01-Apr-2025, 100.00, N/A, 105.00, 100.50, 104.00, 104.00, 103.00, 50000, 520.00, 4000, 20000, 40.00\n",
        encoding="utf-8",
    )
    with pytest.raises(BhavcopyIngestError):
        parse_bhavcopy_file(bad)


def test_load_into_store_applies_publication_policy(fixture_file):
    from unidesk.contracts.market import DailyBar

    store = InMemoryMarketStore()
    rows, _stats = parse_bhavcopy_file(fixture_file)
    added, dups = load_into_store(store, rows)
    assert added == 2 and dups == 0              # unpriced OTHERSYM row skipped at load
    state = store.get_market_state("TRENT", datetime(2025, 4, 1, 10, 0, tzinfo=UTC))
    assert state.daily_bar is None               # 10:00 IST same day: bar not yet available
    state2 = store.get_market_state("TRENT", datetime(2025, 4, 2, 6, 0, tzinfo=UTC))
    assert state2.daily_bar is not None          # 18:00 IST published, visible next morning
    assert state2.daily_bar.bar.close == 104.0


def test_extended_archive_is_the_d15_home():
    from pathlib import Path
    archive = Path(__file__).resolve().parents[2] / "data" / "bhavcopy"
    if not archive.exists():
        pytest.skip("extended archive not present")
    files = [p for p in archive.iterdir()
             if p.suffix.lower() == ".csv" and "bhav" in p.name.lower()]
    assert len(files) >= 400  # D15: 503 files / 477 sessions as of 2026-08-29


def test_real_backlog_directory_smoke():
    """First real-data contact: ingest a few actual backlog files and sanity
    check the shape of what comes out. Skipped if the backlog is absent."""
    from pathlib import Path

    backlog = Path(__file__).resolve().parents[2] / "data" / "bhavcopy"
    if not backlog.exists():
        pytest.skip("bhavcopy backlog not present")
    store = InMemoryMarketStore()
    from unidesk.momentum.data.bhavcopy import ingest_directory

    stats = ingest_directory(store, backlog, limit_files=3)
    assert stats["bars_added"] > 1000
    assert stats["files"] == 3
    state = store.get_market_state("TRENT", datetime(2026, 7, 1, tzinfo=UTC))
    assert state.daily_bar is not None           # Apr 2025 files cover TRENT
    bar = state.daily_bar.bar
    assert 0 < bar.delivery_percentage <= 100
    assert bar.low <= bar.high
