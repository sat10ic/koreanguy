"""Volatility / extension context (build manual Task P1.5): ADR, ATR, ATR%,
today's move in ADR units.

Frozen definitions:

* ``adr(highs, lows, span=20)`` — mean daily range (high-low) over the
  ``span`` sessions BEFORE index ``i`` (exclusive prior; the current session
  never sits in its own baseline). ``None`` before the window fills.
* ``atr(highs, lows, closes, span=14)`` — Wilder ATR. True Range needs the
  prior close, so the TR series starts at index 1; the ATR seed is the SMA of
  the first ``span`` TRs (available at index ``span``), then Wilder smoothing
  ``atr = (prev*(span-1) + tr)/span``. ``None`` before the seed.
* ``atr_pct`` — ATR over close, percent. ``None`` when ATR is None.
* ``today_move_adr(closes, adr_series)`` — signed (close[i]-close[i-1]) /
  adr[i]. ``None`` when either side is missing.

Use: volatility, extension, stop sanity, contraction, risk context — never a
setup trigger (manual P1.5). Warm-up returns None, never zero.
"""
from __future__ import annotations

from typing import Optional, Sequence

from unidesk.contracts.base import ContractError, require_float

from .participation import _series  # shared strict-series helper (same package)


def adr(highs: Sequence[float], lows: Sequence[float], span: int = 20) -> list:
    h = _series(highs, "highs")
    l = _series(lows, "lows")
    if len(h) != len(l):
        raise ContractError("highs and lows must have equal length")
    out: list = []
    for i in range(len(h)):
        if i < span:
            out.append(None)
            continue
        window = [(h[j] - l[j]) for j in range(i - span, i)]
        if any(r < 0 for r in window):
            raise ContractError("negative daily range in input data")
        out.append(sum(window) / span)
    return out


def true_ranges(highs: Sequence[float], lows: Sequence[float], closes: Sequence[float]) -> list:
    """TR[i] for i >= 1 (needs the prior close): max(h-l, |h-pc|, |l-pc|).
    Index 0 is None (no prior close exists — never invented)."""
    h = _series(highs, "highs")
    l = _series(lows, "lows")
    c = _series(closes, "closes")
    if not (len(h) == len(l) == len(c)):
        raise ContractError("highs, lows, closes must have equal length")
    out: list = [None]
    for i in range(1, len(h)):
        out.append(max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])))
    return out


def atr(highs: Sequence[float], lows: Sequence[float], closes: Sequence[float], span: int = 14) -> list:
    if span < 1:
        raise ContractError("span must be >= 1")
    trs = true_ranges(highs, lows, closes)
    n = len(trs)
    out: list = [None] * n
    if n <= span:
        return out
    seed = sum(trs[1:span + 1]) / span
    out[span] = seed
    prev = seed
    for i in range(span + 1, n):
        prev = (prev * (span - 1) + trs[i]) / span
        out[i] = prev
    return out


def atr_pct(atr_series: Sequence[Optional[float]], closes: Sequence[float]) -> list:
    c = _series(closes, "closes")
    if len(atr_series) != len(c):
        raise ContractError("atr_series and closes must have equal length")
    out: list = []
    for a, close in zip(atr_series, c):
        if a is None or close == 0:
            out.append(None)
        else:
            out.append(a / close * 100.0)
    return out


def today_move_adr(closes: Sequence[float], adr_series: Sequence[Optional[float]]) -> list:
    c = _series(closes, "closes")
    if len(c) != len(adr_series):
        raise ContractError("closes and adr_series must have equal length")
    out: list = []
    for i in range(len(c)):
        if i < 1 or adr_series[i] is None or adr_series[i] == 0:
            out.append(None)
            continue
        out.append((c[i] - c[i - 1]) / adr_series[i])
    return out
