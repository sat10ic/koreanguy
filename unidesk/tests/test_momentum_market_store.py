from dataclasses import FrozenInstanceError
from datetime import date, datetime, timedelta, timezone

import pytest

from unidesk.contracts.base import ContractError
from unidesk.contracts.market import DailyBar, IntradayBar, SymbolMaster, Timeframe
from unidesk.momentum.data.market_store import (
    InMemoryMarketStore,
    VersionedDailyBar,
    VersionedIntradayBar,
)
from unidesk.momentum.universe.symbol_master import SymbolClassification, normalize_symbol

UTC = timezone.utc


def ts(day, hour=0, minute=0):
    return datetime(2025, 1, day, hour, minute, tzinfo=UTC)


def master(symbol="ACME"):
    return SymbolMaster(symbol, "NSE", "acme-token", "Acme Ltd", "Tech", "Software", "MID", (), (), (), date(2020, 1, 1), True, date(2020, 1, 1))


def daily(version="v1", session=date(2025, 1, 2), delivery=None, upper=None):
    return DailyBar("ACME", session, 10, 12, 9, 11, 100, delivery_quantity=delivery, upper_circuit=upper, data_version=version)


def intraday(version="v1", when=ts(2, 10)):
    return IntradayBar("ACME", when, Timeframe.FIVE_MIN, 10, 11, 9, 10.5, 50, version)


def classification(version="c1", start=ts(1), end=None, available=ts(1), sector="Tech"):
    source = master()
    source = SymbolMaster(source.symbol, source.exchange, source.instrument_token, source.company_name, sector, source.industry, source.market_cap_bucket, source.index_membership, source.theme_tags, source.surveillance_flags, source.listing_date, source.active, source.valid_from, source.valid_to)
    return SymbolClassification(source, start, end, available, version)


def test_normalize_symbol_is_exact_and_provider_neutral():
    assert normalize_symbol(" acme-1 ") == "ACME-1"
    for invalid in ("NSE:ACME", "ACME/NS", "A B", "", ".ACME", "a" * 33):
        with pytest.raises(ContractError):
            normalize_symbol(invalid)


def test_classification_is_effective_and_available_point_in_time():
    store = InMemoryMarketStore()
    store.add_classification(classification("old", ts(1), ts(4), ts(1), "Old"))
    store.add_classification(classification("future", ts(4), None, ts(5), "New"))
    assert store.get_market_state("acme", ts(3)).classification.master.sector == "Old"
    assert store.get_market_state("ACME", ts(4)).classification is None
    assert store.get_market_state("ACME", ts(5)).classification.master.sector == "New"


def test_later_revision_cannot_leak_backwards_and_latest_available_wins():
    store = InMemoryMarketStore()
    store.add_daily_bar(VersionedDailyBar(daily("first"), ts(2, 16)))
    store.add_daily_bar(VersionedDailyBar(daily("revision"), ts(4, 9)))
    assert store.get_market_state("ACME", ts(3)).daily_bar.bar.data_version == "first"
    assert store.get_market_state("ACME", ts(4, 9)).daily_bar.bar.data_version == "revision"


def test_future_and_same_session_eod_bars_are_hidden_until_available():
    store = InMemoryMarketStore()
    store.add_daily_bar(VersionedDailyBar(daily("today"), ts(2, 15, 31)))
    store.add_daily_bar(VersionedDailyBar(daily("future", date(2025, 1, 3)), ts(3, 15, 31)))
    assert store.get_market_state("ACME", ts(2, 15, 30)).daily_bar is None
    assert store.get_market_state("ACME", ts(2, 16)).daily_bar.bar.data_version == "today"
    assert store.get_market_state("ACME", ts(2, 16)).daily_bar.bar.session == date(2025, 1, 2)


def test_intraday_never_returns_future_bar_or_future_revision():
    store = InMemoryMarketStore()
    store.add_intraday_bar(VersionedIntradayBar(intraday("early", ts(2, 10)), ts(2, 10, 1)))
    store.add_intraday_bar(VersionedIntradayBar(intraday("revised", ts(2, 10)), ts(2, 11)))
    store.add_intraday_bar(VersionedIntradayBar(intraday("future", ts(2, 12)), ts(2, 12, 1)))
    state = store.get_market_state("ACME", ts(2, 10, 30))
    assert [item.bar.data_version for item in state.intraday_bars] == ["early"]
    assert store.get_market_state("ACME", ts(2, 11)).intraday_bars[0].bar.data_version == "revised"


def test_duplicates_and_equal_available_revisions_fail_closed():
    store = InMemoryMarketStore()
    first = VersionedDailyBar(daily("v1"), ts(2, 16))
    store.add_daily_bar(first)
    with pytest.raises(ContractError, match="duplicate"):
        store.add_daily_bar(first)
    with pytest.raises(ContractError, match="ambiguous"):
        store.add_daily_bar(VersionedDailyBar(daily("v2"), ts(2, 16)))


def test_timestamps_must_be_aware_and_results_are_frozen():
    with pytest.raises(ContractError, match="timezone-aware"):
        VersionedDailyBar(daily(), datetime(2025, 1, 2, 16))
    store = InMemoryMarketStore()
    store.add_daily_bar(VersionedDailyBar(daily(delivery=None, upper=None), ts(2, 16)))
    state = store.get_market_state("ACME", ts(2, 16))
    assert state.daily_bar.bar.delivery_quantity is None
    assert state.daily_bar.bar.upper_circuit is None
    with pytest.raises(FrozenInstanceError):
        state.symbol = "OTHER"


def test_missing_surveillance_remains_none_and_intraday_cannot_precede_completion():
    store = InMemoryMarketStore()
    store.add_classification(classification())
    state = store.get_market_state("ACME", ts(2))
    assert state.classification.surveillance_state is None
    with pytest.raises(ContractError, match="cannot precede"):
        VersionedIntradayBar(intraday(when=ts(2, 10)), ts(2, 9, 59))


def test_surveillance_empty_tuple_distinct_from_none():
    """CP-2 finding 5: `()` (feed explicitly reported no flags) must survive
    storage and query distinctly from None (feed provided nothing)."""
    from unidesk.momentum.universe.symbol_master import SymbolClassification

    def classification(surveillance_state):
        return SymbolClassification(
            master=master("TRENT"),
            effective_from=ts(1),
            effective_to=None,
            available_at=ts(1),
            version="v1",
            surveillance_state=surveillance_state,
        )

    store = InMemoryMarketStore()
    store.add_classification(classification(()))
    state_empty = store.get_market_state("TRENT", ts(5))
    assert state_empty.classification.surveillance_state == ()   # explicit no-flags

    store2 = InMemoryMarketStore()
    store2.add_classification(classification(None))
    state_none = store2.get_market_state("TRENT", ts(5))
    assert state_none.classification.surveillance_state is None  # feed silent
    assert state_none.classification.surveillance_state != ()
