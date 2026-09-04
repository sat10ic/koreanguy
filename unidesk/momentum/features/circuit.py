"""Circuit / structural exit-risk (build manual Task P1.8).

Uses only OFFICIAL circuit bands (upper/lower circuit on the daily bar) —
never inferred from depth (manual acceptance). Missing bands mean UNKNOWN
with the named reason; the distinction between "no bands published" and
"bands present and far" is preserved (R12).
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from unidesk.contracts.base import ContractError, require_float


class CircuitRiskState(Enum):
    UC_RISK = "UC_RISK"          # at/near the upper band: exit flexibility at risk
    LC_RISK = "LC_RISK"          # at/near the lower band
    NONE = "NONE"                # bands present and comfortably away
    UNKNOWN = "UNKNOWN"          # bands not published for this session


def circuit_risk_state(
    close: float,
    upper_circuit: Optional[float],
    lower_circuit: Optional[float],
    proximity_pct: float = 2.0,
) -> tuple[CircuitRiskState, tuple]:
    """Return (state, reasons). ``proximity_pct`` is caller policy (config),
    passed in — not a hard-coded product threshold."""
    close = require_float(close, "close")
    if close < 0:
        raise ContractError("close must be non-negative")
    if proximity_pct < 0:
        raise ContractError("proximity_pct must be non-negative")

    if upper_circuit is None or lower_circuit is None:
        return CircuitRiskState.UNKNOWN, ("CIRCUIT_BANDS_NOT_PUBLISHED",)
    upper = require_float(upper_circuit, "upper_circuit")
    lower = require_float(lower_circuit, "lower_circuit")
    if upper < lower:
        raise ContractError("upper_circuit below lower_circuit")

    band = upper - lower
    near = band * (proximity_pct / 100.0) if band > 0 else 0.0
    if close >= upper - near:
        return CircuitRiskState.UC_RISK, ("near_upper_circuit",)
    if close <= lower + near:
        return CircuitRiskState.LC_RISK, ("near_lower_circuit",)
    return CircuitRiskState.NONE, ()
