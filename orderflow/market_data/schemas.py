"""Canonical market-data models for the order-flow layer.

These are the ONLY models downstream code may consume. Provider field names
never appear here or anywhere downstream — the adapter
(``market_data/fyers_adapter.py``) is the sole translator.

R5 (build manual): a field the source did not supply is ``None``, never a
zero, never a default. Zero is valid data; ``None`` is unknown; callers that
need a value must handle ``None`` explicitly.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Tuple


class SchemaError(ValueError):
    """A canonical model was constructed from impossible data."""


def ensure_utc(value: datetime) -> datetime:
    """Return ``value`` normalised to UTC. Naive datetimes are rejected, not
    guessed: a timestamp without a stated timezone is unusable for latency or
    skew arithmetic."""
    if value.tzinfo is None:
        raise SchemaError(f"timestamp must be timezone-aware, got {value!r}")
    return value.astimezone(timezone.utc)


def _checked_float(value: Optional[float], name: str, *, allow_zero: bool = True) -> Optional[float]:
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        raise SchemaError(f"{name} must be a number, got {value!r}")
    if out != out or out in (float("inf"), float("-inf")):
        raise SchemaError(f"{name} must be finite, got {value!r}")
    if out < 0 or (out == 0 and not allow_zero):
        raise SchemaError(f"{name} must be non-negative, got {out}")
    return out


def _checked_int(value: Optional[int], name: str) -> Optional[int]:
    if value is None:
        return None
    try:
        out = int(value)
    except (TypeError, ValueError):
        raise SchemaError(f"{name} must be an integer, got {value!r}")
    if out < 0:
        raise SchemaError(f"{name} must be non-negative, got {out}")
    return out


@dataclass(frozen=True)
class DepthLevel:
    """One price level of one side of the book.

    ``order_count`` is ``None`` when the source did not supply it — several
    providers omit per-level order counts; absence is recorded, never zero.
    """

    price: float
    quantity: int
    order_count: Optional[int] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "price", _checked_float(self.price, "price"))
        object.__setattr__(self, "quantity", _checked_int(self.quantity, "quantity"))
        object.__setattr__(self, "order_count", _checked_int(self.order_count, "order_count"))


@dataclass(frozen=True)
class QuoteUpdate:
    """One top-of-book / trade tick.

    ``ts_exchange`` is the exchange's own feed timestamp if the source carried
    one (``None`` otherwise). ``ts_received`` is when our process received the
    message; both are timezone-aware UTC. ``feed_latency_ms`` is deliberately
    not stored on quotes — it is derivable from the two timestamps.
    """

    ts_exchange: Optional[datetime]
    ts_received: datetime
    symbol: str
    ltp: Optional[float] = None
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    prev_close: Optional[float] = None
    session_volume: Optional[int] = None
    last_trade_qty: Optional[int] = None

    def __post_init__(self) -> None:
        if not self.symbol:
            raise SchemaError("symbol must be a non-empty string")
        object.__setattr__(self, "ts_received", ensure_utc(self.ts_received))
        if self.ts_exchange is not None:
            object.__setattr__(self, "ts_exchange", ensure_utc(self.ts_exchange))
        for name in ("ltp", "open", "high", "low", "prev_close"):
            object.__setattr__(self, name, _checked_float(getattr(self, name), name))
        object.__setattr__(self, "session_volume", _checked_int(self.session_volume, "session_volume"))
        object.__setattr__(self, "last_trade_qty", _checked_int(self.last_trade_qty, "last_trade_qty"))

    @property
    def feed_latency_ms(self) -> Optional[float]:
        if self.ts_exchange is None:
            return None
        return (self.ts_received - self.ts_exchange).total_seconds() * 1000.0


@dataclass(frozen=True)
class DepthSnapshot:
    """One full-depth observation of one symbol.

    ``bids``/``asks`` carry as many levels as the source supplied — 5 on the
    standard data socket, up to 50 if a tick-by-tick feed is provisioned. The
    level count is itself a capability measurement, never an assumption.

    ``feed_latency_ms`` is set when both timestamps exist, else ``None``.
    """

    ts_exchange: Optional[datetime]
    ts_received: datetime
    symbol: str
    bids: Tuple[DepthLevel, ...] = ()
    asks: Tuple[DepthLevel, ...] = ()
    total_buy_qty: Optional[int] = None
    total_sell_qty: Optional[int] = None
    feed_latency_ms: Optional[float] = None

    def __post_init__(self) -> None:
        if not self.symbol:
            raise SchemaError("symbol must be a non-empty string")
        object.__setattr__(self, "ts_received", ensure_utc(self.ts_received))
        if self.ts_exchange is not None:
            object.__setattr__(self, "ts_exchange", ensure_utc(self.ts_exchange))
        bids = tuple(self.bids)
        asks = tuple(self.asks)
        for levels, name in ((bids, "bids"), (asks, "asks")):
            for level in levels:
                if not isinstance(level, DepthLevel):
                    raise SchemaError(f"{name} levels must be DepthLevel, got {type(level)!r}")
        object.__setattr__(self, "bids", bids)
        object.__setattr__(self, "asks", asks)
        object.__setattr__(self, "total_buy_qty", _checked_int(self.total_buy_qty, "total_buy_qty"))
        object.__setattr__(self, "total_sell_qty", _checked_int(self.total_sell_qty, "total_sell_qty"))
        latency = self.feed_latency_ms
        if latency is None and self.ts_exchange is not None:
            latency = (self.ts_received - self.ts_exchange).total_seconds() * 1000.0
        # Negative latency is legal: it means the exchange clock is ahead of
        # ours (clock skew). It is a measurement, not invalid data — record it.
        if latency is not None:
            try:
                latency = float(latency)
            except (TypeError, ValueError):
                raise SchemaError(f"feed_latency_ms must be a number, got {latency!r}")
            if latency != latency or latency in (float("inf"), float("-inf")):
                raise SchemaError(f"feed_latency_ms must be finite, got {latency}")
        object.__setattr__(self, "feed_latency_ms", latency)
