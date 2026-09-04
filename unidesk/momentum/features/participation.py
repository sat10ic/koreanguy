"""Participation features (build manual Task P1.4): RVOL, delivery volume,
delivery-volume ratio.

Pure functions over chronological daily series. Frozen rules:

* **Exclusive prior windows.** Every baseline at index ``i`` is the mean over
  the ``span`` sessions BEFORE ``i`` (``values[i-span:i]``) — the current
  session never contaminates its own baseline (the W5/``activity.py``
  warm-up lesson: never persist half-baked ratios).
* **Warm-up honesty.** Fewer than ``span`` prior sessions → ``None``,
  never zero, never a partial baseline.
* **Delivery reconstruction rule.** ``DeliveryVolume = Volume x Delivery%``
  exists only when BOTH inputs exist. The ratio requires delivery data in
  the FULL prior window plus today — one missing day disables the ratio
  (delivery absence disables dependent features only, and never silently
  degrades a baseline).

Thresholds (strong/exceptional RVOL etc.) are caller policy, not encoded here.
"""
from __future__ import annotations

import math
from typing import Optional, Sequence

from unidesk.contracts.base import ContractError, require_float


def _series(values: Sequence[Optional[float]], name: str, *, allow_none: bool = False) -> list:
    out = []
    for i, v in enumerate(values):
        if v is None:
            if allow_none:
                out.append(None)
                continue
            raise ContractError(f"{name}[{i}] is None; resolve missing bars upstream (R12)")
        # Archive bars are normally finite built-in floats.  Preserve the
        # validator and its indexed error text for every other representation.
        if type(v) is float and math.isfinite(v):
            out.append(v)
        else:
            out.append(require_float(v, f"{name}[{i}]"))
    return out


def _prior_mean(values: Sequence[float], i: int, span: int) -> Optional[float]:
    """Mean of values[i-span:i]; None when the window is not full."""
    if i < span:
        return None
    window = values[i - span:i]
    return sum(window) / span


def rvol(volumes: Sequence[float], span: int = 20) -> list:
    """Today's volume over the exclusive-prior mean. None before the window
    fills; baseline is undefined (not 1.0) on the first tradable day."""
    vols = _series(volumes, "volumes")
    out: list = []
    for i in range(len(vols)):
        base = _prior_mean(vols, i, span)
        out.append(None if base is None or base == 0 else vols[i] / base)
    return out


def delivery_volume(volumes: Sequence[float], delivery_pcts: Sequence[Optional[float]]) -> list:
    """DeliveryVolume = Volume x Delivery% / 100, per session. None wherever
    delivery% is absent — volume alone is never a substitute."""
    vols = _series(volumes, "volumes")
    pcts = _series(delivery_pcts, "delivery_pcts", allow_none=True)
    if len(vols) != len(pcts):
        raise ContractError("volumes and delivery_pcts must have equal length")
    out: list = []
    for vol, pct in zip(vols, pcts):
        if pct is None:
            out.append(None)
        elif pct < 0 or pct > 100:
            raise ContractError(f"delivery_pct {pct} outside 0..100")
        else:
            out.append(vol * pct / 100.0)
    return out


def delivery_volume_ratio(
    volumes: Sequence[float],
    delivery_pcts: Sequence[Optional[float]],
    span: int = 20,
) -> list:
    """Today's delivery volume over the exclusive-prior delivery-volume mean.

    Strict rule: the ratio at ``i`` exists only when delivery data is present
    for today AND for the ENTIRE prior window — a partially-populated baseline
    is never averaged into a number.
    """
    vols = _series(volumes, "volumes")
    pcts = _series(delivery_pcts, "delivery_pcts", allow_none=True)
    if len(vols) != len(pcts):
        raise ContractError("volumes and delivery_pcts must have equal length")
    dvs: list = []
    for vol, pct in zip(vols, pcts):
        if pct is None or pct < 0 or pct > 100:
            dvs.append(None)
        else:
            dvs.append(vol * pct / 100.0)

    out: list = []
    for i in range(len(dvs)):
        if i < span or dvs[i] is None or any(v is None for v in dvs[i - span:i]):
            out.append(None)
            continue
        base = sum(dvs[i - span:i]) / span
        out.append(None if base == 0 else dvs[i] / base)
    return out
