"""ROTATION N-25 — group RS: percentile (default) and JdK (Pro/Lab) forms.

MATHS (frozen; HANDOFF_2026-09-04_MARKET_ROTATION §2):
  JdK:  RS          = group_index / benchmark_index
        RS_Ratio    = 100 * EMA(RS, m) / RollingMean(EMA(RS, m), m)
        ROC         = (RS_Ratio[t] - RS_Ratio[t-k]) / RS_Ratio[t-k]
        RS_Momentum = 100 + 100 * EMA(ROC, m)
  alpha = 2/(m+1); daily m=20, k=20. Warm-up ≈ 2m+k ≈ 60 sessions → None
  before that (R12: never a partial value).

Percentile form (spec §20, the default): percentile rank of group RS and
group RS-accel across ALL GROUPS ON THAT DATE — point-in-time by
construction; no full-sample percentiles.

RS acceleration (spec §11): slope(RS_ratio, 5) − slope(RS_ratio, 20).
THE FRONTEND NEVER COMPUTES ACCELERATION — it renders what the backend
emits.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional, Sequence


def ema(values: Sequence[float], span: int) -> list[Optional[float]]:
    """EMA with warm-up: the first span-1 values are None (R12)."""
    if span < 1:
        raise ValueError("span must be >= 1")
    alpha = 2.0 / (span + 1.0)
    out: list[Optional[float]] = [None] * len(values)
    prev: Optional[float] = None
    for i, v in enumerate(values):
        if prev is None:
            prev = v
        else:
            prev = alpha * v + (1 - alpha) * prev
        out[i] = prev if i >= span - 1 else None
    return out


def jdk_rs_series(
    group_closes: Sequence[float],
    benchmark_closes: Sequence[float],
    *,
    m: int = 20,
    k: int = 20,
) -> list[tuple[Optional[float], Optional[float]]]:
    """(rs_ratio, rs_momentum) per session; (None, None) before ~2m+k sessions.

    RS = group/benchmark; RS_Ratio = 100·EMA(RS,m)/SMA(EMA(RS),m);
    ROC = (ratio[t] − ratio[t−k]) / ratio[t−k]; momentum = 100 + 100·EMA(ROC, m).
    """
    if len(group_closes) != len(benchmark_closes):
        raise ValueError("group and benchmark series must have equal length")
    if any(b == 0 for b in benchmark_closes):
        raise ValueError("benchmark contains zero — division would fabricate a value")

    rs = [g / b for g, b in zip(group_closes, benchmark_closes)]
    ema_rs = ema(rs, m)

    # SMA of the EMA series, skipping the warm-up Nones
    ratio: list[Optional[float]] = [None] * len(rs)
    for i in range(len(rs)):
        if i >= m - 1 and ema_rs[i] is not None:
            window = ema_rs[i - m + 1: i + 1]
            if all(v is not None for v in window):
                sma_val = sum(window) / m
                if sma_val:
                    ratio[i] = 100.0 * ema_rs[i] / sma_val

    momentum: list[Optional[float]] = [None] * len(rs)
    warm = 2 * m + k  # ~60 for daily defaults
    rocs: list[float] = []
    for i in range(len(rs)):
        if i < warm or ratio[i] is None or ratio[i - k] in (None, 0):
            continue
        roc = (ratio[i] - ratio[i - k]) / ratio[i - k]
        rocs.append(roc)
        # EMA over the ROC sequence
        alpha = 2.0 / (m + 1.0)
        if len(rocs) == 1:
            ema_roc = roc
        else:
            ema_roc = alpha * roc + (1 - alpha) * ema_roc
        momentum[i] = 100.0 + 100.0 * ema_roc

    return list(zip(ratio, momentum))


def percentile_rank(values: Sequence[float], value: float) -> float:
    """Percentile of ``value`` within ``values`` (0-100). Ties share the
    lowest rank (consistent with scipy rankdata 'min' on the peer set)."""
    below = sum(1 for v in values if v < value)
    total = len(values)
    if total <= 1:
        return 50.0
    return round(100.0 * below / (total - 1), 1)


def percentile_normalise(
    *,
    session: str,
    groups: dict[str, tuple[Optional[float], Optional[float]]],
) -> dict[str, dict[str, Optional[float]]]:
    """Percentile-form axes (the default): x = percentile of RS_Ratio, y =
    percentile of RS_Momentum, across ALL GROUPS ON THAT DATE (spec §20).
    Groups with None on an axis are excluded from that axis's peer set and
    get None — no fabricated midpoint."""
    ratios = [v[0] for v in groups.values() if v[0] is not None]
    momenta = [v[1] for v in groups.values() if v[1] is not None]
    out: dict[str, dict[str, Optional[float]]] = {}
    for name, (ratio, mom) in groups.items():
        out[name] = {
            "rs_ratio_pct": percentile_rank(ratios, ratio) if ratio is not None and len(ratios) > 1 else None,
            "rs_momentum_pct": percentile_rank(momenta, mom) if mom is not None and len(momenta) > 1 else None,
        }
    return out


def rs_acceleration(
    ratio_series: Sequence[Optional[float]],
    as_of_index: int,
    *,
    short: int = 5,
    long: int = 20,
) -> Optional[float]:
    """slope(short) − slope(long) over the RS_Ratio series (spec §11).

    Slope is least-squares on the log ratio — stated per the handoff's
    "state which". Returns None when either window is incomplete. The
    frontend renders this; it never computes it."""
    if as_of_index >= len(ratio_series):
        return None

    def _slope(window: int) -> Optional[float]:
        start = as_of_index - window + 1
        if start < 0:
            return None
        pts = []
        for i in range(start, as_of_index + 1):
            v = ratio_series[i]
            if v is None or v <= 0:
                return None
            pts.append(v)
        if len(pts) < window:
            return None
        n = len(pts)
        xs = list(range(n))
        ys = [__import__("math").log(v) for v in pts]
        mean_x = sum(xs) / n
        mean_y = sum(ys) / n
        num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
        den = sum((x - mean_x) ** 2 for x in xs)
        return num / den if den else None

    s = _slope(short)
    l = _slope(long)
    if s is None or l is None:
        return None
    return round(s - l, 6)
