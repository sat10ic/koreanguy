"""Relative-strength context (build manual Task P1.3) — point-in-time,
cross-sectional, snapshot-shaped.

Frozen definitions:

* ``window_return(closes, n)`` — ``close[i]/close[i-n] - 1``; None before the
  window exists. No look-ahead.
* ``rs_excess(stock_return, benchmark_return)`` — arithmetic excess in
  percentage points (stock − benchmark). Simple, signed, deterministic.
* ``percentile_rank(values, v)`` — 0..100 cross-sectional rank of ``v``
  within ``values`` (mid-rank on ties). The caller passes the POINT-IN-TIME
  universe; this function does not know about time.

The snapshot API (``rs_snapshot``) answers the manual's four comparisons —
stock vs market, stock vs sector, sector vs market, stock vs peers — for one
symbol at one instant. Missing sector membership disables sector/peer
comparisons with a named reason (R12); it never falls back to the market
figure.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional, Sequence

from unidesk.contracts.base import ContractError, require_float, require_str


def window_return(closes: Sequence[float], n: int) -> list:
    if n < 1:
        raise ContractError("n must be >= 1")
    out: list = []
    for i, close in enumerate(closes):
        close = require_float(close, f"closes[{i}]")
        if i < n:
            out.append(None)
            continue
        base = closes[i - n]
        base = require_float(base, f"closes[{i - n}]")
        if base <= 0:
            raise ContractError(f"close[{i-n}] must be positive for a return")
        out.append((close / base - 1.0) * 100.0)
    return out


def rs_excess(stock_return: Optional[float], benchmark_return: Optional[float]) -> Optional[float]:
    """Arithmetic excess return in percentage points. None if either side is
    missing — never zero-by-default."""
    if stock_return is None or benchmark_return is None:
        return None
    return require_float(stock_return, "stock_return") - require_float(benchmark_return, "benchmark_return")


def percentile_rank(values: Sequence[float], v: float) -> float:
    """0..100 mid-rank percentile of ``v`` within ``values`` (inclusive of v)."""
    if not values:
        raise ContractError("percentile_rank needs a non-empty universe")
    vals = [require_float(x, "values[]") for x in values]
    below = sum(1 for x in vals if x < v)
    equal = sum(1 for x in vals if x == v)
    return (below + 0.5 * equal) / len(vals) * 100.0


@dataclass(frozen=True)
class RSResult:
    symbol: str
    window: int
    stock_return: Optional[float]
    benchmark_return: Optional[float]
    rs_market: Optional[float]
    rs_sector: Optional[float]
    sector_vs_market: Optional[float]
    rs_rank: Optional[float]           # percentile within the full universe
    peer_rank: Optional[float]         # percentile within the sector peers
    peer_count: int = 0
    sector_count: int = 0
    reasons: tuple = field(default_factory=tuple)


def rs_snapshot(
    symbol: str,
    window_returns: Mapping[str, Optional[float]],
    sector_of: Mapping[str, str],
    benchmark: str,
) -> RSResult:
    """One symbol's RS context at one instant.

    ``window_returns`` maps EVERY point-in-time universe member to its window
    return (None where the member has no qualifying history). ``sector_of``
    maps members to sector names; the stock's own membership must exist or
    sector/peer comparisons become None with reason ``NO_SECTOR_MEMBERSHIP``.
    """
    symbol = require_str(symbol, "symbol")
    if symbol not in window_returns:
        raise ContractError(f"{symbol} missing from the point-in-time universe")
    if benchmark not in window_returns:
        raise ContractError(f"benchmark {benchmark} missing from the universe")

    stock_return = window_returns[symbol]
    bench_return = window_returns[benchmark]
    rs_market = rs_excess(stock_return, bench_return)

    reasons = []
    sector = sector_of.get(symbol)
    rs_sector = sector_vs_market = peer_rank = None
    peer_returns: list = []
    sector_count = 0
    if sector is None:
        reasons.append("NO_SECTOR_MEMBERSHIP")
    else:
        peers = [s for s, sec in sector_of.items() if sec == sector and s in window_returns]
        sector_count = len(peers)
        sector_returns = [window_returns[s] for s in peers if window_returns[s] is not None]
        if sector_return_mean := _mean(sector_returns):
            sector_vs_market = rs_excess(sector_return_mean, bench_return)
            rs_sector = rs_excess(stock_return, sector_return_mean)
        else:
            reasons.append("NO_SECTOR_RETURNS")
        peer_returns = [window_returns[s] for s in peers
                        if s != symbol and window_returns[s] is not None]
        if len(peer_returns) >= 1 and stock_return is not None:
            peer_rank = percentile_rank(peer_returns + [stock_return], stock_return)
        else:
            reasons.append("NO_PEER_RETURNS")

    universe_returns = [v for v in window_returns.values() if v is not None]
    rs_rank = percentile_rank(universe_returns, stock_return) if stock_return is not None else None

    return RSResult(
        symbol=symbol,
        window=0,  # informational: caller owns the window length
        stock_return=stock_return,
        benchmark_return=bench_return,
        rs_market=rs_market,
        rs_sector=rs_sector,
        sector_vs_market=sector_vs_market,
        rs_rank=rs_rank,
        peer_rank=peer_rank,
        peer_count=len(peer_returns),
        sector_count=sector_count,
        reasons=tuple(reasons),
    )


def _mean(values: Sequence[float]) -> Optional[float]:
    return sum(values) / len(values) if values else None
