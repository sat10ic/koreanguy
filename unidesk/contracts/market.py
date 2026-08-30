"""Market data contracts (build manual §4.1–4.3): SymbolMaster, DailyBar,
IntradayBar."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Optional

from .base import (
    ContractError,
    coerce_enum,
    ensure_date,
    ensure_utc,
    require_bool,
    require_float,
    require_int,
    require_non_negative,
    require_opt_float,
    require_opt_int,
    require_str,
    require_str_tuple,
)


class Timeframe(Enum):
    ONE_MIN = "1m"
    FIVE_MIN = "5m"
    FIFTEEN_MIN = "15m"


@dataclass(frozen=True)
class SymbolMaster:
    """Point-in-time symbol classification. Historical queries must never see
    today's sector/index membership (valid_from/valid_to versioning)."""

    symbol: str
    exchange: str
    instrument_token: str
    company_name: str
    sector: str
    industry: str
    market_cap_bucket: str
    index_membership: tuple
    theme_tags: tuple
    surveillance_flags: tuple
    listing_date: date
    active: bool
    valid_from: date
    valid_to: Optional[date] = None  # open-ended membership when None

    def __post_init__(self):
        _set = lambda name, v: object.__setattr__(self, name, v)  # noqa: E731
        _set("symbol", require_str(self.symbol, "symbol"))
        _set("exchange", require_str(self.exchange, "exchange"))
        _set("instrument_token", require_str(self.instrument_token, "instrument_token"))
        _set("company_name", require_str(self.company_name, "company_name"))
        _set("sector", require_str(self.sector, "sector"))
        _set("industry", require_str(self.industry, "industry"))
        _set("market_cap_bucket", require_str(self.market_cap_bucket, "market_cap_bucket"))
        _set("index_membership", require_str_tuple(self.index_membership, "index_membership"))
        _set("theme_tags", require_str_tuple(self.theme_tags, "theme_tags"))
        _set("surveillance_flags", require_str_tuple(self.surveillance_flags, "surveillance_flags"))
        _set("listing_date", ensure_date(self.listing_date, "listing_date"))
        _set("active", require_bool(self.active, "active"))
        _set("valid_from", ensure_date(self.valid_from, "valid_from"))
        if self.valid_to is not None:
            _set("valid_to", ensure_date(self.valid_to, "valid_to"))


def require_str_tuple_local(value, field):
    return require_str_tuple(value, field)


@dataclass(frozen=True)
class DailyBar:
    symbol: str
    session: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    turnover: Optional[float] = None
    delivery_quantity: Optional[int] = None
    delivery_percentage: Optional[float] = None
    upper_circuit: Optional[float] = None
    lower_circuit: Optional[float] = None
    data_version: str = ""

    def __post_init__(self):
        _set = lambda name, v: object.__setattr__(self, name, v)  # noqa: E731
        _set("symbol", require_str(self.symbol, "symbol"))
        _set("session", ensure_date(self.session, "session"))
        for name in ("open", "high", "low", "close"):
            _set(name, require_non_negative(require_float(getattr(self, name), name), name))
        _set("volume", require_non_negative(require_int(self.volume, "volume"), "volume"))
        _set("turnover", require_opt_float(self.turnover, "turnover"))
        _set("delivery_quantity", require_opt_int(self.delivery_quantity, "delivery_quantity"))
        _set("delivery_percentage", require_opt_float(self.delivery_percentage, "delivery_percentage"))
        _set("upper_circuit", require_opt_float(self.upper_circuit, "upper_circuit"))
        _set("lower_circuit", require_opt_float(self.lower_circuit, "lower_circuit"))
        _set("data_version", require_str(self.data_version, "data_version"))


@dataclass(frozen=True)
class IntradayBar:
    symbol: str
    ts: datetime
    timeframe: Timeframe
    open: float
    high: float
    low: float
    close: float
    volume: int
    data_version: str

    def __post_init__(self):
        _set = lambda name, v: object.__setattr__(self, name, v)  # noqa: E731
        _set("symbol", require_str(self.symbol, "symbol"))
        _set("ts", ensure_utc(self.ts, "ts"))
        _set("timeframe", coerce_enum(self.timeframe, Timeframe, "timeframe"))
        for name in ("open", "high", "low", "close"):
            _set(name, require_non_negative(require_float(getattr(self, name), name), name))
        _set("volume", require_non_negative(require_int(self.volume, "volume"), "volume"))
        _set("data_version", require_str(self.data_version, "data_version"))
