"""Point-in-time anchors for IPO and realised-earnings AVWAP research."""
from datetime import date, datetime, timezone

import pytest

from unidesk.contracts.base import ContractError
from unidesk.research.event_anchors import (
    anchored_vwap,
    anchor_for_ipo_listing,
    anchor_for_realised_result,
)
from unidesk.research.market_events import EarningsResultEvent, IPOListingFact


UTC = timezone.utc
HASH = "a" * 64


def _ipo(listing_date=date(2026, 1, 5)):
    return IPOListingFact(
        symbol="IPOCO", isin="INE000A01000", listing_date=listing_date,
        source_url="https://nse.example/listing.pdf",
        available_at=datetime(2026, 1, 5, 8, tzinfo=UTC),
        retrieved_at=datetime(2026, 1, 5, 9, tzinfo=UTC), source_hash=HASH,
    )


def _result(disseminated_at):
    return EarningsResultEvent(
        symbol="EPCO", period_ended=date(2025, 12, 31),
        received_at=disseminated_at, disseminated_at=disseminated_at,
        available_at=disseminated_at, retrieved_at=disseminated_at,
        source_url="https://nse.example/result.pdf", attachment_hash=HASH,
        parser_version="results-v1",
    )


def test_ipo_anchor_requires_the_actual_primary_listing_session():
    anchor = anchor_for_ipo_listing(
        _ipo(), [date(2026, 1, 5), date(2026, 1, 6)],
        adjustment_basis="ca-v1", volume_basis="official-bhavcopy-volume",
    )
    assert anchor.anchor_session == date(2026, 1, 5)
    assert anchor.source_hash == HASH
    with pytest.raises(ContractError, match="listing session"):
        anchor_for_ipo_listing(
            _ipo(), [date(2026, 1, 6)],
            adjustment_basis="ca-v1", volume_basis="official-bhavcopy-volume",
        )


def test_eod_ep_anchor_waits_for_the_first_completed_session_after_dissemination():
    result = _result(datetime(2026, 1, 5, 16, tzinfo=UTC))
    anchor = anchor_for_realised_result(
        result,
        {
            date(2026, 1, 5): datetime(2026, 1, 5, 12, 30, tzinfo=UTC),
            date(2026, 1, 6): datetime(2026, 1, 6, 12, 30, tzinfo=UTC),
        },
        adjustment_basis="ca-v1", volume_basis="official-bhavcopy-volume",
    )
    assert anchor.anchor_session == date(2026, 1, 6)
    assert anchor.available_at == result.disseminated_at
    assert anchor.source_hash == HASH


def test_anchored_vwap_is_prefix_invariant_and_rejects_a_basis_mismatch():
    sessions = [date(2026, 1, d) for d in (5, 6, 7)]
    anchor = anchor_for_ipo_listing(
        _ipo(), sessions, adjustment_basis="ca-v1", volume_basis="official-bhavcopy-volume",
    )
    value = anchored_vwap(
        sessions=sessions, highs=[102.0, 112.0, 999.0], lows=[98.0, 108.0, 1.0],
        closes=[100.0, 110.0, 500.0], volumes=[100.0, 100.0, 1.0],
        anchor=anchor, as_of=date(2026, 1, 6), adjustment_basis="ca-v1",
    )
    assert value == pytest.approx(105.0)
    with pytest.raises(ContractError, match="adjustment basis"):
        anchored_vwap(
            sessions=sessions, highs=[102.0, 112.0, 999.0], lows=[98.0, 108.0, 1.0],
            closes=[100.0, 110.0, 500.0], volumes=[100.0, 100.0, 1.0],
            anchor=anchor, as_of=date(2026, 1, 6), adjustment_basis="ca-v2",
        )
