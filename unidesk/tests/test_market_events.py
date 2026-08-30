"""IPO and earnings events must carry point-in-time source evidence."""
from datetime import date, datetime, timezone

import pytest

from unidesk.contracts.base import ContractError
from unidesk.research.market_events import EarningsResultEvent, IPOListingFact


UTC = timezone.utc


def test_listing_fact_keeps_listing_date_separate_from_when_the_source_was_seen():
    fact = IPOListingFact(
        symbol="DEMO",
        isin="INE000A01001",
        listing_date=date(2026, 8, 31),
        source_url="https://www.nseindia.com/market-data/new-stock-exchange-listings-recent",
        available_at=datetime(2026, 8, 29, 12, tzinfo=UTC),
        retrieved_at=datetime(2026, 8, 29, 12, 1, tzinfo=UTC),
        source_hash="a" * 64,
    )

    assert fact.listing_date.isoformat() == "2026-08-31"
    assert fact.available_at < datetime(2026, 8, 31, tzinfo=UTC)


def test_result_event_refuses_an_unverifiable_or_future_known_timestamp():
    with pytest.raises(ContractError, match="retrieved_at"):
        EarningsResultEvent(
            symbol="DEMO",
            period_ended=date(2026, 6, 30),
            received_at=datetime(2026, 8, 1, 10, tzinfo=UTC),
            disseminated_at=datetime(2026, 8, 1, 10, 1, tzinfo=UTC),
            available_at=datetime(2026, 8, 1, 10, 1, tzinfo=UTC),
            retrieved_at=datetime(2026, 8, 1, 10, 0, tzinfo=UTC),
            source_url="https://www.nseindia.com/companies-listing/corporate-filings-announcements",
            attachment_hash="b" * 64,
            parser_version="nse-results-v1",
        )
