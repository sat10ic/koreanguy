"""Point-in-time source contracts for IPO and realised earnings events.

These are source records, not trading signals. Consumers must use
``available_at`` rather than a listing date, fiscal period, or announced future
board-meeting date when deciding what was knowable.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import re

from unidesk.contracts.base import ContractError, ensure_date, ensure_utc, require_str
from unidesk.momentum.universe.symbol_master import normalize_symbol


_HASH_RE = re.compile(r"[0-9a-f]{64}\Z")


def _source_url(value: str) -> str:
    value = require_str(value, "source_url")
    if not value.startswith("https://"):
        raise ContractError("source_url must use https")
    return value


def _hash(value: str, name: str) -> str:
    value = require_str(value, name).lower()
    if not _HASH_RE.fullmatch(value):
        raise ContractError(f"{name} must be a SHA-256 hex digest")
    return value


@dataclass(frozen=True)
class IPOListingFact:
    symbol: str
    isin: str
    listing_date: date
    source_url: str
    available_at: datetime
    retrieved_at: datetime
    source_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", normalize_symbol(self.symbol))
        object.__setattr__(self, "isin", require_str(self.isin, "isin").upper())
        object.__setattr__(self, "listing_date", ensure_date(self.listing_date, "listing_date"))
        object.__setattr__(self, "source_url", _source_url(self.source_url))
        object.__setattr__(self, "available_at", ensure_utc(self.available_at, "available_at"))
        object.__setattr__(self, "retrieved_at", ensure_utc(self.retrieved_at, "retrieved_at"))
        object.__setattr__(self, "source_hash", _hash(self.source_hash, "source_hash"))
        if self.retrieved_at < self.available_at:
            raise ContractError("retrieved_at cannot precede available_at")


@dataclass(frozen=True)
class EarningsResultEvent:
    symbol: str
    period_ended: date
    received_at: datetime
    disseminated_at: datetime
    available_at: datetime
    retrieved_at: datetime
    source_url: str
    attachment_hash: str
    parser_version: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", normalize_symbol(self.symbol))
        object.__setattr__(self, "period_ended", ensure_date(self.period_ended, "period_ended"))
        for name in ("received_at", "disseminated_at", "available_at", "retrieved_at"):
            object.__setattr__(self, name, ensure_utc(getattr(self, name), name))
        object.__setattr__(self, "source_url", _source_url(self.source_url))
        object.__setattr__(self, "attachment_hash", _hash(self.attachment_hash, "attachment_hash"))
        object.__setattr__(self, "parser_version", require_str(self.parser_version, "parser_version"))
        if self.disseminated_at < self.received_at:
            raise ContractError("disseminated_at cannot precede received_at")
        if self.available_at != self.disseminated_at:
            raise ContractError("available_at must equal disseminated_at for a realised result")
        if self.retrieved_at < self.available_at:
            raise ContractError("retrieved_at cannot precede available_at")
