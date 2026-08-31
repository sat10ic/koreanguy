"""Reactor Scale activity score (adopted from traderlog/adopted/activity.py).

Clean-room reversal of the proprietary Reactor Scale, built from public NSE
bhavcopy fields (volume, num_trades, delivery_pct). The output is a
direction-neutral abnormal-activity analogue — never presented as
institutional identity, trade direction, or a risk input.

Formula (frozen coefficients, V2 calibration fit on 60 constraints):
    avg_trade_qty = volume / num_trades
    q_ratio = today_avg_qty / mean(prior_20_avg_qty)
    d_ratio = today_delivery_pct / mean(prior_19_delivery_pct)
    activity_score = 1.165335*q + 1.04631*d + 1.152161*(q*d)^0.84 - 0.213928

Coefficients and formula adopted verbatim from traderlog/adopted/activity.py
(provenance: manas_os/alpha/activity.py). The sole drift from the original
is the exclusive prior window (current session excluded from the denominator),
which is a deliberate brief-driven change, not a data-forced one.
"""
from __future__ import annotations

from typing import Optional, Sequence

from unidesk.contracts.base import ContractError, require_float

Q_COEFFICIENT = 1.165335
D_COEFFICIENT = 1.04631
INTERACTION_COEFFICIENT = 1.152161
INTERACTION_EXPONENT = 0.84
INTERCEPT = -0.213928
WARMUP_PRIOR = 20
DELIVERY_PRIOR = 19


def _avg_trade_qty(volume: float, num_trades: float) -> Optional[float]:
    """Shares per trade. Missing/zero denominator -> None."""
    if volume <= 0 or num_trades <= 0:
        return None
    return volume / num_trades


def _q_ratio(today_avg: float, prior_avg_qtys: Sequence[float]) -> Optional[float]:
    """Today's avg trade qty vs mean of prior 20 sessions (exclusive)."""
    if len(prior_avg_qtys) < WARMUP_PRIOR:
        return None
    window = list(prior_avg_qtys[-WARMUP_PRIOR:])
    mean = sum(window) / len(window)
    if mean <= 0 or today_avg <= 0:
        return None
    return today_avg / mean


def _d_ratio(today_delivery: float, prior_delivery: Sequence[float]) -> Optional[float]:
    """Today's delivery% vs mean of prior 19 sessions (exclusive)."""
    if len(prior_delivery) < DELIVERY_PRIOR:
        return None
    window = list(prior_delivery[-DELIVERY_PRIOR:])
    mean = sum(window) / len(window)
    if mean <= 0 or today_delivery <= 0:
        return None
    return today_delivery / mean


def _raw_score(q_ratio: float, d_ratio: float) -> float:
    """Unrounded activity score."""
    return (
        Q_COEFFICIENT * q_ratio
        + D_COEFFICIENT * d_ratio
        + INTERACTION_COEFFICIENT * ((q_ratio * d_ratio) ** INTERACTION_EXPONENT)
        + INTERCEPT
    )


def activity_score(
    *,
    volume: float,
    num_trades: float,
    delivery_pct: float,
    prior_volumes: Sequence[float],
    prior_num_trades: Sequence[float],
    prior_delivery_pcts: Sequence[float],
) -> Optional[dict]:
    """Compute Reactor Scale activity score for one symbol-date.

    Returns a dict with the score components, or None when any input is
    missing (warm-up, zero denominator, etc.) — never a fabricated value.

    ``prior_volumes``/``prior_num_trades``/``prior_delivery_pcts`` must be
    the chronological series of bars BEFORE the current session (strictly
    past). The function requires at least 20 prior sessions for q_ratio and
    19 for d_ratio.
    """
    today_avg = _avg_trade_qty(require_float(volume, "volume"),
                                require_float(num_trades, "num_trades"))
    if today_avg is None:
        return None

    prior_avg_qtys = []
    for v, n in zip(prior_volumes, prior_num_trades):
        a = _avg_trade_qty(require_float(v, "prior_volume"),
                           require_float(n, "prior_num_trades"))
        if a is not None:
            prior_avg_qtys.append(a)
    if len(prior_avg_qtys) < WARMUP_PRIOR:
        return None

    q = _q_ratio(today_avg, prior_avg_qtys)
    if q is None:
        return None

    today_deliv = require_float(delivery_pct, "delivery_pct")
    if today_deliv <= 0:
        return None
    clean_prior_delivery = [require_float(d, "prior_delivery_pct") for d in prior_delivery_pcts
                           if d is not None]
    d = _d_ratio(today_deliv, clean_prior_delivery)
    if d is None:
        return None

    raw = _raw_score(q, d)
    return {
        "activity_score": round(raw, 2),
        "q_ratio": round(q, 6),
        "d_ratio": round(d, 6),
        "avg_trade_qty": round(today_avg, 4),
    }