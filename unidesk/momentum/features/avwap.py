"""Anchored VWAP (build manual Task P1.6) — participant-cost context.

Frozen definition: from the anchor index onward,

    avwap[i] = sum(typical[j] * volume[j] for j in anchor..i)
               / sum(volume[j] for j in anchor..i)

``typical`` = (high + low + close) / 3. Nothing before the anchor (None —
the anchor does not exist yet at those times, and back-filling a cost basis
would be inventing history). Anchor DETECTION (EP/BREAKOUT/IPO/…) belongs to
setup primitives; this module only prices a given anchor.

Confluence (multiple anchors) is the caller's job and must keep the source
levels inspectable — this module returns one series per anchor.
"""
from __future__ import annotations

from typing import Optional, Sequence

from unidesk.contracts.base import ContractError, require_float


def typical_price(highs: Sequence[float], lows: Sequence[float], closes: Sequence[float]) -> list:
    h = [require_float(v, f"highs[{i}]") for i, v in enumerate(highs)]
    l = [require_float(v, f"lows[{i}]") for i, v in enumerate(lows)]
    c = [require_float(v, f"closes[{i}]") for i, v in enumerate(closes)]
    if not (len(h) == len(l) == len(c)):
        raise ContractError("highs, lows, closes must have equal length")
    for i in range(len(h)):
        if l[i] > h[i]:
            raise ContractError(f"low[{i}] above high[{i}]")
    return [(h[i] + l[i] + c[i]) / 3.0 for i in range(len(h))]


def avwap(
    typical: Sequence[float],
    volumes: Sequence[float],
    anchor_index: int,
) -> list:
    """Anchored VWAP series. ``None`` before ``anchor_index``; a zero
    cumulative volume at/after the anchor yields None (no trade data — never
    a fabricated price)."""
    tp = [require_float(v, f"typical[{i}]") for i, v in enumerate(typical)]
    vol = [require_float(v, f"volumes[{i}]") for i, v in enumerate(volumes)]
    if len(tp) != len(vol):
        raise ContractError("typical and volumes must have equal length")
    if anchor_index < 0 or anchor_index >= len(tp):
        raise ContractError(f"anchor_index {anchor_index} outside the series")
    if any(v < 0 for v in vol):
        raise ContractError("negative volume in input data")

    out: list = [None] * len(tp)
    cum_pv = 0.0
    cum_v = 0.0
    for i in range(anchor_index, len(tp)):
        cum_pv += tp[i] * vol[i]
        cum_v += vol[i]
        out[i] = None if cum_v == 0 else cum_pv / cum_v
    return out
