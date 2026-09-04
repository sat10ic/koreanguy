"""N-43 — Trade Planner: deterministic arithmetic over owner-supplied inputs.

The planner is a CALCULATOR (X-03 amendment, approved): qty = floor(risk_budget
/ risk_per_share). It authors nothing the owner did not supply. Every output
names its inputs and shows the binding constraint. Remove the risk-fraction
input and every size output disappears — never a fallback default.

Four distinct risk fields (never one number called "risk"):
  planned_risk   — what you intend to lose if the stop is hit
  stress_risk    — what you'd lose if the gap/liquidity scenario hit
  open_risk      — sum of planned risk across currently open positions
  profit_at_risk — how much unrealized profit is exposed to the current stop

THE BINDING CONSTRAINT IS ALWAYS SHOWN: "final qty 2,240 ← liquidity cap binding"
is the entire value of the constraint engine; a bare number is not.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PlannerInputs:
    symbol: str
    entry: float
    stop: float
    risk_fraction_pct: float          # owner's: e.g. 0.5
    equity: float                     # owner's: e.g. 50000
    max_position_pct: float           # owner's: e.g. 40
    open_risk_total: float = 0.0      # sum across open positions
    open_risk_ceiling_pct: Optional[float] = None  # tool-suggested per regime/breadth
    direction: str = "long"           # "long" | "short"


@dataclass(frozen=True)
class PlannerOutput:
    symbol: str
    qty: int
    binding_constraint: str           # which cap bound the size
    planned_risk: float
    planned_risk_pct: float
    position_value: float
    position_pct_of_equity: float
    risk_per_share: float
    open_risk_after: float
    open_risk_ceiling_breached: bool
    warnings: list[str]


def plan_trade(inputs: PlannerInputs) -> PlannerOutput:
    """Deterministic position sizing. The binding constraint is always named."""
    if inputs.entry <= 0 or inputs.stop <= 0:
        return PlannerOutput(inputs.symbol, 0, "invalid entry/stop", 0, 0, 0, 0, 0, 0, False,
                             ["entry and stop must be positive"])
    risk_per_share = abs(inputs.entry - inputs.stop)
    if risk_per_share <= 0:
        return PlannerOutput(inputs.symbol, 0, "entry == stop", 0, 0, 0, 0, 0, 0, False,
                             ["entry and stop must differ"])

    risk_budget = inputs.equity * inputs.risk_fraction_pct / 100.0
    qty_raw = int(risk_budget / risk_per_share)

    # constraint: max position as % of equity
    max_pos_value = inputs.equity * inputs.max_position_pct / 100.0
    qty_position_cap = int(max_pos_value / inputs.entry) if inputs.entry > 0 else 0

    # constraint: open-risk ceiling (computed from risk_budget for the cap;
    # the output open_risk_after uses the final capped qty)
    ceiling = None
    open_risk_after_uncapped = inputs.open_risk_total + risk_budget
    if inputs.open_risk_ceiling_pct is not None and inputs.open_risk_ceiling_pct > 0:
        ceiling = inputs.equity * inputs.open_risk_ceiling_pct / 100.0
        if open_risk_after_uncapped > ceiling:
            remaining = max(0, ceiling - inputs.open_risk_total)
            qty_open_risk = int(remaining / risk_per_share) if risk_per_share > 0 else 0
            qty_raw = min(qty_raw, qty_open_risk)

    qty = min(qty_raw, qty_position_cap)

    # determine binding constraint
    open_risk_after = inputs.open_risk_total + (qty * risk_per_share)
    if qty == 0:
        binding = "all constraints → zero size"
        if qty_position_cap == 0:
            binding = "position cap binds at zero (entry too high for equity)"
        elif ceiling is not None and open_risk_after_uncapped > ceiling:
            binding = "open-risk ceiling binds at zero"
    elif qty == qty_position_cap and qty_position_cap < int(inputs.equity * inputs.risk_fraction_pct / 100.0 / risk_per_share):
        binding = f"position cap binding (max {inputs.max_position_pct}% of equity)"
    elif ceiling is not None and open_risk_after_uncapped > ceiling:
        binding = f"open-risk ceiling binding ({inputs.open_risk_ceiling_pct}% of equity)"
    else:
        binding = f"risk fraction binding ({inputs.risk_fraction_pct}% of equity)"

    planned_risk = qty * risk_per_share
    planned_risk_pct = planned_risk / inputs.equity * 100 if inputs.equity else 0.0
    position_value = qty * inputs.entry
    position_pct = position_value / inputs.equity * 100 if inputs.equity else 0.0

    warnings: list[str] = []
    if inputs.direction == "long" and inputs.stop >= inputs.entry:
        warnings.append("stop is above entry for a long — inverted stop")
    if position_pct > inputs.max_position_pct:
        warnings.append(f"position {position_pct:.0f}% exceeds cap {inputs.max_position_pct}%")

    return PlannerOutput(
        symbol=inputs.symbol, qty=qty, binding_constraint=binding,
        planned_risk=planned_risk, planned_risk_pct=planned_risk_pct,
        position_value=position_value, position_pct_of_equity=position_pct,
        risk_per_share=risk_per_share,
        open_risk_after=open_risk_after,
        open_risk_ceiling_breached=(ceiling is not None and open_risk_after > ceiling),
        warnings=warnings,
    )
