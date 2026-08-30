"""T5 EP signature (S_ep) — Day-0 quality score (swing-edges spec §8.2).

Deterministic composite over caller-computed point-in-time values. Five
weighted components (gap significance, RVOL anomaly, close quality, prior
compression, delivery shock) plus two explicit guards:

* ``circuit_ep`` — a locked EP day's close_location is not informative;
  the close-quality component is excluded (coverage drops honestly) and the
  event is flagged for the delayed list, never scored as if it closed weak.
* ``climax_on_climax`` — prior 20d gain >= 40% is reported as a boolean
  guard for the experiment layer to filter on; it is NOT folded into the
  score (no invented penalty math — the spec treats it as an avoidance rule).

Score = weighted mean over AVAILABLE components; missing inputs reduce the
component set honestly and are named (R12). This module never recommends a
trade — Experiment B measures whether S_ep ranking beats gap-and-go.
"""
from __future__ import annotations

from dataclasses import dataclass

from unidesk.contracts.base import ContractError, require_float

WEIGHTS = {
    "gap_significance": 25.0,     # gap_pct: 5% -> 0, 12%+ -> 100
    "rvol_anomaly": 20.0,         # rvol: 2.0 -> 0, 4.0+ -> 100 (cash default)
    "close_quality": 20.0,        # close_loc: 0.5 -> 0, 0.9+ -> 100
    "prior_compression": 20.0,    # ATR percentile: 80 -> 0, 35 -> 100 (inverted)
    "delivery_shock": 15.0,       # delivery vs median: 1x -> 0, 3x+ -> 100
}


@dataclass(frozen=True)
class EPDecision:
    symbol: str
    session: str
    s_ep: float                       # 0..100 over available components
    coverage: float                   # available weight / total weight
    circuit_ep: bool                  # locked day — delayed-list candidate
    climax_on_climax: Optional[bool]  # prior 20d gain >= 40% (None if unknown)
    components: dict
    unknowns: tuple


def _clamp(v: float) -> float:
    return max(0.0, min(100.0, v))


def _lin(value: float, zero_at: float, hundred_at: float) -> float:
    if zero_at == hundred_at:
        raise ContractError("zero_at == hundred_at")
    return _clamp((value - zero_at) / (hundred_at - zero_at) * 100.0)


def ep_signature(
    *,
    symbol: str,
    session: str,
    gap_pct: float,
    rvol: Optional[float],
    close_loc: Optional[float],
    prior_compression_pctile: Optional[float],
    delivery_shock: Optional[float],
    circuit_locked: bool = False,
    prior_20d_gain_pct: Optional[float] = None,
) -> EPDecision:
    symbol = str(symbol).strip()
    if not symbol:
        raise ContractError("symbol required")
    gap = require_float(gap_pct, "gap_pct")

    comps: dict[str, Optional[float]] = {}
    unknowns: list[str] = []

    comps["gap_significance"] = _lin(gap, 5.0, 12.0)

    if rvol is None:
        comps["rvol_anomaly"] = None
        unknowns.append("RVOL_UNAVAILABLE")
    else:
        comps["rvol_anomaly"] = _lin(require_float(rvol, "rvol"), 2.0, 4.0)

    if circuit_locked:
        comps["close_quality"] = None
        unknowns.append("CIRCUIT_EP_CLOSE_NOT_INFORMATIVE")
    elif close_loc is None:
        comps["close_quality"] = None
        unknowns.append("CLOSE_LOC_UNAVAILABLE")
    else:
        comps["close_quality"] = _lin(require_float(close_loc, "close_loc"), 0.5, 0.9)

    if prior_compression_pctile is None:
        comps["prior_compression"] = None
        unknowns.append("COMPRESSION_PERCENTILE_UNAVAILABLE")
    else:
        pct = require_float(prior_compression_pctile, "prior_compression_pctile")
        comps["prior_compression"] = _clamp(100.0 - (pct / 80.0) * 100.0)

    if delivery_shock is None:
        comps["delivery_shock"] = None
        unknowns.append("DELIVERY_SHOCK_UNAVAILABLE")
    else:
        comps["delivery_shock"] = _lin(require_float(delivery_shock, "delivery_shock"), 1.0, 3.0)

    climax: Optional[bool] = None
    if prior_20d_gain_pct is not None:
        climax = prior_20d_gain_pct >= 40.0

    available_weight = sum(WEIGHTS[k] for k in WEIGHTS if comps.get(k) is not None)
    total_weight = sum(WEIGHTS.values())
    weighted = sum(comps[k] * WEIGHTS[k] for k in WEIGHTS if comps.get(k) is not None)
    s_ep = round(weighted / available_weight, 3) if available_weight else 0.0

    return EPDecision(
        symbol=symbol, session=session, s_ep=s_ep,
        coverage=round(available_weight / total_weight, 3),
        circuit_ep=circuit_locked,
        climax_on_climax=climax,
        components=comps, unknowns=tuple(unknowns),
    )
