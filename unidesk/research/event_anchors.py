"""Fact-backed, point-in-time AVWAP anchors for IPO and realised EP research.

These functions intentionally accept only immutable IPO listing facts and
realised exchange-result events. A planned board meeting or calendar date has
no compatible type, so it cannot become an anchor by accident.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Mapping, Sequence

from unidesk.contracts.base import ContractError, ensure_date, ensure_utc, require_float, require_str
from unidesk.research.market_events import EarningsResultEvent, IPOListingFact


@dataclass(frozen=True)
class EventAnchor:
    """One immutable AVWAP anchor with enough provenance to reproduce it."""

    kind: str
    source_event_id: str
    symbol: str
    anchor_session: date
    available_at: datetime
    source_hash: str
    adjustment_basis: str
    volume_basis: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", require_str(self.kind, "kind"))
        object.__setattr__(self, "source_event_id", require_str(self.source_event_id, "source_event_id"))
        object.__setattr__(self, "symbol", require_str(self.symbol, "symbol"))
        object.__setattr__(self, "anchor_session", ensure_date(self.anchor_session, "anchor_session"))
        object.__setattr__(self, "available_at", ensure_utc(self.available_at, "available_at"))
        object.__setattr__(self, "source_hash", require_str(self.source_hash, "source_hash"))
        object.__setattr__(self, "adjustment_basis", require_str(self.adjustment_basis, "adjustment_basis"))
        object.__setattr__(self, "volume_basis", require_str(self.volume_basis, "volume_basis"))


def _sessions(values: Sequence[date]) -> tuple[date, ...]:
    result = tuple(ensure_date(value, f"sessions[{index}]") for index, value in enumerate(values))
    if not result:
        raise ContractError("sessions must not be empty")
    if tuple(sorted(result)) != result or len(set(result)) != len(result):
        raise ContractError("sessions must be unique and chronological")
    return result


def anchor_for_ipo_listing(
    fact: IPOListingFact,
    sessions: Sequence[date],
    *,
    adjustment_basis: str,
    volume_basis: str,
) -> EventAnchor:
    """Anchor IPO AVWAP on the documented primary listing session only."""
    known_sessions = _sessions(sessions)
    if fact.listing_date not in known_sessions:
        raise ContractError("documented IPO listing session is absent from the market series")
    return EventAnchor(
        kind="ipo_listing",
        source_event_id=f"ipo:{fact.isin}:{fact.listing_date.isoformat()}",
        symbol=fact.symbol,
        anchor_session=fact.listing_date,
        available_at=fact.available_at,
        source_hash=fact.source_hash,
        adjustment_basis=adjustment_basis,
        volume_basis=volume_basis,
    )


def anchor_for_realised_result(
    event: EarningsResultEvent,
    completed_at_by_session: Mapping[date, datetime],
    *,
    adjustment_basis: str,
    volume_basis: str,
) -> EventAnchor:
    """Anchor EOD EP AVWAP after the first completed post-filing session."""
    completed = sorted(
        (ensure_date(session, "completed_at_by_session key"), ensure_utc(instant, "completed_at_by_session value"))
        for session, instant in completed_at_by_session.items()
    )
    for session, completed_at in completed:
        if completed_at > event.available_at:
            return EventAnchor(
                kind="earnings_result",
                source_event_id=(
                    f"earnings:{event.symbol}:{event.period_ended.isoformat()}:"
                    f"{event.attachment_hash[:16]}"
                ),
                symbol=event.symbol,
                anchor_session=session,
                available_at=event.available_at,
                source_hash=event.attachment_hash,
                adjustment_basis=adjustment_basis,
                volume_basis=volume_basis,
            )
    raise ContractError("no completed market session exists after results dissemination")


def anchored_vwap(
    *,
    sessions: Sequence[date],
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    volumes: Sequence[float],
    anchor: EventAnchor,
    as_of: date,
    adjustment_basis: str,
) -> float:
    """EOD AVWAP from a fact-backed anchor through ``as_of`` only."""
    series_sessions = _sessions(sessions)
    as_of = ensure_date(as_of, "as_of")
    if require_str(adjustment_basis, "adjustment_basis") != anchor.adjustment_basis:
        raise ContractError("adjustment basis does not match event anchor")
    if not (len(series_sessions) == len(highs) == len(lows) == len(closes) == len(volumes)):
        raise ContractError("sessions, OHLC and volumes must have equal length")
    if as_of < anchor.anchor_session:
        raise ContractError("as_of precedes event anchor")

    weighted_total = 0.0
    volume_total = 0.0
    for index, session in enumerate(series_sessions):
        if session < anchor.anchor_session or session > as_of:
            continue
        high = require_float(highs[index], f"highs[{index}]")
        low = require_float(lows[index], f"lows[{index}]")
        close = require_float(closes[index], f"closes[{index}]")
        volume = require_float(volumes[index], f"volumes[{index}]")
        if volume <= 0:
            raise ContractError("anchor-window volume must be positive")
        weighted_total += ((high + low + close) / 3.0) * volume
        volume_total += volume
    if volume_total <= 0:
        raise ContractError("no bars exist in the event-anchor window")
    return weighted_total / volume_total
