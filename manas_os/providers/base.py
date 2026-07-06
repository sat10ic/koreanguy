"""Provider interface: SnapshotRow shape + MarketDataProvider ABC.

All providers (Fyers live, bhavcopy EOD) normalize to SnapshotRow so the rest
of the app never branches on data source.

Adopted from legacy ssrvol/providers/base.py (copied + rewired to manas_os).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class SnapshotRow:
    """One symbol's live-quote-equivalent snapshot, normalized across providers."""
    symbol: str
    last: Optional[float] = None
    today_open: Optional[float] = None
    today_low: Optional[float] = None
    today_high: Optional[float] = None
    today_volume: Optional[float] = None
    prev_close: Optional[float] = None
    avg_vol_n: Optional[float] = None
    ok: bool = True
    error: Optional[str] = None


@dataclass
class DailyBar:
    date: str  # ISO yyyy-mm-dd
    open: float
    high: float
    low: float
    close: float
    volume: float


class MarketDataProvider(ABC):
    """Common interface every data provider implements."""

    name: str = "base"

    @abstractmethod
    def get_snapshot(self, symbols: list[str], lookback: int = 20) -> list[SnapshotRow]:
        """Return one SnapshotRow per symbol (today's live/EOD quote +
        prev_close + avg_vol_n over `lookback` prior completed days)."""
        raise NotImplementedError

    @abstractmethod
    def get_daily_history(self, symbol: str, lookback_days: int = 60) -> list[DailyBar]:
        """Return up to `lookback_days` of daily OHLCV bars, oldest first."""
        raise NotImplementedError

    def is_available(self) -> bool:
        """Whether this provider is currently usable (creds/deps present)."""
        return True
