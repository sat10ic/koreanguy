"""The swing-edges spec §1.5 feature library — the missing primitives
(N2), frozen definitions, all pure functions over chronological series.

Adopted from ``plan/SWING_EDGES_TECHNICAL_SPEC.md`` (D11). Warm-up returns
``None`` — never zero (R12). Where the spec's definition differs from an
existing module (e.g. median-RVOL vs our mean-RVOL), BOTH exist: the spec's
frozen definition is authoritative for its experiments, ours remains for
backward compatibility.
"""
from __future__ import annotations

from statistics import median
from typing import Optional, Sequence

from unidesk.contracts.base import ContractError, require_float


def _series(values: Sequence[Optional[float]], name: str) -> list:
    out = []
    for i, v in enumerate(values):
        if v is None:
            raise ContractError(f"{name}[{i}] is None; resolve missing bars upstream (R12)")
        out.append(require_float(v, f"{name}[{i}]"))
    return out


def sma(values: Sequence[float], span: int) -> list:
    """Simple moving average. ``None`` for the first ``span-1`` points."""
    if span < 1:
        raise ContractError("span must be >= 1")
    series = _series(values, "values")
    out: list = [None] * len(series)
    running = 0.0
    for i, v in enumerate(series):
        running += v
        if i >= span:
            running -= series[i - span]
        if i >= span - 1:
            out[i] = running / span
    return out


def rvol_median(volumes: Sequence[float], span: int = 20) -> list:
    """``rvol_20`` per the spec: volume / MEDIAN(volume over the prior
    ``span`` sessions, exclusive). Median (not mean) resists spike days.
    None before the window fills; None when the prior median is 0."""
    vols = _series(volumes, "volumes")
    out: list = []
    for i in range(len(vols)):
        if i < span:
            out.append(None)
            continue
        base = median(vols[i - span:i])
        out.append(None if base == 0 else vols[i] / base)
    return out


def delivery_z(delivery_pcts: Sequence[Optional[float]], span: int = 20) -> list:
    """Z-score of today's delivery% vs the prior ``span`` sessions.
    Any None inside the window (including today) → None: a partially known
    baseline is never standardized (R12)."""
    series = []
    for i, v in enumerate(delivery_pcts):
        if v is not None:
            series.append(require_float(v, f"delivery_pcts[{i}]"))
        else:
            series.append(None)
    out: list = []
    for i in range(len(series)):
        if i < span or series[i] is None or any(v is None for v in series[i - span:i]):
            out.append(None)
            continue
        window = series[i - span:i]
        mean = sum(window) / span
        var = sum((v - mean) ** 2 for v in window) / span
        std = var ** 0.5
        out.append(None if std == 0 else (series[i] - mean) / std)
    return out


def pocket_pivot(closes: Sequence[float], volumes: Sequence[float], lookback: int = 10) -> list:
    """``pocket_pivot[i]``: close rose vs the prior close AND volume exceeds
    the MAX volume of the down-close days within the prior ``lookback``
    sessions. None during the lookback warm-up; False when no down-close day
    exists in the window (no benchmark to clear)."""
    c = _series(closes, "closes")
    v = _series(volumes, "volumes")
    if len(c) != len(v):
        raise ContractError("closes and volumes must have equal length")
    out: list = []
    for i in range(len(c)):
        if i < 1 or i < lookback:
            out.append(None)
            continue
        up = c[i] > c[i - 1]
        down_vols = [v[j] for j in range(i - lookback, i) if c[j] < c[j - 1]]
        bench = max(down_vols) if down_vols else None
        if bench is None:
            out.append(False)
        else:
            out.append(bool(up and v[i] > bench))
    return out


def tight_ratio(highs: Sequence[float], lows: Sequence[float], n: int = 10) -> list:
    """``tight_10`` ratio per the spec: max(high, n) / min(low, n) − 1.
    The spec's 0.08 threshold is caller policy."""
    h = _series(highs, "highs")
    l = _series(lows, "lows")
    if len(h) != len(l):
        raise ContractError("highs and lows must have equal length")
    out: list = []
    for i in range(len(h)):
        if i + 1 < n:
            out.append(None)
            continue
        window_h = h[i + 1 - n:i + 1]
        window_l = l[i + 1 - n:i + 1]
        lo = min(window_l)
        out.append(None if lo <= 0 else max(window_h) / lo - 1.0)
    return out


def stack_bull(close: float, ema10: float, ema21: float, sma50: float, sma200: float) -> bool:
    return close > ema10 > ema21 > sma50 > sma200


def stage2(close: float, sma200_series: Sequence[Optional[float]],
           *, slope_lookback: int = 50, min_window: int = 126,
           premium: float = 1.15) -> bool:
    """``stage2``: close > SMA200, SMA200 50d slope > 0, and close >=
    1.15 × the minimum SMA200 of the trailing 126 sessions. False (not
    None) on warm-up: stage is a state, and an unproven series is simply
    not stage 2."""
    c = require_float(close, "close")
    if len(sma200_series) < min_window:
        return False
    window = sma200_series[-min_window:]
    if any(v is None for v in window):
        return False
    current = sma200_series[-1]
    past = sma200_series[-1 - slope_lookback]
    if current is None or past is None:
        return False
    return c > current and current > past and c >= premium * min(window)
