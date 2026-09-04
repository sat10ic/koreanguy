"""Structural levels — pivot-density KDE (clean-room from the published
description of SatohK's `Support & Resistance KDE`; reimplemented from the
algorithm description, never from the Pine source — the author requests
contact before non-personal use of the logic, and none was made).

The idea, frozen (HANDOFF_2026-09-04_MARKET_ROTATION §0.1 / levels handoff §1):
collect CONFIRMED swing pivots over a lookback; for each, place a triangular
kernel centred on the pivot price whose half-width is that pivot bar's own
high−low range; sum the kernels over a price grid; take local maxima; keep
the top levels separated by at least ``MIN_SEPARATION_ATR × atr``.

Two properties make it fit this repo: the kernel bandwidth is data-derived
(the pivot bar's own range — no magic constant), and only confirmed pivots
are used, so the module is point-in-time by construction.

Point-in-time contract — explicit in ``confirmed_pivots``' signature: a pivot
at bar *i* is returned only when ``as_of_index >= i + right``. Nothing at or
beyond the as-of boundary is ever read.

Warm-up refuses: fewer than ``MIN_PIVOTS`` confirmed pivots in the lookback
window → ``None`` (R12: never an empty list, never 0).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from unidesk.contracts.base import ContractError, ensure_date  # noqa: F401 (conventions)

PIVOT_LEFT_DEFAULT = 10
PIVOT_RIGHT_DEFAULT = 5    # a pivot is CONFIRMED only after this many bars
LOOKBACK_DEFAULT = 400     # sessions of pivot history
MIN_SEPARATION_ATR = 1.5
GRID_STEPS = 100
MIN_PIVOTS = 8             # below this, refuse — a KDE over 3 pivots is noise


@dataclass(frozen=True)
class Pivot:
    index: int
    price: float
    bar_range: float
    kind: str                 # "HIGH" | "LOW"


@dataclass(frozen=True)
class Level:
    price: float
    density: float
    n_supporting_pivots: int
    kind: str                 # kind of the strongest supporting pivot


def _require_series(name: str, *series: Sequence[float]) -> None:
    lengths = {len(s) for s in series}
    if len(lengths) != 1:
        raise ContractError(f"{name}: series lengths must match, got {sorted(lengths)}")


def confirmed_pivots(
    highs: Sequence[float],
    lows: Sequence[float],
    *,
    left: int,
    right: int,
    as_of_index: int,
) -> list[Pivot]:
    """Swing pivots confirmed as of ``as_of_index`` (exclusive bound on the
    future: a pivot at bar *i* appears only when ``as_of_index >= i + right``).

    Pivot HIGH at *i*: ``highs[i]`` is strictly greater than every high in
    ``[i-left, i-1]`` and at least every high in ``[i+1, i+right]``. Pivot
    LOW symmetric on ``lows`` (strict on the left, tolerant on the right).
    The asymmetric rule kills plateau duplicates: a flat series has no
    pivots, and a run of equal highs pivots once, at its end."""
    if left < 1 or right < 1:
        raise ContractError("left and right must be >= 1")
    _require_series("highs/lows", highs, lows)
    n = len(highs)
    if as_of_index is None or not (0 <= as_of_index <= n):
        raise ContractError(f"as_of_index must be in [0, {n}]")
    out: list[Pivot] = []
    for i in range(left, as_of_index - right + 1):
        hi, lo = highs[i], lows[i]
        w_left_h = highs[max(0, i - left):i]
        w_right_h = highs[i + 1:min(n, i + right + 1)]
        w_left_l = lows[max(0, i - left):i]
        w_right_l = lows[i + 1:min(n, i + right + 1)]
        if w_left_h and all(hi > h for h in w_left_h) and all(hi >= h for h in w_right_h):
            out.append(Pivot(i, float(hi), float(hi - lows[i]), "HIGH"))
        elif w_left_l and all(lo < l for l in w_left_l) and all(lo <= l for l in w_right_l):
            out.append(Pivot(i, float(lo), float(highs[i] - lo), "LOW"))
    return out


def level_density(pivots: Sequence[Pivot], grid: Sequence[float]) -> list[float]:
    """Sum of triangular kernels: kernel of pivot p at price g is
    ``max(0, 1 - |g - p.price| / p.bar_range)`` — zero beyond the pivot's own
    bar range. Pivots with non-positive range are skipped (they have no
    width, so they claim no density)."""
    density = [0.0] * len(grid)
    for p in pivots:
        if p.bar_range <= 0:
            continue
        for gi, g in enumerate(grid):
            w = 1.0 - abs(g - p.price) / p.bar_range
            if w > 0.0:
                density[gi] += w
    return density


def structural_levels(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    atr: float,
    *,
    left: int = PIVOT_LEFT_DEFAULT,
    right: int = PIVOT_RIGHT_DEFAULT,
    lookback: int = LOOKBACK_DEFAULT,
    as_of_index: Optional[int] = None,
    grid_steps: int = GRID_STEPS,
    min_separation_atr: float = MIN_SEPARATION_ATR,
    min_pivots: int = MIN_PIVOTS,
) -> Optional[list[Level]]:
    """Ordered structural levels (strongest first), or ``None`` on warm-up.

    ``atr`` is the caller-supplied volatility unit for the separation rule
    (e.g. ATR(14) at the as-of session). Levels are local maxima of the pivot
    density, kept at least ``min_separation_atr * atr`` apart. Fewer than
    ``min_pivots`` confirmed pivots in the lookback window → ``None``."""
    if atr is None or atr <= 0:
        raise ContractError("atr must be > 0")
    if grid_steps < 10:
        raise ContractError("grid_steps must be >= 10")
    _require_series("highs/lows/closes", highs, lows, closes)
    n = len(closes)
    if n == 0:
        return None
    if as_of_index is None:
        as_of_index = n
    if not (0 <= as_of_index <= n):
        raise ContractError(f"as_of_index must be in [0, {n}]")

    lo_bound = max(0, as_of_index - lookback)
    pivots = [p for p in confirmed_pivots(
        highs[lo_bound:as_of_index], lows[lo_bound:as_of_index],
        left=left, right=right, as_of_index=as_of_index - lo_bound,
    )]
    # re-anchor pivot indices to absolute positions
    pivots = [Pivot(p.index + lo_bound, p.price, p.bar_range, p.kind) for p in pivots]

    if len(pivots) < min_pivots:
        return None

    lo = min(p.price for p in pivots)
    hi = max(p.price for p in pivots)
    if hi <= lo:
        # every pivot at one price: the level IS that price
        supporting = list(pivots)
        return [Level(price=lo, density=float(len(pivots)),
                      n_supporting_pivots=len(pivots),
                      kind=max(pivots, key=lambda p: p.bar_range).kind)]
    step = (hi - lo) / grid_steps
    grid = [lo + step * i for i in range(grid_steps + 1)]
    density = level_density(pivots, grid)

    # local maxima of the density, strongest first. Boundary points count as
    # maxima against their single inner neighbour — a cluster at the edge of
    # the pivot price range is as real as an interior one.
    maxima: list[tuple[int, float]] = []
    for gi in range(len(grid)):
        left_d = density[gi - 1] if gi > 0 else -1.0
        right_d = density[gi + 1] if gi < len(grid) - 1 else -1.0
        if density[gi] > left_d and density[gi] >= right_d and density[gi] > 0:
            maxima.append((gi, density[gi]))
    maxima.sort(key=lambda x: -x[1])

    levels: list[Level] = []
    min_sep = min_separation_atr * atr
    for gi, dens in maxima:
        price = grid[gi]
        if any(abs(price - lv.price) < min_sep for lv in levels):
            continue
        supporting = [p for p in pivots if abs(p.price - price) <= p.bar_range]
        if not supporting:
            continue
        strongest = max(supporting, key=lambda p: p.bar_range)
        levels.append(Level(price=price, density=dens,
                            n_supporting_pivots=len(supporting), kind=strongest.kind))
    return levels or None


def nearest_below(levels: Sequence[Level], price: float) -> Optional[Level]:
    """Strongest level strictly below ``price`` (levels are strongest-first)."""
    below = [lv for lv in levels if lv.price < price]
    return max(below, key=lambda lv: lv.price) if below else None


def nearest_above(levels: Sequence[Level], price: float) -> Optional[Level]:
    """Strongest level strictly above ``price`` (levels are strongest-first)."""
    above = [lv for lv in levels if lv.price > price]
    return min(above, key=lambda lv: lv.price) if above else None
