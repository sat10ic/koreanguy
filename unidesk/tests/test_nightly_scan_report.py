"""N1 tests: universe scan + nightly report rendering (deterministic fixtures)
plus the real-backlog smoke run."""
from datetime import datetime, timedelta, timezone

import pytest

from unidesk.contracts.market import DailyBar
from unidesk.momentum.data.market_store import InMemoryMarketStore, VersionedDailyBar
from unidesk.momentum.detectors.momentum_burst import Detection
from unidesk.momentum.report import build_nightly_report
from unidesk.momentum.data.corp_actions import ConfirmedAction
from unidesk.momentum.scan import scan_universe

UTC = timezone.utc
DAY0 = datetime(2026, 6, 1, 18, 0, tzinfo=UTC)


def add_session(store, symbol, i, close, high=None, low=None, vol=1000.0, dvp=None):
    session = (DAY0 + timedelta(days=i)).date()
    bar = DailyBar(
        symbol=symbol, session=session,
        open=close, high=high or close + 0.5, low=low or close - 0.5,
        close=close, volume=int(vol),
        delivery_percentage=dvp, data_version="test",
    )
    store.add_daily_bar(VersionedDailyBar(bar=bar, available_at=DAY0 + timedelta(days=i + 1)))


def build_store():
    store = InMemoryMarketStore()
    # STRONG: steady uptrend 90 -> 140 (clearly expanding, RS leader)
    for i in range(70):
        add_session(store, "STRONG", i, 90 + i * 0.75, vol=1000 + i * 10, dvp=50.0)
    # FLAT: constant price (real zeros; low RS rank)
    for i in range(70):
        add_session(store, "FLAT", i, 50.0, vol=800.0)
    return store


def test_scan_produces_named_features_point_in_time():
    store = build_store()
    result = scan_universe(store, DAY0 + timedelta(days=70))
    assert result.scanned == 2
    by = {s.symbol: s for s in result.symbols}
    strong = by["STRONG"]
    assert strong.trend.value == "STRONG_UPTREND"
    assert strong.adr_pct is not None and strong.rvol is not None
    assert strong.rs_rank == pytest.approx(75.0)    # mid-rank of 2 names: (1+0.5)/2
    flat = by["FLAT"]
    assert flat.trend.value in ("TRANSITION", "WEAK", "UNKNOWN")


def test_scan_respects_publication_time():
    store = build_store()
    # one hour before the last bar's available_at: that bar must be invisible
    result = scan_universe(store, DAY0 + timedelta(days=69, hours=2))
    by = {s.symbol: s for s in result.symbols}
    assert by["STRONG"].sessions == 69               # last session not yet published


def test_report_contains_sections_and_named_numbers():
    store = build_store()
    result = scan_universe(store, DAY0 + timedelta(days=70))
    report = build_nightly_report(result)
    assert "# Tonight's Report" in report
    assert "## Setups" in report
    assert "## Honesty footer" in report
    assert "not built yet" in report                 # regime placeholder is honest
    assert "not recommendations" in report
    assert "Unadjusted prices" in report


def test_report_footer_counts_skips():
    store = build_store()
    store.add_daily_bar(VersionedDailyBar(
        bar=DailyBar(symbol="SHORTY", session=(DAY0 + timedelta(days=3)).date(),
                     open=10, high=11, low=9, close=10, volume=100,
                     data_version="test"),
        available_at=DAY0 + timedelta(days=4)))
    result = scan_universe(store, DAY0 + timedelta(days=70))
    report = build_nightly_report(result)
    assert "insufficient history" in report


def test_real_backlog_scan_smoke():
    """First end-to-end nightly scan over the real ingested backlog."""
    from pathlib import Path
    from unidesk.momentum.data.bhavcopy import ingest_directory

    backlog = Path(__file__).resolve().parents[2] / "bhavcopy_extractor" / "data" / "bhavcopy"
    if not backlog.exists():
        pytest.skip("backlog not present")
    store = InMemoryMarketStore()
    ingest_directory(store, backlog, limit_files=12)
    result = scan_universe(store, datetime(2026, 6, 30, 18, 30, tzinfo=UTC), min_sessions=9)
    assert result.scanned > 50
    burst = [s for s in result.symbols
             if s.detectors.get("momentum_burst", (None,))[0] is Detection.VALID]
    assert isinstance(burst, list)
    report = build_nightly_report(result)
    assert "Momentum Burst" in report or "No candidates passed" in report


def test_scan_applies_confirmed_split_without_mutating_raw():
    store = InMemoryMarketStore()
    for i in range(70):
        add_session(store, "SPLIT", i, 200.0 if i < 35 else 100.0, vol=1000)
    for i in range(70):
        add_session(store, "FLAT", i, 50.0, vol=800)
    raw = [b.bar.close for b in store._daily if b.bar.symbol == "SPLIT"]
    assert raw[0] == 200.0 and raw[35] == 100.0
    ex = (DAY0 + timedelta(days=35)).date()
    actions = [ConfirmedAction("SPLIT", ex, 0.5, "test")]
    result = scan_universe(store, DAY0 + timedelta(days=70), actions=actions)
    by = {s.symbol: s for s in result.symbols}
    assert result.adjusted_symbols == 1
    assert result.actions_applied == 1
    assert by["SPLIT"].close == pytest.approx(100.0)
    assert by["SPLIT"].ema50 == pytest.approx(100.0, abs=1.0)
    assert [b.bar.close for b in store._daily if b.bar.symbol == "SPLIT"] == raw
    report = build_nightly_report(result)
    assert "derived view" in report
    assert "Unadjusted prices" not in report
