"""OHLC / delivery invariants (Phase 0 spec §10.2 / §14.1).

Violating rows go to quarantine. They are never silently repaired.
"""
from __future__ import annotations

from typing import Optional

from unidesk.contracts.base import require_float


def ohlc_violations(
    *,
    open: float,
    high: float,
    low: float,
    close: float,
    volume: float,
    traded_value: Optional[float] = None,
) -> tuple[str, ...]:
    """Named invariant failures. Empty tuple = row is structurally valid."""
    open = require_float(open, "open")
    high = require_float(high, "high")
    low = require_float(low, "low")
    close = require_float(close, "close")
    volume = require_float(volume, "volume")
    failures = []
    if high < max(open, close):
        failures.append("high < max(open, close)")
    if low > min(open, close):
        failures.append("low > min(open, close)")
    if high < low:
        failures.append("high < low")
    if volume < 0:
        failures.append("volume < 0")
    if traded_value is not None:
        traded_value = require_float(traded_value, "traded_value")
        if traded_value < 0:
            failures.append("traded_value < 0")
    return tuple(failures)


def delivery_violations(
    *,
    traded_qty: float,
    deliverable_qty: float,
    delivery_pct_source: Optional[float] = None,
    delivery_pct_calc: Optional[float] = None,
    pct_tolerance: float = 0.2,
) -> tuple[str, ...]:
    traded_qty = require_float(traded_qty, "traded_qty")
    deliverable_qty = require_float(deliverable_qty, "deliverable_qty")
    failures = []
    if traded_qty < 0:
        failures.append("traded_qty < 0")
    if deliverable_qty < 0:
        failures.append("deliverable_qty < 0")
    if deliverable_qty > traded_qty:
        failures.append("deliverable_qty > traded_qty")
    if delivery_pct_source is not None and not (0.0 <= delivery_pct_source <= 100.0):
        failures.append("delivery_pct_source outside 0..100")
    if (
        delivery_pct_source is not None
        and delivery_pct_calc is not None
        and abs(delivery_pct_source - delivery_pct_calc) > pct_tolerance
    ):
        failures.append("delivery_pct source/calc diverge > tolerance")
    return tuple(failures)


def delivery_pct_calc(traded_qty: float, deliverable_qty: float) -> Optional[float]:
    traded_qty = require_float(traded_qty, "traded_qty")
    deliverable_qty = require_float(deliverable_qty, "deliverable_qty")
    if traded_qty <= 0:
        return None
    return deliverable_qty / traded_qty * 100.0
