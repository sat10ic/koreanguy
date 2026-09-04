"""N-44 — Portfolio Heat: four distinct risk fields, sector clusters.

NEVER one number called "risk". Each field answers a different question:
  planned_risk    — what you INTEND to lose if every stop is hit
  stress_risk    — what you'd lose in a gap/liquidity scenario (no stop protection)
  open_risk      — planned risk currently deployed (subset of planned)
  profit_at_risk — how much unrealised profit is exposed to the current stop

Sector clusters: exposure grouped by the merged Chartsmaze+Nexus sector map.
Theme clusters: "—" until N-29 lands. Planned risk can never go negative.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class OpenPosition:
    symbol: str
    sector: Optional[str]
    entry: float
    stop: float
    quantity: int
    current_price: float
    planned_risk: float          # what the planner allocated
    unrealised_pnl: float        # current marks


@dataclass(frozen=True)
class PortfolioHeat:
    planned_risk: float
    stress_risk: float
    open_risk: float
    profit_at_risk: float
    planned_risk_pct: float
    stress_risk_pct: float
    sector_clusters: dict[str, dict]
    positions: list


def compute_heat(
    positions: list[OpenPosition],
    equity: float,
    *,
    gap_stress_pct: float = 10.0,
) -> PortfolioHeat:
    """Aggregate the four risk fields from open positions.

    ``gap_stress_pct``: the stress scenario assumes a gap of this % through
    the stop (stop protection is void in a gap). Frozen at 10% (a typical
    NSE single-day circuit band). Stated, not hidden."""
    planned = sum(p.planned_risk for p in positions)
    stress = sum(
        (abs(p.entry - p.stop) + p.entry * gap_stress_pct / 100.0) * p.quantity
        for p in positions
    )
    # open risk = planned risk still deployed (positions not yet in profit)
    open_risk = sum(
        p.planned_risk for p in positions if p.current_price < p.entry
    )
    # profit at risk = unrealised profit that would evaporate if the stop is hit
    profit_at_risk = sum(
        max(0, p.current_price - p.stop) * p.quantity
        for p in positions if p.current_price > p.stop
    )

    # sector clusters
    sector_clusters: dict[str, dict] = {}
    for p in positions:
        key = p.sector or "UNMAPPED"
        c = sector_clusters.setdefault(key, {"planned_risk": 0.0, "count": 0})
        c["planned_risk"] += p.planned_risk
        c["count"] += 1

    planned_pct = planned / equity * 100 if equity else 0.0
    stress_pct = stress / equity * 100 if equity else 0.0

    return PortfolioHeat(
        planned_risk=planned,
        stress_risk=stress,
        open_risk=open_risk,
        profit_at_risk=profit_at_risk,
        planned_risk_pct=round(planned_pct, 2),
        stress_risk_pct=round(stress_pct, 2),
        sector_clusters=sector_clusters,
        positions=[p.symbol for p in positions],
    )
