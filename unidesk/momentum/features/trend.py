"""Deterministic trend features (build manual Task P1.2).

Pure functions over plain float series (daily closes from the market store);
no storage, no I/O, no provider vocabulary. Every definition here is frozen
and fixture-tested; none of it creates a buy signal — trend state is context
(R5-era: market context does not create geometry).

EMA definition (frozen): seeded with the SMA of the first ``span`` values;
``output[i] is None`` for ``i < span-1``. Output at index ``i`` depends only
on ``values[:i+1]`` — a no-look-ahead property enforced by test.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional, Sequence

from unidesk.contracts.base import ContractError, require_float


class TrendState(Enum):
    STRONG_UPTREND = "STRONG_UPTREND"
    UPTREND = "UPTREND"
    TRANSITION = "TRANSITION"
    WEAK = "WEAK"
    UNKNOWN = "UNKNOWN"


def _series(values: Sequence[Optional[float]], name: str) -> list:
    out = []
    for i, v in enumerate(values):
        if v is None:
            raise ContractError(f"{name}[{i}] is None; callers must resolve missing bars upstream (R12)")
        out.append(require_float(v, f"{name}[{i}]"))
    return out


def ema(values: Sequence[float], span: int) -> list:
    """Exponential moving average, SMA-seeded. None during warm-up."""
    if span < 1:
        raise ContractError("span must be >= 1")
    series = _series(values, "values")
    if len(series) < span:
        return [None] * len(series)
    k = 2.0 / (span + 1.0)
    seed = sum(series[:span]) / span
    out: list = [None] * (span - 1) + [seed]
    prev = seed
    for v in series[span:]:
        prev = v * k + prev * (1.0 - k)
        out.append(prev)
    return out


def ema_slope_pct(ema_series: Sequence[Optional[float]], lookback: int = 5) -> list:
    """Percentage change of the EMA over ``lookback`` points. None until both
    endpoints exist (warm-up honest, never zero-filled)."""
    if lookback < 1:
        raise ContractError("lookback must be >= 1")
    out: list = []
    for i in range(len(ema_series)):
        j = i - lookback
        if i < 0 or j < 0 or ema_series[i] is None or ema_series[j] is None:
            out.append(None)
            continue
        base = ema_series[j]
        if base == 0:
            out.append(None)
            continue
        out.append((ema_series[i] / base - 1.0) * 100.0)
    return out


def price_vs_ema_pct(close: float, ema_value: Optional[float]) -> Optional[float]:
    """Distance of close from its EMA, in percent. None if EMA not ready."""
    close = require_float(close, "close")
    if close < 0:
        raise ContractError("close must be non-negative")
    if ema_value is None:
        return None
    if ema_value == 0:
        return None
    return (close / ema_value - 1.0) * 100.0


def trend_state(
    close: float,
    ema21: Optional[float],
    ema50: Optional[float],
    ema21_rising: bool,
) -> TrendState:
    """Context classification only. Rules (frozen):
    STRONG_UPTREND  close > ema21 > ema50 and ema21 rising
    UPTREND         close > ema50 and ema21 > ema50
    WEAK            close < ema50 and ema21 < ema50
    TRANSITION      anything else
    UNKNOWN         EMAs not ready (warm-up honest)"""
    if ema21 is None or ema50 is None:
        return TrendState.UNKNOWN
    if close > ema21 > ema50 and ema21_rising:
        return TrendState.STRONG_UPTREND
    if close > ema50 and ema21 > ema50:
        return TrendState.UPTREND
    if close < ema50 and ema21 < ema50:
        return TrendState.WEAK
    return TrendState.TRANSITION


def ema_rising(ema_series: Sequence[Optional[float]], i: int, lookback: int = 5) -> bool:
    """True when the EMA at ``i`` is above its value ``lookback`` points back
    (both must exist; otherwise False — warm-up never invents direction)."""
    j = i - lookback
    if j < 0 or i >= len(ema_series) or j >= len(ema_series):
        return False
    a, b = ema_series[i], ema_series[j]
    if a is None or b is None:
        return False
    return a > b
