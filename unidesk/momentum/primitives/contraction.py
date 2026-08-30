"""Contraction / volume-dry-up primitives (build manual Task P2.2).

Frozen definitions, all over chronological windows of completed sessions:

* ``base_depth_pct(highs, lows, start, end)`` — (max high − min low) /
  min low × 100 over the base window ``[start, end)``. The base's "depth"
  as a percentage of its floor.
* ``range_contraction_ratio(highs, lows, recent_n, prior_n)`` — mean range of
  the most recent ``recent_n`` sessions over the mean range of the
  ``prior_n`` before them (< 1 means contracting). Needs both windows full.
* ``volume_dryup_ratio(volumes, recent_n, prior_n)`` — mean volume of the
  most recent ``recent_n`` over the mean of the ``prior_n`` before them
  (< 1 means drying up). Exclusive windows, no overlap.
"""
from __future__ import annotations

from typing import Optional, Sequence

from unidesk.contracts.base import ContractError, require_float


def _window(values: Sequence[float], start: int, n: int, name: str) -> list:
    if start < 0 or start + n > len(values):
        raise ContractError(f"{name}: window [{start},{start + n}) outside the series")
    out = [require_float(values[j], f"{name}[{j}]") for j in range(start, start + n)]
    return out


def base_depth_pct(highs: Sequence[float], lows: Sequence[float], start: int, end: int) -> float:
    if end - start < 2:
        raise ContractError("base window needs at least 2 sessions")
    if start < 0 or end > len(highs) or len(highs) != len(lows):
        raise ContractError("invalid base window")
    hs = [require_float(v, f"highs[{j}]") for j, v in enumerate(highs[start:end])]
    ls = [require_float(v, f"lows[{j}]") for j, v in enumerate(lows[start:end])]
    floor = min(ls)
    if floor <= 0:
        raise ContractError("base floor must be positive")
    return (max(hs) - floor) / floor * 100.0


def range_contraction_ratio(
    highs: Sequence[float], lows: Sequence[float], recent_n: int, prior_n: int
) -> Optional[float]:
    if recent_n < 1 or prior_n < 1:
        raise ContractError("windows must be >= 1")
    total = recent_n + prior_n
    if len(highs) != len(lows):
        raise ContractError("highs and lows must have equal length")
    if len(highs) < total:
        return None  # warm-up: window not fillable — unavailable, never an error
    i = len(highs)
    recent = [
        require_float(highs[j], "highs[]") - require_float(lows[j], "lows[]")
        for j in range(i - recent_n, i)
    ]
    prior = [
        require_float(highs[j], "highs[]") - require_float(lows[j], "lows[]")
        for j in range(i - total, i - recent_n)
    ]
    prior_mean = sum(prior) / prior_n
    if prior_mean <= 0:
        return None
    return (sum(recent) / recent_n) / prior_mean


def volume_dryup_ratio(
    volumes: Sequence[float], recent_n: int, prior_n: int
) -> Optional[float]:
    if recent_n < 1 or prior_n < 1:
        raise ContractError("windows must be >= 1")
    total = recent_n + prior_n
    if len(volumes) < total:
        return None  # warm-up: window not fillable — unavailable, never an error
    vols = [require_float(v, "volumes[]") for v in volumes]
    i = len(vols)
    recent = vols[i - recent_n:i]
    prior = vols[i - total:i - recent_n]
    prior_mean = sum(prior) / prior_n
    if prior_mean <= 0:
        return None
    return (sum(recent) / recent_n) / prior_mean
