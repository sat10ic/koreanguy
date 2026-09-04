"""N-51 — setup-family review horizons, versioned and configurable.

One 10-bar horizon for every family is wrong — EP resolves in 3-5 bars,
IPO base in 10-15. These are DEFAULTS from the review table, not truth.
Never silently tuned after observing performance (E8: that is fitting the
measurement to the result — owner-gated to change).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


HORIZON_VERSION = "horizons-v1-ep3-base10-ipo15"

HORIZONS: dict[str, int] = {
    "episodic_pivot": 3,
    "momentum_burst": 5,
    "inside_bar": 10,
    "base_breakout": 10,
    "pullback": 10,
    "reversal_reclaim": 10,
    "ipo_base": 15,
    "power_play": 5,
    "_default": 10,
}


def horizon_for(detector: str) -> int:
    return HORIZONS.get(detector, HORIZONS["_default"])


def all_horizons() -> dict[str, int]:
    return dict(HORIZONS)
