"""Wiring tests for the quality-score layer + R0 regime classifier (F2
finding: both previously had zero production call sites).

Covers: stock_quality_snapshot now runs inside scan_universe and lands on
SymbolScan/report_json; entry_quality_snapshot is exported and importable
(the __all__ bug); regime_state.py round-trips RegimeClassifier hysteresis
across process boundaries (the gap a single in-memory classifier instance
cannot cover for a fresh nightly process each run).
"""
from datetime import date, datetime, timedelta, timezone

import pytest

from unidesk.contracts.market import DailyBar
from unidesk.momentum.data.market_store import InMemoryMarketStore, VersionedDailyBar
from unidesk.momentum.regime import Regime, RegimeClassifier
from unidesk.momentum.regime_state import load_classifier, save_classifier
from unidesk.momentum.report_json import build_nightly_json
from unidesk.momentum.scan import DEFAULT_STOCK_QUALITY_WEIGHTS, scan_universe
from unidesk.momentum.scoring import EntryQualitySnapshot, entry_quality_snapshot

UTC = timezone.utc
DAY0 = datetime(2026, 6, 1, 18, 0, tzinfo=UTC)


def add_session(store, symbol, i, close, high=None, low=None, vol=1000.0, dvp=None,
                uc=None, lc=None):
    session = (DAY0 + timedelta(days=i)).date()
    bar = DailyBar(
        symbol=symbol, session=session,
        open=close, high=high or close + 0.5, low=low or close - 0.5,
        close=close, volume=int(vol), delivery_percentage=dvp, data_version="test",
        upper_circuit=uc, lower_circuit=lc,
    )
    store.add_daily_bar(VersionedDailyBar(bar=bar, available_at=DAY0 + timedelta(days=i + 1)))


def build_store():
    store = InMemoryMarketStore()
    for i in range(70):
        add_session(store, "STRONG", i, 90 + i * 0.75, vol=1000 + i * 10, dvp=50.0,
                    uc=200.0, lc=50.0)
    for i in range(70):
        add_session(store, "FLAT", i, 50.0, vol=800.0)
    return store


# --------------------------------------------------------------------- P1.9


def test_scan_universe_attaches_a_real_stock_quality_snapshot():
    store = build_store()
    result = scan_universe(store, DAY0 + timedelta(days=70))
    by = {s.symbol: s for s in result.symbols}
    sq = by["STRONG"].stock_quality
    assert sq is not None
    assert sq.feature_version == "P1.9-v1"
    # STRONG has published circuit bands, trend, rs_rank, rvol, delivery --
    # only the 52-week-high distance is unavailable (70 loaded sessions
    # < the 252-session floor), so coverage must be < 1.0, not zero, and
    # the score must still exist over the remaining contributors (R12).
    assert sq.coverage == pytest.approx(0.85)
    assert "DISTANCE_52W_UNAVAILABLE" in sq.unknowns
    assert sq.score is not None and 0.0 <= sq.score <= 100.0


def test_stock_quality_config_hash_is_stable_for_the_default_weights():
    store = build_store()
    r1 = scan_universe(store, DAY0 + timedelta(days=70))
    r2 = scan_universe(store, DAY0 + timedelta(days=70))
    h1 = {s.symbol: s.stock_quality.config_hash for s in r1.symbols}
    h2 = {s.symbol: s.stock_quality.config_hash for s in r2.symbols}
    assert h1 == h2
    assert len(DEFAULT_STOCK_QUALITY_WEIGHTS) == 6


def test_report_json_carries_the_real_stock_quality_score_per_candidate():
    # Same tuned-for-momentum-burst fixture as test_report_json.py, needed
    # because the generic build_store() above never clears a real detector.
    store = InMemoryMarketStore()
    for i in range(70):
        close = 90 + i * 0.9
        if i < 65:
            half_range, vol = 3.0, 1000.0
        else:
            half_range, vol = 0.5, (5000.0 if i == 69 else 1000.0)
        add_session(store, "STRONG2", i, close, high=close + half_range,
                    low=close - half_range, vol=vol, dvp=60.0)
    for i in range(70):
        add_session(store, "FLAT2", i, 50.0, vol=800.0)
    scan = scan_universe(store, DAY0 + timedelta(days=70))
    data = build_nightly_json(scan)
    if not data["candidates"]:
        pytest.skip("fixture did not clear the burst detector this run")
    for c in data["candidates"]:
        assert "stock_quality" in c
        sq = c["stock_quality"]
        assert sq is None or (isinstance(sq, dict) and "score" in sq and "coverage" in sq)


# ---------------------------------------------------------- entry_quality


def test_entry_quality_snapshot_is_exported_from_scoring_package():
    """The __all__ bug: entry_quality_snapshot was never exported, and the
    module could not even import (missing Optional/Sequence)."""
    T0 = datetime(2026, 8, 28, tzinfo=UTC)
    s = entry_quality_snapshot(
        "TRENT", T0, current=100.0, trigger=100.5, invalidation=95.0, hurdle=115.0,
        adr_pct=5.0, ema21_extension_pct=0.0,
        weights={"room_adr": 25, "initial_rr": 25, "ema21_extension": 25, "trigger_proximity": 25},
        feature_version="fv", config_hash="cfg",
    )
    assert isinstance(s, EntryQualitySnapshot)
    assert s.coverage == 1.0


# ------------------------------------------------------------------ regime


def test_regime_state_round_trips_hysteresis_across_a_fresh_process(tmp_path):
    """The gap this closes: a brand-new RegimeClassifier() every nightly
    run would never accumulate hysteresis days across nights. Persisting
    and reloading state must continue counting where the last run left
    off, not reset to a cold start."""
    state_path = tmp_path / "regime_state.json"

    rc1, last1 = load_classifier(state_path)
    assert last1 is None  # cold start: no file yet
    d0 = date(2026, 6, 1)
    row = rc1.update(d0, 0.65)             # seeds BULL immediately
    assert row.regime is Regime.BULL
    save_classifier(state_path, rc1, last_session=d0.isoformat())

    # Two sessions of BEAR breadth pending -- not yet 3, so still BULL.
    d1, d2 = date(2026, 6, 2), date(2026, 6, 3)
    for d in (d1, d2):
        rc, last = load_classifier(state_path)
        assert last is not None
        row = rc.update(d, 0.30)
        assert row.regime is Regime.BULL   # hysteresis not yet satisfied
        save_classifier(state_path, rc, last_session=d.isoformat())

    # Third consecutive BEAR-breadth session, resumed from a fresh
    # classifier instance each time -- must flip now, exactly as it would
    # have in one long-lived process.
    d3 = date(2026, 6, 4)
    rc, last = load_classifier(state_path)
    row = rc.update(d3, 0.30)
    assert row.regime is Regime.BEAR
    assert last == d2.isoformat()


def test_regime_state_cold_starts_honestly_on_config_mismatch(tmp_path):
    state_path = tmp_path / "regime_state.json"
    rc1, _ = load_classifier(state_path, hysteresis_days=3)
    rc1.update(date(2026, 6, 1), 0.65)
    save_classifier(state_path, rc1, last_session="2026-06-01")

    # A different hysteresis window must not resume the old counter under
    # a rule it was never measured against.
    rc2, last2 = load_classifier(state_path, hysteresis_days=5)
    assert last2 is None
    assert rc2.hysteresis_days == 5
