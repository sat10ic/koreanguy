"""In-memory reference store for point-in-time market-state queries.

It is deliberately an in-process port, not a persistent data-home decision.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from unidesk.contracts.base import ContractError, ensure_utc, require_str
from unidesk.contracts.market import DailyBar, IntradayBar
from unidesk.momentum.universe.symbol_master import (
    SymbolClassification,
    normalize_symbol,
    resolve_classification,
)


@dataclass(frozen=True)
class VersionedDailyBar:
    """An EOD observation, visible only once ``available_at`` has passed."""

    bar: DailyBar
    available_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "available_at", ensure_utc(self.available_at, "available_at"))
        if normalize_symbol(self.bar.symbol) != self.bar.symbol:
            raise ContractError("DailyBar.symbol must already be normalized")


@dataclass(frozen=True)
class VersionedIntradayBar:
    """A completed intraday observation, visible only at ``available_at``."""

    bar: IntradayBar
    available_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "available_at", ensure_utc(self.available_at, "available_at"))
        if normalize_symbol(self.bar.symbol) != self.bar.symbol:
            raise ContractError("IntradayBar.symbol must already be normalized")
        if self.available_at < self.bar.ts:
            raise ContractError("intraday available_at cannot precede completed-bar ts")


@dataclass(frozen=True)
class MarketState:
    """Immutable state visible for one normalized symbol at an instant."""

    as_of: datetime
    symbol: str
    classification: Optional[SymbolClassification]
    daily_bar: Optional[VersionedDailyBar]
    intraday_bars: tuple[VersionedIntradayBar, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "as_of", ensure_utc(self.as_of, "as_of"))
        object.__setattr__(self, "symbol", normalize_symbol(self.symbol))
        object.__setattr__(self, "intraday_bars", tuple(self.intraday_bars))


class InMemoryMarketStore:
    """Reference port with deterministic duplicate rejection and PIT reads.

    A persistent adapter is intentionally absent and owner-gated.
    """

    def __init__(self) -> None:
        self._classifications: list[SymbolClassification] = []
        self._daily: list[VersionedDailyBar] = []
        self._intraday: list[VersionedIntradayBar] = []
        # O(1) duplicate-guard indexes (same semantics as the list scans they
        # replaced; bulk ingestion of ~600k bars made the scans quadratic).
        self._daily_keys: set = set()
        self._daily_avail: set = set()
        self._intraday_keys: set = set()
        self._intraday_avail: set = set()

    def add_classification(self, item: SymbolClassification) -> None:
        key = (item.symbol, item.effective_from, item.effective_to, item.version)
        if any((x.symbol, x.effective_from, x.effective_to, x.version) == key for x in self._classifications):
            raise ContractError("duplicate classification key/version")
        # Equal availability would make two revisions ambiguous at one instant.
        if any(
            x.symbol == item.symbol
            and x.effective_from == item.effective_from
            and x.effective_to == item.effective_to
            and x.available_at == item.available_at
            for x in self._classifications
        ):
            raise ContractError("ambiguous classification versions have equal available_at")
        self._classifications.append(item)

    def add_daily_bar(self, item: VersionedDailyBar) -> None:
        key = (item.bar.symbol, item.bar.session, item.bar.data_version)
        if key in self._daily_keys:
            raise ContractError("duplicate daily observation key/version")
        avail = (item.bar.symbol, item.bar.session, item.available_at)
        if avail in self._daily_avail:
            raise ContractError("ambiguous daily observation versions have equal available_at")
        self._daily_keys.add(key)
        self._daily_avail.add(avail)
        self._daily.append(item)

    def add_intraday_bar(self, item: VersionedIntradayBar) -> None:
        key = (item.bar.symbol, item.bar.ts, item.bar.timeframe, item.bar.data_version)
        if key in self._intraday_keys:
            raise ContractError("duplicate intraday observation key/version")
        avail = (item.bar.symbol, item.bar.ts, item.bar.timeframe, item.available_at)
        if avail in self._intraday_avail:
            raise ContractError("ambiguous intraday observation versions have equal available_at")
        self._intraday_keys.add(key)
        self._intraday_avail.add(avail)
        self._intraday.append(item)

    def get_market_state(self, symbol: str, as_of: datetime) -> MarketState:
        normalized = normalize_symbol(symbol)
        instant = ensure_utc(as_of, "as_of")
        classification = resolve_classification(self._classifications, normalized, instant)
        daily = self._daily_at(normalized, instant)
        intraday = self._intraday_at(normalized, instant)
        return MarketState(instant, normalized, classification, daily, intraday)

    def _daily_at(self, symbol: str, as_of: datetime) -> Optional[VersionedDailyBar]:
        candidates = [
            item for item in self._daily
            if item.bar.symbol == symbol and item.bar.session <= as_of.date() and item.available_at <= as_of
        ]
        if not candidates:
            return None
        # One latest available revision per session, then latest session.
        selected: dict[object, VersionedDailyBar] = {}
        for item in candidates:
            current = selected.get(item.bar.session)
            if current is None or item.available_at > current.available_at:
                selected[item.bar.session] = item
        return max(selected.values(), key=lambda item: item.bar.session)

    def _intraday_at(self, symbol: str, as_of: datetime) -> tuple[VersionedIntradayBar, ...]:
        candidates = [
            item for item in self._intraday
            if item.bar.symbol == symbol and item.bar.ts <= as_of and item.available_at <= as_of
        ]
        selected: dict[tuple[datetime, object], VersionedIntradayBar] = {}
        for item in candidates:
            key = (item.bar.ts, item.bar.timeframe)
            current = selected.get(key)
            if current is None or item.available_at > current.available_at:
                selected[key] = item
        return tuple(sorted(selected.values(), key=lambda item: (item.bar.ts, item.bar.timeframe.value)))
